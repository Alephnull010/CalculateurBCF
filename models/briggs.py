def briggs_bcf(log_kow: float) -> float:
    """
    Calcule le BCF sol-plante selon Briggs et al. (1982)
    Log BCF = 0.77 * log_kow - 1.52

    Valide pour log Kow entre -0.57 et 3.7
    Unité sortie : mg/kg_vegsec / (mg/kg_sol)
    """
    log_bcf = 0.77 * log_kow - 1.52
    return 10 ** log_bcf


def briggs_validity(log_kow: float) -> list:
    warnings = []
    if not (-0.57 <= log_kow <= 3.7):
        warnings.append(
            f"log Kow={log_kow} hors domaine Briggs [-0.57 ; 3.7] "
            f"— résultat peu fiable"
        )
    return warnings