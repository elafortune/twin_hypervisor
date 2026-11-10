# M2 – Graphe de connaissances (15 points)

## 1. Utilité

Le graphe de connaissances (KG) est la **mémoire symbolique** du jumeau numérique. Il rassemble dans un même formalisme :
- la structure du bâtiment (niveaux, espaces, portes, liaisons, distances), issue de M1 ;
- les équipements SSI (M4) ;
- les observations des capteurs et l'état dynamique des espaces (M5) ;
- les routes recommandées (M5).

Il sert à :
1. **Interroger** (SPARQL) : c'est l'outil principal de l'agent M6 pour répondre aux questions.
2. **Valider** (SHACL) : c'est le garde-fou symbolique. Une action n'est validée que si le graphe reste conforme.
3. **Interopérer** : en s'alignant sur des ontologies standard (BOT, SOSA/SSN, SAREF), le graphe devient lisible par d'autres outils et d'autres jumeaux. C'est le « interopérable » du titre de la thèse.

## 2. Fondements

### 2.1 RDF, RDFS, OWL
- **RDF** : un graphe est un ensemble de triplets $(s, p, o) \in (I \cup B) \times I \times (I \cup B \cup L)$, avec $I$ = IRI, $B$ = nœuds anonymes et $L$ = littéraux typés (`xsd:decimal`, `xsd:dateTime`…).
- **RDFS** : `rdfs:subClassOf` et `rdfs:subPropertyOf` (transitifs), `rdfs:domain` et `rdfs:range`.
  **Piège classique** : `domain`/`range` ne sont **pas des contraintes** mais des règles d'**inférence**. Si `ssi:coversSpace` a pour domaine `ssi:Detector`, alors tout sujet de `coversSpace` *devient* un `Detector` ; on n'obtient jamais d'erreur.
- **OWL 2** (logiques de description, *SROIQ*) : `owl:SymmetricProperty` (pour `isConnectedTo`), `owl:oneOf` (pour `Status` = {Normal, Dangerous}), `owl:equivalentClass`.
- **Hypothèse du monde ouvert (OWA)** : en OWL, l'absence d'un fait ne signifie pas qu'il est faux, et il n'y a pas d'hypothèse de noms uniques. On ne peut donc pas *vérifier* « chaque espace a un détecteur » en OWL. C'est pour ça qu'on utilise **SHACL**.

### 2.2 SHACL (W3C, 2017) : validation en monde fermé
- Une **forme** (`sh:NodeShape`) cible des nœuds (`sh:targetClass`) et impose des contraintes (`sh:minCount`, `sh:maxCount`, `sh:class`, `sh:datatype`, `sh:minExclusive`…) ou une requête SPARQL (`sh:sparql`) qui renvoie les nœuds fautifs.
- Le résultat est un rapport `sh:ValidationReport` (`sh:conforms`, plus la liste des `sh:ValidationResult`).
- Points critiques dans les 8 formes du kit :
  - **F1** passe par `[sh:inversePath bot:hasSpace]` : il faut écrire `?niveau bot:hasSpace ?espace` directement, et exactement un niveau par espace.
  - **F3** utilise `rdfs:subClassOf* ssi:Detector` : le graphe validé doit contenir la hiérarchie de classes, d'où `-e ontologie -i rdfs`.
  - **F4/F5** lisent le nœud **unique** `ssi:Parameters` : il faut l'instancier à partir de `parametres.json` (« paramètres personnels »).
  - **F7** : `from` ≠ `to`, distance strictement positive, un seul `from` et un seul `to`.
  - **F8** : une route ne doit ni **traverser** ni **partir** d'un espace `Dangerous` (`passesThrough` ∪ `routeFor`).
- **Formes cachées** : le jury en appliquera d'autres. On peut s'y préparer en écrivant ses propres formes « de bon sens » (un seul état par espace, distances dans les deux sens pour chaque `isConnectedTo`, observations bien typées, pas de porte reliant deux espaces de niveaux différents…).

### 2.3 SPARQL 1.1
Algèbre : motifs de triplets (BGP), `OPTIONAL`, `FILTER`, `UNION`, agrégats (`SUM`, `COUNT`), **chemins de propriétés** (`rdfs:subClassOf*`, `ssi:isConnectedTo+`) et `SPARQL UPDATE` (`INSERT`/`DELETE`) pour la mise à jour dynamique du graphe en M5.

