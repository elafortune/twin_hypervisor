# Détecteurs de fumée ou de chaleur : comparaison sur toute la chaîne

Le kit laisse le type de détecteur automatique libre (`theorie/M4` §1 : « détecteurs automatiques (fumée ou chaleur) » ; l'ontologie et `devices.schema.json` acceptent `SmokeDetector` et `HeatDetector` ; `theorie/M6` propose pour D3 une « détection temporaire (chaleur, autonome) »). Ce document compare les deux choix **étape par étape**, en rejouant la chaîne.

## Protocole

| Variante | Fichier de paramètres | Ce qui change |
|---|---|---|
| fumée (référence) | `data/parametres.json` (kit) | — |
| chaleur A1R | `data/variantes/parametres_chaleur.json` | `detecteur_type = HeatDetector` ; alarme : +10 °C en 60 s ou ≥ 65 °C |
| chaleur A1 | `data/variantes/parametres_chaleur_A1.json` | idem, statique seule (≥ 65 °C) |
| chaleur A1R, rayon 3,54 m | `data/variantes/parametres_chaleur_rayon.json` | idem A1R, surface surveillée par détecteur divisée par 2 |

- Seuls les paramètres changent, pas le code : `detecteur_type` (M4 : type posé ; M5 : condition d'alarme), `detecteur_chaleur_classe` (A1R par défaut), `detecteur_chaleur_rayon_m` (défaut : `detecteur_rayon_m`).
- Hypothèse : le signal d'un espace dans `observations.csv` est celui que verrait un détecteur placé dans cet espace (pas de modèle de transport de fumée).
- Classes EN 54-5 : A1 = réponse statique entre 54 et 65 °C (on prend 65 °C, borne prudente) ; A1R = A1 + thermovélocimétrique, approchée par +10 °C en 60 s (approximation : la norme fixe des temps de réponse par rampe).
- M1 et M3 sont repris tels quels (indépendants du type de détecteur) ; M2, M4, M5 recalculés ; M6 rejoué à partir du journal du LLM du run fumée (mêmes prompts → mêmes réponses, sans Ollama). Le run réel de M6 sur la variante A1R a répondu aux 20 questions (20 / 20 conformes) avant d'être arrêté par manque de mémoire pendant les demandes.
- Commandes : `python -m twinhyp run … --params data/variantes/parametres_chaleur.json --out sorties_chaleur`, puis `python -m twinhyp comparer sorties sorties_chaleur sorties_chaleur_A1 sorties_chaleur_rayon` ; délais par espace : `python -m twinhyp detecteurs --out sorties`.

## Résultats par étape

| Étape | Indicateur | Fumée | Chaleur A1R | Chaleur A1 | A1R, rayon 3,54 m |
|---|---|---|---|---|---|
| M4 | détecteurs (MILP optimal) | 20 | 20 | 20 | 24 (Level 1 : 14, Level 2 : 10) |
| M4 | équipements au total | 42 | 42 | 42 | 46 |
| M4 | `kg.ttl` conforme F1–F8 | oui | oui | oui | oui |
| M5 | instant de l'alarme | **70 s** | 80 s | **130 s** | 80 s |
| M5 | délai entre l'alarme et la première perte de route sûre (A202, A203 à 180 s) | **110 s** | 100 s | **50 s** | 100 s |
| M5 | occupants présents avant l'alarme (somme personnes × pas de 10 s) | 77 | 88 | 143 | 88 |
| M5 | routes nulles (stratégie 2) | 86 | 86 | 86 | 86 |
| M6 | réponses de référence Q01–Q20 | — | identiques | identiques | identiques |
| M6 | D1 cuisine en chaleur | acceptée (1 détecteur changé) | acceptée, **rien à changer** | idem | idem |
| M6 | D2 | refusée (F3) | refusée (F3) | refusée (F3) | refusée (F3) |
| M6 | D3 retirer les détecteurs du Level 2 | acceptée avec adaptation (10 détecteurs de chaleur temporaires) | **refusée** : détecteurs déjà de chaleur, insensibles aux poussières, maintenus | idem | idem |
| M6 | D4 (5 espaces) | refusée (F8), mise à l'abri | idem | idem | idem |

Par espace (`detecteurs`) : la fumée alarme 10 à 60 s avant la chaleur A1R et 40 à 150 s avant la chaleur statique ; un détecteur statique alarme à peu près quand l'espace devient dangereux (A103 : alarme A1 à 130 s, danger à 120 s).

## Lecture

- **M4** : à rayon égal, le type ne change rien au placement (même MILP). Si l'on applique une surface surveillée plus petite au détecteur de chaleur, il en faut 20 % de plus (24), et 70 % de plus à 2,74 m (34).
- **M5** : c'est là que se joue la différence. Les routes ne changent pas (aucun espace n'est dangereux avant 120 s), mais l'alarme arrive 10 s (A1R) ou 60 s (A1) plus tard. Avec A1, l'alarme sonne **après** que la cuisine est devenue dangereuse, et il ne reste que 50 s avant que les chambres A202 et A203 perdent toute route sûre (contre 110 s avec la fumée).
- **Q15–Q19** ne changent pas : Q15 porte sur l'obscurcissement mesuré (pas sur le détecteur posé) et la route de Q17 est la même à 70, 80 ou 130 s.
- **M6** : les règles de demandes sont génériques vis-à-vis du type. La comparaison a révélé deux défauts, corrigés : D1 comptait un triplet ajouté alors que le détecteur était déjà de chaleur ; D3 proposait de remplacer des détecteurs « de fumée » qui étaient déjà de chaleur (90 triplets retirés puis remis).

## Conclusion

- **Fumée par défaut dans M4** : alarme la plus précoce (70 s), plus grande marge avant la perte des routes sûres (110 s), moins de détecteurs si la surface surveillée est plus grande.
- **Chaleur seulement là où la fumée gêne** (D1 : cuisine ; D3 : travaux), en classe **A1R** : le coût est de 10 s sur ce scénario. La classe A1 seule est à éviter : l'alarme vient après le danger.

## Limites

- Signal par espace sans transport de fumée ni hauteur de plafond ; seuils A1/A1R simplifiés.
- Rayon des détecteurs de chaleur : ordre de grandeur, à vérifier dans NF S 61-970 / CEN/TS 54-14.
- Les justifications de D1 et D3 des variantes sont les textes de secours (leurs prompts n'existent pas dans le journal rejoué) ; les décisions, elles, sont calculées.
