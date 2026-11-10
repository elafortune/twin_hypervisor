"""Petit utilitaire MILP (HiGHS, licence MIT) : variables binaires, contraintes linéaires.

Sert aux trois sous-problèmes de couverture de M4 (détecteurs, déclencheurs, caméras).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import highspy
import numpy as np


@dataclass
class Solution:
    x: np.ndarray
    objectif: float
    statut: str
    gap_relatif: float
    temps_s: float


def resoudre(couts, lignes, maximiser: bool = False, limite_s: float = 120.0, continues=()) -> Solution:
    """couts : (n,) ; lignes : liste de (indices, coefficients, borne_inf, borne_sup) ; x ∈ {0, 1}^n,
    sauf les indices `continues` (x ∈ [0, 1] réel, ex. un ratio minimal à maximiser)."""
    n = len(couts)
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", float(limite_s))
    h.setOptionValue("random_seed", 0)
    inf = highspy.kHighsInf
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), np.asarray(couts, float))
    reels = set(continues)
    types = [highspy.HighsVarType.kContinuous if j in reels else highspy.HighsVarType.kInteger for j in range(n)]
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), np.array(types))
    if maximiser:
        h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    for idx, coef, lo, hi in lignes:
        idx = np.asarray(idx, dtype=np.int32)
        h.addRow(-inf if lo is None else float(lo), inf if hi is None else float(hi), len(idx), idx,
                 np.asarray(coef, float))
    t0 = time.perf_counter()
    h.run()
    duree = time.perf_counter() - t0
    statut = h.modelStatusToString(h.getModelStatus())
    info = h.getInfo()
    brut = np.asarray(h.getSolution().col_value[:n]) if n else np.zeros(0)
    x = np.round(brut)
    gap = float(info.mip_gap) if np.isfinite(info.mip_gap) else 0.0
    sol = Solution(x.astype(int), float(info.objective_function_value), statut, gap, round(duree, 3))
    sol.brut = brut
    return sol


def couverture_ensemble(n_candidats: int, couvrants: list[list[int]], couts=None, **k) -> Solution:
    """min Σ c_j x_j  s.c.  Σ_{j ∈ N(i)} x_j ≥ 1 pour chaque élément i."""
    couts = np.ones(n_candidats) if couts is None else couts
    lignes = [(N, np.ones(len(N)), 1, None) for N in couvrants]
    return resoudre(couts, lignes, **k)
