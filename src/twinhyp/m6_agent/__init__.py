"""M6 – Agent neuro-symbolique : questions + demandes -> answers.jsonl, audit_log.jsonl (+ kg.ttl modifié).

- LLM open-weight LOCAL (Ollama ; par défaut qwen2.5:14b, choisi par un banc d'essai, cf. choix.md 9.x),
  température 0 et graine fixe ; chaque appel est journalisé dans `llm_journal.jsonl`.
- Questions : le LLM choisit l'outil et ses arguments, l'outil calcule (agent.py).
- Demandes : plan LLM -> delta -> veto SHACL sur copie -> adaptations -> ordre lexicographique (demandes.py).
- Contrôle : chaque réponse est comparée à la référence sans LLM (reference.py) ; un écart est SIGNALÉ
  (`conforme_reference`), jamais corrigé.

Configuration (`parametres.json`, clé facultative "agent") : modele, url, graine, max_iterations.
Variables d'environnement : TWINHYP_LLM_MODELE (remplace le modèle), TWINHYP_LLM_REJEU (chemin d'un
journal à rejouer sans Ollama : mêmes prompts -> mêmes réponses), TWINHYP_LLM=factice (tests de plomberie).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from rdflib import Graph

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json, ecrire_jsonl
from twinhyp.m6_agent import agent, demandes as D, outils as O, reference
from twinhyp.m6_agent.llm import Factice, Journal, Ollama, Rejeu

log = logging.getLogger("twinhyp")

DEFAUTS = {"modele": "qwen2.5:14b", "url": "http://localhost:11434", "graine": 0, "max_iterations": 3, "contexte": 8192}
FICHIER_JOURNAL = "llm_journal.jsonl"
FICHIER_RESUME = "agent_resume.json"


def config(params: dict) -> dict:
    cfg = {**DEFAUTS, **params.get("agent", {})}
    if os.environ.get("TWINHYP_LLM_MODELE"):
        cfg["modele"] = os.environ["TWINHYP_LLM_MODELE"]
    return cfg


def client(cfg: dict, journal: Journal):
    if os.environ.get("TWINHYP_LLM") == "factice":
        return Factice(journal)
    rejeu = os.environ.get("TWINHYP_LLM_REJEU")
    if rejeu:
        return Rejeu(Path(rejeu), journal)
    return Ollama(cfg["modele"], journal, cfg["url"], cfg["graine"], cfg["contexte"])


def executer(ctx: Contexte, llm=None) -> list[str]:
    cfg = config(ctx.params)
    from twinhyp.m5_evacuation import FICHIER_KG_AVANT_AGENT

    avant = ctx.sortie / FICHIER_KG_AVANT_AGENT  # état après M5 : M6 est idempotent
    g = Graph().parse(avant if avant.is_file() else ctx.chemin_sortie("kg"), format="turtle")
    boite = O.Boite(g, ctx.params, pareto=ctx.chemin_sortie("pareto"), devices=ctx.chemin_sortie("devices"),
                    geometrie=ctx.chemin_sortie("geometry"), ontologie=ctx.chemin_sortie("ontology"), formes=ctx.formes)
    journal = Journal(ctx.sortie / (FICHIER_JOURNAL + ".partiel"))  # un run interrompu n'écrase pas le journal précédent
    llm = llm or client(cfg, journal)
    resume = agent.resume_batiment(g)
    systeme = agent.SYSTEME.format(resume=resume)
    ref = reference.reponses(g, boite.pareto)

    t0 = time.perf_counter()
    questions = json.loads(ctx.questions.read_text(encoding="utf-8"))["questions"]
    reponses = []
    for q in questions:
        r = agent.repondre_question(llm, boite, q, systeme, cfg["max_iterations"])
        if q["id"] in ref:
            r["conforme_reference"] = (not r.get("echec")) and reference.identiques(r["reponse"], ref[q["id"]][0])
        log.info("m6 %s : %s (%s, %d itération(s), %.1f s)", q["id"], r.get("outil"),
                 "conforme" if r.get("conforme_reference") else "ÉCART", r["iterations"], r["duree_s"])
        reponses.append(r)
    ecrire_jsonl(ctx.chemin_sortie("answers"), reponses)
    t_questions = time.perf_counter() - t0

    t1 = time.perf_counter()
    valider = D.Validateur(ctx.formes, ctx.chemin_sortie("ontology"))
    dem = json.loads(ctx.demandes.read_text(encoding="utf-8"))["demandes"]
    audit = D.traiter(llm, g, dem, boite, valider, resume)
    ecrire_jsonl(ctx.chemin_sortie("audit"), audit)
    g.serialize(ctx.chemin_sortie("kg"), format="turtle", encoding="utf-8")  # modifications validées (commit)
    t_demandes = time.perf_counter() - t1

    ecrire_json(ctx.sortie / FICHIER_RESUME, {
        "modele": getattr(llm, "modele", None), "digest": getattr(llm, "digest", None),
        "rejeu": bool(os.environ.get("TWINHYP_LLM_REJEU")), "options": {"temperature": 0, "graine": cfg["graine"]},
        "questions": len(reponses), "conformes_reference": sum(bool(r.get("conforme_reference")) for r in reponses),
        "ecarts": [r["id"] for r in reponses if r["id"] in ref and not r.get("conforme_reference")],
        "iterations_totales": sum(r["iterations"] for r in reponses),
        "decisions": [{"demande": l["demande_id"], "espace": l.get("espace_globalId"), "decision": l["decision"]}
                      for l in audit],
        "validations_shacl": valider.appels, "duree_questions_s": round(t_questions, 1),
        "duree_demandes_s": round(t_demandes, 1)})
    journal.chemin.replace(ctx.sortie / FICHIER_JOURNAL)
    return ["answers", "audit", "kg"]
