"""Valeurs des figures 4 et 5 de l'IWCMC, relevées à l'œil sur le PDF (précision ≈ ±0,005 en
couverture, ±0,2 dBm en qualité). Servent uniquement à la confrontation dans pareto.json."""

# (avec_jumeau, mu) -> {n: (couverture, qualité moyenne de lien en dBm)}
FIGURES = {
    (True, 0): {1: (0.44, -45.1), 2: (0.775, -35.7), 3: (0.905, -31.9), 4: (0.95, -29.5), 5: (0.985, -28.5),
                6: (0.99, -27.8), 7: (0.99, -27.2), 8: (0.995, -26.6), 9: (0.997, -26.2), 10: (0.998, -25.8)},
    (False, 0): {1: (0.35, -48.6), 2: (0.67, -38.9), 3: (0.825, -33.9), 4: (0.92, -31.0), 5: (0.965, -29.4),
                 6: (0.97, -28.6), 7: (0.975, -27.8), 8: (0.98, -27.1), 9: (0.985, -26.6), 10: (0.988, -26.3)},
    (True, 3): {4: (0.939, -29.5), 5: (0.98, -28.6), 6: (0.986, -27.7), 7: (0.992, -27.2), 8: (0.993, -26.7),
                9: (0.997, -26.3), 10: (0.998, -25.9)},
    (False, 3): {6: (0.957, -29.2), 7: (0.966, -28.4), 8: (0.968, -27.7), 9: (0.986, -26.9), 10: (0.993, -26.3)},
}


def point(avec_jumeau: bool, mu: int, n: int) -> dict | None:
    v = FIGURES.get((avec_jumeau, mu), {}).get(n)
    return {"couverture": v[0], "qualite_lien_moyenne_dBm": v[1]} if v else None
