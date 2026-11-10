"""Connectivité radio du réseau SSI avec le modèle de M3 (équation 2 de l'IWCMC, sans shadowing).

Arête entre deux équipements si le lien passe dans les deux sens (P_TX − PL > S_RX) ; on rapporte
l'arête-connexité λ et, si le réseau n'est pas connexe, on ajoute des relais IoTNode (glouton :
la position autorisée qui relie le plus de composantes)."""

from __future__ import annotations

import networkx as nx
import numpy as np

from twinhyp.m3_iwcmc.radio import TABLEAU_I, Environnement, obstacles_traverses, perte_espace_libre


def matrice_pertes(env: Environnement, pts: np.ndarray, techno: str, facteur: float, lecture: str = "voxel") -> np.ndarray:
    t = TABLEAU_I[techno]
    L = [env.attenuation_par_voxel(techno, True)]
    PL = perte_espace_libre(t["PL0"], pts, pts).astype(float)
    for i, p in enumerate(pts):
        v, m = obstacles_traverses(env, p, pts, L)
        PL[i] += facteur * (v[0] if lecture == "voxel" else m[0])
    return PL


def graphe(PL: np.ndarray, P_TX: float, S_RX: float) -> nx.Graph:
    ok = (P_TX - PL > S_RX) & (P_TX - PL.T > S_RX)
    G = nx.Graph()
    G.add_nodes_from(range(len(PL)))
    G.add_edges_from((i, j) for i in range(len(PL)) for j in range(i + 1, len(PL)) if ok[i, j])
    return G


def analyser(env: Environnement, pts: np.ndarray, cfg: dict, facteur: float) -> dict:
    PL = matrice_pertes(env, pts, cfg["technologie"], facteur, cfg.get("lecture_L_obs", "voxel"))
    G = graphe(PL, cfg["P_TX_dBm"], cfg["S_RX_dBm"])
    return {"facteur_attenuation": facteur, "aretes": G.number_of_edges(),
            "composantes": nx.number_connected_components(G),
            "arete_connexite": int(nx.edge_connectivity(G)) if nx.is_connected(G) and len(G) > 1 else 0}


def relais(env: Environnement, pts: np.ndarray, candidats: np.ndarray, cfg: dict, facteur: float,
           max_relais: int = 10) -> list[int]:
    """Ajoute des relais (indices de `candidats`) jusqu'à rendre le réseau connexe."""
    choisis = []
    for _ in range(max_relais):
        tous = np.vstack([pts, candidats[choisis]]) if choisis else pts
        G = graphe(matrice_pertes(env, tous, cfg["technologie"], facteur), cfg["P_TX_dBm"], cfg["S_RX_dBm"])
        if nx.is_connected(G):
            break
        comp = {n: k for k, c in enumerate(nx.connected_components(G)) for n in c}
        t = TABLEAU_I[cfg["technologie"]]
        L = [env.attenuation_par_voxel(cfg["technologie"], True)]
        meilleur, gain = None, 0
        for j, c in enumerate(candidats):
            if j in choisis:
                continue
            v, _ = obstacles_traverses(env, c, tous, L)
            pl = perte_espace_libre(t["PL0"], c[None, :], tous)[0] + facteur * v[0]
            relies = {comp[i] for i in np.flatnonzero(cfg["P_TX_dBm"] - pl > cfg["S_RX_dBm"])}
            if len(relies) > gain:
                meilleur, gain = j, len(relies)
        if meilleur is None or gain < 2:
            break
        choisis.append(meilleur)
    return choisis
