# -*- coding: utf-8 -*-
"""
Coefficients de transfert sol-plante (Br) et air-plante (Bf, mercure uniquement)
pour 8 éléments traces métalliques, publiés directement par INERIS.

Source : INERIS-DRC-17-163615-01452A (26/06/2017), "Coefficients de transfert
des éléments traces métalliques vers les plantes, utilisés pour l'évaluation
de l'exposition - Application dans le logiciel MODUL'ERS", Tableaux 1 à 9.
https://www.ineris.fr/ (rapport ETM, distinct de celui des PCB/PCDD-F)

Ce rapport ne couvre que 8 des 15 ETM traités par `data/metaux.py` :
As, Cd, Cr, Hg, Ni, Pb, Se, V. Les 7 autres (Co, Cu, Mn, Mo, Sb, Tl, Zn) ne
sont pas couverts ici et restent calculés par la régression BAPPET
"maison" (`compute_bcf_metaux` dans `data/metaux.py`).

Structure par (ETM, catégorie) : dict avec :
  n            : nombre de données retenues (int ou None)
  mediane      : meilleure valeur ponctuelle disponible (médiane de la
                 distribution ajustée, ou valeur ponctuelle du rapport quand
                 aucune distribution n'a été ajustée - ex. vanadium)
  min, max     : bornes de l'intervalle observé (None si non fourni)
  regression   : None, ou dict décrivant `ln BCF = intercept + coefs...`
                 - intercept, coef_ln_cs / coef_ph / coef_mo (absents si la
                   variable n'entre pas dans le modèle retenu)
                 - ph_log : True si la variable pH entre comme ln(pH) et non
                   pH brut (cas particulier : nickel légumes-fruits)
                 - n, r2, significatif (test de Fisher)
                 - domaine : {"Cs": (min,max), "pH": (min,max), "MO": (min,max)}
                   bornes de validité des variables utilisées, hors desquelles
                   le rapport recommande de ne pas utiliser la régression
                 - op_range : (min,max) du ratio observé/prédit
  source_categorie : None, ou le nom d'une autre catégorie dont les valeurs
                 sont intégralement reprises (substitution faute de données
                 propres - ex. tubercules reprenant légumes-racines)

Usage :
    from data.metaux_ineris_lookup import BR_PAR_ETM, BF_HG_PAR_CATEGORIE, ETM_COUVERTS
"""

ETM_COUVERTS = {"As", "Cd", "Cr", "Hg", "Ni", "Pb", "Se", "V"}

# ═══════════════════════════════════════════════════════════════════════════════
# Br - sol -> plante (mg.kg-1 sec / mg.kg-1 sec) - Tableaux 1 à 4, 6 à 9
# ═══════════════════════════════════════════════════════════════════════════════

