"""Scénario d'observations SYNTHÉTIQUE pour un bâtiment quelconque (étape 10 : généricité).

Le kit ne fournit des observations que pour le duplex ; pour tester la chaîne sur un autre IFC, on fabrique
un fichier au même format (`t_s,horodatage,capteur,type,espace_globalId,valeur,unite`), à partir du graphe
de connectivité de geometry.json :
- un espace à k liaisons de l'origine du feu reçoit le front avec un retard `k × retard_par_liaison_s`,
  atténué d'un facteur `attenuation_par_liaison^k` ;
- croissance en t² (feu « t-carré »), plafonnée : profils calés sur ceux du kit (cuisine A103 : alarme
  fumée vers 60 s, 60 °C vers 120 s, plateau ≈ 626 °C ; CO plafonné à 5 000 ppm) ;
- caméras : `n_occupes` espaces occupés (tirage reproductible, graine), la moitié évacue après l'alarme
  et l'autre moitié reste (personnes en attente, comme A202 / A203 dans le kit).

Ce n'est pas un modèle de feu : seulement un jeu de données plausible pour exercer M5 et M6.
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import networkx as nx

DEFAUTS = {"duree_s": 600, "pas_s": 10, "retard_par_liaison_s": 50.0, "attenuation_par_liaison": 0.65,
           "t_ambiante_degC": 26.0, "t_max_degC": 626.0, "obscurcissement_max_par_m": 3.0, "co_max_ppm": 5000.0,
           "k_fumee": 1.0e-5, "k_temperature": 2.4e-3, "k_co": 0.02, "n_occupes": 6, "graine": 0,
           "debut": "2026-11-20T10:00:00Z"}


def _graphe(geo: dict) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(e["globalId"] for e in geo["espaces"])
    G.add_edges_from((l["de"], l["vers"]) for l in geo["liaisons"])
    return G


def generer(geo: dict, origine: str, cfg: dict | None = None) -> list[dict]:
    c = {**DEFAUTS, **(cfg or {})}
    espaces = {e["globalId"]: e for e in geo["espaces"] if e["occupable"]}
    if origine not in espaces:
        origine = next((g for g, e in espaces.items() if e["nom"] == origine), origine)
    if origine not in espaces:
        raise ValueError(f"origine du feu inconnue ou non occupable : {origine}")
    hops = nx.single_source_shortest_path_length(_graphe(geo), origine)
    rng = random.Random(c["graine"])
    candidats = sorted(g for g in espaces if g != origine and hops.get(g, 99) >= 1)
    occupes = rng.sample(candidats, min(c["n_occupes"], len(candidats)))
    personnes = {g: rng.randint(1, 3) for g in occupes}
    restent = set(occupes[::2])  # la moitié reste sur place (attente)
    t0 = datetime.fromisoformat(c["debut"].replace("Z", "+00:00"))
    lignes = []
    for t in range(0, int(c["duree_s"]) + 1, int(c["pas_s"])):
        h = (t0 + timedelta(seconds=t)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for g in sorted(espaces, key=lambda g: espaces[g]["nom"]):
            nom, k = espaces[g]["nom"], hops.get(g)
            if k is None:
                f = d = 0.0
            else:
                f, d = c["attenuation_par_liaison"] ** k, max(0.0, t - k * c["retard_par_liaison_s"])
            fumee = min(c["obscurcissement_max_par_m"] * f, c["k_fumee"] * d * d) if f else 0.0
            temp = c["t_ambiante_degC"] + (min((c["t_max_degC"] - c["t_ambiante_degC"]) * f, c["k_temperature"] * d * d) if f else 0.0)
            co = min(c["co_max_ppm"] * f, c["k_co"] * d * d) if f else 0.0
            for capteur, type_, v, u in ((f"SD_{nom}", "SmokeAlarm", round(fumee, 4), "1/m"),
                                         (f"TH_{nom}", "TemperatureSensor", round(temp, 1), "degC"),
                                         (f"CO_{nom}", "COSensor", round(co, 1), "ppm")):
                lignes.append({"t_s": t, "horodatage": h, "capteur": capteur, "type": type_, "espace_globalId": g,
                               "valeur": v, "unite": u})
            if g in personnes:
                n = personnes[g] if (g in restent or t < 150 + 30 * occupes.index(g)) else 0
                lignes.append({"t_s": t, "horodatage": h, "capteur": f"CAM_{nom}", "type": "Camera",
                               "espace_globalId": g, "valeur": n, "unite": "personnes"})
    return lignes


def ecrire(lignes: list[dict], chemin: Path) -> None:
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["t_s", "horodatage", "capteur", "type", "espace_globalId", "valeur", "unite"])
        w.writeheader()
        w.writerows(lignes)


def depuis_fichiers(geometrie: Path, origine: str, sortie: Path, cfg: dict | None = None) -> int:
    geo = json.loads(Path(geometrie).read_text(encoding="utf-8"))
    lignes = generer(geo, origine, cfg)
    ecrire(lignes, sortie)
    return len(lignes)
