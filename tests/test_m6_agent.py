"""Étape 9 : agent neuro-symbolique (outils, boucle d'agent, veto SHACL, demandes, rejeu du journal).

Le LLM est remplacé par un LLM SCRIPTÉ (appels d'outils et plans écrits à la main) : on teste la partie
symbolique et la boucle sans dépendre d'Ollama. L'agent réel (qwen2.5:14b) est mesuré par la chaîne.
"""

import json

import pytest
from rdflib import Graph

from conftest import IFC_DUPLEX, OBS, PARAMS
from twinhyp.contexte import Contexte
from twinhyp.m6_agent import agent, demandes as D, outils as O, reference
from twinhyp.m6_agent.llm import Journal, Rejeu, empreinte
from twinhyp.pipeline import executer


class Scripte:
    """Renvoie, dans l'ordre, les réponses prévues pour chaque tâche."""
    modele, digest = "scripte", None

    def __init__(self, script: dict):
        self.script = {k: list(v) for k, v in script.items()}
        self.appels = []

    def chat(self, messages, outils=None, format_=None, tache=""):
        self.appels.append(tache)
        rep = self.script[tache].pop(0)
        if isinstance(rep, tuple):  # appel d'outil
            return {"reponse": {"role": "assistant", "content": "",
                                "tool_calls": [{"function": {"name": rep[0], "arguments": rep[1]}}]}}
        return {"reponse": {"role": "assistant", "content": json.dumps(rep) if isinstance(rep, dict) else rep}}


@pytest.fixture(scope="module")
def sorties(tmp_path_factory):
    """Chaîne M1, M2, M4, M5 sur le duplex (M3 inutile ici : seule Q20 en dépend)."""
    out = tmp_path_factory.mktemp("m6")
    ctx = Contexte(ifc=IFC_DUPLEX, params_chemin=PARAMS, obs=OBS, sortie=out)
    executer(ctx, ["m1", "m2", "m4", "m5"])
    return ctx


@pytest.fixture
def boite(sorties):
    g = Graph().parse(sorties.chemin_sortie("kg"), format="turtle")
    return O.Boite(g, sorties.params, devices=sorties.chemin_sortie("devices"), geometrie=sorties.chemin_sortie("geometry"))


# Outils ------------------------------------------------------------------------------------------
@pytest.mark.integration
def test_sparql_en_lecture_seule(boite):
    with pytest.raises(O.ErreurOutil, match="lecture seule"):
        O.appeler(boite, "sparql", {"requete": "DELETE WHERE { ?s ?p ?o }"})
    assert len(boite.g) > 0


@pytest.mark.integration
def test_nom_ambigu_renvoie_une_erreur_exploitable(boite):
    with pytest.raises(O.ErreurOutil, match="ambigu"):
        O.resoudre_espace(boite.g, "B202")  # deux espaces portent ce nom dans l'IFC
    assert O.resoudre_espace(boite.g, "B202", "Bedroom 2") != O.resoudre_espace(boite.g, "B202", "Bedroom 1")


@pytest.mark.integration
def test_outils_generiques_egaux_a_la_reference(boite):
    ref = reference.reponses(boite.g)
    assert O.appeler(boite, "espaces_du_niveau", {"niveau": "level 2"}).valeur == ref["Q01"][0]
    assert O.appeler(boite, "surface_totale", {"niveau": "Level 2"}).valeur == ref["Q10"][0]
    r = O.appeler(boite, "route_evacuation", {"espace": "A202", "t_s": "alarme"})
    assert r.valeur == ref["Q17"][0] and r.requetes


# Boucle d'agent ---------------------------------------------------------------------------------
@pytest.mark.integration
def test_auto_correction_apres_erreur_d_outil(boite):
    q = {"id": "Q08", "type": "ensemble", "question": "…"}
    llm = Scripte({"Q08": [("itineraire", {"depart": "B202", "arrivee": "B101", "mesure": "espaces_traverses"}),
                           ("itineraire", {"depart": "B202", "depart_nom_long": "Bedroom 2", "arrivee": "B101",
                                           "mesure": "espaces_traverses"})]})
    r = agent.repondre_question(llm, boite, q, "système")
    assert r["iterations"] == 2 and "ambigu" in r["trace"][0]["erreur"]
    assert r["reponse"] == reference.reponses(boite.g)["Q08"][0]


@pytest.mark.integration
def test_type_de_reponse_controle(boite):
    q = {"id": "Q05", "type": "valeur", "question": "…"}
    llm = Scripte({"Q05": [("espaces_du_niveau", {"niveau": "Level 1"}), ("surface_totale", {"prefixe": "A"})]})
    r = agent.repondre_question(llm, boite, q, "système")
    assert r["iterations"] == 2 and isinstance(r["reponse"], float)