### 2.4 Les ontologies de référence
| Ontologie | Rôle | Concepts clés à réutiliser |
|---|---|---|
| **BOT** (Building Topology Ontology, W3C LBD CG, Rasmussen et al. 2017/2020) | Topologie du bâtiment | `bot:Building`, `bot:Storey`, `bot:Space`, `bot:Element`, `bot:Zone`, `bot:hasStorey`, `bot:hasSpace`, `bot:adjacentElement`, `bot:containsElement`, `bot:interfaceOf` |
| **SOSA/SSN** (W3C/OGC, 2017) | Capteurs et observations | `sosa:Sensor`, `sosa:Observation`, `sosa:madeObservation`, `sosa:observedProperty`, `sosa:hasFeatureOfInterest`, `sosa:hasSimpleResult`, `sosa:resultTime`, `sosa:ObservableProperty` |
| **SAREF** (ETSI TS 103 264) et **SAREF4BLDG** | Objets connectés, extension bâtiment calquée sur IFC | `saref:Device`, `saref:Property`, `saref:Measurement`, `saref:Function` ; s4bldg reprend les classes IFC (`s4bldg:Door`…) |
| **FE ontology** de Pang (2024) | Évacuation incendie | Building–Storey–Space, `isConnectedTo`, `EvacuationDistance(from, to, hasDistance)`, `Status`, `hasPeopleValue`, `Device` (4 sous-classes), `Observation(hasResult, resultTime)` |

### 2.5 Patrons de modélisation utiles
- **Relation n-aire réifiée** (W3C Note *Defining N-ary Relations*) : `ssi:EvacuationDistance` est un nœud qui porte `from`, `to`, `hasDistance` et `connectionType`. On ne peut pas mettre une distance sur un simple triplet `isConnectedTo`.
- **Patron d'observation SOSA** : `capteur sosa:madeObservation obs` ; `obs sosa:observedProperty ssi:Temperature ; sosa:hasFeatureOfInterest espace ; sosa:hasSimpleResult 63.2 ; sosa:resultTime "…"^^xsd:dateTime`.
- **Données temporelles** : l'état d'un espace change au cours du temps (voir Choix 5).

### 2.6 Comparaison attendue avec l'ontologie de Pang (à développer dans le rapport)
| Aspect | Pang (FE ontology) | Notre modèle |
|---|---|---|
| Espace de noms | Ad hoc (`fe:`), rien d'aligné | Socle `ssi:` aligné sur BOT, SOSA et SAREF |
| Topologie | `hasStorey`/`hasSpace` maison | `bot:hasStorey`/`bot:hasSpace` |
| Observations | « inspirées de SOSA », `hasResult` | SOSA natif (`hasSimpleResult`, `resultTime`, `observedProperty`) |
| Personnes | `hasPeopleValue` sur l'espace | `ssi:peopleCount`, et/ou observation `ssi:Occupancy` |
| Danger | Statut + distance portée à 1 000 m | Statut + **contrainte dure F8** (pas de falsification de la distance) |
| Validation | Aucune | SHACL F1–F8 et formes maison |
| Équipements SSI | Capteurs génériques | Détecteurs, déclencheurs, caméras, zones de détection (EN 54) |
| Correspondance IFC | Tableau 1 (IfcAlarm → SmokeSensor…) | `ssi:ifcGlobalId` sur chaque entité |

## 3. Choix techniques et d'architecture

### Choix 1 – Manière d'étendre et d'aligner l'ontologie
Options : `rdfs:subClassOf` (alignement faible), `owl:equivalentClass` (fort), ou correspondances SKOS (`skos:closeMatch`).
**Aspects** : le socle ne doit **pas être renommé ni contredit** ; l'équivalence est un engagement fort, avec des inférences dans les deux sens et un risque d'incohérence ; préférer la subsomption, sauf correspondance exacte. Garder `ontology.ttl` (TBox) séparé de `kg.ttl` (ABox).

