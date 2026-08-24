# Local batteries — plancher 3 × 3 m

Ce sous-projet décrit uniquement le plancher du local technique, soit une
emprise hors-tout de `3 000 × 3 000 mm` (`9,00 m²`). Il réutilise les familles
de composants déjà présentes dans le projet principal et vise une forte
rigidité pour environ `1 000 kg` de batteries posées au sol.

## Principe retenu

- 2 madriers collés Douglas GT24 de `120 × 240 × 3 000 mm` en rives ;
- 5 traverses dans le même madrier, coupées à `2 756 mm` entre sabots SAI ;
- 9 lignes de STEICOjoist `SJ60/240`, à entraxe réel `276,8 mm` ;
- 4 travées par ligne, soit 36 tronçons de poutre en I de `593 mm` ;
- étriers EWH aux deux extrémités de chaque tronçon ;
- Isonat Flex 55 de `145 mm` entre les âmes des poutres en I ;
- 40 fonds de caisson en OSB 3 BD de `12 mm`, posés par le dessus ;
- 8 tasseaux de rive Douglas de `60 × 40 × 593 mm` à gauche et à droite ;
- 2 couches croisées d'OSB 3 rainuré-languetté de `22 mm`.

La traverse centrale passe sous l'axe du local. Les quatre travées de poutres
en I ne font que `593 mm`, ce qui évite de faire travailler les SJ60/240 sur
une portée proche des 3 m.

La couche inférieure alterne ses joints d'about entre la traverse centrale et
les deux traverses intermédiaires latérales. La couche supérieure est tournée
à 90° et alterne son joint entre les solives situées à `Y = −830,4` et
`+830,4 mm`. Il n'existe donc aucune ligne de joint continue d'une bande à
l'autre. Le débit commun réemploie les chutes entre couches et demande 14
dalles brutes de `2 500 × 675 × 22 mm`.

Les fonds OSB sont découpés en 40 morceaux de `593 × 265,8 mm`. Ils sont
descendus dans les caissons par le dessus et reposent sur les membrures basses
des poutres en I. Dans les huit caissons des rives gauche et droite, leur bord
extérieur repose sur un tasseau Douglas `60 × 40 mm` fixé latéralement au
madrier. Aucun panneau continu ne passe sous la dalle. Une grille de 16 fonds
par panneau demande 3 panneaux OSB 3 BD de `2 800 × 1 196 × 12 mm`.

L'isolant est découpé en 40 morceaux posés de `599 × 268,8 mm`, directement
au-dessus des fonds OSB. Les coupes de `607,5 × 278,8 mm` intègrent la
compression de pose et permettent quatre
morceaux par panneau Isonat brut, soit 10 panneaux utiles. Le conditionnement
commercial de quatre panneaux conduira le chiffrage à acheter trois colis.

La rigidité recherchée vient donc d'une trame serrée, de travées courtes et de
la double peau croisée. Le modèle ne suppose pas que les deux couches d'OSB
travaillent comme un panneau composite collé.

## Utilisation

Avec le viewer déjà démarré :

```console
just local-batteries
```

Pour exporter la nomenclature de fabrication et la liste d'achats :

```console
just local-batteries-bom
```

Le chiffrage et les prix fournisseurs sont fournis par le framework commun :

```console
just chiffrage local_batteries
just optimiser local_batteries
```

Le sous-projet ne contient aucun prix. Les références communes sont résolues
par `maison/prix.py`, y compris automatiquement pour toute longueur de madrier
`120 × 240`, de STEICOjoist `SJ60/240` ou de tasseau `60 × 40`. Les CSV sont
écrits dans `build/local_batteries/`.

## Points à figer avant exécution

La tonne de batteries est une cible de conception, pas une validation de
structure. Il faudra encore connaître l'empreinte et le nombre de pieds des
racks, la position exacte des batteries et la nature des appuis sous le
plancher. Les assemblages, les réactions dans les fondations et la résistance
locale de l'OSB sous chaque pied doivent être vérifiés avant construction.

Le local batteries demandera aussi une étude séparée pour la ventilation, le
risque incendie, l'humidité, la rétention éventuelle et les prescriptions du
fabricant des batteries. Ces sujets ne sont pas inclus dans ce sous-projet.
