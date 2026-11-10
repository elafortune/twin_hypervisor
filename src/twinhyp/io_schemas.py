"""Lecture / écriture des sorties et validation contre leurs contrats.

- JSON et JSONL : JSON Schema draft 2020-12 (`data/schemas/`) ; un JSONL est
  validé ligne par ligne.
- Turtle (`kg.ttl`) : formes SHACL, avec l'ontologie chargée comme graphe
  d'ontologie et l'inférence RDFS (nécessaire à `rdfs:subClassOf*` dans F3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

# Sortie -> schéma qui la décrit.
SCHEMA_DE = {
    "geometry.json": "geometry.schema.json",
    "pareto.json": "pareto.schema.json",
    "devices.json": "devices.schema.json",
    "evacuation_dynamique.jsonl": "evacuation_dynamique.schema.json",
    "answers.jsonl": "answers.schema.json",
    "audit_log.jsonl": "audit_log.schema.json",
}


class SortieNonConforme(ValueError):
    """Une sortie ne respecte pas son contrat (schéma JSON ou formes SHACL)."""


# Écriture ------------------------------------------------------------------
def ecrire_json(chemin: Path, donnees: Any) -> None:
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ecrire_jsonl(chemin: Path, lignes: Iterable[dict]) -> None:
    with chemin.open("w", encoding="utf-8", newline="\n") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def lire_jsonl(chemin: Path) -> list[dict]:
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]


# Validation JSON -------------------------------------------------------------
def charger_validateur(dossier_schemas: Path, nom_schema: str) -> Draft202012Validator:
    schema = json.loads((dossier_schemas / nom_schema).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def erreurs_document(validateur: Draft202012Validator, document: Any, prefixe: str = "") -> list[str]:
    erreurs = []
    for e in sorted(validateur.iter_errors(document), key=lambda e: list(map(str, e.absolute_path))):
        chemin = "/".join(str(p) for p in e.absolute_path) or "(racine)"
        erreurs.append(f"{prefixe}{chemin} : {e.message}")
    return erreurs


def erreurs_sortie_json(chemin: Path, dossier_schemas: Path) -> list[str]:
    """Liste toutes les violations du schéma pour une sortie JSON ou JSONL."""
    validateur = charger_validateur(dossier_schemas, SCHEMA_DE[chemin.name])
    texte = chemin.read_text(encoding="utf-8")
    if chemin.suffix == ".jsonl":
        erreurs = []
        for num, ligne in enumerate(texte.splitlines(), start=1):
            if not ligne.strip():
                continue
            try:
                document = json.loads(ligne)
            except json.JSONDecodeError as exc:
                erreurs.append(f"ligne {num} : JSON invalide ({exc})")
                continue
            erreurs += erreurs_document(validateur, document, prefixe=f"ligne {num} : ")
        return erreurs
    document = json.loads(texte)
    # pareto.json regroupe les 4 scénarios : liste d'objets décrits chacun par le schéma.
    if isinstance(document, list):
        erreurs = []
        for i, element in enumerate(document):
            erreurs += erreurs_document(validateur, element, prefixe=f"[{i}] ")
        return erreurs
    return erreurs_document(validateur, document)


# Validation SHACL ------------------------------------------------------------
# Formes portant sur les équipements SSI : sans objet tant que M4 n'a pas placé d'équipement.
FORMES_EQUIPEMENTS = ("F3_Detection", "F4_Declencheur", "F5_Video", "F6_Zone", "F6_ZoneNiveau")


def formes_differees(dossier_sorties: Path) -> tuple[str, ...]:
    """F3–F6 sont différées si devices.json est absent ou non calculé (chaîne lancée avant M4)."""
    devices = dossier_sorties / "devices.json"
    if not devices.is_file():
        return FORMES_EQUIPEMENTS
    statut = json.loads(devices.read_text(encoding="utf-8")).get("objectif", {}).get("statut_solveur")
    return FORMES_EQUIPEMENTS if statut == "non_calcule" else ()


def graphe_formes(formes: Path | list[Path], differees: Iterable[str] = ()):
    """Charge les formes ; une forme différée perd sa cible (elle ne s'applique alors à rien)."""
    from rdflib import Graph, URIRef
    from rdflib.namespace import SH

    g = Graph()
    for f in ([formes] if isinstance(formes, Path) else formes):
        g.parse(f, format="turtle")
    noms = set(differees)
    for forme in set(g.subjects()):
        if isinstance(forme, URIRef) and forme.split("#")[-1] in noms:
            for cible in (SH.targetClass, SH.targetNode, SH.targetSubjectsOf, SH.targetObjectsOf):
                g.remove((forme, cible, None))
    return g


def rapport_shacl(chemin_kg: Path, formes: Path | list[Path], ontologie: Path,
                  differees: Iterable[str] = ()) -> tuple[bool, str]:
    from pyshacl import validate

    conforme, _, texte = validate(
        data_graph=str(chemin_kg),
        shacl_graph=graphe_formes(formes, differees),
        ont_graph=str(ontologie),
        inference="rdfs",
        abort_on_first=False,
        allow_warnings=True,
    )
    return bool(conforme), texte


def formes_violees_graphe(data, formes: Path | list[Path], ontologie: Path) -> tuple[list[str], str]:
    """Valide un graphe rdflib EN MÉMOIRE (copie modifiée par l'agent) ; renvoie les noms des NodeShapes
    ayant au moins une violation (sévérité sh:Violation) et le rapport texte."""
    from pyshacl import validate
    from rdflib import Graph
    from rdflib.namespace import RDF, SH

    formes_g = graphe_formes(formes)
    _, resultats, texte = validate(data_graph=data, shacl_graph=formes_g, ont_graph=Graph().parse(ontologie),
                                   inference="rdfs", abort_on_first=False, allow_warnings=True, inplace=False)
    parent = {}
    for s, p, o in formes_g.triples((None, None, None)):
        if p in (SH.property, SH.sparql):
            parent[o] = s
    noms = set()
    for r in resultats.subjects(RDF.type, SH.ValidationResult):
        if resultats.value(r, SH.resultSeverity) != SH.Violation:
            continue
        forme = resultats.value(r, SH.sourceShape)
        while forme in parent:
            forme = parent[forme]
        noms.add(str(forme).split("#")[-1])
    return sorted(noms), texte


# Point d'entrée commun -------------------------------------------------------
def verifier_sortie(chemin: Path, dossier_schemas: Path, formes: Path | list[Path] | None = None,
                    ontologie: Path | None = None, differees: Iterable[str] | None = None) -> None:
    """`differees` : formes SHACL à ne pas appliquer ; None = déduit de devices.json (commande valider)."""
    if not chemin.is_file():
        raise SortieNonConforme(f"{chemin.name} : fichier absent")
    if chemin.name in SCHEMA_DE:
        erreurs = erreurs_sortie_json(chemin, dossier_schemas)
        if erreurs:
            raise SortieNonConforme(f"{chemin.name} :\n  " + "\n  ".join(erreurs[:20]))
    elif chemin.name == "kg.ttl" and formes is not None and ontologie is not None:
        differees = formes_differees(chemin.parent) if differees is None else tuple(differees)
        conforme, texte = rapport_shacl(chemin, formes, ontologie, differees)
        if not conforme:
            note = " (F3–F6 différées : M4 non calculé)" if differees else ""
            raise SortieNonConforme(f"kg.ttl ne respecte pas les formes SHACL{note} :\n{texte}")
