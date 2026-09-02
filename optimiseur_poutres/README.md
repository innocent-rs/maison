# Optimiseur du système poutres, pieux et solives en I

Application Flask locale de pré-dimensionnement du système porteur d'une surface
rectangulaire. Deux onglets présentent les poutres principales sur pieux vissés
et les solives STEICOjoist posées perpendiculairement entre les principales. Le
choix économique est effectué sur le système complet, pas étage par étage.

```bash
python -m optimiseur_poutres.webapp
```

Ouvrir <http://127.0.0.1:5051>.

Le calcul couvre la flexion et le cisaillement aux ELU, la flèche finale avec
fluage aux ELS, la capacité verticale statique des pieux et une vérification
simplifiée de compression du bois perpendiculairement au fil sur la platine.
Il ne remplace pas une note de calcul : assemblages, arrachement, sol,
stabilité, feu, séisme et panneaux ne sont pas vérifiés.

## Poutres principales et pieux

Le catalogue principal compare trois références dont la géométrie et la classe
de résistance sont verrouillées :

- `120 × 240 mm` C24, `40,01 €/m`, longueur maximale `13 m` ;
- `140 × 320 mm` GL24H, `68,80 €/m`, longueur standard `13,50 m` ;
- `140 × 360 mm` GL24H, `77,40 €/m`, longueur standard `13,50 m`.

Le prix au mètre et la longueur commerciale restent éditables. Le C24 utilise
les propriétés avancées saisies dans le projet. Le GL24H utilise ses propriétés
de classe (`E0,mean = 11 500 MPa`, `Gmean = 650 MPa`, `fm,k = 24 MPa`,
`fv,k = 3,5 MPa`, `fc,90,k = 2,5 MPa`) et la densité `450 kg/m³` annoncée par
le fournisseur.

La longueur commerciale doit couvrir le plus grand côté du plancher, quelle que
soit l'orientation retenue pour les principales. Cette règle inclut les pièces
de rive du système complet et aucun aboutage n'est modélisé : un rectangle dont
un côté mesure `13,50 m` exclut donc toujours le C24 limité à `13 m`, mais reste
compatible avec les deux GL24H de `13,50 m`.

La distance entre deux poutres principales devient la portée utilisée dans
l'onglet des solives. Le champ de portée secondaire maximale borne cette
distance dès la recherche des principales ; sa valeur par défaut est `4 m` et
`0` désactive uniquement cette borne géométrique.
La recherche interdit toujours un entraxe inférieur à la largeur de la section,
afin qu'une multiplication artificielle des poutres ne puisse pas masquer une
section insuffisante.

Les appuis intermédiaires sont des pieux vissés répartis en rangées de travées
égales et chaque travée est vérifiée comme simplement appuyée. L'optimisation
détermine automatiquement le nombre de rangées par recherche bornée. Un pieu
est placé sous chaque poutre à chaque rangée, avec un coût de `500 €`, une
platine indicative de `200 mm` et une capacité statique figée de `5 t`, soit
`49,05 kN`. Une réaction ELU supérieure rend la configuration non conforme.
Chaque pieu possède un identifiant, des coordonnées et ses réactions ELS/ELU ;
le plan coloré représente les platines à leur taille relative réelle. Le sol,
le flambement, la corrosion, la résistance propre de la platine, sa liaison au
bois et l'arrachement restent à dimensionner. Ces trois caractéristiques du
pieu ne sont pas paramétrables dans la V1.

Chaque poutre principale reçoit également un pieu à chacune de ses deux
extrémités. Les quatre coins sont donc toujours présents et le coût affiché
inclut tous les pieux de rive comme les pieux intermédiaires.

La limite de flèche finale se choisit par profil de projet : atelier ou stockage
léger `L/250`, maison `L/300`, maison avec finitions fragiles `L/400`, toiture
non accessible `L/200`, ou diviseur personnalisé. Ces profils sont des
hypothèses de pré-dimensionnement et non une validation réglementaire complète.

Des profils d'usage proposent également des valeurs initiales éditables de
charges permanentes et d'exploitation. Ces valeurs facilitent un premier essai
mais ne déterminent pas automatiquement la catégorie de charge réglementaire :
elles doivent être confirmées pour le projet.

Pour les usages de plancher, l'interface affiche une fréquence propre et une
flèche sous charge ponctuelle de `1 kN`. Cette jauge vibratoire est volontairement
**indicative et non bloquante** : une vérification complète de l'Eurocode 5 doit
inclure les solives secondaires, la masse et la rigidité du plancher, le
diaphragme et l'amortissement. Elle n'est donc pas utilisée pour déclarer une
configuration conforme.

## Solives STEICOjoist — V3

Le catalogue initial reprend les trois produits disponibles sur la fiche
Matériaux Naturels au 2 septembre 2026 :

- `SJ60/240`, `14,10 €/m` ;
- `SJ60/300`, `14,40 €/m` ;
- `SJ90/360`, `20,30 €/m`.

Les résistances caractéristiques `Mk` et `Vk`, les rigidités moyennes `EI` et
`GA`, ainsi que les poids linéiques proviennent du guide STEICOconstruction et
de l'ETA-20/0995. Les propriétés mécaniques sont verrouillées dans l'interface ;
les prix restent éditables.

