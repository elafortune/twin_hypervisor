# Plan d'exécution – ordre des étapes, connaissances et lectures

> Établi le lundi 9 novembre 2026. Remise : **jeudi 12 novembre à 16h00**. Entretien : vendredi 13 novembre au matin.
> Il reste environ **3,5 jours** : le plan priorise les points sûrs et isole les tâches à risque (M3, M6).

## Principes d'ordonnancement

1. **Suivre les dépendances de données** : M1 → M2 → (M5, M3, M4) → M6. L'agent M6 vient en dernier, car il orchestre les outils des autres modules.
2. **Sécuriser tôt les points bon marché** : M5 ne dépend que du graphe et des observations, pas de M3 ni de M4. On le fait juste après M2, ce qui sécurise aussi les réponses Q15–Q19.
3. **Lancer tôt ce qui calcule longtemps** : les 4 scénarios PREP-NSGA de M3 (300 itérations × 160 mutants, plusieurs graines) tournent en arrière-plan pendant qu'on code M4.
4. **Le squelette d'abord, la qualité ensuite** : on crée dès le jour 1 la commande unique de reproduction et les tests de conformité aux schémas. Chaque module s'y branche au fur et à mesure (les 5 points de qualité logicielle s'obtiennent sans effort supplémentaire).
5. **Écrire le carnet de bord tous les jours**, y compris les impasses. Le rapport de 6 pages se rédige à partir du carnet, pas de mémoire le jeudi matin.
6. **Tester la généricité avant l'entretien** sur un second IFC public (voir étape 10).

## Calendrier prévisionnel

| Créneau | Étapes |
|---|---|
| Lun 9 (après-midi, soir) | 0 Squelette · 1 Extraction IFC · 2 Connectivité et anomalies |
| Mar 10 (matin) | 3 Distances d'évacuation · 4 Ontologie et graphe statique |
| Mar 10 (après-midi) | 5 Évacuation dynamique (M5) |
| Mar 10 (soir) | 6 Voxels, matériaux, positions autorisées |
| Mer 11 (matin) | 7 Reproduction IWCMC (M3), puis lancement des calculs en arrière-plan |
| Mer 11 (après-midi) | 8 Déploiement SSI (M4) |
| Mer 11 (soir) → Jeu 12 (matin) | 9 Agent neuro-symbolique (M6) |
| Jeu 12 (matin) | 10 Chaîne de bout en bout, tests, second IFC |
| Jeu 12 (jusqu'à 16h) | 11 Rapport, carnet, déclaration IA, dépôt Git partagé |
| Jeu 12 (soir) | 12 Préparation de l'entretien, **sans IA** |

---

## Étape 0 – Squelette du dépôt (≈ 1 h 30)

**Objectif** : un dépôt Git propre avec une commande unique, du type `python -m twinhyp run --ifc duplex.ifc --params parametres.json --obs observations.csv --out sorties/`, même si chaque module ne fait encore rien.

**Contenu** : `pyproject.toml` (versions figées), dossier `src/twinhyp/` avec un module par étape (`m1_geometrie`, `m2_graphe`, …), `tests/` (pytest), validation de chaque sortie avec `jsonschema` contre `schemas/`, et `carnet_de_bord.md`.

**Connaissances nécessaires**
- Git (commits atomiques et messages clairs : l'**historique complet** est évalué).
- Packaging Python moderne (`pyproject.toml`, environnement virtuel ou conda), interface en ligne de commande (`argparse` ou `typer`).
- pytest, et la validation JSON Schema (draft 2020-12).

**Lectures**
- Énoncé : section « Livrables » (relire mot à mot).
- Les 6 fichiers de `schemas/` : ce sont les contrats d'interface de la chaîne.
- Documentation `jsonschema` (Python), en particulier la validation des fichiers JSONL ligne par ligne.

**Critère de fin** : `pytest` passe, la commande crée les 8 fichiers de sortie (même vides mais conformes).

---

## Étape 1 – M1 : extraction IFC (≈ 3 h)

**Objectif** : niveaux, espaces (polygone, surface, hauteur, occupable), portes (largeur), escaliers, propriétés (« GSA BIM Area »), en **mètres** et en **coordonnées monde**.

**Connaissances nécessaires**
- Schéma IFC : hiérarchie spatiale, `IfcRelAggregates`, `IfcRelContainedInSpatialStructure`, jeux de propriétés.
- Placements locaux et composition de transformations homogènes 4×4.
- Unités IFC (`IfcUnitAssignment`), différences IFC2x3 / IFC4.
- API IfcOpenShell : `by_type`, `ifcopenshell.util.element.get_psets`, `ifcopenshell.util.placement`, `ifcopenshell.geom` (paramètre `USE_WORLD_COORDS`).
- Shapely : polygones, aire, projection 2D d'un maillage d'espace.

**Lectures**
- **[Pang] §4.1 et 4.1.1** (extraction des entités, tableau 1 de correspondance IFC → ontologie).
- Fiche `theorie/M1_jumeau_geometrique.md` §2.1.
- Documentation IfcOpenShell (docs.ifcopenshell.org) : « Hello world », `ifcopenshell.util` (element, placement, unit), `ifcopenshell.geom`.
- Documentation IFC2x3 de buildingSMART : `IfcSpace`, `IfcBuildingStorey`, `IfcDoor` (attributs `OverallWidth`/`OverallHeight`), `IfcRelDefinesByProperties`.

**Critère de fin** : réponses vérifiées **à la main** dans un visualiseur IFC (BIMvision ou le module BlenderBIM / Bonsai) pour Q01, Q05, Q10, Q12 et Q14. Noter dans le carnet ce qui a été vérifié à la main (exigé par la déclaration IA).

---

## Étape 2 – M1 : connectivité, sorties, escaliers, anomalies (≈ 3 h)

**Objectif** : la liste des `liaisons` (porte / ouverture / escalier), les portes de sortie et les `anomalies` de `geometry.json`.

**Connaissances nécessaires**
- Relations IFC `IfcRelSpaceBoundary`, `IfcRelVoidsElement`, `IfcRelFillsElement`, et la chaîne Mur → Ouverture → Porte de Pang.
- Différence entre limite physique et virtuelle, interne et externe.
- Repli géométrique : intersection de la boîte d'une porte avec les polygones des espaces dilatés (`buffer` de shapely).
- Graphes (networkx) : graphe non orienté typé, composantes connexes (chaque espace doit pouvoir atteindre l'extérieur).
- Notion de **contrôle de qualité de données** : invariants, règles de détection génériques.

**Lectures**
- **[Pang] §4.1.2 et figure 3** (connectivité virtuelle et par porte).
- Documentation IFC2x3 : `IfcRelSpaceBoundary`, `IfcOpeningElement`, `IfcRelFillsElement`, `IfcStair`/`IfcStairFlight`.
- Fiche M1 §2.2 et §2.5 (liste des invariants à tester).

**Critère de fin** : graphe de connectivité dessiné (networkx + matplotlib) et comparé au plan ; Q02, Q03, Q04, Q06, Q08, Q09, Q13 vérifiées à la main ; au moins 3 anomalies documentées avec leur traitement.

---

## Étape 3 – M1 : distances d'évacuation (≈ 2 h)

**Objectif** : une distance **orientée** par liaison, depuis le point le plus défavorable de l'espace jusqu'à la porte ou l'ouverture.

**Connaissances nécessaires**
- Graphe de visibilité dans un polygone (segment inclus dans le polygone : `polygon.covers(segment)`).
- Algorithme de Dijkstra sur ce graphe, plus courts chemins géodésiques.
- Propriété du point géodésique le plus éloigné (atteint en un sommet).
- Escaliers : longueur de volée à partir de la géométrie de `IfcStairFlight`.

**Lectures**
- **[Pang] §4.1.3 et figure 4** (formule $L = \max(L_{C_i}, L_{D_i})$).
- de Berg, Cheong, van Kreveld, Overmars, *Computational Geometry: Algorithms and Applications*, **chapitre 15 « Visibility Graphs »**.
- Fiche M1 §2.3.

**Critère de fin** : test unitaire sur un polygone en L dont on connaît la réponse à la main, puis Q07 vérifiée.

---

## Étape 4 – M2 : ontologie et graphe statique (≈ 4 h)

**Objectif** : `ontology.ttl` (socle étendu et aligné) et `kg.ttl` (niveaux, espaces, portes, sorties, `isConnectedTo`, `EvacuationDistance`, nœud `ssi:Parameters`) conformes à F1, F2 et F7 ; premières formes maison.

**Connaissances nécessaires**
- RDF/Turtle, IRI, littéraux typés ; RDFS (sous-classes, domain/range comme inférences) ; OWL (`SymmetricProperty`, `oneOf`).
- Hypothèse du monde ouvert contre validation en monde fermé (SHACL).
- SHACL : formes de nœuds et de propriétés, `sh:sparql`, rapport de validation ; pySHACL (`-e`, `-i rdfs`).
- SPARQL 1.1 : BGP, `FILTER`, agrégats, chemins de propriétés.
- rdflib : construction d'un graphe, sérialisation, requêtes.

**Lectures**
- **[Pang] §3 et figure 2** (structure de l'ontologie FE), et **tableau 4** (les 7 requêtes SPARQL, à réécrire avec ton vocabulaire).
- Spécification **BOT** : https://w3id.org/bot (classes et propriétés, exemples).
- Recommandation W3C **SOSA/SSN** (2017) : https://www.w3.org/TR/vocab-ssn/ , sections 4 (SOSA) et les exemples d'observation.
- **SAREF core** (https://saref.etsi.org/core/) et l'extension **SAREF4BLDG** (correspondance avec IFC).
- Recommandation W3C **SHACL** : https://www.w3.org/TR/shacl/ , sections 2 (formes), 4 (composants de contraintes), 5 (contraintes SPARQL).
- W3C Note *Defining N-ary Relations on the Semantic Web* (justifie `EvacuationDistance`).
- Livre de référence (facultatif) : Allemang & Hendler, *Semantic Web for the Working Ontologist*, chapitres RDFS/OWL et monde ouvert.
- Fiche `theorie/M2_graphe_connaissances.md` en entier (y compris le tableau de comparaison avec Pang, à reprendre dans le rapport).

**Critère de fin** : `pyshacl -s formes_publiques.ttl -e ontology.ttl -i rdfs kg.ttl` passe pour F1, F2 et F7 ; Q01–Q14 obtenues **par SPARQL** (et non plus par Python), ce qui prépare directement les gabarits de M6.

---

## Étape 5 – M5 : évacuation dynamique (≈ 4 h)

**Objectif** : observations SOSA dans le graphe, rejeu pas à pas (algorithme 1 de Pang), stratégies 1 et 2, contrainte dure F8, `evacuation_dynamique.jsonl`.

**Connaissances nécessaires**
- Patron d'observation SOSA (`madeObservation`, `observedProperty`, `hasFeatureOfInterest`, `hasSimpleResult`, `resultTime`).
- SPARQL UPDATE (`DELETE`/`INSERT … WHERE`) pour mettre à jour l'état.
- Dijkstra (preuve de correction, poids positifs), multi-sorties avec super-puits, graphe inversé ; BFS pour l'existence d'une route.
- Différence pénalité / contrainte dure (relaxation de type lagrangien).
- Notions de tenabilité en incendie (seuils de température et de CO, obscurcissement, Beer–Lambert).

**Lectures**
- **[Pang] §2.2, §4.2.2, §4.3 (algorithme 1, tableau 3), §5.3 (tableaux 5 à 8, figures 14 et 15)**. C'est la lecture la plus importante de l'étape.
- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms* (CLRS) : chapitre « Single-Source Shortest Paths » (Dijkstra) et BFS.
- Documentation networkx : `dijkstra_path`, `multi_source_dijkstra`, `has_path`.
- Pour le rapport (facultatif) : notions **ASET/RSET** et ISO 13571 (dose effective fractionnaire, Purser) ; SFPE Handbook, chapitre sur la tenabilité.
- Fiche `theorie/M5_evacuation_dynamique.md` (tableau pénalité / contrainte dure et subtilité F8).

**Critère de fin** : Q15–Q19 calculées par SPARQL et cohérentes avec le JSONL ; exemple chiffré où la pénalité de 1 000 m donne une route dangereuse et où la contrainte dure renvoie `null` ; routes conformes à F8.

---

## Étape 6 – M1 : voxels, matériaux, positions autorisées (≈ 3 h)

**Objectif** : grille de voxels (avec matériau par voxel) et ensemble $A$ des positions au plafond, sauvegardés en `.npz`.

**Connaissances nécessaires**
- Voxelisation de maillages, test d'appartenance (parité des intersections).
- Lancer de rayons : intersection rayon–triangle (Möller–Trumbore), structures accélératrices (BVH).
- Matériaux IFC : `IfcRelAssociatesMaterial`, `IfcMaterialLayerSetUsage` (murs multicouches).
- Gestion mémoire numpy (taille de grille, `uint8` pour les codes matériau).

**Lectures**
- **[IWCMC] §III.A et figures 1–2** ; dernier paragraphe de §V.B (« voxel size of 50 cm × 50 cm × 25 cm »).
- Möller & Trumbore, « Fast, Minimum Storage Ray/Triangle Intersection », *Journal of Graphics Tools*, 1997.
- Documentation **trimesh** (`ray`, `voxel`) ou **Open3D** (`RaycastingScene`).
- Fiche M1 §2.4.

**Critère de fin** : coupe horizontale de la grille affichée par niveau (murs colorés par matériau), nombre de positions $|A|$ par niveau, et part de plaque de plâtre parmi les obstacles comparée aux 18 % annoncés par l'IWCMC.

---

## Étape 7 – M3 : reproduction IWCMC 2024 (≈ 5 h de code, puis calcul en arrière-plan)

**Objectif** : modèle multi-murs, score de couverture, µ-connexité, PREP-NSGA, 4 scénarios dans `pareto.json`, confrontation aux figures 4 et 5.

**Connaissances nécessaires**
- Propagation radio : Friis, log-distance, modèle multi-murs, shadowing gaussien.
- Traversée de voxels 3D (DDA d'Amanatides & Woo).
- Théorie des graphes : arête-connexité, théorème de Menger, inégalité de Whitney, coupe minimale.
- Optimisation multi-objectif : dominance, front de Pareto, NSGA-II (tri non dominé, distance d'encombrement, élitisme), gestion des contraintes.
- Couverture maximale et sous-modularité (référence gloutonne pour valider l'algorithme génétique).
- Méthodologie expérimentale : graines multiples, médiane et dispersion, temps CPU.

**Lectures**
- **[IWCMC] en entier**, surtout §III.B (équations 1–2), §IV (équations 3–5 et contrainte µ), §V (algorithme 1, tableaux I et II, figures 4 et 5, §V.C protocole « sans jumeau »).
- Deb, Pratap, Agarwal, Meyarivan, « A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II », *IEEE Trans. Evol. Comput.*, 2002, sections II et III.
- Chambon et al., « Optimizing IoT networks deployment under connectivity constraint for dynamic digital twin », IEEE MetaCom 2023 (référence [7] de l'IWCMC : article d'origine de PREP-NSGA, **absent du kit**, à chercher si accessible).
- Kacou et al., « A multi-wall and multi-frequency home environment path loss characterization and modeling », 2018 (référence [15], origine du tableau I).
- Rappaport, *Wireless Communications: Principles and Practice*, chapitre 4 (log-distance, shadowing, modèles de murs).
- Amanatides & Woo, « A Fast Voxel Traversal Algorithm for Ray Tracing », Eurographics 1987.
- Diestel, *Graph Theory*, chapitre 3 (connexité, Menger) ; documentation networkx `edge_connectivity`.
- Nemhauser, Wolsey & Fisher, 1978 (garantie $1 - 1/e$ du glouton), pour la référence gloutonne.
- Fiche `theorie/M3_reproduction_IWCMC.md` (ambiguïtés à trancher : unité de $L_{obs}$, $F_{max}$, domaine en voxels).

**Critère de fin** : tests unitaires du modèle radio (une valeur calculée à la main) et de la µ-connexité (petits graphes connus) ; un essai court (≈ 20 itérations) sur les 4 scénarios ; **puis** lancement des vrais calculs en arrière-plan avec le temps CPU journalisé. Q20 extraite du front.

---

## Étape 8 – M4 : déploiement SSI (≈ 4 h)

**Objectif** : détecteurs, déclencheurs manuels, caméras 3D, zones de détection et relais, écrits dans `devices.json` et `kg.ttl`, avec F3 à F6 conformes.

**Connaissances nécessaires**
- Programmation linéaire en nombres entiers : couverture d'ensemble (*set cover*), relaxation linéaire, gap d'optimalité, statut du solveur.
- Modèle de caméra en 3D (frustum, rotations, tests angulaires) et visibilité par lancer de rayon.
- Couverture *full-view* et directions d'évacuation.
- Distance de cheminement (réutiliser l'étape 3) pour les déclencheurs.
- Notions de SSI : rôles des détecteurs de fumée et de chaleur, déclencheurs manuels, zones de détection.

**Lectures**
- **[PIMRC] §IV (équations 2 à 4, figure 4, tableau I des notations) et §V** (algorithme, mutation de connectivité).
- Wang & Cao, « On Full-View Coverage in Camera Sensor Networks », IEEE INFOCOM 2011 (définition du *full-view*).
- Wolsey, *Integer Programming* (chapitre 1 : formulations, couverture d'ensemble) ; documentation **HiGHS** (`highspy`) ou PuLP.
- Vue d'ensemble des normes (sans les acheter) : EN 54-5 (chaleur), EN 54-7 (fumée), EN 54-11 (déclencheurs manuels), NF S 61-970 (règles d'installation, zones). Une fiche de synthèse d'un fabricant ou d'un organisme de formation suffit, car l'exercice les simplifie.
- Fiche `theorie/M4_deploiement_SSI.md`.

**Critère de fin** : `pyshacl` passe F1 à F7 sur le graphe complet ; `devices.json` conforme au schéma, avec statut du solveur et gap renseignés.

---

## Étape 9 – M6 : agent neuro-symbolique (≈ 6 h)

**Objectif** : agent LLM local avec au moins 4 outils, réponses aux 20 questions dans `answers.jsonl`, traitement des 4 demandes dans `audit_log.jsonl`, journal de chaque appel au modèle.

**Connaissances nécessaires**
- API Ollama : `/api/chat`, appel d'outils (`tools`), sortie JSON contrainte (`format`), `options` (`temperature`, `seed`), métriques renvoyées (jetons, durées).
- Patron ReAct, appel de fonctions, auto-correction sur erreur d'outil.
- Génération de SPARQL par un LLM (prompt avec résumé d'ontologie et exemples) et gabarits paramétrés.
- Architecture de garde-fou : delta de triplets, validation SHACL sur une copie, *commit*/*rollback*, ordre lexicographique de décision.
- Ingénierie de prompt pour petits modèles (consignes courtes, sorties structurées).

**Lectures**
- Documentation Ollama : API REST (https://github.com/ollama/ollama/blob/main/docs/api.md) et la page sur l'appel d'outils.
- Yao et al., « ReAct: Synergizing Reasoning and Acting in Language Models », ICLR 2023.
- Sur le texte → SPARQL : l'article de synthèse ou les travaux du défi « Text2SPARQL » (ou les jeux de données LC-QuAD) suffisent pour comprendre les erreurs typiques.
- Sur le neuro-symbolique : Garcez & Lamb, « Neurosymbolic AI: The 3rd Wave », *Artificial Intelligence Review*, 2023 (pour situer la thèse et l'argumenter à l'entretien).
- `demandes_modification.json` relu au regard des formes F3, F5, F6, F8 ; fiche `theorie/M6_agent_neuro_symbolique.md` §2.3–2.4.

**Critère de fin** : petit banc d'essai des modèles installés (exactitude et latence sur 4 questions) qui justifie le choix ; 20 réponses identiques à celles de l'étape 4/5 ; audit des 4 demandes avec formes violées et décision justifiée ; durée totale mesurée.

---

## Étape 10 – Chaîne de bout en bout et généricité (≈ 3 h)

**Objectif** : la commande unique enchaîne tout ; tous les tests passent ; la chaîne tourne sur **un autre IFC**.

**Connaissances nécessaires** : intégration continue locale (un script `make`/`tox`), journalisation (`logging`), mesure des temps par module.

**Lectures / ressources**
- Les *Common Building Information Model Files* (NIBS / buildingSMART alliance), d'où vient le duplex : prendre un autre bâtiment de la même série (par exemple un bâtiment de bureaux) pour simuler l'entretien. Fabriquer un petit fichier d'observations synthétique pour ce bâtiment.

**Critère de fin** : exécution complète sur le second IFC sans modifier le code, et temps total compatible avec les **10 minutes** de présentation (sinon, prévoir un mode « rapide » paramétrable pour M3).

---

## Étape 11 – Rapport, carnet, déclaration IA (≈ 3 h)

**Contenu du rapport (6 pages maximum)** : architecture de la chaîne ; écarts à l'IWCMC (figures superposées, hypothèses, explications) ; incohérences de la maquette ; comparaison avec l'ontologie de Pang ; pénalité ou contrainte dure ; décisions de l'agent ; matériel et temps de calcul.

**Lectures** : relire l'énoncé (barème, livrables), `prompt.md` (déclaration IA) et le carnet de bord.

**Critère de fin** : dépôt Git partagé avec le jury **avant 16h00**, avec historique complet.

---

## Étape 12 – Préparation de l'entretien, sans IA (soirée du jeudi)

1. Lancer la chaîne en conditions réelles sur le second IFC, chronomètre en main.
2. Écrire au tableau, de mémoire : la formulation du problème d'optimisation (M3 et le *set cover* de M4) et un choix de modélisation de l'ontologie (`EvacuationDistance` réifiée, ou contrainte dure F8 plutôt que pénalité).
3. S'entraîner à prédire l'effet d'un paramètre : $S_{RX}$, µ, δ, rayon de détection, seuil de température, `minCameraCoverage` (les sections « À maîtriser » des fiches donnent les réponses attendues).
4. Faire soi-même deux petites modifications de code en 10 minutes, sans assistant : ajouter une règle d'anomalie, ajouter un outil à l'agent.

---

## Plan de repli si le temps manque

| Module menacé | Version réduite acceptable |
|---|---|
| M3 | Moins d'itérations ou de graines (déclarées dans `parametres_algo`), référence gloutonne en complément |
| M4 | Mode 2D pour les caméras (champ `mode`), *full-view* rapporté comme indicateur plutôt qu'imposé |
| M6 | Gabarits SPARQL paramétrés plutôt que SPARQL libre ; adaptations des demandes issues de règles |
| Rapport | Rédigé à partir du carnet de bord, avec figures générées par la chaîne |

**Ne jamais sacrifier** : la reproductibilité (« un résultat non retrouvé est éliminatoire »), la conformité aux schémas, la conformité SHACL et l'historique Git.
