"""Sous-problèmes de placement SSI (formulations MILP de couverture d'ensemble, résolues par HiGHS).

- Détecteurs (F3) : chaque cellule (pas de la grille) de chaque espace occupable doit être à moins de
  `detecteur_rayon_m` (distance horizontale) d'un détecteur placé au plafond DU MÊME espace, en vue
  directe dans l'espace (portes supposées fermées : la fumée ne traverse pas les cloisons).
- Déclencheurs manuels (F4) : chaque sortie doit être servie par un déclencheur dont la distance de
  CHEMINEMENT à la sortie est ≤ `declencheur_distance_max_m` ; candidats : un point par sortie, côté
  intérieur, à 1,2 m du sol.
- Caméras (F5) : chaque cellule des chemins d'évacuation (à hauteur de visage) doit être vue (frustum
  3D + ligne de vue dans la grille de voxels) ; puis, à nombre de caméras fixé, on maximise le
  full-view selon les directions d'évacuation (PIMRC, éq. 4).
"""

from __future__ import annotations

import math

import networkx as nx
import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from twinhyp.m1_geometrie.distances import cible_dans, itineraire, milieu_contact
from twinhyp.m3_iwcmc.radio import Environnement, obstacles_traverses
from twinhyp.m4_deploiement.milp import couverture_ensemble, resoudre

HAUTEUR_DECLENCHEUR_M = 1.2      # usage courant (NF S 61-970) : boîtier à hauteur d'homme
RETRAIT_DECLENCHEUR_M = 0.4      # côté intérieur de la porte de sortie
HAUTEUR_VISAGE_M = 1.6           # cellules des chemins observées par les caméras
AZIMUTS_DEG = tuple(range(0, 360, 45))
INCLINAISONS_DEG = (20, 45)
ANGLE_FULL_VIEW_DEG = 45.0       # Φ du PIMRC : la caméra fait face au marcheur à ±Φ près


def _poly(e: dict) -> Polygon:
    return Polygon(e["polygone_xy"])


def cellules_espace(e: dict, pas: float, origine_xy) -> np.ndarray:
    """Centres de la grille (alignée sur les voxels) contenus dans l'espace ; à défaut, un point intérieur."""
    p = _poly(e)
    x0, y0, x1, y1 = p.bounds
    xs = origine_xy[0] + (np.arange(math.floor((x0 - origine_xy[0]) / pas), math.ceil((x1 - origine_xy[0]) / pas)) + 0.5) * pas
    ys = origine_xy[1] + (np.arange(math.floor((y0 - origine_xy[1]) / pas), math.ceil((y1 - origine_xy[1]) / pas)) + 0.5) * pas
    pts = [(x, y) for x in xs for y in ys if p.contains(Point(x, y))]
    if not pts:
        q = p.representative_point()
        pts = [(q.x, q.y)]
    return np.array(pts)


# Détecteurs ----------------------------------------------------------------------------
def detecteurs(geometrie: dict, params: dict, origine_xy) -> tuple[list[dict], dict]:
    rayon, pas = float(params["detecteur_rayon_m"]), float(params.get("pas_grille_m", 0.5))
    positions = geometrie["positions_autorisees"]
    couvrants, cellules_info, sans_candidat = [], [], []
    for e in geometrie["espaces"]:
        if not e["occupable"]:
            continue
        zone = _poly(e).buffer(0.01)
        cand = [j for j, a in enumerate(positions) if a["espace_globalId"] == e["globalId"]]
        for c in cellules_espace(e, pas, origine_xy):
            N = [j for j in cand
                 if math.dist(positions[j]["xyz"][:2], c) <= rayon and zone.covers(LineString([positions[j]["xyz"][:2], c]))]
            if N:
                couvrants.append(N)
                cellules_info.append(e["globalId"])
            else:
                sans_candidat.append(e["nom"])
    sol = couverture_ensemble(len(positions), couvrants)
    choisis = [j for j in np.flatnonzero(sol.x)]
    eqs = [{"type": "SmokeDetector", "espace_globalId": positions[j]["espace_globalId"],
            "x": positions[j]["xyz"][0], "y": positions[j]["xyz"][1], "z": positions[j]["xyz"][2]} for j in choisis]
    return eqs, {"variables": len(positions), "contraintes": len(couvrants), "valeur": sol.objectif,
                 "statut": sol.statut, "gap_relatif": sol.gap_relatif, "temps_s": sol.temps_s,
                 "cellules_sans_candidat": sorted(set(sans_candidat)), "rayon_m": rayon}


