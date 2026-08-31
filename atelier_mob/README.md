# Atelier MOB

Modèle paramétrique d'un atelier rectangulaire en ossature bois. Le projet
n'est plus une maison en A : sa géométrie de plancher est désormais
indépendante de la forme future des murs et de la toiture.

## Hypothèse d'emprise

L'état initial adopte une longueur ronde de `15 m` : `7 000 × 15 000 mm`, soit
`105 m²`. La largeur et la longueur peuvent être modifiées :

```python
from atelier_mob import creer_atelier_mob

atelier = creer_atelier_mob(
    largeur_interieure=7_000,
    longueur_interieure=15_000,
)
```

## Plancher de référence

Le modèle courant comprend, de bas en haut :

- des fonds de caisson en OSB 3 à bords droits de `12 mm`, posés sur les
  membrures basses et sur des tasseaux de rive ;
- des panneaux semi-rigides en fibre de bois Isonat Flex 55 de `145 mm`
  (`R = 4,00 m²·K/W` déclaré pour cette épaisseur) ;
- des solives en I STEICOjoist `SJ60/240`, réparties à environ `564 mm`
  d'entraxe ;
- une rangée médiane d'entretoises pleine hauteur en STEICOjoist dans chacune
  des sept travées, avec douze blocs par rangée ;
- un plancher porteur en OSB 3 rainuré-languetté de `22 mm`.

Les deux poutres longitudinales et les huit traverses primaires sont des
éléments de `120 × 240 mm`. Les solives en I sont découpées en sept travées de
`1 999 mm` environ. Le calepinage à huit traverses maintient les joints des
dalles supérieures de `2 500 mm` sur des appuis.

Les `84` entretoises comprennent `70` coupes de `504 mm` entre solives et `14`
coupes de rive de `530 mm`. Chaque fond OSB est divisé au droit de l'âme de
l'entretoise et repose sur sa membrure basse. L'isolant est également découpé
de part et d'autre de la membrure afin qu'aucun solide ne se chevauche.

Les poutres longitudinales de `15 000 mm` restent représentées continues
pour lire le chemin des charges. Leur débit transportable, leurs aboutages au
droit des appuis et la disponibilité commerciale ne sont pas encore résolus.

L'OSB inférieur est pour l'instant une hypothèse géométrique utile pour fermer
et contreventer les caissons. Avant exécution, la composition doit faire
l'objet d'une vérification hygrothermique : un atelier chauffé demande une
bonne continuité d'étanchéité à l'air côté chaud et une sous-face suffisamment
ouverte à la diffusion et protégée du vent, de l'eau et des rongeurs.

## Fondations et chemin des charges

Par défaut, trois platines de pieux sont placées sous chacune des huit
traverses : une sous chaque poutre de rive et une sous l'axe central, soit
`24` appuis. Chaque demi-traverse a ainsi une portée géométrique d'environ
`3 380 mm`. Les fûts et parties enterrées des pieux ne sont pas représentés.

Une implantation explicite reste possible ; passer `positions_platines=()`
désactive entièrement la trame automatique.

```python
atelier = creer_atelier_mob(
    positions_platines=((60, -3_440), (60, 0), (60, 3_440)),
)
```

## Statut du dimensionnement

Il s'agit d'un avant-projet paramétrique, pas d'un plan d'exécution. Les
charges réelles d'atelier (machines, stockage, cloisons), les murs, les
assemblages, le diaphragme, les vibrations, le feu, le fluage, le vent, le
soulèvement et la capacité du sol et des pieux doivent encore être vérifiés.
Les abaques STEICO doivent notamment être relus avec la catégorie d'usage et
les charges permanentes du projet.

