# Phase de compréhension théorique

Une fiche par module. Chaque fiche suit le même plan :

1. **Utilité** : ce qu'est le module et à quoi il sert dans la chaîne.
2. **Fondements** : équations, théorèmes, normes et articles qui le régissent.
3. **Choix techniques et d'architecture** : les décisions à prendre et, pour chacune, les aspects à peser.
4. **À maîtriser pour l'entretien** : ce qu'on pourra te demander au tableau ou en modification de code.

| Fiche | Module | Points |
|---|---|---|
| [M1_jumeau_geometrique.md](M1_jumeau_geometrique.md) | IFC → espaces, portes, graphe de connectivité, distances, voxels | 15 |
| [M2_graphe_connaissances.md](M2_graphe_connaissances.md) | Ontologie (BOT/SOSA/SAREF), graphe RDF, SHACL | 15 |
| [M3_reproduction_IWCMC.md](M3_reproduction_IWCMC.md) | Propagation multi-murs, couverture, µ-connexité, PREP-NSGA | 15 |
| [M4_deploiement_SSI.md](M4_deploiement_SSI.md) | Caméras 3D, détecteurs, déclencheurs, réseau | 10 |
| [M5_evacuation_dynamique.md](M5_evacuation_dynamique.md) | Rejeu des observations, Dijkstra, contrainte dure F8 | 10 |
| [M6_agent_neuro_symbolique.md](M6_agent_neuro_symbolique.md) | LLM local, outils, SPARQL, veto SHACL, audit | 10 |

## Vue d'ensemble : flux de données entre modules

```
duplex.ifc ──► M1 ──► geometry.json (espaces, portes, liaisons, distances, anomalies)
                │       └─► grille de voxels + matériaux + positions autorisées A
                ▼
               M2 ──► ontology.ttl + kg.ttl  ◄──────────────┐
                │      (SHACL F1, F2, F7)                    │
   voxels+A ──► M3 ──► pareto.json                           │
                │      (modèle radio réutilisé)              │
                ▼                                            │
               M4 ──► devices.json  ──► kg.ttl (F3–F6)       │
                                                             │
observations.csv ─► M5 ──► evacuation_dynamique.jsonl ──► kg.ttl (états, routes, F8)
                                                             │
questions.json, demandes.json ─► M6 (LLM + 4 outils) ──► answers.jsonl, audit_log.jsonl
```

**Idée directrice de la thèse** : le LLM *propose et explique*, le symbolique *calcule et garantit*. Chaque module doit produire des faits vérifiables (calcul déterministe + validation SHACL) que l'agent M6 ne fait qu'orchestrer.

## Trois principes transverses

1. **Généricité** : à l'entretien, la chaîne tourne sur un autre IFC, plus grand. Aucun GlobalId, nom d'espace ou seuil codé en dur : tout vient de l'IFC, de `parametres.json` ou des observations.
2. **Reproductibilité** : le jury recalcule tout à partir de tes sorties. Graines aléatoires fixées, tri déterministe (départage des égalités), versions des bibliothèques figées, temps de calcul et matériel déclarés.
3. **Traçabilité** : chaque hypothèse ou écart (à l'article, à la maquette) est documenté dans le carnet de bord, puis dans le rapport.

## Premiers indices relevés dans le kit (à confirmer en M1)

- L'IFC est en **IFC2x3** (Revit 2011), alors que Pang travaille en IFC4. Il n'y a **aucun `IfcVirtualElement`** : la connectivité « sans porte » doit venir d'ailleurs (50 `IfcOpeningElement` pour seulement 38 `IfcRelFillsElement` → 12 ouvertures sans remplissage, candidates aux « ouvertures libres » de Q04).
- 21 `IfcSpace`, 14 portes, 2 escaliers, 4 niveaux (`T/FDN`, `Level 1`, `Level 2`, `Roof`).
- Incohérences visibles dès la lecture brute : **deux espaces nommés `B202`** (« Bedroom 2 » et « Bedroom 1 »), `B105` de nom long « Room » alors que son homologue `A105` est « Stair », un espace `R301` « Roof ».
- La forme **F8** cible aussi `ssi:routeFor` : une route pour des occupants qui se trouvent *déjà* dans un espace dangereux viole F8.
- La forme **F3** utilise `rdfs:subClassOf*` : la validation doit inclure l'ontologie (`-e ontologie -i rdfs`).
