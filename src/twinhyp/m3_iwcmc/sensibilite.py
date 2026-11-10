"""Référence gloutonne et étude de sensibilité de l'atténuation des obstacles.

- `glouton` : ajoute à chaque pas la position qui augmente le plus F_obj (couverture sous-modulaire :
  garantie (1 − 1/e) ; Nemhauser, Wolsey & Fisher, 1978). Sert à valider PREP-NSGA (µ = 0).
- `etude` : pour plusieurs facteurs k appliqués aux L_obs du tableau I et les deux lectures
  (voxel / mètre), front glouton évalué avec jumeau, comparé à la figure 4 de l'IWCMC.
  Objectif : mesurer de combien il faudrait renforcer l'atténuation pour retrouver les courbes.
"""

from __future__ import annotations

import numpy as np

from twinhyp.m3_iwcmc import article
from twinhyp.m3_iwcmc.score import Radio


def glouton(r: Radio, n_max: int = 10) -> list[tuple]:
    choisis, meilleur_pl, solutions = [], np.full(r.PL.shape[1], np.inf, np.float32), []
    for _ in range(n_max):
        cand = np.minimum(meilleur_pl[None, :], r.PL)                        # (|A|, F)
        v = (r.P_TX - cand - r.S_RX) / (r.P_TX - r.S_RX)
        score = (r.alpha * v + r.beta * (v > 0)).sum(1)
        score[choisis] = -np.inf
        a = int(np.argmax(score))
        choisis.append(a)
        meilleur_pl = cand[a]
        solutions.append(tuple(sorted(choisis)))
    return solutions


def etude(construire_radios, facteurs=(1, 2, 5, 10, 20, 50), lectures=("voxel", "metre"), n_max: int = 10) -> list[dict]:
    """`construire_radios(k, lecture)` -> {True: Radio avec jumeau, False: Radio sans jumeau}."""
    lignes = []
    for lecture in lectures:
        for k in facteurs:
            r = construire_radios(k, lecture)
            courbe = {}
            for jumeau in (True, False):
                for ind in glouton(r[jumeau], n_max):
                    m = r[True].metriques(ind)
                    courbe[(jumeau, len(ind))] = (m["couverture"], m["qualite_lien_moyenne_dBm"])
            ecart = [abs(courbe[(j, n)][0] - article.FIGURES[(j, 0)][n][0])
                     for j in (True, False) for n in range(1, n_max + 1)]
            lignes.append({"lecture": lecture, "facteur": k,
                           "couverture_1_avec": courbe[(True, 1)][0], "couverture_1_sans_evaluee_avec": courbe[(False, 1)][0],
                           "qualite_1_avec": courbe[(True, 1)][1],
                           "n_90_avec": min((n for n in range(1, n_max + 1) if courbe[(True, n)][0] >= 0.9), default=None),
                           "ecart_moyen_couverture_fig4": round(float(np.mean(ecart)), 3),
                           "courbe": {f"{'avec' if j else 'sans'}_{n}": v for (j, n), v in courbe.items()}})
    return lignes
