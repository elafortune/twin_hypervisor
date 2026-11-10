# Étapes 0 à 2 – décisions validées, résultats, mode d'emploi

> Document de référence des étapes 0, 1 et 2. Les décisions ci-dessous ont été proposées par l'assistant et **validées par moi le 10/11/2026**. Le détail des options écartées est dans `guide_etapes_0_a_2.md`.

## 1. Décisions validées

### Étape 0 – Squelette
| # | Décision | Raison |
|---|---|---|
| D0.1 | Dépôt **privé**, jury invité à la remise ; `articles/` et PDF exclus | Consigne du kit (ne pas diffuser les articles) |
| D0.2 | Entrées du kit versionnées dans `data/`, **à l'octet près** (`.gitattributes`) | Le jury rejoue sans le kit ; données non altérées |
| D0.3 | Environnement conda **Python 3.11**, versions figées dans `requirements.lock` | ifcopenshell indisponible simplement sur 3.14 ; reproductibilité |
| D0.4 | CLI **argparse** : `run`, `valider`, `visualiser` ; option `--etapes` | Bibliothèque standard, modifiable sans assistant |
| D0.5 | **Les modules communiquent par les fichiers de sortie** (M2 lit `geometry.json`, pas l'IFC) | Chaque module testable et relançable seul ; le jury recalcule à partir des sorties |
| D0.6 | Chaque sortie est validée à la fin de son étape (JSON Schema ligne par ligne, SHACL pour `kg.ttl`) | Une sortie non conforme arrête la chaîne au lieu d'être découverte par le jury |
| D0.7 | Tests sur **3 niveaux** : unitaires, conformité, intégration | Qualité logicielle (5 pts), non-régression |
| D0.8 | `execution.json` : machine, versions, graine, durées | « Déclarer le matériel et les temps de calcul » |
| D0.9 | `pareto.json` = **liste** des 4 scénarios, chacun conforme au schéma | Le schéma décrit un seul scénario (ambiguïté notée) |

### Étape 1 – Extraction IFC
| # | Décision | Raison |
|---|---|---|
| D1.1 | Tout est indexé par **GlobalId**, jamais par nom | Deux espaces s'appellent `B202` ; généricité |
| D1.2 | `surface_m2` = propriété **« GSA BIM Area »** (repli : géométrie) ; `surface_geometrique_m2` toujours fourni | Q05 et Q10 citent cette propriété ; la géométrie sert aux distances |
| D1.3 | `polygone_xy` = **empreinte géométrique** (union des triangles projetés) | Marche pour toute représentation IFC |
| D1.4 | `hauteur_m` = zmax − zmin du maillage | Géométrique, recoupable avec `Unbounded Height` |
| D1.5 | **Occupable** = faux si le nom, le nom long ou le niveau contient un mot-clé (toit, roof, gaine…) ; escaliers et couloirs occupables | Règle générique ; la liste est surchargeable par `mots_cles_non_occupable` dans les paramètres |
| D1.6 | Unité de longueur **lue dans le fichier** | L'IFC de l'entretien peut être en mm |
| D1.7 | Anomalies détectées par **règles génériques** (invariants), jamais corrigées en silence | Traçabilité ; pas de ML (21 espaces, besoin d'explication) |
| D1.8 | Niveau d'un élément pour la géométrie = **altitude de sa base** ; le rattachement IFC est contrôlé | Le rattachement IFC est faux pour un escalier |

> **Ajustement de D1.5** par rapport à la proposition initiale (« niveau le plus haut ») : sur un immeuble, le dernier niveau est souvent occupé ; seul le **nom** (« Roof ») est retenu, pas la position.

### Visualisation
| # | Décision | Raison |
|---|---|---|
| DV.1 | **plotly** (HTML interactif hors ligne) plutôt que matplotlib | Survol (GlobalId, surfaces, anomalies), zoom, couches cliquables |
| DV.2 | **Plan 2D** construit depuis `geometry.json` uniquement | Montre ce que la chaîne a compris (pas ce que dit l'IFC) |
| DV.3 | **Vue 3D** construite depuis l'IFC, + superpositions issues des sorties (portes, sorties, puis équipements de `devices.json`) | Indispensable pour M3/M4 (hauteurs, caméras, voxels) |

### Étape 2 – Connectivité (réalisée le 10/11)
| # | Décision | Raison |
|---|---|---|
| D2.1 | Connectivité recoupée sur **3 sources** : `IfcRelSpaceBoundary`, chaîne mur → ouverture → porte (Pang), géométrie | Un désaccord entre sources = anomalie ; robustesse sur un IFC sans limites d'espace |
| D2.2 | Liaisons « ouverture » = **limites virtuelles** entre espaces | Les 12 ouvertures sans porte sont des trous de meubles / de toit, pas des passages |
| D2.3 | Sortie = porte bordant **un seul** espace intérieur ; `IsExternal` en recoupement ; `IsFireExit` ignoré | `IsFireExit` est une valeur fictive |
| D2.4 | Escalier = liaison **cage (x105) ↔ espace d'arrivée (x201)** ; le foyer rejoint la cage par une ouverture. Si une paire est reliée à la fois par un escalier et une limite virtuelle, seule la liaison « escalier » est gardée | La volée est entièrement dans la cage double hauteur ; Q09 = espaces de liaison verticale |
| D2.6 | **Vote à la majorité** (≥ 2 sources sur 3) pour les espaces d'une porte ; seul un désaccord impliquant la source IFC est une anomalie de maquette | Une citation isolée de la géométrie ou de la chaîne de Pang est une imprécision de méthode, pas une erreur du modèle |
| D2.7 | Ouverture libre = contours qui se touchent (< 2 cm), **sans chevauchement**, sur ≥ 0,60 m, confirmée par des limites virtuelles IFC | Deux espaces séparés par un mur sont à ≥ 12 cm ; un chevauchement est une erreur de contour |
| D2.5 | Pas de graphe de connaissances, pas de Dijkstra, pas de ML à l'étape 2 (BFS de contrôle seulement) | KG à l'étape 4, Dijkstra aux étapes 3 et 5 |

## 2. Résultats principaux (étape 1)

Extraction en **1,4 s** ; `geometry.json` conforme.

| Élément | Résultat |
|---|---|
| Niveaux | 4 : T/FDN −1,25 m · Level 1 0 m · Level 2 3,1 m · Roof 6,0 m |
| Espaces | 21 (Level 1 : 10 dont les 2 cages d'escalier double hauteur ; Level 2 : 10 ; Roof : R301, seul non occupable) |
| Portes | 14 ; largeurs 0,762 m (4) à 1,25 m (2 portes d'entrée) ; **4 sorties provisoires** (entrées A101/B101, portes vitrées A102/B102) |
| Escaliers | 2 volées de 16 contremarches, z = 0 → 3,05 m, dans A105 et B105 |
| Surfaces | géométrique < déclarée de 7 à 23 % pour **tous** les espaces : convention de mesure, pas une anomalie |

**Anomalies détectées (10 lignes, 7 constats)**

| Règle | Élément | Constat | Traitement |
|---|---|---|---|
| nom_unique | `…dl_39`, `…dl_3A` | Deux espaces nommés `B202` | Identification par GlobalId |
| nom_coherent_proprietes | `…dl_39` (Bedroom 2) | Nom IFC `B202` mais `PSet_Revit_Identity Data.Number = B203` : **le nom a été modifié** | Nom IFC conservé, `B203` signalé comme nom d'origine probable |
| fonction_coherente | `10mjSDZJj9gPS2PrQaxa4o` (B105) | Nommé « Room » alors que son jumeau A105 est « Stair » et que sa catégorie OmniClass est « Stairway » | Fonction déduite de la catégorie (escalier) |
| booleen_type | 14 portes | `IsFireExit = 'IsFireExit'` (texte) | Ignoré ; sorties par géométrie + `IsExternal` |
| rattachement_niveau | `21ldoMpbP4VfsJ0XGY_34d` (escalier B) | Rattaché au niveau Roof, base à z = 0 | Niveau corrigé en Level 1 pour la connectivité |
| dimensions_escalier | 2 volées | Hauteur de marche 0,6357 et giron 0,8202 : **en pieds** (0,194 m et 0,25 m) | Valeurs ignorées ; géométrie utilisée |

**Réponses préliminaires** (à vérifier à la main dans BIMvision, puis à confirmer par SPARQL à l'étape 4) :

| Question | Résultat préliminaire |
|---|---|
| Q01 – espaces de Level 2 | 10 : A201–A205, B201, B202 ×2, B204, B205 *(A105/B105, double hauteur, sont rattachés à Level 1 : à discuter)* |
| Q05 – surface totale du logement A (GSA BIM Area) | **138,16 m²** (10 espaces, A105 inclus) |
| Q10 – surface totale de Level 2 | **134,53 m²** |
| Q12 – salles de bains de Level 2 | A204, B204 |
| Q14 – portes < 0,80 m | 4 portes de 0,762 m : `1aj$VJZFn2TxepZUBcKp$i`, `1aj$VJZFn2TxepZUBcKpac`, `1hOSvn6df7F8_7GcBWlS8Z`, `1hOSvn6df7F8_7GcBWlS9F` |

## 2 bis. Résultats principaux (étape 2)

Connectivité calculée en **0,6 s** de plus (M1 complet : 1,9 s). 20 liaisons :

| Type | Liaisons |
|---|---|
| porte (10) | A101–A104, A201–A202, A201–A203, A201–A204, **A204–A205**, et leurs symétriques dans B ; les 3 sources concordent sauf pour A204–A205 |
| ouverture (8) | A101–A102, A101–A103, A102–A103, A101–A105 et symétriques B (IFC + géométrie concordent) |
| escalier (2) | A105 → A201, B105 → B201 |
| sorties (4) | entrées A101, B101 ; portes vitrées A102, B102 (géométrie et `IsExternal` concordent) |

Tous les espaces occupables atteignent une sortie. **Aucune liaison entre les logements A et B.**

**Nouvelles anomalies (5 constats)**

| Règle | Constat | Traitement |
|---|---|---|
| porte_sources_concordantes | La porte `1aj$VJZFn2TxepZUBcKpac` (A204–A205) a aussi une limite IFC vers A201, contredite par la chaîne de Pang et la géométrie (sa symétrique dans B n'en a pas) | Relation vers A201 écartée par le vote |
| chevauchement_espaces | Les cages A105 / B105 empiètent de 0,15 m² sur les chambres A203 / B202 (« Bedroom 2 ») au niveau 2 | Pas de liaison ; signalé |
| limite_bien_placee | Les limites virtuelles de A201 et B201 sont à 6 à 10 m de leur espace : placement local de ces espaces modifié sans mettre à jour leurs limites | Connectivité par contact géométrique |
| limite_type_coherent | 12 limites virtuelles typées EXTERNAL font face à un autre espace (foyers, cuisines, cages) | Traitées comme internes |

**Réponses préliminaires** (à confirmer par SPARQL à l'étape 4) :

| Question | Résultat |
|---|---|
| Q02 – portes vers l'extérieur | 4 : `1hOSvn6df7F8_7GcBWlRGQ`, `…RH8`, `1s1jVhK8z0pgKYcr9jt781`, `…7AB` |
| Q03 – accès direct à une sortie | A101, A102, B101, B102 |
| Q04 – communiquent avec A101 sans porte | A102, A103, A105 |
| Q06 – une seule porte au Level 2 | A202, A203, A205, B202 (×2), B205 |
| Q08 – de B « Bedroom 2 » à l'entrée B | B201, B105, B101 |
| Q09 – liaison verticale | A105, B105 |
| Q13 – passage direct A ↔ B | **aucun** (ensemble vide) |

## 3. Mode d'emploi

Depuis `C:\Users\emeri\twin_hypervisor`, dans un terminal où l'environnement est activé (`conda activate twinhyp`) :

```bash
# 1. Lancer la chaîne (ou seulement M1)
python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc --params data/parametres.json \
    --obs data/observations.csv --out sorties --etapes m1

# 2. Générer les visualisations
python -m twinhyp visualiser --out sorties          # plan 2D + vue 3D (~15 s)
python -m twinhyp visualiser --out sorties --sans-3d  # plan 2D seul (~1 s)

# 3. Revalider les sorties
python -m twinhyp valider --out sorties

# 4. Tests
pytest                       # tout (~25 s)
pytest -m "not integration"  # rapides
```

**Où regarder**

| Fichier | Contenu | Comment l'ouvrir |
|---|---|---|
| `sorties/figures/plan_2d.html` | Plan par niveau (menu en haut à gauche) ; survol d'un espace = GlobalId, surfaces, anomalies ; contour **orange** = espace avec anomalie ; ★ rouge = sortie ; cadre violet = escalier | Double-clic (navigateur), fonctionne hors ligne |
| `sorties/figures/vue_3d.html` | Maquette 3D ; menu « niveau » ; boutons **Perspective / Vue de dessus** ; légende cliquable (mobilier, revêtements, toiture masqués par défaut) ; espaces orange = anomalie | Idem (garder `plotly.min.js` dans le même dossier) |
| `sorties/geometry.json` | Sortie M1 complète (anomalies comprises) | Éditeur ou navigateur |
| `sorties/execution.json` | Machine, versions, durées | Éditeur |

Vérification indépendante de l'IFC : **BIMvision** (gratuit, Windows) pour contrôler à la main surfaces, largeurs et noms.
