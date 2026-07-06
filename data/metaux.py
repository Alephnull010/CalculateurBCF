# -*- coding: utf-8 -*-
"""
Calcul des BCF par régression logarithmique — méthode INERIS (alignement strict)
Source    : data/bappet/bappet.csv  (ETM – métaux en éléments traces)

Filtres INERIS de qualité des données appliqués avant régression :
  F1  Mode de culture       – pleine terre uniquement (exclusion pot / intérieur / container)
  F2  Contexte              – exclure urbain + industriel          [relâché si n ≤ 10]
  F3  Origine pollution     – exclure artificielle + urbaine       [relâché si n ≤ 10]
  F4  Extraction sol        – totale / pseudo-totale uniquement
                              (exception : As -> extraction partielle conservée)
  F5  Organe analysé        – partie consommée du végétal uniquement
  F6  LOQ                   – exclure valeurs < LQ / < LD dans sol et plante
  F7  Préparation végétaux  – lavage requis ; « non précisé » exclu en mode strict
                                                                   [relâché si n ≤ 10]
  F8  Appariement sol-plante – Cp ET Cs numériques obligatoires (implicite via BCF calculable)
  F9  Bruit de fond RECORD94 – exclusion si Cs < 5×BDF ET BCF > 10×BCF_médian_groupe
  F10 Grubbs α = 5 %        – retrait outliers résiduels sur ln(BCF)

Assouplissement (n ≤ 10 par groupe ETM × catégorie INERIS) :
  Si le nombre de données valides après filtres stricts est ≤ 10,
  les critères F2 (contexte), F3 (origine) et F7 (lavage) sont relâchés.

Régression :
  · OLS simple  (scipy.stats.linregress)
  · OLS multiple avec présélection Pearson α = 10 % (XLSTAT-like, INERIS)
  · Distribution ajustée par Anderson-Darling

Pour 8 des 15 ETM (As, Cd, Cr, Hg, Ni, Pb, Se, V), INERIS a directement publié
les coefficients de transfert (régression et/ou distribution) dans le rapport
INERIS-DRC-17-163615-01452A - voir `data/metaux_ineris_lookup.py`. Ces 8 ETM
utilisent cette table officielle plutôt que la régression BAPPET ci-dessus,
qui reste utilisée pour les 7 ETM non couverts (Co, Cu, Mn, Mo, Sb, Tl, Zn).

Usage module :
  from data.metaux import compute_bcf_metaux
  df = compute_bcf_metaux()          # chemins par défaut (data/bappet/, data/aprifel/)
  df = compute_bcf_metaux(data_path=Path("..."), aprifel_path=Path("..."))

Usage standalone :
  python data/metaux.py              # produit data/bcf_metaux_results.csv
"""

import re
import sys
import unicodedata
from difflib import get_close_matches
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats

from data.metaux_ineris_lookup import BR_PAR_ETM, ETM_COUVERTS, resolve_categorie

# -- Config ---------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent

MIN_N_SIMPLE          = 3
MIN_N_MULTIPLE        = 9
GRUBBS_ALPHA          = 0.05
PEARSON_ALPHA         = 0.10
SEUIL_ASSOUPLISSEMENT = 10   # n ≤ 10 -> relâcher F2, F3, F7

# -- Mapping Type Plante -> 6 catégories MODUL'ERS / INERIS ---------------------
CATEGORIE_INERIS = {
    "légume-feuille":    "légumes-feuilles",
    "légume-fleur":      "légumes-feuilles",
    "légume-bulbe":      "légumes-feuilles",
    "légume-tige":       "légumes-feuilles",
    "plante aromatique": "légumes-feuilles",
    "plante entière":    "légumes-feuilles",
    "légume-fruit":      "légumes-fruits",
    "fruit":             "légumes-fruits",
    "légume-graine":     "légumes-fruits",   # rapport INERIS : pas de diff. significative avec légumes-fruits
    "légume-sec":        "légumes-fruits",   # idem
    "légume-racine":     "légumes-racines",
    "légume-tubercule":  "tubercules",
    "céréale":           "céréales",
    "gazon":             "fourrage",
    "prairie":           "fourrage",
    "herbe":             "fourrage",
    "fourrage":          "fourrage",
}

PCT_MS_PAR_TYPE = {
    "légume-feuille":    10.0,
    "légume-racine":     12.0,
    "légume-fruit":       6.0,
    "légume-graine":     85.0,
    "légume-tubercule":  20.0,
    "légume-fleur":      12.0,
    "légume-bulbe":      12.0,
    "légume-tige":       10.0,
    "légume-sec":        85.0,
    "plante aromatique": 10.0,
    "plante entière":    10.0,
    "céréale":           85.0,
    "fruit":              8.0,
    "gazon":             25.0,
}
PCT_MS_FALLBACK = 10.0

_NAN_STRINGS = {
    "non précisé", "non applicable", "non détectable",
    ">ld", "nan", "",
    "donnée non mise à jour",
    "paramètre non renseigné lors de la création de bappop",
    "paramètre non renseingné à la création de bappop",
    "non renseigné",
}

# -- Bruit de fond RECORD 1994 (mg/kg MS) --------------------------------------
# Valeurs médianes du fond géochimique français — à vérifier contre le document original
BRUIT_DE_FOND_RECORD94 = {
    "As":  11.0,
    "Cd":   0.26,
    "Co":  10.0,
    "Cr":  54.0,
    "Cu":  14.0,
    "Hg":   0.09,
    "Mn": 500.0,
    "Mo":   1.0,
    "Ni":  23.0,
    "Pb":  29.0,
    "Sb":   1.0,
    "Se":   0.4,
    "Tl":   0.5,
    "V":   50.0,
    "Zn":  60.0,
}
FACTEUR_BDF = 5.0   # seuil = 5 × BDF (RECORD 1994)

# -- Constantes de filtrage INERIS ----------------------------------------------

# F1 : pleine terre uniquement — mots-clés identifiant une culture en pot/indoor
_F1_EXCL_KEYWORDS = ("intérieur", "container", "bacs", "couvert", "sous abris")

# F4 : extraction totale / pseudo-totale
_F4_EXTRACTION_OK        = {"totale", "pseudo-totale", "totale ou pseudo-totale"}
_F4_ETM_EXCEPTION        = {"As"}   # pour As, extraction partielle conservée

