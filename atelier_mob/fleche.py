"""Calcul analytique de flèche d'une poutre GT24 simplement appuyée.

Les unités internes sont cohérentes en N, mm et MPa. Le modèle additionne les
déformations de flexion d'Euler-Bernoulli et de cisaillement de Timoshenko.
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class HypothesesFleche:
    portee_mm: float = 3_000.0
    largeur_mm: float = 120.0
    hauteur_mm: float = 240.0
    module_young_mpa: float = 11_000.0
    module_cisaillement_mpa: float = 690.0
    coefficient_cisaillement: float = 5 / 6
    masse_volumique_kg_m3: float = 500.0
    charge_permanente_kN_m2: float = 0.5
    charge_exploitation_kN_m2: float = 1.5
    largeur_tributaire_m: float = 3.5
    charge_ponctuelle_kN: float = 0.0
    inclure_poids_propre: bool = True
    limite_fleche_diviseur: float = 300.0

    def __post_init__(self) -> None:
        positives = (
            self.portee_mm,
            self.largeur_mm,
            self.hauteur_mm,
            self.module_young_mpa,
            self.module_cisaillement_mpa,
            self.coefficient_cisaillement,
            self.masse_volumique_kg_m3,
            self.largeur_tributaire_m,
            self.limite_fleche_diviseur,
        )
        non_negatives = (
            self.charge_permanente_kN_m2,
            self.charge_exploitation_kN_m2,
            self.charge_ponctuelle_kN,
        )
        if not all(isfinite(valeur) for valeur in (*positives, *non_negatives)):
            raise ValueError("toutes les valeurs doivent être des nombres finis")
        if min(positives) <= 0:
            raise ValueError("les dimensions et propriétés doivent être positives")
        if min(non_negatives) < 0:
            raise ValueError("les charges ne peuvent pas être négatives")
        if self.coefficient_cisaillement > 1:
            raise ValueError("le coefficient de cisaillement ne peut pas dépasser 1")

    @property
    def aire_mm2(self) -> float:
        return self.largeur_mm * self.hauteur_mm

    @property
    def inertie_mm4(self) -> float:
        return self.largeur_mm * self.hauteur_mm**3 / 12

    @property
    def module_section_mm3(self) -> float:
        return self.largeur_mm * self.hauteur_mm**2 / 6

    @property
    def poids_propre_kN_m(self) -> float:
        if not self.inclure_poids_propre:
            return 0.0
        aire_m2 = self.aire_mm2 / 1_000_000
        return self.masse_volumique_kg_m3 * aire_m2 * 9.81 / 1_000

    @property
    def charge_lineique_permanente_kN_m(self) -> float:
        return (
            self.charge_permanente_kN_m2 * self.largeur_tributaire_m
            + self.poids_propre_kN_m
        )

    @property
    def charge_lineique_exploitation_kN_m(self) -> float:
        return self.charge_exploitation_kN_m2 * self.largeur_tributaire_m


@dataclass(frozen=True, slots=True)
class ResultatCasFleche:
    nom: str
    charge_lineique_kN_m: float
    charge_ponctuelle_kN: float
    fleche_flexion_mm: float
    fleche_cisaillement_mm: float
    fleche_totale_mm: float
    moment_max_kN_m: float
    contrainte_flexion_mpa: float
    reaction_par_appui_kN: float
    limite_fleche_mm: float
    taux_limite: float
    respecte_limite: bool


@dataclass(frozen=True, slots=True)
class ResultatFleche:
    hypotheses: HypothesesFleche
    permanente: ResultatCasFleche
    exploitation: ResultatCasFleche
    service: ResultatCasFleche
    profil_service: tuple[tuple[float, float], ...]


def _calculer_cas(
    hypotheses: HypothesesFleche,
    nom: str,
    charge_lineique_kN_m: float,
    charge_ponctuelle_kN: float,
) -> ResultatCasFleche:
    longueur = hypotheses.portee_mm
    # 1 kN/m est numériquement égal à 1 N/mm.
    charge_lineique_n_mm = charge_lineique_kN_m
    charge_ponctuelle_n = charge_ponctuelle_kN * 1_000
    ei = hypotheses.module_young_mpa * hypotheses.inertie_mm4
    ga_reduit = (
        hypotheses.module_cisaillement_mpa
        * hypotheses.coefficient_cisaillement
        * hypotheses.aire_mm2
    )

    fleche_flexion = (
        5 * charge_lineique_n_mm * longueur**4 / (384 * ei)
        + charge_ponctuelle_n * longueur**3 / (48 * ei)
    )
    fleche_cisaillement = (
        charge_lineique_n_mm * longueur**2 / (8 * ga_reduit)
        + charge_ponctuelle_n * longueur / (4 * ga_reduit)
    )
    moment_n_mm = (
        charge_lineique_n_mm * longueur**2 / 8
        + charge_ponctuelle_n * longueur / 4
    )
    reaction_n = (
        charge_lineique_n_mm * longueur + charge_ponctuelle_n
    ) / 2
    fleche_totale = fleche_flexion + fleche_cisaillement
    limite = longueur / hypotheses.limite_fleche_diviseur
    taux = fleche_totale / limite

    return ResultatCasFleche(
        nom=nom,
        charge_lineique_kN_m=charge_lineique_kN_m,
        charge_ponctuelle_kN=charge_ponctuelle_kN,
        fleche_flexion_mm=fleche_flexion,
        fleche_cisaillement_mm=fleche_cisaillement,
        fleche_totale_mm=fleche_totale,
        moment_max_kN_m=moment_n_mm / 1_000_000,
        contrainte_flexion_mpa=moment_n_mm / hypotheses.module_section_mm3,
        reaction_par_appui_kN=reaction_n / 1_000,
        limite_fleche_mm=limite,
        taux_limite=taux,
        respecte_limite=taux <= 1,
    )


def _fleche_en_x(
    hypotheses: HypothesesFleche,
    x_mm: float,
    charge_lineique_kN_m: float,
    charge_ponctuelle_kN: float,
) -> float:
    longueur = hypotheses.portee_mm
    x_symetrique = min(x_mm, longueur - x_mm)
    ei = hypotheses.module_young_mpa * hypotheses.inertie_mm4
    ga_reduit = (
        hypotheses.module_cisaillement_mpa
        * hypotheses.coefficient_cisaillement
        * hypotheses.aire_mm2
    )
    charge_ponctuelle_n = charge_ponctuelle_kN * 1_000

    flexion_repartie = (
        charge_lineique_kN_m
        * x_mm
        * (longueur**3 - 2 * longueur * x_mm**2 + x_mm**3)
        / (24 * ei)
    )
    flexion_ponctuelle = (
        charge_ponctuelle_n
        * x_symetrique
        * (3 * longueur**2 - 4 * x_symetrique**2)
        / (48 * ei)
    )
    cisaillement_reparti = (
        charge_lineique_kN_m
        * (longueur * x_mm - x_mm**2)
        / (2 * ga_reduit)
    )
    cisaillement_ponctuel = charge_ponctuelle_n * x_symetrique / (2 * ga_reduit)
    return (
        flexion_repartie
        + flexion_ponctuelle
        + cisaillement_reparti
        + cisaillement_ponctuel
    )


def calculer_fleche(hypotheses: HypothesesFleche) -> ResultatFleche:
    """Calcule les cas G, Q et G+Q, sans pondération ni fluage."""
    charge_g = hypotheses.charge_lineique_permanente_kN_m
    charge_q = hypotheses.charge_lineique_exploitation_kN_m
    permanente = _calculer_cas(hypotheses, "G", charge_g, 0)
    exploitation = _calculer_cas(
        hypotheses,
        "Q",
        charge_q,
        hypotheses.charge_ponctuelle_kN,
    )
    service = _calculer_cas(
        hypotheses,
        "G + Q",
        charge_g + charge_q,
        hypotheses.charge_ponctuelle_kN,
    )
    profil = tuple(
        (
            hypotheses.portee_mm * index / 80,
            _fleche_en_x(
                hypotheses,
                hypotheses.portee_mm * index / 80,
                service.charge_lineique_kN_m,
                service.charge_ponctuelle_kN,
            ),
        )
        for index in range(81)
    )
    return ResultatFleche(
        hypotheses=hypotheses,
        permanente=permanente,
        exploitation=exploitation,
        service=service,
        profil_service=profil,
    )
