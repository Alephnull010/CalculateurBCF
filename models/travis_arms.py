def travis_arms_bcf(log_kow: float) -> float:
    """
    Calcule le BCF sol-plante selon Travis & Arms (1988)
    Log BCF = 1.588 - 0.578 × log Kow

    Basé sur parties aériennes (fruits, feuilles, tiges)

    Domaine de calibration source : 1 < log Kow < 9
    (McKone & Maddalena, LBNL-60273, 2007)

    Borne haute retenue : 8.0 (choix conservateur —
    au-delà de log Kow ~ 7-8, les données de calibration
    sont rares et très dispersées, Fig.2 McKone 2007)

    Unité sortie : mg/kg_vegsec / (mg/kg_sol)
    """
    log_bcf = 1.588 - 0.578 * log_kow
    return 10 ** log_bcf


def travis_arms_validity(log_kow: float) -> list:
    warnings = []
    if not (1.0 <= log_kow <= 8.0):
        warnings.append(
            f"log Kow={log_kow} hors domaine Travis & Arms [1.0 ; 8.0] "
            f"— résultat peu fiable"
        )
    return warnings
