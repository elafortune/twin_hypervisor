"""Réponses de RÉFÉRENCE aux 20 questions du kit, calculées sans LLM (gabarits SPARQL + planificateur).

Sert à deux choses : la commande `python -m twinhyp questions` (étapes 4–5) et le CONTRÔLE de l'agent
(chaque réponse de l'agent est comparée à celle-ci ; un écart est signalé, jamais corrigé en silence).
Les paramètres (« Level 2 », « A202 »…) sont ceux des énoncés du kit : propres au duplex, donc
uniquement ici, jamais dans l'agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph

from twinhyp.m2_graphe import requetes as R


def reponses(g: Graph, pareto: Path | None = None) -> dict[str, tuple]:
    """{qid: (réponse, requêtes SPARQL exécutées)} ; Q15–Q19 absentes si le scénario n'a pas été rejoué."""
    from twinhyp.m5_evacuation import instant_alarme, plus_de_route_sure, route_a

    rep = {}
    for qid in ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q09", "Q10", "Q11", "Q12", "Q13", "Q14"]:
        rep[qid] = R.repondre(g, qid)
    q07 = R.chemin(g, R.espace(g, "A202")[0], R.espace(g, "A101")[0])
    rep["Q07"] = (q07["largeur_min_porte_m"], q07["requetes"])
    q08 = R.chemin(g, R.espace(g, "B202", "Bedroom 2")[0], R.espace(g, "B101")[0])
    rep["Q08"] = (q08["espaces"][1:], q08["requetes"])
    if instant_alarme(g) is not None:
        rep["Q15"] = R.repondre(g, "Q15")
        rep["Q16"] = R.repondre(g, "Q16")
        a202 = R.espace(g, "A202")[0]
        route, req = route_a(g, a202, instant_alarme(g))
        rep["Q17"] = (route["route"] if route else [], req)
        rep["Q18"] = plus_de_route_sure(g, a202)
        rep["Q19"] = R.repondre(g, "Q19")
    if pareto is not None and pareto.is_file():
        from twinhyp.m3_iwcmc import q20

        rep["Q20"] = (q20(json.loads(pareto.read_text(encoding="utf-8"))), [])
    return dict(sorted(rep.items()))


def identiques(a, b) -> bool:
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and sorted(map(str, a)) == sorted(map(str, b))
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
