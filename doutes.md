# Doutes de l'assistant

> Les endroits où je ne suis **pas sûr** de mon raisonnement ou de mon interprétation, pour que tu puisses vérifier à la main ou trancher. Une ligne par doute : ce que j'ai fait, pourquoi j'hésite, comment vérifier.
>
> **Confiance** : 🔴 faible (vérifier en priorité) · 🟠 moyenne · 🟢 assez sûr mais non prouvé.
> **Statut** : ☐ ouvert · ☑ levé (avec qui/quoi l'a levé).

## Interprétation des questions

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| Q-1 | 🔴 | **Q01** : les cages d'escalier A105/B105 (double hauteur 0–5,7 m) sont-elles « au niveau Level 2 » ? | Non : rattachées à Level 1 dans l'IFC → Q01 = 10 espaces | Décision de ta part ; à défendre devant le jury dans les deux sens | ☑ 10/11 : les deux cages ont leur base à z = 0,02 m (Level 1) et contiennent chacune la volée de leur logement ; B105 n'est pas au-dessus de A105 (6,9 m d'écart en x) → Level 1, Q01 = 10 |
| Q-2 | 🟠 | **Q06** « une seule porte » : une ouverture libre ou un escalier compte-t-il comme accès ? | Seules les `IfcDoor` comptent | Relire l'énoncé ; au Level 2 aucun espace n'a d'ouverture libre, donc sans effet ici | ☐ |
| Q-3 | 🟠 | **Q07** : « portes franchies » inclut-il la porte d'entrée elle-même ? | Oui (0,864 m de la chambre < 1,25 m de l'entrée : sans effet sur le résultat) | Sans effet ici ; à préciser si la question change | ☐ |
| Q-4 | 🟠 | **Q07/Q08** : itinéraire choisi = somme des distances « pire point » (Pang). Un autre critère (moins de portes, distance porte à porte) pourrait choisir un autre chemin | Dans le duplex il n'existe qu'un chemin possible, donc sans effet | Vérifier sur le gros IFC de l'entretien | ☐ |
| Q-5 | 🟠 | **Q09** « liaison verticale » : cages (A105, B105) ou aussi les espaces d'arrivée (A201, B201) ? | Espaces qui **contiennent** l'escalier (`bot:containsElement`) → A105, B105 | Ton avis | ☐ |
| Q-6 | 🟠 | **Q11** « pour chaque logement » : un logement = composante connexe contenant une sortie ; ici = préfixe A/B | A102, B102 (séjours, 30,14 m²) | Recoupé avec le préfixe ; peut différer sur un immeuble à hall commun | ☐ |
| Q-7 | 🟠 | **Q12** salles de bains : repérées par le nom long (`bath`, `salle de bain`, `wc`…). La catégorie OmniClass serait plus robuste | A204, B204 | Vérifier si « Utility » (A205/B205) contient une salle d'eau dans BIMvision | ☐ |
| Q-8 | 🔴 | **Q13** vide : question piège ou erreur de ma connectivité ? | ∅ ; test qui prouve que la requête trouverait un passage s'il existait | Regarder dans BIMvision le mur mitoyen A/B (porte ? ouverture ?) | ☑ 10/11 : les 4 murs « Party Wall – Residential Unit Dimising Wall » n'ont aucune ouverture ; aucune limite IFC ni porte entre A et B ; les couloirs A201/B201 sont à 4 m l'un de l'autre → ∅ confirmé |
| Q-9 | 🟢 | **Q05** inclut la cage A105 (escalier) dans la surface du logement A | 138,16 m² | ☑ vérifié dans BIMvision (somme GSA BIM Area) | ☑ |

