# Carnet de bord

Entrées datées, y compris les impasses. Outils : Claude Code (Claude Opus 5.5) comme assistant de code ; voir `prompt.md` pour la trace des prompts. Les vérifications faites à la main sont signalées par **[vérifié à la main]**.

---

## 2026-11-07 – Lecture du kit

- Lecture de l'énoncé, du kit et des trois articles ; synthèse dans `feuille_de_route.md`, fiches dans `theorie/`.
- Points à vérifier à la main : tableau I de l'IWCMC (extrait d'un tableau pivoté), interprétation du domaine 16 × 34 × 10, unité des pertes $L_{obs}$.

## 2026-11-09 – Plan

- Ordre des étapes et lectures : `plan_execution.md`. M5 placé avant M3/M4 (il ne dépend que du graphe et des observations).

## 2026-11-10 – Étape 0 : squelette

**Décisions**
- Dépôt GitHub passé en **privé** (le jury sera invité) ; `articles/` et les PDF exclus par `.gitignore`.
- Environnement **conda, Python 3.11** : ifcopenshell n'était pas installable simplement sur le Python 3.14 du système. ifcopenshell 0.9.0, versions exactes dans `requirements.lock`.
- CLI **argparse** (bibliothèque standard, modifiable sans assistant). Sous-commandes `run` et `valider` ; option `--etapes`.
- **Les modules communiquent par les fichiers de sortie** : chaque module est testable et relançable seul, et le jury recalcule à partir de ces mêmes fichiers.
- Chaque sortie est validée à la fin de son étape (JSON Schema 2020-12 ligne par ligne pour les JSONL, SHACL pour `kg.ttl` avec l'ontologie et l'inférence RDFS). Le format `date-time` est réellement vérifié (`jsonschema[format-nongpl]`), sinon il est ignoré en silence.
- `execution.json` trace machine, versions, graine et durée par étape (exigence « déclarer le matériel et les temps de calcul »).
- Tests sur trois niveaux : unitaires (le validateur détecte bien les sorties fausses), conformité (schémas du kit valides, `exemple_minimal.ttl` conforme), intégration (commande complète). 17 tests verts.

**Ambiguïté relevée** : `pareto.schema.json` décrit **un** objet `{scenario, parametres_algo, front}` alors que 4 scénarios sont demandés dans un seul `pareto.json`. Choix provisoire : `pareto.json` est une **liste** de 4 objets, chacun conforme au schéma. À confirmer (question possible au contact de l'exercice).

**Visualisation : 2D plotly maintenant, 3D plus tard si le temps le permet**
- Bibliothèque : **plotly** (MIT) plutôt que matplotlib : HTML interactif (survol = GlobalId, nom, surface ; zoom ; légende cliquable par type de liaison), utilisable hors ligne.
- Estimation du coût d'une vue 3D (plotly `Mesh3d` à partir des triangles d'ifcopenshell, avec sélection par niveau) :

| | Plan 2D (espaces, portes, liaisons, sorties) | Vue 3D + vue de dessus |
|---|---|---|
| Code | ~120 lignes | +150 à 200 lignes |
| Temps | ~1 h | +2 h 30 à 3 h (triangulation par élément, fusion des maillages pour rester fluide, couleurs par classe, menu de niveaux, caméra) |
| Apport M1–M2 | Vérifier contours, connectivité, sorties, anomalies : l'essentiel | Faible : les escaliers et liaisons entre niveaux se lisent aussi en 2D (deux plans côte à côte + arêtes « escalier ») |
| Apport M3–M4 | Positions en x, y | **Réel** : hauteur des caméras, cônes de vue, voxels, positions autorisées au plafond |
| Risque | Nul | Lenteur sur l'IFC plus grand de l'entretien |

  Décision : 2D maintenant (étapes 1–2). La 3D sera faite après M4 si le temps reste, en réutilisant les mêmes données, pour montrer les équipements.

## 2026-11-10 – Étape 1 : exploration de l'IFC (avant d'écrire le code)

Scripts jetables (hors dépôt) : ifcopenshell 0.9, géométrie en coordonnées monde.

