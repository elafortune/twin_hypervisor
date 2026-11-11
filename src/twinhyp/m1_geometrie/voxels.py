"""Étape 6 – grille de voxels avec matériau, et positions autorisées au plafond ([IWCMC] §III.A).

Une seule primitive géométrique sert aux deux calculs : le **rayon vertical**.
- Voxelisation : chaque voxel est échantillonné par `SOUS_ECHANTILLONS²` colonnes verticales ;
  le long d'une colonne, l'intérieur d'un solide fermé est donné par la parité des
  intersections (théorème de Jordan) -> intervalles [z_entrée, z_sortie]. La fraction du
  voxel occupée par chaque élément en découle ; le voxel est un obstacle (v = 0) dès
  qu'un élément obstacle l'occupe, et prend la catégorie de matériau de l'élément qui
  l'occupe le plus.
- Positions autorisées A_i : pour chaque niveau i et chaque centre de colonne (pas ρ),
  rayon vers le haut depuis le plancher ; le premier impact sur un élément « plafond »
  (couverture, dalle, toit) donne un point de A_i s'il est au-dessus d'un espace occupable
  du niveau.

Intersection rayon vertical / triangle : coordonnées barycentriques dans le plan XY
(cas particulier de Möller–Trumbore quand la direction est (0, 0, 1)).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from shapely import contains_xy
from shapely.geometry import Polygon

from twinhyp.m1_geometrie import ifc_outils as io

# Catégories de matériau = colonnes du tableau I de l'IWCMC (+ libre et « autre »).
CATEGORIES = {0: "libre", 1: "plaque_de_platre", 2: "mur_beton", 3: "mur_porteur", 4: "bois", 5: "autre"}
CODE = {v: k for k, v in CATEGORIES.items()}

# Table déclarative nom de matériau IFC -> catégorie (première expression qui correspond).
MATERIAUX = [
    (r"plaster|gypsum|plâtre|platre", "plaque_de_platre"),
    (r"masonry|brick|block|brique|parpaing|maçonnerie", "mur_porteur"),
    (r"concrete|béton|beton|ceramic|grout|carrelage", "mur_beton"),
    (r"wood|bois|plywood|timber|lumber", "bois"),
]
# Couches sans effet retenu sur la catégorie (lame d'air, isolant, ossature métallique, membranes).
NEGLIGEABLES = r"air|insulation|isolant|stud|membrane|barrier|grass|epdm"

# Éléments obstacles (IWCMC : murs, toits, plafonds ; + portes, colonne « wooden door » du tableau I).
CLASSES_OBSTACLES = ("IfcWall", "IfcSlab", "IfcRoof", "IfcCovering", "IfcDoor")
CLASSES_PLAFOND = ("IfcCovering", "IfcSlab", "IfcRoof")
SOUS_ECHANTILLONS = 5            # 5 x 5 colonnes par voxel (0,1 m pour un pas de 0,5 m)
DECALAGE = np.array([1.37e-4, 2.71e-4])  # évite les rayons passant exactement par une arête
HAUTEUR_DEPART_PLAFOND_M = 0.5   # origine des rayons vers le plafond, au-dessus du plancher


# Géométrie ------------------------------------------------------------------------
def triangles(m: io.Maillage) -> np.ndarray:
    return m.sommets[m.faces]  # (M, 3, 3)


def impacts_verticaux(colonnes: np.ndarray, tri: np.ndarray) -> list[np.ndarray]:
    """Altitudes des intersections de chaque colonne verticale (K, 2) avec les triangles (M, 3, 3)."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    v0, v1 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2]
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-12  # faces verticales : projection dégénérée, jamais coupées par un rayon vertical
    a, b, c, v0, v1, den = a[ok], b[ok], c[ok], v0[ok], v1[ok], den[ok]
    resultat = []
    for debut in range(0, len(colonnes), 2048):  # par paquets pour borner la mémoire
        P = colonnes[debut:debut + 2048]
        d = P[:, None, :] - a[None, :, :2]
        u = (d[..., 0] * v1[:, 1] - v1[:, 0] * d[..., 1]) / den
        v = (v0[:, 0] * d[..., 1] - d[..., 0] * v0[:, 1]) / den
        dedans = (u >= 0) & (v >= 0) & (u + v <= 1)
        z = a[:, 2] + u * (b[:, 2] - a[:, 2]) + v * (c[:, 2] - a[:, 2])
        resultat += [np.sort(z[k][dedans[k]]) for k in range(len(P))]
    return resultat


def intervalles(z: np.ndarray) -> list[tuple[float, float]]:
    """Parité : entrées/sorties successives ; un nombre impair (maillage non fermé) -> [min, max]."""
    z = np.unique(np.round(z, 6))
    if len(z) < 2:
        return []
    if len(z) % 2:
        return [(float(z[0]), float(z[-1]))]
    return [(float(z[i]), float(z[i + 1])) for i in range(0, len(z), 2)]


