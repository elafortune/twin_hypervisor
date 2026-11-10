"""Règles d'anomalie : chaque règle est testée sur un cas synthétique (elle doit
détecter, et ne pas détecter un cas sain), puis sur le duplex."""

import pytest

from conftest import IFC_DUPLEX
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m1_geometrie.anomalies import (dimensions_escalier, niveau_attendu, noms_dupliques,
                                             rattachement_niveau)

NIVEAUX = [{"globalId": "N0", "nom": "RDC", "altitude_m": 0.0},
           {"globalId": "N1", "nom": "R+1", "altitude_m": 3.0},
           {"globalId": "N2", "nom": "Toit", "altitude_m": 6.0}]


def test_noms_dupliques():
    espaces = [{"globalId": "a", "nom": "X1", "nom_long": "Ch 1"},
               {"globalId": "b", "nom": "X1", "nom_long": "Ch 2"},
               {"globalId": "c", "nom": "X2", "nom_long": "Ch 3"}]
    assert sorted(a["element_globalId"] for a in noms_dupliques(espaces)) == ["a", "b"]


@pytest.mark.parametrize("z, attendu", [(0.02, "N0"), (3.1, "N1"), (2.8, "N1"), (5.0, "N1"), (-1.0, None)])
def test_niveau_attendu(z, attendu):
    n = niveau_attendu(z, NIVEAUX)
    assert (n["globalId"] if n else None) == attendu


def test_rattachement_niveau():
    escaliers = [{"globalId": "s", "nom": "esc", "niveau_globalId": "N2", "z_bas_m": 0.0}]
    sain = [{"globalId": "t", "nom": "esc", "niveau_globalId": "N0", "z_bas_m": 0.0}]
    assert len(rattachement_niveau([], escaliers, NIVEAUX)) == 1
    assert rattachement_niveau([], sain, NIVEAUX) == []


def test_dimensions_escalier_en_pieds():
    esc = {"globalId": "s", "z_bas_m": 0.0, "z_haut_m": 3.0,
           "volees": [{"globalId": "v", "contremarches": 16,
                       "hauteur_marche_declaree": 0.6, "giron_declare": 0.27}]}
    anomalies = dimensions_escalier([esc])
    assert len(anomalies) == 1 and "pieds" in anomalies[0]["description"]


def test_anomalies_du_duplex():
    geo = construire_geometrie(IFC_DUPLEX)
    regles = {a["regle"] for a in geo["anomalies"]}
    assert {"nom_unique", "nom_coherent_proprietes", "fonction_coherente", "booleen_type",
            "rattachement_niveau", "dimensions_escalier"} <= regles
    fonction = [a for a in geo["anomalies"] if a["regle"] == "fonction_coherente"]
    assert [a["element_globalId"] for a in fonction] == ["10mjSDZJj9gPS2PrQaxa4o"]  # B105 « Room »
