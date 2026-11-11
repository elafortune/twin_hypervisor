"""Étape 2 – connectivité entre espaces : portes, ouvertures libres, escaliers.

Portes : trois sources indépendantes, décision à la majorité (≥ 2 sur 3) :
  A. IFC  : espaces ayant une `IfcRelSpaceBoundary` sur la porte ;
  B. Pang : chaîne porte → ouverture (IfcRelFillsElement) → mur hôte
            (IfcRelVoidsElement), puis espaces qui longent ce mur près de la porte ;
  C. géométrie : espaces dont le contour passe à moins de `TOL_PORTE_M` de la porte.
Un désaccord entre sources devient une anomalie (la source minoritaire est signalée).

Ouvertures libres : deux sources —
  A. IFC : limites d'espace VIRTUAL ;
  C. géométrie : contours qui se touchent sans mur (distance ≈ 0) sur au moins
     `LONGUEUR_MIN_OUVERTURE_M`, sans chevauchement.
Escaliers : volée → espace bas (point de départ) et espace haut (point d'arrivée).

Aucune règle ne dépend des noms ni des GlobalId du duplex.
"""

from __future__ import annotations

from collections import defaultdict

import networkx as nx
import numpy as np
from shapely.geometry import LineString, Point, Polygon

from twinhyp.m1_geometrie import ifc_outils as io
from twinhyp.m1_geometrie.anomalies import anomalie

TOL_PORTE_M = 0.40               # distance max porte -> contour d'espace (≈ épaisseur de mur)
TOL_MUR_M = 0.10                 # distance max mur hôte -> contour d'espace
TOL_CONTACT_M = 0.02             # deux contours « se touchent » en dessous de cette distance
LONGUEUR_MIN_OUVERTURE_M = 0.60  # largeur minimale d'un passage libre
AIRE_CHEVAUCHEMENT_M2 = 0.01     # au-delà : deux espaces se chevauchent (erreur de modélisation)
TOL_LIMITE_M = 0.50              # une limite virtuelle doit être sur le contour de son espace


# ------------------------------------------------------------------------------
class Index:
    """Accès géométrique aux espaces de geometry.json."""

    def __init__(self, espaces: list[dict]):
        self.espaces = {e["globalId"]: e for e in espaces}
        self.poly = {g: Polygon(e["polygone_xy"]) for g, e in self.espaces.items()}

    def z(self, g):
        e = self.espaces[g]
        return e["z_bas_m"], e["z_bas_m"] + e["hauteur_m"]

    def a_hauteur(self, g, z, marge=0.3):
        z0, z1 = self.z(g)
        return z0 - marge <= z <= z1 + marge

    def proches(self, geom, z, tol):
        return sorted(g for g, p in self.poly.items() if p.distance(geom) <= tol and self.a_hauteur(g, z))

    def chevauchement_vertical(self, a, b):
        (a0, a1), (b0, b1) = self.z(a), self.z(b)
        return min(a1, b1) - max(a0, b0)


# Portes -----------------------------------------------------------------------
def source_ifc(f, porte) -> set[str]:
    return {r.RelatingSpace.GlobalId for r in f.get_inverse(porte)
            if r.is_a("IfcRelSpaceBoundary") and r.RelatingSpace is not None}


def source_pang(porte, idx: Index, centre) -> set[str] | None:
    """Chaîne de Pang : porte -> ouverture -> mur hôte -> espaces qui longent le mur près de la porte."""
    if not porte.FillsVoids:
        return None
    ouverture = porte.FillsVoids[0].RelatingOpeningElement
    if not ouverture.VoidsElements:
        return None
    mur = ouverture.VoidsElements[0].RelatingBuildingElement
    m = io.maillage(mur)
    if m is None:
        return None
    empreinte_mur = io.empreinte(m)
    point = Point(centre[0], centre[1])
    return {g for g, p in idx.poly.items()
            if p.distance(empreinte_mur) <= TOL_MUR_M and p.distance(point) <= TOL_PORTE_M + 0.2
            and idx.a_hauteur(g, centre[2])}