BR_PAR_ETM = {

    "As": {
        "legumes_feuilles": {
            "n": 27, "mediane": 2.5e-2, "min": 4.8e-4, "max": 3.4e-1,
            "regression": {
                "intercept": -0.62, "coef_ln_cs": -0.78,
                "n": 27, "r2": 0.45, "significatif": True,
                "domaine": {"Cs": (3.0, 420)}, "op_range": (0.07, 9),
            },
        },
        "legumes_fruits": {
            "n": 39, "mediane": 1.8e-2, "min": 1.2e-4, "max": 8.2e-1,
            "regression": {
                "intercept": -11.9, "coef_ln_cs": -0.67, "coef_ph": 1.2, "coef_mo": 4.1e-2,
                "n": 27, "r2": 0.83, "significatif": True,
                "domaine": {"Cs": (0.8, 420), "pH": (6.0, 7.7), "MO": (1.2, 26)},
                "op_range": (0.07, 3),
            },
        },
        "legumes_racines": {
            "n": 11, "mediane": 5.5e-3, "min": 8.0e-4, "max": 4.8e-2,
            "regression": {
                "intercept": -3.4, "coef_ln_cs": -0.43,
                "n": 11, "r2": 0.18, "significatif": False,
                "domaine": {"Cs": (10, 420)}, "op_range": (0.2, 11),
            },
        },
        "tubercules": {
            "n": 11, "mediane": 1.1e-3, "min": 8.6e-4, "max": 5.5e-3,
            "regression": None,
        },
        "cereales":  {"source_categorie": "legumes_fruits"},
        "fourrage":  {"source_categorie": "legumes_feuilles"},
    },

    "Cd": {
        "legumes_feuilles": {
            "n": 86, "mediane": 1.6, "min": 1.3e-1, "max": 21,
            "regression": {
                "intercept": 5.1, "coef_ln_cs": -0.11, "coef_ph": -0.63, "coef_mo": -0.18,
                "n": 47, "r2": 0.47, "significatif": True,
                "domaine": {"Cs": (0.09, 38), "pH": (4.8, 8.9), "MO": (0.2, 10)},
                "op_range": (0.1, 6),
            },
        },
        "legumes_fruits": {
            "n": 50, "mediane": 2.3e-1, "min": 1.3e-2, "max": 2.0,
            "regression": {
                "intercept": -0.87, "coef_ln_cs": 0.2, "coef_mo": -0.24,
                "n": 38, "r2": 0.3, "significatif": True,
                "domaine": {"Cs": (0.2, 38), "MO": (0.2, 11)}, "op_range": (0.1, 13),
            },
        },
        "legumes_racines": {
            "n": 36, "mediane": 7.4e-1, "min": 1.7e-1, "max": 4.6,
            "regression": {
                "intercept": 8.0, "coef_ln_cs": 0.18, "coef_ph": -1.2, "coef_mo": -0.19,
                "n": 11, "r2": 0.78, "significatif": True,
                "domaine": {"Cs": (0.19, 4.1), "pH": (4.9, 7.3), "MO": (0.2, 10)},
                "op_range": (0.4, 2),
            },
        },
        "tubercules": {
            "n": 11, "mediane": 3.0e-1, "min": 1.2e-1, "max": 1.3,
            "regression": {
                "intercept": 0.92, "coef_ln_cs": -0.46, "coef_ph": -0.43, "coef_mo": 0.13,
                "n": 8, "r2": 0.88, "significatif": True,
                "domaine": {"Cs": (0.19, 1.3), "pH": (4.9, 7.3), "MO": (1.6, 5.7)},
                "op_range": (0.8, 1.3),
            },
        },
        "cereales": {"n": 15, "mediane": 0.12, "min": 4.0e-2, "max": 4.0e-1, "regression": None},
        "fourrage": {"n": 29, "mediane": 0.40, "min": 1.6e-2, "max": 1.2, "regression": None},
    },

    "Cr": {
        "legumes_feuilles": {
            "n": 11, "mediane": 3.3e-2, "min": 2.2e-4, "max": 2.7,
            "regression": {
                "intercept": -5.3, "coef_mo": 0.25,
                "n": 10, "r2": 0.33, "significatif": False,
                "domaine": {"MO": (1.1, 25)}, "op_range": (0.03, 53),
            },
        },
        "legumes_fruits": {
            "n": 14, "mediane": 1.1e-1, "min": 1.2e-3, "max": 1.0,
            "regression": None,
        },
        "legumes_racines": {
            "n": 24, "mediane": 1.4e-2, "min": 9.1e-4, "max": 1.3,
            "regression": {
                "intercept": -13.5, "coef_ph": 1.5,
                "n": 10, "r2": 0.49, "significatif": True,
                "domaine": {"pH": (5.4, 8.6)}, "op_range": (0.06, 10),
            },
        },
        "tubercules": {
            "n": 21, "mediane": 6.6e-3, "min": 5.8e-4, "max": 4.6e-2,
            "regression": {
                "intercept": -4.1, "coef_ln_cs": -1.5, "coef_ph": 0.58,
                "n": 12, "r2": 0.87, "significatif": True,
                "domaine": {"Cs": (10, 50), "pH": (6.5, 8.4)}, "op_range": (0.4, 1.4),
            },
        },
        "cereales": {"source_categorie": "legumes_fruits"},
        "fourrage": {"source_categorie": "legumes_feuilles"},
    },

    # Mercure : aucune régression publiée (sol-plante) - médiane/intervalle
    # seulement. Tubercules/céréales/fourrage : sources hétérogènes
    # (US EPA 1997, Mosbaek et al. 1988), pas de médiane fournie.
    "Hg": {
        "legumes_feuilles": {"n": 24, "mediane": 4.0e-2, "min": 1.4e-2, "max": 3.2e-1, "regression": None},
        "legumes_fruits":   {"n": 22, "mediane": 1.7e-2, "min": 1.8e-3, "max": 6.2e-2, "regression": None},
        "legumes_racines":  {"n": 15, "mediane": 4.4e-2, "min": None,   "max": None,   "regression": None},
        "tubercules": {"n": None, "mediane": None, "min": 0.05,  "max": 0.2,   "regression": None},
        "cereales":   {"n": None, "mediane": None, "min": 4e-4,  "max": 6e-2,  "regression": None},
        "fourrage":   {"n": None, "mediane": None, "min": 3e-3,  "max": 5e-2,  "regression": None},
    },

    "Ni": {
        "legumes_feuilles": {"n": 25, "mediane": 2.8e-2, "min": 3.2e-3, "max": 4.1e-1, "regression": None},
        "legumes_fruits": {
            "n": 20, "mediane": 1.4e-1, "min": 1.5e-2, "max": 1.0,
            "regression": {
                "intercept": 5.9, "coef_ph": -1.3, "ph_log": True,
                "n": 11, "r2": 0.31, "significatif": False,
                "domaine": {"pH": (6.0, 7.1)}, "op_range": (0.3, 5),
            },
        },
        "legumes_racines": {"n": 32, "mediane": 4.0e-2, "min": 8.8e-3, "max": 1.3, "regression": None},
        "tubercules": {
            "n": 11, "mediane": 2.5e-2, "min": 8.6e-3, "max": 7.3e-1,
            "regression": {
                "intercept": 7.8, "coef_ln_cs": -3.6,
                "n": 11, "r2": 0.57, "significatif": True,
                "domaine": {"Cs": (15, 35)}, "op_range": (0.2, 5),
            },
        },
        "cereales": {"n": 24, "mediane": 5.0e-3, "min": 1.8e-3, "max": 1.4e-2, "regression": None},
        "fourrage": {"n": 29, "mediane": 3.4e-2, "min": 5.6e-3, "max": 2.8e-1, "regression": None},
    },

    "Pb": {
        "legumes_feuilles": {
            "n": 67, "mediane": 1.7e-2, "min": 3.5e-4, "max": 1.4,
            "regression": {
                "intercept": -1.5, "coef_ln_cs": -0.3, "coef_mo": -0.27,
                "n": 48, "r2": 0.24, "significatif": True,
                "domaine": {"Cs": (20, 2700), "MO": (0.2, 15)}, "op_range": (0.03, 90),
            },
        },
        "legumes_fruits": {
            "n": 47, "mediane": 1.3e-2, "min": 4.7e-4, "max": 1.8,
            "regression": {
                "intercept": -25.0, "coef_ln_cs": -0.65, "coef_ph": 3.9, "coef_mo": -0.27,
                "n": 17, "r2": 0.59, "significatif": True,
                "domaine": {"Cs": (20, 2700), "pH": (5.6, 7.0), "MO": (0.2, 10)},
                "op_range": (0.06, 17),
            },
        },
        "legumes_racines": {
            "n": 32, "mediane": 3.6e-2, "min": 1.5e-3, "max": 4.0e-1,
            "regression": {
                "intercept": 0.33, "coef_ln_cs": -0.40, "coef_mo": -0.83,
                "n": 16, "r2": 0.81, "significatif": True,
                "domaine": {"Cs": (20, 2700), "MO": (0.2, 6)}, "op_range": (0.2, 5),
            },
        },
        "tubercules": {
            "n": 21, "mediane": 2.4e-2, "min": 6.0e-4, "max": 2.1e-1,
            "regression": {
                "intercept": -11.6, "coef_ln_cs": 0.76, "coef_ph": 0.96, "coef_mo": -2.2e-2,
                "n": 16, "r2": 0.88, "significatif": True,
                "domaine": {"Cs": (5, 42), "pH": (4.3, 6.1), "MO": (2.5, 74)},
                "op_range": (0.5, 2),
            },
        },
        "cereales": {"n": 13, "mediane": 1.0e-3, "min": 3.3e-4, "max": 4.7e-3, "regression": None},
        "fourrage": {"n": 19, "mediane": 1.0e-2, "min": 3.3e-3, "max": 1.7e-2, "regression": None},
    },

    "Se": {
        "legumes_feuilles": {"n": 19, "mediane": 1.0e-1, "min": 4.7e-2, "max": 2.7e-1, "regression": None},
        "legumes_fruits":   {"n": 19, "mediane": 3.4e-2, "min": 6.7e-3, "max": 1.7e-1, "regression": None},
        "legumes_racines": {
            "n": 13, "mediane": 1.6e-1, "min": 2.0e-2, "max": 9.2e-1,
            "regression": {
                "intercept": -3.0, "coef_ln_cs": -0.67,
                "n": 13, "r2": 0.14, "significatif": False,
                "domaine": {"Cs": (0.04, 0.39)}, "op_range": (0.1, 6),
            },
        },
        "tubercules": {"source_categorie": "legumes_racines"},
        "cereales":   {"source_categorie": "legumes_fruits"},
        "fourrage":   {"source_categorie": "legumes_feuilles"},
    },

    # Vanadium : aucune distribution ajustée (données trop rares) - simple
    # intervalle + valeur ponctuelle, pas de régression.
    "V": {
        "legumes_feuilles": {"n": None, "mediane": 3e-3, "min": 2e-3, "max": 6e-3, "regression": None},
        "legumes_fruits":   {"n": None, "mediane": 1e-4, "min": 1e-4, "max": 3e-3, "regression": None},
        "legumes_racines":  {"n": None, "mediane": 1e-3, "min": 1e-3, "max": 3e-3, "regression": None},
        "tubercules": {"source_categorie": "legumes_racines"},
        "cereales":   {"source_categorie": "legumes_fruits"},
        "fourrage":   {"source_categorie": "legumes_feuilles"},
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Bf - air -> plante (m3 d'air / kg frais de végétal) - Tableau 5, mercure uniquement
# ═══════════════════════════════════════════════════════════════════════════════

BF_HG_PAR_CATEGORIE = {
    "legumes_feuilles": {"n": 6, "min": 1500, "max": 3000, "mediane": None},
    "legumes_racines":  {"n": 3, "min": 1000, "max": 2300, "mediane": None},
    "fourrage":         {"n": 6, "min": 900,  "max": 4100, "mediane": None},
    "legumes_fruits":   {"source_categorie": "legumes_racines"},
    "tubercules":       {"source_categorie": "legumes_racines"},
    "cereales":         {"n": None, "min": 70, "max": 200, "mediane": None},
}


def resolve_categorie(etm_dict: dict, categorie: str) -> dict:
    """Suit les substitutions ('source_categorie') jusqu'à une entrée réelle."""
    entry = etm_dict.get(categorie)
    seen = set()
    while entry is not None and "source_categorie" in entry and categorie not in seen:
        seen.add(categorie)
        categorie = entry["source_categorie"]
        entry = etm_dict.get(categorie)
    return entry
