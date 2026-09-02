# Mémo de reprise — optimiseur de poutres

Dernière mise à jour : 2 septembre 2026.

Ce document concerne uniquement l'outil autonome `optimiseur_poutres`. Ne pas
étendre une intervention sur cet outil aux modèles CAO (`home_framework`,
`maison`, `atelier_mob`, `local_batteries`) sans demande explicite.

## But de l'outil

Application Flask locale de pré-dimensionnement et de comparaison économique
d'un système porteur rectangulaire composé de :

- poutres principales C24 ou GL24H sur pieux vissés ;
- solives STEICOjoist perpendiculaires, découpées entre les principales et
  suspendues par sabots ;
- exports CSV des pieux et PDF du résultat.

Lancer l'application avec :

```bash
python -m optimiseur_poutres.webapp
```

Puis ouvrir <http://127.0.0.1:5051>.

## Fichiers à connaître

- `calcul.py` : hypothèses projet, sections C24/GL24H, calcul et optimisation des
  poutres principales et des pieux.
- `solives.py` : catalogue STEICOjoist, calcul des solives, calepinage de
  l'isolant et couplage du poids propre avec les principales.
- `webapp.py` : lecture et validation du formulaire, routes Flask et exports.
- `templates/optimiseur.html` : interface des deux onglets et plans SVG.
- `static/optimiseur.css` et `static/optimiseur.js` : présentation et interactions.
- `exports.py` : CSV des pieux et rapport PDF.
- `README.md` : hypothèses détaillées et limites du modèle.
- `tests/test_optimiseur_poutres.py` et `tests/test_optimiseur_solives.py` :
  tests fonctionnels de cet outil.

## Conventions de calcul importantes

### Poutres principales

- Le catalogue compare le `120 × 240 mm` C24 avec les lamellés-collés GL24H
  `140 × 320 mm` et `140 × 360 mm`. Les géométries et classes sont verrouillées ;
  seuls les prix et longueurs commerciales restent éditables.
- La longueur commerciale doit couvrir le plus grand côté du plancher, pièces
  de rive comprises, quelle que soit l'orientation des principales. Un côté de
  `13,50 m` exclut donc toujours le C24 limité à `13 m`.
- Les GL24H utilisent leurs propriétés mécaniques de classe et la densité
  fournisseur de `450 kg/m³`, indépendamment des propriétés C24 éditables.
- Deux orientations peuvent être explorées.
- Une poutre est présente sur chacune des deux rives.
- Les rangées de pieux divisent les poutres en travées égales, calculées comme
  simplement appuyées.
- Le champ « portée secondaire maximale » borne l'écartement des principales,
  donc la portée future des solives.
- Coût indicatif actuel : `500 €` par pieu ; capacité verticale statique :
  `5 t`, soit `49,05 kN` ; platine indicative : `200 mm`.
- La conformité bloque sur la flèche, la flexion, le cisaillement, la capacité
  du pieu et la compression locale bois/platine. La vibration reste indicative.

### Solives en I

- Catalogue initial : `SJ60/240`, `SJ60/300`, `SJ90/360`.
- Chaque ligne de solive est découpée en un segment entre chaque paire de
  poutres principales.
- Deux sabots sont comptés par segment, à `7,30 €` l'unité par défaut.
- La portée d'une solive est l'entraxe des principales.
- L'entraxe affiché et utilisé pour les charges est toujours le plus grand
  intervalle réellement présent dans le calepinage.
- Le poids propre de la solution de solives est converti en kg/m² puis
  réinjecté dans la charge permanente des principales jusqu'à stabilisation.

## Calepinage de l'isolant

Le formulaire propose `575 mm`, `600 mm` ou la désactivation de cette priorité.
La tolérance de préconception considère compatible une compression comprise
entre `0` et `20 mm`.

Pour une SJ60 :

- isolant `575 mm` : module visé `625 mm`, vide `565 mm`, serrage `10 mm` ;
- isolant `600 mm` : module visé `650 mm`, vide `590 mm`, serrage `10 mm`.

Le module visé n'est retenu que s'il respecte l'entraxe maximal saisi et les
vérifications structurelles. Avec une limite de `625 mm`, un panneau de
`600 mm` entre SJ60 donnerait `35 mm` de compression : l'interface le marque
« à adapter ».

La longueur totale n'est plus divisée systématiquement en entraxes uniformes.
L'algorithme conserve le module sur les travées courantes et place le reliquat :

1. sur une seule travée de rive si sa largeur permet de ne pas superposer les
   membrures ;
2. sur les deux rives si le reliquat unique serait trop étroit.

Exemple validé : sur `6 000 mm`, une SJ60 avec isolant `575 mm` donne neuf
travées courantes à `625 mm` et une rive à `375 mm`. Les neuf panneaux courants
restent entiers ; seule la bande de rive est recoupée. Le plan SVG utilise les
axes réels contenus dans `ResultatConfigurationSolives.axes_mm`.

Champs de résultat utiles :

