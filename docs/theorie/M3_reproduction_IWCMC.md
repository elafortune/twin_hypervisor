# M3 – Reproduction de l'article IWCMC 2024 (15 points)

## 1. Utilité

- **Scientifique** : reproduire un résultat publié de l'équipe d'accueil (Chambon, Sahli, Rachedi, Mebarki) et **expliquer les écarts**. C'est le cœur de l'évaluation de ta rigueur de chercheur : un écart bien expliqué vaut mieux qu'une courbe identique obtenue sans comprendre.
- **Question de recherche** : que gagne-t-on à utiliser le jumeau numérique (les matériaux réels des murs) pour optimiser un déploiement IoT ? L'article annonce jusqu'à +8 % de qualité de lien et +20 % de couverture. Avec µ = 3, il trouve aussi des solutions à 4 ou 5 nœuds que l'environnement « sans jumeau » ne trouve pas.
- **Technique** : le modèle radio et le calcul de µ-connexité sont **réutilisés en M4** pour vérifier la connectivité du réseau SSI.
- La réponse à **Q20** (plus petit nombre de nœuds atteignant 90 % de couverture, avec jumeau, µ = 0) vient directement de ton front de Pareto.

## 2. Fondements

### 2.1 Propagation radio
- **Friis (espace libre)** : $P_R = P_T + G_T + G_R - 20\log_{10}\!\left(\frac{4\pi d}{\lambda}\right)$. À 2,4 GHz ($\lambda \approx 12{,}5$ cm), la perte à 1 m vaut ≈ 40 dB. Le tableau I donne $PL_0 = 37{,}15$ dB, une valeur mesurée (Kacou et al., 2018).
- **Modèle log-distance** : $PL(d) = PL_0 + 10\,n\log_{10}(d/d_0) + X_\sigma$. L'IWCMC prend $n = 2$, d'où le terme $20\log_{10}\|o - p\|$.
- **Modèle multi-murs** (Motley–Keenan / COST 231) : on ajoute la perte due à chaque obstacle traversé.
- **Équation (2) de l'IWCMC** :
  $$PL[o,p] = PL_0 + 20\log_{10}\|o - p\| + \sum_{obs \in \Omega} L_{obs} + X$$
  où $\Omega$ est l'ensemble des obstacles traversés par le segment $[o,p]$ (obtenu par lancer de rayon) et $X \sim \mathcal N(0, \sigma^2)$ l'atténuation aléatoire (*shadowing*).
- **Tableau I, ligne WiFi 2,4 GHz** (extraction texte, à vérifier visuellement sur le PDF) :

  | $PL_0$ | Porte bois | Plaque de plâtre | Mur béton | Mur porteur | σ |
  |---|---|---|---|---|---|
  | 37,15 dB | 0,23 | **0,32** | 0,18 | 0,22 | 3,26 dB |

  Unité annoncée : **dB/m**. C'est physiquement très faible : un mur porteur de 20 cm n'atténuerait que 0,04 dB, alors qu'un mur réel atténue plutôt 5 à 15 dB. Il faut donc trancher entre plusieurs interprétations : par mètre traversé, par voxel traversé, ou par centimètre. **Choisir une hypothèse, la justifier, mesurer la sensibilité et la documenter comme écart.**
- **Matériau le plus absorbant à 2,4 GHz** d'après ce tableau : la **plaque de plâtre** (0,32), ce qui est contre-intuitif. Le scénario « sans jumeau » met donc *tous* les obstacles en plaque de plâtre. L'article indique que 18 % des obstacles du duplex sont faits de ce matériau, ce qui donne une vérification croisée de ton étiquetage des matériaux.
- **Correspondance des matériaux IFC vers les catégories du tableau I** : l'IFC contient « Masonry - Brick », « Masonry - Concrete Block », « Plasterboard », « Concrete - Cast In Situ », « Concrete », des bois, des isolants, « Metal - Stud Layer »… Les murs sont des **multicouches** (`IfcMaterialLayerSetUsage`) : il faut soit sommer couche par couche, soit prendre le matériau dominant.

