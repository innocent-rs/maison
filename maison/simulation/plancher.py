"""Modèle éléments finis du plancher fini.

Le modèle linéaire 3D représente le châssis primaire et chaque segment de
STEICOjoist. Les couches non structurelles fournissent leur poids propre mais
ne sont pas utilisées pour rigidifier le modèle. Il s'agit d'un outil de
conception et de comparaison, pas d'une note de calcul d'exécution.
"""

from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from math import isclose

import openseespy.opensees as ops

from maison.structure import PlancherAFrame


class CasAssemblage(StrEnum):
    """Bornes de raideur de la liaison traverse–poutre de rive."""

    RIGIDE = "rigide_sans_entaille"
    ARTICULE = "sabots_sai_articules"


class CasCharge(StrEnum):
    """Cas de service non pondérés."""

    PERMANENTE = "G"
    EXPLOITATION = "Q"
    SERVICE = "G+Q"


@dataclass(frozen=True, slots=True)
class HypothesesSimulation:
    """Charges et masses modifiables sans toucher au modèle, en unités SI."""

    charge_exploitation_kN_m2: float = 1.5
    charge_permanente_rapportee_kN_m2: float = 0.0
    densite_osb_kg_m3: float = 600.0
    densite_isonat_kg_m3: float = 55.0
    densite_bois_massif_kg_m3: float = 500.0
    densite_membrures_solive_i_kg_m3: float = 480.0
    densite_ame_solive_i_kg_m3: float = 900.0
    gravite_m_s2: float = 9.81
    limite_fleche_diviseur: float = 300.0

    def __post_init__(self) -> None:
        if min(
            self.charge_exploitation_kN_m2,
            self.charge_permanente_rapportee_kN_m2,
            self.densite_osb_kg_m3,
            self.densite_isonat_kg_m3,
            self.densite_bois_massif_kg_m3,
            self.densite_membrures_solive_i_kg_m3,
            self.densite_ame_solive_i_kg_m3,
            self.gravite_m_s2,
        ) < 0:
            raise ValueError("les charges et masses ne peuvent pas être négatives")
        if self.limite_fleche_diviseur <= 0:
            raise ValueError("le diviseur de la limite de flèche doit être positif")


@dataclass(frozen=True, slots=True)
class ResultatSimulation:
    cas: CasAssemblage
    cas_charge: CasCharge
    charge_permanente_surfacique_kN_m2: float
    charge_exploitation_kN_m2: float
    poids_propre_structure_n: float
    charge_totale_n: float
    fleche_max_mm: float
    noeud_fleche_max: int
    fleche_relative_poutres_rive_max_mm: float
    limite_fleche_poutres_rive_mm: float
    taux_fleche_poutres_rive: float
    respecte_limite_fleche_poutres_rive: bool
    fleche_relative_traverses_max_mm: float
    limite_fleche_traverses_mm: float
    taux_fleche_traverses: float
    respecte_limite_fleche_traverses: bool
    fleche_relative_solives_i_max_mm: float
    limite_fleche_solives_i_mm: float
    taux_fleche_solives_i: float
    respecte_limite_fleche_solives_i: bool
    somme_reactions_z_n: float
    reaction_max_z_n: float
    nombre_noeuds: int
    nombre_elements: int
    nombre_elements_solives_i: int
    convergence: bool

    @property
    def charge_n(self) -> float:
        """Alias conservé pour les consommateurs de la première version."""
        return self.charge_totale_n


@dataclass(frozen=True, slots=True)
class MateriauBois:
    """Valeurs moyennes du bois massif, en N et mm."""

    module_young: float = 11_000.0
    module_cisaillement: float = 690.0


@dataclass(frozen=True, slots=True)
class _RigiditesSoliveI:
    ei_n_mm2: float
    ga_n: float


