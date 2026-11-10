"""Requêtes SPARQL des questions statiques Q01–Q14 (gabarits réutilisés par l'agent M6).

Chaque question = une requête SPARQL sur kg.ttl qui renvoie des GlobalId (ensemble)
ou un nombre (valeur). Q07 et Q08 demandent un plus court chemin : le graphe pondéré
est extrait par SPARQL (distances d'évacuation), puis Dijkstra est appliqué en Python
(SPARQL 1.1 ne sait pas calculer de plus court chemin pondéré).

Les noms (« Level 2 », « A101 », préfixe « A »…) sont des paramètres des gabarits,
jamais des constantes : la même requête sert sur un autre IFC.
"""

from __future__ import annotations

import networkx as nx
from rdflib import Graph

PREFIXES = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
PREFIX bot: <https://w3id.org/bot#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
"""

GABARITS = {
    "Q01": """SELECT ?gid WHERE {{ ?n rdfs:label "{niveau}" ; bot:hasSpace ?s . ?s ssi:ifcGlobalId ?gid }}""",
    "Q02": """SELECT ?gid WHERE {{ ?p a ssi:Exit ; ssi:ifcGlobalId ?gid }}""",
    "Q03": """SELECT DISTINCT ?gid WHERE {{ ?p a ssi:Exit ; ssi:connects ?s . ?s ssi:ifcGlobalId ?gid }}""",
    "Q04": """SELECT DISTINCT ?gid WHERE {{
        ?a rdfs:label "{espace}" .
        ?d a ssi:EvacuationDistance ; ssi:from ?a ; ssi:to ?b ; ssi:connectionType "ouverture" .
        ?b ssi:ifcGlobalId ?gid }}""",
    "Q05": """SELECT (SUM(?surf) AS ?total) WHERE {{
        ?s a bot:Space ; rdfs:label ?nom ; ssi:area ?surf . FILTER STRSTARTS(?nom, "{prefixe}") }}""",
    "Q06": """SELECT ?gid WHERE {{
        ?n rdfs:label "{niveau}" ; bot:hasSpace ?s . ?s ssi:ifcGlobalId ?gid .
        {{ SELECT ?s (COUNT(DISTINCT ?p) AS ?nb) WHERE {{ ?p a ssi:Door ; ssi:connects ?s }} GROUP BY ?s }}
        FILTER (?nb = 1) }}""",
    "Q09": """SELECT DISTINCT ?gid WHERE {{ ?s bot:containsElement ?e . ?e a ssi:Stair . ?s ssi:ifcGlobalId ?gid }}""",
    "Q10": """SELECT (SUM(?surf) AS ?total) WHERE {{ ?n rdfs:label "{niveau}" ; bot:hasSpace ?s . ?s ssi:area ?surf }}""",
    "Q11": """SELECT ?gid WHERE {{
        ?s ssi:inDwelling ?z ; ssi:area ?surf ; ssi:ifcGlobalId ?gid .
        {{ SELECT ?z (MAX(?a) AS ?max) WHERE {{ ?x ssi:inDwelling ?z ; ssi:area ?a }} GROUP BY ?z }}
        FILTER (?surf = ?max) }}""",
    "Q12": """SELECT ?gid WHERE {{
        ?n rdfs:label "{niveau}" ; bot:hasSpace ?s . ?s ssi:longName ?nl ; ssi:ifcGlobalId ?gid .
        FILTER REGEX(?nl, "{motif}", "i") }}""",
    "Q13": """SELECT DISTINCT ?gid WHERE {{
        ?a ssi:inDwelling ?za . ?b ssi:inDwelling ?zb . ?za rdfs:label "{logement_a}" . ?zb rdfs:label "{logement_b}" .
        ?d a ssi:EvacuationDistance ; ssi:from ?a ; ssi:to ?b .
        OPTIONAL {{ ?d ssi:viaElement ?e . ?e ssi:ifcGlobalId ?eg }}
        BIND (COALESCE(?eg, CONCAT("ouverture:", STR(?a), "|", STR(?b))) AS ?gid) }}""",
    "Q14": """SELECT ?gid WHERE {{ ?p a ssi:Door ; ssi:doorWidth ?l ; ssi:ifcGlobalId ?gid . FILTER (?l < {seuil}) }}""",
    # --- scénario dynamique (graphe après M5) ---
    "Q15": """SELECT (MIN(?t) AS ?t0) WHERE {{
        ?o sosa:observedProperty ssi:SmokeObscuration ; sosa:hasSimpleResult ?v ; ssi:scenarioTime ?t .
        FILTER (?v > {seuil}) }}""",
    "Q16": """SELECT ?gid WHERE {{ ?s ssi:dangerSince ?t0 ; ssi:ifcGlobalId ?gid . FILTER (?t0 <= {t}) }}""",
    "Q16_observations": """SELECT DISTINCT ?gid WHERE {{
        ?o sosa:hasFeatureOfInterest ?s ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v ; ssi:scenarioTime ?t .
        FILTER (?t <= {t} && ((?p = ssi:Temperature && ?v > {temp}) || (?p = ssi:COConcentration && ?v > {co})))
        ?s ssi:ifcGlobalId ?gid }}""",
    "Q19": """SELECT ?gid WHERE {{
        ?o sosa:hasFeatureOfInterest ?s ; sosa:observedProperty ssi:Occupancy ; sosa:hasSimpleResult ?n ; ssi:scenarioTime ?t .
        {{ SELECT ?s (MAX(?t2) AS ?dernier) WHERE {{
             ?o2 sosa:hasFeatureOfInterest ?s ; sosa:observedProperty ssi:Occupancy ; ssi:scenarioTime ?t2 . FILTER (?t2 <= {t}) }}
           GROUP BY ?s }}
        FILTER (?t = ?dernier && ?n > 0)
        ?s ssi:ifcGlobalId ?gid }}""",
}

# Valeurs des paramètres pour les questions du kit (tirées de leur énoncé).
PARAMETRES_KIT = {
    "Q01": {"niveau": "Level 2"}, "Q04": {"espace": "A101"}, "Q05": {"prefixe": "A"},
    "Q06": {"niveau": "Level 2"}, "Q10": {"niveau": "Level 2"},
    "Q12": {"niveau": "Level 2", "motif": "bath|salle de bain|sdb|toilet|wc"},
    "Q13": {"logement_a": "Logement A", "logement_b": "Logement B"}, "Q14": {"seuil": 0.80},
    "Q15": {"seuil": 0.0328}, "Q16": {"t": 300}, "Q16_observations": {"t": 300, "temp": 60, "co": 1000},
    "Q19": {"t": 300},
}

ARETES = """SELECT ?a ?b ?d ?type ?via ?larg WHERE {
    ?x a ssi:EvacuationDistance ; ssi:from ?sa ; ssi:to ?sb ; ssi:hasDistance ?d ; ssi:connectionType ?type .
    ?sa ssi:ifcGlobalId ?a . ?sb ssi:ifcGlobalId ?b .
    OPTIONAL { ?x ssi:viaElement ?e . ?e ssi:ifcGlobalId ?via . OPTIONAL { ?e ssi:doorWidth ?larg } } }"""
SORTIES = """SELECT ?a ?p ?d ?larg WHERE {
    ?x a ssi:ExitDistance ; ssi:exitFrom ?s ; ssi:exitVia ?e ; ssi:exitDistance ?d .
    ?s ssi:ifcGlobalId ?a . ?e ssi:ifcGlobalId ?p ; ssi:doorWidth ?larg }"""
ESPACE_PAR_NOM = """SELECT ?gid WHERE {{ ?s rdfs:label "{nom}" ; ssi:ifcGlobalId ?gid . {filtre} }}"""
# ifcGlobalId est typé xsd:string : comparer par STR() (rdflib distingue "x" et "x"^^xsd:string)
SORTIE_DE = """SELECT ?p WHERE {{ ?e a ssi:Exit ; ssi:connects ?s ; ssi:ifcGlobalId ?p . ?s ssi:ifcGlobalId ?g .
    FILTER (STR(?g) = "{espace}") }}"""


def requete(cle_ou_texte: str, **params) -> str:
    corps = GABARITS.get(cle_ou_texte, cle_ou_texte)
    return PREFIXES + corps.format(**params)


def executer(g: Graph, texte: str) -> list:
    return [tuple(v.toPython() if v is not None else None for v in ligne) for ligne in g.query(texte)]


def repondre(g: Graph, qid: str, **params) -> tuple[list[str] | float, list[str]]:
    """Réponse + requêtes SPARQL exécutées (pour answers.jsonl)."""
    params = {**PARAMETRES_KIT.get(qid, {}), **params}
    texte = requete(qid, **params)
    lignes = executer(g, texte)
    if qid in ("Q05", "Q10"):
        return round(float(lignes[0][0] or 0), 2), [texte]
    if qid == "Q15":
        return (int(lignes[0][0]) if lignes and lignes[0][0] is not None else None), [texte]
    return sorted({str(l[0]) for l in lignes}), [texte]


# Plus courts chemins (Q07, Q08) ---------------------------------------------------
def graphe_pondere(g: Graph) -> tuple[nx.DiGraph, list[str]]:
    textes = [PREFIXES + ARETES, PREFIXES + SORTIES]
    G = nx.DiGraph()
    for a, b, d, type_, via, larg in executer(g, textes[0]):
        if not G.has_edge(a, b) or G[a][b]["weight"] > float(d):
            G.add_edge(a, b, weight=float(d), type=type_, via=via, largeur=float(larg) if larg else None)
    for a, p, d, larg in executer(g, textes[1]):
        G.add_edge(a, f"sortie:{p}", weight=float(d), type="sortie", via=p, largeur=float(larg))
    return G, textes


def espace(g: Graph, nom: str, nom_long: str | None = None) -> tuple[str, str]:
    filtre = f'?s ssi:longName "{nom_long}" .' if nom_long else ""
    texte = PREFIXES + ESPACE_PAR_NOM.format(nom=nom, filtre=filtre)
    gids = [l[0] for l in executer(g, texte)]
    if len(gids) != 1:
        raise ValueError(f"{nom} / {nom_long} désigne {len(gids)} espaces : préciser le nom long")
    return str(gids[0]), texte


def chemin(g: Graph, depart: str, espace_sortie: str) -> dict:
    """Itinéraire le plus court de `depart` à la sortie de `espace_sortie` (GlobalId)."""
    G, textes = graphe_pondere(g)
    texte_sortie = PREFIXES + SORTIE_DE.format(espace=espace_sortie)
    sorties = [f"sortie:{l[0]}" for l in executer(g, texte_sortie)]
    longueur, noeuds = min(nx.single_source_dijkstra(G, depart, s, weight="weight") for s in sorties)
    aretes = [G[u][v] for u, v in zip(noeuds, noeuds[1:])]
    largeurs = [a["largeur"] for a in aretes if a["type"] in ("porte", "sortie") and a["largeur"]]
    return {"espaces": [n for n in noeuds if not n.startswith("sortie:")], "distance_m": round(longueur, 3),
            "largeur_min_porte_m": min(largeurs) if largeurs else None, "requetes": textes + [texte_sortie]}
