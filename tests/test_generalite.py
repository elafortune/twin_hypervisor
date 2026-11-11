"""Étape 10 : règles ajoutées pour un 2e IFC (bureaux NIBS) et scénario synthétique — sans dépendre d'un IFC."""

from twinhyp import scenario
from twinhyp.m1_geometrie import connectivite


def _geo():
    esp = lambda g, nom: {"globalId": g, "nom": nom, "nom_long": nom, "occupable": True,
                          "polygone_xy": [[0, 0], [4, 0], [4, 4], [0, 4]]}
    return {"espaces": [esp("A", "A"), esp("B", "B"), esp("G", "ELEV")],
            "liaisons": [{"de": "A", "vers": "B", "type": "porte"}],
            "portes": [{"globalId": "P", "sortie": True, "espaces": ["A"]}]}


def test_espace_isole_requalifie_non_occupable():
    geo = _geo()
    anomalies = connectivite.controler_evacuabilite(geo)
    assert [a["regle"] for a in anomalies] == ["espace_isole"]
    assert not next(e for e in geo["espaces"] if e["globalId"] == "G")["occupable"]


def test_espace_relie_sans_sortie_reste_bloquant():
    geo = _geo()
    geo["portes"] = []
    assert {a["regle"] for a in connectivite.controler_evacuabilite(geo)} == {"espace_isole", "espace_evacuable"}


def test_scenario_synthetique_retard_par_liaison():
    geo = _geo()
    lignes = scenario.generer(geo, "A", {"n_occupes": 1})
    alarme = lambda g: min(l["t_s"] for l in lignes if l["espace_globalId"] == g and l["type"] == "SmokeAlarm"
                           and l["valeur"] > 0.0328)
    assert alarme("A") < alarme("B")  # B est une liaison plus loin
    assert all(l["valeur"] == 0 for l in lignes if l["espace_globalId"] == "G" and l["type"] in ("SmokeAlarm", "COSensor"))
    assert {l["type"] for l in lignes} == {"SmokeAlarm", "TemperatureSensor", "COSensor", "Camera"}
