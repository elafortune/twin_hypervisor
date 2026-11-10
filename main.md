# Mémo – commandes et résultats

Depuis `C:\Users\emeri\twin_hypervisor`, après `conda activate twinhyp`.

## Commandes

| Commande | À quoi elle sert |
|---|---|
| `python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc --params data/parametres.json --obs data/observations.csv --out sorties` | Rejoue toute la chaîne M1 → M6 et écrit les 8 sorties dans `sorties/` |
| `… run … --etapes m1` | Relance seulement certains modules (ex. `m1,m2`) |
| `python -m twinhyp visualiser --out sorties` | Crée `sorties/figures/plan_2d.html`, `voxels.html` (coupes de la grille par altitude) et `vue_3d.html` (double-clic pour ouvrir) ; cliquer « Distances (pire point) » dans la légende du plan pour voir les distances |
| `python -m twinhyp visualiser --out sorties --sans-3d` | Plan 2D seul (1 s au lieu de 15 s) |
| `python -m twinhyp valider --out sorties` | Revérifie que les sorties respectent schémas et formes SHACL |
| `python -m twinhyp questions --out sorties` | Affiche les réponses Q01–Q19 obtenues par SPARQL sur `kg.ttl` (`--sparql` : montre les requêtes) |
| `pytest` | Lance tous les tests (~3 min) |
| `pytest -m "not integration"` | Tests rapides seulement |

## Résultats par phase

