# Optimiseur du système poutres, pieux et solives en I

Application Flask locale de pré-dimensionnement du système porteur d'une surface
rectangulaire. Deux onglets dimensionnent successivement les poutres principales
sur pieux vissés et les solives STEICOjoist posées perpendiculairement entre les
principales.

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

La distance entre deux poutres principales devient la portée utilisée dans
l'onglet des solives. Le champ de portée secondaire maximale borne cette
distance dès la recherche des principales ; sa valeur par défaut est `4 m` et
`0` désactive uniquement cette borne géométrique.
La recherche interdit toujours un entraxe inférieur à la largeur de la section,
afin qu'une multiplication artificielle des poutres ne puisse pas masquer une
section insuffisante.

Les appuis intermédiaires sont des pieux vissés répartis en rangées de travées
égales et chaque travée est vérifiée comme simplement appuyée. L'optimisation
détermine automatiquement le nombre de rangées : elle s'arrête dès que des
travées supplémentaires ne pourraient plus réduire la quantité de bois. Un pieu
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

## Solives STEICOjoist — V2

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
validation de sa capacité.

Deux sabots sont comptés par segment au prix indicatif de `7,30 €` pièce. Leur
résistance, la référence exacte, les pointes, les renforts d'âme, les anti-dévers
et les détails de rive restent à vérifier. Le poids propre des solives retenues
est automatiquement converti en kg/m² et réinjecté dans la charge permanente
des poutres principales et des pieux jusqu'à stabilisation de la solution.

Le plan V2 superpose les principales et les solives à l'échelle. La fréquence
propre et la flèche sous `1 kN` y restent indicatives tant que le panneau, son
effet diaphragme, les assemblages et l'amortissement ne sont pas modélisés. Les
machines et véhicules localisés constituent l'étape suivante.

Trois lectures de l'optimisation sont présentées : coût minimal, nombre minimal
de pieux et meilleure marge structurelle parmi les configurations explorées.
Le CSV exporte l'implantation et les réactions de chaque pieu ; le PDF rassemble
les hypothèses, les taux de travail, le plan à l'échelle et la descente de
charges. Les résultats exportés sont recalculés depuis les valeurs visibles du
formulaire.

Les catalogues initiaux proviennent des fiches « Poutre et poteau en épicéa
contrecollé C24 » et « Poutre en I STEICO joist » de Matériaux Naturels,
relevées le 2 septembre 2026. Les prix restent éditables dans l'interface.