Chaque solive est divisée en segments simplement appuyés entre deux poutres
principales, conformément au principe de pose sur sabots retenu pour le projet.
L'optimiseur recherche la référence et le nombre de lignes qui respectent
l'entraxe maximal, la flexion, le cisaillement et la flèche finale. Le réglage
initial est une classe de service 2, un entraxe maximal de `625 mm` et une limite
de flèche `L/350`, cohérente avec l'abaque de pré-dimensionnement de plancher
publié par STEICO.

Le calepinage peut privilégier un isolant souple de `575 mm` ou `600 mm`. Pour
chaque référence, l'outil calcule le vide réel entre membrures et cherche, parmi
les trames structurellement conformes, une pose légèrement serrée de `0 à 20 mm`.
Il conserve le module choisi sur les travées courantes et reporte le reliquat de
longueur sur une seule rive, ou sur les deux rives si la dernière travée serait
trop étroite pour les membrures. Le calcul mécanique utilise toujours le plus
grand entraxe réellement posé. Le plan affiche les axes réels et précise les
bandes de rive à recouper.

Avec une SJ60 et un entraxe courant de `625 mm`, le vide vaut `565 mm` : un
panneau de `575 mm` est donc serré de `10 mm` et marqué compatible. Sur une zone
de `6 000 mm`, par exemple, neuf travées conservent ce module et la dernière est
ajustée à `375 mm`, au lieu de dégrader toute la trame à `600 mm`. Pour un panneau
de `600 mm`, le module visé avec une SJ60 est `650 mm`; il n'est retenu que si
l'entraxe maximal saisi et le calcul structurel le permettent. Sinon le résultat
indique la compression excessive ou le jeu restant au lieu de masquer l'écart.

Les faces supérieures des principales et des solives sont supposées alignées
pour recevoir le plancher. Une solive plus haute descend donc sous la principale.
La vérification de la solive reste affichée, mais cet assemblage est signalé
comme hors détail EWH standard : la fiche de pose demande de fixer le sabot sur
le porteur avec les fixations prescrites et ne justifie explicitement que le cas
inverse, où le porteur est plus haut que le sabot. Il faut alors faire valider une
poutre principale au moins aussi haute ou un connecteur/détail de reprise prévu
pour le décalage ; la seule référence dimensionnelle du sabot ne vaut pas
validation de sa capacité. Lorsqu'au moins une combinaison compatible en hauteur
existe dans les catalogues actifs, elle est prioritaire dans le choix du système
complet avant la comparaison économique. Cela permet notamment aux `140 × 320`
et `140 × 360` de recevoir respectivement les `SJ60/300` et `SJ90/360` sans
dépassement géométrique.

Deux sabots sont comptés par segment au prix indicatif de `7,30 €` pièce. Leur
résistance, la référence exacte, les pointes, les renforts d'âme, les anti-dévers
et les détails de rive restent à vérifier. Le poids propre des solives retenues
est automatiquement converti en kg/m² et réinjecté dans la charge permanente
des poutres principales et des pieux jusqu'à stabilisation de la solution.

## Moteur d'optimisation

Le moteur sépare désormais deux opérations :

- l'évaluation légère des contraintes et des coûts pendant la recherche ;
- la création détaillée des pieux, coordonnées et réactions uniquement pour
  les résultats effectivement exposés ou exportés.

Pour chaque section, chaque orientation et chaque nombre de travées, la
première trame de poutres conforme est trouvée par dichotomie. Des bornes de coût
arrêtent les branches qui ne peuvent plus améliorer le résultat. Les candidats
utiles sont ensuite comparés avec leur solution de solives, leurs sabots et le
poids propre réinjecté. La compatibilité de hauteur principale/solive puis la
priorité de calepinage 575/600 mm sont appliquées avant le coût lorsqu'une trame
compatible existe.

Le calcul structurel n'est pas formulé en MILP : les portées dépendent des
entiers recherchés par des quotients, et la flèche contient notamment une
puissance quatrième de la portée. Une linéarisation apporterait ici des
approximations et un solveur supplémentaire sans avantage sur cette recherche
discrète bornée. Un MILP reste pertinent pour une future optimisation de
commande et de débit à partir de longueurs commerciales, qui est un problème
linéaire distinct du dimensionnement mécanique.

Le plan V3 superpose les principales et les solives à l'échelle. La fréquence
propre et la flèche sous `1 kN` y restent indicatives tant que le panneau, son
effet diaphragme, les assemblages et l'amortissement ne sont pas modélisés. Les
machines et véhicules localisés constituent l'étape suivante.

Trois lectures de l'optimisation sont présentées : système complet retenu,
nombre minimal de pieux et meilleure marge structurelle parmi les
configurations explorées.
Le CSV exporte l'implantation et les réactions de chaque pieu ; le PDF rassemble
les hypothèses, les taux de travail, le plan à l'échelle et la descente de
charges. Les résultats exportés sont recalculés depuis les valeurs visibles du
formulaire.

Les poutres principales et le catalogue de solives proviennent des fiches
« Poutre et poteau en épicéa contrecollé C24 », « Panne lamellé-collé en
épicéa » et « Poutre en I STEICO joist » de Matériaux Naturels, relevées le
2 septembre 2026. Les prix restent éditables dans l'interface.
