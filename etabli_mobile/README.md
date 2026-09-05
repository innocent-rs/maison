# Base de l'établi mobile

Le module décrit le rectangle inférieur en profilés aluminium 45 × 90 mm, avec
les 90 mm orientés verticalement. Deux supports en contreplaqué de 12 mm,
limités aux empreintes des caisses, reçoivent deux modules Qbrick System ONE.
Les pieds, les montants et le cadre supérieur ne font pas encore partie du
modèle. Les roues ne sont pas dessinées, mais leurs huit axes sont implantés.

L'enveloppe mesure `1 700 × 385 × 90 mm`. La longueur est plafonnée à
`1 700 mm` afin de rester compatible avec le transport dans un Kangoo. La
profondeur correspond exactement à celle des Qbrick. Avec les supports, la
base atteint `102 mm` de haut sous les caisses.

## Supports CP et Qbrick System ONE

Le contreplaqué est limité à deux découpes de `585 × 385 × 12 mm`, chacune
placée directement sous un module. Leur masse indicative totale est de
`3,51 kg` avec une densité paramétrable de `650 kg/m³`. Les supports sont
plaqués aux extrémités du châssis et laissent un vide central de `530 mm`.
Leurs arêtes intérieures à `x = -265 mm` et `x = +265 mm` coïncident avec les
faces intérieures de traverses dédiées. Les axes de ces traverses sont à
`x = -287,5 mm` et `x = +287,5 mm` : leurs `45 mm` de largeur sont donc
entièrement sous le CP.

Deux enveloppes Qbrick System ONE de `585 × 385 × 301 mm` sont disposées
suivant la longueur, centrées à `x = -557,5 mm` et `x = +557,5 mm`. Leurs faces
extérieures affleurent les extrémités du châssis à `x = -850 mm` et
`x = +850 mm`. L'empreinte correspond au
[gabarit du Qbrick System ONE 350 2.0 VARIO](https://www.qbricksystem.com/fr/product/qbrick-system-one-350-vario-2-0/).
Ce modèle sert de référence d'encombrement jusqu'au choix des deux variantes
exactes ; les poignées, nervures et connecteurs ne sont pas modélisés.

## Renforts et roues

La base comprend :

- deux longerons de `1 700 mm` ;
- quatre traverses de `295 mm` : deux aux extrémités et deux sous les arêtes
  intérieures des supports CP ;
- quatre petits renforts diagonaux dans les angles extérieurs ;
- huit renforts identiques autour des deux traverses sous les Qbrick ;
- huit axes de roues, alignés par paires sur les quatre traverses.

Les renforts rejoignent les deux côtés de chaque angle avec un recul
paramétrable de `115 mm`, valeur entière maximale sans collision. Chacun reçoit
deux coupes à 45° : longueur d'axe `162,6 mm`, pointe longue `207,6 mm` et
pointe courte `117,6 mm`. Cette cote devra être ajustée à la platine des roues
et validée avec les connecteurs et les charges réelles.

## Poids indicatif

Le [catalogue Bosch Rexroth](https://apps.boschrexroth.com/DCUS/2023/08.25.AT_Uploads/R999001283_2020-09_media-1.pdf)
donne `3,0 kg/m` pour le profilé 45×90L. Avec cette hypothèse paramétrable, les
profilés du bâti courant pèsent environ `19,59 kg`. Avec les deux supports CP,
la masse structurelle connue est d'environ `23,11 kg`. Le même bâti pèserait
`27,43 kg` en profilés avec la variante 45×90 standard donnée à `4,2 kg/m` dans
ce catalogue. Ces totaux excluent les Qbrick System ONE, les connecteurs, la
visserie, les platines et les roues. La longueur de débit cumulée, mesurée aux
pointes longues, est de `7,072 m`.

## Utilisation

```console
just etabli-mobile
just chiffrage etabli_mobile chassis
```

Les profilés sont représentés par leur enveloppe pleine, sans rainures. Le
volume d'aluminium n'est donc pas déduit de cette géométrie simplifiée.