### Choix 2 – Schéma des IRI des instances
Options : IRI fondées sur le GlobalId (`…/duplex/space/0BTBFw6f90Nfh9rP1dlXr$`), sur le nom (`A102`) ou sur un UUID.
**Aspects** : **stabilité** d'une exécution à l'autre (reproductibilité, comparaison par le jury), unicité (les noms ne sont pas uniques : il y a deux `B202` !), caractères spéciaux (`$` et `_` dans les GlobalId : valides dans une IRI complète, mais pas dans un nom préfixé Turtle → laisser rdflib sérialiser ou encoder en pourcentage).

### Choix 3 – Bibliothèques et triplestore
| Option | Pour | Contre |
|---|---|---|
| **rdflib + pySHACL** | Pur Python, SPARQL 1.1, pySHACL est la référence du kit | Lent sur de gros graphes (sans importance ici : quelques dizaines de milliers de triplets) |
| pyoxigraph | Très rapide (Rust), SPARQL complet | Pas de SHACL, donc pySHACL en plus |
| Apache Jena / Fuseki | Serveur, raisonneurs, SHACL | Java, plus lourd à installer et démontrer |
| owlready2 | Raisonnement OWL (HermiT) | Peu adapté à SHACL et SOSA |

**Aspects** : support de SHACL avec SPARQL, simplicité d'installation pour l'entretien, besoins de raisonnement, volume de données.

### Choix 4 – Raisonnement : matérialiser ou non
Options : aucun raisonnement, RDFS (`-i rdfs`), OWL-RL (`owlrl`), ou **matérialisation explicite** à la génération (écrire les deux sens de `isConnectedTo` et le type le plus spécifique).
**Aspects** : les requêtes SPARQL de l'agent ne voient pas les inférences si le graphe n'est pas matérialisé ; la propriété symétrique doit être écrite dans les deux sens ; inférer via `domain`/`range` peut ajouter des types inattendus et casser des formes cachées.

### Choix 5 – Représentation du temps et de l'état dynamique
| Option | Pour | Contre |
|---|---|---|
| Instantané : un seul `hasStatus` courant + `statusTime`, réécrit à chaque pas | Simple, formes faciles à satisfaire | Historique perdu dans le graphe |
| Un graphe nommé par pas de temps (`kg_t200`) | Historique complet, requêtes « à t = 300 s » | Plus complexe, formes à appliquer par graphe |
| Observations SOSA complètes et état *dérivé* par requête | Fidèle à SOSA, rien de recalculé à la main | Requêtes plus lourdes (Q15–Q19) |

**Aspects** : les questions Q15–Q19 portent sur des instants précis ; F8 s'applique aux routes ; un `kg.ttl` final doit être conforme ; la démarche de Pang consiste à **mettre à jour** le graphe. Compromis raisonnable : toutes les observations en SOSA, un état courant dans `kg.ttl` final, et des instantanés (ou une requête par `resultTime`) pour répondre à t donné.

### Choix 6 – Volume des observations
4 087 observations × ~6 triplets ≈ 25 000 triplets, sans problème. **Aspect** : tout garder permet de répondre à Q15 par SPARQL (`MIN(?t)` où obscurcissement > 0,0328).

### Choix 7 – Génération : depuis l'IFC ou depuis `geometry.json`
Générer le graphe à partir de `geometry.json` (sortie M1) découple les modules et rend les tests unitaires simples. L'énoncé dit « automatiquement depuis l'IFC » : la chaîne IFC → M1 → M2 reste automatique.
**Aspects** : source unique de vérité, cohérence entre `geometry.json` et `kg.ttl` (le jury recoupe les deux).

### Choix 8 – Formes SHACL supplémentaires
Écrire ses propres formes (fichier `formes_maison.ttl`) pour anticiper les formes cachées et prouver la qualité du graphe.
**Aspects** : montrer qu'on a compris l'esprit (EN 54, NF S 61-93x), sans rendre le graphe inutilement rigide.

## 4. À maîtriser pour l'entretien
- Expliquer pourquoi SHACL et pas OWL pour vérifier (monde ouvert / monde fermé), et pourquoi `domain`/`range` ne sont pas des contraintes.
- Justifier au tableau **un choix de modélisation** : typiquement, la réification d'`EvacuationDistance` (relation n-aire orientée), ou le patron d'observation SOSA plutôt que `hasPeopleValue` directement sur l'espace.
- Écrire de mémoire une requête SPARQL du type Q01 ou Q05 (filtre sur niveau, `SUM` sur une propriété).
