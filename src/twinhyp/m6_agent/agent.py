"""Boucle d'agent pour les questions (ReAct borné, appel de fonctions Ollama).

Pour chaque question : le LLM lit la question et un résumé du bâtiment, puis appelle un outil.
- l'outil réussit et le type correspond (ensemble / valeur) -> la réponse EST le résultat de l'outil
  (GlobalId et requêtes SPARQL exacts : le LLM ne recopie jamais d'identifiant) ;
- l'outil échoue (nom inconnu, argument ambigu…) ou le type ne correspond pas -> le message d'erreur
  est renvoyé au LLM qui corrige son appel (auto-correction), au plus `max_iterations` tours.
"""

from __future__ import annotations

import json
import time

from twinhyp.m2_graphe import requetes as R
from twinhyp.m6_agent import outils as O

SYSTEME = """Tu es l'agent d'un jumeau numérique de bâtiment (sécurité incendie). Pour répondre à la question,
appelle UN outil avec les bons arguments ; la réponse sera le résultat de l'outil, n'invente aucun identifiant.
Prends les noms d'espaces, de niveaux et de logements dans le résumé du bâtiment ci-dessous (nom court, ex. A101).
Respecte les précisions de la question : seuils, instants, unités, espace de départ inclus ou exclu.
Pour une route « à l'instant de l'alarme », passe t_s = "alarme". Une couverture de 90 % s'écrit 0.9.

Résumé du bâtiment :
{resume}"""

SORTIES_BAT = R.PREFIXES + """SELECT ?l ?larg ?esp ?nl WHERE { ?p a ssi:Exit ; rdfs:label ?l ; ssi:connects ?s .
    ?s rdfs:label ?esp . OPTIONAL { ?p ssi:doorWidth ?larg } OPTIONAL { ?s ssi:longName ?nl } }"""


def resume_batiment(g) -> str:
    """Résumé générique (niveaux, logements, espaces, sorties), construit par SPARQL sur le graphe."""
    esp = sorted(O._espaces(g), key=lambda e: (e["niveau"], e["nom"], e["nom_long"]))
    lignes = ["Niveaux : " + ", ".join(sorted({e["niveau"] for e in esp if e["niveau"]})),
              "Logements : " + (", ".join(sorted({e["logement"] for e in esp if e["logement"]})) or "aucun"),
              "Espaces (nom court « nom long », niveau, logement) :"]
    lignes += [f"- {e['nom']} « {e['nom_long']} », {e['niveau'] or '?'}, {e['logement'] or 'hors logement'}" for e in esp]
    lignes.append("Portes de sortie vers l'extérieur (type de porte, largeur, espace) :")
    for l, larg, s, nl in sorted(R.executer(g, SORTIES_BAT), key=lambda x: str(x[2])):
        lignes.append(f"- {str(l).split(':')[0]} ({larg} m), espace {s} « {nl or ''} »")
    return "\n".join(lignes)


def _type_ok(attendu: str, valeur) -> bool:
    if attendu == "ensemble":
        return isinstance(valeur, list)
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)


def repondre_question(llm, boite: O.Boite, q: dict, systeme: str, max_iterations: int = 3) -> dict:
    messages = [{"role": "system", "content": systeme},
                {"role": "user", "content": f"Question {q['id']} (réponse attendue : {q['type']}) : {q['question']}"}]
    outils = O.schemas_ollama()
    jetons, t0, trace = 0, time.perf_counter(), []
    for it in range(1, max_iterations + 1):
        e = llm.chat(messages, outils, tache=q["id"])
        jetons += int(e.get("jetons_prompt", 0)) + int(e.get("jetons_generes", 0))
        msg = e["reponse"]
        appels = msg.get("tool_calls") or []
        messages.append({"role": "assistant", "content": msg.get("content", ""), **({"tool_calls": appels} if appels else {})})
        if not appels:
            messages.append({"role": "user", "content": "Appelle un des outils pour obtenir la réponse."})
            trace.append({"iteration": it, "erreur": "pas d'appel d'outil"})
            continue
        f = appels[0]["function"]
        nom, args = f["name"], f.get("arguments") or {}
        if isinstance(args, str):
            args = json.loads(args or "{}")
        try:
            res = O.appeler(boite, nom, args)
            if not _type_ok(q["type"], res.valeur):
                raise O.ErreurOutil(f"cet outil renvoie {type(res.valeur).__name__}, la question attend "
                                    f"{'une liste' if q['type'] == 'ensemble' else 'un nombre'} : choisir un autre outil")
        except O.ErreurOutil as exc:
            messages.append({"role": "tool", "content": f"ERREUR : {exc}. Corrige l'appel."})
            trace.append({"iteration": it, "outil": nom, "arguments": args, "erreur": str(exc)})
            continue
        trace.append({"iteration": it, "outil": nom, "arguments": args, "resultat": res.texte[:300]})
        return {"id": q["id"], "reponse": res.valeur, "requetes_sparql": res.requetes, "iterations": it,
                "jetons": jetons, "outil": nom, "arguments": args, "duree_s": round(time.perf_counter() - t0, 2),
                "trace": trace}
    return {"id": q["id"], "reponse": [], "requetes_sparql": [], "iterations": max_iterations, "jetons": jetons,
            "echec": True, "duree_s": round(time.perf_counter() - t0, 2), "trace": trace}
