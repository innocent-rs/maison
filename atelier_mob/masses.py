"""Inventaire des masses installées du plancher de l'atelier."""

from dataclasses import dataclass
from math import pi

from home_framework.structure.bois import Madrier, PoutreI, Tasseau
from home_framework.structure.connecteurs import SabotEWH, SabotSAI500_120_2
from home_framework.structure.isolation import PanneauIsonatFlex55
from home_framework.structure.panneaux import (
    PanneauFondCaissonOSB,
    PanneauPlancherOSB,
)
from home_framework.structure.plancher import PlancherBois


@dataclass(frozen=True, slots=True)
class HypothesesMasses:
    masse_volumique_bois_kg_m3: float = 500.0
    masse_volumique_osb_kg_m3: float = 600.0
    masse_volumique_isolant_kg_m3: float = 55.0
    masse_volumique_acier_kg_m3: float = 7_850.0
    masse_lineique_sj60_240_kg_m: float = 4.12
    masse_sai500_120_2_kg: float = 0.560
    masse_ewh240_61_kg: float = 0.327
    gravite_m_s2: float = 9.81

    def __post_init__(self) -> None:
        if min(
            self.masse_volumique_bois_kg_m3,
            self.masse_volumique_osb_kg_m3,
            self.masse_volumique_isolant_kg_m3,
            self.masse_volumique_acier_kg_m3,
            self.masse_lineique_sj60_240_kg_m,
            self.masse_sai500_120_2_kg,
            self.masse_ewh240_61_kg,
            self.gravite_m_s2,
        ) <= 0:
            raise ValueError("les masses, densités et la gravité doivent être positives")


@dataclass(frozen=True, slots=True)
class LigneMasse:
    reference: str
    designation: str
    quantite: int
    masse_unitaire_kg: float
    masse_totale_kg: float
    masse_lineique_kg_m: float | None
    famille_charge: str
    mode_calcul: str


@dataclass(frozen=True, slots=True)
class RapportMasses:
    hypotheses: HypothesesMasses
    lignes: tuple[LigneMasse, ...]
    surface_plancher_m2: float

    @property
    def masse_totale_kg(self) -> float:
        return sum(ligne.masse_totale_kg for ligne in self.lignes)

    @property
    def masse_madriers_primaires_kg(self) -> float:
        return sum(
            ligne.masse_totale_kg
            for ligne in self.lignes
            if ligne.famille_charge == "madrier_primaire"
        )

    @property
    def masse_solives_i_kg(self) -> float:
        return sum(
            ligne.masse_totale_kg
            for ligne in self.lignes
            if ligne.famille_charge == "solive_i"
        )

    @property
    def masse_surfacique_hors_madriers_kg_m2(self) -> float:
        return (
            self.masse_totale_kg - self.masse_madriers_primaires_kg
        ) / self.surface_plancher_m2

    @property
    def charge_surfacique_hors_madriers_kN_m2(self) -> float:
        return (
            self.masse_surfacique_hors_madriers_kg_m2
            * self.hypotheses.gravite_m_s2
            / 1_000
        )

    @property
    def charge_surfacique_couches_hors_solives_kN_m2(self) -> float:
        masse = (
            self.masse_totale_kg
            - self.masse_madriers_primaires_kg
            - self.masse_solives_i_kg
        )
        return (
            masse
            * self.hypotheses.gravite_m_s2
            / 1_000
            / self.surface_plancher_m2
        )

    @property
    def charge_surfacique_totale_kN_m2(self) -> float:
        return (
            self.masse_totale_kg
            * self.hypotheses.gravite_m_s2
            / 1_000
            / self.surface_plancher_m2
        )


