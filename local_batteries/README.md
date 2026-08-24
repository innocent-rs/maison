# Local batteries — structure monobloc 3 × 3 m

Ce sous-projet décrit le plancher et les quatre murs solidaires du local
technique, soit une emprise de plancher de `3 000 × 3 000 mm` (`9,00 m²`). Il
réutilise les familles de composants déjà présentes dans le projet principal
et vise une forte rigidité pour environ `1 000 kg` de batteries posées au sol.

## Principe retenu : un plancher simple

- 2 madriers collés Douglas GT24 de `120 × 240 × 3 000 mm` en rives ;
- 2 traverses d'extrémité dans le même madrier, coupées à `2 756 mm` ;
- 4 STEICOjoist `SJ60/240` continues de `2 750 mm`, entraxe `553,6 mm` ;
- 8 étriers EWH et 4 sabots SAI au total ;
- Isonat Flex 55 de `145 mm` dans les cinq grands caissons ;
- 5 fonds de caisson en OSB 3 BD de `12 mm`, posés par le dessus ;
- 2 tasseaux de rive Douglas de `60 × 40 × 2 750 mm` ;
- une seule couche porteuse d'OSB 3 rainuré-languetté de `22 mm` ;
- quatre murs en ossature Douglas `45 × 145 mm`, hauteur `2 575 mm` ;
- une réservation de porte centrée de `900 × 2 150 mm`, sans fenêtre ;
- isolation murale Isonat Flex 55 de `145 mm` ;
- voile extérieur en OSB 3 BD de `12 mm`.

L'ancienne grille de cinq traverses et 36 petits tronçons de poutre en I reste
constructible par `creer_local_batteries_renforce()`, uniquement pour comparer
les coûts et les calculs. Elle n'est plus la variante courante.

Le grand axe des dalles OSB supérieures est perpendiculaire aux SJ60/240. Leur
unique ligne de joints d'about tombe sur la quatrième solive. Dix découpes sont
issues de 7 dalles brutes `2 500 × 675 × 22 mm`. Les cinq fonds inférieurs de
`2 750 × 542,6 mm` utilisent toujours 3 panneaux OSB BD : la simplification
réduit surtout les coupes et les fixations, sans retirer le contreventement bas.

Chaque caisson reçoit deux longueurs d'isolant de `1 220 mm` et un complément
de `316 mm`. Les dix grandes découpes consomment dix panneaux ; les cinq
compléments sont regroupés sur deux panneaux, soit 12 panneaux pour le
plancher.

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
douze bandes étroites de la façade sont débitées deux par panneau. Avec les 12
panneaux du plancher, la commande totale est de 49 panneaux, arrondie par le
chiffrage commun à 13 colis de quatre.

L'ossature représente `106,00 m` utiles de Douglas `45 × 145 mm`, débités dans
20 barres de 6 m avec un rendement de `88,33 %`. Le tarif de cette nouvelle
famille de coupe reste centralisé dans `catalogues/prix.py`.

La rigidité recherchée vient des quatre SJ60/240 continues et de la peau
porteuse. Le local reste volontairement une boîte technique : aucune cloison,
fenêtre ou finition intérieure n'est ajoutée au nom de l'optimisation.

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
totalité du plancher : 8 poutres, 4 sabots Simpson SAI,
8 étriers Simpson EWH, 2 tasseaux de rive, 5 fonds OSB et 15 découpes
d'isolant, puis 10 découpes OSB porteuses. Les
quantités, dimensions, positions et vues sont relues sur le
graphe de contraintes qui produit aussi les solides `build123d`, la BOM et les
débits. Les neuf opérations ne sont pas écrites dans le générateur : elles sont
déduites des références orientées et du regroupement des pièces partageant la
même intention de pose. Les textes et contrôles de fixation Simpson sont
portés par les déclarations CAO. Les murs restent hors de cette édition du
manuel.

## Chiffrage et optimisation

Le chiffrage et les prix fournisseurs sont fournis par le framework commun :

```console
just chiffrage local_batteries
just optimiser local_batteries
just local-batteries-chiffrage
```

Le sous-projet ne contient aucun prix. Les références communes sont résolues
par `catalogues/prix.py`, y compris automatiquement pour toute longueur de madrier
`120 × 240`, de STEICOjoist `SJ60/240`, de tasseau `60 × 40` ou de bois
d'ossature `45 × 145`. Les CSV sont écrits dans `build/local_batteries/`.

Aux tarifs TTC datés dans le catalogue, la BOM d'achat complète actuellement
renseignée passe de `4 732,30 €` pour l'ancienne grille renforcée à
`3 258,32 €` pour le plancher simple, soit `1 473,98 €` ou `31,1 %`
d'économie. Ce total est un coût de fournitures : il exclut notamment
livraison, main-d'œuvre, fondations, toiture, porte, bardage et électricité.
La variante retenue se répartit en `1 685,52 €` pour le plancher complet et
`1 572,80 €` pour les quatre murs.

Le comparatif n'utilise pas des mètres théoriques : il achète des barres et
conditionnements entiers. La simplification fait notamment passer le Douglas
`120 × 240` de deux barres à une, les SJ60/240 de deux barres à une, les EWH de
72 à 8 et les SAI de 10 à 4. L'isolant de plancher augmente de deux panneaux,
ce qui est inclus dans le solde. `comparatif_couts.md`, `chiffrage_renforce.csv`
et `chiffrage_optimise.csv` sont générés dans `build/local_batteries/`.

## POC CalculiX piloté par la CAO

Le premier modèle éléments finis du plancher est généré directement depuis le
`PlancherBois` du local : les deux axes de traverses, les quatre axes de solives,
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
la charge verticale atteint `14,086 kN`. CalculiX 2.23 donne une flèche élastique
maximale de `4,038 mm` et quatre réactions symétriques de `3,522 kN`. Le repère
indicatif `L/300` vaut `9,17 mm`. Un cas exploratoire linéaire à `2 000 kg`
atteint `7,613 mm`, mais ne constitue pas une charge admissible.

Ce résultat est une première borne de raideur : les croisements SAI/EWH sont
parfaitement rigides et l'OSB distribue les charges sans contribuer à la
rigidité. Les rigidités `EI = 709 kN·m²` et `GA = 3,18 MN` de la SJ60/240 sont
reproduites par une section orthotrope équivalente. Les murs, les fondations,
le glissement et la résistance des connecteurs, le fluage, les vibrations, les
combinaisons ELU, le poinçonnement local de l'OSB et les vérifications au feu
sont exclus. La valeur de `4,038 mm` ne constitue donc ni une charge admissible
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
