"""M5 – Évacuation dynamique : kg.ttl + observations -> evacuation_dynamique.jsonl.

Squelette (étape 0) : aucune ligne.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_jsonl


def executer(ctx: Contexte) -> list[str]:
    ecrire_jsonl(ctx.chemin_sortie("evacuation"), [])
    return ["evacuation"]
