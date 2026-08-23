"""Géométrie générale de la maison en A."""

from dataclasses import dataclass
from math import radians, tan


@dataclass(frozen=True, slots=True)
class GeometrieAFrame:
    """Dimensions intérieures calculées d'un A-frame symétrique.

    Les longueurs sont exprimées en millimètres et les surfaces en m².
    Le calcul est théorique : doublages, cloisons et trémie seront déduits
    lorsqu'ils seront introduits dans le modèle.
    """

    largeur_interieure: float = 6_000.0
    angle_degres: float = 60.0
    surface_comptable_cible: float = 20.5
    hauteur_limite: float = 1_800.0

    def __post_init__(self) -> None:
        if self.largeur_interieure <= 0:
            raise ValueError("largeur_interieure doit être strictement positive")
        if not 0 < self.angle_degres < 90:
            raise ValueError("angle_degres doit être compris entre 0 et 90")
        if self.surface_comptable_cible <= 0:
            raise ValueError("surface_comptable_cible doit être strictement positive")
        if self.largeur_comptable <= 0:
            raise ValueError(
                "la largeur et l'angle ne permettent aucune zone au-dessus "
                "de la hauteur limite"
            )

    @property
    def pente(self) -> float:
        return tan(radians(self.angle_degres))

    @property
    def hauteur_faitage(self) -> float:
        return self.largeur_interieure / 2 * self.pente

    @property
    def retrait_hauteur_limite(self) -> float:
        """Distance horizontale entre un pied du A et la hauteur limite."""
        return self.hauteur_limite / self.pente

    @property
    def largeur_comptable(self) -> float:
        return self.largeur_interieure - 2 * self.retrait_hauteur_limite

    @property
    def longueur_interieure(self) -> float:
        return self.surface_comptable_cible * 1_000_000 / self.largeur_comptable

    @property
    def surface_plancher(self) -> float:
        return self.largeur_interieure * self.longueur_interieure / 1_000_000

