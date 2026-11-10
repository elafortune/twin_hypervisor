# IWCMC 2024 – résumé de l'article et décalages de notre reproduction

> Chambon, Sahli, Rachedi, Mebarki, « Analyzing the Integration of 3D Building Digital Twins for Optimal IoT Networks Deployment », IWCMC 2024.
> Résumé rédigé pour vérifier ma compréhension. Paraphrase ; les citations sont courtes et entre guillemets. L'article lui-même n'est pas versionné (consigne du kit).

## 1. Question posée

Que gagne-t-on à utiliser le **jumeau numérique** (géométrie **et matériaux** des obstacles) pour optimiser le déploiement d'un réseau IoT intérieur, par rapport à un environnement où l'on connaît les obstacles **sans leurs matériaux** ? Réponse de l'article : jusqu'à **+8 %** de qualité moyenne de lien (+4 % en moyenne) et **+20 %** de couverture (1 équipement ; +5 % en moyenne) pour µ = 0 ; pour µ = 3, gains plus faibles (+3 % / +2 %), mais l'environnement sans jumeau **ne trouve aucune solution à 4 ou 5 équipements**.

## 2. Modèle de l'environnement (§III.A)

- Niveaux lus dans le jumeau (ou inférés par DBSCAN sur les toits).
- **Positions autorisées** A_i par niveau : rayons lancés **vers le haut** depuis chaque point d'une grille de pas ρ ; les impacts sur une surface « roof » forment A_i ; A = ∪ A_i.
- **Grille de voxels** V couvrant le bâtiment : v = 0 pour un voxel d'obstacle (« walls, roofs and ceilings »), v = 1 pour l'espace libre à couvrir.

## 3. Modèle radio (§III.B, équation 2, tableau I)