# F5 : parties végétales consommées
_F5_ORGANE_OK = {
    "partie consommable", "feuille", "fruit", "tubercule",
    "graine", "bulbe", "fleur", "feuille (pétiole)", "feuille (limbe)",
}

# F6 : marqueurs de valeur censurée (< LOQ / < LD) dans BAPPET
_F6_LOQ_MARKERS = {
    "< lq", "<lq", "< ld", "<ld", "< loq", "<loq",
    "non détectable", "non détecté", "non détecté ",
}

# F7 : lavage — exclusions selon le mode (strict vs relâché)
_F7_EXCL_STRICT = {"non lavé", "non lavé, non pelé"}
_F7_EXCL_RELAX  = {"non lavé", "non lavé, non pelé"}

# -- Distributions candidates Anderson-Darling ----------------------------------
_DISTRIB_CANDIDATS = {
    "lognormale": stats.lognorm,
    "normale":    stats.norm,
    "Pearson_V":  stats.invgamma,
    "gamma":      stats.gamma,
    "uniforme":   stats.uniform,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers génériques
# ═══════════════════════════════════════════════════════════════════════════════

def to_float(val: object) -> float:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    s = str(val).strip().lower()
    if s in _NAN_STRINGS:
        return np.nan
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return np.nan


def normalise_etm(val: str) -> str:
    s = str(val).strip()
    return s[0].upper() + s[1:].lower() if s else s


def convertir_cp(row) -> float:
    statut = str(row["MS ou MF"]).strip().upper()
    cp_raw = row["Moyenne Plante (mg/kg)_num"]
    if statut == "MF":
        pct = row["pct_ms"]
        return cp_raw / (pct / 100.0) if pct and pct > 0 else np.nan
    elif statut == "MS":
        return cp_raw
    else:
        return np.nan


def _norm_str(series: pd.Series) -> pd.Series:
    """Lowercase + strip pour comparaison robuste de chaînes."""
    return series.fillna("non précisé").astype(str).str.strip().str.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers APRIFEL
# ═══════════════════════════════════════════════════════════════════════════════

def _norm_espece(name: str) -> str:
    s = unicodedata.normalize("NFD", str(name))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s*\([^)]*\)", "", s)
    return s.lower().strip()


def build_aprifel_lookup(aprifel_df: pd.DataFrame):
    by_norm: dict = {}
    for _, row in aprifel_df.iterrows():
        norm = _norm_espece(row["espece"])
        is_raw = any(kw in row["espece"].lower() for kw in ("cru", "crue"))
        pct = float(row["pct_MS"])
        if norm not in by_norm:
            by_norm[norm] = {"raw": [], "other": []}
        (by_norm[norm]["raw"] if is_raw else by_norm[norm]["other"]).append(pct)
    lookup = {
        norm: float(np.mean(v["raw"] if v["raw"] else v["other"]))
        for norm, v in by_norm.items()
    }
    fw_index: dict = {}
    for norm, pct in lookup.items():
        w = norm.split()[0] if norm.split() else ""
        if w:
            fw_index.setdefault(w, []).append(pct)
    first_word_lookup = {w: float(np.mean(p)) for w, p in fw_index.items()}
    return lookup, list(lookup.keys()), first_word_lookup


def get_pct_ms(espece: str, type_plante: str,
               aprifel_lookup: dict, aprifel_norms: list,
               first_word_lookup: dict) -> tuple:
    norm = _norm_espece(espece)
    if norm in aprifel_lookup:
        return aprifel_lookup[norm], "aprifel_exact"
    matches = get_close_matches(norm, aprifel_norms, n=1, cutoff=0.75)
    if matches:
        return aprifel_lookup[matches[0]], "aprifel_approche"
    fw = norm.split()[0] if norm.split() else ""
    if fw and fw in first_word_lookup:
        return first_word_lookup[fw], "aprifel_premier_mot"
    pct = PCT_MS_PAR_TYPE.get(str(type_plante).strip().lower(), PCT_MS_FALLBACK)
    return pct, "fallback_type"


# ═══════════════════════════════════════════════════════════════════════════════
# Grubbs
# ═══════════════════════════════════════════════════════════════════════════════

def grubbs_filter(series: pd.Series, alpha: float = GRUBBS_ALPHA) -> pd.Series:
    v = series.dropna().copy()
    while len(v) >= 3:
        n = len(v); mean, std = v.mean(), v.std(ddof=1)
        if std == 0:
            break
        g = (v - mean).abs().max() / std
        t_c = stats.t.ppf(1 - alpha / (2 * n), df=n - 2)
        g_c = ((n - 1) / np.sqrt(n)) * np.sqrt(t_c**2 / (n - 2 + t_c**2))
        if g > g_c:
            v = v.drop((v - mean).abs().idxmax())
        else:
            break
    return v


# ═══════════════════════════════════════════════════════════════════════════════
# Régressions OLS
# ═══════════════════════════════════════════════════════════════════════════════

def ols_simple(x: np.ndarray, y: np.ndarray):
    slope, intercept, r_val, p_val, _ = stats.linregress(x, y)
    return float(intercept), float(slope), float(r_val**2), float(p_val)


def ols_multiple(X: np.ndarray, y: np.ndarray, k: int):
    coefs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ coefs
    ss_res = ((y - y_pred)**2).sum()
    ss_tot = ((y - y.mean())**2).sum()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    n = len(y); df_model = k; df_resid = n - k - 1
    if np.isfinite(r2) and df_resid > 0 and r2 < 1.0:
        f = (r2 / df_model) / ((1.0 - r2) / df_resid)
        p = 1.0 - stats.f.cdf(f, df_model, df_resid)
    else:
        f, p = np.nan, np.nan
    return coefs, r2, f, p


def r2_ajuste(r2: float, n: int, k: int) -> float:
    if n <= k + 1:
        return np.nan
    return 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Anderson-Darling
# ═══════════════════════════════════════════════════════════════════════════════

