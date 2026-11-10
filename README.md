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
