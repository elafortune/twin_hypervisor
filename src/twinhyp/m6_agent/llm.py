"""Client du LLM local (Ollama, API REST /api/chat) et journal de CHAQUE appel.

Reproductibilité : température 0, graine fixe, digest exact du modèle noté dans le journal.
Le journal (`llm_journal.jsonl`) contient pour chaque appel : tâche, prompt complet (messages et
noms d'outils), réponse, durées (totale, chargement, évaluation du prompt, génération), jetons.

`Rejeu` relit un journal existant (clé = empreinte du prompt) : la chaîne se rejoue à l'identique
sans Ollama (machine du jury, tests). Un prompt absent du journal est une erreur, jamais une invention.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class LLMIndisponible(RuntimeError):
    pass


def empreinte(messages: list[dict], outils: list[dict] | None, format_: dict | None) -> str:
    texte = json.dumps({"m": messages, "t": [o["function"]["name"] for o in outils or []], "f": format_},
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()[:16]


class Journal:
    def __init__(self, chemin: Path):
        self.chemin = Path(chemin)
        self.chemin.write_text("", encoding="utf-8")

    def ecrire(self, entree: dict) -> None:
        with self.chemin.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entree, ensure_ascii=False) + "\n")


class Ollama:
    def __init__(self, modele: str, journal: Journal, url: str = "http://localhost:11434", graine: int = 0,
                 contexte: int = 8192, delai_s: float = 900):
        self.modele, self.journal, self.url = modele, journal, url.rstrip("/")
        self.options = {"temperature": 0, "seed": graine, "num_ctx": contexte}
        self.delai_s = delai_s
        self.digest = self._digest()

    def _post(self, chemin: str, corps: dict) -> dict:
        req = urllib.request.Request(self.url + chemin, json.dumps(corps).encode("utf-8"),
                                     {"Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=self.delai_s).read())
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            raise LLMIndisponible(f"Ollama injoignable sur {self.url} ({exc}) : lancer `ollama serve` "
                                  f"et `ollama pull {self.modele}`") from exc

    def _digest(self) -> str:
        try:
            tags = json.loads(urllib.request.urlopen(self.url + "/api/tags", timeout=10).read())
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            raise LLMIndisponible(f"Ollama injoignable sur {self.url} ({exc}) : lancer `ollama serve`") from exc
        for m in tags.get("models", []):
            if m["name"] == self.modele or m["model"] == self.modele:
                return m["digest"]
        raise LLMIndisponible(f"modèle {self.modele} absent d'Ollama : `ollama pull {self.modele}`")

    def chat(self, messages: list[dict], outils: list[dict] | None = None, format_: dict | None = None,
             tache: str = "") -> dict:
        corps = {"model": self.modele, "messages": messages, "stream": False, "options": self.options}
        if outils:
            corps["tools"] = outils
        if format_:
            corps["format"] = format_
        t0 = time.perf_counter()
        r = self._post("/api/chat", corps)
        duree = time.perf_counter() - t0
        ns = lambda k: round(r.get(k, 0) / 1e9, 3)
        entree = {"horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tache": tache,
                  "empreinte": empreinte(messages, outils, format_), "modele": self.modele, "digest": self.digest,
                  "options": self.options, "messages": messages, "outils": [o["function"]["name"] for o in outils or []],
                  "format": format_, "reponse": r.get("message", {}), "duree_s": round(duree, 3),
                  "duree_chargement_s": ns("load_duration"), "duree_prompt_s": ns("prompt_eval_duration"),
                  "duree_generation_s": ns("eval_duration"), "jetons_prompt": r.get("prompt_eval_count", 0),
                  "jetons_generes": r.get("eval_count", 0)}
        self.journal.ecrire(entree)
        return entree


class Rejeu:
    """Relit les réponses d'un journal précédent (même prompt -> même réponse), et les rejournalise."""

    def __init__(self, source: Path, journal: Journal):
        self.par_empreinte = {}
        for ligne in Path(source).read_text(encoding="utf-8").splitlines():
            if ligne.strip():
                e = json.loads(ligne)
                self.par_empreinte.setdefault(e["empreinte"], e)
        self.journal = journal
        premier = next(iter(self.par_empreinte.values()), {})
        self.modele, self.digest = premier.get("modele", "rejeu"), premier.get("digest")

    def chat(self, messages, outils=None, format_=None, tache=""):
        cle = empreinte(messages, outils, format_)
        if cle not in self.par_empreinte:
            raise LLMIndisponible(f"rejeu : prompt de la tâche {tache} absent du journal (empreinte {cle})")
        entree = {**self.par_empreinte[cle], "rejeu": True,
                  "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        self.journal.ecrire(entree)
        return entree


class Factice:
    """LLM factice pour les tests de PLOMBERIE de la chaîne (TWINHYP_LLM=factice) : n'appelle aucun outil et
    renvoie un plan « autre ». Les réponses sont alors vides et marquées en échec : jamais pour des résultats."""

    modele, digest = "factice", None

    def __init__(self, journal: Journal):
        self.journal = journal

    def chat(self, messages, outils=None, format_=None, tache=""):
        contenu = json.dumps({"action": "autre"}) if format_ else ""
        entree = {"horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tache": tache,
                  "empreinte": empreinte(messages, outils, format_), "modele": "factice", "messages": messages,
                  "reponse": {"role": "assistant", "content": contenu}, "duree_s": 0.0}
        self.journal.ecrire(entree)
        return entree
