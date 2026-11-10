import json

import pytest

from conftest import IFC_DUPLEX
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.visualisation import plan2d, vue3d


@pytest.fixture(scope="module")
def geo():
    return construire_geometrie(IFC_DUPLEX)


def test_plan2d_un_bouton_par_niveau_occupe(geo):
    fig = plan2d.figure_plan(geo)
    labels = [b.label for b in fig.layout.updatemenus[0].buttons]
    assert [l.split(" (")[0] for l in labels] == ["Level 1", "Level 2", "Roof"]
    # chaque bouton rend visible au moins un espace
    for b in fig.layout.updatemenus[0].buttons:
        assert any(b.args[0]["visible"])


def test_plan2d_ecrit_le_html(geo, tmp_path):
    chemin_geo = tmp_path / "geometry.json"
    chemin_geo.write_text(json.dumps(geo), encoding="utf-8")
    html = plan2d.generer(chemin_geo, tmp_path / "figures")
    assert html.is_file() and (tmp_path / "figures" / "plotly.min.js").is_file()


@pytest.mark.integration
def test_vue3d(geo, tmp_path):
    fig = vue3d.figure_3d(IFC_DUPLEX, geo)
    noms = {t.name for t in fig.data}
    assert {"Murs", "Portes", "Escaliers", "Espaces", "Sorties"} <= noms
    boutons = [b.label for b in fig.layout.updatemenus[0].buttons]
    assert boutons[0] == "Tous les niveaux" and len(boutons) >= 3
