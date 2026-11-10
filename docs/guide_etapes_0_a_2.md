# Guide pratique – Étapes 0, 1 et 2

> Établi le 10 novembre 2026. Dépôt : https://github.com/elafortune/twin_hypervisor (vide, et **public** au moment de la vérification).
> Ce guide complète `plan_execution.md`. Il dit **quoi faire**, **quoi lire**, **quels choix trancher**, et **à quoi sert** chaque étape.

---

## Vue d'ensemble : à quoi servent ces trois étapes ?

| Étape | Produit | Pourquoi c'est la fondation |
|---|---|---|
| 0 – Squelette | Dépôt, environnement, commande unique, tests de schémas | Le jury rejoue tout avec **une commande** ; si elle n'existe pas dès le début, on la bricole le jeudi. Les tests rapportent 5 points de qualité « gratuitement ». |
| 1 – Extraction IFC | `niveaux`, `espaces`, `portes` de `geometry.json` | Tout le reste (graphe RDF, voxels, caméras, évacuation) lit ces objets. Une erreur d'unité ou de coordonnées ici se propage partout. |
| 2 – Connectivité et anomalies | `liaisons`, `sortie` des portes, `anomalies` | C'est le **graphe de navigation** du bâtiment (M2 le traduit en `isConnectedTo`, M5 y fait tourner Dijkstra). Les anomalies sont explicitement évaluées. |

---

## Étape 0 – Squelette du dépôt

### 0.1 À connaître
- **Git** : commits atomiques (« une idée = un commit »), messages à l'impératif (`m1: extraire les niveaux`). L'historique complet est noté : ne pas tout pousser en un commit le jeudi.
- **Disposition `src/`** et `pyproject.toml` : le paquet s'installe avec `pip install -e .`, la commande devient `python -m twinhyp …`.
- **JSON Schema draft 2020-12** : les fichiers de `schemas/` sont les **contrats d'interface**. Un `.jsonl` se valide **ligne par ligne** (chaque ligne est un objet conforme au schéma).
- **pytest** : un test = une fonction `test_…`, des *fixtures* pour charger l'IFC une seule fois (`scope="session"`).

### 0.2 À lire
1. Énoncé, section « Livrables » et « Reproduction » (mot à mot).
2. Les 6 schémas de `schemas/` : noter les champs **obligatoires** de chacun (ex. `geometry.json` : `niveaux[globalId, nom, altitude_m]`, `espaces[globalId, nom, niveau_globalId, polygone_xy, surface_m2, hauteur_m, occupable]`, `portes[globalId, largeur_m, espaces, sortie]`, `liaisons[de, vers, type ∈ {porte, ouverture, escalier}]`, `anomalies[element_globalId, description, traitement]`).
3. Docs `jsonschema` : `Draft202012Validator`, `iter_errors` (pour afficher toutes les erreurs, pas seulement la première).

### 0.3 Choix à trancher
| # | Choix | Options | Recommandation | Pourquoi |
|---|---|---|---|---|
| C1 | **Confidentialité du dépôt** | Public / **privé + jury invité** | **Privé**, puis inviter le jury | Le dépôt est public : le kit demande de ne pas diffuser les articles, et un dépôt public pendant le concours expose ton travail. |
| C2 | Ce qu'on versionne du kit | Tout / **données d'entrée seulement** | `data/` : IFC, `parametres.json`, `observations.csv`, `questions.json`, `demandes_modification.json`, `schemas/`, `ontologie/`. **Jamais `articles/`** (dans `.gitignore`). | Le jury doit pouvoir rejouer sans le kit à côté ; les articles ne se diffusent pas. |
| C3 | Emplacement du dépôt | Dans le dossier du kit / **dossier séparé** | Cloner dans `C:\Users\emeri\twin_hypervisor` et y copier les entrées | Évite de committer par erreur le PDF, les articles, `.DS_Store`, le fichier verrou Word. |
| C4 | Environnement Python | Python 3.14 système / **conda Python 3.11** / venv | **conda, Python 3.11** (`environment.yml`) | `ifcopenshell` n'est pas installé sur ton 3.14 et ses roues binaires sortent avec retard sur les nouvelles versions de Python. 3.11 est la plus sûre pour ifcopenshell, pyshacl, highspy. |
| C5 | CLI | **argparse** / typer / click | **argparse** | Bibliothèque standard, zéro dépendance, facile à modifier sans IA à l'entretien. |
| C6 | Structure interne | dicts / **dataclasses** / pydantic | **dataclasses** + `to_dict()` ; validation par `jsonschema` en sortie | Typage lisible, pas de dépendance ; le schéma reste la référence. |
| C7 | Figer les versions | `>=` / **`==` dans `requirements.lock`** | `pyproject.toml` (bornes) + `pip freeze > requirements.lock` | Reproductibilité exigée par le jury. |
| C8 | Paramètres | constantes dans le code / **lecture de `parametres.json`** | Toujours lu depuis le fichier passé en argument | F4/F5 parlent d'un « paramètre personnel » : rien en dur. |

