"""Comparaison détecteur de fumée / détecteur de chaleur sur le scénario du kit (justifie D1 et D3).

Le kit laisse le type libre (« détecteurs automatiques (fumée ou chaleur) », theorie/M4 §1) ; on compare
donc les deux sur les MESURES de `observations.csv`, espace par espace :
- délai d'alarme : fumée (obscurcissement > seuil de M5) ; chaleur statique EN 54-5 classe A1
  (température de réponse statique 54–65 °C : on donne les deux bornes) ; chaleur thermovélocimétrique
  (classe A1R, approchée par une élévation ≥ X °C en 60 s : APPROXIMATION pédagogique, la norme définit
  des temps de réponse par rampe) ;
- marge avant que l'espace devienne Dangerous (seuils de M5 : T > 60 °C ou CO > 1 000 ppm) ;
- effet sur la première alarme du bâtiment et du niveau si l'on remplace les détecteurs d'un ensemble
  d'espaces (D1 : la cuisine ; D3 : le Level 2) ;
- nombre de détecteurs requis (MILP de M4) selon le rayon de couverture d'un détecteur de chaleur.

Hypothèse : chaque espace instrumenté dans observations.csv donne le signal vu par un détecteur placé
dans cet espace (pas de modèle de transport de fumée ni de plafond).
Aucun seuil n'est en dur : tout passe par parametres.json (clés facultatives, défauts ci-dessous).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

DEFAUTS = {
    "detecteur_chaleur_statique_degC": [54.0, 65.0],      # EN 54-5 classe A1 : réponse statique 54–65 °C
    "detecteur_chaleur_vitesse_degC_en_60s": 10.0,        # A1R, approximation (voir docstring)
    "detecteur_chaleur_rayons_m": None,                   # None -> [r, r·√0,5, r·√0,3] (surface /2, ×0,3)
}


def _p(params: dict, cle: str):
    return params.get(cle, DEFAUTS[cle])


def series(chemin_obs: Path) -> dict[tuple[str, str], dict[int, float]]:
    s = defaultdict(dict)
    with open(chemin_obs, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f):
            s[(l["espace_globalId"], l["type"])][int(l["t_s"])] = float(l["valeur"])
    return s


def _premier(serie: dict[int, float], cond) -> int | None:
    return next((t for t in sorted(serie) if cond(t, serie)), None)


def delais(geo: dict, obs: dict, params: dict) -> list[dict]:
    from twinhyp.m5_evacuation import seuils

    s = seuils(params)
    t_bas, t_haut = _p(params, "detecteur_chaleur_statique_degC")
    dv = float(_p(params, "detecteur_chaleur_vitesse_degC_en_60s"))
    niveau = {n["globalId"]: n["nom"] for n in geo["niveaux"]}
    lignes = []
    for e in geo["espaces"]:
        fum, tem, co = (obs.get((e["globalId"], k), {}) for k in ("SmokeAlarm", "TemperatureSensor", "COSensor"))
        if not e["occupable"] or not (fum or tem):
            continue
        danger = [t for t in (_premier(tem, lambda t, x: x[t] > s["seuil_danger_temperature_degC"]),
                              _premier(co, lambda t, x: x[t] > s["seuil_danger_co_ppm"])) if t is not None]
        l = {"espace_globalId": e["globalId"], "espace": e["nom"], "nom_long": e.get("nom_long"),
             "niveau": niveau.get(e["niveau_globalId"]),
             "fumee_s": _premier(fum, lambda t, x: x[t] > s["seuil_alarme_obscurcissement_par_m"]),
             "chaleur_statique_bas_s": _premier(tem, lambda t, x: x[t] >= t_bas),
             "chaleur_statique_haut_s": _premier(tem, lambda t, x: x[t] >= t_haut),
             "chaleur_vitesse_s": _premier(tem, lambda t, x: t - 60 in x and x[t] - x[t - 60] >= dv),
             "danger_s": min(danger) if danger else None,
             "temperature_max_degC": max(tem.values()) if tem else None}
        for k in ("fumee_s", "chaleur_statique_bas_s", "chaleur_statique_haut_s", "chaleur_vitesse_s"):
            l["marge_" + k[:-2] + "_s"] = (l["danger_s"] - l[k]) if l["danger_s"] is not None and l[k] is not None else None
        lignes.append(l)
    return lignes


def _premiere(lignes: list[dict], chaleur: set[str], cle_chaleur: str, niveau: str | None = None) -> int | None:
    """Première alarme si les espaces de `chaleur` portent un détecteur de chaleur, les autres de fumée."""
    t = [l[cle_chaleur] if l["espace_globalId"] in chaleur else l["fumee_s"]
         for l in lignes if niveau is None or l["niveau"] == niveau]
    t = [x for x in t if x is not None]
    return min(t) if t else None


def scenarios(lignes: list[dict], geo: dict, params: dict) -> list[dict]:
    feu = params.get("origine_feu", {}).get("globalId")
    niveaux = [n["nom"] for n in geo["niveaux"] if any(l["niveau"] == n["nom"] for l in lignes)]
    cas = [("tout fumée (M4)", set())]
    if feu:
        cas.append(("origine du feu en chaleur (D1)", {feu}))
    for n in niveaux:
        ids = {l["espace_globalId"] for l in lignes if l["niveau"] == n}
        if ids:
            cas.append((f"{n} en chaleur (D3 si niveau des travaux)", ids))
    cas.append(("tout chaleur", {l["espace_globalId"] for l in lignes}))
    res = []
    for nom, ids in cas:
        r = {"cas": nom, "espaces_en_chaleur": len(ids)}
        for k in ("chaleur_vitesse_s", "chaleur_statique_bas_s", "chaleur_statique_haut_s"):
            r["premiere_alarme_" + k] = _premiere(lignes, ids, k)
            r["par_niveau_" + k] = {n: _premiere(lignes, ids, k, n) for n in niveaux}
        res.append(r)
    return res


def nombre_detecteurs(geo: dict, params: dict) -> list[dict]:
    from twinhyp.m4_deploiement import placement

    r0 = float(params["detecteur_rayon_m"])
    rayons = _p(params, "detecteur_chaleur_rayons_m") or [r0, round(r0 * 0.5 ** 0.5, 2), round(r0 * 0.3 ** 0.5, 2)]
    niv_de = {e["globalId"]: e["niveau_globalId"] for e in geo["espaces"]}
    res = []
    for r in rayons:
        eqs, resume = placement.detecteurs(geo, {**params, "detecteur_rayon_m": r}, geo["voxels"]["origine_m"][:2])
        res.append({"rayon_m": r, "detecteurs": len(eqs), "statut": resume["statut"], "gap_relatif": resume["gap_relatif"],
                    "par_niveau": {n["nom"]: sum(1 for e in eqs if niv_de[e["espace_globalId"]] == n["globalId"])
                                   for n in geo["niveaux"]}})
    return res


def comparer(geo_chemin: Path, obs_chemin: Path, params: dict) -> dict:
    geo = json.loads(Path(geo_chemin).read_text(encoding="utf-8"))
    lignes = delais(geo, series(obs_chemin), params)
    return {"hypotheses": {k: _p(params, k) for k in DEFAUTS}, "par_espace": lignes,
            "scenarios": scenarios(lignes, geo, params), "nombre_detecteurs": nombre_detecteurs(geo, params)}
