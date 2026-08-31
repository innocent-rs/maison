# Atelier MOB

Modèle paramétrique d'un atelier rectangulaire en ossature bois. Le projet
n'est plus une maison en A : sa géométrie de plancher est désormais
indépendante de la forme future des murs et de la toiture.

## Hypothèse d'emprise

L'état initial adopte une longueur ronde de `15 m` : `7 000 × 15 000 mm`, soit
`105 m²`. La largeur et la longueur peuvent être modifiées :

```python
from atelier_mob import creer_atelier_mob

atelier = creer_atelier_mob(
    largeur_interieure=7_000,
    longueur_interieure=15_000,
)
```

## Plancher de référence

Le modèle courant comprend, de bas en haut :

- des fonds de caisson en OSB 3 à bords droits de `12 mm`, posés sur les
  membrures basses et sur des tasseaux de rive ;
- des panneaux semi-rigides en fibre de bois Isonat Flex 55 de `145 mm`
  (`R = 4,00 m²·K/W` déclaré pour cette épaisseur) ;
- des solives en I STEICOjoist `SJ60/240`, réparties à environ `564 mm`
  d'entraxe ;
- un plancher porteur en OSB 3 rainuré-languetté de `22 mm`.

Les deux poutres longitudinales et les huit traverses primaires sont des
éléments de `120 × 240 mm`. Les solives en I sont découpées en sept travées de
`1 999 mm` environ. Le calepinage à huit traverses maintient les joints des
dalles supérieures de `2 500 mm` sur des appuis.

Les poutres longitudinales de `15 000 mm` restent représentées continues
pour lire le chemin des charges. Leur débit transportable, leurs aboutages au
droit des appuis et la disponibilité commerciale ne sont pas encore résolus.

L'OSB inférieur est pour l'instant une hypothèse géométrique utile pour fermer
et contreventer les caissons. Avant exécution, la composition doit faire
l'objet d'une vérification hygrothermique : un atelier chauffé demande une
bonne continuité d'étanchéité à l'air côté chaud et une sous-face suffisamment
ouverte à la diffusion et protégée du vent, de l'eau et des rongeurs.

## Fondations et chemin des charges

Par défaut, trois platines de pieux sont placées sous chacune des huit
traverses : une sous chaque poutre de rive et une sous l'axe central, soit
`24` appuis. Chaque demi-traverse a ainsi une portée géométrique d'environ
`3 380 mm`. Les fûts et parties enterrées des pieux ne sont pas représentés.

Une implantation explicite reste possible ; passer `positions_platines=()`
désactive entièrement la trame automatique.

```python
atelier = creer_atelier_mob(
    positions_platines=((60, -3_440), (60, 0), (60, 3_440)),
)
```

## Statut du dimensionnement

Il s'agit d'un avant-projet paramétrique, pas d'un plan d'exécution. Les
charges réelles d'atelier (machines, stockage, cloisons), les murs, les
assemblages, le diaphragme, les vibrations, le feu, le fluage, le vent, le
soulèvement et la capacité du sol et des pieux doivent encore être vérifiés.
Les abaques STEICO doivent notamment être relus avec la catégorie d'usage et
les charges permanentes du projet.

À titre de contrôle de cohérence seulement, une demi-traverse modélisée comme
une poutre `120 × 240 mm` simplement appuyée sur `3 380 mm`, avec
`G = 0,60 kN/m²`, `Q = 2,50 kN/m²`, une largeur tributaire de `2,13 m` et les
modules exploratoires `E = 11 000 MPa`, `G = 690 MPa`, donne une flèche
instantanée `G + Q` d'environ `8,1 mm`, soit `L/417`. Ce calcul conservateur ne
vérifie ni la résistance de calcul Eurocode 5, ni les charges ponctuelles, ni
le fluage, ni l'appui central réel, ni le mur porté.

Documents produit de référence :

- [guide technique STEICOconstruction](https://www.steico.com/fileadmin/user_upload/importer/downloads/4028b6097384810e01749ff1e1ce608c/Guide_technique_STEICOconstruction_FR_i.pdf) ;
- [certificat ACERMI Isonat Flex 55](https://www.isonat.com/documents/certification-acermi/15-217-984-6-flex-55-0.pdf) ;
- [fiche Simpson Strong-Tie SAI-SAIL](https://pim.strongtie.eu/api/v1/public/download/fr/fr/product/40/SAI-SAIL.pdf).

## Visualisation et calculateur de flèche

```console
just atelier-mob
just atelier-mob-fleche
```

Le second outil reste un calculateur exploratoire pour une poutre rectangulaire
simplement appuyée. Il ne dimensionne ni les poutres en I, ni les traverses
continues sur les trois appuis, ni les assemblages.