- Perte en « per meter » L_obs selon le matériau et la technologie (tableau I, d'après Kacou et al.).
- **PL[o, p] = PL₀ + 20 log‖oₙ − p‖ + Σ_{obs ∈ Θ} L_obs + X_σ**, Θ = « set of obstacles between oₙ and p obtained by raycast », X_σ gaussien centré.
- WiFi 2,4 GHz (technologie retenue) : PL₀ = 37,15 dB ; L (dB/m) : porte bois 0,23 · **plaque de plâtre 0,32** · mur béton 0,18 · mur porteur 0,22 ; σ = 3,26 dB. Le matériau le plus absorbant est la plaque de plâtre.

## 4. Score et contrainte (§IV)

- Équation (1) : v′_p = v_p (P_TX − max_{o∈O} PL[o, p]) ; équation (3) : v″_p = (v′_p − S_RX) / (P_TX − S_RX) ; équation (4) : F_obj = Σ_{p∈Ω} (α v″_p + β 𝟙_{v″_p > 0}).
- **µ-connexité** : graphe G_O des équipements, arête si E_TX − PL[o_k, o_l] > S_RX, liens unidirectionnels supprimés ; Γ(G_O) = nombre minimal d'arêtes à retirer pour déconnecter ; contrainte Γ ≥ µ.
- Problème (5) : min |O|, max F_obj, sous Γ(G_O) ≥ µ.

## 5. Algorithme (§V.A, algorithme 1) et protocole (§V.B–C)

- **PREP-NSGA** (Chambon et al., MetaCom 2023, référence [7], absente du kit) : population initialisée **à partir des A_i** (« cells of interest »), pas de croisement ; à chaque itération N_Mu mutants (déplacer un équipement dans un cercle de rayon γ, en retirer un, en ajouter un n'importe où sur A) ; les mutants qui violent la contrainte sont rejetés ; tri de Pareto (F_obj, F_cost), on garde les N premiers.
- Tableau II : domaine 16 × 34 × 10 ; ρ = 0,5 m ; E_TX = 20 dBm ; S_RX = −65 dBm ; (α, β) = (1, 1) ; µ ∈ {0, 3} ; N_It = 300 ; N_pop = 40 ; N_Mu = 160 ; γ = 2 m.
- Duplex IFC2x3 open source ; voxels de 50 × 50 × 25 cm.
- **Sans jumeau** : même grille, mais tous les obstacles prennent le matériau le plus absorbant ; on optimise dans cet environnement, puis on **évalue** les solutions dans l'environnement avec jumeau.
- Métriques : couverture = Σ 𝟙_{v″>0} / F_max, F_max = Σ v (voxels libres) ; qualité moyenne de lien en dBm.
- 18 % des obstacles du duplex sont dans le matériau le plus absorbant.

## 6. Ma lecture des points ambigus (à confirmer avec les auteurs)

| # | Point de l'article | Lecture littérale | Lecture retenue | Pourquoi |
|---|---|---|---|---|
| I-1 | Unité de L_obs (dB/m) et équation (2) (somme sur Θ, sans longueur) | dB par mètre traversé, ou une fois par obstacle | **Une fois par voxel obstacle traversé** (option 2) ; « × longueur traversée » (option 1) en sensibilité | L'équation somme L_obs sur les obstacles de Θ sans facteur de longueur ; au §III.A un obstacle est un voxel |
| I-2 | Θ = « set of obstacles » | voxels ou éléments (murs) | Voxels | Cohérent avec §III.A ; un mur traversé en biais compte 2–3 voxels |
| I-3 | Équation (1) : max_{o} PL | équipement le **moins** bon | Meilleur serveur : P_TX − **min** PL | Sens physique de la couverture ; probablement une coquille |
| I-4 | Équation (4) : somme sur tout Ω | un voxel obstacle (v = 0) donne v″ = 65/85 > 0, compté « couvert » | Somme sur les **voxels libres** | Sinon les murs comptent comme couverts |
| I-5 | Qualité moyenne de lien | formule extraite « (P_TX + S_RX) F_obj/F_max − S_RX » (extraction PDF douteuse) | (P_TX − S_RX) · moyenne sur **tous** les voxels libres de max(v″, 0) + S_RX (un voxel non couvert compte pour S_RX) ; la moyenne sur les seuls voxels couverts est fournie en complément | Seule lecture qui rend la courbe croissante comme la figure 4 (a), dont la légende parle de « relative coverage » ; la moyenne sur les voxels couverts baisse entre 1 et 3 équipements |
| I-6 | X_σ | non précisé (tirage par lien ? par évaluation ?) | Tiré **une fois** par couple (équipement, voxel) et par couple d'équipements, graine fixée | Reproductible ; asymétrie des liens (« unidirectional connections are dropped ») |
| I-7 | Initialisation « à partir des A_i » | non détaillée (MetaCom 2023) | Individus formés de « cellules d'intérêt » : centre des positions A de chaque espace, regroupées par niveau | Seule lecture possible sans la référence [7] |
| I-8 | E_TX (contrainte) / P_TX (couverture) | deux symboles | Même valeur, 20 dBm | Tableau II ne donne que E_TX |
| I-9 | Nombre d'équipements | non borné | Borné à 10 (axe des figures 4 et 5) | Concentre la population sur la zone comparée |
| I-10 | Point d'émission | impact du rayon sur le plafond | Centre du voxel libre le plus proche juste sous le voxel du plafond (décalage ≤ 1 voxel au-dessus d'un mur) | L'impact tombe dans un voxel obstacle (faux plafond) : sinon chaque liaison longerait la couche du plafond et les équipements ne se « verraient » plus |

## 7. Décalages de notre reproduction avec l'IWCMC

Ce tableau est complété au fil de l'étape 7 (valeurs chiffrées dans `pareto.json` et `docs/carnet_de_bord.md`).

| # | Élément | IWCMC | Notre reproduction | Effet attendu |
|---|---|---|---|---|
| E-1 | Domaine horizontal | 16 × 34 voxels de 0,5 m | 16 × 34 (emprise des espaces) | identique |
| E-2 | Domaine vertical | 10 couches de 25 cm (= 2,5 m) | 24 couches de 25 cm (0 → 6 m, deux niveaux) | F_max plus grand ; « 10 » incompatible avec un duplex de 6 m |
| E-3 | Part du matériau le plus absorbant | 18 % des obstacles | 47 % des voxels obstacles (catégorie dominante) ; 8 % du volume réel de matière | écart avec / sans jumeau probablement **plus faible** que dans l'article (l'article note que l'écart diminue quand cette part augmente) |
| E-4 | Obstacles | murs, toits, plafonds | murs, dalles, toit, faux plafonds **et portes** (colonne « wooden door » du tableau I) ; fenêtres libres | légère hausse des obstacles |
| E-5 | Voxel obstacle | non précisé | obstacle dès qu'un élément l'occupe (même 1,6 cm de finition) | couches de plancher entièrement obstacles |
| E-6 | Correspondance matériaux | non précisée | table déclarative (plâtre, maçonnerie → mur porteur, béton, bois) ; air, isolant, ossature métal ignorés | voir `choix.md` 6.6 |
| E-7 | Positions autorisées | impacts sur les « roofs » | impacts sur faux plafonds, dalles, toit, au-dessus des espaces occupables : 932 positions | — |
| E-8 | Interprétations I-1 à I-10 | — | ci-dessus | à valider avec les auteurs |
| E-9 | **Couverture avec les valeurs du tableau I** | 1 équipement : 44 % (avec jumeau), 35 % (sans) | **100 % dès 1 équipement**, avec ou sans jumeau, pour les deux lectures de L_obs (voxel ou mètre) | Perte max ≈ 62,5 dB (espace libre, 19 m) + ≤ 10 dB d'obstacles : le signal reste > −65 dBm partout. Le problème devient trivial |
| E-10 | Écart avec / sans jumeau (tableau I) | +4 % de qualité en moyenne, jusqu'à +20 % de couverture | < 0,05 dB et 0 % : aucun gain mesurable | Les L_obs (0,18 à 0,32 dB par obstacle) sont trop faibles pour différencier les matériaux |
| E-11 | µ = 3 sans jumeau (tableau I) | aucune solution à 4 ou 5 équipements | solutions à 4 et 5 équipements (λ = 3) | Tous les équipements s'entendent : graphe complet |
| E-12 | Atténuation qui reproduit les figures | — | **L_obs × 30 par voxel obstacle** (≈ 10 dB par voxel de plâtre, valeur réaliste d'un mur) : couverture 1 équipement 49 % (article 44 %), Q20 = 3 (article 3), écart moyen de couverture à la figure 4 : 0,035 | Hypothèse : l'implémentation d'origine applique L_obs par **échantillon** de raycast (pas de quelques cm) et non par voxel ou par mètre — à confirmer avec les auteurs |
| E-13 | Écart avec / sans jumeau (× 30) | 1 équipement : 44 % / 35 % | 49 % / 49 % ; 2 : 81 % / 78 % ; 3 : 94 % / 89 % | Même sens, écart plus faible : notre part de plâtre (47 % des voxels obstacles) est bien plus haute que leurs 18 % ; l'article note lui-même que l'écart diminue quand cette part augmente |
| E-14 | µ = 3 (× 30) | 94 % dès 4 équipements avec jumeau | 75 % à 4, 84 % à 5 ; l'optimisation « sans jumeau » trouve mieux à 4–5 (82 %, 94 %) | L'algorithme génétique converge mal sous la contrainte µ = 3 (peu de solutions faisables, peine de mort) avec une seule graine : à refaire avec plusieurs graines |

## 8. Résultats chiffrés (graine 0, 300 itérations)

> La campagne complète (12 expériences, 5 graines) et son analyse sont dans **`comparaison.md`**.

| | n = 1 | 2 | 3 | 4 | 5 | 10 |
|---|---|---|---|---|---|---|
| Article, couverture avec / sans jumeau (µ = 0) | 0,44 / 0,35 | 0,775 / 0,67 | 0,905 / 0,825 | 0,95 / 0,92 | 0,985 / 0,965 | 0,998 / 0,988 |
| Tableau I tel quel (pareto.json) | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| L_obs × 30 (iwcmc/pareto_facteur30.json) | 0,49 / 0,49 | 0,81 / 0,78 | 0,94 / 0,89 | 0,995 / 0,996 | 0,998 / 0,998 | 1 / 1 |
| Article, qualité avec jumeau (dBm) | −45,1 | −35,7 | −31,9 | −29,5 | −28,5 | −25,8 |
| Tableau I tel quel | −33,3 | −28,6 | −27,3 | −26,1 | −25,3 | −22,8 |
| L_obs × 30 | −53,8 | −47,2 | −42,2 | −35,3 | −32,4 | −24,7 |

**Q20** (plus petit nombre d'équipements atteignant 90 %, avec jumeau, µ = 0) : **1** avec les valeurs du tableau I (`pareto.json`), **3** avec L_obs × 30 — comme l'article.

Temps CPU (Ryzen 7 7730U) : matrices de perte 932 positions × 8 100 voxels ≈ 5 min (mises en cache) ; PREP-NSGA ≈ 12 s par scénario à µ = 0, ≈ 40 s à µ = 3.