- IFC2X3, longueurs en mètres (échelle 1.0). 4 niveaux : T/FDN −1,25 ; Level 1 0 ; Level 2 3,1 ; Roof 6,0.
- 21 espaces, tous avec `GSA Space Areas`, `PSet_Revit_Dimensions` (Area, Unbounded Height), `PSet_Revit_Constraints`.
- **Surface géométrique (union des triangles projetés) inférieure de 7 à 23 % à « GSA BIM Area »**, de façon identique entre logements A et B : écart **systématique** (convention de mesure), pas une anomalie. Une règle « écart > 5 % » signalerait tout : écartée. Q05 et Q10 demandent explicitement « GSA BIM Area ».
- **Les 12 ouvertures non remplies ne sont pas des passages** : 8 percent des meubles hauts, 2 des plans de travail (évier), 2 la dalle de toit. Les liaisons « ouverture » viennent donc des **limites virtuelles** (`IfcRelSpaceBoundary` VIRTUAL : 16 internes, 12 externes).
- 14 portes : 4 extérieures (`Pset_DoorCommon.IsExternal = True`, une seule limite d'espace) : entrées A101/B101, portes vitrées A102/B102.
- Anomalies candidates repérées :
  1. `IsFireExit` vaut le texte `'IsFireExit'` pour **toutes** les portes (valeur fictive du gabarit Revit) : inutilisable pour les sorties.
  2. Deux espaces nommés `B202` (`…_39` « Bedroom 2 », `…_3A` « Bedroom 1 ») ; le logement A a A202/A203.
  3. `B105` « Room » alors que son symétrique `A105` est « Stair » (même géométrie, hauteur 5,7 m).
  4. La porte `1aj$VJZFn2TxepZUBcKpac` borde **3 espaces** (A204, A205, A201) ; sa symétrique dans B n'en borde que 2.
  5. Le second escalier est rattaché au niveau **Roof** (le premier à Level 1), alors que sa volée va de z = 0 à 3,05.
  6. `RiserHeight` = 0,6357 et `TreadLength` = 0,8202 : ce sont des **pieds** (0,194 m et 0,25 m) dans un fichier en mètres.
- Escaliers : chaque volée touche le foyer, l'espace escalier (x105, double hauteur 0–5,7 m), le couloir x201 et une chambre du niveau 2.
- Q13 (passage direct A ↔ B) : aucune porte ni limite virtuelle ne relie les deux logements dans les relations IFC. À confirmer par la géométrie : la réponse attendue est peut-être l'ensemble vide.

## 2026-11-10 – Étape 1 : extraction et visualisation

- Décisions validées et résultats consignés dans `etape0a2.md`.
- Extraction M1 : 4 niveaux, 21 espaces, 14 portes, 2 escaliers en 1,4 s ; 10 lignes d'anomalies (7 constats) par 6 règles génériques.
- **Découverte** : l'espace `…dl_39` nommé `B202` a pour numéro Revit `B203` (`PSet_Revit_Identity Data.Number`) : le nom IFC a été modifié. La règle « nom IFC ≠ copies du nom dans les propriétés » le détecte sans connaître le duplex.
- B105 « Room » détecté par la règle des jumeaux géométriques (même surface, hauteur et niveau que A105) combinée à la catégorie OmniClass « Stairway ». Bedroom 1 / Bedroom 2 ne déclenchent pas la règle (numéro final ignoré).
- Règle « occupable » : la proposition « niveau le plus haut » a été abandonnée au profit des seuls mots-clés (un dernier étage est en général occupé).
- Impasse : export PNG des figures pour vérification nécessitant `kaleido` (installé dans l'environnement pour le contrôle, non requis par la chaîne).
- Visualisation contrôlée à l'œil (plan Level 1, Level 2, vue 3D) : contours, portes et escaliers aux bons endroits.
- **À faire à la main** : vérifier Q01, Q05, Q10, Q12, Q14 dans BIMvision.
- **[vérifié à la main]** 10/11 : dans BIMvision, surfaces GSA BIM Area, espaces de Level 2, salles de bains, largeurs de portes et anomalies (double `B202`, B105 catégorie « Stairway ») conformes à la chaîne (Q01, Q05, Q10, Q12, Q14).

## 2026-11-10 – Étape 2 : connectivité

- Exploration : les limites virtuelles sont des `IfcSurfaceOfLinearExtrusion` de polylignes ; décodées en segments monde. Celles de A201/B201 tombent à 6–10 m de leur espace : leur `ObjectPlacement` (6,42 ; −11,55 ; 3,12) n'est pas nul contrairement aux autres espaces, alors que les coordonnées des limites restent absolues.
- **Impasse** : `ifcopenshell.geom.create_shape` échoue sur ces surfaces d'extrusion → décodage manuel de la polyligne + placement.
- **Impasse** : la chaîne de Pang (porte → ouverture → mur → espaces du mur) renvoie tous les espaces qui longent un mur (jusqu'à 5) ; il faut la restreindre aux espaces proches de la porte.
- Premier essai : toute citation minoritaire signalée → 2 fausses anomalies (A105/B105 cités par la seule chaîne de Pang, à cause du chevauchement cage/chambre). Décision : seule une citation minoritaire **de la source IFC** est une anomalie de la maquette.
- Escaliers : la volée est entièrement dans la cage (x105, double hauteur) ; arrivée détectée dans x201. Liaison A105 → A201 ; la limite virtuelle A201/A105 est l'arrivée de l'escalier (pas une ouverture distincte).
- Résultats et réponses préliminaires : `etape0a2.md` §2 bis. 54 tests verts.

## 2026-11-10 – Étape 3 : distances d'évacuation

- `m1_geometrie/distances.py` : graphe de visibilité (sommets du contour + cible, segments contenus dans l'espace à 1 cm près) puis Dijkstra depuis la cible ; distance = max sur les sommets. Formule de Pang calculée à côté.
- 40 distances orientées (20 liaisons × 2 sens) + 4 distances vers les sorties, toutes > 0 ; calcul en ≈ 0,5 s.
- **Constat** : la formule de Pang (un seul sommet intermédiaire) donne exactement la même valeur que Dijkstra sur **tous** les espaces du duplex, y compris le foyer A101 (12 sommets, non convexe). Elle échoue sur un polygone en U (test unitaire) : à montrer au jury.
- Volée : course mesurée sur l'empreinte le long de l'axe bas → haut (3,77 m, cohérent avec 15 girons de 0,25 m une fois convertis depuis les pieds), dénivelé 3,05 m, longueur 4,85 m. Le premier calcul (distance entre centres des marches basses et hautes) donnait 3,52 m de course : corrigé.
- Distances extrêmes : foyer A101 → entrée 8,35 m ; A201 → cage (descente) 4,11 m + 4,85 m.
- Itinéraire A202 → entrée A101 : A202, A201, A105, A101 ; portes franchies 0,864 m (chambre) et entrée → **Q07 = 0,864 m**. Q08 confirmée (B201, B105, B101).
- 62 tests verts.
- Vérification Q07 dans BIMvision : la porte A202–A201 n'est pas nommée par ses espaces ; repérage par le numéro Revit 159834 / Mark A202. **Recoupement** : la porte de « Bedroom 2 » (B202 en double) porte la marque `B203`, ce qui confirme que l'espace s'appelait B203 à l'origine.
- **[vérifié à la main]** BIMvision ne montre que 7 portes sous Level 2 et aucune de Mark A202 : la porte `2OBrcmyk58NupXoVOHUvVV` (A202–A201) **n'est rattachée à aucun niveau** (absente de `IfcRelContainedInSpatialStructure`) — seul élément de la maquette dans ce cas. La chaîne ne l'avait pas vu, car `ifcopenshell.util.element.get_container` déduit silencieusement un niveau (Level 2). Ajout de la règle générique `rattachement_spatial` (contrôle de la relation IFC directe) et d'un test. Leçon : ne pas se fier aux utilitaires qui « réparent » la donnée lorsqu'on cherche des anomalies.

## 2026-11-10 – Étape 4 : ontologie et graphe de connaissances

- `m2_graphe/` : `ontologie_extension.ttl` (alignement BOT / SAREF4BLDG, logement, distance vers sortie, anomalie, paramètres), `construction.py` (geometry.json → kg.ttl), `formes_maison.ttl` (M1–M9), `requetes.py` (gabarits SPARQL Q01–Q14).
- **Piège évité** : `rdfs:domain` est une règle d'inférence. Réutiliser `ssi:connects` pour l'escalier en ferait une porte (F2) ; réutiliser `ssi:from/hasDistance` pour la distance vers une sortie en ferait une `EvacuationDistance` sans `ssi:to` (F7). Propriétés dédiées créées.
- **Piège évité** : rattacher les espaces au logement par `bot:hasSpace` viole F1 (un seul parent `bot:hasSpace`, de type Storey) → `ssi:inDwelling`.
- **Impasse** : rdflib distingue `"x"` et `"x"^^xsd:string` dans les requêtes ; comparer les GlobalId par `STR()`.
- **Impasse** : mes premières formes maison rejetaient l'exemple minimal du kit (symétrie écrite dans un seul sens, porte sans largeur). Exigences de complétude passées en `sh:Warning` ; seuls les invariants restent des violations.
- Graphe statique conforme à F1, F2, F7, F8 et M1–M9 ; F3 (20 espaces) et F4 (4 sorties) échouent comme attendu sans équipements : différées automatiquement tant que M4 n'est pas calculé.
- Les 14 questions statiques obtenues par SPARQL donnent les mêmes résultats que le calcul Python. Nouvelle : Q11 = A102, B102 (séjours, 30,14 m²).
- Fichier `doutes.md` créé à ta demande. 76 tests verts.

## 2026-11-10 – Vérification Q01 (cages d'escalier) et Q13 (passage A ↔ B)

- Hypothèse discutée : B105 serait une cage au-dessus de A105, donc au Level 2. **Infirmée** : B105 (x 0,42–1,43 ; y −9,72 à −5,97) est le symétrique de A105 (x 7,37–8,38 ; y −11,82 à −8,07), à 6,9 m de distance ; base à z = 0,02 m et hauteur 5,68 m pour les deux ; chacune contient la volée de son propre logement (z 0 → 3,05). Le duplex est fait de deux logements symétriques, chacun avec son escalier.
- Q13 vérifiée par 4 voies indépendantes : (1) les 4 murs « Party Wall – CMU Residential Unit Dimising Wall » (2 au Level 1, 1 au Level 2, 1 sans espace) n'ont **aucune** ouverture ; (2) aucune `IfcRelSpaceBoundary` (physique ou virtuelle) ne relie un espace A à un espace B, hormis des murs ; (3) les 14 portes desservent chacune un seul logement ; (4) seules les chambres A202/A203 et B202 sont voisines (0,55 m = épaisseur du mur mitoyen), et les couloirs A201/B201 sont à 4 m. Les murs extérieurs qui bordent A et B à la fois ne portent que les portes d'entrée et des fenêtres. → ∅ confirmé ; test ajouté.

## 2026-11-10 – Étape 5 : évacuation dynamique

- Scénario lu : feu dans la cuisine A103 ; fumée (> 0,0328 /m) dès 70 s, puis A101/A102 (120 s), A105 (170 s), A201 (200 s), étage A (330 s) ; température > 60 °C : A103 120 s, A101/A102 180 s, A105 250 s, A201 290 s, chambres 460 s. Logement B jamais touché (26 °C). Caméras dans 7 espaces ; `CAM_B203` observe le B202 « Bedroom 2 » (indice supplémentaire du renommage).
- `m5_evacuation` : observations en SOSA (~29 700 triplets au total), état mis à jour par SPARQL UPDATE (verrouillé, `ssi:dangerSince`), personnes par caméra, stratégies 1 (statique) et 2 (contrainte dure), route « pénalité » jointe pour comparaison ; routes finales dans le graphe (F8).
- **Impasse** : rdflib ne convertit pas `xsd:integer("2.0"^^xsd:double)` (résultat vide → aucune personne comptée, JSONL vide au premier essai) ; contourné par `xsd:integer(ROUND(?v))`.
- **Exemple chiffré** : à 180 s, A202 → pénalité : A202, A201, A105, A101 à 1 026 m (traverse A101 dangereux) ; contrainte dure : null + confinement. À 300 s : 3 026 m (trois espaces dangereux traversés).
- Q15 = 70 · Q16 = A101, A102, A103, A105, A201 · Q17 = A202, A201, A105, A101 · Q18 = 180 · Q19 = A202, A203 ; obtenues par SPARQL et recoupées avec le JSONL. 86 tests verts (≈ 3 min ; `-m "not integration"` pour les rapides).
- **Décisions du 10/11** : Q18 = 180 s (route coupée) ; capteurs du scénario ≠ équipements de sécurité (validé) ; risque « espaces dangereux sans caméra » signalé à chaque pas ; variante « détour réactif » ajoutée (coût ≈ 30 lignes, champ du JSONL car le schéma limite `strategie` à 1 ou 2). Résultat : à 180 s, l'occupant de A202 qui suit le plan s'arrête dans la cage A105 (15 m parcourus) sans issue ; à 250 s, il serait bloqué dès le couloir A201. Dans ce duplex, le détour ne trouve jamais d'autre route (un seul chemin par logement) ; il prendra son sens sur un bâtiment plus grand.

## 2026-11-10 – Étape 6 : voxels, matériaux, positions autorisées

- Lecture de l'IWCMC §III.A et §V.B : domaine 16 × 34 × 10, voxels de 50 × 50 × 25 cm, obstacles = murs, toits, plafonds ; positions = impacts de rayons vers le haut sur les « roofs » ; 18 % des obstacles dans le matériau le plus absorbant (plaque de plâtre à 2,4 GHz). Incohérence : 10 couches de 25 cm = 2,5 m, pas la hauteur du duplex.
- Matériaux IFC : cloisons = plâtre + ossature métal ; murs extérieurs = brique + parpaing + isolant + plâtre ; mur mitoyen = 2 parpaings ; dalles = bois ou béton ; faux plafonds = plâtre ; portes sans matériau (→ bois).
- `m1_geometrie/voxels.py` : une seule primitive, le rayon vertical (barycentriques XY). Voxelisation par parité sur 5 × 5 colonnes par voxel ; positions A par premier impact sur couverture / dalle / toit. Pas de nouvelle dépendance. 9 s.
- Résultats : grille 16 × 34 × 24 — les 16 × 34 de l'IWCMC retrouvés en prenant l'emprise des espaces ; 4 956 obstacles sur 13 056 ; plafonds à 2,60 m et 5,70 m ; cages d'escalier libres à travers le plancher ; 932 positions.
- **Écart** : plaque de plâtre = 47 % des voxels obstacles (catégorie dominante), 8 % en volume réel de matière, contre 18 % dans l'article. Aucune méthode simple ne donne 18 % : à présenter comme écart documenté.
- Outil : `pypdf` installé dans l'environnement pour lire l'article (non requis par la chaîne).

## 2026-11-10 – Étape 7 : reproduction IWCMC

- Relecture de l'article (texte + figures rendues en image) ; `iwcmc.md` : résumé, lectures I-1 à I-10, décalages E-1 à E-14. Valeurs des figures 4 et 5 relevées à l'œil (`m3_iwcmc/article.py`).
- `m3_iwcmc` : `radio.py` (équation 2, tableau I complet, traversée par échantillonnage 5 cm, lectures voxel / mètre, environnement sans jumeau), `score.py` (équations 1, 3, 4, métriques, µ-connexité par `edge_connectivity`), `prep_nsga.py` (algorithme 1), `sensibilite.py` (glouton + étude du facteur), `article.py`. Matrices 932 × 8 100 en cache (≈ 5 min, 33 Mo).
- **Constat majeur** : avec les valeurs du tableau I, un équipement couvre 100 % du duplex (perte ≤ 62,5 + 10 dB, sensibilité −65 dBm) ; avec et sans jumeau identiques. Les figures de l'article (44 % pour un équipement) ne sont pas reproductibles ainsi.
- **Impasse** : équipements placés au point d'impact (dans le voxel du faux plafond) → les liaisons équipement–équipement longent la couche du plafond ; avec atténuation renforcée, plus aucune liaison et µ = 3 sans solution initiale (plantage). Antenne déplacée dans le voxel libre juste sous le plafond.
- **Impasse** : qualité moyenne sur les seuls voxels couverts → courbe non monotone ; la moyenne sur tous les voxels libres (non couvert = S_RX) reproduit la forme de la figure 4 (a) (« relative coverage »).
- Étude de sensibilité (glouton) : lecture voxel × 30 reproduit la figure 4 (écart moyen 0,035 ; Q20 = 3) ; lecture mètre ne s'en approche qu'au-delà de × 50.
- PREP-NSGA (graine 0, 300 itérations) : tableau I → fronts plats à 100 % ; × 30 → µ = 0 proche de l'article, µ = 3 en dessous (convergence, une seule graine).
- Outils installés pour lire l'article seulement : `pypdf`, `pymupdf` (non requis par la chaîne).

## 2026-11-10 – Campagne de comparaison IWCMC

- `m3_iwcmc/campagne.py` : comptes de voxels traversés par groupe de matériau (6 groupes, 8 min, vérifié à 8 × 10⁻⁷ dB contre le calcul direct) → toutes les variantes par combinaison linéaire. 12 expériences, 33 min au total.
- Résultats (détail dans `comparaison.md`) : tableau I → 100 % dès 1 équipement pour toutes les lectures, technologies, S_RX jusqu'à −45 dBm, domaine 1 ou 2 niveaux ; facteur × 30–40 (lecture voxel) → figure 4 (écart 0,02–0,035, Q20 = 3 à × 30) ; part de plâtre 21 % → gain du jumeau +5 points à 2 équipements (contre +1,5 à 47 %) ; µ = 3 : optimum local de PREP-NSGA (100, 300, 1 000 itérations identiques), étendue de 7 à 16 points entre graines ; précision du lancer de rayons : 91 % des rayons identiques entre pas 5 cm et 1,25 cm.
- Figures : `sorties/figures/comparaison.html` (synthèse), `iwcmc.html` (fronts).

## 2026-11-10 – Étape 8 : déploiement SSI

- Dépendance ajoutée : `highspy` (HiGHS, MIT) pour les MILP exacts ; `requirements.lock` et `pyproject.toml` mis à jour.
- `m4_deploiement/` : `milp.py` (couverture d'ensemble), `placement.py` (détecteurs, déclencheurs, chemins, caméras + full-view), `reseau.py` (connectivité, relais), `graphe.py` (écriture F3–F6), `__init__.py` (devices.json, zones).
- Détecteurs : 932 candidats, 944 cellules, 20 détecteurs (un par espace occupable), optimal en 0,13 s.
- Déclencheurs : 2 pour 4 sorties (distance de marche 0,4 m et 6,6 m dans le plateau séjour–foyer–cuisine), optimal.
- **Impasse** : 78 cellules des chemins invisibles au premier essai. Au Level 2, une caméra à 3,1 + 2,4 = 5,5 m tombe dans la couche de voxels du faux plafond et était écartée. Correction : pose juste sous cette couche. Ensuite 0 cellule invisible.
- Caméras : 7 184 candidats (positions × 8 azimuts × 2 inclinaisons), 182 cellules, 18 caméras (optimal), couverture 100 % de chaque chemin, full-view 69 % (phase 2 à 18 caméras).
- Réseau : connexe (λ = 39 avec le tableau I, λ = 1 avec × 30) ; aucun relais.
- **Impasse** : la chaîne complète échouait en M2 car un `devices.json` d'un run précédent (calculé) activait F3–F6 avant que le graphe ne contienne d'équipements. Le report des formes dépend maintenant de l'étape (M1–M3) et non du fichier sur disque.
- Chaîne complète : `kg.ttl` conforme à F1–F8 et aux 11 formes maison ; `valider` : 8 sorties OK. 10 tests M4.

## 2026-11-10 – Retours sur l'étape 8 (S-1, S-4)

- S-1 : un déclencheur par sortie (décision) → 4 DM à 0,4 m ; option `declencheur_un_par_sortie` pour revenir au minimum. Lève aussi S-2.
- S-4 : diagnostic → le full-view nul de B102/B103 n'était PAS structurel (88–93 % atteignables par au moins un candidat) : l'objectif « somme » sacrifiait les chemins courts. **Mon explication précédente était fausse.**
- Phase 2 des caméras passée en lexicographique : max du full-view minimal par chemin, puis du total (variable continue ajoutée à `milp.resoudre`).
- À 18 caméras, le MILP prouve qu'un minimum > 0 est impossible ; option `cameras_supplementaires_full_view` : k = 1 → 10 %, k = 2 → 62,5 % (global 86 %), k = 3 → 79 %, k = 4 → 80 %.
- 2 tests ajoutés (12 tests M4).

## 2026-11-10/11 – Étape 9 : agent neuro-symbolique

- Ollama 0.40 vérifié, `qwen2.5:14b` présent (appels d'outils). Boucle ReAct bornée écrite à la main (`agent.py`), 19 outils génériques (`outils.py`), référence sans LLM (`reference.py`), demandes (`demandes.py`), client + journal + rejeu (`llm.py`).
- Micro-banc : qwen2.5:14b juste ; llama3.1 argument faux ; mistral appels dupliqués ; qwen3:4b réflexion trop longue.
- **Impasse** : routes candidates de D4 rejetées par M11 (`validAt` manquant) → horodatage à t = 200 s ajouté aux triplets candidats.
- **Impasse** : banc d'essai (llama3.1, qwen3:4b, mistral) arrêté par manque de mémoire ; llama3.1 2/4 sur Q07, Q08, Q12, Q17.
- **Impasse** : llama3.1 envoie `"False"` en texte, lu comme vrai en Python → conversion des booléens dans `outils.appeler` + test.
- Run réel : 20 / 20 conformes ; décisions D1–D4 identiques aux plans écrits à la main.
- **Impasse** : justifications « la politique qui privilégie l'accessibilité et la sobriété » : le modèle lisait `a > b > c` à l'envers → ordre écrit en liste numérotée.
- **Impasse** : une relance arrêtée (mémoire) avait vidé `llm_journal.jsonl` (troncature au démarrage) ; rejouer `sorties/` vers `sorties/` le vidait aussi → journal écrit en `.partiel`, renommé en fin de run.
- Run final : 20 / 20, 21 itérations, 12 validations SHACL, 1 400 s (questions 678 s, demandes 706 s dont 600 s de LLM) ; `valider` : 8 sorties OK.

## 2026-11-11 – Fumée ou chaleur (D1, D3) et quantification

- Consignes relues : type de détecteur libre (theorie/M4 §1, ontologie, schéma) ; D3 « détection temporaire (chaleur, autonome) » proposée par theorie/M6.
- `m4_deploiement/fumee_chaleur.py` + commande `detecteurs` : délais par espace depuis observations.csv. Fumée 70 s dans la cuisine contre 110–130 s en chaleur statique (danger à 120 s) ; au Level 2 la chaleur statique alarme au moment du danger.
- D1 retarde la 1re alarme du bâtiment (70 → 80 s en A1R, 110–120 s en A1) ; D3 ne la retarde pas (feu au Level 1) mais retarde l'alarme du Level 2 (200 → 220 s A1R, 280 s A1).
- Rayon : 20 détecteurs à 5 m, 24 à 3,54 m, 34 à 2,74 m (MILP optimal).
- Quantification : `ollama show` → qwen2.5:14b est déjà en Q4_K_M (14,8 G paramètres, 9 Go) ; pas de gain de temps à attendre de ce côté.

## 2026-11-11 – Chaîne complète avec détecteurs de chaleur

- `detecteur_type` (M4 : type et rayon ; M5 : condition d'alarme via `fumee_chaleur.declencheur_alarme`), `detecteur_chaleur_classe` (A1R / A1) ; variantes dans `data/variantes/` ; commande `comparer`.
- Fumée / A1R / A1 / A1R rayon 3,54 m : alarme 70 / 80 / 130 / 80 s ; marge avant perte de route sûre 110 / 100 / 50 / 100 s ; 20 / 20 / 20 / 24 détecteurs ; réponses de référence identiques.
- **Impasse** : run réel de M6 sur la variante A1R arrêté par manque de mémoire pendant les demandes (les 20 questions étaient faites : 20 / 20) → M6 rejoué à partir du journal du run fumée (`TWINHYP_LLM_REJEU`), ~110 s par variante.
- Défauts révélés et corrigés : D1 comptait un triplet ajouté déjà présent ; D3 remplaçait des détecteurs déjà de chaleur (90 triplets retirés puis remis) → refus, détection maintenue. Test ajouté.
