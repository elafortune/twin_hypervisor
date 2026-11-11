# Étape 10 – Généricité : la chaîne sur un second IFC

Le kit demande (`plan_execution.md`, étape 10) de faire tourner la chaîne **sans modifier le code** sur un autre bâtiment de la série des *Common Building Information Model Files* (NIBS / buildingSMART alliance), « par exemple un bâtiment de bureaux », avec un petit fichier d'observations synthétique, en un temps compatible avec les **10 minutes** de l'entretien.

## Le bâtiment

| | Duplex (kit) | Bureaux NIBS |
|---|---|---|
| Fichier | `duplex_TwinHypervisor.ifc` | `data/bureaux/Office_A_20110811.ifc` (IFC2x3, Revit 2011, 4,1 Mo) |
| Niveaux | 2 (+ fondation, toit) | 2 (+ toit) |
| Espaces / occupables | 21 / 20 | 99 / 98 |
| Portes / sorties | 14 / 4 | 102 / 6 |
| Escaliers | 2 (cages sur deux niveaux) | 2 (cages découpées par niveau : S101–S201, S102–S202) |
| Voxels / positions au plafond | 0,5 m · 932 positions | 1 m (mode rapide) · 3 297 positions |

Source : le portail NIBS d'origine ne répond plus, et la copie de la page WBDG sur la Wayback Machine bloque les téléchargements automatiques. Le même fichier (`Office_A_20110811.ifc`, celui de la série « Common BIM Files ») est repris tel quel du dépôt public `ThatOpen/engine_web-ifc` (`tests/ifcfiles/public/`) ; SHA-256 `3ccc7df480d7ae9d1af148d13634fe1af8f1a75949fdf3cb1f87c60464df4700`.

## Ce qui est propre au bâtiment (fichiers, pas code)

| Fichier | Contenu |
|---|---|
| `data/bureaux/parametres_bureaux.json` | paramètres du kit, sauf : origine du feu (salle de pause 125) et **mode rapide** : grille de 1 m, M3 sur 60 positions et 100 itérations sans la variante ×30, `kg.ttl` validé une seule fois en fin de chaîne |
| `data/bureaux/observations_bureaux.csv` | scénario synthétique (`python -m twinhyp scenario --geometrie … --origine 125 …`) : front de feu propagé sur le graphe de connectivité, retard de 50 s et atténuation × 0,65 par liaison, profils calés sur ceux du kit ; 6 espaces occupés (graine 0) |
| `data/bureaux/questions_bureaux.json`, `demandes_bureaux.json` | les 20 questions et 4 demandes du kit, avec les noms du bâtiment (couloir 121, salle de pause 231, bureau OPS SGT, espace 221…) |

## Ce que le second IFC a révélé (corrigé, générique, duplex inchangé)

Le critère « sans modifier le code » n'a pas tenu au premier essai : le bâtiment de bureaux contient des cas absents du duplex. Chaque correction est une règle générale, testée, et le `geometry.json` du duplex est **identique** avant et après (comparaison champ par champ).

| # | Symptôme sur les bureaux | Cause | Correction |
|---|---|---|---|
| G-1 | M2 refuse le graphe : « espace occupable sans chemin vers une sortie » (124 ELEV) | gaine d'ascenseur sans porte ni ouverture | M1 : un espace **sans aucune liaison** est requalifié non occupable (anomalie `espace_isole`) ; un espace relié mais sans sortie reste bloquant |
| G-2 | 15 « sorties », dont 4 au Level 2 dans des sanitaires | portes de cabines de toilettes (centre à 0,76 m, au milieu du sanitaire) : une seule pièce de chaque côté → lues comme sorties | M1 : une porte au milieu de son unique espace (> 0,40 m du contour) n'est ni une liaison ni une sortie (anomalie `porte_interieure_espace`) → 6 vraies sorties |
| G-3 | F3 violée : local technique 219 sans détecteur | aucun plafond modélisé au-dessus (local ouvert) → aucune position candidate | M1 : repli sur le sommet de l'espace, **seulement** pour un espace sans aucune position |
| G-4 | Q09 (liaisons verticales) vide | cages découpées par niveau : aucun espace ne contient la volée | requête : à défaut de cage, espaces reliés par l'escalier |
| G-5 | « sanitaires du Level 2 » vide | « MENS RR » (*restroom*) | synonymes `restroom`, `rr`, `lavatory` ; types `bureau`, `salle_de_reunion`, `local_technique` |
| G-6 | M6 s'arrête au démarrage | la référence sans LLM porte les noms du duplex | référence facultative : sur un autre bâtiment, réponses non contrôlées (signalé dans `agent_resume.json`) |
| G-7 | demandes > 25 min | une validation SHACL = 42 s sur 136 000 triplets ; D4 en faisait 2 par espace (39 espaces) | D4 valide toutes les routes candidates **en une passe** (violations attribuées par nœud fautif) : 8 validations au lieu de ~80 |

