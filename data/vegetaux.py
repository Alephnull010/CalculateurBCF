VEGETAUX = {
    "légumes_fruits": {
        "organe":             "fruit",
        "lipide":             0.02,    # g lipide/g MS — modèle Trapp (Corn/Leaves)
        "densite":            1.00,    # kg/L — corn density 1000 kg/m³
        "tsp":                0.15,    # teneur MS — water content corn = 0.15 g/g → MS ≈ 0.85, mais ici fraction sèche ~ 0.15
        "evapotranspiration": 0.2,     # L/j — transpiration corn (Plant all)
        "surface_feuille":    1.0,     # m² (Leaf Area corn = 1 m²)
        "exemples": ["tomate", "haricot", "courgette",
                     "aubergine", "concombre", "poivron"],
    },
    "légumes_feuilles": {
        "organe":             "feuille",
        "lipide":             0.02,    # g lipide/g MS — Leaves TGD, Lipid content = 0.02 g/g
        "densite":            0.50,    # kg/L — shoot density = 500 kg/m³ (Plant all)
        "tsp":                0.20,    # fraction MS — water content = 0.8 g/g → MS ≈ 0.2
        "evapotranspiration": 1.0,     # L/j — Transpiration = 1 L/d (Leaves TGD)
        "surface_feuille":    5.0,     # m² — Leaf Area = 5 m² (Leaves TGD & Plant all)
        "exemples": ["laitue", "épinard", "chou",
                     "endive", "chicorée", "fenouil"],
    },
    "légumes_racines": {
        "organe":             "racine",
        "lipide":             0.025,   # kg/kg — Root data Lipid content = 0.025 kg/kg (Plant all)
        "densite":            1.95,    # kg/L — wet density racine ≈ wet density sol = 1.95 (Plant all)
        "tsp":                0.11,    # fraction MS — water content racine = 0.89 L/kg → MS ≈ 1-0.89 = 0.11
        "evapotranspiration": 1.0,     # L/j — Transpiration Q root = 1 L/d
        "surface_feuille":    0.3,     # m² — faible (pas de surface foliaire dominante)
        "exemples": ["carotte", "betterave", "navet", "radis"],
    },
    "tubercules": {
        "organe":             "racine",
        "lipide":             0.001,   # kg/kg — Potato lipid fraction = 0.001 kg/kg (Potato sheet)
        "densite":            1.95,    # kg/L — Potato wet density = 1.95 kg/L (Potato sheet)
        "tsp":                0.222,   # fraction MS — water content potato = 0.778 L/kg → MS ≈ 0.222
        "evapotranspiration": 0.7,     # L/j — pas dans les Excel, valeur conservée
        "surface_feuille":    0.4,     # m²
        "exemples": ["pomme de terre"],
    },
    "fruits": {
        "organe":             "fruit",
        "lipide":             0.02,    # g/g — Fruit tree model, même lipide que feuilles
        "densite":            0.90,    # kg/L — cohérent avec la valeur initiale
        "tsp":                0.15,    # fraction MS — typique fruits charnus
        "evapotranspiration": 0.822,   # L/j — Q transpiration Fruit tree (Fruit tree sheet)
        "surface_feuille":    2.0,     # m² — Leaf Area fruit tree = 2 m²
        "exemples": ["fraisier", "pommier", "poirier", "raisin"],
    },
}

# Catégories végétales pour les PCB (méthodologie INERIS-DRC-16-159776-09593A)
# Structure allégée : pas de propriétés physico-chimiques (inutiles pour le lookup PCB)
VEGETAUX_PCB = {
    "tubercules":      {"organe": "racine",  "exemples": ["pomme de terre"]},
    "legumes_racines": {"organe": "racine",  "exemples": ["carotte", "radis", "betterave"]},
    "legumes_feuilles":{"organe": "feuille", "exemples": ["laitue", "épinard", "chou"]},
    "fourrage":        {"organe": "feuille", "exemples": ["prairie", "herbe", "ray-grass"]},
    "legumes_fruits":  {"organe": "fruit",   "exemples": ["tomate", "haricot", "poivron"]},
    "cucurbita":       {"organe": "fruit",   "exemples": ["courgette", "potiron", "concombre"]},
    "cereales":        {"organe": "graine",  "exemples": ["blé", "maïs grain", "orge"]},
    "ensilage_herbe":  {"organe": "feuille", "exemples": ["ensilage herbe"]},
    "ensilage_mais":   {"organe": "feuille", "exemples": ["ensilage maïs"]},
}