### 0.4 Arborescence proposée
```
twin_hypervisor/
├── README.md               # installation + LA commande + matériel et temps de calcul
├── pyproject.toml          # dépendances, point d'entrée
├── environment.yml         # conda, Python 3.11
├── requirements.lock       # versions exactes (pip freeze)
├── .gitignore              # articles/, sorties/, __pycache__, .DS_Store, ~$*
├── data/                   # entrées du kit (sans les articles)
├── docs/                   # feuille_de_route, theorie/, plan, prompt.md, carnet_de_bord.md
├── src/twinhyp/
│   ├── __main__.py         # python -m twinhyp run --ifc … --params … --obs … --out …
│   ├── pipeline.py         # enchaîne M1 → M6, écrit les 8 sorties
│   ├── io_schemas.py       # validation jsonschema (json et jsonl)
│   ├── m1_geometrie/       # extraction.py, connectivite.py, anomalies.py, distances.py, voxels.py
│   ├── m2_graphe/  m3_iwcmc/  m4_deploiement/  m5_evacuation/  m6_agent/
└── tests/
    ├── conftest.py         # fixtures : modèle IFC, paramètres
    ├── test_schemas.py     # chaque sortie respecte son schéma
    └── test_m1_*.py
```

### 0.5 À faire, dans l'ordre
1. Passer le dépôt en **privé** (GitHub → Settings → Danger Zone → Change visibility).
2. `git clone https://github.com/elafortune/twin_hypervisor C:\Users\emeri\twin_hypervisor`
3. `conda create -n twinhyp python=3.11` puis `pip install ifcopenshell shapely numpy networkx rdflib pyshacl jsonschema pytest matplotlib`.
4. Vérifier le kit : `pyshacl -s data/ontologie/formes_publiques.ttl -e data/ontologie/ssi_socle.ttl -i rdfs -a data/ontologie/exemple_minimal.ttl` → `Conforms: True`. **Premier test automatisé** : le même contrôle en Python.
5. Écrire la CLI et un `pipeline.py` qui produit les 8 fichiers **vides mais conformes** (`geometry.json` avec 5 listes vides, `.jsonl` vides, `.ttl` = socle).
6. `test_schemas.py` : lance la chaîne dans un dossier temporaire (`tmp_path`) et valide chaque sortie.
7. Commits : `init: structure du dépôt`, `env: environnement conda et dépendances`, `cli: commande unique de reproduction`, `test: validation des sorties par les schémas`.
8. Ouvrir `docs/carnet_de_bord.md` : première entrée datée (choix C1–C8 et pourquoi).

**Critère de fin** : `pytest` vert, `python -m twinhyp run …` crée les 8 fichiers.

---

## Étape 1 – M1 : extraction IFC