## Résultats

| Module | Bureaux NIBS |
|---|---|
| M1 | 99 espaces, 98 occupables, 100 liaisons, 6 sorties, 47 anomalies (9 portes de cabines, 16 fonctions incohérentes, `IsFireExit` textuel comme dans le duplex…) |
| M2 | graphe conforme (F1, F2, F7, F8 + formes maison) |
| M3 | 4 fronts de Pareto (avec / sans jumeau, µ = 0 / 3) ; part de plaque de plâtre 65 % |
| M4 | 149 détecteurs, 6 déclencheurs (un par sortie), 75 caméras (100 % des chemins, full-view 62 %), réseau connexe (λ = 206), tous les MILP optimaux |
| M5 | alarme à 60 s, 510 lignes, routes conformes à F8 |
| M6, partie symbolique (LLM scripté) | les 20 outils répondent ; D1 acceptée, D2 acceptée (le couloir 201 reste couvert), D3 acceptée avec adaptation (détecteurs de chaleur temporaires), D4 acceptée pour les 39 espaces du Level 2 (escaliers encore sûrs à 200 s) ; 8 validations, 345 s |
| M6 avec le LLM | **non mesuré** : run arrêté par manque de mémoire pendant le chargement du modèle (voir doute A-6) |

## Temps (CPU Ryzen 7 7730U, 15,4 Go)

| Étape | Premier essai (paramètres du kit + origine du feu) | Mode rapide final |
|---|---|---|
| M1 | 48 s (grille 0,5 m, 12 845 positions) | 29 s (grille 1 m) |
| M2 | 1 s | 1 s |
| M3 | 412 s (150 positions) | 128 s (40 positions, sans variante ×30) |
| M4 | 155 s (caméras : 116 s) | 165 s |
| M5 | 100 s | 93 s |
| Validations de `kg.ttl` | après M2, M4, M5 : ≈ 196 s | une seule, en fin de chaîne : 130 s |
| **M1 → M5** | **655 s (10 min 55)** | **≈ 554 s (9 min 15)** (mesuré : 613 s avec 60 positions ; M3 à 40 positions mesuré seul) |
| M6 (estimation) | — | ~20 min avec qwen2.5:14b sur CPU |

Pour l'entretien : M1 → M5 en direct tient dans les 10 minutes en mode rapide ; M6 sur CPU ne tient pas (doute A-6) : le lancer en parallèle de la présentation, ou montrer les outils et le veto symbolique avec le LLM scripté (≈ 6 min).

## Limites

- Questions et demandes rédigées par moi : pas de réponses de référence du jury ; vérification par les outils (LLM scripté) et à la main sur quelques cas (Q03 : 6 espaces à sortie directe ; Q12 : sanitaires 207, 209 ; Q14 : aucune porte < 0,80 m).
- Scénario synthétique : ce n'est pas un modèle de feu.
- M3 en mode rapide (60 positions) : Q20 n'est pas comparable à l'article.
- M6 avec le LLM sur ce bâtiment : à mesurer quand la mémoire le permet (~20 min attendues : 20 questions à ~30 s, 8 appels pour les demandes, 345 s de validations).