### 2.2 Couverture et score
- **Équation (1)**, meilleur serveur : $v_p = \max_{o\in O}\big(P_{TX} - PL[o,p]\big)$ pour chaque voxel libre $p$.
- **Équation (3)**, normalisation min-max : $\tilde v_p = \dfrac{v_p - S_{RX}}{P_{TX} - S_{RX}}$. On a $\tilde v_p > 0$ si et seulement si le signal reçu dépasse la sensibilité.
- **Équation (4)**, score : $F_{obj} = \sum_p \big(\alpha\,\tilde v_p + \beta\,\mathbb 1_{\tilde v_p > 0}\big)$, avec $(\alpha, \beta) = (1, 1)$. Ambiguïté : la somme porte-t-elle sur tous les voxels (les $\tilde v_p$ négatifs pénalisent alors) ou seulement sur les voxels couverts ? À documenter.
- **Métriques des figures 4 et 5** : la couverture vaut $\frac{\sum_p \mathbb 1_{\tilde v_p>0}}{F_{max}}$, où $F_{max}$ est le nombre de voxels libres. La qualité moyenne de lien vaut $(P_{TX} - S_{RX})\cdot\overline{\tilde v} + S_{RX}$ en dBm, calculée sur les voxels couverts.

### 2.3 µ-connexité (théorie des graphes)
- **Graphe des équipements** : $G_O = (O, E)$, avec une arête $(o_k, o_l)$ si $P_{TX} - PL[o_k, o_l] > S_{RX}$. Les liens unidirectionnels sont supprimés (avec $X \ne 0$, $PL$ peut différer selon le sens).
- **Arête-connexité** $\lambda(G)$ : nombre minimal d'arêtes à retirer pour déconnecter le graphe. La contrainte s'écrit $\lambda(G_O) \ge \mu$.
- **Théorème de Menger** : $\lambda(G) \ge k$ si et seulement si toute paire de nœuds est reliée par $k$ chemins arête-disjoints. Autrement dit, le réseau survit à $k-1$ pannes de liens (« opérationnel après deux pannes » pour µ = 3).
- **Inégalité de Whitney** : $\kappa(G) \le \lambda(G) \le \delta(G)$ (degré minimal). Cela donne un **filtre rapide** : si un nœud a un degré inférieur à µ, la solution est infaisable. C'est la « mutation de connectivité » du PIMRC, qui retire les nœuds de degré inférieur à $k$.
- **Conséquence** : $\lambda \le n - 1$, donc µ = 3 exige **au moins 4 nœuds**. C'est pourquoi la figure 5 commence à 4 équipements.
- **Calcul** : flot maximum / coupe minimum (Ford–Fulkerson) ou Stoer–Wagner ; `networkx.edge_connectivity`.

### 2.4 Optimisation multi-objectif
- **Problème (5)** : minimiser $F_{cost} = |O|$ et maximiser $F_{obj}$, sous la contrainte $\lambda(G_O) \ge \mu$, avec $O \subset A$.
- **Dominance de Pareto** : une solution $a$ domine $b$ si elle est au moins aussi bonne sur tous les objectifs et strictement meilleure sur au moins un. Le front de Pareto est l'ensemble des solutions non dominées.
- **NSGA-II** (Deb et al., 2002) : tri non dominé rapide en $O(MN^2)$, distance d'encombrement (*crowding*) pour la diversité, élitisme (μ + λ).
- **PREP-NSGA** (Chambon et al., MetaCom 2023), algorithme 1 de l'IWCMC :
  - initialisation **non aléatoire**, à partir de « cellules d'intérêt » extraites de la structure (chaque $A_i$) ;
  - **pas de croisement** : à chaque itération, $N_{Mu} = 160$ mutants sont produits à partir d'individus tirés au hasard ;
  - trois mutations : déplacer un nœud dans un cercle de rayon 2 m, retirer un nœud, ajouter un nœud n'importe où dans $A$ ;
  - **contrainte en « peine de mort »** : un mutant infaisable est rejeté ;
  - tri de Pareto sur $(F_{obj}, F_{cost})$, puis on garde les $N_{pop} = 40$ meilleurs, pendant $N_{It} = 300$ itérations.
