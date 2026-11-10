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
    sen = sous.add_parser("sensibilite", help="IWCMC : sensibilité de l'atténuation (glouton, comparé à la figure 4)")
    sen.add_argument("--out", required=True, type=Path)
    sen.add_argument("--params", type=Path, default=DONNEES_PAR_DEFAUT / "parametres.json")
    sen.add_argument("--facteurs", default="1,2,5,10,20,50")

    cmp_ = sous.add_parser("campagne", help="IWCMC : campagne complète d'expériences (comparaison.md)")
    cmp_.add_argument("--out", required=True, type=Path)
    cmp_.add_argument("--rapide", action="store_true", help="2 graines au lieu de 5")

    qst = sous.add_parser("questions", help="réponses Q01–Q14 obtenues par SPARQL sur <out>/kg.ttl")
    qst.add_argument("--out", required=True, type=Path)
    qst.add_argument("--sparql", action="store_true", help="afficher aussi les requêtes")
    return p


def commande_sensibilite(args: argparse.Namespace) -> int:
    import json

    from twinhyp.io_schemas import ecrire_json
    from twinhyp.m3_iwcmc import config, obstacles, radios
    from twinhyp.m3_iwcmc.radio import Environnement
    from twinhyp.m3_iwcmc.sensibilite import etude

    cfg = config(json.loads(args.params.read_text(encoding="utf-8")))
    geo = json.loads((args.out / SORTIES["geometry"]).read_text(encoding="utf-8"))
    env = Environnement.charger(args.out / geo["voxels"]["fichier"])
    obs = obstacles(env, cfg["technologie"], args.out / "iwcmc")
    lignes = etude(lambda k, lecture: radios(env, obs, {**cfg, "facteur_attenuation": k, "lecture_L_obs": lecture}, 0),
                   facteurs=[float(x) for x in args.facteurs.split(",")])
    ecrire_json(args.out / "iwcmc" / "sensibilite.json", lignes)
    print("lecture  facteur  couv.1 avec  couv.1 sans  qualité 1  n(90 %)  écart moyen fig. 4")
    for l in lignes:
        print(f"{l['lecture']:7}  {l['facteur']:7}  {l['couverture_1_avec']:11}  {l['couverture_1_sans_evaluee_avec']:11}"
              f"  {l['qualite_1_avec']:9}  {l['n_90_avec']}  {l['ecart_moyen_couverture_fig4']:7}")
    print("Article (fig. 4) : couv.1 avec 0,44 · sans 0,35 · qualité 1 −45,1 dBm · n(90 %) = 3")
    return 0


def commande_questions(args: argparse.Namespace) -> int:
    from rdflib import Graph, RDFS

    from twinhyp.m2_graphe.construction import SSI
    from twinhyp.m6_agent import reference

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

    rep = reference.reponses(g, args.out / SORTIES["pareto"])
    for qid, (reponse, requetes) in rep.items():
        afficher(qid, reponse, requetes)
    if "Q15" not in rep:
        print("Q15–Q19 : scénario non rejoué (lancer M5)")
    return 0


def commande_visualiser(args: argparse.Namespace) -> int:
    import json

    from twinhyp.visualisation import comparaison, iwcmc, plan2d, voxels, vue3d

    geo = args.out / SORTIES["geometry"]
    if not geo.is_file():
        raise FileNotFoundError(f"{geo} absent : lancer d'abord `run --etapes m1`")
    dossier = args.out / "figures"
    print(f"Plan 2D : {plan2d.generer(geo, dossier).resolve()}")
    npz = args.out / "grille_voxels.npz"
    if npz.is_file():
        print(f"Voxels  : {voxels.generer(npz, dossier).resolve()}")
    chemin_iwcmc = iwcmc.generer(args.out, dossier)
    if chemin_iwcmc:
        print(f"IWCMC   : {chemin_iwcmc.resolve()}")
    chemin_cmp = comparaison.generer(args.out, dossier)
    if chemin_cmp:
        print(f"Campagne: {chemin_cmp.resolve()}")
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
        if args.commande == "sensibilite":
            return commande_sensibilite(args)
        if args.commande == "campagne":
            from twinhyp.m3_iwcmc.campagne import campagne
            campagne(args.out, args.rapide)
            print(f"Résultats : {(args.out / 'iwcmc' / 'campagne' / 'resultats.json').resolve()}")
            return 0
        return commande_valider(args)
    except (FileNotFoundError, SortieNonConforme, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
