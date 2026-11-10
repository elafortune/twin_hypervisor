"""M2 – Graphe de connaissances : geometry.json + observations -> ontology.ttl, kg.ttl.

Squelette (étape 0) : l'ontologie est le socle recopié, le graphe est vide.
"""

import shutil

from twinhyp.contexte import Contexte

ENTETE_KG = """@prefix ssi: <https://ligm.univ-eiffel.fr/twinhypervisor/ssi#> .
@prefix bot: <https://w3id.org/bot#> .
"""


def executer(ctx: Contexte) -> list[str]:
    shutil.copyfile(ctx.ontologie_socle, ctx.chemin_sortie("ontology"))
    ctx.chemin_sortie("kg").write_text(ENTETE_KG, encoding="utf-8")
    return ["ontology", "kg"]
