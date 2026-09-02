"""Pré-dimensionnement et optimisation de poutres principales en bois.

Le modèle est volontairement simple : poutres principales rectangulaires,
parallèles et isostatiques, avec une poutre sur chacune des deux rives. La
charge du complexe secondaire (futures solives en I et plancher) est ramenée
à une charge linéique uniforme par largeur tributaire. Les unités internes
sont N, mm et MPa.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite
from typing import Literal


Orientation = Literal["longueur", "largeur"]

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

    def __post_init__(self) -> None:
        valeurs = (
            self.largeur_mm,
            self.hauteur_mm,
            self.prix_eur_m,
            self.longueur_max_m,
        )
        if not self.nom.strip():
            raise ValueError("chaque section doit avoir un nom")
        if not all(isfinite(v) for v in valeurs) or min(valeurs) <= 0:
            raise ValueError(f"les valeurs de la section {self.nom} doivent être positives")

    @property
    def aire_mm2(self) -> float:
        return self.largeur_mm * self.hauteur_mm

    @property
    def inertie_mm4(self) -> float:
        return self.largeur_mm * self.hauteur_mm**3 / 12

    @property
    def module_section_mm3(self) -> float:
        return self.largeur_mm * self.hauteur_mm**2 / 6


SECTIONS_FOURNISSEUR = (
    CatalogueSection("140 × 140", 140, 140, 26.64, 13),
    CatalogueSection("100 × 200", 100, 200, 29.02, 13),
    CatalogueSection("160 × 160", 160, 160, 32.45, 12),
    CatalogueSection("120 × 240", 120, 240, 40.01, 13),
    CatalogueSection("200 × 200", 200, 200, 55.98, 13),
)


@dataclass(frozen=True, slots=True)
class HypothesesProjet:
    longueur_m: float = 10.0
    largeur_m: float = 10.0
    masse_permanente_kg_m2: float = 75.0
    masse_exploitation_kg_m2: float = 150.0
    masse_ajoutee_totale_kg: float = 0.0
    masse_volumique_kg_m3: float = 500.0
    # 0 laisse l'optimisation structurelle libre. Une valeur positive représente
    # la portée maximale provisoirement admise pour le futur système secondaire.
    entraxe_max_m: float = 4.0
    limite_fleche_diviseur: float = 300.0
    e_moyen_mpa: float = 11_000.0
    g_moyen_mpa: float = 690.0
    fm_k_mpa: float = 24.0
    fv_k_mpa: float = 4.0
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
class ResultatConfiguration:
    section: CatalogueSection
    orientation: Orientation
    portee_m: float
    portee_totale_m: float
    largeur_repartie_m: float
    nombre_poutres: int
    nombre_travees: int
    nombre_lignes_appui_intermediaires: int
    nombre_appuis_ponctuels: int
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
    reaction_appui_intermediaire_elu_kN: float
    capacite_appui_kN: float
    taux_appui: float
    conforme: bool
    contraintes: tuple[str, ...]

    @property
    def taux_dimensionnant(self) -> float:
        return max(
            self.taux_fleche,
            self.taux_flexion,
            self.taux_cisaillement,
            self.taux_appui,
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
        return "Pieu vissé ELU"


@dataclass(frozen=True, slots=True)
class ResultatOptimisation:
    hypotheses: HypothesesProjet
    configurations: tuple[ResultatConfiguration, ...]
    meilleure: ResultatConfiguration | None


def _fleche_uniforme_mm(
    charge_kN_m: float,
    portee_mm: float,
    section: CatalogueSection,
    hypotheses: HypothesesProjet,
) -> float:
    # 1 kN/m = 1 N/mm. Flexion d'Euler-Bernoulli + cisaillement de Timoshenko.
    flexion = (
        5
        * charge_kN_m
        * portee_mm**4
        / (384 * hypotheses.e_moyen_mpa * section.inertie_mm4)
    )
    cisaillement = (
        charge_kN_m
        * portee_mm**2
        / (
            8
            * hypotheses.coefficient_cisaillement
            * hypotheses.g_moyen_mpa
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
    poids_propre_kN_m = 0.0
    if hypotheses.inclure_poids_propre:
        poids_propre_kN_m = (
            section.aire_mm2 / 1_000_000
            * hypotheses.masse_volumique_kg_m3
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
    resistance_flexion = hypotheses.kmod * hypotheses.fm_k_mpa / hypotheses.gamma_m
    resistance_cisaillement = hypotheses.kmod * hypotheses.fv_k_mpa / hypotheses.gamma_m
    taux_flexion = contrainte_flexion / resistance_flexion
    taux_cisaillement = contrainte_cisaillement / resistance_cisaillement
    nombre_lignes_appui_intermediaires = nombre_travees - 1
    # Deux travées simplement appuyées aboutissent sur chaque pieu intérieur :
    # R = qL/2 + qL/2. Sans ligne intermédiaire, aucun pieu n'est chiffré ici.
    reaction_appui_intermediaire = (
        charge_elu * portee_m if nombre_lignes_appui_intermediaires else 0.0
    )
    capacite_appui_kN = CAPACITE_PIEU_VISSE_TONNES * 9.81
    taux_appui = reaction_appui_intermediaire / capacite_appui_kN

    contraintes: list[str] = []
    if portee_m > section.longueur_max_m:
        contraintes.append("portée supérieure à la longueur commerciale")
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

    longueur_totale = nombre_poutres * portee_totale_m
    masse_poutres = (
        longueur_totale
        * section.aire_mm2
        / 1_000_000
        * hypotheses.masse_volumique_kg_m3
    )
    nombre_appuis_ponctuels = nombre_poutres * nombre_lignes_appui_intermediaires
    cout_bois = longueur_totale * section.prix_eur_m
    cout_appuis = nombre_appuis_ponctuels * COUT_PIEU_VISSE_EUR
    return ResultatConfiguration(
        section=section,
        orientation=orientation,
        portee_m=portee_m,
        portee_totale_m=portee_totale_m,
        largeur_repartie_m=largeur_repartie_m,
        nombre_poutres=nombre_poutres,
        nombre_travees=nombre_travees,
        nombre_lignes_appui_intermediaires=nombre_lignes_appui_intermediaires,
        nombre_appuis_ponctuels=nombre_appuis_ponctuels,
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
        reaction_appui_intermediaire_elu_kN=reaction_appui_intermediaire,
        capacite_appui_kN=capacite_appui_kN,
        taux_appui=taux_appui,
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
) -> ResultatOptimisation:
    if not sections:
        raise ValueError("sélectionnez au moins une section")
    orientations: tuple[Orientation, ...]
    if hypotheses.orientation == "auto":
        orientations = ("longueur", "largeur")
    else:
        orientations = (hypotheses.orientation,)

    configurations: list[ResultatConfiguration] = []
    for orientation in orientations:
        for section in sections:
            candidates: list[ResultatConfiguration] = []
            minimum = _minimum_geometrique(hypotheses, orientation)
            maximum_physique = _maximum_sans_chevauchement(
                hypotheses, section, orientation
            )
            for nombre_travees in range(1, MAX_TRAVEES_RECHERCHE + 1):
                derniere: ResultatConfiguration | None = None
                # Si la contrainte secondaire exige déjà des poutres qui se
                # chevauchent, on garde la dernière trame physique pour le diagnostic.
                debut = (
                    minimum
                    if minimum <= maximum_physique
                    else max(2, maximum_physique)
                )
                maximum_recherche = max(2, maximum_physique)
                for nombre in range(debut, maximum_recherche + 1):
                    derniere = evaluer_configuration(
                        hypotheses,
                        section,
                        orientation,
                        nombre,
                        nombre_travees,
                    )
                    if derniere.conforme:
                        candidates.append(derniere)
                        # Cette section utilise désormais le nombre minimal de
                        # poutres permis par la géométrie secondaire. Des travées
                        # plus courtes ne réduiraient plus le bois, mais ajouteraient
                        # nécessairement une rangée de pieux à 500 € par poutre.
                        if nombre == minimum:
                            break
                        break
                else:
                    if derniere is not None:
                        candidates.append(derniere)

                if derniere is not None and derniere.conforme and derniere.nombre_poutres == minimum:
                    break
                # Le nombre de poutres demandé par la portée secondaire ne peut
                # pas tenir dans le rectangle : les appuis longitudinaux n'y
                # changeront rien.
                if minimum > maximum_physique:
                    break

            conformes = [candidate for candidate in candidates if candidate.conforme]
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
    return ResultatOptimisation(hypotheses, tuple(configurations), meilleure)