| Phase | Résultat en une phrase |
|---|---|
| 0 – Squelette | La commande unique produit les 8 sorties conformes et `execution.json` trace machine, versions et durées. |
| 1 – Extraction IFC | 4 niveaux, 21 espaces (R301 seul non occupable), 14 portes dont 4 sorties, 2 escaliers, extraits en 1,4 s. |
| 1 – Anomalies | 7 constats : `B202` en double (dont un vrai `B203`), B105 « Room » au lieu d'escalier, `IsFireExit` textuel, escalier B rattaché au toit, marches en pieds. |
| 1 – Surfaces | La surface géométrique est 7 à 23 % sous « GSA BIM Area » partout : convention de mesure, pas une anomalie. |
| 1 – Réponses préliminaires | Q05 = 138,16 m² · Q10 = 134,53 m² · Q12 = A204, B204 · Q14 = 4 portes de 0,762 m. |
| 2 – Connectivité | 20 liaisons (10 portes, 8 ouvertures libres, 2 escaliers) et 4 sorties ; tout espace occupable atteint une sortie ; aucun passage entre logements A et B (Q13 vide). |
| 2 – Anomalies | 5 constats de plus : porte A204–A205 reliée à tort à A201 dans l'IFC, cages d'escalier qui empiètent sur une chambre, limites de A201/B201 décalées de 6–10 m, 12 limites « EXTERNAL » entre deux espaces. |
| 2 – Réponses préliminaires | Q03 = A101, A102, B101, B102 · Q04 = A102, A103, A105 · Q09 = A105, B105 · Q13 = ∅. |
| 3 – Distances | 40 distances orientées (point le plus défavorable → passage) + 4 vers les sorties ; la formule de Pang égale Dijkstra sur tout le duplex ; volée = 4,85 m. |
| 3 – Réponses préliminaires | Q07 = 0,864 m (A202 → A201 → A105 → A101 → entrée) · Q08 confirmée = B201, B105, B101. |
| 4 – Graphe de connaissances | `ontology.ttl` (socle + extension alignée BOT/SAREF4BLDG) et `kg.ttl` (~880 triplets) conformes aux formes publiques F1, F2, F7, F8 et à 9 formes maison ; F3–F6 attendent les équipements de M4. |
| 4 – Réponses par SPARQL | Les 14 questions statiques sont obtenues par requêtes sur le graphe, identiques aux réponses calculées en Python ; Q11 = A102, B102 (séjours). |
| 5 – Évacuation dynamique | Feu en cuisine A103 : alarme à 70 s, A101 dangereux à 180 s ; dès lors les chambres A202/A203 n'ont plus de route sûre (confinement), alors que la pénalité de Pang leur propose une route de 1 026 m à travers le feu ; le logement B évacue normalement. |
| 5 – Réponses | Q15 = 70 s · Q16 = A101, A102, A103, A105, A201 · Q17 = A202, A201, A105, A101 · Q18 = 180 s · Q19 = A202, A203. |
| 5 – Détour réactif | Sans guidage dynamique, l'occupant de A202 qui suit le plan à t = 180 s est bloqué dans la cage A105 après 15 m (dangereuse à 250 s) : pire que le confinement recommandé par la stratégie 2. |
| 6 – Voxels | Grille 16 × 34 × 24 (pas 0,5 × 0,5 × 0,25 m, comme l'IWCMC), 38 % d'obstacles colorés par matériau ; plaque de plâtre = 47 % des voxels obstacles (8 % en volume réel) contre 18 % annoncés par l'IWCMC : écart à discuter. |
| 6 – Positions autorisées | 932 positions au plafond (518 au Level 1 à 2,60 m, 414 au Level 2 à 5,70 m), uniquement au-dessus des espaces occupables. |

## Écarts de la maquette à présenter au jury

Vérifiés à la main dans BIMvision le 10/11 (toutes les valeurs de la chaîne correspondent).

| Écart | Ce qu'on observe | Ce que fait la chaîne |
|---|---|---|
| `B202` en double | Deux espaces nommés `B202` ; « Bedroom 2 » a pour numéro Revit `B203` | Identifie par GlobalId ; signale `B203` comme nom d'origine |
| B105 « Room » | Catégorie OmniClass « Stairway », jumeau de A105 « Stair » | Traite B105 comme une cage d'escalier |
| `IsFireExit` | Valeur texte « IsFireExit » sur les 14 portes | Ignore la propriété ; sorties par géométrie + `IsExternal` |
| Escalier B sous Roof | Rattaché au toit alors que sa base est à 0 m | Le replace sur Level 1 |
| Marches en pieds | Hauteur 0,6357 et giron 0,8202 dans un fichier en mètres | Utilise la géométrie |
| Porte A204–A205 | L'IFC la relie aussi au couloir A201 (pas sa symétrique dans B) | Vote 3 sources : A201 écarté |
| Cages d'escalier | A105 / B105 empiètent de 0,15 m² sur A203 / B202 | Pas de liaison, signalé |
| Limites de A201 / B201 | Décalées de 6 à 10 m (placement de l'espace modifié) | Contact géométrique utilisé |
| Limites « EXTERNAL » | 12 limites virtuelles entre deux espaces typées externes | Traitées comme internes |
| Porte A202–A201 orpheline | La porte `…159834` (Mark A202, 0,864 m) n'est rattachée à aucun niveau : BIMvision ne montre que 7 portes sous Level 2 | Niveau déduit du placement ; règle `rattachement_spatial` (trouvée grâce à la vérification BIMvision) |
| Risque : espaces sans caméra | 7 espaces seulement ont un comptage de personnes ; à t = 600 s, 6 espaces dangereux (A101, A103, A104, A105, A201, A204) n'en ont pas : des personnes peuvent y être bloquées sans être vues | Signalé à chaque pas dans `evacuation_dynamique.jsonl` (`espaces_dangereux_sans_comptage`) |
| Q13 vide | Aucun passage direct entre A et B | À justifier (question piège possible) |

## Choix de méthode à valider / défendre

Liste complète, avec les options écartées : `choix.md`.

| Choix | Pourquoi |
|---|---|
| Un désaccord entre sources n'est une anomalie que si la source IFC est minoritaire ou absente | Sinon la chaîne de Pang crée seule 2 fausses anomalies (cages A105/B105 citées à cause du chevauchement de 0,15 m²) |
| Une paire reliée à la fois par un escalier et une limite virtuelle ne garde que « escalier » | La limite virtuelle A105–A201 matérialise l'arrivée de la volée, ce n'est pas un second passage |
| `surface_m2` = « GSA BIM Area » (pas la surface géométrique) | Q05 et Q10 la citent ; l'écart de 7–23 % est une convention de mesure |
| Espace non occupable = mot-clé dans le nom (roof, gaine, plenum…) uniquement | Le critère « niveau le plus haut » proposé au départ classerait à tort un dernier étage habité |

## Où trouver le détail

- Tous les choix, options écartées et quand y revenir : `choix.md`
- Mes doutes, à vérifier ou trancher : `doutes.md`
- Décisions et résultats des étapes 0 à 2 : `docs/etape0a2.md`
- Journal daté (y compris impasses) : `docs/carnet_de_bord.md`
- Vérifications à la main : `docs/verification_bimvision.md`
- Trace des prompts (déclaration IA) : `docs/prompt.md`
