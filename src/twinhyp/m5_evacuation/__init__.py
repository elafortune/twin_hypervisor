"""M5 – Évacuation dynamique : kg.ttl + observations.csv -> evacuation_dynamique.jsonl (+ kg.ttl mis à jour).

Algorithme 1 de [Pang] : à chaque pas de temps,
  1. les observations du pas sont insérées dans le graphe (patron SOSA) ;
  2. l'état des espaces est mis à jour par SPARQL UPDATE (Dangerous si T > seuil ou CO > seuil,
     état VERROUILLÉ ensuite) ; le nombre de personnes vient des caméras ;
  3. pour chaque espace occupé, deux stratégies :
     - stratégie 1 : route vers la sortie la plus proche sur le graphe STATIQUE (plan d'évacuation) ;
     - stratégie 2 : Dijkstra sur le graphe privé des espaces dangereux (contrainte dure F8) ;
       aucune route -> route = null et action de repli.
     La route que donnerait la pénalité de 1 000 m de Pang est jointe pour comparaison.

Le graphe de routage (distances orientées de M1) est extrait de kg.ttl par SPARQL.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import networkx as nx
from rdflib import RDF, XSD, Graph, Literal, Namespace

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_jsonl
from twinhyp.m2_graphe import requetes as R
from twinhyp.m2_graphe.construction import BOT, SSI, iri

SOSA = Namespace("http://www.w3.org/ns/sosa/")
EXTERIEUR = "EXTERIEUR"

# Seuils de l'énoncé (d'après Pang) ; surchargeables par parametres.json sans toucher au code.
SEUILS_PAR_DEFAUT = {
    "seuil_alarme_obscurcissement_par_m": 0.0328,
    "seuil_danger_temperature_degC": 60.0,
    "seuil_danger_co_ppm": 1000.0,
    "penalite_pang_m": 1000.0,
}

PROPRIETE = {"SmokeAlarm": SSI.SmokeObscuration, "TemperatureSensor": SSI.Temperature,
             "COSensor": SSI.COConcentration, "Camera": SSI.Occupancy}


def seuils(params: dict) -> dict:
    return {k: float(params.get(k, v)) for k, v in SEUILS_PAR_DEFAUT.items()}


def lire_observations(chemin: Path) -> dict[int, list[dict]]:
    par_t = defaultdict(list)
    with open(chemin, encoding="utf-8", newline="") as f:
        for ligne in csv.DictReader(f):
            ligne["t_s"], ligne["valeur"] = int(ligne["t_s"]), float(ligne["valeur"])
            par_t[ligne["t_s"]].append(ligne)
    return dict(sorted(par_t.items()))


# 1. Insertion SOSA ------------------------------------------------------------------
def inserer(g: Graph, observations: list[dict]) -> None:
    g.bind("sosa", SOSA)
    for o in observations:
        if o["type"] not in PROPRIETE:
            continue
        capteur = iri("sensor", o["capteur"])
        obs = iri("observation", f"{o['capteur']}_{o['t_s']:04d}")
        g.add((capteur, RDF.type, SOSA.Sensor))
        g.add((capteur, SOSA.observes, PROPRIETE[o["type"]]))
        g.add((capteur, SOSA.madeObservation, obs))
        g.add((obs, RDF.type, SOSA.Observation))
        g.add((obs, SOSA.observedProperty, PROPRIETE[o["type"]]))
        g.add((obs, SOSA.hasFeatureOfInterest, iri("space", o["espace_globalId"])))
        g.add((obs, SOSA.hasSimpleResult, Literal(o["valeur"], datatype=XSD.double)))
        g.add((obs, SOSA.resultTime, Literal(o["horodatage"], datatype=XSD.dateTime)))
        g.add((obs, SSI.scenarioTime, Literal(o["t_s"], datatype=XSD.integer)))


# 2. Mise à jour de l'état (SPARQL UPDATE) ----------------------------------------------
MAJ_DANGER = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
DELETE { ?s ssi:hasStatus ?ancien }
INSERT { ?s ssi:hasStatus ssi:Dangerous ; ssi:dangerSince %(t)d }
WHERE {
  ?o sosa:hasFeatureOfInterest ?s ; ssi:scenarioTime %(t)d ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
  FILTER ((?p = ssi:Temperature && ?v > %(temp)s) || (?p = ssi:COConcentration && ?v > %(co)s))
  ?s ssi:hasStatus ?ancien . FILTER (?ancien != ssi:Dangerous)
}"""

