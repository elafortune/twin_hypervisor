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