À titre de contrôle de cohérence seulement, une demi-traverse modélisée comme
une poutre `120 × 240 mm` simplement appuyée sur `3 380 mm`, avec
`G = 0,60 kN/m²`, `Q = 2,50 kN/m²`, une largeur tributaire de `2,13 m` et les
modules exploratoires `E = 11 000 MPa`, `G = 690 MPa`, donne une flèche
instantanée `G + Q` d'environ `8,1 mm`, soit `L/417`. Ce calcul conservateur ne
vérifie ni la résistance de calcul Eurocode 5, ni les charges ponctuelles, ni
le fluage, ni l'appui central réel, ni le mur porté.

Documents produit de référence :

- [guide technique STEICOconstruction](https://www.steico.com/fileadmin/user_upload/importer/downloads/4028b6097384810e01749ff1e1ce608c/Guide_technique_STEICOconstruction_FR_i.pdf) ;
- [certificat ACERMI Isonat Flex 55](https://www.isonat.com/documents/certification-acermi/15-217-984-6-flex-55-0.pdf) ;
- [fiche Simpson Strong-Tie SAI-SAIL](https://pim.strongtie.eu/api/v1/public/download/fr/fr/product/40/SAI-SAIL.pdf).

## Pré-vérification automatique Eurocode 5

Le moteur de calcul `atelier_mob.dimensionnement` produit des vérifications
unitaires ELU/ELS et un taux d'utilisation pour chaque critère. La combinaison
ELU fondamentale utilisée par défaut est `1,35 Gk + 1,50 Qk`. Les flèches ELS
incluent la flexion et le cisaillement ; la flèche finale applique séparément
les coefficients de fluage de l'ETA STEICO.

```console
just atelier-mob-verification
```

La commande renvoie `0` pour une validation complète, `1` pour une
non-conformité calculée et `2` lorsqu'aucun calcul n'échoue mais que des données
ou contrôles manquent encore. Elle peut ainsi être utilisée dans une
vérification automatisée sans confondre « conforme » et « non vérifié ».

Hypothèses courantes :

- `Gk` calculé depuis chaque pièce, augmenté de `0,20 kN/m²` de finitions et
  réseaux rapportés, et `Qk = 2,50 kN/m²` ;
- classe de service 2, action variable de durée moyenne ;
- `γG = 1,35`, `γQ = 1,50`, `ψ2 = 0,80` ;
- limites de projet `L/300` instantanée et `L/250` finale ;
- bois primaire assimilé provisoirement à `fm,k = 24 MPa`, `fv,k = 3,5 MPa`
  et `fc,90,k = 2,5 MPa` avec `γM = 1,30` ;
- SJ60/240 : `Mk = 12,94 kN·m`, `Vk = 16,08 kN`,
  `EI = 709 kN·m²`, `GA = 3,18 MN` ;
- pour la SJ60/240 en classe 2 : `kmod = 0,80` en flexion mais seulement
  `0,45` en cisaillement ; `kdef = 0,80` en flexion et `3,00` en
  cisaillement.

### Masses et poids propres

Chaque élément CAO reçoit maintenant une masse installée. Les pièces identiques
sont regroupées dans `atelier.inventorier_masses()` avec quantité, masse
unitaire, masse totale, mode de calcul et masse linéique lorsqu'elle est
pertinente :

- madrier `120×240` : `14,40 kg/m`, calculé avec `500 kg/m³` ;
- STEICOjoist SJ60/240 : `4,12 kg/m`, valeur fabricant ;
- entretoises STEICOjoist : `4,12 kg/m`, comptées comme charge surfacique ;
- tasseau `60×40` : `1,20 kg/m` ;
- OSB : volume CAO × `600 kg/m³` ;
- Isonat : volume réellement posé × `55 kg/m³` ;
- SAI500/120/2 : `0,560 kg/pièce` ;
- EWH240/61 : `0,327 kg/pièce` ;
- vis et pointes : estimation par la tige cylindrique en acier, tête non
  comprise et signalée comme telle.

Le plancher installé représente environ `4 940,3 kg`, dont `1 210,3 kg` de
madriers primaires, `634,2 kg` de solives en I et `175,9 kg` d'entretoises.
Les couches et accessoires hors madriers et solives longitudinales donnent
`0,289 kN/m²`. Après ajout de `0,20 kN/m²` de charges rapportées, une solive
reçoit donc `0,489 kN/m²` plus son propre `4,12 kg/m`. Une traverse reçoit en
plus le poids des solives, soit `0,548 kN/m²`, puis son propre `14,40 kg/m`.
Cette séparation évite de compter deux fois le poids de la pièce en cours de
vérification.

Une valeur forfaitaire reste possible avec
`charge_permanente_surfacique_kN_m2=...`; elle remplace alors explicitement le
calcul détaillé.

### Résultats

Résultat de la configuration actuelle, avant charges de murs, toiture et
machines :

| Élément / critère | Taux | État |
|---|---:|---|
| Traverse 120×240 — flexion ELU | 81,6 % | conforme |
| Traverse 120×240 — cisaillement ELU | 39,8 % | conforme |
| Traverse — compression sur platine centrale | 89,1 % | conforme, proche limite |
| SAI500/120/2 — réaction verticale | 89,9 % | conforme, proche limite |
| Traverse — flèche instantanée | 70,6 % | conforme |
| Traverse — flèche finale avec fluage | 98,4 % | conforme, très proche limite |
| SJ60/240 — flexion ELU | 14,6 % | conforme |
| SJ60/240 — cisaillement ELU | 45,4 % | conforme |
| EWH240/61 — réaction verticale | 37,3 % | conforme |
| EWH opposés — non-croisement des pointes | 58,3 % | géométriquement conforme |
| EWH opposés — non-recouvrement des brides | 66,7 % | géométriquement conforme |
| SJ60/240 — flèche finale | 22,3 % | conforme |

Le rapport différencie deux notions :

- `conforme_calculs` indique qu'aucun critère effectivement calculé ne dépasse
  100 % ;
- `validation_automatique` exige en plus qu'aucun contrôle ne soit absent et
  qu'aucune réserve ne subsiste.

```python
from atelier_mob import HypothesesEurocode5, creer_atelier_mob

atelier = creer_atelier_mob()
rapport = atelier.verifier_structure(
    HypothesesEurocode5(
        charge_ponctuelle_solive_kN=4,
        charge_permanente_mur_toiture_kN_m=2,
        charge_variable_toiture_kN_m=1,
    )
)

for ligne in rapport.lignes_resume():
    print(ligne)
```

La validation complète reste volontairement bloquée tant que les charges des
murs/toiture et des machines, la DoP exacte du GT24, le sol et les pieux, les
ancrages, le diaphragme OSB, les vibrations, le feu, le vent, le soulèvement et
les percements des poutres en I ne sont pas traités. Une valeur absente n'est
jamais interprétée comme une charge nulle.

Références de calcul : [NF EN 1995-1-1 et son annexe nationale française en vigueur](https://www.boutique.afnor.org/fr-fr/norme/nf-en-199511-na/eurocode-5-conception-et-calcul-des-structures-en-bois-partie-11-generalite/fa163225/35259),
[supports pédagogiques officiels JRC sur l'EN 1995-1-1](https://eurocodes.jrc.ec.europa.eu/sites/default/files/2022-06/EN1995_2_Winter.pdf),
[ETA-20/0995 STEICO](https://www.steico.com/fileadmin/user_upload/importer/downloads/stegtrager_und_steico_lvl_zulassungen_und_sonstige_zertifikate/STEICO_approval_european-technical-assessment-20-0995_joist_wall_EUR_en.pdf)
et [fiche EWH Simpson Strong-Tie](https://pim.strongtie.eu/api/v1/public/download/be/fr/product/1672/EWH.pdf).

## Visualisation et calculateur de flèche

```console
just atelier-mob
just atelier-mob-fleche
just atelier-mob-verification
```

Le second outil reste un calculateur exploratoire pour une poutre rectangulaire
simplement appuyée. Il ne dimensionne ni les poutres en I, ni les traverses
continues sur les trois appuis, ni les assemblages.
