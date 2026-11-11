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
    """Couverture selon le nombre d'équipements, deux panneaux (µ = 0 : fig. 4b ; µ = 3 : fig. 5) ; avec et sans
    jumeau ; article (gris), L_obs × 30 (couleur), tableau I tel quel (bleu, 100 % partout)."""
    def fronts(f):
        return {s["scenario"]: {p["n_equipements"]: p for p in s["front"]} for s in json.loads(f.read_text(encoding="utf-8"))}
    t1, x30 = fronts(sorties / "pareto.json"), fronts(sorties / "iwcmc" / "pareto_facteur30.json")
    W, H, PW = 820, 300, 380
    el = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial" font-size="11">',
          f'<rect width="{W}" height="{H}" fill="white"/>']
    for k, (mu, titre) in enumerate([(0, "µ = 0 (figure 4b)"), (3, "µ = 3 (figure 5)")]):
        g, d, h, b = 50 + k * (PW + 30), 10, 26, 40
        x1 = g + PW - 50
        X = lambda n: g + (n - 1) / 9 * (x1 - g)
        Y = lambda c: h + (1 - (c - 0.3) / 0.72) * (H - h - b)
        el.append(f'<text x="{(g + x1) / 2}" y="14" text-anchor="middle" font-weight="bold">{titre}</text>')
        for c in (0.4, 0.6, 0.8, 1.0):
            el.append(f'<line x1="{g}" x2="{x1}" y1="{Y(c):.1f}" y2="{Y(c):.1f}" stroke="#e5e5e5"/>'
                      f'<text x="{g - 6}" y="{Y(c) + 4:.1f}" text-anchor="end">{int(c * 100)} %</text>')
        for n in range(1, 11):
            el.append(f'<text x="{X(n):.1f}" y="{H - b + 16}" text-anchor="middle">{n}</text>')
        el.append(f'<text x="{(g + x1) / 2}" y="{H - 8}" text-anchor="middle">nombre d\'équipements</text>'
                  f'<line x1="{g}" x2="{g}" y1="{h}" y2="{H - b}" stroke="#333"/>'
                  f'<line x1="{g}" x2="{x1}" y1="{H - b}" y2="{H - b}" stroke="#333"/>')
        avec, sans = f"avec jumeau, mu={mu}", f"sans jumeau, mu={mu}"
        series = [("article, avec jumeau", "#555555", "6,4", [(n, p["article"]["couverture"]) for n, p in x30[avec].items() if p.get("article", {}).get("couverture")]),
                  ("article, sans jumeau", "#aaaaaa", "2,3", [(n, p["article"]["couverture"]) for n, p in x30[sans].items() if p.get("article", {}).get("couverture")]),
                  ("L_obs × 30, avec jumeau", "#d1495b", "", [(n, p["couverture"]) for n, p in x30[avec].items()]),
                  ("L_obs × 30, sans jumeau", "#edae49", "", [(n, p["couverture"]) for n, p in x30[sans].items()]),
                  ("tableau I tel quel (pareto.json)", "#1f6fb4", "", [(n, p["couverture"]) for n, p in t1[avec].items()])]
        for j, (nom, coul, tiret, pts) in enumerate(series):
            pts = sorted(pts)
            el.append(f'<polyline points="{" ".join(f"{X(n):.1f},{Y(c):.1f}" for n, c in pts)}" fill="none" '
                      f'stroke="{coul}" stroke-width="2" stroke-dasharray="{tiret}"/>')
            el += [f'<circle cx="{X(n):.1f}" cy="{Y(c):.1f}" r="2.5" fill="{coul}"/>' for n, c in pts]
            if k == 1:
                y = h + 120 + 16 * j
                el.append(f'<line x1="{g + 140}" x2="{g + 162}" y1="{y}" y2="{y}" stroke="{coul}" stroke-width="2" stroke-dasharray="{tiret}"/>'
                          f'<text x="{g + 167}" y="{y + 4}">{nom}</text>')
    el.append("</svg>")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(el), encoding="utf-8")


CSS = """body{font-family:Calibri,Arial,sans-serif;font-size:10pt;line-height:1.3;margin:0;color:#111}
h1{font-size:15pt;margin:0 0 4pt}h2{font-size:12pt;margin:10pt 0 3pt;border-bottom:1px solid #ccc;break-after:avoid}table,img{break-inside:avoid}
table{border-collapse:collapse;width:100%;margin:4pt 0;font-size:8.6pt}th,td{border:1px solid #bbb;padding:2pt 4pt;vertical-align:top;text-align:left}
th{background:#f0f0f0}code{font-family:Consolas,monospace;font-size:8.6pt}p{margin:3pt 0}img{display:block;margin:4pt auto;max-width:100%}
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
        tmp = Path(profil) / "rapport.pdf"
        subprocess.run([str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profil}",
                        f"--print-to-pdf={tmp}", page.as_uri()], check=True, timeout=180)
        import time

        for _ in range(90):  # Edge peut rendre la main avant d'avoir fini d'écrire
            if tmp.is_file() and tmp.stat().st_size > 0:
                time.sleep(1)
                break
            time.sleep(1)
        else:
            raise RuntimeError("Edge n'a pas produit le PDF")
        try:
            tmp.replace(pdf)
        except PermissionError:  # rapport.pdf ouvert dans un lecteur (fichier verrouillé sous Windows)
            pdf = RACINE / "rapport_nouveau.pdf"
            tmp.replace(pdf)
            print("rapport.pdf est ouvert ailleurs : nouveau PDF écrit dans rapport_nouveau.pdf")
    return pdf


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--out", type=Path, default=RACINE / "sorties")
    print(construire(a.parse_args().out))
