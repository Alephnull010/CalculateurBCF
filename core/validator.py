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

    # BCF négatif ou nul
    if bcf <= 0:
        warnings.append("ERREUR : BCF <= 0 : vérifier les paramètres d'entrée")

    return warnings
