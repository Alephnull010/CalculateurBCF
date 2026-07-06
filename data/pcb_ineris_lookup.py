# -*- coding: utf-8 -*-
"""
Facteurs de bioconcentration sol-plante (Br) et air gazeux-plante (Bf) pour les
PCDD/F (dioxines/furannes) et PCB, publiés directement par INERIS.

Source : INERIS-DRC-16-159776-09593A (26/06/2017), "Paramètres de transfert des
polychlorodibenzodioxines, polychlorodibenzofurannes et des polychlorobiphényles,
utilisés pour l'évaluation de l'exposition - Application dans le logiciel MODUL'ERS".
https://www.ineris.fr/sites/ineris.fr/files/contribution/Documents/rapport-ineris-drc-16-159776-09593a-pcb-pcddf9-fl-rbn-1502451900.pdf

Tableaux 1-6 (Br, sol-plante, kg sec.kg-1) : tubercules, légumes-racines,
légumes-feuilles, légumes-fruits et fruits (hors Cucurbita), Cucurbita, fourrage.
Tableaux 7-9 (Bf, air gazeux-plante, m3.kg frais-1) : fourrage, légumes-feuilles,
légumes-fruits et fruits.

Ces valeurs sont directement issues du projet TROPHé (INERIS/ADEME) et déjà
validées/publiées par INERIS pour MODUL'ERS - contrairement à data/pcb.py qui
recalcule sa propre régression OLS sur les données brutes BAPPOP. Les deux
sources partagent la même origine (TROPHé) mais celle-ci est la version
officiellement retenue par INERIS.

Format par tableau : dict {clé_substance: (min, max, valeur_ponctuelle)}.
`None` = valeur non déterminée/non fournie par le rapport (pas "zéro").
Valeurs "censurées" (préfixées "<" dans le rapport, ex: "< 1,3") sont stockées
telles quelles (le nombre donné), sans distinction du caractère censuré.
Les colonnes "Nb de données du projet TROPHé" (traçabilité des mesures) ne sont
pas reprises ici - se référer au rapport source si besoin d'audit fin.
"""

