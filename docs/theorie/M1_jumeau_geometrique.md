# M1 – Jumeau géométrique (15 points)

## 1. Utilité

Le jumeau géométrique transforme la maquette IFC, un fichier d'échange riche mais difficile à exploiter, en **représentations calculables** dont tous les autres modules dépendent :

| Représentation | Sert à | Utilisée par |
|---|---|---|
| Liste des niveaux, espaces (polygone, surface, hauteur), portes (largeur), sorties, escaliers | Inventaire du bâtiment | M2, M6 (Q01–Q14) |
| **Graphe de connectivité** espaces ↔ espaces (porte, ouverture, escalier) | Topologie de l'évacuation | M2, M5 |
| **Distances d'évacuation** par liaison (point le plus défavorable) | Poids du graphe pour Dijkstra | M5 |
| **Grille de voxels** avec matériau par voxel | Propagation radio, visibilité caméra | M3, M4 |
| **Positions autorisées A** (impacts au plafond) | Espace de recherche du placement | M3, M4 |
| **Anomalies** de la maquette | Qualité des données, robustesse | Rapport, M2 |

C'est le module « fondation » : une erreur de connectivité ici fausse les routes M5, les réponses M6 et la validation SHACL.

## 2. Fondements

### 2.1 Le modèle IFC (ISO 16739)

- **Hiérarchie spatiale** : `IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey → IfcSpace`, reliés par `IfcRelAggregates` (décomposition). Les éléments physiques (murs, portes, escaliers) sont rattachés aux niveaux par `IfcRelContainedInSpatialStructure`.
- **Placement** : chaque objet a un `IfcLocalPlacement` relatif à son parent. La position monde s'obtient par **composition de transformations homogènes 4×4** :
  $M_{\text{monde}} = M_{\text{site}} \cdot M_{\text{bâtiment}} \cdot M_{\text{niveau}} \cdot M_{\text{objet}}$
  avec $M = \begin{pmatrix} R & t \\ 0 & 1 \end{pmatrix}$, où $R$ est construite à partir des axes `Axis` (Z) et `RefDirection` (X), $Y = Z \times X$.
