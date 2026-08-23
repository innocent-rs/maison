"""Connecteurs métalliques et fixations de la structure bois.

Les géométries restent volontairement légères : elles représentent
l'encombrement utile pour contrôler l'assemblage, tandis que les plans de
perçage certifiés du fabricant restent les documents d'exécution.
"""

from dataclasses import dataclass
from enum import StrEnum

from build123d import Align, Box, Compound, Cylinder, Part, Pos, Rot, Shape

from maison.nomenclature import ArticleBOM


class PlanFixationSAI(StrEnum):
    """Plans de fixation publiés pour le sabot SAI500/120/2."""

    PARTIEL = "partiel"
    TOTAL = "total"


class PlanFixationEWH(StrEnum):
    """Montages standards publiés pour l'étrier EWH."""

    BRIDES_SUPERIEURES = "brides_superieures"
    BRIDES_LATERALES = "brides_laterales"


@dataclass(frozen=True, slots=True)
class SabotSAI500_120_2:
    """Sabot Simpson Strong-Tie SAI500/120/2 à ailes intérieures.

    La forme modélise l'assise, les deux joues et les deux ailes intérieures.
    Les trous ne sont pas reproduits : leur position doit toujours provenir
    du plan Simpson associé à la référence commerciale.
    """

    largeur_interieure: float = 120.0
    hauteur: float = 190.0
    profondeur: float = 76.0
    epaisseur: float = 2.0
    largeur_aile: float = 34.0
    materiau: str = "Acier galvanisé S250GD + Z275"

    def __post_init__(self) -> None:
        dimensions = (
            self.largeur_interieure,
            self.hauteur,
            self.profondeur,
            self.epaisseur,
            self.largeur_aile,
        )
        if min(dimensions) <= 0:
            raise ValueError("les dimensions du sabot doivent être positives")
        if not 118 <= self.largeur_interieure <= 120:
            raise ValueError(
                "le SAI500/120/2 accepte une largeur de bois de 118 à 120 mm"
            )
        if 2 * self.largeur_aile >= self.largeur_interieure:
            raise ValueError("les ailes intérieures se chevaucheraient")

    def construire(self) -> Shape:
        """Construit l'enveloppe simplifiée du sabot.

        Le bois porté progresse suivant +Y. La face du porteur se trouve à
        Y=0 et le dessus de l'assise à Z=0.
        """
        demi_largeur = self.largeur_interieure / 2

        assise = Box(
            self.largeur_interieure + 2 * self.epaisseur,
            self.profondeur,
            self.epaisseur,
            align=(Align.CENTER, Align.MIN, Align.MAX),
        )
        joue_gauche = Pos(-demi_largeur, 0, 0) * Box(
            self.epaisseur,
            self.profondeur,
            self.hauteur,
            align=(Align.MAX, Align.MIN, Align.MIN),
        )
        joue_droite = Pos(demi_largeur, 0, 0) * Box(
            self.epaisseur,
            self.profondeur,
            self.hauteur,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        aile_gauche = Pos(-demi_largeur, 0, 0) * Box(
            self.largeur_aile,
            self.epaisseur,
            self.hauteur,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        aile_droite = Pos(demi_largeur, 0, 0) * Box(
            self.largeur_aile,
            self.epaisseur,
            self.hauteur,
            align=(Align.MAX, Align.MIN, Align.MIN),
        )
        return Compound(
            children=(
                assise,
                joue_gauche,
                joue_droite,
                aile_gauche,
                aile_droite,
            )
        )

    def nombre_fixations_porteur(self, plan: PlanFixationSAI) -> int:
        return 32 if plan is PlanFixationSAI.TOTAL else 18

    def nombre_fixations_porte(self, plan: PlanFixationSAI) -> int:
        return 18 if plan is PlanFixationSAI.TOTAL else 10

    def nombre_fixations(self, plan: PlanFixationSAI) -> int:
        return self.nombre_fixations_porteur(plan) + self.nombre_fixations_porte(plan)

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
            reference="SIMPSON-SAI500-120-2",
            designation="Sabot à ailes intérieures SAI500/120/2",
            categorie="Connecteur / sabot",
            materiau=self.materiau,
            longueur_mm=self.profondeur,
            largeur_mm=self.largeur_interieure,
            hauteur_mm=self.hauteur,
        )


@dataclass(frozen=True, slots=True)
class SabotEWH:
    """Étrier Simpson Strong-Tie EWH pour STEICOjoist SJ60.

    La CAO est une enveloppe simplifiée sans trous. Le plan de perçage et les
    capacités résistantes restent ceux de l'ETA-17/0554 et de la fiche Simpson.
    """

    largeur_interieure: float = 61.0
    hauteur: float = 240.0
    profondeur_assise: float = 80.0
    largeur_aile_porteur: float = 49.0
    longueur_bride_superieure: float = 40.0
    epaisseur: float = 0.9
    materiau: str = "Acier galvanisé S250GD + Z275"

    def __post_init__(self) -> None:
        dimensions = (
            self.largeur_interieure,
            self.hauteur,
            self.profondeur_assise,
            self.largeur_aile_porteur,
            self.longueur_bride_superieure,
            self.epaisseur,
        )
        if min(dimensions) <= 0:
            raise ValueError("les dimensions de l'étrier doivent être positives")
        if self.largeur_interieure != 61 or self.hauteur not in (240, 300):
            raise ValueError(
                "le projet accepte uniquement les EWH240/61 et EWH300/61"
            )

    def accepte_largeur_poutre(self, largeur: float) -> bool:
        """Vérifie la plage fabricant A - 3 mm à A."""
        return self.largeur_interieure - 3 <= largeur <= self.largeur_interieure

    def construire(self) -> Shape:
        """Construit l'enveloppe du EWH avec ses brides supérieures pliées.

        La poutre portée progresse suivant +Y. La face intérieure du porteur
        est à Y=0 et le dessous de la poutre portée à Z=0.
        """
        demi_largeur = self.largeur_interieure / 2
        largeur_hors_tout = self.largeur_interieure + 2 * self.epaisseur

        assise = Box(
            largeur_hors_tout,
            self.profondeur_assise,
            self.epaisseur,
            align=(Align.CENTER, Align.MIN, Align.MAX),
        )
        joue_gauche = Pos(-demi_largeur, 0, 0) * Box(
            self.epaisseur,
            self.profondeur_assise,
            self.hauteur,
            align=(Align.MAX, Align.MIN, Align.MIN),
        )
        joue_droite = Pos(demi_largeur, 0, 0) * Box(
            self.epaisseur,
            self.profondeur_assise,
            self.hauteur,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )

        aile_gauche = Pos(-demi_largeur, 0, 0) * Box(
            self.largeur_aile_porteur,
            self.epaisseur,
            self.hauteur,
            align=(Align.MIN, Align.MAX, Align.MIN),
        )
        aile_droite = Pos(demi_largeur, 0, 0) * Box(
            self.largeur_aile_porteur,
            self.epaisseur,
            self.hauteur,
            align=(Align.MAX, Align.MAX, Align.MIN),
        )
        bride_gauche = Pos(-demi_largeur, 0, self.hauteur) * Box(
            self.largeur_aile_porteur,
            self.longueur_bride_superieure,
            self.epaisseur,
            align=(Align.MIN, Align.MAX, Align.MAX),
        )
        bride_droite = Pos(demi_largeur, 0, self.hauteur) * Box(
            self.largeur_aile_porteur,
            self.longueur_bride_superieure,
            self.epaisseur,
            align=(Align.MAX, Align.MAX, Align.MAX),
        )
        return Compound(
            children=(
                assise,
                joue_gauche,
                joue_droite,
                aile_gauche,
                aile_droite,
                bride_gauche,
                bride_droite,
            )
        )

    def nombre_pointes_porteur(self, plan: PlanFixationEWH) -> int:
        """Nombre de CNA dans le porteur pour le montage standard."""
        if plan is PlanFixationEWH.BRIDES_SUPERIEURES:
            return 8 + 4
        return 8

    def nombre_pointes_porte(self) -> int:
        return 4

    def nombre_pointes(self, plan: PlanFixationEWH) -> int:
        return self.nombre_pointes_porteur(plan) + self.nombre_pointes_porte()

    def article_bom(self) -> ArticleBOM:
        suffixe = f"{self.hauteur:g}-{self.largeur_interieure:g}"
        return ArticleBOM(
            reference=f"SIMPSON-EWH{suffixe}",
            designation=(
                f"Étrier pour poutre en I EWH{self.hauteur:g}/"
                f"{self.largeur_interieure:g}"
            ),
            categorie="Connecteur / étrier poutre en I",
            materiau=self.materiau,
            longueur_mm=self.profondeur_assise,
            largeur_mm=self.largeur_interieure,
            hauteur_mm=self.hauteur,
        )


@dataclass(frozen=True, slots=True)
class VisConnecteurCSA5x40:
    """Vis Simpson CSA5.0X40 destinée aux connecteurs métalliques."""

    diametre: float = 5.0
    longueur: float = 40.0
    diametre_tete: float = 8.3
    materiau: str = "Acier électrozingué"

    def __post_init__(self) -> None:
        if min(self.diametre, self.longueur, self.diametre_tete) <= 0:
            raise ValueError("les dimensions de la vis doivent être positives")

    def construire(self) -> Part:
        """Construit une représentation simplifiée, orientée suivant Z."""
        corps = Cylinder(
            self.diametre / 2,
            self.longueur,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        tete = Pos(0, 0, self.longueur) * Cylinder(
            self.diametre_tete / 2,
            self.epaisseur_tete,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        return corps + tete

    @property
    def epaisseur_tete(self) -> float:
        """Épaisseur seulement destinée à la représentation CAO."""
        return 2.0

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
            reference="SIMPSON-CSA5.0X40",
            designation="Vis pour connecteur CSA 5,0 × 40 mm",
            categorie="Fixation / vis connecteur",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.diametre,
        )


@dataclass(frozen=True, slots=True)
class PointeAncrageCNA4x35:
    """Pointe annelée Simpson CNA4.0X35 pour connecteurs métalliques."""

    diametre: float = 4.0
    longueur: float = 35.0
    materiau: str = "Acier électrozingué"

    def __post_init__(self) -> None:
        if min(self.diametre, self.longueur) <= 0:
            raise ValueError("les dimensions de la pointe doivent être positives")

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
            reference="SIMPSON-CNA4.0X35",
            designation="Pointe annelée CNA 4,0 × 35 mm",
            categorie="Fixation / pointe connecteur",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.diametre,
        )


@dataclass(frozen=True, slots=True)
class VisBoisOSB4x35:
    """Vis bois générique pour fixer l'OSB aux membrures basses."""

    diametre: float = 4.0
    longueur: float = 35.0
    materiau: str = "Acier zingué"

    def __post_init__(self) -> None:
        if min(self.diametre, self.longueur) <= 0:
            raise ValueError("les dimensions de la vis doivent être positives")

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
            reference="VIS-BOIS-OSB-4X35",
            designation="Vis bois pour OSB 4 × 35 mm",
            categorie="Fixation / vis panneau",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.diametre,
        )