# --- Substances : (clé, nom complet, famille, numéro PCB ou None, sigle d'affichage) ---
SUBSTANCES = [
    ("2378-tcdd",      "2,3,7,8-Tétrachlorodibenzodioxine",        "Dioxine", None, "2,3,7,8-TCDD"),
    ("12378-pecdd",    "1,2,3,7,8-Pentachlorodibenzodioxine",      "Dioxine", None, "1,2,3,7,8-PeCDD"),
    ("123478-hxcdd",   "1,2,3,4,7,8-Hexachlorodibenzodioxine",     "Dioxine", None, "1,2,3,4,7,8-HxCDD"),
    ("123678-hxcdd",   "1,2,3,6,7,8-Hexachlorodibenzodioxine",     "Dioxine", None, "1,2,3,6,7,8-HxCDD"),
    ("123789-hxcdd",   "1,2,3,7,8,9-Hexachlorodibenzodioxine",     "Dioxine", None, "1,2,3,7,8,9-HxCDD"),
    ("1234678-hpcdd",  "1,2,3,4,6,7,8-Heptachlorodibenzodioxine",  "Dioxine", None, "1,2,3,4,6,7,8-HpCDD"),
    ("ocdd",           "Octachlorodibenzodioxine",                  "Dioxine", None, "OCDD"),
    ("2378-tcdf",      "2,3,7,8-Tétrachlorodibenzofuranne",        "Furanne", None, "2,3,7,8-TCDF"),
    ("12378-pecdf",    "1,2,3,7,8-Pentachlorodibenzofuranne",      "Furanne", None, "1,2,3,7,8-PeCDF"),
    ("23478-pecdf",    "2,3,4,7,8-Pentachlorodibenzofuranne",      "Furanne", None, "2,3,4,7,8-PeCDF"),
    ("123478-hxcdf",   "1,2,3,4,7,8-Hexachlorodibenzofuranne",     "Furanne", None, "1,2,3,4,7,8-HxCDF"),
    ("123678-hxcdf",   "1,2,3,6,7,8-Hexachlorodibenzofuranne",     "Furanne", None, "1,2,3,6,7,8-HxCDF"),
    ("123789-hxcdf",   "1,2,3,7,8,9-Hexachlorodibenzofuranne",     "Furanne", None, "1,2,3,7,8,9-HxCDF"),
    ("234678-hxcdf",   "2,3,4,6,7,8-Hexachlorodibenzofuranne",     "Furanne", None, "2,3,4,6,7,8-HxCDF"),
    ("1234789-hpcdf",  "1,2,3,4,7,8,9-Heptachlorodibenzofuranne",  "Furanne", None, "1,2,3,4,7,8,9-HpCDF"),
    ("1234678-hpcdf",  "1,2,3,4,6,7,8-Heptachlorodibenzofuranne",  "Furanne", None, "1,2,3,4,6,7,8-HpCDF"),
    ("ocdf",           "Octachlorodibenzofuranne",                  "Furanne", None, "OCDF"),
    ("pcb28",  "2,4,4'-Trichlorobiphényle (28)",           "PCB", 28,  "PCB28"),
    ("pcb52",  "2,2',5,5'-Tétrachlorobiphényle (52)",      "PCB", 52,  "PCB52"),
    ("pcb77",  "3,3',4,4'-Tétrachlorobiphényle (77)",      "PCB", 77,  "PCB77"),
    ("pcb81",  "3,4,4',5-Tétrachlorobiphényle (81)",       "PCB", 81,  "PCB81"),
    ("pcb101", "2,2',4,5,5'-Pentachlorobiphényle (101)",   "PCB", 101, "PCB101"),
    ("pcb105", "2,3,3',4,4'-Pentachlorobiphényle (105)",   "PCB", 105, "PCB105"),
    ("pcb114", "2,3,4,4',5-Pentachlorobiphényle (114)",    "PCB", 114, "PCB114"),
    ("pcb118", "2,3',4,4',5-Pentachlorobiphényle (118)",   "PCB", 118, "PCB118"),
    ("pcb126", "3,3',4,4',5-Pentachlorobiphényle (126)",   "PCB", 126, "PCB126"),
    ("pcb138", "2,2',3,4,4',5'-Hexachlorobiphényle (138)", "PCB", 138, "PCB138"),
    ("pcb153", "2,2',4,4',5,5'-Hexachlorobiphényle (153)", "PCB", 153, "PCB153"),
    ("pcb156", "2,3,3',4,4',5-Hexachlorobiphényle (156)",  "PCB", 156, "PCB156"),
    ("pcb157", "2,3,3',4,4',5'-Hexachlorobiphényle (157)", "PCB", 157, "PCB157"),
    ("pcb167", "2,3',4,4',5,5'-Hexachlorobiphényle (167)", "PCB", 167, "PCB167"),
    ("pcb169", "3,3',4,4',5,5'-Hexachlorobiphényle (169)", "PCB", 169, "PCB169"),
    ("pcb180", "2,2',3,4,4',5,5'-Heptachlorobiphényle (180)", "PCB", 180, "PCB180"),
    ("pcb189", "2,3,3',4,4',5,5'-Heptachlorobiphényle (189)", "PCB", 189, "PCB189"),
]
_KEYS = [s[0] for s in SUBSTANCES]


def _table(*rows):
    """Associe chaque ligne (min, max, point) à la clé de substance correspondante (même ordre que SUBSTANCES)."""
    assert len(rows) == len(_KEYS), f"{len(rows)} lignes fournies, {len(_KEYS)} attendues"
    return dict(zip(_KEYS, rows))


