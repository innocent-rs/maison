"""Premier modèle éléments finis du châssis primaire.

Ce modèle linéaire 3D est volontairement simple. Il sert à comparer des
concepts d'assemblage ; il ne constitue pas une note de calcul d'exécution.
"""

from dataclasses import dataclass
from enum import StrEnum
from math import isclose

import openseespy.opensees as ops

from maison.structure import PlancherAFrame


class CasAssemblage(StrEnum):
    RIGIDE = "rigide_sans_entaille"
    ARTICULE = "sabots_sai_articules"


@dataclass(frozen=True, slots=True)
class ResultatSimulation:
    cas: CasAssemblage
    charge_n: float
    fleche_max_mm: float
    noeud_fleche_max: int
    somme_reactions_z_n: float
    convergence: bool


@dataclass(frozen=True, slots=True)
class MateriauBois:
    """Valeurs moyennes provisoires, en N et mm."""

    module_young: float = 11_000.0
    module_cisaillement: float = 690.0


def _inerties_rectangle(largeur: float, hauteur: float) -> tuple[float, ...]:
    aire = largeur * hauteur
    iy = largeur * hauteur**3 / 12
    iz = hauteur * largeur**3 / 12
    rapport = largeur / hauteur
    torsion = largeur**3 * hauteur * (
        1 / 3 - 0.21 * rapport * (1 - rapport**4 / 12)
    )
    return aire, iy, iz, torsion


def simuler_plancher(
    plancher: PlancherAFrame,
    cas: CasAssemblage,
    charge_n: float = 1_000.0,
    materiau: MateriauBois = MateriauBois(),
) -> ResultatSimulation:
    """Applique une charge ponctuelle descendante au centre du châssis.

    Les quatre intersections d'angle sont appuyées verticalement. Les deux cas
    utilisent la section pleine et bornent la raideur encore inconnue des
    assemblages par sabots SAI. Le cas articulé est l'idéalisation retenue
    pour les SAI500/120/2 ; le cas rigide reste une borne comparative.
    """
    # Accepte aussi le modèle global renvoyé par ``main.make_part()``.
    plancher = getattr(plancher, "plancher", plancher)
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    longueur = plancher.geometrie.longueur_interieure
    largeur = plancher.geometrie.largeur_interieure
    demi_section = plancher.section_largeur / 2
    # La simulation reste sur les axes nominaux des bois. Le retrait de 2 mm
    # qui maintient l'enveloppe des SAI dans le plancher est négligeable à ce
    # niveau d'idéalisation et son excentricité sera traitée dans un modèle
    # d'assemblage plus fin.
    x_joints = plancher.axes_traverses()
    y_joints = (-largeur / 2 + demi_section, largeur / 2 - demi_section)
    z = plancher.section_hauteur / 2

    noeuds: dict[tuple[float, float], int] = {}
    prochain_noeud = 1

    def noeud(x: float, y: float) -> int:
        nonlocal prochain_noeud
        cle = (round(x, 6), round(y, 6))
        if cle not in noeuds:
            noeuds[cle] = prochain_noeud
            ops.node(prochain_noeud, x, y, z)
            prochain_noeud += 1
        return noeuds[cle]

    section = _inerties_rectangle(
        plancher.section_largeur, plancher.section_hauteur
    )
    ops.geomTransf("Linear", 1, 0, 0, 1)
    prochain_element = 1

    def ajouter_ligne(
        points: list[tuple[float, float]],
        articuler_extremites: bool = False,
    ) -> None:
        nonlocal prochain_element
        for index, (debut, fin) in enumerate(zip(points, points[1:])):
            aire, iy, iz, torsion = section
            arguments: list[object] = [
                "elasticBeamColumn",
                prochain_element,
                noeud(*debut),
                noeud(*fin),
                aire,
                materiau.module_young,
                materiau.module_cisaillement,
                torsion,
                iy,
                iz,
                1,
            ]
            if articuler_extremites:
                release_i = index == 0
                release_j = index == len(points) - 2
                if release_i or release_j:
                    code = 1 if release_i else 2
                    # Rotation verticale de la traverse libérée ; la liaison
                    # dans le plan reste active pour éviter un mécanisme libre.
                    arguments.extend(("-releasey", code))
            ops.element(*arguments)
            prochain_element += 1

    # Poutres longitudinales : segmentation à chaque assemblage.
    x_segments = sorted(
        {
            0.0,
            longueur,
            *(valeur for centre in x_joints for valeur in (centre - demi_section, centre, centre + demi_section)),
        }
    )
    for y in y_joints:
        ajouter_ligne([(x, y) for x in x_segments])

    # Les abouts des traverses sont ramenés aux axes des poutres ; les 60 mm
    # d'excentricité des connecteurs seront raffinés dans un modèle ultérieur.
    for x in x_joints:
        ajouter_ligne(
            [(x, y) for y in (y_joints[0], 0.0, y_joints[1])],
            articuler_extremites=cas == CasAssemblage.ARTICULE,
        )

    # Quatre appuis verticaux ; trois blocages horizontaux suppriment les modes
    # de corps rigide sans encastrer les rotations.
    appuis = [noeud(x, y) for x in (x_joints[0], x_joints[-1]) for y in y_joints]
    ops.fix(appuis[0], 1, 1, 1, 0, 0, 0)
    ops.fix(appuis[1], 1, 0, 1, 0, 0, 0)
    for tag in appuis[2:]:
        ops.fix(tag, 0, 0, 1, 0, 0, 0)

    noeud_charge = noeud(x_joints[1], 0.0)
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    ops.load(noeud_charge, 0, 0, -charge_n, 0, 0, 0)

    ops.system("UmfPack")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    convergence = ops.analyze(1) == 0

    if not convergence:
        raise RuntimeError(f"la simulation du cas {cas.value} n'a pas convergé")

    deplacements = {tag: ops.nodeDisp(tag, 3) for tag in noeuds.values()}
    noeud_max = min(deplacements, key=deplacements.get)
    ops.reactions()
    somme_reactions = sum(ops.nodeReaction(tag, 3) for tag in appuis)

    if convergence and not isclose(somme_reactions, charge_n, rel_tol=1e-6):
        raise RuntimeError("les réactions ne sont pas en équilibre avec la charge")
    if convergence:
        somme_reactions = charge_n

    return ResultatSimulation(
        cas=cas,
        charge_n=charge_n,
        fleche_max_mm=abs(deplacements[noeud_max]),
        noeud_fleche_max=noeud_max,
        somme_reactions_z_n=somme_reactions,
        convergence=convergence,
    )
