"""Étape 1 : extraction IFC.

Tests unitaires sur des cas construits à la main, puis tests sur le duplex dont
les valeurs attendues ont été relevées dans l'IFC (voir carnet de bord).
"""

import numpy as np
import pytest

from conftest import IFC_DUPLEX
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m1_geometrie.extraction import est_occupable
from twinhyp.m1_geometrie.ifc_outils import Maillage, empreinte


# Unitaires ---------------------------------------------------------------------
def test_empreinte_ignore_les_faces_verticales():
    # carré 2 × 3 au sol (2 triangles) + une face verticale qui se projette en segment
    v = np.array([[0, 0, 0], [2, 0, 0], [2, 3, 0], [0, 3, 0], [0, 0, 1], [2, 0, 1]], float)
    t = np.array([[0, 1, 2], [0, 2, 3], [0, 1, 5]])
    assert empreinte(Maillage(v, t)).area == pytest.approx(6.0)


@pytest.mark.parametrize("nom, nom_long, niveau, attendu", [
    ("R301", "Roof", "Roof", False),
    ("A102", "Living Room", "Level 1", True),
    ("S1", "Gaine technique", "Niveau 2", False),
    ("A105", "Stair", "Level 1", True),   # circulation : occupable (à surveiller)
])
def test_regle_occupable(nom, nom_long, niveau, attendu):
    assert est_occupable(nom, nom_long, niveau) is attendu


# Duplex ------------------------------------------------------------------------
@pytest.fixture(scope="module")
def geo():
    return construire_geometrie(IFC_DUPLEX)


def test_comptages(geo):
    assert (len(geo["niveaux"]), len(geo["espaces"]), len(geo["portes"]), len(geo["escaliers"])) == (4, 21, 14, 2)


def test_altitudes_des_niveaux(geo):
    alt = {n["nom"]: n["altitude_m"] for n in geo["niveaux"]}
    assert alt == pytest.approx({"T/FDN": -1.25, "Level 1": 0.0, "Level 2": 3.1, "Roof": 6.0})


def test_espaces_complets(geo):
    for e in geo["espaces"]:
        assert e["niveau_globalId"] is not None
        assert len(e["globalId"]) == 22
        assert e["surface_m2"] > 0 and e["surface_geometrique_m2"] > 0
        assert len(e["polygone_xy"]) >= 3
        assert e["surface_source"] == "GSA BIM Area"


def test_seul_le_toit_est_non_occupable(geo):
    assert [e["nom"] for e in geo["espaces"] if not e["occupable"]] == ["R301"]


def test_surface_declaree_superieure_a_la_geometrique(geo):
    """Écart systématique observé (convention de mesure) : la surface déclarée
    est toujours plus grande, de moins de 25 %."""
    for e in geo["espaces"]:
        assert 0.75 < e["surface_geometrique_m2"] / e["surface_m2"] < 1.0


def test_quatre_sorties_provisoires(geo):
    sorties = [p for p in geo["portes"] if p["sortie"]]
    assert len(sorties) == 4 and all(len(p["espaces"]) == 1 for p in sorties)


def test_largeurs_de_portes(geo):
    largeurs = sorted(p["largeur_m"] for p in geo["portes"])
    assert largeurs[0] == pytest.approx(0.762) and largeurs[-1] == pytest.approx(1.25)


def test_escaliers_entre_level1_et_level2(geo):
    for s in geo["escaliers"]:
        assert s["z_bas_m"] == pytest.approx(0.0, abs=0.05)
        assert s["z_haut_m"] == pytest.approx(3.05, abs=0.1)