MAJ_PERSONNES = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
DELETE { ?s ssi:peopleCount ?ancien }
INSERT { ?s ssi:peopleCount ?n }
WHERE {
  ?o sosa:hasFeatureOfInterest ?s ; ssi:scenarioTime %(t)d ; sosa:observedProperty ssi:Occupancy ; sosa:hasSimpleResult ?v .
  BIND (xsd:integer(ROUND(?v)) AS ?n)  # rdflib ne convertit pas directement un double en entier
  OPTIONAL { ?s ssi:peopleCount ?ancien }
}"""

MAJ_HEURE = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
PREFIX bot: <https://w3id.org/bot#>
DELETE { ?s ssi:statusTime ?ancien }
INSERT { ?s ssi:statusTime "%(horodatage)s"^^<http://www.w3.org/2001/XMLSchema#dateTime> }
WHERE { ?s a bot:Space ; ssi:hasStatus ?etat . OPTIONAL { ?s ssi:statusTime ?ancien } }"""

DANGEREUX = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
SELECT ?gid WHERE { ?s ssi:hasStatus ssi:Dangerous ; ssi:ifcGlobalId ?gid }"""

OCCUPES = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
SELECT ?gid ?n WHERE { ?s ssi:peopleCount ?n ; ssi:ifcGlobalId ?gid . FILTER (?n > 0) }"""


def mettre_a_jour(g: Graph, t: int, horodatage: str, s: dict) -> None:
    g.update(MAJ_DANGER % {"t": t, "temp": s["seuil_danger_temperature_degC"], "co": s["seuil_danger_co_ppm"]})
    g.update(MAJ_PERSONNES % {"t": t})
    g.update(MAJ_HEURE % {"horodatage": horodatage})


def dangereux(g: Graph) -> set[str]:
    return {str(l[0]) for l in g.query(DANGEREUX)}


def occupes(g: Graph) -> dict[str, int]:
    return {str(gid): int(n) for gid, n in g.query(OCCUPES)}


# 3. Routage ---------------------------------------------------------------------------
def graphe_routage(g: Graph) -> nx.DiGraph:
    """Graphe orienté des distances (SPARQL) + super-puits EXTERIEUR relié aux sorties (poids 0)."""
    G, _ = R.graphe_pondere(g)
    for n in [n for n in G if n.startswith("sortie:")]:
        G.add_edge(n, EXTERIEUR, weight=0.0, type="sortie")
    return G


def _resultat(noeuds: list[str], longueur: float) -> dict:
    sortie = next((n.split(":", 1)[1] for n in noeuds if n.startswith("sortie:")), None)
    return {"route": [n for n in noeuds if n != EXTERIEUR and not n.startswith("sortie:")],
            "sortie_globalId": sortie, "distance_m": round(longueur, 3)}


def route_sure(G: nx.DiGraph, depart: str, interdits: set[str]) -> dict | None:
    """Contrainte dure : les espaces dangereux sont retirés du graphe (départ compris, cf. F8 routeFor)."""
    if depart in interdits:
        return None
    H = G.subgraph([n for n in G if n not in interdits])
    try:
        longueur, noeuds = nx.single_source_dijkstra(H, depart, EXTERIEUR, weight="weight")
    except nx.NetworkXNoPath:
        return None
    return _resultat(noeuds, longueur)


def route_penalite(G: nx.DiGraph, depart: str, interdits: set[str], penalite: float) -> dict | None:
    """Pang : on ajoute `penalite` à tout arc qui ENTRE dans un espace dangereux ; une route existe toujours."""
    def poids(u, v, d):
        return d["weight"] + (penalite if v in interdits else 0.0)
    try:
        longueur, noeuds = nx.single_source_dijkstra(G, depart, EXTERIEUR, weight=poids)
    except nx.NetworkXNoPath:
        return None
    r = _resultat(noeuds, longueur)
    r["espaces_dangereux_traverses"] = [n for n in r["route"] if n in interdits]
    return r


def action(strategie: int, route: dict | None, depart: str, interdits: set[str], alarme: bool) -> str:
    if not alarme:
        return "Pas d'alarme : aucune évacuation déclenchée."
    if strategie == 1:
        sur_route = [n for n in route["route"] if n in interdits] if route else []
        return ("Plan statique : la route traverse des espaces dangereux, à éviter."
                if sur_route else "Plan statique : suivre la route vers la sortie la plus proche.")
    if route is not None:
        return "Évacuer par la route sûre indiquée."
    if depart in interdits:
        return "Espace de départ dangereux : secours prioritaire, signaler la position et le nombre de personnes."
    return ("Aucune route sûre : rester confiné (porte fermée, calfeutrer), se signaler aux secours "
            "avec la position et le nombre de personnes.")


