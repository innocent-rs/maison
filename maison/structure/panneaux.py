"""Panneaux structurels utilisables dans la maison."""

from dataclasses import dataclass
from typing import ClassVar

from build123d import Align, Box, Part

from maison.nomenclature import ArticleBOM


@dataclass(frozen=True, slots=True)
class DalleOSB:
    """Dalle OSB de 675 × 2500 mm, disponible en quatre épaisseurs.

    Par convention, la longueur est orientée sur X, la largeur sur Y et
    l'épaisseur sur Z. L'origine se trouve au milieu de la largeur, sous la
    face de départ du panneau.
    """

    EPAISSEURS_DISPONIBLES: ClassVar[tuple[float, ...]] = (12.0, 15.0, 18.0, 22.0)

    epaisseur: float
    largeur: float = 675.0
    longueur: float = 2_500.0
    materiau: str = "Panneau structurel OSB (classe à définir)"

    def __post_init__(self) -> None:
        if self.epaisseur not in self.EPAISSEURS_DISPONIBLES:
            valeurs = ", ".join(f"{valeur:g}" for valeur in self.EPAISSEURS_DISPONIBLES)
            raise ValueError(f"épaisseur indisponible : choisir {valeurs} mm")
        if self.largeur <= 0 or self.longueur <= 0:
            raise ValueError("largeur et longueur doivent être strictement positives")

    def construire(self) -> Part:
        """Construit et renvoie la géométrie build123d de la dalle."""
        return Box(
            self.longueur,
            self.largeur,
            self.epaisseur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    @property
    def designation(self) -> str:
        return (
            f"Dalle OSB {self.largeur:g} × {self.longueur:g}"
            f" × {self.epaisseur:g} mm"
        )

    def article_bom(self) -> ArticleBOM:
        """Décrit cette dalle pour la nomenclature."""
        return ArticleBOM(
            reference=(
                f"OSB-{self.largeur:g}x{self.longueur:g}x{self.epaisseur:g}"
            ).replace(".", "_"),
            designation=self.designation,
            categorie="Panneaux / dalle OSB",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.longueur * self.largeur * self.epaisseur,
        )
