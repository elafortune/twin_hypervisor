"""Tests de conformité du kit lui-même : si l'un échoue, l'environnement est faux."""

import json

import pytest
from jsonschema import Draft202012Validator

from conftest import DONNEES
from twinhyp.io_schemas import SCHEMA_DE, rapport_shacl


@pytest.mark.parametrize("nom_schema", sorted(SCHEMA_DE.values()))
def test_schemas_du_kit_sont_valides(nom_schema):
    schema = json.loads((DONNEES / "schemas" / nom_schema).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_exemple_minimal_conforme_aux_formes_publiques():
    """Équivalent de la vérification du LISEZMOI (pyshacl ... -> Conforms: True)."""
    onto = DONNEES / "ontologie"
    conforme, texte = rapport_shacl(onto / "exemple_minimal.ttl", onto / "formes_publiques.ttl",
                                    onto / "ssi_socle.ttl")
    assert conforme, texte
