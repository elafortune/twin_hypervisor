# Comparaison avec l'IWCMC 2024 – tests, scénarios et résultats

> Reproduction de Chambon et al., « Analyzing the Integration of 3D Building Digital Twins for Optimal IoT Networks Deployment » (IWCMC 2024) sur le duplex du kit, et confrontation aux figures 4 et 5 de l'article.
> Résumé de l'article et lectures des ambiguïtés : `iwcmc.md`. Résultats bruts : `sorties/iwcmc/campagne/resultats.json` (commande `python -m twinhyp campagne --out sorties`, 33 min sur Ryzen 7 7730U). Figures : `sorties/figures/iwcmc.html` et `comparaison.html`.

## 0. En une phrase

**Avec les valeurs du tableau I, le problème de l'article devient trivial sur ce duplex : un seul équipement couvre 100 % du bâtiment, avec ou sans jumeau.** Les figures 4 et 5 ne se retrouvent qu'en multipliant l'atténuation par obstacle par environ 30 (≈ 10 dB par voxel de plâtre). Le gain apporté par le jumeau a alors le bon signe, mais il est 2 à 3 fois plus faible que dans l'article.

## 1. Ce qui est comparé

| Élément | Article | Notre reproduction |
|---|---|---|
| Bâtiment | duplex IFC2x3 open source | même fichier (`data/duplex_TwinHypervisor.ifc`) |
| Grille | 16 × 34 × 10 voxels de 50 × 50 × 25 cm | 16 × 34 × 24 (deux niveaux) ; variante « 10 couches » testée (F) |
| Positions autorisées | impacts de rayons vers le haut sur les « roofs » | 932 positions (518 au Level 1, 414 au Level 2), antenne dans le voxel libre sous le plafond |
| Modèle radio | équation (2), tableau I, WiFi 2,4 GHz | idem ; lecture principale : L_obs ajouté une fois par voxel obstacle traversé |
| Score, contrainte | équations (3)–(5), µ ∈ {0, 3} | idem (lectures I-3, I-4 dans `iwcmc.md`) |
| Algorithme | PREP-NSGA, 300 itérations, population 40, 160 mutants, γ = 2 m | idem, implémentation maison ; 5 graines |
| Protocole sans jumeau | optimisation avec tous les obstacles en plâtre, évaluation avec jumeau | idem |
| Métriques | couverture stricte (fig. b), qualité moyenne de lien (fig. a) | idem (qualité : moyenne sur tous les voxels libres, non couvert = S_RX) |

Les valeurs de l'article ont été relevées à l'œil sur les figures (±0,005 en couverture, ±0,2 dBm) : `src/twinhyp/m3_iwcmc/article.py`.

**Indicateurs utilisés dans les tableaux** : `couv. 1` = couverture d'un seul équipement ; `Q20` = plus petit nombre d'équipements atteignant 90 % (avec jumeau, µ = 0) ; `gain` = couverture avec jumeau − sans jumeau, moyenne sur n = 1…10 ; `écart fig. 4` = écart absolu moyen à la figure 4 sur les 20 points (avec et sans jumeau, n = 1…10).

## 2. Tests de validation du code (`tests/test_m3_iwcmc.py`, `tests/test_m1_voxels.py`)

Avant de comparer à l'article, on vérifie que chaque brique calcule ce qu'elle prétend calculer.

