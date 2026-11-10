"""PREP-NSGA (algorithme 1 de l'IWCMC) : NSGA-II sans croisement, mutations, peine de mort.

Individu = ensemble trié d'indices de positions autorisées (taille variable).
Objectifs : minimiser |O|, maximiser F_obj. Contrainte : Γ(G_O) ≥ µ (mutants infaisables rejetés).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from twinhyp.m3_iwcmc.score import Radio, faisable


@dataclass
class Parametres:
    n_it: int = 300
    n_pop: int = 40
    n_mu: int = 160
    gamma_m: float = 2.0
    mu: int = 0
    n_max: int = 10          # borne de l'axe des figures 4–5 (lecture I-9)
    graine: int = 0


@dataclass
class Resultat:
    population: list[tuple]
    objectifs: dict
    historique: list[dict] = field(default_factory=list)


# Tri non dominé et encombrement (Deb et al., 2002) ----------------------------------
def domine(a, b) -> bool:
    """a = (n, f) : minimiser n, maximiser f."""
    return a[0] <= b[0] and a[1] >= b[1] and (a[0] < b[0] or a[1] > b[1])


def fronts(objs: list[tuple]) -> list[list[int]]:
    n = len(objs)
    domines = [[] for _ in range(n)]
    compte = [0] * n
    F = [[]]
    for p in range(n):
        for q in range(n):
            if domine(objs[p], objs[q]):
                domines[p].append(q)
            elif domine(objs[q], objs[p]):
                compte[p] += 1
        if compte[p] == 0:
            F[0].append(p)
    i = 0
    while F[i]:
        suivant = []
        for p in F[i]:
            for q in domines[p]:
                compte[q] -= 1
                if compte[q] == 0:
                    suivant.append(q)
        i += 1
        F.append(suivant)
    return F[:-1]


def encombrement(objs: list[tuple], front: list[int]) -> dict[int, float]:
    d = {i: 0.0 for i in front}
    for m in range(2):
        tri = sorted(front, key=lambda i: objs[i][m])
        d[tri[0]] = d[tri[-1]] = float("inf")
        etendue = objs[tri[-1]][m] - objs[tri[0]][m] or 1.0
        for k in range(1, len(tri) - 1):
            d[tri[k]] += (objs[tri[k + 1]][m] - objs[tri[k - 1]][m]) / etendue
    return d


def selection(pop: list[tuple], objs: list[tuple], n: int) -> list[int]:
    garde = []
    for f in fronts(objs):
        if len(garde) + len(f) <= n:
            garde += f
        else:
            d = encombrement(objs, f)
            garde += sorted(f, key=lambda i: -d[i])[: n - len(garde)]
            break
    return garde


# Initialisation et mutations -------------------------------------------------------
def cellules_interet(positions: list[dict]) -> list[int]:
    """Une cellule par espace : la position autorisée la plus proche du centre des positions de l'espace
    (lecture I-7 : « cells of interest based on the building structure »)."""
    par_espace: dict[str, list[int]] = {}
    for i, a in enumerate(positions):
        par_espace.setdefault(a["espace_globalId"], []).append(i)
    cellules = []
    for idx in par_espace.values():
        P = np.array([positions[i]["xyz"] for i in idx])
        c = P.mean(0)
        cellules.append(idx[int(np.argmin(np.linalg.norm(P - c, axis=1)))])
    return sorted(cellules)


def initialiser(r: Radio, positions: list[dict], p: Parametres, rng) -> list[tuple]:
    cellules = cellules_interet(positions)
    pop, essais = set(), 0
    while len(pop) < p.n_pop and essais < 100 * p.n_pop:
        essais += 1
        k = int(rng.integers(max(1, p.mu + 1), min(p.n_max, len(cellules)) + 1))
        ind = tuple(sorted(rng.choice(cellules, size=k, replace=False).tolist()))
        if faisable(r, ind, p.mu):
            pop.add(ind)
    return sorted(pop)


def muter(ind: tuple, xyz: np.ndarray, p: Parametres, rng) -> tuple:
    ind = list(ind)
    choix = rng.integers(3)
    if choix == 0:   # déplacer un équipement dans un cercle de rayon γ (même hauteur de plafond)
        k = int(rng.integers(len(ind)))
        o = xyz[ind[k]]
        proches = np.flatnonzero((np.linalg.norm(xyz[:, :2] - o[:2], axis=1) <= p.gamma_m)
                                 & (np.abs(xyz[:, 2] - o[2]) < 0.5))
        ind[k] = int(rng.choice(proches))
    elif choix == 1 and len(ind) > 1:  # retirer un équipement
        ind.pop(int(rng.integers(len(ind))))
    elif len(ind) < p.n_max:           # ajouter un équipement n'importe où sur A
        ind.append(int(rng.integers(len(xyz))))
    return tuple(sorted(set(ind)))


def prep_nsga(r: Radio, positions: list[dict], p: Parametres, journal_tous: int = 50) -> Resultat:
    rng = np.random.default_rng(p.graine)
    xyz = np.array([a["xyz"] for a in positions])
    cache: dict[tuple, float] = {}

    def objectif(ind):
        if ind not in cache:
            cache[ind] = r.f_obj(ind)
        return (len(ind), cache[ind])

    pop = initialiser(r, positions, p, rng)
    historique = []
    if not pop:
        return Resultat([], {}, [{"iteration": 0, "remarque": "aucun individu initial faisable"}])
    for it in range(p.n_it):
        candidats = set(pop)
        for _ in range(p.n_mu):
            parent = pop[int(rng.integers(len(pop)))]
            enfant = muter(parent, xyz, p, rng)
            if enfant and enfant not in candidats and faisable(r, enfant, p.mu):
                candidats.add(enfant)
        candidats = sorted(candidats)
        objs = [objectif(c) for c in candidats]
        pop = [candidats[i] for i in selection(candidats, objs, p.n_pop)]
        if it % journal_tous == 0 or it == p.n_it - 1:
            meilleurs = meilleur_par_taille(pop, cache)
            historique.append({"iteration": it, "f_obj_par_n": {n: round(f, 1) for n, (f, _) in meilleurs.items()}})
    return Resultat(pop, {ind: cache[ind] for ind in pop}, historique)


def meilleur_par_taille(pop: list[tuple], f: dict) -> dict[int, tuple[float, tuple]]:
    """Point du front pour chaque nombre d'équipements : meilleur F_obj à taille fixée."""
    meilleurs = {}
    for ind in pop:
        n = len(ind)
        if n not in meilleurs or f[ind] > meilleurs[n][0]:
            meilleurs[n] = (f[ind], ind)
    return dict(sorted(meilleurs.items()))