# Matériaux ------------------------------------------------------------------------
def categorie_materiau(nom: str | None) -> str | None:
    nom = (nom or "").lower()
    if re.search(NEGLIGEABLES, nom):
        return None
    return next((cat for motif, cat in MATERIAUX if re.search(motif, nom)), None)


def composition(element) -> list[tuple[str, float]]:
    """Couches (nom, épaisseur) ; une seule « couche » d'épaisseur nulle si matériau simple."""
    import ifcopenshell.util.element as ue
    m = ue.get_material(element, should_skip_usage=True)
    if m is None:
        return []
    if m.is_a("IfcMaterialLayerSet"):
        return [(l.Material.Name if l.Material else "", float(l.LayerThickness or 0)) for l in m.MaterialLayers]
    if m.is_a("IfcMaterial"):
        return [(m.Name, 0.0)]
    if m.is_a("IfcMaterialList"):
        return [(x.Name, 0.0) for x in m.Materials]
    return []


def categorie_element(element) -> tuple[str, dict[str, float]]:
    """Catégorie dominante (plus forte épaisseur cumulée parmi les couches significatives)
    et part de chaque catégorie dans l'épaisseur significative (pour M3)."""
    if element.is_a("IfcDoor"):
        return "bois", {"bois": 1.0}
    cumul: dict[str, float] = {}
    for nom, ep in composition(element):
        cat = categorie_materiau(nom)
        if cat:
            cumul[cat] = cumul.get(cat, 0.0) + (ep or 1.0)
    if not cumul:
        return "autre", {"autre": 1.0}
    total = sum(cumul.values())
    return max(cumul, key=cumul.get), {k: round(v / total, 3) for k, v in cumul.items()}


# Grille ----------------------------------------------------------------------------
@dataclass
class Grille:
    origine: np.ndarray       # (3,) coin inférieur
    pas: np.ndarray           # (3,) dx, dy, dz
    forme: tuple[int, int, int]

    def centres_xy(self) -> np.ndarray:
        nx, ny, _ = self.forme
        i, j = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
        return np.stack([self.origine[0] + (i + 0.5) * self.pas[0], self.origine[1] + (j + 0.5) * self.pas[1]], -1)


def definir_grille(geometrie: dict, pas_xy: float, pas_z: float) -> Grille:
    """Domaine = emprise des espaces occupables (IWCMC : 16 x 34 voxels de 0,5 m pour le duplex),
    du plancher du plus bas niveau occupé au sommet de l'espace occupable le plus haut."""
    occ = [e for e in geometrie["espaces"] if e["occupable"]]
    pts = np.array([p for e in occ for p in e["polygone_xy"]])
    zmin = min(e["z_bas_m"] for e in occ)
    zmax = max(e["z_bas_m"] + e["hauteur_m"] for e in occ)
    bas = np.array([pts[:, 0].min(), pts[:, 1].min(), round(zmin / pas_z) * pas_z])
    pas = np.array([pas_xy, pas_xy, pas_z])
    haut = np.array([pts[:, 0].max(), pts[:, 1].max(), zmax])
    forme = tuple(int(np.ceil((haut[d] - bas[d]) / pas[d] - 1e-6)) for d in range(3))
    return Grille(bas, pas, forme)