# ═══════════════════════════════════════════════════════════════════════════════
# Br - sol -> plante (kg sec.kg-1) - Tableaux 1 à 6
# ═══════════════════════════════════════════════════════════════════════════════

BR_TUBERCULES = _table(
    (1.1e-2, 2.3e-2, 8.7e-3), (6.0e-3, 2.9e-2, 8.4e-3), (4.6e-3, 2.7e-2, 6.8e-3),
    (4.6e-3, 2.9e-2, 7.5e-3), (1.8e-3, 1.4e-2, 4.8e-3), (1.7e-3, 1.5e-2, 4.1e-3),
    (1.1e-3, 7.3e-3, 2.8e-3),
    (1.9e-2, 7.0e-2, 2.2e-2), (1.4e-2, 4.2e-2, 1.6e-2), (8.3e-3, 4.3e-2, 1.1e-2),
    (6.3e-3, 3.9e-2, 9.1e-3), (5.0e-3, 2.3e-2, 7.7e-3), (3.3e-3, 3.9e-2, 8.0e-3),
    (3.3e-3, 1.8e-2, 7.1e-3), (5.2e-4, 2.5e-3, 8.8e-4), (9.9e-3, 8.1e-2, 2.5e-2),
    (1.3e-3, 6.1e-3, 3.4e-3),
    (0, 2.5e-1, 1.2e-1), (0, 4.0e-1, 1.4e-1), (1.9e-2, 4.6e-2, 2.1e-2),
    (1.1e-2, 6.0e-2, 2.3e-2), (3.4e-2, 3.0e-1, 7.2e-2), (3.2e-2, 1.1e-1, 3.5e-2),
    (3.3e-2, 6.9e-2, 4.8e-2), (2.9e-2, 1.4e-1, 3.4e-2), (1.9e-2, 1.5e-1, 2.3e-2),
    (1.2e-2, 1.5e-1, 9.1e-2), (1.4e-2, 2.3e-1, 1.1e-1), (2.9e-2, 8.7e-2, 4.8e-2),
    (3.0e-2, 1.3e-1, 4.8e-2), (3.1e-2, 1.2e-1, 5.9e-2), (2.2e-2, 5.3e-2, 5.9e-2),
    (2.1e-2, 8.3e-2, 5.6e-2), (1.6e-2, 9.9e-2, 3.0e-2),
)

BR_LEGUMES_RACINES = _table(
    (4.0e-3, 4.2e-2, None), (4.9e-3, 1.3e-1, 1.1e-2), (4.8e-3, 1.2e-1, 9.7e-3),
    (4.8e-3, 1.1e-1, 1.1e-2), (3.3e-3, 8.2e-2, None), (8.7e-4, 5.4e-2, 4.7e-3),
    (0, 3.4e-2, None),
    (2.4e-3, 1.9e-1, 4.4e-2), (1.6e-3, 1.5e-1, 2.6e-2), (7.8e-4, 1.6e-1, 1.5e-2),
    (7.1e-4, 1.0e-1, 1.4e-2), (1.9e-3, 1.1e-1, 1.0e-2), (7.1e-4, 1.1e-1, 1.0e-2),
    (1.1e-3, 9.4e-2, 7.1e-3), (2.7e-4, 1.3e-2, 1.5e-3), (1.7e-3, 2.4e-1, 2.9e-2),
    (3.3e-4, 3.6e-2, 4.5e-3),
    (0, 4.2e-1, None), (0, 3.8, 7.4e-1), (1.7e-2, 5.0e-1, 2.3e-2),
    (1.7e-2, 1.7e-1, None), (0, 6.0e-1, 3.2e-1), (1.1e-2, 2.7e-1, 3.5e-2),
    (3.8e-2, 1.9e-1, 7.0e-2), (3.0e-3, 3.3e-1, 3.6e-2), (4.4e-3, 2.3e-1, 2.5e-2),
    (1.0e-2, 5.9e-1, 8.5e-2), (2.9e-2, 7.4e-1, 1.3e-1), (7.6e-3, 3.7e-1, 5.4e-2),
    (7.4e-3, 3.4e-1, 4.1e-2), (8.7e-3, 4.0e-1, 6.0e-2), (0, 2.8e-1, 2.8e-1),
    (1.5e-2, 3.3, 6.6e-2), (5.2e-3, 2.6e-1, 3.8e-2),
)

