from pathlib import Path

import pytest

from twinhyp.contexte import DONNEES_PAR_DEFAUT, Contexte

DONNEES = DONNEES_PAR_DEFAUT
IFC_DUPLEX = DONNEES / "duplex_TwinHypervisor.ifc"
PARAMS = DONNEES / "parametres.json"
OBS = DONNEES / "observations.csv"


@pytest.fixture
def ctx(tmp_path: Path) -> Contexte:
    """Contexte sur le duplex du kit, sorties dans un dossier temporaire."""
    return Contexte(ifc=IFC_DUPLEX, params_chemin=PARAMS, obs=OBS, sortie=tmp_path / "sorties")
