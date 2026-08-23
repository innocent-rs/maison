"""Ossature paramétrique des fermes du A-frame."""

from dataclasses import dataclass
from math import cos, floor, radians, tan

from build123d import Pos, Rot, Shape

from maison.geometrie import GeometrieAFrame
from maison.nomenclature import Nomenclaturable
from maison.structure.bois import Arbaletrier
from maison.structure.connecteurs import FerrurePiedAFrame, KitTirantAFrame


@dataclass(frozen=True, slots=True)
class ElementCharpente:
    nom: str
    piece: Nomenclaturable
    forme: Shape
    couleur: str

    def article_bom(self):
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class CharpenteAFrame:
    """Couples d'arbalétriers répartis suivant la longueur du plancher.

    Les pieds reposent sur les poutres de rive et sont accompagnés de ferrures
    de principe. Un tirant sous plancher ferme chaque triangle ; son diamètre
    et les ferrures devront être validés après calcul des efforts.
    """

    geometrie: GeometrieAFrame
    entraxe_fermes: float = 500.0
    largeur_arbaletrier: float = 120.0
    hauteur_arbaletrier: float = 250.0
    largeur_poutre_rive: float = 120.0
    niveau_appui: float = 272.0
    inclure_liaisons_pied: bool = False
    diametre_tirants: float = 16.0
    niveau_axes_tirants: float = -30.0
    marge_percage_tirant: float = 20.0

    def __post_init__(self) -> None:
        if min(
            self.entraxe_fermes,
            self.largeur_arbaletrier,
            self.hauteur_arbaletrier,
            self.largeur_poutre_rive,
            self.diametre_tirants,
            self.marge_percage_tirant,
        ) <= 0:
            raise ValueError("les dimensions de charpente doivent être positives")
        if self.niveau_appui < 0:
            raise ValueError("le niveau d'appui ne peut pas être négatif")
        if (
            self.inclure_liaisons_pied
            and self.niveau_axes_tirants + self.diametre_tirants / 2 > 0
        ):
            raise ValueError("le tirant doit rester entièrement sous le plancher")
        if self.geometrie.longueur_interieure < self.largeur_arbaletrier:
            raise ValueError("le plancher est trop court pour une ferme")
        if self.largeur_entre_axes_pieds <= 0:
            raise ValueError("la largeur est insuffisante pour les pieds de ferme")

    @property
    def nombre_fermes(self) -> int:
        """Nombre de fermes à entraxe exact, avec deux retraits symétriques."""
        longueur_utile = (
            self.geometrie.longueur_interieure - self.largeur_arbaletrier
        )
        return floor(longueur_utile / self.entraxe_fermes) + 1

    @property
    def retrait_fermes_extremes(self) -> float:
        longueur_occupee = (self.nombre_fermes - 1) * self.entraxe_fermes
        return (self.geometrie.longueur_interieure - longueur_occupee) / 2

    def axes_fermes(self) -> tuple[float, ...]:
        retrait = self.retrait_fermes_extremes
        return tuple(
            retrait + index * self.entraxe_fermes
            for index in range(self.nombre_fermes)
        )

    @property
    def largeur_entre_axes_pieds(self) -> float:
        return self.geometrie.largeur_interieure - self.largeur_poutre_rive

    @property
    def longueur_arbaletrier(self) -> float:
        demi_portee = self.largeur_entre_axes_pieds / 2
        return demi_portee / cos(radians(self.geometrie.angle_degres))

    @property
    def hauteur_faitage_interieure(self) -> float:
        """Niveau du centre de la coupe verticale de faîtage."""
        demi_portee = self.largeur_entre_axes_pieds / 2
        return self.niveau_appui + demi_portee * tan(
            radians(self.geometrie.angle_degres)
        )

    @property
    def niveau_haut_faitage(self) -> float:
        demi_hauteur_verticale = self.hauteur_arbaletrier / (
            2 * cos(radians(self.geometrie.angle_degres))
        )
        return self.hauteur_faitage_interieure + demi_hauteur_verticale

    @property
    def longueur_debit_arbaletrier(self) -> float:
        return Arbaletrier(
            longueur_axe=self.longueur_arbaletrier,
            angle_degres=self.geometrie.angle_degres,
            largeur=self.largeur_arbaletrier,
            hauteur=self.hauteur_arbaletrier,
        ).longueur_debit

    @property
    def nombre_ferrures_pied(self) -> int:
        return 2 * self.nombre_fermes if self.inclure_liaisons_pied else 0

    @property
    def nombre_tirants(self) -> int:
        return self.nombre_fermes if self.inclure_liaisons_pied else 0

    @property
    def hauteur_retour_ferrure(self) -> float:
        """Retour depuis l'appui jusqu'au-dessous du perçage du tirant."""
        return (
            self.niveau_appui
            - self.niveau_axes_tirants
            + self.diametre_tirants / 2
            + self.marge_percage_tirant
        )

    def elements(self) -> list[ElementCharpente]:
        demi_largeur = self.geometrie.largeur_interieure / 2
        axe_pied_gauche = -demi_largeur + self.largeur_poutre_rive / 2
        axe_pied_droit = demi_largeur - self.largeur_poutre_rive / 2
        piece = Arbaletrier(
            longueur_axe=self.longueur_arbaletrier,
            angle_degres=self.geometrie.angle_degres,
            largeur=self.largeur_arbaletrier,
            hauteur=self.hauteur_arbaletrier,
            largeur_appui_pied=self.largeur_poutre_rive,
        )
        arbaletrier = piece.construire()
        elements: list[ElementCharpente] = []
        ferrure_piece = FerrurePiedAFrame(
            largeur_bois=self.largeur_arbaletrier,
            largeur_appui=self.largeur_poutre_rive,
            hauteur_ancrage_poutre=self.hauteur_retour_ferrure,
        )
        ferrure = ferrure_piece.construire()
        tirant_piece = KitTirantAFrame(
            longueur=self.geometrie.largeur_interieure,
            diametre=self.diametre_tirants,
        )
        tirant = tirant_piece.construire()

        for numero, x in enumerate(self.axes_fermes(), start=1):
            elements.extend(
                (
                    ElementCharpente(
                        f"Arbalétrier {numero:02d} gauche",
                        piece,
                        Pos(x, axe_pied_gauche, self.niveau_appui)
                        * Rot(self.geometrie.angle_degres, 0, 90)
                        * arbaletrier,
                        "firebrick",
                    ),
                    ElementCharpente(
                        f"Arbalétrier {numero:02d} droit",
                        piece,
                        Pos(x, axe_pied_droit, self.niveau_appui)
                        * Rot(-self.geometrie.angle_degres, 0, -90)
                        * arbaletrier,
                        "darkred",
                    ),
                )
            )
            if self.inclure_liaisons_pied:
                elements.extend(
                    (
                        ElementCharpente(
                            f"Ferrure de pied {numero:02d} gauche",
                            ferrure_piece,
                            Pos(x, -demi_largeur, self.niveau_appui) * ferrure,
                            "silver",
                        ),
                        ElementCharpente(
                            f"Ferrure de pied {numero:02d} droite",
                            ferrure_piece,
                            Pos(x, demi_largeur, self.niveau_appui)
                            * Rot(0, 0, 180)
                            * ferrure,
                            "silver",
                        ),
                        ElementCharpente(
                            f"Tirant sous plancher {numero:02d}",
                            tirant_piece,
                            Pos(
                                x,
                                -demi_largeur,
                                self.niveau_axes_tirants,
                            )
                            * Rot(0, 0, 90)
                            * tirant,
                            "steelblue",
                        ),
                    )
                )
        return elements
