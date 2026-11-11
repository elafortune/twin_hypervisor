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

Chaque exécution écrit `sorties/execution.json` : versions des paquets, machine, graine et durée de chaque étape.

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
