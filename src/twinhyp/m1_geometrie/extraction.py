"""Étape 1 – extraction IFC : niveaux, espaces, portes, escaliers.

Décisions (voir docs/etape0a2.md) :
- tout est indexé par GlobalId, jamais par nom ;
- `surface_m2` = propriété « GSA BIM Area » (celle des questions Q05/Q10),
  repli sur la surface géométrique ; `surface_geometrique_m2` est toujours fourni ;
- `polygone_xy` = empreinte géométrique (union des triangles projetés) ;
- `hauteur_m` = zmax − zmin du maillage ;
- occupable : règle par mots-clés (toit…), paramétrable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
from shapely.geometry import MultiPolygon, Polygon

from twinhyp.m1_geometrie import ifc_outils as io

# Mots-clés (minuscules) d'un espace non occupable, cherchés dans le nom, le nom
# long de l'espace et le nom de son niveau. Surchargeable par la clé
# `mots_cles_non_occupable` de parametres.json.
MOTS_CLES_NON_OCCUPABLE = ("roof", "toit", "toiture", "shaft", "gaine", "vide sanitaire", "plenum")

PROPRIETE_SURFACE = "GSA BIM Area"


@dataclass
class Niveau:
    globalId: str
    nom: str
    altitude_m: float


@dataclass
class Espace:
    globalId: str
    nom: str
    nom_long: str | None
    niveau_globalId: str | None
    polygone_xy: list[list[float]]
    surface_m2: float
    surface_source: str
    surface_geometrique_m2: float
    hauteur_m: float
    z_bas_m: float
    occupable: bool
    centre_xy: list[float] = field(default_factory=list)


@dataclass
class Porte:
    globalId: str
    nom: str
    niveau_globalId: str | None
    largeur_m: float
    hauteur_m: float | None
    position_xyz: list[float]
    espaces: list[str]          # GlobalId des espaces bordés (IfcRelSpaceBoundary), complété à l'étape 2
    sortie: bool                # provisoire (une seule limite d'espace) ; recoupé à l'étape 2


@dataclass
class Escalier:
    globalId: str
    nom: str
    niveau_globalId: str | None
    z_bas_m: float
    z_haut_m: float
    boite_xy: list[list[float]]  # [[xmin, ymin], [xmax, ymax]]
    volees: list[dict]


def _arrondi(x: float, n: int = 4) -> float:
    return round(float(x), n)


def _polygone_principal(forme) -> Polygon:
    if isinstance(forme, MultiPolygon):
        return max(forme.geoms, key=lambda p: p.area)
    return forme


# ------------------------------------------------------------------------------
def extraire_niveaux(f) -> list[Niveau]:
    e = io.echelle_longueur(f)
    niveaux = [Niveau(s.GlobalId, s.Name or "", _arrondi((s.Elevation or 0.0) * e))
               for s in f.by_type("IfcBuildingStorey")]
    return sorted(niveaux, key=lambda n: n.altitude_m)


def est_occupable(nom: str, nom_long: str | None, nom_niveau: str | None,
                  mots_cles=MOTS_CLES_NON_OCCUPABLE) -> bool:
    texte = " ".join(t for t in (nom, nom_long, nom_niveau) if t).lower()
    return not any(m in texte for m in mots_cles)


def extraire_espaces(f, mots_cles=MOTS_CLES_NON_OCCUPABLE) -> list[Espace]:
    e = io.echelle_longueur(f)
    espaces = []
    for sp in f.by_type("IfcSpace"):
        niveau = io.niveau_de(sp)
        m = io.maillage(sp)
        if m is None:
            continue  # signalé par la règle d'anomalie « espace sans géométrie »
        poly = _polygone_principal(io.empreinte(m))
        surface_geo = poly.area
        declarees = [v for _, v in io.chercher_propriete(sp, PROPRIETE_SURFACE) if isinstance(v, (int, float))]
        if declarees:
            surface, source = float(declarees[0]) * e * e, PROPRIETE_SURFACE
        else:
            surface, source = surface_geo, "geometrie"
        coords = [[_arrondi(x), _arrondi(y)] for x, y in poly.exterior.coords[:-1]]
        espaces.append(Espace(
            globalId=sp.GlobalId, nom=sp.Name or "", nom_long=sp.LongName,
            niveau_globalId=niveau.GlobalId if niveau else None,
            polygone_xy=coords, surface_m2=_arrondi(surface), surface_source=source,
            surface_geometrique_m2=_arrondi(surface_geo),
            hauteur_m=_arrondi(m.zmax - m.zmin), z_bas_m=_arrondi(m.zmin),
            occupable=est_occupable(sp.Name or "", sp.LongName, niveau.Name if niveau else None, mots_cles),
            centre_xy=[_arrondi(c) for c in poly.representative_point().coords[0]],
        ))
    return sorted(espaces, key=lambda s: s.globalId)


def espaces_bordes(f, element) -> list[str]:
    """GlobalId distincts des espaces qui ont une limite (IfcRelSpaceBoundary) sur l'élément."""
    gids = {r.RelatingSpace.GlobalId for r in f.get_inverse(element)
            if r.is_a("IfcRelSpaceBoundary") and r.RelatingSpace is not None}
    return sorted(gids)


