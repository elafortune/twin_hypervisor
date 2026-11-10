"""Interface en ligne de commande.

    python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc \
        --params data/parametres.json --obs data/observations.csv --out sorties/

    python -m twinhyp run ... --etapes m1,m2     # relancer une partie de la chaîne
    python -m twinhyp valider --out sorties/     # revalider des sorties existantes
    python -m twinhyp questions --out sorties/   # réponses Q01–Q14 par SPARQL
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from twinhyp.contexte import DONNEES_PAR_DEFAUT, SORTIES
from twinhyp.io_schemas import SortieNonConforme, formes_differees, verifier_sortie


def construire_parseur() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="twinhyp", description="Du BIM au SSI neuro-symbolique")
    sous = p.add_subparsers(dest="commande", required=True)

    run = sous.add_parser("run", help="rejouer la chaîne complète (ou certaines étapes)")
    run.add_argument("--ifc", required=True, type=Path, help="maquette IFC")
    run.add_argument("--params", required=True, type=Path, help="parametres.json")
    run.add_argument("--obs", required=True, type=Path, help="observations.csv")
    run.add_argument("--out", required=True, type=Path, help="dossier de sortie")
    run.add_argument("--etapes", default="m1,m2,m3,m4,m5,m6", help="ex. m1,m2 (défaut : toutes)")
    run.add_argument("--donnees", type=Path, default=DONNEES_PAR_DEFAUT,
                     help="dossier contenant schemas/ et ontologie/")
    run.add_argument("--questions", type=Path, help="questions.json (défaut : données du kit)")
    run.add_argument("--demandes", type=Path, help="demandes_modification.json (défaut : données du kit)")
    run.add_argument("--graine", type=int, default=0, help="graine aléatoire (reproductibilité)")

    val = sous.add_parser("valider", help="valider des sorties existantes contre les contrats")
    val.add_argument("--out", required=True, type=Path)
    val.add_argument("--donnees", type=Path, default=DONNEES_PAR_DEFAUT)

    vis = sous.add_parser("visualiser", help="plan 2D et vue 3D interactifs (HTML) dans <out>/figures/")
    vis.add_argument("--out", required=True, type=Path, help="dossier de sortie d'un run")
    vis.add_argument("--ifc", type=Path, help="IFC pour la vue 3D (défaut : celui de geometry.json)")
    vis.add_argument("--sans-3d", action="store_true", help="plan 2D seulement")
    qst = sous.add_parser("questions", help="réponses Q01–Q14 obtenues par SPARQL sur <out>/kg.ttl")
    qst.add_argument("--out", required=True, type=Path)
    qst.add_argument("--sparql", action="store_true", help="afficher aussi les requêtes")
    return p


def commande_questions(args: argparse.Namespace) -> int:
    from rdflib import Graph, RDFS

    from twinhyp.m2_graphe import requetes as R
    from twinhyp.m2_graphe.construction import SSI

    g = Graph().parse(args.out / SORTIES["kg"], format="turtle")
    libelle = {str(gid): f"{lab}" + (f" ({g.value(s, SSI.longName)})" if g.value(s, SSI.longName) else "")
               for s, gid in g.subject_objects(SSI.ifcGlobalId) for lab in [g.value(s, RDFS.label)]}

    def afficher(qid, reponse, requetes):
        if isinstance(reponse, list):
            texte = ", ".join(f"{libelle.get(x, x)} [{x}]" for x in reponse) or "∅ (aucun)"
        else:
            texte = str(reponse)
        print(f"{qid} : {texte}")
        if args.sparql:
            for r in requetes:
                print("    " + r.replace("\n", "\n    "))

    for qid in ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06"]:
        afficher(qid, *R.repondre(g, qid))
    q07 = R.chemin(g, R.espace(g, "A202")[0], R.espace(g, "A101")[0])
    afficher("Q07", q07["largeur_min_porte_m"], q07["requetes"])
    q08 = R.chemin(g, R.espace(g, "B202", "Bedroom 2")[0], R.espace(g, "B101")[0])
    afficher("Q08", q08["espaces"][1:], q08["requetes"])
    for qid in ["Q09", "Q10", "Q11", "Q12", "Q13", "Q14"]:
        afficher(qid, *R.repondre(g, qid))
    return 0


def commande_visualiser(args: argparse.Namespace) -> int:
    import json

    from twinhyp.visualisation import plan2d, vue3d

    geo = args.out / SORTIES["geometry"]
    if not geo.is_file():
        raise FileNotFoundError(f"{geo} absent : lancer d'abord `run --etapes m1`")
    dossier = args.out / "figures"
    print(f"Plan 2D : {plan2d.generer(geo, dossier).resolve()}")
    if not args.sans_3d:
        ifc = args.ifc or Path(json.loads(geo.read_text(encoding="utf-8"))["source"]["ifc"])
        chemin = vue3d.generer(ifc, dossier, geo, args.out / SORTIES["devices"])
        print(f"Vue 3D  : {chemin.resolve()}")
    return 0


def commande_run(args: argparse.Namespace) -> int:
    from twinhyp.contexte import Contexte
    from twinhyp.pipeline import executer

    ctx = Contexte(ifc=args.ifc, params_chemin=args.params, obs=args.obs, sortie=args.out,
                   donnees=args.donnees, questions=args.questions, demandes=args.demandes,
                   graine=args.graine)
    executer(ctx, [e.strip() for e in args.etapes.split(",") if e.strip()])
    return 0


def commande_valider(args: argparse.Namespace) -> int:
    schemas = args.donnees / "schemas"
    formes = [args.donnees / "ontologie" / "formes_publiques.ttl",
              Path(__file__).parent / "m2_graphe" / "formes_maison.ttl"]
    ontologie = args.out / SORTIES["ontology"]
    differees = formes_differees(args.out)
    if differees:
        print(f"NOTE    formes {', '.join(differees)} différées : devices.json non calculé (M4)")
    echecs = 0
    for nom in SORTIES.values():
        try:
            verifier_sortie(args.out / nom, schemas, formes=formes, ontologie=ontologie)
            print(f"OK      {nom}")
        except SortieNonConforme as exc:
            echecs += 1
            print(f"ÉCHEC   {exc}")
    return 1 if echecs else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = construire_parseur().parse_args(argv)
    try:
        if args.commande == "run":
            return commande_run(args)
        if args.commande == "visualiser":
            return commande_visualiser(args)
        if args.commande == "questions":
            return commande_questions(args)
        return commande_valider(args)
    except (FileNotFoundError, SortieNonConforme, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
