# Calculateur BCF sol-plante — MODUL'ERS

Calcule le facteur de bioconcentration sol-plante (Br_E) à renseigner dans l'outil MODUL'ERS (INERIS).  
Sortie : `mg/kg_vegsec / (mg/kg_sol)`, exportée dans un fichier Excel par site.

---

## Sommaire

1. [Principe général](#1-principe-général)
2. [Structure du projet](#2-structure-du-projet)
3. [Données d'entrée](#3-données-dentrée)
4. [Sélection du modèle (organiques)](#4-sélection-du-modèle-organiques)
5. [Modèles de calcul (organiques)](#5-modèles-de-calcul-organiques)
6. [Système d'avertissements (organiques)](#6-système-davertissements-organiques)
7. [Pipeline Métaux (BAPPET)](#7-pipeline-métaux-bappet)
8. [Pipeline PCB (BAPPOP)](#8-pipeline-pcb-bappop)
9. [Utilisation](#9-utilisation)
10. [Format de sortie](#10-format-de-sortie)
11. [Ajouter un site](#11-ajouter-un-site)
12. [Références](#12-références)

---

## 1. Principe général

Le script produit le facteur de bioconcentration sol-plante pour **trois familles de polluants**, chacune avec sa propre méthodologie de calcul, puis **fusionne les résultats en une feuille Excel par catégorie végétale** (et non par pipeline) — chaque feuille liste tous les polluants applicables à cette catégorie, tous pipelines confondus :

| Pipeline | Polluants | Méthode |
|----------|-----------|---------|
| **Organiques** | HAP, BTEX, COHV, HCT (37 substances) | Modèles mécanistes/empiriques (Briggs, Travis & Arms, Mackay_97, PlantX) sélectionnés selon organe/H/log Kow |
| **Métaux** | 15 ETM (As, Cd, Co, Cr, Cu, Hg, Mn, Mo, Ni, Pb, Sb, Se, Tl, V, Zn) | Régression statistique sur données terrain BAPPET, filtres qualité INERIS |
| **PCB** | 7 congénères indicateurs (PCB 28/52/101/118/138/153/180) | Régression OLS sur données terrain BAPPOP (projet TROPHé) |

Pour le pipeline **organiques**, pour chaque combinaison `(polluant × végétal)`, le script :

1. charge les paramètres physico-chimiques du polluant et les caractéristiques du végétal ;
2. sélectionne automatiquement le modèle le plus adapté selon l'organe cible et les propriétés du polluant ;
3. calcule le Br_E ;
4. génère des avertissements si le polluant sort du domaine de validité du modèle.

Les pipelines **Métaux** et **PCB** ne partent pas de propriétés physico-chimiques mais recalculent un facteur de bioconcentration par régression statistique sur des bases de données terrain (BAPPET, BAPPOP), rechargées et traitées à chaque exécution. `main.py::build_sheets_par_vegetal()` fusionne ensuite les 3 résultats dans un schéma de colonnes commun et les répartit par catégorie végétale (voir [§10](#10-format-de-sortie)).

---

## 2. Structure du projet

```
CalculateurBCF/
│
├── main.py                  # Point d'entrée — 3 pipelines (organiques/métaux/PCB), export Excel multi-onglets
│
├── core/
│   ├── selector.py          # Choix du modèle organique selon organe, log Kow, H
│   ├── calculator.py        # Orchestration du calcul Br_E organiques
│   └── validator.py         # Warnings post-calcul (domaine de validité, BCF négatif…)
│
├── models/
│   ├── briggs.py            # Briggs et al. (1982) — racines
│   ├── mackay97.py          # Hung & Mackay (1997) — feuilles volatils
│   ├── travis_arms.py       # Travis & Arms (1988) — parties aériennes
│   └── plantx.py            # Trapp & Matthies (1995) — bilan de masse
│
└── data/
    ├── polluants.py         # Base de données polluants organiques (HAP, BTEX, COHV)
    ├── vegetaux.py          # Paramètres des 5 catégories végétales + 9 catégories PCB (VEGETAUX_PCB)
    ├── sol.py               # Chargement, estimation et validation des paramètres sol
    ├── metaux.py            # Pipeline BCF métaux (BAPPET) — filtres INERIS, régressions OLS, distribution
    ├── pcb.py                # Pipeline BCF PCB (BAPPOP) — régression OLS par congénère × catégorie
    ├── bappet/bappet.csv     # Données terrain métaux (source du pipeline Métaux)
    ├── bappop/bappop.csv     # Données terrain PCB, projet TROPHé (source du pipeline PCB)
    ├── aprifel/aprifel_pct_ms.csv  # % matière sèche par espèce (conversion MF→MS, pipeline Métaux)
    └── sites/
        ├── site_default.json  # Site de référence (exemple complet)
        └── site_A.json        # Exemple site réel
```

---

## 3. Données d'entrée

### Polluants (`data/polluants.py`)

37 substances réparties en quatre familles. **8 substances** (4 HAP, 2 BTEX, 2 COHV) sont issues du Tableau 2 INERIS DRC-05-57281 (validées expérimentalement sur tomate, haricot, laitue, carotte) ; les **29 substances restantes** complètent la couverture HAP/BTEX/COHV/HCT depuis d'autres sources (IARC92, EPI Suite, EPA SSL, TPHCWG — voir le champ `source` dans `data/polluants.py`) et sont marquées « à valider » :

| Famille | Substances | Issues du Tableau 2 INERIS |
|---------|-----------|------------------------------|
| HAP (16) | naphtalène, acénaphtylène, acénaphtène, fluorène, phénanthrène, anthracène, fluoranthène, pyrène, benzo(a)anthracène, chrysène, benzo(b)fluoranthène, benzo(k)fluoranthène, benzo(a)pyrène, indéno(1,2,3-cd)pyrène, dibenzo(a,h)anthracène, benzo(g,h,i)pérylène | naphtalène, anthracène, phénanthrène, benzo(a)pyrène (4/16) |
| BTEX (6) | benzène, toluène, éthylbenzène, o/m/p-xylène | benzène, toluène (2/6) |
| COHV (13) | chloroforme, tétrachloroéthylène, trichloroéthylène, cis-1,2-dichloroéthylène, trans-1,2-dichloroéthylène, 1,1-dichloroéthylène, chlorure de vinyle, 1,1,2-trichloroéthane, 1,1,1-trichloroéthane, 1,2-dichloroéthane, 1,1-dichloroéthane, tétrachlorométhane, dichlorométhane | chloroforme, tétrachloroéthylène (2/13) |
| HCT (2) | fraction c10-c12, fraction c12-c16 | aucune (nouvelle famille, hors Tableau 2 INERIS — voir note ci-dessous) |

Chaque polluant est défini par : `log_kow`, `log_koc`, `MW` (g/mol), `Pvap` (Pa), `H` (constante de Henry adimensionnelle).

#### HCT — hydrocarbures totaux (fractions C10-C40)

Les hydrocarbures pétroliers sont mesurés en laboratoire (norme ISO 16703) sous forme de fractions par bande de carbone (`Fraction C10-C12`, `C12-C16`, `C16-C20`, ... jusqu'à `C36-C40`), pas comme une substance unique — un « HC Totaux » global n'a pas de sens physico-chimique pour un calcul par organe (log Kow/H « moyen » sur un agrégat de centaines de composés très hétérogènes).

**Seules 2 fractions sont modélisées : `fraction c10-c12` et `fraction c12-c16`.** Leurs paramètres physico-chimiques sont un mix pondéré 70 % aliphatique / 30 % aromatique (convention par défaut faute de spéciation labo, guide wallon des sols pollués), dérivés des tables TPHCWG (1997) via Washington State Dept. of Ecology (MTCA Table 747-4 / CLARC Table 4, rev. 2022) — voir le champ `source` de chaque entrée dans `data/polluants.py` pour le détail des calculs (ordre des opérations important : dérivation par composante aliphatique/aromatique puis mix, pas l'inverse).

**Les fractions plus lourdes (C16-C20 à C36-C40) sont volontairement exclues**, pas seulement par manque de données : leur log Kow extrapolé avoisine 10, très au-delà du domaine calibré des 4 modèles du pipeline (Briggs/Travis_Arms/Mackay_97/PlantX, calés empiriquement sur log Kow ≲ 8). Cette exclusion est cohérente avec le comportement physico-chimique connu des composés très hydrophobes : la formule TSCF déjà utilisée par le pipeline (`TSCF = 0.784 × exp(-(log Kow - 1.78)² / 2.44)`, Briggs 1982, voir §5 PlantX/Mackay_97) est une courbe en cloche qui décroît fortement au-delà de log Kow ≈ 3-4 — le transfert xylémique devient quasi nul pour ces composés, qui sont majoritairement retenus par la matière organique du sol plutôt que transférés vers la plante. Ce n'est donc pas qu'une limite de calcul, mais un phénomène physique réel qui justifie l'absence de modélisation.

> **Comportement si des clés `conc_air` supplémentaires sont ajoutées** (ex. un futur bulletin labo réel avec les 8 fractions, dont les 6 exclues) : `data/sol.py::validate_sol()` ne vérifie que les clés *manquantes* par rapport à `POLLUANTS` — une clé de `conc_air` sans correspondance dans `POLLUANTS` (ex. `"fraction c16-c20"`) est **silencieusement ignorée**, sans erreur ni avertissement. Elle n'est simplement jamais lue nulle part dans le pipeline.

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

**Paramètres optionnels spécifiques aux pipelines Métaux/PCB** :

| Clé | Description | Effet si renseigné |
|-----|-------------|---------------------|
| `conc_sol_metaux` | `{ETM: Cs mg/kg_MS}` | Br_E métaux calculé par régression BAPPET (`exp(A + B·ln(Cs))`) si Cs dans le domaine de validité et régression retenue ; sinon fallback moyenne géométrique pondérée (voir [§7](#7-pipeline-métaux-bappet)) |
| `conc_sol_pcb` | `{PCB_xx: Cs mg/kg_MS}` | Présent dans `site_default.json` mais **non consommé** par `data/pcb.py` à ce jour — le pipeline PCB retourne un Br générique par congénère × catégorie, pas de Br_E site-dépendant |
| `conc_air_gaz_pcb` | `{PCB_xx: Cair µg/m³}` | Idem — champ réservé, pas encore utilisé (le calcul de Bf, BCF air→plante, est documenté comme non calculable depuis BAPPOP) |

**Paramètres calculés automatiquement par `load_sol()` :**

- `carbone_organique` = MO / 1.72
- `densite` — Manrique & Jones (1991) si argile+limon disponibles, sinon Rawls (1983)
- `fraction_eau` — Saxton & Rawls (2006) si argile disponible, sinon 0.30 (INERIS)
- `fraction_air` = porosité totale − fraction_eau

---

## 4. Sélection du modèle (organiques)

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

## 5. Modèles de calcul (organiques)

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

## 6. Système d'avertissements (organiques)

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

## 7. Pipeline Métaux (BAPPET)

`data/metaux.py` calcule un Br_E pour 15 éléments traces métalliques (ETM) à partir de données terrain sol-plante (`data/bappet/bappet.csv`), selon une méthodologie de filtrage et de régression alignée sur les rapports INERIS. Contrairement au pipeline organiques, ce n'est **pas** un modèle physico-chimique : c'est une régression statistique recalculée à chaque exécution.

### Filtres qualité INERIS (F1–F10)

Appliqués séquentiellement sur les données BAPPET avant régression :

| Filtre | Critère | Assouplissement (n ≤ 10) |
|--------|---------|---------------------------|
| F1 | Mode de culture — pleine terre uniquement (exclusion pot/intérieur/container) | — |
| F2 | Contexte — exclusion urbain + industriel | relâché |
| F3 | Origine de la pollution — exclusion artificielle + urbaine | relâché |
| F4 | Extraction sol — totale/pseudo-totale (exception : As → partielle conservée) | — |
| F5 | Organe analysé — partie consommée du végétal uniquement | — |
| F6 | LOQ — exclusion des valeurs < LQ/< LD (sol et plante) | — |
| F7 | Préparation — lavage requis ; « non précisé » exclu en mode strict | relâché |
| F8 | Appariement sol-plante — Cp et Cs numériques (implicite via BCF calculable) | — |
| F9 | Bruit de fond RECORD 1994 — exclusion si `Cs < 5×BDF` et `BCF > 10×BCF_médian_groupe` | — |
| F10 | Grubbs α = 5 % — retrait itératif des outliers sur `ln(BCF)` | — |

Par groupe `(ETM × catégorie INERIS)`, si le nombre de données valides après filtres stricts est **≤ 10**, F2/F3/F7 sont relâchés pour ce groupe (mode `assoupli` vs `strict`, tracé dans la colonne `mode_filtrage`).

Les 6 catégories INERIS (mapping depuis `Type Plante` de BAPPET) : `légumes-feuilles`, `légumes-fruits`, `légumes-racines`, `tubercules`, `céréales`, `fourrage`.

Le pourcentage de matière sèche (conversion MF→MS de la concentration plante) est lu depuis BAPPET si disponible, sinon recherché dans `data/aprifel/aprifel_pct_ms.csv` par correspondance exacte/approchée du nom d'espèce, avec fallback sur une valeur par défaut par type de plante.

### Régressions et distribution

- **Régression simple OLS** : `ln(BCF) = A + B·ln(Cs)`, calculée si n ≥ 3 points et Cs variable.
- **Régression multiple OLS** : ajout de `pH` et/ou `matière organique` si n ≥ 9 et présélection Pearson (α = 10 %) + amélioration du R² ajusté.
- **Distribution ajustée (Anderson-Darling)** : la loi log-normale est retenue si le test AD de log-normalité a un p ≥ 5 % ; sinon la meilleure alternative parmi {normale, Pearson V, gamma, uniforme} (plus petite statistique AD).
- **Régression retenue** (`regression_retenue`) : la régression simple est jugée plus informative que la distribution si son ratio observé/prédit (`OP_max/OP_min`) est inférieur au plus petit des ratios `BCF_max/BCF_min` et du ratio interpercentile [2,5 % ; 97,5 %] de la distribution.

### Calcul du Br_E final

Pour chaque groupe `(ETM × catégorie)`, le Br_E dépend de la présence de `conc_sol_metaux` dans le site JSON (`Br_E_source`) :

| Cas | Br_E | Source |
|-----|------|--------|
| Régression retenue, Cs fourni et dans le domaine de validité `[Cs_valid_min ; Cs_valid_max]` | `exp(A_simple + B_simple·ln(Cs))` | `regression` |
| Régression retenue, Cs fourni mais hors domaine | `BCF_mean_geom_pond` | `moy_geom_hors_domaine` |
| `conc_sol_metaux` absent du site JSON | `BCF_mean_geom_pond` | `moy_geom_cs_absent` |
| Régression non retenue (non significative ou n insuffisant) | `BCF_mean_geom_pond` | `moy_geom_reg_non_retenue` |

`BCF_mean_geom_pond` est la moyenne géométrique du BCF pondérée par le nombre d'échantillons par observation (`Nb échantillons` BAPPET).

---

## 8. Pipeline PCB (BAPPOP)

`data/pcb.py` calcule un facteur de transfert Br par régression OLS pour 7 congénères indicateurs (PCB 28, 52, 101, 118, 138, 153, 180), à partir des données terrain du projet TROPHé (`data/bappop/bappop.csv`), selon la méthodologie du rapport INERIS-DRC-16-159776-09593A.

### Traitement

1. Filtre sur le milieu `Sol (mg/kg)` et exclusion des valeurs `< LOQ` (plante ou sol).
2. Conversion matière fraîche → matière sèche via un % MS par défaut selon le type de plante (`_PCT_MS_DEFAULT`, pas de lookup APRIFEL contrairement au pipeline métaux).
3. Regroupement par `(congénère × catégorie INERIS)` — mapping depuis `Type plante` vers 6 catégories atteignables en pratique (`legumes_feuilles`, `legumes_fruits`, `legumes_racines`, `tubercules`, `cereales`, `fourrage`) parmi les 9 catégories définies dans `VEGETAUX_PCB` (`data/vegetaux.py`).
4. Retrait des outliers par test de Grubbs (α = 5 %) sur les résidus d'une régression OLS préliminaire, puis régression OLS finale sur les données nettoyées (minimum 4 points, `MIN_N`).
5. `Br` (pente de la régression `Cp_MS = f(Cs)`) retenu comme valeur ponctuelle si r² > 0,5 (`Br_retenu`) ; sinon utiliser l'intervalle `[BCF_min ; BCF_max]`.

`Bf` (BCF depuis l'air gazeux vers la plante) n'est **pas calculable** depuis BAPPOP — les données terrain/enceinte ne fournissent pas de concentration en air gazeux mesurée. La colonne `Bf` est toujours `None`, à compléter manuellement depuis les tableaux 1-9 du rapport INERIS si nécessaire.

> Contrairement au pipeline Métaux, le pipeline PCB ne combine pas encore le résultat avec une concentration sol du site : `data/pcb.py` ne prend pas `sol` en paramètre. Les champs `conc_sol_pcb` et `conc_air_gaz_pcb` du JSON site sont réservés pour une évolution future.

---

## 9. Utilisation

### Prérequis

```
pip install pandas openpyxl scipy numpy
```

### Lancer le calcul

```bash
# Site par défaut (data/sites/site_default.json) — calcule les 3 pipelines
python main.py

# Site spécifique (data/sites/site_A.json)
python main.py --site A

# Désactiver un pipeline (ex : si les CSV BAPPET/BAPPOP ne sont pas disponibles)
python main.py --no-metaux
python main.py --no-pcb
```

| Option | Effet |
|--------|-------|
| `--site <nom>` | Charge `data/sites/site_<nom>.json` (défaut : `default`) |
| `--no-metaux` | Ignore le calcul BCF métaux (BAPPET) — famille `Métal` absente des feuilles générées |
| `--no-pcb` | Ignore le calcul BCF PCB (BAPPOP) — famille `PCB` absente des feuilles générées |

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

----------Calcul BCF polluants organiques...

----------Calcul BCF métaux (BAPPET)...
...
----------Calcul BCF PCB (BAPPOP)...
...
----------Export : Br_E_default.xlsx  (4 onglet(s))
  légumes_feuilles (58 lignes)
  légumes_fruits (58 lignes)
  légumes_racines (55 lignes)
  tubercules (56 lignes)
```

---

## 10. Format de sortie

Fichier Excel `Br_E_<site>.xlsx` avec **une feuille par catégorie végétale**, construite par `main.py::build_sheets_par_vegetal()` qui fusionne les 3 pipelines (organiques/métaux/PCB) dans un schéma de colonnes commun. Seules les catégories ayant au moins une ligne de résultat génèrent une feuille (ex : `fourrage` peut être absente si aucun des 3 pipelines n'a de donnée pour cette catégorie sur le site en cours).

**Catégories** (ordre d'affichage) : `légumes_feuilles`, `légumes_fruits`, `légumes_racines`, `tubercules`, `fruits`, `céréales`, `fourrage`. Les 5 premières viennent de la taxonomie `data/vegetaux.py` (pipeline organiques) ; `céréales`/`fourrage` n'existent que pour les pipelines Métaux/PCB. Les catégories Métaux (`légumes-feuilles`, tirets) et PCB (`legumes_feuilles`, sans accents) sont ramenées à cette taxonomie unique via `_MET_CAT_MAP`/`_PCB_CAT_MAP` dans `main.py`.

Chaque feuille contient une ligne par polluant applicable à la catégorie, toutes familles mélangées (HAP/BTEX/COHV/Métal/PCB), avec les colonnes communes suivantes :

| Colonne | Description |
|---------|-------------|
| `polluant` | Nom du polluant (organique), ETM (métal) ou congénère PCB |
| `famille` | HAP / BTEX / COHV / Métal / PCB |
| `categorie` | Catégorie végétale (= nom de la feuille) |
| `Br_E` | Facteur de bioconcentration retenu — voir la logique par famille ci-dessous |
| `unité` | mg/kg_vegsec / (mg/kg_sol) |
| `methode` | Modèle/méthode utilisé (voir détail par famille) |
| `note` | Avertissements ou détails de qualité de la régression (voir détail par famille) |

**Logique de `Br_E`/`methode`/`note` selon la famille :**

- **Organiques (HAP/BTEX/COHV)** : `Br_E` = sortie directe du modèle sélectionné (§4-5) ; `methode` = nom du modèle (Briggs/Travis_Arms/Mackay_97/PlantX) ; `note` = warnings de `core/validator.py` concaténés (ex : domaine de validité, PlantX hors HAP lourds).
- **Métal** : `Br_E` = valeur finale calculée par `data/metaux.py` (régression Cs-dépendante ou moyenne géométrique pondérée selon `Br_E_source`, voir [§7](#7-pipeline-métaux-bappet)) ; `methode` = `"<modele> (<Br_E_source>)"` ; `note` = taille d'échantillon, mode de filtrage (`strict`/`assoupli`) et r² de la régression simple si disponible.
- **PCB** : `Br_E` = `Br` (pente de régression) si `Br_retenu` (r² > 0,5), sinon `BCF_median` en repli ; `methode` indique laquelle des deux voies a été utilisée ; `note` = taille d'échantillon et r² (ou intervalle `[BCF_min ; BCF_max]` si la régression n'est pas retenue).

Les colonnes détaillées propres à chaque pipeline (statistiques de régression complètes pour les métaux, `Bf`/`intercept_air_contrib` pour les PCB, `nb_cycles`/`organe` pour les organiques…) ne sont **pas** reportées dans ce format condensé — elles restent disponibles en appelant directement `compute_bcf_metaux()` / `compute_bcf_pcb()` / `compute_bre()` en Python si une analyse plus fine est nécessaire.

---

## 11. Ajouter un site

Créer `data/sites/site_<nom>.json` en copiant `site_default.json` et en renseignant :

1. `pH` et `matiere_organique` propres au site ;
2. optionnellement `pct_argile`, `pct_limon`, `temperature` pour affiner les estimations pédologiques ;
3. `conc_air` pour chacun des 37 polluants organiques (utiliser le seuil de quantification si non mesuré) ;
4. optionnellement `conc_sol_metaux` pour affiner le `Br_E` métaux par régression site-dépendante (sinon moyenne géométrique utilisée par défaut).

Puis lancer :

```bash
python main.py --site <nom>
```

---

## 12. Références

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

- **INERIS-DRC-16-159776-09593A**  
  Méthodologie de calcul du facteur de transfert sol-plante des PCB (projet TROPHé) ; filtres qualité et régression appliqués dans `data/pcb.py`.

- **RECORD 1994**  
  Fond géochimique naturel français en éléments traces métalliques ; valeurs utilisées pour le filtre F9 (bruit de fond) dans `data/metaux.py` — à vérifier contre le document source (signalé comme tel dans le code).

- **APRIFEL**  
  Base de données % matière sèche par espèce végétale ; utilisée pour la conversion matière fraîche → matière sèche dans le pipeline Métaux (`data/aprifel/aprifel_pct_ms.csv`).