- `entraxe_mm` : plus grand entraxe et module courant ;
- `axes_mm` : positions exactes de toutes les lignes ;
- `nombre_travees_modulaires` : nombre de travées au module courant ;
- `entraxes_rive_mm` : zéro, une ou deux travées ajustées ;
- `compression_isolant_mm`, `isolant_compatible`, `isolant_sans_recoupe`.

## Solive plus haute que la poutre principale

Les faces supérieures sont supposées alignées pour recevoir le plancher. Une
solive plus haute descend donc sous la poutre principale de :

```text
hauteur solive - hauteur poutre principale
```

La résistance de la solive continue d'être calculée, mais cela ne valide pas
l'assemblage. L'interface affiche une alerte « assemblage hors détail EWH
standard », la différence de hauteur et la réaction ELU à reprendre.

Ne pas présenter la seule référence dimensionnelle `EWH hauteur/largeur` comme
une validation. Il faut faire justifier l'une des solutions suivantes :

- une poutre principale au moins aussi haute ;
- un connecteur prévu pour un porteur moins haut ;
- un détail de reprise spécifique validé par le fabricant ou l'ingénieur
  structure.

La notice EWH demande toutes les fixations prescrites dans le porteur et décrit
explicitement l'ajustement lorsque le porteur est plus haut que le sabot, pas le
cas inverse :
<https://pim.strongtie.eu/api/v1/public/download/gb/en/product/1672/EWH.pdf>.

## État à la fin de cette session

- Les anciennes sections principales 140 × 140, 100 × 200, 160 × 160 et
  200 × 200 ont été retirées du catalogue actif. Les GL24H `140 × 320` et
  `140 × 360` ont été ajoutées depuis la fiche fournisseur. L'ajout libre, la
  suppression et la modification de géométrie restent absents de l'interface.
- Le moteur principal utilise des évaluations légères sans liste de pieux,
  une dichotomie sur le nombre de poutres et des bornes de coût. Le détail des
  pieux n'est créé que pour les résultats affichés ou exportés.
- Le choix économique compare maintenant le total poutres + pieux + solives +
  sabots, puis réinjecte la masse des solives jusqu'à stabilisation. Il ne
  choisit plus d'abord les principales indépendamment du second étage.
- Les rectangles 24 × 12 m et 30 × 20 m n'ont plus de solution dans ce catalogue
  tant qu'un aboutage sur appui n'est pas explicitement modélisé.
- Mesure locale du calcul des principales 30 × 20 m : environ 0,009 s après
  refonte contre 13,9 s avant refonte. Le système complet prend environ 0,24 s
  sur cette machine.
- Le calepinage modulaire 575/600 mm fonctionne sur les longueurs exactes et
  non multiples.
- Une ou deux rives ajustées sont calculées, affichées et dessinées à leur axe
  réel.
- Le calcul structurel prend l'entraxe maximal réel, pas une moyenne favorable.
- Le tableau comparatif indique la compatibilité de l'isolant.
- Le PDF reprend l'entraxe courant, les rives ajustées et l'avertissement sur
  les solives plus hautes.
- Une combinaison dont la solive dépasse sous la principale reste calculable et
  accompagnée d'une alerte, mais le choix global préfère désormais une combinaison
  compatible en hauteur lorsqu'il en existe une dans les catalogues actifs.

## Vérifications

Tests ciblés :

```bash
python -m unittest tests.test_optimiseur_solives tests.test_optimiseur_poutres
```

État constaté après la correction des longueurs : `50` tests réussis, dont un budget
déterministe inférieur à 1 000 évaluations pour les principales 30 × 20 m.

Suite complète :

```bash
python -m unittest discover -s tests
```

État constaté : `220` tests réussis. Dans le bac à sable, l'initialisation
FreeCAD/MPI peut nécessiter l'autorisation d'ouvrir un socket local ; les tests
ciblés de l'optimiseur n'ont pas ce besoin.

Avant toute reprise, exécuter `git status --short` : les changements de
l'utilisateur doivent être préservés et ce mémo ne garantit pas que l'arbre de
travail soit encore dans le même état.

## Limites et suites possibles

- Les capacités réelles des sabots, leurs pointes, renforts d'âme, anti-dévers
  et détails de rive ne sont pas dimensionnés.
- Les charges ponctuelles de machines ou véhicules ne sont pas appliquées aux
  solives.
- Le panneau de plancher, son diaphragme, son éventuel effet composite et
  l'amortissement ne sont pas modélisés.
- Le dépassement de hauteur reste un avertissement, mais il est prioritaire sur
  le coût dans le choix global dès qu'une principale assez haute est disponible.
- Le dimensionnement mécanique reste une recherche discrète analytique. Ne pas
  le convertir directement en MILP : les portées et flèches sont non linéaires.
  Réserver un éventuel MILP à la future optimisation de commande/débit des
  longueurs commerciales.
- L'outil reste un pré-dimensionnement et ne remplace pas une note de calcul.