| Test | Ce qu'il vérifie | Pourquoi c'est important |
|---|---|---|
| `test_perte_calculee_a_la_main` | Couloir de 3 voxels (libre / plâtre / libre) : PL = 37,15 + 20 log 2 + 0,32 dB, lecture voxel = 0,32, lecture mètre = 0,32 × 1 m | Valide l'équation (2) et les deux lectures de L_obs sur un cas calculable à la main |
| `test_sans_jumeau_tout_en_materiau_le_plus_absorbant` | Sans jumeau, tout obstacle vaut 0,32 dB ; avec jumeau, un mur porteur vaut 0,22 dB | Valide le protocole §V.C |
| `test_score_meilleur_serveur_et_normalisation` | v″, F_obj, couverture et qualité sur 2 équipements × 3 voxels | Valide les équations (1), (3), (4) et la métrique de qualité retenue |
| `test_mu_connexite_graphes_connus` | K4 : λ = 3 ; anneau : λ = 2 ; 3 nœuds infaisables pour µ = 3 | Valide Γ(G_O) et le filtre de Whitney (µ = 3 ⇒ au moins 4 nœuds) |
| `test_lien_unidirectionnel_supprime` | Un lien qui ne passe que dans un sens ne crée pas d'arête | « unidirectional connections are dropped » |
| `test_pareto` | Dominance, premier front, meilleur individu par taille | Valide le tri de Pareto de PREP-NSGA |
| `test_antenne_sous_le_plafond_et_a_cote_d_un_mur` | L'antenne se place dans le voxel libre sous le plafond, décalée d'un voxel au-dessus d'un mur | Lecture I-10 |
| `test_valeurs_article_releves` | Les valeurs relevées donnent Q20 = 3 et aucune solution à 4 nœuds sans jumeau (µ = 3) | Cohérence du relevé avec le texte de l'article |
| `test_campagne_ecart_nul_sur_les_valeurs_de_l_article` | L'indicateur d'écart vaut 0 sur les valeurs de l'article | Valide les indicateurs de la campagne |
| `test_campagne_variante_par_groupes` | Les pertes reconstruites à partir des comptes par matériau = calcul direct | Valide l'astuce qui permet toutes les variantes sans relancer le lancer de rayons (écart mesuré sur le duplex : 8 × 10⁻⁷ dB) |
| `test_parite_rayon_vertical_dans_un_cube`, `test_grille_iwcmc_16_x_34`, `test_cages_escalier_libres…`, `test_positions_au_plafond…` | Voxelisation et positions autorisées | La grille est l'entrée de tout le modèle |
| `test_commande_unique_produit_les_8_sorties` | La chaîne complète (M3 réduit) produit un `pareto.json` conforme au schéma | Intégration |

**Expérience K – précision du lancer de rayons.** Sur 20 positions × 8 100 voxels, le nombre de voxels obstacles traversés avec un pas de 5 cm est comparé à un pas de 1,25 cm : **91 % des rayons sont identiques**, écart moyen 0,12 voxel, soit 0,04 dB avec les valeurs du tableau I. Les écarts viennent des rayons qui passent exactement par un coin de voxel (ambiguïté inhérente à toute traversée de grille). Le pas de 5 cm est donc suffisant.

## 3. Expériences

### A. Reproduction avec les valeurs du tableau I (résultat principal, `pareto.json`)

**Question** : obtient-on les figures 4 et 5 avec les paramètres de l'article ?
**Protocole** : PREP-NSGA, 4 scénarios, 5 graines, lecture « voxel ».

| n | 1 | 2 | 3 | 4 | 5 | 10 |
|---|---|---|---|---|---|---|
| Article, couverture avec / sans jumeau | 0,44 / 0,35 | 0,775 / 0,67 | 0,905 / 0,825 | 0,95 / 0,92 | 0,985 / 0,965 | 0,998 / 0,988 |
| Reproduction (médiane 5 graines) | **1 / 1** | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| Article, qualité avec jumeau (dBm) | −45,1 | −35,7 | −31,9 | −29,5 | −28,5 | −25,8 |
| Reproduction | −33,3 | −28,6 | −27,3 | −26,1 | −25,3 | −22,8 |

µ = 3 : 100 % de couverture dès 4 équipements, avec et sans jumeau, et l'environnement sans jumeau **trouve** des solutions à 4 et 5 équipements (l'article n'en trouve pas). Les 5 graines donnent exactement le même front (le problème n'a plus de difficulté).

**Interprétation.** La perte maximale vaut ≈ 62,5 dB en espace libre (19 m) plus au plus 10 dB d'obstacles : le signal reste au-dessus de −65 dBm partout. Avec 0,18 à 0,32 dB par obstacle, la différence entre matériaux (≤ 0,14 dB par voxel) est noyée sous le shadowing (σ = 3,26 dB) : le jumeau n'apporte rien (écart de qualité < 0,05 dB). **Q20 = 1.**

### B. Lecture « dB par mètre traversé » (option 1)

**Question** : l'autre lecture de l'unité change-t-elle la conclusion ?
**Résultat** : non. Elle atténue 2 à 4 fois moins que la lecture « voxel » (un voxel fait 0,5 m en plan, 0,25 m en hauteur) : couverture 100 % dès 1 équipement, qualité −32,0 dBm pour 1 équipement. Avec et sans jumeau identiques.

### C. Facteur sur L_obs : quelle atténuation reproduit l'article ? (référence gloutonne)

**Question** : de combien faudrait-il multiplier les L_obs pour retrouver la figure 4 ?
**Protocole** : front glouton (µ = 0), facteur k de 1 à 100, deux lectures.

