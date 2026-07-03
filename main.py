import argparse
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

# Colonnes à conserver dans l'onglet PCB
_COLS_PCB = [
    "congener", "congenere_key", "categorie",
    "n", "n_outliers",
    "Br", "Br_retenu", "r2", "p_val",
    "BCF_min", "BCF_max", "BCF_median", "BCF_mean",
    "intercept_air_contrib",
    "Bf", "Bf_note",
]

# Ordre d'affichage des feuilles par catégorie végétale
CATEGORIE_ORDER = [
    "légumes_feuilles", "légumes_fruits", "légumes_racines",
    "tubercules", "fourrage",
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
    out["note"] = (
        "n=" + out["n_total"].astype(str)
        + ", mode=" + out["mode_filtrage"]
        + out["r2_simple"].apply(lambda r: f", r²={r:.2f}" if pd.notna(r) else "")
    )
    return out[_UNIFIED_COLS]


def _rows_pcb(df_pcb: pd.DataFrame) -> pd.DataFrame:
    out = df_pcb.copy()
    out["categorie"] = out["categorie"].map(_PCB_CAT_MAP)
    out["famille"]   = "PCB"
    out["polluant"]  = out["congener"]
    out["unité"]     = "mg/kg_vegsec / (mg/kg_sol)"
    out["Br_E"]      = out.apply(
        lambda r: r["Br"] if r["Br_retenu"] else r["BCF_median"], axis=1
    )
    out["methode"] = out["Br_retenu"].apply(
        lambda ok: "BAPPOP_OLS (régression)" if ok else "BAPPOP (médiane, r²≤0.5)"
    )
    out["note"] = out.apply(
        lambda r: f"n={r['n']}, r²={r['r2']:.2f}" if pd.notna(r["r2"])
        else f"n={r['n']}, intervalle [{r['BCF_min']:.3g};{r['BCF_max']:.3g}]",
        axis=1,
    )
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
        print("\n----------Calcul BCF PCB (BAPPOP)...")
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