def source_geometrie(idx: Index, centre) -> set[str]:
    return set(idx.proches(Point(centre[0], centre[1]), centre[2], TOL_PORTE_M))


def vote(sources: dict[str, set | None]) -> tuple[list[str], dict[str, list[str]]]:
    """Garde un espace s'il est cité par la majorité des sources disponibles."""
    dispo = {k: v for k, v in sources.items() if v is not None}
    seuil = 2 if len(dispo) >= 2 else 1
    compte = defaultdict(list)
    for nom, ens in dispo.items():
        for g in ens:
            compte[g].append(nom)
    retenus = sorted(g for g, s in compte.items() if len(s) >= seuil)
    return retenus, {g: sorted(s) for g, s in compte.items()}


def est_externe_declare(porte) -> bool | None:
    valeurs = [v for _, v in io.chercher_propriete(porte, "IsExternal") if isinstance(v, bool)]
    return valeurs[0] if valeurs else None


def connecter_portes(f, geometrie: dict, idx: Index):
    liaisons, anomalies = [], []
    portes = {p["globalId"]: p for p in geometrie["portes"]}
    for porte in sorted(f.by_type("IfcDoor"), key=lambda d: d.GlobalId):
        p = portes.get(porte.GlobalId)
        if p is None or not p["position_xyz"]:
            continue
        c = p["position_xyz"]
        sources = {"ifc": source_ifc(f, porte), "pang": source_pang(porte, idx, c),
                   "geometrie": source_geometrie(idx, c)}
        retenus, citations = vote(sources)
        p["espaces"] = retenus
        p["sources"] = {k: sorted(v) if v is not None else None for k, v in sources.items()}
        # Seul un désaccord impliquant la maquette (source IFC) est une anomalie de la
        # maquette ; une citation isolée de pang/géométrie est une imprécision de méthode.
        nom = lambda g: idx.espaces[g]["nom"]
        retenus_txt = ", ".join(nom(x) for x in retenus)
        for g, s in sorted(citations.items()):
            if g not in retenus and "ifc" in s:
                anomalies.append(anomalie(
                    porte.GlobalId,
                    f"Porte {porte.GlobalId} : la maquette (IfcRelSpaceBoundary) la relie aussi à {nom(g)} ({g}), "
                    f"ce que ni la chaîne mur → ouverture → porte ni la géométrie ne confirment "
                    f"(espaces retenus : {retenus_txt}).",
                    f"Relation vers {nom(g)} écartée (vote à la majorité des 3 sources).",
                    "porte_sources_concordantes", espace_ecarte=g))
            elif g in retenus and sources["ifc"] is not None and "ifc" not in s and f.by_type("IfcRelSpaceBoundary"):
                anomalies.append(anomalie(
                    porte.GlobalId,
                    f"Porte {porte.GlobalId} : la maquette ne déclare pas de limite avec {nom(g)} ({g}), "
                    "alors que la chaîne de Pang et la géométrie l'y relient.",
                    "Relation ajoutée (vote à la majorité des 3 sources).", "porte_sources_concordantes",
                    espace_ajoute=g))
        if len(retenus) == 2:
            liaisons.append({"de": retenus[0], "vers": retenus[1], "type": "porte",
                             "element_globalId": porte.GlobalId, "largeur_m": p["largeur_m"],
                             "sources": sorted({s for g in retenus for s in citations[g]})})
            p["sortie"] = False
        elif len(retenus) == 1 and idx.poly[retenus[0]].boundary.distance(Point(c[0], c[1])) > TOL_PORTE_M \
                and idx.poly[retenus[0]].contains(Point(c[0], c[1])):
            # porte au milieu de son unique espace (cabine de sanitaires, placard) : ni liaison ni sortie.
            # Découvert sur le 2e IFC (bureaux NIBS : portes de cabines des sanitaires prises pour des sorties).
            p["sortie"] = False
            anomalies.append(anomalie(
                porte.GlobalId, f"Porte {porte.GlobalId} à l'intérieur de {nom(retenus[0])}, à plus de "
                f"{TOL_PORTE_M} m de son contour (porte de cabine ou de placard).",
                "Ni liaison ni sortie.", "porte_interieure_espace"))
        elif len(retenus) == 1:
            p["sortie"] = True
        else:
            p["sortie"] = False
            anomalies.append(anomalie(
                porte.GlobalId, f"Porte {porte.GlobalId} reliée à {len(retenus)} espace(s) après vote.",
                "Porte exclue de la connectivité.", "porte_deux_espaces"))
        declare = est_externe_declare(porte)
        if declare is not None and declare != p["sortie"]:
            anomalies.append(anomalie(
                porte.GlobalId,
                f"Porte {porte.GlobalId} : IsExternal = {declare} mais la géométrie indique "
                f"{'une sortie' if p['sortie'] else 'une porte intérieure'}.",
                "La géométrie fait foi.", "sortie_coherente"))
    return liaisons, anomalies


