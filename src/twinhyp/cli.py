"""Interface en ligne de commande.

    python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc \
        --params data/parametres.json --obs data/observations.csv --out sorties/

    python -m twinhyp run ... --etapes m1,m2     # relancer une partie de la chaîne
    python -m twinhyp valider --out sorties/     # revalider des sorties existantes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from twinhyp.contexte import DONNEES_PAR_DEFAUT, SORTIES
from twinhyp.io_schemas import SortieNonConforme, verifier_sortie


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
    return p


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
    formes = args.donnees / "ontologie" / "formes_publiques.ttl"
    ontologie = args.out / SORTIES["ontology"]
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
        return commande_valider(args)
    except (FileNotFoundError, SortieNonConforme, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
