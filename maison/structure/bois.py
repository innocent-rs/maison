"""Pièces structurelles en bois.

Toutes les dimensions sont exprimées en millimètres. Par convention, une
pièce longitudinale est orientée ainsi :

- X : longueur ;
- Y : largeur ;
- Z : hauteur.
"""

from dataclasses import dataclass

from build123d import Align, Box, Part

from maison.nomenclature import ArticleBOM


@dataclass(frozen=True, slots=True)
class Madrier:
    """Madrier rectangulaire paramétrique, de section 120 × 250 mm par défaut.

    L'origine se trouve au milieu de la largeur, sur la face de départ et sous
    la pièce. Cette convention simplifie le placement des éléments du plancher.
    """

    longueur: float
    largeur: float = 120.0
    hauteur: float = 250.0
    materiau: str = "Bois massif structurel (classe à définir)"

    def __post_init__(self) -> None:
        for nom, valeur in (
            ("longueur", self.longueur),
            ("largeur", self.largeur),
            ("hauteur", self.hauteur),
        ):
            if valeur <= 0:
                raise ValueError(f"{nom} doit être strictement positif")

    def construire(self) -> Part:
        """Construit et renvoie la géométrie build123d du madrier."""
        return Box(
            self.longueur,
            self.largeur,
            self.hauteur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    @property
    def designation(self) -> str:
        """Désignation lisible avec section et longueur."""
        return (
            f"Madrier {self.largeur:g} × {self.hauteur:g} mm"
            f" — L {self.longueur:g} mm"
        )

    def article_bom(self) -> ArticleBOM:
        """Décrit cette coupe de bois pour la nomenclature."""
        reference = (
            f"MAD-{self.largeur:g}x{self.hauteur:g}-L{self.longueur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=self.designation,
            categorie="Bois / madrier",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            volume_mm3=self.longueur * self.largeur * self.hauteur,
        )
