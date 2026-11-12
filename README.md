# twin_hypervisor – Du BIM au SSI neuro-symbolique

Test technique de la thèse CIFRE TwinHypervisor (uGetWin / LIGM, Université Gustave Eiffel).
Chaîne : **IFC → jumeau géométrique → graphe de connaissances → déploiement SSI → évacuation dynamique → agent LLM local sous contrôle symbolique**.

## Installation

```bash
conda env create -f environment.yml      # Python 3.11 + paquet installé en mode éditable
conda activate twinhyp
# versions exactes utilisées pour les résultats rapportés :
pip install -r requirements.lock
```

## Reproduction (une seule commande)

```bash
python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc \
    --params data/parametres.json --obs data/observations.csv --out sorties/
```

Options : `--etapes m1,m2` (relancer une partie de la chaîne à partir des sorties existantes), `--graine N`, `--questions`, `--demandes`, `--donnees` (dossier contenant `schemas/` et `ontologie/`).

Revalider des sorties existantes : `python -m twinhyp valider --out sorties/`.

Visualiser : `python -m twinhyp visualiser --out sorties/` produit `sorties/figures/plan_2d.html` (plan par niveau) et `sorties/figures/vue_3d.html` (maquette 3D, vue de dessus), consultables hors ligne.

Voxels : `visualiser` produit aussi `sorties/figures/voxels.html` (coupe de la grille par altitude, couleur = matériau, positions autorisées au plafond) ; la grille complète est dans `sorties/grille_voxels.npz`.

IWCMC : `run` produit `pareto.json` (valeurs du tableau I) et `sorties/iwcmc/` (solutions, variante à atténuation renforcée) ; `python -m twinhyp sensibilite --out sorties/` compare la couverture à la figure 4 selon un facteur sur L_obs ; `visualiser` produit `sorties/figures/iwcmc.html`. Les matrices de perte (≈ 5 min) sont mises en cache.

Comparaison approfondie : `python -m twinhyp campagne --out sorties/` (≈ 33 min) ; résultats commentés dans `comparaison.md`.

Questions statiques : `python -m twinhyp questions --out sorties/` affiche les réponses Q01–Q19 obtenues par SPARQL sur `kg.ttl`. Les formes F3–F6 (équipements) ne sont différées que pour M1–M3 ; dès M4 (déploiement SSI, solveur MILP HiGHS), le graphe complet doit respecter F1–F8.

