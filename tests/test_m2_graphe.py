"""Étape 4 : ontologie, graphe statique, formes SHACL, requêtes SPARQL Q01–Q14."""

import json
from pathlib import Path

import pytest
from rdflib import RDF, RDFS, BNode, Graph, Literal

from conftest import DONNEES, IFC_DUPLEX, PARAMS
from twinhyp.io_schemas import FORMES_EQUIPEMENTS, rapport_shacl
from twinhyp.m1_geometrie import construire_geometrie
from twinhyp.m2_graphe import FORMES_MAISON, ontologie
from twinhyp.m2_graphe import requetes as R
from twinhyp.m2_graphe.construction import BOT, INST, SSI, construire, iri, logements

FORMES = [DONNEES / "ontologie" / "formes_publiques.ttl", FORMES_MAISON]


@pytest.fixture(scope="module")
def geo():
    return construire_geometrie(IFC_DUPLEX)


@pytest.fixture(scope="module")
def kg(geo):
    return construire(geo, json.loads(Path(PARAMS).read_text(encoding="utf-8")), "duplex")


@pytest.fixture(scope="module")
def onto(tmp_path_factory):
    chemin = tmp_path_factory.mktemp("onto") / "ontology.ttl"
    ontologie(DONNEES / "ontologie" / "ssi_socle.ttl").serialize(chemin, format="turtle")
    return chemin


def valider(g: Graph, onto: Path, tmp_path: Path, differees=FORMES_EQUIPEMENTS):
    chemin = tmp_path / "kg.ttl"
    g.serialize(chemin, format="turtle")
    return rapport_shacl(chemin, FORMES, onto, differees)


def nom(g: Graph, gids):
    return sorted(str(g.value(iri("space", x), RDFS.label)) for x in gids)


# Ontologie ---------------------------------------------------------------------
def test_extension_ne_renomme_pas_le_socle(onto):
    socle = Graph().parse(DONNEES / "ontologie" / "ssi_socle.ttl")
    complet = Graph().parse(onto)
    sans_noeud_anonyme = [t for t in socle if not any(isinstance(x, BNode) for x in t)]
    assert all(t in complet for t in sans_noeud_anonyme)  # le socle est inclus tel quel
    assert len(complet) > len(socle)


def test_exemple_du_kit_reste_conforme(onto, tmp_path):
    """Nos formes maison ne rejettent pas l'exemple minimal du kit."""
    ok, texte = valider(Graph().parse(DONNEES / "ontologie" / "exemple_minimal.ttl"), onto, tmp_path, ())
    assert ok, texte


# Graphe ------------------------------------------------------------------------
def test_graphe_conforme_avant_m4(kg, onto, tmp_path):
    ok, texte = valider(kg, onto, tmp_path)
    assert ok, texte


def test_f3_f4_echouent_sans_equipement(kg, onto, tmp_path):
    """Sans différer F3–F6, le graphe statique est (normalement) non conforme : pas de détecteur."""
    ok, texte = valider(kg, onto, tmp_path, ())
    assert not ok and "F3" in texte and "F4" in texte


def test_shacl_detecte_un_espace_sans_niveau(kg, onto, tmp_path):
    g = Graph() + kg
    espace = next(g.subjects(RDF.type, BOT.Space))
    g.remove((None, BOT.hasSpace, espace))
    ok, texte = valider(g, onto, tmp_path)
    assert not ok and "F1" in texte


def test_shacl_avertit_d_une_connexion_a_sens_unique(kg, onto, tmp_path):
    g = Graph() + kg
    a, b = next(g.subject_objects(SSI.isConnectedTo))
    g.remove((b, SSI.isConnectedTo, a))
    ok, texte = valider(g, onto, tmp_path)
    assert ok and "M1" in texte  # avertissement (sh:Warning), pas violation


def test_distance_nulle_rejetee(kg, onto, tmp_path):
    g = Graph() + kg
    d = next(g.subjects(RDF.type, SSI.EvacuationDistance))
    g.set((d, SSI.hasDistance, Literal(0.0)))
    ok, texte = valider(g, onto, tmp_path)
    assert not ok and "F7" in texte


def test_deux_logements_par_composante_connexe(geo):
    noms = {e["globalId"]: e["nom"] for e in geo["espaces"]}
    comps = logements(geo)
    assert len(comps) == 2
    for c in comps:  # recoupement avec le préfixe des noms (Q05 : « logement A (préfixe A) »)
        assert len({noms[g][0] for g in c}) == 1


def test_parametres_lus_dans_le_fichier(kg):
    p = INST["parameters"]
    params = json.loads(Path(PARAMS).read_text(encoding="utf-8"))
    assert float(kg.value(p, SSI.maxCallPointDistance)) == params["declencheur_distance_max_m"]
    assert float(kg.value(p, SSI.minCameraCoverage)) == params["couverture_video_min"]


# Questions par SPARQL ------------------------------------------------------------
def test_q01_q14_par_sparql(kg):
    r = {q: R.repondre(kg, q)[0] for q in ["Q01", "Q03", "Q04", "Q05", "Q06", "Q09", "Q10", "Q11", "Q12", "Q13", "Q14"]}
    assert len(r["Q01"]) == 10
    assert nom(kg, r["Q03"]) == ["A101", "A102", "B101", "B102"]
    assert nom(kg, r["Q04"]) == ["A102", "A103", "A105"]
    assert r["Q05"] == pytest.approx(138.16)
    assert nom(kg, r["Q06"]) == ["A202", "A203", "A205", "B202", "B202", "B205"]
    assert nom(kg, r["Q09"]) == ["A105", "B105"]
    assert r["Q10"] == pytest.approx(134.53)
    assert nom(kg, r["Q11"]) == ["A102", "B102"]
    assert nom(kg, r["Q12"]) == ["A204", "B204"]
    assert r["Q13"] == []
    assert len(r["Q14"]) == 4
    assert len(R.repondre(kg, "Q02")[0]) == 4


def test_q13_detecterait_un_passage(kg):
    """Garde-fou : la requête Q13 trouve bien une liaison A–B si on en ajoute une."""
    g = Graph() + kg
    a, b = iri("space", R.espace(g, "A102")[0]), iri("space", R.espace(g, "B102")[0])
    d = INST["distance/test"]
    g.add((d, RDF.type, SSI.EvacuationDistance))
    g.add((d, SSI["from"], a))
    g.add((d, SSI.to, b))
    assert len(R.repondre(g, "Q13")[0]) == 1


def test_q07_q08_par_le_graphe(kg):
    r = R.chemin(kg, R.espace(kg, "A202")[0], R.espace(kg, "A101")[0])
    assert r["largeur_min_porte_m"] == pytest.approx(0.864)
    b = R.chemin(kg, R.espace(kg, "B202", "Bedroom 2")[0], R.espace(kg, "B101")[0])
    assert nom(kg, b["espaces"][1:]) == ["B101", "B105", "B201"]


def test_nom_ambigu_signale(kg):
    with pytest.raises(ValueError, match="2 espaces"):
        R.espace(kg, "B202")
