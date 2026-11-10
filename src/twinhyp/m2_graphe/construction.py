"""Construction du graphe de connaissances statique à partir de geometry.json.

Patrons :
- topologie BOT : Site -> Building -> Storey (bot:hasStorey) -> Space (bot:hasSpace) ;
  portes adjacentes aux espaces (bot:adjacentElement), escalier contenu dans sa cage
  (bot:containsElement) ;
- connectivité : ssi:isConnectedTo écrit dans les DEUX sens (matérialisation de la
  symétrie OWL, pour que SPARQL sans raisonneur la voie) ;
- distances : relation n-aire réifiée ssi:EvacuationDistance (from, to, hasDistance,
  connectionType, viaElement), une par sens ;
- paramètres personnels : un seul nœud ssi:Parameters, valeurs lues dans parametres.json.

IRI des instances : <base>/<type>/<GlobalId> -> stables d'une exécution à l'autre et
uniques même quand deux espaces portent le même nom.
"""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote

import networkx as nx
from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

SSI = Namespace("https://ligm.univ-eiffel.fr/twinhypervisor/ssi#")
BOT = Namespace("https://w3id.org/bot#")
INST = Namespace("https://ligm.univ-eiffel.fr/twinhypervisor/kg/")

TYPE_CONNEXION = {"porte": "porte", "ouverture": "ouverture", "escalier": "escalier"}

# parametres.json -> propriété du nœud ssi:Parameters (les deux premières sont imposées par le socle)
PARAMETRES = {
    "declencheur_distance_max_m": SSI.maxCallPointDistance,
    "couverture_video_min": SSI.minCameraCoverage,
    "pas_grille_m": SSI.gridStep,
    "camera_champ_horizontal_deg": SSI.cameraHorizontalFov,
    "camera_champ_vertical_deg": SSI.cameraVerticalFov,
    "camera_portee_m": SSI.cameraRange,
    "camera_hauteur_pose_m": SSI.cameraMountHeight,
    "detecteur_rayon_m": SSI.detectorRadius,
}


def iri(genre: str, ident: str) -> URIRef:
    return INST[f"{genre}/{quote(ident, safe='')}"]


def dec(x: float, chiffres: int = 3) -> Literal:
    return Literal(Decimal(str(round(float(x), chiffres))), datatype=XSD.decimal)


def logements(geometrie: dict) -> list[list[str]]:
    """Logement = composante connexe du graphe des liaisons qui contient une sortie.
    Règle générique (aucun nom) ; recoupée avec le préfixe des noms dans les tests."""
    G = nx.Graph()
    G.add_nodes_from(e["globalId"] for e in geometrie["espaces"])
    G.add_edges_from((l["de"], l["vers"]) for l in geometrie["liaisons"])
    avec_sortie = {p["espaces"][0] for p in geometrie["portes"] if p["sortie"] and p["espaces"]}
    composantes = [sorted(c) for c in nx.connected_components(G) if c & avec_sortie]
    nom = {e["globalId"]: e["nom"] for e in geometrie["espaces"]}
    return sorted(composantes, key=lambda c: min(nom[g] for g in c))


def _prefixe_commun(noms: list[str]) -> str:
    p = noms[0]
    for n in noms[1:]:
        while not n.startswith(p):
            p = p[:-1]
    return p.rstrip("0123456789")


