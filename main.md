# Mémo – commandes et résultats

Depuis `C:\Users\emeri\twin_hypervisor`, après `conda activate twinhyp`.

## Commandes

| Commande | À quoi elle sert |
|---|---|
| `python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc --params data/parametres.json --obs data/observations.csv --out sorties` | Rejoue toute la chaîne M1 → M6 et écrit les 8 sorties dans `sorties/` |
| `… run … --etapes m1` | Relance seulement certains modules (ex. `m1,m2`) |
| `python -m twinhyp visualiser --out sorties` | Crée `sorties/figures/plan_2d.html` et `vue_3d.html` (double-clic pour ouvrir) |
| `python -m twinhyp visualiser --out sorties --sans-3d` | Plan 2D seul (1 s au lieu de 15 s) |
| `python -m twinhyp valider --out sorties` | Revérifie que les sorties respectent schémas et formes SHACL |
| `pytest` | Lance tous les tests (~25 s) |
| `pytest -m "not integration"` | Tests rapides seulement |

## Résultats par phase

| Phase | Résultat en une phrase |
|---|---|
| 0 – Squelette | La commande unique produit les 8 sorties conformes et `execution.json` trace machine, versions et durées. |
| 1 – Extraction IFC | 4 niveaux, 21 espaces (R301 seul non occupable), 14 portes dont 4 sorties, 2 escaliers, extraits en 1,4 s. |
| 1 – Anomalies | 7 constats : `B202` en double (dont un vrai `B203`), B105 « Room » au lieu d'escalier, `IsFireExit` textuel, escalier B rattaché au toit, marches en pieds. |
| 1 – Surfaces | La surface géométrique est 7 à 23 % sous « GSA BIM Area » partout : convention de mesure, pas une anomalie. |
| 1 – Réponses préliminaires | Q05 = 138,16 m² · Q10 = 134,53 m² · Q12 = A204, B204 · Q14 = 4 portes de 0,762 m. |
| 2 – Connectivité | *à venir* |

## Où trouver le détail

- Décisions et résultats des étapes 0 à 2 : `docs/etape0a2.md`
- Journal daté (y compris impasses) : `docs/carnet_de_bord.md`
- Vérifications à la main : `docs/verification_bimvision.md`
- Trace des prompts (déclaration IA) : `docs/prompt.md`
