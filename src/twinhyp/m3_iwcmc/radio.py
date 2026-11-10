"""Modèle radio multi-murs de l'IWCMC (équation 2, tableau I) sur la grille de voxels de M1.

PL[o, p] = PL0 + 20 log10 ||o - p|| + Σ_{obs ∈ Θ} L_obs + X_σ

Θ = voxels obstacles traversés par le segment [o, p] (échantillonné finement ; le voxel
de l'équipement, collé au plafond, n'est pas compté). Deux lectures de L_obs (dB/m) :
- « voxel »  (principale, option 2) : L_obs ajouté une fois par voxel obstacle traversé ;
- « metre »  (sensibilité, option 1) : L_obs × longueur traversée dans l'obstacle.
Environnement « sans jumeau » : même géométrie, tous les obstacles dans le matériau le plus
absorbant de la technologie.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Tableau I de l'IWCMC (d'après Kacou et al., 2018). L en dB/m, PL0 et sigma en dB.
TABLEAU_I = {
    "IoT":       {"PL0": 31.61, "bois": 0.21, "plaque_de_platre": 0.15, "mur_beton": 0.09, "mur_porteur": 0.10, "sigma": 2.24},
    "GSM":       {"PL0": 31.60, "bois": 0.18, "plaque_de_platre": 0.12, "mur_beton": 0.10, "mur_porteur": 0.14, "sigma": 2.60},
    "DETC":      {"PL0": 36.05, "bois": 0.25, "plaque_de_platre": 0.23, "mur_beton": 0.16, "mur_porteur": 0.21, "sigma": 2.97},
    "WiFi 2.4GHz": {"PL0": 37.15, "bois": 0.23, "plaque_de_platre": 0.32, "mur_beton": 0.18, "mur_porteur": 0.22, "sigma": 3.26},
    "5G":        {"PL0": 40.27, "bois": 0.46, "plaque_de_platre": 0.21, "mur_beton": 0.24, "mur_porteur": 0.24, "sigma": 3.64},
    "WiFi 5.2GHz": {"PL0": 45.33, "bois": 0.13, "plaque_de_platre": 0.13, "mur_beton": 0.24, "mur_porteur": 0.30, "sigma": 4.59},
    "WiFi 5.5GHz": {"PL0": 48.23, "bois": 0.19, "plaque_de_platre": 0.13, "mur_beton": 0.21, "mur_porteur": 0.26, "sigma": 4.58},
}
MATERIAUX_TABLE = ("bois", "plaque_de_platre", "mur_beton", "mur_porteur")
PAS_ECHANTILLON_M = 0.05


@dataclass
class Environnement:
    origine: np.ndarray
    pas: np.ndarray
    libre: np.ndarray        # (nx, ny, nz) uint8
    materiau: np.ndarray     # (nx, ny, nz) uint8, codes de voxels.CATEGORIES
    categories: dict[int, str]
    positions: np.ndarray    # (|A|, 3)

    @classmethod
    def charger(cls, chemin_npz: Path) -> "Environnement":
        d = np.load(chemin_npz)
        cats = {int(k): v for k, v in json.loads(str(d["categories"])).items()}
        return cls(d["origine"], d["pas"], d["libre"], d["materiau"], cats, d["positions"].astype(float))

    @property
    def forme(self):
        return self.libre.shape

    def centres_libres(self) -> np.ndarray:
        i, j, k = np.nonzero(self.libre)
        return self.origine + (np.stack([i, j, k], -1) + 0.5) * self.pas

    def antennes(self) -> np.ndarray:
        """Point d'émission de chaque position autorisée : centre du voxel LIBRE le plus proche dans
        la couche juste sous le voxel du plafond (l'impact du rayon tombe dans le voxel obstacle du
        faux plafond ; au-dessus d'un mur, on se décale d'un voxel). Lecture I-10."""
        nx, ny, nz = self.forme
        ijk = np.clip(np.floor((self.positions - self.origine) / self.pas).astype(int), 0, [nx - 1, ny - 1, nz - 1])
        sortie = self.positions.copy()
        for n, (i, j, k) in enumerate(ijk):
            for kk in range(k - 1, max(k - 4, -1), -1):
                voisins = [(a, b) for a in range(max(i - 1, 0), min(i + 2, nx)) for b in range(max(j - 1, 0), min(j + 2, ny))
                           if self.libre[a, b, kk]]
                if voisins:
                    a, b = min(voisins, key=lambda v: (v[0] - i) ** 2 + (v[1] - j) ** 2)
                    sortie[n] = self.origine + (np.array([a, b, kk]) + 0.5) * self.pas
                    break
        return sortie

    def attenuation_par_voxel(self, techno: str, avec_jumeau: bool) -> np.ndarray:
        """L_obs (dB/m) de chaque voxel ; 0 pour un voxel libre."""
        t = TABLEAU_I[techno]
        pire = max(t[m] for m in MATERIAUX_TABLE)
        L = np.zeros(self.forme, dtype=np.float32)
        obstacle = self.libre == 0
        if not avec_jumeau:
            L[obstacle] = pire
            return L
        for code, nom in self.categories.items():
            if code:
                L[(self.materiau == code) & obstacle] = t.get(nom, pire)  # « autre » -> le plus absorbant
        return L


def indice_voxel(env: Environnement, pts: np.ndarray) -> np.ndarray:
    ijk = np.floor((pts - env.origine) / env.pas).astype(np.int64)
    nx, ny, nz = env.forme
    np.clip(ijk[..., 0], 0, nx - 1, out=ijk[..., 0])
    np.clip(ijk[..., 1], 0, ny - 1, out=ijk[..., 1])
    np.clip(ijk[..., 2], 0, nz - 1, out=ijk[..., 2])
    return (ijk[..., 0] * ny + ijk[..., 1]) * nz + ijk[..., 2]


def obstacles_traverses(env: Environnement, source: np.ndarray, cibles: np.ndarray,
                        L_vox: list[np.ndarray], pas: float = PAS_ECHANTILLON_M) -> tuple[np.ndarray, np.ndarray]:
    """Pour chaque champ L de `L_vox` et chaque cible :
    - lecture « voxel » : Σ L sur les voxels obstacles distincts traversés ;
    - lecture « mètre » : Σ L × longueur traversée.
    Renvoie deux tableaux (len(L_vox), len(cibles))."""
    Ls = np.stack([L.ravel() for L in L_vox])
    d = cibles - source
    longueur = np.linalg.norm(d, axis=1)
    n = max(int(np.ceil(longueur.max() / pas)), 1)
    t = (np.arange(n) + 0.5) / n
    par_voxel = np.zeros((len(Ls), len(cibles)), np.float32)
    par_metre = np.zeros_like(par_voxel)
    v_source = indice_voxel(env, source[None, :])[0]
    for debut in range(0, len(cibles), 1024):
        fin = debut + 1024
        pts = source + t[None, :, None] * d[debut:fin, None, :]
        idx = indice_voxel(env, pts)                           # (K, n)
        nouveau = np.ones_like(idx, dtype=bool)
        nouveau[:, 1:] = idx[:, 1:] != idx[:, :-1]
        hors_source = idx != v_source                          # l'équipement est collé à son plafond
        for c in range(len(Ls)):
            Lp = Ls[c][idx] * hors_source
            par_voxel[c, debut:fin] = (Lp * nouveau).sum(1)
            par_metre[c, debut:fin] = Lp.sum(1) * (longueur[debut:fin] / n)
    return par_voxel, par_metre


def matrices_obstacles(env: Environnement, sources: np.ndarray, cibles: np.ndarray,
                       L_vox: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """(len(L_vox), |sources|, |cibles|) pour les lectures « voxel » et « mètre »."""
    V = np.zeros((len(L_vox), len(sources), len(cibles)), np.float32)
    M = np.zeros_like(V)
    for i, s in enumerate(sources):
        V[:, i], M[:, i] = obstacles_traverses(env, s, cibles, L_vox)
    return V, M


def perte_espace_libre(PL0: float, sources: np.ndarray, cibles: np.ndarray) -> np.ndarray:
    d = np.linalg.norm(sources[:, None, :] - cibles[None, :, :], axis=-1)
    return (PL0 + 20 * np.log10(np.maximum(d, 1e-3))).astype(np.float32)
