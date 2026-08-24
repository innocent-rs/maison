"""Plancher très rigide de 9 m² pour le local batteries."""

from dataclasses import dataclass
from enum import StrEnum
from math import ceil

from build123d import Align, Box, Location

from home_framework.assemblage import (
    AssemblageContraint,
    InstructionAssemblage,
    PieceInstance,
)
from home_framework.geometrie import GeometriePlancherRectangulaire
from home_framework.nomenclature import (
    ArticleBOM,
    LotBOM,
    Nomenclature,
    Nomenclaturable,
)
from home_framework.structure import (
    DalleOSB,
    ElementPlancher,
    PanneauIsonatFlex55,
    PlancherBois,
    TypeBordsOSB,
    VisPlancherOSB5x60,
)
from home_framework.structure.panneaux import PanneauPlancherOSB

from .murs import MursLocalBatteries


@dataclass(frozen=True, slots=True)
class DecoupeIsonatLocalBatteries:
    """Découpe comprimée entre âmes, représentée à sa dimension de pose."""

    longueur_pose: float
    largeur_pose: float
    longueur_decoupe: float
    largeur_decoupe: float
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


class VariantePlancherLocal(StrEnum):
    """Deux niveaux explicites pour comparer sans perdre l'ancien POC."""

    OPTIMISEE = "optimisee"
    RENFORCEE = "renforcee"


