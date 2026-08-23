"""Pièces structurelles en bois.

Toutes les dimensions sont exprimées en millimètres. Par convention, une
pièce longitudinale est orientée ainsi :

- X : longueur ;
- Y : largeur ;
- Z : hauteur.
"""

from dataclasses import dataclass
from math import cos, radians, sin, tan

from build123d import Align, Box, Face, Part, Pos, Vector, Wire, extrude

from maison.nomenclature import ArticleBOM


@dataclass(frozen=True, slots=True)
class Madrier:
    """Madrier rectangulaire paramétrique, de section 120 × 240 mm par défaut.

    L'origine se trouve au milieu de la largeur, sur la face de départ et sous
    la pièce. Cette convention simplifie le placement des éléments du plancher.
    """

    longueur: float
    largeur: float = 120.0
    hauteur: float = 240.0
    materiau: str = "Douglas contrecollé structurel GT24"

    def __post_init__(self) -> None:
        for nom, valeur in (
            ("longueur", self.longueur),
            ("largeur", self.largeur),
            ("hauteur", self.hauteur),
        ):
            if valeur <= 0:
                raise ValueError(f"{nom} doit être strictement positif")

    def construire(self) -> Part:
        """Construit et renvoie la géométrie build123d du madrier."""
        return Box(
            self.longueur,
            self.largeur,
            self.hauteur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    @property
    def designation(self) -> str:
        """Désignation lisible avec section et longueur."""
        return (
            f"Madrier {self.largeur:g} × {self.hauteur:g} mm"
            f" — L {self.longueur:g} mm"
        )

    def article_bom(self) -> ArticleBOM:
        """Décrit cette coupe de bois pour la nomenclature."""
        reference = (
            f"MAD-{self.largeur:g}x{self.hauteur:g}-L{self.longueur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=self.designation,
            categorie="Bois / madrier",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            volume_mm3=self.longueur * self.largeur * self.hauteur,
        )


@dataclass(frozen=True, slots=True)
class Arbaletrier:
    """Arbalétrier avec faîtage vertical et assise limitée au pied.

    ``longueur_axe`` relie le centre de la coupe de pied au centre de la coupe
    de faîtage. La pièce est construite suivant X, centrée suivant Y et Z ; la
    charpente se charge ensuite de l'orienter dans le plan YZ.
    """

    longueur_axe: float
    angle_degres: float = 60.0
    largeur: float = 120.0
    hauteur: float = 250.0
    largeur_appui_pied: float = 120.0
    jeu_relief_pied: float = 2.0
    materiau: str = "Bois massif structurel (classe à définir)"

    def __post_init__(self) -> None:
        if min(
            self.longueur_axe,
            self.largeur,
            self.hauteur,
            self.largeur_appui_pied,
            self.jeu_relief_pied,
        ) <= 0:
            raise ValueError("les dimensions de l'arbalétrier doivent être positives")
        if not 0 < self.angle_degres < 90:
            raise ValueError("l'angle de l'arbalétrier doit être compris entre 0 et 90°")
        if self.longueur_courte <= 0:
            raise ValueError("l'arbalétrier est trop court pour ses coupes")
        if self.largeur_appui_pied >= self.longueur_coupe_horizontale_complete:
            raise ValueError("l'appui de pied ne laisse aucune zone de relief")

    @property
    def angle_coupe_pied_axe(self) -> float:
        return self.angle_degres

    @property
    def angle_coupe_faitage_axe(self) -> float:
        return 90 - self.angle_degres

    @property
    def recul_pointe_pied(self) -> float:
        """Dépassement axial du nu extérieur au-delà du centre du pied."""
        return self.largeur_appui_pied / 2 * cos(radians(self.angle_degres))

    @property
    def longueur_coupe_horizontale_complete(self) -> float:
        """Longueur qu'aurait la coupe horizontale sans limitation extérieure."""
        return self.hauteur / sin(radians(self.angle_degres))

    @property
    def longueur_relief_interieur(self) -> float:
        """Projection horizontale dégagée au-delà de la poutre d'appui."""
        angle = radians(self.angle_degres)
        fin_relief = (
            self.hauteur / (2 * cos(angle)) + self.jeu_relief_pied
        ) / tan(angle)
        return fin_relief - self.largeur_appui_pied / 2

    @property
    def depassement_pointe_faitage(self) -> float:
        """Dépassement axial de la pointe haute au-delà de l'axe du faîtage."""
        return self.hauteur / 2 * tan(radians(self.angle_degres))

    @property
    def longueur_debit(self) -> float:
        """Longueur minimale du brut, de pointe longue à pointe longue."""
        return (
            self.longueur_axe
            + self.recul_pointe_pied
            + self.depassement_pointe_faitage
        )

    @property
    def longueur_courte(self) -> float:
        """Longueur de l'arête opposée aux deux pointes longues."""
        return (
            self.longueur_axe
            - self.hauteur / (2 * tan(radians(self.angle_degres)))
            - self.depassement_pointe_faitage
        )

    def construire(self) -> Part:
        demi_hauteur = self.hauteur / 2
        angle = radians(self.angle_degres)
        pente = tan(angle)
        sinus = sin(angle)
        cosinus = cos(angle)
        demi_appui = self.largeur_appui_pied / 2

        def depuis_horizontal(horizontal: float, vertical: float) -> Vector:
            """Ramène un point du plan horizontal/vertical dans l'axe du bois."""
            return Vector(
                horizontal * cosinus + vertical * sinus,
                0,
                -horizontal * sinus + vertical * cosinus,
            )

        fin_relief = (
            demi_hauteur / cosinus + self.jeu_relief_pied
        ) / pente
        pied_exterieur_haut_x = (
            -demi_appui + demi_hauteur * sinus
        ) / cosinus
        points = (
            depuis_horizontal(-demi_appui, 0),
            depuis_horizontal(demi_appui, 0),
            depuis_horizontal(demi_appui, self.jeu_relief_pied),
            depuis_horizontal(fin_relief, self.jeu_relief_pied),
            Vector(
                self.longueur_axe - demi_hauteur * pente,
                0,
                -demi_hauteur,
            ),
            Vector(
                self.longueur_axe + demi_hauteur * pente,
                0,
                demi_hauteur,
            ),
            Vector(pied_exterieur_haut_x, 0, demi_hauteur),
        )
        profil = Face(Wire.make_polygon((*points, points[0])))
        return extrude(
            profil,
            amount=self.largeur / 2,
            both=True,
            dir=Vector(0, 1, 0),
        )

    @property
    def designation(self) -> str:
        return (
            f"Arbalétrier {self.largeur:g} × {self.hauteur:g} mm"
            f" — débit {self.longueur_debit:g} mm — pente {self.angle_degres:g}°"
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"ARB-{self.largeur:g}x{self.hauteur:g}"
            f"-A{self.angle_degres:g}-LD{self.longueur_debit:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=self.designation,
            categorie="Bois / arbalétrier",
            materiau=self.materiau,
            longueur_mm=self.longueur_debit,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            volume_mm3=self.construire().volume,
        )


@dataclass(frozen=True, slots=True)
class Tasseau:
    """Tasseau rectangulaire, orienté selon la convention générale XYZ."""

    longueur: float
    largeur: float = 90.0
    hauteur: float = 45.0
    materiau: str = "Bois massif structurel (classe à définir)"

    def __post_init__(self) -> None:
        if min(self.longueur, self.largeur, self.hauteur) <= 0:
            raise ValueError("les dimensions du tasseau doivent être positives")

    def construire(self) -> Part:
        return Box(
            self.longueur,
            self.largeur,
            self.hauteur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    @property
    def designation(self) -> str:
        return (
            f"Tasseau {self.largeur:g} × {self.hauteur:g} mm"
            f" — L {self.longueur:g} mm"
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"TAS-{self.largeur:g}x{self.hauteur:g}-L{self.longueur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=self.designation,
            categorie="Bois / tasseau",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            volume_mm3=self.longueur * self.largeur * self.hauteur,
        )


@dataclass(frozen=True, slots=True)
class PoutreI:
    """Poutre en I de type STEICOjoist SJ60/240.

    La géométrie utilise deux membrures de 60 × 39 mm et une âme centrée de
    8 mm. Les dimensions restent paramétrables pour de futures variantes.
    """

    longueur: float
    hauteur: float = 240.0
    largeur_membrure: float = 60.0
    hauteur_membrure: float = 39.0
    epaisseur_ame: float = 8.0
    modele: str | None = None
    materiau: str = "Membrures bois/LVL et âme en fibre de bois"

    def __post_init__(self) -> None:
        dimensions = (
            self.longueur,
            self.hauteur,
            self.largeur_membrure,
            self.hauteur_membrure,
            self.epaisseur_ame,
        )
        if min(dimensions) <= 0:
            raise ValueError("les dimensions de la poutre en I doivent être positives")
        if 2 * self.hauteur_membrure >= self.hauteur:
            raise ValueError("les membrures ne laissent aucune hauteur pour l'âme")
        if self.epaisseur_ame > self.largeur_membrure:
            raise ValueError("l'âme ne peut pas être plus large que les membrures")

    @property
    def hauteur_ame(self) -> float:
        return self.hauteur - 2 * self.hauteur_membrure

    def construire(self) -> Part:
        """Construit la section en I extrudée suivant l'axe X."""
        alignement = (Align.MIN, Align.CENTER, Align.MIN)
        membrure_basse = Box(
            self.longueur,
            self.largeur_membrure,
            self.hauteur_membrure,
            align=alignement,
        )
        ame = Pos(0, 0, self.hauteur_membrure) * Box(
            self.longueur,
            self.epaisseur_ame,
            self.hauteur_ame,
            align=alignement,
        )
        membrure_haute = Pos(0, 0, self.hauteur - self.hauteur_membrure) * Box(
            self.longueur,
            self.largeur_membrure,
            self.hauteur_membrure,
            align=alignement,
        )
        return membrure_basse + ame + membrure_haute

    @property
    def designation(self) -> str:
        modele = self.modele or (
            f"STEICOjoist SJ{self.largeur_membrure:g}/{self.hauteur:g}"
        )
        return f"Poutre en I {modele} — L {self.longueur:g} mm"

    @property
    def volume_mm3(self) -> float:
        section_membrures = (
            2 * self.largeur_membrure * self.hauteur_membrure
        )
        section_ame = self.epaisseur_ame * self.hauteur_ame
        return self.longueur * (section_membrures + section_ame)

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
        reference=(
            f"SJI-{self.largeur_membrure:g}x{self.hauteur:g}-L{self.longueur:g}"
        ).replace(".", "_"),
            designation=self.designation,
            categorie="Bois / poutre en I",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur_membrure,
            hauteur_mm=self.hauteur,
            volume_mm3=self.volume_mm3,
        )
