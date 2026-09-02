# Résumé rapide — prochaine session

Dernière mise à jour : 2 septembre 2026.

## Périmètre

Les changements concernent uniquement l'application `optimiseur_poutres`.
Ne pas les propager aux modèles CAO sans demande explicite. L'arbre Git contient
des modifications non validées : toujours commencer par `git status --short`.

## État actuel

- Catalogue des principales :
  - `120 × 240` C24, 40,01 €/m, longueur maximale 13 m ;
  - `140 × 320` GL24H, 68,80 €/m, longueur maximale 13,50 m ;
  - `140 × 360` GL24H, 77,40 €/m, longueur maximale 13,50 m.
- Les GL24H utilisent leurs propriétés mécaniques propres et une densité
  fournisseur de 450 kg/m³.
- Le choix du système complet privilégie une principale au moins aussi haute
  que la solive en I lorsqu'une combinaison compatible existe.
- Règle projet explicite : la longueur commerciale d'une référence doit couvrir
  le plus grand côté du plancher, pièces de rive comprises, quelle que soit
  l'orientation des principales. Aucun aboutage n'est actuellement modélisé.
- Cas de régression : `13,50 × 10 m`, atelier léger, exclut le `120 × 240` dans
  les deux orientations et retient le `140 × 320` GL24H (28 pieux, total indicatif
  21 965,60 € avec les valeurs actuelles).

## Point à reprendre : nombre de pieux

Sur `10 × 10 m`, profil stockage (`G = 125 kg/m²`, `Q = 500 kg/m²`), le résultat
à 36 pieux correspond à 6 poutres × 6 rangées. Ce nombre n'est pas imposé par la
flèche du `120 × 240`, mais par la vérification simplifiée de compression du bois
sur une platine de 200 mm avec `kc,90 = 1,0` :

- 30 pieux : compression bois/platine ≈ 125 %, seul critère en échec ;
- 35 pieux : compression bois/platine ≈ 104 % ;
- 36 pieux : compression bois/platine ≈ 99,8 %, accepté de justesse.

La prochaine étape pertinente est de modéliser le vrai détail de tête de pieu :
dimensions et diffusion de la platine, coefficient `kc,90` justifié, éventuel
renfort, et résistance géotechnique de calcul du pieu. Il faut aussi confirmer si
les 500 kg/m² s'appliquent réellement sur les 100 m² ou seulement par zones.

## Vérifications

```bash
python -m unittest tests.test_optimiseur_poutres tests.test_optimiseur_solives
python -m unittest discover -s tests
```

État constaté : 50 tests ciblés et 220 tests complets réussis. La suite complète
demande l'autorisation d'ouvrir le socket local utilisé par FreeCAD/MPI.

Après modification du code, redémarrer l'application (pas de rechargement
automatique) :

```bash
python -m optimiseur_poutres.webapp
```