def _masse_element(
    piece,
    volume_mm3: float,
    hypotheses: HypothesesMasses,
) -> tuple[float, float | None, str, str]:
    if isinstance(piece, Madrier):
        lineique = (
            piece.largeur
            * piece.hauteur
            / 1_000_000
            * hypotheses.masse_volumique_bois_kg_m3
        )
        return (
            lineique * piece.longueur / 1_000,
            lineique,
            "madrier_primaire",
            f"section × {hypotheses.masse_volumique_bois_kg_m3:g} kg/m³",
        )
    if isinstance(piece, PoutreI):
        if (piece.largeur_membrure, piece.hauteur) != (60, 240):
            raise ValueError("masse linéique fabricant absente pour cette poutre en I")
        lineique = hypotheses.masse_lineique_sj60_240_kg_m
        return (
            lineique * piece.longueur / 1_000,
            lineique,
            "solive_i",
            "masse linéique fabricant STEICO SJ60/240",
        )
    if isinstance(piece, Tasseau):
        lineique = (
            piece.largeur
            * piece.hauteur
            / 1_000_000
            * hypotheses.masse_volumique_bois_kg_m3
        )
        return (
            lineique * piece.longueur / 1_000,
            lineique,
            "charge_surfacique",
            f"section × {hypotheses.masse_volumique_bois_kg_m3:g} kg/m³",
        )
    if isinstance(piece, (PanneauFondCaissonOSB, PanneauPlancherOSB)):
        return (
            volume_mm3 / 1_000_000_000 * hypotheses.masse_volumique_osb_kg_m3,
            None,
            "charge_surfacique",
            f"volume CAO × {hypotheses.masse_volumique_osb_kg_m3:g} kg/m³",
        )
    if isinstance(piece, PanneauIsonatFlex55):
        return (
            volume_mm3
            / 1_000_000_000
            * hypotheses.masse_volumique_isolant_kg_m3,
            None,
            "charge_surfacique",
            f"volume posé × {hypotheses.masse_volumique_isolant_kg_m3:g} kg/m³",
        )
    if isinstance(piece, SabotSAI500_120_2):
        return (
            hypotheses.masse_sai500_120_2_kg,
            None,
            "charge_surfacique",
            "masse unitaire fabricant Simpson",
        )
    if isinstance(piece, SabotEWH):
        return (
            hypotheses.masse_ewh240_61_kg,
            None,
            "charge_surfacique",
            "masse unitaire fabricant Simpson",
        )
    raise TypeError(f"masse non renseignée pour {type(piece).__name__}")


def inventorier_masses_plancher(
    plancher: PlancherBois,
    hypotheses: HypothesesMasses | None = None,
) -> RapportMasses:
    """Agrège les masses posées et les masses linéiques disponibles."""

    h = hypotheses or HypothesesMasses()
    groupes: dict[
        tuple[str, float, float | None, str, str],
        tuple[str, int],
    ] = {}
    for element in plancher.elements():
        article = element.piece.article_bom()
        volume = element.forme.volume
        masse, lineique, famille, mode = _masse_element(
            element.piece,
            volume,
            h,
        )
        cle = (article.reference, round(masse, 9), lineique, famille, mode)
        designation, quantite = groupes.get(cle, (article.designation, 0))
        groupes[cle] = (designation, quantite + 1)

    # Les fixations ne sont pas des solides CAO. Leur masse est estimée par le
    # cylindre de tige, sans tête : approximation conservée séparément et
    # visible dans le rapport plutôt que masquée dans un forfait.
    for lot in plancher.lots_fixations():
        article = lot.article_bom()
        if article.longueur_mm is None or article.largeur_mm is None:
            continue
        volume_tige_mm3 = (
            pi * (article.largeur_mm / 2) ** 2 * article.longueur_mm
        )
        masse = (
            volume_tige_mm3
            / 1_000_000_000
            * h.masse_volumique_acier_kg_m3
        )
        mode = "tige cylindrique acier, tête non comprise"
        cle = (
            article.reference,
            round(masse, 9),
            None,
            "charge_surfacique",
            mode,
        )
        groupes[cle] = (article.designation, lot.quantite_bom)

    lignes = tuple(
        LigneMasse(
            reference=reference,
            designation=designation,
            quantite=quantite,
            masse_unitaire_kg=masse,
            masse_totale_kg=masse * quantite,
            masse_lineique_kg_m=lineique,
            famille_charge=famille,
            mode_calcul=mode,
        )
        for (
            reference,
            masse,
            lineique,
            famille,
            mode,
        ), (designation, quantite) in sorted(groupes.items())
    )
    return RapportMasses(h, lignes, plancher.geometrie.surface_plancher)