def extraire_portes(f) -> list[Porte]:
    e = io.echelle_longueur(f)
    portes = []
    for d in f.by_type("IfcDoor"):
        m = io.maillage(d)
        largeur = d.OverallWidth * e if d.OverallWidth else None
        hauteur = d.OverallHeight * e if d.OverallHeight else None
        if largeur is None and m is not None:  # repli : plus grande dimension horizontale
            etendue = m.sommets.max(axis=0) - m.sommets.min(axis=0)
            largeur = float(max(etendue[0], etendue[1]))
        niveau = io.niveau_de(d)
        espaces = espaces_bordes(f, d)
        portes.append(Porte(
            globalId=d.GlobalId, nom=d.Name or "",
            niveau_globalId=niveau.GlobalId if niveau else None,
            largeur_m=_arrondi(largeur or 0.0), hauteur_m=_arrondi(hauteur) if hauteur else None,
            position_xyz=[_arrondi(c) for c in m.centre] if m is not None else [],
            espaces=espaces, sortie=len(espaces) == 1,
        ))
    return sorted(portes, key=lambda p: p.globalId)


def extraire_escaliers(f) -> list[Escalier]:
    e = io.echelle_longueur(f)
    escaliers = []
    for st in f.by_type("IfcStair"):
        parties = [p for r in st.IsDecomposedBy for p in r.RelatedObjects]
        volees = [p for p in parties if p.is_a("IfcStairFlight")]
        maillages = [m for m in (io.maillage(p) for p in (volees or [st])) if m is not None]
        if not maillages:
            continue
        v = np.vstack([m.sommets for m in maillages])
        niveau = io.niveau_de(st)
        escaliers.append(Escalier(
            globalId=st.GlobalId, nom=st.Name or "",
            niveau_globalId=niveau.GlobalId if niveau else None,
            z_bas_m=_arrondi(v[:, 2].min()), z_haut_m=_arrondi(v[:, 2].max()),
            boite_xy=[[_arrondi(v[:, 0].min()), _arrondi(v[:, 1].min())],
                      [_arrondi(v[:, 0].max()), _arrondi(v[:, 1].max())]],
            volees=[{
                "globalId": fl.GlobalId,
                "contremarches": fl.NumberOfRiser,
                "hauteur_marche_declaree": fl.RiserHeight * e if fl.RiserHeight else None,
                "giron_declare": fl.TreadLength * e if fl.TreadLength else None,
            } for fl in volees],
        ))
    return sorted(escaliers, key=lambda s: s.globalId)


def en_dicts(objets) -> list[dict]:
    return [asdict(o) for o in objets]
