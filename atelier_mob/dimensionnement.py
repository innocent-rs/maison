"""Pré-vérification ELU/ELS du plancher selon l'Eurocode 5.

Le module automatise des contrôles déterministes de poutres simplement
appuyées. Il ne remplace ni la définition réglementaire des actions, ni une
note de calcul d'exécution signée par un ingénieur structure.
"""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from home_framework.structure.bois import PoutreI
from home_framework.structure.connecteurs import PointeAncrageCNA4x35, SabotEWH
from home_framework.structure.plancher import PlancherBois

from .masses import HypothesesMasses, RapportMasses, inventorier_masses_plancher


SOURCE_EC5 = (
    "NF EN 1995-1-1:2005 + A1:2008 + A2:2014 et annexe nationale "
    "NF EN 1995-1-1/NA:2010 ; paramètres du projet à confirmer"
)
SOURCE_STEICO = "STEICO ETA-20/0995, tableaux C9 à C11 — SJ60/240"
SOURCE_EWH = "Simpson Strong-Tie EWH — montage TF standard, R1,k = 11 kN"
SOURCE_EWH_DOS_A_DOS = (
    "Simpson Strong-Tie EWH — contrôle géométrique du montage TF dos à dos"
)
SOURCE_SAI = (
    "Simpson Strong-Tie SAI500/120/2 — fixation totale, R1,k = 29,7 kN"
)


class DureeCharge(StrEnum):
    PERMANENTE = "permanente"
    LONGUE = "longue"
    MOYENNE = "moyenne"
    COURTE = "courte"
    INSTANTANEE = "instantanee"


class StatutVerification(StrEnum):
    CONFORME = "conforme"
    NON_CONFORME = "non_conforme"
    NON_VERIFIE = "non_verifie"


_KMOD_BOIS = {
    DureeCharge.PERMANENTE: 0.60,
    DureeCharge.LONGUE: 0.70,
    DureeCharge.MOYENNE: 0.80,
    DureeCharge.COURTE: 0.90,
    DureeCharge.INSTANTANEE: 1.10,
}

_KMOD_STEICO_CISAILLEMENT_NFB = {
    1: {
        DureeCharge.PERMANENTE: 0.30,
        DureeCharge.LONGUE: 0.45,
        DureeCharge.MOYENNE: 0.65,
        DureeCharge.COURTE: 0.85,
        DureeCharge.INSTANTANEE: 1.10,
    },
    2: {
        DureeCharge.PERMANENTE: 0.20,
        DureeCharge.LONGUE: 0.30,
        DureeCharge.MOYENNE: 0.45,
        DureeCharge.COURTE: 0.60,
        DureeCharge.INSTANTANEE: 0.80,
    },
}


