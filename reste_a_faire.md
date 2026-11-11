# Reste à faire avant l'envoi au jury

Échéance : **jeudi 12 novembre 2026, 16 h 00** (objectif : envoi le mercredi 11 au soir).
Livrables (`docs/feuille_de_route.md`) : dépôt Git avec historique et tests · une commande unique · 8 sorties conformes · rapport de 6 pages maximum · carnet de bord et déclaration IA.

## 1. Run final sur le duplex et sorties dans le dépôt — bloquant

- [x] M1 → M5 avec le code final (4 min 20)
- [x] M6 avec qwen2.5:14b (≈ 25 min, ≈ 9 Go de RAM : **fermer Chrome**)
- [x] `python -m twinhyp valider --out sorties` → 8 × OK
- [x] Commiter `sorties/` : les 8 sorties, `llm_journal.jsonl` (rejeu), `agent_resume.json`, `execution.json`, figures ; **sans** les caches `.npz` de M3 (57 Mo, régénérés)

## 2. Rapport (6 pages maximum) — obligatoire

- [x] `rapport.md` : architecture ; écarts à l'IWCMC (figures, hypothèses) ; incohérences de la maquette ; comparaison à l'ontologie de Pang ; pénalité ou contrainte dure ; décisions de l'agent ; matériel et temps
- [ ] Relecture (toi)
- [x] Export PDF éventuel (`*.pdf` est dans `.gitignore` : `git add -f rapport.pdf`)

## 3. Déclaration IA — obligatoire

- [x] `declaration_ia.md` : outils utilisés et pour quoi ; ce qui a été vérifié à la main (`docs/verification_bimvision.md`, validation à chaque étape) ; agent M6 sur LLM local ; renvoi vers `docs/prompt.md`
- [ ] Relecture (toi)

## 4. Décisions — tranchées le 12/11 : choix par défaut gardés

| Sujet | Options | Défaut actuel |
|---|---|---|
| Q20 | 1 (tableau I tel quel) · 3 (atténuation ×30, figure 4 reproduite) | 1 |
| Caméras | 18 (minimum ; full-view min. 0 %) · 20 (min. 62,5 %) | 18 |
| D3 : citer la classe A1R dans la justification | oui (relancer M6) · non (documenté dans `fumee_chaleur.md`) | non |
| `docs/architecture.md`, `docs/architecture_schema.html` (commités par erreur) | garder · retirer | gardés |

## 5. Nettoyage — rapide

- [x] Tableau « Points ouverts » de `choix.md` (périmé)
- [ ] Relire `main.md` et le README
- [x] Test depuis un clone neuf : 99 tests rapides OK (environnement conda non recréé, commande complète non relancée depuis le clone)

## 6. Envoi (toi)

- [ ] Accès au dépôt `elafortune/twin_hypervisor` (privé) : ajouter le jury comme collaborateur, ou rendre public (les articles et les PDF sont exclus)
- [ ] Mail à abderrezak.rachedi@univ-eiffel.fr, objet « Exercice CIFRE TwinHypervisor », lien du dépôt et du rapport

## 7. Préparation de l'entretien, sans IA (jeudi soir)

- [ ] Chaîne sur les bureaux, chronomètre en main (`generalite.md`, ≈ 9 min 15 pour M1 → M5)
- [ ] Au tableau : *set cover* des détecteurs, MILP des caméras, PREP-NSGA ; contrainte dure F8 contre pénalité
- [ ] Prédire l'effet d'un paramètre (S_RX, µ, rayon de détection, seuil de température, `minCameraCoverage`)
- [ ] Deux petites modifications de code en 10 min (une règle d'anomalie, un outil de l'agent)

## Facultatif

- M6 avec le LLM sur les bureaux (≈ 20 min)
- Banc d'essai qwen3:4b et mistral (modèle plus rapide pour l'entretien)
