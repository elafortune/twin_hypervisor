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
| 1.8 bis | Élément sans niveau | se fier à `get_container` d'ifcopenshell · **contrôler la relation IFC directe** | ↩ Règle `rattachement_spatial` : un élément absent de `IfcRelContainedInSpatialStructure` est signalé ; son niveau est déduit du placement | ifcopenshell déduit un niveau sans le dire : la porte A202 semblait sur Level 2 alors qu'elle n'est rattachée à rien (vu dans BIMvision) | — |
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

## Étape 4 – Ontologie et graphe de connaissances

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 4.1 | Étendre / aligner l'ontologie | `owl:equivalentClass` · **`rdfs:subClassOf`** · SKOS `closeMatch` | 🟡 Subsomption (`ssi:Door ⊑ s4bldg:Door`, `ssi:Dwelling ⊑ bot:Zone`) ; socle recopié sans modification | L'équivalence engage dans les deux sens (risque d'incohérence) | — |
| 4.2 | TBox / ABox | un seul fichier · **séparés** | `ontology.ttl` = socle + extension ; `kg.ttl` = instances | Exigé par l'énoncé, validation `-e ontology.ttl` | — |
| 4.3 | Source du graphe | IFC · **`geometry.json`** | `geometry.json` (+ `parametres.json`) | Modules découplés (0.5) ; la chaîne IFC → M1 → M2 reste automatique | — |
| 4.4 | IRI des instances | nom · UUID · **GlobalId** | `…/kg/<type>/<GlobalId encodé>` | Stables d'une exécution à l'autre ; uniques malgré les deux `B202` | — |
| 4.5 | Bibliothèques | **rdflib + pySHACL** · pyoxigraph · Jena/Fuseki · owlready2 | rdflib + pySHACL | pySHACL est l'outil du kit ; pur Python ; ~1 000 triplets | gros IFC trop lent (pyoxigraph pour SPARQL) |
| 4.6 | Raisonnement | aucun · RDFS · OWL-RL · **matérialiser à la génération** | `isConnectedTo` écrit dans les deux sens ; types les plus précis écrits ; RDFS seulement à la validation | SPARQL sans raisonneur doit voir les deux sens | — |
| 4.7 | Propriétés du socle à domaine inadapté | réutiliser · **créer une propriété dédiée** | 🟡 `ssi:linksSpace` pour les escaliers (pas `ssi:connects`, domaine Door) ; `ssi:ExitDistance` + `exitFrom/exitVia/exitDistance` (pas `from/to/hasDistance`) | Le domaine est une règle d'inférence : l'escalier deviendrait une porte, la distance vers une sortie violerait F7 | — |
| 4.8 | Logement | préfixe du nom · **composante connexe avec sortie** | 🟡 Composante connexe, recoupée par le préfixe ; lien `ssi:inDwelling` (pas `bot:hasSpace`, F1) | Règle générique, ne dépend pas des noms | immeuble avec hall commun (tout est connexe) |
| 4.9 | Paramètres personnels | constantes · **nœud unique `ssi:Parameters`** | Toutes les valeurs de `parametres.json` (2 imposées + 6 ajoutées + origine du feu) | F4/F5 et « paramètre personnel » | — |
| 4.10 | Formes F3–F6 avant M4 | échouer · désactiver à la main · **différer automatiquement** | Différées tant que `devices.json` est « non calculé » | Le graphe statique les viole forcément (pas d'équipement) | — |
| 4.11 | Formes maison | aucune · **9 formes (M1–M9)** | Violation pour les invariants (évacuabilité, surface, GlobalId unique, un seul nœud Parameters…) ; avertissement pour la complétude (symétrie écrite, distance par liaison, largeur de porte) | Anticiper les formes cachées sans rejeter l'exemple minimal du kit | une forme cachée contredit un choix |
| 4.12 | Q07 / Q08 (plus court chemin) | SPARQL seul · **SPARQL pour extraire le graphe pondéré + Dijkstra en Python** | Hybride | SPARQL 1.1 ne calcule pas de plus court chemin pondéré | — |
| 4.13 | Anomalies dans le graphe | non · **oui (`ssi:ModelAnomaly`)** | 🟡 Incluses avec règle, description, traitement, éléments concernés | L'agent M6 peut les citer | une forme cachée les gêne |
| 4.14 | État initial | aucun · **`hasStatus Normal`** | 🟡 Normal sur tous les espaces | État initial de Pang ; mis à jour par M5 | — |

## Étape 5 – Évacuation dynamique

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 5.1 | Architecture du rejeu | calcul en mémoire puis écriture · **mise à jour du graphe RDF à chaque pas** | Observations insérées en SOSA, état mis à jour par SPARQL UPDATE, graphe de routage extrait par SPARQL | Fidèle à l'algorithme 1 de Pang ; le graphe reste la source de vérité | durée (17 s ici) trop longue sur un gros scénario |
| 5.2 | Persistance de l'état Dangerous | réversible · hystérésis · **verrouillé** | 🟡 Verrouillé (`ssi:dangerSince`) | Prudence : un espace passé à 60 °C reste suspect ; dans ce scénario les valeurs ne redescendent pas, donc sans effet | scénario où la température redescend |
| 5.3 | Seuils (0,0328 /m, 60 °C, 1 000 ppm) | en dur · **valeurs de l'énoncé surchargeables par `parametres.json`** | Constantes nommées + clés optionnelles (`seuil_danger_temperature_degC`…) | Règle « jamais en dur » ; le kit ne les fournit pas dans les paramètres | — |
| 5.4 | Lignes du JSONL | à partir de l'alarme · **à chaque pas** | Chaque pas (61), chaque espace occupé (caméra > 0), 2 stratégies : 410 lignes | Le schéma demande « une ligne par pas » ; avant l'alarme, action « pas d'évacuation » | — |
| 5.5 | Stratégie 1 | détour réactif (tableau 7 de Pang) · route statique pure · **les deux** | ↩ Route statique (champ `route`) + variante « détour réactif » (champ `route_detour_reactif`) : l'occupant suit le plan, s'arrête dans le dernier espace sûr avant le premier espace dangereux et repart de là ; sinon il est bloqué en chemin | Comparer avec et sans détour (demande du 10/11) ; coût ≈ 30 lignes ; le schéma n'autorise que les stratégies 1 et 2, d'où un champ et non une stratégie 3 | — |
| 5.6 | Danger : pénalité ou contrainte dure | pénalité 1 000 m (Pang) · **contrainte dure (F8)** | Espaces dangereux retirés ; route = `null` sinon ; la route « pénalité » est jointe à chaque ligne pour comparaison | La pénalité renvoie une route qui traverse le feu (1 026 m à t = 180 s) | — |
| 5.7 | Occupants dans un espace dangereux | exclure le départ du contrôle · **route = null + secours prioritaire** | 🟡 null (F8 interdit `routeFor` un espace dangereux) | Respect strict de F8 | — |
| 5.8 | Action sans route sûre | **confinement + signalement** · espace sûr le plus éloigné | Confinement porte fermée, signalement aux secours avec position et nombre | Consigne classique en l'absence d'issue | — |
| 5.9 | Routes dans `kg.ttl` | toutes · **seulement celles du dernier pas** | Routes courantes (état final) ; historique dans le JSONL | F8 s'applique à l'état final : une route ancienne traverserait un espace devenu dangereux | — |
| 5.10 | Capteurs du scénario | `ssi:SmokeDetector` · **`sosa:Sensor` seul** | ✅ `sosa:Sensor` (validé 10/11 : l'énoncé distingue capteurs de danger et équipements de sécurité) | Ne pas confondre capteurs du scénario et équipements placés par M4 (sinon F3/F6 faussés) | M4 doit réutiliser ces capteurs |
| 5.11 | Q15–Q19 | JSONL · **SPARQL sur le graphe + planificateur** | Q15, Q16, Q19 en SPARQL pur ; Q17, Q18 : état par SPARQL + Dijkstra ; recoupés avec le JSONL dans les tests | Exigence « par SPARQL » ; prépare les outils de M6 | — |

| 5.12 | Q18 « plus aucune route sûre » | instant où la route est coupée · instant où la chambre devient dangereuse | ✅ Route coupée (180 s) | Validé 10/11 : l'accent est mis sur les routes vers les sorties | — |
| 5.13 | Espaces sans caméra | ignorer · **signaler** | ✅ Chaque ligne liste les espaces dangereux occupables sans comptage | Validé 10/11 : risque de personnes bloquées non vues | M4 : placer des caméras / compteurs |

## Étape 6 – Voxels, matériaux, positions autorisées

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 6.1 | Outil de lancer de rayons | trimesh (+ embree) · Open3D · **rayons verticaux en numpy** | 🟡 Rayons verticaux uniquement, barycentriques en XY (Möller–Trumbore avec direction (0, 0, 1)) | Voxelisation (parité) et plafonds n'ont besoin que de rayons verticaux ; aucune dépendance ajoutée | M3 a besoin de rayons obliques (on écrira alors une traversée de voxels DDA) |
| 6.2 | Domaine de la grille | boîte du bâtiment · **emprise des espaces occupables** | xy = emprise des espaces (→ 16 × 34 voxels de 0,5 m, exactement l'IWCMC) ; z = plancher du Level 1 au sommet du Level 2 | Reproduit le domaine de l'article | — |
| 6.3 | Pas vertical | 0,5 m · **0,25 m** | `pas_grille_vertical_m` (défaut : la moitié du pas horizontal = 0,25 m, texte de l'IWCMC) → 24 couches | L'article annonce 50 × 50 × 25 cm mais « n = 10 » (soit 2,5 m seulement) : incohérence notée | le jury tranche autrement |
| 6.4 | Quand un voxel est-il un obstacle ? | centre du voxel dans l'élément · **toute occupation > 0** (échantillonnage 5 × 5 colonnes par voxel) | Obstacle dès qu'un élément l'occupe ; fraction occupée conservée | Le test au centre « perd » les cloisons de 12 cm (murs troués) | sur-épaississement gênant (voir doute X-2) |
| 6.5 | Éléments obstacles | **murs, dalles, toit, plafonds (IWCMC) + portes** · + fenêtres · + mobilier | Murs, dalles, toit, faux plafonds, portes ; fenêtres, mobilier, escaliers exclus | Liste de l'IWCMC ; les portes ont leur colonne dans le tableau I | — |
| 6.6 | Matériau d'un élément multicouche | couche par couche · **catégorie dominante (épaisseur des couches significatives)** + composition conservée | Table déclarative nom IFC → catégorie (plâtre, béton, mur porteur, bois) ; air, isolant, ossature métal ignorés | Résolution 0,5 m ≫ épaisseur des couches ; la composition reste disponible pour M3 | M3 veut sommer les couches |
| 6.7 | Positions autorisées A | sol · **plafond** | Rayon vers le haut depuis plancher + 0,5 m, premier impact sur couverture / dalle / toit, au-dessus d'un espace occupable du niveau | Fidèle à l'IWCMC (« surfaces labeled as roof ») | — |
| 6.8 | Stockage | JSON · **`.npz` + résumé dans `geometry.json`** | `sorties/grille_voxels.npz` (uint8 / float16) ; `geometry.json` : résumé `voxels` + liste `positions_autorisees` | Taille (13 056 voxels) et lecture rapide par M3/M4 | — |

## Étape 7 – Reproduction IWCMC

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 7.1 | Lecture de L_obs (dB/m) | 1 : × longueur traversée · **2 : une fois par voxel obstacle** · 3 : dB/cm | ✅ Option 2 principale, option 1 en sensibilité (validé 10/11 : rester sur les valeurs de l'article) | Équation (2) : somme sur les obstacles de Θ sans facteur de longueur ; obstacles = voxels (§III.A) | les auteurs précisent |
| 7.2 | Résultat principal | valeurs ajustées · **valeurs du tableau I** | `pareto.json` = tableau I tel quel ; variante × 30 dans `sorties/iwcmc/` pour expliquer l'écart | Le jury est l'auteur de l'article : comparer à ses vraies valeurs | — |
| 7.3 | Traversée des voxels | DDA exact · **échantillonnage tous les 5 cm** (vectorisé) | Échantillonnage, voxels distincts comptés une fois | 932 × 8 100 rayons en 5 min ; ≥ 5 échantillons par voxel | coins de voxel manqués gênants |
| 7.4 | Point d'émission | impact au plafond · **voxel libre juste dessous** | Lecture I-10 | Sinon les équipements ne se voient plus (rayon le long du plafond) | — |
| 7.5 | Shadowing X_σ | 0 · **tiré une fois par couple, graine fixée** · Monte-Carlo | Tirage unique (équipement → voxel, équipement → équipement orienté) | Reproductible ; asymétrie des liens | — |
| 7.6 | Qualité moyenne de lien | moyenne sur les voxels couverts · **moyenne sur tous les voxels (non couvert = S_RX)** | ↩ Lecture I-5 révisée après comparaison à la figure 4 (a) | Seule lecture croissante comme l'article (« relative coverage ») | — |
| 7.7 | Algorithme génétique | pymoo · DEAP · **maison** | PREP-NSGA maison (tri non dominé + encombrement, 3 mutations, peine de mort, initialisation par cellules d'intérêt) | Fidèle à l'algorithme 1, explicable | — |
| 7.8 | Validation de l'algorithme | aucune · **référence gloutonne** | Glouton (garantie 1 − 1/e) utilisé pour l'étude de sensibilité | Contrôle indépendant de PREP-NSGA | — |
| 7.9 | Robustesse statistique | 1 graine · **5 graines** | ✅ 5 graines pour les scénarios principaux (médiane, min, max) | Un algorithme génétique est stochastique | — |
| 7.10 | Campagne de comparaison | quelques variantes à la main · **campagne automatisée** | 12 expériences (A–L) : facteur, lecture, S_RX, domaine, shadowing, part de plâtre, technologies, poids, précision, graines, itérations ; comptes par groupe de matériau pour tout faire varier sans relancer le lancer de rayons | Demande du 10/11 : comparaison approfondie ; voir `comparaison.md` | — |

## Étape 8 – Déploiement SSI

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 8.1 | Formulation | un MILP global · algorithme génétique de M3 · **séquentielle (détecteurs → déclencheurs → caméras → réseau)** | Séquentielle, chaque sous-problème exact | Petits problèmes exacts, explicables au tableau, statut et gap fournis | l'optimum global est demandé |
| 8.2 | Solveur | PuLP + CBC · OR-Tools · scipy.milp · **HiGHS (`highspy`)** | HiGHS, licence MIT ; seule dépendance ajoutée à cette étape | Libre, rapide, statut et gap directs | — |
| 8.3 | Détecteurs : que couvrir ? | disque de 5 m quel que soit l'espace · **chaque cellule couverte par un détecteur DU MÊME espace, en vue directe** | 🟡 Couverture par espace (portes supposées fermées) ; `coversSpace` = l'espace où il est installé | La fumée ne traverse pas les cloisons ; sens clair pour F3 | règle plus souple acceptée par le jury |
| 8.4 | Type de détecteur | chaleur en cuisine d'emblée · **fumée partout** | Fumée partout | La demande D1 (M6) porte justement sur le passage de la cuisine en chaleur | — |
| 8.5 | Déclencheurs : distance | euclidienne · **de cheminement (graphe de visibilité dans le plateau ouvert)** | Distance de marche, plateaux reliés par ouvertures fusionnés | Label de `ssi:distanceToExit` ; distance réaliste | — |
| 8.6 | Nombre de déclencheurs | **un par sortie** · minimum couvrant toutes les sorties | ✅ Un par sortie (validé) : 4 déclencheurs à 0,4 m de leur sortie ; `distanceToExit` sans ambiguïté. Option `declencheur_un_par_sortie: false` → minimum (2 pour 4 sorties, jusqu'à 6,6 m) | Usage NF S 61-970 ; une distance par déclencheur (lève S-2) | — |
| 8.7 | Chemins d'évacuation | ligne centrale · bande · **polyligne espace → passages → sortie, à hauteur de visage** | 20 chemins (un par espace occupable, sortie la plus proche selon M1), échantillonnés à 0,25 m dans les voxels libres (182 cellules) | Cohérent avec M1 / M5 ; couverture 100 % faisable | — |
| 8.8 | Caméras | 2D (PIMRC) · **3D : frustum 90° × 60°, portée 8 m, ligne de vue dans les voxels** | 8 azimuts × 2 inclinaisons (20°, 45°) sur les positions A, pose à 2,4 m (ou juste sous le faux plafond) : 7 184 candidats | Mode 3D attendu | plus d'orientations si couverture infaisable |
| 8.9 | Full-view | contrainte · objectif secondaire « somme » · **objectif secondaire lexicographique max-min puis somme** | Phase 1 : nombre minimal N* (18) ; phase 2a : à N* + k caméras, maximiser le full-view MINIMAL par chemin ; 2b : à ce minimum, maximiser le total. k = `cameras_supplementaires_full_view` (défaut 0) | La « somme » sacrifiait les chemins courts (B102, B103 à 0 %, alors que 88–93 % y étaient atteignables) ; le max-min prouve qu'à 18 caméras un minimum > 0 est impossible. Compromis : k = 1 → min 10 % ; k = 2 → min 62,5 %, global 86 % ; k = 3 → 79 % | le jury veut un full-view minimal garanti (k = 2) |
| 8.10 | Zones de détection | une par niveau · une par espace · **une par niveau et par logement** | 4 zones (A/B × Level 1/2) | F6 ; localisation de l'alarme par logement | — |
| 8.11 | Réseau | ignoré · **modèle de M3 + relais si non connexe** | λ = 39 (tableau I) et 1 (× 30) : connexe, aucun relais | Réutilise M3 | — |
| 8.12 | Formes F3–F6 dans la chaîne | toujours · selon `devices.json` · **selon l'étape** | Différées pour M1–M3 seulement ; actives dès M4 | Corrigé après un échec : un `devices.json` d'un run précédent activait F3–F6 dès M2 | — |

## Étape 9 – Agent neuro-symbolique (M6)

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 9.1 | Moteur d'inférence | **Ollama** · llama.cpp · vLLM | Ollama (déjà installé, API REST `/api/chat`, outils, sortie JSON contrainte) | CPU seulement (pas de CUDA) ; démontrable hors ligne | — |
| 9.2 | Modèle | **qwen2.5:14b** · llama3.1:8b · mistral:7b · qwen3:4b | 🟡 qwen2.5:14b (déjà quantifié en 4 bits : Q4_K_M, 9 Go, 14,8 G paramètres nominaux « 14B », cité comme candidat par `theorie/M6` ; Apache 2.0), choisi par le banc d'essai (voir tableau ci-dessous) | Seul à 20/20 et sans argument faux ; dans la borne 3–14 B | la latence est rédhibitoire à l'entretien (voir doutes A-6) |
| 9.3 | Cadre d'agent | LangChain / LangGraph · smolagents · **boucle écrite à la main** | Boucle ReAct bornée (~80 lignes, `agent.py`) | Journal exact de chaque appel, aucun appel caché, modifiable sans assistant | — |
| 9.4 | Réponse aux questions | texte → SPARQL libre · **outils paramétrés (un par intention) + SPARQL libre en secours** | 19 outils génériques ; le LLM choisit l'outil et ses arguments ; la RÉPONSE est le résultat de l'outil | Le LLM ne recopie jamais un GlobalId ; requêtes réellement exécutées tracées ; marche sur un autre IFC (aucun nom en dur) | — |
| 9.5 | Fin de la boucle | le LLM décide de s'arrêter · **arrêt symbolique** | Arrêt dès qu'un outil réussit avec le bon type (ensemble/valeur) ; sinon l'erreur est renvoyée au LLM (≤ 3 tours) | Un appel LLM par question au lieu de deux : temps divisé par 2 sur CPU | une question demande plusieurs outils |
| 9.6 | Contexte donné au LLM | rien · **résumé du bâtiment généré par SPARQL** | Niveaux, logements, espaces (nom court, nom long), sorties : ~2 200 jetons, identiques d'une question à l'autre (cache de préfixe d'Ollama) | Le LLM doit relier « porte d'entrée du logement B » à B101 et lever « B202 » ambigu | bâtiment très grand (dépasser le contexte) |
| 9.7 | Contrôle des réponses | aucun · **comparaison à la référence sans LLM** | `conforme_reference` dans answers.jsonl + `agent_resume.json` ; un écart est signalé, jamais corrigé | Honnêteté ; détecte une régression du modèle | — |
| 9.8 | Demandes : pipeline | LLM décide · **LLM → plan JSON contraint → règles → SHACL sur copie → adaptations → ordre lexicographique → justification LLM** | `demandes.py` ; le veto est du code | Le LLM ne peut pas contourner une forme ; décision rejouable | — |
| 9.9 | Ordre de décision | somme pondérée · **lexicographique** | (sécurité : conformité SHACL, part des espaces occupables détectés) > (accessibilité : F4/F8) > (sobriété : nombre d'équipements) > satisfaction de la demande | Politique imposée « sécurité > accessibilité > sobriété » ; la satisfaction ne départage qu'à égalité | — |
| 9.10 | D1 – cuisine en chaleur | **accepter** · dédoubler · refuser | Acceptée : DF de A103 → HeatDetector (F3 toujours vraie : HeatDetector ⊑ Detector) | Aucune forme violée | un rayon de couverture propre aux détecteurs de chaleur est fourni (`detecteur_chaleur_rayon_m`, recalcul automatique) |
| 9.11 | D2 – déplacer l'équipement de A201 | accepter · **refuser** · relais en plus | Refusée (veto F3 : le couloir A201 ne serait plus détecté) ; le relais est écarté par sobriété car le réseau est DÉJÀ connexe (M4) | Sécurité d'abord, puis sobriété | le réseau n'est pas connexe (le relais serait alors retenu) |
| 9.12 | D3 – retirer les détecteurs du Level 2 | accepter · refuser · **détection de chaleur temporaire** | Acceptée avec adaptation : retrait (veto F3) remplacé par 10 détecteurs de chaleur temporaires placés par le MILP de M4 | Conformité maintenue ; les détecteurs de chaleur sont insensibles aux poussières de chantier, ce qui répond au motif ; à sécurité symbolique égale, la satisfaction départage | tu juges la détection de chaleur moins sûre (alors : refus) — doute A-1 |
| 9.13 | D4 – route habituelle à 200 s | accepter · **refuser + route sûre** · aucune route → mise à l'abri | Refusée pour les 5 espaces du Level 2 du logement A : la route habituelle traverse A101 (Dangerous) → F8 violée ; à 200 s les deux sorties du logement A (A101, A102) sont dangereuses et aucune route sûre n'existe → mise à l'abri sur place, position signalée aux secours | F8 évaluée sur une copie du graphe dans l'état de t = 200 s | — |
| 9.14 | Effet des demandes | simulé seulement · **appliqué à kg.ttl (commit)** | kg.ttl final = état après M5 + D1 + D3 ; routes de D4 non écrites (valables à 200 s, pas à l'état final) ; devices.json reste le déploiement de M4 | « Modifications appliquées » ; graphe final re-validé par SHACL | le jury attend devices.json mis à jour |
| 9.15 | Reproductibilité | recalcul obligatoire · **journal + rejeu** | Température 0, graine 0, digest du modèle ; `llm_journal.jsonl` ; `TWINHYP_LLM_REJEU=<journal>` rejoue sans Ollama ; M6 repart de `kg_avant_agent.ttl` (idempotent) | Le jury recalcule à partir des sorties | — |
| 9.16 | Vitesse de SHACL dans M6 | graphe complet · **copie sans observations SOSA** | Les ~20 000 triplets d'observations sont retirés des copies (aucun delta ne les touche ; M10 vérifiée sur le graphe initial) | Mesuré sur le run réel : 106 s hors LLM pour les 12 validations + le MILP de D3 (≤ 9 s par validation), contre 33 s pour une validation du graphe complet | une demande porte sur les observations |

### Banc d'essai des modèles (CPU, Ollama 0.40, température 0)

| Modèle | Questions testées | Conformes à la référence | Temps par appel (à chaud) | Remarques |
|---|---|---|---|---|
| **qwen2.5:14b** | 20 (run complet, deux fois) | **20 / 20** | 13–30 s (premier appel 240 s : chargement) | Q08 auto-corrigée après l'erreur « ambigu » |
| llama3.1:8b | Q07, Q08, Q12, Q17 | 2 / 4 | ~20 s | Q12 : mauvais outil ; Q08 : booléen envoyé en texte (« False »), bug de mon côté corrigé depuis |
| mistral:7b | essai initial | — | — | appels d'outils dupliqués ; banc arrêté par manque de mémoire |
| qwen3:4b | essai initial | — | — | raisonnement (« thinking ») trop long ; banc arrêté par manque de mémoire |

### Fumée ou chaleur : comparaison mesurée (`python -m twinhyp detecteurs --out sorties`)

Le kit laisse le type libre (`theorie/M4` §1 : « détecteurs automatiques (fumée ou chaleur) » ; l'ontologie et `devices.schema.json` acceptent les deux ; `theorie/M6` propose pour D3 « détection temporaire (chaleur, autonome) »). Comparaison sur les mesures de `observations.csv` (signal de l'espace = signal vu par un détecteur placé dans l'espace) ; fumée : seuil de M5 (0,0328 /m) ; chaleur statique EN 54-5 classe A1 (réponse entre 54 et 65 °C) ; chaleur thermovélocimétrique A1R approchée par +10 °C en 60 s (approximation) ; danger : seuils de M5.

| Espace | Fumée | Chaleur A1R | Chaleur A1 (54–65 °C) | Danger | Marge fumée / A1 |
|---|---|---|---|---|---|
| A103 Kitchen (feu) | 70 s | 80 s | 110–130 s | 120 s | 50 s / 10 à −10 s |
| A101, A102 | 120 s | 130 s | 170–190 s | 180 s | 60 s / 10 à −10 s |
| A201 Hallway (Level 2) | 200 s | 220 s | 280–300 s | 290 s | 90 s / 10 à −10 s |
| A202–A204 (Level 2) | 330 s | 390 s | 440–480 s | 460 s | 130 s / 20 à −20 s |
| A205 Utility | 470 s | jamais (49,8 °C max) | jamais | jamais | — |

| Déploiement | 1re alarme du bâtiment (A1R / A1 54 °C / A1 65 °C) | 1re alarme du Level 2 (A1 54 °C) |
|---|---|---|
| Tout fumée (M4) | 70 s | 200 s |
| Cuisine en chaleur (D1) | 80 / 110 / 120 s | 200 s |
| Level 2 en chaleur (D3) | 70 s (inchangée : le feu est au Level 1) | 280 s (A1R : 220 s) |

| Rayon de couverture | Détecteurs (MILP M4, optimal) |
|---|---|
| 5,0 m (kit, fumée) | 20 |
| 3,54 m (surface surveillée ÷ 2) | 24 |
| 2,74 m (surface × 0,3) | 34 |

Lecture : un détecteur de chaleur statique alarme **au moment où l'espace devient dangereux** (marge −20 à +20 s) ; la fumée laisse 50 à 130 s. Le thermovélocimétrique est intermédiaire (10 à 60 s après la fumée).
- **Fumée par défaut dans M4** : justifiée par les mesures (marge ASET la plus grande) et par le nombre de détecteurs (rayon plus grand).
- **D1** : acceptée (F3 reste vraie, demande du kit « a priori acceptable »), mais elle a un coût mesuré : la 1re alarme passe de 70 s à 80 s (A1R) ou 110–120 s (A1). Recommandation à joindre à la décision : classe **A1R**.
- **D3** : l'adaptation chaleur ne retarde pas la 1re alarme du bâtiment dans ce scénario (feu au Level 1) ; elle retarde l'alarme locale du Level 2 de 20 s (A1R) ou 80 s (A1). Pour un feu qui naîtrait au Level 2 pendant les travaux, le retard serait celui du tableau par espace. L'alternative « refus » laisse le Level 2 sans détection. Adaptation maintenue, en A1R.
- Les rayons 3,54 / 2,74 m sont des ordres de grandeur (surface surveillée par un détecteur de chaleur environ deux à trois fois plus petite selon les règles d'installation) : à vérifier dans NF S 61-970 / CEN/TS 54-14.

Chaîne complète rejouée avec des détecteurs de chaleur (A1R, A1, rayon réduit) : `fumee_chaleur.md`. Alarme 70 s (fumée) · 80 s (A1R) · 130 s (A1) ; délai avant la première perte de route sûre 110 · 100 · 50 s ; réponses Q01–Q20 identiques ; D3 refusée quand les détecteurs sont déjà de chaleur. Le type est un paramètre (`detecteur_type`, défaut fumée).

### Run réel de M6 (qwen2.5:14b, 2026-11-11)

- Questions : 20 / 20 conformes, 21 itérations, 678 s (LLM 663 s).
- Demandes : D1 acceptée · D2 refusée (veto F3) · D3 acceptée avec adaptation (F3) · D4 refusée pour les 5 espaces (F8) ; 12 validations SHACL ; 706 s (LLM : plans 227 s, justifications 373 s).
- Total M6 : 1 400 s ; journal de 29 appels (`sorties/llm_journal.jsonl`), rejouable sans Ollama.
- Justifications : au premier run, le modèle lisait « sécurité > accessibilité > sobriété » à l'envers ; ordre réécrit en liste numérotée dans le prompt.

## Étape 10 – Généricité (second IFC)

| # | Question | Options envisagées | Choix final | Pourquoi | Revenir dessus si… |
|---|---|---|---|---|---|
| 10.1 | Second IFC | **bureaux NIBS (Office_A_20110811)** · clinique NIBS · FZK-Haus | Bureaux, comme le conseille le kit (même série que le duplex, 5 fois plus d'espaces) | Conseil explicite de `plan_execution.md` | le jury fournit un autre fichier |
| 10.2 | Source du fichier | portail NIBS · Wayback Machine · **miroir public identique** | `ThatOpen/engine_web-ifc`, SHA-256 noté | Portail hors service ; la Wayback Machine bloque les téléchargements automatiques (pas de contournement) | — |
| 10.3 | Observations | aucune · **générateur synthétique sur le graphe** | `python -m twinhyp scenario` : retard et atténuation par liaison, profils du kit | Réutilisable pour tout IFC ; reproductible (graine) | le jury fournit un scénario |
| 10.4 | Questions et demandes | celles du kit telles quelles · **reformulées avec les noms du bâtiment** | `data/bureaux/questions_bureaux.json`, `demandes_bureaux.json` | Les questions du kit nomment A202, B101… | — |
| 10.5 | Échecs révélés | paramétrer au cas par cas · **règles générales** | G-1 à G-7 (`generalite.md`) ; duplex identique avant / après | Le jury apportera un IFC inconnu : il faut des règles, pas des exceptions | — |
| 10.6 | Tenir 10 min | tout recalculer · **mode rapide par paramètres** | grille 1 m, M3 sur 40 positions sans ×30, `validation_kg_intermediaire = false` | Le kit prévoit « un mode rapide paramétrable pour M3 » ; le graphe final reste validé en entier | machine plus rapide (repasser en mode complet) |
| 10.7 | D4 sur un grand bâtiment | une validation par route · **validation en lot** | une passe SHACL pour toutes les routes ; violations attribuées par `sh:focusNode` ; repli unitaire si une violation n'est pas attribuable | 42 s par validation × ~80 → 8 validations | — |

## Points ouverts à trancher

| Sujet | Options | Échéance |
|---|---|---|
| Q01 : A105/B105 comptés à Level 2 ? | oui (double hauteur) · non (rattachement) | avant M6 (étape 9) |
| Q13 vide (aucun passage A ↔ B) | réponse vide justifiée · question piège à signaler | M6 |
| Format de `pareto.json` | liste · objet | dès qu'on écrit M3 |