### 1.1 À connaître
- **Hiérarchie spatiale IFC** : `IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey → IfcSpace`, reliés par `IfcRelAggregates` (décomposition). Les éléments physiques (murs, portes, escaliers) sont rattachés à un niveau par `IfcRelContainedInSpatialStructure`.
- **Propriétés** : `IfcRelDefinesByProperties → IfcPropertySet → IfcPropertySingleValue`. Les quantités (surface, hauteur) peuvent être dans `IfcElementQuantity` **ou** dans des psets Revit (« GSA BIM Area », « PSet_Revit_Dimensions »…). Il faut savoir **laquelle on croit** : la surface géométrique calculée ou la propriété déclarée (leur désaccord est une anomalie possible).
- **Placements** : chaque objet a un `IfcLocalPlacement` relatif à celui de son parent. La position monde = produit de matrices 4×4 le long de la chaîne. `ifcopenshell.util.placement.get_local_placement()` le fait pour toi ; `ifcopenshell.geom` avec `USE_WORLD_COORDS=True` donne directement des sommets en coordonnées monde.
- **Unités** : ici **mètres** (`IFCSIUNIT(.LENGTHUNIT.,.METRE.)`), angles en radians. Lire quand même l'unité depuis le fichier (`ifcopenshell.util.unit.calculate_unit_scale`) : l'IFC de l'entretien peut être en millimètres.
- **Polygone d'un espace** : la géométrie d'un `IfcSpace` est un solide (souvent `IfcExtrudedAreaSolid` : profil 2D × hauteur). Deux façons d'obtenir `polygone_xy` :
  1. maillage triangulé (`ifcopenshell.geom.create_shape`) → union shapely des triangles projetés en 2D → contour ; **générique** (marche pour tout type de représentation) ;
  2. lecture directe du profil extrudé ; plus exact mais ne marche que pour ce type.
- **Occupable** : un espace est occupable s'il accueille des personnes (pas un vide technique, pas un toit). Ici, `R301 "Roof"` est un candidat évident à `occupable = false`. La règle doit être **générique** (nom, `PredefinedType`, hauteur, niveau), pas une liste de GlobalId.