## Maquette et extraction (étapes 1–2)

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| M-1 | 🟠 | Liste des incohérences **volontairement ajoutées** : j'en ai trouvé ~12, mais d'autres peuvent m'échapper (la porte orpheline m'avait échappé jusqu'à ta vérification) | Règles génériques | Continuer les contrôles manuels BIMvision ; chercher dans les propriétés des portes et murs | ☐ |
| M-2 | 🟠 | Chevauchement de 0,15 m² entre les cages et les chambres : anomalie ajoutée ou simple imprécision de modélisation Revit ? | Signalé comme anomalie | Mesurer dans BIMvision | ☐ |
| M-3 | 🟠 | Limites virtuelles de A201/B201 décalées de 6–10 m : modification volontaire ou export Revit d'espaces à placement non nul ? | Signalé, contact géométrique utilisé | Comparer le placement de A201 avec un autre espace dans BIMvision | ☐ |
| M-4 | 🟢 | Écart de 7–23 % entre surface géométrique et GSA BIM Area : convention de mesure (axe des murs ?) | Pas une anomalie | Mesurer une pièce dans BIMvision | ☐ |
| M-5 | 🟠 | Sorties : A102/B102 (portes vitrées sur jardin) sont-elles de vraies sorties d'évacuation ? | Oui (géométrie + `IsExternal`) | Ton avis / usage réglementaire | ☐ |

## Distances (étape 3)

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| D-1 | 🟠 | Cible d'une ouverture libre = milieu du segment de contact | Choix validé, limite connue (surestime dans un grand séjour) | — | ☑ validé |
| D-2 | 🟠 | Escalier : distance = jusqu'au pied (montée) / à la tête (descente) + longueur de volée. Pang ne détaille pas le cas | 4,85 m ajoutés | Relire [Pang] §4.1.3 | ☐ |

## Graphe de connaissances (étape 4)

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| G-1 | 🟠 | Les classes `s4bldg:Door` et `s4bldg:Stair` existent-elles exactement sous ces noms dans SAREF4BLDG ? | Alignement par `rdfs:subClassOf` | Vérifier sur https://saref.etsi.org/saref4bldg/ | ☐ |
| G-2 | 🔴 | **Formes cachées** : le jury peut exiger ce que l'exemple du kit ne montre pas (ex. `ssi:statusTime`, `ssi:peopleCount` sur chaque espace, `isConnectedTo` dans un seul sens…) | État initial `Normal` sur tous les espaces, symétrie écrite dans les deux sens | Impossible à vérifier ; à justifier par la modélisation | ☐ |
| G-3 | 🟠 | Écrire `hasStatus Normal` dès le graphe statique (avant toute observation) | Oui : état initial de Pang | Ton avis | ☐ |
| G-4 | 🟠 | Logement relié aux espaces par `ssi:inDwelling` et non `bot:hasSpace` (qui serait le patron BOT) | F1 interdit un second « parent » `bot:hasSpace` | Choix assumé, à expliquer | ☐ |
| G-5 | 🟠 | Les « ouvertures libres » n'ont pas de nœud propre (pas de GlobalId) : Q13 ne pourrait renvoyer qu'un identifiant fabriqué | Identifiant `ouverture:<espace>|<espace>` | Utiliser le GlobalId de la limite virtuelle IFC ? | ☐ |
| G-6 | 🟢 | F3–F6 différées tant que M4 n'a pas tourné (le graphe statique les viole forcément) | Différées automatiquement si `devices.json` est « non calculé » | — | ☐ |
| G-7 | 🟠 | Anomalies M1 écrites dans le graphe (`ssi:ModelAnomaly`) : utile pour l'agent, mais alourdit et pourrait gêner une forme cachée | Incluses | Ton avis | ☐ |

