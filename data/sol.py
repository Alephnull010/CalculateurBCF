import json
import os
import math

# Facteur de Van Bemmelen : MO (%) = Corg (%) × VAN_BEMMELEN_FACTOR
VAN_BEMMELEN_FACTOR = 1.724

# --- Clés obligatoires dans le JSON ---
# Note : "matiere_organique" n'est pas listée ici bien qu'obligatoire au sens
# large — elle est requise SAUF si "carbone_organique_mgkg" est fourni à la
# place (voir load_sol), auquel cas elle est dérivée automatiquement.
SOL_REQUIRED_KEYS = [
    "pH",
    "conc_air",
]

# --- Clés optionnelles avec leurs valeurs par défaut ---
SOL_OPTIONAL_KEYS = {
    "temperature":             17.5,  # °C — Météo-France si non fourni
    "pct_argile":              None,  # % — si None → Rawls utilisé pour densité
    "pct_limon":               None,  # % — si None → Rawls utilisé pour densité
    "carbone_organique_mgkg":  None,  # mg/kg — COT labo ; si fourni, remplace l'estimation MO/1.724
                                       # et peut aussi servir à dériver matiere_organique si absente
}


# ─────────────────────────────────────────────
# Fonctions d'estimation (pédotransfer functions)
# ─────────────────────────────────────────────

def estimate_densite(MO: float,
                     pct_argile: float = None,
                     pct_limon: float = None) -> float:
    """
    Estime la densité apparente du sol (kg/dm³)

    Si argile + limon disponibles → Manrique & Jones (1991)
    Sinon                         → Rawls (1983)
    """
    if pct_argile is not None and pct_limon is not None:
        # Manrique & Jones (1991)
        da = (1.519
              - 0.0234 * pct_argile
              - 0.00078 * pct_limon
              - 0.59 * MO)
    else:
        # Rawls (1983) — fallback
        da = 1.66 - 0.318 * math.sqrt(MO)

    # Bornes réalistes
    return round(max(0.8, min(da, 1.8)), 3)


def estimate_fraction_eau(MO: float,
                          pct_argile: float = None) -> float:
    """
    Estime la fraction volumique en eau à la capacité au champ (m³/m³)

    Si argile disponible → Saxton & Rawls (2006) simplifié
    Sinon               → valeur par défaut INERIS (0.30)
    """
    if pct_argile is not None:
        # Saxton & Rawls (2006) simplifié
        fw = (0.299
              - 0.251 * MO
              + 0.195 * (pct_argile / 100))
    else:
        fw = 0.30   # valeur par défaut INERIS

    # Bornes réalistes
    return round(max(0.1, min(fw, 0.6)), 3)


def estimate_fraction_air(densite: float,
                          fraction_eau: float) -> float:
    """
    Estime la fraction volumique en air (m³/m³)

    fraction_air = porosité totale - fraction_eau
    porosité     = 1 - (Da / Dr)
    Dr           = densité réelle des particules = 2.65 kg/dm³
    """
    Dr       = 2.65
    porosite = 1.0 - (densite / Dr)
    fa       = porosite - fraction_eau

    # Bornes réalistes
    return round(max(0.0, min(fa, 0.5)), 3)


# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────

def validate_sol(sol: dict, site_name: str) -> None:
    """
    Vérifie la cohérence des paramètres sol calculés
    """
    # Fractions volumiques
    total = sol["fraction_eau"] + sol["fraction_air"]
    if total >= 1.0:
        raise ValueError(
            f"fraction_eau ({sol['fraction_eau']}) + "
            f"fraction_air ({sol['fraction_air']}) = {total:.3f} >= 1.0 — "
            f"vérifier les paramètres sol de site_{site_name}.json"
        )

    # Densité
    if not (0.8 <= sol["densite"] <= 1.8):
        raise ValueError(
            f"Densité estimée = {sol['densite']} hors plage [0.8 ; 1.8] — "
            f"vérifier %MO, %argile, %limon"
        )

    # MO
    if not (0.0 < sol["matiere_organique"] < 1.0):
        raise ValueError(
            f"matiere_organique = {sol['matiere_organique']} — "
            f"doit être une fraction (ex: 0.17 pour 17%)"
        )

    # conc_air — vérifie que tous les polluants sont présents
    from data.polluants import POLLUANTS
    missing_air = [p for p in POLLUANTS if p not in sol["conc_air"]]
    if missing_air:
        raise ValueError(
            f"conc_air manquante pour : {missing_air} — "
            f"utiliser seuil de quantification si non mesuré"
        )