Agent (M6) : prérequis [Ollama](https://ollama.com) lancé (`ollama serve`) et `ollama pull qwen2.5:14b` (~9 Go de RAM, CPU suffisant ; ~23 min). Chaque appel est journalisé dans `sorties/llm_journal.jsonl` ; `agent_resume.json` compare chaque réponse à la référence sans LLM. Variables d'environnement : `TWINHYP_LLM_REJEU=<journal>` rejoue un run sans Ollama (copier le journal hors de `sorties/` n'est pas nécessaire), `TWINHYP_LLM_MODELE=<modèle>` change de modèle, `TWINHYP_LLM=factice` pour les tests de plomberie. Options dans `parametres.json`, clé facultative `agent` (`modele`, `url`, `graine`, `max_iterations`, `contexte`).

Fumée ou chaleur : `python -m twinhyp detecteurs --out sorties/` compare les délais d'alarme (fumée, chaleur A1 / A1R) et le nombre de détecteurs selon le rayon ; écrit `sorties/comparaison_detecteurs.json`.

Variantes : `data/variantes/` contient des copies de `parametres.json` qui ne changent qu'une clé (ex. `detecteur_type = HeatDetector`) ; `python -m twinhyp comparer sorties sorties_chaleur …` compare des dossiers de sorties étape par étape (M4 équipements, M5 alarme et routes, réponses de référence, décisions de M6) et écrit `comparaison.json`. Détail : `fumee_chaleur.md`.

Second IFC (étape 10) : `data/bureaux/` contient le bâtiment de bureaux NIBS, ses paramètres (mode rapide), un scénario synthétique et des questions / demandes adaptées :

```bash
python -m twinhyp run --ifc data/bureaux/Office_A_20110811.ifc --params data/bureaux/parametres_bureaux.json \
    --obs data/bureaux/observations_bureaux.csv --questions data/bureaux/questions_bureaux.json \
    --demandes data/bureaux/demandes_bureaux.json --out sorties_bureaux/
```

Scénario pour un autre bâtiment : `python -m twinhyp scenario --geometrie <out>/geometry.json --origine <espace> --sortie obs.csv`. Mode rapide : `"validation_kg_intermediaire": false` (graphe validé une fois, en fin de chaîne), `"pas_grille_m": 1.0`, `"iwcmc": {"max_positions": 40, "facteurs_supplementaires": []}`. Détail : `generalite.md`.

Chaque exécution écrit `sorties/execution.json` : versions des paquets, machine, graine et durée de chaque étape.

## Retrouver nos résultats (jury)

Les sorties livrées dans `sorties/` ont été produites par la commande unique ci-dessus (graine 0). Vérifié le 12/11/2026 sur deux runs neufs, dans des dossiers vides, avec deux valeurs de `PYTHONHASHSEED` :

| Sortie | Recalcul |
|---|---|
| `geometry.json`, `devices.json`, `evacuation_dynamique.jsonl`, `pareto.json` (+ `iwcmc/pareto_facteur30.json`) | **identiques** (hors durées `temps_s` / `temps_cpu_s`) |
| `ontology.ttl`, `kg.ttl` | **isomorphes** (mêmes triplets) |
| `answers.jsonl`, `audit_log.jsonl` | **identiques** (hors horodatage) en rejouant le journal du LLM : `TWINHYP_LLM_REJEU=sorties/llm_journal.jsonl python -m twinhyp run … --etapes m6` (≈ 2 min, sans Ollama) |

- Tout l'aléa est tiré d'une graine (`--graine`, défaut 0) : PREP-NSGA, *shadowing* X_σ, HiGHS (`random_seed = 0`).
- Les MILP de M4 sont résolus à l'optimum prouvé (statut « Optimal », gap 0, dans `devices.json`) ; si la limite `milp_limite_s` (défaut 600 s) était atteinte, un avertissement le signalerait.
- Le cache des matrices de perte de M3 (`sorties/iwcmc/obstacles_*.npz`, non livré) est recalculé à l'identique (≈ 5 min).
- M6 relancé **avec Ollama** (qwen2.5:14b, température 0, graine 0) : sur une autre machine, le texte des justifications peut varier ; les réponses sont contrôlées par une référence sans LLM (`conforme_reference` dans `answers.jsonl`) et les décisions sont prises par le moteur symbolique. Pour retrouver nos fichiers à l'identique, utiliser le rejeu ci-dessus.
- Versions exactes : `requirements.lock` (Python 3.11).

## Sorties

| Fichier | Module | Contrat |
|---|---|---|
| `geometry.json` | M1 | `data/schemas/geometry.schema.json` |
| `ontology.ttl`, `kg.ttl` | M2 | formes SHACL `data/ontologie/formes_publiques.ttl` |
| `pareto.json` | M3 | `pareto.schema.json` (liste des 4 scénarios) |
| `devices.json` | M4 | `devices.schema.json` |
| `evacuation_dynamique.jsonl` | M5 | `evacuation_dynamique.schema.json` |
| `answers.jsonl`, `audit_log.jsonl` | M6 | `answers.schema.json`, `audit_log.schema.json` |

Chaque sortie est validée contre son contrat à la fin de l'étape qui la produit : une sortie non conforme arrête la chaîne.

## Architecture

```
src/twinhyp/
  cli.py          commande unique (argparse)
  pipeline.py     orchestrateur M1 → M6, validation, trace d'exécution
  contexte.py     chemins + paramètres lus depuis parametres.json (aucune valeur en dur)
  io_schemas.py   écriture JSON/JSONL, validation JSON Schema et SHACL
  m1_geometrie/ … m6_agent/   un paquet par module ; chacun expose executer(ctx)
  visualisation/  plan 2D (depuis geometry.json) et vue 3D (depuis l'IFC), plotly
```

Les modules ne communiquent que **par les fichiers de sortie** : M2 lit `geometry.json`, pas l'IFC. Chaque module se teste et se relance seul.

## Tests

```bash
pytest              # tout
pytest -m "not integration"   # tests rapides seulement
```

Trois niveaux : unitaires, conformité (kit, schémas, SHACL), intégration (commande complète).

## Matériel

AMD Ryzen 7 7730U (8 cœurs / 16 fils), 15,4 Go de RAM, GPU intégré AMD (pas de CUDA) ; Windows 11. Les temps de calcul de chaque étape sont dans `sorties/execution.json`.

## Documentation

`docs/` : feuille de route, fiches théoriques par module, plan d'exécution, carnet de bord, historique des prompts (déclaration d'usage de l'IA).

Les articles de l'équipe ne sont pas versionnés (consigne du kit).
