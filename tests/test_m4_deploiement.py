"""Étape 8 : déploiement SSI (MILP de couverture, déclencheurs, caméras, zones, F3–F6)."""

import json
import math

import numpy as np
import pytest
from rdflib import Graph
from shapely.geometry import Polygon

from conftest import DONNEES, IFC_DUPLEX, PARAMS
from twinhyp.io_schemas import charger_validateur, erreurs_document, rapport_shacl
from twinhyp.m1_geometrie import FICHIER_VOXELS, ajouter_voxels, construire_geometrie
from twinhyp.m2_graphe import FORMES_MAISON, ontologie
from twinhyp.m2_graphe.construction import construire
from twinhyp.m3_iwcmc.radio import Environnement
from twinhyp.m4_deploiement import deployer
from twinhyp.m4_deploiement import graphe as kg_m4
from twinhyp.m4_deploiement.milp import couverture_ensemble, resoudre
from twinhyp.m4_deploiement.placement import geodesique


# Unitaires ---------------------------------------------------------------------
def test_couverture_ensemble_optimale():
    # 4 éléments en cycle, chaque candidat en couvre 2 : l'optimum est 2
    s = couverture_ensemble(4, [[0, 3], [0, 1], [1, 2], [2, 3]])
    assert s.statut == "Optimal" and s.objectif == 2 and s.gap_relatif == 0


def test_milp_infaisable_signale():
    s = resoudre([1.0], [([0], [1.0], 2, None)])  # x ≤ 1 et x ≥ 2
    assert s.statut != "Optimal"


def test_distance_de_cheminement_contourne_le_mur():
    L = Polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 4), (0, 4)])
    d = geodesique(L, (3.5, 0.5), (0.5, 3.5))
    assert d == pytest.approx(math.dist((3.5, 0.5), (1, 1)) + math.dist((1, 1), (0.5, 3.5)), abs=0.02)
    assert d > math.dist((3.5, 0.5), (0.5, 3.5))  # plus long que la distance euclidienne


# Duplex ------------------------------------------------------------------------
@pytest.fixture(scope="module")
def deploiement(tmp_path_factory):
    dossier = tmp_path_factory.mktemp("m4")
    params = json.loads(PARAMS.read_text(encoding="utf-8"))
    geo = construire_geometrie(IFC_DUPLEX, params)
    ajouter_voxels(IFC_DUPLEX, geo, params, dossier / FICHIER_VOXELS)
    env = Environnement.charger(dossier / FICHIER_VOXELS)
    eqs, zones, chemins, sous = deployer(geo, params, env)
    return geo, params, eqs, zones, chemins, sous, dossier


@pytest.mark.integration
def test_un_detecteur_dans_chaque_espace_occupable(deploiement):
    geo, _, eqs, _, _, sous, _ = deploiement
    occupables = {e["globalId"] for e in geo["espaces"] if e["occupable"]}
    avec_detecteur = {e["espace_globalId"] for e in eqs if e["type"] == "SmokeDetector"}
    assert avec_detecteur == occupables
    assert sous["detecteurs"]["statut"] == "Optimal" and not sous["detecteurs"]["cellules_sans_candidat"]


@pytest.mark.integration
def test_chaque_sortie_a_un_declencheur_a_distance_reglementaire(deploiement):
    geo, params, eqs, *_ = deploiement
    sorties = {p["globalId"] for p in geo["portes"] if p["sortie"]}
    servies = {s for e in eqs if e["type"] == "ManualCallPoint" for s, d in e["sorties_servies"]
               if d <= params["declencheur_distance_max_m"]}
    assert servies == sorties


@pytest.mark.integration
def test_chemins_entierement_vus_par_les_cameras(deploiement):
    _, params, eqs, _, chemins, sous, _ = deploiement
    assert all(c["couverture"] >= params["couverture_video_min"] for c in chemins.values())
    assert sous["cameras"]["statut"] == "Optimal" and sous["cameras"]["cellules_invisibles"] == 0
    assert all(-1e-9 <= c["full_view"] <= 1 for c in chemins.values())


@pytest.mark.integration
def test_zones_par_niveau_et_logement(deploiement):
    geo, _, eqs, zones, *_ = deploiement
    niveau = {e["globalId"]: e["niveau_globalId"] for e in geo["espaces"]}
    for e in eqs:
        if e["type"] != "Camera":
            assert zones[e["zone_detection"]] == niveau[e["espace_globalId"]]  # F6 : un seul niveau


@pytest.mark.integration
def test_reseau_connexe(deploiement):
    *_, sous, _ = deploiement
    assert sous["reseau"]["principal"]["composantes"] == 1


@pytest.mark.integration
def test_graphe_complet_conforme_f1_a_f8(deploiement):
    geo, params, eqs, zones, chemins, _, dossier = deploiement
    g = construire(geo, params, "duplex")
    kg_m4.ecrire(g, geo, eqs, zones, chemins)
    kg, onto = dossier / "kg.ttl", dossier / "ontology.ttl"
    g.serialize(kg, format="turtle")
    ontologie(DONNEES / "ontologie" / "ssi_socle.ttl").serialize(onto, format="turtle")
    ok, texte = rapport_shacl(kg, [DONNEES / "ontologie" / "formes_publiques.ttl", FORMES_MAISON], onto)
    assert ok, texte[:3000]
    # cas négatif : sans détecteur dans un espace, F3 échoue
    g2 = Graph() + g
    det = next(s for s, _, o in g2.triples((None, None, None)) if str(s).endswith("DF-01"))
    g2.remove((det, None, None))
    g2.serialize(kg, format="turtle")
    ok2, texte2 = rapport_shacl(kg, [DONNEES / "ontologie" / "formes_publiques.ttl", FORMES_MAISON], onto)
    assert not ok2 and "F3" in texte2


@pytest.mark.integration
def test_equipements_conformes_au_schema(deploiement):
    _, _, eqs, *_ = deploiement
    v = charger_validateur(DONNEES / "schemas", "devices.schema.json")
    doc = {"parametres": "parametres.json", "objectif": {"valeur": len(eqs), "statut_solveur": "Optimal",
                                                         "temps_s": 1, "mode": "3D"},
           "equipements": [{k: x for k, x in e.items() if k != "cellules_vues"} for e in eqs]}
    assert not erreurs_document(v, doc)


@pytest.mark.integration
def test_un_declencheur_par_sortie_par_defaut(deploiement):
    geo, _, eqs, *_ = deploiement
    sorties = [p["globalId"] for p in geo["portes"] if p["sortie"]]
    dm = [e for e in eqs if e["type"] == "ManualCallPoint"]
    assert len(dm) == len(sorties) and all(len(e["sorties_servies"]) == 1 for e in dm)


@pytest.mark.integration
def test_full_view_max_min_avec_une_camera_de_plus(deploiement):
    # à N* caméras le minimum par chemin est 0 (prouvé par le MILP) ; une caméra de plus suffit à le rendre > 0
    from twinhyp.m4_deploiement import placement
    geo, params, _, _, _, sous, dossier = deploiement
    env = Environnement.charger(dossier / FICHIER_VOXELS)
    chem = placement.chemins(geo, env, float(params["pas_grille_m"]) / 2)
    eqs, res, par = placement.cameras(geo, {**params, "cameras_supplementaires_full_view": 1}, env, chem)
    assert len(eqs) == sous["cameras"]["valeur"] + 1
    assert res["full_view_min_par_chemin"] > 0 and min(c["full_view"] for c in par.values()) > 0
    assert all(c["couverture"] >= params["couverture_video_min"] for c in par.values())
