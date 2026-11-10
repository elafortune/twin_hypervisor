# Choix réalisés, étape par étape

> Vue d'ensemble de toutes les décisions : la question posée, les options sérieuses, le choix retenu, pourquoi, et **quand revenir dessus**. Validé par moi sauf mention « choix de l'assistant ». Codes D… = `docs/etape0a2.md`, C… = `docs/guide_etapes_0_a_2.md`.

**Légende du statut** : ✅ validé · 🟡 choix de l'assistant, à confirmer · ↩ ajusté après coup

---

## Étape 0 – Squelette et outillage

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 0.1 | Visibilité du dépôt | public · **privé + jury invité** | Privé, articles et PDF exclus (`.gitignore`) | Le kit interdit de diffuser les articles | — |
| 0.2 | Que versionner du kit | tout · **entrées seulement** | `data/` à l'octet près (`.gitattributes`) | Le jury rejoue sans le kit | — |
| 0.3 | Environnement Python | Python 3.14 système · venv · **conda 3.11** | conda `twinhyp`, Python 3.11, `requirements.lock` | ifcopenshell, pyshacl, highspy sûrs en 3.11 | une dépendance exige une autre version |
| 0.4 | Interface de lancement | **argparse** · typer · click · notebook | `python -m twinhyp run / valider / visualiser`, option `--etapes` | Standard, sans dépendance, modifiable à l'entretien sans IA | — |
| 0.5 | Communication entre modules | appels en mémoire · **fichiers de sortie** | Chaque module lit les sorties du précédent (M2 lit `geometry.json`, pas l'IFC) | Modules testables et relançables seuls | coût d'E/S trop élevé sur un gros IFC (peu probable) |
| 0.6 | Contrôle des sorties | à la fin · **à chaque étape** | JSON Schema (ligne par ligne pour JSONL), SHACL pour `kg.ttl` | Une sortie fausse arrête la chaîne tout de suite | — |
| 0.7 | Tests | unitaires seuls · **3 niveaux** | unitaires · conformité · intégration (`-m integration`) | Qualité logicielle notée, non-régression | — |
| 0.8 | Traçabilité d'exécution | log texte · **`execution.json`** | machine, versions, graine, durées par étape | « Déclarer le matériel et les temps de calcul » | — |
| 0.9 | Structures internes | dicts · **dataclasses** · pydantic | dataclasses + conversion en dict ; le schéma JSON fait foi | Lisible, sans dépendance | — |
| 0.10 | Paramètres | constantes · **`parametres.json`** | Toujours lus depuis le fichier passé en argument | F4/F5 parlent de « paramètre personnel » | — |
| 0.11 | `pareto.json` | un objet · **liste de 4 scénarios** | Liste, chaque élément validé par le schéma | Le schéma décrit un seul scénario, l'énoncé en demande 4 (ambiguïté) 🟡 | le jury précise le format attendu |

## Visualisation

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| V.1 | Bibliothèque | matplotlib · **plotly** · pyvista · viewer web IFC (That Open) | plotly, HTML hors ligne | Survol, zoom, couches cliquables, aucun serveur | besoin de sélection d'objets IFC fine (viewer dédié) |
| V.2 | Source du plan 2D | IFC · **`geometry.json`** | `geometry.json` uniquement | Montre ce que la chaîne a compris, pas ce que dit l'IFC | — |
| V.3 | Vue 3D | aucune · **3D + vue de dessus** | Maillages IFC fusionnés par classe et niveau, menu niveau, vue orthographique | Surcoût modéré par rapport au 2D, indispensable pour M3/M4 (caméras, hauteurs) | temps de génération trop long sur le gros IFC (`--sans-3d`) |
| V.4 | Couche distances (étape 3) | toujours affichée · **cachée par défaut** | Activée en cliquant « Distances (pire point) » dans la légende | 40 tracés surchargent le plan | — |

## Étape 1 – Extraction IFC

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 1.1 | Identifiant des éléments | nom · **GlobalId** | GlobalId partout | Deux espaces s'appellent `B202` | — |
| 1.2 | Surface d'un espace | géométrique · **« GSA BIM Area »** · `NetFloorArea` | `surface_m2` = GSA BIM Area (repli géométrie) ; `surface_geometrique_m2` toujours fourni | Q05 et Q10 citent la propriété | ↩ la règle « écart > 5 % = anomalie » a été **abandonnée** : écart de 7–23 % partout = convention de mesure |
| 1.3 | Contour d'un espace | `IfcRelSpaceBoundary` · profil d'extrusion · **empreinte du maillage** | Union des triangles projetés (shapely) | Marche pour toute représentation IFC | contours trop lourds sur un gros IFC (simplifier) |
| 1.4 | Hauteur | propriété · **zmax − zmin** | Géométrique, recoupée avec les propriétés | — | — |
| 1.5 | Unités | supposer le mètre · **lire l'unité du fichier** | Échelle lue dans `IfcUnitAssignment` | L'IFC de l'entretien peut être en mm | — |
| 1.6 | Espace occupable | mots-clés · hauteur < 1,8 m · « niveau le plus haut » | **Mots-clés seulement** (roof, gaine, plenum…), surchargeables par `mots_cles_non_occupable` | ↩ « niveau le plus haut » retiré : un dernier étage est souvent habité | le gros IFC contient des locaux techniques mal nommés (ajouter la hauteur) |
| 1.7 | Détection des anomalies | correction silencieuse · ML · **règles génériques (invariants)** | Une règle par invariant, chaque correction écrite dans `anomalies` avec son traitement | 21 espaces : pas de données pour du ML ; il faut expliquer chaque constat | — |
| 1.8 | Niveau d'un élément | rattachement IFC · **altitude de la base** | Altitude de la base ; le rattachement IFC est contrôlé | L'escalier B est rattaché au toit | — |
| 1.9 | Dimensions d'escalier | propriétés · **géométrie** | Géométrie ; propriétés en pieds signalées | `RiserHeight` 0,6357 n'est pas en mètres | — |

## Étape 2 – Connectivité

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 2.1 | Source de connectivité des portes | IFC seul · chaîne de Pang seule · géométrie seule · **les 3 recoupées** | Vote à la majorité (≥ 2 sources sur 3) | Robuste si une source manque ; un désaccord révèle une anomalie | — |
| 2.2 | Quand un désaccord est-il une anomalie ? | tout désaccord · **seulement si la source IFC est minoritaire ou absente** | 🟡 IFC minoritaire = anomalie de maquette ; citation isolée de Pang ou de la géométrie = imprécision de méthode | Évite 2 fausses anomalies (cages A105/B105 citées par Pang à cause du chevauchement) | une erreur de maquette n'apparaît que via Pang/géométrie |
| 2.3 | Passages sans porte | ouvertures non remplies · **limites virtuelles + contact géométrique** | Contours à < 2 cm, sans chevauchement, sur ≥ 0,60 m, confirmés par des limites virtuelles IFC | Les 12 ouvertures non remplies sont des trous de meubles / toit | — |
| 2.4 | Définition d'une sortie | `IsFireExit` · `IsExternal` · **géométrie** | Porte bordant un seul espace intérieur ; `IsExternal` en recoupement | `IsFireExit` vaut le texte « IsFireExit » | — |
| 2.5 | Liaison escalier | foyer ↔ étage · **cage ↔ espace d'arrivée** | x105 ↔ x201 ; le foyer rejoint la cage par une ouverture | La volée est entièrement dans la cage double hauteur | — |
| 2.6 | Paire reliée par escalier **et** limite virtuelle | garder les deux · **garder « escalier »** | 🟡 seule la liaison escalier est gardée | La limite virtuelle A105–A201 est l'arrivée de la volée, pas un second passage | — |
| 2.7 | Liaisons orientées ? | **non orientées** · orientées | Non orientées dans `liaisons` ; orientées dans `distances` | La connectivité est symétrique, pas les distances | — |
| 2.8 | Outils à l'étape 2 | KG · Dijkstra · ML · **BFS de contrôle** | BFS d'évacuabilité seulement | KG à l'étape 4, Dijkstra aux étapes 3 et 5 | — |
| 2.9 | Espaces double hauteur (A105/B105) dans Q01 | comptés à Level 2 · **rattachés à Level 1 seulement** | 🟡 Level 1 (rattachement IFC et altitude de base) | Q01 = 10 espaces | à trancher avant M6 |

## Étape 3 – Distances d'évacuation

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 3.1 | Algorithme | formule de Pang (1 sommet intermédiaire) · **graphe de visibilité + Dijkstra** · grille 0,5 m + BFS / fast marching | Visibilité + Dijkstra (shapely + networkx), Pang calculé à côté | Exact sur tout polygone, généralise Pang ; la grille introduit une erreur ≈ δ·√2 | — |
| 3.2 | Point le plus défavorable | échantillonnage de l'espace · **sommets du contour** | Max sur les sommets | Le point géodésiquement le plus éloigné est un sommet (Suri, 1989) — c'est aussi ce que fait Pang | espaces à trous (poteaux) : les sommets des trous sont déjà inclus |
| 3.3 | Point cible d'une porte | position brute (dans le mur) · **projection sur le contour** | Point du contour le plus proche de la porte | La porte est dans l'épaisseur du mur, hors du polygone | — |
| 3.4 | Point cible d'une ouverture libre | **milieu du segment de contact** · point du passage le plus proche du pire point | Milieu | Simple et stable ; limite : surestime un peu dans les grands séjours ouverts | les distances servent à un critère fin (ajouter plusieurs sources le long du segment) |
| 3.5 | Escalier | dénivelé seul · course seule · **√(course² + dénivelé²)** | Distance dans l'espace de départ jusqu'au pied (en montant) ou à la tête (en descendant) + longueur de volée 4,85 m | Course mesurée sur l'empreinte de la volée (3,77 m ≈ 15 girons de 0,25 m) | réglementation qui majore les escaliers (coefficient) |
| 3.6 | Distances vers l'extérieur | liaison vers un nœud « EXTERIEUR » · **liste séparée `distances_sortie`** | Liste séparée | F7 exige deux espaces distincts ; l'extérieur n'est pas un `bot:Space` | — |
| 3.7 | Poids d'un itinéraire | **somme des distances orientées (pire point de chaque espace)** · distance réelle porte à porte | 🟡 Somme des distances de Pang | Convention de Pang ; majorant prudent | M5 a besoin de temps d'évacuation réalistes |
| 3.8 | Tolérance numérique | aucune · **1 cm** | Un segment qui longe un mur reste « dans » l'espace | Les segments sur le contour sont sinon rejetés par arrondi | — |

## Points ouverts à trancher

| Sujet | Options | Échéance |
|---|---|---|
| Q01 : A105/B105 comptés à Level 2 ? | oui (double hauteur) · non (rattachement) | avant M6 (étape 9) |
| Q13 vide (aucun passage A ↔ B) | réponse vide justifiée · question piège à signaler | M6 |
| Format de `pareto.json` | liste · objet | dès qu'on écrit M3 |