BR_LEGUMES_FEUILLES = _table(
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (1.9e-3, 2.6e-3, None), (0, 0, 0),
    (3.8e-3, 2.3e-2, 4.9e-3), (2.0e-3, 8.5e-2, 2.4e-3), (1.6e-3, 9.0e-2, 1.6e-3),
    (1.2e-3, 9.4e-3, 1.5e-3), (1.1e-3, 3.1e-3, 2.1e-3), (8.5e-4, 9.4e-3, 1.6e-3),
    (8.5e-4, 1.1e-3, 1.3e-3), (1.6e-4, 9.7e-4, 5.6e-4), (9.7e-4, 1.0e-1, 3.9e-3),
    (3.7e-4, 5.6e-2, 1.0e-2),
    (0, 5.9, 0), (0, 35, 0), (4.7e-2, 7.3e-1, 3.0e-1),
    (7.5e-2, 1.1e-1, None), (4.3e-2, 5.3, 5.9e-2), (9.4e-2, 2.7, 2.2e-1),
    (1.7e-1, 8.4, 2.1e-1), (7.2e-2, 4.6, 1.8e-1), (6.3e-3, 2.3e-2, 1.2e-2),
    (2.0e-2, 1.2e-1, 3.4e-2), (4.4e-2, 1.1e-1, 5.0e-2), (1.9e-2, 3.4e-1, 2.6e-2),
    (2.2e-2, 6.6e-1, 3.1e-2), (2.0e-2, 2.7e-1, 2.8e-2), (0, 1.3, 0),
    (None, 1.2e-1, 3.7e-2), (8.6e-3, 7.5e-2, 1.8e-2),
)

BR_LEGUMES_FRUITS_ET_FRUITS = _table(
    (0, 4.1e-2, None), (0, 2.3e-3, None), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (0, 5.5e-3, None), (0, 0, 0),
    (0, 2.9e-3, None), (0, 1.3e-3, None), (0, 0, 0), (0, 2.1e-4, None),
    (0, 2.1e-4, None), (0, 2.1e-4, None), (0, 2.1e-4, None), (0, 1.2e-4, None),
    (0, 1.2e-4, None), (0, 6.1e-5, None),
    (0, 0, 0), (0, 1.6, 5.7e-2), (0, 1.4e-2, None), (0, 0, 0),
    (0, 7.4e-2, None), (0, 4.7e-1, 0), (0, 1.4e-1, 2.1e-2), (0, 7.7e-1, 2.0e-4),
    (0, 1.1e-2, None), (0, 0, 0), (0, 0, 0), (0, 5.4e-3, None),
    (0, 4.5e-3, None), (0, 6.7e-3, None), (0, 0, 0), (0, 0, 0), (0, 0, 0),
)

