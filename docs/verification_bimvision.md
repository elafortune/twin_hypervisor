# Vérifications à la main dans BIMvision

Cocher la case quand la valeur lue dans BIMvision est identique à celle de la chaîne. Noter tout écart dans le carnet de bord.

## Espaces (Q01, Q05, Q10, Q12)

Valeur à lire : propriété **GSA BIM Area** (jeu de propriétés « GSA Space Areas »).

| ✓ | Niveau | Nom | Nom long | GSA BIM Area (m²) | GlobalId (fin) |
|---|---|---|---|---|---|
| ☐ | Level 1 | A101 | Foyer | 17.9362 | …dlXrr |
| ☐ | Level 1 | A102 | Living Room | 30.1416 | …dlXr2 |
| ☐ | Level 1 | A103 | Kitchen | 13.8975 | …dlXr$ |
| ☐ | Level 1 | A104 | Bathroom 1 | 3.9978 | …dlXru |
| ☐ | Level 1 | A105 | Stair | 4.9222 | …xa3z |
| ☐ | Level 1 | B101 | Foyer | 17.9362 | …dl_3Q |
| ☐ | Level 1 | B102 | Living Room | 30.1416 | …dl_CZ |
| ☐ | Level 1 | B103 | Kitchen | 13.8975 | …dl_3S |
| ☐ | Level 1 | B104 | Bathroom 1 | 3.9978 | …dl_3P |
| ☐ | Level 1 | B105 | Room | 4.9222 | …xa4o |
| ☐ | Level 2 | A201 | Hallway | 7.8 | …dlXri |
| ☐ | Level 2 | A202 | Bedroom 1 | 26.1193 | …dlXrc |
| ☐ | Level 2 | A203 | Bedroom 2 | 26.178 | …dlXrb |
| ☐ | Level 2 | A204 | Bathroom 2 | 5.4158 | …dlXre |
| ☐ | Level 2 | A205 | Utility | 1.754 | …X3FV |
| ☐ | Level 2 | B201 | Hallway | 7.8 | …dl_3G |
| ☐ | Level 2 | B202 | Bedroom 2 | 26.178 | …dl_39 |
| ☐ | Level 2 | B202 | Bedroom 1 | 26.1193 | …dl_3A |
| ☐ | Level 2 | B204 | Bathroom 2 | 5.4415 | …dl_3C |
| ☐ | Level 2 | B205 | Utility | 1.7284 | …X3FC |
| ☐ | Roof | R301 | Roof | 145.7217 | …s3sW |

- Q01 : 10 espaces sous **Level 2** dans l'arbre.
- Q05 : somme des 10 espaces A = **138,16 m²**.
- Q10 : somme des 10 espaces de Level 2 = **134,53 m²**.
- Q12 : salles de bains de Level 2 = **A204, B204**.

## Portes (Q14)

Valeur à lire : **OverallWidth** (onglet des attributs de l'élément) ou le nom du type (`0762 x 2032mm` = 0,762 m).

| ✓ | GlobalId | Largeur (m) |
|---|---|---|
| ☐ | 1aj$VJZFn2TxepZUBcKp$i | 0.762 |
| ☐ | 1aj$VJZFn2TxepZUBcKpac | 0.762 |
| ☐ | 1hOSvn6df7F8_7GcBWlS8Z | 0.762 |
| ☐ | 1hOSvn6df7F8_7GcBWlS9F | 0.762 |
| ☐ | 1s1jVhK8z0pgKYcr9jt781 / …7AB (portes vitrées) | 0.813 |
| ☐ | 1hOSvn6df7F8_7GcBWlRGQ / …RH8 (entrées) | 1.25 |
| ☐ | 6 autres portes intérieures | 0.864 |

Q14 : portes de moins de 0,80 m = les **4 portes de 0,762 m**.

## Anomalies à constater visuellement

| ✓ | Quoi regarder |
|---|---|
| ☐ | Deux espaces `B202` dans l'arbre sous Level 2 |
| ☐ | Propriétés de B202 « Bedroom 2 » : `Number` = **B203** (jeu « PSet_Revit_Identity Data ») |
| ☐ | B105 nommé « Room », catégorie OmniClass « Stairway » |
| ☐ | Dans l'arbre, un escalier rangé sous **Roof** |
| ☐ | Propriétés d'une porte : `IsFireExit` = « IsFireExit » |
