# maison-codex

Petit projet Python de CAO paramétrique avec
[build123d](https://build123d.readthedocs.io/) et visualisation dans Firefox via
le serveur web autonome de `ocp_vscode`.

## Démarrage sous NixOS

1. Entrer dans l'environnement (les dépendances Python sont synchronisées
   automatiquement depuis `uv.lock`) :

   ```console
   nix develop
   ```

2. Lancer le serveur en arrière-plan :

   ```console
   just server
   ```

   L'option `--tree_width 240` est nécessaire avec `ocp-vscode 2.9.0` : sans
   elle, cette version produit une valeur JavaScript invalide et le navigateur
   n'affiche qu'une page blanche.

3. Ouvrir <http://127.0.0.1:3939/viewer> dans Firefox.

4. Envoyer le modèle au serveur :

   ```console
   just run
   ```

5. Arrêter le serveur :

   ```console
   just kill
   ```

Avec `direnv`, exécuter une fois `direnv allow` pour entrer automatiquement
dans le shell Nix à l'ouverture du dossier.

Dans le shell Nix, le virtualenv `.venv` est automatiquement synchronisé puis
activé. Le fichier `uv.lock` fixe les versions Python, tandis que `flake.lock`
fixe les dépendances Nix.

Les sorties du serveur sont conservées dans `.ocp-vscode.log`.

### Simulation du plancher fini

