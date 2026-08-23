"""Pièces structurelles en bois.

Toutes les dimensions sont exprimées en millimètres. Par convention, une
pièce longitudinale est orientée ainsi :

- X : longueur ;
- Y : largeur ;
- Z : hauteur.
"""

from dataclasses import dataclass

from build123d import Align, Box, Part, Pos

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


@dataclass(frozen=True, slots=True)
class Tasseau:
    """Tasseau rectangulaire, orienté selon la convention générale XYZ."""

    longueur: float
    largeur: float = 90.0
    hauteur: float = 45.0
    materiau: str = "Bois massif structurel (classe à définir)"

    def __post_init__(self) -> None:
        if min(self.longueur, self.largeur, self.hauteur) <= 0:
            raise ValueError("les dimensions du tasseau doivent être positives")

    def construire(self) -> Part:
        return Box(
            self.longueur,
            self.largeur,
            self.hauteur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    @property
    def designation(self) -> str:
        return (
            f"Tasseau {self.largeur:g} × {self.hauteur:g} mm"
            f" — L {self.longueur:g} mm"
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"TAS-{self.largeur:g}x{self.hauteur:g}-L{self.longueur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=self.designation,
            categorie="Bois / tasseau",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            volume_mm3=self.longueur * self.largeur * self.hauteur,
        )


@dataclass(frozen=True, slots=True)
class PoutreI:
    """Poutre en I de type STEICOjoist SJ90/360.

    La géométrie utilise deux membrures de 90 × 45 mm et une âme centrée de
    8 mm. Les dimensions restent paramétrables pour de futures variantes.
    """

    longueur: float
    hauteur: float = 360.0
    largeur_membrure: float = 90.0
    hauteur_membrure: float = 45.0
    epaisseur_ame: float = 8.0
    modele: str = "STEICOjoist SJ90/360"
    materiau: str = "Membrures bois/LVL et âme en fibre de bois"

    def __post_init__(self) -> None:
        dimensions = (
            self.longueur,
            self.hauteur,
            self.largeur_membrure,
            self.hauteur_membrure,
            self.epaisseur_ame,
        )
        if min(dimensions) <= 0:
            raise ValueError("les dimensions de la poutre en I doivent être positives")
        if 2 * self.hauteur_membrure >= self.hauteur:
            raise ValueError("les membrures ne laissent aucune hauteur pour l'âme")
        if self.epaisseur_ame > self.largeur_membrure:
            raise ValueError("l'âme ne peut pas être plus large que les membrures")

    @property
    def hauteur_ame(self) -> float:
        return self.hauteur - 2 * self.hauteur_membrure

    def construire(self) -> Part:
        """Construit la section en I extrudée suivant l'axe X."""
        alignement = (Align.MIN, Align.CENTER, Align.MIN)
        membrure_basse = Box(
            self.longueur,
            self.largeur_membrure,
            self.hauteur_membrure,
            align=alignement,
        )
        ame = Pos(0, 0, self.hauteur_membrure) * Box(
            self.longueur,
            self.epaisseur_ame,
            self.hauteur_ame,
            align=alignement,
        )
        membrure_haute = Pos(0, 0, self.hauteur - self.hauteur_membrure) * Box(
            self.longueur,
            self.largeur_membrure,
            self.hauteur_membrure,
            align=alignement,
        )
        return membrure_basse + ame + membrure_haute

    @property
    def designation(self) -> str:
        return f"Poutre en I {self.modele} — L {self.longueur:g} mm"

    @property
    def volume_mm3(self) -> float:
        section_membrures = (
            2 * self.largeur_membrure * self.hauteur_membrure
        )
        section_ame = self.epaisseur_ame * self.hauteur_ame
        return self.longueur * (section_membrures + section_ame)

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
        reference=(
            f"SJI-{self.largeur_membrure:g}x{self.hauteur:g}-L{self.longueur:g}"
        ).replace(".", "_"),
            designation=self.designation,
            categorie="Bois / poutre en I",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur_membrure,
            hauteur_mm=self.hauteur,
            volume_mm3=self.volume_mm3,
        )
