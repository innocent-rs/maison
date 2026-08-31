"""Détection générique des volumes inoccupés dans une enveloppe CAO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from build123d import Shape, Solid


@dataclass(frozen=True, slots=True)
class ComposanteVide:
    """Volume vide connexe extrait automatiquement de l'enveloppe."""

    numero: int
    forme: Solid

    @property
    def volume_m3(self) -> float:
        return self.forme.volume / 1_000_000_000


@dataclass(frozen=True, slots=True)
class RapportVides:
    """Résultat indépendant de la nature et de la forme des occupants."""

    enveloppe: Shape
    composantes: tuple[ComposanteVide, ...]
    nombre_occupants: int

    @property
    def nombre_composantes(self) -> int:
        return len(self.composantes)

    @property
    def volume_enveloppe_m3(self) -> float:
        return self.enveloppe.volume / 1_000_000_000

    @property
    def volume_vide_m3(self) -> float:
        return sum(composante.volume_m3 for composante in self.composantes)

    @property
    def taux_vide_pct(self) -> float:
        return 100 * self.volume_vide_m3 / self.volume_enveloppe_m3


def _boites_se_chevauchent(gauche: Shape, droite: Shape) -> bool:
    a = gauche.bounding_box()
    b = droite.bounding_box()
    return not (
        a.max.X <= b.min.X
        or a.min.X >= b.max.X
        or a.max.Y <= b.min.Y
        or a.min.Y >= b.max.Y
        or a.max.Z <= b.min.Z
        or a.min.Z >= b.max.Z
    )


def detecter_vides(
    enveloppe: Shape,
    occupants: Iterable[Shape],
    *,
    volume_min_mm3: float = 1.0,
) -> RapportVides:
    """Calcule ``enveloppe - occupants`` et sépare les volumes connexes.

    L'appelant choisit seulement la frontière de la zone à analyser. Aucune
    connaissance des matériaux, types de pièces ou profils constructifs n'est
    nécessaire. Les formes sans volume et celles extérieures à l'enveloppe
    sont ignorées automatiquement.
    """

    if enveloppe.volume <= 0:
        raise ValueError("l'enveloppe d'analyse doit avoir un volume positif")
    if volume_min_mm3 < 0:
        raise ValueError("le volume minimal ne peut pas être négatif")

    occupants_utiles = tuple(
        forme
        for forme in occupants
        if forme.volume > 0 and _boites_se_chevauchent(enveloppe, forme)
    )
    resultat = (
        enveloppe.cut(*occupants_utiles)
        if occupants_utiles
        else enveloppe
    )
    solides = sorted(
        (
            solide
            for solide in resultat.solids()
            if solide.volume >= volume_min_mm3
        ),
        key=lambda solide: solide.volume,
        reverse=True,
    )
    return RapportVides(
        enveloppe=enveloppe,
        composantes=tuple(
            ComposanteVide(numero=index, forme=solide)
            for index, solide in enumerate(solides, start=1)
        ),
        nombre_occupants=len(occupants_utiles),
    )
