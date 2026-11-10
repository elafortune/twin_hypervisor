"""M1 – Jumeau géométrique : IFC -> geometry.json (+ voxels à l'étape 6).

Squelette (étape 0) : écrit un geometry.json vide mais conforme.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json


def executer(ctx: Contexte) -> list[str]:
    geometrie = {"niveaux": [], "espaces": [], "portes": [], "liaisons": [], "anomalies": []}
    ecrire_json(ctx.chemin_sortie("geometry"), geometrie)
    return ["geometry"]
