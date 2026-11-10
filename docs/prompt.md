# Historique des prompts (déclaration d'usage de l'IA)

Trace des prompts adressés à l'assistant IA (Claude Code, modèle Claude Opus 5.5) pendant le test technique. Les prompts sont recopiés tels quels, dans l'ordre chronologique.

---

## 1 — 2026-11-07 — Compréhension de l'énoncé

> j'ai postulé à l'offre de thèse cifre suivante : https://emploi.abg.asso.fr/fr/candidatOffres/show/id_offre/140412/job/ia-agentique-et-llm-souverain-pour-l-orchestration-de-jumeaux-numeriques-iot-fondee-sur-une-ontologie-interoperable-application-aux-systemes-de-securite-incendie
> Il faut que je réalise leur test technique qui est le fichier courant
> explique moi en quoi consiste le test technique
> l'objectif, les tools donner le format de réponse et les différents documents attendus, les consignes

**Résultat :** lecture du kit (énoncé PDF, LISEZMOI, paramètres, questions, demandes, schémas, formes SHACL) et synthèse → devenue `feuille_de_route.md`.

---

## 2 — 2026-11-07 — Feuille de route et phase théorique

> déjà enregistre ccette réponse qui va constituer ma feuille de route dans feuille_de_route.md
> ensuite avant de réaliser la partie code on va réaliser une phase de compréhension théorique pour chacun des modules. Cette phase va contenir les différents aspects suivants pour chaque module : utilité du module (qu'est ce que c'est, à quoi sert il), quelles équations mathématiques/physiques et théorèmes fondamentaux régissent ce module (ou quels articles de thèse), quels sont les différents choix techniques/ d'architecture à faire concernant ce module et donne moi les différents aspects à prendre en compte pour faire ces choix
>
> crée un fichier prompt.md qui laisse une trace des différents prompts que j'ai utilisé (dont celui ci et celui précédents)

**Résultat :** création de `feuille_de_route.md`, de ce fichier `prompt.md` et du dossier `theorie/` (index + une fiche par module M1 à M6). Pour rédiger les fiches, l'assistant a lu les trois articles (extraction texte avec `pdftotext`), l'ontologie socle, les 8 formes SHACL, et a fait un inventaire rapide de l'IFC (types d'entités, matériaux, espaces) ainsi que du matériel (RAM, CPU, modèles Ollama installés).

**Points à vérifier à la main :**
- le tableau I de l'IWCMC (valeurs WiFi 2,4 GHz extraites d'un tableau pivoté) ;
- l'interprétation du domaine 16 × 34 × 10 ;
- l'unité des pertes $L_{obs}$.

---

## 3 — 2026-11-09 — Ordre des étapes et lectures

> J'ai lu en partie les documents de théorie. dis moi maintenant dans quel ordre réaliser les différentes étapes nécessaires à la résolution de l'exercice. En plus de cela tu dois prendre en compte les connaissances que j'ai besoin pour chacune des étapes et me diriger vers les articles ou les thèmes dont je devrai prendre connaissance pour chaque étape

**Résultat :** création de `plan_execution.md` : 13 étapes ordonnées (0 à 12) avec calendrier du 9 au 12 novembre, connaissances nécessaires, lectures (sections précises des articles du kit et références externes), critère de fin par étape et plan de repli.

---

## 4 — 2026-11-10 — Préparation des étapes 0, 1 et 2

> j'ai créé le git : https://github.com/elafortune/twin_hypervisor allons commencer ensemble les étapes 0,1,2 dis moi quoi faire : les éléments à connaitre, fichiers à lire, choix technologiques à faire afin qu'on puisse faire ces étapes et que je sache ce que chacune des étapes contient et à quoi elles servent

**Résultat :** création de `guide_etapes_0_a_2.md` : pour chaque étape, ce qu'il faut connaître, les lectures, les choix à trancher (C1 à C19) avec recommandation, la liste d'actions et le critère de fin. Vérifications faites par l'assistant : dépôt GitHub vide et public, ifcopenshell absent du Python 3.14, conda disponible, unités de l'IFC en mètres, 265 `IfcRelSpaceBoundary`, propriété `IsFireExit` de valeur textuelle.

---

## 5 — 2026-11-10 — Clarifications sur les étapes 0, 1 et 2

> étapeo 0 établie les test et la commande qui servira aux différents lancement
> étape 1 : comment lire et visualiser l'ifc ? est ce une fonction de visualisation qui etre mise en place ?
> étape 2 : comment établir la connectivité est ce qu'il faut établir le knowledge graph pour cette étape ? que faut il faire d'autre : dijstra pour les chemins, modèle de machine learning pour les anomalies ? est ce que dans cette étape on fait aussi l'ontologie avec la description des liens entre les éléments dans le cadre du knowledge graph ?
>
> dis moi les différents éléments indispensable des étapes 0, 1, 2, les choix entre différentes architectures à faire pour ces étapes là, sur quoi me baser pour faire ces choix, et ce qu'il faut connaitre coté théorique

