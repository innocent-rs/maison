"""Ossature et enveloppe des quatre murs du local batteries."""

from dataclasses import dataclass

from build123d import Align, Box, Pos

from home_framework.nomenclature import ArticleBOM, LotBOM, Nomenclaturable
from home_framework.structure import (
    DalleOSB,
    ElementPlancher,
    PanneauIsonatFlex55,
    TypeBordsOSB,
    VisBoisOSB4x35,
    VisOssatureKlimas6x100,
)


@dataclass(frozen=True, slots=True)
class BoisOssature45x145:
    """Coupe dans une barre Douglas 45 × 145 mm de 6 m."""

    longueur: float
    largeur: float = 45.0
    profondeur: float = 145.0
    materiau: str = "Douglas massif raboté classe d'emploi 2"

    def construire(self):
        return Box(
            self.longueur,
            self.largeur,
            self.profondeur,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )

    def article_bom(self) -> ArticleBOM:
        reference = f"BO-MOB-45x145-L{self.longueur:g}".replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=f"Bois d'ossature Douglas 45 × 145 — L {self.longueur:g} mm",
            categorie="Bois / ossature mur",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.profondeur,
            volume_mm3=self.longueur * self.largeur * self.profondeur,
        )


@dataclass(frozen=True, slots=True)
class PanneauMurOSB:
    """Découpe rectangulaire du voile travaillant extérieur."""

    largeur: float
    hauteur: float
    epaisseur: float = 12.0
    materiau: str = "Panneau structurel OSB 3 à bords droits (BD)"

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"OSB-MUR-BD-{self.largeur:g}x{self.hauteur:g}x{self.epaisseur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Voile mural OSB 3 BD {self.largeur:g} × {self.hauteur:g}"
                f" × {self.epaisseur:g} mm"
            ),
            categorie="Panneaux / découpe OSB mur",
            materiau=self.materiau,
            longueur_mm=self.hauteur,
            largeur_mm=self.largeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.largeur * self.hauteur * self.epaisseur,
        )


@dataclass(frozen=True, slots=True)
class DecoupeIsonatMur:
    """Découpe d'isolant, décrite aux dimensions avant compression."""

    largeur_pose: float
    hauteur_pose: float
    largeur_decoupe: float
    hauteur_decoupe: float
    epaisseur: float = 145.0
    materiau: str = "Fibre de bois semi-rigide Isonat Flex 55 Contact"

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"ISOL-MUR-ISONAT-{self.epaisseur:g}-"
            f"{self.largeur_decoupe:g}x{self.hauteur_decoupe:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Découpe Isonat mur {self.largeur_decoupe:g} × "
                f"{self.hauteur_decoupe:g} × {self.epaisseur:g} mm"
            ),
            categorie="Isolation / découpe fibre de bois mur",
            materiau=self.materiau,
            longueur_mm=self.hauteur_decoupe,
            largeur_mm=self.largeur_decoupe,
            hauteur_mm=self.epaisseur,
            volume_mm3=(
                self.largeur_decoupe * self.hauteur_decoupe * self.epaisseur
            ),
        )