| Lecture | k | couv. 1 (avec / sans) | qualité 1 (dBm) | Q20 | gain moyen | gain max | écart fig. 4 |
|---|---|---|---|---|---|---|---|
| voxel | 1 | 1 / 1 | −33,3 | 1 | 0 | 0 | 0,117 |
| voxel | 10 | 0,85 / 0,85 | −48,9 | 2 | 0,000 | 0,002 | 0,102 |
| voxel | 20 | 0,58 / 0,58 | −51,5 | 2 | 0,000 | 0,001 | 0,066 |
| voxel | 25 | 0,53 / 0,53 | −52,8 | 3 | 0,000 | 0,000 | 0,052 |
| **voxel** | **30** | **0,49 / 0,49** | **−53,8** | **3** | **0,005** | **0,041** | **0,035** |
| voxel | 35 | 0,46 / 0,46 | −54,6 | 4 | −0,002 | 0,017 | 0,025 |
| voxel | 40 | 0,42 / 0,42 | −55,2 | 4 | 0,000 | 0,001 | **0,021** |
| voxel | 50 | 0,36 / 0,36 | −56,1 | 5 | 0,005 | 0,015 | 0,045 |
| mètre | 30 | 0,92 / 0,89 | −47,6 | 1 | 0,002 | 0,025 | 0,108 |
| mètre | 100 | 0,50 / 0,50 | −54,3 | 3 | 0,013 | 0,080 | 0,033 |
| Article | — | 0,44 / 0,35 | −45,1 | 3 | 0,05 | 0,105 | 0 |

**Interprétation.**
- L'écart à la figure 4 est minimal pour k ≈ 30–40 en lecture voxel (≈ 100 en lecture mètre). **k = 30** est retenu car c'est la plus petite valeur qui donne **Q20 = 3, comme l'article**, avec un écart de couverture de 0,035. Il correspond à ≈ 10 dB par voxel de plâtre, 5,4 dB par voxel de béton : l'ordre de grandeur réel d'un mur à 2,4 GHz.
- Avec un facteur 30 sur des valeurs en dB/m, l'hypothèse la plus simple est que l'implémentation d'origine ajoute L_obs **à chaque échantillon du lancer de rayons** (pas de quelques centimètres) et non une fois par obstacle. C'est une question à poser aux auteurs.
- La qualité moyenne reste 9 à 12 dB sous l'article pour 1 à 3 équipements (glouton et PREP-NSGA) : notre métrique de qualité (lecture I-5) n'est sans doute pas exactement la leur.

### D. PREP-NSGA avec L_obs × 30 (5 graines)

| µ = 0, n | 1 | 2 | 3 | 4 | 5 | 10 |
|---|---|---|---|---|---|---|
| Avec jumeau : médiane [min–max] | 0,489 [0,489–0,491] | 0,796 [0,794–0,812] | 0,935 [0,935–0,938] | 0,991 [0,987–0,996] | 0,998 | 1 |
| Sans jumeau (évalué avec jumeau) | 0,491 | 0,782 [0,776–0,782] | 0,892 [0,889–0,892] | 0,996 | 0,998 | 1 |
| Article avec / sans | 0,44 / 0,35 | 0,775 / 0,67 | 0,905 / 0,825 | 0,95 / 0,92 | 0,985 / 0,965 | 0,998 / 0,988 |

| µ = 3, n | 4 | 5 | 6 | 7 | 8 | 10 |
|---|---|---|---|---|---|---|
| Avec jumeau : médiane [min–max] | 0,756 [0,734–0,802] | 0,837 [0,837–0,932] | 0,935 [0,873–0,949] | 0,991 | 0,996 | 1 |
| Sans jumeau | 0,823 [0,702–0,827] | 0,928 [0,766–0,933] | 0,923 [0,864–0,942] | 0,990 | 0,993 | 1 |
| Article avec / sans | 0,939 / — | 0,98 / — | 0,986 / 0,957 | 0,992 / 0,966 | 0,993 / 0,968 | 0,998 / 0,993 |

**Interprétation.**
- **µ = 0** : forme de la figure 4 retrouvée (saturation vers 4–5 équipements). Le jumeau améliore la couverture à 2 et 3 équipements (+1,5 et **+4,3 points**), dans le même sens que l'article (+10,5 et +8 points) mais 2 à 3 fois moins. À 1 équipement, avec et sans jumeau choisissent la même position (le meilleur emplacement unique ne dépend pas des matériaux), alors que l'article montre +9 points.
- **µ = 3** : nos fronts restent sous l'article à 4–6 équipements (0,76 contre 0,94 à n = 4), et l'avantage du jumeau n'est pas visible : les étendues sur 5 graines se recouvrent. Contrairement à l'article, l'optimisation sans jumeau trouve des solutions à 4 et 5 équipements.
- Temps CPU : ≈ 10 s par graine à µ = 0, ≈ 30 s à µ = 3.

