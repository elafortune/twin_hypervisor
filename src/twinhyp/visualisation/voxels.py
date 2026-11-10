"""Coupes horizontales de la grille de voxels (matériau par voxel) et positions autorisées A.

Menu : une coupe par couche de voxels (altitude du centre). Les positions au plafond
dont l'altitude tombe dans la couche affichée sont superposées.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from twinhyp.visualisation import ecrire_html

COULEURS = {0: "#ffffff", 1: "#f59e0b", 2: "#6b7280", 3: "#b91c1c", 4: "#92400e", 5: "#a855f7"}


def figure_voxels(chemin_npz: Path) -> go.Figure:
    d = np.load(chemin_npz)
    cats = {int(k): v for k, v in json.loads(str(d["categories"])).items()}
    mat, o, pas = d["materiau"], d["origine"], d["pas"]
    nx, ny, nz = mat.shape
    xs = o[0] + (np.arange(nx) + 0.5) * pas[0]
    ys = o[1] + (np.arange(ny) + 0.5) * pas[1]
    n = len(cats)
    echelle = [[v, COULEURS[c]] for c in sorted(cats) for v in (c / n, (c + 1) / n)]
    fig = go.Figure()
    for k in range(nz):
        z = o[2] + (k + 0.5) * pas[2]
        texte = np.vectorize(lambda c: cats[int(c)])(mat[:, :, k].T)
        fig.add_trace(go.Heatmap(x=xs, y=ys, z=mat[:, :, k].T, zmin=0, zmax=n, colorscale=echelle,
                                 text=texte, hovertemplate="x %{x:.2f} · y %{y:.2f}<br>%{text}<extra></extra>",
                                 showscale=False, visible=k == 0))
        P = d["positions"]
        sel = P[(P[:, 2] >= z - pas[2] / 2) & (P[:, 2] < z + pas[2] / 2)] if len(P) else P
        fig.add_trace(go.Scatter(x=sel[:, 0], y=sel[:, 1], mode="markers", visible=k == 0,
                                 marker=dict(size=5, color="#16a34a", symbol="square"),
                                 name="positions A", hovertemplate="A : z = %{customdata:.2f} m<extra></extra>",
                                 customdata=sel[:, 2]))
    for c in sorted(cats):  # légende des matériaux
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=cats[c],
                                 marker=dict(size=12, color=COULEURS[c], symbol="square",
                                             line=dict(width=1, color="#334155"))))
    boutons = []
    for k in range(nz):
        vis = [False] * (2 * nz) + [True] * n
        vis[2 * k] = vis[2 * k + 1] = True
        z = o[2] + (k + 0.5) * pas[2]
        boutons.append(dict(label=f"z = {z:.2f} m", method="update",
                            args=[{"visible": vis}, {"title.text": f"Voxels – coupe à z = {z:.2f} m"}]))
    fig.update_layout(title=dict(text=f"Voxels – coupe à z = {o[2] + pas[2] / 2:.2f} m", x=0.5),
                      template="plotly_white", height=850,
                      updatemenus=[dict(buttons=boutons, direction="down", x=0, xanchor="left", y=1.1)],
                      xaxis=dict(title="x (m)", constrain="domain"),
                      yaxis=dict(title="y (m)", scaleanchor="x", scaleratio=1), margin=dict(t=90))
    return fig


def generer(chemin_npz: Path, dossier: Path) -> Path:
    return ecrire_html(figure_voxels(chemin_npz), Path(dossier) / "voxels.html")
