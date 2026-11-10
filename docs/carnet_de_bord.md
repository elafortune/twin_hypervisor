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
