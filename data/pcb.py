# -*- coding: utf-8 -*-
"""
Calcul des Br (BCF sol->plante) pour les PCB par régression linéaire OLS.
Source : data/bappop/bappop.csv (projet TROPHé INERIS/ADEME)
Méthode : rapport INERIS-DRC-16-159776-09593A

Br = pente de la régression Cp_MS = f(Cs_MS) par congénère × catégorie végétale.
Valeur retenue si r² > 0.5, sinon utiliser l'intervalle [BCF_min, BCF_max].

Bf (BCF air_gazeux->plante) non calculable depuis BAPPOP (données terrain/enceinte
sans C_air_gaz mesurée) -> None, à compléter depuis les Tableaux 1-9 du rapport INERIS.

Usage module :
    from data.pcb import compute_bcf_pcb
    df = compute_bcf_pcb()

Usage standalone :
    python data/pcb.py   -> data/bcf_pcb_results.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_DATA_DIR = Path(__file__).parent

# Congénères présents dans BAPPOP
CONGENERES_BAPPOP = {"PCB28", "PCB52", "PCB101", "PCB118", "PCB138", "PCB153", "PCB180"}

# Normalisation vers les clés du dictionnaire POLLUANTS_PCB
CONGENERE_TO_KEY = {
    "PCB28":  "PCB_28",
    "PCB52":  "PCB_52",
    "PCB101": "PCB_101",
    "PCB118": "PCB_118",
    "PCB138": "PCB_138",
    "PCB153": "PCB_153",
    "PCB180": "PCB_180",
}

# Mapping Type plante -> catégorie INERIS (snake_case sans accents)
CATEGORIE_INERIS = {
    "légume-feuille":    "legumes_feuilles",
    "légume-fleur":      "legumes_feuilles",
    "légume-tige":       "legumes_feuilles",
    "plante aromatique": "legumes_feuilles",
    "légume-fruit":      "legumes_fruits",
    "légume-graine":     "legumes_fruits",
    "légume-racine":     "legumes_racines",
    "légume-tubercule":  "tubercules",
    "céréale":           "cereales",
    "gazon":             "fourrage",
    "prairie":           "fourrage",
    "herbe":             "fourrage",
    "fourrage":          "fourrage",
}

# % MS par défaut par type_plante (conversion MF -> MS)
_PCT_MS_DEFAULT = {
    "légume-feuille":   10.0,
    "légume-racine":    12.0,
    "légume-fruit":      6.0,
    "légume-tubercule": 20.0,
    "légume-graine":    85.0,
    "céréale":          85.0,
}
_PCT_MS_FALLBACK = 10.0

MIN_N = 4        # minimum de points pour la régression (rapport INERIS : ≥ 4 échantillons > LOQ)
R2_SEUIL = 0.5   # seuil r² pour retenir la valeur ponctuelle Br
GRUBBS_ALPHA = 0.05

_LOQ_MARKERS = {
    "< ld", "<ld", "< lq", "<lq", "< loq", "<loq",
    "non détectable", "non détecté", "nd", "nr",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_float(val) -> float:
    if val is None:
        return np.nan
    s = str(val).strip().lower()
    if not s or s in {"nan", "non précisé", "non renseigné"}:
        return np.nan
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return np.nan


def _grubbs_mask(values: np.ndarray) -> np.ndarray:
    """
    Retrait itératif d'outliers (Grubbs α=5%) sur un vecteur 1D.
    Retourne un masque booléen de même longueur que values (True = conserver).
    """
    keep = np.ones(len(values), dtype=bool)
    while keep.sum() >= 3:
        v = values[keep]
        n = len(v)
        mean, std = v.mean(), v.std(ddof=1)
        if std == 0:
            break
        g = np.abs(v - mean).max() / std
        t_c = stats.t.ppf(1 - GRUBBS_ALPHA / (2 * n), df=n - 2)
        g_c = ((n - 1) / np.sqrt(n)) * np.sqrt(t_c**2 / (n - 2 + t_c**2))
        if g > g_c:
            orig_idx = np.where(keep)[0]
            keep[orig_idx[np.argmax(np.abs(v - mean))]] = False
        else:
            break
    return keep


# ── Pipeline ───────────────────────────────────────────────────────────────────

def compute_bcf_pcb(data_path: Path = None,
                    aprifel_path: Path = None) -> pd.DataFrame:
    """
    Calcule les Br (pentes OLS Cp_MS = f(Cs)) par congénère × catégorie végétale
    à partir de BAPPOP.csv (données TROPHé).

    Retourne un DataFrame avec colonnes :
      congener, congenere_key, categorie, n, n_outliers,
      Br, intercept, r2, p_val, Br_retenu,
      BCF_min, BCF_max, BCF_median, BCF_mean
    """
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if data_path is None:
        data_path = _DATA_DIR / "bappop" / "bappop.csv"

    # 1. Chargement
    df_raw = pd.read_csv(
        data_path, sep=",", encoding="utf-8-sig",
        dtype=str, on_bad_lines="skip",
    )
    print(f"Chargé : {df_raw.shape[0]} lignes, {df_raw.shape[1]} colonnes")

    # 2. Filtre PCB + Sol (mg/kg)
    mask_pcb = df_raw["Polluant organique (fr)"].isin(CONGENERES_BAPPOP)
    mask_sol = df_raw["Milieu"].str.strip() == "Sol (mg/kg)"
    df = df_raw[mask_pcb & mask_sol].copy()
    print(f"Après filtre PCB + Sol (mg/kg) : {len(df)} lignes")

    # 3. Filtre LOQ : exclure valeurs < LQ dans Cp et Cs
    cp_str = df["Moyenne plante"].str.strip().str.lower().fillna("")
    cs_str = df["Moyenne milieu"].str.strip().str.lower().fillna("")
    mask_loq = cp_str.isin(_LOQ_MARKERS) | cs_str.isin(_LOQ_MARKERS)
    df = df[~mask_loq].copy()
    print(f"Après filtre LOQ               : {len(df)} lignes")

    # 4. Conversion numérique Cp et Cs
    df["Cp_raw"] = df["Moyenne plante"].apply(_to_float)
    df["Cs"]     = df["Moyenne milieu"].apply(_to_float)

    # Conversion MF -> MS pour Cp
    def _pct_ms(type_plante: str) -> float:
        return _PCT_MS_DEFAULT.get(str(type_plante).strip().lower(), _PCT_MS_FALLBACK)

    df["pct_ms"] = df["Type plante"].apply(_pct_ms)

    def _cp_to_ms(row) -> float:
        statut = str(row["MS/MF"]).strip().upper()
        cp = row["Cp_raw"]
        if np.isnan(cp):
            return np.nan
        if statut == "MF":
            pct = row["pct_ms"]
            return cp / (pct / 100.0) if pct > 0 else np.nan
        return cp  # MS ou Non précisé -> garder tel quel

    df["Cp_MS"] = df.apply(_cp_to_ms, axis=1)

    # Conserver uniquement les lignes calculables (Cp > 0 ET Cs > 0)
    df = df[
        df["Cp_MS"].notna() & (df["Cp_MS"] >= 0) &
        df["Cs"].notna()    & (df["Cs"] > 0)
    ].copy()
    df["BCF_calc"] = df["Cp_MS"] / df["Cs"]
    df = df[df["BCF_calc"] >= 0].copy()
    print(f"Après conversion numérique     : {len(df)} lignes calculables")

    # 5. Catégorie INERIS
    df["categorie"] = (
        df["Type plante"].str.strip().str.lower()
        .map(CATEGORIE_INERIS)
        .fillna("autre")
    )
    n_autre = (df["categorie"] == "autre").sum()
    if n_autre:
        print(f"  {n_autre} lignes non mappées -> 'autre'")

    # 6. Régressions OLS par groupe (congénère × catégorie)
    print(f"\n-- Régressions OLS (seuil r² > {R2_SEUIL}) --")
    results = []

    for (congenere, cat), grp in df.groupby(
        ["Polluant organique (fr)", "categorie"]
    ):
        if cat == "autre":
            continue

        xs_all  = grp["Cs"].values
        ys_all  = grp["Cp_MS"].values
        n_total = len(grp)

        # ── Grubbs sur résidus de la régression (méthode INERIS) ─────────────
        # Passe 1 : OLS préliminaire pour calculer les résidus
        # Passe 2 : OLS final sur les données nettoyées
        if n_total >= MIN_N and xs_all.std() > 0:
            s0, i0, _, _, _ = stats.linregress(xs_all, ys_all)
            residuals        = ys_all - (i0 + s0 * xs_all)
            keep             = _grubbs_mask(residuals)
            n_outliers       = int((~keep).sum())
            xs = xs_all[keep]
            ys = ys_all[keep]
        else:
            keep       = np.ones(n_total, dtype=bool)
            n_outliers = 0
            xs, ys     = xs_all, ys_all

        bcf = ys / xs   # BCF_calc sur données nettoyées
        n   = int(keep.sum())

        rec = {
            "congener":      congenere,
            "congenere_key": CONGENERE_TO_KEY.get(congenere, congenere),
            "categorie":     cat,
            "n":             n,
            "n_outliers":    n_outliers,
            "BCF_min":       float(bcf.min())    if n > 0 else np.nan,
            "BCF_max":       float(bcf.max())    if n > 0 else np.nan,
            "BCF_median":    float(np.median(bcf)) if n > 0 else np.nan,
            "BCF_mean":      float(bcf.mean())   if n > 0 else np.nan,
        }

        # ── Passe 2 : OLS final ───────────────────────────────────────────────
        if n >= MIN_N and xs.std() > 0:
            slope, intercept, r_val, p_val, _ = stats.linregress(xs, ys)
            r2 = r_val ** 2
            rec.update({
                "Br":                       float(slope),
                "intercept_air_contrib":    float(intercept),  # base pour Bf = intercept / C_air_gaz_enceinte
                "r2":                       float(r2),
                "p_val":                    float(p_val),
                "Br_retenu":                bool(r2 > R2_SEUIL),
            })
        else:
            rec.update({
                "Br": np.nan, "intercept_air_contrib": np.nan,
                "r2": np.nan, "p_val": np.nan,
                "Br_retenu": False,
            })

        # Bf non calculable depuis BAPPOP (C_air_gaz_enceinte non disponible)
        rec["Bf"]      = None
        rec["Bf_note"] = "incalculable BAPPOP — Bf = intercept / C_air_gaz_enceinte (TROPHé)"

        results.append(rec)

    res_df = pd.DataFrame(results)
    return res_df


# ── Standalone ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    res = compute_bcf_pcb()

    out_path = _DATA_DIR / "bcf_pcb_results.csv"
    res.to_csv(out_path, index=False, encoding="utf-8-sig", float_format="%.6f")
    print(f"\nFichier sauvegardé : {out_path}")

    pd.options.display.float_format = "{:.4f}".format
    pd.options.display.width = 200
    cols = ["congener", "categorie", "n", "BCF_min", "BCF_max",
            "BCF_mean", "Br", "r2", "Br_retenu"]
    print("\n-- Résultats (Br OLS par congénère × catégorie) --")
    print(res[cols].sort_values(["congener", "categorie"]).to_string(index=False))