# ─────────────────────────────────────────────
# Loader principal
# ─────────────────────────────────────────────

def load_sol(site_name: str = "default") -> dict:
    """
    Charge et complète les paramètres sol depuis un fichier JSON.

    Paramètres obligatoires dans le JSON :
        pH, conc_air, conc_sol, et matiere_organique OU carbone_organique_mgkg
        (au moins l'un des deux — voir ci-dessous)

    Paramètres optionnels (estimés automatiquement si absents) :
        pct_argile, pct_limon, temperature

    Paramètres optionnels de mesure directe (remplacent une estimation) :
        carbone_organique_mgkg — COT mesuré en laboratoire (mg/kg). Si fourni :
        - remplace l'estimation carbone_organique = matiere_organique / 1,724
          (facteur de Van Bemmelen, une approximation à éviter quand le COT
          est mesuré directement) ;
        - et si matiere_organique est absente du JSON, la dérive automatiquement
          (matiere_organique = carbone_organique_mgkg/1e6 × 1,724) — on peut
          donc renseigner l'un OU l'autre, pas nécessairement les deux.

    Paramètres calculés automatiquement :
        carbone_organique, densite, fraction_eau, fraction_air

    Usage :
        sol = load_sol("site_A")
        sol = load_sol()          # charge site_default.json
    """

    # --- Chargement JSON ---
    path = os.path.join(
        os.path.dirname(__file__),
        "sites",
        f"site_{site_name}.json"
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Fichier site introuvable : {path}\n"
            f"Créez un fichier data/sites/site_{site_name}.json "
            f"en vous basant sur site_default.json"
        )

    with open(path, encoding="utf-8") as f:
        sol = json.load(f)

    # --- Validation clés obligatoires ---
    missing = [k for k in SOL_REQUIRED_KEYS if k not in sol]
    if missing:
        raise ValueError(
            f"Paramètres obligatoires manquants dans "
            f"site_{site_name}.json : {missing}"
        )

    # --- Injection valeurs optionnelles manquantes ---
    for key, default in SOL_OPTIONAL_KEYS.items():
        if key not in sol:
            sol[key] = default
            print(f"  [info] {key} non fourni -> valeur par défaut : {default}")

    # --- matiere_organique : obligatoire, sauf si carbone_organique_mgkg fourni ---
    if "matiere_organique" not in sol:
        if sol["carbone_organique_mgkg"] is not None:
            sol["matiere_organique"] = round(
                (sol["carbone_organique_mgkg"] / 1e6) * VAN_BEMMELEN_FACTOR, 4
            )
            print(
                f"  [info] matiere_organique non fournie -> dérivée du COT labo : "
                f"{sol['matiere_organique']:.4f} ({sol['matiere_organique']*100:.2f} %)"
            )
        else:
            raise ValueError(
                f"Il faut fournir 'matiere_organique' ou 'carbone_organique_mgkg' "
                f"dans site_{site_name}.json"
            )

    # --- Calculs automatiques ---
    MO         = sol["matiere_organique"]
    pct_argile = sol.get("pct_argile")
    pct_limon  = sol.get("pct_limon")
    cot_mgkg   = sol.get("carbone_organique_mgkg")

    if cot_mgkg is not None:
        sol["carbone_organique"]      = round(cot_mgkg / 1e6, 4)
        sol["carbone_organique_source"] = "mesure_labo"
    else:
        sol["carbone_organique"]      = round(MO / VAN_BEMMELEN_FACTOR, 4)
        sol["carbone_organique_source"] = "estime_MO/1.724"

    sol["densite"]           = estimate_densite(MO, pct_argile, pct_limon)
    sol["fraction_eau"]      = estimate_fraction_eau(MO, pct_argile)
    sol["fraction_air"]      = estimate_fraction_air(
                                   sol["densite"],
                                   sol["fraction_eau"]
                               )

    # --- Validation cohérence globale ---
    validate_sol(sol, site_name)

    # --- Résumé console ---
    print(f"\n---------- Sol chargé : site_{site_name}")
    print(f"   pH               = {sol['pH']}")
    print(f"   MO               = {sol['matiere_organique']*100:.1f} %")
    print(f"   Corg             = {sol['carbone_organique']:.4f}  ({sol['carbone_organique_source']})")
    print(f"   Densité estimée  = {sol['densite']} kg/dm³")
    print(f"   Fraction eau     = {sol['fraction_eau']}")
    print(f"   Fraction air     = {sol['fraction_air']}")
    print(f"   Température      = {sol['temperature']} °C")

    return sol