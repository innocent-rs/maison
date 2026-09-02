# Optimiseur de poutres principales en bois

Application Flask locale de pré-dimensionnement des poutres principales d'une
surface rectangulaire. Elle compare les deux sens de portée, les sections du
catalogue et le nombre de poutres principales, puis classe les solutions
conformes par coût.

```bash
python -m optimiseur_poutres.webapp
```

Ouvrir <http://127.0.0.1:5051>.

Le calcul couvre la flexion et le cisaillement aux ELU, la flèche finale avec
fluage aux ELS, la capacité verticale statique des pieux et une vérification
simplifiée de compression du bois perpendiculairement au fil sur la platine.
Il ne remplace pas une note de calcul : assemblages, arrachement, sol,
stabilité, feu, séisme et panneaux ne sont pas vérifiés.

Les futures solives en I ne sont ni dimensionnées ni chiffrées dans cette V1.
Leurs réactions rapprochées sont assimilées à une charge linéique uniforme sur
les poutres principales. Le champ de portée secondaire maximale sert seulement
de contrainte géométrique provisoire ; sa valeur par défaut est `4 m` et `0` le
désactive.
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
configuration conforme dans cette V1.

Trois lectures de l'optimisation sont présentées : coût minimal, nombre minimal
de pieux et meilleure marge structurelle parmi les configurations explorées.
Le CSV exporte l'implantation et les réactions de chaque pieu ; le PDF rassemble
les hypothèses, les taux de travail, le plan à l'échelle et la descente de
charges. Les résultats exportés sont recalculés depuis les valeurs visibles du
formulaire.

Le catalogue initial provient de la fiche « Poutre et poteau en épicéa
contrecollé C24 » de Matériaux Naturels, relevée le 2 septembre 2026. Les prix
restent éditables dans l'interface.
