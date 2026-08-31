"""Structure paramétrique réutilisable d'un plancher bois."""

from dataclasses import dataclass
from itertools import pairwise
from math import ceil, isclose
from build123d import Align, Box, Location, Pos, Rot, Shape

from home_framework.assemblage import (
    AssemblageContraint,
    InstructionAssemblage,
    PieceInstance,
    PiecePlacee,
    TrameEntreFaces,
)
from home_framework.geometrie import GeometriePlancher
from home_framework.nomenclature import LotBOM, Nomenclaturable
from home_framework.structure.bois import (
    EntretoisePoutreI,
    Madrier,
    PoutreI,
    Tasseau,
)
from home_framework.structure.connecteurs import (
    PlanFixationEWH,
    PlanFixationSAI,
    PointeAncrageCNA4x35,
    PointeEntretoise2_5x80,
    PointeEntretoise3_1x90,
    SabotEWH,
    SabotSAI500_120_2,
    VisBoisOSB4x35,
    VisConnecteurCSA5x40,
    VisPlancherOSB5x60,
    VisTasseauKlimas6x160,
)
from home_framework.structure.isolation import PanneauIsonatFlex55
from home_framework.structure.panneaux import (
    DalleOSB,
    PanneauFondCaissonOSB,
    PanneauPlancherOSB,
    TypeBordsOSB,
)


ElementPlancher = PiecePlacee


