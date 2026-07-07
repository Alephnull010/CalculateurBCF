def check_warnings(
        polluant: dict,
        vegetal:  dict,
        modele:   str,
        bcf:      float) -> list:

    warnings = []

    # PlantX hors domaine de validation pour les HAP très lipophiles
    if modele == "PlantX" and polluant["log_kow"] > 5.0:
        warnings.append(
            f"log Kow={polluant['log_kow']} > 5.0 : "
            f"PlantX non validé pour les HAP lourds — résultat à interpréter avec précaution"
        )

    # Mackay_97 : vérifier la fiabilité de conc_air pour les composés très volatils
    if modele == "Mackay_97" and vegetal["organe"] == "feuille":
        warnings.append(
            "Mackay_97 feuille : BCF sensible à conc_air — "
            "utiliser une mesure représentative du site"
        )

    # Fruits non testés hors tomate/haricot (uniquement pour PlantX)
    if modele == "PlantX" and vegetal["organe"] == "fruit" and vegetal.get("exemples"):
        non_valides = [e for e in vegetal["exemples"]
                       if e not in ["tomate", "haricot"]]
        if non_valides:
            warnings.append(
                "PlantX validé uniquement sur tomate/haricot"
            )

    # Kipopoulou et al. (1999) : mesure carotte extrapolée à racine/tubercule
    if modele == "Kipopoulou_1999":
        warnings.append(
            "Kipopoulou et al. (1999) : BCF mesuré sur carotte (Thessalonique) "
            "extrapolé à l'ensemble légumes racines/tubercules — une part de la "
            "contamination mesurée peut provenir de l'adhésion de particules de sol "
            "plutôt que d'une absorption réelle ; préciser épluchage/lavage en exposition"
        )
        if polluant["nom"] in {"acénaphtylène", "acénaphtène", "fluorène"}:
            warnings.append(
                "BCF dérivé par régression interne (log BCF = 2.809 - 0.5703×log Kow, "
                "R=-0.85, n=12), faute de mesure directe dans Kipopoulou (1999)"
            )

    # BCF négatif ou nul
    if bcf <= 0:
        warnings.append("ERREUR : BCF <= 0 : vérifier les paramètres d'entrée")

    return warnings
