# Optimiseur de poutres principales en bois

Application Flask locale de pré-dimensionnement des poutres principales d'une
surface rectangulaire. Elle compare les deux sens de portée, les sections du
catalogue et le nombre de poutres principales, puis classe les solutions
conformes par coût.

```bash
python -m optimiseur_poutres.webapp
```

Ouvrir <http://127.0.0.1:5051>.

Le calcul couvre la flexion et le cisaillement aux ELU ainsi que la flèche finale
avec fluage aux ELS. Il ne remplace pas une note de calcul : vibrations,
assemblages, appuis, stabilité, feu, séisme et panneaux ne sont pas vérifiés.

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
`49,05 kN`. Une réaction ELU
supérieure rend la configuration non conforme. Le sol, le flambement, la
corrosion, la platine, la liaison au bois et les fondations de rive restent à
dimensionner. Ces trois caractéristiques du pieu ne sont pas paramétrables dans
la V1.

Chaque poutre principale reçoit également un pieu à chacune de ses deux
extrémités. Les quatre coins sont donc toujours présents et le coût affiché
inclut tous les pieux de rive comme les pieux intermédiaires.

La limite de flèche finale se choisit par profil de projet : atelier ou stockage
léger `L/250`, maison `L/300`, maison avec finitions fragiles `L/400`, toiture
non accessible `L/200`, ou diviseur personnalisé. Ces profils sont des
hypothèses de pré-dimensionnement et non une validation réglementaire complète.

Le catalogue initial provient de la fiche « Poutre et poteau en épicéa
contrecollé C24 » de Matériaux Naturels, relevée le 2 septembre 2026. Les prix
restent éditables dans l'interface.