def voxeliser(f, grille: Grille) -> dict:
    nx, ny, nz = grille.forme
    s = SOUS_ECHANTILLONS
    # colonnes fines : s x s par voxel
    fx = grille.origine[0] + (np.arange(nx * s) + 0.5) * grille.pas[0] / s
    fy = grille.origine[1] + (np.arange(ny * s) + 0.5) * grille.pas[1] / s
    FX, FY = np.meshgrid(fx, fy, indexing="ij")
    colonnes = np.stack([FX.ravel(), FY.ravel()], -1) + DECALAGE
    vi, vj = (np.arange(nx * s)[:, None] // s * np.ones(ny * s, int)).ravel(), \
             (np.ones(nx * s, int)[:, None] * (np.arange(ny * s) // s)).ravel()
    zbas = grille.origine[2] + np.arange(nz) * grille.pas[2]

    elements, occupation = [], []
    for el in sorted((e for c in CLASSES_OBSTACLES for e in f.by_type(c)), key=lambda e: e.GlobalId):
        if el.is_a("IfcRoof") and el.IsDecomposedBy:
            continue  # le toit est porté par ses dalles décomposées
        m = io.maillage(el)
        if m is None:
            continue
        lo, hi = m.sommets.min(0), m.sommets.max(0)
        if hi[2] < zbas[0] or lo[2] > zbas[-1] + grille.pas[2]:
            continue
        dans = ((colonnes[:, 0] >= lo[0]) & (colonnes[:, 0] <= hi[0]) &
                (colonnes[:, 1] >= lo[1]) & (colonnes[:, 1] <= hi[1]))
        idx = np.flatnonzero(dans)
        if not len(idx):
            continue
        occ = np.zeros(grille.forme, dtype=np.float32)
        for k, z in zip(idx, impacts_verticaux(colonnes[idx], triangles(m))):
            for z0, z1 in intervalles(z):
                recouvrement = np.clip(np.minimum(z1, zbas + grille.pas[2]) - np.maximum(z0, zbas), 0, None)
                occ[vi[k], vj[k]] += recouvrement / grille.pas[2] / (s * s)
        if occ.any():
            elements.append(el)
            occupation.append(occ)

    pile = np.stack(occupation) if occupation else np.zeros((1, *grille.forme), np.float32)
    dominant = pile.argmax(0)
    total = pile.sum(0)
    cats = [categorie_element(el) for el in elements]
    code_el = np.array([CODE[c] for c, _ in cats], dtype=np.uint8)
    materiau = np.where(total > 0, code_el[dominant], 0).astype(np.uint8)
    return {"libre": (total == 0).astype(np.uint8),           # v = 1 libre, 0 obstacle (IWCMC)
            "materiau": materiau,
            "fraction_obstacle": np.clip(total, 0, 1).astype(np.float16),
            "element": np.where(total > 0, dominant, -1).astype(np.int16),
            "elements": [{"globalId": el.GlobalId, "classe": el.is_a(), "nom": el.Name,
                          "categorie": c, "composition": comp} for el, (c, comp) in zip(elements, cats)]}


def positions_plafond(f, geometrie: dict, grille: Grille) -> list[dict]:
    """A = ∪ A_i : impacts des rayons verticaux sur les plafonds, au-dessus des espaces occupables."""
    plafonds = []
    for el in (e for c in CLASSES_PLAFOND for e in f.by_type(c)):
        if el.is_a("IfcRoof") and el.IsDecomposedBy:
            continue
        m = io.maillage(el)
        if m is not None:
            plafonds.append(triangles(m))
    tri = np.concatenate(plafonds)
    centres = grille.centres_xy().reshape(-1, 2) + DECALAGE
    impacts = impacts_verticaux(centres, tri)
    positions = []
    for n in geometrie["niveaux"]:
        espaces = [e for e in geometrie["espaces"] if e["occupable"] and e["niveau_globalId"] == n["globalId"]]
        if not espaces:
            continue
        z0 = n["altitude_m"] + HAUTEUR_DEPART_PLAFOND_M
        for e in espaces:
            dedans = np.flatnonzero(contains_xy(Polygon(e["polygone_xy"]), centres[:, 0], centres[:, 1]))
            avant = len(positions)
            for k in dedans:
                z = impacts[k][impacts[k] > z0]
                if len(z):
                    positions.append({"niveau_globalId": n["globalId"], "espace_globalId": e["globalId"],
                                      "xyz": [round(float(centres[k, 0] - DECALAGE[0]), 3),
                                              round(float(centres[k, 1] - DECALAGE[1]), 3),
                                              round(float(z[0]), 3)]})
            if len(positions) == avant:
                # aucun plafond modélisé au-dessus de l'espace (2e IFC : local technique 219 ouvert) :
                # repli sur le sommet de l'espace (z_bas + hauteur), pour ne pas laisser un espace occupable sans détecteur
                haut = round(float(e["z_bas_m"] + e["hauteur_m"]), 3)
                positions += [{"niveau_globalId": n["globalId"], "espace_globalId": e["globalId"],
                               "xyz": [round(float(centres[k, 0] - DECALAGE[0]), 3),
                                       round(float(centres[k, 1] - DECALAGE[1]), 3), haut]} for k in dedans]
    return positions


def calculer(f, geometrie: dict, params: dict) -> tuple[Grille, dict, list[dict], dict]:
    pas_xy = float(params.get("pas_grille_m", 0.5))
    pas_z = float(params.get("pas_grille_vertical_m", pas_xy / 2))  # IWCMC : 50 x 50 x 25 cm
    grille = definir_grille(geometrie, pas_xy, pas_z)
    vox = voxeliser(f, grille)
    A = positions_plafond(f, geometrie, grille)
    obstacles = vox["libre"] == 0
    par_cat = {CATEGORIES[c]: int(((vox["materiau"] == c) & obstacles).sum()) for c in CATEGORIES if c}
    resume = {
        "origine_m": [round(float(x), 3) for x in grille.origine], "pas_m": [float(x) for x in grille.pas],
        "dimensions": list(grille.forme), "voxels": int(np.prod(grille.forme)),
        "voxels_libres": int((~obstacles).sum()), "voxels_obstacles": int(obstacles.sum()),
        "obstacles_par_categorie": par_cat,
        "part_plaque_de_platre": round(par_cat.get("plaque_de_platre", 0) / max(int(obstacles.sum()), 1), 3),
        "positions_par_niveau": {n["nom"]: sum(1 for a in A if a["niveau_globalId"] == n["globalId"])
                                 for n in geometrie["niveaux"]},
    }
    return grille, vox, A, resume
