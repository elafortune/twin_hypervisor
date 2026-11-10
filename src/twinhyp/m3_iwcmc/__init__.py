"""M3 – Reproduction IWCMC 2024 : grille de voxels + matériaux (M1) -> pareto.json (4 scénarios).

Scénarios : {avec jumeau, sans jumeau} × {µ = 0, µ = 3}. « Sans jumeau » : on OPTIMISE dans
l'environnement où tous les obstacles sont dans le matériau le plus absorbant, puis on ÉVALUE
les solutions dans l'environnement avec jumeau (§V.C).

Paramètres (tableau II par défaut) surchargeables par la clé "iwcmc" de parametres.json.
Lectures des ambiguïtés : voir iwcmc.md (I-1 à I-9).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from twinhyp.contexte import Contexte
from twinhyp.io_schemas import ecrire_json
from twinhyp.m3_iwcmc import article
from twinhyp.m3_iwcmc.prep_nsga import Parametres, meilleur_par_taille, prep_nsga
from twinhyp.m3_iwcmc.radio import TABLEAU_I, Environnement, matrices_obstacles, perte_espace_libre
from twinhyp.m3_iwcmc.score import Radio

DEFAUTS = {
    "technologie": "WiFi 2.4GHz", "P_TX_dBm": 20.0, "S_RX_dBm": -65.0, "alpha": 1.0, "beta": 1.0,
    "n_it": 300, "n_pop": 40, "n_mu": 160, "gamma_m": 2.0, "n_max": 10,
    "lecture_L_obs": "voxel",        # "voxel" (option 2, principale) ou "metre" (option 1)
    "facteur_attenuation": 1.0,      # 1 = valeurs du tableau I telles quelles
    "shadowing": True,
    # Variantes à atténuation renforcée, pour expliquer l'écart aux figures (sorties/iwcmc/pareto_facteurK.json)
    "facteurs_supplementaires": [30],
    "max_positions": None,           # sous-échantillonnage régulier de A (tests rapides) ; None = toutes
}
SCENARIOS = [(True, 0), (False, 0), (True, 3), (False, 3)]


def config(params: dict) -> dict:
    return {**DEFAUTS, **params.get("iwcmc", {})}


def nom_scenario(jumeau: bool, mu: int) -> str:
    return f"{'avec' if jumeau else 'sans'} jumeau, mu={mu}"


# Matrices de perte ---------------------------------------------------------------
def obstacles(env: Environnement, techno: str, dossier: Path) -> dict[str, np.ndarray]:
    """Pertes d'obstacles (avec / sans jumeau, lectures voxel / mètre), mises en cache :
    c'est le calcul le plus long (≈ 0,3 s par position autorisée)."""
    A = env.antennes()
    empreinte = hashlib.sha1(env.libre.tobytes() + env.materiau.tobytes() + A.tobytes()
                             + techno.encode()).hexdigest()[:16]
    cache = dossier / f"obstacles_{empreinte}.npz"
    if cache.is_file():
        return dict(np.load(cache))
    C = env.centres_libres()
    Ls = [env.attenuation_par_voxel(techno, True), env.attenuation_par_voxel(techno, False)]
    V, M = matrices_obstacles(env, A, C, Ls)
    VA, MA = matrices_obstacles(env, A, A, Ls)
    res = {"voxel_avec": V[0], "voxel_sans": V[1], "metre_avec": M[0], "metre_sans": M[1],
           "AA_voxel_avec": VA[0], "AA_voxel_sans": VA[1], "AA_metre_avec": MA[0], "AA_metre_sans": MA[1]}
    dossier.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **{k: v.astype(np.float16) for k, v in res.items()})
    return res


def radios(env: Environnement, obs: dict, cfg: dict, graine: int) -> dict[bool, Radio]:
    t = TABLEAU_I[cfg["technologie"]]
    C, A = env.centres_libres(), env.antennes()
    rng = np.random.default_rng(graine)
    X = rng.normal(0, t["sigma"], (len(A), len(C))).astype(np.float32) if cfg["shadowing"] else 0
    XA = rng.normal(0, t["sigma"], (len(A), len(A))).astype(np.float32) if cfg["shadowing"] else 0
    libre = perte_espace_libre(t["PL0"], A, C)
    libre_AA = perte_espace_libre(t["PL0"], A, A)
    k, lecture = cfg["facteur_attenuation"], cfg["lecture_L_obs"]
    sortie = {}
    for jumeau in (True, False):
        suffixe = "avec" if jumeau else "sans"
        sortie[jumeau] = Radio(PL=libre + k * obs[f"{lecture}_{suffixe}"].astype(np.float32) + X,
                               PL_AA=libre_AA + k * obs[f"AA_{lecture}_{suffixe}"].astype(np.float32) + XA,
                               P_TX=cfg["P_TX_dBm"], S_RX=cfg["S_RX_dBm"], alpha=cfg["alpha"], beta=cfg["beta"])
    return sortie