# Distances de cheminement ----------------------------------------------------------------
def geodesique(poly, a, b) -> float:
    """Plus court chemin de a à b dans le polygone (graphe de visibilité + Dijkstra)."""
    zone = poly.buffer(0.01)
    pts = [tuple(a), tuple(b)]
    for g in getattr(poly, "geoms", [poly]):
        pts += [tuple(map(float, v)) for v in list(g.exterior.coords)[:-1]]
    G = nx.Graph()
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if zone.covers(LineString([pts[i], pts[j]])):
                G.add_edge(i, j, weight=math.dist(pts[i], pts[j]))
    try:
        return nx.dijkstra_path_length(G, 0, 1)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return math.inf


def plateaux_ouverts(geometrie: dict) -> dict[str, Polygon]:
    """Espaces reliés par des ouvertures libres (même plateau) : union des contours."""
    G = nx.Graph()
    G.add_nodes_from(e["globalId"] for e in geometrie["espaces"])
    G.add_edges_from((l["de"], l["vers"]) for l in geometrie["liaisons"] if l["type"] == "ouverture")
    poly = {e["globalId"]: _poly(e) for e in geometrie["espaces"]}
    plateau = {}
    for comp in nx.connected_components(G):
        union = unary_union([poly[g].buffer(0.03) for g in comp])
        for g in comp:
            plateau[g] = union
    return plateau


# Déclencheurs manuels ------------------------------------------------------------------------
def declencheurs(geometrie: dict, params: dict) -> tuple[list[dict], dict]:
    dmax = float(params["declencheur_distance_max_m"])
    espaces = {e["globalId"]: e for e in geometrie["espaces"]}
    niveaux = {n["globalId"]: n["altitude_m"] for n in geometrie["niveaux"]}
    plateau = plateaux_ouverts(geometrie)
    sorties = [p for p in geometrie["portes"] if p["sortie"] and p["espaces"]]
    candidats = []
    for p in sorties:
        e = espaces[p["espaces"][0]]
        poly = _poly(e)
        bord = cible_dans(poly, p["position_xyz"][:2])
        c = np.array(poly.representative_point().coords[0]) - np.array([bord.x, bord.y])
        pt = np.array([bord.x, bord.y]) + RETRAIT_DECLENCHEUR_M * c / (np.linalg.norm(c) or 1)
        candidats.append({"espace": e["globalId"], "xy": pt,
                          "z": niveaux[e["niveau_globalId"]] + HAUTEUR_DECLENCHEUR_M})
    dist = np.full((len(candidats), len(sorties)), math.inf)
    for i, c in enumerate(candidats):
        for k, p in enumerate(sorties):
            s = p["espaces"][0]
            if plateau[c["espace"]] is plateau[s]:
                cible = cible_dans(plateau[s] if c["espace"] != s else _poly(espaces[s]), p["position_xyz"][:2])
                zone = plateau[s] if c["espace"] != s else _poly(espaces[s])
                dist[i, k] = geodesique(zone, c["xy"], (cible.x, cible.y))
    # `declencheur_un_par_sortie` (défaut : vrai, usage NF S 61-970) : chaque sortie a SON déclencheur ;
    # faux : minimum de déclencheurs couvrant toutes les sorties (un DM peut en servir plusieurs).
    par_sortie = bool(params.get("declencheur_un_par_sortie", True))
    if par_sortie:
        dist = np.where(np.eye(len(sorties), dtype=bool), dist, math.inf)
    couvrants = [list(np.flatnonzero(dist[:, k] <= dmax)) for k in range(len(sorties))]
    non_servies = [sorties[k]["globalId"] for k, N in enumerate(couvrants) if not N]  # F4 violée : signalé
    sol = couverture_ensemble(len(candidats), [N for N in couvrants if N])
    eqs = []
    for i in np.flatnonzero(sol.x):
        servies = [(sorties[k]["globalId"], round(float(dist[i, k]), 3)) for k in range(len(sorties)) if dist[i, k] <= dmax]
        c = candidats[i]
        eqs.append({"type": "ManualCallPoint", "espace_globalId": c["espace"], "x": round(float(c["xy"][0]), 3),
                    "y": round(float(c["xy"][1]), 3), "z": round(c["z"], 3),
                    "sortie_servie_globalId": min(servies, key=lambda s: s[1])[0], "sorties_servies": servies})
    return eqs, {"variables": len(candidats), "contraintes": len(sorties), "valeur": sol.objectif,
                 "statut": sol.statut, "gap_relatif": sol.gap_relatif, "temps_s": sol.temps_s,
                 "distance_max_m": dmax, "un_par_sortie": par_sortie, "sorties_non_servies": non_servies}


