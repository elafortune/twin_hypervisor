"""Étape 7 : modèle radio, score, µ-connexité, tri de Pareto (valeurs calculées à la main)."""

import math

import numpy as np
import pytest

from twinhyp.m3_iwcmc import article
from twinhyp.m3_iwcmc.prep_nsga import domine, fronts, meilleur_par_taille
from twinhyp.m3_iwcmc.radio import Environnement, matrices_obstacles, perte_espace_libre
from twinhyp.m3_iwcmc.score import Radio, connectivite, faisable


@pytest.fixture
def couloir():
    """3 voxels de 1 m en ligne : libre | plaque de plâtre | libre."""
    libre = np.array([1, 0, 1], np.uint8).reshape(3, 1, 1)
    materiau = np.array([0, 1, 0], np.uint8).reshape(3, 1, 1)
    return Environnement(np.zeros(3), np.ones(3), libre, materiau,
                         {0: "libre", 1: "plaque_de_platre"}, np.array([[0.5, 0.5, 0.5]]))


def test_perte_calculee_a_la_main(couloir):
    L = [couloir.attenuation_par_voxel("WiFi 2.4GHz", True)]
    V, M = matrices_obstacles(couloir, np.array([[0.5, 0.5, 0.5]]), np.array([[2.5, 0.5, 0.5]]), L)
    assert V[0, 0, 0] == pytest.approx(0.32)          # un voxel obstacle traversé
    assert M[0, 0, 0] == pytest.approx(0.32, abs=0.01)  # 1 m traversé × 0,32 dB/m
    PL = perte_espace_libre(37.15, np.array([[0.5, 0.5, 0.5]]), np.array([[2.5, 0.5, 0.5]]))[0, 0] + V[0, 0, 0]
    assert PL == pytest.approx(37.15 + 20 * math.log10(2) + 0.32, abs=1e-4)


def test_sans_jumeau_tout_en_materiau_le_plus_absorbant(couloir):
    couloir.materiau[1] = 3  # catégorie inconnue de la table -> le plus absorbant
    couloir.categories[3] = "mur_porteur"
    assert couloir.attenuation_par_voxel("WiFi 2.4GHz", True)[1, 0, 0] == pytest.approx(0.22)
    assert couloir.attenuation_par_voxel("WiFi 2.4GHz", False)[1, 0, 0] == pytest.approx(0.32)


def test_score_meilleur_serveur_et_normalisation():
    # 2 équipements, 3 voxels ; v″ = (P_TX − min PL − S_RX) / (P_TX − S_RX)
    r = Radio(PL=np.array([[60.0, 90.0, 80.0], [95.0, 70.0, 100.0]]), PL_AA=np.zeros((2, 2)))
    v = r.v2((0, 1))
    assert v == pytest.approx([(20 - 60 + 65) / 85, (20 - 70 + 65) / 85, (20 - 80 + 65) / 85])
    assert r.f_obj((0, 1)) == pytest.approx(v.sum() + 3)
    m = r.metriques((0,))  # seul l'équipement 0 : voxel 1 (90 dB) non couvert
    assert m["couverture"] == pytest.approx(2 / 3, abs=1e-4)
    v0 = r.v2((0,))
    assert m["qualite_lien_moyenne_dBm"] == pytest.approx(85 * np.clip(v0, 0, None).mean() - 65, abs=0.01)


def test_mu_connexite_graphes_connus():
    n = 4
    complet = Radio(PL=np.zeros((n, 1)), PL_AA=np.full((n, n), 50.0))
    assert connectivite(complet, range(n)) == 3          # K4 : λ = 3
    anneau = np.full((n, n), 200.0)
    for i in range(n):
        anneau[i, (i + 1) % n] = anneau[(i + 1) % n, i] = 50.0
    assert connectivite(Radio(PL=np.zeros((n, 1)), PL_AA=anneau), range(n)) == 2
    assert not faisable(complet, (0, 1, 2), 3)            # Whitney : µ = 3 exige 4 nœuds


def test_lien_unidirectionnel_supprime():
    PL_AA = np.array([[0.0, 50.0], [200.0, 0.0]])           # 0 -> 1 passe, 1 -> 0 non
    assert connectivite(Radio(PL=np.zeros((2, 1)), PL_AA=PL_AA), (0, 1)) == 0


def test_pareto():
    assert domine((2, 10.0), (3, 9.0)) and not domine((2, 10.0), (1, 5.0))
    objs = [(1, 5.0), (2, 9.0), (2, 8.0), (3, 7.0)]
    assert fronts(objs)[0] == [0, 1]
    assert meilleur_par_taille([(1,), (1, 2), (3, 4)], {(1,): 5.0, (1, 2): 9.0, (3, 4): 8.0})[2] == (9.0, (1, 2))


def test_valeurs_article_releves():
    assert article.point(True, 0, 3)["couverture"] >= 0.9    # Q20 de l'article : 3 équipements
    assert article.point(False, 3, 4) is None                 # sans jumeau, µ = 3 : pas de solution à 4


def test_antenne_sous_le_plafond_et_a_cote_d_un_mur():
    """Plafond obstacle en haut ; sous la position, un mur (colonne obstacle) : l'antenne se décale d'un voxel."""
    libre = np.ones((3, 1, 3), np.uint8)
    libre[:, :, 2] = 0          # faux plafond
    libre[1, 0, :] = 0          # mur sous la position
    env = Environnement(np.zeros(3), np.ones(3), libre, 1 - libre, {0: "libre", 1: "plaque_de_platre"},
                        np.array([[1.5, 0.5, 2.6]]))
    a = env.antennes()[0]
    assert a[2] == pytest.approx(1.5) and a[0] in (0.5, 2.5)
