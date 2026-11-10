"""Écriture du déploiement dans kg.ttl : équipements, zones de détection, chemins d'évacuation (F3–F6)."""

from __future__ import annotations

from rdflib import RDF, RDFS, XSD, Graph, Literal

from twinhyp.m2_graphe.construction import SSI, dec, iri

CLASSE = {"SmokeDetector": SSI.SmokeDetector, "HeatDetector": SSI.HeatDetector,
          "ManualCallPoint": SSI.ManualCallPoint, "Camera": SSI.Camera, "IoTNode": SSI.SafetyDevice}


def ecrire(g: Graph, geometrie: dict, equipements: list[dict], zones: dict[str, str], chemins: dict) -> None:
    niveau_de = {e["globalId"]: e["niveau_globalId"] for e in geometrie["espaces"]}
    for zid, niveau in zones.items():
        z = iri("zone", zid)
        g.add((z, RDF.type, SSI.DetectionZone))
        g.add((z, RDFS.label, Literal(zid)))
        g.add((z, SSI.onStorey, iri("storey", niveau)))
    for (espace, sortie), info in chemins.items():
        p = iri("path", f"{espace}__{sortie}")
        g.add((p, RDF.type, SSI.EvacuationPath))
        g.add((p, SSI.pathFrom, iri("space", espace)))
        g.add((p, SSI.pathTo, iri("door", sortie)))
        g.add((p, SSI.coverageRatio, dec(info["couverture"], 4)))
        g.add((p, SSI.fullViewRatio, dec(info["full_view"], 4)))
    for e in equipements:
        d = iri("device", e["id"])
        g.add((d, RDF.type, CLASSE[e["type"]]))
        g.add((d, RDFS.label, Literal(e["id"])))
        g.add((d, SSI.isLocatedIn, iri("space", e["espace_globalId"])))
        g.add((d, SSI.onStorey, iri("storey", niveau_de[e["espace_globalId"]])))
        for cle, prop in (("x", SSI.posX), ("y", SSI.posY), ("z", SSI.posZ)):
            g.add((d, prop, dec(e[cle])))
        if e.get("zone_detection"):
            g.add((d, SSI.inDetectionZone, iri("zone", e["zone_detection"])))
        if e["type"] in ("SmokeDetector", "HeatDetector"):
            g.add((d, SSI.coversSpace, iri("space", e["espace_globalId"])))
        if e["type"] == "ManualCallPoint":
            for sortie, distance in e.get("sorties_servies", []):
                g.add((d, SSI.servesExit, iri("door", sortie)))
            # une seule valeur par déclencheur : la plus défavorable des sorties servies (prudent pour F4)
            g.add((d, SSI.distanceToExit, dec(max(dd for _, dd in e["sorties_servies"]))))
        if e["type"] == "Camera":
            g.add((d, SSI.azimuthDeg, dec(e["orientation_deg"])))
            g.add((d, SSI.tiltDeg, dec(e["inclinaison_deg"])))
            for (espace, sortie), info in chemins.items():
                if set(info["indices"]) & set(e["cellules_vues"]):
                    g.add((d, SSI.monitors, iri("path", f"{espace}__{sortie}")))
