"""Contexte d'exécution partagé par tous les modules de la chaîne.

Chaque module reçoit le même `Contexte` : les chemins d'entrée, les paramètres
lus depuis `parametres.json` (jamais de valeur en dur) et le dossier de sortie.
Les modules communiquent uniquement par les fichiers de sortie (contrats définis
par `data/schemas/`) : M2 lit `geometry.json`, pas l'IFC.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RACINE_DEPOT = Path(__file__).resolve().parents[2]
DONNEES_PAR_DEFAUT = RACINE_DEPOT / "data"

# Nom de fichier de chaque sortie imposée par l'énoncé.
SORTIES = {
    "geometry": "geometry.json",
    "ontology": "ontology.ttl",
    "kg": "kg.ttl",
    "pareto": "pareto.json",
    "devices": "devices.json",
    "evacuation": "evacuation_dynamique.jsonl",
    "answers": "answers.jsonl",
    "audit": "audit_log.jsonl",
}


@dataclass
class Contexte:
    ifc: Path
    params_chemin: Path
    obs: Path
    sortie: Path
    donnees: Path = DONNEES_PAR_DEFAUT
    questions: Path | None = None
    demandes: Path | None = None
    graine: int = 0
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.ifc = Path(self.ifc)
        self.params_chemin = Path(self.params_chemin)
        self.obs = Path(self.obs)
        self.sortie = Path(self.sortie)
        self.donnees = Path(self.donnees)
        self.questions = Path(self.questions) if self.questions else self.donnees / "questions.json"
        self.demandes = Path(self.demandes) if self.demandes else self.donnees / "demandes_modification.json"
        for nom, chemin in [("IFC", self.ifc), ("paramètres", self.params_chemin), ("observations", self.obs)]:
            if not chemin.is_file():
                raise FileNotFoundError(f"Fichier {nom} introuvable : {chemin}")
        self.params = json.loads(self.params_chemin.read_text(encoding="utf-8"))
        self.sortie.mkdir(parents=True, exist_ok=True)

    def chemin_sortie(self, cle: str) -> Path:
        return self.sortie / SORTIES[cle]

    @property
    def schemas(self) -> Path:
        return self.donnees / "schemas"

    @property
    def ontologie_socle(self) -> Path:
        return self.donnees / "ontologie" / "ssi_socle.ttl"

    @property
    def formes_publiques(self) -> Path:
        return self.donnees / "ontologie" / "formes_publiques.ttl"

    @property
    def figures(self) -> Path:
        chemin = self.sortie / "figures"
        chemin.mkdir(exist_ok=True)
        return chemin
