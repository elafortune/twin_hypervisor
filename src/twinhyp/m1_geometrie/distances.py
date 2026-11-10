"""Étape 3 – distances d'évacuation orientées ([Pang] §4.1.3, fig. 4).

Pour une liaison A -> B, la distance est mesurée DANS l'espace de départ A, depuis
son point le plus défavorable jusqu'au passage vers B (porte, milieu de l'ouverture,
pied ou tête de la volée), en contournant les murs ; pour un escalier on ajoute la
longueur de la volée. Les distances sont donc orientées : d(A -> B) != d(B -> A).

Méthode : graphe de visibilité (sommets du contour + cible, arêtes = segments
contenus dans le polygone) puis Dijkstra depuis la cible. Le point géodésiquement le
plus éloigné d'une source dans un polygone est atteint en un sommet (Suri, 1989),
d'où le max sur les sommets. La formule de Pang (un seul sommet intermédiaire) est
calculée à côté pour comparaison : elle coïncide sur un espace convexe.
"""

from __future__ import annotations

import math

import networkx as nx
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import linemerge

from twinhyp.m1_geometrie.anomalies import anomalie
from twinhyp.m1_geometrie.connectivite import TOL_CONTACT_M

MARGE_M = 0.01      # tolérance numérique : un segment qui longe un mur reste « dans » l'espace
CIBLE = "cible"


# Géométrie élémentaire -----------------------------------------------------------
def cible_dans(poly: Polygon, xy) -> Point:
    """Le passage est dans l'épaisseur du mur : on le ramène sur le contour de l'espace."""
    p = Point(xy[0], xy[1])
    if poly.covers(p):
        return p
    return poly.exterior.interpolate(poly.exterior.project(p))


def sommets(poly: Polygon) -> list[tuple[float, float]]:
    pts = list(poly.exterior.coords)[:-1]
    for trou in poly.interiors:
        pts += list(trou.coords)[:-1]
    return [(float(x), float(y)) for x, y in pts]


def graphe_visibilite(poly: Polygon, cible: Point) -> tuple[nx.Graph, list[tuple[float, float]]]:
    zone = poly.buffer(MARGE_M)
    pts = sommets(poly)
    noeuds = {i: p for i, p in enumerate(pts)} | {CIBLE: (cible.x, cible.y)}
    G = nx.Graph()
    G.add_nodes_from(noeuds)
    cles = list(noeuds)
    for i, a in enumerate(cles):
        for b in cles[i + 1:]:
            pa, pb = noeuds[a], noeuds[b]
            if pa == pb or zone.covers(LineString([pa, pb])):
                G.add_edge(a, b, weight=math.dist(pa, pb))
    return G, pts


def distance_pang(G: nx.Graph, pts) -> float | None:
    """L = max_i(L_Di, L_Ci), L_Ci = min_j(L_Pij + L_Dj) : un seul sommet intermédiaire."""
    L_D = {i: G[i][CIBLE]["weight"] for i in range(len(pts)) if G.has_edge(i, CIBLE)}
    pire = 0.0
    for i in range(len(pts)):
        if i in L_D:
            pire = max(pire, L_D[i])
            continue
        candidats = [G[i][j]["weight"] + L_D[j] for j in G[i] if j in L_D]
        if not candidats:
            return None  # deux sommets intermédiaires au moins : la formule ne s'applique pas
        pire = max(pire, min(candidats))
    return pire


def distance_defavorable(poly: Polygon, cible: Point) -> dict | None:
    G, pts = graphe_visibilite(poly, cible)
    dist, chemins = nx.single_source_dijkstra(G, CIBLE, weight="weight")
    if any(i not in dist for i in range(len(pts))):
        return None
    pire = max(range(len(pts)), key=lambda i: dist[i])
    chemin = [pts[k] if k != CIBLE else (cible.x, cible.y) for k in reversed(chemins[pire])]
    pang = distance_pang(G, pts)
    return {"distance_plan_m": dist[pire], "distance_pang_m": pang,
            "point_defavorable_xy": list(pts[pire]), "cible_xy": [cible.x, cible.y],
            "chemin_xy": [list(p) for p in chemin]}


def milieu_contact(poly_de: Polygon, poly_vers: Polygon) -> Point | None:
    contact = poly_de.boundary.intersection(poly_vers.buffer(TOL_CONTACT_M))
    if contact.is_empty:
        return None
    if isinstance(contact, MultiLineString):
        contact = linemerge(contact)
    morceaux = list(contact.geoms) if hasattr(contact, "geoms") else [contact]
    lignes = [m for m in morceaux if isinstance(m, LineString)]
    if not lignes:
        return None
    return max(lignes, key=lambda l: l.length).interpolate(0.5, normalized=True)


# Calcul sur le jumeau ---------------------------------------------------------------
def _arrondi(r: dict) -> dict:
    return {k: (round(v, 3) if isinstance(v, float) else
                [round(x, 3) for x in v] if k.endswith("_xy") and v and not isinstance(v[0], list) else
                [[round(x, 3) for x in p] for p in v] if k == "chemin_xy" else v)
            for k, v in r.items()}


