import argparse
import sys
import pandas as pd
from data.polluants  import POLLUANTS
from data.vegetaux   import VEGETAUX
from data.sol        import load_sol
from core.calculator import compute_bre
from data.metaux     import compute_bcf_metaux
from data.pcb        import compute_bcf_pcb

# Colonnes à conserver dans l'onglet Métaux
_COLS_METAUX = [
    "ETM", "Categorie_INERIS", "Br_E", "Br_E_source", "Cs_site", "unité", "modele",
    "BCF_min", "BCF_median", "BCF_max", "BCF_mean_geom_pond",
    "Cs_valid_min", "Cs_valid_max", "mode_filtrage", "n_total", "n_outliers_grubbs",
    "A_simple", "B_simple", "r2_simple", "p_simple",
    "regression_retenue", "best_distrib",
]

# Colonnes à conserver dans l'onglet PCB (table officielle INERIS)
_COLS_PCB = [
    "substance", "sigle", "nom", "famille", "pcb_numero", "categorie",
    "Br_min", "Br_max", "Br_ponctuel",
    "Bf_min", "Bf_max", "Bf_ponctuel",
]

# Ordre d'affichage des feuilles par catégorie végétale
CATEGORIE_ORDER = [
    "légumes_feuilles", "légumes_fruits", "légumes_racines",
    "tubercules",
]

# Mapping des catégories métaux (BAPPET, tirets) vers la taxonomie unifiée
_MET_CAT_MAP = {
    "légumes-feuilles": "légumes_feuilles",
    "légumes-fruits":   "légumes_fruits",
    "légumes-racines":  "légumes_racines",
    "tubercules":       "tubercules",
    "céréales":         "céréales",
    "fourrage":         "fourrage",
}

# Mapping des catégories PCB (BAPPOP, sans accents) vers la taxonomie unifiée
_PCB_CAT_MAP = {
    "legumes_feuilles": "légumes_feuilles",
    "legumes_fruits":   "légumes_fruits",
    "legumes_racines":  "légumes_racines",
    "tubercules":       "tubercules",
    "cereales":         "céréales",
    "fourrage":         "fourrage",
}

_UNIFIED_COLS = ["polluant", "famille", "categorie", "Br_E", "unité", "methode", "note"]


def _rows_organiques(df_org: pd.DataFrame) -> pd.DataFrame:
    out = df_org.copy()
    out["categorie"] = out["vegetal"]
    out["methode"]   = out["modele"]
    out["note"]      = out["warnings"].apply(lambda w: "; ".join(w) if w else "")
    return out[_UNIFIED_COLS]


def _rows_metaux(df_met: pd.DataFrame) -> pd.DataFrame:
    out = df_met.copy()
    out["categorie"] = out["Categorie_INERIS"].map(_MET_CAT_MAP)
    out["famille"]   = "Métal"
    out["polluant"]  = out["ETM"]
    out["methode"]   = out["modele"] + " (" + out["Br_E_source"] + ")"

    def _note(r):
        n_txt = f"n={r['n_total']:.0f}" if pd.notna(r["n_total"]) else "n=?"
        r2_txt = f", r²={r['r2_simple']:.2f}" if pd.notna(r["r2_simple"]) else ""
        return f"{n_txt}, mode={r['mode_filtrage']}{r2_txt}"

    out["note"] = out.apply(_note, axis=1)
    return out[_UNIFIED_COLS]


def _pick_pcb_value(row, min_col, max_col, point_col):
    """Valeur ponctuelle si publiée, sinon milieu de l'intervalle, sinon la seule borne connue."""
    if pd.notna(row[point_col]):
        return row[point_col]
    mn, mx = row[min_col], row[max_col]
    if pd.notna(mn) and pd.notna(mx):
        return (mn + mx) / 2
    return mx if pd.notna(mx) else (mn if pd.notna(mn) else None)


