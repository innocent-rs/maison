"""Plancher très rigide de 9 m² pour le local batteries."""

from dataclasses import dataclass

from build123d import Align, Box, Pos, Rot

from maison.geometrie import GeometriePlancherRectangulaire
from maison.nomenclature import ArticleBOM, LotBOM, Nomenclature, Nomenclaturable
from maison.structure import (
    DalleOSB,
    ElementPlancher,
    PanneauIsonatFlex55,
    PlancherAFrame,
    TypeBordsOSB,
    VisPlancherOSB5x60,
    VisPlancherOSB5x80,
)
from maison.structure.panneaux import PanneauPlancherOSB


@dataclass(frozen=True, slots=True)
class DecoupeIsonatLocalBatteries:
    """Découpe comprimée entre âmes, représentée à sa dimension de pose."""

    longueur_pose: float
    largeur_pose: float
    longueur_decoupe: float = 607.5
    largeur_decoupe: float = 278.8
    epaisseur: float = 145.0
    materiau: str = "Fibre de bois semi-rigide Isonat Flex 55 Contact"

    def construire(self):
        return Box(
            self.longueur_pose,
            self.largeur_pose,
            self.epaisseur,
            align=(Align.MIN, Align.CENTER, Align.MIN),
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"ISOL-DECOUPE-ISONAT-{self.epaisseur:g}-"
            f"{self.largeur_decoupe:g}x{self.longueur_decoupe:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Découpe Isonat {self.largeur_decoupe:g} × "
                f"{self.longueur_decoupe:g} × {self.epaisseur:g} mm"
            ),
            categorie="Isolation / découpe fibre de bois",
            materiau=self.materiau,
            longueur_mm=self.longueur_decoupe,
            largeur_mm=self.largeur_decoupe,
            hauteur_mm=self.epaisseur,
            volume_mm3=(
                self.longueur_decoupe * self.largeur_decoupe * self.epaisseur
            ),
        )


