"""Vue 3D interactive de la maquette IFC (plotly Mesh3d).

- une couche par classe d'éléments (murs, dalles, portes…) et par niveau,
  maillages fusionnés pour rester fluide sur un grand bâtiment ;
- un maillage par espace (survol : nom, GlobalId, anomalies) ;
- menu : niveau affiché ; boutons : perspective / vue de dessus orthographique ;
- couches optionnelles superposées : portes et sorties de geometry.json, puis
  (M3/M4) équipements de devices.json.

Le rattachement d'un élément à un niveau est fait par l'altitude de sa base
(pas par la relation IFC, qui peut être fausse : voir anomalie « rattachement »).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from twinhyp.m1_geometrie import ifc_outils as io
from twinhyp.m1_geometrie.anomalies import niveau_attendu
from twinhyp.m1_geometrie.extraction import extraire_niveaux, en_dicts
from twinhyp.visualisation import ecrire_html

# (libellé, classes IFC, couleur, opacité, visible par défaut)
COUCHES = [
    ("Murs", ("IfcWall",), "#94a3b8", 0.55, True),
    ("Dalles", ("IfcSlab",), "#cbd5e1", 0.35, True),
    ("Toitures", ("IfcRoof",), "#a8a29e", 0.30, "legendonly"),
    ("Portes", ("IfcDoor",), "#2563eb", 0.95, True),
    ("Fenêtres", ("IfcWindow",), "#38bdf8", 0.60, True),
    ("Escaliers", ("IfcStair", "IfcStairFlight"), "#9333ea", 0.90, True),
    ("Garde-corps", ("IfcRailing", "IfcMember"), "#7c3aed", 0.70, True),
    ("Poteaux / poutres", ("IfcColumn", "IfcBeam"), "#64748b", 0.80, True),
    ("Revêtements", ("IfcCovering",), "#e2e8f0", 0.25, "legendonly"),
    ("Mobilier", ("IfcFurnishingElement",), "#d97706", 0.80, "legendonly"),
]


def _fusion(maillages):
    sommets, faces, decalage = [], [], 0
    for m in maillages:
        sommets.append(m.sommets)
        faces.append(m.faces + decalage)
        decalage += len(m.sommets)
    return np.vstack(sommets), np.vstack(faces)


def _mesh(v, t, **kw):
    return go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=t[:, 0], j=t[:, 1], k=t[:, 2],
                     flatshading=True, lighting=dict(ambient=0.6, diffuse=0.7), **kw)


def figure_3d(chemin_ifc: Path, geometrie: dict | None = None, devices: dict | None = None) -> go.Figure:
    f = io.ouvrir(chemin_ifc)
    niveaux = en_dicts(extraire_niveaux(f))
    fig = go.Figure()
    niveau_trace: list[str | None] = []   # niveau de chaque trace (None = toujours visible)
    visible_defaut: list[object] = []

    def ajouter(trace, niveau_gid, visible=True):
        trace.visible = visible
        fig.add_trace(trace)
        niveau_trace.append(niveau_gid)
        visible_defaut.append(visible)

    def niveau_par_z(m):
        n = niveau_attendu(m.zmin, niveaux)
        return n["globalId"] if n else None

    # Éléments physiques, fusionnés par (couche, niveau) ---------------------
    vus = set()
    for libelle, classes, couleur, opacite, visible in COUCHES:
        groupes = defaultdict(list)
        for cls in classes:
            for el in f.by_type(cls):
                if el.id() in vus:
                    continue
                vus.add(el.id())
                m = io.maillage(el)
                if m is not None:
                    groupes[niveau_par_z(m)].append(m)
        for k, (ngid, ms) in enumerate(sorted(groupes.items(), key=lambda kv: str(kv[0]))):
            v, t = _fusion(ms)
            ajouter(_mesh(v, t, color=couleur, opacity=opacite, name=libelle, legendgroup=libelle,
                          showlegend=k == 0, hoverinfo="name"), ngid, visible)

    # Espaces : un maillage chacun, pour l'infobulle ----------------------------
    infos = {e["globalId"]: e for e in (geometrie or {}).get("espaces", [])}
    anomalies = defaultdict(list)
    for a in (geometrie or {}).get("anomalies", []):
        for gid in a.get("elements_concernes", [a["element_globalId"]]):
            anomalies[gid].append(a["description"][:100])
    for k, sp in enumerate(sorted(f.by_type("IfcSpace"), key=lambda s: s.GlobalId)):
        m = io.maillage(sp)
        if m is None:
            continue
        e = infos.get(sp.GlobalId, {})
        texte = (f"<b>{sp.Name}</b> – {sp.LongName or ''}<br>{sp.GlobalId}"
                 + (f"<br>{e['surface_m2']} m² · h {e['hauteur_m']} m" if e else "")
                 + "".join(f"<br>⚠ {d}" for d in anomalies.get(sp.GlobalId, [])))
        couleur = "#ea580c" if anomalies.get(sp.GlobalId) else ("#60a5fa" if e.get("occupable", True) else "#cbd5e1")
        ajouter(_mesh(m.sommets, m.faces, color=couleur, opacity=0.18, name="Espaces", legendgroup="Espaces",
                      showlegend=k == 0, hovertext=texte, hoverinfo="text"), niveau_par_z(m))

    # Superpositions issues des sorties -------------------------------------------
    if geometrie:
        for est_sortie, nom, couleur, taille in [(False, "Portes (geometry.json)", "#1d4ed8", 4),
                                                 (True, "Sorties", "#dc2626", 8)]:
            sel = [p for p in geometrie["portes"] if p["position_xyz"] and p["sortie"] == est_sortie]
            if sel:
                ajouter(go.Scatter3d(
                    x=[p["position_xyz"][0] for p in sel], y=[p["position_xyz"][1] for p in sel],
                    z=[p["position_xyz"][2] for p in sel], mode="markers", name=nom,
                    marker=dict(size=taille, color=couleur, symbol="diamond"),
                    text=[f"{p['globalId']}<br>largeur {p['largeur_m']} m" for p in sel], hoverinfo="text"), None)
    if devices:
        par_type = defaultdict(list)
        for d in devices.get("equipements", []):
            par_type[d["type"]].append(d)
        for typ, ds in sorted(par_type.items()):
            ajouter(go.Scatter3d(x=[d["x"] for d in ds], y=[d["y"] for d in ds], z=[d["z"] for d in ds],
                                 mode="markers", name=typ, marker=dict(size=6),
                                 text=[f"{d['id']} ({typ})" for d in ds], hoverinfo="text"), None)

    # Menus --------------------------------------------------------------------------
    def masque(ngid_choisi):
        return [vd if (n is None or ngid_choisi is None or n == ngid_choisi) else False
                for n, vd in zip(niveau_trace, visible_defaut)]

    utiles = [n for n in niveaux if n["globalId"] in set(niveau_trace)]
    boutons_niveaux = [dict(label="Tous les niveaux", method="restyle", args=[{"visible": masque(None)}])]
    boutons_niveaux += [dict(label=f"{n['nom']} ({n['altitude_m']} m)", method="restyle",
                             args=[{"visible": masque(n["globalId"])}]) for n in utiles]
    camera_3d = dict(eye=dict(x=1.4, y=-1.4, z=1.0), projection=dict(type="perspective"))
    camera_dessus = dict(eye=dict(x=0, y=0, z=2.5), up=dict(x=0, y=1, z=0), projection=dict(type="orthographic"))
    fig.update_layout(
        title=dict(text="Maquette 3D", x=0.5), template="plotly_white", height=850, margin=dict(t=60, l=0, r=0, b=0),
        scene=dict(aspectmode="data", xaxis_title="x (m)", yaxis_title="y (m)", zaxis_title="z (m)",
                   camera=camera_3d),
        updatemenus=[
            dict(buttons=boutons_niveaux, direction="down", x=0, xanchor="left", y=1.06, yanchor="top"),
            dict(type="buttons", direction="right", x=0.3, xanchor="left", y=1.06, yanchor="top",
                 buttons=[dict(label="Perspective", method="relayout", args=[{"scene.camera": camera_3d}]),
                          dict(label="Vue de dessus", method="relayout", args=[{"scene.camera": camera_dessus}])]),
        ],
    )
    return fig


def generer(chemin_ifc: Path, dossier: Path, chemin_geometrie: Path | None = None,
            chemin_devices: Path | None = None) -> Path:
    lire = lambda p: json.loads(Path(p).read_text(encoding="utf-8")) if p and Path(p).is_file() else None
    fig = figure_3d(Path(chemin_ifc), lire(chemin_geometrie), lire(chemin_devices))
    return ecrire_html(fig, Path(dossier) / "vue_3d.html")
