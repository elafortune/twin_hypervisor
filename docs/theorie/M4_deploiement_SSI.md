# M4 – Déploiement SSI sur le Duplex (10 points)

## 1. Utilité

On conçoit le **système de sécurité incendie** du duplex et on l'écrit dans `devices.json` et dans le graphe :
- **détecteurs automatiques** (fumée ou chaleur) : détecter le feu tôt dans chaque espace occupable (F3) ;
- **déclencheurs manuels** (DM, « boîtiers bris de glace ») : permettre de donner l'alarme près de chaque sortie (F4) ;
- **caméras** : surveiller les chemins d'évacuation et compter les personnes restantes, ce qui alimente `peopleCount` en M5 (F5) ;
- **zones de détection** : regrouper les détecteurs pour localiser l'alarme, sans mélanger les niveaux (F6) ;
- **réseau sans fil** : garantir que les équipements communiquent, avec le modèle radio de M3 et éventuellement des relais `IoTNode`.

C'est l'application directe de M1 (géométrie, positions autorisées), M2 (graphe, formes) et M3 (radio, optimisation) à un vrai problème de conception.

## 2. Fondements

### 2.1 Modèle de caméra du PIMRC, transposé en 3D
- **PIMRC (2D)** : une caméra $c = \langle(x_c, y_c), \varphi_c\rangle$ couvre un **secteur circulaire** d'ouverture θ et de rayon $R$ : $Cov(c) = \{(x_c + r\cos\omega,\ y_c + r\sin\omega) \mid r \le R,\ \omega \in [\varphi_c - \theta/2, \varphi_c + \theta/2]\}$, filtré par la **visibilité** $Vis(c)$ (pas d'obstacle sur la ligne de Bresenham).
- **3D (paramètres fournis)** : champ horizontal 90°, champ vertical 60°, portée 8 m, hauteur de pose 2,4 m. Un point $p$ est vu par la caméra en $c$ (azimut φ, inclinaison τ vers le bas) si les quatre conditions suivantes sont vraies :
  1. $\|p - c\| \le R$ ;
  2. $|\text{angle}(\text{proj}_{xy}(p - c),\ \varphi)| \le 45°$ (demi-champ horizontal) ;
  3. $|\text{élévation}(p - c) + \tau| \le 30°$ (demi-champ vertical, élévation négative vers le bas) ;
  4. le segment $[c, p]$ ne traverse aucun voxel obstacle (DDA 3D de M3).

  Dans un repère caméra (matrice de rotation $R_z(\varphi)R_y(\tau)$), ces conditions se ramènent à des tests sur $\arctan$ des coordonnées : c'est un modèle de **pyramide de vision (frustum)** tronquée par la portée.
- **Quels points tester ?** Les cellules du **chemin d'évacuation**, prises à hauteur de visage (~1,6 m) ou au sol, sur la grille de 0,5 m.

### 2.2 Couverture *full-view*
- **Définition générale** (Wang & Cao, 2011) : un point est couvert en *full-view* si, quelle que soit la direction $\vec d$ du visage, une caméra le voit avec un angle entre $\vec d$ et $\overrightarrow{pc}$ inférieur ou égal à θ₀. On garantit ainsi de voir chaque personne de face.
- **Simplification du PIMRC (éq. 4)** : on ne considère que les **directions d'évacuation** prévues, c'est-à-dire les arêtes sortantes du multigraphe orienté vers l'évacuation :
  $$FV(S) = \frac{1}{|X'|}\sum_{n \in X'} \frac{|\{t \in E_n \mid \exists o \in s_n,\ |\theta_{o,n} - (t + \pi)| < \Phi\}|}{\deg(n)}$$
  Une direction de marche $t$ est couverte si une caméra regarde **à contre-sens** (angle $t + \pi$, à Φ près). En pratique, la caméra est placée en aval, du côté de la sortie, et regarde vers l'amont pour voir les visages des personnes qui arrivent.
- **Ici** : les directions d'évacuation se déduisent des routes de M5 (stratégie 1 à t = 0) ou des distances de M1, avec une direction par cellule du chemin, orientée vers la sortie.

### 2.3 Couverture des chemins (F5)
- `ssi:EvacuationPath` : un chemin par couple (espace, sortie) retenu. On a $\text{coverageRatio} = \frac{|\text{cellules du chemin vues par au moins une caméra}|}{|\text{cellules du chemin}|}$.
- F5 impose `coverageRatio` ≥ `minCameraCoverage`, et **ce paramètre vaut 1,0** : **100 % des cellules** doivent être vues. Le problème devient une **couverture d'ensemble** (*set cover*), non plus une couverture maximale.

### 2.4 Détecteurs automatiques (F3)
- Modèle disque : un détecteur au plafond couvre les points situés à une distance horizontale de 5 m au plus (`detecteur_rayon_m`).
- **Problème de couverture d'ensemble** : soit $J$ l'ensemble des positions candidates (positions autorisées $A$ de M1) et $I$ l'ensemble des cellules des espaces occupables. On pose $N(i) = \{j \in J : \|i - j\| \le r\}$ (avec visibilité, pour ne pas couvrir à travers un mur) :
  $$\min \sum_{j\in J} x_j \quad \text{s.c.} \quad \sum_{j \in N(i)} x_j \ge 1\ \ \forall i \in I,\qquad x_j \in \{0,1\}$$
  Ce problème est NP-difficile en général (Karp, 1972), mais résolu **exactement** en quelques secondes par un solveur MILP à cette taille. Les champs `statut_solveur` et `gap_relatif` de `devices.json` indiquent que le jury **attend un solveur exact**.
