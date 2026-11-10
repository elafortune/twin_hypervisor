"""Plan 2D interactif par niveau, construit uniquement à partir de geometry.json.

Survol d'un espace : nom, nom long, GlobalId, surfaces, hauteur, occupable.
Menu déroulant : choix du niveau. Légende cliquable : couches (espaces, portes,
sorties, escaliers, liaisons par type, anomalies).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

from twinhyp.visualisation import PALETTE_LIAISONS, ecrire_html

COULEUR_OCCUPABLE = "rgba(147, 197, 253, 0.45)"
COULEUR_NON_OCCUPABLE = "rgba(203, 213, 225, 0.55)"
COULEUR_ANOMALIE = "#ea580c"


def _infobulle_espace(e: dict, anomalies: list[dict]) -> str:
    lignes = [
        f"<b>{e['nom']}</b> – {e.get('nom_long') or ''}",
        f"GlobalId : {e['globalId']}",
        f"Surface : {e['surface_m2']} m² ({e.get('surface_source', '')})",
        f"Surface géométrique : {e.get('surface_geometrique_m2')} m²",
        f"Hauteur : {e['hauteur_m']} m · occupable : {'oui' if e['occupable'] else 'non'}",
    ]
    lignes += [f"<span style='color:{COULEUR_ANOMALIE}'>⚠ {a['description'][:110]}</span>" for a in anomalies]
    return "<br>".join(lignes)


def figure_plan(geometrie: dict) -> go.Figure:
    niveaux = {n["globalId"]: n for n in geometrie["niveaux"]}
    espaces = {e["globalId"]: e for e in geometrie["espaces"]}
    anomalies_de = defaultdict(list)
    for a in geometrie.get("anomalies", []):
        for gid in a.get("elements_concernes", [a["element_globalId"]]):
            anomalies_de[gid].append(a)
    # niveaux affichés : ceux qui portent des espaces, du bas vers le haut
    affiches = [gid for gid in niveaux if any(e["niveau_globalId"] == gid for e in espaces.values())]

    fig = go.Figure()
    traces_du_niveau = defaultdict(list)

    def ajouter(trace, niveau_gid):
        traces_du_niveau[niveau_gid].append(len(fig.data))
        fig.add_trace(trace)

    for ngid in affiches:
        visible = ngid == affiches[0]
        # Espaces ---------------------------------------------------------
        for i, e in enumerate(sorted((e for e in espaces.values() if e["niveau_globalId"] == ngid),
                                     key=lambda e: e["nom"])):
            xs = [p[0] for p in e["polygone_xy"]] + [e["polygone_xy"][0][0]]
            ys = [p[1] for p in e["polygone_xy"]] + [e["polygone_xy"][0][1]]
            anomal = bool(anomalies_de.get(e["globalId"]))
            ajouter(go.Scatter(
                x=xs, y=ys, fill="toself", mode="lines", visible=visible,
                fillcolor=COULEUR_OCCUPABLE if e["occupable"] else COULEUR_NON_OCCUPABLE,
                line=dict(color=COULEUR_ANOMALIE if anomal else "#1e3a8a", width=3 if anomal else 1),
                name="Espaces", legendgroup="espaces", showlegend=i == 0,
                hoveron="fills", text=_infobulle_espace(e, anomalies_de.get(e["globalId"], [])),
                hoverinfo="text"), ngid)
        etiquettes = [e for e in espaces.values() if e["niveau_globalId"] == ngid]
        ajouter(go.Scatter(
            x=[e["centre_xy"][0] for e in etiquettes], y=[e["centre_xy"][1] for e in etiquettes],
            mode="text", text=[f"{e['nom']}<br><sub>{e.get('nom_long') or ''}</sub>" for e in etiquettes],
            textfont=dict(size=10, color="#0f172a"), hoverinfo="skip", showlegend=False,
            visible=visible), ngid)

        # Liaisons (étape 2) ----------------------------------------------
        par_type = defaultdict(lambda: ([], [], []))
        for l in geometrie.get("liaisons", []):
            a, b = espaces.get(l["de"]), espaces.get(l["vers"])
            if not a or not b or ngid not in (a["niveau_globalId"], b["niveau_globalId"]):
                continue
            xs, ys, txt = par_type[l["type"]]
            xs += [a["centre_xy"][0], b["centre_xy"][0], None]
            ys += [a["centre_xy"][1], b["centre_xy"][1], None]
            txt += [f"{l['type']} : {a['nom']} ↔ {b['nom']}"] * 3
        for t, (xs, ys, txt) in sorted(par_type.items()):
            ajouter(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=PALETTE_LIAISONS.get(t, "#000"),
                                                                    width=2, dash="dot" if t == "escalier" else "solid"),
                               name=f"Liaison {t}", legendgroup=f"l_{t}", text=txt, hoverinfo="text",
                               visible=visible), ngid)

        # Escaliers ---------------------------------------------------------
        z_niveau = niveaux[ngid]["altitude_m"]
        for j, s in enumerate(geometrie.get("escaliers", [])):
            if not (s["z_bas_m"] - 0.3 <= z_niveau <= s["z_haut_m"] + 0.3):
                continue
            (x0, y0), (x1, y1) = s["boite_xy"]
            ajouter(go.Scatter(
                x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0], mode="lines",
                line=dict(color="#9333ea", width=2, dash="dash"), fill="toself",
                fillcolor="rgba(147, 51, 234, 0.12)", name="Escaliers", legendgroup="escaliers",
                showlegend=j == 0, hoveron="fills", hoverinfo="text", visible=visible,
                text=f"<b>Escalier</b><br>{s['globalId']}<br>z : {s['z_bas_m']} → {s['z_haut_m']} m"), ngid)

        # Portes ------------------------------------------------------------
        portes = [p for p in geometrie["portes"] if p["position_xyz"]
                  and (p["niveau_globalId"] == ngid or any(espaces.get(g, {}).get("niveau_globalId") == ngid
                                                            for g in p["espaces"]))]
        for est_sortie, nom, symbole, couleur in [(False, "Portes", "square", "#2563eb"),
                                                 (True, "Sorties", "star", "#dc2626")]:
            sel = [p for p in portes if p["sortie"] == est_sortie]
            if not sel:
                continue
            ajouter(go.Scatter(
                x=[p["position_xyz"][0] for p in sel], y=[p["position_xyz"][1] for p in sel],
                mode="markers", marker=dict(symbol=symbole, size=13 if est_sortie else 9, color=couleur,
                                            line=dict(width=1, color="white")),
                name=nom, legendgroup=nom, visible=visible, hoverinfo="text",
                text=[(f"<b>{'Sortie' if est_sortie else 'Porte'}</b> {p['globalId']}<br>"
                       f"largeur {p['largeur_m']} m<br>espaces : "
                       + ", ".join(espaces[g]["nom"] for g in p["espaces"] if g in espaces)
                       + "".join(f"<br><span style='color:{COULEUR_ANOMALIE}'>⚠ {a['description'][:110]}</span>"
                                 for a in anomalies_de.get(p["globalId"], [])))
                      for p in sel]), ngid)

    n = len(fig.data)
    boutons = []
    for ngid in affiches:
        masque = [False] * n
        for i in traces_du_niveau[ngid]:
            masque[i] = True
        nv = niveaux[ngid]
        boutons.append(dict(label=f"{nv['nom']} ({nv['altitude_m']} m)", method="update",
                            args=[{"visible": masque}, {"title.text": f"Plan – {nv['nom']}"}]))
    premier = niveaux[affiches[0]]["nom"] if affiches else ""
    fig.update_layout(
        title=dict(text=f"Plan – {premier}", x=0.5), template="plotly_white", hovermode="closest",
        updatemenus=[dict(buttons=boutons, direction="down", x=0, xanchor="left", y=1.12, yanchor="top")],
        legend=dict(itemclick="toggle", itemdoubleclick="toggleothers"),
        xaxis=dict(title="x (m)", constrain="domain"),
        yaxis=dict(title="y (m)", scaleanchor="x", scaleratio=1),
        margin=dict(t=90), height=800,
    )
    return fig


def generer(chemin_geometrie: Path, dossier: Path) -> Path:
    geometrie = json.loads(Path(chemin_geometrie).read_text(encoding="utf-8"))
    return ecrire_html(figure_plan(geometrie), Path(dossier) / "plan_2d.html")
