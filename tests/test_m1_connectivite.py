"""Étape 2 : connectivité (vote à 3 sources, ouvertures, escaliers, évacuabilité)."""

import pytest

from conftest import IFC_DUPLEX
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m1_geometrie.connectivite import Index, controler_evacuabilite, fusionner, graphe, vote


# Unitaires ---------------------------------------------------------------------
def test_vote_majorite():
    retenus, _ = vote({"ifc": {"a", "b", "c"}, "pang": {"a", "b"}, "geometrie": {"a", "b"}})
    assert retenus == ["a", "b"]


def test_vote_source_absente():
    retenus, _ = vote({"ifc": set(), "pang": None, "geometrie": {"a", "b"}})
    assert retenus == []  # 2 sources disponibles, seuil 2 : une seule citation ne suffit pas
    retenus, _ = vote({"ifc": None, "pang": None, "geometrie": {"a", "b"}})
    assert retenus == ["a", "b"]  # seule source disponible


def test_escalier_prioritaire_sur_ouverture():
    ls = [{"de": "x", "vers": "y", "type": "ouverture"}, {"de": "y", "vers": "x", "type": "escalier"}]
    assert [l["type"] for l in fusionner(ls)] == ["escalier"]


def test_espace_isole_detecte():
    geo = {"espaces": [{"globalId": "a", "nom": "A", "occupable": True},
                       {"globalId": "b", "nom": "B", "occupable": True}],
           "portes": [{"globalId": "p", "espaces": ["a"], "sortie": True}], "liaisons": []}
    assert [x["element_globalId"] for x in controler_evacuabilite(geo)] == ["b"]


def test_index_chevauchement_vertical():
    idx = Index([{"globalId": "a", "polygone_xy": [[0, 0], [1, 0], [1, 1]], "z_bas_m": 0, "hauteur_m": 2.6},
                 {"globalId": "b", "polygone_xy": [[0, 0], [1, 0], [1, 1]], "z_bas_m": 3.1, "hauteur_m": 2.6}])
    assert idx.chevauchement_vertical("a", "b") < 0


# Duplex ------------------------------------------------------------------------
@pytest.fixture(scope="module")
def geo():
    return construire_geometrie(IFC_DUPLEX)


@pytest.fixture(scope="module")
def nom(geo):
    return {e["globalId"]: e["nom"] for e in geo["espaces"]}


def paires(geo, nom, type_):
    return {frozenset((nom[l["de"]], nom[l["vers"]])) for l in geo["liaisons"] if l["type"] == type_}


def test_dix_portes_interieures_et_quatre_sorties(geo):
    assert len([l for l in geo["liaisons"] if l["type"] == "porte"]) == 10
    sorties = [p for p in geo["portes"] if p["sortie"]]
    assert len(sorties) == 4


def test_porte_a_trois_espaces_corrigee(geo, nom):
    porte = next(p for p in geo["portes"] if p["globalId"] == "1aj$VJZFn2TxepZUBcKpac")
    assert sorted(nom[g] for g in porte["espaces"]) == ["A204", "A205"]
    assert any(a["regle"] == "porte_sources_concordantes" and a["element_globalId"] == porte["globalId"]
               for a in geo["anomalies"])


def test_ouvertures_libres(geo, nom):
    assert paires(geo, nom, "ouverture") == {frozenset(p) for p in [
        ("A101", "A102"), ("A101", "A103"), ("A102", "A103"), ("A101", "A105"),
        ("B101", "B102"), ("B101", "B103"), ("B102", "B103"), ("B101", "B105")]}


def test_escaliers_depuis_les_cages(geo, nom):
    assert paires(geo, nom, "escalier") == {frozenset(("A105", "A201")), frozenset(("B105", "B201"))}


def test_aucun_passage_entre_logements(geo, nom):
    """Q13 : aucune liaison ne relie un espace A à un espace B."""
    for l in geo["liaisons"]:
        assert nom[l["de"]][0] == nom[l["vers"]][0]


def test_tout_espace_occupable_est_evacuable(geo):
    assert not [a for a in geo["anomalies"] if a["regle"] == "espace_evacuable"]
    G = graphe(geo)
    assert G.degree("EXTERIEUR") == 4


def test_anomalies_de_connectivite(geo):
    regles = {a["regle"] for a in geo["anomalies"]}
    assert {"porte_sources_concordantes", "chevauchement_espaces", "limite_bien_placee",
            "limite_type_coherent"} <= regles
