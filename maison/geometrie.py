"""Géométrie générale de la maison en A."""

from dataclasses import dataclass
from math import radians, tan


@dataclass(frozen=True, slots=True)
class GeometrieAFrame:
    """Dimensions de référence calculées d'un A-frame symétrique.

    Les longueurs sont exprimées en millimètres et les surfaces en m².
    Pour compatibilité avec l'API initiale, ``largeur_interieure`` et
    ``longueur_interieure`` désignent ici l'emprise hors-tout du plancher.
    Le calcul est théorique : doublages, cloisons et trémie seront déduits
    lorsqu'ils seront introduits dans le modèle.
    """

    largeur_interieure: float = 6_000.0
    angle_degres: float = 60.0
    surface_comptable_cible: float = 20.5
    hauteur_limite: float = 1_800.0
    surface_plancher_max: float | None = None
    longueur_interieure_imposee: float | None = None

    def __post_init__(self) -> None:
        if self.largeur_interieure <= 0:
            raise ValueError("largeur_interieure doit être strictement positive")
        if not 0 < self.angle_degres < 90:
            raise ValueError("angle_degres doit être compris entre 0 et 90")
        if self.surface_comptable_cible <= 0:
            raise ValueError("surface_comptable_cible doit être strictement positive")
        if self.surface_plancher_max is not None and self.surface_plancher_max <= 0:
            raise ValueError("surface_plancher_max doit être strictement positive")
        if (
            self.longueur_interieure_imposee is not None
            and self.longueur_interieure_imposee <= 0
        ):
            raise ValueError("longueur_interieure_imposee doit être positive")
        if (
            self.longueur_interieure_imposee is not None
            and self.surface_plancher_max is not None
            and self.largeur_interieure * self.longueur_interieure_imposee
            > self.surface_plancher_max * 1_000_000 + 1e-6
        ):
            raise ValueError("la longueur imposée dépasse la surface maximale")
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
        if self.longueur_interieure_imposee is not None:
            return self.longueur_interieure_imposee
        longueur_carrez = (
            self.surface_comptable_cible * 1_000_000 / self.largeur_comptable
        )
        if self.surface_plancher_max is None:
            return longueur_carrez
        longueur_surface_totale = (
            self.surface_plancher_max * 1_000_000 / self.largeur_interieure
        )
        return min(longueur_carrez, longueur_surface_totale)

    @property
    def surface_comptable(self) -> float:
        """Surface théorique dont la hauteur est supérieure ou égale à 1,80 m."""
        return self.largeur_comptable * self.longueur_interieure / 1_000_000

    @property
    def surface_plancher(self) -> float:
        return self.largeur_interieure * self.longueur_interieure / 1_000_000