# Ouvertures libres --------------------------------------------------------------
def segment_limite(limite) -> LineString | None:
    """Segment monde d'une limite d'espace décrite par une surface d'extrusion de polyligne."""
    try:
        from ifcopenshell.util.placement import get_axis2placement, get_local_placement
        surf = limite.ConnectionGeometry.SurfaceOnRelatingElement
        points = surf.SweptCurve.Curve.Points
        M = get_local_placement(limite.RelatingSpace.ObjectPlacement) @ get_axis2placement(surf.Position)
        pts = [(M @ np.array([*pt.Coordinates[:2], 0.0, 1.0]))[:2] for pt in points]
        return LineString(pts)
    except Exception:  # autre représentation : pas de contrôle géométrique
        return None


def connecter_ouvertures(f, idx: Index):
    liaisons, anomalies = [], []
    # Source IFC : espaces portant des limites virtuelles
    virtuelles = defaultdict(list)
    for b in f.by_type("IfcRelSpaceBoundary"):
        if b.PhysicalOrVirtualBoundary == "VIRTUAL" and b.RelatingSpace is not None:
            virtuelles[b.RelatingSpace.GlobalId].append(b)

    mal_placees, externes_face_espace = [], []
    for g, limites in virtuelles.items():
        if g not in idx.poly:
            continue
        for b in limites:
            seg = segment_limite(b)
            if seg is not None and idx.poly[g].distance(seg) > TOL_LIMITE_M:
                mal_placees.append((g, b, idx.poly[g].distance(seg)))
            elif seg is not None and b.InternalOrExternalBoundary == "EXTERNAL":
                face = [o for o in idx.poly if o != g and idx.poly[o].distance(seg) < 0.05
                        and idx.chevauchement_vertical(g, o) > 0.5]
                if face:
                    externes_face_espace.append((g, b, face))

    # Source géométrique : contacts sans mur, puis vote
    ids = sorted(idx.poly)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if idx.chevauchement_vertical(a, b) < 0.5 or idx.poly[a].distance(idx.poly[b]) > TOL_CONTACT_M:
                continue
            aire = idx.poly[a].intersection(idx.poly[b]).area
            if aire > AIRE_CHEVAUCHEMENT_M2:
                anomalies.append(anomalie(
                    a, f"Les espaces {idx.espaces[a]['nom']} ({a}) et {idx.espaces[b]['nom']} ({b}) se chevauchent "
                       f"sur {aire:.2f} m² en plan, à la même hauteur.",
                    "Pas de liaison créée ; chevauchement signalé (erreur de contour).",
                    "chevauchement_espaces", elements_concernes=[a, b]))
                continue
            contact = idx.poly[a].boundary.intersection(idx.poly[b].buffer(TOL_CONTACT_M)).length
            if contact < LONGUEUR_MIN_OUVERTURE_M:
                continue
            ifc = bool(virtuelles.get(a)) and bool(virtuelles.get(b))
            sources = ["geometrie"] + (["ifc"] if ifc else [])
            liaisons.append({"de": a, "vers": b, "type": "ouverture", "element_globalId": None,
                             "largeur_m": round(contact, 3), "sources": sources})
            if not ifc:
                anomalies.append(anomalie(
                    a, f"{idx.espaces[a]['nom']} et {idx.espaces[b]['nom']} se touchent sans mur sur {contact:.2f} m "
                       "mais aucune limite virtuelle IFC ne le déclare.",
                    "Liaison « ouverture » créée sur la seule géométrie.", "ouverture_declaree",
                    elements_concernes=[a, b]))

    if mal_placees:
        gids = sorted({g for g, _, _ in mal_placees})
        ecarts = ", ".join("{} : {:.1f} m".format(idx.espaces[g]["nom"], d) for g, _, d in mal_placees)
        anomalies.append(anomalie(
            gids[0], f"Limites virtuelles situées à plus de {TOL_LIMITE_M} m de leur espace ({ecarts}) : "
                     "placement local de l'espace incohérent avec la géométrie de ses limites.",
            "Géométrie des limites ignorée pour ces espaces ; connectivité établie par contact géométrique.",
            "limite_bien_placee", elements_concernes=gids))
    if externes_face_espace:
        gids = sorted({g for g, _, _ in externes_face_espace})
        anomalies.append(anomalie(
            gids[0], f"{len(externes_face_espace)} limites virtuelles typées EXTERNAL font face à un autre espace "
                     f"({', '.join(sorted({idx.espaces[g]['nom'] for g in gids}))}).",
            "Traitées comme des limites internes (passage libre entre espaces).", "limite_type_coherent",
            elements_concernes=gids))
    return liaisons, anomalies


