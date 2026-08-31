# Viewer Three.js — atelier MOB

Viewer web indépendant du modèle CAO `atelier_mob`. Les éléments sont exportés
en onze couches GLB activables séparément : fondations, poutres primaires,
connecteurs, solives en I, entretoises pleine hauteur, tasseaux, fonds OSB,
isolant, OSB supérieur et vide résiduel de l'enveloppe. Cette dernière couche
est calculée par soustraction de toute la CAO, rouge translucide, sans masse,
masquée au démarrage et accessible par le bouton **Vides structure**.
Le bouton **Éclaté** sépare verticalement ces sous-ensembles et recadre
automatiquement la caméra ; un second clic restitue l’assemblage normal.

## Lancer

Depuis la racine du dépôt :

```bash
just atelier-mob-viewer
```

Puis ouvrir <http://127.0.0.1:8080>. Le script régénère les fichiers GLB avant
de lancer le serveur. Arrêter avec `Ctrl+C`.

Three.js est chargé depuis jsDelivr avec la version `0.185.1` épinglée. Une
connexion réseau est donc nécessaire au chargement initial de la page ; les
modèles 3D restent locaux.

## Régénérer uniquement les modèles

```bash
just atelier-mob-viewer-export
```

Le manifeste `public/models/manifest.json` contient les dimensions du projet,
les couleurs, les quantités et les masses par couche. Les masses du plancher
proviennent directement de `atelier_mob.masses`; les fixations, sans solide
CAO, sont incluses dans le total du plancher mais pas dans une couche visible.
Il contient également le volume de l'enveloppe analysée, le volume vide, son
taux et le nombre de composantes connexes. Ces métriques constituent un
pré-diagnostic géométrique et non un calcul de coefficient linéique `ψ` selon
l'ISO 10211.