BR_CUCURBITA = _table(
    (3.5e-2, 2.7e-1, None), (3.2e-2, 1.5, 6.3e-2), (3.1e-2, 1.7, 6.4e-2),
    (1.6e-2, 9.2e-1, 3.4e-2), (8.7e-3, 1.8e-1, 2.5e-2), (3.2e-3, 3.2e-1, 1.4e-2),
    (0, 1.9e-4, None),
    (4.5e-2, 1.3, 1.1e-1), (4.9e-2, 1.4, 1.1e-1), (3.1e-2, 1.2, 8.2e-2),
    (3.8e-2, 1.3, 1.0e-1), (1.6e-2, 6.8e-1, 4.3e-2), (1.0e-3, 1.3, 5.5e-2),
    (9.1e-3, 5.0e-1, 2.3e-2), (1.0e-3, 5.2e-2, 2.9e-3), (1.5e-2, 1.2, 7.7e-2),
    (9.2e-4, 4.9e-2, 3.4e-3),
    (0, 11, None), (8.0e-1, 35, 9.3), (7.3e-2, 1.4, 1.7e-1), (0, 1.4e-1, 1.4e-1),
    (3.7e-1, 16, 6.2), (2.5e-1, 7.4, 1.9), (3.6e-1, 13, 4.0e-1), (2.4e-1, 9.0, 2.5),
    (7.8e-3, 2.4e-1, 9.8e-2), (2.8e-1, 8.1, 5.2), (1.9e-1, 11, 7.8),
    (2.5e-1, 6.7, 3.2), (1.6e-1, 6.7, 2.8), (2.0e-1, 6.0, 2.8), (0, 1.3, 0),
    (8.6e-2, 4.7, 2.9), (5.8e-2, 2.7, 9.7e-1),
)

BR_FOURRAGE = _table(
    (0, 7.9e-2, 0), (0, 4.4e-2, 0), (0, 7.5e-2, 0), (0, 3.3e-2, 0),
    (0, 4.8e-2, 0), (0, 8.4e-2, 1.2e-4), (0, 1.1e-2, 0),
    (0, 4.3e-1, 7.8e-3), (0, 2.8e-1, 2.2e-3), (0, 1.6e-1, 8.9e-4),
    (0, 1.1e-1, 4.3e-4), (0, 1.3e-1, 3.7e-4), (0, 1.3e-1, None),
    (0, 6.6e-2, 1.1e-4), (0, 2.8e-2, 6.9e-6), (0, 2.5e-1, 3.3e-4), (0, 3.1e-2, 0),
    (0, 5.5, 0), (0, 14, 0), (2.0e-2, 3.6, 2.0e-2), (0, 1.5, 0),
    (3.3e-1, 12, 0), (0, 7.1, 0), (0, 22, 0), (0, 9.9, 0),
    (7.3e-3, 7.9e-1, 7.3e-3), (3.2e-3, 1.1, 3.2e-3), (3.0e-3, 1.3, 3.0e-3),
    (7.4e-3, 6.4e-1, 7.4e-3), (1.4e-2, 5.7e-1, 1.4e-2), (1.4e-2, 4.9e-1, 1.4e-2),
    (0, 0.14, 0), (1.2e-2, 1.0, 1.2e-2), (5.7e-3, 3.2e-1, 5.7e-3),
)

# Céréales : valeur ponctuelle = 0 pour tous les congénères (règle explicite du
# rapport §2.3.6 - transfert jugé nul, grain protégé par une enveloppe).
BR_CEREALES = {k: (None, None, 0.0) for k in _KEYS}

# Ensilage herbe : identique au fourrage (§2.3.7).
BR_ENSILAGE_HERBE = dict(BR_FOURRAGE)

# Ensilage maïs : min/ponctuelle = fourrage / 2, max = fourrage (§2.3.7,
# grain ~50% de la MS de la plante entière, contamination du grain jugée nulle).
def _ensilage_mais(fourrage):
    out = {}
    for k, (mn, mx, pt) in fourrage.items():
        out[k] = (
            mn / 2 if mn is not None else None,
            mx,
            pt / 2 if pt is not None else None,
        )
    return out


BR_ENSILAGE_MAIS = _ensilage_mais(BR_FOURRAGE)


# ═══════════════════════════════════════════════════════════════════════════════
# Bf - air gazeux -> plante (m3.kg frais-1) - Tableaux 7 à 9
# ═══════════════════════════════════════════════════════════════════════════════

