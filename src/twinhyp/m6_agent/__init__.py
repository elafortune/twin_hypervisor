"""M6 – Agent neuro-symbolique : questions + demandes -> answers.jsonl, audit_log.jsonl.

Squelette (étape 0) : aucune réponse, aucune action.
"""

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_jsonl


def executer(ctx: Contexte) -> list[str]:
    ecrire_jsonl(ctx.chemin_sortie("answers"), [])
    ecrire_jsonl(ctx.chemin_sortie("audit"), [])
    return ["answers", "audit"]
