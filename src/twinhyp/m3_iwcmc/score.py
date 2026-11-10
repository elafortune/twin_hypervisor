"""Score de couverture (équations 1, 3, 4), métriques des figures 4–5 et µ-connexité de l'IWCMC."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np


@dataclass
class Radio:
    PL: np.ndarray        # (|A|, F) perte équipement -> voxel libre, en dB (X_σ compris)
    PL_AA: np.ndarray     # (|A|, |A|) perte équipement -> équipement (orientée, X_σ compris)
    P_TX: float = 20.0
    S_RX: float = -65.0
    alpha: float = 1.0
    beta: float = 1.0

    def v2(self, ind) -> np.ndarray:
        """v″ des voxels libres : meilleur serveur (min PL ; lecture I-3), normalisation (3)."""
        v1 = self.P_TX - self.PL[list(ind)].min(0)
        return (v1 - self.S_RX) / (self.P_TX - self.S_RX)

    def f_obj(self, ind) -> float:
        """Équation (4), somme sur les voxels libres (lecture I-4)."""
        v = self.v2(ind)
        return float((self.alpha * v + self.beta * (v > 0)).sum())

    def metriques(self, ind) -> dict:
        """Couverture stricte (fig. 4b) et qualité moyenne de lien (fig. 4a, « relative coverage ») :
        moyenne sur TOUS les voxels libres, un voxel non couvert comptant pour S_RX (lecture I-5).
        La moyenne sur les seuls voxels couverts est donnée en complément."""
        v = self.v2(ind)
        couvert = v > 0
        echelle = self.P_TX - self.S_RX
        qualite = echelle * float(np.clip(v, 0, None).mean()) + self.S_RX
        qualite_couverts = echelle * float(v[couvert].mean()) + self.S_RX if couvert.any() else None
        return {"couverture": round(float(couvert.mean()), 4),
                "qualite_lien_moyenne_dBm": round(qualite, 2),
                "qualite_voxels_couverts_dBm": round(qualite_couverts, 2) if qualite_couverts is not None else None,
                "f_obj": round(self.f_obj(ind), 2),
                "connectivite": connectivite(self, ind)}


def graphe_equipements(r: Radio, ind) -> nx.Graph:
    """Arête si le lien passe dans les DEUX sens (liens unidirectionnels supprimés)."""
    ind = list(ind)
    G = nx.Graph()
    G.add_nodes_from(ind)
    sous = r.PL_AA[np.ix_(ind, ind)]
    ok = (r.P_TX - sous > r.S_RX) & (r.P_TX - sous.T > r.S_RX)
    for a in range(len(ind)):
        for b in range(a + 1, len(ind)):
            if ok[a, b]:
                G.add_edge(ind[a], ind[b])
    return G


def connectivite(r: Radio, ind) -> int:
    """Γ(G_O) = arête-connexité (0 pour un seul équipement ou un graphe non connexe)."""
    if len(ind) < 2:
        return 0
    return int(nx.edge_connectivity(graphe_equipements(r, ind)))


def faisable(r: Radio, ind, mu: int) -> bool:
    if mu <= 0:
        return True
    if len(ind) <= mu:  # λ ≤ δ ≤ n − 1 (Whitney)
        return False
    return connectivite(r, ind) >= mu
