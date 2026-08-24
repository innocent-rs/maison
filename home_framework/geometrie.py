"""Contrats et géométries élémentaires partagés entre projets."""

from dataclasses import dataclass
from typing import Protocol


class GeometriePlancher(Protocol):
    largeur_interieure: float
    longueur_interieure: float

    @property
    def surface_plancher(self) -> float: ...


@dataclass(frozen=True, slots=True)
class GeometriePlancherRectangulaire:
    """Emprise rectangulaire indépendante de tout type de bâtiment."""

    largeur_interieure: float
    longueur_interieure: float

    def __post_init__(self) -> None:
        if min(self.largeur_interieure, self.longueur_interieure) <= 0:
            raise ValueError("les dimensions du plancher doivent être positives")

    @property
    def surface_plancher(self) -> float:
        return self.largeur_interieure * self.longueur_interieure / 1_000_000