def _cibles(l: dict, poly: dict, position_porte: dict):
    """(départ, arrivée, cible, longueur ajoutée) pour les deux sens d'une liaison."""
    a, b = l["de"], l["vers"]
    for de, vers in ((a, b), (b, a)):
        if l["type"] == "porte":
            xy = position_porte.get(l.get("element_globalId"))
            yield de, vers, (cible_dans(poly[de], xy) if xy else None), 0.0
        elif l["type"] == "ouverture":
            yield de, vers, milieu_contact(poly[de], poly[vers]), 0.0
        else:  # escalier : la cage (de) monte par le pied, l'arrivée (vers) descend par la tête
            xy = l.get("pied_xy") if de == a else l.get("tete_xy")
            yield de, vers, (cible_dans(poly[de], xy) if xy else None), float(l.get("longueur_volee_m") or 0.0)


def calculer(geometrie: dict) -> list[dict]:
    """Ajoute `distances` (liaisons orientées) et `distances_sortie` ; renvoie les anomalies."""
    espaces = {e["globalId"]: e for e in geometrie["espaces"]}
    poly = {g: Polygon(e["polygone_xy"]) for g, e in espaces.items()}
    position_porte = {p["globalId"]: p["position_xyz"][:2] for p in geometrie["portes"] if p.get("position_xyz")}
    distances, anomalies = [], []

    def mesurer(de, cible, ajout, base):
        if cible is None:
            anomalies.append(anomalie(de, f"{espaces[de]['nom']} : point de passage introuvable pour {base}.",
                                      "Distance non calculée.", "distance_calculable"))
            return None
        r = distance_defavorable(poly[de], cible)
        if r is None:
            anomalies.append(anomalie(de, f"{espaces[de]['nom']} : contour non connexe pour le graphe de visibilité.",
                                      "Distance non calculée.", "distance_calculable"))
            return None
        r["distance_m"] = r["distance_plan_m"] + ajout
        return r

    for l in geometrie.get("liaisons", []):
        for de, vers, cible, ajout in _cibles(l, poly, position_porte):
            r = mesurer(de, cible, ajout, f"la liaison {l['type']} vers {espaces[vers]['nom']}")
            if r:
                distances.append(_arrondi({"de": de, "vers": vers, "type": l["type"],
                                           "element_globalId": l.get("element_globalId"), **r,
                                           **({"longueur_volee_m": ajout} if ajout else {}),
                                           "methode": "visibilite_dijkstra"}))

    sorties = []
    for p in geometrie["portes"]:
        if p["sortie"] and p["espaces"] and p.get("position_xyz"):
            de = p["espaces"][0]
            r = mesurer(de, cible_dans(poly[de], p["position_xyz"][:2]), 0.0, f"la sortie {p['globalId']}")
            if r:
                sorties.append(_arrondi({"de": de, "porte_globalId": p["globalId"], **r,
                                         "methode": "visibilite_dijkstra"}))

    geometrie["distances"] = sorted(distances, key=lambda d: (d["de"], d["vers"], d["type"]))
    geometrie["distances_sortie"] = sorted(sorties, key=lambda d: (d["de"], d["porte_globalId"]))
    return anomalies


# Itinéraires (réutilisés par M5 / M6) --------------------------------------------------
SORTIE = "EXTERIEUR"


def graphe_oriente(geometrie: dict) -> nx.DiGraph:
    """Espaces + EXTERIEUR ; arc A -> B pondéré par d(A -> B)."""
    G = nx.DiGraph()
    G.add_nodes_from(e["globalId"] for e in geometrie["espaces"])
    G.add_node(SORTIE)
    for d in geometrie.get("distances", []):
        if not G.has_edge(d["de"], d["vers"]) or G[d["de"]][d["vers"]]["weight"] > d["distance_m"]:
            G.add_edge(d["de"], d["vers"], weight=d["distance_m"], type=d["type"], element=d["element_globalId"])
    for d in geometrie.get("distances_sortie", []):
        noeud = f"{SORTIE}:{d['porte_globalId']}"
        G.add_edge(d["de"], noeud, weight=d["distance_m"], type="sortie", element=d["porte_globalId"])
        G.add_edge(noeud, SORTIE, weight=0.0, type="sortie", element=d["porte_globalId"])
    return G


def itineraire(geometrie: dict, depart: str, porte_sortie: str | None = None) -> dict:
    """Plus court itinéraire (somme des distances orientées) vers une sortie donnée ou la plus proche."""
    G = graphe_oriente(geometrie)
    but = f"{SORTIE}:{porte_sortie}" if porte_sortie else SORTIE
    longueur, noeuds = nx.single_source_dijkstra(G, depart, but, weight="weight")
    largeur = {p["globalId"]: p["largeur_m"] for p in geometrie["portes"]}
    arcs = [G[u][v] for u, v in zip(noeuds, noeuds[1:])]
    portes = list(dict.fromkeys(a["element"] for a in arcs if a["type"] in ("porte", "sortie")))
    espaces = [n for n in noeuds if not n.startswith(SORTIE)]
    return {"espaces": espaces, "portes": portes, "distance_m": round(longueur, 3),
            "largeur_min_porte_m": min((largeur[p] for p in portes if largeur.get(p)), default=None)}