@dataclass(frozen=True, slots=True)
class LocalBatteries:
    """Sous-ensemble constructif du plancher, hors murs et fondations."""

    plancher: PlancherAFrame
    charge_batteries_kg: float = 1_000.0
    nombre_dalles_osb_achetees: int = 14
    nombre_panneaux_isolant_achetes: int = 10
    nombre_vis_couche_inferieure: int = 600
    nombre_vis_couche_superieure: int = 300

    def __post_init__(self) -> None:
        geometrie = self.plancher.geometrie
        if geometrie.largeur_interieure != 3_000:
            raise ValueError("le local batteries doit mesurer 3 000 mm de large")
        if geometrie.longueur_interieure != 3_000:
            raise ValueError("le local batteries doit mesurer 3 000 mm de long")
        if self.charge_batteries_kg <= 0:
            raise ValueError("la masse des batteries doit être positive")
        if self.plancher.nombre_traverses != 5:
            raise ValueError("le plancher renforcé doit comporter cinq traverses")
        if not self.plancher.inclure_solives_i:
            raise ValueError("le plancher renforcé exige les poutres en I")
        if self.plancher.entraxe_solives_i > 300:
            raise ValueError("l'entraxe des poutres en I ne doit pas dépasser 300 mm")

    @property
    def geometrie(self) -> GeometriePlancherRectangulaire:
        return self.plancher.geometrie

    def _elements_isolant(self) -> list[ElementPlancher]:
        elements: list[ElementPlancher] = []
        demi_traverse = self.plancher.section_largeur / 2
        axes_traverses = self.plancher.axes_traverses()
        axes_solives = self.plancher.axes_solives_i()
        demi_ame = self.plancher.epaisseur_ame_solive_i / 2
        face_rive_gauche = -1_500 + self.plancher.section_largeur
        face_rive_droite = 1_500 - self.plancher.section_largeur
        limites_caissons_y = [
            (face_rive_gauche, axes_solives[0] - demi_ame),
            *(
                (axe_gauche + demi_ame, axe_droit - demi_ame)
                for axe_gauche, axe_droit in zip(axes_solives, axes_solives[1:])
            ),
            (axes_solives[-1] + demi_ame, face_rive_droite),
        ]
        index = 0
        for axe_gauche, axe_droit in zip(axes_traverses, axes_traverses[1:]):
            debut_x = axe_gauche + demi_traverse
            fin_x = axe_droit - demi_traverse
            for debut_y, fin_y in limites_caissons_y:
                index += 1
                piece = DecoupeIsonatLocalBatteries(
                    longueur_pose=round(fin_x - debut_x, 6),
                    largeur_pose=round(fin_y - debut_y, 6),
                )
                elements.append(
                    ElementPlancher(
                        f"Isolant Isonat {index:02d}",
                        piece,
                        Pos(
                            debut_x,
                            (debut_y + fin_y) / 2,
                            self.plancher.hauteur_membrure_solive_i
                            + self.plancher.epaisseur_osb_caissons,
                        )
                        * piece.construire(),
                        "khaki",
                    )
                )
        return elements

    def _elements_osb(self) -> list[ElementPlancher]:
        elements: list[ElementPlancher] = []
        niveau_bas = self.plancher.niveau_haut_traverses

        # Couche porteuse : cinq rangées de 600 mm alternent leurs joints
        # d'about. Les rangées impaires joignent sur la traverse centrale ; les
        # rangées paires sur les deux autres traverses intermédiaires.
        axes_traverses = self.plancher.axes_traverses()
        limites_centrales = (0.0, axes_traverses[2], 3_000.0)
        limites_laterales = (
            0.0,
            axes_traverses[1],
            axes_traverses[3],
            3_000.0,
        )
        index = 0
        for bande_y in range(5):
            limites_x = (
                limites_centrales if bande_y % 2 == 0 else limites_laterales
            )
            for debut_x, fin_x in zip(limites_x, limites_x[1:]):
                index += 1
                piece_inferieure = PanneauPlancherOSB(
                    epaisseur=22,
                    largeur=600,
                    longueur=round(fin_x - debut_x, 6),
                    materiau="OSB 3 R+L — couche porteuse inférieure",
                )
                elements.append(
                    ElementPlancher(
                        f"OSB inférieur {index:02d}",
                        piece_inferieure,
                        Pos(
                            debut_x,
                            -1_500 + bande_y * 600 + 300,
                            niveau_bas,
                        )
                        * piece_inferieure.construire(),
                        "darkorange",
                    )
                )

        # La couche supérieure est croisée à 90°. Son joint d'about alterne
        # entre deux axes de solives afin de supprimer toute charnière continue.
        axes_solives = self.plancher.axes_solives_i()
        joints_y = (axes_solives[7], axes_solives[1])
        index = 0
        for bande_x in range(5):
            joint_y = joints_y[bande_x % 2]
            for debut_y, fin_y in ((-1_500.0, joint_y), (joint_y, 1_500.0)):
                index += 1
                piece = PanneauPlancherOSB(
                    epaisseur=22,
                    largeur=600,
                    longueur=round(fin_y - debut_y, 6),
                    materiau="OSB 3 R+L — couche de répartition supérieure",
                )
                elements.append(
                    ElementPlancher(
                        f"OSB supérieur {index:02d}",
                        piece,
                        Pos(bande_x * 600 + 300, debut_y, niveau_bas + 22)
                        * Rot(0, 0, 90)
                        * piece.construire(),
                        "orangered",
                    )
                )
        return elements

    def elements(self) -> list[ElementPlancher]:
        return [
            *self.plancher.elements(),
            *self._elements_isolant(),
            *self._elements_osb(),
        ]

    def pieces_bom(self) -> list[Nomenclaturable]:
        pieces: list[Nomenclaturable] = [
            *self.plancher.pieces_bom(),
            *self._elements_isolant(),
            *self._elements_osb(),
            LotBOM(
                VisPlancherOSB5x60().article_bom(),
                self.nombre_vis_couche_inferieure,
            ),
            LotBOM(
                VisPlancherOSB5x80().article_bom(),
                self.nombre_vis_couche_superieure,
            ),
        ]
        return pieces

    def pieces_achat(self) -> list[Nomenclaturable]:
        pieces = [
            piece
            for piece in self.pieces_bom()
            if not piece.article_bom().reference.startswith(
                (
                    "OSB-PLANCHER-",
                    "OSB-FOND-",
                    "ISOL-DECOUPE-",
                )
            )
        ]
        dalle_plancher = DalleOSB(
            epaisseur=22,
            largeur=675,
            longueur=2_500,
            type_bords=TypeBordsOSB.RAINURE_LANGUETTE,
        )
        dalle_fonds_caissons = DalleOSB(
            epaisseur=12,
            largeur=1_196,
            longueur=2_800,
            type_bords=TypeBordsOSB.BORDS_DROITS,
        )
        isolant = PanneauIsonatFlex55(epaisseur=145)
        pieces.extend(
            (
                LotBOM(
                    dalle_plancher.article_bom(),
                    self.nombre_dalles_osb_achetees,
                ),
                LotBOM(
                    dalle_fonds_caissons.article_bom(),
                    self.plancher.nombre_dalles_brutes_osb_caissons,
                ),
                LotBOM(
                    isolant.article_bom(),
                    self.nombre_panneaux_isolant_achetes,
                ),
            )
        )
        return pieces

    def nomenclature(self) -> Nomenclature:
        return Nomenclature(self.pieces_bom())

    def nomenclature_achats(self) -> Nomenclature:
        return Nomenclature(self.pieces_achat())


def creer_local_batteries() -> LocalBatteries:
    """Construit la variante 3 × 3 m en réemployant les familles existantes."""
    geometrie = GeometriePlancherRectangulaire(
        largeur_interieure=3_000,
        longueur_interieure=3_000,
    )
    plancher = PlancherAFrame(
        geometrie,
        section_largeur=120,
        section_hauteur=240,
        nombre_traverses=5,
        entraxe_solives_i_max=300,
        hauteur_solives_i=240,
        largeur_membrure_solives_i=60,
        caissons_uniformes=True,
        inclure_connecteurs=True,
        inclure_solives_i=True,
        inclure_connecteurs_solives_i=True,
        inclure_osb_caissons=True,
        inclure_isolant_caissons=False,
        inclure_osb_plancher=False,
    )
    return LocalBatteries(plancher)
