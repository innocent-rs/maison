"""Pré-dimensionnement et optimisation de poutres principales en bois.

Le modèle est volontairement simple : poutres principales rectangulaires,
parallèles et isostatiques, avec une poutre sur chacune des deux rives. La
charge du complexe secondaire (futures solives en I et plancher) est ramenée
à une charge linéique uniforme par largeur tributaire. Les unités internes
sont N, mm et MPa.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite, pi, sqrt
from typing import Literal


Orientation = Literal["longueur", "largeur"]
ProfilFleche = Literal["atelier", "maison", "maison_fragile", "toiture", "personnalise"]
ProfilUsage = Literal["maison", "atelier", "stockage", "toiture", "personnalise"]

PROFILS_FLECHE: dict[str, float] = {
    "atelier": 250.0,
    "maison": 300.0,
    "maison_fragile": 400.0,
    "toiture": 200.0,
}

PROFILS_USAGE: dict[str, tuple[float, float]] = {
    # Masses surfaciques de pré-dimensionnement G/Q en kg/m², toujours éditables.
    "maison": (75.0, 150.0),
    "atelier": (100.0, 250.0),
    "stockage": (125.0, 500.0),
    "toiture": (60.0, 100.0),
}

LIMITES_VIBRATOIRES: dict[str, tuple[float, float] | None] = {
    "atelier": (4.5, 2.0),
    "maison": (8.0, 1.0),
    "maison_fragile": (8.0, 0.5),
    "toiture": None,
    "personnalise": (8.0, 1.0),
}

# Hypothèse V1 volontairement figée. La platine est descriptive : sa vérification
# locale et celle de la liaison au bois restent hors du modèle.
COUT_PIEU_VISSE_EUR = 500.0
CAPACITE_PIEU_VISSE_TONNES = 5.0
DIAMETRE_PLATINE_PIEU_MM = 200.0
MAX_TRAVEES_RECHERCHE = 1_000


@dataclass(frozen=True, slots=True)
class CatalogueSection:
    nom: str
    largeur_mm: float
    hauteur_mm: float
    prix_eur_m: float
    longueur_max_m: float = 13.0
    classe_resistance: str = "C24"
    e_moyen_mpa: float | None = None
    g_moyen_mpa: float | None = None
    fm_k_mpa: float | None = None
    fv_k_mpa: float | None = None
    fc90_k_mpa: float | None = None
    masse_volumique_kg_m3: float | None = None

    def __post_init__(self) -> None:
        valeurs = (
            self.largeur_mm,
            self.hauteur_mm,
            self.prix_eur_m,
            self.longueur_max_m,
        )
        proprietes_optionnelles = (
            self.e_moyen_mpa,
            self.g_moyen_mpa,
            self.fm_k_mpa,
            self.fv_k_mpa,
            self.fc90_k_mpa,
            self.masse_volumique_kg_m3,
        )
        if not self.nom.strip() or not self.classe_resistance.strip():
            raise ValueError("chaque section doit avoir un nom")
        if not all(isfinite(v) for v in valeurs) or min(valeurs) <= 0:
            raise ValueError(f"les valeurs de la section {self.nom} doivent être positives")
        if any(
            valeur is not None
            and (not isfinite(valeur) or valeur <= 0)
            for valeur in proprietes_optionnelles
        ):
            raise ValueError(
                f"les propriétés du matériau {self.classe_resistance} doivent être positives"
            )

    @property
    def aire_mm2(self) -> float:
        return self.largeur_mm * self.hauteur_mm

    @property
    def inertie_mm4(self) -> float:
        return self.largeur_mm * self.hauteur_mm**3 / 12

    @property
    def module_section_mm3(self) -> float:
        return self.largeur_mm * self.hauteur_mm**2 / 6


SECTION_PRINCIPALE = CatalogueSection("120 × 240", 120, 240, 40.01, 13)

# Catalogue Matériaux Naturels relevé le 2 septembre 2026. Les propriétés du
# GL24H suivent l'EN 14080 ; la densité de 450 kg/m³ est celle déclarée sur la
# fiche du produit vendu. Les propriétés laissées à None sur le C24 restent
# pilotées par les hypothèses avancées du projet.
SECTIONS_FOURNISSEUR = (
    SECTION_PRINCIPALE,
    CatalogueSection(
        "140 × 320",
        140,
        320,
        68.80,
        13.5,
        classe_resistance="GL24H",
        e_moyen_mpa=11_500,
        g_moyen_mpa=650,
        fm_k_mpa=24,
        fv_k_mpa=3.5,
        fc90_k_mpa=2.5,
        masse_volumique_kg_m3=450,
    ),
    CatalogueSection(
        "140 × 360",
        140,
        360,
        77.40,
        13.5,
        classe_resistance="GL24H",
        e_moyen_mpa=11_500,
        g_moyen_mpa=650,
        fm_k_mpa=24,
        fv_k_mpa=3.5,
        fc90_k_mpa=2.5,
        masse_volumique_kg_m3=450,
    ),
)


@dataclass(frozen=True, slots=True)
class HypothesesProjet:
    longueur_m: float = 10.0
    largeur_m: float = 10.0
    masse_permanente_kg_m2: float = 75.0
    masse_exploitation_kg_m2: float = 150.0
    masse_ajoutee_totale_kg: float = 0.0
    masse_volumique_kg_m3: float = 500.0
    profil_usage: ProfilUsage = "maison"
    # 0 laisse l'optimisation structurelle libre. Une valeur positive représente
    # la portée maximale provisoirement admise pour le futur système secondaire.
    entraxe_max_m: float = 4.0
    profil_fleche: ProfilFleche = "maison"
    limite_fleche_diviseur: float = 300.0
    e_moyen_mpa: float = 11_000.0
    g_moyen_mpa: float = 690.0
    fm_k_mpa: float = 24.0
    fv_k_mpa: float = 4.0
    fc90_k_mpa: float = 2.5
    kc90: float = 1.0
    kmod: float = 0.8
    kdef: float = 0.8
    psi2: float = 0.3
    gamma_m: float = 1.3
    coefficient_cisaillement: float = 5 / 6
    orientation: Literal["auto", "longueur", "largeur"] = "auto"
    inclure_poids_propre: bool = True

    def __post_init__(self) -> None:
        strictement_positifs = (
            self.longueur_m,
            self.largeur_m,
            self.masse_volumique_kg_m3,
            self.limite_fleche_diviseur,
            self.e_moyen_mpa,
            self.g_moyen_mpa,
            self.fm_k_mpa,
            self.fv_k_mpa,
            self.fc90_k_mpa,
            self.kc90,
            self.kmod,
            self.gamma_m,
            self.coefficient_cisaillement,
        )
        non_negatifs = (
            self.masse_permanente_kg_m2,
            self.masse_exploitation_kg_m2,
            self.masse_ajoutee_totale_kg,
            self.entraxe_max_m,
            self.kdef,
            self.psi2,
        )
        if not all(isfinite(v) for v in (*strictement_positifs, *non_negatifs)):
            raise ValueError("toutes les hypothèses doivent être des nombres finis")
        if min(strictement_positifs) <= 0 or min(non_negatifs) < 0:
            raise ValueError("les dimensions et propriétés doivent être positives")
        if self.orientation not in ("auto", "longueur", "largeur"):
            raise ValueError("le sens de portée est invalide")
        if self.profil_usage not in (*PROFILS_USAGE, "personnalise"):
            raise ValueError("le profil d'usage est invalide")
        if self.profil_fleche not in (*PROFILS_FLECHE, "personnalise"):
            raise ValueError("le profil de flèche est invalide")
        if self.profil_fleche in PROFILS_FLECHE:
            object.__setattr__(
                self,
                "limite_fleche_diviseur",
                PROFILS_FLECHE[self.profil_fleche],
            )
        if self.psi2 > 1 or self.coefficient_cisaillement > 1:
            raise ValueError("ψ₂ et le coefficient de cisaillement ne peuvent pas dépasser 1")

    @property
    def surface_m2(self) -> float:
        return self.longueur_m * self.largeur_m

    @property
    def charge_g_surfacique_kN_m2(self) -> float:
        return self.masse_permanente_kg_m2 * 9.81 / 1_000

    @property
    def charge_q_surfacique_kN_m2(self) -> float:
        masse_totale_par_m2 = self.masse_ajoutee_totale_kg / self.surface_m2
        return (self.masse_exploitation_kg_m2 + masse_totale_par_m2) * 9.81 / 1_000


@dataclass(frozen=True, slots=True)
class ResultatPieu:
    identifiant: str
    colonne: int
    rangee: int
    x_m: float
    y_m: float
    type_appui: Literal["angle", "rive", "intermediaire"]
    reaction_els_kN: float
    reaction_elu_kN: float
    taux_capacite: float

    @property
    def niveau(self) -> str:
        if self.taux_capacite > 1:
            return "depasse"
        if self.taux_capacite >= 0.7:
            return "vigilance"
        return "marge"


@dataclass(frozen=True, slots=True)
class ResultatConfiguration:
    section: CatalogueSection
    orientation: Orientation
    portee_m: float
    portee_totale_m: float
    largeur_repartie_m: float
    nombre_poutres: int
    nombre_travees: int
    nombre_lignes_appui_intermediaires: int
    nombre_pieux_intermediaires: int
    nombre_pieux_rive: int
    nombre_pieux_total: int
    entraxe_m: float
    longueur_totale_m: float
    cout_bois_eur: float
    cout_appuis_eur: float
    cout_eur: float
    masse_poutres_kg: float
    charge_g_kN_m: float
    charge_q_kN_m: float
    fleche_g_mm: float
    fleche_q_mm: float
    fleche_finale_mm: float
    limite_fleche_mm: float
    taux_fleche: float
    moment_elu_kN_m: float
    contrainte_flexion_mpa: float
    resistance_flexion_mpa: float
    taux_flexion: float
    effort_tranchant_elu_kN: float
    contrainte_cisaillement_mpa: float
    resistance_cisaillement_mpa: float
    taux_cisaillement: float
    reaction_pieu_max_elu_kN: float
    capacite_appui_kN: float
    taux_appui: float
    contrainte_compression_appui_mpa: float
    resistance_compression_appui_mpa: float
    taux_compression_appui: float
    frequence_propre_hz: float
    frequence_min_hz: float | None
    fleche_sous_1kn_mm: float
    fleche_sous_1kn_limite_mm: float | None
    taux_vibration: float | None
    vibration_respectee: bool | None
    pieux: tuple[ResultatPieu, ...]
    conforme: bool
    contraintes: tuple[str, ...]

    @property
    def taux_dimensionnant(self) -> float:
        return max(
            self.taux_fleche,
            self.taux_flexion,
            self.taux_cisaillement,
            self.taux_appui,
            self.taux_compression_appui,
        )

    @property
    def critere_dimensionnant(self) -> str:
        taux = self.taux_dimensionnant
        if taux == self.taux_fleche:
            return "Flèche finale"
        if taux == self.taux_flexion:
            return "Flexion ELU"
        if taux == self.taux_cisaillement:
            return "Cisaillement ELU"
        if taux == self.taux_appui:
            return "Pieu vissé ELU"
        return "Compression sur platine"


@dataclass(frozen=True, slots=True)
class ResultatOptimisation:
    hypotheses: HypothesesProjet
    configurations: tuple[ResultatConfiguration, ...]
    meilleure: ResultatConfiguration | None
    moins_de_pieux: ResultatConfiguration | None
    meilleure_marge: ResultatConfiguration | None
    alternatives: tuple[ResultatConfiguration, ...]
    # Configurations conformes légères (sans le détail des pieux), destinées
    # aux optimisations couplées. Les vues continuent d'utiliser les champs
    # ci-dessus, entièrement matérialisés.
    candidats_conformes: tuple[ResultatConfiguration, ...] = ()


def _fleche_uniforme_mm(
    charge_kN_m: float,
    portee_mm: float,
    section: CatalogueSection,
    hypotheses: HypothesesProjet,
) -> float:
    # 1 kN/m = 1 N/mm. Flexion d'Euler-Bernoulli + cisaillement de Timoshenko.
    e_moyen_mpa = section.e_moyen_mpa or hypotheses.e_moyen_mpa
    g_moyen_mpa = section.g_moyen_mpa or hypotheses.g_moyen_mpa
    flexion = (
        5
        * charge_kN_m
        * portee_mm**4
        / (384 * e_moyen_mpa * section.inertie_mm4)
    )
    cisaillement = (
        charge_kN_m
        * portee_mm**2
        / (
            8
            * hypotheses.coefficient_cisaillement
            * g_moyen_mpa
            * section.aire_mm2
        )
    )
    return flexion + cisaillement


def _fleche_ponctuelle_centrale_mm(
    charge_kN: float,
    portee_mm: float,
    section: CatalogueSection,
    hypotheses: HypothesesProjet,
) -> float:
    charge_n = charge_kN * 1_000
    e_moyen_mpa = section.e_moyen_mpa or hypotheses.e_moyen_mpa
    g_moyen_mpa = section.g_moyen_mpa or hypotheses.g_moyen_mpa
    flexion = (
        charge_n
        * portee_mm**3
        / (48 * e_moyen_mpa * section.inertie_mm4)
    )
    cisaillement = (
        charge_n
        * portee_mm
        / (
            4
            * hypotheses.coefficient_cisaillement
            * g_moyen_mpa
            * section.aire_mm2
        )
    )
    return flexion + cisaillement


def evaluer_configuration(
    hypotheses: HypothesesProjet,
    section: CatalogueSection,
    orientation: Orientation,
    nombre_poutres: int,
    nombre_travees: int = 1,
    *,
    generer_pieux: bool = True,
) -> ResultatConfiguration:
    if nombre_poutres < 2:
        raise ValueError("il faut au moins deux poutres principales, une sur chaque rive")
    if nombre_travees < 1 or not isinstance(nombre_travees, int):
        raise ValueError("il faut au moins une travée")
    if orientation == "longueur":
        portee_totale_m, largeur_repartie_m = hypotheses.longueur_m, hypotheses.largeur_m
    else:
        portee_totale_m, largeur_repartie_m = hypotheses.largeur_m, hypotheses.longueur_m

    # Sous charges uniformes et avec des appuis de même nature, des travées
    # égales minimisent la portée maximale, donc la flèche dimensionnante.
    portee_m = portee_totale_m / nombre_travees

    entraxe_m = largeur_repartie_m / (nombre_poutres - 1)
    e_moyen_mpa = section.e_moyen_mpa or hypotheses.e_moyen_mpa
    masse_volumique_kg_m3 = (
        section.masse_volumique_kg_m3 or hypotheses.masse_volumique_kg_m3
    )
    poids_propre_kN_m = 0.0
    if hypotheses.inclure_poids_propre:
        poids_propre_kN_m = (
            section.aire_mm2 / 1_000_000
            * masse_volumique_kg_m3
            * 9.81
            / 1_000
        )
    # Avec seulement deux rives, chacune ne reprend qu'un demi-entraxe. À partir
    # de trois lignes, une poutre intérieure reprend l'entraxe complet et gouverne.
    largeur_tributaire_m = entraxe_m / 2 if nombre_poutres == 2 else entraxe_m
    charge_g = (
        hypotheses.charge_g_surfacique_kN_m2 * largeur_tributaire_m
        + poids_propre_kN_m
    )
    charge_q = hypotheses.charge_q_surfacique_kN_m2 * largeur_tributaire_m
    portee_mm = portee_m * 1_000
    fleche_g = _fleche_uniforme_mm(charge_g, portee_mm, section, hypotheses)
    fleche_q = _fleche_uniforme_mm(charge_q, portee_mm, section, hypotheses)
    # EN 1995-1-1 §2.2.3 : déformation finale avec fluage des actions G et Q.
    fleche_finale = (
        fleche_g * (1 + hypotheses.kdef)
        + fleche_q * (1 + hypotheses.psi2 * hypotheses.kdef)
    )
    limite_fleche = portee_mm / hypotheses.limite_fleche_diviseur
    taux_fleche = fleche_finale / limite_fleche

    charge_elu = 1.35 * charge_g + 1.5 * charge_q
    moment_n_mm = charge_elu * portee_mm**2 / 8
    effort_tranchant_n = charge_elu * portee_mm / 2
    contrainte_flexion = moment_n_mm / section.module_section_mm3
    contrainte_cisaillement = 1.5 * effort_tranchant_n / section.aire_mm2
    fm_k_mpa = section.fm_k_mpa or hypotheses.fm_k_mpa
    fv_k_mpa = section.fv_k_mpa or hypotheses.fv_k_mpa
    fc90_k_mpa = section.fc90_k_mpa or hypotheses.fc90_k_mpa
    resistance_flexion = hypotheses.kmod * fm_k_mpa / hypotheses.gamma_m
    resistance_cisaillement = hypotheses.kmod * fv_k_mpa / hypotheses.gamma_m
    taux_flexion = contrainte_flexion / resistance_flexion
    taux_cisaillement = contrainte_cisaillement / resistance_cisaillement
    nombre_lignes_appui_intermediaires = nombre_travees - 1
    # Un pieu de rive reprend qL/2. Un pieu intérieur commun à deux travées
    # reprend qL/2 + qL/2 et gouverne dès qu'une rangée intermédiaire existe.
    reaction_pieu_max = (
        charge_elu * portee_m
        if nombre_lignes_appui_intermediaires
        else charge_elu * portee_m / 2
    )
    capacite_appui_kN = CAPACITE_PIEU_VISSE_TONNES * 9.81
    taux_appui = reaction_pieu_max / capacite_appui_kN

    longueur_contact_mm = (
        DIAMETRE_PLATINE_PIEU_MM
        if nombre_lignes_appui_intermediaires
        else DIAMETRE_PLATINE_PIEU_MM / 2
    )
    aire_contact_mm2 = min(section.largeur_mm, DIAMETRE_PLATINE_PIEU_MM) * longueur_contact_mm
    contrainte_compression_appui = reaction_pieu_max * 1_000 / aire_contact_mm2
    resistance_compression_appui = (
        hypotheses.kc90
        * hypotheses.kmod
        * fc90_k_mpa
        / hypotheses.gamma_m
    )
    taux_compression_appui = (
        contrainte_compression_appui / resistance_compression_appui
    )

    masse_q_kg_m2 = (
        hypotheses.masse_exploitation_kg_m2
        + hypotheses.masse_ajoutee_totale_kg / hypotheses.surface_m2
    )
    masse_lineique_kg_m = (
        (
            hypotheses.masse_permanente_kg_m2
            + hypotheses.psi2 * masse_q_kg_m2
        )
        * largeur_tributaire_m
        + section.aire_mm2 / 1_000_000 * masse_volumique_kg_m3
    )
    ei_n_m2 = e_moyen_mpa * section.inertie_mm4 * 1e-6
    frequence_propre = (
        pi / (2 * portee_m**2) * sqrt(ei_n_m2 / masse_lineique_kg_m)
    )
    fleche_sous_1kn = _fleche_ponctuelle_centrale_mm(
        1.0, portee_mm, section, hypotheses
    )
    limites_vibration = LIMITES_VIBRATOIRES[hypotheses.profil_fleche]
    if limites_vibration is None:
        frequence_min = None
        fleche_1kn_limite = None
        taux_vibration = None
        vibration_respectee = None
    else:
        frequence_min, fleche_1kn_limite = limites_vibration
        taux_vibration = max(
            frequence_min / frequence_propre,
            fleche_sous_1kn / fleche_1kn_limite,
        )
        vibration_respectee = taux_vibration <= 1

    pieux: list[ResultatPieu] = []
    if generer_pieux:
        index_pieu = 1
        for rangee in range(nombre_travees + 1):
            facteur_reaction = 0.5 if rangee in (0, nombre_travees) else 1.0
            for colonne in range(nombre_poutres):
                largeur_pieu = (
                    entraxe_m / 2
                    if colonne in (0, nombre_poutres - 1)
                    else entraxe_m
                )
                qg_pieu = (
                    hypotheses.charge_g_surfacique_kN_m2 * largeur_pieu
                    + poids_propre_kN_m
                )
                qq_pieu = hypotheses.charge_q_surfacique_kN_m2 * largeur_pieu
                reaction_els = facteur_reaction * (qg_pieu + qq_pieu) * portee_m
                reaction_elu = (
                    facteur_reaction
                    * (1.35 * qg_pieu + 1.5 * qq_pieu)
                    * portee_m
                )
                angle = (
                    rangee in (0, nombre_travees)
                    and colonne in (0, nombre_poutres - 1)
                )
                type_appui: Literal["angle", "rive", "intermediaire"] = (
                    "angle"
                    if angle
                    else "rive"
                    if rangee in (0, nombre_travees)
                    else "intermediaire"
                )
                pieux.append(
                    ResultatPieu(
                        identifiant=f"P{index_pieu:02d}",
                        colonne=colonne,
                        rangee=rangee,
                        x_m=colonne * entraxe_m,
                        y_m=rangee * portee_m,
                        type_appui=type_appui,
                        reaction_els_kN=reaction_els,
                        reaction_elu_kN=reaction_elu,
                        taux_capacite=reaction_elu / capacite_appui_kN,
                    )
                )
                index_pieu += 1

    contraintes: list[str] = []
    longueur_requise_m = max(hypotheses.longueur_m, hypotheses.largeur_m)
    if longueur_requise_m > section.longueur_max_m + 1e-12:
        contraintes.append("dimension du plancher supérieure à la longueur commerciale")
    if hypotheses.entraxe_max_m and entraxe_m > hypotheses.entraxe_max_m + 1e-12:
        contraintes.append("portée secondaire maximale dépassée")
    if entraxe_m + 1e-12 < section.largeur_mm / 1_000:
        contraintes.append("poutres géométriquement superposées")
    if taux_fleche > 1:
        contraintes.append("flèche finale")
    if taux_flexion > 1:
        contraintes.append("résistance en flexion")
    if taux_cisaillement > 1:
        contraintes.append("résistance au cisaillement")
    if taux_appui > 1:
        contraintes.append("capacité statique du pieu vissé")
    if taux_compression_appui > 1:
        contraintes.append("compression du bois sur la platine")

    longueur_totale = nombre_poutres * portee_totale_m
    masse_poutres = (
        longueur_totale
        * section.aire_mm2
        / 1_000_000
        * masse_volumique_kg_m3
    )
    nombre_pieux_intermediaires = (
        nombre_poutres * nombre_lignes_appui_intermediaires
    )
    # Chaque ligne de poutre simplement appuyée doit reposer aux deux rives.
    # Les quatre intersections extrêmes sont donc toujours les quatre coins.
    nombre_pieux_rive = 2 * nombre_poutres
    nombre_pieux_total = nombre_pieux_intermediaires + nombre_pieux_rive
    cout_bois = longueur_totale * section.prix_eur_m
    cout_appuis = nombre_pieux_total * COUT_PIEU_VISSE_EUR
    return ResultatConfiguration(
        section=section,
        orientation=orientation,
        portee_m=portee_m,
        portee_totale_m=portee_totale_m,
        largeur_repartie_m=largeur_repartie_m,
        nombre_poutres=nombre_poutres,
        nombre_travees=nombre_travees,
        nombre_lignes_appui_intermediaires=nombre_lignes_appui_intermediaires,
        nombre_pieux_intermediaires=nombre_pieux_intermediaires,
        nombre_pieux_rive=nombre_pieux_rive,
        nombre_pieux_total=nombre_pieux_total,
        entraxe_m=entraxe_m,
        longueur_totale_m=longueur_totale,
        cout_bois_eur=cout_bois,
        cout_appuis_eur=cout_appuis,
        cout_eur=cout_bois + cout_appuis,
        masse_poutres_kg=masse_poutres,
        charge_g_kN_m=charge_g,
        charge_q_kN_m=charge_q,
        fleche_g_mm=fleche_g,
        fleche_q_mm=fleche_q,
        fleche_finale_mm=fleche_finale,
        limite_fleche_mm=limite_fleche,
        taux_fleche=taux_fleche,
        moment_elu_kN_m=moment_n_mm / 1_000_000,
        contrainte_flexion_mpa=contrainte_flexion,
        resistance_flexion_mpa=resistance_flexion,
        taux_flexion=taux_flexion,
        effort_tranchant_elu_kN=effort_tranchant_n / 1_000,
        contrainte_cisaillement_mpa=contrainte_cisaillement,
        resistance_cisaillement_mpa=resistance_cisaillement,
        taux_cisaillement=taux_cisaillement,
        reaction_pieu_max_elu_kN=reaction_pieu_max,
        capacite_appui_kN=capacite_appui_kN,
        taux_appui=taux_appui,
        contrainte_compression_appui_mpa=contrainte_compression_appui,
        resistance_compression_appui_mpa=resistance_compression_appui,
        taux_compression_appui=taux_compression_appui,
        frequence_propre_hz=frequence_propre,
        frequence_min_hz=frequence_min,
        fleche_sous_1kn_mm=fleche_sous_1kn,
        fleche_sous_1kn_limite_mm=fleche_1kn_limite,
        taux_vibration=taux_vibration,
        vibration_respectee=vibration_respectee,
        pieux=tuple(pieux),
        conforme=not contraintes,
        contraintes=tuple(contraintes),
    )


def _minimum_geometrique(hypotheses: HypothesesProjet, orientation: Orientation) -> int:
    largeur = hypotheses.largeur_m if orientation == "longueur" else hypotheses.longueur_m
    if hypotheses.entraxe_max_m == 0:
        return 2
    return max(2, ceil(largeur / hypotheses.entraxe_max_m) + 1)


def _maximum_sans_chevauchement(
    hypotheses: HypothesesProjet,
    section: CatalogueSection,
    orientation: Orientation,
) -> int:
    """Nombre maximal de lignes dont les sections ne se chevauchent pas.

    Les axes des deux poutres de rive sont placés sur les limites du rectangle,
    conformément au modèle de largeur tributaire utilisé par l'outil.
    """
    largeur_m = (
        hypotheses.largeur_m if orientation == "longueur" else hypotheses.longueur_m
    )
    return max(1, floor(largeur_m / (section.largeur_mm / 1_000)) + 1)


def optimiser(
    hypotheses: HypothesesProjet,
    sections: tuple[CatalogueSection, ...] | list[CatalogueSection] = SECTIONS_FOURNISSEUR,
    *,
    exploration_systeme: bool = False,
) -> ResultatOptimisation:
    if not sections:
        raise ValueError("sélectionnez au moins une section")
    orientations: tuple[Orientation, ...]
    if hypotheses.orientation == "auto":
        orientations = ("longueur", "largeur")
    else:
        orientations = (hypotheses.orientation,)

    configurations: list[ResultatConfiguration] = []
    toutes_conformes: list[ResultatConfiguration] = []
    for orientation in orientations:
        for section in sections:
            candidates: list[ResultatConfiguration] = []
            minimum = _minimum_geometrique(hypotheses, orientation)
            maximum_physique = _maximum_sans_chevauchement(
                hypotheses, section, orientation
            )
            longueur_requise_m = max(
                hypotheses.longueur_m,
                hypotheses.largeur_m,
            )
            if longueur_requise_m > section.longueur_max_m + 1e-12:
                # Le système constructif exige que la référence puisse couvrir
                # le plus grand côté, y compris ses éléments de rive. Les appuis
                # intermédiaires réduisent la portée mécanique mais ne rendent
                # pas disponible une pièce commerciale plus longue.
                configurations.append(
                    evaluer_configuration(
                        hypotheses,
                        section,
                        orientation,
                        min(minimum, max(2, maximum_physique)),
                        generer_pieux=False,
                    )
                )
                continue
            meilleur_cout = float("inf")
            for nombre_travees in range(1, MAX_TRAVEES_RECHERCHE + 1):
                # Si la contrainte secondaire exige déjà des poutres qui se
                # chevauchent, on garde la dernière trame physique pour le diagnostic.
                debut = (
                    minimum
                    if minimum <= maximum_physique
                    else max(2, maximum_physique)
                )
                maximum_recherche = max(2, maximum_physique)

                # Pour un nombre de travées fixé, le coût croît avec le nombre
                # de poutres. Cette borne permet d'arrêter les travées dès
                # qu'aucune suivante ne peut battre la meilleure trouvée.
                cout_minimal = debut * (
                    section.prix_eur_m
                    * (
                        hypotheses.longueur_m
                        if orientation == "longueur"
                        else hypotheses.largeur_m
                    )
                    + COUT_PIEU_VISSE_EUR * (nombre_travees + 1)
                )
                if (
                    not exploration_systeme
                    and cout_minimal > meilleur_cout + 1e-9
                ):
                    break

                evaluations: dict[int, ResultatConfiguration] = {}

                def evaluer_nombre(nombre: int) -> ResultatConfiguration:
                    if nombre not in evaluations:
                        evaluations[nombre] = evaluer_configuration(
                            hypotheses,
                            section,
                            orientation,
                            nombre,
                            nombre_travees,
                            generer_pieux=False,
                        )
                    return evaluations[nombre]

                # Toutes les vérifications s'améliorent lorsque les poutres se
                # rapprochent. Une dichotomie trouve donc la première trame
                # conforme sans construire chaque nombre intermédiaire.
                haute = evaluer_nombre(maximum_recherche)
                if haute.conforme:
                    basse_nombre = debut
                    haute_nombre = maximum_recherche
                    while basse_nombre < haute_nombre:
                        milieu = (basse_nombre + haute_nombre) // 2
                        if evaluer_nombre(milieu).conforme:
                            haute_nombre = milieu
                        else:
                            basse_nombre = milieu + 1
                    derniere = evaluer_nombre(basse_nombre)
                else:
                    derniere = haute

                candidates.append(derniere)
                if derniere.conforme:
                    meilleur_cout = min(meilleur_cout, derniere.cout_eur)
                if derniere.conforme and derniere.nombre_poutres == minimum:
                    break
                # Le nombre de poutres demandé par la portée secondaire ne peut
                # pas tenir dans le rectangle : les appuis longitudinaux n'y
                # changeront rien.
                if minimum > maximum_physique:
                    break

            conformes = [candidate for candidate in candidates if candidate.conforme]
            toutes_conformes.extend(conformes)
            if conformes:
                configurations.append(
                    min(
                        conformes,
                        key=lambda c: (
                            c.cout_eur,
                            c.nombre_lignes_appui_intermediaires,
                            c.masse_poutres_kg,
                        ),
                    )
                )
            elif candidates:
                configurations.append(
                    min(
                        candidates,
                        key=lambda c: (
                            c.taux_dimensionnant,
                            len(c.contraintes),
                            c.cout_eur,
                        ),
                    )
                )

    configurations.sort(
        key=lambda c: (
            not c.conforme,
            c.cout_eur if c.conforme else c.taux_dimensionnant,
            c.nombre_lignes_appui_intermediaires,
            c.masse_poutres_kg,
        )
    )
    meilleure = next((c for c in configurations if c.conforme), None)
    alternatives = sorted(
        toutes_conformes,
        key=lambda c: (c.cout_eur, c.nombre_pieux_total, c.taux_dimensionnant),
    )
    moins_de_pieux = (
        min(
            toutes_conformes,
            key=lambda c: (c.nombre_pieux_total, c.cout_eur, c.taux_dimensionnant),
        )
        if toutes_conformes
        else None
    )
    meilleure_marge = (
        min(
            toutes_conformes,
            key=lambda c: (c.taux_dimensionnant, c.cout_eur, c.nombre_pieux_total),
        )
        if toutes_conformes
        else None
    )
    details: dict[
        tuple[CatalogueSection, Orientation, int, int], ResultatConfiguration
    ] = {}

    def avec_pieux(configuration: ResultatConfiguration | None) -> ResultatConfiguration | None:
        if configuration is None:
            return None
        cle = (
            configuration.section,
            configuration.orientation,
            configuration.nombre_poutres,
            configuration.nombre_travees,
        )
        if cle not in details:
            details[cle] = evaluer_configuration(
                hypotheses,
                configuration.section,
                configuration.orientation,
                configuration.nombre_poutres,
                configuration.nombre_travees,
            )
        return details[cle]

    return ResultatOptimisation(
        hypotheses,
        tuple(avec_pieux(c) for c in configurations),
        avec_pieux(meilleure),
        avec_pieux(moins_de_pieux),
        avec_pieux(meilleure_marge),
        tuple(avec_pieux(c) for c in alternatives[:24]),
        tuple(alternatives),
    )
