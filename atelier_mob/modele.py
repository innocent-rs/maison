"""Agrégation du plancher MOB et de ses fondations sur pieux vissés."""

from dataclasses import dataclass, field

from home_framework.nomenclature import Nomenclature
from home_framework.structure.plancher import PlancherBois

from .fondations import FondationsPieuxVisses
from .geometrie import GeometrieAtelierMob
from .plancher import creer_plancher_atelier, positions_pieux_pour_plancher


@dataclass(frozen=True, slots=True)
class AtelierMob:
    """Atelier rectangulaire avec son plancher isolé et ses appuis."""

    geometrie: GeometrieAtelierMob = field(default_factory=GeometrieAtelierMob)
    fondations: FondationsPieuxVisses | None = None
    plancher: PlancherBois | None = None

    def __post_init__(self) -> None:
        plancher = self.plancher
        if plancher is None:
            plancher = creer_plancher_atelier(self.geometrie)
            object.__setattr__(self, "plancher", plancher)
        elif plancher.geometrie != self.geometrie:
            raise ValueError("le plancher et l'atelier doivent partager la géométrie")

        if self.fondations is None:
            object.__setattr__(
                self,
                "fondations",
                FondationsPieuxVisses(
                    positions_platines=positions_pieux_pour_plancher(plancher),
                ),
            )

    @property
    def chassis_plancher(self) -> PlancherBois:
        """Alias de migration pour les anciens appels du projet."""
        return self.plancher

    def elements(self):
        return (*self.fondations.elements(), *self.plancher.elements())

    def nomenclature_fondations(self) -> Nomenclature:
        return self.fondations.nomenclature_achats()

    def nomenclature_plancher(self) -> Nomenclature:
        return self.plancher.nomenclature_achats()

    def nomenclature_achats(self) -> Nomenclature:
        return Nomenclature(
            (*self.fondations.elements(), *self.plancher.pieces_achat())
        )

    def verifier_structure(self, hypotheses=None):
        """Lance la pré-vérification ELU/ELS Eurocode 5 du plancher."""
        from .dimensionnement import verifier_plancher_eurocode5

        return verifier_plancher_eurocode5(self.plancher, hypotheses)

    def inventorier_masses(self, hypotheses=None):
        """Détaille les masses installées utilisées comme poids propres."""
        from .masses import inventorier_masses_plancher

        return inventorier_masses_plancher(self.plancher, hypotheses)


def creer_atelier_mob(
    positions_platines: tuple[tuple[float, float], ...] | None = None,
    largeur_interieure: float = 7_000.0,
    longueur_interieure: float = 15_000.0,
    nombre_traverses: int = 8,
    entraxe_solives_i_max: float = 573.0,
) -> AtelierMob:
    """Crée l'atelier et, par défaut, la trame de 3 pieux par traverse.

    Passer explicitement ``positions_platines=()`` permet de construire le
    modèle sans fondations automatiques.
    """

    geometrie = GeometrieAtelierMob(
        largeur_interieure=largeur_interieure,
        longueur_interieure=longueur_interieure,
    )
    plancher = creer_plancher_atelier(
        geometrie,
        nombre_traverses=nombre_traverses,
        entraxe_solives_i_max=entraxe_solives_i_max,
    )
    if positions_platines is None:
        positions_platines = positions_pieux_pour_plancher(plancher)
    return AtelierMob(
        geometrie=geometrie,
        fondations=FondationsPieuxVisses(positions_platines=positions_platines),
        plancher=plancher,
    )
