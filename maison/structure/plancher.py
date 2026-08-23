"""Structure paramétrique du plancher du A-frame."""

from dataclasses import dataclass
from itertools import pairwise
from math import ceil, isclose
from build123d import Pos, Rot, Shape

from maison.geometrie import GeometrieAFrame
from maison.nomenclature import LotBOM, Nomenclaturable
from maison.structure.bois import Madrier, PoutreI, Tasseau
from maison.structure.connecteurs import (
    PlanFixationEWH,
    PlanFixationSAI,
    PointeAncrageCNA4x35,
    SabotEWH219_91,
    SabotSAI500_120_2,
    VisBoisOSB4x35,
    VisConnecteurCSA5x40,
)
from maison.structure.isolation import PanneauSTEICOflex036
from maison.structure.panneaux import PanneauFondCaissonOSB


@dataclass(frozen=True, slots=True)
class ElementPlancher:
    nom: str
    piece: Nomenclaturable
    forme: Shape
    couleur: str

    def article_bom(self):
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class PlancherAFrame:
    """Châssis primaire : deux poutres longitudinales et trois traverses.

    Il s'agit d'une géométrie de conception, pas encore d'un dimensionnement
    structurel. Les sections devront être validées selon les portées, charges,
    assemblages et la classe du bois. Les solives en I sont longitudinales et
    réparties en deux travées, entre les traverses basse, milieu et haute.
    Chaque about est suspendu à une traverse massive par un étrier EWH.
    """

    geometrie: GeometrieAFrame
    section_largeur: float = 120.0
    section_hauteur: float = 250.0
    nombre_traverses: int = 3
    entraxe_solives_i_max: float = 500.0
    trame_isolant_sans_decoupe: bool = False
    inclure_connecteurs: bool = True
    plan_fixation_sai: PlanFixationSAI = PlanFixationSAI.TOTAL
    inclure_solives_i: bool = False
    inclure_connecteurs_solives_i: bool = True
    plan_fixation_ewh: PlanFixationEWH = PlanFixationEWH.BRIDES_SUPERIEURES
    hauteur_solives_i: float = 220.0
    jeu_about_solives_i: float = 3.0
    inclure_osb_caissons: bool = False
    inclure_isolant_caissons: bool = False
    epaisseur_osb_caissons: float = 12.0
    jeu_joint_osb: float = 3.0
    entraxe_vis_osb: float = 150.0
    retrait_extremite_vis_osb: float = 100.0

    def __post_init__(self) -> None:
        if min(
            self.section_largeur,
            self.section_hauteur,
            self.entraxe_solives_i_max,
            self.hauteur_solives_i,
            self.epaisseur_osb_caissons,
            self.entraxe_vis_osb,
            self.retrait_extremite_vis_osb,
        ) <= 0:
            raise ValueError("les sections doivent être strictement positives")
        if self.nombre_traverses < 2:
            raise ValueError("le châssis doit comporter au moins deux traverses")
        if self.nombre_traverses != 3:
            raise ValueError("ce plan d'assemblage est défini pour trois traverses")
        if self.geometrie.largeur_interieure <= 2 * self.section_largeur:
            raise ValueError("la largeur est insuffisante pour les poutres de rive")
        if not 0 <= self.jeu_about_solives_i <= 3:
            raise ValueError("le jeu aux abouts des solives doit être compris entre 0 et 3 mm")
        if not 0 <= self.jeu_joint_osb <= 3:
            raise ValueError("le jeu entre panneaux OSB doit être compris entre 0 et 3 mm")
        if self.inclure_osb_caissons and not self.inclure_solives_i:
            raise ValueError("les fonds de caisson exigent les solives en I")
        if self.inclure_isolant_caissons and not self.inclure_osb_caissons:
            raise ValueError("l'isolant exige les fonds de caisson OSB")
        if self.inclure_isolant_caissons and not self.trame_isolant_sans_decoupe:
            raise ValueError("l'isolant entier exige la trame sans découpe")
        if self.trame_isolant_sans_decoupe:
            _ = self.nombre_lignes_solives_i
            if self.entraxe_solives_i > self.entraxe_solives_i_max + 1e-6:
                raise ValueError("la trame isolant dépasse l'entraxe maximal")
        if self.inclure_isolant_caissons:
            panneau_isolant = PanneauSTEICOflex036()
            if not isclose(
                self.longueur_caisson_isolant,
                panneau_isolant.longueur,
                abs_tol=1e-6,
            ):
                raise ValueError(
                    "la longueur des caissons n'accepte pas un panneau isolant entier"
                )
            if not 0 < self.hauteur_caisson_isolant <= panneau_isolant.epaisseur:
                raise ValueError("la hauteur des caissons est incompatible avec l'isolant")
        if self.inclure_solives_i and self.inclure_connecteurs_solives_i:
            etrier = SabotEWH219_91()
            if self.hauteur_solives_i != 220:
                raise ValueError(
                    "le EWH219/91 du plan courant exige une solive haute de 220 mm"
                )
            largeur_membrure = PoutreI(
                longueur=1,
                hauteur=self.hauteur_solives_i,
            ).largeur_membrure
            if not etrier.accepte_largeur_poutre(largeur_membrure):
                raise ValueError("le EWH219/91 est incompatible avec la poutre en I")

    @property
    def entraxe_traverses(self) -> float:
        """Distance entre les axes des traverses successives."""
        axes = self.axes_traverses()
        return axes[1] - axes[0]

    def axes_traverses(self) -> tuple[float, float, float]:
        """Axes X, sabots d'extrémité maintenus dans l'emprise du plancher."""
        demi_section = self.section_largeur / 2
        retrait_extremites = self.retrait_connecteur_par_about
        longueur = self.geometrie.longueur_interieure
        return (
            demi_section + retrait_extremites,
            longueur / 2,
            longueur - demi_section - retrait_extremites,
        )

    @property
    def nombre_intervalles_solives_i(self) -> int:
        """Nombre d'intervalles entre les deux poutres longitudinales."""
        if self.trame_isolant_sans_decoupe:
            return self._nombre_lignes_solives_modulaires() + 1
        distance_entre_axes = self.geometrie.largeur_interieure - self.section_largeur
        return ceil(distance_entre_axes / self.entraxe_solives_i_max)

    @property
    def nombre_lignes_solives_i(self) -> int:
        """Nombre de lignes longitudinales, hors poutres de rive."""
        if self.trame_isolant_sans_decoupe:
            return self._nombre_lignes_solives_modulaires()
        return self.nombre_intervalles_solives_i - 1

    @property
    def nombre_solives_i(self) -> int:
        """Nombre de segments : deux travées pour chaque ligne de solivage."""
        return self.nombre_lignes_solives_i * (self.nombre_traverses - 1)

    @property
    def entraxe_solives_i(self) -> float:
        if self.trame_isolant_sans_decoupe:
            return self.largeur_caisson_isolant + self.epaisseur_ame_solive_i
        distance_entre_axes = self.geometrie.largeur_interieure - self.section_largeur
        return distance_entre_axes / self.nombre_intervalles_solives_i

    @property
    def epaisseur_ame_solive_i(self) -> float:
        return PoutreI(longueur=1, hauteur=self.hauteur_solives_i).epaisseur_ame

    @property
    def largeur_membrure_solive_i(self) -> float:
        return PoutreI(
            longueur=1,
            hauteur=self.hauteur_solives_i,
        ).largeur_membrure

    @property
    def hauteur_membrure_solive_i(self) -> float:
        return PoutreI(
            longueur=1,
            hauteur=self.hauteur_solives_i,
        ).hauteur_membrure

    @property
    def largeur_caisson_isolant(self) -> float:
        panneau = PanneauSTEICOflex036()
        return panneau.largeur_pose

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
        sabot = SabotEWH219_91()
        return self.nombre_sabots_ewh * sabot.nombre_pointes(self.plan_fixation_ewh)

    @property
    def largeur_panneaux_osb_caissons(self) -> float:
        distance_entre_ames = self.entraxe_solives_i - self.epaisseur_ame_solive_i
        return distance_entre_ames - self.jeu_joint_osb

    @property
    def largeur_panneaux_osb_rive(self) -> float:
        """Largeur entre la poutre de rive et l'âme de la première solive."""
        if self.trame_isolant_sans_decoupe:
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
        return nombre_interstices * (self.nombre_traverses - 1)

    @property
    def nombre_panneaux_osb_rive(self) -> int:
        if not self.inclure_osb_caissons:
            return 0
        return 2 * (self.nombre_traverses - 1)

    @property
    def nombre_panneaux_osb_caissons(self) -> int:
        return self.nombre_panneaux_osb_interieurs + self.nombre_panneaux_osb_rive

    @property
    def nombre_tasseaux_rive(self) -> int:
        if not self.inclure_osb_caissons:
            return 0
        return 2 * (self.nombre_traverses - 1)

    @property
    def nombre_vis_par_panneau_osb(self) -> int:
        longueur_vissable = (
            self.longueur_solives_i - 2 * self.retrait_extremite_vis_osb
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
        return self.nombre_panneaux_osb_caissons

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
        """Axes Y des onze lignes de solivage longitudinales."""
        axe_poutre_gauche = (
            -self.geometrie.largeur_interieure / 2 + self.section_largeur / 2
        )
        if self.trame_isolant_sans_decoupe:
            premier_axe = axe_poutre_gauche + self.decalage_premiere_solive_modulaire
            return tuple(
                premier_axe + index * self.entraxe_solives_i
                for index in range(self.nombre_lignes_solives_i)
            )
        return tuple(
            axe_poutre_gauche + index * self.entraxe_solives_i
            for index in range(1, self.nombre_intervalles_solives_i)
        )

    def debuts_travees_solives_i(self) -> tuple[float, ...]:
        """Faces de départ X des deux travées, retrait EWH inclus."""
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

    def elements(self) -> list[ElementPlancher]:
        largeur = self.geometrie.largeur_interieure
        longueur = self.geometrie.longueur_interieure
        demi_section = self.section_largeur / 2

        poutre_piece = Madrier(
            longueur=longueur,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        poutre = poutre_piece.construire()
        elements: list[ElementPlancher] = []

        # Les poutres longitudinales restent entières et sans entaille.
        for nom, y_min in (
            ("Poutre longitudinale gauche", -largeur / 2),
            (
                "Poutre longitudinale droite",
                largeur / 2 - self.section_largeur,
            ),
        ):
            forme = Pos(0, y_min + demi_section, 0) * poutre
            elements.append(ElementPlancher(nom, poutre_piece, forme, "saddlebrown"))

        # Les traverses sont coupées entre les deux ailes de sabot. En leur
        # absence, elles retrouvent toute la distance entre les faces bois.
        traverse_piece = Madrier(
            longueur=self.longueur_traverses,
            largeur=self.section_largeur,
            hauteur=self.section_hauteur,
        )
        traverse = traverse_piece.construire()
        for nom, x in zip(
            ("Traverse haute", "Traverse milieu", "Traverse basse"),
            self.axes_traverses(),
        ):
            forme = (
                Pos(
                    x,
                    -largeur / 2
                    + self.section_largeur
                    + self.retrait_connecteur_par_about,
                    0,
                )
                * Rot(0, 0, 90)
                * traverse
            )
            elements.append(
                ElementPlancher(
                    nom,
                    traverse_piece,
                    forme,
                    "burlywood",
                )
            )

        if self.inclure_connecteurs:
            sabot_piece = SabotSAI500_120_2(
                largeur_interieure=self.section_largeur,
            )
            sabot = sabot_piece.construire()
            face_interieure_gauche = -largeur / 2 + self.section_largeur
            face_interieure_droite = largeur / 2 - self.section_largeur
            for nom_traverse, x in zip(
                ("haute", "milieu", "basse"),
                self.axes_traverses(),
            ):
                elements.extend(
                    (
                        ElementPlancher(
                            f"Sabot SAI {nom_traverse} gauche",
                            sabot_piece,
                            Pos(x, face_interieure_gauche, 0) * sabot,
                            "lightgray",
                        ),
                        ElementPlancher(
                            f"Sabot SAI {nom_traverse} droit",
                            sabot_piece,
                            Pos(x, face_interieure_droite, 0)
                            * Rot(0, 0, 180)
                            * sabot,
                            "lightgray",
                        ),
                    )
                )

        if self.inclure_solives_i:
            solive_i_piece = PoutreI(
                longueur=self.longueur_solives_i,
                hauteur=self.hauteur_solives_i,
                modele="STEICOjoist SJ90/220",
            )
            solive_i = solive_i_piece.construire()
            niveau_bas_solives = self.niveau_haut_traverses - solive_i_piece.hauteur

            for ligne, y in enumerate(self.axes_solives_i(), start=1):
                for travee, x in enumerate(
                    self.debuts_travees_solives_i(), start=1
                ):
                    elements.append(
                        ElementPlancher(
                            f"Solive en I {ligne:02d}.{travee}",
                            solive_i_piece,
                            Pos(x, y, niveau_bas_solives) * solive_i,
                            "goldenrod",
                        )
                    )

            if self.inclure_connecteurs_solives_i:
                sabot_ewh_piece = SabotEWH219_91()
                sabot_ewh = sabot_ewh_piece.construire()
                for ligne, y in enumerate(self.axes_solives_i(), start=1):
                    for travee, x_debut in enumerate(
                        self.debuts_travees_solives_i(), start=1
                    ):
                        face_debut = x_debut - self.jeu_ewh_par_about
                        face_fin = (
                            x_debut
                            + self.longueur_solives_i
                            + self.jeu_ewh_par_about
                        )
                        elements.extend(
                            (
                                ElementPlancher(
                                    f"Étrier EWH solive {ligne:02d}.{travee} début",
                                    sabot_ewh_piece,
                                    Pos(face_debut, y, niveau_bas_solives)
                                    * Rot(0, 0, -90)
                                    * sabot_ewh,
                                    "silver",
                                ),
                                ElementPlancher(
                                    f"Étrier EWH solive {ligne:02d}.{travee} fin",
                                    sabot_ewh_piece,
                                    Pos(face_fin, y, niveau_bas_solives)
                                    * Rot(0, 0, 90)
                                    * sabot_ewh,
                                    "silver",
                                ),
                            )
                        )

            if self.inclure_osb_caissons:
                tasseau_piece = Tasseau(
                    longueur=self.longueur_solives_i,
                    largeur=solive_i_piece.largeur_membrure,
                    hauteur=solive_i_piece.hauteur_membrure,
                )
                tasseau = tasseau_piece.construire()
                face_interieure_gauche = -largeur / 2 + self.section_largeur
                face_interieure_droite = largeur / 2 - self.section_largeur
                axes_tasseaux = (
                    face_interieure_gauche + tasseau_piece.largeur / 2,
                    face_interieure_droite - tasseau_piece.largeur / 2,
                )
                for travee, x in enumerate(
                    self.debuts_travees_solives_i(), start=1
                ):
                    for cote, y in zip(("gauche", "droit"), axes_tasseaux):
                        elements.append(
                            ElementPlancher(
                                f"Tasseau de rive {cote} {travee}",
                                tasseau_piece,
                                Pos(x, y, niveau_bas_solives) * tasseau,
                                "sienna",
                            )
                        )

                panneau_piece = PanneauFondCaissonOSB(
                    epaisseur=self.epaisseur_osb_caissons,
                    largeur=self.largeur_panneaux_osb_caissons,
                    longueur=self.longueur_solives_i,
                )
                panneau = panneau_piece.construire()
                niveau_osb = niveau_bas_solives + solive_i_piece.hauteur_membrure
                axes = self.axes_solives_i()
                axes_interstices = tuple(
                    (gauche + droite) / 2
                    for gauche, droite in pairwise(axes)
                )
                for travee, x in enumerate(
                    self.debuts_travees_solives_i(), start=1
                ):
                    for interstice, y in enumerate(axes_interstices, start=1):
                        elements.append(
                            ElementPlancher(
                                f"Fond OSB caisson {interstice:02d}.{travee}",
                                panneau_piece,
                                Pos(x, y, niveau_osb) * panneau,
                                "peru",
                            )
                        )

                panneau_rive_piece = PanneauFondCaissonOSB(
                    epaisseur=self.epaisseur_osb_caissons,
                    largeur=self.largeur_panneaux_osb_rive,
                    longueur=self.longueur_solives_i,
                    avec_encoches=False,
                )
                panneau_rive = panneau_rive_piece.construire()
                retrait_lateral = self.jeu_joint_osb / 2
                demi_largeur_rive = panneau_rive_piece.largeur / 2
                axes_panneaux_rive = (
                    face_interieure_gauche
                    + retrait_lateral
                    + demi_largeur_rive,
                    face_interieure_droite
                    - retrait_lateral
                    - demi_largeur_rive,
                )
                for travee, x in enumerate(
                    self.debuts_travees_solives_i(), start=1
                ):
                    for cote, y in zip(
                        ("gauche", "droit"), axes_panneaux_rive
                    ):
                        elements.append(
                            ElementPlancher(
                                f"Fond OSB caisson de rive {cote} {travee}",
                                panneau_rive_piece,
                                Pos(x, y, niveau_osb) * panneau_rive,
                                "chocolate",
                            )
                        )

                if self.inclure_isolant_caissons:
                    isolant_piece = PanneauSTEICOflex036(
                        epaisseur_pose=self.hauteur_caisson_isolant,
                        largeur_pose=self.largeur_caisson_isolant,
                    )
                    isolant = isolant_piece.construire()
                    niveau_isolant = niveau_osb + self.epaisseur_osb_caissons
                    for travee, x in enumerate(
                        self.debuts_panneaux_isolant(), start=1
                    ):
                        for caisson, y in enumerate(
                            self.axes_panneaux_isolant(), start=1
                        ):
                            elements.append(
                                ElementPlancher(
                                    f"Isolant STEICOflex {caisson:02d}.{travee}",
                                    isolant_piece,
                                    Pos(x, y, niveau_isolant) * isolant,
                                    "khaki",
                                )
                            )

        return elements

    def nomenclature(self):
        """Construit la nomenclature agrégée du plancher."""
        from maison.nomenclature import Nomenclature

        pieces: list[Nomenclaturable] = list(self.elements())
        if self.inclure_connecteurs:
            vis = VisConnecteurCSA5x40()
            pieces.append(LotBOM(vis.article_bom(), self.nombre_vis_connecteurs))
        if self.nombre_pointes_ewh:
            pointes = PointeAncrageCNA4x35()
            pieces.append(LotBOM(pointes.article_bom(), self.nombre_pointes_ewh))
        if self.nombre_vis_osb:
            vis_osb = VisBoisOSB4x35()
            pieces.append(LotBOM(vis_osb.article_bom(), self.nombre_vis_osb))
        return Nomenclature(pieces)
