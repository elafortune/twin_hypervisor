"""M1 – Jumeau géométrique : IFC -> geometry.json.

Étape 1 : niveaux, espaces, portes, escaliers, anomalies d'attributs.
Étape 2 : liaisons recoupées sur 3 sources, sorties, anomalies de connectivité.
Étape 3 : distances d'évacuation orientées (point le plus défavorable, visibilité + Dijkstra).
Étape 6 : grille de voxels avec matériau (grille_voxels.npz) et positions autorisées au plafond.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json
import json

import numpy as np

from twinhyp.m1_geometrie import anomalies, connectivite, distances, extraction, voxels
from twinhyp.m1_geometrie import ifc_outils as io


def construire_geometrie(chemin_ifc, params: dict | None = None) -> dict:
    params = params or {}
    f = io.ouvrir(chemin_ifc)
    mots_cles = tuple(params.get("mots_cles_non_occupable", extraction.MOTS_CLES_NON_OCCUPABLE))
    niveaux = extraction.en_dicts(extraction.extraire_niveaux(f))
    espaces = extraction.en_dicts(extraction.extraire_espaces(f, mots_cles))
    portes = extraction.en_dicts(extraction.extraire_portes(f))
    escaliers = extraction.en_dicts(extraction.extraire_escaliers(f))
    geometrie = {
        "source": {"ifc": str(chemin_ifc), "schema_ifc": f.schema,
                   "echelle_longueur_m": io.echelle_longueur(f)},
        "niveaux": niveaux,
        "espaces": espaces,
        "portes": portes,
        "escaliers": escaliers,
        "liaisons": [],
        "anomalies": anomalies.detecter(f, niveaux, espaces, escaliers),
    }
    geometrie["anomalies"] += connectivite.calculer(f, geometrie)  # étape 2
    geometrie["anomalies"] += distances.calculer(geometrie)        # étape 3
    return geometrie


FICHIER_VOXELS = "grille_voxels.npz"


def ajouter_voxels(chemin_ifc, geometrie: dict, params: dict, chemin_npz) -> None:
    """Étape 6 : la grille complète va dans un .npz (tableaux), le résumé et A dans geometry.json."""
    grille, vox, A, resume = voxels.calculer(io.ouvrir(chemin_ifc), geometrie, params)
    np.savez_compressed(
        chemin_npz, origine=grille.origine, pas=grille.pas, libre=vox["libre"], materiau=vox["materiau"],
        fraction_obstacle=vox["fraction_obstacle"], element=vox["element"],
        positions=np.array([a["xyz"] for a in A], dtype=np.float32).reshape(-1, 3),
        categories=json.dumps(voxels.CATEGORIES, ensure_ascii=False),
        elements=json.dumps(vox["elements"], ensure_ascii=False))
    geometrie["voxels"] = {"fichier": chemin_npz.name, **resume}
    geometrie["positions_autorisees"] = A


def executer(ctx: Contexte) -> list[str]:
    geometrie = construire_geometrie(ctx.ifc, ctx.params)
    ajouter_voxels(ctx.ifc, geometrie, ctx.params, ctx.sortie / FICHIER_VOXELS)
    ecrire_json(ctx.chemin_sortie("geometry"), geometrie)
    return ["geometry"]