def rejouer(g: Graph, observations: dict[int, list[dict]], s: dict) -> list[dict]:
    G = graphe_routage(g)
    statique = {}  # stratégie 1 : calculée une fois, sans tenir compte du feu
    lignes, alarme = [], None
    for t, obs in observations.items():
        inserer(g, obs)
        mettre_a_jour(g, t, obs[0]["horodatage"], s)
        if alarme is None and any(o["type"] == "SmokeAlarm" and o["valeur"] > s["seuil_alarme_obscurcissement_par_m"]
                                  for o in obs):
            alarme = t
        danger, presents = dangereux(g), occupes(g)
        for espace in sorted(presents):
            if espace not in statique:
                statique[espace] = route_sure(G, espace, set())
            r1 = statique[espace]
            lignes.append({"t_s": t, "espace_globalId": espace, "strategie": 1,
                           "route": r1["route"] if r1 else None,
                           "sortie_globalId": r1["sortie_globalId"] if r1 else None,
                           "distance_m": r1["distance_m"] if r1 else None,
                           "espaces_dangereux": sorted(n for n in (r1["route"] if r1 else []) if n in danger),
                           "personnes": presents[espace],
                           "action_recommandee": action(1, r1, espace, danger, alarme is not None)})
            r2 = route_sure(G, espace, danger)
            lignes.append({"t_s": t, "espace_globalId": espace, "strategie": 2,
                           "route": r2["route"] if r2 else None,
                           "sortie_globalId": r2["sortie_globalId"] if r2 else None,
                           "distance_m": r2["distance_m"] if r2 else None,
                           "espaces_dangereux": sorted(danger),
                           "personnes": presents[espace],
                           "route_penalite_pang": route_penalite(G, espace, danger, s["penalite_pang_m"]),
                           "action_recommandee": action(2, r2, espace, danger, alarme is not None)})
    if alarme is not None:
        for b in g.subjects(RDF.type, BOT.Building):
            g.set((b, SSI.alarmTime, Literal(alarme, datatype=XSD.integer)))
    return lignes


def ecrire_routes(g: Graph, lignes: list[dict]) -> None:
    """Routes COURANTES (dernier pas) de la stratégie 2 : F8 s'applique à l'état final du graphe.
    L'historique des routes est dans evacuation_dynamique.jsonl."""
    if not lignes:
        return
    t_final = max(l["t_s"] for l in lignes)
    horodatage = next(g.objects(None, SSI.statusTime), None)
    for l in lignes:
        if l["t_s"] != t_final or l["strategie"] != 2 or l["route"] is None:
            continue
        r = iri("route", f"{l['espace_globalId']}_{t_final:04d}")
        g.add((r, RDF.type, SSI.EvacuationRoute))
        g.add((r, SSI.routeFor, iri("space", l["espace_globalId"])))
        for espace in l["route"][1:]:
            g.add((r, SSI.passesThrough, iri("space", espace)))
        g.add((r, SSI.routeTo, iri("door", l["sortie_globalId"])))
        if horodatage is not None:
            g.add((r, SSI.validAt, horodatage))


# Questions dynamiques (Q17, Q18) : état lu dans le graphe (ssi:dangerSince) + planificateur -----
DANGER_A = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
SELECT ?gid WHERE { ?s ssi:dangerSince ?t0 ; ssi:ifcGlobalId ?gid . FILTER (?t0 <= %(t)d) }"""
INSTANTS = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
SELECT DISTINCT ?t WHERE { ?o ssi:scenarioTime ?t } ORDER BY ?t"""
ALARME = """PREFIX ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#>
SELECT ?t WHERE { ?b ssi:alarmTime ?t }"""


def dangereux_a(g: Graph, t: int) -> tuple[set[str], str]:
    texte = DANGER_A % {"t": t}
    return {str(l[0]) for l in g.query(texte)}, texte


def route_a(g: Graph, depart: str, t: int) -> tuple[dict | None, list[str]]:
    """Route de la stratégie 2 à l'instant t (contrainte dure)."""
    danger, texte = dangereux_a(g, t)
    return route_sure(graphe_routage(g), depart, danger), [texte]


def instant_alarme(g: Graph) -> int | None:
    lignes = list(g.query(ALARME))
    return int(lignes[0][0]) if lignes else None


def plus_de_route_sure(g: Graph, depart: str) -> tuple[int | None, list[str]]:
    """Premier instant du scénario à partir duquel `depart` n'a plus de route sûre."""
    G = graphe_routage(g)
    for (t,) in g.query(INSTANTS):
        danger, texte = dangereux_a(g, int(t))
        if route_sure(G, depart, danger) is None:
            return int(t), [INSTANTS, texte]
    return None, [INSTANTS]


def executer(ctx: Contexte) -> list[str]:
    g = Graph().parse(ctx.chemin_sortie("kg"), format="turtle")
    lignes = rejouer(g, lire_observations(ctx.obs), seuils(ctx.params))
    ecrire_routes(g, lignes)
    ecrire_jsonl(ctx.chemin_sortie("evacuation"), lignes)
    g.serialize(ctx.chemin_sortie("kg"), format="turtle", encoding="utf-8")
    return ["evacuation", "kg"]