@dataclass(frozen=True, slots=True)
class HypothesesEurocode5:
    """Actions et paramètres modifiables de la pré-vérification.

    ``charge_ponctuelle_solive_kN=None`` signifie que la charge de machine n'a
    pas encore été renseignée. Une valeur explicite, y compris zéro, lève cette
    réserve pour le contrôle local d'une solive.
    """

    charge_permanente_surfacique_kN_m2: float | None = None
    charge_permanente_rapportee_kN_m2: float = 0.20
    charge_exploitation_surfacique_kN_m2: float = 2.50
    charge_ponctuelle_solive_kN: float | None = None
    charge_permanente_mur_toiture_kN_m: float | None = None
    charge_variable_toiture_kN_m: float | None = None
    classe_service: int = 2
    duree_charge_variable: DureeCharge = DureeCharge.MOYENNE
    gamma_g: float = 1.35
    gamma_q: float = 1.50
    psi_2: float = 0.80
    limite_fleche_instantanee: float = 300.0
    limite_fleche_finale: float = 250.0

    # Hypothèse GT24 assimilée à une classe de résistance 24 MPa.
    fm_k_bois_mpa: float = 24.0
    fv_k_bois_mpa: float = 3.5
    fc90_k_bois_mpa: float = 2.5
    e_moyen_bois_mpa: float = 11_000.0
    g_moyen_bois_mpa: float = 690.0
    gamma_m_bois: float = 1.30
    masse_volumique_bois_kg_m3: float = 500.0
    largeur_appui_central_mm: float = 200.0

    # Valeurs ETA-20/0995 pour STEICOjoist SJ60/240 à âme NFB.
    steico_moment_k_kN_m: float = 12.94
    steico_cisaillement_k_kN: float = 16.08
    steico_ei_kN_m2: float = 709.0
    steico_ga_mn: float = 3.18
    gamma_m_steico_flexion: float = 1.20
    gamma_m_steico_cisaillement: float = 1.30

    # Capacités caractéristiques fabricant, direction verticale R1.
    resistance_k_ewh_kN: float = 11.0
    resistance_k_sai_kN: float = 29.7
    gamma_m_connecteurs: float = 1.30

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "duree_charge_variable",
            DureeCharge(self.duree_charge_variable),
        )
        if self.classe_service not in (1, 2):
            raise ValueError("la vérification STEICO accepte les classes de service 1 ou 2")
        positifs = (
            self.gamma_g,
            self.gamma_q,
            self.limite_fleche_instantanee,
            self.limite_fleche_finale,
            self.fm_k_bois_mpa,
            self.fv_k_bois_mpa,
            self.fc90_k_bois_mpa,
            self.e_moyen_bois_mpa,
            self.g_moyen_bois_mpa,
            self.gamma_m_bois,
            self.masse_volumique_bois_kg_m3,
            self.largeur_appui_central_mm,
            self.steico_moment_k_kN_m,
            self.steico_cisaillement_k_kN,
            self.steico_ei_kN_m2,
            self.steico_ga_mn,
            self.gamma_m_steico_flexion,
            self.gamma_m_steico_cisaillement,
            self.resistance_k_ewh_kN,
            self.resistance_k_sai_kN,
            self.gamma_m_connecteurs,
        )
        optionnels = (
            self.charge_permanente_surfacique_kN_m2,
            self.charge_ponctuelle_solive_kN,
            self.charge_permanente_mur_toiture_kN_m,
            self.charge_variable_toiture_kN_m,
        )
        non_negatifs = (
            self.charge_permanente_rapportee_kN_m2,
            self.charge_exploitation_surfacique_kN_m2,
            self.psi_2,
            *(valeur for valeur in optionnels if valeur is not None),
        )
        if not all(isfinite(valeur) and valeur > 0 for valeur in positifs):
            raise ValueError("les propriétés et coefficients doivent être positifs")
        if not all(isfinite(valeur) and valeur >= 0 for valeur in non_negatifs):
            raise ValueError("les actions et psi_2 doivent être positifs ou nuls")
        if self.psi_2 > 1:
            raise ValueError("psi_2 ne peut pas dépasser 1")

    @property
    def kmod_bois(self) -> float:
        return _KMOD_BOIS[self.duree_charge_variable]

    @property
    def kdef_bois(self) -> float:
        return 0.60 if self.classe_service == 1 else 0.80

    @property
    def kmod_steico_flexion(self) -> float:
        return _KMOD_BOIS[self.duree_charge_variable]

    @property
    def kmod_steico_cisaillement(self) -> float:
        return _KMOD_STEICO_CISAILLEMENT_NFB[self.classe_service][
            self.duree_charge_variable
        ]

    @property
    def kdef_steico_flexion(self) -> float:
        return 0.60 if self.classe_service == 1 else 0.80

    @property
    def kdef_steico_cisaillement(self) -> float:
        return 2.25 if self.classe_service == 1 else 3.00


@dataclass(frozen=True, slots=True)
class Verification:
    element: str
    critere: str
    etat_limite: str
    sollicitation: float | None
    capacite: float | None
    unite: str
    taux_utilisation: float | None
    statut: StatutVerification
    source: str
    commentaire: str = ""