@dataclass(frozen=True, slots=True)
class MursLocalBatteries:
    """Quatre murs solidaires, sans fenêtre et avec une porte centrée."""

    niveau_sol: float
    largeur_exterieure: float = 3_000.0
    longueur_exterieure: float = 3_000.0
    hauteur_ossature: float = 2_575.0
    largeur_montant: float = 45.0
    profondeur_ossature: float = 145.0
    epaisseur_osb: float = 12.0
    largeur_porte_tableau: float = 900.0
    hauteur_porte_tableau: float = 2_150.0
    nombre_panneaux_osb_achetes: int = 10
    nombre_panneaux_isolant_achetes: int = 37
    nombre_vis_osb: int = 950
    nombre_vis_ossature: int = 200

    def __post_init__(self) -> None:
        if self.largeur_exterieure != 3_000:
            raise ValueError("les murs doivent suivre le plancher de 3 000 mm")
        if self.longueur_exterieure != 3_000:
            raise ValueError("les murs doivent suivre le plancher de 3 000 mm")
        if self.hauteur_libre_ossature != 2_440:
            raise ValueError("la hauteur libre doit accepter deux Isonat de 1 220 mm")
        if self.largeur_porte_tableau != 900:
            raise ValueError("la porte standard retenue doit faire 900 mm de large")
        if self.hauteur_porte_tableau != 2_150:
            raise ValueError("la porte standard retenue doit faire 2 150 mm de haut")

    @property
    def hauteur_libre_ossature(self) -> float:
        return self.hauteur_ossature - 3 * self.largeur_montant

    @property
    def longueur_murs_lateraux(self) -> float:
        return self.longueur_exterieure - 2 * self.profondeur_ossature

    @property
    def debut_porte(self) -> float:
        return (self.largeur_exterieure - self.largeur_porte_tableau) / 2

    @property
    def fin_porte(self) -> float:
        return self.debut_porte + self.largeur_porte_tableau

    def _bois_facade(
        self,
        elements: list[ElementPlancher],
        nom: str,
        x: float,
        y: float,
        z: float,
        longueur: float,
        vertical: bool,
        couleur: str = "burlywood",
    ) -> None:
        piece = BoisOssature45x145(longueur)
        forme = (
            Box(45, 145, longueur, align=(Align.MIN, Align.MIN, Align.MIN))
            if vertical
            else Box(longueur, 145, 45, align=(Align.MIN, Align.MIN, Align.MIN))
        )
        elements.append(ElementPlancher(nom, piece, Pos(x, y, z) * forme, couleur))

    def _bois_lateral(
        self,
        elements: list[ElementPlancher],
        nom: str,
        x: float,
        y: float,
        z: float,
        longueur: float,
        vertical: bool,
        couleur: str = "burlywood",
    ) -> None:
        piece = BoisOssature45x145(longueur)
        forme = (
            Box(145, 45, longueur, align=(Align.MIN, Align.MIN, Align.MIN))
            if vertical
            else Box(145, longueur, 45, align=(Align.MIN, Align.MIN, Align.MIN))
        )
        elements.append(ElementPlancher(nom, piece, Pos(x, y, z) * forme, couleur))

    def _elements_ossature_mur_plein(
        self,
        nom: str,
        lateral: bool,
        position: float,
    ) -> list[ElementPlancher]:
        elements: list[ElementPlancher] = []
        niveau_montants = self.niveau_sol + 45
        niveau_lisse_haute = self.niveau_sol + self.hauteur_libre_ossature + 45
        if lateral:
            debut = -1_500 + self.profondeur_ossature
            # Les montants à 1 051 et 2 247 mm d'axe reprennent exactement
            # les joints des panneaux OSB de 1 196 mm vus depuis l'extérieur.
            starts = [0, 514.25, 1_028.5, 1_626.5, 2_224.5, 2_665]
            if position == 2_855:
                # Appui du joint créé en divisant la dernière bande de 608 mm
                # en deux bandes de 304 mm sur le mur droit.
                starts.insert(-1, 2_528.5)
            for couche, z in enumerate(
                (self.niveau_sol, niveau_lisse_haute, niveau_lisse_haute + 45),
                start=1,
            ):
                self._bois_lateral(
                    elements,
                    f"{nom} lisse {couche}",
                    position,
                    debut,
                    z,
                    self.longueur_murs_lateraux,
                    False,
                )
            for index, start in enumerate(starts, start=1):
                self._bois_lateral(
                    elements,
                    f"{nom} montant {index}",
                    position,
                    debut + start,
                    niveau_montants,
                    self.hauteur_libre_ossature,
                    True,
                )
        else:
            starts = (0, 586.75, 1_173.5, 1_771.5, 2_369.5, 2_955)
            for couche, z in enumerate(
                (self.niveau_sol, niveau_lisse_haute, niveau_lisse_haute + 45),
                start=1,
            ):
                self._bois_facade(
                    elements,
                    f"{nom} lisse {couche}",
                    0,
                    position,
                    z,
                    self.largeur_exterieure,
                    False,
                )
            for index, start in enumerate(starts, start=1):
                self._bois_facade(
                    elements,
                    f"{nom} montant {index}",
                    start,
                    position,
                    niveau_montants,
                    self.hauteur_libre_ossature,
                    True,
                )
        return elements

    def _elements_ossature_facade_porte(self) -> list[ElementPlancher]:
        elements: list[ElementPlancher] = []
        y = -1_500.0
        niveau_montants = self.niveau_sol + 45
        niveau_lisse_haute = self.niveau_sol + self.hauteur_libre_ossature + 45

        for index, x in enumerate((0.0, self.fin_porte), start=1):
            longueur = self.debut_porte if index == 1 else 3_000 - self.fin_porte
            self._bois_facade(
                elements,
                f"Façade porte lisse basse {index}",
                x,
                y,
                self.niveau_sol,
                longueur,
                False,
            )
        for couche, z in enumerate((niveau_lisse_haute, niveau_lisse_haute + 45), 1):
            self._bois_facade(
                elements,
                f"Façade porte lisse haute {couche}",
                0,
                y,
                z,
                3_000,
                False,
            )

        montants_pleine_hauteur = (
            0.0,
            320.0,
            640.0,
            960.0,
            1_995.0,
            2_315.0,
            2_635.0,
            2_955.0,
        )
        for index, x in enumerate(montants_pleine_hauteur, start=1):
            self._bois_facade(
                elements,
                f"Façade porte montant {index}",
                x,
                y,
                niveau_montants,
                self.hauteur_libre_ossature,
                True,
            )

        for cote, x in (("gauche", 1_005.0), ("droit", 1_950.0)):
            self._bois_facade(
                elements,
                f"Façade porte montant d'appui {cote}",
                x,
                y,
                niveau_montants,
                self.hauteur_porte_tableau - 45,
                True,
            )

        for pli, y_linteau in enumerate((y, y + 100), start=1):
            piece = BoisOssature45x145(990)
            forme = Box(990, 45, 145, align=(Align.MIN, Align.MIN, Align.MIN))
            elements.append(
                ElementPlancher(
                    f"Façade porte linteau pli {pli}",
                    piece,
                    Pos(1_005, y_linteau, self.niveau_sol + 2_150) * forme,
                    "sandybrown",
                )
            )

        for index, x in enumerate((1_252.5, 1_477.5, 1_702.5), start=1):
            self._bois_facade(
                elements,
                f"Façade porte montant haut {index}",
                x,
                y,
                self.niveau_sol + 2_295,
                190,
                True,
            )
        return elements

    def _element_osb_facade(
        self,
        nom: str,
        x: float,
        y: float,
        z: float,
        largeur: float,
        hauteur: float,
    ) -> ElementPlancher:
        piece = PanneauMurOSB(largeur, hauteur)
        forme = Box(largeur, 12, hauteur, align=(Align.MIN, Align.MIN, Align.MIN))
        return ElementPlancher(nom, piece, Pos(x, y, z) * forme, "goldenrod")

    def _element_osb_lateral(
        self,
        nom: str,
        x: float,
        y: float,
        largeur: float,
    ) -> ElementPlancher:
        piece = PanneauMurOSB(largeur, self.hauteur_ossature)
        forme = Box(
            12,
            largeur,
            self.hauteur_ossature,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        return ElementPlancher(
            nom,
            piece,
            Pos(x, y, self.niveau_sol) * forme,
            "goldenrod",
        )

    def _elements_osb(self) -> list[ElementPlancher]:
        elements: list[ElementPlancher] = []
        largeurs = (1_196.0, 1_196.0, 608.0)
        debuts = (0.0, 1_196.0, 2_392.0)
        for nom, y in (("Mur arrière", 1_500.0),):
            for index, (x, largeur) in enumerate(zip(debuts, largeurs), start=1):
                elements.append(
                    self._element_osb_facade(
                        f"{nom} OSB {index}",
                        x,
                        y,
                        self.niveau_sol,
                        largeur,
                        self.hauteur_ossature,
                    )
                )
        for nom, x in (("Mur gauche", -12.0),):
            for index, (y, largeur) in enumerate(
                zip((-1_500.0, -304.0, 892.0), largeurs),
                start=1,
            ):
                elements.append(
                    self._element_osb_lateral(
                        f"{nom} OSB {index}", x, y, largeur
                    )
                )

        for index, (y, largeur) in enumerate(
            zip((-1_500.0, -304.0, 892.0, 1_196.0), (1_196, 1_196, 304, 304)),
            start=1,
        ):
            elements.append(
                self._element_osb_lateral(
                    f"Mur droit OSB {index}", 3_000, y, largeur
                )
            )

        elements.extend(
            (
                self._element_osb_facade(
                    "Façade porte OSB gauche",
                    0,
                    -1_512,
                    self.niveau_sol,
                    self.debut_porte,
                    self.hauteur_ossature,
                ),
                self._element_osb_facade(
                    "Façade porte OSB droit",
                    self.fin_porte,
                    -1_512,
                    self.niveau_sol,
                    3_000 - self.fin_porte,
                    self.hauteur_ossature,
                ),
                self._element_osb_facade(
                    "Façade porte OSB linteau gauche",
                    self.debut_porte,
                    -1_512,
                    self.niveau_sol + self.hauteur_porte_tableau,
                    225,
                    self.hauteur_ossature - self.hauteur_porte_tableau,
                ),
                self._element_osb_facade(
                    "Façade porte OSB linteau centre gauche",
                    self.debut_porte + 225,
                    -1_512,
                    self.niveau_sol + self.hauteur_porte_tableau,
                    225,
                    self.hauteur_ossature - self.hauteur_porte_tableau,
                ),
                self._element_osb_facade(
                    "Façade porte OSB linteau centre droit",
                    self.debut_porte + 450,
                    -1_512,
                    self.niveau_sol + self.hauteur_porte_tableau,
                    225,
                    self.hauteur_ossature - self.hauteur_porte_tableau,
                ),
                self._element_osb_facade(
                    "Façade porte OSB linteau droit",
                    self.debut_porte + 675,
                    -1_512,
                    self.niveau_sol + self.hauteur_porte_tableau,
                    225,
                    self.hauteur_ossature - self.hauteur_porte_tableau,
                ),
            )
        )
        return elements

    def _element_isolant_facade(
        self,
        nom: str,
        x: float,
        y: float,
        z: float,
        largeur_pose: float,
        hauteur_pose: float,
        largeur_decoupe: float,
        hauteur_decoupe: float,
    ) -> ElementPlancher:
        piece = DecoupeIsonatMur(
            largeur_pose,
            hauteur_pose,
            largeur_decoupe,
            hauteur_decoupe,
        )
        forme = Box(
            largeur_pose,
            145,
            hauteur_pose,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        return ElementPlancher(nom, piece, Pos(x, y, z) * forme, "khaki")

    def _element_isolant_lateral(
        self,
        nom: str,
        x: float,
        y: float,
        z: float,
        largeur_pose: float,
    ) -> ElementPlancher:
        piece = DecoupeIsonatMur(largeur_pose, 1_220, largeur_pose + 10, 1_220)
        forme = Box(
            145,
            largeur_pose,
            1_220,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        return ElementPlancher(nom, piece, Pos(x, y, z) * forme, "khaki")

    def _elements_isolant(self) -> list[ElementPlancher]:
        elements: list[ElementPlancher] = []
        niveau = self.niveau_sol + 45

        cavites_arriere = (
            (45.0, 541.75),
            (631.75, 541.75),
            (1_218.5, 553.0),
            (1_816.5, 553.0),
            (2_414.5, 540.5),
        )
        for rangee in range(2):
            for index, (x, largeur) in enumerate(cavites_arriere, start=1):
                elements.append(
                    self._element_isolant_facade(
                        f"Mur arrière isolant {rangee + 1}.{index}",
                        x,
                        1_355,
                        niveau + rangee * 1_220,
                        largeur,
                        1_220,
                        largeur + 10,
                        1_220,
                    )
                )

        cavites_laterales = (
            (45.0, 469.25),
            (559.25, 469.25),
            (1_073.5, 553.0),
            (1_671.5, 553.0),
            (2_269.5, 395.5),
        )
        for cote, x in (("gauche", 0.0),):
            for rangee in range(2):
                for index, (debut, largeur) in enumerate(
                    cavites_laterales, start=1
                ):
                    elements.append(
                        self._element_isolant_lateral(
                            f"Mur {cote} isolant {rangee + 1}.{index}",
                            x,
                            -1_355 + debut,
                            niveau + rangee * 1_220,
                            largeur,
                        )
                    )

        cavites_droites = (
            (45.0, 469.25),
            (559.25, 469.25),
            (1_073.5, 553.0),
            (1_671.5, 553.0),
            (2_269.5, 259.0),
            (2_573.5, 91.5),
        )
        for rangee in range(2):
            for index, (debut, largeur) in enumerate(cavites_droites, start=1):
                elements.append(
                    self._element_isolant_lateral(
                        f"Mur droit isolant {rangee + 1}.{index}",
                        2_855,
                        -1_355 + debut,
                        niveau + rangee * 1_220,
                        largeur,
                    )
                )

        cavites_facade = (
            (45.0, 275.0),
            (365.0, 275.0),
            (685.0, 275.0),
            (2_040.0, 275.0),
            (2_360.0, 275.0),
            (2_680.0, 275.0),
        )
        for rangee in range(2):
            for index, (x, largeur) in enumerate(cavites_facade, start=1):
                elements.append(
                    self._element_isolant_facade(
                        f"Façade porte isolant {rangee + 1}.{index}",
                        x,
                        -1_500,
                        niveau + rangee * 1_220,
                        largeur,
                        1_220,
                        280,
                        1_220,
                    )
                )
        isolants_hauts = (
            (1_050.0, 202.5),
            (1_297.5, 180.0),
            (1_522.5, 180.0),
            (1_747.5, 202.5),
        )
        for index, (x, largeur) in enumerate(isolants_hauts, start=1):
            elements.append(
                self._element_isolant_facade(
                    f"Façade porte isolant haut {index}",
                    x,
                    -1_500,
                    self.niveau_sol + 2_295,
                    largeur,
                    190,
                    largeur + 10,
                    200,
                )
            )
        return elements

    def elements(self) -> list[ElementPlancher]:
        return [
            *self._elements_ossature_mur_plein("Mur arrière", False, 1_355),
            *self._elements_ossature_mur_plein("Mur gauche", True, 0),
            *self._elements_ossature_mur_plein("Mur droit", True, 2_855),
            *self._elements_ossature_facade_porte(),
            *self._elements_isolant(),
            *self._elements_osb(),
        ]

    def pieces_bom(self) -> list[Nomenclaturable]:
        return [
            *self.elements(),
            LotBOM(VisBoisOSB4x35().article_bom(), self.nombre_vis_osb),
            LotBOM(VisOssatureKlimas6x100().article_bom(), self.nombre_vis_ossature),
        ]

    def pieces_achat(self) -> list[Nomenclaturable]:
        pieces = [
            piece
            for piece in self.pieces_bom()
            if not piece.article_bom().reference.startswith(
                ("OSB-MUR-", "ISOL-MUR-")
            )
        ]
        dalle_osb = DalleOSB(
            epaisseur=12,
            largeur=1_196,
            longueur=2_800,
            type_bords=TypeBordsOSB.BORDS_DROITS,
        )
        isolant = PanneauIsonatFlex55(epaisseur=145)
        pieces.extend(
            (
                LotBOM(dalle_osb.article_bom(), self.nombre_panneaux_osb_achetes),
                LotBOM(isolant.article_bom(), self.nombre_panneaux_isolant_achetes),
            )
        )
        return pieces
