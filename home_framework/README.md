# home-framework

Ce package est le moteur réutilisable du dépôt. Il ne dépend ni de `maison`,
ni de `local_batteries`, ni du catalogue commercial.

Un assemblage de poutres se décrit par intentions : une racine, des relations
parallèles et des trames entre appuis. Les solides, les placements, la BOM et
la séquence consommée par le manuel sont ensuite dérivés du même graphe.

```python
assemblage = AssemblageContraint.declarer(
    PieceInstance.ancrer(
        "rive_gauche", "Rive gauche", rive,
        Location((0, -largeur / 2, 0)), "saddlebrown",
    ),
    PieceInstance.parallele_a(
        "rive_droite", "Rive droite", rive,
        "rive_gauche", (0, largeur, 0), "saddlebrown",
    ),
    TrameEntreFaces(
        prefixe_identifiant="traverse",
        nom_piece="Traverse",
        piece=traverse,
        couleur="burlywood",
        axes=axes_traverses,
        appuis=(("rive_gauche", "rive_droite"),),
        axe_portee="Y",
    ),
)
```

Chaque composant linéaire possède des `RigidJoint` build123d intrinsèques
nommés `debut` et `fin`. Les coordonnées explicites restent limitées à la
racine et aux axes fonctionnels ; les transformations des pièces mobiles sont
effectuées par connexion de joints.

Les panneaux et connecteurs utilisent un `ComposantRigide` muni d'un joint
`origine`, connecté par `PieceInstance.placer_sur(...)`. Une
`InstructionAssemblage` facultative stocke avec la contrainte le titre, le
geste et les contrôles qui seront rendus dans le manuel.
