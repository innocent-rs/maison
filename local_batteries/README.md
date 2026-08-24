# Local batteries — structure monobloc 3 × 3 m

Ce sous-projet décrit le plancher et les quatre murs solidaires du local
technique, soit une emprise de plancher de `3 000 × 3 000 mm` (`9,00 m²`). Il
réutilise les familles de composants déjà présentes dans le projet principal
et vise une forte rigidité pour environ `1 000 kg` de batteries posées au sol.

## Principe retenu

- 2 madriers collés Douglas GT24 de `120 × 240 × 3 000 mm` en rives ;
- 5 traverses dans le même madrier, coupées à `2 756 mm` entre sabots SAI ;
- 9 lignes de STEICOjoist `SJ60/240`, à entraxe réel `276,8 mm` ;
- 4 travées par ligne, soit 36 tronçons de poutre en I de `593 mm` ;
- étriers EWH aux deux extrémités de chaque tronçon ;
- Isonat Flex 55 de `145 mm` entre les âmes des poutres en I ;
- 40 fonds de caisson en OSB 3 BD de `12 mm`, posés par le dessus ;
- 8 tasseaux de rive Douglas de `60 × 40 × 593 mm` à gauche et à droite ;
- 1 couche porteuse d'OSB 3 rainuré-languetté de `22 mm` ;
- quatre murs en ossature Douglas `45 × 145 mm`, hauteur `2 575 mm` ;
- une réservation de porte centrée de `900 × 2 150 mm`, sans fenêtre ;
- isolation murale Isonat Flex 55 de `145 mm` ;
- voile extérieur en OSB 3 BD de `12 mm`.

La traverse centrale passe sous l'axe du local. Les quatre travées de poutres
en I ne font que `593 mm`, ce qui évite de faire travailler les SJ60/240 sur
une portée proche des 3 m.

La couche porteuse alterne ses joints d'about entre la traverse centrale et
les deux traverses intermédiaires latérales. Chaque joint est ainsi porté et
il n'existe aucune ligne de joint continue d'une bande à l'autre. Son débit
demande 8 dalles brutes de `2 500 × 675 × 22 mm`.

Les fonds OSB sont découpés en 40 morceaux de `593 × 265,8 mm`. Ils sont
descendus dans les caissons par le dessus et reposent sur les membrures basses
des poutres en I. Dans les huit caissons des rives gauche et droite, leur bord
extérieur repose sur un tasseau Douglas `60 × 40 mm` fixé latéralement au
madrier. Aucun panneau continu ne passe sous la dalle. Une grille de 16 fonds
par panneau demande 3 panneaux OSB 3 BD de `2 800 × 1 196 × 12 mm`.

L'isolant est découpé en 40 morceaux posés de `599 × 268,8 mm`, directement
au-dessus des fonds OSB. Les coupes de `607,5 × 278,8 mm` intègrent la
compression de pose et permettent quatre morceaux par panneau Isonat brut,
soit 10 panneaux utiles. Le conditionnement
commercial de quatre panneaux conduira le chiffrage à acheter trois colis.

## Murs et porte

Les murs forment une seule ossature : les façades avant et arrière font
`3 000 mm`, les murs latéraux de `2 710 mm` viennent entre elles et leurs
voiles OSB ferment les angles sur l'emprise complète. Chaque mur comprend une
lisse basse, une double lisse haute et des montants de `45 × 145 mm`. La
hauteur libre entre lisses est de `2 440 mm`, exactement deux hauteurs de
panneau Isonat de `1 220 mm`.

