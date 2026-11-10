"""Étape 6 : rayons verticaux, voxelisation, matériaux, positions autorisées."""

import json

import numpy as np
import pytest

from conftest import IFC_DUPLEX, PARAMS
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m1_geometrie import ifc_outils as io
from twinhyp.m1_geometrie import voxels as V


def cube(x0, y0, z0, c):
    s = np.array([[x0 + dx * c, y0 + dy * c, z0 + dz * c] for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)], float)
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return io.Maillage(s, f)


def test_parite_rayon_vertical_dans_un_cube():
    tri = V.triangles(cube(0, 0, 1, 2))
    z_dedans, z_dehors = V.impacts_verticaux(np.array([[0.7, 1.3], [5.0, 5.0]]), tri)
    assert V.intervalles(z_dedans) == [(1.0, 3.0)]
    assert V.intervalles(z_dehors) == []


def test_categories_de_materiaux():
    assert V.categorie_materiau("Plasterboard") == "plaque_de_platre"
    assert V.categorie_materiau("Masonry - Concrete Block") == "mur_porteur"
    assert V.categorie_materiau("Concrete - Cast In Situ") == "mur_beton"
    assert V.categorie_materiau("Misc. Air Layers - Air Space") is None
    assert V.categorie_materiau("Metal - Stud Layer") is None


@pytest.fixture(scope="module")
def resultat():
    geo = construire_geometrie(IFC_DUPLEX)
    params = json.loads(PARAMS.read_text(encoding="utf-8"))
    return geo, V.calculer(io.ouvrir(IFC_DUPLEX), geo, params)


@pytest.mark.integration
def test_grille_iwcmc_16_x_34(resultat):
    _, (grille, vox, _, resume) = resultat
    assert grille.forme[:2] == (16, 34)  # [IWCMC] : domaine 16 x 34 voxels de 0,5 m
    assert vox["materiau"].shape == grille.forme and vox["materiau"].dtype == np.uint8
    assert 0 < resume["part_plaque_de_platre"] < 1
    assert resume["voxels_libres"] + resume["voxels_obstacles"] == resume["voxels"]


@pytest.mark.integration
def test_cages_escalier_libres_a_travers_le_plancher(resultat):
    """La cage A105 (double hauteur) traverse le plancher du Level 2 : voxels libres à z ≈ 2,9 m."""
    geo, (grille, vox, _, _) = resultat
    a105 = next(e for e in geo["espaces"] if e["nom"] == "A105")
    cx, cy = np.mean(a105["polygone_xy"], axis=0)
    i, j = int((cx - grille.origine[0]) // grille.pas[0]), int((cy - grille.origine[1]) // grille.pas[1])
    k = int((2.9 - grille.origine[2]) // grille.pas[2])
    assert vox["libre"][i, j, k] == 1
    assert vox["libre"][grille.forme[0] // 2, grille.forme[1] // 2, k] == 0  # plancher ailleurs


@pytest.mark.integration
def test_positions_au_plafond_par_niveau(resultat):
    geo, (_, _, A, resume) = resultat
    assert resume["positions_par_niveau"]["Level 1"] > 0 and resume["positions_par_niveau"]["Level 2"] > 0
    niveaux = {n["globalId"]: n["altitude_m"] for n in geo["niveaux"]}
    assert all(a["xyz"][2] > niveaux[a["niveau_globalId"]] + 2.0 for a in A)  # au plafond, pas au sol
    occupables = {e["globalId"] for e in geo["espaces"] if e["occupable"]}
    assert all(a["espace_globalId"] in occupables for a in A)
