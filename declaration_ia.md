# Déclaration d'usage de l'IA

## Outils utilisés

| Outil | Usage | Hors usage |
|---|---|---|
| **Claude Code** (Anthropic, modèle Claude Opus 5.5), assistant de programmation dans le terminal | écriture du code, des tests et de la documentation ; exécution des commandes ; lecture du kit ; recherche du second IFC | aucun résultat rapporté n'est produit par un LLM propriétaire : toutes les sorties sont calculées par la chaîne |
| **qwen2.5:14b** (Alibaba, Apache 2.0) via **Ollama**, exécuté **localement** sur CPU | agent M6 : choix de l'outil et de ses arguments, plan des demandes, rédaction des justifications | les réponses sont les résultats des outils, les décisions sont prises par le moteur symbolique (veto SHACL, ordre lexicographique) |

Aucune API de LLM propriétaire n'intervient dans la chaîne ni dans les résultats.

## Méthode de travail

- **Je pilotais, l'assistant exécutait.** Chaque étape (0 à 10) a été proposée, exécutée, puis **validée par moi** avant de passer à la suivante ; plusieurs choix ont été corrigés à ma demande (un déclencheur par sortie, objectif max-min du *full-view*, comparaison fumée / chaleur sur toute la chaîne, étape 10 sur un bâtiment de bureaux…).
- **Tous mes prompts sont recopiés mot pour mot** dans `docs/prompt.md`, chacun suivi du résultat obtenu.
- Chaque choix, avec les options écartées et le moment où y revenir, est dans `choix.md` ; les doutes de l'assistant, avec leur niveau de confiance, dans `doutes.md` ; le journal daté, **impasses comprises**, dans `docs/carnet_de_bord.md`.
- L'assistant a été tenu de signaler ses erreurs : par exemple, son explication initiale du *full-view* nul (« aucune caméra ne peut faire face ») était **fausse**, ce qui est écrit dans `doutes.md` (S-4) et le carnet.

## Ce que j'ai vérifié à la main

| Vérification | Où | Résultat |
|---|---|---|
| Les 21 espaces du duplex (niveau, nom, nom long, GSA BIM Area, GlobalId) dans **BIMvision** | `docs/verification_bimvision.md` | toutes les valeurs de la chaîne correspondent (10/11/2026) |
| Q01, Q05, Q10, Q12, Q14 recalculées dans BIMvision | idem | identiques |
| Portes du Level 2 dans l'arbre de BIMvision | idem | 7 portes visibles au lieu de 8 → **anomalie trouvée à la main** (porte A202–A201 sans niveau), ajoutée ensuite à la chaîne |
| Anomalies de la maquette (B202 en double, B105 « Room », `IsFireExit` textuel, escalier B sous Roof…) | `main.md`, « Écarts de la maquette » | confirmées dans BIMvision |
| Validation de chaque étape à partir des sorties et des figures (`plan_2d.html`, `vue_3d.html`, `voxels.html`, `iwcmc.html`) | `docs/prompt.md` | — |

## Vérifications automatiques (sans IA)

- 133 tests pytest, dont des cas synthétiques indépendants du duplex (polygone en U pour la formule de Pang, séries d'observations, géométries jouets).
- Les réponses de l'agent sont comparées à une **référence calculée sans LLM** (`answers.jsonl` : `conforme_reference`) ; un écart est signalé, jamais corrigé.
- Chaque sortie est validée contre son schéma et les formes SHACL ; `python -m twinhyp valider --out sorties` le refait sur des sorties existantes.

## Limites que je déclare

- Le code a été écrit en grande partie par l'assistant ; je dois le maîtriser pour l'entretien sans IA (modification de 10 minutes) : c'est l'objet de ma préparation (`reste_a_faire.md`, point 7).
- La rédaction du rapport et de cette déclaration a été assistée ; je les ai relues et je m'en porte garant.
