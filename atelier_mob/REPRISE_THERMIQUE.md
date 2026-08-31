# Reprise — optimisation thermique des vides du plancher

## Point de départ

Le plancher de l'atelier MOB mesure `7 × 15 m`, soit `105 m²`. Le viewer et le
modèle CAO disposent maintenant d'un détecteur de vides générique. Il ne
connaît aucun type de pièce particulier et effectue l'opération suivante :

```text
volume vide = enveloppe d'analyse − union des solides CAO présents
```

Le moteur réutilisable se trouve dans `home_framework/vides.py`. L'adaptateur
du plancher se trouve dans `atelier_mob/thermique.py`. Pour un mur ou une
toiture, il faudra seulement fournir une autre enveloppe d'analyse au même
moteur.

## Enveloppe actuellement analysée

Pour le plancher, la zone est comprise entre :

- la face intérieure du fond de caisson OSB, à `Z = 51 mm` ;
- la sous-face de l'OSB supérieur, à `Z = 240 mm`.

Elle couvre toute l'emprise `15 000 × 7 000 mm` et mesure donc `189 mm`
d'épaisseur, soit un volume brut de `19,845 m³`.

Le détecteur soustrait automatiquement toutes les formes volumiques qui
intersectent cette enveloppe. Les pièces sans volume CAO et les pièces situées
hors de l'enveloppe sont ignorées.

## Résultat de référence

Avec la composition courante :

- `339` solides intersectent réellement l'enveloppe ;
- le vide résiduel vaut `4,070 m³` ;
- il représente `20,51 %` du volume analysé ;
- le résultat forme une seule composante connexe.

Cette composante unique montre que plusieurs zones communiquent entre elles :
les cavités autour des âmes des poutres en I, les jeux géométriques et surtout
le plénum laissé au-dessus des `145 mm` d'Isonat dans une hauteur disponible de
`189 mm`.

Ces valeurs évolueront automatiquement si la géométrie, l'épaisseur de
l'isolant ou une pièce du plancher change.

## Viewer

Le viewer Three.js exporte onze couches. La couche de diagnostic :

- porte l'identifiant `vides_structure` ;
- utilise `public/models/vides_structure.glb` ;
- est rouge translucide et masquée au démarrage ;
- est accessible par le bouton **Vides structure** ;
- n'a aucune masse et ne modifie pas les poids propres.

Le manifeste expose les données dans `summary.voidAnalysis` : volume de
l'enveloppe, volume vide, taux volumique, nombre d'occupants et nombre de
composantes connexes.

## API utile

```python
from atelier_mob import creer_atelier_mob

atelier = creer_atelier_mob()
rapport = atelier.analyser_vides()

print(rapport.volume_enveloppe_m3)  # 19.845
print(rapport.volume_vide_m3)       # 4.07004396
print(rapport.taux_vide_pct)        # 20.509...
print(rapport.nombre_composantes)   # 1
```

Utilisation indépendante d'un projet :

```python
from home_framework import detecter_vides

rapport = detecter_vides(enveloppe, formes_des_occupants)
```

## Limite importante

Le taux de vide de `20,51 %` n'est ni une baisse de résistance thermique de
`20,51 %`, ni une part de déperdition, ni un coefficient de pont thermique.
Le détecteur actuel ne calcule aucun flux de chaleur.

Un calcul thermique doit distinguer au minimum :

- l'isolant, le bois/LVL, l'âme, les OSB, l'acier et l'air ;
- une cavité d'air fermée, faiblement ventilée ou ventilée ;
- le sens du flux et les résistances superficielles intérieure/extérieure ;
- les chemins thermiques répétitifs et les liaisons singulières ;
- les conditions réelles sous le plancher : extérieur, vide sanitaire ou
  volume non chauffé.

Une valeur `ψ` ne doit pas être déduite du seul volume vide. Elle demandera un
modèle de flux 2D ou 3D conforme à l'ISO 10211.

## Suite recommandée

1. Fixer la situation thermique : atelier chauffé, température de calcul,
   humidité, nature du volume sous le plancher et exposition au vent.
2. Décider si le plénum de `44 mm` au-dessus de l'Isonat est volontaire et si
   les cavités sont étanches, faiblement ventilées ou ventilées.
3. Ajouter au modèle une bibliothèque de propriétés thermiques sourcées :
   conductivité `λ`, résistance des cavités et résistances superficielles.
4. Calculer le `R` puis le `U` du chemin courant entre solives comme cas de
   référence unidimensionnel.
5. Extraire automatiquement des coupes représentatives : milieu de caisson,
   solive en I, entretoise, traverse primaire et rive.
6. Résoudre les coupes en 2D pour obtenir un `U` équivalent et les coefficients
   linéiques `ψ`, sans utiliser une simple moyenne du taux de vide.
7. Comparer plusieurs variantes CAO : Isonat `180 mm`, remplissage du plénum,
   remplissage autour des âmes, complément continu et traitement des rives.
8. Renvoyer les résultats dans le viewer sous forme de couches ou d'une carte
   colorée : vide, matériaux, zones de flux élevé et variantes comparées.
9. Ajouter des critères automatiques : `R` minimal, `U` maximal, absence de
   cavité ventilée non prévue et température superficielle minimale.

## Questions à trancher à la reprise

- Le dessous du plancher donne-t-il sur l'air extérieur ou un vide sanitaire ?
- Le local sera-t-il chauffé en permanence ou ponctuellement ?
- Le vide de `44 mm` au-dessus des panneaux est-il voulu ?
- Souhaite-t-on remplir les cavités des profils en I ou poser une couche
  continue supplémentaire ?
- Quelle cible retenir : résistance `R`, coefficient `U`, exigence RE2020 ou
  objectif de confort propre au projet ?

## Validation et commandes

La dernière validation complète compte `170` tests réussis.

```console
just atelier-mob-viewer-export
just atelier-mob-viewer
just test
```

Fichiers principaux à relire :

- `home_framework/vides.py` : soustraction générique et composantes connexes ;
- `atelier_mob/thermique.py` : enveloppe du plancher ;
- `atelier_mob_viewer/export_model.py` : export GLB et manifeste ;
- `atelier_mob_viewer/main.js` : affichage de la couche et des métriques ;
- `tests/test_vides.py` : comportement générique ;
- `tests/test_thermique_atelier_mob.py` : valeurs de référence du plancher ;
- `tests/test_viewer_atelier_mob.py` : intégrité de l'export viewer.

Références déjà retenues :

- ISO 10211 pour les calculs détaillés de ponts thermiques ;
- certificat ACERMI de l'Isonat Flex 55 pour les propriétés déclarées de
  l'isolant ;
- documentation technique STEICO pour la géométrie et les propriétés des
  poutres en I.
