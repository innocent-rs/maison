"""Panneaux structurels utilisables dans la maison."""

from dataclasses import dataclass
from typing import ClassVar

from build123d import Align, Box, Part, Pos

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


@dataclass(frozen=True, slots=True)
class PanneauFondCaissonOSB:
    """Découpe d'OSB formant le fond d'un caisson entre deux solives en I.

    Les angles peuvent être dégagés pour ne pas croiser les assises des étriers
    EWH. Le panneau est posé par-dessus les membrures basses. La longueur suit
    X, la largeur Y et l'origine est sous la face de départ, au milieu de la
    largeur.
    """

    epaisseur: float
    largeur: float
    longueur: float
    longueur_encoche: float = 82.0
    largeur_encoche: float = 47.0
    avec_encoches: bool = True
    materiau: str = "Panneau structurel OSB 3"

    def __post_init__(self) -> None:
        if self.epaisseur not in DalleOSB.EPAISSEURS_DISPONIBLES:
            raise ValueError("épaisseur OSB indisponible")
        if min(
            self.largeur,
            self.longueur,
            self.longueur_encoche,
            self.largeur_encoche,
        ) <= 0:
            raise ValueError("les dimensions du panneau doivent être positives")
        if 2 * self.longueur_encoche >= self.longueur:
            raise ValueError("les encoches se rejoindraient dans la longueur")
        if 2 * self.largeur_encoche >= self.largeur:
            raise ValueError("les encoches se rejoindraient dans la largeur")

    def construire(self) -> Part:
        panneau = Box(
            self.longueur,
            self.largeur,
            self.epaisseur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )
        if not self.avec_encoches:
            return panneau
        demi_largeur = self.largeur / 2
        encoche = Box(
            self.longueur_encoche,
            self.largeur_encoche,
            self.epaisseur,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        for x in (0, self.longueur - self.longueur_encoche):
            for y in (-demi_largeur, demi_largeur - self.largeur_encoche):
                panneau -= Pos(x, y, 0) * encoche
        return panneau

    @property
    def volume_mm3(self) -> float:
        surface = self.longueur * self.largeur
        if self.avec_encoches:
            surface -= 4 * self.longueur_encoche * self.largeur_encoche
        return surface * self.epaisseur

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"OSB-FOND-{self.largeur:g}x{self.longueur:g}x{self.epaisseur:g}"
        ).replace(".", "_")
        if not self.avec_encoches:
            reference += "-RECT"
        suffixe = "" if self.avec_encoches else " — sans encoche"
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Fond de caisson OSB {self.largeur:g} × {self.longueur:g}"
                f" × {self.epaisseur:g} mm{suffixe}"
            ),
            categorie="Panneaux / découpe OSB",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.volume_mm3,
        )


@dataclass(frozen=True, slots=True)
class PanneauPlancherOSB:
    """Découpe rectangulaire d'OSB rainuré-languetté pour le plancher porteur."""

    epaisseur: float
    largeur: float
    longueur: float
    materiau: str = "Panneau structurel OSB 3 rainuré-languetté"

    def __post_init__(self) -> None:
        if self.epaisseur not in DalleOSB.EPAISSEURS_DISPONIBLES:
            raise ValueError("épaisseur OSB indisponible")
        if min(self.largeur, self.longueur) <= 0:
            raise ValueError("les dimensions du panneau doivent être positives")

    def construire(self) -> Part:
        """Représente l'enveloppe rectangulaire, sans détailler le profil R+L."""
        return Box(
            self.longueur,
            self.largeur,
            self.epaisseur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    @property
    def volume_mm3(self) -> float:
        return self.longueur * self.largeur * self.epaisseur

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"OSB-PLANCHER-{self.largeur:g}x{self.longueur:g}x"
            f"{self.epaisseur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Plancher OSB 3 R+L {self.largeur:g} × {self.longueur:g}"
                f" × {self.epaisseur:g} mm"
            ),
            categorie="Panneaux / plancher OSB",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.volume_mm3,
        )
