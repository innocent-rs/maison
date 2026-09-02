"""Pré-dimensionnement des solives STEICOjoist entre poutres principales.

Les valeurs mécaniques proviennent du guide STEICOconstruction et de
l'ETA-20/0995. Les solives sont modélisées par segments simplement appuyés,
accrochés par sabots entre deux poutres principales successives.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, floor, pi, sqrt

from .calcul import (
    CatalogueSection,
    HypothesesProjet,
    LIMITES_VIBRATOIRES,
    ResultatConfiguration,
    ResultatOptimisation,
    SECTIONS_FOURNISSEUR,
    optimiser,
)


COUT_SABOT_EWH_EUR = 7.30


@dataclass(frozen=True, slots=True)
class CatalogueSolive:
    nom: str
    largeur_mm: float
    hauteur_mm: float
    prix_eur_m: float
    poids_kg_m: float
    moment_caracteristique_kNm: float
    cisaillement_caracteristique_kN: float
    ei_moyen_kNm2: float
    ga_moyen_MN: float
    longueur_max_m: float = 13.0

    def __post_init__(self) -> None:
        valeurs = (
            self.largeur_mm,
            self.hauteur_mm,
            self.prix_eur_m,
            self.poids_kg_m,
            self.moment_caracteristique_kNm,
            self.cisaillement_caracteristique_kN,
            self.ei_moyen_kNm2,
            self.ga_moyen_MN,
            self.longueur_max_m,
        )
        if not self.nom.strip() or min(valeurs) <= 0:
            raise ValueError("les propriétés d'une solive doivent être positives")


# Catalogue disponible sur la fiche Matériaux Naturels au 2 septembre 2026.
# Propriétés : guide STEICOconstruction, valeurs suivant ETA-20/0995.
SOLIVES_FOURNISSEUR = (
    CatalogueSolive("SJ60/240", 60, 240, 14.10, 4.2, 12.94, 16.08, 709, 3.18),
    CatalogueSolive("SJ60/300", 60, 300, 14.40, 4.8, 16.91, 18.47, 1203, 4.18),
    CatalogueSolive("SJ90/360", 90, 360, 20.30, 6.7, 31.02, 20.80, 2714, 5.19),
)


@dataclass(frozen=True, slots=True)
class HypothesesSolives:
    entraxe_max_mm: float = 625.0
    classe_service: int = 2
    limite_fleche_diviseur: float = 350.0
    largeur_isolant_mm: int = 575
    inclure_sabots: bool = True

    def __post_init__(self) -> None:
        if self.entraxe_max_mm <= 0:
            raise ValueError("l'entraxe maximal des solives doit être positif")
        if self.classe_service not in (1, 2):
            raise ValueError("la classe de service des solives doit être 1 ou 2")
        if self.limite_fleche_diviseur <= 0:
            raise ValueError("la limite de flèche des solives doit être positive")
        if self.largeur_isolant_mm not in (0, 575, 600):
            raise ValueError("la largeur d'isolant doit être 575 mm, 600 mm ou désactivée")

    @property
    def kmod_flexion(self) -> float:
        # Charge d'exploitation de durée moyenne, guide STEICO p. 8.
        return 0.80

    @property
    def kmod_cisaillement(self) -> float:
        return 0.65 if self.classe_service == 1 else 0.45


@dataclass(frozen=True, slots=True)
class ResultatConfigurationSolives:
    section: CatalogueSolive
    portee_m: float
    longueur_zone_m: float
    nombre_lignes_solives: int
    nombre_segments: int
    nombre_sabots: int
    entraxe_mm: float
    largeur_vide_isolant_mm: float
    compression_isolant_mm: float | None
    depassement_sous_principale_mm: float
    longueur_totale_m: float
    masse_solives_kg: float
    cout_solives_eur: float
    cout_sabots_eur: float
    cout_eur: float
    charge_g_kN_m: float
    charge_q_kN_m: float
    moment_elu_kNm: float
    moment_resistant_kNm: float
    taux_flexion: float
    effort_tranchant_elu_kN: float
    effort_tranchant_resistant_kN: float
    taux_cisaillement: float
    reaction_sabot_elu_kN: float
    fleche_finale_mm: float
    limite_fleche_mm: float
    taux_fleche: float
    frequence_propre_hz: float
    fleche_sous_1kn_mm: float
    taux_vibration: float | None
    conforme: bool
    contraintes: tuple[str, ...]

    @property
    def taux_dimensionnant(self) -> float:
        return max(self.taux_flexion, self.taux_cisaillement, self.taux_fleche)

    @property
    def critere_dimensionnant(self) -> str:
        if self.taux_dimensionnant == self.taux_fleche:
            return "Flèche finale"
        if self.taux_dimensionnant == self.taux_flexion:
            return "Flexion ELU"
        return "Cisaillement ELU"

    @property
    def isolant_compatible(self) -> bool | None:
        if self.compression_isolant_mm is None:
            return None
        # Une surlargeur de 0 à 20 mm permet une pose légèrement serrée sans
        # transformer l'isolant souple en variable structurelle.
        return 0 <= self.compression_isolant_mm <= 20


@dataclass(frozen=True, slots=True)
class ResultatOptimisationSolives:
    hypotheses: HypothesesSolives
    support: ResultatConfiguration
    configurations: tuple[ResultatConfigurationSolives, ...]
    meilleure: ResultatConfigurationSolives | None
    meilleure_confort: ResultatConfigurationSolives | None


@dataclass(frozen=True, slots=True)
class ResultatSystemePorteur:
    principales: ResultatOptimisation
    solives: ResultatOptimisationSolives | None
    masse_solives_kg_m2: float


def _fleche_uniforme_mm(
    charge_kN_m: float,
    portee_m: float,
    section: CatalogueSolive,
) -> float:
    flexion_m = 5 * charge_kN_m * portee_m**4 / (384 * section.ei_moyen_kNm2)
    cisaillement_m = (
        charge_kN_m * portee_m**2 / (8 * section.ga_moyen_MN * 1_000)
    )
    return (flexion_m + cisaillement_m) * 1_000


def _fleche_ponctuelle_1kn_mm(
    portee_m: float,
    section: CatalogueSolive,
) -> float:
    flexion_m = portee_m**3 / (48 * section.ei_moyen_kNm2)
    cisaillement_m = portee_m / (4 * section.ga_moyen_MN * 1_000)
    return (flexion_m + cisaillement_m) * 1_000


def evaluer_solives(
    projet: HypothesesProjet,
    hypotheses: HypothesesSolives,
    support: ResultatConfiguration,
    section: CatalogueSolive,
    nombre_lignes_solives: int,
) -> ResultatConfigurationSolives:
    if nombre_lignes_solives < 2:
        raise ValueError("il faut au moins deux lignes de solives")

    portee_m = support.entraxe_m
    longueur_zone_m = support.portee_totale_m
    entraxe_m = longueur_zone_m / (nombre_lignes_solives - 1)
    largeur_vide_isolant = entraxe_m * 1_000 - section.largeur_mm
    compression_isolant = (
        hypotheses.largeur_isolant_mm - largeur_vide_isolant
        if hypotheses.largeur_isolant_mm
        else None
    )
    depassement_sous_principale = max(
        0.0,
        section.hauteur_mm - support.section.hauteur_mm,
    )
    charge_g = projet.charge_g_surfacique_kN_m2 * entraxe_m
    charge_g += section.poids_kg_m * 9.81 / 1_000
    charge_q = projet.charge_q_surfacique_kN_m2 * entraxe_m
    charge_elu = 1.35 * charge_g + 1.5 * charge_q

    moment_elu = charge_elu * portee_m**2 / 8
    effort_tranchant = charge_elu * portee_m / 2
    gamma_m = 1.3
    moment_resistant = (
        hypotheses.kmod_flexion * section.moment_caracteristique_kNm / gamma_m
    )
    effort_tranchant_resistant = (
        hypotheses.kmod_cisaillement
        * section.cisaillement_caracteristique_kN
        / gamma_m
    )
    taux_flexion = moment_elu / moment_resistant
    taux_cisaillement = effort_tranchant / effort_tranchant_resistant

    fleche_g = _fleche_uniforme_mm(charge_g, portee_m, section)
    fleche_q = _fleche_uniforme_mm(charge_q, portee_m, section)
    fleche_finale = (
        fleche_g * (1 + projet.kdef)
        + fleche_q * (1 + projet.psi2 * projet.kdef)
    )
    limite_fleche = portee_m * 1_000 / hypotheses.limite_fleche_diviseur
    taux_fleche = fleche_finale / limite_fleche

    masse_lineique = (
        projet.masse_permanente_kg_m2
        + projet.psi2
        * (
            projet.masse_exploitation_kg_m2
            + projet.masse_ajoutee_totale_kg / projet.surface_m2
        )
    ) * entraxe_m + section.poids_kg_m
    ei_n_m2 = section.ei_moyen_kNm2 * 1_000
    frequence_propre = pi / (2 * portee_m**2) * sqrt(ei_n_m2 / masse_lineique)
    fleche_1kn = _fleche_ponctuelle_1kn_mm(portee_m, section)
    limites_vibration = LIMITES_VIBRATOIRES[projet.profil_fleche]
    taux_vibration = None
    if limites_vibration is not None:
        frequence_min, fleche_1kn_limite = limites_vibration
        taux_vibration = max(
            frequence_min / frequence_propre,
            fleche_1kn / fleche_1kn_limite,
        )

    contraintes: list[str] = []
    if portee_m > section.longueur_max_m:
        contraintes.append("portée supérieure à la longueur commerciale")
    if entraxe_m * 1_000 > hypotheses.entraxe_max_mm + 1e-9:
        contraintes.append("entraxe maximal dépassé")
    if entraxe_m * 1_000 + 1e-9 < section.largeur_mm:
        contraintes.append("solives géométriquement superposées")
    if taux_flexion > 1:
        contraintes.append("résistance en flexion")
    if taux_cisaillement > 1:
        contraintes.append("résistance au cisaillement")
    if taux_fleche > 1:
        contraintes.append("flèche finale")

    nombre_segments = nombre_lignes_solives * (support.nombre_poutres - 1)
    nombre_sabots = 2 * nombre_segments if hypotheses.inclure_sabots else 0
    longueur_totale = nombre_lignes_solives * support.largeur_repartie_m
    cout_solives = longueur_totale * section.prix_eur_m
    cout_sabots = nombre_sabots * COUT_SABOT_EWH_EUR
    return ResultatConfigurationSolives(
        section=section,
        portee_m=portee_m,
        longueur_zone_m=longueur_zone_m,
        nombre_lignes_solives=nombre_lignes_solives,
        nombre_segments=nombre_segments,
        nombre_sabots=nombre_sabots,
        entraxe_mm=entraxe_m * 1_000,
        largeur_vide_isolant_mm=largeur_vide_isolant,
        compression_isolant_mm=compression_isolant,
        depassement_sous_principale_mm=depassement_sous_principale,
        longueur_totale_m=longueur_totale,
        masse_solives_kg=longueur_totale * section.poids_kg_m,
        cout_solives_eur=cout_solives,
        cout_sabots_eur=cout_sabots,
        cout_eur=cout_solives + cout_sabots,
        charge_g_kN_m=charge_g,
        charge_q_kN_m=charge_q,
        moment_elu_kNm=moment_elu,
        moment_resistant_kNm=moment_resistant,
        taux_flexion=taux_flexion,
        effort_tranchant_elu_kN=effort_tranchant,
        effort_tranchant_resistant_kN=effort_tranchant_resistant,
        taux_cisaillement=taux_cisaillement,
        reaction_sabot_elu_kN=effort_tranchant,
        fleche_finale_mm=fleche_finale,
        limite_fleche_mm=limite_fleche,
        taux_fleche=taux_fleche,
        frequence_propre_hz=frequence_propre,
        fleche_sous_1kn_mm=fleche_1kn,
        taux_vibration=taux_vibration,
        conforme=not contraintes,
        contraintes=tuple(contraintes),
    )


def optimiser_solives(
    projet: HypothesesProjet,
    hypotheses: HypothesesSolives,
    support: ResultatConfiguration,
    sections: tuple[CatalogueSolive, ...] | list[CatalogueSolive] = SOLIVES_FOURNISSEUR,
) -> ResultatOptimisationSolives:
    if not sections:
        raise ValueError("sélectionnez au moins une section de solive")

    configurations: list[ResultatConfigurationSolives] = []
    for section in sections:
        minimum = max(
            2,
            ceil(support.portee_totale_m / (hypotheses.entraxe_max_mm / 1_000)) + 1,
        )
        maximum = max(
            2,
            floor(support.portee_totale_m / (section.largeur_mm / 1_000)) + 1,
        )
        candidats = [
            evaluer_solives(projet, hypotheses, support, section, nombre)
            for nombre in range(minimum, maximum + 1)
        ]
        conformes = [c for c in candidats if c.conforme]
        if conformes:
            if hypotheses.largeur_isolant_mm:
                compatibles = [c for c in conformes if c.isolant_compatible]
                if compatibles:
                    choix = min(compatibles, key=lambda c: (c.cout_eur, c.entraxe_mm))
                else:
                    choix = min(
                        conformes,
                        key=lambda c: (
                            abs((c.compression_isolant_mm or 0) - 10),
                            c.cout_eur,
                        ),
                    )
                configurations.append(choix)
            else:
                configurations.append(
                    min(conformes, key=lambda c: (c.cout_eur, c.entraxe_mm))
                )
        elif candidats:
            configurations.append(min(candidats, key=lambda c: c.taux_dimensionnant))

    configurations.sort(
        key=lambda c: (
            not c.conforme,
            c.cout_eur if c.conforme else c.taux_dimensionnant,
            c.masse_solives_kg,
        )
    )
    meilleure = next((c for c in configurations if c.conforme), None)
    meilleure_confort = next(
        (
            c
            for c in configurations
            if c.conforme and (c.taux_vibration is None or c.taux_vibration <= 1)
        ),
        None,
    )
    return ResultatOptimisationSolives(
        hypotheses=hypotheses,
        support=support,
        configurations=tuple(configurations),
        meilleure=meilleure,
        meilleure_confort=meilleure_confort,
    )


def optimiser_systeme_porteur(
    projet: HypothesesProjet,
    hypotheses_solives: HypothesesSolives,
    sections_principales: tuple[CatalogueSection, ...] | list[CatalogueSection] = SECTIONS_FOURNISSEUR,
    sections_solives: tuple[CatalogueSolive, ...] | list[CatalogueSolive] = SOLIVES_FOURNISSEUR,
) -> ResultatSystemePorteur:
    """Couple les deux étages en réinjectant le poids propre des solives dans G.

    La charge surfacique saisie reste inchangée dans l'interface. Seul le calcul
    des principales reçoit automatiquement le poids des STEICOjoist retenues.
    """
    masse_solives_kg_m2 = 0.0
    empreinte_precedente: tuple[object, ...] | None = None
    principales: ResultatOptimisation | None = None
    resultat_solives: ResultatOptimisationSolives | None = None

    for _ in range(6):
        projet_principales = replace(
            projet,
            masse_permanente_kg_m2=(
                projet.masse_permanente_kg_m2 + masse_solives_kg_m2
            ),
        )
        principales = optimiser(projet_principales, sections_principales)
        if principales.meilleure is None:
            return ResultatSystemePorteur(
                principales=replace(principales, hypotheses=projet),
                solives=None,
                masse_solives_kg_m2=masse_solives_kg_m2,
            )
        resultat_solives = optimiser_solives(
            projet,
            hypotheses_solives,
            principales.meilleure,
            sections_solives,
        )
        if resultat_solives.meilleure is None:
            return ResultatSystemePorteur(
                principales=replace(principales, hypotheses=projet),
                solives=resultat_solives,
                masse_solives_kg_m2=masse_solives_kg_m2,
            )
        meilleure_principale = principales.meilleure
        meilleure_solive = resultat_solives.meilleure
        nouvelle_masse = meilleure_solive.masse_solives_kg / projet.surface_m2
        empreinte = (
            meilleure_principale.section.nom,
            meilleure_principale.orientation,
            meilleure_principale.nombre_poutres,
            meilleure_principale.nombre_travees,
            meilleure_solive.section.nom,
            meilleure_solive.nombre_lignes_solives,
            round(nouvelle_masse, 9),
        )
        if empreinte == empreinte_precedente:
            masse_solives_kg_m2 = nouvelle_masse
            break
        empreinte_precedente = empreinte
        masse_solives_kg_m2 = nouvelle_masse

    # Recalcul final avec la masse convergée afin que les taux des principales
    # correspondent exactement au système affiché.
    projet_principales = replace(
        projet,
        masse_permanente_kg_m2=projet.masse_permanente_kg_m2 + masse_solives_kg_m2,
    )
    principales = optimiser(projet_principales, sections_principales)
    resultat_solives = (
        optimiser_solives(
            projet,
            hypotheses_solives,
            principales.meilleure,
            sections_solives,
        )
        if principales.meilleure
        else None
    )
    return ResultatSystemePorteur(
        principales=replace(principales, hypotheses=projet),
        solives=resultat_solives,
        masse_solives_kg_m2=masse_solives_kg_m2,
    )