@dataclass(frozen=True, slots=True)
class VisPlancherOSB5x60:
    """Vis bois à filetage complet pour le plancher porteur en OSB de 22 mm."""

    diametre: float = 5.0
    longueur: float = 60.0
    materiau: str = "Acier zingué"

    def __post_init__(self) -> None:
        if min(self.diametre, self.longueur) <= 0:
            raise ValueError("les dimensions de la vis doivent être positives")

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
            reference="VIS-PLANCHER-OSB-5X60",
            designation="Vis bois pour plancher OSB 5 × 60 mm",
            categorie="Fixation / vis plancher",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.diametre,
        )


@dataclass(frozen=True, slots=True)
class FerrurePiedAFrame:
    """Enveloppe de principe d'une ferrure de pied à deux joues.

    Ce composant n'est pas une référence commerciale dimensionnée. Il matérialise
    le volume réservé à une ferrure de type PCAB ou à une pièce mécano-soudée
    équivalente, à vérifier après calcul des efforts de pied.
    """

    largeur_bois: float = 120.0
    largeur_appui: float = 120.0
    epaisseur: float = 4.0
    longueur_joue: float = 200.0
    hauteur_joue: float = 220.0
    hauteur_ancrage_poutre: float = 180.0
    largeur_ancrage_poutre: float = 160.0
    materiau: str = "Acier galvanisé, nuance et épaisseur à dimensionner"

    def __post_init__(self) -> None:
        dimensions = (
            self.largeur_bois,
            self.largeur_appui,
            self.epaisseur,
            self.longueur_joue,
            self.hauteur_joue,
            self.hauteur_ancrage_poutre,
            self.largeur_ancrage_poutre,
        )
        if min(dimensions) <= 0:
            raise ValueError("les dimensions de la ferrure doivent être positives")

    def construire(self) -> Shape:
        demi_bois = self.largeur_bois / 2
        joue = Box(
            self.epaisseur,
            self.longueur_joue,
            self.hauteur_joue,
            align=(Align.CENTER, Align.MIN, Align.MIN),
        )
        joue_gauche = Pos(-demi_bois - self.epaisseur / 2, 0, 0) * joue
        joue_droite = Pos(demi_bois + self.epaisseur / 2, 0, 0) * joue

        ancrage = Box(
            self.largeur_ancrage_poutre,
            self.epaisseur,
            self.hauteur_ancrage_poutre,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
        )
        ancrage_exterieur = Pos(0, self.epaisseur / 2, 0) * ancrage
        ancrage_interieur = Pos(
            0,
            self.largeur_appui - self.epaisseur / 2,
            0,
        ) * ancrage
        return Compound(
            children=(
                joue_gauche,
                joue_droite,
                ancrage_exterieur,
                ancrage_interieur,
            )
        )

    @property
    def volume_mm3(self) -> float:
        joues = 2 * self.epaisseur * self.longueur_joue * self.hauteur_joue
        ancrages = (
            2
            * self.largeur_ancrage_poutre
            * self.epaisseur
            * self.hauteur_ancrage_poutre
        )
        return joues + ancrages

    def article_bom(self) -> ArticleBOM:
        return ArticleBOM(
            reference=f"FERRURE-PIED-AFRAME-PROV-{self.largeur_bois:g}",
            designation=(
                "Ferrure de pied A-frame à deux joues — principe à dimensionner"
            ),
            categorie="Connecteur / pied A-frame",
            materiau=self.materiau,
            longueur_mm=self.longueur_joue,
            largeur_mm=self.largeur_bois,
            hauteur_mm=self.hauteur_joue + self.hauteur_ancrage_poutre,
            volume_mm3=self.volume_mm3,
        )


@dataclass(frozen=True, slots=True)
class KitTirantAFrame:
    """Tirant sous plancher avec platines, écrous et réglage à dimensionner."""

    longueur: float
    diametre: float = 16.0
    materiau: str = "Acier galvanisé, classe de tige à dimensionner"

    def __post_init__(self) -> None:
        if min(self.longueur, self.diametre) <= 0:
            raise ValueError("les dimensions du tirant doivent être positives")

    def construire(self) -> Part:
        tige_verticale = Cylinder(
            self.diametre / 2,
            self.longueur,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        return Rot(0, 90, 0) * tige_verticale

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"KIT-TIRANT-AFRAME-M{self.diametre:g}-L{self.longueur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Kit tirant A-frame M{self.diametre:g} — L {self.longueur:g} mm"
                " — platines, écrous et réglage à dimensionner"
            ),
            categorie="Acier / tirant de ferme",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.diametre,
            volume_mm3=self.longueur * 3.141592653589793 * (self.diametre / 2) ** 2,
        )