- **Fumée ou chaleur** (EN 54-7 / EN 54-5) : le détecteur de chaleur sert dans les locaux où la fumée « normale » provoque de fausses alarmes (cuisine). C'est l'objet de la demande D1 en M6.
- **Sémantique de `ssi:coversSpace`** : un détecteur « couvre » un espace s'il est situé dedans, ou si son disque recouvre tout ou partie de l'espace. À définir et documenter (F3 vérifie seulement l'existence d'au moins un lien).

### 2.5 Déclencheurs manuels (F4)
- Contrainte : pour chaque sortie $e$, au moins un DM tel que `distanceToExit` ≤ `maxCallPointDistance` (10 m).
- **Il s'agit d'une distance de cheminement** (cf. label de `ssi:distanceToExit`), pas d'une distance euclidienne : on la calcule par plus court chemin sur la grille ou sur le graphe de visibilité (M1).
- Usage courant (NF S 61-970) : les DM sont placés près des sorties, côté intérieur, à hauteur d'environ 1,2 m.

### 2.6 Zones de détection (F6)
- Chaque détecteur appartient à **exactement une** zone, et une zone ne s'étend **pas sur deux niveaux** (simplification de NF S 61-970 / EN 54-14).
- Choix naturel : une zone par niveau et par logement (A-N1, A-N2, B-N1, B-N2).

### 2.7 Connectivité du réseau SSI
- On réutilise le modèle de M3 : graphe des équipements, arête si le lien est bidirectionnel au-dessus de $S_{RX}$, puis on vérifie $\lambda(G) \ge \mu$.
- Si le réseau n'est pas connexe, on ajoute des **relais `IoTNode`**. C'est un problème d'**arbre de Steiner** / de placement de relais (NP-difficile), qu'on traite par heuristique gloutonne ou par MILP de flot.

## 3. Choix techniques et d'architecture

### Choix 1 – Formulation globale ou séquentielle
| Option | Pour | Contre |
|---|---|---|
| **Séquentielle** : détecteurs (set cover) → DM → caméras → relais | Problèmes petits et exacts, chacun explicable au tableau | Optimum global non garanti |
| Un seul MILP pondéré ou lexicographique | Optimum global | Gros modèle, difficile à déboguer |
| Algorithme génétique de M3 réutilisé | Unifié avec M3 | Pas de preuve d'optimalité ni de gap |

**Aspects** : la formulation à écrire au tableau, les temps de calcul sur le bâtiment plus grand de l'entretien, et les champs `statut_solveur`/`gap_relatif`.

### Choix 2 – Solveur
| Option | Pour | Contre |
|---|---|---|
| **HiGHS** (`highspy`, ou via PuLP / scipy.milp) | Libre (MIT), rapide, gap fourni | – |
| PuLP + CBC | Simple, très répandu | Plus lent que HiGHS |
| OR-Tools CP-SAT | Excellent sur les problèmes combinatoires | API différente, gap moins direct |

**Aspects** : licence libre (exigée), vitesse, accès au statut et au gap, facilité de modification.

### Choix 3 – Discrétisation des caméras
Les positions viennent de $A$ (plafond), éventuellement abaissées à 2,4 m ou posées en applique au mur. On discrétise l'azimut (8, 12 ou 16 valeurs) et l'inclinaison (2 ou 3 valeurs).
**Aspects** : taille du modèle ($|A| \times n_\varphi \times n_\tau$ variables), qualité de la solution, cohérence avec « hauteur de pose 2,4 m ». Le mode **3D** est attendu (« transposé en 3D »).

### Choix 4 – Définition des chemins d'évacuation
Un chemin par espace occupable vers sa sortie la plus proche, ou vers toutes les sorties. On le représente par la ligne centrale ou par une bande de cellules.
**Aspects** : faisabilité de « 100 % de couverture » (une bande large avec des recoins peut être infaisable), cohérence avec M5 (mêmes routes), nombre de caméras.

### Choix 5 – Intégration du *full-view*
En contrainte (seuil minimal sur FV), en objectif secondaire ou en indicateur rapporté seulement.
**Aspects** : l'énoncé demande la « couverture prioritaire des chemins et le full-view selon les directions d'évacuation » ; un MILP gère bien le full-view sous forme de contraintes de couverture par paires (cellule, direction).

### Choix 6 – Écriture dans le graphe
Triplets : `ssi:isLocatedIn`, `ssi:coversSpace`, `ssi:inDetectionZone`, `ssi:onStorey`, `ssi:servesExit`, `ssi:distanceToExit`, `ssi:monitors`, `ssi:coverageRatio`, plus le nœud `ssi:Parameters`.
**Aspects** : conformité à F3–F6 **vérifiée automatiquement** à la fin de M4 (test), et cohérence parfaite entre `devices.json` et `kg.ttl`.

### Choix 7 – Validation de la connectivité
Quel µ exiger pour le réseau SSI ? µ = 1 (connexe) ou µ = 2 (survit à une panne de lien) ; ajout de relais si besoin.
**Aspects** : la sécurité des personnes est la priorité, la sobriété (nombre d'équipements) vient en dernier, comme dans la politique de M6.

## 4. À maîtriser pour l'entretien
- Écrire le **set cover** des détecteurs et le modèle des caméras au tableau.
- Prédire : si le rayon de détection passe de 5 à 3 m, il faut environ $(5/3)^2 \approx 2{,}8$ fois plus de détecteurs dans les grandes pièces ; si `minCameraCoverage` passe de 1,0 à 0,8, le nombre de caméras baisse nettement (les recoins ne sont plus obligatoires).
- Expliquer la différence entre distance euclidienne et distance de cheminement (F4).
