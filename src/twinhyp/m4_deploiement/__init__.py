"""M4 – Déploiement SSI : caméras, détecteurs, déclencheurs -> devices.json.

Squelette (étape 0) : aucun équipement, objectif non calculé.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json


def executer(ctx: Contexte) -> list[str]:
    devices = {
        "parametres": ctx.params_chemin.name,
        "objectif": {"valeur": 0, "statut_solveur": "non_calcule", "temps_s": 0, "mode": "3D"},
        "equipements": [],
    }
    ecrire_json(ctx.chemin_sortie("devices"), devices)
    return ["devices"]
