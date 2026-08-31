"""Emprise rectangulaire de l'atelier en ossature bois."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeometrieAtelierMob:
    """Emprise du plancher, indépendante de la forme de la toiture.

    Les dimensions par défaut sont maintenant les valeurs rondes retenues pour
    le projet : 7 m de largeur et 15 m de longueur.
    """

    largeur_interieure: float = 7_000.0
    longueur_interieure: float = 15_000.0

    def __post_init__(self) -> None:
        if min(self.largeur_interieure, self.longueur_interieure) <= 0:
            raise ValueError("les dimensions doivent être strictement positives")

    @property
    def surface_plancher(self) -> float:
        return self.largeur_interieure * self.longueur_interieure / 1_000_000


# Compatibilité temporaire avec les appels écrits avant l'abandon de l'A-frame.
GeometrieAtelierAFrame = GeometrieAtelierMob