def construire(geometrie: dict, params: dict, nom_batiment: str = "batiment") -> Graph:
    g = Graph()
    g.bind("ssi", SSI)
    g.bind("bot", BOT)
    g.bind("inst", INST)

    espaces = {e["globalId"]: e for e in geometrie["espaces"]}
    # Niveau corrigé par M1 (anomalie rattachement_niveau) si présent
    niveau_corrige = {a["element_globalId"]: a["niveau_corrige_globalId"]
                      for a in geometrie["anomalies"] if a.get("niveau_corrige_globalId")}

    site, batiment = iri("site", nom_batiment), iri("building", nom_batiment)
    g.add((site, RDF.type, BOT.Site))
    g.add((batiment, RDF.type, BOT.Building))
    g.add((site, BOT.hasBuilding, batiment))
    g.add((batiment, RDFS.label, Literal(nom_batiment)))

    for n in geometrie["niveaux"]:
        s = iri("storey", n["globalId"])
        g.add((s, RDF.type, BOT.Storey))
        g.add((batiment, BOT.hasStorey, s))
        g.add((s, SSI.ifcGlobalId, Literal(n["globalId"], datatype=XSD.string)))
        g.add((s, RDFS.label, Literal(n["nom"])))
        g.add((s, SSI.elevation, dec(n["altitude_m"])))

    for gid, e in espaces.items():
        s = iri("space", gid)
        niveau = niveau_corrige.get(gid, e["niveau_globalId"])
        g.add((s, RDF.type, BOT.Space))
        g.add((iri("storey", niveau), BOT.hasSpace, s))
        g.add((s, SSI.ifcGlobalId, Literal(gid, datatype=XSD.string)))
        g.add((s, RDFS.label, Literal(e["nom"])))
        if e.get("nom_long"):
            g.add((s, SSI.longName, Literal(e["nom_long"])))
        g.add((s, SSI.area, dec(e["surface_m2"])))
        g.add((s, SSI.areaSource, Literal(e.get("surface_source", ""))))
        if e.get("surface_geometrique_m2") is not None:
            g.add((s, SSI.geometricArea, dec(e["surface_geometrique_m2"])))
        g.add((s, SSI.height, dec(e["hauteur_m"])))
        g.add((s, SSI.occupiable, Literal(bool(e["occupable"]))))
        g.add((s, SSI.hasStatus, SSI.Normal))  # état initial, mis à jour par M5

    for p in geometrie["portes"]:
        d = iri("door", p["globalId"])
        g.add((d, RDF.type, SSI.Exit if p["sortie"] else SSI.Door))
        g.add((d, SSI.ifcGlobalId, Literal(p["globalId"], datatype=XSD.string)))
        if p.get("nom"):
            g.add((d, RDFS.label, Literal(p["nom"])))
        g.add((d, SSI.doorWidth, dec(p["largeur_m"])))
        niveau = p.get("niveau_globalId")
        if niveau:
            g.add((d, SSI.onStorey, iri("storey", niveau)))
        for gs in p["espaces"]:
            g.add((d, SSI.connects, iri("space", gs)))
            g.add((iri("space", gs), BOT.adjacentElement, d))

    for st in geometrie.get("escaliers", []):
        s = iri("stair", st["globalId"])
        g.add((s, RDF.type, SSI.Stair))
        g.add((s, SSI.ifcGlobalId, Literal(st["globalId"], datatype=XSD.string)))
        if st.get("nom"):
            g.add((s, RDFS.label, Literal(st["nom"])))
        niveau = niveau_corrige.get(st["globalId"], st.get("niveau_globalId"))
        if niveau:
            g.add((s, SSI.onStorey, iri("storey", niveau)))

    for l in geometrie["liaisons"]:
        a, b = iri("space", l["de"]), iri("space", l["vers"])
        g.add((a, SSI.isConnectedTo, b))
        g.add((b, SSI.isConnectedTo, a))
        if l["type"] == "escalier":
            s = iri("stair", l["element_globalId"])
            g.add((s, SSI.linksSpace, a))
            g.add((s, SSI.linksSpace, b))
            if l.get("cage_globalId"):
                g.add((iri("space", l["cage_globalId"]), BOT.containsElement, s))
            if l.get("longueur_volee_m"):
                g.add((s, SSI.flightLength, dec(l["longueur_volee_m"])))

    for d in geometrie.get("distances", []):
        via = d.get("element_globalId") or "libre"
        n = iri("distance", f"{d['de']}__{d['vers']}__{via}")
        g.add((n, RDF.type, SSI.EvacuationDistance))
        g.add((n, SSI["from"], iri("space", d["de"])))
        g.add((n, SSI.to, iri("space", d["vers"])))
        g.add((n, SSI.hasDistance, dec(d["distance_m"])))
        g.add((n, SSI.connectionType, Literal(TYPE_CONNEXION[d["type"]])))
        if d.get("element_globalId"):
            g.add((n, SSI.viaElement, iri("door" if d["type"] == "porte" else "stair", d["element_globalId"])))
        if d.get("distance_pang_m") is not None:
            g.add((n, SSI.pangDistance, dec(d["distance_pang_m"])))

    for d in geometrie.get("distances_sortie", []):
        n = iri("exitdistance", f"{d['de']}__{d['porte_globalId']}")
        g.add((n, RDF.type, SSI.ExitDistance))
        g.add((n, SSI.exitFrom, iri("space", d["de"])))
        g.add((n, SSI.exitVia, iri("door", d["porte_globalId"])))
        g.add((n, SSI.exitDistance, dec(d["distance_m"])))

    for i, comp in enumerate(logements(geometrie), start=1):
        prefixe = _prefixe_commun([espaces[x]["nom"] for x in comp])
        z = iri("dwelling", prefixe or str(i))
        g.add((z, RDF.type, SSI.Dwelling))
        g.add((batiment, BOT.containsZone, z))
        g.add((z, RDFS.label, Literal(f"Logement {prefixe or i}")))
        for x in comp:
            g.add((iri("space", x), SSI.inDwelling, z))

    connus = set(espaces) | {p["globalId"] for p in geometrie["portes"]} | \
             {s["globalId"] for s in geometrie.get("escaliers", [])}
    genre = {**{gid: "space" for gid in espaces}, **{p["globalId"]: "door" for p in geometrie["portes"]},
             **{s["globalId"]: "stair" for s in geometrie.get("escaliers", [])}}
    for i, a in enumerate(geometrie["anomalies"], start=1):
        n = iri("anomaly", f"{i:03d}")
        g.add((n, RDF.type, SSI.ModelAnomaly))
        g.add((n, SSI.rule, Literal(a.get("regle", ""))))
        g.add((n, RDFS.comment, Literal(a["description"])))
        g.add((n, SSI.treatment, Literal(a["traitement"])))
        for gid in a.get("elements_concernes", [a["element_globalId"]]):
            g.add((n, SSI.concernsGlobalId, Literal(gid, datatype=XSD.string)))
            if gid in connus:
                g.add((n, SSI.concerns, iri(genre[gid], gid)))

    p = INST["parameters"]
    g.add((p, RDF.type, SSI.Parameters))
    for cle, prop in PARAMETRES.items():
        if cle in params:
            g.add((p, prop, dec(params[cle], 4)))
    origine = (params.get("origine_feu") or {}).get("globalId")
    if origine in espaces:
        g.add((p, SSI.fireOrigin, iri("space", origine)))
    return g
