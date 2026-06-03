# Calculateur BCF sol-plante — MODUL'ERS

Calcule le facteur de bioconcentration sol-plante (Br_E) à renseigner dans l'outil MODUL'ERS (INERIS).  
Sortie : `mg/kg_vegsec / (mg/kg_sol)`, exportée dans un fichier Excel par site.

---

## Sommaire

1. [Principe général](#1-principe-général)
2. [Structure du projet](#2-structure-du-projet)
3. [Données d'entrée](#3-données-dentrée)
4. [Sélection du modèle](#4-sélection-du-modèle)
5. [Modèles de calcul](#5-modèles-de-calcul)
6. [Système d'avertissements](#6-système-davertissements)
7. [Utilisation](#7-utilisation)
8. [Format de sortie](#8-format-de-sortie)
9. [Ajouter un site](#9-ajouter-un-site)
10. [Références](#10-références)

---

## 1. Principe général

Pour chaque combinaison `(polluant × végétal)`, le script :

1. charge les paramètres physico-chimiques du polluant et les caractéristiques du végétal ;
2. sélectionne automatiquement le modèle le plus adapté selon l'organe cible et les propriétés du polluant ;
3. calcule le Br_E ;
4. génère des avertissements si le polluant sort du domaine de validité du modèle ;
5. exporte l'ensemble des résultats dans un fichier Excel.

---

## 2. Structure du projet

```
CalculateurBCF/
│
├── main.py                  # Point d'entrée — boucle polluants × végétaux, export Excel
│
├── core/
│   ├── selector.py          # Choix du modèle selon organe, log Kow, H
│   ├── calculator.py        # Orchestration du calcul Br_E
│   └── validator.py         # Warnings post-calcul (domaine de validité, BCF négatif…)
│
├── models/
│   ├── briggs.py            # Briggs et al. (1982) — racines
│   ├── mackay97.py          # Hung & Mackay (1997) — feuilles volatils
│   ├── travis_arms.py       # Travis & Arms (1988) — parties aériennes
│   └── plantx.py            # Trapp & Matthies (1995) — bilan de masse
│
└── data/
    ├── polluants.py         # Base de données polluants (HAP, BTEX, COHV)
    ├── vegetaux.py          # Paramètres des 5 catégories végétales
    ├── sol.py               # Chargement, estimation et validation des paramètres sol
    └── sites/
        ├── site_default.json  # Site de référence (exemple complet)
        └── site_A.json        # Exemple site réel
```

---

## 3. Données d'entrée

### Polluants (`data/polluants.py`)

24 substances réparties en trois familles, issues du Tableau 2 INERIS DRC-05-57281 :

| Famille | Substances |
|---------|-----------|
| HAP | naphtalène, acénaphtylène, acénaphtène, fluorène, phénanthrène, anthracène, fluoranthène, pyrène, benzo(a)anthracène, chrysène, benzo(b)fluoranthène, benzo(k)fluoranthène, benzo(a)pyrène, indéno(1,2,3-cd)pyrène, dibenzo(a,h)anthracène, benzo(g,h,i)pérylène |
| BTEX | benzène, toluène, éthylbenzène, o/m/p-xylène |
| COHV | chloroforme, tétrachloroéthylène |

Chaque polluant est défini par : `log_kow`, `log_koc`, `MW` (g/mol), `Pvap` (Pa), `H` (constante de Henry adimensionnelle).

### Végétaux (`data/vegetaux.py`)

5 catégories, chacune caractérisée par son organe cible et ses paramètres physiologiques :

| Catégorie | Organe | Exemples |
|-----------|--------|---------|
| légumes_fruits | fruit | tomate, haricot, courgette… |
| légumes_feuilles | feuille | laitue, épinard, chou… |
| légumes_racines | racine | carotte, betterave, navet… |
| tubercules | racine | pomme de terre |
| fruits | fruit | fraisier, pommier, vigne… |

Paramètres utilisés par les modèles : `lipide`, `densite`, `evapotranspiration`, `surface_feuille`.

### Sol (`data/sites/site_*.json`)

**Paramètres obligatoires :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `pH` | pH du sol | `8.0` |
| `matiere_organique` | fraction massique (ex: 0.17 = 17 %) | `0.17` |
| `conc_air` | concentration atmosphérique par polluant (µg/m³) | voir JSON |

> **Note — `conc_sol` absente intentionnellement**  
> Br_E est un facteur de transfert (ratio plante/sol) : pour les modèles racine (Briggs, PlantX) et les modèles parties aériennes sans voie atmosphérique (Travis & Arms), la concentration sol se simplifie algébriquement et n'influe pas sur le résultat.  
> Pour les organes aériens avec voie atmosphérique (PlantX feuille/fruit, Mackay_97), c'est `conc_air` qui introduit la dépendance au site — c'est le seul paramètre de concentration nécessaire.  
> `conc_sol` est à renseigner directement dans MODUL'ERS pour obtenir la concentration absolue dans le végétal (`C_plante = Br_E × conc_sol`).

**Paramètres optionnels** (estimés automatiquement si absents) :

| Clé | Description | Défaut si absent |
|-----|-------------|-----------------|
| `pct_argile` | % argile | `None` → Rawls (1983) |
| `pct_limon` | % limon | `None` → Rawls (1983) |
| `temperature` | °C | `17.5` (Météo-France) |

**Paramètres calculés automatiquement par `load_sol()` :**

- `carbone_organique` = MO / 1.72
- `densite` — Manrique & Jones (1991) si argile+limon disponibles, sinon Rawls (1983)
- `fraction_eau` — Saxton & Rawls (2006) si argile disponible, sinon 0.30 (INERIS)
- `fraction_air` = porosité totale − fraction_eau

---

## 4. Sélection du modèle

`core/selector.py` choisit automatiquement le modèle selon l'organe cible, la constante de Henry (H) et le log Kow :

```
organe = racine
    log Kow ≤ 5.0  →  Briggs
    log Kow > 5.0  →  PlantX       (HAP lourds, hors domaine Briggs)

organe = feuille
    H > 0.1                        →  Mackay_97    (voie atmosphérique dominante)
    H ≤ 0.1 et 1 ≤ log Kow ≤ 8    →  Travis_Arms
    sinon                          →  PlantX

organe = fruit
    H > 0.1                        →  PlantX
    H ≤ 0.1 et 1 ≤ log Kow ≤ 8    →  Travis_Arms
    sinon                          →  PlantX
```

---

## 5. Modèles de calcul

### Briggs et al. (1982) — racines, log Kow ≤ 5.0

Régression empirique sur orge hydroponique :

```
log BCF = 0.77 × log Kow − 1.52
```

Domaine de calibration documenté : −0.57 ≤ log Kow ≤ 3.7. Un warning est émis hors de cette plage.  
Ne dépend que du log Kow — les paramètres végétaux ne sont pas utilisés.

**Traitement des limites de validité :**

| Limite | Comportement | Justification |
|--------|-------------|---------------|
| log Kow > 5.0 | Bascule sur PlantX (dans le sélecteur) | Briggs non fiable pour les HAP lourds |
| log Kow < −0.57 | Warning post-calcul uniquement, Briggs maintenu | Composés en dessous de cette limite rares en contexte sites pollués — un avertissement est jugé suffisant |

### Travis & Arms (1988) — parties aériennes

Régression empirique sur végétaux de champ :

    log BCF = 1.588 − 0.578 × log Kow

Domaine de validité : 1.0 ≤ log Kow ≤ 8.0.

**Conditions de sélection :**  
Retenu pour les feuilles et fruits quand H ≤ 0.1 (voie atmosphérique 
négligeable) et log Kow ∈ [1.0 ; 8.0]. Dans ces conditions, la régression 
empirique calibrée sur parties aériennes de végétaux de champ est jugée 
plus adaptée que PlantX, dont la validation expérimentale (INERIS 
DRC-05-57281) porte principalement sur les fruits (tomate, haricot).

**Limites documentées :**  
Prédit les valeurs centrales des observations sans caractère conservatoire 
(McKone & Maddalena, 2007). Non fiable au-delà de log Kow = 8.0.

### Hung & Mackay (1997) — feuilles, composés volatils (H > 0.1)

Modèle fugacité 3 compartiments. Calcule la concentration foliaire à partir de deux voies d'entrée :
- voie racinaire via le flux de transpiration (TSCF) ;
- voie atmosphérique via la conductance foliaire (gA).

Sensible à `conc_air` : utiliser une mesure représentative du site.

**Note sur la voie atmosphérique :**  
Le terme sol `TSCF × Ceau/Csol × Q` est en kg/j (ρb normalisé par Csol) ; le terme air `Cair × gA / H` est converti de mg/j en kg/j (facteur 1e-6) pour homogénéité. Pour des concentrations en air typiques (< 1 000 µg/m³), la voie atmosphérique reste négligeable devant la voie sol dans le calcul du Br_E.

### PlantX — Trapp & Matthies (1995) — bilan de masse

Modèle mécaniste à l'état pseudo-stationnaire. La chaîne de calcul est conditionnée à l'organe cible pour éviter les calculs inutiles :

**Toujours calculés :**
- TSCF (Transpiration Stream Concentration Factor), formule Briggs 1982 uniquement :  
  `TSCF = 0.784 × exp(−(log Kow − 1.78)² / 2.44)`  
  La formule Hsu 1991 (`0.70 × exp(−(log Kow − 3.07)² / 2.78)`) n'est pas retenue. Les deux formules divergent d'environ un ordre de grandeur pour 0 < log Kow < 5 (McKone & Maddalena, LBNL-60273, p.13) ; faute de consensus, l'approche `max(Briggs, Hsu)` n'est pas implémentée.
- BCF_racine via flux de transpiration et TSCF

**Uniquement si feuille ou fruit :**
- BCF_feuille = bilan flux xylème entrant + échange atmosphérique  
  (terme air converti de mg/j en kg/j par ×1e-6 pour homogénéité avec le terme sol)

**Uniquement si fruit :**
- BCF_fruit = bilan flux phloème (depuis feuille) + échange atmosphérique  
  (même conversion ×1e-6 sur le terme air)

---

## 6. Système d'avertissements

`core/validator.py` ajoute des warnings post-calcul dans les cas suivants :

| Condition | Message |
|-----------|---------|
| PlantX + log Kow > 5.0 | Modèle non validé pour les HAP lourds |
| Mackay_97 + organe feuille | BCF sensible à `conc_air` — utiliser une mesure site |
| **PlantX** + organe fruit + exemples hors tomate/haricot | PlantX validé sur tomate/haricot uniquement |
| BCF ≤ 0 | Erreur — vérifier les paramètres d'entrée |

> Le warning fruit est restreint au modèle PlantX : Travis & Arms est une régression empirique générale sur parties aériennes qui ne dépend pas de la validation expérimentale tomate/haricot.

Chaque modèle produit également ses propres warnings de domaine de validité (`briggs_validity`, `travis_arms_validity`).

---

## 7. Utilisation

### Prérequis

```
pip install pandas openpyxl
```

### Lancer le calcul

```bash
# Site par défaut (data/sites/site_default.json)
python main.py

# Site spécifique (data/sites/site_A.json)
python main.py --site A
```

### Résultat console (exemple)

```
----------Chargement paramètres sol : site_default.json

---------- Sol chargé : site_default
   pH               = 8.0
   MO               = 17.0 %
   Corg             = 0.0988
   Densité estimée  = 1.082 kg/dm³
   Fraction eau     = 0.348
   Fraction air     = 0.243
   Température      = 17.5 °C

----------Export : Br_E_default.xlsx
```

---

## 8. Format de sortie

Fichier Excel `Br_E_<site>.xlsx`, une ligne par combinaison `(polluant × végétal)` :

| Colonne | Description |
|---------|-------------|
| `polluant` | Nom du polluant |
| `famille` | HAP / BTEX / COHV |
| `nb_cycles` | Nombre de cycles aromatiques (HAP uniquement) |
| `vegetal` | Catégorie végétale |
| `organe` | racine / feuille / fruit |
| `modele` | Modèle utilisé |
| `Br_E` | Facteur de bioconcentration (6 décimales) |
| `unité` | mg/kg_vegsec / (mg/kg_sol) |
| `warnings` | Avertissements éventuels |

---

## 9. Ajouter un site

Créer `data/sites/site_<nom>.json` en copiant `site_default.json` et en renseignant :

1. `pH` et `matiere_organique` propres au site ;
2. optionnellement `pct_argile`, `pct_limon`, `temperature` pour affiner les estimations pédologiques ;
3. `conc_air` pour chacun des 24 polluants (utiliser le seuil de quantification si non mesuré).

Puis lancer :

```bash
python main.py --site <nom>
```

---

## 10. Références

- **Briggs et al. (1982)** — Pestic Sci 13:495–504  
  Modèle sol-racine (orge hydroponique) ; formule TSCF retenue dans PlantX et Mackay_97.

- **Travis & Arms (1988)** — Environ Sci Technol 22:271–274  
  Régression empirique parties aériennes ; domaine de calibration source 1 < log Kow < 9, borne opérationnelle retenue à 8.0.

- **Hung & Mackay (1997)** — Chemosphere 35:959–977  
  Modèle fugacité 3 compartiments ; appliqué aux feuilles pour les composés volatils (H > 0.1).

- **Trapp & Matthies (1995)** — Environ Sci Technol 29:2333–2338  
  Modèle PlantX bilan de masse pseudo-stationnaire ; racines, feuilles et fruits.

- **McKone & Maddalena (2007)** — LBNL-60273  
  Comparaison des modèles TSCF (Briggs, Hsu, Trapp) et domaines de validité de Travis & Arms ; justification des bornes opérationnelles retenues.

- **INERIS DRC-05-57281 (2005)**  
  Modèles de transfert sol-plante des polluants organiques ; validation expérimentale et choix des modèles par organe cible.