# Valeurs moyennes fabricant STEICOjoist SJ60, utilisées directement pour
# reproduire la souplesse de flexion et de cisaillement de la section composée.
_RIGIDITES_SJ60 = {
    240.0: _RigiditesSoliveI(ei_n_mm2=709e9, ga_n=3.18e6),
    300.0: _RigiditesSoliveI(ei_n_mm2=1_203e9, ga_n=4.18e6),
}


def _inerties_rectangle(largeur: float, hauteur: float) -> tuple[float, ...]:
    aire = largeur * hauteur
    iy = largeur * hauteur**3 / 12
    iz = hauteur * largeur**3 / 12
    petit_cote, grand_cote = sorted((largeur, hauteur))
    rapport = petit_cote / grand_cote
    torsion = petit_cote**3 * grand_cote * (
        1 / 3 - 0.21 * rapport * (1 - rapport**4 / 12)
    )
    return aire, iy, iz, torsion


def _section_solive_i(plancher: PlancherAFrame) -> tuple[float, ...]:
    largeur = plancher.largeur_membrure_solives_i
    hauteur = plancher.hauteur_solives_i
    hauteur_membrure = plancher.hauteur_membrure_solive_i
    epaisseur_ame = plancher.epaisseur_ame_solive_i
    hauteur_ame = hauteur - 2 * hauteur_membrure
    distance_membrure = hauteur / 2 - hauteur_membrure / 2

    aire = 2 * largeur * hauteur_membrure + epaisseur_ame * hauteur_ame
    iy = (
        2
        * (
            largeur * hauteur_membrure**3 / 12
            + largeur * hauteur_membrure * distance_membrure**2
        )
        + epaisseur_ame * hauteur_ame**3 / 12
    )
    iz = (
        2 * hauteur_membrure * largeur**3 / 12
        + hauteur_ame * epaisseur_ame**3 / 12
    )
    torsion = (
        2 * _inerties_rectangle(hauteur_membrure, largeur)[3]
        + _inerties_rectangle(epaisseur_ame, hauteur_ame)[3]
    )
    return aire, iy, iz, torsion


def charge_permanente_surfacique(
    plancher: PlancherAFrame,
    hypotheses: HypothesesSimulation = HypothesesSimulation(),
) -> float:
    """Poids des couches présentes, hors structure, en kN/m²."""
    plancher = getattr(plancher, "plancher", plancher)
    masse_kg_m2 = 0.0
    if plancher.inclure_osb_caissons:
        masse_kg_m2 += (
            hypotheses.densite_osb_kg_m3
            * plancher.epaisseur_osb_caissons
            / 1_000
        )
    if plancher.inclure_isolant_caissons:
        masse_kg_m2 += (
            hypotheses.densite_isonat_kg_m3
            * plancher.epaisseur_isolant_nominale
            / 1_000
        )
    if plancher.inclure_osb_plancher:
        masse_kg_m2 += (
            hypotheses.densite_osb_kg_m3
            * plancher.epaisseur_osb_plancher
            / 1_000
        )
    return (
        masse_kg_m2 * hypotheses.gravite_m_s2 / 1_000
        + hypotheses.charge_permanente_rapportee_kN_m2
    )


def _masse_lineique_solive_i(
    plancher: PlancherAFrame,
    hypotheses: HypothesesSimulation,
) -> float:
    """Masse estimée depuis les géométries et densités des constituants."""
    aire_membrures_m2 = (
        2
        * plancher.largeur_membrure_solives_i
        * plancher.hauteur_membrure_solive_i
        * 1e-6
    )
    hauteur_ame = (
        plancher.hauteur_solives_i - 2 * plancher.hauteur_membrure_solive_i
    )
    aire_ame_m2 = plancher.epaisseur_ame_solive_i * hauteur_ame * 1e-6
    return (
        aire_membrures_m2 * hypotheses.densite_membrures_solive_i_kg_m3
        + aire_ame_m2 * hypotheses.densite_ame_solive_i_kg_m3
    )