@dataclass(frozen=True, slots=True)
class RapportEurocode5:
    hypotheses: HypothesesEurocode5
    masses: RapportMasses
    charge_permanente_surfacique_utilisee_kN_m2: float
    charge_permanente_surfacique_solive_kN_m2: float
    verifications: tuple[Verification, ...]
    reserves: tuple[str, ...]

    @property
    def conforme_calculs(self) -> bool:
        return all(
            verification.statut is not StatutVerification.NON_CONFORME
            for verification in self.verifications
        )

    @property
    def complet(self) -> bool:
        return not self.reserves and all(
            verification.statut is not StatutVerification.NON_VERIFIE
            for verification in self.verifications
        )

    @property
    def validation_automatique(self) -> bool:
        return self.conforme_calculs and self.complet

    def lignes_resume(self) -> tuple[str, ...]:
        lignes = []
        for verification in self.verifications:
            if verification.taux_utilisation is None:
                mesure = "non vérifié"
            else:
                mesure = (
                    f"{verification.sollicitation:.3g}/{verification.capacite:.3g} "
                    f"{verification.unite} — {100 * verification.taux_utilisation:.1f} %"
                )
            lignes.append(
                f"[{verification.statut.value.upper()}] {verification.element} — "
                f"{verification.critere} ({verification.etat_limite}) : {mesure}"
            )
        if self.reserves:
            lignes.append("Réserves bloquant la validation complète :")
            lignes.extend(f"- {reserve}" for reserve in self.reserves)
        conclusion = (
            "VALIDATION AUTOMATIQUE ACQUISE"
            if self.validation_automatique
            else (
                "CALCULS CONFORMES, VALIDATION INCOMPLÈTE"
                if self.conforme_calculs
                else "NON-CONFORMITÉ DÉTECTÉE"
            )
        )
        lignes.append(conclusion)
        return tuple(lignes)


def _verification(
    element: str,
    critere: str,
    etat_limite: str,
    sollicitation: float,
    capacite: float,
    unite: str,
    source: str,
    commentaire: str = "",
) -> Verification:
    taux = sollicitation / capacite
    return Verification(
        element=element,
        critere=critere,
        etat_limite=etat_limite,
        sollicitation=sollicitation,
        capacite=capacite,
        unite=unite,
        taux_utilisation=taux,
        statut=(
            StatutVerification.CONFORME
            if taux <= 1
            else StatutVerification.NON_CONFORME
        ),
        source=source,
        commentaire=commentaire,
    )


def _non_verifie(element: str, critere: str, commentaire: str) -> Verification:
    return Verification(
        element=element,
        critere=critere,
        etat_limite="ELU/ELS",
        sollicitation=None,
        capacite=None,
        unite="",
        taux_utilisation=None,
        statut=StatutVerification.NON_VERIFIE,
        source=SOURCE_EC5,
        commentaire=commentaire,
    )


def _fleches_rectangulaires_mm(
    *,
    portee_mm: float,
    largeur_mm: float,
    hauteur_mm: float,
    e_mpa: float,
    g_mpa: float,
    charge_kN_m: float,
) -> tuple[float, float]:
    inertie = largeur_mm * hauteur_mm**3 / 12
    aire_cisaillement = 5 / 6 * largeur_mm * hauteur_mm
    flexion = 5 * charge_kN_m * portee_mm**4 / (384 * e_mpa * inertie)
    cisaillement = charge_kN_m * portee_mm**2 / (
        8 * g_mpa * aire_cisaillement
    )
    return flexion, cisaillement


def _fleches_steico_mm(
    *,
    portee_m: float,
    charge_kN_m: float,
    charge_ponctuelle_kN: float,
    ei_kN_m2: float,
    ga_mn: float,
) -> tuple[float, float]:
    ga_kN = ga_mn * 1_000
    flexion_m = (
        5 * charge_kN_m * portee_m**4 / (384 * ei_kN_m2)
        + charge_ponctuelle_kN * portee_m**3 / (48 * ei_kN_m2)
    )
    cisaillement_m = (
        charge_kN_m * portee_m**2 / (8 * ga_kN)
        + charge_ponctuelle_kN * portee_m / (4 * ga_kN)
    )
    return flexion_m * 1_000, cisaillement_m * 1_000