- **Tableau II** : $\delta = 0{,}5$ m ; $P_{TX} = 20$ dBm ; $S_{RX} = -65$ dBm ; $(\alpha, \beta) = (1, 1)$ ; µ ∈ {0, 3} ; domaine 16 × 34 × 10 (en voxels de 50 × 50 × 25 cm, d'après le texte).
- **Remarque utile** : comme $|O|$ est entier (de 1 à 10), le front revient à résoudre, pour chaque $n$, un **problème de couverture maximale**. Ce problème est NP-difficile, mais la couverture est une fonction **sous-modulaire** : l'algorithme glouton garantit $(1 - 1/e) \approx 63\,\%$ de l'optimum (Nemhauser, Wolsey & Fisher, 1978). C'est une excellente référence pour valider ton algorithme génétique.

### 2.5 Protocole « avec jumeau » / « sans jumeau » (§V.C)
- On **optimise** dans l'environnement dégradé (tous les obstacles dans le matériau le plus absorbant), puis on **évalue** les solutions obtenues dans l'environnement avec jumeau (le « réel »). C'est un point crucial à respecter, sinon la comparaison n'a pas de sens.
- Il y a quatre scénarios : {avec, sans jumeau} × {µ = 0, µ = 3}, chacun dans un `pareto.json`.

## 3. Choix techniques et d'architecture

### Choix 1 – Traversée des voxels pour Ω et les longueurs traversées
| Option | Pour | Contre |
|---|---|---|
| **DDA 3D (Amanatides & Woo, 1987)** | Exact : liste ordonnée des voxels traversés et longueur dans chacun | À coder, mais simple |
| Bresenham 3D | Simple, c'est la méthode du PIMRC | Pas de longueur exacte, une seule cellule par pas |
| Échantillonnage le long du segment | Trivial | Imprécis, coûteux à pas fin |
| Lancer de rayons sur maillage (trimesh/embree) | Précis sur la géométrie réelle | Matériau par face à gérer |

**Aspects** : le **coût** est central. Il faut $|A| \times N_{voxels}$ trajets : par exemple 2 000 positions × 40 000 voxels = 80 millions de rayons. Cela impose de **précalculer et mettre en cache** la matrice $PL[a, p]$ (≈ 320 Mo en float32), de vectoriser (numpy/Numba), ou de sous-échantillonner les voxels cibles. Calcule l'ordre de grandeur avant de coder.

### Choix 2 – Interprétation de $L_{obs}$
Par mètre traversé, par voxel traversé, ou « par mur ».
**Aspects** : plausibilité physique, comparaison aux figures 4 et 5 (une hypothèse qui reproduit l'ordre de grandeur des courbes est probablement la bonne), étude de sensibilité dans le rapport.

### Choix 3 – Shadowing $X$
Options : $X = 0$ (déterministe, modèle moyen), ou $X$ tiré une fois par lien avec une graine fixe, ou Monte-Carlo.
**Aspects** : reproductibilité (le jury recalcule), asymétrie des liens (« unidirectional connections are dropped »), comparabilité à l'article.

### Choix 4 – Correspondance des matériaux
Une table déclarative `matériau IFC → catégorie du tableau I`, avec une catégorie par défaut. Pour les murs multicouches : couche par couche ou matériau dominant.
**Aspects** : généricité sur un IFC inconnu, cohérence avec les 18 % annoncés, traçabilité.

### Choix 5 – Voxels comptés dans la couverture
Voxels libres de tout le bâtiment, de chaque niveau, ou seulement les voxels intérieurs (hors extérieur et vides techniques).
**Aspects** : la définition de $F_{max}$ change directement le pourcentage de couverture et la réponse à Q20.

### Choix 6 – Implémentation de l'algorithme génétique
| Option | Pour | Contre |
|---|---|---|
| **Implémentation maison** | Exactement l'algorithme 1, individus de taille variable, facile à expliquer et modifier en 10 min | Écrire le tri non dominé (50 lignes) |
| pymoo | NSGA-II robuste, outils d'indicateurs (hypervolume) | Individus de taille variable et contrainte « peine de mort » peu naturels |
| DEAP | Flexible | API vieillissante, plus verbeuse |

**Aspects** : fidélité à PREP-NSGA, explicabilité à l'entretien, testabilité, vitesse.

### Choix 7 – Robustesse statistique
Plusieurs graines (par exemple 5), avec médiane et dispersion par point du front ; temps CPU déclaré ; référence gloutonne.
**Aspects** : un algorithme génétique est stochastique, un seul tirage ne prouve rien ; le budget de calcul est limité (5 jours).

### Choix 8 – Confrontation aux figures 4 et 5
Numériser les courbes (WebPlotDigitizer) et tracer les tiennes par-dessus avec les mêmes axes.
**Aspects** : quantifier l'écart, puis l'expliquer (interprétation de $L_{obs}$, pas vertical, $F_{max}$, matériaux, $X$, initialisation).

## 4. À maîtriser pour l'entretien
- **Écrire au tableau la formulation** (c'est demandé explicitement) : variables $O \subset A$, objectifs $\min |O|$ et $\max F_{obj}$, contrainte $\lambda(G_O) \ge \mu$, et définitions de $PL$, $\tilde v_p$ et $G_O$.
- Prédire l'effet d'un changement de paramètre : si $S_{RX}$ passe de −65 à −75 dBm, la portée augmente (+10 dB, soit environ ×3,2 en distance avec $n = 2$), la couverture monte et il faut moins de nœuds pour 90 % ; avec µ plus élevé, il faut plus de nœuds ; avec δ plus petit, le temps de calcul augmente fortement.
- Expliquer pourquoi µ = 3 impose au moins 4 nœuds (Whitney, $\lambda \le \delta \le n - 1$).