@dataclass(frozen=True, slots=True)
class PlancherBois:
    """Châssis primaire : deux poutres longitudinales et des traverses.

    Il s'agit d'une géométrie de conception, pas encore d'un dimensionnement
    structurel. Les sections devront être validées selon les portées, charges,
    assemblages et la classe du bois. Les solives en I sont longitudinales et
    réparties entre les traverses successives. Chaque about est suspendu à une
    traverse massive par un étrier EWH.
    """

    geometrie: GeometriePlancher
    section_largeur: float = 120.0
    section_hauteur: float = 240.0
    nombre_traverses: int = 3
    entraxe_solives_i_max: float = 500.0
    trame_isolant_sans_decoupe: bool = False
    caissons_uniformes: bool = False
    inclure_connecteurs: bool = True
    plan_fixation_sai: PlanFixationSAI = PlanFixationSAI.TOTAL
    inclure_solives_i: bool = False
    inclure_entretoises_solives_i: bool = False
    nombre_rangees_entretoises_par_travee: int = 1
    inclure_connecteurs_solives_i: bool = True
    plan_fixation_ewh: PlanFixationEWH = PlanFixationEWH.BRIDES_SUPERIEURES
    hauteur_solives_i: float = 240.0
    largeur_membrure_solives_i: float = 60.0
    jeu_about_solives_i: float = 3.0
    inclure_osb_caissons: bool = False
    inclure_isolant_caissons: bool = False
    inclure_osb_plancher: bool = False
    epaisseur_osb_caissons: float = 12.0
    epaisseur_isolant_nominale: float = 145.0
    epaisseur_osb_plancher: float = 22.0
    jeu_joint_osb: float = 3.0
    entraxe_vis_osb: float = 150.0
    retrait_extremite_vis_osb: float = 100.0
    hauteur_tasseaux_rive: float = 40.0
    entraxe_vis_tasseaux_rive: float = 300.0
    retrait_extremite_vis_tasseaux_rive: float = 100.0
    largeur_dalle_osb_caissons: float = 1_196.0
    longueur_dalle_osb_caissons: float = 2_800.0
    largeur_dalle_osb_plancher: float = 675.0
    longueur_dalle_osb_plancher: float = 2_500.0
    entraxe_vis_bord_osb_plancher: float = 150.0
    entraxe_vis_appui_osb_plancher: float = 300.0
    retrait_coin_vis_osb_plancher: float = 25.0
    axes_reservations_pieds: tuple[float, ...] = ()
    largeur_reservation_pied: float = 120.0
    profondeur_reservation_pied: float = 120.0

    def __post_init__(self) -> None:
        if min(
            self.section_largeur,
            self.section_hauteur,
            self.entraxe_solives_i_max,
            self.hauteur_solives_i,
            self.largeur_membrure_solives_i,
            self.epaisseur_osb_caissons,
            self.epaisseur_isolant_nominale,
            self.epaisseur_osb_plancher,
            self.entraxe_vis_osb,
            self.retrait_extremite_vis_osb,
            self.hauteur_tasseaux_rive,
            self.entraxe_vis_tasseaux_rive,
            self.retrait_extremite_vis_tasseaux_rive,
            self.largeur_dalle_osb_caissons,
            self.longueur_dalle_osb_caissons,
            self.largeur_dalle_osb_plancher,
            self.longueur_dalle_osb_plancher,
            self.entraxe_vis_bord_osb_plancher,
            self.entraxe_vis_appui_osb_plancher,
            self.retrait_coin_vis_osb_plancher,
            self.largeur_reservation_pied,
            self.profondeur_reservation_pied,
        ) <= 0:
            raise ValueError("les sections doivent être strictement positives")
        if self.nombre_traverses < 2:
            raise ValueError("le châssis doit comporter au moins deux traverses")
        if self.geometrie.largeur_interieure <= 2 * self.section_largeur:
            raise ValueError("la largeur est insuffisante pour les poutres de rive")
        if not 0 <= self.jeu_about_solives_i <= 3:
            raise ValueError("le jeu aux abouts des solives doit être compris entre 0 et 3 mm")
        if not 0 <= self.jeu_joint_osb <= 3:
            raise ValueError("le jeu entre panneaux OSB doit être compris entre 0 et 3 mm")
        if self.inclure_osb_caissons and not self.inclure_solives_i:
            raise ValueError("les fonds de caisson exigent les solives en I")
        if self.inclure_entretoises_solives_i and not self.inclure_solives_i:
            raise ValueError("les entretoises exigent les solives en I")
        if self.nombre_rangees_entretoises_par_travee < 1:
            raise ValueError("le nombre de rangées d'entretoises doit être positif")
        if self.inclure_entretoises_solives_i and (
            self.longueur_compartiment_isolant <= 0
            or self.longueur_segment_osb_caisson <= 0
        ):
            raise ValueError("les entretoises ne laissent plus de caisson disponible")
        if self.inclure_isolant_caissons and not self.inclure_osb_caissons:
            raise ValueError("l'isolant exige les fonds de caisson OSB")
        if self.inclure_osb_plancher and not self.inclure_solives_i:
            raise ValueError("le plancher OSB exige les solives en I")
        if self.trame_isolant_sans_decoupe:
            _ = self.nombre_lignes_solives_i
            if self.entraxe_solives_i > self.entraxe_solives_i_max + 1e-6:
                raise ValueError("la trame isolant dépasse l'entraxe maximal")
        if self.inclure_isolant_caissons:
            panneau_isolant = PanneauIsonatFlex55(
                epaisseur=self.epaisseur_isolant_nominale,
            )
            if self.largeur_caisson_isolant > panneau_isolant.largeur + 1e-6:
                raise ValueError(
                    "un caisson est trop large pour un panneau isolant entier"
                )
            if not 0 < panneau_isolant.epaisseur <= self.hauteur_caisson_isolant:
                raise ValueError(
                    "la hauteur des caissons est incompatible avec l'isolant"
                )
        if self.inclure_osb_plancher:
            if self.epaisseur_osb_plancher != 22:
                raise ValueError("le plancher courant est défini en OSB de 22 mm")
            _ = self.decoupes_osb_plancher()
        if self.inclure_solives_i and self.inclure_connecteurs_solives_i:
            etrier = SabotEWH(
                largeur_interieure=self.largeur_membrure_solives_i + 1,
                hauteur=self.hauteur_solives_i,
            )
            if self.hauteur_solives_i not in (240, 300):
                raise ValueError(
                    "le plan courant accepte une STEICOjoist SJ60 de 240 ou 300 mm"
                )
            largeur_membrure = PoutreI(
                longueur=1,
                hauteur=self.hauteur_solives_i,
                largeur_membrure=self.largeur_membrure_solives_i,
            ).largeur_membrure
            if not etrier.accepte_largeur_poutre(largeur_membrure):
                raise ValueError("le EWH est incompatible avec la poutre en I")

    @property
    def entraxe_traverses(self) -> float:
        """Distance entre les axes des traverses successives."""
        axes = self.axes_traverses()
        return axes[1] - axes[0]

    def axes_traverses(self) -> tuple[float, ...]:
        """Axes X régulièrement espacés, sabots maintenus dans l'emprise."""
        demi_section = self.section_largeur / 2
        retrait_extremites = self.retrait_connecteur_par_about
        longueur = self.geometrie.longueur_interieure
        premier = demi_section + retrait_extremites
        dernier = longueur - demi_section - retrait_extremites
        entraxe = (dernier - premier) / (self.nombre_traverses - 1)
        return tuple(
            premier + index * entraxe for index in range(self.nombre_traverses)
        )

    @property
    def nombre_intervalles_solives_i(self) -> int:
        """Nombre d'intervalles entre les deux poutres longitudinales."""
        if self.trame_isolant_sans_decoupe:
            return self._nombre_lignes_solives_modulaires() + 1
        if not self.caissons_uniformes:
            distance_entre_axes = (
                self.geometrie.largeur_interieure - self.section_largeur
            )
            return ceil(distance_entre_axes / self.entraxe_solives_i_max)
        distance_entre_faces = (
            self.geometrie.largeur_interieure - 2 * self.section_largeur
        )
        return ceil(
            (distance_entre_faces + self.epaisseur_ame_solive_i)
            / self.entraxe_solives_i_max
        )

    @property
    def nombre_lignes_solives_i(self) -> int:
        """Nombre de lignes longitudinales, hors poutres de rive."""
        if self.trame_isolant_sans_decoupe:
            return self._nombre_lignes_solives_modulaires()
        return self.nombre_intervalles_solives_i - 1

    @property
    def nombre_solives_i(self) -> int:
        """Nombre de segments sur toutes les lignes et toutes les travées."""
        return self.nombre_lignes_solives_i * (self.nombre_traverses - 1)

    @property
    def nombre_entretoises_solives_i(self) -> int:
        """Nombre de blocs pleine hauteur répartis dans toutes les travées."""
        if not self.inclure_entretoises_solives_i:
            return 0
        return (
            self.nombre_intervalles_solives_i
            * (self.nombre_traverses - 1)
            * self.nombre_rangees_entretoises_par_travee
        )

    @property
    def nombre_pointes_entretoises_2_5x80(self) -> int:
        """Deux pointes par bloc, une de chaque côté de l'âme."""
        return 2 * self.nombre_entretoises_solives_i

    @property
    def nombre_pointes_entretoises_3_1x90(self) -> int:
        """Deux pointes par bloc, une par membrure."""
        return 2 * self.nombre_entretoises_solives_i

    @property
    def entraxe_solives_i(self) -> float:
        if self.trame_isolant_sans_decoupe:
            return self.largeur_caisson_isolant + self.epaisseur_ame_solive_i
        if not self.caissons_uniformes:
            distance_entre_axes = (
                self.geometrie.largeur_interieure - self.section_largeur
            )
            return distance_entre_axes / self.nombre_intervalles_solives_i
        return self.largeur_caisson_isolant + self.epaisseur_ame_solive_i

    @property
    def epaisseur_ame_solive_i(self) -> float:
        return PoutreI(
            longueur=1,
            hauteur=self.hauteur_solives_i,
            largeur_membrure=self.largeur_membrure_solives_i,
        ).epaisseur_ame

    @property
    def largeur_membrure_solive_i(self) -> float:
        return PoutreI(
            longueur=1,
            hauteur=self.hauteur_solives_i,
            largeur_membrure=self.largeur_membrure_solives_i,
        ).largeur_membrure

    @property
    def hauteur_membrure_solive_i(self) -> float:
        return PoutreI(
            longueur=1,
            hauteur=self.hauteur_solives_i,
            largeur_membrure=self.largeur_membrure_solives_i,
        ).hauteur_membrure

    @property
    def largeur_caisson_isolant(self) -> float:
        if self.trame_isolant_sans_decoupe:
            return PanneauIsonatFlex55().largeur_pose
        if not self.caissons_uniformes:
            return PanneauIsonatFlex55().largeur_pose
        distance_entre_faces = (
            self.geometrie.largeur_interieure - 2 * self.section_largeur
        )
        return (
            distance_entre_faces
            - self.nombre_lignes_solives_i * self.epaisseur_ame_solive_i
        ) / self.nombre_intervalles_solives_i

    @property
    def decalage_premiere_solive_modulaire(self) -> float:
        return (
            self.section_largeur / 2
            + self.largeur_caisson_isolant
            + self.epaisseur_ame_solive_i / 2
        )

    def _nombre_lignes_solives_modulaires(self) -> int:
        distance_entre_axes_rive = (
            self.geometrie.largeur_interieure - self.section_largeur
        )
        distance_entre_premiere_derniere = (
            distance_entre_axes_rive - 2 * self.decalage_premiere_solive_modulaire
        )
        nombre_intervalles = round(
            distance_entre_premiere_derniere / self.entraxe_solives_i
        )
        if nombre_intervalles < 1 or not isclose(
            distance_entre_premiere_derniere,
            nombre_intervalles * self.entraxe_solives_i,
            abs_tol=1e-6,
        ):
            raise ValueError(
                "la largeur du plancher n'est pas compatible avec la trame isolant"
            )
        return nombre_intervalles + 1

    @property
    def niveau_haut_traverses(self) -> float:
        return self.section_hauteur

    @property
    def retrait_connecteur_par_about(self) -> float:
        """Épaisseur de tôle interposée à chaque about de traverse."""
        return SabotSAI500_120_2().epaisseur if self.inclure_connecteurs else 0

    @property
    def longueur_traverses(self) -> float:
        distance_entre_faces = (
            self.geometrie.largeur_interieure - 2 * self.section_largeur
        )
        return distance_entre_faces - 2 * self.retrait_connecteur_par_about

    @property
    def nombre_sabots(self) -> int:
        """Compatibilité : nombre de sabots SAI du châssis primaire."""
        return 2 * self.nombre_traverses if self.inclure_connecteurs else 0

    @property
    def nombre_vis_connecteurs(self) -> int:
        """Compatibilité : nombre de CSA des six sabots SAI."""
        if not self.inclure_connecteurs:
            return 0
        sabot = SabotSAI500_120_2()
        return self.nombre_sabots * sabot.nombre_fixations(self.plan_fixation_sai)

    @property
    def jeu_ewh_par_about(self) -> float:
        """Jeu de pose entre l'about de solive et la face de la traverse."""
        if not (self.inclure_solives_i and self.inclure_connecteurs_solives_i):
            return 0
        return self.jeu_about_solives_i

    @property
    def longueur_solives_i(self) -> float:
        distance_entre_faces = self.entraxe_traverses - self.section_largeur
        return distance_entre_faces - 2 * self.jeu_ewh_par_about

    @property
    def nombre_sabots_ewh(self) -> int:
        if not (self.inclure_solives_i and self.inclure_connecteurs_solives_i):
            return 0
        return 2 * self.nombre_solives_i

    @property
    def nombre_pointes_ewh(self) -> int:
        sabot = SabotEWH(
            largeur_interieure=self.largeur_membrure_solives_i + 1,
            hauteur=self.hauteur_solives_i,
        )
        return self.nombre_sabots_ewh * sabot.nombre_pointes(self.plan_fixation_ewh)

    @property
    def largeur_panneaux_osb_caissons(self) -> float:
        distance_entre_ames = self.entraxe_solives_i - self.epaisseur_ame_solive_i
        return distance_entre_ames - self.jeu_joint_osb

    @property
    def largeur_panneaux_osb_rive(self) -> float:
        """Largeur entre la poutre de rive et l'âme de la première solive."""
        if self.trame_isolant_sans_decoupe or self.caissons_uniformes:
            return self.largeur_caisson_isolant - self.jeu_joint_osb
        distance_face_ame = (
            self.entraxe_solives_i
            - self.section_largeur / 2
            - self.epaisseur_ame_solive_i / 2
        )
        return distance_face_ame - self.jeu_joint_osb

    @property
    def nombre_panneaux_osb_interieurs(self) -> int:
        if not self.inclure_osb_caissons:
            return 0
        nombre_interstices = self.nombre_lignes_solives_i - 1
        return (
            nombre_interstices
            * (self.nombre_traverses - 1)
            * self.nombre_segments_osb_par_caisson
        )

    @property
    def nombre_panneaux_osb_rive(self) -> int:
        if not self.inclure_osb_caissons:
            return 0
        return (
            2
            * (self.nombre_traverses - 1)
            * self.nombre_segments_osb_par_caisson
        )

    @property
    def nombre_panneaux_osb_caissons(self) -> int:
        return self.nombre_panneaux_osb_interieurs + self.nombre_panneaux_osb_rive

    @property
    def nombre_segments_osb_par_caisson(self) -> int:
        if not self.inclure_entretoises_solives_i:
            return 1
        return self.nombre_rangees_entretoises_par_travee + 1

    @property
    def largeur_joint_osb_entretoise(self) -> float:
        return self.epaisseur_ame_solive_i + self.jeu_joint_osb

    @property
    def longueur_segment_osb_caisson(self) -> float:
        largeur_joints = (
            self.nombre_rangees_entretoises_par_travee
            * self.largeur_joint_osb_entretoise
            if self.inclure_entretoises_solives_i
            else 0
        )
        return (
            self.longueur_solives_i - largeur_joints
        ) / self.nombre_segments_osb_par_caisson

    def decalages_segments_osb_caisson(self) -> tuple[float, ...]:
        return tuple(
            segment
            * (self.longueur_segment_osb_caisson + self.largeur_joint_osb_entretoise)
            for segment in range(self.nombre_segments_osb_par_caisson)
        )

    def rendement_dalle_osb_caissons(self, largeur_decoupe: float) -> int:
        """Nombre de fonds rectangulaires débitables dans un panneau brut."""
        rendement = max(
            int(self.largeur_dalle_osb_caissons // largeur_decoupe)
            * int(self.longueur_dalle_osb_caissons // self.longueur_segment_osb_caisson),
            int(self.largeur_dalle_osb_caissons // self.longueur_segment_osb_caisson)
            * int(self.longueur_dalle_osb_caissons // largeur_decoupe),
        )
        if rendement < 1:
            raise ValueError("une découpe de fond de caisson dépasse la dalle OSB")
        return rendement

    @property
    def nombre_dalles_brutes_osb_caissons(self) -> int:
        """Budget conservateur de dalles, calculé par famille de largeur."""
        if not self.inclure_osb_caissons:
            return 0
        interieur = ceil(
            self.nombre_panneaux_osb_interieurs
            / self.rendement_dalle_osb_caissons(
                self.largeur_panneaux_osb_caissons
            )
        )
        rive = ceil(
            self.nombre_panneaux_osb_rive
            / self.rendement_dalle_osb_caissons(self.largeur_panneaux_osb_rive)
        )
        return interieur + rive

    @property
    def nombre_tasseaux_rive(self) -> int:
        if not self.inclure_osb_caissons:
            return 0
        return 2 * (self.nombre_traverses - 1)

    @property
    def nombre_vis_par_tasseau_rive(self) -> int:
        longueur_vissable = (
            self.longueur_solives_i
            - 2 * self.retrait_extremite_vis_tasseaux_rive
        )
        intervalles = ceil(longueur_vissable / self.entraxe_vis_tasseaux_rive)
        return intervalles + 1

    @property
    def nombre_vis_tasseaux_rive(self) -> int:
        return self.nombre_tasseaux_rive * self.nombre_vis_par_tasseau_rive

    @property
    def nombre_vis_par_panneau_osb(self) -> int:
        longueur_vissable = (
            self.longueur_segment_osb_caisson - 2 * self.retrait_extremite_vis_osb
        )
        intervalles = ceil(longueur_vissable / self.entraxe_vis_osb)
        return 2 * (intervalles + 1)

    @property
    def nombre_vis_osb(self) -> int:
        return self.nombre_panneaux_osb_caissons * self.nombre_vis_par_panneau_osb

    @property
    def nombre_panneaux_isolant(self) -> int:
        if not self.inclure_isolant_caissons:
            return 0
        return (
            self.nombre_intervalles_solives_i
            * (self.nombre_traverses - 1)
            * self.nombre_segments_isolant_par_caisson
        )

    @property
    def nombre_segments_isolant_par_caisson(self) -> int:
        return (
            self.nombre_compartiments_isolant_par_caisson
            * self.nombre_segments_isolant_par_compartiment
        )

    @property
    def nombre_compartiments_isolant_par_caisson(self) -> int:
        if not self.inclure_entretoises_solives_i:
            return 1
        return self.nombre_rangees_entretoises_par_travee + 1

    @property
    def largeur_rangee_entretoises(self) -> float:
        """Emprise suivant X d'une rangée, égale à la largeur des membrures."""
        return self.largeur_membrure_solives_i

    @property
    def longueur_compartiment_isolant(self) -> float:
        largeur_entretoises = (
            self.nombre_rangees_entretoises_par_travee
            * self.largeur_rangee_entretoises
            if self.inclure_entretoises_solives_i
            else 0
        )
        return (
            self.longueur_caisson_isolant - largeur_entretoises
        ) / self.nombre_compartiments_isolant_par_caisson

    @property
    def nombre_segments_isolant_par_compartiment(self) -> int:
        longueur_panneau = PanneauIsonatFlex55(
            epaisseur=self.epaisseur_isolant_nominale,
        ).longueur
        return ceil(self.longueur_compartiment_isolant / longueur_panneau)

    @property
    def longueur_segment_isolant(self) -> float:
        return (
            self.longueur_compartiment_isolant
            / self.nombre_segments_isolant_par_compartiment
        )

    def decalages_segments_isolant(self) -> tuple[float, ...]:
        """Départs X relatifs des panneaux, en sautant les entretoises."""
        return tuple(
            compartiment
            * (self.longueur_compartiment_isolant + self.largeur_rangee_entretoises)
            + segment * self.longueur_segment_isolant
            for compartiment in range(self.nombre_compartiments_isolant_par_caisson)
            for segment in range(self.nombre_segments_isolant_par_compartiment)
        )

    @property
    def largeur_decoupe_isolant(self) -> float:
        """Largeur coupée avec la surcote de pose de 10 mm prescrite."""
        panneau = PanneauIsonatFlex55(epaisseur=self.epaisseur_isolant_nominale)
        return min(panneau.largeur, self.largeur_caisson_isolant + 10)

    @property
    def longueur_decoupe_segment_isolant(self) -> float:
        """Longueur coupée avec la surcote de pose de 10 mm prescrite."""
        panneau = PanneauIsonatFlex55(epaisseur=self.epaisseur_isolant_nominale)
        return min(panneau.longueur, self.longueur_segment_isolant + 10)

    @property
    def longueur_caisson_isolant(self) -> float:
        """Distance libre entre les faces de deux traverses."""
        return self.entraxe_traverses - self.section_largeur

    @property
    def hauteur_caisson_isolant(self) -> float:
        """Hauteur entre l'OSB et le dessous de la membrure haute."""
        niveau_bas_solives = self.niveau_haut_traverses - self.hauteur_solives_i
        niveau_haut_osb = (
            niveau_bas_solives
            + self.hauteur_membrure_solive_i
            + self.epaisseur_osb_caissons
        )
        niveau_sous_membrure_haute = (
            self.niveau_haut_traverses - self.hauteur_membrure_solive_i
        )
        return niveau_sous_membrure_haute - niveau_haut_osb

    def axes_solives_i(self) -> tuple[float, ...]:
        """Axes Y des lignes de solivage longitudinales."""
        axe_poutre_gauche = (
            -self.geometrie.largeur_interieure / 2 + self.section_largeur / 2
        )
        if self.trame_isolant_sans_decoupe:
            premier_axe = axe_poutre_gauche + self.decalage_premiere_solive_modulaire
            return tuple(
                premier_axe + index * self.entraxe_solives_i
                for index in range(self.nombre_lignes_solives_i)
            )
        if self.caissons_uniformes:
            face_interieure_gauche = (
                -self.geometrie.largeur_interieure / 2 + self.section_largeur
            )
            premier_axe = (
                face_interieure_gauche
                + self.largeur_caisson_isolant
                + self.epaisseur_ame_solive_i / 2
            )
            return tuple(
                premier_axe + index * self.entraxe_solives_i
                for index in range(self.nombre_lignes_solives_i)
            )
        return tuple(
            axe_poutre_gauche + index * self.entraxe_solives_i
            for index in range(1, self.nombre_intervalles_solives_i)
        )

    def intervalles_entretoises_solives_i(
        self,
    ) -> tuple[tuple[float, float], ...]:
        """Faces Y entre lesquelles sont coupées les entretoises."""
        demi_membrure = self.largeur_membrure_solives_i / 2
        largeur = self.geometrie.largeur_interieure
        face_interieure_gauche = -largeur / 2 + self.section_largeur
        face_interieure_droite = largeur / 2 - self.section_largeur
        axes = self.axes_solives_i()
        faces_debut = (face_interieure_gauche, *(axe + demi_membrure for axe in axes))
        faces_fin = (*(axe - demi_membrure for axe in axes), face_interieure_droite)
        return tuple(zip(faces_debut, faces_fin))

    def decalages_rangees_entretoises(self) -> tuple[float, ...]:
        """Axes X relatifs des rangées dans une travée."""
        if not self.inclure_entretoises_solives_i:
            return ()
        return tuple(
            (rangee + 1) * self.longueur_compartiment_isolant
            + (rangee + 0.5) * self.largeur_rangee_entretoises
            for rangee in range(self.nombre_rangees_entretoises_par_travee)
        )

    def debuts_travees_solives_i(self) -> tuple[float, ...]:
        """Faces de départ X des travées successives, retrait EWH inclus."""
        demi_section = self.section_largeur / 2
        return tuple(
            axe + demi_section + self.jeu_ewh_par_about
            for axe in self.axes_traverses()[:-1]
        )

    def debuts_panneaux_isolant(self) -> tuple[float, ...]:
        """Faces X des traverses depuis lesquelles partent les panneaux entiers."""
        demi_section = self.section_largeur / 2
        return tuple(axe + demi_section for axe in self.axes_traverses()[:-1])

    def axes_panneaux_isolant(self) -> tuple[float, ...]:
        """Axes Y des douze caissons, rives comprises."""
        largeur = self.geometrie.largeur_interieure
        face_interieure_gauche = -largeur / 2 + self.section_largeur
        face_interieure_droite = largeur / 2 - self.section_largeur
        axes_solives = self.axes_solives_i()
        return (
            face_interieure_gauche + self.largeur_caisson_isolant / 2,
            *(sum(paire) / 2 for paire in pairwise(axes_solives)),
            face_interieure_droite - self.largeur_caisson_isolant / 2,
        )

    def bandes_x_osb_plancher(self) -> tuple[tuple[float, float], ...]:
        """Portées suivant X, avec chaque joint sur une traverse primaire."""
        longueur = self.geometrie.longueur_interieure
        limites = (0.0, *self.axes_traverses()[1:-1], longueur)
        if any(droite <= gauche for gauche, droite in pairwise(limites)):
            raise ValueError("la longueur ne permet pas le calepinage OSB supérieur")
        if any(
            droite - gauche > self.longueur_dalle_osb_plancher + 1e-6
            for gauche, droite in pairwise(limites)
        ):
            raise ValueError(
                "une portée OSB dépasse la longueur de dalle entre deux traverses"
            )
        return tuple(pairwise(limites))

    def limites_y_osb_plancher(self) -> tuple[float, ...]:
        """Rives longitudinales toutes placées sur un appui en bois."""
        axes = self.axes_solives_i()
        bord_gauche = -self.geometrie.largeur_interieure / 2
        bord_droit = self.geometrie.largeur_interieure / 2
        limites = [bord_gauche]
        if axes[0] - bord_gauche > self.largeur_dalle_osb_plancher + 1e-6:
            limites.append(bord_gauche + self.section_largeur / 2)
        limites.extend(axes)
        if bord_droit - axes[-1] > self.largeur_dalle_osb_plancher + 1e-6:
            limites.append(bord_droit - self.section_largeur / 2)
        limites.append(bord_droit)
        if any(
            droite - gauche > self.largeur_dalle_osb_plancher + 1e-6
            for gauche, droite in pairwise(limites)
        ):
            raise ValueError("une bande OSB dépasse la largeur de dalle brute")
        return tuple(limites)

    def decoupes_osb_plancher(self) -> tuple[tuple[float, float, float, float], ...]:
        """Découpes ``(x, y, longueur_X, largeur_Y)`` du plancher supérieur."""
        decoupes: list[tuple[float, float, float, float]] = []
        for x_gauche, x_droit in self.bandes_x_osb_plancher():
            for y_bas, y_haut in pairwise(self.limites_y_osb_plancher()):
                decoupes.append(
                    tuple(
                        round(valeur, 6)
                        for valeur in (
                            x_gauche,
                            y_bas,
                            x_droit - x_gauche,
                            y_haut - y_bas,
                        )
                    )
                )
        return tuple(decoupes)

    @property
    def nombre_panneaux_osb_plancher(self) -> int:
        if not self.inclure_osb_plancher:
            return 0
        return len(self.decoupes_osb_plancher())

    @property
    def nombre_dalles_brutes_osb_plancher(self) -> int:
        """Budget conservateur : une dalle brute par découpe porteuse."""
        if not self.inclure_osb_plancher:
            return 0
        return self.nombre_panneaux_osb_plancher

    @property
    def nombre_reservations_pieds(self) -> int:
        if not self.inclure_osb_plancher:
            return 0
        return 2 * len(self.axes_reservations_pieds)

    def _reserver_pieds_dans_osb(self, forme: Shape) -> Shape:
        if not self.axes_reservations_pieds:
            return forme
        demi_largeur_x = self.largeur_reservation_pied / 2
        largeur = self.geometrie.largeur_interieure
        reservation = Box(
            self.largeur_reservation_pied,
            self.profondeur_reservation_pied,
            self.epaisseur_osb_plancher,
            align=(Align.CENTER, Align.MIN, Align.MIN),
        )
        boite = forme.bounding_box()
        for axe_x in self.axes_reservations_pieds:
            if not (
                boite.min.X < axe_x + demi_largeur_x
                and boite.max.X > axe_x - demi_largeur_x
            ):
                continue
            for y in (-largeur / 2, largeur / 2 - self.profondeur_reservation_pied):
                if boite.min.Y < y + self.profondeur_reservation_pied and boite.max.Y > y:
                    forme -= Pos(axe_x, y, self.niveau_haut_traverses) * reservation
        return forme

    def _nombre_fixations_sur_ligne(self, longueur: float, entraxe: float) -> int:
        longueur_utile = longueur - 2 * self.retrait_coin_vis_osb_plancher
        if longueur_utile <= 0:
            return 1
        return ceil(longueur_utile / entraxe) + 1

    @property
    def nombre_vis_osb_plancher(self) -> int:
        """Budget de vis aux rives, sur chaque solive et sur les traverses."""
        if not self.inclure_osb_plancher:
            return 0
        axes_solives = self.axes_solives_i()
        axes_traverses = self.axes_traverses()
        demi_traverse = self.section_largeur / 2
        total = 0
        for x, y, longueur_x, largeur_y in self.decoupes_osb_plancher():
            total += 2 * self._nombre_fixations_sur_ligne(
                longueur_x, self.entraxe_vis_bord_osb_plancher
            )
            appuis_intermediaires = sum(
                y + 1e-6 < axe < y + largeur_y - 1e-6
                for axe in axes_solives
            )
            total += appuis_intermediaires * self._nombre_fixations_sur_ligne(
                longueur_x, self.entraxe_vis_appui_osb_plancher
            )
            for axe in axes_traverses:
                recouvrement = min(x + longueur_x, axe + demi_traverse) - max(
                    x, axe - demi_traverse
                )
                if recouvrement >= 2 * 9:
                    total += self._nombre_fixations_sur_ligne(
                        largeur_y, self.entraxe_vis_appui_osb_plancher
                    )
        return total

    def declarations_poutres(
        self,
        *,
        prerequis_traverses: tuple[str, ...] = (),
        prerequis_solives: tuple[str, ...] = (),
        operation_traverses: InstructionAssemblage | None = None,
    ) -> tuple[PieceInstance | TrameEntreFaces, ...]:
        """Déclare les rives et les deux trames contraintes du plancher."""
        largeur = self.geometrie.largeur_interieure
        longueur = self.geometrie.longueur_interieure
        demi_section = self.section_largeur / 2
        poutre_piece = Madrier(
            longueur=longueur,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        traverse_piece = Madrier(
            longueur=self.longueur_traverses,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        noms_traverses = (
            ("Traverse haute", "Traverse milieu", "Traverse basse")
            if self.nombre_traverses == 3
            else tuple(
                f"Traverse {index:02d}"
                for index in range(1, self.nombre_traverses + 1)
            )
        )
        declarations: list[PieceInstance | TrameEntreFaces] = [
            PieceInstance.ancrer(
                identifiant="rive_gauche",
                nom="Poutre longitudinale gauche",
                piece=poutre_piece,
                location=Location((0, -largeur / 2 + demi_section, 0)),
                couleur="saddlebrown",
            ),
            PieceInstance.parallele_a(
                identifiant="rive_droite",
                nom="Poutre longitudinale droite",
                piece=poutre_piece,
                reference="rive_gauche",
                translation=(0, largeur - self.section_largeur, 0),
                couleur="saddlebrown",
            ),
            TrameEntreFaces(
                prefixe_identifiant="traverse",
                nom_piece="Traverse",
                piece=traverse_piece,
                couleur="burlywood",
                axes=self.axes_traverses(),
                appuis=(("rive_gauche", "rive_droite"),),
                axe_portee="Y",
                jeu_about=self.retrait_connecteur_par_about,
                noms_axes=noms_traverses,
                prerequis=prerequis_traverses,
                operation=operation_traverses,
            ),
        ]

        if self.inclure_solives_i:
            solive_i_piece = PoutreI(
                longueur=self.longueur_solives_i,
                hauteur=self.hauteur_solives_i,
                largeur_membrure=self.largeur_membrure_solives_i,
                modele=(
                    f"STEICOjoist SJ{self.largeur_membrure_solives_i:g}/"
                    f"{self.hauteur_solives_i:g}"
                ),
            )
            declarations.append(
                TrameEntreFaces(
                    prefixe_identifiant="solive",
                    nom_piece="Solive en I",
                    piece=solive_i_piece,
                    couleur="goldenrod",
                    axes=self.axes_solives_i(),
                    appuis=tuple(
                        (f"traverse_{index:02d}", f"traverse_{index + 1:02d}")
                        for index in range(1, self.nombre_traverses)
                    ),
                    axe_portee="X",
                    niveau=self.niveau_haut_traverses - solive_i_piece.hauteur,
                    jeu_about=self.jeu_ewh_par_about,
                    prerequis=prerequis_solives,
                )
            )
        return tuple(declarations)

    def assemblage_poutres(self) -> AssemblageContraint:
        """Résout la vue historique limitée aux poutres du plancher."""
        return AssemblageContraint.declarer(*self.declarations_poutres())

    def declarations_assemblage(
        self,
    ) -> tuple[PieceInstance | TrameEntreFaces, ...]:
        """Déclare la construction jusqu'aux fonds de caisson et à l'isolant."""
        largeur = self.geometrie.largeur_interieure
        face_interieure_gauche = -largeur / 2 + self.section_largeur
        face_interieure_droite = largeur / 2 - self.section_largeur

        ids_sai = (
            tuple(
                f"sabot_sai_{index:02d}_{cote}"
                for index in range(1, self.nombre_traverses + 1)
                for cote in ("gauche", "droit")
            )
            if self.inclure_connecteurs
            else ()
        )
        ids_ewh = (
            tuple(
                f"ewh_{ligne:02d}_{travee}_{about}"
                for ligne in range(1, self.nombre_lignes_solives_i + 1)
                for travee in range(1, self.nombre_traverses)
                for about in ("debut", "fin")
            )
            if self.inclure_solives_i and self.inclure_connecteurs_solives_i
            else ()
        )

        operation_traverses = None
        if ids_sai:
            operation_traverses = InstructionAssemblage(
                "traverses",
                "Engager et fixer les traverses",
                "Engager les traverses dans les SAI déjà fixés aux rives, "
                "puis achever la fixation côté bois porté.",
                (
                    f"Plan SAI {self.plan_fixation_sai.value} : "
                    f"{SabotSAI500_120_2().nombre_fixations_porte(self.plan_fixation_sai)} "
                    "vis CSA 5×40 côté traverse par sabot",
                ),
            )

        poutres = list(
            self.declarations_poutres(
                prerequis_traverses=ids_sai,
                prerequis_solives=ids_ewh,
                operation_traverses=operation_traverses,
            )
        )
        declarations: list[PieceInstance | TrameEntreFaces] = poutres[:2]

        if self.inclure_connecteurs:
            sabot_sai = SabotSAI500_120_2(
                largeur_interieure=self.section_largeur,
            )
            operation_sai = InstructionAssemblage(
                "sabots_sai",
                "Positionner les sabots Simpson SAI",
                "Tracer les axes, présenter les SAI sur les faces intérieures "
                "des deux rives et les fixer côté porteur avant les traverses.",
                (
                    f"Plan SAI {self.plan_fixation_sai.value} : "
                    f"{sabot_sai.nombre_fixations_porteur(self.plan_fixation_sai)} "
                    "vis CSA 5×40 côté rive par sabot",
                    "Respecter le plan de perçage Simpson de la référence commerciale",
                ),
            )
            noms_connecteurs = (
                ("haute", "milieu", "basse")
                if self.nombre_traverses == 3
                else tuple(
                    f"{index:02d}"
                    for index in range(1, self.nombre_traverses + 1)
                )
            )
            for index, (nom_traverse, x) in enumerate(
                zip(noms_connecteurs, self.axes_traverses()),
                start=1,
            ):
                declarations.extend(
                    (
                        PieceInstance.placer_sur(
                            f"sabot_sai_{index:02d}_gauche",
                            f"Sabot SAI {nom_traverse} gauche",
                            sabot_sai,
                            "rive_gauche",
                            Location((x, face_interieure_gauche, 0)),
                            "lightgray",
                            operation=operation_sai,
                        ),
                        PieceInstance.placer_sur(
                            f"sabot_sai_{index:02d}_droit",
                            f"Sabot SAI {nom_traverse} droit",
                            sabot_sai,
                            "rive_droite",
                            Location(
                                (x, face_interieure_droite, 0),
                                (0, 0, 180),
                            ),
                            "lightgray",
                            operation=operation_sai,
                        ),
                    )
                )

        declarations.append(poutres[2])

        if self.inclure_solives_i and self.inclure_connecteurs_solives_i:
            sabot_ewh = SabotEWH(
                largeur_interieure=self.largeur_membrure_solives_i + 1,
                hauteur=self.hauteur_solives_i,
            )
            niveau_bas_solives = self.niveau_haut_traverses - self.hauteur_solives_i
            operation_ewh = InstructionAssemblage(
                "etriers_ewh",
                "Positionner les étriers Simpson EWH",
                "Fixer les EWH sur les traverses avant d'engager les solives en I. "
                "Conserver les pointes côté solive pour la phase suivante.",
                (
                    f"Plan EWH {self.plan_fixation_ewh.value} : "
                    f"{sabot_ewh.nombre_pointes_porteur(self.plan_fixation_ewh)} "
                    "pointes CNA 4×35 côté traverse par étrier",
                    f"Prévoir {sabot_ewh.nombre_pointes_porte()} pointes CNA 4×35 "
                    "côté solive après engagement",
                    "Respecter le plan de perçage Simpson de la référence commerciale",
                ),
            )
            for ligne, y in enumerate(self.axes_solives_i(), start=1):
                for travee, x_debut in enumerate(
                    self.debuts_travees_solives_i(),
                    start=1,
                ):
                    face_debut = x_debut - self.jeu_ewh_par_about
                    face_fin = (
                        x_debut
                        + self.longueur_solives_i
                        + self.jeu_ewh_par_about
                    )
                    declarations.extend(
                        (
                            PieceInstance.placer_sur(
                                f"ewh_{ligne:02d}_{travee}_debut",
                                f"Étrier EWH solive {ligne:02d}.{travee} début",
                                sabot_ewh,
                                f"traverse_{travee:02d}",
                                Location(
                                    (face_debut, y, niveau_bas_solives),
                                    (0, 0, -90),
                                ),
                                "silver",
                                operation=operation_ewh,
                            ),
                            PieceInstance.placer_sur(
                                f"ewh_{ligne:02d}_{travee}_fin",
                                f"Étrier EWH solive {ligne:02d}.{travee} fin",
                                sabot_ewh,
                                f"traverse_{travee + 1:02d}",
                                Location(
                                    (face_fin, y, niveau_bas_solives),
                                    (0, 0, 90),
                                ),
                                "silver",
                                operation=operation_ewh,
                            ),
                        )
                    )

        if self.inclure_solives_i:
            declarations.append(poutres[3])

        def identifiant_solive(ligne: int, travee: int) -> str:
            suffixe = (
                f"{ligne:02d}"
                if self.nombre_traverses == 2
                else f"{ligne:02d}_{travee}"
            )
            return f"solive_{suffixe}"

        ids_solives = tuple(
            identifiant_solive(ligne, travee)
            for ligne in range(1, self.nombre_lignes_solives_i + 1)
            for travee in range(1, self.nombre_traverses)
        )
        ids_entretoises: list[str] = []
        if self.inclure_solives_i and self.inclure_entretoises_solives_i:
            operation_entretoises = InstructionAssemblage(
                "entretoises_solives_i",
                "Poser les entretoises pleine hauteur",
                "Aligner une rangée d'entretoises STEICOjoist au milieu de "
                "chaque travée, sans entailler les membrures des solives.",
                (
                    "Une pointe 2,5×80 de chaque côté de l'âme par entretoise",
                    "Une pointe 3,1×90 par membrure et par entretoise",
                    "Confirmer le détail de fixation avec le prescripteur STEICO",
                ),
            )
            intervalles_y = self.intervalles_entretoises_solives_i()
            for travee, debut_caisson in enumerate(
                self.debuts_panneaux_isolant(),
                start=1,
            ):
                for rangee, decalage_x in enumerate(
                    self.decalages_rangees_entretoises(),
                    start=1,
                ):
                    x = debut_caisson + decalage_x
                    for intervalle, (y_debut, y_fin) in enumerate(
                        intervalles_y,
                        start=1,
                    ):
                        identifiant = (
                            f"entretoise_{travee}_{rangee}_{intervalle:02d}"
                        )
                        ids_entretoises.append(identifiant)
                        reference_gauche = (
                            "rive_gauche"
                            if intervalle == 1
                            else identifiant_solive(intervalle - 1, travee)
                        )
                        reference_droite = (
                            "rive_droite"
                            if intervalle == self.nombre_intervalles_solives_i
                            else identifiant_solive(intervalle, travee)
                        )
                        entretoise = EntretoisePoutreI(
                            longueur=y_fin - y_debut,
                            hauteur=self.hauteur_solives_i,
                            largeur_membrure=self.largeur_membrure_solives_i,
                        )
                        declarations.append(
                            PieceInstance.placer_sur(
                                identifiant,
                                (
                                    f"Entretoise en I travée {travee}, "
                                    f"rangée {rangee}, intervalle {intervalle:02d}"
                                ),
                                entretoise,
                                reference_gauche,
                                Location(
                                    (
                                        x,
                                        y_debut,
                                        self.niveau_haut_traverses
                                        - self.hauteur_solives_i,
                                    ),
                                    (0, 0, 90),
                                ),
                                "rosybrown",
                                prerequis=(reference_droite,),
                                operation=operation_entretoises,
                            )
                        )
        ids_tasseaux: list[str] = []
        ids_fonds_osb: list[str] = []
        if self.inclure_solives_i and self.inclure_osb_caissons:
            solive = PoutreI(
                longueur=self.longueur_solives_i,
                hauteur=self.hauteur_solives_i,
                largeur_membrure=self.largeur_membrure_solives_i,
            )
            niveau_bas_solives = self.niveau_haut_traverses - solive.hauteur
            tasseau = Tasseau(
                longueur=self.longueur_solives_i,
                largeur=solive.largeur_membrure,
                hauteur=self.hauteur_tasseaux_rive,
                materiau="Douglas massif raboté 2 faces séché",
            )
            niveau_bas_tasseaux = (
                niveau_bas_solives
                + solive.hauteur_membrure
                - tasseau.hauteur
            )
            axes_tasseaux = (
                face_interieure_gauche + tasseau.largeur / 2,
                face_interieure_droite - tasseau.largeur / 2,
            )
            operation_tasseaux = InstructionAssemblage(
                "tasseaux_rive",
                "Poser les tasseaux de rive",
                "Fixer les tasseaux au niveau des membrures basses afin de "
                "porter les fonds des caissons latéraux.",
                (
                    f"{self.nombre_vis_par_tasseau_rive} vis Klimas 6×160 par tasseau",
                ),
            )
            for travee, x in enumerate(
                self.debuts_travees_solives_i(),
                start=1,
            ):
                for cote, y, ligne in zip(
                    ("gauche", "droit"),
                    axes_tasseaux,
                    (1, self.nombre_lignes_solives_i),
                ):
                    identifiant = f"tasseau_{cote}_{travee}"
                    ids_tasseaux.append(identifiant)
                    declarations.append(
                        PieceInstance.placer_sur(
                            identifiant,
                            f"Tasseau de rive {cote} {travee}",
                            tasseau,
                            identifiant_solive(ligne, travee),
                            Location((x, y, niveau_bas_tasseaux)),
                            "sienna",
                            prerequis=ids_solives,
                            operation=operation_tasseaux,
                        )
                    )

            niveau_osb = niveau_bas_solives + solive.hauteur_membrure
            axes_solives = self.axes_solives_i()
            axes_interstices = tuple(
                (gauche + droite) / 2
                for gauche, droite in pairwise(axes_solives)
            )
            retrait_lateral = self.jeu_joint_osb / 2
            demi_largeur_rive = self.largeur_panneaux_osb_rive / 2
            axes_panneaux_rive = (
                face_interieure_gauche + retrait_lateral + demi_largeur_rive,
                face_interieure_droite - retrait_lateral - demi_largeur_rive,
            )
            operation_osb = InstructionAssemblage(
                "fonds_osb",
                "Poser le contreventement OSB inférieur",
                "Présenter les fonds OSB entre les solives en I, engager les "
                "encoches autour des EWH pour les panneaux concernés, puis "
                "visser sur les membrures basses et les tasseaux de rive.",
                (
                    f"Jeu périphérique : {self.jeu_joint_osb:g} mm",
                    f"{self.nombre_vis_par_panneau_osb} vis OSB 4×35 par fond",
                ),
            )

            def identifiant_fond_interieur(
                interstice: int,
                travee: int,
                segment: int,
            ) -> str:
                base = f"fond_osb_{interstice:02d}_{travee}"
                return (
                    base
                    if self.nombre_segments_osb_par_caisson == 1
                    else f"{base}_{segment}"
                )

            def identifiant_fond_rive(
                cote: str,
                travee: int,
                segment: int,
            ) -> str:
                base = f"fond_osb_rive_{cote}_{travee}"
                return (
                    base
                    if self.nombre_segments_osb_par_caisson == 1
                    else f"{base}_{segment}"
                )

            def prerequis_entretoises_caisson(
                travee: int,
                intervalle: int,
            ) -> tuple[str, ...]:
                if not self.inclure_entretoises_solives_i:
                    return ()
                return tuple(
                    f"entretoise_{travee}_{rangee}_{intervalle:02d}"
                    for rangee in range(
                        1,
                        self.nombre_rangees_entretoises_par_travee + 1,
                    )
                )

            for travee, x in enumerate(
                self.debuts_travees_solives_i(),
                start=1,
            ):
                for segment, decalage_x in enumerate(
                    self.decalages_segments_osb_caisson(),
                    start=1,
                ):
                    panneau = PanneauFondCaissonOSB(
                        epaisseur=self.epaisseur_osb_caissons,
                        largeur=self.largeur_panneaux_osb_caissons,
                        longueur=self.longueur_segment_osb_caisson,
                        encoches_debut=segment == 1,
                        encoches_fin=(
                            segment == self.nombre_segments_osb_par_caisson
                        ),
                    )
                    panneau_rive = PanneauFondCaissonOSB(
                        epaisseur=self.epaisseur_osb_caissons,
                        largeur=self.largeur_panneaux_osb_rive,
                        longueur=self.longueur_segment_osb_caisson,
                        avec_encoches=False,
                    )
                    x_segment = x + decalage_x
                    for interstice, y in enumerate(axes_interstices, start=1):
                        identifiant = identifiant_fond_interieur(
                            interstice,
                            travee,
                            segment,
                        )
                        ids_fonds_osb.append(identifiant)
                        declarations.append(
                            PieceInstance.placer_sur(
                                identifiant,
                                (
                                    f"Fond OSB caisson {interstice:02d}."
                                    f"{travee}.{segment}"
                                ),
                                panneau,
                                identifiant_solive(interstice, travee),
                                Location((x_segment, y, niveau_osb)),
                                "peru",
                                prerequis=(
                                    identifiant_solive(interstice + 1, travee),
                                    *prerequis_entretoises_caisson(
                                        travee,
                                        interstice + 1,
                                    ),
                                    *ids_tasseaux,
                                ),
                                operation=operation_osb,
                            )
                        )
                    for cote, y, ligne, intervalle in zip(
                        ("gauche", "droit"),
                        axes_panneaux_rive,
                        (1, self.nombre_lignes_solives_i),
                        (1, self.nombre_intervalles_solives_i),
                    ):
                        identifiant = identifiant_fond_rive(
                            cote,
                            travee,
                            segment,
                        )
                        ids_fonds_osb.append(identifiant)
                        declarations.append(
                            PieceInstance.placer_sur(
                                identifiant,
                                (
                                    f"Fond OSB caisson de rive {cote} "
                                    f"{travee}.{segment}"
                                ),
                                panneau_rive,
                                f"tasseau_{cote}_{travee}",
                                Location((x_segment, y, niveau_osb)),
                                "chocolate",
                                prerequis=(
                                    identifiant_solive(ligne, travee),
                                    *prerequis_entretoises_caisson(
                                        travee,
                                        intervalle,
                                    ),
                                ),
                                operation=operation_osb,
                            )
                        )

            if self.inclure_isolant_caissons:
                niveau_isolant = niveau_osb + self.epaisseur_osb_caissons
                operation_isolant = InstructionAssemblage(
                    "isolant_caissons",
                    "Remplir les caissons d'isolant",
                    "Poser l'isolant fibre de bois sur chaque fond OSB sans "
                    "laisser de vide et sans comprimer son épaisseur.",
                    (
                        f"Épaisseur posée : {self.epaisseur_isolant_nominale:g} mm",
                        "Découpe avec la surcote de pose prescrite",
                    ),
                )
                for travee, debut_caisson in enumerate(
                    self.debuts_panneaux_isolant(),
                    start=1,
                ):
                    for segment, decalage_x in enumerate(
                        self.decalages_segments_isolant(),
                        start=1,
                    ):
                        isolant = PanneauIsonatFlex55(
                            epaisseur=self.epaisseur_isolant_nominale,
                            epaisseur_pose=self.epaisseur_isolant_nominale,
                            largeur_pose=self.largeur_caisson_isolant,
                            longueur_pose=self.longueur_segment_isolant,
                        )
                        x = debut_caisson + decalage_x
                        compartiment = (
                            (segment - 1)
                            // self.nombre_segments_isolant_par_compartiment
                            + 1
                        )
                        for caisson, y in enumerate(
                            self.axes_panneaux_isolant(),
                            start=1,
                        ):
                            reference = (
                                identifiant_fond_rive(
                                    "gauche",
                                    travee,
                                    compartiment,
                                )
                                if caisson == 1
                                else (
                                    identifiant_fond_rive(
                                        "droit",
                                        travee,
                                        compartiment,
                                    )
                                    if caisson == self.nombre_intervalles_solives_i
                                    else identifiant_fond_interieur(
                                        caisson - 1,
                                        travee,
                                        compartiment,
                                    )
                                )
                            )
                            declarations.append(
                                PieceInstance.placer_sur(
                                    f"isolant_{caisson:02d}_{travee}_{segment}",
                                    f"Isolant Isonat {caisson:02d}.{travee}.{segment}",
                                    isolant,
                                    reference,
                                    Location((x, y, niveau_isolant)),
                                    "khaki",
                                    prerequis=tuple(ids_fonds_osb),
                                    operation=operation_isolant,
                                )
                            )

        return tuple(declarations)

    def assemblage_construction(self) -> AssemblageContraint:
        """Résout le graphe déclaratif complet actuellement pris en charge."""
        return AssemblageContraint.declarer(*self.declarations_assemblage())

    def elements(self) -> list[ElementPlancher]:
        resolus = self.assemblage_construction().pieces
        ordre = {
            Madrier: 0,
            SabotSAI500_120_2: 1,
            PoutreI: 2,
            EntretoisePoutreI: 3,
            SabotEWH: 4,
            Tasseau: 5,
            PanneauFondCaissonOSB: 6,
            PanneauIsonatFlex55: 7,
        }
        elements: list[ElementPlancher] = sorted(
            resolus,
            key=lambda element: ordre.get(type(element.piece), 99),
        )

        if self.inclure_solives_i and self.inclure_osb_plancher:
            for index, (x, y, longueur_x, largeur_y) in enumerate(
                self.decoupes_osb_plancher(), start=1
            ):
                panneau_plancher_piece = PanneauPlancherOSB(
                    epaisseur=self.epaisseur_osb_plancher,
                    largeur=largeur_y,
                    longueur=longueur_x,
                )
                panneau_plancher = panneau_plancher_piece.construire()
                forme_panneau = (
                    Pos(
                        x,
                        y + largeur_y / 2,
                        self.niveau_haut_traverses,
                    )
                    * panneau_plancher
                )
                forme_panneau = self._reserver_pieds_dans_osb(forme_panneau)
                elements.append(
                    ElementPlancher(
                        f"Plancher OSB supérieur {index:02d}",
                        panneau_plancher_piece,
                        forme_panneau,
                        "darkorange",
                    )
                )

        return elements

    def pieces_bom(self) -> list[Nomenclaturable]:
        """Retourne les pièces et lots prêts à agréger dans une BOM globale."""
        return [*self.elements(), *self.lots_fixations()]

    def lots_fixations(self) -> list[LotBOM]:
        """Lots de vis et pointes associés aux composants du graphe."""
        pieces: list[LotBOM] = []
        if self.inclure_connecteurs:
            vis = VisConnecteurCSA5x40()
            pieces.append(LotBOM(vis.article_bom(), self.nombre_vis_connecteurs))
        if self.nombre_pointes_ewh:
            pointes = PointeAncrageCNA4x35()
            pieces.append(LotBOM(pointes.article_bom(), self.nombre_pointes_ewh))
        if self.nombre_pointes_entretoises_2_5x80:
            pointes_ame = PointeEntretoise2_5x80()
            pieces.append(
                LotBOM(
                    pointes_ame.article_bom(),
                    self.nombre_pointes_entretoises_2_5x80,
                )
            )
        if self.nombre_pointes_entretoises_3_1x90:
            pointes_membrures = PointeEntretoise3_1x90()
            pieces.append(
                LotBOM(
                    pointes_membrures.article_bom(),
                    self.nombre_pointes_entretoises_3_1x90,
                )
            )
        if self.nombre_vis_osb:
            vis_osb = VisBoisOSB4x35()
            pieces.append(LotBOM(vis_osb.article_bom(), self.nombre_vis_osb))
        if self.nombre_vis_tasseaux_rive:
            vis_tasseaux = VisTasseauKlimas6x160()
            pieces.append(
                LotBOM(
                    vis_tasseaux.article_bom(),
                    self.nombre_vis_tasseaux_rive,
                )
            )
        if self.nombre_vis_osb_plancher:
            vis_plancher = VisPlancherOSB5x60()
            pieces.append(
                LotBOM(vis_plancher.article_bom(), self.nombre_vis_osb_plancher)
            )
        return pieces

    def pieces_achat(self) -> list[Nomenclaturable]:
        """BOM d'achat : remplace les découpes OSB par les dalles brutes."""
        pieces = [
            piece
            for piece in self.pieces_bom()
            if not piece.article_bom().reference.startswith(
                ("OSB-FOND-", "OSB-PLANCHER-")
            )
        ]
        if self.nombre_dalles_brutes_osb_caissons:
            dalle_caissons = DalleOSB(
                epaisseur=self.epaisseur_osb_caissons,
                largeur=self.largeur_dalle_osb_caissons,
                longueur=self.longueur_dalle_osb_caissons,
                type_bords=TypeBordsOSB.BORDS_DROITS,
            )
            pieces.append(
                LotBOM(
                    dalle_caissons.article_bom(),
                    self.nombre_dalles_brutes_osb_caissons,
                )
            )
        if self.nombre_dalles_brutes_osb_plancher:
            dalle_plancher = DalleOSB(
                epaisseur=self.epaisseur_osb_plancher,
                largeur=self.largeur_dalle_osb_plancher,
                longueur=self.longueur_dalle_osb_plancher,
                type_bords=TypeBordsOSB.RAINURE_LANGUETTE,
            )
            pieces.append(
                LotBOM(
                    dalle_plancher.article_bom(),
                    self.nombre_dalles_brutes_osb_plancher,
                )
            )
        return pieces

    def nomenclature(self):
        """Construit la nomenclature agrégée du plancher."""
        from home_framework.nomenclature import Nomenclature

        return Nomenclature(self.pieces_bom())

    def nomenclature_achats(self):
        """Construit la nomenclature destinée au chiffrage des achats."""
        from home_framework.nomenclature import Nomenclature

        return Nomenclature(self.pieces_achat())


# Compatibilité avec le nom historique du projet A-frame.
PlancherAFrame = PlancherBois