# Escaliers -----------------------------------------------------------------------
def connecter_escaliers(f, idx: Index):
    liaisons, anomalies = [], []
    for st in sorted(f.by_type("IfcStair"), key=lambda s: s.GlobalId):
        volees = [p for r in st.IsDecomposedBy for p in r.RelatedObjects if p.is_a("IfcStairFlight")] or [st]
        for fl in volees:
            m = io.maillage(fl)
            if m is None:
                continue
            v = m.sommets
            bas = v[v[:, 2] <= m.zmin + 0.25]
            haut = v[v[:, 2] >= m.zmax - 0.25]
            p_bas, p_haut = Point(*bas[:, :2].mean(axis=0)), Point(*haut[:, :2].mean(axis=0))
            cage = [g for g in idx.proches(Point(*v[:, :2].mean(axis=0)), m.zmin, 0.0)
                    if idx.z(g)[1] >= m.zmax - 0.3]  # espace qui contient toute la volée
            depart = cage or idx.proches(p_bas, m.zmin + 0.1, 0.3)
            arrivee = [g for g in idx.proches(p_haut, m.zmax, 0.6)
                       if g not in cage and abs(idx.z(g)[0] - m.zmax) < 0.4]
            if not depart or not arrivee:
                anomalies.append(anomalie(
                    st.GlobalId, f"Volée {fl.GlobalId} : espace de départ ou d'arrivée introuvable.",
                    "Escalier non relié.", "escalier_relie"))
                continue
            a = min(depart, key=lambda g: idx.poly[g].distance(p_bas))
            b = min(arrivee, key=lambda g: idx.poly[g].distance(p_haut))
            # axe de la volée (bas -> haut) ; course = étendue de l'empreinte le long de l'axe
            u = np.array([p_haut.x - p_bas.x, p_haut.y - p_bas.y])
            u = u / (np.linalg.norm(u) or 1.0)
            proj = v[:, :2] @ u
            c = v[:, :2].mean(axis=0)
            pied, tete = c + u * (proj.min() - c @ u), c + u * (proj.max() - c @ u)
            course, denivele = float(proj.max() - proj.min()), float(m.zmax - m.zmin)
            liaisons.append({"de": a, "vers": b, "type": "escalier", "element_globalId": st.GlobalId,
                             "course_m": round(course, 3), "denivele_m": round(denivele, 3),
                             "longueur_volee_m": round(float(np.hypot(course, denivele)), 3),
                             "pied_xy": [round(float(x), 3) for x in pied],
                             "tete_xy": [round(float(x), 3) for x in tete], "sources": ["geometrie"],
                             "cage_globalId": cage[0] if cage else None})
    return liaisons, anomalies