**Résultat :** réponse dans le terminal et section « Précisions » ajoutée à `guide_etapes_0_a_2.md` : pas de visualiseur à coder (outil externe + tracé 2D matplotlib), pas de graphe de connaissances ni d'ontologie à l'étape 2 (étape 4), pas de Dijkstra (étapes 3 et 5) ni de ML (règles), modules découplés par les fichiers de sortie.

---

## 6 — 2026-11-10 — Validation des choix et lancement de l'étape 0

> je valide tous les éléments et le processus que tu as proposé : trois niveau de test, méthode de lancement des scriptes, architectures avec les modules communiquant ayant chacun leur sortie pour faciliter les tests, tracé 2D mais avec une librairie plus qualitative que matplotlib, calcule à quel point avoir le visualiseur 3D avec vue 2D est plus complexe par rapport à l'ajout sur la visualisation et la compréhension de l'architecture,je valide les choix et critères et l'utilisation des 3 source de connectivité pour vérifier la présence d'anomalies. tu peux commencer

**Résultat :** dépôt cloné dans `C:\Users\emeri\twin_hypervisor`, environnement conda `twinhyp` (Python 3.11), squelette de l'étape 0 (CLI, orchestrateur, validation des sorties, 17 tests), choix de plotly et estimation 2D / 3D dans `carnet_de_bord.md`. À partir de cette entrée, la copie de référence de ce fichier est `docs/prompt.md` dans le dépôt.

---

## 7 — 2026-11-10 — Visualisation 2D + 3D et extraction (étape 1)

> réalise 2D +3D dès maintenant qui sera utile pour la suite, je valide tes propositions que tu vas consigner dans etape0a2.md et tu vas m'indiquer les résultats principaux et quels scriptes lancers pour les visualiser / où les visualiser

**Résultat :** `docs/etape0a2.md` (décisions validées, résultats, mode d'emploi) ; extraction M1 (`extraction.py`, `ifc_outils.py`, `anomalies.py`) ; commande `visualiser` produisant `plan_2d.html` et `vue_3d.html` (plotly) ; 42 tests verts.

---

## 8 — 2026-11-10 — Mémo des commandes et vérification dans BIMvision

> tu peux créer un fichier simpliste main.md qui va noter les différentes commandes de lancement et les résultats importants de chaque phase en une phrase, c'est un fichier simpliste qui résume tout les éléments importants les commandes (à quoi elles servent) et les résultats sans devoir parcourir beaucoup de texte.
> j'ai bimvision et j'ai ouvert le duplex ifc mais je ne vois pas comment vérifier la surface et les différentes questions. dis moi comment faire cela ensuite on passe à la prochaine étape

**Résultat :** `main.md` (mémo commandes + résultat de chaque phase en une phrase) et `docs/verification_bimvision.md` (grille de contrôle des valeurs à lire dans BIMvision) ; mode opératoire BIMvision donné dans le terminal.

---

## 9 — 2026-11-10 — Vérification faite, passage à l'étape 2

> j'ai vérifié,le double B202 et le B105 classé en stairway a la place de room note ces éléments de décalages dans main.md je suppose que ce seront des éléments dont je parlerai avec le jury. tout correspond, passons à l'étape 2

**Résultat :** section « Écarts de la maquette à présenter au jury » dans `main.md`, grille BIMvision cochée ; étape 2 réalisée (`connectivite.py` : vote à 3 sources pour les portes, ouvertures par limites virtuelles + contact géométrique, escaliers, contrôle d'évacuabilité), 5 nouvelles anomalies, 54 tests verts, plan 2D avec liaisons.

---

## 10 — 2026-11-10 — Choix de l'étape 2 dans main.md, proposition de l'étape 3

> indique ces choix dans main.md aussi et dis moi comment l'étape 3 sera réalisée afin que je valide

**Résultat :** section « Choix de méthode à valider / défendre » dans `main.md` ; plan de l'étape 3 (distances d'évacuation) proposé dans le terminal, en attente de validation.

---

## 11 — 2026-11-10 — Validation de l'étape 3 et fichier des choix

> je valide ce plan crée aussi un fichier choix.md qui décris tous les choix qui ont du etre fait à chaque étape , les différentes propositions pertinentes et le choix final réalisé cela me permet de pouvoir garder une vision d'ensemble des choix faits et potentiellement de revenir sur certains choix réalisés par la suite avec une meilleure compréhension, tu peux continuer

**Résultat :** `choix.md` (toutes les décisions des étapes 0 à 3 : options, choix final, raison, quand y revenir) ; étape 3 réalisée (`distances.py` : graphe de visibilité + Dijkstra, formule de Pang en comparaison, longueur de volée, itinéraires), couche « Distances » dans le plan 2D, Q07 = 0,864 m, 62 tests verts.

---

## 12 — 2026-11-10 — Porte A202–A201 introuvable dans BIMvision

> je ne trouve pas de porte A202-201 à l'étahe level 2 dans BIMvision

**Résultat :** la porte existe (`2OBrcmyk58NupXoVOHUvVV`, nom IFC « M_Single-Flush:0864 x 2032mm:0864 x 2032mm:159834 », marque Revit `A202`) ; table d'identification des 14 portes ajoutée dans `docs/verification_bimvision.md`.