Le modèle OpenSeesPy représente les deux poutres de rive, les trois traverses
et les douze segments de STEICOjoist. Les SJ60/240 utilisent directement les
rigidités moyennes du [guide technique STEICO](https://www.steico.com/fileadmin/user_upload/importer/downloads/4028b609775e65ec0177d608769c2bda/Guide_technique_STEICOconstruction_FR_i.pdf)
(`EI = 709 kN·m²`, `GA = 3,18 MN`) dans des éléments de poutre de Timoshenko ;
leurs abouts dans les EWH sont articulés.
Deux bornes restent comparées pour les liaisons SAI entre traverses et poutres
de rive : parfaitement rigides ou articulées.

Les charges sont désormais réparties par largeur tributaire. Le cas `G`
comprend les poids propres des éléments porteurs et des couches réellement
actives : OSB inférieur `12 mm`, Isonat `145 mm` et OSB supérieur `22 mm`.
Le cas `Q` utilise par défaut une hypothèse modifiable de `1,5 kN/m²`, et le cas
`G+Q` les additionne sans pondération. Cette valeur est une hypothèse de travail
à confirmer avec la catégorie d'usage et l'annexe nationale applicables ; une
charge permanente rapportée peut être ajoutée pour les cloisons et finitions.

```console
just simulate
```

Les six résultats sont écrits dans `build/simulation/resultats.csv`. Le rapport
distingue la flèche globale, la flèche propre des poutres de rive, celle des
traverses et celle des solives, avec un repère indicatif `L/300`, ainsi que la
réaction maximale et l'équilibre total des quatre appuis.

Avec le plancher courant, `G = 0,27836 kN/m²` pour les couches et le poids de la
structure modélisée vaut `3,837 kN`. Sous `G+Q`, la charge totale est
`37,981 kN`. Dans la borne articulée, les résultats sont : poutres de rive
`13,68 / 15,59 mm`, traverses `8,47 / 12,52 mm` et SJ60/240
`0,81 / 7,37 mm`. La flèche verticale cumulée au point le plus bas atteint
`22,15 mm` : même si les trois contrôles relatifs restent sous le repère
indicatif, ce déplacement global mérite d'être examiné avant de figer les
appuis et le critère de confort.

L'OSB distribue les charges mais sa rigidité de diaphragme ou son éventuel
effet composite n'est pas crédité. Les déformations différées, vibrations,
charges concentrées réglementaires, efforts et résistances des assemblages,
stabilité, feu et combinaisons ELU ne sont pas encore vérifiés. Ce modèle
linéaire reste donc un outil de conception ; il ne remplace pas une note de
calcul établie ou validée par un ingénieur structure.

### Nomenclature et chiffrage

La nomenclature regroupe automatiquement les pièces identiques et exporte les
quantités, dimensions, longueurs et volumes cumulés :

```console
just bom
```

Le résultat est écrit dans `build/bom.csv` avec un séparateur `;`, adapté aux
tableurs en environnement français. Chaque nouvelle famille de pièces doit
implémenter `article_bom()` ; elle est ensuite agrégée sans modifier l'exporteur.

### Chiffrage par lot

Les tarifs TTC sont maintenus directement en Python dans
`maison/prix.py`. Un tarif représente toujours une unité réellement achetée :
une barre complète, une pièce, une boîte ou un lot minimal exprimé en mètres
linéaires. Il n'existe pas de facturation de la seule longueur utile.

Pour regrouper plusieurs coupes dans un même produit commercial, les références
BOM concernées partagent une instance de `Tarif.en_barres` :

```python
TARIF_DOUGLAS = Tarif.en_barres(
    "693.23",                     # prix TTC de la barre entière
    reference_achat="DOUGLAS-GT24-120x240-L13500",
    designation_achat="Douglas contrecollé 120 × 240 — L 13 500 mm",
    longueur_commerciale_mm=13_500,
    trait_scie_mm=5,
)

TARIFS = {
    "MAD-120x240-L3756": TARIF_DOUGLAS,
    "MAD-120x240-L4800": TARIF_DOUGLAS,
}
```

L'optimiseur minimise exactement le nombre de barres, inclut le trait de scie
entre les pièces et multiplie le prix de la barre par la quantité entière à
commander. Le prix linéaire éventuellement affiché par le vendeur doit donc
être converti en prix de barre dans la base locale.

Pour un article vendu à la pièce :

```python
"SIMPSON-EWH240-61": Tarif.par_conditionnement(
    "12.90",
    quantite=1,
    conditionnement="pièce",
    fournisseur="Fournisseur à renseigner",
    date_tarif="2026-08-23",
    url="https://...",
)
```

Enfin, pour une boîte de vis :

```python
"SIMPSON-CSA5.0X40": Tarif.par_conditionnement(
    "89.90",                         # prix TTC de la boîte complète
    quantite=250,
    conditionnement="boîte de 250",
    fournisseur="Fournisseur à renseigner",
)
```

Avec `300` CSA dans des boîtes de `250`, le calcul achète deux boîtes. L'arrondi
se fait toujours au conditionnement supérieur.

Lorsqu'un fournisseur impose un minimum en mètres linéaires sans publier les
longueurs unitaires livrées, utiliser un lot linéaire plutôt que d'inventer des
barres de stock :

```python
"TAS-60x40-L2212": Tarif.en_lots_lineaires(
    "182.00",                         # 20 ml × 9,10 € TTC/ml
    longueur_du_lot_mm=20_000,
    conditionnement="commande minimale de 20 ml",
    fournisseur="Matériaux Naturels",
)
```

Les quatre tasseaux actifs demandent `8,848 ml`, mais le chiffrage achète donc
un lot de `20 ml` à `182,00 € TTC` et expose `11,152 ml` de surplus. Si le
besoin dépasse `20 ml`, le nombre de lots est automatiquement arrondi au-dessus.

Générer les trois chiffrages :

```console
just chiffrage
```

Ou un seul sous-ensemble :

```console
just chiffrage plancher
just chiffrage charpente
just chiffrage total
```

`a-frame` est accepté comme alias de `charpente`. Les fichiers sont écrits dans
`build/chiffrage_<lot>.csv`. Une ligne sans prix conserve un coût vide et le
résultat porte le statut `INCOMPLET` ; le sous-total affiché ne comprend que les
lignes renseignées. Pour faire échouer une automatisation en présence d'un prix
manquant, lancer `python chiffrer.py --lot total --strict`.

Le CSV distingue la longueur utile de la BOM, la longueur de l'unité d'achat et
la longueur réellement achetée. Le chiffrage actif du plancher est actuellement
complet et vaut `3 448,50 € TTC` avec les tarifs datés du `2026-08-23`.

Afficher et exporter séparément le plan de débit :

```console
just optimiser plancher
```

Le détail d'une barre par ligne est écrit dans `build/debit_<lot>.csv`, avec les
coupes, les traits de scie, la chute restante et le rendement matière.

La BOM principale reste une nomenclature de fabrication et contient donc les
découpes. Le chiffrage regroupe les références débitées qui partagent un même
produit commercial. Les madriers et les poutres en I sont ainsi optimisés
séparément dans leurs barres respectives.

## Modèle structurel

Les dimensions du modèle sont exprimées en millimètres. Les pièces de bois
réutilisables se trouvent dans `maison/structure/bois.py`. Le premier composant
est un `Madrier` en Douglas contrecollé de section `120 × 240 mm` et de longueur
paramétrable :

```python
from maison.structure import Madrier

madrier = Madrier(longueur=4_000)
forme = madrier.construire()
```

La convention d'axes est `X = longueur`, `Y = largeur`, `Z = hauteur`. L'origine
du madrier est placée sous sa face de départ et au milieu de sa largeur.

Les panneaux OSB portent explicitement leur type de bords dans la BOM : `BD`
pour les bords droits et `RL` pour les panneaux rainurés-languettés. Par
défaut, la dalle paramétrique de `675 × 2500 mm` est une dalle RL :

```python
from maison.structure import DalleOSB

dalle = DalleOSB(epaisseur=22)
forme = dalle.construire()
```

Chaque format, épaisseur et type de bords possède une référence BOM distincte,
par exemple `OSB-RL-675x2500x22`. Les fonds de caisson utilisent le produit
commercial OSB 3 BD de `12 × 2800 × 1196 mm`, référencé
`OSB-BD-1196x2800x12`.

### Base actuelle du A-frame

Le prototype technique utilise une emprise hors-tout de `4 000 × 4 800 mm`,
soit `19,20 m²`, et conserve une pente de `60°`. La zone théorique au-dessus de
`1 800 mm` représente environ `9,22 m²`. Ces valeurs restent des paramètres de
CAO et non une qualification réglementaire de la surface.

La configuration active contient les cinq poutres porteuses : deux
longitudinales de `4 800 mm` et trois traverses de `3 756 mm`, toutes en section
`120 × 240 mm`, en Douglas contrecollé GT24. Les axes des traverses sont `62`,
`2 400` et `4 738 mm`. Les `4 mm` retranchés aux traverses correspondent aux
deux tôles de `2 mm` interposées à leurs abouts.

Chaque traverse est suspendue par deux sabots Simpson SAI500/120/2, soit six
sabots. Le plan de fixation total utilise `32` CSA5.0X40 côté porteur et `18`
côté poutre portée par sabot : `300` vis, achetées dans deux boîtes de `250`.
Six lignes de STEICOjoist SJ60/240 relient les trois traverses : douze segments
de `2 212 mm`, espacés de `538,286 mm`. Chaque segment reçoit deux EWH240/61,
soit vingt-quatre étriers et `384` pointes CNA4.0X35. Leur débit nécessite trois
poutres commerciales entières de `13 m`.

Les quatorze fonds de caisson actifs sont en OSB 3 BD de `12 mm` et mesurent
`527,286 × 2212 mm` avec un jeu latéral total de `3 mm`. Dix panneaux
intérieurs sont encochés autour des EWH et quatre panneaux de rive restent
rectangulaires. Quatre lambourdes de rive Douglas rabotées et séchées
`60 × 40 × 2212 mm`, descendues de `1 mm`, complètent leurs appuis au niveau
des membrures STEICO réelles de `60 × 39 mm`. Elles sont fixées aux madriers
par `32` vis structurelles Klimas `6 × 160 mm`. La fixation des fonds utilise
`420` SPAX `0191010400355` à filetage partiel, achetées dans une boîte de
`1 000`.

Deux découpes entrent dans chaque panneau commercial BD de
`12 × 2800 × 1196 mm` : le chiffrage achète donc sept panneaux entiers.

Les quatorze caissons de `150 × 530,286 × 2218 mm` reçoivent de l'[Isonat Flex
55 Contact](https://www.materiaux-naturels.fr/produit/437-isonat-flex-55-plus-h-panneau-laine-de-bois)
de `145 mm` (R nominal `4,03 m².K/W`). Cette épaisseur laisse `5 mm` dans la
hauteur libre sans comprimer verticalement le panneau ; la variante de `160 mm`
aurait dû être écrasée de `10 mm`. Chaque caisson reçoit deux segments posés de
`145 × 530,286 × 1109 mm`, débités avec une surcote de maintien de `10 mm` en
largeur et en longueur. Il faut donc vingt-huit panneaux bruts
`145 × 580 × 1220 mm`, soit sept colis de quatre. Au tarif promotionnel daté du
`2026-08-23`, l'isolant ajoute `339,36 € TTC`.

Le plancher supérieur actif est en OSB 3 rainuré-languetté de `22 mm`, au niveau
`Z = 240–262 mm`. Les dalles commerciales `675 × 2500 mm` sont orientées avec
leur longueur suivant X. Deux portées de `2400 mm` se rejoignent exactement sur
la traverse centrale à `X = 2400 mm` ; la rainure et la languette de cette rive
peuvent ainsi être conservées en recoupant les `100 mm` aux extrémités libres.

Suivant Y, les six solives en I définissent sept bandes : deux bandes de rive de
`654,286 mm` et cinq bandes intérieures de `538,286 mm`. Les rives découpées de
chaque bande sont centrées sur les membrures de `60 mm`. Les quatorze panneaux
posés ont donc tous leurs joints intérieurs sur une traverse ou une solive :
aucun raccord ne reste au-dessus du vide. Le calepinage achète quatorze dalles
brutes à `27,51 € TTC`, soit `385,14 € TTC`, et prévoit `568` vis Klimas
`5 × 60 mm`, achetées dans trois boîtes de `200` pour `32,40 € TTC`.

La BOM d'achat active contient quatorze références : bois primaire, poutres en
I, connecteurs Simpson, tasseaux, OSB BD, OSB RL, isolant et visserie. Seuls les
éléments de charpente restent désactivés.

La géométrie CAO des connecteurs représente leur enveloppe utile sans détailler
les trous. Les fixations d'exécution devront suivre les plans certifiés des
fabricants. Les sections, les assemblages et la zone de batteries devront être
validés à partir des masses réelles et des cas de charge du local technique.

### Fermes en A — désactivées

La charpente comprend dix couples d'arbalétriers espacés de `500 mm` suivant la
longueur. Leurs axes vont de `150` à `4650 mm`, avec un retrait symétrique de
`150 mm` aux deux extrémités.

Les vingt arbalétriers provisoires ont une section de `120 × 250 mm`, une
longueur d'axe de `3880 mm` et une longueur minimale de débit d'environ
`4127 mm`. Le centre de la coupe de faîtage atteint `Z ≈ 3610 mm` et sa pointe
haute `Z ≈ 3860 mm`.

La coupe de pied comporte une face verticale au nu extérieur du plancher, une
assise horizontale de `120 mm` alignée au-dessus de la poutre de rive et un
relief intérieur de `2 mm`. Les triangles restent ainsi dans l'enveloppe
`Y = ±2000 mm`. Les réservations du plancher établissent le contact bois-bois
direct avec les poutres de rive, au niveau d'appui `Z = 250 mm`.

L'assise forme `60°` avec l'axe du bois, soit un écart de `30°` par rapport à
une coupe d'équerre. La coupe de faîtage est verticale et forme `30°` avec
l'axe, soit `60°` par rapport à l'équerre. Les deux faces supérieures portent
ainsi l'une contre l'autre ; les futures plaques d'acier assureront notamment
leur maintien latéral. L'assemblage de pied reste à valider sous poussée
horizontale et soulèvement.

Chaque ferme peut recevoir deux ferrures de pied à deux joues
et un tirant transversal sous plancher. La BOM contient donc vingt ferrures de
principe et dix kits de tirant provisoires `M16 × 4000 mm`. Les ferrures
représentent uniquement une enveloppe inspirée du principe PCAB ; leurs
épaisseurs, perçages, ancrages, fixations et résistances ne constituent pas un
plan d'exécution et devront être déterminés après le calcul des efforts de pied.
Leurs retours descendent sous les poutres de rive jusqu'à l'axe `Z = -30 mm`
du tirant, avec `20 mm` de matière de principe sous le perçage.

Le futur OSB posé sur les versants formera le contreventement dans la longueur
et stabilisera les fermes entre elles, à condition de définir le calepinage, les
jonctions de panneaux et le plan de clouage. Il ne remplace pas les tirants :
ceux-ci ferment chaque triangle et reprennent la poussée qui tend à écarter les
deux pieds. Les plaques de faîtage et ce diaphragme de toiture seront ajoutés
dans une étape suivante.
