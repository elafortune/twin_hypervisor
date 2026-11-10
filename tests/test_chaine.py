"""Tests d'intégration : la commande unique produit les 8 sorties conformes."""

import json

import pytest

from conftest import IFC_DUPLEX, OBS, PARAMS
from twinhyp.cli import main
from twinhyp.contexte import SORTIES
from twinhyp.pipeline import executer

pytestmark = pytest.mark.integration


def test_commande_unique_produit_les_8_sorties(tmp_path):
    out = tmp_path / "sorties"
    code = main(["run", "--ifc", str(IFC_DUPLEX), "--params", str(PARAMS), "--obs", str(OBS),
                 "--out", str(out)])
    assert code == 0
    for nom in SORTIES.values():
        assert (out / nom).is_file(), nom
    trace = json.loads((out / "execution.json").read_text(encoding="utf-8"))
    assert list(trace["etapes"]) == ["m1", "m2", "m3", "m4", "m5", "m6"]
    assert main(["valider", "--out", str(out)]) == 0


def test_etapes_partielles_dans_l_ordre(ctx):
    trace = executer(ctx, ["m2", "m1"])
    assert list(trace["etapes"]) == ["m1", "m2"]


def test_etape_inconnue_refusee(ctx):
    with pytest.raises(ValueError):
        executer(ctx, ["m7"])


def test_fichier_absent_code_erreur(tmp_path):
    code = main(["run", "--ifc", str(tmp_path / "absent.ifc"), "--params", str(PARAMS),
                 "--obs", str(OBS), "--out", str(tmp_path / "o")])
    assert code == 2
