"""Structure paramétrique du plancher du A-frame."""

from dataclasses import dataclass
from math import ceil
from build123d import Align, Box, Part, Pos, Rot

from maison.geometrie import GeometrieAFrame
from maison.nomenclature import Nomenclaturable
from maison.structure.bois import Madrier, PoutreI


@dataclass(frozen=True, slots=True)
class ElementPlancher:
    nom: str
    piece: Nomenclaturable
    forme: Part
    couleur: str

    def article_bom(self):
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class PlancherAFrame:
    """Châssis primaire : deux poutres longitudinales et trois traverses.

    Il s'agit d'une géométrie de conception, pas encore d'un dimensionnement
    structurel. Les sections devront être validées selon les portées, charges,
    assemblages et la classe du bois. Les futures solives en I formeront une
    couche secondaire distincte entre les traverses.
    """

    geometrie: GeometrieAFrame
    section_largeur: float = 120.0
    section_hauteur: float = 250.0
    nombre_traverses: int = 3
    entraxe_solives_i_max: float = 500.0
    inclure_solives_i: bool = False

    def __post_init__(self) -> None:
        if min(
            self.section_largeur,
            self.section_hauteur,
            self.entraxe_solives_i_max,
        ) <= 0:
            raise ValueError("les sections doivent être strictement positives")
        if self.nombre_traverses < 2:
            raise ValueError("le châssis doit comporter au moins deux traverses")
        if self.nombre_traverses != 3:
            raise ValueError("ce plan d'assemblage est défini pour trois traverses")
        if self.geometrie.largeur_interieure <= 2 * self.section_largeur:
            raise ValueError("la largeur est insuffisante pour les poutres de rive")

    @property
    def entraxe_traverses(self) -> float:
        """Distance entre les axes des traverses successives."""
        return (
            self.geometrie.longueur_interieure - self.section_largeur
        ) / (self.nombre_traverses - 1)

    @property
    def nombre_intervalles_solives_i(self) -> int:
        distance_entre_poutres = (
            self.geometrie.largeur_interieure - self.section_largeur
        )
        return ceil(distance_entre_poutres / self.entraxe_solives_i_max)

    @property
    def nombre_solives_i(self) -> int:
        """Nombre de solives, hors poutres longitudinales de rive."""
        return self.nombre_intervalles_solives_i - 1

    @property
    def entraxe_solives_i(self) -> float:
        return (
            self.geometrie.largeur_interieure - self.section_largeur
        ) / self.nombre_intervalles_solives_i

    @property
    def niveau_haut_traverses(self) -> float:
        return self.section_hauteur

    def elements(self) -> list[ElementPlancher]:
        largeur = self.geometrie.largeur_interieure
        longueur = self.geometrie.longueur_interieure
        demi_section = self.section_largeur / 2
        profondeur_mi_bois = self.section_hauteur / 2
        align_min = (Align.MIN, Align.MIN, Align.MIN)

        poutre_piece = Madrier(
            longueur=longueur,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        poutre = poutre_piece.construire()
        elements: list[ElementPlancher] = []

        # Les poutres reçoivent la moitié supérieure des six mi-bois.
        for nom, y_min in (
            ("Poutre longitudinale gauche", -largeur / 2),
            (
                "Poutre longitudinale droite",
                largeur / 2 - self.section_largeur,
            ),
        ):
            forme = Pos(0, y_min + demi_section, 0) * poutre
            for x in (
                0,
                longueur / 2 - demi_section,
                longueur - self.section_largeur,
            ):
                forme -= Pos(x, y_min, profondeur_mi_bois) * Box(
                    self.section_largeur,
                    self.section_largeur,
                    profondeur_mi_bois,
                    align=align_min,
                )
            elements.append(ElementPlancher(nom, poutre_piece, forme, "saddlebrown"))

        # Les traverses reçoivent la moitié inférieure complémentaire et se
        # posent verticalement dans les entailles ouvertes des poutres.
        traverse_piece = Madrier(
            longueur=largeur,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        traverse = traverse_piece.construire()
        for nom, x in (
            ("Traverse haute", demi_section),
            ("Traverse milieu", longueur / 2),
            ("Traverse basse", longueur - demi_section),
        ):
            forme = Pos(x, -largeur / 2, 0) * Rot(0, 0, 90) * traverse
            for y in (-largeur / 2, largeur / 2 - self.section_largeur):
                forme -= Pos(
                    x - demi_section,
                    y,
                    0,
                ) * Box(
                    self.section_largeur,
                    self.section_largeur,
                    profondeur_mi_bois,
                    align=align_min,
                )
            elements.append(
                ElementPlancher(
                    nom,
                    traverse_piece,
                    forme,
                    "burlywood",
                )
            )

        if self.inclure_solives_i:
            solive_i_piece = PoutreI(longueur=longueur)
            solive_i = solive_i_piece.construire()
            axe_poutre_gauche = -largeur / 2 + demi_section

            for index in range(1, self.nombre_intervalles_solives_i):
                y = axe_poutre_gauche + index * self.entraxe_solives_i
                elements.append(
                    ElementPlancher(
                        f"Solive en I {index:02d}",
                        solive_i_piece,
                        Pos(0, y, self.niveau_haut_traverses) * solive_i,
                        "goldenrod",
                    )
                )

        return elements

    def nomenclature(self):
        """Construit la nomenclature agrégée du plancher."""
        from maison.nomenclature import Nomenclature

        return Nomenclature(self.elements())
