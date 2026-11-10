"""M3 – Reproduction IWCMC 2024 : voxels + matériaux -> pareto.json (4 scénarios).

Squelette (étape 0) : liste de scénarios vide.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json


def executer(ctx: Contexte) -> list[str]:
    ecrire_json(ctx.chemin_sortie("pareto"), [])
    return ["pareto"]
