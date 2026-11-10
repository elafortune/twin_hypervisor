"""M4 – Déploiement SSI : geometry.json + voxels + paramètres -> devices.json, kg.ttl (F3–F6).

Formulation séquentielle, chaque sous-problème résolu EXACTEMENT par HiGHS (statut et gap rapportés) :
1. détecteurs automatiques (couverture d'ensemble, rayon `detecteur_rayon_m`) ;
2. déclencheurs manuels (couverture des sorties à distance de cheminement ≤ `declencheur_distance_max_m`) ;
3. caméras 3D (couverture des chemins ≥ `couverture_video_min`, puis full-view maximal à nombre fixé) ;
4. zones de détection : une par niveau et par logement ;
5. connectivité radio (modèle de M3) et relais IoTNode si nécessaire.
Tous les paramètres viennent de parametres.json (« paramètres personnels » de F4/F5).
"""

from __future__ import annotations

import json

import numpy as np
from rdflib import Graph

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json
from twinhyp.m2_graphe.construction import logements
from twinhyp.m3_iwcmc import config as config_iwcmc
from twinhyp.m3_iwcmc.radio import Environnement
from twinhyp.m4_deploiement import graphe as kg_m4
from twinhyp.m4_deploiement import placement, reseau

PREFIXE_ID = {"SmokeDetector": "DF", "HeatDetector": "DC", "ManualCallPoint": "DM", "Camera": "CAM", "IoTNode": "RELAIS"}


def zones_detection(geometrie: dict, equipements: list[dict]) -> dict[str, str]:
    """Zone = (niveau, logement) : jamais à cheval sur deux niveaux (F6)."""
    nom = {e["globalId"]: e["nom"] for e in geometrie["espaces"]}
    niveau = {e["globalId"]: e["niveau_globalId"] for e in geometrie["espaces"]}
    nom_niveau = {n["globalId"]: n["nom"].replace(" ", "") for n in geometrie["niveaux"]}
    logement = {}
    for comp in logements(geometrie):
        prefixe = min(nom[g] for g in comp)[0]
        for g in comp:
            logement[g] = prefixe
    zones = {}
    for e in equipements:
        if e["type"] == "Camera":
            continue
        s = e["espace_globalId"]
        zid = f"ZD_{logement.get(s, 'X')}_{nom_niveau[niveau[s]]}"
        e["zone_detection"] = zid
        zones[zid] = niveau[s]
    return zones


def deployer(geometrie: dict, params: dict, env: Environnement) -> tuple[list[dict], dict, dict, dict]:
    det, r_det = placement.detecteurs(geometrie, params, env.origine[:2])
    dm, r_dm = placement.declencheurs(geometrie, params)
    chem = placement.chemins(geometrie, env, float(params.get("pas_grille_m", 0.5)) / 2)
    cam, r_cam, par_chemin = placement.cameras(geometrie, params, env, chem)
    equipements = det + dm + cam
    compteur = {}
    for e in equipements:
        compteur[e["type"]] = compteur.get(e["type"], 0) + 1
        e["id"] = f"{PREFIXE_ID[e['type']]}-{compteur[e['type']]:02d}"
    # Réseau : modèle de M3 avec la lecture et le facteur retenus (tableau I tel quel par défaut)
    cfg = config_iwcmc(params)
    pts = np.array([[e["x"], e["y"], e["z"]] for e in equipements])
    r_reseau = {"principal": reseau.analyser(env, pts, cfg, cfg["facteur_attenuation"]),
                "attenuation_x30": reseau.analyser(env, pts, cfg, 30.0)}
    ajout = reseau.relais(env, pts, env.antennes(), cfg, cfg["facteur_attenuation"])
    for k, j in enumerate(ajout, start=1):
        a = geometrie["positions_autorisees"][j]
        equipements.append({"id": f"RELAIS-{k:02d}", "type": "IoTNode", "espace_globalId": a["espace_globalId"],
                            "x": a["xyz"][0], "y": a["xyz"][1], "z": a["xyz"][2]})
    r_reseau["relais_ajoutes"] = len(ajout)
    zones = zones_detection(geometrie, equipements)
    sous = {"detecteurs": r_det, "declencheurs": r_dm, "cameras": r_cam, "reseau": r_reseau}
    return equipements, zones, par_chemin, sous


def executer(ctx: Contexte) -> list[str]:
    geometrie = json.loads(ctx.chemin_sortie("geometry").read_text(encoding="utf-8"))
    env = Environnement.charger(ctx.sortie / geometrie["voxels"]["fichier"])
    equipements, zones, par_chemin, sous = deployer(geometrie, ctx.params, env)
    cles = ("detecteurs", "declencheurs", "cameras")
    statuts = [sous[k]["statut"] for k in cles]
    devices = {
        "parametres": ctx.params_chemin.name,
        "objectif": {"valeur": float(len(equipements)),
                     "statut_solveur": "Optimal" if all(s == "Optimal" for s in statuts) else "; ".join(statuts),
                     "gap_relatif": max(sous[k]["gap_relatif"] for k in cles),
                     "temps_s": round(sum(sous[k]["temps_s"] for k in cles), 3),
                     "mode": "3D", "formulation": "séquentielle : détecteurs, déclencheurs, caméras (HiGHS)"},
        "sous_problemes": sous,
        "zones_detection": zones,
        "chemins": [{"espace_globalId": e, "sortie_globalId": s, **{k: v for k, v in i.items() if k != "indices"}}
                    for (e, s), i in par_chemin.items()],
        "equipements": [{k: v for k, v in e.items() if k != "cellules_vues"} for e in equipements],
    }
    ecrire_json(ctx.chemin_sortie("devices"), devices)
    g = Graph().parse(ctx.chemin_sortie("kg"), format="turtle")
    kg_m4.ecrire(g, geometrie, equipements, zones, par_chemin)
    g.serialize(ctx.chemin_sortie("kg"), format="turtle", encoding="utf-8")
    return ["devices", "kg"]