def verifier_plancher_eurocode5(
    plancher: PlancherBois,
    hypotheses: HypothesesEurocode5 | None = None,
) -> RapportEurocode5:
    """Vérifie automatiquement les éléments actuellement quantifiables."""

    h = hypotheses or HypothesesEurocode5()
    masses = inventorier_masses_plancher(
        plancher,
        HypothesesMasses(
            masse_volumique_bois_kg_m3=h.masse_volumique_bois_kg_m3,
        ),
    )
    charge_permanente_surfacique = (
        h.charge_permanente_surfacique_kN_m2
        if h.charge_permanente_surfacique_kN_m2 is not None
        else (
            masses.charge_surfacique_hors_madriers_kN_m2
            + h.charge_permanente_rapportee_kN_m2
        )
    )
    charge_permanente_surfacique_solive = (
        h.charge_permanente_surfacique_kN_m2
        if h.charge_permanente_surfacique_kN_m2 is not None
        else (
            masses.charge_surfacique_couches_hors_solives_kN_m2
            + h.charge_permanente_rapportee_kN_m2
        )
    )
    verifications: list[Verification] = []
    reserves: list[str] = []

    # Traverse : deux demi-portées supposées simplement appuyées. Ce schéma est
    # conservateur pour la flèche positive et explicite le chemin vers le pieu
    # central, sans revendiquer une analyse complète de poutre continue.
    portee_traverse_mm = plancher.longueur_traverses / 2
    portee_traverse_m = portee_traverse_mm / 1_000
    largeur_tributaire_traverse_m = plancher.entraxe_traverses / 1_000
    poids_propre_traverse = (
        plancher.section_largeur
        * plancher.section_hauteur
        / 1_000_000
        * h.masse_volumique_bois_kg_m3
        * 9.81
        / 1_000
    )
    g_traverse = (
        charge_permanente_surfacique
        * largeur_tributaire_traverse_m
        + poids_propre_traverse
    )
    q_traverse = (
        h.charge_exploitation_surfacique_kN_m2
        * largeur_tributaire_traverse_m
    )
    w_d_traverse = h.gamma_g * g_traverse + h.gamma_q * q_traverse
    moment_d_traverse = w_d_traverse * portee_traverse_m**2 / 8
    effort_tranchant_d_traverse = w_d_traverse * portee_traverse_m / 2
    module_section = (
        plancher.section_largeur * plancher.section_hauteur**2 / 6
    )
    contrainte_flexion = moment_d_traverse * 1_000_000 / module_section
    resistance_flexion = h.kmod_bois * h.fm_k_bois_mpa / h.gamma_m_bois
    verifications.append(
        _verification(
            "Traverse 120×240 — demi-portée",
            "flexion",
            "ELU",
            contrainte_flexion,
            resistance_flexion,
            "MPa",
            SOURCE_EC5,
        )
    )
    contrainte_cisaillement = (
        1.5
        * effort_tranchant_d_traverse
        * 1_000
        / (plancher.section_largeur * plancher.section_hauteur)
    )
    resistance_cisaillement = h.kmod_bois * h.fv_k_bois_mpa / h.gamma_m_bois
    verifications.append(
        _verification(
            "Traverse 120×240 — demi-portée",
            "cisaillement",
            "ELU",
            contrainte_cisaillement,
            resistance_cisaillement,
            "MPa",
            SOURCE_EC5,
        )
    )
    reaction_centrale = 2 * effort_tranchant_d_traverse
    contrainte_appui = (
        reaction_centrale
        * 1_000
        / (plancher.section_largeur * h.largeur_appui_central_mm)
    )
    resistance_appui = h.kmod_bois * h.fc90_k_bois_mpa / h.gamma_m_bois
    verifications.append(
        _verification(
            "Traverse 120×240 — appui central",
            "compression perpendiculaire (kc,90 = 1,0)",
            "ELU",
            contrainte_appui,
            resistance_appui,
            "MPa",
            SOURCE_EC5,
            "Appui utile limité à la largeur de platine renseignée.",
        )
    )
    resistance_sai_d = h.kmod_bois * h.resistance_k_sai_kN / h.gamma_m_connecteurs
    verifications.append(
        _verification(
            "SAI500/120/2 — extrémité de traverse",
            "réaction verticale R1",
            "ELU",
            effort_tranchant_d_traverse,
            resistance_sai_d,
            "kN",
            SOURCE_SAI,
            "Fixation totale et bois porteur compatible avec la fiche fabricant.",
        )
    )
    flex_g, cis_g = _fleches_rectangulaires_mm(
        portee_mm=portee_traverse_mm,
        largeur_mm=plancher.section_largeur,
        hauteur_mm=plancher.section_hauteur,
        e_mpa=h.e_moyen_bois_mpa,
        g_mpa=h.g_moyen_bois_mpa,
        charge_kN_m=g_traverse,
    )
    flex_q, cis_q = _fleches_rectangulaires_mm(
        portee_mm=portee_traverse_mm,
        largeur_mm=plancher.section_largeur,
        hauteur_mm=plancher.section_hauteur,
        e_mpa=h.e_moyen_bois_mpa,
        g_mpa=h.g_moyen_bois_mpa,
        charge_kN_m=q_traverse,
    )
    fleche_instantanee_traverse = flex_g + cis_g + flex_q + cis_q
    fleche_finale_traverse = (
        (flex_g + cis_g) * (1 + h.kdef_bois)
        + (flex_q + cis_q) * (1 + h.psi_2 * h.kdef_bois)
    )
    verifications.append(
        _verification(
            "Traverse 120×240 — demi-portée",
            "flèche instantanée G+Q",
            "ELS",
            fleche_instantanee_traverse,
            portee_traverse_mm / h.limite_fleche_instantanee,
            "mm",
            SOURCE_EC5,
        )
    )
    verifications.append(
        _verification(
            "Traverse 120×240 — demi-portée",
            "flèche finale avec fluage",
            "ELS",
            fleche_finale_traverse,
            portee_traverse_mm / h.limite_fleche_finale,
            "mm",
            SOURCE_EC5,
        )
    )

    # Solive en I : valeurs globales de section et facteurs spécifiques issus
    # de l'ETA. Le point P est appliqué au milieu d'une seule solive.
    solive = PoutreI(
        longueur=plancher.longueur_solives_i,
        hauteur=plancher.hauteur_solives_i,
        largeur_membrure=plancher.largeur_membrure_solives_i,
    )
    portee_solive_m = plancher.longueur_solives_i / 1_000
    largeur_tributaire_solive_m = plancher.entraxe_solives_i / 1_000
    poids_propre_solive = (
        solive.volume_mm3
        / solive.longueur
        / 1_000_000
        * h.masse_volumique_bois_kg_m3
        * 9.81
        / 1_000
    )
    g_solive = (
        charge_permanente_surfacique_solive * largeur_tributaire_solive_m
        + poids_propre_solive
    )
    q_solive = (
        h.charge_exploitation_surfacique_kN_m2 * largeur_tributaire_solive_m
    )
    point_k = h.charge_ponctuelle_solive_kN or 0.0
    w_d_solive = h.gamma_g * g_solive + h.gamma_q * q_solive
    point_d = h.gamma_q * point_k
    moment_d_solive = (
        w_d_solive * portee_solive_m**2 / 8
        + point_d * portee_solive_m / 4
    )
    effort_tranchant_d_solive = (
        w_d_solive * portee_solive_m / 2 + point_d / 2
    )
    resistance_moment_steico = (
        h.kmod_steico_flexion
        * h.steico_moment_k_kN_m
        / h.gamma_m_steico_flexion
    )
    resistance_cisaillement_steico = (
        h.kmod_steico_cisaillement
        * h.steico_cisaillement_k_kN
        / h.gamma_m_steico_cisaillement
    )
    verifications.append(
        _verification(
            "STEICOjoist SJ60/240",
            "moment résistant",
            "ELU",
            moment_d_solive,
            resistance_moment_steico,
            "kN·m",
            SOURCE_STEICO,
        )
    )
    verifications.append(
        _verification(
            "STEICOjoist SJ60/240",
            "effort tranchant résistant",
            "ELU",
            effort_tranchant_d_solive,
            resistance_cisaillement_steico,
            "kN",
            SOURCE_STEICO,
            "Âme NFB sans ouverture pénalisante.",
        )
    )
    resistance_ewh_d = h.kmod_bois * h.resistance_k_ewh_kN / h.gamma_m_connecteurs
    verifications.append(
        _verification(
            "EWH240/61 — extrémité de solive",
            "réaction verticale R1",
            "ELU",
            effort_tranchant_d_solive,
            resistance_ewh_d,
            "kN",
            SOURCE_EWH,
            "Montage à brides supérieures et plan de pointage standard.",
        )
    )
    ewh = SabotEWH(
        largeur_interieure=plancher.largeur_membrure_solives_i + 1,
        hauteur=plancher.hauteur_solives_i,
    )
    pointe_ewh = PointeAncrageCNA4x35()
    verifications.extend(
        (
            _verification(
                "Deux EWH240/61 opposés sur traverse 120×240",
                "non-croisement des pointes opposées",
                "constructibilité",
                2 * pointe_ewh.longueur,
                plancher.section_largeur,
                "mm",
                SOURCE_EWH_DOS_A_DOS,
                (
                    f"Noyau résiduel théorique : "
                    f"{plancher.section_largeur - 2 * pointe_ewh.longueur:g} mm."
                ),
            ),
            _verification(
                "Deux EWH240/61 opposés sur traverse 120×240",
                "non-recouvrement des brides supérieures",
                "constructibilité",
                2 * ewh.longueur_bride_superieure,
                plancher.section_largeur,
                "mm",
                SOURCE_EWH_DOS_A_DOS,
                (
                    f"Bande centrale théorique libre : "
                    f"{plancher.section_largeur - 2 * ewh.longueur_bride_superieure:g} mm."
                ),
            ),
        )
    )
    flex_g_i, cis_g_i = _fleches_steico_mm(
        portee_m=portee_solive_m,
        charge_kN_m=g_solive,
        charge_ponctuelle_kN=0,
        ei_kN_m2=h.steico_ei_kN_m2,
        ga_mn=h.steico_ga_mn,
    )
    flex_q_i, cis_q_i = _fleches_steico_mm(
        portee_m=portee_solive_m,
        charge_kN_m=q_solive,
        charge_ponctuelle_kN=point_k,
        ei_kN_m2=h.steico_ei_kN_m2,
        ga_mn=h.steico_ga_mn,
    )
    fleche_instantanee_solive = flex_g_i + cis_g_i + flex_q_i + cis_q_i
    fleche_finale_solive = (
        flex_g_i * (1 + h.kdef_steico_flexion)
        + cis_g_i * (1 + h.kdef_steico_cisaillement)
        + flex_q_i * (1 + h.psi_2 * h.kdef_steico_flexion)
        + cis_q_i * (1 + h.psi_2 * h.kdef_steico_cisaillement)
    )
    portee_solive_mm = plancher.longueur_solives_i
    verifications.append(
        _verification(
            "STEICOjoist SJ60/240",
            "flèche instantanée G+Q+P",
            "ELS",
            fleche_instantanee_solive,
            portee_solive_mm / h.limite_fleche_instantanee,
            "mm",
            SOURCE_STEICO,
        )
    )
    verifications.append(
        _verification(
            "STEICOjoist SJ60/240",
            "flèche finale avec fluages flexion/cisaillement",
            "ELS",
            fleche_finale_solive,
            portee_solive_mm / h.limite_fleche_finale,
            "mm",
            SOURCE_STEICO,
        )
    )

    if (
        h.charge_permanente_mur_toiture_kN_m is None
        or h.charge_variable_toiture_kN_m is None
    ):
        verifications.append(
            _non_verifie(
                "Poutres longitudinales 120×240",
                "murs et toiture entre pieux",
                "Les charges linéiques des murs, de la toiture, de la neige et du vent "
                "ne sont pas encore renseignées.",
            )
        )
        reserves.append(
            "renseigner les charges linéiques permanentes et variables des murs/toiture"
        )
    else:
        portee_rive_mm = plancher.entraxe_traverses
        portee_rive_m = portee_rive_mm / 1_000
        g_rive = h.charge_permanente_mur_toiture_kN_m + poids_propre_traverse
        q_rive = h.charge_variable_toiture_kN_m
        w_d_rive = h.gamma_g * g_rive + h.gamma_q * q_rive
        moment_d_rive = w_d_rive * portee_rive_m**2 / 8
        contrainte_rive = moment_d_rive * 1_000_000 / module_section
        verifications.append(
            _verification(
                "Poutres longitudinales 120×240",
                "flexion sous murs et toiture",
                "ELU",
                contrainte_rive,
                resistance_flexion,
                "MPa",
                SOURCE_EC5,
            )
        )
        effort_tranchant_d_rive = w_d_rive * portee_rive_m / 2
        contrainte_cisaillement_rive = (
            1.5
            * effort_tranchant_d_rive
            * 1_000
            / (plancher.section_largeur * plancher.section_hauteur)
        )
        verifications.append(
            _verification(
                "Poutres longitudinales 120×240",
                "cisaillement sous murs et toiture",
                "ELU",
                contrainte_cisaillement_rive,
                resistance_cisaillement,
                "MPa",
                SOURCE_EC5,
            )
        )
        # À un pieu intérieur, deux demi-travées longitudinales et l'extrémité
        # d'une traverse peuvent charger la même platine.
        reaction_d_pieu_rive = (
            w_d_rive * portee_rive_m + effort_tranchant_d_traverse
        )
        contrainte_appui_rive = (
            reaction_d_pieu_rive
            * 1_000
            / (plancher.section_largeur * h.largeur_appui_central_mm)
        )
        verifications.append(
            _verification(
                "Poutres longitudinales 120×240 — appui sur pieu",
                "compression perpendiculaire cumulée",
                "ELU",
                contrainte_appui_rive,
                resistance_appui,
                "MPa",
                SOURCE_EC5,
                "Inclut la réaction verticale d'une extrémité de traverse.",
            )
        )
        flex_g_rive, cis_g_rive = _fleches_rectangulaires_mm(
            portee_mm=portee_rive_mm,
            largeur_mm=plancher.section_largeur,
            hauteur_mm=plancher.section_hauteur,
            e_mpa=h.e_moyen_bois_mpa,
            g_mpa=h.g_moyen_bois_mpa,
            charge_kN_m=g_rive,
        )
        flex_q_rive, cis_q_rive = _fleches_rectangulaires_mm(
            portee_mm=portee_rive_mm,
            largeur_mm=plancher.section_largeur,
            hauteur_mm=plancher.section_hauteur,
            e_mpa=h.e_moyen_bois_mpa,
            g_mpa=h.g_moyen_bois_mpa,
            charge_kN_m=q_rive,
        )
        fleche_instantanee_rive = (
            flex_g_rive + cis_g_rive + flex_q_rive + cis_q_rive
        )
        fleche_finale_rive = (
            (flex_g_rive + cis_g_rive) * (1 + h.kdef_bois)
            + (flex_q_rive + cis_q_rive) * (1 + h.psi_2 * h.kdef_bois)
        )
        verifications.append(
            _verification(
                "Poutres longitudinales 120×240",
                "flèche instantanée murs/toiture",
                "ELS",
                fleche_instantanee_rive,
                portee_rive_mm / h.limite_fleche_instantanee,
                "mm",
                SOURCE_EC5,
            )
        )
        verifications.append(
            _verification(
                "Poutres longitudinales 120×240",
                "flèche finale murs/toiture",
                "ELS",
                fleche_finale_rive,
                portee_rive_mm / h.limite_fleche_finale,
                "mm",
                SOURCE_EC5,
            )
        )

    if h.charge_ponctuelle_solive_kN is None:
        reserves.append(
            "renseigner la charge ponctuelle maximale d'une machine sur une solive"
        )
    reserves.extend(
        (
            "confirmer par DoP les valeurs caractéristiques du bois GT24 120×240",
            "confirmer la capacité SAI avec le plan exact de vis CSA5×40 du projet",
            "valider les entraxes, distances de rive et le fendage local "
            "des deux groupes EWH opposés",
            "dimensionner les pieux, platines, ancrages et le sol hors Eurocode 5",
            "vérifier le diaphragme OSB, les vibrations, le feu, le vent et le soulèvement",
            "valider les renforts d'âme, percements et détails d'appui STEICO",
            "confirmer le rôle structural et le plan de pointage des entretoises STEICOjoist",
        )
    )

    return RapportEurocode5(
        h,
        masses,
        charge_permanente_surfacique,
        charge_permanente_surfacique_solive,
        tuple(verifications),
        tuple(reserves),
    )