@dataclass(frozen=True, slots=True)
class LocalBatteries:
    """Local technique monobloc, hors toiture et fondations."""

    plancher: PlancherBois
    murs: MursLocalBatteries
    charge_batteries_kg: float = 1_000.0
    variante_plancher: VariantePlancherLocal = VariantePlancherLocal.OPTIMISEE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "variante_plancher",
            VariantePlancherLocal(self.variante_plancher),
        )

        geometrie = self.plancher.geometrie
        if geometrie.largeur_interieure != 3_000:
            raise ValueError("le local batteries doit mesurer 3 000 mm de large")
        if geometrie.longueur_interieure != 3_000:
            raise ValueError("le local batteries doit mesurer 3 000 mm de long")
        if self.charge_batteries_kg <= 0:
            raise ValueError("la masse des batteries doit être positive")
        if not self.plancher.inclure_solives_i:
            raise ValueError("le plancher exige les poutres en I")
        if self.variante_plancher is VariantePlancherLocal.OPTIMISEE:
            if self.plancher.nombre_traverses != 2:
                raise ValueError("le plancher optimisé doit avoir deux traverses")
            if self.plancher.nombre_lignes_solives_i != 4:
                raise ValueError("le plancher optimisé doit avoir quatre solives")
            if self.plancher.entraxe_solives_i > 600:
                raise ValueError("l'entraxe optimisé ne doit pas dépasser 600 mm")
        elif self.variante_plancher is VariantePlancherLocal.RENFORCEE:
            if self.plancher.nombre_traverses != 5:
                raise ValueError("le plancher renforcé doit avoir cinq traverses")
            if self.plancher.entraxe_solives_i > 300:
                raise ValueError("l'entraxe renforcé ne doit pas dépasser 300 mm")
        if self.murs.niveau_sol != self.plancher.niveau_haut_traverses + 22:
            raise ValueError("les murs doivent reposer sur l'OSB porteur du plancher")

    @property
    def nombre_dalles_osb_achetees(self) -> int:
        return 7 if self.variante_plancher is VariantePlancherLocal.OPTIMISEE else 8

    @property
    def nombre_panneaux_isolant_achetes(self) -> int:
        return 12 if self.variante_plancher is VariantePlancherLocal.OPTIMISEE else 10

    @property
    def nombre_vis_osb_superieur(self) -> int:
        return 200 if self.variante_plancher is VariantePlancherLocal.OPTIMISEE else 600

    @property
    def geometrie(self) -> GeometriePlancherRectangulaire:
        return self.plancher.geometrie

    def _declarations_isolant(self) -> tuple[PieceInstance, ...]:
        """Déclare chaque découpe d'isolant sur son fond OSB porteur."""
        declarations: list[PieceInstance] = []
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
        operation = InstructionAssemblage(
            "isolant_caissons",
            "Remplir les caissons d'isolant",
            "Découper puis poser la fibre de bois sur les fonds OSB, caisson "
            "par caisson, sans vide périphérique et sans écraser l'épaisseur.",
            (
                "Surcote de pose : 10 mm lorsque la dimension du panneau le permet",
                "Épaisseur posée : 145 mm",
            ),
        )
        for travee, (axe_gauche, axe_droit) in enumerate(
            zip(axes_traverses, axes_traverses[1:]),
            start=1,
        ):
            debut_x = axe_gauche + demi_traverse
            fin_x = axe_droit - demi_traverse
            longueur_caisson = fin_x - debut_x
            nombre_segments = ceil(longueur_caisson / 1_220)
            longueurs_segments = (
                (longueur_caisson,)
                if nombre_segments == 1
                else (
                    *(1_220.0 for _ in range(nombre_segments - 1)),
                    longueur_caisson - 1_220 * (nombre_segments - 1),
                )
            )
            for caisson, (debut_y, fin_y) in enumerate(
                limites_caissons_y,
                start=1,
            ):
                reference = (
                    f"fond_osb_rive_gauche_{travee}"
                    if caisson == 1
                    else (
                        f"fond_osb_rive_droit_{travee}"
                        if caisson == len(limites_caissons_y)
                        else f"fond_osb_{caisson - 1:02d}_{travee}"
                    )
                )
                position_x = debut_x
                for segment, longueur_pose in enumerate(
                    longueurs_segments,
                    start=1,
                ):
                    largeur_pose = fin_y - debut_y
                    if self.variante_plancher is VariantePlancherLocal.RENFORCEE:
                        longueur_decoupe = 607.5
                        largeur_decoupe = 278.8
                    else:
                        longueur_decoupe = min(1_220.0, longueur_pose + 10)
                        largeur_decoupe = min(580.0, largeur_pose + 10)
                    piece = DecoupeIsonatLocalBatteries(
                        longueur_pose=round(longueur_pose, 6),
                        largeur_pose=round(largeur_pose, 6),
                        longueur_decoupe=round(longueur_decoupe, 6),
                        largeur_decoupe=round(largeur_decoupe, 6),
                    )
                    suffixe = "" if nombre_segments == 1 else f"_{segment}"
                    declarations.append(
                        PieceInstance.placer_sur(
                            f"isolant_local_{caisson:02d}_{travee}{suffixe}",
                            f"Isolant Isonat {caisson:02d}.{travee}.{segment}",
                            piece,
                            reference,
                            Location(
                                (
                                    position_x,
                                    (debut_y + fin_y) / 2,
                                    self.plancher.hauteur_membrure_solive_i
                                    + self.plancher.epaisseur_osb_caissons,
                                )
                            ),
                            "khaki",
                            operation=operation,
                        )
                    )
                    position_x += longueur_pose
        return tuple(declarations)

    def assemblage_plancher(self) -> AssemblageContraint:
        """Source unique de la CAO et du manuel jusqu'au plancher fini."""
        return AssemblageContraint.declarer(
            *self.plancher.declarations_assemblage(),
            *self._declarations_isolant(),
            *self._declarations_osb_plancher(),
        )

    def _declarations_osb_plancher(self) -> tuple[PieceInstance, ...]:
        """Déclare l'unique couche OSB et les caissons qu'elle recouvre."""
        if self.variante_plancher is VariantePlancherLocal.OPTIMISEE:
            return self._declarations_osb_plancher_optimisee()
        return self._declarations_osb_plancher_renforcee()

    def _declarations_osb_plancher_renforcee(self) -> tuple[PieceInstance, ...]:
        """Conserve le calepinage historique de la variante de comparaison."""
        declarations: list[PieceInstance] = []
        niveau_bas = self.plancher.niveau_haut_traverses

        def chevauche(
            rectangle_a: tuple[float, float, float, float],
            rectangle_b: tuple[float, float, float, float],
        ) -> bool:
            ax1, ax2, ay1, ay2 = rectangle_a
            bx1, bx2, by1, by2 = rectangle_b
            return min(ax2, bx2) - max(ax1, bx1) > 1e-6 and min(
                ay2, by2
            ) - max(ay1, by1) > 1e-6

        demi_traverse = self.plancher.section_largeur / 2
        demi_ame = self.plancher.epaisseur_ame_solive_i / 2
        axes_traverses = self.plancher.axes_traverses()
        axes_solives = self.plancher.axes_solives_i()
        face_rive_gauche = -1_500 + self.plancher.section_largeur
        face_rive_droite = 1_500 - self.plancher.section_largeur
        limites_caissons_y = (
            (face_rive_gauche, axes_solives[0] - demi_ame),
            *(
                (axe_gauche + demi_ame, axe_droit - demi_ame)
                for axe_gauche, axe_droit in zip(axes_solives, axes_solives[1:])
            ),
            (axes_solives[-1] + demi_ame, face_rive_droite),
        )
        rectangles_isolant = tuple(
            (
                f"isolant_local_{caisson:02d}_{travee}",
                (
                    axe_gauche + demi_traverse,
                    axe_droit - demi_traverse,
                    debut_y,
                    fin_y,
                ),
            )
            for travee, (axe_gauche, axe_droit) in enumerate(
                zip(axes_traverses, axes_traverses[1:]),
                start=1,
            )
            for caisson, (debut_y, fin_y) in enumerate(
                limites_caissons_y,
                start=1,
            )
        )

        operation_porteuse = InstructionAssemblage(
            "osb_porteur",
            "Poser la première couche OSB porteuse",
            "Poser les panneaux rainurés-languettés perpendiculairement aux "
            "solives. Alterner les joints d'about et les centrer sur les "
            "traverses avant vissage.",
            (
                "Tous les joints d'about doivent être portés par une traverse",
                f"Fixation totale : {self.nombre_vis_osb_superieur} vis 5×60",
            ),
        )

        # Couche porteuse : cinq rangées de 600 mm alternent leurs joints
        # d'about. Les rangées impaires joignent sur la traverse centrale ; les
        # rangées paires sur les deux autres traverses intermédiaires.
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
                debut_y = -1_500 + bande_y * 600
                rectangle = (debut_x, fin_x, debut_y, debut_y + 600)
                identifiant = f"osb_porteur_{index:02d}"
                isolants_recouverts = tuple(
                    identifiant_isolant
                    for identifiant_isolant, rectangle_isolant in rectangles_isolant
                    if chevauche(rectangle, rectangle_isolant)
                )
                index_traverse = min(
                    range(len(axes_traverses)),
                    key=lambda position: abs(axes_traverses[position] - debut_x),
                )
                declarations.append(
                    PieceInstance.placer_sur(
                        identifiant,
                        f"OSB porteur {index:02d}",
                        piece_inferieure,
                        f"traverse_{index_traverse + 1:02d}",
                        Location((debut_x, debut_y + 300, niveau_bas)),
                        "darkorange",
                        prerequis=isolants_recouverts,
                        operation=operation_porteuse,
                    )
                )
        return tuple(declarations)

    def _declarations_osb_plancher_optimisee(self) -> tuple[PieceInstance, ...]:
        """Pose sept dalles avec leur axe fort perpendiculaire aux solives.

        Les cinq bandes couvrent les 3 m suivant X. Leur unique joint d'about
        suivant Y tombe sur la dernière solive en I, ce qui permet de rester
        dans le format commercial 2 500 × 675 mm sans ajouter d'entretoise.
        """
        niveau = self.plancher.niveau_haut_traverses
        joint_y = self.plancher.axes_solives_i()[-1]
        longueurs_y = (joint_y + 1_500, 1_500 - joint_y)
        largeurs_x = (675.0, 675.0, 675.0, 675.0, 300.0)
        prerequis_isolant = tuple(
            declaration.identifiant for declaration in self._declarations_isolant()
        )
        operation = InstructionAssemblage(
            "osb_porteur",
            "Poser l'unique couche OSB porteuse",
            "Poser les dalles R+L de 22 mm avec leur grand axe suivant Y, "
            "donc perpendiculaire aux solives en I. Porter l'unique ligne de "
            "joints d'about sur la solive repérée dans la CAO.",
            (
                f"Joint porté sur l'axe Y = {joint_y:g} mm",
                "Entraxe maximal des solives : 600 mm",
                f"Fixation totale budgétée : {self.nombre_vis_osb_superieur} vis 5×60",
            ),
        )
        declarations: list[PieceInstance] = []
        index = 0
        debut_x = 0.0
        for largeur_x in largeurs_x:
            debut_y = -1_500.0
            for longueur_y in longueurs_y:
                index += 1
                piece = PanneauPlancherOSB(
                    epaisseur=22,
                    largeur=largeur_x,
                    longueur=round(longueur_y, 6),
                    materiau="OSB 3 R+L — couche porteuse unique",
                )
                declarations.append(
                    PieceInstance.placer_sur(
                        f"osb_porteur_{index:02d}",
                        f"OSB porteur {index:02d}",
                        piece,
                        "traverse_01",
                        Location(
                            (debut_x + largeur_x / 2, debut_y, niveau),
                            (0, 0, 90),
                        ),
                        "darkorange",
                        prerequis=prerequis_isolant,
                        operation=operation,
                    )
                )
                debut_y += longueur_y
            debut_x += largeur_x
        return tuple(declarations)

    def elements(self) -> list[ElementPlancher]:
        return [
            *self.assemblage_plancher().pieces,
            *self.murs.elements(),
        ]

    def pieces_bom_plancher(self) -> list[Nomenclaturable]:
        """Pièces de fabrication du seul plancher."""
        return [
            *self.assemblage_plancher().pieces,
            *self.plancher.lots_fixations(),
            LotBOM(
                VisPlancherOSB5x60().article_bom(),
                self.nombre_vis_osb_superieur,
            ),
        ]

    def pieces_bom(self) -> list[Nomenclaturable]:
        return [*self.pieces_bom_plancher(), *self.murs.pieces_bom()]

    def pieces_achat_plancher(self) -> list[Nomenclaturable]:
        """Achats du plancher, découpes remplacées par produits bruts."""
        pieces = [
            piece
            for piece in self.pieces_bom_plancher()
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

    def pieces_achat(self) -> list[Nomenclaturable]:
        return [*self.pieces_achat_plancher(), *self.murs.pieces_achat()]

    def nomenclature(self) -> Nomenclature:
        return Nomenclature(self.pieces_bom())

    def nomenclature_achats(self) -> Nomenclature:
        return Nomenclature(self.pieces_achat())

    def nomenclature_achats_plancher(self) -> Nomenclature:
        return Nomenclature(self.pieces_achat_plancher())

    def nomenclature_achats_murs(self) -> Nomenclature:
        return Nomenclature(self.murs.pieces_achat())


def _creer_local_batteries(variante: VariantePlancherLocal) -> LocalBatteries:
    """Construit une variante depuis la même définition déclarative."""
    geometrie = GeometriePlancherRectangulaire(
        largeur_interieure=3_000,
        longueur_interieure=3_000,
    )
    optimisee = variante is VariantePlancherLocal.OPTIMISEE
    plancher = PlancherBois(
        geometrie,
        section_largeur=120,
        section_hauteur=240,
        nombre_traverses=2 if optimisee else 5,
        entraxe_solives_i_max=600 if optimisee else 300,
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
    murs = MursLocalBatteries(
        niveau_sol=plancher.niveau_haut_traverses + 22,
    )
    return LocalBatteries(plancher, murs, variante_plancher=variante)


def creer_local_batteries() -> LocalBatteries:
    """Construit le local simple optimisé, variante de référence du projet."""
    return _creer_local_batteries(VariantePlancherLocal.OPTIMISEE)


def creer_local_batteries_renforce() -> LocalBatteries:
    """Reconstruit l'ancien plancher en grille pour le comparatif de coût."""
    return _creer_local_batteries(VariantePlancherLocal.RENFORCEE)
