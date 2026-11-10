"""Fronts de Pareto de la reproduction IWCMC comparés aux figures 4 et 5 de l'article.

Une ligne par µ (0, 3), deux colonnes (qualité moyenne de lien, couverture). Courbes : article
(pointillés), notre reproduction avec les valeurs du tableau I (pareto.json) et, si présentes,
les variantes à atténuation renforcée (sorties/iwcmc/pareto_facteur*.json).
"""

from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from twinhyp.m3_iwcmc import article
from twinhyp.visualisation import ecrire_html

COULEUR = {True: "#2563eb", False: "#111827"}


def figure(fichiers: dict[str, Path]) -> go.Figure:
    fig = make_subplots(rows=2, cols=2, horizontal_spacing=0.1, vertical_spacing=0.14,
                        subplot_titles=["µ = 0 : qualité moyenne de lien (dBm)", "µ = 0 : couverture",
                                        "µ = 3 : qualité moyenne de lien (dBm)", "µ = 3 : couverture"])
    styles = ["solid", "dash", "dot", "dashdot"]
    for ligne, mu in enumerate((0, 3), start=1):
        for jumeau in (True, False):
            ref = article.FIGURES[(jumeau, mu)]
            n = sorted(ref)
            for col, k in ((1, 1), (2, 0)):
                fig.add_trace(go.Scatter(x=n, y=[ref[i][k] for i in n], mode="markers+lines",
                                         line=dict(color=COULEUR[jumeau], dash="dot", width=1),
                                         marker=dict(symbol="diamond-open", size=9),
                                         name=f"Article {'w/DT' if jumeau else 'w/oDT'}", legendgroup=f"a{jumeau}",
                                         showlegend=ligne == 1 and col == 1), row=ligne, col=col)
        for s, (libelle, chemin) in enumerate(fichiers.items()):
            for sc in json.loads(Path(chemin).read_text(encoding="utf-8")):
                if not sc["scenario"].endswith(f"mu={mu}") or not sc["front"]:
                    continue
                jumeau = sc["scenario"].startswith("avec")
                pts = sc["front"]
                for col, cle in ((1, "qualite_lien_moyenne_dBm"), (2, "couverture")):
                    fig.add_trace(go.Scatter(
                        x=[p["n_equipements"] for p in pts], y=[p[cle] for p in pts], mode="markers+lines",
                        line=dict(color=COULEUR[jumeau], dash=styles[(s + 1) % len(styles)], width=2),
                        name=f"{libelle} {'avec' if jumeau else 'sans'} jumeau", legendgroup=f"{libelle}{jumeau}",
                        showlegend=ligne == 1 and col == 1), row=ligne, col=col)
    fig.update_xaxes(title_text="nombre d'équipements", dtick=1)
    fig.update_layout(template="plotly_white", height=900, title=dict(text="IWCMC 2024 : article contre reproduction", x=0.5))
    return fig


def generer(dossier_sorties: Path, dossier: Path) -> Path | None:
    principal = dossier_sorties / "pareto.json"
    if not principal.is_file() or not json.loads(principal.read_text(encoding="utf-8")):
        return None
    fichiers = {"Tableau I": principal}
    for f in sorted((dossier_sorties / "iwcmc").glob("pareto_facteur*.json")):
        fichiers[f"L × {f.stem.removeprefix('pareto_facteur')}"] = f
    return ecrire_html(figure(fichiers), Path(dossier) / "iwcmc.html")
