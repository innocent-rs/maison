"""Isolants paramétriques de la structure."""

from dataclasses import dataclass

from build123d import Align, Box, Part

from home_framework.nomenclature import ArticleBOM


@dataclass(frozen=True, slots=True)
class PanneauIsonatFlex55:
    """Panneau Isonat acheté entier et représenté à ses dimensions de pose."""

    epaisseurs_disponibles = (40, 60, 80, 100, 120, 145, 160, 180, 200, 220, 240)

    epaisseur: float = 145.0
    largeur: float = 580.0
    longueur: float = 1_220.0
    epaisseur_pose: float = 145.0
    largeur_pose: float = 565.0
    longueur_pose: float | None = None
    conductivite_thermique: float = 0.036
    densite_kg_m3: float = 55.0
    materiau: str = "Fibre de bois semi-rigide Isonat Flex 55 Contact"

    def __post_init__(self) -> None:
        dimensions = (
            self.epaisseur,
            self.largeur,
            self.longueur,
            self.epaisseur_pose,
            self.largeur_pose,
        )
        if min(dimensions) <= 0:
            raise ValueError("les dimensions de l'isolant doivent être positives")
        if self.epaisseur not in self.epaisseurs_disponibles:
            raise ValueError(
                "l'épaisseur demandée n'existe pas dans la gamme Isonat Flex 55"
            )
        if self.epaisseur_pose > self.epaisseur:
            raise ValueError("l'épaisseur posée dépasse l'épaisseur nominale")
        if self.largeur_pose > self.largeur:
            raise ValueError("la largeur posée dépasse la largeur nominale")
        if self.longueur_pose is not None:
            if self.longueur_pose <= 0:
                raise ValueError("la longueur posée doit être positive")
            if self.longueur_pose > self.longueur:
                raise ValueError("la longueur posée dépasse la longueur nominale")

    @property
    def longueur_modelee(self) -> float:
        return self.longueur if self.longueur_pose is None else self.longueur_pose

    @property
    def resistance_thermique_nominale(self) -> float:
        return self.epaisseur / 1_000 / self.conductivite_thermique

    def construire(self) -> Part:
        return Box(
            self.longueur_modelee,
            self.largeur_pose,
            self.epaisseur_pose,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"ISOL-ISONAT-FLEX55-{self.epaisseur:g}x"
            f"{self.largeur:g}x{self.longueur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Panneau Isonat Flex 55 Contact {self.epaisseur:g} × "
                f"{self.largeur:g} × {self.longueur:g} mm"
            ),
            categorie="Isolation / fibre de bois",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.longueur * self.largeur * self.epaisseur,
        )
