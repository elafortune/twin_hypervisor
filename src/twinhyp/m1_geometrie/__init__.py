"""M1 – Jumeau géométrique : IFC -> geometry.json.

Étape 1 : niveaux, espaces, portes, escaliers, anomalies d'attributs.
Étape 2 : liaisons recoupées sur 3 sources, sorties, anomalies de connectivité.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json
from twinhyp.m1_geometrie import anomalies, connectivite, extraction
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
    return geometrie


def executer(ctx: Contexte) -> list[str]:
    ecrire_json(ctx.chemin_sortie("geometry"), construire_geometrie(ctx.ifc, ctx.params))
    return ["geometry"]