### 1.2 À lire
1. **[Pang] §4.1 et §4.1.1** et son **tableau 1** (correspondance entité IFC → classe de l'ontologie).
2. Fiche `theorie/M1_jumeau_geometrique.md` §2.1.
3. docs.ifcopenshell.org : « Hello World » (ouvrir, `by_type`), `ifcopenshell.util.element` (`get_psets`, `get_container`), `ifcopenshell.util.placement`, `ifcopenshell.geom` (settings, `create_shape`, itérateur).
4. buildingSMART IFC2x3 TC1 : fiches `IfcSpace`, `IfcBuildingStorey` (attribut `Elevation`), `IfcDoor` (`OverallWidth`, `OverallHeight`), `IfcRelDefinesByProperties`.
5. Shapely 2 : `Polygon`, `unary_union`, `.area`, `.exterior.coords`, `make_valid`.

### 1.3 Choix à trancher
| # | Choix | Recommandation |
|---|---|---|
| C9 | Source du polygone | Maillage `ifcopenshell.geom` + union shapely (générique) ; comparer la surface obtenue à la propriété « GSA BIM Area » et signaler les écarts > 5 % en anomalie. |
| C10 | Hauteur d'un espace | `zmax − zmin` du maillage (géométrique), recoupée avec les propriétés. |
| C11 | Altitude d'un niveau | `IfcBuildingStorey.Elevation` × échelle d'unité ; recoupée avec le placement. |
| C12 | Largeur de porte | `OverallWidth` ; repli sur la dimension de la boîte englobante si absent (et anomalie). |
| C13 | Règle « occupable » | Règle générique documentée (mots-clés de nom/`LongName` du type toit, gaine, vide ; hauteur < 1,8 m ; niveau toit) et paramétrable. |
| C14 | Identifiants | **Tout est indexé par GlobalId**, jamais par nom (deux espaces s'appellent `B202`). |

### 1.4 À faire
1. Dans un *notebook* ou un script jetable : ouvrir l'IFC, lister niveaux, espaces (`Name`, `LongName`), portes, escaliers ; afficher les psets d'un espace et d'une porte. **But : connaître le fichier avant de coder.**
2. `extraction.py` : fonctions `extraire_niveaux`, `extraire_espaces`, `extraire_portes`, `extraire_escaliers`, qui renvoient des dataclasses.
3. Tests : 4 niveaux aux altitudes −1,25 / 0 / 3,1 / 6,0 ; 21 espaces ; 14 portes ; toutes les surfaces > 0 ; chaque espace a un niveau.
4. Vérification **à la main** dans un visualiseur (BIMvision gratuit, ou Bonsai dans Blender) : 2 ou 3 surfaces, une largeur de porte, et les réponses Q01, Q05, Q10, Q12, Q14. L'écrire dans le carnet.
5. Brancher dans `pipeline.py` → `geometry.json` partiellement rempli, toujours conforme.

**Critère de fin** : tests verts, vérifications manuelles notées dans le carnet.

---

## Étape 2 – M1 : connectivité, sorties, escaliers, anomalies

### 2.1 À connaître
- **Chaîne de Pang** (§4.1.2) : `IfcDoor ←(IfcRelFillsElement)– IfcOpeningElement –(IfcRelVoidsElement)→ IfcWall`. La porte remplit une ouverture, l'ouverture perce un mur ; le mur sépare deux espaces → ces deux espaces sont reliés **par la porte**.
- **Ouverture libre** : une ouverture **sans** porte (`IfcOpeningElement` non rempli). Ici 50 ouvertures pour 38 remplissages → **12 ouvertures non remplies**. Certaines sont des fenêtres manquantes ou des réservations, d'autres des **passages** (liaison de type `ouverture`). À trier par une règle (dimensions, hauteur d'allège : un passage commence au sol et fait plus de ~1,8 m de haut).
- **`IfcRelSpaceBoundary`** (265 dans le fichier) : relie un espace à l'élément qui le borde (mur, porte, dalle), avec un type physique/virtuel et interne/externe. C'est la **source la plus directe** : si une porte borde deux espaces, ils sont connectés. Les limites **virtuelles** (`VIRTUAL`) correspondent à des séparations sans mur (espaces ouverts l'un sur l'autre) → liaison `ouverture`.
- **Sortie** : porte qui ne relie qu'**un** espace intérieur (l'autre côté est l'extérieur), ou limite `EXTERNAL`. Le fichier contient aussi une propriété `IsFireExit`, **dont la valeur est le texte `'IsFireExit'` au lieu d'un booléen** : à examiner (anomalie probable), et à recouper avec la géométrie.
- **Escaliers** : `IfcStair`/`IfcStairFlight` relient deux niveaux. On relie l'espace qui contient le pied de l'escalier à celui qui contient son sommet (boîte englobante de la volée contre polygones des espaces de chaque niveau).
- **Repli géométrique** : dilater légèrement les polygones des espaces (`buffer(0,2)`) et chercher quels espaces intersectent la boîte de la porte. Sert à **recouper** les relations IFC.
- **Graphe** (networkx) : nœuds = espaces + nœud `EXTERIEUR`, arêtes typées. Contrôles : chaque espace occupable atteint l'extérieur, aucune porte ne relie un espace à lui-même, pas d'espace isolé.
- **Contrôle qualité** : une anomalie se détecte par une **règle générique** (un invariant violé), pas en connaissant la réponse. Chaque anomalie a une **description** et un **traitement** (corrigé, ignoré, signalé, hypothèse retenue).

### 2.2 Invariants à tester (chaque violation = anomalie candidate)
| Invariant | Indice déjà repéré |
|---|---|
| Noms d'espaces uniques par bâtiment | `B202` apparaît deux fois (Bedroom 1 et Bedroom 2) |
| Cohérence entre logements symétriques (même nom ↔ même fonction) | `A105 = Stair` mais `B105 = Room` |
| Une porte relie exactement 2 espaces, ou 1 espace + extérieur | à calculer |
| Toute porte remplit une ouverture, toute ouverture perce un élément | 12 ouvertures non remplies |
| Propriétés au bon type (booléen attendu → booléen) | `IsFireExit = 'IsFireExit'` |
| Surface déclarée ≈ surface géométrique | à calculer |
| Espace contenu dans le niveau de son altitude | à calculer |
| Chaque espace occupable relié à une sortie | à calculer |
| Espace non occupable (toit) non relié comme pièce | `R301 Roof` |
| Escalier relié à un espace sur chaque niveau | à calculer |

### 2.3 À lire
1. **[Pang] §4.1.2 et figure 3** (connectivité par porte et virtuelle).
2. IFC2x3 : `IfcRelSpaceBoundary` (attributs `PhysicalOrVirtualBoundary`, `InternalOrExternalBoundary`), `IfcOpeningElement`, `IfcRelVoidsElement`, `IfcRelFillsElement`, `IfcStair`, `IfcStairFlight`.
3. Fiche M1 §2.2 et §2.5.
4. networkx : `Graph`, attributs d'arêtes, `connected_components`, `has_path`, dessin avec `nx.draw` et les centroïdes comme positions.

### 2.4 Choix à trancher
| # | Choix | Recommandation |
|---|---|---|
| C15 | Source de connectivité | **Trois sources recoupées** : `IfcRelSpaceBoundary` (principale), chaîne de Pang (confirmation), géométrie (repli). Un désaccord entre sources → anomalie. C'est générique et ça montre la rigueur. |
| C16 | Définition d'une sortie | Géométrique (porte avec un seul espace intérieur) ; la propriété IFC sert de recoupement. |
| C17 | Ouvertures non remplies | Passage si au sol et assez haute, sinon ignorée ; la règle est paramétrable. |
| C18 | Traitement des anomalies | **Ne jamais corriger en silence** : chaque correction est écrite dans `anomalies` avec son traitement. On ne renomme pas les GlobalId ; on corrige les attributs dérivés. |
| C19 | Liaisons orientées ou non | Non orientées dans `liaisons` (connectivité), orientées seulement pour les distances (étape 3). |

### 2.5 À faire
1. Explorer : pour 2 portes, suivre la chaîne porte → ouverture → mur → espaces à la main dans le script ; lister les `IfcRelSpaceBoundary` d'une porte.
2. `connectivite.py` : `liaisons_par_portes`, `liaisons_ouvertures`, `liaisons_escaliers`, `detecter_sorties`.
3. `anomalies.py` : une fonction par invariant, chacune renvoie une liste d'`Anomalie(element_globalId, description, traitement)`.
4. Dessiner le graphe sur le plan (espaces + arêtes colorées par type) et le comparer au plan de l'IFC dans le visualiseur.
5. Tests : chaque porte a 1 ou 2 espaces, au moins une sortie par logement, chaque espace occupable atteint l'extérieur, au moins 3 anomalies détectées.
6. Vérifier à la main Q02, Q03, Q04, Q06, Q08, Q09, Q13 ; noter les impasses dans le carnet.

**Critère de fin** : `geometry.json` complet (sauf distances), graphe dessiné, au moins 3 anomalies documentées.

---

## Ce que tu dois savoir expliquer sans IA après ces 3 étapes
- Le chemin IFC qui mène d'une porte aux deux espaces qu'elle relie, et ce qui change avec une limite virtuelle.
- Pourquoi on indexe par GlobalId et pourquoi rien ne dépend des noms du duplex.
- Comment chaque anomalie a été trouvée (quel invariant), et pourquoi ce traitement-là.
- Comment ta chaîne réagit à un IFC en millimètres ou sans `IfcRelSpaceBoundary`.

---

## Précisions (questions du 10/11)

| Question | Réponse courte |
|---|---|
| Faut-il coder un visualiseur IFC ? | Non. Lecture par **ifcopenshell** ; visualisation 3D dans un **logiciel externe** (BIMvision, Bonsai/Blender). On code seulement une **fonction de tracé 2D** (matplotlib) du plan par niveau : espaces, portes, liaisons, sorties. Elle sert à vérifier et à montrer les résultats à l'entretien sur l'IFC inconnu. |
| Le graphe de connaissances se fait-il à l'étape 2 ? | Non. L'étape 2 calcule la connectivité en Python (networkx) et l'écrit dans `geometry.json` (`liaisons`). L'ontologie et le RDF sont faits à l'étape 4 (M2), **à partir de `geometry.json`**. On prépare seulement une correspondance simple : `liaisons.type` ↔ `ssi:connectionType`, porte ↔ `ssi:Door`, sortie ↔ `ssi:Exit`. |
| Dijkstra à l'étape 2 ? | Non. Étape 2 : simple **parcours (BFS / composantes connexes)** pour vérifier que chaque espace atteint l'extérieur. Dijkstra intervient à l'étape 3 (dans une pièce, graphe de visibilité) et à l'étape 5 (entre pièces, évacuation). |
| Machine learning pour les anomalies ? | Non. 21 espaces, aucune donnée d'entraînement, besoin d'explication et de déterminisme : **règles** (invariants de qualité de données). Plusieurs règles seront ré-exprimées en formes SHACL maison à l'étape 4. |
| Choix d'architecture central | Les modules communiquent par les **fichiers de sortie** (contrats) : M2 lit `geometry.json`, pas l'IFC. Chaque module est testable seul et rejouable séparément (`--etapes m1,m2`). |
