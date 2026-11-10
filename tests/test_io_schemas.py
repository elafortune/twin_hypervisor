"""Tests unitaires de la validation des sorties : on vérifie que le contrôle
détecte bien les sorties fausses (un validateur qui accepte tout ne sert à rien)."""

import pytest

from conftest import DONNEES
from twinhyp.io_schemas import (SortieNonConforme, ecrire_json, ecrire_jsonl, erreurs_sortie_json,
                                verifier_sortie)

SCHEMAS = DONNEES / "schemas"
GID = "0BTBFw6f90Nfh9rP1dl_39"


def test_geometry_valide(tmp_path):
    chemin = tmp_path / "geometry.json"
    ecrire_json(chemin, {"niveaux": [{"globalId": GID, "nom": "Level 1", "altitude_m": 0.0}],
                         "espaces": [], "portes": [], "liaisons": [], "anomalies": []})
    assert erreurs_sortie_json(chemin, SCHEMAS) == []


def test_geometry_champ_manquant_detecte(tmp_path):
    chemin = tmp_path / "geometry.json"
    ecrire_json(chemin, {"niveaux": [{"globalId": GID, "nom": "Level 1"}],
                         "espaces": [], "portes": [], "liaisons": []})
    erreurs = erreurs_sortie_json(chemin, SCHEMAS)
    assert any("anomalies" in e for e in erreurs)
    assert any("altitude_m" in e for e in erreurs)


def test_type_de_liaison_hors_enumeration(tmp_path):
    chemin = tmp_path / "geometry.json"
    ecrire_json(chemin, {"niveaux": [], "espaces": [], "portes": [], "anomalies": [],
                         "liaisons": [{"de": "a", "vers": "b", "type": "fenetre"}]})
    with pytest.raises(SortieNonConforme):
        verifier_sortie(chemin, SCHEMAS)


def test_jsonl_valide_ligne_par_ligne(tmp_path):
    chemin = tmp_path / "evacuation_dynamique.jsonl"
    bonne = {"t_s": 10, "espace_globalId": GID, "strategie": 2, "route": [GID], "sortie_globalId": GID}
    mauvaise = {"t_s": 20, "espace_globalId": GID, "strategie": 3, "route": None, "sortie_globalId": None}
    ecrire_jsonl(chemin, [bonne, mauvaise])
    erreurs = erreurs_sortie_json(chemin, SCHEMAS)
    assert len(erreurs) == 1 and erreurs[0].startswith("ligne 2")


def test_format_date_heure_verifie(tmp_path):
    chemin = tmp_path / "audit_log.jsonl"
    ecrire_jsonl(chemin, [{"horodatage": "hier", "demande_id": "D1", "action": "x",
                           "decision": "acceptee", "justification": "", "formes_violees": []}])
    assert erreurs_sortie_json(chemin, SCHEMAS)


def test_sortie_absente(tmp_path):
    with pytest.raises(SortieNonConforme):
        verifier_sortie(tmp_path / "devices.json", SCHEMAS)
