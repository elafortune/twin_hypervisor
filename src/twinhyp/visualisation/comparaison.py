"""Figures de la campagne de comparaison IWCMC (sorties/iwcmc/campagne/resultats.json)."""

from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from twinhyp.m3_iwcmc import article
from twinhyp.visualisation import ecrire_html

BLEU, NOIR, GRIS = "#2563eb", "#111827", "#9ca3af"


def figure(R: dict) -> go.Figure:
    fig = make_subplots(rows=3, cols=2, vertical_spacing=0.09, horizontal_spacing=0.1, subplot_titles=[
        "C. Écart de couverture à la figure 4 selon le facteur sur L_obs",
        "E. Couverture d'un équipement selon S_RX (tableau I)",
        "D. PREP-NSGA × 30, µ = 0 : médiane et étendue sur 5 graines",
        "D. PREP-NSGA × 30, µ = 3 : médiane et étendue sur 5 graines",
        "H. Gain du jumeau selon la part de plâtre (× 30)",
        "J. Couverture d'1 équipement par technologie"])
    # C
    for lecture, couleur in (("voxel", BLEU), ("metre", NOIR)):
        lignes = [l for l in R.get("C_facteur", []) if l["lecture"] == lecture]
        fig.add_trace(go.Scatter(x=[l["facteur"] for l in lignes], y=[l["ecart_couverture"] for l in lignes],
                                 mode="lines+markers", name=f"lecture {lecture}", line=dict(color=couleur)), 1, 1)
    fig.update_xaxes(type="log", title_text="facteur k", row=1, col=1)
    # E
    lignes = R.get("E_srx", [])
    fig.add_trace(go.Scatter(x=[l["S_RX"] for l in lignes], y=[l["couv_1_avec"] for l in lignes], mode="lines+markers",
                             name="1 équipement, avec jumeau", line=dict(color=BLEU)), 1, 2)
    fig.add_hline(y=0.44, line_dash="dot", line_color=GRIS, row=1, col=2)
    fig.update_xaxes(title_text="S_RX (dBm)", row=1, col=2)
    # D
    for col, mu in ((1, 0), (2, 3)):
        for jumeau, couleur in ((True, BLEU), (False, NOIR)):
            sc = R.get("D_ga_facteur30", {}).get(f"{'avec' if jumeau else 'sans'} jumeau, mu={mu}")
            if not sc:
                continue
            n = sorted(int(k) for k in sc["par_n"])
            s = [sc["par_n"][str(k)] for k in n]
            fig.add_trace(go.Scatter(x=n, y=[x["couverture_mediane"] for x in s], mode="lines+markers",
                                     error_y=dict(type="data", symmetric=False,
                                                  array=[x["couverture_max"] - x["couverture_mediane"] for x in s],
                                                  arrayminus=[x["couverture_mediane"] - x["couverture_min"] for x in s]),
                                     name=f"reproduction {'avec' if jumeau else 'sans'} jumeau µ={mu}",
                                     line=dict(color=couleur)), 2, col)
            ref = article.FIGURES[(jumeau, mu)]
            fig.add_trace(go.Scatter(x=sorted(ref), y=[ref[k][0] for k in sorted(ref)], mode="markers+lines",
                                     marker=dict(symbol="diamond-open", size=9), line=dict(color=couleur, dash="dot"),
                                     name=f"article {'w/DT' if jumeau else 'w/oDT'} µ={mu}"), 2, col)
    # H
    lignes = [l for l in R.get("H_part_platre", []) if l["facteur"] == 30]
    fig.add_trace(go.Scatter(x=[l["part_plus_absorbant"] for l in lignes], y=[l["gain_couverture_moyen"] for l in lignes],
                             mode="lines+markers+text", text=[l["variante"] for l in lignes], textposition="top center",
                             name="gain du jumeau", line=dict(color=BLEU)), 3, 1)
    fig.update_xaxes(title_text="part du matériau le plus absorbant parmi les voxels obstacles", row=3, col=1)
    # J
    lignes = R.get("J_technologies", [])
    for k, couleur in ((1, GRIS), (30, BLEU)):
        sel = [l for l in lignes if l["facteur"] == k]
        fig.add_trace(go.Bar(x=[l["technologie"] for l in sel], y=[l["couv_1_avec"] for l in sel], name=f"facteur {k}",
                             marker_color=couleur), 3, 2)
    fig.update_layout(template="plotly_white", height=1400, title=dict(text="Campagne de comparaison IWCMC", x=0.5))
    return fig


def generer(dossier_sorties: Path, dossier: Path) -> Path | None:
    f = dossier_sorties / "iwcmc" / "campagne" / "resultats.json"
    if not f.is_file():
        return None
    return ecrire_html(figure(json.loads(f.read_text(encoding="utf-8"))), Path(dossier) / "comparaison.html")