# Demandes ----------------------------------------------------------------------------------------
PLANS = {
    "D1": {"action": "changer_type_detecteur", "espace": "A103", "nouveau_type": "HeatDetector"},
    "D2": {"action": "deplacer_equipement", "espace": "A201", "espace_cible": "A202"},
    "D3": {"action": "retirer_detecteurs", "niveau": "Level 2"},
    "D4": {"action": "diriger_evacuation", "niveau": "Level 2", "logement": "A", "t_s": 200, "route": "habituelle"},
}


@pytest.fixture(scope="module")
def audit(sorties):
    g = Graph().parse(sorties.chemin_sortie("kg"), format="turtle")
    b = O.Boite(g, sorties.params, devices=sorties.chemin_sortie("devices"), geometrie=sorties.chemin_sortie("geometry"))
    script = {}
    for d, p in PLANS.items():
        script[f"{d}:plan"] = [{**{k: None for k in D.PLAN["required"]}, **p}]
        script[f"{d}:justification"] = [{"justification": "texte"}]
    dem = json.loads(sorties.demandes.read_text(encoding="utf-8"))["demandes"]
    v = D.Validateur(sorties.formes, sorties.chemin_sortie("ontology"))
    lignes = D.traiter(Scripte(script), g, dem, b, v, "résumé")
    return g, lignes, sorties


@pytest.mark.integration
def test_d1_accepte_detecteur_de_chaleur(audit):
    g, lignes, _ = audit
    l = next(l for l in lignes if l["demande_id"] == "D1")
    assert l["decision"] == "acceptee" and not l["formes_violees"] and l["triplets_ajoutes"] >= 1
    a103 = O.resoudre_espace(g, "A103")
    assert any("HeatDetector" in str(c) for d in D.detecteurs(g, D.iri("space", a103)) for c in g.objects(d, D.RDF.type))


@pytest.mark.integration
def test_d2_veto_f3_et_refus(audit):
    _, lignes, _ = audit
    l = next(l for l in lignes if l["demande_id"] == "D2")
    assert l["decision"] == "refusee" and "F3_Detection" in l["formes_violees"] and l["source"] == "veto_symbolique"


@pytest.mark.integration
def test_d3_adaptation_detection_temporaire(audit):
    _, lignes, _ = audit
    l = next(l for l in lignes if l["demande_id"] == "D3")
    assert l["decision"] == "acceptee_avec_adaptation" and "F3_Detection" in l["formes_violees"]


@pytest.mark.integration
def test_d4_route_habituelle_refusee_par_f8(audit):
    _, lignes, _ = audit
    d4 = [l for l in lignes if l["demande_id"] == "D4"]
    assert d4 and all("F8_RouteSure" in l["formes_violees"] for l in d4 if l["decision"] != "acceptee")
    assert all(l["route"] is None or l["decision"] == "acceptee_avec_adaptation" for l in d4)


@pytest.mark.integration
def test_graphe_apres_demandes_conforme_et_audit_au_schema(audit):
    from twinhyp.io_schemas import charger_validateur, erreurs_document, formes_violees_graphe

    g, lignes, ctx = audit
    assert formes_violees_graphe(g, ctx.formes, ctx.chemin_sortie("ontology"))[0] == []
    v = charger_validateur(ctx.schemas, "audit_log.schema.json")
    assert all(not erreurs_document(v, l) for l in lignes)


# Journal et rejeu -----------------------------------------------------------------------------------
def test_rejeu_rend_la_meme_reponse(tmp_path):
    msgs = [{"role": "user", "content": "q"}]
    j = tmp_path / "j.jsonl"
    j.write_text(json.dumps({"empreinte": empreinte(msgs, None, None), "modele": "m", "digest": "d",
                             "reponse": {"content": "42"}}) + "\n", encoding="utf-8")
    r = Rejeu(j, Journal(tmp_path / "nouveau.jsonl"))
    assert r.chat(msgs, tache="t")["reponse"]["content"] == "42"
    assert json.loads((tmp_path / "nouveau.jsonl").read_text(encoding="utf-8"))["rejeu"] is True
    with pytest.raises(RuntimeError):
        r.chat([{"role": "user", "content": "autre"}], tache="t")


@pytest.mark.integration
def test_booleen_en_texte_converti(boite):
    a = O.appeler(boite, "itineraire", {"depart": "A202", "arrivee": "A101", "mesure": "espaces_traverses", "inclure_depart": "False"})
    b = O.appeler(boite, "itineraire", {"depart": "A202", "arrivee": "A101", "mesure": "espaces_traverses", "inclure_depart": False})
    assert a.valeur == b.valeur
