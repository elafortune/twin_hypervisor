"""Construit le rapport : figure SVG depuis les sorties (pareto), rapport.md -> rapport.html -> rapport.pdf.

Usage : python outils/rapport_pdf.py [--out sorties]
Dépendances (rapport seulement, pas la chaîne) : `markdown` (pip) ; PDF par Microsoft Edge en mode headless.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]


def svg_couverture(sorties: Path, chemin: Path) -> None:
    """Couverture en fonction du nombre d'équipements (avec jumeau, µ = 0) : article, tableau I, L_obs × 30."""
    def front(f):
        s = next(x for x in json.loads(f.read_text(encoding="utf-8")) if x["scenario"] == "avec jumeau, mu=0")
        return {p["n_equipements"]: p for p in s["front"]}
    t1, x30 = front(sorties / "pareto.json"), front(sorties / "iwcmc" / "pareto_facteur30.json")
    ns = [n for n in range(1, 11) if n in x30]
    series = [("Article (fig. 4b)", "#888888", "6,4", [(n, x30[n]["article"]["couverture"]) for n in ns if x30[n].get("article")]),
              ("Tableau I tel quel (pareto.json)", "#1f6fb4", "", [(n, t1[n]["couverture"]) for n in ns if n in t1]),
              ("L_obs × 30", "#d1495b", "", [(n, x30[n]["couverture"]) for n in ns])]
    W, H, g, d, h, b = 640, 300, 60, 20, 20, 45
    X = lambda n: g + (n - 1) / 9 * (W - g - d)
    Y = lambda c: h + (1 - (c - 0.3) / 0.72) * (H - h - b)
    el = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial" font-size="12">',
          f'<rect width="{W}" height="{H}" fill="white"/>']
    for c in (0.4, 0.6, 0.8, 1.0):
        el.append(f'<line x1="{g}" x2="{W - d}" y1="{Y(c):.1f}" y2="{Y(c):.1f}" stroke="#e5e5e5"/>'
                  f'<text x="{g - 8}" y="{Y(c) + 4:.1f}" text-anchor="end">{int(c * 100)} %</text>')
    for n in ns:
        el.append(f'<text x="{X(n):.1f}" y="{H - b + 18}" text-anchor="middle">{n}</text>')
    el.append(f'<text x="{(W + g) / 2}" y="{H - 6}" text-anchor="middle">nombre d\'équipements (avec jumeau, µ = 0)</text>'
              f'<text transform="translate(14,{(H - b) / 2}) rotate(-90)" text-anchor="middle">couverture</text>'
              f'<line x1="{g}" x2="{g}" y1="{h}" y2="{H - b}" stroke="#333"/>'
              f'<line x1="{g}" x2="{W - d}" y1="{H - b}" y2="{H - b}" stroke="#333"/>')
    for k, (nom, coul, tiret, pts) in enumerate(series):
        chemin_pts = " ".join(f"{X(n):.1f},{Y(c):.1f}" for n, c in pts)
        el.append(f'<polyline points="{chemin_pts}" fill="none" stroke="{coul}" stroke-width="2.2" stroke-dasharray="{tiret}"/>')
        el += [f'<circle cx="{X(n):.1f}" cy="{Y(c):.1f}" r="3" fill="{coul}"/>' for n, c in pts]
        y = h + 150 + 18 * k
        el.append(f'<line x1="{W - 250}" x2="{W - 225}" y1="{y}" y2="{y}" stroke="{coul}" stroke-width="2.2" stroke-dasharray="{tiret}"/>'
                  f'<text x="{W - 218}" y="{y + 4}">{nom}</text>')
    el.append("</svg>")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(el), encoding="utf-8")


CSS = """body{font-family:Calibri,Arial,sans-serif;font-size:10pt;line-height:1.3;margin:0;color:#111}
h1{font-size:15pt;margin:0 0 4pt}h2{font-size:12pt;margin:10pt 0 3pt;border-bottom:1px solid #ccc}
table{border-collapse:collapse;width:100%;margin:4pt 0;font-size:8.6pt}th,td{border:1px solid #bbb;padding:2pt 4pt;vertical-align:top;text-align:left}
th{background:#f0f0f0}code{font-family:Consolas,monospace;font-size:8.6pt}p{margin:3pt 0}img{display:block;margin:4pt auto;max-width:80%}
@page{size:A4;margin:14mm 15mm}"""


def construire(sorties: Path) -> Path:
    import markdown

    svg_couverture(sorties, RACINE / "figures_rapport" / "iwcmc_couverture.svg")
    md = (RACINE / "rapport.md").read_text(encoding="utf-8").replace("iwcmc_couverture.png", "iwcmc_couverture.svg")
    html = markdown.markdown(md, extensions=["tables"])
    page = RACINE / "rapport.html"
    page.write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Rapport TwinHypervisor</title>'
                    f"<style>{CSS}</style></head><body>{html}</body></html>", encoding="utf-8")
    edge = next((e for e in EDGE if e.is_file()), None)
    if edge is None:
        print("Edge introuvable : rapport.html écrit, PDF non produit")
        return page
    import tempfile

    pdf = RACINE / "rapport.pdf"
    with tempfile.TemporaryDirectory() as profil:  # instance isolée (un Edge déjà ouvert ignorerait la commande)
        subprocess.run([str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profil}",
                        f"--print-to-pdf={pdf}", page.as_uri()], check=True, timeout=180)
    return pdf


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--out", type=Path, default=RACINE / "sorties")
    print(construire(a.parse_args().out))
