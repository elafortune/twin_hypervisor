# M5 – Évacuation dynamique (10 points)

## 1. Utilité

Pendant l'incendie, le jumeau numérique devient un **outil d'aide à la décision en temps réel** :
1. il **ingère** les observations des capteurs (fumée, température, CO, comptage de personnes par caméra) toutes les 10 s ;
2. il **met à jour** le graphe : alarme, état `Normal`/`Dangerous` des espaces, personnes en attente ;
3. il **recalcule** pour chaque espace occupé la meilleure route sûre vers une sortie ;
4. il **détecte** les situations sans issue (aucune route sûre) et recommande alors une autre action (confinement, signalement aux secours).

On compare ainsi la consigne classique (plan d'évacuation statique, ISO 23601) avec un guidage dynamique fondé sur le graphe ([Pang]), et on corrige la faiblesse de Pang (la pénalité de 1 000 m) par une contrainte dure.

## 2. Fondements

### 2.1 Algorithme 1 de [Pang] (mise à jour du graphe)
```
initialiser le graphe ; pas de temps t1..T ; capteurs 1..N
pour chaque t :
    insérer les observations de t dans le graphe
    pour chaque capteur n :
        si la valeur est dans la plage de danger :
            mettre à jour l'état de l'espace (Dangerous) et ses distances d'évacuation
```

### 2.2 Seuils (pédagogiques, issus de Pang)
- **Alarme** : obscurcissement > **0,0328 /m**. C'est le seuil classique de **1 %/pied** des détecteurs de fumée (UL 268), car 1 %/ft = 3,28 %/m. L'obscurcissement découle de la loi de **Beer–Lambert** : $I/I_0 = e^{-K L}$, d'où une obscuration par mètre égale à $1 - e^{-K}$.
- **Dangerous** : température > **60 °C** ou CO > **1 000 ppm**. Ce sont les valeurs médianes de la classe « Dangerous » du tableau 3 de Pang (50–80 °C, 200–2 000 ppm), qui reprend des niveaux de tenabilité.
- Pour aller plus loin (rapport, entretien) : **ISO 13571**, tenabilité par dose effective fractionnaire (FED de Purser), et concepts **ASET/RSET** (temps disponible / temps nécessaire pour évacuer). Pang raisonne en instantané, pas en dose cumulée : c'est une limite à mentionner.

### 2.3 Plus court chemin : Dijkstra
- Graphe orienté pondéré $G_t = (V, E, w)$, avec $w(u \to v)$ = `EvacuationDistance(from = u, to = v)` de M1.
- **Dijkstra** (1959) : correct si les poids sont **positifs ou nuls** (F7 l'impose : distance > 0). Complexité $O((V + E)\log V)$ avec un tas. L'invariant glouton est le suivant : le nœud extrait du tas a sa distance définitive.
- **Astuce multi-sorties** : on ajoute un nœud fictif « Extérieur », relié à chaque sortie par une arête de poids 0. Un seul Dijkstra depuis ce puits, sur le **graphe inversé**, donne la distance et la route de *tous* les espaces d'un coup.
- **Départage déterministe** : à distance égale, le résultat dépend de l'ordre de parcours. Il faut trier les nœuds (par GlobalId) pour que les résultats soient reproductibles (Q17 est vérifiée sur tes sorties).

### 2.4 Les deux stratégies ([Pang] §5.3, tableaux 5–8)
- **Stratégie 1 – sortie la plus proche** : route calculée sur le graphe **statique** (sans tenir compte du feu), comme sur un plan d'évacuation. Dans Pang (tableau 7), les occupants suivent cette route, découvrent sur place un espace impraticable et se détournent : la route réelle s'allonge (70,1 m) et devient risquée.
- **Stratégie 2 – Dijkstra sur le graphe dynamique** : on tient compte des espaces dangereux à l'instant $t$.

### 2.5 Pénalité ou contrainte dure (cœur de la question M5.3)
| | Pénalité de Pang | Contrainte dure (F8) |
|---|---|---|
| Mise en œuvre | $w(u \to v) \leftarrow 1\,000$ m si $v$ est dangereux | On retire les nœuds dangereux : $G_t' = G_t - D_t$ |
| Une route sûre existe | Même résultat, tant que les vraies routes font moins de 1 000 m | Même résultat |
| **Aucune route sûre** | Dijkstra renvoie quand même une route (coût ≥ 1 000) **qui traverse le feu**, présentée comme « optimale » | Aucun chemin : **route = `null`** et action alternative |
| Bâtiment très grand | Une route sûre de plus de 1 000 m peut perdre face à une route dangereuse : **erreur silencieuse** | Correct quelle que soit la taille |
| Graphe de connaissances | La distance est **falsifiée** (le graphe ment sur la géométrie) | La géométrie reste vraie ; le danger est porté par l'état |
| Vérifiabilité | Rien à vérifier formellement | SHACL F8 rejette toute route qui traverse un espace `Dangerous` |

Formellement : avec la pénalité, on minimise $\sum w + M \cdot |\text{espaces dangereux traversés}|$, ce qui revient à une **relaxation lagrangienne** de la contrainte, sans garantie de faisabilité. Avec la contrainte dure, on cherche un plus court chemin **sous la contrainte** $\text{route} \cap D_t = \emptyset$. L'existence d'une route se décide par un simple parcours (BFS) de $G_t'$.

**Subtilité F8** : la forme cible aussi `ssi:routeFor`. Si les occupants sont *eux-mêmes* dans un espace `Dangerous`, toute route les concernant viole F8. Il faut décider (et documenter) : `route = null` avec l'action « évacuer immédiatement vers l'espace sûr adjacent / secours prioritaire », ou exclure l'espace de départ du contrôle (ce qui contredirait F8). Q18 (« plus aucune route sûre ») dépend de ce choix.

### 2.6 Occupation
- `peopleCount` vient des **caméras** (`CAM_A102`, … de type `Camera`, unité « personnes »). Seuls les espaces équipés de caméra ont un comptage connu.
- Les déplacements des personnes ne sont pas simulés : les comptages des observations font foi (Q19 : « à t = 300 s, quels espaces comptent encore des personnes »).

## 3. Choix techniques et d'architecture

### Choix 1 – Architecture du rejeu
| Option | Pour | Contre |
|---|---|---|
| **Boucle temporelle qui met à jour le graphe RDF** (SPARQL UPDATE), puis construit le graphe de routage par requête SPARQL (Q4/Q5 de Pang) | Fidèle à Pang et à l'énoncé (« mettre à jour le graphe »), neuro-symbolique de bout en bout | Un peu plus lent (60 pas : négligeable) |
| Calcul en mémoire (pandas + networkx), écriture du graphe à la fin | Rapide, simple | Le graphe n'est plus la source de vérité |

**Aspects** : fidélité, cohérence entre `evacuation_dynamique.jsonl` et `kg.ttl`, réutilisation par l'outil « planificateur » de M6.

### Choix 2 – Persistance de l'état `Dangerous`
Options : **verrouillé** (une fois dangereux, toujours dangereux) ou **réversible** (retour à `Normal` si les valeurs redescendent).
**Aspects** : la sécurité des personnes est prioritaire (un espace qui a dépassé 60 °C reste suspect ; dégradation des structures), réalisme physique, réponses à Q16/Q18. Choix prudent : verrouillé, ou hystérésis avec un seuil de retour plus bas, à justifier.

### Choix 3 – Espaces sans capteur
État inconnu : supposé `Normal` (optimiste), `Dangerous` (pessimiste) ou déduit des voisins.
**Aspects** : couverture réelle des capteurs dans `observations.csv`, sécurité, et lien avec M4 (le déploiement est censé garantir la couverture).

### Choix 4 – Granularité de la sortie
Le schéma impose une ligne par (t, espace occupé, stratégie), avec `route`, `sortie_globalId`, `distance_m`, `espaces_dangereux` et `action_recommandee`.
**Aspects** : calculer à **chaque pas** ou seulement à partir de l'alarme (Pang commence à l'alarme ; Q17 porte sur « l'instant de l'alarme ») ; définir quels espaces sont « occupés » (peopleCount > 0).

### Choix 5 – Modélisation de la stratégie 1
Route statique pure (calculée une fois) ou route statique avec **détour réactif** quand l'occupant rencontre un espace dangereux (comme dans le tableau 7 de Pang).
**Aspects** : fidélité à Pang, clarté de la comparaison, interprétation de la colonne `route` pour la stratégie 1.

### Choix 6 – Action recommandée sans route sûre
Confinement dans l'espace en fermant les portes, déplacement vers l'espace sûr le plus éloigné du feu, ou signalement prioritaire aux secours (position et nombre de personnes).
**Aspects** : sécurité des personnes, lien avec M6 (l'agent doit refuser D4 si la « route habituelle » traverse un espace dangereux).

### Choix 7 – Pondération des escaliers et des liaisons sans porte
Longueur géométrique seule, ou majoration (vitesse plus faible dans l'escalier) ; distances orientées de M1.
**Aspects** : cohérence avec M1, réalisme, impact sur Q17.

## 4. À maîtriser pour l'entretien
- Démontrer l'échec de la pénalité sur un mini-graphe au tableau : deux chemins, l'un de 1 200 m sûr, l'autre de 20 m via un espace dangereux (+1 000 m) ; la pénalité choisit le dangereux.
- Prédire : si le seuil de température descend de 60 à 50 °C, des espaces deviennent dangereux plus tôt, l'instant « plus de route sûre » (Q18) arrive plus tôt, et il y a plus de lignes avec `route = null`.
- Expliquer le Dijkstra multi-sorties avec le super-puits.