# Scénarios ------------------------------------------------------------------------
def scenario(r: dict[bool, Radio], positions: list[dict], cfg: dict, jumeau: bool, mu: int,
             graine: int, dossier: Path) -> dict:
    p = Parametres(n_it=cfg["n_it"], n_pop=cfg["n_pop"], n_mu=cfg["n_mu"], gamma_m=cfg["gamma_m"],
                   mu=mu, n_max=cfg["n_max"], graine=graine)
    t0 = time.process_time()
    res = prep_nsga(r[jumeau], positions, p)
    cpu = time.process_time() - t0
    if not res.population:  # aucune solution initiale ne respecte la contrainte
        return {"scenario": nom_scenario(jumeau, mu), "parametres_algo": {**cfg, "mu": mu, "graine": graine},
                "temps_cpu_s": round(cpu, 2), "front": [], "remarque": "aucune solution faisable trouvée"}
    nom = nom_scenario(jumeau, mu)
    fichier = f"{'avec' if jumeau else 'sans'}_jumeau_mu{mu}.json"
    front, solutions = [], {}
    for n, (f, ind) in meilleur_par_taille(res.population, res.objectifs).items():
        m = r[True].metriques(ind)  # toujours évalué dans l'environnement avec jumeau (§V.C)
        point = {"n_equipements": n, "couverture": m["couverture"],
                 "qualite_lien_moyenne_dBm": m["qualite_lien_moyenne_dBm"],
                 "qualite_voxels_couverts_dBm": m["qualite_voxels_couverts_dBm"], "connectivite": m["connectivite"],
                 "f_obj_jumeau": m["f_obj"], "f_obj_optimise": round(f, 2), "fichier_solution": f"iwcmc/{fichier}"}
        ref = article.point(jumeau, mu, n)
        if ref:
            point["article"] = ref
        front.append(point)
        solutions[n] = [{"position": int(i), **positions[i]} for i in ind]
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire_json(dossier / fichier, {"scenario": nom, "solutions": solutions, "historique": res.historique})
    return {"scenario": nom, "parametres_algo": {**cfg, "mu": mu, "graine": graine},
            "temps_cpu_s": round(cpu, 2), "front": front}


def q20(pareto: list[dict], seuil: float = 0.9) -> int | None:
    """Plus petit nombre d'équipements du front « avec jumeau, µ = 0 » atteignant `seuil` de couverture."""
    front = next(s["front"] for s in pareto if s["scenario"] == nom_scenario(True, 0))
    return min((pt["n_equipements"] for pt in front if pt["couverture"] >= seuil), default=None)


def executer(ctx: Contexte) -> list[str]:
    cfg = config(ctx.params)
    geometrie = json.loads(ctx.chemin_sortie("geometry").read_text(encoding="utf-8"))
    env = Environnement.charger(ctx.sortie / geometrie["voxels"]["fichier"])
    dossier = ctx.sortie / "iwcmc"
    positions = geometrie["positions_autorisees"]
    if cfg["max_positions"] and len(positions) > cfg["max_positions"]:
        garde = np.linspace(0, len(positions) - 1, int(cfg["max_positions"])).astype(int)
        positions = [positions[i] for i in garde]
        env.positions = env.positions[garde]
    obs = obstacles(env, cfg["technologie"], dossier)
    r = radios(env, obs, cfg, ctx.graine)
    pareto = [scenario(r, positions, cfg, jumeau, mu, ctx.graine, dossier) for jumeau, mu in SCENARIOS]
    ecrire_json(ctx.chemin_sortie("pareto"), pareto)
    for k in cfg["facteurs_supplementaires"]:  # n'entre pas dans pareto.json : analyse de l'écart
        variante = {**cfg, "facteur_attenuation": k}
        rk = radios(env, obs, variante, ctx.graine)
        sous = dossier / f"facteur{k:g}"
        ecrire_json(dossier / f"pareto_facteur{k:g}.json",
                    [scenario(rk, positions, variante, jumeau, mu, ctx.graine, sous) for jumeau, mu in SCENARIOS])
    return ["pareto"]
