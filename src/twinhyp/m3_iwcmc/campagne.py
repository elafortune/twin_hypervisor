"""Campagne d'expériences de la comparaison IWCMC (résultats commentés dans comparaison.md).

Pour pouvoir tout faire varier sans relancer le lancer de rayons, on compte, pour chaque couple
(position, voxel cible), les voxels obstacles traversés **par groupe de matériau** (et la longueur
traversée dans chaque groupe). Toute variante (table de matériaux, technologie, facteur,
« sans jumeau », lecture voxel / mètre) est alors une combinaison linéaire de ces comptes.

Groupes : 1 plâtre (murs, cloisons) · 2 béton · 3 mur porteur · 4 bois (portes, planchers) ·
5 autre · 6 plâtre des faux plafonds (séparé pour l'expérience sur la part de plâtre).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from twinhyp.io_schemas import ecrire_json
from twinhyp.m3_iwcmc import article
from twinhyp.m3_iwcmc.prep_nsga import Parametres, meilleur_par_taille, prep_nsga
from twinhyp.m3_iwcmc.radio import (MATERIAUX_TABLE, TABLEAU_I, Environnement, matrices_obstacles,
                                    obstacles_traverses, perte_espace_libre)
from twinhyp.m3_iwcmc.score import Radio
from twinhyp.m3_iwcmc.sensibilite import glouton

GROUPES = {1: "plaque_de_platre", 2: "mur_beton", 3: "mur_porteur", 4: "bois", 5: "autre", 6: "plaque_de_platre"}
NOMS_GROUPES = {1: "plâtre (murs)", 2: "béton", 3: "mur porteur", 4: "bois", 5: "autre", 6: "plâtre (faux plafonds)"}


# Comptes par groupe ---------------------------------------------------------------
def groupes_voxels(env: Environnement, chemin_npz: Path) -> np.ndarray:
    d = np.load(chemin_npz)
    elements = json.loads(str(d["elements"]))
    g = env.materiau.astype(np.int8).copy()
    g[env.libre == 1] = 0
    plafond = np.array([e["classe"] == "IfcCovering" for e in elements] + [False])
    el = d["element"].astype(int)
    g[(g == 1) & plafond[el]] = 6
    return g


def comptes(env: Environnement, groupes: np.ndarray, dossier: Path) -> dict[str, np.ndarray]:
    """Clés : voxel / metre (6, |A|, F) et AA_voxel / AA_metre (6, |A|, |A|), en cache."""
    A, C = env.antennes(), env.centres_libres()
    cle = hashlib.sha1(groupes.tobytes() + A.tobytes()).hexdigest()[:16]
    cache = dossier / f"comptes_{cle}.npz"
    if cache.is_file():
        return dict(np.load(cache))
    champs = [(groupes == k).astype(np.float32) for k in sorted(GROUPES)]
    V, M = matrices_obstacles(env, A, C, champs)
    VA, MA = matrices_obstacles(env, A, A, champs)
    res = {"voxel": V.astype(np.float16), "metre": M.astype(np.float16),
           "AA_voxel": VA.astype(np.float16), "AA_metre": MA.astype(np.float16)}
    dossier.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **res)
    return res


# Variantes -------------------------------------------------------------------------
DEFAUT = {"technologie": "WiFi 2.4GHz", "lecture": "voxel", "facteur": 1.0, "S_RX": -65.0, "P_TX": 20.0,
          "alpha": 1.0, "beta": 1.0, "shadowing": True, "graine_X": 0, "groupes": dict(GROUPES),
          "domaine": "duplex"}


def variante(**k) -> dict:
    return {**DEFAUT, **k}


def radios(env: Environnement, c: dict, v: dict) -> tuple[dict[bool, Radio], np.ndarray, np.ndarray]:
    """Radios avec / sans jumeau pour la variante v ; renvoie aussi les masques (positions, voxels)."""
    t = TABLEAU_I[v["technologie"]]
    pire = max(t[m] for m in MATERIAUX_TABLE)
    A, C = env.antennes(), env.centres_libres()
    lignes = np.ones(len(A), bool)
    colonnes = np.ones(len(C), bool)
    if v["domaine"] == "niveau1_10couches":  # lecture « 16 × 34 × 10 » : premier niveau seulement
        z_max = env.origine[2] + 10 * env.pas[2]
        colonnes = C[:, 2] < z_max
        lignes = A[:, 2] < z_max
    Lg = np.array([t.get(v["groupes"][k], pire) for k in sorted(GROUPES)], np.float32)
    rng = np.random.default_rng(v["graine_X"])
    X = rng.normal(0, t["sigma"], (len(A), len(C))).astype(np.float32) if v["shadowing"] else 0
    XA = rng.normal(0, t["sigma"], (len(A), len(A))).astype(np.float32) if v["shadowing"] else 0
    libre = perte_espace_libre(t["PL0"], A, C) + X
    libre_AA = perte_espace_libre(t["PL0"], A, A) + XA
    cle, cle_AA = v["lecture"], f"AA_{v['lecture']}"
    obs_avec = np.tensordot(Lg, c[cle].astype(np.float32), 1)
    obs_sans = pire * c[cle].astype(np.float32).sum(0)
    obsA_avec = np.tensordot(Lg, c[cle_AA].astype(np.float32), 1)
    obsA_sans = pire * c[cle_AA].astype(np.float32).sum(0)
    r = {}
    for jumeau, o, oA in ((True, obs_avec, obsA_avec), (False, obs_sans, obsA_sans)):
        PL = (libre + v["facteur"] * o)[np.ix_(lignes, colonnes)]
        PLA = (libre_AA + v["facteur"] * oA)[np.ix_(lignes, lignes)]
        r[jumeau] = Radio(PL=PL, PL_AA=PLA, P_TX=v["P_TX"], S_RX=v["S_RX"], alpha=v["alpha"], beta=v["beta"])
    return r, lignes, colonnes


def courbe_glouton(r: dict[bool, Radio], n_max: int = 10) -> dict:
    """Fronts gloutons (µ = 0) avec / sans jumeau, toujours évalués avec jumeau."""
    sortie = {}
    for jumeau in (True, False):
        for ind in glouton(r[jumeau], n_max):
            m = r[True].metriques(ind)
            sortie[f"{'avec' if jumeau else 'sans'}_{len(ind)}"] = [m["couverture"], m["qualite_lien_moyenne_dBm"]]
    return sortie


def ecarts_figure4(courbe: dict) -> dict:
    ec_c, ec_q = [], []
    for jumeau in (True, False):
        for n, (c_ref, q_ref) in article.FIGURES[(jumeau, 0)].items():
            c, q = courbe[f"{'avec' if jumeau else 'sans'}_{n}"]
            ec_c.append(abs(c - c_ref))
            ec_q.append(abs(q - q_ref))
    return {"ecart_couverture": round(float(np.mean(ec_c)), 3), "ecart_qualite_dB": round(float(np.mean(ec_q)), 2)}


def resume(courbe: dict) -> dict:
    n90 = min((n for n in range(1, 11) if courbe[f"avec_{n}"][0] >= 0.9), default=None)
    gain = [courbe[f"avec_{n}"][0] - courbe[f"sans_{n}"][0] for n in range(1, 11)]
    gain_q = [courbe[f"avec_{n}"][1] - courbe[f"sans_{n}"][1] for n in range(1, 11)]
    return {"couv_1_avec": courbe["avec_1"][0], "couv_1_sans": courbe["sans_1"][0],
            "qual_1_avec": courbe["avec_1"][1], "q20": n90,
            "gain_couverture_moyen": round(float(np.mean(gain)), 4), "gain_couverture_max": round(float(np.max(gain)), 4),
            "gain_qualite_moyen_dB": round(float(np.mean(gain_q)), 2), **ecarts_figure4(courbe)}


def ga(r: dict[bool, Radio], positions: list[dict], mu: int, jumeau: bool, graine: int, n_it: int = 300) -> dict:
    p = Parametres(n_it=n_it, mu=mu, graine=graine)
    t0 = time.process_time()
    res = prep_nsga(r[jumeau], positions, p)
    front = {}
    for n, (_, ind) in meilleur_par_taille(res.population, res.objectifs).items():
        m = r[True].metriques(ind)
        front[n] = [m["couverture"], m["qualite_lien_moyenne_dBm"], m["connectivite"]]
    return {"front": front, "cpu_s": round(time.process_time() - t0, 1), "historique": res.historique}


def ga_multigraines(r, positions, graines, n_it=300) -> dict:
    sortie = {}
    for jumeau, mu in ((True, 0), (False, 0), (True, 3), (False, 3)):
        runs = [ga(r, positions, mu, jumeau, g, n_it) for g in graines]
        tailles = sorted({n for x in runs for n in x["front"]})
        stat = {}
        for n in tailles:
            vals = np.array([x["front"][n][:2] for x in runs if n in x["front"]], float)
            stat[n] = {"runs": len(vals), "couverture_mediane": round(float(np.median(vals[:, 0])), 4),
                       "couverture_min": round(float(vals[:, 0].min()), 4), "couverture_max": round(float(vals[:, 0].max()), 4),
                       "qualite_mediane": round(float(np.median(vals[:, 1])), 2)}
        sortie[f"{'avec' if jumeau else 'sans'} jumeau, mu={mu}"] = {
            "par_n": stat, "cpu_s_total": round(sum(x["cpu_s"] for x in runs), 1),
            "historique_graine0": runs[0]["historique"]}
    return sortie


# Campagne -----------------------------------------------------------------------------
def campagne(sorties: Path, rapide: bool = False) -> dict:
    geo = json.loads((sorties / "geometry.json").read_text(encoding="utf-8"))
    npz = sorties / geo["voxels"]["fichier"]
    env = Environnement.charger(npz)
    dossier = sorties / "iwcmc" / "campagne"
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "resultats.json"
    R = json.loads(fichier.read_text(encoding="utf-8")) if fichier.is_file() else {}

    def garder(nom, valeur):
        R[nom] = valeur
        ecrire_json(fichier, R)
        print(f"[{time.strftime('%H:%M:%S')}] {nom} terminé", flush=True)

    t0 = time.time()
    g = groupes_voxels(env, npz)
    c = comptes(env, g, dossier)
    pos = geo["positions_autorisees"]
    garder("meta", {"positions": len(pos), "voxels_libres": int(env.libre.sum()),
                    "obstacles_par_groupe": {NOMS_GROUPES[k]: int((g == k).sum()) for k in GROUPES},
                    "temps_comptes_s": round(time.time() - t0, 1)})
    graines = [0, 1] if rapide else [0, 1, 2, 3, 4]

    # C. Facteur sur L_obs, deux lectures (glouton)
    lignes = []
    for lecture in ("voxel", "metre"):
        for k in (1, 2, 5, 10, 15, 20, 25, 30, 35, 40, 50, 75, 100):
            r, _, _ = radios(env, c, variante(lecture=lecture, facteur=k))
            cb = courbe_glouton(r)
            lignes.append({"lecture": lecture, "facteur": k, **resume(cb), "courbe": cb})
    garder("C_facteur", lignes)

    # E. Sensibilité S_RX (tableau I tel quel)
    lignes = []
    for srx in (-65, -60, -55, -50, -45, -40):
        r, _, _ = radios(env, c, variante(S_RX=float(srx)))
        cb = courbe_glouton(r)
        lignes.append({"S_RX": srx, **resume(cb), "courbe": cb})
    garder("E_srx", lignes)

    # F. Domaine « 16 × 34 × 10 » = premier niveau seulement
    lignes = []
    for k in (1, 10, 20, 30, 40):
        r, lig, _ = radios(env, c, variante(facteur=k, domaine="niveau1_10couches"))
        cb = courbe_glouton(r)
        lignes.append({"facteur": k, "positions": int(lig.sum()), "voxels_libres": int(r[True].PL.shape[1]),
                       **resume(cb), "courbe": cb})
    garder("F_domaine_niveau1", lignes)

    # G. Shadowing : sans X, et dispersion selon le tirage de X
    lignes = []
    for k in (1, 30):
        for sh, gx in ((False, 0), (True, 0), (True, 1), (True, 2)):
            r, _, _ = radios(env, c, variante(facteur=k, shadowing=sh, graine_X=gx))
            cb = courbe_glouton(r)
            lignes.append({"facteur": k, "shadowing": sh, "graine_X": gx, **resume(cb)})
    garder("G_shadowing", lignes)

    # H. Part du matériau le plus absorbant : faux plafonds comptés en béton (part ≈ 21 %)
    lignes = []
    part = lambda grp: round(sum(int((g == k).sum()) for k in GROUPES if grp[k] == "plaque_de_platre") / int((g > 0).sum()), 3)
    for nom, grp in (("plafonds en plâtre (réel)", dict(GROUPES)),
                     ("plafonds en béton (synthétique)", {**GROUPES, 6: "mur_beton"}),
                     ("tout le plâtre en béton (synthétique)", {**GROUPES, 1: "mur_beton", 6: "mur_beton"})):
        for k in (1, 30):
            r, _, _ = radios(env, c, variante(facteur=k, groupes=grp))
            cb = courbe_glouton(r)
            lignes.append({"variante": nom, "part_plus_absorbant": part(grp), "facteur": k, **resume(cb), "courbe": cb})
    garder("H_part_platre", lignes)

    # J. Autres technologies (tableau I tel quel et × 30)
    lignes = []
    for tech in TABLEAU_I:
        for k in (1, 30):
            r, _, _ = radios(env, c, variante(technologie=tech, facteur=k))
            cb = courbe_glouton(r)
            pire = max(MATERIAUX_TABLE, key=lambda m: TABLEAU_I[tech][m])
            lignes.append({"technologie": tech, "facteur": k, "plus_absorbant": pire, **resume(cb)})
    garder("J_technologies", lignes)

    # L. Poids α, β (× 30)
    lignes = []
    for a, b in ((1, 1), (1, 0), (0, 1)):
        r, _, _ = radios(env, c, variante(facteur=30, alpha=float(a), beta=float(b)))
        lignes.append({"alpha": a, "beta": b, **resume(courbe_glouton(r))})
    garder("L_poids", lignes)

    # K. Pas d'échantillonnage du lancer de rayons (précision), sur 20 positions
    A, C = env.antennes(), env.centres_libres()
    idx = np.linspace(0, len(A) - 1, 20).astype(int)
    champ = [(g > 0).astype(np.float32)]
    diffs = []
    for i in idx:
        v1, _ = obstacles_traverses(env, A[i], C, champ, pas=0.05)
        v2, _ = obstacles_traverses(env, A[i], C, champ, pas=0.0125)
        diffs.append(np.abs(v1 - v2).ravel())
    d = np.concatenate(diffs)
    garder("K_pas_echantillonnage", {"positions": 20, "ecart_moyen_voxels": round(float(d.mean()), 4),
                                     "ecart_max_voxels": int(d.max()), "part_rayons_identiques": round(float((d == 0).mean()), 4)})

    # A, B, D, I, H-GA : algorithme génétique, plusieurs graines
    r, _, _ = radios(env, c, variante())
    garder("A_ga_tableau_I", ga_multigraines(r, pos, graines))
    r, _, _ = radios(env, c, variante(facteur=30))
    garder("D_ga_facteur30", ga_multigraines(r, pos, graines))
    garder("I_glouton_facteur30", courbe_glouton(r))
    garder("I_ga_iterations_mu3", {str(n_it): ga(r, pos, 3, True, 0, n_it)["front"] for n_it in (100, 300, 1000)})
    r, _, _ = radios(env, c, variante(lecture="metre"))
    garder("B_ga_metre", ga_multigraines(r, pos, [0]))
    r, _, _ = radios(env, c, variante(facteur=30, groupes={**GROUPES, 6: "mur_beton"}))
    garder("H_ga_plafonds_beton_facteur30", ga_multigraines(r, pos, [0]))
    r, lig, _ = radios(env, c, variante(facteur=30, domaine="niveau1_10couches"))
    garder("F_ga_niveau1_facteur30", ga_multigraines(r, [p for p, ok in zip(pos, lig) if ok], [0]))
    garder("duree_totale_s", round(time.time() - t0, 1))
    return R
