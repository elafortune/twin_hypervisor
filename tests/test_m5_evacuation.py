"""Étape 5 : évacuation dynamique (SOSA, état verrouillé, stratégies, pénalité / contrainte dure, Q15–Q19)."""

import json
from pathlib import Path

import networkx as nx
import pytest
from rdflib import Graph

from conftest import DONNEES, IFC_DUPLEX, OBS, PARAMS
from twinhyp.io_schemas import FORMES_EQUIPEMENTS, charger_validateur, erreurs_document, rapport_shacl
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m2_graphe import FORMES_MAISON, ontologie
from twinhyp.m2_graphe import requetes as R
from twinhyp.m2_graphe.construction import construire
from twinhyp.m5_evacuation import (EXTERIEUR, ecrire_routes, lire_observations, plus_de_route_sure,
                                   rejouer, route_a, route_penalite, route_sure, seuils, instant_alarme)


# Unitaires : pénalité contre contrainte dure ---------------------------------------
@pytest.fixture
def mini():
    """Deux chemins vers la sortie : 1 200 m sûr par S, 20 m par D (dangereux)."""
    G = nx.DiGraph()
    G.add_edge("A", "D", weight=10.0)
    G.add_edge("D", EXTERIEUR, weight=10.0)
    G.add_edge("A", "S", weight=600.0)
    G.add_edge("S", EXTERIEUR, weight=600.0)
    return G


def test_penalite_choisit_le_chemin_dangereux(mini):
    r = route_penalite(mini, "A", {"D"}, 1000.0)
    assert r["route"] == ["A", "D"] and r["espaces_dangereux_traverses"] == ["D"]


def test_contrainte_dure_choisit_le_chemin_sur(mini):
    assert route_sure(mini, "A", {"D"})["route"] == ["A", "S"]


def test_sans_route_sure_la_contrainte_dure_renvoie_null(mini):
    assert route_sure(mini, "A", {"D", "S"}) is None
    assert route_penalite(mini, "A", {"D", "S"}, 1000.0) is not None  # la pénalité « trouve » une route


def test_depart_dangereux_pas_de_route(mini):
    assert route_sure(mini, "A", {"A"}) is None  # F8 : routeFor ne peut pas être dangereux


def test_seuils_surchargeables():
    assert seuils({"seuil_danger_temperature_degC": 50})["seuil_danger_temperature_degC"] == 50.0
    assert seuils({})["seuil_alarme_obscurcissement_par_m"] == 0.0328


# Duplex ------------------------------------------------------------------------
@pytest.fixture(scope="module")
def scenario():
    geo = construire_geometrie(IFC_DUPLEX)
    params = json.loads(Path(PARAMS).read_text(encoding="utf-8"))
    g = construire(geo, params, "duplex")
    lignes = rejouer(g, lire_observations(OBS), seuils(params))
    ecrire_routes(g, lignes)
    return g, lignes


@pytest.mark.integration
def test_jsonl_conforme_au_schema(scenario):
    _, lignes = scenario
    v = charger_validateur(DONNEES / "schemas", "evacuation_dynamique.schema.json")
    assert lignes and all(not erreurs_document(v, l) for l in lignes)


@pytest.mark.integration
def test_q15_a_q19(scenario):
    g, lignes = scenario
    nom = lambda gids: sorted(R.executer(g, R.PREFIXES + f'SELECT ?n WHERE {{ ?s ssi:ifcGlobalId ?g ; '
                                         f'<http://www.w3.org/2000/01/rdf-schema#label> ?n . FILTER (STR(?g) = "{x}") }}')[0][0]
                              for x in gids)
    assert R.repondre(g, "Q15")[0] == 70
    q16 = R.repondre(g, "Q16")[0]
    assert nom(q16) == ["A101", "A102", "A103", "A105", "A201"]
    assert q16 == R.repondre(g, "Q16_observations")[0]  # état verrouillé = recalcul depuis les observations
    a202 = R.espace(g, "A202")[0]
    route, _ = route_a(g, a202, instant_alarme(g))
    assert nom(route["route"]) == ["A101", "A105", "A201", "A202"]
    t18, _ = plus_de_route_sure(g, a202)
    assert t18 == 180
    # cohérence avec le JSONL : première ligne sans route pour A202 (stratégie 2)
    assert min(l["t_s"] for l in lignes if l["espace_globalId"] == a202 and l["strategie"] == 2
               and l["route"] is None) == t18
    assert nom(R.repondre(g, "Q19")[0]) == ["A202", "A203"]


@pytest.mark.integration
def test_exemple_chiffre_penalite(scenario):
    """À t = 180 s : la pénalité propose une route par A101 (dangereux), la contrainte dure renvoie null."""
    g, lignes = scenario
    a202 = R.espace(g, "A202")[0]
    l = next(x for x in lignes if x["t_s"] == 180 and x["espace_globalId"] == a202 and x["strategie"] == 2)
    assert l["route"] is None
    assert l["route_penalite_pang"]["espaces_dangereux_traverses"] and l["route_penalite_pang"]["distance_m"] > 1000


@pytest.mark.integration
def test_graphe_final_conforme_f8(scenario, tmp_path):
    g, _ = scenario
    onto = tmp_path / "ontology.ttl"
    ontologie(DONNEES / "ontologie" / "ssi_socle.ttl").serialize(onto, format="turtle")
    kg = tmp_path / "kg.ttl"
    g.serialize(kg, format="turtle")
    ok, texte = rapport_shacl(kg, [DONNEES / "ontologie" / "formes_publiques.ttl", FORMES_MAISON], onto,
                              FORMES_EQUIPEMENTS)
    assert ok, texte[:3000]


def test_detour_reactif(mini):
    from twinhyp.m5_evacuation import route_detour
    statique = route_sure(mini, "A", set())  # A -> D -> sortie (20 m)
    assert statique["route"] == ["A", "D"]
    d = route_detour(mini, statique, {"D"})
    assert d["route"] == ["A", "S"] and d["detour"]  # s'arrête en A, repart par S
    assert route_detour(mini, statique, {"D", "S"})["bloque_dans"] == "A"


@pytest.mark.integration
def test_detour_bloque_dans_la_cage_et_espaces_sans_camera(scenario):
    """À 180 s, l'occupant de A202 qui suit le plan est bloqué dans la cage A105 (pire que le confinement)."""
    g, lignes = scenario
    a202, a105 = R.espace(g, "A202")[0], R.espace(g, "A105")[0]
    l1 = next(x for x in lignes if x["t_s"] == 180 and x["espace_globalId"] == a202 and x["strategie"] == 1)
    assert l1["route_detour_reactif"]["bloque_dans"] == a105
    l2 = next(x for x in lignes if x["t_s"] == 300 and x["espace_globalId"] == a202 and x["strategie"] == 2)
    assert a105 in l2["espaces_dangereux_sans_comptage"]