# Chemins d'évacuation --------------------------------------------------------------------------
def chemins(geometrie: dict, env: Environnement, pas_echantillon: float) -> list[dict]:
    """Un chemin par espace occupable vers sa sortie la plus proche (somme des distances orientées de M1).
    Polyligne : point intérieur de l'espace de départ, passages successifs (porte, milieu d'ouverture,
    tête puis pied de volée), porte de sortie ; échantillonnée à hauteur de visage."""
    espaces = {e["globalId"]: e for e in geometrie["espaces"]}
    alt = {n["globalId"]: n["altitude_m"] for n in geometrie["niveaux"]}
    porte = {p["globalId"]: p for p in geometrie["portes"]}
    liaison = {}
    for l in geometrie["liaisons"]:
        liaison[(l["de"], l["vers"])] = l
        liaison[(l["vers"], l["de"])] = l
    z_de = lambda g: alt[espaces[g]["niveau_globalId"]] + HAUTEUR_VISAGE_M
    sortie = []
    for e in geometrie["espaces"]:
        if not e["occupable"]:
            continue
        it = itineraire(geometrie, e["globalId"])
        sp = it["espaces"]
        q = _poly(e).representative_point()
        pts = [(q.x, q.y, z_de(sp[0]))]
        for u, v in zip(sp, sp[1:]):
            l = liaison[(u, v)]
            if l["type"] == "porte":
                x, y = porte[l["element_globalId"]]["position_xyz"][:2]
                pts.append((x, y, z_de(u)))
            elif l["type"] == "ouverture":
                m = milieu_contact(_poly(espaces[u]), _poly(espaces[v]))
                pts.append((m.x, m.y, z_de(u)))
            else:  # escalier : la cage est l['de'] (pied), l'arrivée l['vers'] (tête)
                bas, haut = (l["pied_xy"], l["tete_xy"])
                a, b = (haut, bas) if u == l["vers"] else (bas, haut)
                pts += [(a[0], a[1], z_de(u)), (b[0], b[1], z_de(v))]
        x, y = porte[it["portes"][-1]]["position_xyz"][:2]
        pts.append((x, y, z_de(sp[-1])))
        echant, directions = [], []
        for p0, p1 in zip(pts, pts[1:]):
            p0, p1 = np.array(p0), np.array(p1)
            n = max(int(np.ceil(np.linalg.norm(p1 - p0) / pas_echantillon)), 1)
            az = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            for t in (np.arange(n) + 0.5) / n:
                echant.append(p0 + t * (p1 - p0))
                directions.append(az)
        echant = np.array(echant)
        ijk = np.floor((echant - env.origine) / env.pas).astype(int)
        dans = np.all((ijk >= 0) & (ijk < np.array(env.forme)), axis=1)
        vus, cellules, dirs = set(), [], []
        for k in np.flatnonzero(dans):
            cle = tuple(ijk[k])
            if cle in vus or not env.libre[cle]:
                continue
            vus.add(cle)
            cellules.append(cle)
            dirs.append(directions[k])
        sortie.append({"espace": e["globalId"], "sortie": it["portes"][-1], "espaces": sp,
                       "cellules": cellules, "directions": dirs})
    return sortie


