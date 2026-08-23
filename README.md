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

### Base actuelle du A-frame

Le modèle de départ utilise :

- une largeur intérieure de `6 000 mm` ;
- un angle de toiture de `60°` ;
- une cible théorique de `20,5 m²` au-dessus de `1 800 mm` ;
- une longueur calculée d'environ `5 228 mm` ;
- une hauteur théorique au faîtage d'environ `5 196 mm` ;
- deux poutres longitudinales de section provisoire `120 × 250 mm` ;
- dix solives transversales de même section, espacées d'environ `568 mm`.

La cible de `20,5 m²` conserve une petite marge avant l'ajout des doublages,
cloisons et de la trémie. Les sections indiquées sont des hypothèses de
conception et devront faire l'objet d'un calcul structurel avant construction.
