"""Étape 3 : distances d'évacuation (point le plus défavorable, visibilité + Dijkstra, Pang)."""

import math

import pytest
from shapely.geometry import Point, Polygon

from conftest import IFC_DUPLEX
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m1_geometrie.distances import distance_defavorable, itineraire


# Unitaires : réponses calculées à la main ----------------------------------------
def test_rectangle_coin_le_plus_eloigne():
    r = distance_defavorable(Polygon([(0, 0), (3, 0), (3, 2), (0, 2)]), Point(0, 1))
    assert r["distance_plan_m"] == pytest.approx(math.sqrt(10))
    assert r["distance_pang_m"] == pytest.approx(math.sqrt(10))
    assert r["point_defavorable_xy"][0] == 3


def test_polygone_en_L_contourne_l_angle():
    """Cible en haut de la branche verticale ; le pire point (4,0) passe par l'angle rentrant (1,1)."""
    L = Polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 4), (0, 4)])
    r = distance_defavorable(L, Point(0.5, 4))
    attendu = math.sqrt(10) + math.sqrt(9.25)
    assert r["distance_plan_m"] == pytest.approx(attendu)
    assert r["distance_pang_m"] == pytest.approx(attendu)  # un seul sommet intermédiaire : Pang exact
    assert r["point_defavorable_xy"] == [4.0, 0.0]
    assert [1.0, 1.0] in r["chemin_xy"]


def test_polygone_en_U_depasse_la_formule_de_pang():
    """Deux angles rentrants à contourner : Pang ne s'applique plus, Dijkstra si."""
    U = Polygon([(0, 0), (3, 0), (3, 3), (2, 3), (2, 1), (1, 1), (1, 3), (0, 3)])
    r = distance_defavorable(U, Point(0.5, 3))
    assert r["distance_plan_m"] == pytest.approx(math.sqrt(5) + 1 + math.sqrt(4.25))
    assert r["distance_pang_m"] is None


# Duplex ------------------------------------------------------------------------
@pytest.fixture(scope="module")
def geo():
    return construire_geometrie(IFC_DUPLEX)


@pytest.fixture(scope="module")
def gid(geo):
    return {e["nom"] if e.get("nom_long") != "Bedroom 2" else "B202_bedroom2": e["globalId"]
            for e in geo["espaces"]}


def test_deux_sens_par_liaison_et_distances_positives(geo):
    assert len(geo["distances"]) == 2 * len(geo["liaisons"])
    assert all(d["distance_m"] > 0 for d in geo["distances"])  # forme F7
    assert len(geo["distances_sortie"]) == 4
    assert not [a for a in geo["anomalies"] if a["regle"] == "distance_calculable"]


def test_distances_orientees(geo, gid):
    d = {(x["de"], x["vers"]): x["distance_m"] for x in geo["distances"]}
    assert d[(gid["A105"], gid["A101"])] != pytest.approx(d[(gid["A101"], gid["A105"])])


def test_longueur_de_volee(geo):
    volees = [l["longueur_volee_m"] for l in geo["liaisons"] if l["type"] == "escalier"]
    # 15 girons de 0,25 m et 3,05 m de dénivelé : ≈ 4,85 m
    assert all(4.5 < v < 5.2 for v in volees)


def test_q07_largeur_min_entre_A202_et_entree_A101(geo, gid):
    entree = next(d["porte_globalId"] for d in geo["distances_sortie"] if d["de"] == gid["A101"])
    r = itineraire(geo, gid["A202"], entree)
    assert r["espaces"] == [gid[n] for n in ("A202", "A201", "A105", "A101")]
    assert r["largeur_min_porte_m"] == pytest.approx(0.864)


def test_q08_chemin_bedroom2_vers_entree_B(geo, gid):
    entree = next(d["porte_globalId"] for d in geo["distances_sortie"] if d["de"] == gid["B101"])
    r = itineraire(geo, gid["B202_bedroom2"], entree)
    assert r["espaces"][1:] == [gid[n] for n in ("B201", "B105", "B101")]