def _largeurs_tributaires(
    axes: tuple[float, ...], bord_bas: float, bord_haut: float
) -> dict[float, float]:
    limites = (
        bord_bas,
        *(sum(paire) / 2 for paire in pairwise(axes)),
        bord_haut,
    )
    return {
        axe: droite - gauche
        for axe, (gauche, droite) in zip(axes, pairwise(limites), strict=True)
    }


def simuler_plancher(
    plancher: PlancherAFrame,
    cas: CasAssemblage,
    charge_n: float = 0.0,
    materiau: MateriauBois = MateriauBois(),
    hypotheses: HypothesesSimulation = HypothesesSimulation(),
    cas_charge: CasCharge = CasCharge.SERVICE,
) -> ResultatSimulation:
    """Simule le plancher sous charges surfaciques de service non pondérées.

    ``G`` comprend les deux OSB, l'Isonat, une éventuelle charge rapportée et
    le poids propre des éléments porteurs. ``Q`` est la charge d'exploitation.
    ``charge_n`` ajoute facultativement une charge ponctuelle descendante au
    nœud de plancher le plus proche du centre.
    """
    plancher = getattr(plancher, "plancher", plancher)
    if charge_n < 0:
        raise ValueError("la charge ponctuelle ne peut pas être négative")
    if plancher.inclure_solives_i:
        if not isclose(plancher.largeur_membrure_solives_i, 60.0):
            raise ValueError("seules les STEICOjoist SJ60 sont calibrées")
        if plancher.hauteur_solives_i not in _RIGIDITES_SJ60:
            raise ValueError("cette hauteur de STEICOjoist SJ60 n'est pas calibrée")

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    longueur = plancher.geometrie.longueur_interieure
    largeur = plancher.geometrie.largeur_interieure
    demi_section = plancher.section_largeur / 2
    x_traverses = plancher.axes_traverses()
    y_rives = (-largeur / 2 + demi_section, largeur / 2 - demi_section)
    y_solives = plancher.axes_solives_i() if plancher.inclure_solives_i else ()
    y_porteurs = tuple(sorted((*y_rives, *y_solives)))
    z = plancher.section_hauteur / 2

    noeuds: dict[tuple[float, float], int] = {}
    coordonnees_noeuds: dict[int, tuple[float, float]] = {}
    prochain_noeud = 1

    def nouveau_noeud(x: float, y: float) -> int:
        nonlocal prochain_noeud
        tag = prochain_noeud
        ops.node(tag, x, y, z)
        coordonnees_noeuds[tag] = (x, y)
        prochain_noeud += 1
        return tag

    def noeud_primaire(x: float, y: float) -> int:
        cle = (round(x, 6), round(y, 6))
        if cle not in noeuds:
            noeuds[cle] = nouveau_noeud(x, y)
        return noeuds[cle]

    ops.geomTransf("Linear", 1, 0, 0, 1)
    prochain_element = 1
    elements_rive: dict[float, list[int]] = {y: [] for y in y_rives}
    elements_traverses: list[int] = []
    elements_solives: dict[float, list[int]] = {y: [] for y in y_solives}
    travees_solives: list[tuple[int, int, int]] = []

    section_massive = _inerties_rectangle(
        plancher.section_largeur, plancher.section_hauteur
    )

    def ajouter_element_massif(
        debut: int,
        fin: int,
        release_y: int | None = None,
    ) -> int:
        nonlocal prochain_element
        aire, iy, iz, torsion = section_massive
        arguments: list[object] = [
            "elasticBeamColumn",
            prochain_element,
            debut,
            fin,
            aire,
            materiau.module_young,
            materiau.module_cisaillement,
            torsion,
            iy,
            iz,
            1,
        ]
        if release_y is not None:
            arguments.extend(("-releasey", release_y))
        ops.element(*arguments)
        tag = prochain_element
        prochain_element += 1
        return tag

    # Les poutres de rive sont maillées aux traverses et à mi-travée afin de
    # relever la flèche entre appuis, y compris sur les petits porte-à-faux.
    x_rives = tuple(
        sorted(
            {
                0.0,
                longueur,
                *x_traverses,
                *(sum(paire) / 2 for paire in pairwise(x_traverses)),
            }
        )
    )
    for y in y_rives:
        for x_debut, x_fin in pairwise(x_rives):
            tag = ajouter_element_massif(
                noeud_primaire(x_debut, y), noeud_primaire(x_fin, y)
            )
            elements_rive[y].append(tag)

    # Les traverses sont continues sous les solives. Les relâchements ne sont
    # placés qu'à leurs deux liaisons avec les poutres de rive.
    for x in x_traverses:
        for index, (y_debut, y_fin) in enumerate(pairwise(y_porteurs)):
            release_y = None
            if cas == CasAssemblage.ARTICULE:
                if len(y_porteurs) == 2:
                    release_y = 3
                elif index == 0:
                    release_y = 1
                elif index == len(y_porteurs) - 2:
                    release_y = 2
            tag = ajouter_element_massif(
                noeud_primaire(x, y_debut),
                noeud_primaire(x, y_fin),
                release_y,
            )
            elements_traverses.append(tag)

    # Chaque segment de solive possède ses propres rotations d'about. Les cinq
    # autres ddl restent liés au nœud de traverse correspondant.
    if y_solives:
        aire_i, iy_i, iz_i, torsion_i = _section_solive_i(plancher)
        rigidites_i = _RIGIDITES_SJ60[plancher.hauteur_solives_i]
        module_i = rigidites_i.ei_n_mm2 / iy_i
        aire_cisaillement_z = rigidites_i.ga_n / materiau.module_cisaillement
        aire_cisaillement_y = aire_i

        for y in y_solives:
            for x_debut, x_fin in pairwise(x_traverses):
                maitre_debut = noeud_primaire(x_debut, y)
                maitre_fin = noeud_primaire(x_fin, y)
                debut = nouveau_noeud(x_debut, y)
                fin = nouveau_noeud(x_fin, y)
                milieu = nouveau_noeud((x_debut + x_fin) / 2, y)
                ops.equalDOF(maitre_debut, debut, 1, 2, 3, 4, 6)
                ops.equalDOF(maitre_fin, fin, 1, 2, 3, 4, 6)
                travees_solives.append((maitre_debut, milieu, maitre_fin))
                for noeud_debut, noeud_fin in ((debut, milieu), (milieu, fin)):
                    ops.element(
                        "ElasticTimoshenkoBeam",
                        prochain_element,
                        noeud_debut,
                        noeud_fin,
                        module_i,
                        materiau.module_cisaillement,
                        aire_i,
                        torsion_i,
                        iy_i,
                        iz_i,
                        aire_cisaillement_y,
                        aire_cisaillement_z,
                        1,
                    )
                    elements_solives[y].append(prochain_element)
                    prochain_element += 1

    # Quatre appuis verticaux. Trois blocages horizontaux retirent les modes de
    # corps rigide sans encastrer les rotations.
    appuis = [
        noeud_primaire(x, y)
        for x in (x_traverses[0], x_traverses[-1])
        for y in y_rives
    ]
    ops.fix(appuis[0], 1, 1, 1, 0, 0, 0)
    ops.fix(appuis[1], 1, 0, 1, 0, 0, 0)
    for tag in appuis[2:]:
        ops.fix(tag, 0, 0, 1, 0, 0, 0)

    charge_g = charge_permanente_surfacique(plancher, hypotheses)
    charge_q = hypotheses.charge_exploitation_kN_m2
    charge_surface = {
        CasCharge.PERMANENTE: charge_g,
        CasCharge.EXPLOITATION: charge_q,
        CasCharge.SERVICE: charge_g + charge_q,
    }[cas_charge]
    inclure_structure = cas_charge in (CasCharge.PERMANENTE, CasCharge.SERVICE)

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)

    # 1 kN/m² = 0,001 N/mm². Chaque ligne porte sa largeur tributaire ; pour
    # les solives, la charge des bandes d'extrémité est ramenée sur la portée
    # entre axes afin de conserver exactement la charge surfacique totale.
    tributaires = _largeurs_tributaires(y_porteurs, -largeur / 2, largeur / 2)
    for y, tags in elements_rive.items():
        w_n_mm = charge_surface * 0.001 * tributaires[y]
        for tag in tags:
            ops.eleLoad("-ele", tag, "-type", "-beamUniform", 0.0, -w_n_mm, 0.0)
    longueur_modele_solives = x_traverses[-1] - x_traverses[0]
    for y, tags in elements_solives.items():
        w_n_mm = (
            charge_surface
            * 0.001
            * tributaires[y]
            * longueur
            / longueur_modele_solives
        )
        for tag in tags:
            ops.eleLoad("-ele", tag, "-type", "-beamUniform", 0.0, -w_n_mm, 0.0)

    poids_propre_structure = 0.0
    if inclure_structure:
        aire_massive_m2 = plancher.section_largeur * plancher.section_hauteur * 1e-6
        poids_lineique_massif_n_mm = (
            aire_massive_m2
            * hypotheses.densite_bois_massif_kg_m3
            * hypotheses.gravite_m_s2
            / 1_000
        )
        for tags in elements_rive.values():
            for tag in tags:
                ops.eleLoad(
                    "-ele", tag, "-type", "-beamUniform", 0.0,
                    -poids_lineique_massif_n_mm, 0.0,
                )
        poids_propre_structure += 2 * longueur * poids_lineique_massif_n_mm

        longueur_modele_traverse = y_rives[1] - y_rives[0]
        facteur_traverse = plancher.longueur_traverses / longueur_modele_traverse
        for tag in elements_traverses:
            ops.eleLoad(
                "-ele", tag, "-type", "-beamUniform", 0.0,
                -poids_lineique_massif_n_mm * facteur_traverse, 0.0,
            )
        poids_propre_structure += (
            plancher.nombre_traverses
            * plancher.longueur_traverses
            * poids_lineique_massif_n_mm
        )

        if elements_solives:
            poids_lineique_i_n_mm = (
                _masse_lineique_solive_i(plancher, hypotheses)
                * hypotheses.gravite_m_s2
                / 1_000
            )
            facteur_solive = plancher.longueur_solives_i / plancher.entraxe_traverses
            for tags in elements_solives.values():
                for tag in tags:
                    ops.eleLoad(
                        "-ele", tag, "-type", "-beamUniform", 0.0,
                        -poids_lineique_i_n_mm * facteur_solive, 0.0,
                    )
            poids_propre_structure += (
                plancher.nombre_solives_i
                * plancher.longueur_solives_i
                * poids_lineique_i_n_mm
            )

    if charge_n:
        centre_x, centre_y = longueur / 2, 0.0
        noeud_charge = min(
            coordonnees_noeuds,
            key=lambda tag: (
                (coordonnees_noeuds[tag][0] - centre_x) ** 2
                + (coordonnees_noeuds[tag][1] - centre_y) ** 2
            ),
        )
        ops.load(noeud_charge, 0, 0, -charge_n, 0, 0, 0)

    ops.system("UmfPack")
    ops.numberer("RCM")
    ops.constraints("Transformation")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    convergence = ops.analyze(1) == 0
    if not convergence:
        raise RuntimeError(f"la simulation du cas {cas.value} n'a pas convergé")

    deplacements = {tag: ops.nodeDisp(tag, 3) for tag in coordonnees_noeuds}
    noeud_max = min(deplacements, key=deplacements.get)
    fleches_rive: list[float] = []
    x_appui_debut, x_appui_fin = x_traverses[0], x_traverses[-1]
    for y in y_rives:
        deplacement_debut = deplacements[noeud_primaire(x_appui_debut, y)]
        deplacement_fin = deplacements[noeud_primaire(x_appui_fin, y)]
        for x in x_rives:
            if x_appui_debut <= x <= x_appui_fin:
                position = (x - x_appui_debut) / (x_appui_fin - x_appui_debut)
                corde = deplacement_debut + position * (
                    deplacement_fin - deplacement_debut
                )
                fleches_rive.append(abs(deplacements[noeud_primaire(x, y)] - corde))
    fleche_rive = max(fleches_rive, default=0.0)
    portee_rive = x_appui_fin - x_appui_debut
    limite_rive = portee_rive / hypotheses.limite_fleche_diviseur
    taux_fleche_rive = fleche_rive / limite_rive
    fleches_traverses: list[float] = []
    for x in x_traverses:
        deplacement_gauche = deplacements[noeud_primaire(x, y_rives[0])]
        deplacement_droit = deplacements[noeud_primaire(x, y_rives[1])]
        for y in y_porteurs:
            position = (y - y_rives[0]) / (y_rives[1] - y_rives[0])
            corde = deplacement_gauche + position * (
                deplacement_droit - deplacement_gauche
            )
            fleches_traverses.append(
                abs(deplacements[noeud_primaire(x, y)] - corde)
            )
    fleche_traverses = max(fleches_traverses, default=0.0)
    limite_traverses = (
        plancher.longueur_traverses / hypotheses.limite_fleche_diviseur
    )
    taux_fleche_traverses = fleche_traverses / limite_traverses
    fleches_relatives = [
        abs(deplacements[milieu] - (deplacements[debut] + deplacements[fin]) / 2)
        for debut, milieu, fin in travees_solives
    ]
    fleche_solives = max(fleches_relatives, default=0.0)
    limite_solives = (
        plancher.longueur_solives_i / hypotheses.limite_fleche_diviseur
        if travees_solives
        else 0.0
    )
    taux_fleche = fleche_solives / limite_solives if limite_solives else 0.0

    ops.reactions()
    reactions = [ops.nodeReaction(tag, 3) for tag in appuis]
    somme_reactions = sum(reactions)
    charge_totale = (
        charge_surface * plancher.geometrie.surface_plancher * 1_000
        + poids_propre_structure
        + charge_n
    )
    if not isclose(somme_reactions, charge_totale, rel_tol=1e-7, abs_tol=1e-4):
        raise RuntimeError(
            "les réactions ne sont pas en équilibre avec les charges "
            f"({somme_reactions:.6f} N contre {charge_totale:.6f} N)"
        )

    return ResultatSimulation(
        cas=cas,
        cas_charge=cas_charge,
        charge_permanente_surfacique_kN_m2=charge_g,
        charge_exploitation_kN_m2=charge_q,
        poids_propre_structure_n=poids_propre_structure,
        charge_totale_n=charge_totale,
        fleche_max_mm=abs(deplacements[noeud_max]),
        noeud_fleche_max=noeud_max,
        fleche_relative_poutres_rive_max_mm=fleche_rive,
        limite_fleche_poutres_rive_mm=limite_rive,
        taux_fleche_poutres_rive=taux_fleche_rive,
        respecte_limite_fleche_poutres_rive=taux_fleche_rive <= 1.0,
        fleche_relative_traverses_max_mm=fleche_traverses,
        limite_fleche_traverses_mm=limite_traverses,
        taux_fleche_traverses=taux_fleche_traverses,
        respecte_limite_fleche_traverses=taux_fleche_traverses <= 1.0,
        fleche_relative_solives_i_max_mm=fleche_solives,
        limite_fleche_solives_i_mm=limite_solives,
        taux_fleche_solives_i=taux_fleche,
        respecte_limite_fleche_solives_i=taux_fleche <= 1.0,
        somme_reactions_z_n=somme_reactions,
        reaction_max_z_n=max(reactions),
        nombre_noeuds=len(coordonnees_noeuds),
        nombre_elements=prochain_element - 1,
        nombre_elements_solives_i=sum(map(len, elements_solives.values())),
        convergence=convergence,
    )
