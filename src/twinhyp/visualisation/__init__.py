"""Visualisations interactives (plotly, HTML hors ligne).

- `plan2d` : plan par niveau à partir de geometry.json (espaces, portes, sorties,
  escaliers, liaisons, anomalies) — vérification de M1/M2/M5.
- `vue3d` : maquette 3D à partir de l'IFC, filtrable par niveau, avec vue de
  dessus orthographique — servira à montrer les équipements de M3/M4.
"""

from pathlib import Path

PALETTE_LIAISONS = {"porte": "#2563eb", "ouverture": "#16a34a", "escalier": "#9333ea"}


def ecrire_html(fig, chemin: Path) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # plotly.min.js écrit une seule fois à côté des pages : consultable hors ligne
    fig.write_html(str(chemin), include_plotlyjs="directory", full_html=True)
    return chemin