## Évacuation dynamique (étape 5)

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| V-1 | 🟠 | **Q18** : « plus aucune route sûre » commence-t-il quand la route est coupée (A101 dangereux, 180 s) ou quand la chambre elle-même devient dangereuse (460 s) ? | 180 s : route coupée | Ton avis ; avec la pénalité de Pang il y aurait toujours une route | ☑ 10/11 : 180 s, l'accent est mis sur les routes vers les sorties |
| V-2 | 🟠 | **Q16** : état verrouillé ou instantané ? Ici identique (valeurs jamais redescendues sous les seuils) | Verrouillé | Sans effet sur ce scénario | ☐ |
| V-3 | 🟠 | **Q19** : seuls les espaces avec caméra ont un comptage ; un espace sans caméra pourrait abriter des personnes | A202, A203 (comptages caméra) | Énoncé : « les comptages font foi » | ☑ 10/11 : **risque de sécurité à présenter** ; chaque ligne du JSONL liste les espaces dangereux sans caméra (6 à t = 600 s : A101, A103, A104, A105, A201, A204) |
| V-4 | 🟠 | **Q17** : « à l'instant de l'alarme » = 70 s (premier dépassement de 0,0328 /m, dans A103) | Route calculée avec l'état à 70 s (aucun espace dangereux) | — | ☐ |
| V-5 | 🟢 | Les comptages tombent à 0 (A102 à 130 s, B à 130–220 s) sans que la chaîne déplace les personnes : je suppose qu'elles sont sorties | Les comptages font foi | — | ☐ |
| V-6 | 🟠 | Stratégie 1 sans détour réactif (Pang, tableau 7, fait se détourner les occupants) | Route statique pure | Relire [Pang] §5.3 | ☑ 10/11 : variante « détour réactif » ajoutée pour comparaison |
| V-7 | 🟢 | Le capteur `CAM_B203` observe l'espace B202 « Bedroom 2 » : nouvel indice du renommage B203 → B202 | Noté | — | ☐ |

## Voxels (étape 6)

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| X-1 | 🔴 | **Part de plaque de plâtre** : 47 % des voxels obstacles (catégorie dominante) contre **18 %** annoncés par l'IWCMC ; en volume réel de matière, 8 %. Les 18 % ne se retrouvent avec aucune méthode simple | Les deux mesures sont calculées et expliquées | Question au jury : comment l'IWCMC a-t-il compté (volume, voxels, éléments) ? | ☐ |
| X-2 | 🟠 | Un élément mince (finition de sol 1,6 cm, faux plafond 5,7 cm) rend obstacle toute une couche de 25 cm : la couche 0–0,25 m est entièrement « obstacle » | Occupation > 0 = obstacle | Seuil d'occupation ? Rendrait les cloisons discontinues | ☐ |
| X-3 | 🟠 | Domaine vertical : l'IWCMC annonce 10 couches de 25 cm (2,5 m), insuffisant pour un duplex de 6 m | 24 couches (0 → 6 m) | Relire l'article / demander | ☐ |
| X-4 | 🟠 | Fenêtres considérées comme libres (non listées par l'IWCMC) | Exclues des obstacles | Le verre atténue peu à 2,4 GHz, mais pas zéro | ☐ |
| X-5 | 🟢 | 3 positions A à 2,795 m au Level 1 (dalle sans faux plafond au-dessus) | Gardées | Vérifier dans la vue voxels | ☐ |

## Reproduction IWCMC (étape 7)

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| R-1 | 🔴 | **Q20** : avec les valeurs du tableau I (`pareto.json`), Q20 = **1** (100 % dès un équipement) ; avec L × 30, Q20 = 3 comme l'article. Laquelle donner ? | `pareto.json` (et donc Q20) suit le tableau I tel quel, comme décidé | Ton choix ; à expliquer au jury dans les deux cas | ☐ |
| R-2 | 🔴 | Facteur 30 : explication par un L_obs appliqué à chaque échantillon de raycast (hypothèse, non prouvée) | Présenté comme hypothèse | Question aux auteurs | ☐ |
| R-3 | 🟠 | µ = 3 : l'optimisation « avec jumeau » fait moins bien que « sans jumeau » à 4–5 équipements (× 30) : convergence insuffisante | Signalé (E-14) | Relancer avec 5 graines / plus d'itérations | ☐ |
| R-4 | 🟠 | Initialisation par « cellules d'intérêt » (référence [7] absente du kit) | Une cellule par espace (centre des positions A) | Lire MetaCom 2023 si accessible | ☐ |
| R-5 | 🟢 | Relevé des figures 4 et 5 à l'œil (±0,005 ; ±0,2 dBm) | Valeurs dans `m3_iwcmc/article.py` | — | ☐ |

## Énoncé

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| E-1 | 🟠 | `pareto.json` : liste de 4 scénarios ou un seul objet ? | Liste, chaque élément validé | Demander au jury / relire l'énoncé | ☐ |
