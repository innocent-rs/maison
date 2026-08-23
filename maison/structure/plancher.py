"""Structure paramétrique du plancher du A-frame."""

from dataclasses import dataclass
from math import ceil

from build123d import Part, Pos, Rot

from maison.geometrie import GeometrieAFrame
from maison.structure.bois import Madrier


@dataclass(frozen=True, slots=True)
class ElementPlancher:
    nom: str
    piece: Madrier
    forme: Part
    couleur: str

    def article_bom(self):
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class PlancherAFrame:
    """Deux poutres de rive longitudinales reliées par des solives.

    Il s'agit d'une géométrie de conception, pas encore d'un dimensionnement
    structurel. Les sections devront être validées selon les portées, charges,
    assemblages et la classe du bois.
    """

    geometrie: GeometrieAFrame
    section_largeur: float = 120.0
    section_hauteur: float = 250.0
    entraxe_max: float = 600.0

    def __post_init__(self) -> None:
        if min(self.section_largeur, self.section_hauteur, self.entraxe_max) <= 0:
            raise ValueError("sections et entraxe doivent être strictement positifs")
        if self.geometrie.largeur_interieure <= 2 * self.section_largeur:
            raise ValueError("la largeur est insuffisante pour les poutres de rive")

    @property
    def nombre_solives(self) -> int:
        longueur_utile = self.geometrie.longueur_interieure - self.section_largeur
        return ceil(longueur_utile / self.entraxe_max) + 1

    @property
    def entraxe_reel(self) -> float:
        if self.nombre_solives == 1:
            return 0.0
        return (
            self.geometrie.longueur_interieure - self.section_largeur
        ) / (self.nombre_solives - 1)

    def elements(self) -> list[ElementPlancher]:
        largeur = self.geometrie.largeur_interieure
        longueur = self.geometrie.longueur_interieure
        demi_section = self.section_largeur / 2

        poutre_piece = Madrier(
            longueur=longueur,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        poutre = poutre_piece.construire()
        elements = [
            ElementPlancher(
                "Poutre longitudinale gauche",
                poutre_piece,
                Pos(0, -largeur / 2 + demi_section, 0) * poutre,
                "saddlebrown",
            ),
            ElementPlancher(
                "Poutre longitudinale droite",
                poutre_piece,
                Pos(0, largeur / 2 - demi_section, 0) * poutre,
                "saddlebrown",
            ),
        ]

        portee_solive = largeur - 2 * self.section_largeur
        solive_piece = Madrier(
            longueur=portee_solive,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        solive = solive_piece.construire()
        depart_y = -largeur / 2 + self.section_largeur

        for index in range(self.nombre_solives):
            x = demi_section + index * self.entraxe_reel
            forme = Pos(x, depart_y, 0) * Rot(0, 0, 90) * solive
            elements.append(
                ElementPlancher(
                    f"Solive {index + 1:02d}",
                    solive_piece,
                    forme,
                    "burlywood",
                )
            )

        return elements

    def nomenclature(self):
        """Construit la nomenclature agrégée du plancher."""
        from maison.nomenclature import Nomenclature

        return Nomenclature(self.elements())
