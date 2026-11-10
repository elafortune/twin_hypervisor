"""Outils IFC génériques : ouverture, unités, géométrie monde, rattachement spatial.

Rien ici ne dépend du duplex : tout passe par les types et relations IFC.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu
import numpy as np
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid


def ouvrir(chemin) -> ifcopenshell.file:
    return ifcopenshell.open(str(chemin))


def echelle_longueur(f: ifcopenshell.file) -> float:
    """Facteur vers le mètre des longueurs stockées dans les attributs (ex. 0.001 si mm)."""
    return float(uu.calculate_unit_scale(f))


@lru_cache(maxsize=1)
def reglages_geometrie() -> ifcopenshell.geom.settings:
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)  # sommets directement en coordonnées monde, en mètres
    return s


@dataclass
class Maillage:
    sommets: np.ndarray  # (n, 3) en mètres, repère monde
    faces: np.ndarray    # (m, 3) indices

    @property
    def zmin(self) -> float:
        return float(self.sommets[:, 2].min())

    @property
    def zmax(self) -> float:
        return float(self.sommets[:, 2].max())

    @property
    def centre(self) -> np.ndarray:
        return (self.sommets.min(axis=0) + self.sommets.max(axis=0)) / 2


def maillage(element) -> Maillage | None:
    """Maillage triangulé d'un élément, ou None s'il n'a pas de géométrie."""
    try:
        forme = ifcopenshell.geom.create_shape(reglages_geometrie(), element)
    except Exception:  # élément sans représentation exploitable
        return None
    v = np.asarray(forme.geometry.verts, dtype=float).reshape(-1, 3)
    t = np.asarray(forme.geometry.faces, dtype=int).reshape(-1, 3)
    return Maillage(v, t) if len(v) and len(t) else None


def empreinte(m: Maillage, tolerance: float = 0.005) -> Polygon | MultiPolygon:
    """Projection 2D d'un maillage : union des triangles projetés sur le plan XY.

    Fonctionne quel que soit le type de représentation IFC (extrusion, B-rep…),
    contrairement à la lecture directe du profil extrudé.
    """
    triangles = []
    for i, j, k in m.faces:
        tri = Polygon(m.sommets[[i, j, k], :2])
        if tri.area > 1e-10:  # les faces verticales se projettent en segments
            triangles.append(tri)
    forme = make_valid(unary_union(triangles)).buffer(0)
    return forme.simplify(tolerance, preserve_topology=True)


def niveau_de(element):
    """Niveau (IfcBuildingStorey) d'un élément : contenance spatiale ou agrégation."""
    conteneur = ue.get_container(element)
    if conteneur is None:
        parent = ue.get_aggregate(element)
        while parent is not None and not parent.is_a("IfcBuildingStorey"):
            parent = ue.get_aggregate(parent)
        conteneur = parent
    return conteneur if conteneur is not None and conteneur.is_a("IfcBuildingStorey") else None


def proprietes(element) -> dict[str, dict]:
    return ue.get_psets(element)


def chercher_propriete(element, nom: str) -> list[tuple[str, object]]:
    """Toutes les occurrences (pset, valeur) d'une propriété, tous psets confondus."""
    return [(pset, valeurs[nom]) for pset, valeurs in proprietes(element).items() if nom in valeurs]
