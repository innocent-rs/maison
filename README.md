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

### Simulation comparative

Le premier modèle OpenSeesPy applique une charge ponctuelle de `1 000 N` au
centre du châssis sur quatre appuis d'angle. Il compare une borne parfaitement
rigide avec l'idéalisation articulée retenue pour les sabots SAI :

```console
just simulate
```

Les résultats sont écrits dans `build/simulation/resultats.csv`. Ce modèle
linéaire sert à comparer les concepts ; il ne remplace pas une note de calcul.

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
une barre complète, une pièce ou une boîte. Il n'existe pas de facturation de
la seule longueur utile.

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
rectangulaires. Quatre tasseaux de rive `60 × 45 × 2212 mm` complètent leurs
appuis. La fixation utilise `420` vis `4 × 35 mm`.

Deux découpes entrent dans chaque panneau commercial BD de
`12 × 2800 × 1196 mm` : le chiffrage achète donc sept panneaux entiers. La BOM
d'achat active contient dix références : bois primaire, poutres en I,
connecteurs Simpson, tasseaux, OSB BD et visserie. L'isolant, le plancher OSB
supérieur et les éléments de charpente restent désactivés.

### Configuration complète conservée mais désactivée

Les composants suivants restent paramétriques et testés dans le dépôt, mais ne
sont plus instanciés par `main.make_part()` et ne participent pas au chiffrage.

L'isolation emploie vingt-huit panneaux bruts STEICOflex 036
`145 × 575 × 1220 mm`, recoupés à environ `138 × 530,286 × 1049 mm` pour la
pose. La compression verticale de principe est donc de `7 mm`. Le changement
d'emprise abandonne volontairement l'ancien objectif de panneaux isolants sans
découpe.

Le plancher supérieur reste en OSB 3 rainuré-languetté de `22 mm`, au niveau
fini `Z = 272 mm`. Son calepinage comporte sept bandes de `675 mm` et une bande
de rive de `75 mm`, avec des joints courts alternés sur les deux poutres en I
centrales. Il comprend seize découpes, budgétées dans quinze dalles brutes
`675 × 2500 mm`, et `422` vis `5 × 60 mm`. Vingt réservations
`120 × 120 mm`, deux par ferme, dégagent maintenant les poutres de rive afin
que les pieds d'arbalétrier portent directement sur le bois et non sur l'OSB.

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
