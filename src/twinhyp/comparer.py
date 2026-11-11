"""Comparaison de deux dossiers de sorties, étape par étape (ex. détecteurs de fumée / de chaleur).

Ne recalcule rien de coûteux : lit devices.json, evacuation_dynamique.jsonl, kg_avant_agent.ttl (réponses
de référence sans LLM), et, s'ils existent, answers.jsonl, audit_log.jsonl et agent_resume.json.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from rdflib import Graph


def _json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.is_file() else []


def m4(out: Path) -> dict:
    d = _json(out / "devices.json") or {}
    eqs = d.get("equipements", [])
    return {"par_type": dict(sorted(Counter(e["type"] for e in eqs).items())), "total": len(eqs),
            "statuts": {k: v.get("statut") for k, v in d.get("sous_problemes", {}).items() if isinstance(v, dict)}}


def m5(out: Path, noms: dict) -> dict:
    lignes = _jsonl(out / "evacuation_dynamique.jsonl")
    s2 = [l for l in lignes if l["strategie"] == 2]
    perte = {}
    for l in sorted(s2, key=lambda l: l["t_s"]):
        if l["route"] is None:
            perte.setdefault(noms.get(l["espace_globalId"], l["espace_globalId"]), l["t_s"])
    s1_danger = [l for l in lignes if l["strategie"] == 1 and l["espaces_dangereux"]]
    alarme = _alarme(out)
    sans_alarme = [l for l in lignes if l["strategie"] == 2 and (alarme is None or l["t_s"] < alarme)]
    premiere_perte = min(perte.values(), default=None)
    return {"alarme_s": alarme,
            "personnes_x_pas_sans_alarme": sum(l["personnes"] for l in sans_alarme),
            "delai_alarme_avant_premiere_perte_de_route_s": (premiere_perte - alarme) if None not in (alarme, premiere_perte) else None,
            "lignes": len(lignes), "routes_nulles_strategie_2": sum(l["route"] is None for l in s2),
            "routes_habituelles_traversant_un_danger": len(s1_danger),
            "perte_de_route_sure_par_espace_s": dict(sorted(perte.items()))}


def _alarme(out: Path) -> int | None:
    import re

    for f in ("kg_avant_agent.ttl", "kg.ttl"):
        if (out / f).is_file():
            m = re.search(r"alarmTime (\d+)", (out / f).read_text(encoding="utf-8"))
            return int(m.group(1)) if m else None
    return None


def reference(out: Path) -> dict:
    from twinhyp.m6_agent import reference as R

    kg = out / "kg_avant_agent.ttl"
    if not kg.is_file():
        kg = out / "kg.ttl"
    g = Graph().parse(kg, format="turtle")
    return {q: v[0] for q, v in R.reponses(g, out / "pareto.json").items()}, g


def m6(out: Path) -> dict:
    res = _json(out / "agent_resume.json")
    audit = _jsonl(out / "audit_log.jsonl")
    return {"resume": {k: res[k] for k in ("modele", "conformes_reference", "ecarts", "duree_questions_s", "duree_demandes_s")}
            if res else None,
            "decisions": [(l["demande_id"], l.get("decision"), l.get("formes_violees"), l.get("triplets_ajoutes"),
                           l.get("triplets_retires")) for l in audit]}


def comparer(a: Path, b: Path) -> dict:
    geo = _json(a / "geometry.json") or {}
    noms = {e["globalId"]: e["nom"] for e in geo.get("espaces", [])}
    ra, _ = reference(a)
    rb, _ = reference(b)
    nom = lambda v: [noms.get(x, x) for x in v] if isinstance(v, list) else v
    return {"a": str(a), "b": str(b),
            "m4": {"a": m4(a), "b": m4(b)},
            "m5": {"a": m5(a, noms), "b": m5(b, noms)},
            "reponses_reference": {q: {"a": nom(ra.get(q)), "b": nom(rb.get(q)), "identiques": ra.get(q) == rb.get(q)}
                                   for q in sorted(set(ra) | set(rb))},
            "m6": {"a": m6(a), "b": m6(b)}}