### E. Sensibilité de S_RX (tableau I tel quel)

**Question** : l'article aurait-il utilisé une sensibilité plus haute (la figure 3 indique −50 dBm) ?

| S_RX (dBm) | −65 | −60 | −55 | −50 | −45 | −40 |
|---|---|---|---|---|---|---|
| couv. 1 équipement | 1 | 1 | 1 | 1 | 0,996 | 0,915 |

**Interprétation** : non. Même à −50 dBm, un équipement bien placé (au centre, < 10 m de tout voxel) couvre tout. Seule une sensibilité irréaliste de −40 dBm commence à réduire la couverture. La sensibilité n'explique pas l'écart.

### F. Domaine « 16 × 34 × 10 » : le premier niveau seulement

**Question** : le « 10 » du tableau II signifie-t-il que l'article ne modélisait que le premier niveau (10 couches de 25 cm = 2,5 m) ?
**Protocole** : voxels libres limités à z < 2,5 m (4 221 voxels), positions du Level 1 seulement (490).

| k | 1 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|
| couv. 1 équipement | 1 | 0,99 | 0,89 | 0,75 | 0,66 |
| Q20 | 1 | 1 | 2 | 2 | 2 |
| écart fig. 4 | 0,117 | 0,117 | 0,105 | 0,091 | 0,077 |

PREP-NSGA (k = 30) : 75 % avec 1 équipement, 100 % dès 2. **Interprétation** : un seul niveau rend le problème encore plus facile (pas de plancher à traverser) et éloigne des figures. La lecture « deux niveaux » est la plus cohérente.

### G. Shadowing X_σ

| k | sans X | X, graine 0 | graine 1 | graine 2 |
|---|---|---|---|---|
| 1 : couv. 1 / gain moyen | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 |
| 30 : couv. 1 / gain moyen / écart fig. 4 | 0,496 / 0,007 / 0,037 | 0,492 / 0,005 / 0,035 | 0,492 / 0,005 / 0,035 | 0,492 / 0,006 / 0,035 |

**Interprétation** : le tirage du shadowing ne change les résultats qu'au troisième chiffre. Les conclusions ne dépendent pas de la graine de X.

### H. Part du matériau le plus absorbant

**Question** : l'article affirme que l'écart avec / sans jumeau diminue quand la part du matériau le plus absorbant augmente (18 % dans leur duplex, 47 % des voxels obstacles chez nous). Notre part élevée explique-t-elle notre gain plus faible ?
**Protocole** : variantes synthétiques où les faux plafonds (part 21 %, proche des 18 %), puis tout le plâtre (part 0 %), sont comptés en béton ; k = 30.

| Variante | part | couv. 1 avec / sans | gain moyen (glouton) | n = 2 avec / sans (GA) | n = 3 avec / sans (GA) |
|---|---|---|---|---|---|
| Plafonds en plâtre (réel) | 47 % | 0,492 / 0,492 | 0,005 | 0,796 / 0,782 | 0,935 / 0,892 |
| Plafonds en béton | 21 % | 0,506 / 0,499 | 0,006 | **0,846 / 0,796** | 0,954 / 0,914 |
| Tout le plâtre en béton | 0 % | 0,532 / 0,532 | 0,005 | — | — |

**Interprétation** : avec une part proche des 18 %, le gain du jumeau à 2 équipements passe de +1,5 à **+5 points**. Cela va dans le sens de l'affirmation de l'article, sans atteindre ses +10 points. Avec une part nulle, le gain retombe : il faut des matériaux **différents** pour que le jumeau serve.

### I. Validité de l'algorithme génétique

