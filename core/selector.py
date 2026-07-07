def select_model_and_bcf(
        polluant: dict,
        vegetal: dict) -> tuple[str, str]:
    """
    Sélection du modèle selon les propriétés physico-chimiques du polluant
    et l'organe cible.

    Critères de sélection :
      racine (légumes_racines + tubercules)
          HAP (hors naphtalène) → Kipopoulou et al. (1999) (mesure/régression carotte)
          sinon → Briggs (modèle sol-racine, orge hydroponique)
      feuille
          H > 0.1              → Mackay_97  (voie atmosphérique significative)
          H ≤ 0.1, Kow ∈ [1;8] → Travis_Arms  (parties aériennes, MODUL'ERS)
          sinon                → PlantX
      fruit
          H > 0.1              → PlantX  (seul modèle fruit + voie atmosphérique)
          H ≤ 0.1, Kow ∈ [1;8] → Travis_Arms  (parties aériennes, MODUL'ERS)
          sinon                → PlantX
    """
    organe  = vegetal["organe"]
    log_kow = polluant["log_kow"]
    kaw     = polluant["H"]

    if organe == "racine":
        if polluant["famille"] == "HAP" and polluant["nom"] != "naphtalène":
            return ("Kipopoulou_1999", "BCF_racine")
        if log_kow <= 5.0:
            return ("Briggs", "BCF_racine")
        return ("PlantX", "BCF_racine")

    if organe == "feuille":
        if kaw > 0.1:
            return ("Mackay_97", "BCF_feuille")
        if 1.0 <= log_kow <= 8.0:
            return ("Travis_Arms", "BCF_feuille")
        return ("PlantX", "BCF_feuille")

    # fruit
    if kaw > 0.1:
        return ("PlantX", "BCF_fruit")
    if 1.0 <= log_kow <= 8.0:
        return ("Travis_Arms", "BCF_fruit")
    return ("PlantX", "BCF_fruit")   # log Kow hors domaine Travis & Arms [1 ; 8]
