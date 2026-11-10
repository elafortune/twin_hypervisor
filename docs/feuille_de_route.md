# Feuille de route – Test technique CIFRE TwinHypervisor

> « Du BIM au SSI neuro-symbolique » – uGetWin / LIGM (UMR 8049), Université Gustave Eiffel
> Synthèse de l'énoncé (`Exercice_enonce.pdf`) et du kit, établie le 2026-11-07.

## Objectif

Construire **en petit** la chaîne logicielle visée par la thèse : une IA agentique souveraine qui pilote un jumeau numérique de bâtiment, appliquée à la sécurité incendie (SSI). On part de la maquette numérique d'un duplex (2 logements A et B, 2 niveaux) et on suit ces étapes :

**IFC → jumeau géométrique → graphe de connaissances (ontologie) → placement optimal des capteurs → évacuation dynamique pendant un incendie → agent LLM local contrôlé par des règles symboliques (SHACL)**

Il faut aussi **reproduire l'article IWCMC 2024 de l'équipe** (Chambon et al.) et le confronter à ses résultats.

## Dates clés

- **Remise : jeudi 12 novembre 2026 à 16h00**, dans un dépôt Git partagé avec le jury.
- **Second entretien : vendredi 13 novembre 2026**, en présentiel, 45 min, **sans assistant IA**, entre 9h15 et 11h15.
- L'IA est autorisée pour le test à condition de la **déclarer**.

## Les 6 modules (75 pts) + qualité (5) + entretien (20)

| Module | Pts | Ce qu'il faut faire |
|---|---|---|
| **M1 – Jumeau géométrique** | 15 | Extraire de l'IFC les niveaux, espaces, portes, sorties et escaliers. Calculer la connectivité entre espaces selon la méthode de [Pang] (chaîne mur → ouverture → porte, limites virtuelles) et la distance d'évacuation depuis le point le plus défavorable. Construire la grille de voxels et les positions autorisées par lancer de rayons vers le plafond, comme dans [IWCMC]. **Trouver les incohérences volontairement ajoutées à la maquette** et les documenter. |
| **M2 – Graphe de connaissances** | 15 | Étendre l'ontologie socle (`ssi_socle.ttl`) en l'alignant sur BOT, SOSA/SSN et SAREF, puis la comparer à celle de [Pang]. Générer automatiquement le graphe RDF depuis l'IFC et représenter les observations avec SOSA. Le graphe doit respecter les **8 formes SHACL publiques**, plus des formes cachées que le jury appliquera. |
| **M3 – Reproduction IWCMC 2024** | 15 | Implémenter le modèle de propagation multi-murs (matériaux IFC, WiFi 2,4 GHz, tableau I), le score de couverture, la µ-connexité et PREP-NSGA (tableau II). Comparer **4 scénarios** : avec ou sans jumeau, µ = 0 ou µ = 3. Confronter les fronts de Pareto aux figures 4 et 5 de l'article et expliquer les écarts. |
| **M4 – Déploiement SSI** | 10 | Placer les caméras (modèle [PIMRC] transposé en 3D, couverture des chemins d'évacuation, full-view), les détecteurs (rayon 5 m) et les déclencheurs manuels (10 m max d'une sortie). Vérifier la connectivité réseau avec le modèle de M3. Le graphe doit alors respecter les formes F3 à F6. |
| **M5 – Évacuation dynamique** | 10 | Rejouer `observations.csv` (600 s, un pas toutes les 10 s) avec l'algorithme 1 de [Pang] : alarme si l'obscurcissement dépasse 0,0328 /m, espace « Dangerous » si la température dépasse 60 °C ou le CO 1 000 ppm. Comparer la stratégie 1 (sortie la plus proche) et la stratégie 2 (Dijkstra sur le graphe dynamique). Remplacer la pénalité de 1 000 m de Pang par une **contrainte dure (F8)** et montrer le cas où il n'existe plus aucune route sûre. |
| **M6 – Agent neuro-symbolique** | 10 | Construire un agent avec un **LLM open-weight local** de 3 à 14 milliards de paramètres (Ollama, llama.cpp ou vLLM ; un modèle 4 bits sur CPU suffit). Il lui faut **au moins 4 outils** : requête SPARQL, optimiseur, planificateur d'évacuation et validation SHACL. Chaque appel au modèle doit être journalisé (prompt, réponse, durée). L'agent répond aux **20 questions** et traite les **4 demandes de modification**. |
| Qualité logicielle | 5 | Tests automatisés, historique Git propre. |
| Second entretien | 20 | Voir plus bas. |

### Les demandes de modification (M6) : des pièges volontaires

La politique à appliquer est **sécurité des personnes > accessibilité > sobriété**. Certaines demandes ne doivent pas être acceptées telles quelles :
- **D1** : passer la cuisine A103 en détecteurs de chaleur. A priori acceptable, en vérifiant que F3 et les formes liées restent valides.
- **D2** : déplacer l'équipement qui couvre le couloir A201 vers la chambre A202. Probablement contraire à F3 ou F5, puisque le couloir est un chemin d'évacuation.
- **D3** : retirer tous les détecteurs du Level 2 pendant des travaux. Viole F3, donc refus ou adaptation (par exemple une détection temporaire).
- **D4** : à t = 200 s, envoyer les occupants de l'étage A vers l'escalier « par la route habituelle ». À vérifier contre F8 : si la route traverse un espace dangereux, il faut la refuser ou l'adapter.