# Caméras ------------------------------------------------------------------------------------
def cameras(geometrie: dict, params: dict, env: Environnement, chem: list[dict]) -> tuple[list[dict], dict, dict]:
    portee = float(params["camera_portee_m"])
    demi_h = math.radians(float(params["camera_champ_horizontal_deg"]) / 2)
    demi_v = math.radians(float(params["camera_champ_vertical_deg"]) / 2)
    hauteur = float(params["camera_hauteur_pose_m"])
    cmin = float(params["couverture_video_min"])
    alt = {n["globalId"]: n["altitude_m"] for n in geometrie["niveaux"]}
    positions = geometrie["positions_autorisees"]
    # cellules uniques des chemins
    index, centres, dir_cellule = {}, [], {}
    for c in chem:
        for cle, d in zip(c["cellules"], c["directions"]):
            if cle not in index:
                index[cle] = len(centres)
                centres.append(env.origine + (np.array(cle) + 0.5) * env.pas)
            dir_cellule.setdefault(index[cle], []).append(d)
    centres = np.array(centres)
    obstacle = [(env.libre == 0).astype(np.float32)]
    candidats, voit, voit_fv = [], [], []
    for a in positions:
        o = np.array([a["xyz"][0], a["xyz"][1], min(alt[a["niveau_globalId"]] + hauteur, a["xyz"][2] - 0.05)])
        ijk = np.floor((o - env.origine) / env.pas).astype(int)
        if np.any(ijk < 0) or np.any(ijk >= env.forme):
            continue
        descente = 0
        while not env.libre[tuple(ijk)] and descente < 2:  # pose juste sous la couche du faux plafond
            ijk[2] -= 1
            descente += 1
            o[2] = env.origine[2] + (ijk[2] + 1) * env.pas[2] - 0.01
        if not env.libre[tuple(ijk)]:
            continue
        d = centres - o
        dist = np.linalg.norm(d, axis=1)
        proche = np.flatnonzero(dist <= portee)
        if not len(proche):
            continue
        n_obs, _ = obstacles_traverses(env, o, centres[proche], obstacle)
        visibles = proche[n_obs[0] == 0]
        if not len(visibles):
            continue
        dv = d[visibles]
        az = np.arctan2(dv[:, 1], dv[:, 0])
        elev = np.arctan2(dv[:, 2], np.linalg.norm(dv[:, :2], axis=1))
        for phi in AZIMUTS_DEG:
            dphi = np.abs((az - math.radians(phi) + np.pi) % (2 * np.pi) - np.pi)
            for tau in INCLINAISONS_DEG:
                ok = (dphi <= demi_h) & (np.abs(elev + math.radians(tau)) <= demi_v)
                vus = visibles[ok]
                if not len(vus):
                    continue
                # full-view : la caméra est devant le marcheur (angle entre (caméra − cellule) et la marche ≤ Φ)
                fv = [i for i in vus if any(abs((math.atan2(-d[i, 1], -d[i, 0]) - t + math.pi) % (2 * math.pi) - math.pi)
                                            <= math.radians(ANGLE_FULL_VIEW_DEG) for t in dir_cellule[i])]
                candidats.append({"espace": a["espace_globalId"], "xyz": o, "azimut": phi, "inclinaison": tau})
                voit.append(set(vus.tolist()))
                voit_fv.append(set(fv))
    n_cell, n_cand = len(centres), len(candidats)
    voyeurs = [[] for _ in range(n_cell)]
    for j, s in enumerate(voit):
        for i in s:
            voyeurs[i].append(j)
    invisibles = [i for i in range(n_cell) if not voyeurs[i]]
    # Phase 1 : minimiser le nombre de caméras ; variables x (caméras) puis y (cellules vues)
    couts = np.r_[np.ones(n_cand), np.zeros(n_cell)]
    lignes = [(voyeurs[i] + [n_cand + i], [1.0] * len(voyeurs[i]) + [-1.0], 0, None) for i in range(n_cell)]
    for c in chem:
        idx = sorted({index[k] for k in c["cellules"]})
        exige = min(math.ceil(cmin * len(idx) - 1e-9), sum(1 for i in idx if voyeurs[i]))
        lignes.append(([n_cand + i for i in idx], [1.0] * len(idx), exige, None))
    s1 = resoudre(couts, lignes)
    n_star = int(round(s1.objectif))
    # Phase 2 : à nombre de caméras ≤ N*, maximiser les cellules vues de face (full-view)
    fv_voyeurs = [[] for _ in range(n_cell)]
    for j, s in enumerate(voit_fv):
        for i in s:
            fv_voyeurs[i].append(j)
    # Variables : x (caméras), y (cellules vues), z (cellules vues de face), t (full-view minimal par chemin).
    # 2a : maximiser t (équité : aucun chemin sacrifié au profit des longs) ; 2b : à t ≥ t*, maximiser Σ z.
    # Un chemin dont aucune cellule ne peut être vue de face est exclu du minimum (signalé).
    zt = n_cand + 2 * n_cell
    n_budget = n_star + int(params.get("cameras_supplementaires_full_view", 0))
    lignes2 = list(lignes) + [(list(range(n_cand)), [1.0] * n_cand, None, n_budget)]
    lignes2 += [(fv_voyeurs[i] + [n_cand + n_cell + i], [1.0] * len(fv_voyeurs[i]) + [-1.0], 0, None) for i in range(n_cell)]
    sans_fv_possible = []
    for c in chem:
        idx = sorted({index[k] for k in c["cellules"]})
        if not any(fv_voyeurs[i] for i in idx):
            sans_fv_possible.append(c["espace"])
            continue
        lignes2.append(([n_cand + n_cell + i for i in idx] + [zt], [1.0] * len(idx) + [-float(len(idx))], 0, None))
    couts2a = np.r_[np.zeros(zt), 1.0]
    s2a = resoudre(couts2a, lignes2, maximiser=True, continues=[zt])
    t_star = float(s2a.brut[zt]) if s2a.statut == "Optimal" else 0.0
    couts2b = np.r_[np.zeros(n_cand + n_cell), np.ones(n_cell), 0.0]
    lignes2b = lignes2 + [([zt], [1.0], max(t_star - 1e-6, 0.0), None)]
    s2 = resoudre(couts2b, lignes2b, maximiser=True, continues=[zt])
    s2.temps_s += s2a.temps_s
    x = s2.x[:n_cand] if s2.statut == "Optimal" else s1.x[:n_cand]
    choisis = list(np.flatnonzero(x))
    vues = set().union(*(voit[j] for j in choisis)) if choisis else set()
    vues_fv = set().union(*(voit_fv[j] for j in choisis)) if choisis else set()
    eqs, par_chemin = [], {}
    for j in choisis:
        c = candidats[j]
        eqs.append({"type": "Camera", "espace_globalId": c["espace"], "x": round(float(c["xyz"][0]), 3),
                    "y": round(float(c["xyz"][1]), 3), "z": round(float(c["xyz"][2]), 3),
                    "orientation_deg": float(c["azimut"]), "inclinaison_deg": float(c["inclinaison"]),
                    "cellules_vues": sorted(voit[j])})
    for c in chem:
        idx = sorted({index[k] for k in c["cellules"]})
        par_chemin[(c["espace"], c["sortie"])] = {
            "cellules": len(idx), "couverture": round(sum(i in vues for i in idx) / max(len(idx), 1), 4),
            "full_view": round(sum(i in vues_fv for i in idx) / max(len(idx), 1), 4), "indices": idx}
    resume = {"candidats": n_cand, "cellules": n_cell, "cellules_invisibles": len(invisibles),
              "valeur": float(len(choisis)), "statut": s1.statut, "gap_relatif": s1.gap_relatif,
              "temps_s": round(s1.temps_s + s2.temps_s, 3), "statut_full_view": s2.statut,
              "full_view_global": round(len(vues_fv) / max(n_cell, 1), 4),
              "full_view_min_par_chemin": round(t_star, 4), "chemins_sans_full_view_possible": sans_fv_possible,
              "couverture_globale": round(len(vues) / max(n_cell, 1), 4)}
    return eqs, resume, par_chemin
