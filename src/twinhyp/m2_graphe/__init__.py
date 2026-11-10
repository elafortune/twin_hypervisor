"""M2 – Graphe de connaissances : geometry.json + paramètres -> ontology.ttl, kg.ttl.

Étape 4 : ontologie = socle (inchangé) + extension alignée (BOT, SAREF4BLDG) ;
graphe statique (niveaux, espaces, portes, sorties, escaliers, liaisons, distances,
logements, anomalies, paramètres). Les observations SOSA arrivent avec M5.
"""

import json
from pathlib import Path

from rdflib import Graph

from twinhyp.contexte import Contexte
from twinhyp.m2_graphe.construction import construire

DOSSIER = Path(__file__).parent
EXTENSION = DOSSIER / "ontologie_extension.ttl"
FORMES_MAISON = DOSSIER / "formes_maison.ttl"


def ontologie(socle: Path) -> Graph:
    g = Graph()
    g.parse(socle, format="turtle")
    g.parse(EXTENSION, format="turtle")
    g.bind("s4bldg", "https://saref.etsi.org/saref4bldg/")
    return g


def executer(ctx: Contexte) -> list[str]:
    geometrie = json.loads(ctx.chemin_sortie("geometry").read_text(encoding="utf-8"))
    ontologie(ctx.ontologie_socle).serialize(ctx.chemin_sortie("ontology"), format="turtle", encoding="utf-8")
    nom = Path(geometrie.get("source", {}).get("ifc", "batiment")).stem
    construire(geometrie, ctx.params, nom).serialize(ctx.chemin_sortie("kg"), format="turtle", encoding="utf-8")
    return ["ontology", "kg"]
