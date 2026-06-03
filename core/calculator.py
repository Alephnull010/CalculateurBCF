from models.briggs       import briggs_bcf, briggs_validity
from models.travis_arms  import travis_arms_bcf, travis_arms_validity
from models.mackay97     import mackay97_bcf
from models.plantx       import plantx_bcf
from core.selector   import select_model_and_bcf
from core.validator  import check_warnings


def compute_bre(
        polluant_nom: str,
        vegetal_nom:  str,
        polluants:    dict,
        vegetaux:     dict,
        sol:          dict) -> dict:
    """
    Calcule Br_E à renseigner dans MODUL'ERS.
    Gère les polluants organiques (modèles physico-chimiques) et les PCB (lookup tabulé).
    """
    p = {**polluants[polluant_nom], "nom": polluant_nom}
    v = vegetaux[vegetal_nom]

    modele, cle_bcf = select_model_and_bcf(p, v)

    if modele == "Briggs":
        bcf_value = briggs_bcf(p["log_kow"])
        warnings  = briggs_validity(p["log_kow"])

    elif modele == "Mackay_97":
        result    = mackay97_bcf(p, v, sol)
        bcf_value = result[cle_bcf]
        warnings  = []

    elif modele == "Travis_Arms":
        bcf_value = travis_arms_bcf(p["log_kow"])
        warnings  = travis_arms_validity(p["log_kow"])

    elif modele == "PlantX":
        result    = plantx_bcf(p, v, sol)
        bcf_value = result[cle_bcf]
        warnings  = []

    warnings += check_warnings(p, v, modele, bcf_value)

    return {
        "polluant":   polluant_nom,
        "famille":    p["famille"],
        "nb_cycles":  p.get("nb_cycles"),
        "vegetal":    vegetal_nom,
        "organe":     v["organe"],
        "modele":     modele,
        "Br_E":       round(bcf_value, 6),
        "unité":      "mg/kg_vegsec / (mg/kg_sol)",
        "warnings":   warnings,
    }
