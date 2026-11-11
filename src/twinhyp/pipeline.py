"""Orchestrateur : enchaîne M1 → M6, valide chaque sortie, trace les temps.

Chaque module expose `executer(ctx) -> list[str]` qui écrit ses sorties dans
`ctx.sortie` et renvoie les clés de `SORTIES` produites. Les modules ne se
parlent que par ces fichiers, ce qui permet de relancer un module seul
(`--etapes m2`) à partir des sorties déjà présentes.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import logging
import os
import platform
import time
from datetime import datetime, timezone

from twinhyp import __version__
from twinhyp.contexte import Contexte
from twinhyp.io_schemas import FORMES_EQUIPEMENTS, ecrire_json, verifier_sortie

log = logging.getLogger("twinhyp")

# Ordre imposé par les dépendances de données.
ETAPES = {
    "m1": "twinhyp.m1_geometrie",
    "m2": "twinhyp.m2_graphe",
    "m3": "twinhyp.m3_iwcmc",
    "m4": "twinhyp.m4_deploiement",
    "m5": "twinhyp.m5_evacuation",
    "m6": "twinhyp.m6_agent",
}

PAQUETS_TRACES = ["ifcopenshell", "numpy", "shapely", "networkx", "rdflib", "pyshacl", "jsonschema", "plotly"]


AVANT_DEPLOIEMENT = ("m1", "m2", "m3")  # le graphe ne contient pas encore d'équipements SSI


def verifier(ctx: Contexte, cles: list[str], etape: str | None = None) -> None:
    differees = FORMES_EQUIPEMENTS if etape in AVANT_DEPLOIEMENT else (() if etape else None)
    for cle in cles:
        verifier_sortie(ctx.chemin_sortie(cle), ctx.schemas, formes=ctx.formes,
                        ontologie=ctx.chemin_sortie("ontology"), differees=differees)


def machine() -> dict:
    versions = {}
    for p in PAQUETS_TRACES:
        try:
            versions[p] = md.version(p)
        except md.PackageNotFoundError:
            versions[p] = None
    return {
        "systeme": platform.platform(),
        "processeur": platform.processor(),
        "coeurs_logiques": os.cpu_count(),
        "python": platform.python_version(),
        "paquets": versions,
    }


def executer(ctx: Contexte, etapes: list[str] | None = None) -> dict:
    etapes = etapes or list(ETAPES)
    inconnues = [e for e in etapes if e not in ETAPES]
    if inconnues:
        raise ValueError(f"Étapes inconnues : {inconnues} (attendu : {list(ETAPES)})")

    trace = {
        "twinhyp": __version__,
        "debut": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entrees": {"ifc": str(ctx.ifc), "parametres": str(ctx.params_chemin), "observations": str(ctx.obs)},
        "graine": ctx.graine,
        "machine": machine(),
        "etapes": {},
    }
    ordre = [e for e in ETAPES if e in etapes]  # toujours dans l'ordre de la chaîne
    # mode rapide (grand bâtiment, entretien) : kg.ttl, réécrit par M2, M4, M5 et M6, n'est validé qu'à la
    # DERNIÈRE étape du run qui le produit (le graphe final est toujours validé en entier)
    kg_final_seulement = not bool(ctx.params.get("validation_kg_intermediaire", True))
    for i, nom in enumerate(ordre):
        module = importlib.import_module(ETAPES[nom])
        t0 = time.perf_counter()
        produites = module.executer(ctx)
        duree = time.perf_counter() - t0
        a_valider = [c for c in produites
                     if not (kg_final_seulement and c == "kg" and any(e in ordre[i + 1:] for e in ("m2", "m4", "m5", "m6")))]
        t1 = time.perf_counter()
        verifier(ctx, a_valider, nom)
        duree_v = time.perf_counter() - t1
        log.info("%s : %.2f s (+ validation %.1f s), sorties conformes : %s%s", nom, duree, duree_v, ", ".join(a_valider),
                 "" if a_valider == produites else " (kg validé en fin de chaîne)")
        trace["etapes"][nom] = {"duree_s": round(duree, 3), "validation_s": round(duree_v, 3), "sorties": produites,
                                "validees": a_valider}

    ecrire_json(ctx.sortie / "execution.json", trace)
    return trace