- **Géométrie** : surtout `IfcExtrudedAreaSolid` (profil 2D × direction × profondeur) et des B-rep facettisées (`IfcFacetedBrep`, `IfcFaceBasedSurfaceModel`). Un noyau géométrique (OpenCascade via IfcOpenShell) les convertit en maillages triangulés.
- **Unités** : déclarées par `IfcUnitAssignment` (Revit exporte souvent en mm ou en pieds). Toujours convertir en mètres.
- **Propriétés** : `IfcRelDefinesByProperties → IfcPropertySet → IfcPropertySingleValue` (ex. « GSA BIM Area » pour Q05/Q10). Les portes portent aussi `OverallWidth`/`OverallHeight`.
- **IFC2x3 ≠ IFC4** : Pang utilise IFC4 (`IfcRelSpaceBoundary` 1st/2nd level, plus d'attributs). Ici, c'est de l'IFC2x3 : il faut adapter la chaîne de Pang.

### 2.2 Connectivité entre espaces ([Pang] §4.1.2, fig. 3)

- `IfcRelSpaceBoundary(RelatingSpace, RelatedBuildingElement, PhysicalOrVirtualBoundary, InternalOrExternalBoundary)` relie un espace à un élément qui le borde.
- **Connexion virtuelle** : deux espaces bordés par le même `IfcVirtualElement` sont en communication libre. *Ici il n'y en a aucun* → il faut détecter les ouvertures libres autrement (ouverture sans remplissage, adjacence géométrique).
- **Connexion par porte** : chaîne `Mur → IfcRelVoidsElement → IfcOpeningElement → IfcRelFillsElement → IfcDoor`. Les deux espaces qui bordent le mur au droit de la porte sont connectés.
- **Sortie** : porte dont un seul côté est un espace intérieur (limite `EXTERNAL`). C'est la définition de F2_Sortie (« relie exactement un espace intérieur »).
- **Escalier** : liaison verticale entre l'espace escalier du niveau 1 et l'espace du niveau 2 qu'il dessert (Q09).

Formellement, on construit un **graphe orienté pondéré** $G = (V, E, w)$, où $V$ = espaces ∪ {Extérieur} et $E$ = liaisons typées. La connectivité est symétrique (`ssi:isConnectedTo` est `owl:SymmetricProperty`), mais les **distances ne le sont pas** (voir 2.3).

### 2.3 Distance d'évacuation depuis le point le plus défavorable ([Pang] §4.1.3, fig. 4)

Définition réglementaire (code chinois cité par Pang) : distance de cheminement, en contournant les murs, du point de l'espace le plus éloigné jusqu'à la porte.

Méthode de Pang sur le polygone de l'espace (sommets $P_i$, porte $D$) :
- $L_{D_i}$ = distance directe sommet → porte si le segment reste dans le polygone ;
- $L_{P_{ij}}$ = distance directe entre sommets visibles ;
- $L_{C_i} = \min_j (L_{P_{ij}} + L_{D_j})$ pour un sommet qui ne voit pas la porte ;
- $L = \max_i (L_{C_i}, L_{D_i})$.

Théorie sous-jacente :
- **Plus court chemin dans un polygone** : le chemin géodésique entre deux points d'un polygone (simple ou à trous) est une ligne brisée dont les sommets intermédiaires sont des **sommets réflexes** du polygone. Il se calcule par **graphe de visibilité + Dijkstra** (Lozano-Pérez & Wesley, 1979).
- **Point le plus éloigné** : dans un polygone simple, le point géodésiquement le plus éloigné d'une source est atteint en un **sommet** du polygone (Suri, 1989). Cela justifie que Pang ne teste que les sommets.
- **Limite de la formule de Pang** : elle n'autorise qu'un seul sommet intermédiaire. Pour un polygone en L ou en U, il en faut parfois deux ou plus → Dijkstra sur le graphe de visibilité généralise proprement.
- **Asymétrie** : $d(A \to B)$ mesure le pire point de A jusqu'à la porte A|B. C'est en général différent de $d(B \to A)$. La classe `ssi:EvacuationDistance` (avec `from`/`to`) est réifiée justement pour porter une distance orientée.

### 2.4 Grille de voxels et positions autorisées ([IWCMC] §III.A, fig. 1–2)

- **Voxelisation** : on discrétise la boîte englobante en cellules de côté δ (`pas_grille_m = 0,5`). Chaque voxel reçoit 1 (libre) ou 0 (obstacle), et **il faut aussi stocker le matériau de l'obstacle**, indispensable pour M3.
  Attention, l'article dit : « cuboid of size 16 × 34 × 10 which corresponds to a voxel size of 50 cm × 50 cm × 25 cm ». Le domaine de 16 × 34 × 10 est donc vraisemblablement **en nombre de voxels** (soit 8 m × 17 m × 2,5 m), avec un pas vertical de 25 cm. C'est une ambiguïté à trancher et à documenter.
- **Test d'appartenance** : un point est dans un solide fermé si une demi-droite issue du point coupe sa frontière un nombre **impair** de fois (théorème de Jordan, version 3D).
- **Lancer de rayons vers le plafond** : pour chaque niveau $i$ et chaque $(i\delta, j\delta)$ du plan, on lance un rayon vertical vers le haut. Le premier impact avec un élément « plafond » (`IfcSlab`, `IfcCovering`, `IfcRoof`) donne un point de $A_i$, et $A = \bigcup_i A_i$.
- **Intersection rayon–triangle** : algorithme de Möller–Trumbore, en $O(1)$ par triangle. Il est accéléré par une hiérarchie de volumes englobants (BVH), ce qui donne $O(\log n)$ par rayon.
- L'IWCMC infère les niveaux par DBSCAN sur les toitures. Ici, l'IFC fournit directement `IfcBuildingStorey`, mais il faut vérifier que les altitudes sont cohérentes avec la géométrie.

### 2.5 Détection d'incohérences

On s'appuie sur des invariants qu'une maquette saine doit respecter :
- unicité des noms et numéros d'espaces (déjà vu : **deux `B202`**) ;
- cohérence nom long / fonction (`B105` « Room » face à `A105` « Stair ») ;
- chaque espace appartient à exactement un niveau, et son altitude est compatible ;
- surface déclarée (« GSA BIM Area ») ≈ surface calculée du polygone ;
- largeur de porte : `OverallWidth` ≈ propriété ≈ géométrie ;
- chaque porte remplit une ouverture hébergée par un mur, et chaque ouverture remplie l'est par une seule porte ;
- les limites d'espace (`IfcRelSpaceBoundary`) sont cohérentes avec l'adjacence géométrique ;
- pas de chevauchement de polygones d'espaces sur un même niveau ;
- GlobalId uniques et de 22 caractères.

## 3. Choix techniques et d'architecture

### Choix 1 – Bibliothèque de lecture IFC
| Option | Pour | Contre |
|---|---|---|
| **IfcOpenShell** (Python) | Standard de fait, IFC2x3 et IFC4, module `geom` (OpenCascade), `pip install ifcopenshell` | API géométrique un peu bas niveau |
| IfcOpenShell + pythonOCC (comme Pang) | Fidèle à l'article, booléens exacts | Installation lourde (conda), surdimensionné ici |
| Parser STEP maison | Contrôle total | Réinvente la roue, ne gère pas la géométrie |

**Aspects à peser** : prise en charge d'IFC2x3, installation sous Windows, robustesse sur un IFC inconnu à l'entretien, performance.

### Choix 2 – Source de la connectivité
| Option | Pour | Contre |
|---|---|---|
| Sémantique (`IfcRelSpaceBoundary`, chaîne de Pang) | Fidèle à Pang, exacte quand la maquette est propre | Les limites peuvent être fausses ou absentes (c'est justement là que se cachent les incohérences) |
| Géométrique (boîte de la porte ∩ polygones des espaces dilatés) | Robuste, indépendante des relations IFC | Seuils de tolérance, faux positifs |
| **Hybride** : sémantique d'abord, contrôle géométrique ensuite, divergences → `anomalies` | Robuste **et** fidèle, détecte les incohérences | Plus de code |

**Aspects** : fidélité à Pang (exigée par l'énoncé), détection des incohérences, généricité.

### Choix 3 – Calcul des distances d'évacuation
| Option | Pour | Contre |
|---|---|---|
| Formule de Pang (sommets, un seul intermédiaire) | Fidèle | Fausse sur polygones non convexes complexes |
| **Graphe de visibilité + Dijkstra** (shapely + networkx) | Exacte, généralise Pang | Un peu plus de code |
| Grille 0,5 m + BFS ou fast marching | Simple, réutilise la grille | Erreur de discrétisation (~δ·√2) |

**Aspects** : exactitude, explicabilité au tableau, distance orientée, cas « espace → sortie » (distance jusqu'à la porte de sortie), liaisons sans porte (prendre le milieu de l'ouverture), escaliers (longueur de la volée : $\sqrt{\text{course}^2 + \text{hauteur}^2}$, éventuellement majorée).

### Choix 4 – Voxelisation et lancer de rayons
| Option | Pour | Contre |
|---|---|---|
| **trimesh** (+ embree en option) | Léger, `ray.intersects_location`, voxelisation | Maillages IFC parfois non fermés |
| Open3D (`RaycastingScene`) | Très rapide, robuste | Dépendance plus lourde |
| Numpy maison sur les boîtes englobantes | Simple | Imprécis pour les murs obliques |

**Aspects** : quels éléments sont des obstacles (murs, dalles, portes, fenêtres, mobilier ?), **matériau par voxel** (nécessaire en M3), résolution horizontale et verticale (0,5 × 0,5 × 0,25 ?), alignement de la grille sur l'origine, mémoire, cohérence avec la grille de M4.

### Choix 5 – Traitement des anomalies
Options : correction automatique, exclusion avec signalement, ou fichier de corrections déclaratif (qui ne dépend pas du duplex).
**Aspects** : ne jamais corriger silencieusement ; chaque anomalie va dans `geometry.json` (`element_globalId`, `description`, `traitement`) ; la règle de détection doit fonctionner sur un autre bâtiment.

### Choix 6 – Format intermédiaire
`geometry.json` doit être la **source unique de vérité** pour M2 à M5, à côté d'un fichier binaire pour la grille (`.npz`). **Aspects** : testabilité module par module, temps de calcul (on ne relit pas l'IFC à chaque étape), conformité au schéma imposé.

## 4. À maîtriser pour l'entretien
- Expliquer la chaîne `Mur → Ouverture → Porte` et pourquoi l'IFC2x3 du duplex n'a pas de `IfcVirtualElement`.
- Justifier la distance orientée et le choix « sommets uniquement » (théorème du point géodésique le plus éloigné).
- Prédire l'effet du pas de grille δ : nombre de voxels en $O(1/\delta^3)$, positions autorisées en $O(1/\delta^2)$, temps de calcul M3.
- Savoir où ajouter une nouvelle règle d'incohérence dans le code.
