"""Fondations légères de l'atelier sur pieux vissés.

Les pieux et leur partie enterrée restent volontairement hors du modèle : seule
la platine supérieure, utile pour implanter la structure bois, est représentée.
"""

from dataclasses import dataclass, field

from build123d import Align, Box, Part, Pos, Shape

from home_framework.nomenclature import ArticleBOM, Nomenclature


@dataclass(frozen=True, slots=True)
class PlatinePieuVisse:
    """Platine supérieure simplifiée d'un pieu vissé, sans perçages."""

    longueur: float = 200.0
    largeur: float = 200.0
    epaisseur: float = 5.0
    materiau: str = "Acier"

    def __post_init__(self) -> None:
        if min(self.longueur, self.largeur, self.epaisseur) <= 0:
            raise ValueError("les dimensions de la platine doivent être positives")

    @property
    def volume_mm3(self) -> float:
        return self.longueur * self.largeur * self.epaisseur

    def construire(self) -> Part:
        """Place le dessus de la platine à Z=0, centré sur l'axe du pieu."""
        return Box(
            self.longueur,
            self.largeur,
            self.epaisseur,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"PLATINE-PIEU-VISSE-{self.longueur:g}x"
            f"{self.largeur:g}x{self.epaisseur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Platine de pieu vissé {self.longueur:g} × "
                f"{self.largeur:g} × {self.epaisseur:g} mm"
            ),
            categorie="Fondation / platine de pieu vissé",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.volume_mm3,
        )


@dataclass(frozen=True, slots=True)
class ElementFondation:
    """Pièce de fondation placée, consommable par le viewer."""

    nom: str
    piece: PlatinePieuVisse
    forme: Shape
    couleur: str = "steelblue"

    def article_bom(self) -> ArticleBOM:
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class FondationsPieuxVisses:
    """Implantation des platines dans le repère global de l'atelier.

    Chaque position est le couple ``(x, y)`` correspondant à l'axe d'un pieu.
    ``niveau_haut`` fixe le plan d'appui futur de la structure bois.
    """

    positions_platines: tuple[tuple[float, float], ...] = ()
    niveau_haut: float = 0.0
    platine: PlatinePieuVisse = field(default_factory=PlatinePieuVisse)

    def __post_init__(self) -> None:
        positions = tuple(tuple(position) for position in self.positions_platines)
        if any(len(position) != 2 for position in positions):
            raise ValueError("chaque platine doit avoir une position (x, y)")
        if len(set(positions)) != len(positions):
            raise ValueError("deux platines ne peuvent pas partager le même axe")
        object.__setattr__(self, "positions_platines", positions)

    @property
    def nombre_platines(self) -> int:
        return len(self.positions_platines)

    def elements(self) -> tuple[ElementFondation, ...]:
        forme = self.platine.construire()
        return tuple(
            ElementFondation(
                nom=f"Platine pieu vissé {index:02d}",
                piece=self.platine,
                forme=Pos(x, y, self.niveau_haut) * forme,
            )
            for index, (x, y) in enumerate(self.positions_platines, start=1)
        )

    def nomenclature_achats(self) -> Nomenclature:
        return Nomenclature(self.elements())
