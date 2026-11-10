# M6 – Agent neuro-symbolique (10 points)

## 1. Utilité

C'est la brique qui donne son titre à la thèse : une **IA agentique souveraine** qui pilote l'hyperviseur de jumeaux numériques.
- **Neuro** : un LLM open-weight exécuté **localement** comprend une demande en langage naturel (« quels espaces… ? », « déplacer l'équipement… »), choisit les outils et rédige la justification.
- **Symbolique** : les outils déterministes (SPARQL, optimiseur, planificateur, SHACL) **calculent et garantissent**. Le LLM n'a jamais le dernier mot sur la sécurité : une action n'est validée que si **toutes les formes SHACL passent** (veto symbolique).
- **Souverain** : aucune donnée du bâtiment ne sort de la machine, aucun LLM propriétaire par API.
- **Traçable** : chaque appel au modèle (prompt, réponse, durée) et chaque décision (`audit_log.jsonl`) sont journalisés. C'est indispensable en sécurité incendie, où une décision doit être auditable.

Livrables : `answers.jsonl` (20 questions) et `audit_log.jsonl` (4 demandes).

## 2. Fondements

### 2.1 LLM et exécution locale
- **Transformer** (Vaswani et al., 2017) : génération autorégressive $p(x_t \mid x_{<t})$. Le décodage peut être glouton (température 0) ou échantillonné. Pour la reproductibilité, on prend **température 0 et une graine fixe**.
- **Quantification** : mémoire ≈ nombre de paramètres × bits / 8. Un modèle de 8 milliards en Q4_K_M (~4,5 bits) occupe environ 4,5 à 5 Go ; un 14B occupe environ 9 Go. Le format GGUF est celui de llama.cpp et d'Ollama.
- **Ta machine** : Ryzen 7 7730U (8 cœurs), **15,4 Go de RAM**, GPU intégré AMD (pas de CUDA). L'inférence se fera **sur CPU**. Un 7–8B Q4 donne quelques tokens par seconde : c'est jouable. Un 14B (9 Go) est possible mais lent et serré en mémoire à côté du reste de la chaîne.
- **Déjà installé** : Ollama 0.40.13 avec `qwen2.5:14b`, `llama3.1` (8B), `mistral` (7B), `qwen3:4b`, `qwen:7b`. Le `qwen3-vl:30b` est hors des limites de l'énoncé (3 à 14 milliards de paramètres).

### 2.2 Patrons d'agents
- **ReAct** (Yao et al., 2023) : boucle *Pensée → Action (appel d'outil) → Observation → …* jusqu'à la réponse. Le champ `iterations` d'`answers.jsonl` correspond au nombre de tours de cette boucle.
- **Appel de fonctions (*function calling*)** : on décrit les outils par un schéma JSON et le modèle répond par un appel structuré. Ollama le prend en charge (`tools`), et il peut aussi **contraindre la sortie à un schéma JSON** (`format`). llama.cpp peut contraindre la sortie par une grammaire (GBNF). Le **décodage contraint** élimine les sorties mal formées, fréquentes avec les petits modèles.
- **Texte → SPARQL** : le LLM génère une requête à partir de la question et d'un **résumé de l'ontologie** (classes, propriétés, exemples) placé dans le prompt (*few-shot*). La requête est exécutée ; en cas d'erreur ou de résultat vide, le message d'erreur est renvoyé au modèle (**auto-correction**). C'est l'ancrage (*grounding*) : la réponse vient du résultat de la requête, pas de la « mémoire » du modèle, ce qui réduit les hallucinations.

### 2.3 Le contrôle symbolique (le cœur du « neuro-symbolique »)
Formalisation d'une demande :
1. le LLM traduit la demande en **plan structuré** $a$ (type d'action, cibles) ;
2. le moteur symbolique calcule le **delta** $\Delta_a = (\text{triplets ajoutés}, \text{triplets retirés})$ ;
3. on applique le delta sur une **copie** : $G' = (G \setminus \Delta^-_a) \cup \Delta^+_a$ ;
4. **validation** : $a$ est acceptable si et seulement si $G' \models \text{SHACL}$ (formes F1–F8 et formes maison), et, pour une route, si F8 tient à l'instant concerné ;
5. sinon, on génère des **adaptations** candidates $a'_1, a'_2, \ldots$ (règles), on les valide de la même façon, puis on les classe ;
6. **validation finale (*commit*)** ou **annulation (*rollback*)**, comme une transaction de base de données.

**Politique lexicographique** : sécurité des personnes ≻ accessibilité ≻ sobriété. Une adaptation $a'$ est préférée à $a''$ si elle est meilleure en sécurité ; à sécurité égale, si elle est meilleure en accessibilité ; et ainsi de suite. C'est un **ordre lexicographique** de la théorie de la décision multicritère : aucun gain de sobriété ne peut compenser une perte de sécurité.

Le champ `source` de l'audit distingue `llm` (décision proposée par le modèle et validée), `regle` (règle déterministe) et `veto_symbolique` (le moteur SHACL a bloqué la proposition).

### 2.4 Les 4 demandes, vues à travers les formes (hypothèses à confirmer en exécutant)
| Demande | Formes concernées | Décision probable |
|---|---|---|
| D1 – cuisine A103 en détecteurs de chaleur | F3 (un `HeatDetector` reste un `Detector`), F6 | **Acceptée** (ou avec adaptation si un même détecteur couvre aussi un autre espace : il faut alors le dédoubler) |
| D2 – déplacer l'équipement du couloir A201 vers A202 | F3 (A201 n'est plus couvert), F5 (chemin d'évacuation non surveillé) | **Refusée**, ou acceptée avec adaptation : ajout dans A202 sans retrait dans A201, éventuellement un relais pour la connectivité |
| D3 – retirer tous les détecteurs du Level 2 | F3 pour tous les espaces occupables du niveau | **Refusée**, ou adaptation : détection temporaire (chaleur, autonome), surveillance renforcée |
| D4 – à t = 200 s, envoyer l'étage A vers l'escalier « par la route habituelle » | F8 à t = 200 s | Dépend de l'état à t = 200 s : si la route habituelle traverse un espace `Dangerous`, **refus de la route habituelle et proposition de la route sûre** (ou d'aucune route + confinement) |

### 2.5 Journalisation et évaluation
- Pour chaque appel au LLM : prompt complet, réponse, durée, jetons (Ollama renvoie `prompt_eval_count`, `eval_count`, `total_duration`).
- `answers.jsonl` : `reponse` est une liste de GlobalId ou un nombre, `requetes_sparql` contient **les requêtes réellement exécutées**. Le jury recalcule : une réponse non retrouvée est éliminatoire.

## 3. Choix techniques et d'architecture

### Choix 1 – Moteur d'inférence
| Option | Pour | Contre |
|---|---|---|
| **Ollama** | Déjà installé, natif Windows, API REST simple, `tools` et `format` JSON, graine et température | Moins de contrôle fin que llama.cpp |
| llama.cpp (serveur) | Grammaires GBNF, contrôle total, très léger | Gestion manuelle des modèles |
| vLLM | Débit élevé | Nécessite un GPU NVIDIA et Linux : **inadapté à ta machine** |

**Aspects** : matériel (CPU seulement), facilité de démonstration à l'entretien (sans connexion, sans IA d'assistance), déterminisme, appel d'outils.

### Choix 2 – Modèle
Candidats parmi ceux déjà installés : `qwen2.5:14b` (meilleur en code, SPARQL et appel d'outils, mais lent et ~9 Go), `llama3.1:8b`, `mistral:7b`, `qwen3:4b` (rapide). D'autres modèles open-weight récents de 7 à 14B sont à envisager (vérifier les versions disponibles en novembre 2026).
**Aspects** :
- qualité de l'**appel d'outils** et de la génération SPARQL (point décisif ; à tester sur 3 ou 4 questions de `questions.json` avant de choisir) ;
- compréhension du **français** ;
- **latence sur CPU** × nombre d'appels (20 questions + 4 demandes, plusieurs itérations chacune) ;
- **licence** (Apache 2.0 pour Qwen et Mistral ; licence communautaire pour Llama). L'argument « souverain » peut favoriser un modèle européen (Mistral) ;
- mémoire disponible en parallèle de rdflib et de l'optimiseur.

### Choix 3 – Cadre d'agent
| Option | Pour | Contre |
|---|---|---|
| **Boucle ReAct écrite à la main** (~200 lignes) | Transparence totale, journalisation exacte, aucun appel caché, modifiable en 10 min à l'entretien | Écrire le parsing des appels |
| LangGraph / LangChain | Briques toutes faites | Dépendances lourdes, abstraction opaque, journalisation moins maîtrisée |
| smolagents | Léger | Moins de contrôle sur le format d'audit |

**Aspects** : exigence de journaliser chaque appel, explicabilité, maîtrise du code sans assistant.

### Choix 4 – Stratégie de réponse aux questions
| Option | Pour | Contre |
|---|---|---|
| Texte → SPARQL libre | Montre la vraie capacité « agentique » | Un petit modèle se trompe souvent (préfixes, chemins de propriétés) |
| **Outils paramétrés** (le LLM choisit un gabarit et ses arguments : niveau, espace, seuil…) | Fiable, générique (fonctionne sur un autre bâtiment), requêtes traçables | Moins « ouvert » |
| **Hybride** : gabarits d'abord, SPARQL libre en secours avec auto-correction | Robuste et démonstratif | Plus de code |

**Aspects** : exactitude (une réponse fausse est pénalisée, une réponse non retrouvée est éliminatoire), exigence « répondre avec l'agent », honnêteté de `requetes_sparql`, généralisation au bâtiment inconnu.

### Choix 5 – Pipeline de traitement des demandes
LLM → plan JSON (schéma contraint) → moteur de règles qui calcule le delta → SHACL sur la copie → adaptations → classement lexicographique → LLM pour la justification → audit.
**Aspects** : le LLM **ne doit jamais pouvoir contourner le veto** (le contrôle est du code, pas une consigne dans le prompt) ; `triplets_ajoutes` et `triplets_retires` sont calculés par le delta ; ordre de traitement imposé (D1 → D4, D4 sur l'état à t = 200 s) ; l'effet cumulatif (D1 accepté modifie le graphe vu par D2) doit être explicite.

### Choix 6 – Les 4 outils (minimum demandé)
1. `sparql_query(requete)` : **lecture seule** (refuser toute requête `INSERT`/`DELETE`) ;
2. `optimiser(type, contraintes)` : appelle M3/M4 (ré-optimisation locale après modification) ;
3. `planifier_evacuation(espace, t)` : appelle M5 (Dijkstra avec contrainte dure) ;
4. `valider_shacl(delta)` : applique le delta sur une copie et renvoie les formes violées.
**Aspects** : signatures simples et typées (les petits modèles se perdent avec trop d'arguments), sorties courtes (contexte limité), messages d'erreur exploitables par le modèle.

### Choix 7 – Reproductibilité
Température 0, graine fixe, version exacte du modèle (digest Ollama), prompts versionnés dans le dépôt, et éventuellement un **cache** des réponses du LLM pour rejouer sans recalcul.
**Aspects** : le jury recalcule à partir des sorties ; à l'entretien, la chaîne tourne sur un autre bâtiment, donc pas de cache utilisable : il faut un temps d'exécution compatible avec 10 minutes.

### Choix 8 – Conception du prompt système
Résumé compact de l'ontologie (classes, propriétés, préfixes), 3 à 5 exemples question → SPARQL, politique de priorité, schémas des outils, consigne « ne réponds qu'à partir des résultats d'outils ».
**Aspects** : taille du contexte (CPU : chaque token de prompt coûte du temps), généricité (pas d'exemples propres au duplex qui ne marcheraient pas ailleurs).

## 4. À maîtriser pour l'entretien
- Expliquer pourquoi le veto est **dans le code** et non dans le prompt, et pourquoi c'est la bonne architecture pour un système critique.
- Dérouler D2 ou D3 au tableau : delta, forme violée, adaptation retenue, place dans l'ordre lexicographique.
- Ajouter un 5ᵉ outil ou une nouvelle règle d'adaptation en 10 minutes.
- Justifier le choix du modèle par des mesures (exactitude sur les questions, latence), pas par réputation.