BF_FOURRAGE = _table(
    (5.0e3, 2.4e4, 1.0e4), (6.2e3, 5.9e4, 3.0e4), (4.8e3, 1.1e5, 6.6e4),
    (4.8e3, 1.5e5, 6.6e4), (4.8e3, 6.9e4, 6.6e4), (6.5e3, 2.7e5, 1.1e5),
    (1.9e4, 4.3e6, 3.0e5),
    (3.6e3, 1.3e4, 6.0e3), (3.1e3, 3.0e4, 1.2e4), (3.1e3, 1.2e4, 1.2e4),
    (3.5e3, 3.8e4, 2.0e4), (3.5e3, 5.0e4, 2.0e4), (3.5e3, 1.6e5, 2.0e4),
    (3.5e3, 7.3e4, 2.0e4), (1.1e4, 1.0e5, 1.0e5), (1.1e4, 2.1e5, 1.0e5),
    (9.7e3, 3.3e6, 2.9e5),
    (3.8e2, 2.2e3, 7.5e2), (3.6e2, 2.1e3, 1.0e3), (2.0e3, 8.5e3, 2.0e3),
    (6.2e2, 5.0e3, None), (6.6e2, 1.3e4, 2.0e3), (2.2e3, 3.1e4, 5.6e3),
    (1.1e3, 1.3e4, None), (1.7e3, 2.7e4, 4.5e3), (2.9e3, 2.1e4, None),
    (2.4e3, 1.3e4, 4.8e3), (1.1e3, 9.7e3, 3.4e3), (4.4e3, 2.8e4, 5.1e3),
    (4.6e3, 3.5e4, 6.1e3), (4.3e3, 2.6e4, 4.9e3), (3.3e3, 2.2e4, 7.5e3),
    (2.2e3, 2.1e4, 9.2e3), (4.6e2, 6.0e4, 9.4e3),
)

BF_LEGUMES_FEUILLES = _table(
    (5.0e2, 2.4e3, 1.0e3), (6.2e2, 5.9e3, 3.0e3), (4.8e2, 1.1e4, 6.6e3),
    (4.8e2, 1.5e4, 6.6e3), (4.8e2, 6.9e3, 6.6e3), (6.5e2, 2.7e4, 1.1e4),
    (1.9e3, 4.3e5, 3.0e4),
    (1.0e2, 1.3e3, 6.0e2), (6.7e1, 3.0e3, 1.2e3), (1.4e2, 1.2e3, 1.2e3),
    (1.1e2, 3.8e3, 2.0e3), (3.5e2, 5.0e3, 2.0e3), (3.5e2, 1.6e4, 2.0e3),
    (3.5e2, 7.3e3, 2.0e3), (1.1e3, 1.0e4, 1.0e4), (1.2e2, 2.1e4, 1.0e4),
    (9.7e2, 3.3e5, 2.9e4),
    (1.3e2, 2.4e2, 1.9e2), (1.5e2, 1.5e3, 2.9e2), (0, 8.5e2, None),
    (6.2e1, 5.0e2, None), (4.8e2, 1.9e3, 1.6e3), (8.7e2, 3.6e3, 2.6e3),
    (1.1e2, 2.3e3, None), (8.2e2, 3.0e3, 2.4e3), (0, 2.1e3, None),
    (2.4e2, 5.8e3, None), (1.1e2, 3.5e3, None), (4.2e2, 2.8e3, None),
    (4.6e2, 3.5e3, None), (4.3e2, 2.6e3, None), (3.3e2, 2.2e3, None),
    (2.2e2, 5.0e3, None), (2.5e1, 6.0e3, None),
)

