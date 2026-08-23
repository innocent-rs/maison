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
centre du châssis sur quatre appuis d'angle. Il compare une section pleine avec
liaisons rigides, des connecteurs articulés idéalisés et les sections réduites
des mi-bois :

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

- une largeur intérieure de `6 000 mm` ;
- un angle de toiture de `60°` ;
- une cible théorique de `20,5 m²` au-dessus de `1 800 mm` ;
- une longueur calculée d'environ `5 228 mm` ;
- une hauteur théorique au faîtage d'environ `5 196 mm` ;
- cinq madriers de section provisoire identique `120 × 250 mm` ;
- deux poutres longitudinales et trois traverses coplanaires ;
- six assemblages à mi-bois, profonds de `125 mm` dans chaque pièce ;
- des entailles ouvertes par le dessus des poutres permettant de descendre les
  traverses verticalement après la pose des deux côtés.

La cible de `20,5 m²` conserve une petite marge avant l'ajout des doublages,
cloisons et de la trémie. Les sections indiquées sont des hypothèses de
conception et devront faire l'objet d'un calcul structurel avant construction.
Ce châssis de cinq poutres n'est pas un plancher fini : les solives secondaires
en I sont des `STEICOjoist SJ90/360` modélisées avec des membrures de
`90 × 45 mm` et une âme de `8 mm`. Onze solives longitudinales reposent sur les
trois traverses primaires, avec un entraxe réparti de `490 mm` (maximum demandé :
`500 mm`). Elles sont temporairement exclues du modèle et de la BOM avec
`inclure_solives_i=False`. Les dalles OSB seront ajoutées dans une prochaine
étape.
