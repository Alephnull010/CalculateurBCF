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

    # ── Export Excel ──────────────────────────────────────────────────────────
    output_file = f"Br_E_{args.site}.xlsx"
    sheets = []
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_org.to_excel(writer, sheet_name="Organiques", index=False)
        sheets.append(f"Organiques ({len(df_org)} lignes)")
        if df_metaux is not None:
            df_metaux.to_excel(writer, sheet_name="Métaux", index=False)
            sheets.append(f"Métaux ({len(df_metaux)} lignes)")
        if df_pcb is not None:
            df_pcb.to_excel(writer, sheet_name="PCB", index=False)
            sheets.append(f"PCB ({len(df_pcb)} lignes)")

    print(f"\n----------Export : {output_file}  ({len(sheets)} onglet(s))")
    for s in sheets:
        print(f"  {s}")


if __name__ == "__main__":
    main()
