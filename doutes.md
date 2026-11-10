# Doutes de l'assistant

> Les endroits où je ne suis **pas sûr** de mon raisonnement ou de mon interprétation, pour que tu puisses vérifier à la main ou trancher. Une ligne par doute : ce que j'ai fait, pourquoi j'hésite, comment vérifier.
>
> **Confiance** : 🔴 faible (vérifier en priorité) · 🟠 moyenne · 🟢 assez sûr mais non prouvé.
> **Statut** : ☐ ouvert · ☑ levé (avec qui/quoi l'a levé).

## Interprétation des questions

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| Q-1 | 🔴 | **Q01** : les cages d'escalier A105/B105 (double hauteur 0–5,7 m) sont-elles « au niveau Level 2 » ? | Non : rattachées à Level 1 dans l'IFC → Q01 = 10 espaces | Décision de ta part ; à défendre devant le jury dans les deux sens | ☐ |
| Q-2 | 🟠 | **Q06** « une seule porte » : une ouverture libre ou un escalier compte-t-il comme accès ? | Seules les `IfcDoor` comptent | Relire l'énoncé ; au Level 2 aucun espace n'a d'ouverture libre, donc sans effet ici | ☐ |
| Q-3 | 🟠 | **Q07** : « portes franchies » inclut-il la porte d'entrée elle-même ? | Oui (0,864 m de la chambre < 1,25 m de l'entrée : sans effet sur le résultat) | Sans effet ici ; à préciser si la question change | ☐ |
| Q-4 | 🟠 | **Q07/Q08** : itinéraire choisi = somme des distances « pire point » (Pang). Un autre critère (moins de portes, distance porte à porte) pourrait choisir un autre chemin | Dans le duplex il n'existe qu'un chemin possible, donc sans effet | Vérifier sur le gros IFC de l'entretien | ☐ |
| Q-5 | 🟠 | **Q09** « liaison verticale » : cages (A105, B105) ou aussi les espaces d'arrivée (A201, B201) ? | Espaces qui **contiennent** l'escalier (`bot:containsElement`) → A105, B105 | Ton avis | ☐ |
| Q-6 | 🟠 | **Q11** « pour chaque logement » : un logement = composante connexe contenant une sortie ; ici = préfixe A/B | A102, B102 (séjours, 30,14 m²) | Recoupé avec le préfixe ; peut différer sur un immeuble à hall commun | ☐ |
| Q-7 | 🟠 | **Q12** salles de bains : repérées par le nom long (`bath`, `salle de bain`, `wc`…). La catégorie OmniClass serait plus robuste | A204, B204 | Vérifier si « Utility » (A205/B205) contient une salle d'eau dans BIMvision | ☐ |
| Q-8 | 🔴 | **Q13** vide : question piège ou erreur de ma connectivité ? | ∅ ; test qui prouve que la requête trouverait un passage s'il existait | Regarder dans BIMvision le mur mitoyen A/B (porte ? ouverture ?) | ☐ |
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

## Énoncé

| # | Conf. | Doute | Ce que j'ai fait | Comment lever le doute | Statut |
|---|---|---|---|---|---|
| E-1 | 🟠 | `pareto.json` : liste de 4 scénarios ou un seul objet ? | Liste, chaque élément validé | Demander au jury / relire l'énoncé | ☐ |