*(Premières hypothèses : chaque décision doit être confirmée en lançant réellement le validateur SHACL sur le graphe.)*

## Livrables

| Livrable | Format |
|---|---|
| **Code** | Dépôt Git avec **historique complet** et **tests automatisés** |
| **Reproduction** | **Une seule commande** qui rejoue toute la chaîne avec en arguments un IFC, un fichier de paramètres et un fichier d'observations |
| **Sorties** (conformes aux schémas de `schemas/`) | voir le tableau suivant |
| **Rapport** | **6 pages maximum**, avec les écarts à l'article IWCMC et les incohérences trouvées |
| **Carnet de bord + déclaration IA** | Entrées datées, **y compris les impasses**, outils utilisés et ce qui a été vérifié à la main |

### Les 8 fichiers de sortie

| Fichier | Contenu |
|---|---|
| `geometry.json` | `niveaux`, `espaces` (polygone, surface, hauteur, occupable), `portes` (largeur, espaces, sortie), `liaisons` (porte, ouverture ou escalier), `anomalies` (élément, description, traitement) |
| `ontology.ttl` | L'ontologie étendue |
| `kg.ttl` | Le graphe de connaissances complet |
| `pareto.json` | Pour chaque scénario : `scenario`, `parametres_algo`, `front` avec `n_equipements` et `couverture` (plus des champs optionnels : connectivité, qualité de lien en dBm…) |
| `devices.json` | `parametres`, `objectif` (valeur, statut du solveur, temps, mode 2D ou 3D), `equipements` (id, type, espace, x, y, z, orientation…) |
| `evacuation_dynamique.jsonl` | Une ligne par pas de temps, espace occupé et stratégie : `t_s`, `espace_globalId`, `strategie`, `route` (`null` si aucune route sûre), `sortie_globalId`… |
| `answers.jsonl` | Une ligne par question : `id`, `reponse` (liste de GlobalId IFC ou nombre), `requetes_sparql` |
| `audit_log.jsonl` | Une ligne par action : `horodatage`, `demande_id`, `action`, `decision` (`acceptee`, `refusee` ou `acceptee_avec_adaptation`), `justification`, `formes_violees`, `source` (`llm`, `regle` ou `veto_symbolique`) |

## Consignes importantes

- **Uniquement des bibliothèques et solveurs libres.** Aucun LLM propriétaire par API pour les résultats rapportés : l'IA aide à coder, mais l'agent M6 doit tourner sur un modèle local.
- **Déclarer le matériel et les temps de calcul.**
- **Tous les résultats seront recalculés à partir des sorties : un résultat non retrouvé est éliminatoire.** La reproductibilité est le critère central.
- Des **formes SHACL cachées** seront appliquées : modéliser proprement, ne pas se contenter de passer les 8 formes publiques.
- Les messages de F4 et F5 parlent d'un **« paramètre personnel »** : ne jamais coder en dur les valeurs (couverture vidéo 1,0, distance des déclencheurs 10 m), toujours les lire depuis `parametres.json`.
- Les questions Q15 à Q20 sont **vérifiées sur nos propres sorties** : les réponses doivent être cohérentes avec les fichiers produits.
- **Ne pas diffuser les articles** de l'équipe.
- Test de départ : `pyshacl -s ontologie/formes_publiques.ttl -e ontologie/ssi_socle.ttl -i rdfs -a ontologie/exemple_minimal.ttl` doit afficher `Conforms: True`.

## Second entretien (45 min, sans IA)

1. Un **autre IFC, plus grand, et un nouveau scénario** : lancer la chaîne en direct pendant la présentation (10 min). La chaîne doit être **générique**, sans dépendance aux GlobalId du duplex.
2. Analyse commune des résultats.
3. Changement d'un paramètre : **prédire son effet** avant de relancer.
4. **Modification de code d'environ 10 min**, sans IA : il faut maîtriser son code.
5. Au tableau : **formulation du problème d'optimisation** et justification d'un **choix de modélisation de l'ontologie**.

Venir avec son ordinateur, la chaîne installée et prête à tourner.

## Remarques

- Le dossier contient `~$ercice_enonce.docx`, simple fichier verrou de Word : le vrai `.docx` est absent, le PDF suffit.
- Contact : abderrezak.rachedi@univ-eiffel.fr — objet « Exercice CIFRE TwinHypervisor ».

## Étapes de travail

1. ✅ Lecture de l'énoncé et du kit → cette feuille de route.
2. ✅ Phase de compréhension théorique, module par module → dossier `theorie/` (à relire et approfondir).
3. ✅ Ordre des étapes, connaissances et lectures → `plan_execution.md`.
4. Architecture du dépôt et choix de la stack.
5. Implémentation M1 → M6, tests, commande de reproduction.
6. Rapport (6 pages), carnet de bord, déclaration IA.
7. Répétition de l'entretien (chaîne sur un autre IFC, formulation au tableau).
