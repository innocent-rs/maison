"""Plancher très rigide de 9 m² pour le local batteries."""

from dataclasses import dataclass

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
    VisPlancherOSB5x80,
)
from home_framework.structure.panneaux import PanneauPlancherOSB

from .murs import MursLocalBatteries


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
    """Local technique monobloc, hors toiture et fondations."""

    plancher: PlancherBois
    murs: MursLocalBatteries
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
        if self.murs.niveau_sol != self.plancher.niveau_haut_traverses + 44:
            raise ValueError("les murs doivent reposer sur la double peau du plancher")

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
                "Découpe : 607,5 × 278,8 mm avant compression de pose",
                "Épaisseur posée : 145 mm",
            ),
        )
        for travee, (axe_gauche, axe_droit) in enumerate(
            zip(axes_traverses, axes_traverses[1:]),
            start=1,
        ):
            debut_x = axe_gauche + demi_traverse
            fin_x = axe_droit - demi_traverse
            for caisson, (debut_y, fin_y) in enumerate(
                limites_caissons_y,
                start=1,
            ):
                piece = DecoupeIsonatLocalBatteries(
                    longueur_pose=round(fin_x - debut_x, 6),
                    largeur_pose=round(fin_y - debut_y, 6),
                )
                reference = (
                    f"fond_osb_rive_gauche_{travee}"
                    if caisson == 1
                    else (
                        f"fond_osb_rive_droit_{travee}"
                        if caisson == len(limites_caissons_y)
                        else f"fond_osb_{caisson - 1:02d}_{travee}"
                    )
                )
                declarations.append(
                    PieceInstance.placer_sur(
                        f"isolant_local_{caisson:02d}_{travee}",
                        f"Isolant Isonat {caisson:02d}.{travee}",
                        piece,
                        reference,
                        Location(
                            (
                                debut_x,
                                (debut_y + fin_y) / 2,
                                self.plancher.hauteur_membrure_solive_i
                                + self.plancher.epaisseur_osb_caissons,
                            )
                        ),
                        "khaki",
                        operation=operation,
                    )
                )
        return tuple(declarations)

    def assemblage_plancher(self) -> AssemblageContraint:
        """Source unique de la CAO et du manuel jusqu'au plancher fini."""
        return AssemblageContraint.declarer(
            *self.plancher.declarations_assemblage(),
            *self._declarations_isolant(),
            *self._declarations_osb_superieur(),
        )

    def _declarations_osb_superieur(self) -> tuple[PieceInstance, ...]:
        """Déclare les deux couches OSB et leurs recouvrements réels."""
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
                f"Fixation totale : {self.nombre_vis_couche_inferieure} vis 5×60",
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
        panneaux_porteurs: list[
            tuple[str, tuple[float, float, float, float]]
        ] = []
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
                panneaux_porteurs.append((identifiant, rectangle))
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
                        f"OSB inférieur {index:02d}",
                        piece_inferieure,
                        f"traverse_{index_traverse + 1:02d}",
                        Location((debut_x, debut_y + 300, niveau_bas)),
                        "darkorange",
                        prerequis=isolants_recouverts,
                        operation=operation_porteuse,
                    )
                )

        operation_repartition = InstructionAssemblage(
            "osb_repartition",
            "Poser la couche OSB croisée",
            "Tourner la seconde couche de 90° et alterner ses joints d'about "
            "sur deux axes de solives afin de supprimer toute charnière "
            "continue entre les couches.",
            (
                "Orientation croisée à 90° par rapport à la couche porteuse",
                "Tous les joints d'about doivent être portés par une solive",
                f"Fixation totale : {self.nombre_vis_couche_superieure} vis 5×80",
            ),
        )

        # La couche supérieure est croisée à 90°. Son joint d'about alterne
        # entre deux axes de solives afin de supprimer toute charnière continue.
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
                debut_x = bande_x * 600
                rectangle = (debut_x, debut_x + 600, debut_y, fin_y)
                porteurs_recouverts = tuple(
                    identifiant_porteur
                    for identifiant_porteur, rectangle_porteur in panneaux_porteurs
                    if chevauche(rectangle, rectangle_porteur)
                )
                declarations.append(
                    PieceInstance.placer_sur(
                        f"osb_repartition_{index:02d}",
                        f"OSB supérieur {index:02d}",
                        piece,
                        porteurs_recouverts[0],
                        Location(
                            (debut_x + 300, debut_y, niveau_bas + 22),
                            (0, 0, 90),
                        ),
                        "orangered",
                        prerequis=porteurs_recouverts[1:],
                        operation=operation_repartition,
                    )
                )
        return tuple(declarations)

    def elements(self) -> list[ElementPlancher]:
        return [
            *self.assemblage_plancher().pieces,
            *self.murs.elements(),
        ]

    def pieces_bom(self) -> list[Nomenclaturable]:
        pieces: list[Nomenclaturable] = [
            *self.assemblage_plancher().pieces,
            *self.plancher.lots_fixations(),
            *self.murs.pieces_bom(),
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
                    "OSB-MUR-",
                    "ISOL-DECOUPE-",
                    "ISOL-MUR-",
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
                    self.plancher.nombre_dalles_brutes_osb_caissons
                    + self.murs.nombre_panneaux_osb_achetes,
                ),
                LotBOM(
                    isolant.article_bom(),
                    self.nombre_panneaux_isolant_achetes
                    + self.murs.nombre_panneaux_isolant_achetes,
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
    plancher = PlancherBois(
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
    murs = MursLocalBatteries(
        niveau_sol=plancher.niveau_haut_traverses + 2 * 22,
    )
    return LocalBatteries(plancher, murs)