def _rows_pcb(df_pcb: pd.DataFrame) -> pd.DataFrame:
    out = df_pcb.copy()
    out["categorie"] = out["categorie"].map(_PCB_CAT_MAP)
    out["polluant"]  = out["sigle"]
    out["unité"]     = "mg/kg_vegsec / (mg/kg_sol)"
    out["Br_E"] = out.apply(
        lambda r: _pick_pcb_value(r, "Br_min", "Br_max", "Br_ponctuel"), axis=1
    )
    out = out[out["Br_E"].notna()].copy()

    def _methode(r):
        if pd.notna(r["Br_ponctuel"]):
            return "INERIS DRC-16-159776 (valeur ponctuelle)"
        if pd.notna(r["Br_min"]) and pd.notna(r["Br_max"]):
            return "INERIS DRC-16-159776 (milieu d'intervalle)"
        return "INERIS DRC-16-159776 (borne unique)"

    out["methode"] = out.apply(_methode, axis=1)

    def _note(r):
        parts = []
        if pd.notna(r["Br_min"]) and pd.notna(r["Br_max"]):
            parts.append(f"intervalle Br [{r['Br_min']:.3g};{r['Br_max']:.3g}]")
        bf = _pick_pcb_value(r, "Bf_min", "Bf_max", "Bf_ponctuel")
        if bf is not None:
            parts.append(f"Bf air-plante≈{bf:.3g} m3/kg frais")
        return "; ".join(parts)

    out["note"] = out.apply(_note, axis=1)
    return out[_UNIFIED_COLS]


def build_sheets_par_vegetal(df_org: pd.DataFrame,
                             df_met: pd.DataFrame = None,
                             df_pcb: pd.DataFrame = None) -> dict:
    """
    Fusionne les 3 pipelines (organiques/métaux/PCB) en un seul jeu de feuilles,
    une par catégorie végétale, chacune listant tous les polluants applicables
    avec un schéma de colonnes commun (polluant, famille, Br_E, unité, methode, note).
    """
    frames = [_rows_organiques(df_org)]
    if df_met is not None:
        frames.append(_rows_metaux(df_met))
    if df_pcb is not None:
        frames.append(_rows_pcb(df_pcb))
    combined = pd.concat(frames, ignore_index=True)

    sheets = {}
    for cat in CATEGORIE_ORDER:
        sub = combined[combined["categorie"] == cat].sort_values(["famille", "polluant"])
        if len(sub):
            sheets[cat] = sub.reset_index(drop=True)
    return sheets


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Calcul Br_E pour MODUL'ERS")
    parser.add_argument(
        "--site", type=str, default="default",
        help="Nom du site à charger (ex: site_A charge data/sites/site_A.json)",
    )
    parser.add_argument("--no-metaux", action="store_true",
                        help="Ignorer le calcul BCF métaux (BAPPET)")
    parser.add_argument("--no-pcb",   action="store_true",
                        help="Ignorer le calcul BCF PCB (BAPPOP)")
    args = parser.parse_args()

    # ── Chargement sol ────────────────────────────────────────────────────────
    print(f"----------Chargement paramètres sol : site_{args.site}.json")
    sol = load_sol(args.site)

    # ── Calcul organiques ─────────────────────────────────────────────────────
    print("\n----------Calcul BCF polluants organiques...")
    results_org = []
    for polluant_nom in POLLUANTS:
        for vegetal_nom in VEGETAUX:
            results_org.append(
                compute_bre(polluant_nom, vegetal_nom, POLLUANTS, VEGETAUX, sol)
            )
    df_org = pd.DataFrame(results_org)

    # ── Calcul métaux ─────────────────────────────────────────────────────────
    df_metaux = None
    if not args.no_metaux:
        print("\n----------Calcul BCF métaux (BAPPET)...")
        df_metaux = compute_bcf_metaux(sol=sol)
        cols = [c for c in _COLS_METAUX if c in df_metaux.columns]
        df_metaux = df_metaux[cols]

    # ── Calcul PCB ────────────────────────────────────────────────────────────
    df_pcb = None
    if not args.no_pcb:
        print("\n----------Calcul BCF PCB/PCDD-F (table officielle INERIS)...")
        df_pcb = compute_bcf_pcb()
        cols = [c for c in _COLS_PCB if c in df_pcb.columns]
        df_pcb = df_pcb[cols]

    # ── Export Excel — une feuille par catégorie végétale ───────────────────────
    output_file = f"Br_E_{args.site}.xlsx"
    sheets_par_veg = build_sheets_par_vegetal(df_org, df_metaux, df_pcb)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for cat, df_cat in sheets_par_veg.items():
            df_cat.to_excel(writer, sheet_name=cat[:31], index=False)

    print(f"\n----------Export : {output_file}  ({len(sheets_par_veg)} onglet(s))")
    for cat, df_cat in sheets_par_veg.items():
        print(f"  {cat} ({len(df_cat)} lignes)")


if __name__ == "__main__":
    main()