La façade avant reçoit une seule porte centrée. Le tableau `900 × 2 150 mm`
correspond au format courant indiqué par
[Bel'M](https://www.belm.fr/conseils/choisir-sa-porte-dentree-sur-mesure) et
[Lapeyre](https://www.lapeyre.fr/produits/porte-dentree-lothey-pvc-FPC642681).
L'ossature comprend deux montants porteurs, deux montants d'appui et un
linteau double `45 × 145 mm`. Le bloc-porte lui-même n'est pas encore choisi
ni chiffré : sa cote hors-tout devra être contrôlée avant la coupe définitive.

Le voile mural demande 10 panneaux OSB BD de `1 196 × 2 800 × 12 mm`. Les murs
arrière et gauche utilisent chacun deux largeurs de `1 196 mm` et une largeur
de `608 mm`; le mur droit utilise deux largeurs de `1 196 mm` et deux bandes
de `304 mm`. Une chute de `274 mm` fournit les quatre morceaux
`225 × 425 mm` au-dessus de la porte ; aucune dalle supplémentaire n'est donc
nécessaire pour le linteau.

Les murs contiennent 48 découpes d'isolant issues de 37 panneaux Isonat. Les
douze bandes étroites de la façade sont débitées deux par panneau. Avec les 10
panneaux du plancher, la commande totale est de 47 panneaux, arrondie par le
chiffrage commun à 12 colis de quatre.

L'ossature représente `106,00 m` utiles de Douglas `45 × 145 mm`, débités dans
20 barres de 6 m avec un rendement de `88,33 %`. Le tarif de cette nouvelle
famille de coupe reste centralisé dans `catalogues/prix.py`.

La rigidité recherchée vient donc d'une trame serrée, de travées courtes et de
la peau porteuse continue. Son interaction avec les solives et les assemblages
devra être étudiée explicitement dans le futur modèle CalculiX.

## Utilisation

Avec le viewer déjà démarré :

```console
just local-batteries
```

Pour exporter la nomenclature de fabrication et la liste d'achats :

```console
just local-batteries-bom
```

Pour générer le POC de manuel d'assemblage PDF piloté par la CAO :

```console
just local-batteries-manuel
```

Le document est écrit dans
`build/local_batteries/manuel_assemblage_poutres.pdf`. Il couvre désormais la
totalité du plancher : 43 poutres, 10 sabots Simpson SAI,
72 étriers Simpson EWH, 8 tasseaux de rive, 40 fonds OSB et 40 découpes
d'isolant, puis 12 panneaux OSB porteurs. Les
quantités, dimensions, positions et vues sont relues sur le
graphe de contraintes qui produit aussi les solides `build123d`, la BOM et les
débits. Les douze opérations ne sont pas écrites dans le générateur : elles sont
déduites des références orientées et du regroupement des pièces partageant la
même intention de pose. Les textes et contrôles de fixation Simpson sont
portés par les déclarations CAO. Les murs restent hors de cette édition du
manuel.

Le chiffrage et les prix fournisseurs sont fournis par le framework commun :

```console
just chiffrage local_batteries
just optimiser local_batteries
```

Le sous-projet ne contient aucun prix. Les références communes sont résolues
par `catalogues/prix.py`, y compris automatiquement pour toute longueur de madrier
`120 × 240`, de STEICOjoist `SJ60/240`, de tasseau `60 × 40` ou de bois
d'ossature `45 × 145`. Les CSV sont écrits dans `build/local_batteries/`.

## POC CalculiX piloté par la CAO

Le premier modèle éléments finis du plancher est généré directement depuis le
`PlancherBois` du local : les cinq axes de traverses, les neuf axes de solives,
les sections, les longueurs et la masse des composants ne sont pas ressaisis
dans un fichier FreeCAD. Le framework commun écrit un jeu CalculiX `B31`, lance
le solveur et contrôle l'équilibre entre charges et réactions :

```console
just local-batteries-simulation
```

La charge batterie est paramétrable sans modifier la CAO. Par exemple :

```console
just local-batteries-simulation -- --masse-batteries 1200 \
  --empreinte-longueur 1200 --empreinte-largeur 800 \
  --centre-x 1650 --centre-y 200
```

Les sorties sont écrites sous `build/local_batteries/simulation_calculix/` :

- `plancher_local.inp` : entrée CalculiX autonome, avec les hypothèses en tête ;
- `plancher_local.dat` et `plancher_local.frd` : résultats bruts, le `.frd`
  contenant déplacements et contraintes et pouvant être ouvert dans FreeCAD
  pour le post-traitement ;
- `plancher_local_resultats.json` : flèche, réactions et erreur d'équilibre ;
- `plancher_local.log` : journal complet du solveur.
- `carte_fleche_verticale.png` : heat map en plan, avec poutres, appuis,
  empreinte des batteries et point de flèche maximale ;
- `deformee_3d.png` : ossature déformée et colorée, amplifiée `×150` par
  défaut pour rendre une flèche millimétrique visible.

L'amplification graphique ne modifie jamais les valeurs calculées :

```console
just local-batteries-simulation -- --amplification-deformee 250
```

Le shell Nix par défaut contient CalculiX 2.23. L'environnement graphique FEM,
plus lourd, ajoute FreeCAD et Gmsh uniquement à la demande :

```console
nix develop .#fem
freecad build/local_batteries/simulation_calculix/plancher_local.frd
```

Le cas par défaut place `1 000 kg` au centre sur une empreinte supposée de
`1 000 × 1 000 mm`. Avec les poids propres du châssis, des deux OSB du plancher
(fond de caisson de 12 mm et unique peau supérieure de 22 mm) et de l'isolant,
la charge verticale atteint `15,438 kN`. CalculiX 2.23 donne une flèche élastique
maximale de `1,504 mm` et quatre réactions symétriques de `3,860 kN`, avec une
erreur d'équilibre de `0,00024 N`.

Ce résultat est une première borne de raideur : les croisements SAI/EWH sont
parfaitement rigides et l'OSB distribue les charges sans contribuer à la
rigidité. Les rigidités `EI = 709 kN·m²` et `GA = 3,18 MN` de la SJ60/240 sont
reproduites par une section orthotrope équivalente. Les murs, les fondations,
le glissement et la résistance des connecteurs, le fluage, les vibrations, les
combinaisons ELU, le poinçonnement local de l'OSB et les vérifications au feu
sont exclus. La valeur de `1,504 mm` ne constitue donc ni une charge admissible
ni une validation de construction.

La heat map automatique montre où le plancher se déplace le plus, pas où une
rupture est prédite. Le `.frd` contient aussi le champ de contraintes `S`, que
FreeCAD peut afficher interactivement. Une véritable carte « où cela flanche »
devra représenter un taux de travail calculé à partir des résistances
caractéristiques du Douglas, des SJ60, de l'OSB et des SAI/EWH, avec les
combinaisons ELU applicables.

## Points à figer avant exécution

La tonne de batteries est une cible de conception, pas une validation de
structure. Il faudra encore connaître l'empreinte et le nombre de pieds des
racks, la position exacte des batteries et la nature des appuis sous le
plancher. Les assemblages, les réactions dans les fondations et la résistance
locale de l'OSB sous chaque pied doivent être vérifiés avant construction.

Le local batteries demandera aussi une étude séparée pour la ventilation, le
risque incendie, l'humidité, la rétention éventuelle et les prescriptions du
fabricant des batteries. Ces sujets ne sont pas inclus dans ce sous-projet.
La toiture, le pare-pluie, le bardage, le frein-vapeur, le parement intérieur,
les ancrages définitifs des murs et le bloc-porte restent également hors du
périmètre actuel.
