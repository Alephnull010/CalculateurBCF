# -*- coding: utf-8 -*-
"""
BCF sol-racine pour les HAP, mesurés par Kipopoulou, Manoli & Samara (1999),
Environ. Pollut. 106:369-380, Tableau 6 (BCF_SV, carotte épluchée, sol agricole
industriel, n=12, base sèche pour sol et végétal).

Valeurs transcrites depuis l'article original (accès direct utilisateur) — non
revérifiées indépendamment (ScienceDirect/ResearchGate inaccessibles en lecture
automatisée : 403).

Limites : espèce unique (carotte), extrapolée ici à légumes_racines ET tubercules.
Écart ×50-100 avec Samsøe-Petersen (2002) sur le benzo(a)pyrène (0.19 vs 0.002-0.004) —
valeur retenue = la plus conservatrice des deux études (choix protecteur ERS).
"""

BCF_KIPOPOULOU_1999_CARROT = {
    "phénanthrène":            3.20,
    "anthracène":               1.40,
    "fluoranthène":             1.11,
    "pyrène":                   1.40,
    "benzo(a)anthracène":       0.17,
    "chrysène":                 0.23,
    "benzo(b)fluoranthène":     0.12,
    "benzo(k)fluoranthène":     0.14,
    "benzo(a)pyrène":           0.19,
    "dibenzo(a,h)anthracène":   0.20,
    "benzo(g,h,i)pérylène":     0.13,
    "indéno(1,2,3-cd)pyrène":   0.16,
}

# Régression log-linéaire recalculée sur les 12 points ci-dessus (log Kow du
# dataset interne data/polluants.py, pas ceux des auteurs) — R=-0.850, n=12.
# Réservée aux 3 HAP légers non couverts par une mesure directe.
REGRESSION_INTERCEPT = 2.809
REGRESSION_SLOPE     = -0.5703
REGRESSION_R         = -0.850
REGRESSION_N         = 12


def kipopoulou_regression_bcf(log_kow: float) -> float:
    log_bcf = REGRESSION_INTERCEPT + REGRESSION_SLOPE * log_kow
    return 10 ** log_bcf
