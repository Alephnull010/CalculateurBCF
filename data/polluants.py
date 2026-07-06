'''
ces valeurs sont directement tirées du Tableau 2 du rapport INERIS :
N°INERIS DRC-05-57281/DESP R01a MODÈLES DE TRANSFERT SOL-PLANTE DES POLLUANTS ORGANIQUES
'''


POLLUANTS = {
    #HAP ==============================================================================
    "naphtalène": {
        "famille":  "HAP",
        "nb_cycles": 2,
        "log_kow":  3.40,
        "log_koc":  3.00,
        "MW":       128.0,    # g/mol
        "Pvap":     10.5,     # Pa
        "H":        0.02,     # sans unité (H = Cair/Ceau)
    },
    "anthracène": {
        "famille":  "HAP",
        "nb_cycles": 3,
        "log_kow":  4.45,
        "log_koc":  4.40,
        "MW":       178.0,
        "Pvap":     2.6e-2,
        "H":        2e-3,
    },
    "phénanthrène": {
        "famille":  "HAP",
        "nb_cycles": 3,
        "log_kow":  4.57,
        "log_koc":  6.13,
        "MW":       178.0,
        "Pvap":     9.1e-2,
        "H":        1.18e-8,
    },
    "benzo(a)pyrène": {
        "famille":  "HAP",
        "nb_cycles": 5,
        "log_kow":  6.00,
        "log_koc":  6.14,
        "MW":       252.0,
        "Pvap":     7.3e-7,
        "H":        1.65e-5,
    },
    "chloroforme": {
        "famille":  "COHV",
        "log_kow":  1.97,
        "log_koc":  1.77,
        "MW":       119.38,
        "Pvap":     2.125e5,
        "H":        0.123,
    },
    "tétrachloroéthylène": {
        "famille":  "COHV",
        "log_kow":  2.67,
        "log_koc":  2.39,
        "MW":       165.8,
        "Pvap":     1900,
        "H":        0.725,
    },

    #COHV Completés (à valider) -------------------
    "trichloroéthylène": {
        "famille": "COHV",
        "log_kow": 2.71, "log_koc": 2.22, "MW": 131.38,
        "Pvap": 9.20e3, "H": 0.422,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6575",
    },
    "cis-1,2-dichloroéthylène": {
        "famille": "COHV",
        "log_kow": 1.86, "log_koc": 1.55, "MW": 96.94,
        "Pvap": 2.67e4, "H": 0.167,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 643833",
    },
    "trans-1,2-dichloroéthylène": {
        "famille": "COHV",
        "log_kow": 2.07, "log_koc": 1.72, "MW": 96.94,
        "Pvap": 4.41e4, "H": 0.385,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 638186",
    },
    "1,1-dichloroéthylène": {
        "famille": "COHV",
        "log_kow": 2.13, "log_koc": 1.77, "MW": 96.94,
        "Pvap": 8.00e4, "H": 1.07,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6366",
    },
    "chlorure de vinyle": {
        "famille": "COHV",
        "log_kow": 1.50, "log_koc": 1.27, "MW": 62.50,
        "Pvap": 3.97e5, "H": 1.11,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6338",
    },
    "1,1,2-trichloroéthane": {
        "famille": "COHV",
        "log_kow": 2.05, "log_koc": 1.70, "MW": 133.40,
        "Pvap": 3.07e3, "H": 0.0374,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6574",
    },
    "1,1,1-trichloroéthane": {
        "famille": "COHV",
        "log_kow": 2.48, "log_koc": 2.04, "MW": 133.40,
        "Pvap": 1.65e4, "H": 0.705,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6278",
    },
    "1,2-dichloroéthane": {
        "famille": "COHV",
        "log_kow": 1.47, "log_koc": 1.24, "MW": 98.96,
        "Pvap": 1.05e4, "H": 0.0401,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 11",
    },
    "1,1-dichloroéthane": {
        "famille": "COHV",
        "log_kow": 1.79, "log_koc": 1.50, "MW": 98.96,
        "Pvap": 3.03e4, "H": 0.230,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6365",
    },
    "tétrachlorométhane": {
        "famille": "COHV",
        "log_kow": 2.73, "log_koc": 2.24, "MW": 153.81,
        "Pvap": 1.53e4, "H": 1.25,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 5943",
    },
    "dichlorométhane": {
        "famille": "COHV",
        "log_kow": 1.25, "log_koc": 1.07, "MW": 84.93,
        "Pvap": 5.80e4, "H": 0.0898,
        "source": "EPA SSL Tech. Background Doc. Table 36/39 (1996) / PubChem CID 6344",
    },

    #HCT (hydrocarbures totaux, fractions fiables uniquement) Complétés (à valider) ---
    # Fractions C16-C40 volontairement exclues : log_kow extrapolé ~10, hors du domaine
    # calibré des modèles (voir README §5) — cohérent avec la mobilité xylémique quasi
    # nulle des composés très hydrophobes (TSCF en cloche, décroissante au-delà de
    # log Kow ~3-4), pas seulement une limite de calcul.
    "fraction c10-c12": {
        "famille": "HCT",
        "log_kow": 5.31, "log_koc": 5.22, "MW": 151.0,
        "Pvap": 64.2, "H": 84.0,
        "source": "TPHCWG (1997) tranche C10-C12. Mix 70% aliphatique/30% aromatique "
                  "(mix par défaut guide wallon des sols pollués, pas de spéciation labo). "
                  "Données aliph./arom. (MW, H, solubilité S, Koc) via WA Dept. of Ecology "
                  "MTCA Table 747-4 / CLARC Table 4 (rev. août 2022). Ordre de calcul : "
                  "1) log_kow et Pvap dérivés SÉPARÉMENT pour la composante aliphatique et "
                  "la composante aromatique (log_kow via EPA SSL Tech. Background Doc. éq.70, "
                  "log Koc=0.983 log Kow+0.00028 ; Pvap = H·R·T·S/MW appliqué à chaque "
                  "composante) ; 2) les deux résultats Pvap (et Kow linéaire, puis log10) sont "
                  "ensuite mixés 70/30. Ne PAS appliquer la formule Pvap aux valeurs H/S/MW "
                  "déjà mixées — l'ordre des opérations n'est pas commutatif ici (écart "
                  "constaté d'un facteur ~150 si on le fait dans le mauvais ordre, car H et S "
                  "varient sur plusieurs ordres de grandeur entre aliphatique et aromatique).",
    },
    "fraction c12-c16": {
        "famille": "HCT",
        "log_kow": 6.69, "log_koc": 6.58, "MW": 185.0,
        "Pvap": 4.95, "H": 364,
        "source": "TPHCWG (1997) tranche C12-C16, mix 70/30 aliph./arom. — mêmes sources et "
                  "même ordre de calcul (dérivation par composante puis mix) que "
                  "'fraction c10-c12', voir note complète ci-dessus.",
    },

    #HAP Completés (à valider) -------------------
    "acénaphtylène": {
        "famille": "HAP", "nb_cycles": 3,
        "log_kow": 3.94, "log_koc": 3.73, "MW": 152.2,
        "Pvap": 0.90,
        "H": 1.2e-3,        # IARC92 : H=2.97 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "acénaphtène": {
        "famille": "HAP", "nb_cycles": 3,
        "log_kow": 3.92, "log_koc": 3.71, "MW": 154.2,
        "Pvap": 0.30,
        "H": 3.7e-4,        # IARC92 : H=0.91 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "fluorène": {
        "famille": "HAP", "nb_cycles": 3,
        "log_kow": 4.18, "log_koc": 3.97, "MW": 166.2,
        "Pvap": 0.09,
        "H": 1.6e-4,        # IARC92 : H=0.40 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "fluoranthène": {
        "famille": "HAP", "nb_cycles": 4,
        "log_kow": 5.22, "log_koc": 5.01, "MW": 202.3,
        "Pvap": 1.23e-2,
        "H": 4.2e-4,        # IARC92 : H=1.04 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "pyrène": {
        "famille": "HAP", "nb_cycles": 4,
        "log_kow": 5.18, "log_koc": 4.97, "MW": 202.3,
        "Pvap": 7.35e-3,
        "H": 3.7e-4,        # IARC92 : H=0.92 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "benzo(a)anthracène": {
        "famille": "HAP", "nb_cycles": 4,
        "log_kow": 5.61, "log_koc": 5.40, "MW": 228.3,
        "Pvap": 2.8e-4,
        "H": 2.3e-4,        # IARC92 : H=0.58 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "chrysène": {
        "famille": "HAP", "nb_cycles": 4,
        "log_kow": 5.86, "log_koc": 5.65, "MW": 228.3,
        "Pvap": 6.5e-5,
        "H": 2.6e-5,        # IARC92 : H=0.065 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "benzo(b)fluoranthène": {
        "famille": "HAP", "nb_cycles": 5,
        "log_kow": 5.80, "log_koc": 5.59, "MW": 252.3,
        "Pvap": 6.67e-5,
        "H": 1.9e-5,        # IARC92 : H=0.047 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "benzo(k)fluoranthène": {
        "famille": "HAP", "nb_cycles": 5,
        "log_kow": 6.00, "log_koc": 5.79, "MW": 252.3,
        "Pvap": 1.28e-5,
        "H": 1.8e-5,        # IARC92 : H=0.045 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "indéno(1,2,3-cd)pyrène": {
        "famille": "HAP", "nb_cycles": 6,
        "log_kow": 6.58, "log_koc": 6.37, "MW": 276.3,
        "Pvap": 1.3e-8,
        "H": 1.25e-5,       # IARC92 : H=0.031 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "dibenzo(a,h)anthracène": {
        "famille": "HAP", "nb_cycles": 5,
        "log_kow": 6.75, "log_koc": 6.54, "MW": 278.4,
        "Pvap": 3.7e-9,
        "H": 1.0e-5,        # IARC92 : H=0.025 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },
    "benzo(g,h,i)pérylène": {
        "famille": "HAP", "nb_cycles": 6,
        "log_kow": 6.63, "log_koc": 6.42, "MW": 276.3,
        "Pvap": 1.4e-8,
        "H": 1.09e-5,       # IARC92 : H=0.027 Pa.m3/mol / RT
        "source": "IARC92 / EPI Suite",
    },

    #BTEX ==============================================================================
    "benzène": {
        "famille": "BTEX",
        "log_kow": 2.13,
        "log_koc": 1.82,
        "MW": 78.11,
        "Pvap": 1.27e4,
        "H": 0.23,
    },
    "toluène": {
        "famille": "BTEX",
        "log_kow": 2.72,
        "log_koc": 2.42,
        "MW": 92.00,
        "Pvap": 2.92e3,
        "H": 0.23,
    },

    #BTEX Completés (à valider) -------------------
    "éthylbenzène": {
        "famille": "BTEX",
        "log_kow": 3.15, "log_koc": 2.94, "MW": 106.2,
        "Pvap": 1.27e3, "H": 0.32,
        "source": "EPI Suite / Mackay 2006",
    },
    "o-xylène": {
        "famille": "BTEX",
        "log_kow": 3.12, "log_koc": 2.91, "MW": 106.2,
        "Pvap": 880, "H": 0.21,
        "source": "EPI Suite / Mackay 2006",
    },
    "m,p-xylène": {
        "famille": "BTEX",
        "log_kow": 3.18, "log_koc": 2.97, "MW": 106.2,
        "Pvap": 1085, "H": 0.305,
        "source": "EPI Suite / Mackay 2006 - moyenne simple 50/50 des valeurs pures "
                  "m-xylène (log_kow 3.20, log_koc 2.99, Pvap 1000, H 0.30) et p-xylène "
                  "(log_kow 3.15, log_koc 2.94, Pvap 1170, H 0.31). Fusionnées en une seule "
                  "entrée car m- et p-xylène co-éluent sur la plupart des colonnes GC "
                  "standards (points d'ébullition quasi identiques, 139°C et 138°C) et sont "
                  "systématiquement rapportés comme un seul résultat 'm,p-xylène' dans les "
                  "bulletins d'analyse - contrairement à l'o-xylène (144°C), résolu séparément.",
    },
}