BF_LEGUMES_FRUITS_ET_FRUITS = _table(
    (5.0e1, 1.2e3, None), (6.2e1, 2.9e3, None), (4.8e1, 5.4e3, None),
    (4.8e1, 7.5e3, None), (4.8e1, 3.4e3, None), (6.5e1, 1.3e4, None),
    (1.9e2, 2.1e5, None),
    (3.6e1, 6.4e2, None), (3.1e1, 1.5e3, None), (3.1e1, 6.1e2, None),
    (3.5e1, 1.9e3, None), (3.5e1, 2.5e3, None), (3.5e1, 8.1e3, None),
    (3.5e1, 3.6e3, None), (1.1e2, 5.0e3, None), (1.1e2, 1.0e4, None),
    (9.7e1, 1.6e5, None),
    (4, 1.1e2, None), (6.9e1, 9.5e1, 7.9e1), (2.0e1, 4.3e2, None),
    (6, 2.5e2, None), (7, 6.7e2, None), (3.6e2, 1.1e3, 7.2e2),
    (1.1e1, 6.4e2, None), (3.6e2, 1.1e3, 7.3e2), (2.9e1, 1.1e3, None),
    (2.4e1, 6.5e2, None), (1.1e1, 4.9e2, None), (4.4e1, 1.4e3, None),
    (4.6e1, 1.7e3, None), (4.3e1, 1.3e3, None), (3.3e1, 1.1e3, None),
    (2.2e1, 1.1e3, None), (5, 3.0e3, None),
)

# Tubercules : Bf considéré comme nul pour tous les congénères (§2.4.4 - ordonnée
# à l'origine des droites de régression sol-tubercule nulle ou proche de 0).
BF_TUBERCULES = {k: (None, None, 0.0) for k in _KEYS}

# Légumes-racines : le rapport indique explicitement qu'il est "difficile et
# prématuré" de définir des valeurs de Bf air-gazeux (§2.4.5) - non déterminé,
# à ne pas confondre avec une valeur nulle.
BF_LEGUMES_RACINES = {k: (None, None, None) for k in _KEYS}

# Céréales : Bf considéré comme nul (§2.4.6 - grain protégé).
BF_CEREALES = {k: (None, None, 0.0) for k in _KEYS}

# Ensilage herbe : identique au fourrage (§2.4.7).
BF_ENSILAGE_HERBE = dict(BF_FOURRAGE)

# Ensilage maïs : même règle que pour Br (§2.4.7).
BF_ENSILAGE_MAIS = _ensilage_mais(BF_FOURRAGE)

# Cucurbita : aucune valeur de Bf n'est publiée dans le rapport (le texte indique
# seulement que l'apport par l'air y est "beaucoup plus faible que celui lié au
# sol", sans chiffrer de Bf dédié) - non déterminé.
BF_CUCURBITA = {k: (None, None, None) for k in _KEYS}


# ═══════════════════════════════════════════════════════════════════════════════
# Regroupement par catégorie végétale (clés alignées sur data/vegetaux.py::VEGETAUX_PCB)
# ═══════════════════════════════════════════════════════════════════════════════

BR_PAR_CATEGORIE = {
    "tubercules":       BR_TUBERCULES,
    "legumes_racines":  BR_LEGUMES_RACINES,
    "legumes_feuilles": BR_LEGUMES_FEUILLES,
    "legumes_fruits":   BR_LEGUMES_FRUITS_ET_FRUITS,
    "cucurbita":        BR_CUCURBITA,
    "fourrage":         BR_FOURRAGE,
    "cereales":         BR_CEREALES,
    "ensilage_herbe":   BR_ENSILAGE_HERBE,
    "ensilage_mais":    BR_ENSILAGE_MAIS,
}

BF_PAR_CATEGORIE = {
    "tubercules":       BF_TUBERCULES,
    "legumes_racines":  BF_LEGUMES_RACINES,
    "legumes_feuilles": BF_LEGUMES_FEUILLES,
    "legumes_fruits":   BF_LEGUMES_FRUITS_ET_FRUITS,
    "cucurbita":        BF_CUCURBITA,
    "fourrage":         BF_FOURRAGE,
    "cereales":         BF_CEREALES,
    "ensilage_herbe":   BF_ENSILAGE_HERBE,
    "ensilage_mais":    BF_ENSILAGE_MAIS,
}
