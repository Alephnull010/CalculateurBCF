from data.kipopoulou_lookup import (
    BCF_KIPOPOULOU_1999_CARROT,
    kipopoulou_regression_bcf,
)


def kipopoulou_bcf_racine(polluant: dict) -> dict:
    """
    BCF sol-racine pour les HAP — Kipopoulou, Manoli & Samara (1999), Tableau 6.
    Mesure directe (carotte) si disponible, sinon régression interne log(BCF) vs log(Kow).
    """
    nom = polluant["nom"]
    if nom in BCF_KIPOPOULOU_1999_CARROT:
        bcf = BCF_KIPOPOULOU_1999_CARROT[nom]
    else:
        bcf = kipopoulou_regression_bcf(polluant["log_kow"])
    return {"BCF_racine": bcf}