- **Contre la référence gloutonne** (k = 30, µ = 0) : le glouton donne 0,812 à n = 2 et 0,933 à n = 3. PREP-NSGA fait mieux à n ≥ 3 (0,935, 0,991 à n = 4 contre 0,977) mais **moins bien à n = 2** (médiane 0,796 ; seule une graine atteint 0,812). Sans croisement, l'algorithme converge mal pour les petites tailles.
- **Nombre d'itérations** (µ = 3, k = 30, graine 0) : 100, 300 et 1 000 itérations donnent le même front à n = 4–6 (0,75 / 0,84 / 0,94). Ce n'est pas un manque d'itérations, mais un **optimum local** : avec la peine de mort, les mutations qui casseraient temporairement la 3-connexité sont rejetées. Les 5 graines donnent des écarts de 7 à 16 points à n = 4–6.
- **Évolution** (graine 0, µ = 0) : F_obj à n = 2 passe de 6 190 (initialisation par cellules d'intérêt) à 7 907 après 300 itérations.

### J. Autres technologies du tableau I

| Technologie | matériau le plus absorbant | couv. 1 (tableau I) | couv. 1 (× 30) | Q20 (× 30) |
|---|---|---|---|---|
| IoT | bois | 1 | 0,65 | 2 |
| GSM | bois | 1 | 0,69 | 2 |
| DETC | bois | 1 | 0,52 | 3 |
| WiFi 2,4 GHz | plâtre | 1 | 0,49 | 3 |
| 5G | bois | 1 | 0,44 | 4 |
| WiFi 5,2 GHz | mur porteur | 1 | 0,47 | 3 |
| WiFi 5,5 GHz | mur porteur | 1 | 0,42 | 4 |

**Interprétation** : la conclusion de A vaut pour toutes les technologies : avec les valeurs du tableau, un équipement couvre tout le duplex.

### L. Poids α, β de F_obj (k = 30)

| (α, β) | (1, 1) | (1, 0) qualité seule | (0, 1) couverture seule |
|---|---|---|---|
| Q20 | 3 | 4 | 3 |
| gain moyen | 0,005 | 0,000 | 0,006 |

**Interprétation** : sans le terme de couverture (β = 0), l'optimisation privilégie la puissance près des équipements et il faut un équipement de plus pour atteindre 90 %. Le choix (1, 1) de l'article est cohérent avec ses figures.

## 4. Synthèse

| Résultat de l'article | Reproduit avec le tableau I ? | Reproduit avec L_obs × 30 ? |
|---|---|---|
| Couverture croissante avec le nombre d'équipements (fig. 4b) | ✗ (100 % dès 1) | ✓ (écart moyen 0,035) |
| Q20 = 3 | ✗ (1) | ✓ |
| Qualité moyenne de lien (fig. 4a) | ✗ (3 à 12 dB au-dessus) | ≈ (< 2 dB) à partir de 6 équipements ; 9 à 12 dB en dessous à 1–3 |
| Le jumeau améliore la couverture (µ = 0) | ✗ (0) | ✓ même sens, 2 à 3 fois plus faible (+4 points à n = 3) |
| +20 % de couverture à 1 équipement | ✗ | ✗ (même position choisie) |
| µ = 3 : pas de solution sans jumeau à 4–5 équipements | ✗ | ✗ (solutions trouvées) |
| L'écart diminue quand la part du matériau le plus absorbant augmente | — | ✓ partiellement (H) |

**Explications de l'écart, de la plus à la moins probable**
1. **Ordre de grandeur de L_obs** (A, B, C) : les valeurs du tableau I en dB/m, appliquées par obstacle ou par mètre, sont 30 fois trop faibles pour produire les figures. Hypothèse : L_obs appliqué à chaque échantillon du lancer de rayons.
2. **Part du plâtre** (H) : 47 % des voxels obstacles chez nous contre 18 % ; avec 21 %, le gain du jumeau triple à 2 équipements.
3. **Algorithme** (I) : PREP-NSGA sans croisement et avec peine de mort converge vers des optimums locaux à µ = 3 ; l'implémentation d'origine (référence [7], absente du kit) diffère sans doute (initialisation, mutations).
4. **Métrique de qualité** (C) : la formule de la qualité moyenne n'est pas lisible dans le PDF ; la nôtre reproduit la forme mais pas le niveau à 1–3 équipements.
5. Écartés par l'expérience : sensibilité S_RX (E), domaine à un niveau (F), tirage du shadowing (G), pas du lancer de rayons (K), technologie (J).

**Questions à poser aux auteurs**
1. Comment Σ L_obs est-il calculé : par voxel, par mètre, ou par échantillon du lancer de rayons (et avec quel pas) ?
2. Le domaine « 16 × 34 × 10 » couvre-t-il un ou deux niveaux ?
3. Quelle est la formule exacte de la qualité moyenne de lien ?
4. Comment les 18 % de plâtre ont-ils été comptés ?

## 5. Reproduire

```bash
python -m twinhyp run --ifc data/duplex_TwinHypervisor.ifc --params data/parametres.json --obs data/observations.csv --out sorties --etapes m1,m3
python -m twinhyp sensibilite --out sorties     # tableau C rapide (≈ 1 min une fois le cache calculé)
python -m twinhyp campagne --out sorties        # toutes les expériences (≈ 33 min, dont 8 min de lancer de rayons)
python -m twinhyp visualiser --out sorties --sans-3d   # iwcmc.html, comparaison.html
pytest tests/test_m3_iwcmc.py tests/test_m1_voxels.py
```