# Assemblage et contrôles -----------------------------------------------------------
def fusionner(liaisons: list[dict]) -> list[dict]:
    """Une seule liaison par paire et par élément ; une paire reliée par escalier
    n'est pas aussi une « ouverture » (la limite virtuelle est l'arrivée de l'escalier)."""
    par_escalier = {frozenset((l["de"], l["vers"])) for l in liaisons if l["type"] == "escalier"}
    sortie = [l for l in liaisons if not (l["type"] == "ouverture" and frozenset((l["de"], l["vers"])) in par_escalier)]
    return sorted(sortie, key=lambda l: (l["type"], l["de"], l["vers"], l.get("element_globalId") or ""))


def graphe(geometrie: dict) -> nx.Graph:
    G = nx.Graph()
    for e in geometrie["espaces"]:
        G.add_node(e["globalId"], nom=e["nom"])
    G.add_node("EXTERIEUR")
    for l in geometrie["liaisons"]:
        G.add_edge(l["de"], l["vers"], type=l["type"], element=l.get("element_globalId"))
    for p in geometrie["portes"]:
        if p["sortie"] and p["espaces"]:
            G.add_edge(p["espaces"][0], "EXTERIEUR", type="sortie", element=p["globalId"])
    return G


def controler_evacuabilite(geometrie: dict) -> list[dict]:
    """Invariant : tout espace occupable atteint l'extérieur."""
    G = graphe(geometrie)
    sortie = []
    for e in geometrie["espaces"]:
        if e["occupable"] and G.degree(e["globalId"]) == 0:
            # aucune porte, ouverture ni escalier : inaccessible (gaine d'ascenseur, local fermé) -> non occupable.
            # Découvert sur le 2e IFC (bureaux NIBS : « ELEV ») ; un espace RELIÉ sans sortie reste une anomalie bloquante.
            e["occupable"] = False
            sortie.append(anomalie(e["globalId"], f"Espace {e['nom']} ({e.get('nom_long')}) sans aucune liaison "
                                   "(porte, ouverture, escalier).", "Requalifié non occupable (inaccessible).",
                                   "espace_isole"))
        elif e["occupable"] and not nx.has_path(G, e["globalId"], "EXTERIEUR"):
            sortie.append(anomalie(e["globalId"], f"Espace occupable {e['nom']} sans chemin vers une sortie.",
                                   "Signalé ; à traiter avant tout calcul d'évacuation.", "espace_evacuable"))
    return sortie


def calculer(f, geometrie: dict) -> list[dict]:
    """Complète geometrie (liaisons, portes.espaces/sortie/sources) et renvoie les anomalies."""
    idx = Index(geometrie["espaces"])
    l_portes, a_portes = connecter_portes(f, geometrie, idx)
    l_ouv, a_ouv = connecter_ouvertures(f, idx)
    l_esc, a_esc = connecter_escaliers(f, idx)
    geometrie["liaisons"] = fusionner(l_portes + l_ouv + l_esc)
    return a_portes + a_ouv + a_esc + controler_evacuabilite(geometrie)