def ad_statistic(data: np.ndarray, dist, params: tuple) -> float:
    n = len(data)
    if n < 3:
        return np.inf
    x = np.sort(data)
    cdf = np.clip(dist.cdf(x, *params), 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    return float(-n - (1.0 / n) * np.sum((2 * i - 1) * (np.log(cdf) + np.log(1 - cdf[::-1]))))


def fit_best_distribution(bcf_values: np.ndarray) -> tuple:
    data = bcf_values[np.isfinite(bcf_values) & (bcf_values > 0)]
    if len(data) < 3:
        return "non_ajustée", np.nan
    best_name, best_ad = "non_ajustée", np.inf
    for name, dist in _DISTRIB_CANDIDATS.items():
        try:
            params = dist.fit(data)
            ad = ad_statistic(data, dist, params)
            if np.isfinite(ad) and ad < best_ad:
                best_ad, best_name = ad, name
        except Exception:
            continue
    return best_name, (best_ad if best_ad < np.inf else np.nan)


def ad_lognorm_test(values: np.ndarray) -> tuple[float, float]:
    """
    Anderson-Darling test for lognormality (normality of log-transformed values).
    Uses scipy.stats.anderson which provides critical values at [15,10,5,2.5,1]%.
    Returns (AD_statistic, p_value) where p_value is linearly interpolated
    between the tabulated critical values (clamped at [0.01, 0.15]).
    Returns (inf, 0.0) if n < 9.
    """
    data = np.log(values[values > 0])
    if len(data) < 9:
        return np.inf, 0.0
    result = stats.anderson(data, dist="norm")
    ad_stat = float(result.statistic)
    # critical_values is increasing; significance_level is [15,10,5,2.5,1] (percents)
    p_val = float(np.interp(ad_stat,
                             result.critical_values,
                             result.significance_level / 100))
    return ad_stat, p_val


def fit_best_distribution_ineris(bcf_values: np.ndarray) -> tuple[str, float, float]:
    """
    Returns (distribution_name, AD_statistic, p_lognorm).
    INERIS rule: retain lognormal if the AD test p-value >= 5%.
    If lognormal is rejected (p < 5%), return the alternative with the smallest AD.
    """
    data = bcf_values[np.isfinite(bcf_values) & (bcf_values > 0)]
    if len(data) < 9:
        return "intervalle_min_max", np.nan, np.nan
    ad_ln, p_ln = ad_lognorm_test(data)
    if p_ln >= 0.05:
        return "lognormale", ad_ln, p_ln
    best_name, best_ad = fit_best_distribution(data)
    return best_name, best_ad, p_ln


def regression_ineris_retenue(rec: dict, bcf_values: np.ndarray) -> bool:
    """Retourne True si la régression est plus informative que la distribution."""
    op_ratio = rec.get("OP_max", np.nan) / rec.get("OP_min", np.nan)
    if np.isnan(op_ratio):
        return False

    data = bcf_values[np.isfinite(bcf_values) & (bcf_values > 0)]
    p25, p975 = np.percentile(data, [2.5, 97.5])
    distrib_ratio = p975 / p25 if p25 > 0 else np.inf

    bcf_ratio = rec.get("BCF_max", np.nan) / rec.get("BCF_min", np.nan)
    seuil = min(distrib_ratio, bcf_ratio)

    return bool(op_ratio < seuil)


# ═══════════════════════════════════════════════════════════════════════════════
# Filtres INERIS
# ═══════════════════════════════════════════════════════════════════════════════

def filtrer_ineris(df: pd.DataFrame, strict: bool = True) -> tuple[pd.DataFrame, dict]:
    """
    Applique les filtres INERIS F1-F7 sur df.

    strict=True  : mode complet (F1+F2+F3+F4+F5+F6+F7 complet)
    strict=False : relâche F2 (contexte), F3 (origine), F7 (lavage non précisé accepté)
    Retourne (df_filtré, dict des comptages retirés par filtre).
    """
    removed = {}

    # -- F1 : mode de culture — pleine terre uniquement -------------------------
    typ = _norm_str(df["Type expérimental"])
    excl_f1 = typ.apply(
        lambda v: v == "non précisé"
        or any(kw in v for kw in _F1_EXCL_KEYWORDS)
    )
    removed["F1_culture_pot"] = int(excl_f1.sum())
    df = df[~excl_f1].copy()

    # -- F2 : contexte — exclure urbain + industriel (strict uniquement) ---------
    if strict:
        ctx = _norm_str(df["Contexte de l'expérimentation"])
        excl_f2 = ctx.apply(lambda v: "urbain" in v or "industriel" in v)
        removed["F2_contexte_exclu"] = int(excl_f2.sum())
        df = df[~excl_f2].copy()
    else:
        removed["F2_contexte_exclu"] = 0

    # -- F3 : origine — exclure artificielle + urbaine (strict uniquement) -------
    if strict:
        ori = _norm_str(df["Origine de la pollution"])
        excl_f3 = ori.apply(lambda v: "artificielle" in v or "urbaine" in v)
        removed["F3_origine_exclue"] = int(excl_f3.sum())
        df = df[~excl_f3].copy()
    else:
        removed["F3_origine_exclue"] = 0

    # -- F4 : extraction sol — totale / pseudo-totale (exception As) -------------
    ext = _norm_str(df["Extraction"])
    etm = df["ETM"].str.strip()
    mask_f4 = ext.isin(_F4_EXTRACTION_OK) | (
        etm.isin(_F4_ETM_EXCEPTION) & (ext == "partielle")
    )
    removed["F4_extraction_partielle"] = int((~mask_f4).sum())
    df = df[mask_f4].copy()

    # -- F5 : organe — partie consommée uniquement --------------------------------
    org = _norm_str(df["Organe analysé"])
    mask_f5 = org.isin(_F5_ORGANE_OK)
    removed["F5_organe_exclu"] = int((~mask_f5).sum())
    df = df[mask_f5].copy()

    # -- F6 : LOQ — exclure valeurs < LQ / < LD dans Cp et Cs -------------------
    cp_s = _norm_str(df["Moyenne Plante (mg/kg)"])
    cs_s = _norm_str(df["Moyenne Milieu"])
    excl_f6 = cp_s.isin(_F6_LOQ_MARKERS) | cs_s.isin(_F6_LOQ_MARKERS)
    removed["F6_loq_exclu"] = int(excl_f6.sum())
    df = df[~excl_f6].copy()

    # -- F7 : lavage — non lavé toujours exclus ; non précisé exclus en strict ---
    lav = _norm_str(df["Lavage/Pelage"])
    excl_lav = _F7_EXCL_STRICT if strict else _F7_EXCL_RELAX
    excl_f7 = lav.isin(excl_lav)
    removed["F7_lavage_exclu"] = int(excl_f7.sum())
    df = df[~excl_f7].copy()

    # -- F8 : appariement sol-plante — exclure min/max isolés si colonne présente -
    if "type_valeur" in df.columns:
        tv = _norm_str(df["type_valeur"])
        mask_f8 = tv.isin({"moyenne", "médiane"})
        removed["F8_appariement_exclu"] = int((~mask_f8).sum())
        df = df[mask_f8].copy()
    else:
        removed["F8_appariement_exclu"] = 0

    return df, removed


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline de calcul BCF + catégories (appliqué après filtrage)
# ═══════════════════════════════════════════════════════════════════════════════

COL_CP     = "Moyenne Plante (mg/kg)"
COL_CS     = "Moyenne Milieu"
COL_PH     = "pH"
COL_MO     = "Matière organique (%)"
COL_NB     = "Nb échantillons"
COL_MS_PCT = "MS (%)"


def calculer_bcf(df: pd.DataFrame,
                 aprifel_lookup: dict,
                 aprifel_norms: list,
                 first_word_lookup: dict) -> pd.DataFrame:
    """
    Effectue conversions numériques, calcul BCF, log-transformation et
    affectation des catégories INERIS. Retourne df avec uniquement les
    lignes à BCF > 0 calculable.
    """
    for col in [COL_CP, COL_CS, COL_PH, COL_MO]:
        df[col + "_num"] = df[col].apply(to_float)

    df["Nb_ech_num"] = df[COL_NB].apply(to_float).fillna(1.0).clip(lower=1.0)

    # % MS
    df["ms_pct_bappet"] = df[COL_MS_PCT].apply(to_float)
    aprifel_res = df.apply(
        lambda r: get_pct_ms(r["Espèce (fr)"], r["Type Plante"],
                             aprifel_lookup, aprifel_norms, first_word_lookup),
        axis=1,
    )
    df["pct_ms"] = df["ms_pct_bappet"].where(
        df["ms_pct_bappet"].notna(),
        aprifel_res.apply(lambda x: x[0]),
    )

    # Cp en matière sèche
    df["Cp_MS"] = df.apply(convertir_cp, axis=1)
    df["Cs"]    = df[COL_CS + "_num"]

    # BCF (F8 appariement implicite : BCF calculable ⟺ Cp ET Cs numériques)
    df["BCF_calc"] = df["Cp_MS"] / df["Cs"]
    df = df[
        df["BCF_calc"].notna() & (df["BCF_calc"] > 0) &
        df["Cs"].notna()        & (df["Cs"] > 0)
    ].copy()

    # Log-transformation
    df["ln_BCF"] = np.log(df["BCF_calc"])
    df["ln_Cs"]  = np.log(df["Cs"])
    df["pH_num"] = df[COL_PH + "_num"]
    df["MO_num"] = df[COL_MO + "_num"]

    # Catégorie INERIS
    df["categorie_ineris"] = (
        df["Type Plante"].str.strip().str.lower()
        .map(CATEGORIE_INERIS)
        .fillna("autre")
    )

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Fonction principale — pipeline complet
# ═══════════════════════════════════════════════════════════════════════════════

def _appliquer_cs_site(res_df: pd.DataFrame, conc_sol: dict) -> pd.DataFrame:
    """
    Calcule Br_E, Cs_site et Br_E_source pour chaque groupe ETM × catégorie.

    Priorité :
      1. regression_retenue=True ET Cs fourni ET dans [Cs_valid_min, Cs_valid_max]
         -> Br_E = exp(A_simple + B_simple * ln(Cs))   source = "regression"
      2. regression_retenue=True ET Cs fourni MAIS hors domaine
         -> Br_E = BCF_mean_geom_pond                  source = "moy_geom_hors_domaine"
      3. Cs absent du JSON site
         -> Br_E = BCF_mean_geom_pond                  source = "moy_geom_cs_absent"
      4. Pas de régression retenue (reg. non sign. ou n insuffisant)
         -> Br_E = BCF_mean_geom_pond                  source = "moy_geom_reg_non_retenue"
    """
    bre_list    = []
    cs_list     = []
    source_list = []

    for _, row in res_df.iterrows():
        etm = row["ETM"]
        cs  = conc_sol.get(etm)

        if cs is None:
            bre_list.append(row["BCF_mean_geom_pond"])
            cs_list.append(np.nan)
            source_list.append("moy_geom_cs_absent")
            continue

        if not row["regression_retenue"] or pd.isna(row["A_simple"]):
            bre_list.append(row["BCF_mean_geom_pond"])
            cs_list.append(cs)
            source_list.append("moy_geom_reg_non_retenue")
            continue

        cs_min = row["Cs_valid_min"]
        cs_max = row["Cs_valid_max"]
        if not (cs_min <= cs <= cs_max):
            print(
                f"  [warning] {etm} / {row['Categorie_INERIS']} : "
                f"Cs_site={cs:.3g} hors domaine [{cs_min:.3g} ; {cs_max:.3g}] "
                f"-> fallback moy_geom"
            )
            bre_list.append(row["BCF_mean_geom_pond"])
            cs_list.append(cs)
            source_list.append("moy_geom_hors_domaine")
            continue

        bre_list.append(float(np.exp(row["A_simple"] + row["B_simple"] * np.log(cs))))
        cs_list.append(cs)
        source_list.append("regression")

    res_df = res_df.copy()
    res_df["Cs_site"]    = cs_list
    res_df["Br_E"]       = bre_list
    res_df["Br_E_source"] = source_list
    return res_df


# ═══════════════════════════════════════════════════════════════════════════════
# ETM couverts par INERIS-DRC-17-163615-01452A (table officielle, pas de régression
# recalculée sur BAPPET) — voir data/metaux_ineris_lookup.py
# ═══════════════════════════════════════════════════════════════════════════════

_CAT_DISPLAY_INERIS = {
    "legumes_feuilles": "légumes-feuilles",
    "legumes_fruits":   "légumes-fruits",
    "legumes_racines":  "légumes-racines",
    "tubercules":       "tubercules",
    "cereales":         "céréales",
    "fourrage":         "fourrage",
}


def _eval_regression_ineris(reg: dict, cs: float, pH: float, mo_pct: float):
    """
    Évalue ln BCF = intercept + coefs..., seulement si toutes les variables
    utilisées par CETTE régression sont disponibles et dans leur domaine de
    validité publié. Contrairement à la régression BAPPET (qui exige
    conc_sol_metaux), une régression n'utilisant que pH/MO est évaluable même
    sans concentration sol fournie (pH et matière organique sont toujours
    connus, ce sont des paramètres obligatoires du site).

    Retourne (Br_E, True) si évaluable, sinon (None, False).
    """
    if reg is None:
        return None, False

    domaine = reg.get("domaine", {})
    ln_bcf = reg["intercept"]

    if "coef_ln_cs" in reg:
        if cs is None:
            return None, False
        lo, hi = domaine.get("Cs", (-np.inf, np.inf))
        if not (lo <= cs <= hi):
            return None, False
        ln_bcf += reg["coef_ln_cs"] * np.log(cs)

    if "coef_ph" in reg:
        if pH is None:
            return None, False
        lo, hi = domaine.get("pH", (-np.inf, np.inf))
        if not (lo <= pH <= hi):
            return None, False
        ph_val = np.log(pH) if reg.get("ph_log") else pH
        ln_bcf += reg["coef_ph"] * ph_val

    if "coef_mo" in reg:
        if mo_pct is None:
            return None, False
        lo, hi = domaine.get("MO", (-np.inf, np.inf))
        if not (lo <= mo_pct <= hi):
            return None, False
        ln_bcf += reg["coef_mo"] * mo_pct

    return float(np.exp(ln_bcf)), True


def _build_ineris_metaux_rows(sol: dict = None) -> pd.DataFrame:
    """
    Construit les lignes Br_E pour les 8 ETM couverts par
    INERIS-DRC-17-163615-01452A, à partir des coefficients officiellement
    publiés (data/metaux_ineris_lookup.py) plutôt que de la régression BAPPET.
    """
    sol         = sol or {}
    conc_sol    = sol.get("conc_sol_metaux", {})
    pH_site     = sol.get("pH")
    mo_pct_site = sol["matiere_organique"] * 100 if "matiere_organique" in sol else None

    rows = []
    for etm in sorted(ETM_COUVERTS):
        etm_table = BR_PAR_ETM[etm]
        for cat_key in _CAT_DISPLAY_INERIS:
            entry = resolve_categorie(etm_table, cat_key)
            if entry is None:
                continue

            cs_site = conc_sol.get(etm)
            br_e, used_regression = _eval_regression_ineris(
                entry.get("regression"), cs_site, pH_site, mo_pct_site
            )
            source = "ineris_regression"

            if not used_regression:
                mediane = entry.get("mediane")
                if mediane is not None:
                    br_e, source = mediane, "ineris_mediane"
                elif entry.get("min") is not None and entry.get("max") is not None:
                    br_e, source = (entry["min"] + entry["max"]) / 2, "ineris_intervalle_moyen"
                else:
                    continue  # aucune valeur disponible pour ce groupe

            reg = entry.get("regression") or {}
            cs_dom = reg.get("domaine", {}).get("Cs", (None, None))
            rows.append({
                "ETM":                 etm,
                "Categorie_INERIS":    _CAT_DISPLAY_INERIS[cat_key],
                "Br_E":                br_e,
                "Br_E_source":         source,
                "Cs_site":             cs_site if used_regression else None,
                "BCF_min":             entry.get("min"),
                "BCF_max":             entry.get("max"),
                "BCF_median":          entry.get("mediane"),
                "BCF_mean_geom_pond":  entry.get("mediane"),
                "Cs_valid_min":        cs_dom[0],
                "Cs_valid_max":        cs_dom[1],
                "mode_filtrage":       "ineris_publie",
                "n_total":             entry.get("n"),
                "n_outliers_grubbs":   None,
                "A_simple":            reg.get("intercept"),
                "B_simple":            reg.get("coef_ln_cs"),
                "r2_simple":           reg.get("r2"),
                "p_simple":            None,
                "regression_retenue":  used_regression,
                "best_distrib":        None,
                "unité":               "mg/kg_vegsec / (mg/kg_sol)",
                "modele":              "INERIS-DRC-17-163615",
            })

    return pd.DataFrame(rows)


def compute_bcf_metaux(data_path: Path = None,
                       aprifel_path: Path = None,
                       sol: dict = None) -> pd.DataFrame:
    """
    Exécute le pipeline complet INERIS (filtres F1-F10, régressions OLS,
    ajustement de distribution) et retourne un DataFrame de résultats.

    Colonnes clés du résultat :
      ETM, Categorie_INERIS, Br_E, Br_E_source, Cs_site, unité, modele,
      BCF_min, BCF_median, BCF_max, BCF_mean_geom_pond, mode_filtrage,
      n_total, n_outliers_grubbs, A_simple, B_simple, r2_simple,
      regression_retenue, best_distrib, …

    Parameters
    ----------
    data_path    : chemin vers bappet.csv (défaut : data/bappet/bappet.csv)
    aprifel_path : chemin vers aprifel_pct_ms.csv (défaut : data/aprifel/aprifel_pct_ms.csv)
    sol          : dict sol du site (issu de load_sol). Si contient
                   "conc_sol_metaux" {ETM: Cs_mg_kg}, la régression
                   Cs-dépendante est utilisée quand elle est retenue.
    """
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if data_path is None:
        data_path = _DATA_DIR / "bappet" / "bappet.csv"
    if aprifel_path is None:
        aprifel_path = _DATA_DIR / "aprifel" / "aprifel_pct_ms.csv"

    # -- 1. Chargement ---------------------------------------------------------
    df_raw = pd.read_csv(data_path, sep=";", encoding="utf-8-sig", dtype=str, low_memory=False)
    df_raw = df_raw.loc[:, ~df_raw.columns.str.startswith("Unnamed")]
    print(f"Chargé : {df_raw.shape[0]} lignes, {df_raw.shape[1]} colonnes")

    df_raw["ETM"] = df_raw["ETM"].apply(normalise_etm)

    aprifel_df = pd.read_csv(aprifel_path)
    aprifel_lookup, aprifel_norms, first_word_lookup = build_aprifel_lookup(aprifel_df)
    print(f"APRIFEL : {len(aprifel_lookup)} espèces normalisées")

    # -- 2. Filtre unité : Sol (mg/kg) -----------------------------------------
    df_sol = df_raw[df_raw["Milieu analysé (unités)"].str.strip() == "Sol (mg/kg)"].copy()
    print(f"\nAprès filtre Sol (mg/kg)       : {df_sol.shape[0]} lignes")

    # Exclusion absolue : végétaux non lavés (avant toute ramification strict/relâché)
    _lav_sol = _norm_str(df_sol["Lavage/Pelage"])
    _mask_non_lave = _lav_sol.isin(_F7_EXCL_RELAX)
    n_non_lave = int(_mask_non_lave.sum())
    df_sol = df_sol[~_mask_non_lave].copy()
    print(f"Végétaux non lavés exclus      : {n_non_lave} lignes")
    print(f"Après exclusion non lavés      : {df_sol.shape[0]} lignes")

    # -- 3. Filtres INERIS — mode strict ---------------------------------------
    print("\n-- Filtres INERIS stricts (F1-F7) ------------------------------------")
    df_strict_raw, strict_stats = filtrer_ineris(df_sol, strict=True)
    for fname, n in strict_stats.items():
        print(f"  {fname:<30s} : {n:>5} lignes retirées")
    print(f"  -> Après filtres stricts       : {df_strict_raw.shape[0]} lignes")

    # -- 4. Filtres INERIS — mode relâché --------------------------------------
    print("\n-- Filtres INERIS relâchés (F1, F4, F5, F6 uniquement) ---------------")
    df_semi_raw, semi_stats = filtrer_ineris(df_sol, strict=False)
    for fname, n in semi_stats.items():
        print(f"  {fname:<30s} : {n:>5} lignes retirées")
    print(f"  -> Après filtres relâchés      : {df_semi_raw.shape[0]} lignes")

    df_semi_raw["_strict"] = df_semi_raw.index.isin(df_strict_raw.index)

    # -- 5. Calcul BCF + catégories INERIS ------------------------------------
    print("\n-- Calcul BCF --------------------------------------------------------")
    df_semi = calculer_bcf(df_semi_raw, aprifel_lookup, aprifel_norms, first_word_lookup)

    n_strict_valid = df_semi["_strict"].sum()
    n_semi_valid   = len(df_semi)
    print(f"  BCF calculable — données strictes  : {n_strict_valid}")
    print(f"  BCF calculable — données relâchées : {n_semi_valid}")

    n_autre = (df_semi["categorie_ineris"] == "autre").sum()
    if n_autre > 0:
        print(f"\n  {n_autre} lignes non mappées -> 'autre' (Type Plante) :")
        for t, c in df_semi.loc[df_semi["categorie_ineris"] == "autre",
                                 "Type Plante"].value_counts().head(10).items():
            print(f"    '{t}' : {c}")

    # -- 6. Régressions OLS par groupe (ETM × catégorie INERIS) ---------------
    print(f"\n-- Régressions OLS (assouplissement si n_strict ≤ {SEUIL_ASSOUPLISSEMENT}) -----")

    results = []

    for (etm, cat), grp_semi in df_semi.groupby(["ETM", "categorie_ineris"]):

        grp_strict = grp_semi[grp_semi["_strict"]].copy()

        # -- F9 : filtre bruit de fond RECORD 1994 ----------------------------
        bdf_val  = BRUIT_DE_FOND_RECORD94.get(etm)
        seuil_cs = FACTEUR_BDF * bdf_val if bdf_val is not None else None

        def appliquer_bdf(grp):
            if seuil_cs is None or len(grp) == 0:
                return grp.copy(), 0
            median_bcf     = np.exp(np.median(grp["ln_BCF"].values))
            seuil_bcf_haut = 10.0 * median_bcf
            mask = ~((grp["Cs"] < seuil_cs) & (grp["BCF_calc"] > seuil_bcf_haut))
            return grp[mask].copy(), int((~mask).sum())

        grp_strict_bdf, n_bdf_strict = appliquer_bdf(grp_strict)
        n_strict = len(grp_strict_bdf)

        if n_strict <= SEUIL_ASSOUPLISSEMENT:
            grp_use, n_bdf_use = appliquer_bdf(grp_semi)
            mode = "assoupli"
        else:
            grp_use   = grp_strict_bdf
            n_bdf_use = n_bdf_strict
            mode = "strict"

        n = len(grp_use)
        if n == 0:
            continue

        # -- F10 : Grubbs sur ln(BCF) -----------------------------------------
        ln_b_filtered = grubbs_filter(grp_use["ln_BCF"])
        n_outliers    = n - len(ln_b_filtered)
        grp_clean     = grp_use.loc[ln_b_filtered.index]

        # -- Statistiques descriptives -----------------------------------------
        w_all   = grp_clean["Nb_ech_num"].values
        ln_vals = ln_b_filtered.values
        W_all   = w_all.sum()

        rec = {
            "ETM":                etm,
            "Categorie_INERIS":   cat,
            "mode_filtrage":      mode,
            "n_strict_bdf":       n_strict,
            "n_total":            n,
            "n_bdf_exclus":       n_bdf_use,
            "n_outliers_grubbs":  n_outliers,
            "poids_total":        W_all,
            "BCF_min":            np.exp(ln_vals.min()),
            "BCF_max":            np.exp(ln_vals.max()),
            "BCF_median":         np.exp(np.median(ln_vals)),
            "BCF_mean_arith":     np.exp(ln_vals).mean(),
            "BCF_mean_geom_pond": np.exp((w_all * ln_vals).sum() / W_all),
        }

        # -- Régression simple OLS ---------------------------------------------
        sub = grp_clean[["ln_BCF", "ln_Cs"]].dropna()
        rec["n_reg_simple"] = len(sub)

        if len(sub) >= MIN_N_SIMPLE and sub["ln_Cs"].nunique() > 1:
            x_s, y_s = sub["ln_Cs"].values, sub["ln_BCF"].values
            intercept, slope, r2, p_val = ols_simple(x_s, y_s)
            ratio_op = np.exp(y_s) / np.exp(intercept + slope * x_s)
            rec.update({
                "A_simple":     intercept,
                "B_simple":     slope,
                "r2_simple":    r2,
                "p_simple":     p_val,
                "OP_min":       ratio_op.min(),
                "OP_max":       ratio_op.max(),
                "Cs_valid_min": np.exp(x_s.min()),
                "Cs_valid_max": np.exp(x_s.max()),
            })
        else:
            rec.update({col: np.nan for col in [
                "A_simple", "B_simple", "r2_simple", "p_simple",
                "OP_min", "OP_max", "Cs_valid_min", "Cs_valid_max",
            ]})

        # -- Présélection Pearson + régression multiple OLS --------------------
        sub_m = grp_clean[["ln_BCF", "ln_Cs", "pH_num", "MO_num"]].dropna()
        rec["n_reg_multiple"] = len(sub_m)

        pearson_p_pH = np.nan
        pearson_p_MO = np.nan
        vars_selected = []

        if len(sub_m) >= MIN_N_MULTIPLE:
            vars_selected = ["ln_Cs"]
            n_obs_m = len(sub_m)
            y_m     = sub_m["ln_BCF"].values

            X_base = np.column_stack([np.ones(n_obs_m), sub_m["ln_Cs"].values])
            _, r2_base, _, _ = ols_multiple(X_base, y_m, k=1)
            r2adj_courant = r2_ajuste(r2_base, n_obs_m, 1)

            pearson_p_pH = float(stats.pearsonr(sub_m["ln_BCF"], sub_m["pH_num"])[1])
            if pearson_p_pH < PEARSON_ALPHA:
                X_test = np.column_stack([np.ones(n_obs_m),
                                          sub_m["ln_Cs"].values,
                                          sub_m["pH_num"].values])
                _, r2_test, _, _ = ols_multiple(X_test, y_m, k=2)
                if r2_ajuste(r2_test, n_obs_m, 2) > r2adj_courant:
                    vars_selected.append("pH")
                    r2adj_courant = r2_ajuste(r2_test, n_obs_m, 2)

            pearson_p_MO = float(stats.pearsonr(sub_m["ln_BCF"], sub_m["MO_num"])[1])
            if pearson_p_MO < PEARSON_ALPHA:
                k_courant = len(vars_selected)
                pred_test = (["ln_Cs"]
                             + (["pH_num"] if "pH" in vars_selected else [])
                             + ["MO_num"])
                X_test = np.column_stack([np.ones(n_obs_m)]
                                         + [sub_m[c].values for c in pred_test])
                _, r2_test, _, _ = ols_multiple(X_test, y_m, k=k_courant + 1)
                if r2_ajuste(r2_test, n_obs_m, k_courant + 1) > r2adj_courant:
                    vars_selected.append("MO")

        rec["pearson_p_pH"]    = pearson_p_pH
        rec["pearson_p_MO"]    = pearson_p_MO
        rec["vars_mult_model"] = "+".join(vars_selected) if vars_selected else ""

        if len(vars_selected) >= 2:
            n_obs = len(sub_m)
            pred_cols = (
                ["ln_Cs"]
                + (["pH_num"] if "pH" in vars_selected else [])
                + (["MO_num"] if "MO" in vars_selected else [])
            )
            X_m = np.column_stack([np.ones(n_obs)] + [sub_m[c].values for c in pred_cols])
            k   = len(pred_cols)
            coefs, r2_m, f_stat, p_fisher = ols_multiple(X_m, sub_m["ln_BCF"].values, k)

            A = float(coefs[0])
            B = float(coefs[1])
            C = float(coefs[2]) if "pH" in vars_selected else np.nan
            D = (float(coefs[3]) if ("pH" in vars_selected and "MO" in vars_selected)
                 else float(coefs[2]) if ("MO" in vars_selected and "pH" not in vars_selected)
                 else np.nan)

            ratio_op_m = np.exp(sub_m["ln_BCF"].values) / np.exp(X_m @ coefs)
            rec.update({
                "A_mult":        A,
                "B_lnCs_mult":   B,
                "C_pH":          C,
                "D_MO":          D,
                "r2_multiple":   r2_m,
                "F_stat_mult":   f_stat,
                "p_fisher_mult": p_fisher,
                "OP_min_mult":   ratio_op_m.min(),
                "OP_max_mult":   ratio_op_m.max(),
                "pH_valid_min":  sub_m["pH_num"].min() if "pH" in vars_selected else np.nan,
                "pH_valid_max":  sub_m["pH_num"].max() if "pH" in vars_selected else np.nan,
                "MO_valid_min":  sub_m["MO_num"].min() if "MO" in vars_selected else np.nan,
                "MO_valid_max":  sub_m["MO_num"].max() if "MO" in vars_selected else np.nan,
            })
        else:
            rec.update({col: np.nan for col in [
                "A_mult", "B_lnCs_mult", "C_pH", "D_MO",
                "r2_multiple", "F_stat_mult", "p_fisher_mult",
                "OP_min_mult", "OP_max_mult",
                "pH_valid_min", "pH_valid_max", "MO_valid_min", "MO_valid_max",
            ]})

        # -- Distribution Anderson-Darling -------------------------------------
        best_dist, best_ad, p_ln = fit_best_distribution_ineris(np.exp(ln_vals))
        rec["best_distrib"]    = best_dist
        rec["AD_stat"]         = best_ad
        rec["AD_pval_lognorm"] = p_ln

        rec["regression_retenue"] = regression_ineris_retenue(rec, np.exp(ln_vals))

        results.append(rec)

    # -- 7. Assemblage du DataFrame --------------------------------------------
    res_df = pd.DataFrame(results)

    # Br_E selon disponibilité de conc_sol_metaux dans le sol site
    conc_sol = (sol or {}).get("conc_sol_metaux", {})
    if conc_sol:
        print(f"\n-- Br_E métaux : régression Cs-dépendante ({len(conc_sol)} ETM fournis) --")
    else:
        print("\n-- Br_E métaux : moyenne géométrique (pas de conc_sol_metaux dans le site) --")

    res_df = _appliquer_cs_site(res_df, conc_sol)
    res_df["unité"]  = "mg/kg_vegsec / (mg/kg_sol)"
    res_df["modele"] = "BAPPET_OLS"

    # -- Retrait des ETM couverts par INERIS-DRC-17-163615-01452A ---------------
    # (As, Cd, Cr, Hg, Ni, Pb, Se, V) : remplacés plus bas par la table
    # officielle plutôt que la régression BAPPET recalculée ci-dessus.
    n_avant_retrait = len(res_df)
    res_df = res_df[~res_df["ETM"].isin(ETM_COUVERTS)].copy()
    print(f"\n-- ETM couverts par INERIS-DRC-17-163615-01452A : {sorted(ETM_COUVERTS)} --")
    print(f"  {n_avant_retrait - len(res_df)} groupes BAPPET retirés (remplacés par la table officielle)")

    if conc_sol:
        n_reg  = (res_df["Br_E_source"] == "regression").sum()
        n_geom = len(res_df) - n_reg
        print(f"  Br_E par régression Cs-site : {n_reg} groupes")
        print(f"  Br_E par moy. géométrique   : {n_geom} groupes")

    n_strict_grps = (res_df["mode_filtrage"] == "strict").sum()
    n_assoup_grps = (res_df["mode_filtrage"] == "assoupli").sum()
    n_simple      = res_df["r2_simple"].notna().sum()
    n_multiple    = res_df["r2_multiple"].notna().sum()
    n_fisher_ok   = (res_df["p_fisher_mult"].fillna(1) < 0.05).sum()

    print(f"\n-- Résultats ----------------------------------------------------------")
    print(f"Groupes (ETM × Catégorie INERIS)                  : {len(res_df)}")
    print(f"  dont filtrage strict                             : {n_strict_grps}")
    print(f"  dont assouplissement (n_strict ≤ {SEUIL_ASSOUPLISSEMENT})             : {n_assoup_grps}")
    print(f"  Bruit de fond RECORD94 retirés (total)           : {res_df['n_bdf_exclus'].sum():.0f}")
    print(f"  Outliers Grubbs retirés (total)                  : {res_df['n_outliers_grubbs'].sum():.0f}")
    print(f"  Régression simple OLS   (n ≥ {MIN_N_SIMPLE})                  : {n_simple}")
    print(f"  Régression multiple OLS (n ≥ {MIN_N_MULTIPLE}, ≥1 var Pearson) : {n_multiple}")
    print(f"  dont Fisher significatif (p < 0.05)              : {n_fisher_ok}")

    # -- Ajout des ETM couverts par la table officielle INERIS ------------------
    df_ineris = _build_ineris_metaux_rows(sol)
    n_reg_ineris = (df_ineris["Br_E_source"] == "ineris_regression").sum()
    print(f"\n-- ETM depuis table officielle INERIS-DRC-17-163615-01452A --")
    print(f"  {len(df_ineris)} groupes ({sorted(ETM_COUVERTS)})")
    print(f"  dont Br_E par régression officielle (pH/MO/Cs) : {n_reg_ineris}")
    print(f"  dont Br_E par médiane/intervalle publié        : {len(df_ineris) - n_reg_ineris}")

    res_df = pd.concat([res_df, df_ineris], ignore_index=True)

    return res_df


# ═══════════════════════════════════════════════════════════════════════════════
# Standalone — python data/metaux.py
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    res_df = compute_bcf_metaux()

    out_path = _DATA_DIR / "bcf_metaux_results.csv"
    res_df.to_csv(out_path, index=False, encoding="utf-8-sig", float_format="%.4f")
    print(f"\nFichier sauvegardé : {out_path}")

    pd.options.display.float_format = "{:.4f}".format
    pd.options.display.max_colwidth = 22
    pd.options.display.width        = 200

    print("\n-- Top 20 groupes — régression simple OLS, r² décroissant ----------")
    cols_s = ["ETM", "Categorie_INERIS", "mode_filtrage", "n_total",
              "BCF_mean_geom_pond", "A_simple", "B_simple", "r2_simple", "p_simple"]
    print(res_df.dropna(subset=["r2_simple"]).nlargest(20, "r2_simple")[cols_s].to_string(index=False))

    print("\n-- Régression multiple OLS — Fisher sig. (p < 0.05), r² décroissant -")
    cols_m = ["ETM", "Categorie_INERIS", "mode_filtrage", "n_reg_multiple",
              "vars_mult_model", "A_mult", "B_lnCs_mult", "C_pH", "D_MO",
              "r2_multiple", "p_fisher_mult"]
    mult = (res_df
            .dropna(subset=["r2_multiple"])
            .query("p_fisher_mult < 0.05")
            .sort_values("r2_multiple", ascending=False))
    print(mult[cols_m].to_string(index=False))

    print("\n-- Groupes assouplis (n_strict ≤ 10) -------------------------------")
    assoup = res_df[res_df["mode_filtrage"] == "assoupli"][
        ["ETM", "Categorie_INERIS", "n_strict_bdf", "n_total"]
    ].sort_values(["ETM", "Categorie_INERIS"])
    print(assoup.to_string(index=False))

    print("\n-- Distribution ajustée — répartition par groupe --------------------")
    print(res_df.groupby("best_distrib")["ETM"].count().rename("nb_groupes").to_string())

    r'''
    # ═══════════════════════════════════════════════════════════════════════════
    # Graphiques ln(BCF) vs ln(Cs) par ETM × catégorie INERIS
    # Décommenter les imports suivants si nécessaire :
    #   import matplotlib
    #   matplotlib.use("Agg")
    #   import matplotlib.pyplot as plt
    # ═══════════════════════════════════════════════════════════════════════════
    PLOT_DIR = Path(r"C:\Users\Utilisateur\PycharmProjects\MFE\data\plots_bcf")
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    res_lookup = {(r["ETM"], r["Categorie_INERIS"]): r for r in res_df.to_dict("records")}

    for etm, grp_etm in df_semi.groupby("ETM"):
        cats = sorted(grp_etm["categorie_ineris"].dropna().unique())
        n_cats = len(cats)
        if n_cats == 0:
            continue

        fig, axes = plt.subplots(1, n_cats, figsize=(5 * n_cats, 4), squeeze=False)
        fig.suptitle(f"{etm} — ln(BCF) vs ln(Cs)", fontsize=13)

        for i, cat in enumerate(cats):
            ax = axes[0][i]
            sub = (grp_etm[grp_etm["categorie_ineris"] == cat][["ln_BCF", "ln_Cs"]]
                   .dropna())

            ax.scatter(sub["ln_Cs"], sub["ln_BCF"],
                       color="red", s=20, alpha=0.7, zorder=3, label="données")

            row = res_lookup.get((etm, cat), {})
            a = row.get("A_simple", np.nan)
            b = row.get("B_simple", np.nan)
            r2 = row.get("r2_simple", np.nan)
            if np.isfinite(a) and np.isfinite(b) and len(sub) >= MIN_N_SIMPLE:
                x_min, x_max = sub["ln_Cs"].min(), sub["ln_Cs"].max()
                x_range = np.linspace(x_min, x_max, 200)
                ax.plot(x_range, a + b * x_range,
                        color="black", linewidth=1.5,
                        label=f"r²={r2:.3f}  y={a:+.3f}{b:+.3f}·x")

            ax.set_xlabel("ln(Cs)")
            ax.set_ylabel("ln(BCF)")
            ax.set_title(f"{cat}\nn={len(sub)}", fontsize=9)
            ax.legend(fontsize=7)
            ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)

        plt.tight_layout()
        fig.savefig(PLOT_DIR / f"{etm}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  {etm} -> {PLOT_DIR / f'{etm}.png'}")

    print(f"\nGraphiques sauvegardés dans : {PLOT_DIR}")
    '''
