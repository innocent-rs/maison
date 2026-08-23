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

## Modèle structurel

Les dimensions du modèle sont exprimées en millimètres. Les pièces de bois
réutilisables se trouvent dans `maison/structure/bois.py`. Le premier composant
est un `Madrier` de section `120 × 250 mm` et de longueur paramétrable :

```python
from maison.structure import Madrier

madrier = Madrier(longueur=4_000)
forme = madrier.construire()
```

La convention d'axes est `X = longueur`, `Y = largeur`, `Z = hauteur`. L'origine
du madrier est placée sous sa face de départ et au milieu de sa largeur.

Les dalles OSB de `675 × 2500 mm` sont disponibles en `12`, `15`, `18` et
`22 mm` :

```python
from maison.structure import DalleOSB

dalle = DalleOSB(epaisseur=22)
forme = dalle.construire()
```

Chaque épaisseur possède une référence BOM distincte, par exemple
`OSB-675x2500x22`.

### Base actuelle du A-frame

Le modèle de départ utilise :

- une largeur hors-tout de plancher de `7 108 mm` ;
- un angle de toiture de `60°` ;
- une emprise totale de plancher plafonnée à `20,0 m²`, poutres comprises ;
- une longueur modulaire imposée de `2 804 mm` ;
- une emprise réelle de `19,93 m²` ;
- une surface théorique d'environ `14,10 m²` au-dessus de `1 800 mm` ;
- une hauteur théorique au faîtage d'environ `6 156 mm` ;
- cinq madriers de section provisoire identique `120 × 250 mm` ;
- deux poutres longitudinales et trois traverses coplanaires ;
- trois traverses de `6 864 mm`, soit les `6 868 mm` entre faces moins les
  deux ailes de sabot de `2 mm` interposées aux abouts ;
- aucune entaille dans les cinq madriers ;
- six sabots Simpson Strong-Tie `SAI500/120/2` à ailes intérieures, un à
  chaque about de traverse ;
- un plan de fixation total de `50` vis de connecteur `CSA5.0X40` par sabot,
  soit `300` vis dans la nomenclature ;
- aucune vis SWWZ traversante dans l'interface, afin de ne pas percer ou
  contourner arbitrairement les tôles des sabots.

La cible Carrez initiale de `20,5 m²` est conservée comme paramètre, mais le
plafond de `20,0 m²` et la trame sans découpe de l'isolant sont prioritaires.
Les dimensions `7 108 × 2 804 mm` découlent des modules de
`575 × 1 220 mm` et laissent une marge d'environ `0,07 m²`. Les sections
indiquées sont des hypothèses de conception et devront faire l'objet d'un calcul
structurel avant construction.
Ce châssis de cinq poutres n'est pas un plancher fini : les solives secondaires
en I sont des `STEICOjoist SJ90/220` modélisées avec des membrures de
`90 × 45 mm` et une âme de `8 mm`. Elles sont orientées longitudinalement et
relient successivement les traverses haute–milieu puis milieu–basse. Onze lignes
de solivage sont réparties sur la largeur avec un entraxe de `573 mm`. Chaque
ligne comporte deux segments : le modèle compte donc vingt-deux STEICOjoist de
`1 214 mm`. Leur face supérieure affleure celle
des cinq madriers primaires. Avec une hauteur de `220 mm`, leur dessous reste
`30 mm` au-dessus de celui des madriers de `250 mm`.

Un jeu de pose de `3 mm` est conservé entre chaque about de solive et la face
de la traverse. Les poutres en I ne pénètrent donc pas dans les madriers ; les
joues de l'étrier recouvrent volontairement les premiers `80 mm` de la solive.

Chaque segment de STEICOjoist est suspendu par deux étriers Simpson Strong-Tie
`EWH219/91`, soit quarante-quatre étriers. Le montage modélisé utilise les brides
supérieures et le plan standard Simpson : huit pointes en face du porteur,
quatre sur son dessus et quatre dans la poutre portée. La BOM contient donc
`704` pointes annelées `CNA4.0X35`. Les solives et leurs étriers sont activés
dans le modèle courant avec `inclure_solives_i=True`.

Les vingt caissons intérieurs, entre deux lignes de STEICOjoist, sont fermés par
des découpes d'OSB 3 de `12 mm` posées par-dessus les membrures basses. Chaque
fond mesure `562 × 1214 mm`, conserve un jeu total de `3 mm` entre les
deux âmes et reçoit quatre encoches de `82 × 47 mm` autour des EWH. Il est vissé
vers le bas dans les deux membrures par deux rangées de huit vis `4 × 35 mm`.
Les quatre panneaux de rive ont les mêmes dimensions `562 × 1214 mm`. Ils
restent rectangulaires, sans découpe dans les angles,
puisque les sabots ne gênent pas leur pose. Le plancher compte ainsi
vingt-quatre panneaux et `384` vis `4 × 35 mm` dans sa configuration actuelle.
Deux découpes tiennent dans une dalle brute de `675 × 2500 mm` ; il faut donc
douze dalles pour cette zone. Quatre tasseaux de rive
`90 × 45 × 1214 mm` — la même section que les membrures des poutres en I —
sont fixés contre les faces intérieures des poutres longitudinales. Leur dessus
est aligné à `75 mm` avec celui des membrures basses afin de porter les fonds
des quatre caissons de rive.

Chaque caisson reçoit un panneau entier de STEICOflex 036 nominalement
`120 × 575 × 1220 mm`. Le panneau flexible est représenté posé à
`118 × 565 × 1220 mm` : `10 mm` de compression latérale et `2 mm` en hauteur,
sans découpe. Les vingt-quatre panneaux figurent dans la BOM. Les petits
recouvrements avec les tôles de `0,9 mm` des EWH représentent la déformation
locale de l'isolant souple autour des étriers, pas une découpe.

La géométrie CAO des sabots représente leur enveloppe utile — assise, joues et
ailes intérieures — sans reproduire leurs trous. Pour l'exécution, le placement
des fixations doit impérativement suivre le plan certifié Simpson de la
référence `SAI500/120/2`. Le plan partiel reste paramétrable avec
`plan_fixation_sai=PlanFixationSAI.PARTIEL`, mais le modèle courant retient le
plan total.
