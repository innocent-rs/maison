"""POC CalculiX du plancher du local batteries.

La géométrie (axes, sections et portées) est lue sur le même ``PlancherBois``
que la CAO, la BOM, la cutlist et le manuel. Les valeurs mécaniques et les
conditions aux limites restent des hypothèses de calcul séparées et visibles.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from home_framework.simulation import (
    AppuiCalculix,
    ChargeNodaleCalculix,
    ElementPoutreCalculix,
    ModeleCalculix,
    NoeudCalculix,
    SectionPoutreCalculix,
    ZoneCharge,
    executer_calculix,
    generer_images_deplacement,
    lire_resultats_dat,
)

from .modele import LocalBatteries, creer_local_batteries


_EI_SJ60_240_N_MM2 = 709e9
_GA_SJ60_240_N = 3.18e6


@dataclass(frozen=True, slots=True)
class HypothesesCalculixLocal:
    """Hypothèses du POC statique linéaire, en N et mm."""

    masse_batteries_kg: float = 1_000.0
    empreinte_longueur_mm: float = 1_000.0
    empreinte_largeur_mm: float = 1_000.0
    centre_x_mm: float = 1_500.0
    centre_y_mm: float = 0.0
    gravite_m_s2: float = 9.81
    module_bois_massif_mpa: float = 11_000.0
    densite_bois_massif_kg_m3: float = 500.0
    densite_membrures_i_kg_m3: float = 480.0
    densite_ame_i_kg_m3: float = 900.0
    densite_osb_kg_m3: float = 600.0
    densite_isolant_kg_m3: float = 55.0

    def __post_init__(self) -> None:
        if min(
            self.masse_batteries_kg,
            self.empreinte_longueur_mm,
            self.empreinte_largeur_mm,
            self.gravite_m_s2,
            self.module_bois_massif_mpa,
            self.densite_bois_massif_kg_m3,
            self.densite_membrures_i_kg_m3,
            self.densite_ame_i_kg_m3,
            self.densite_osb_kg_m3,
            self.densite_isolant_kg_m3,
        ) <= 0:
            raise ValueError("les charges, dimensions et propriétés doivent être positives")


def _limites_tributaires(
    axes: tuple[float, ...], minimum: float, maximum: float
) -> dict[float, tuple[float, float]]:
    limites = (minimum, *(sum(paire) / 2 for paire in pairwise(axes)), maximum)
    return {
        axe: intervalle
        for axe, intervalle in zip(axes, pairwise(limites), strict=True)
    }


def _intersection(
    debut_a: float, fin_a: float, debut_b: float, fin_b: float
) -> float:
    return max(0.0, min(fin_a, fin_b) - max(debut_a, debut_b))


def _masse_couches_kg(
    local: LocalBatteries, hypotheses: HypothesesCalculixLocal
) -> float:
    """Masse des OSB et de l'isolant du plancher, hors murs."""
    plancher = local.plancher
    aire_mm2 = plancher.geometrie.surface_plancher * 1e6
    volume_osb_haut_mm3 = aire_mm2 * 22.0
    nombre_caissons = (
        (plancher.nombre_lignes_solives_i + 1)
        * (plancher.nombre_traverses - 1)
    )
    largeur_caisson = plancher.largeur_caisson_isolant
    longueur_caisson = plancher.entraxe_traverses - plancher.section_largeur
    volume_fonds_mm3 = (
        nombre_caissons
        * longueur_caisson
        * (largeur_caisson - plancher.jeu_joint_osb)
        * plancher.epaisseur_osb_caissons
    )
    volume_isolant_mm3 = (
        nombre_caissons
        * longueur_caisson
        * largeur_caisson
        * plancher.epaisseur_isolant_nominale
    )
    return (
        (volume_osb_haut_mm3 + volume_fonds_mm3)
        * 1e-9
        * hypotheses.densite_osb_kg_m3
        + volume_isolant_mm3
        * 1e-9
        * hypotheses.densite_isolant_kg_m3
    )


def generer_modele_calculix(
    local: LocalBatteries,
    hypotheses: HypothesesCalculixLocal | None = None,
) -> ModeleCalculix:
    """Transforme déclarativement le plancher local en ossature CalculiX."""
    hypotheses = hypotheses or HypothesesCalculixLocal(
        masse_batteries_kg=local.charge_batteries_kg
    )
    plancher = local.plancher
    longueur = plancher.geometrie.longueur_interieure
    largeur = plancher.geometrie.largeur_interieure
    demi_empreinte_x = hypotheses.empreinte_longueur_mm / 2
    demi_empreinte_y = hypotheses.empreinte_largeur_mm / 2
    if not (
        0 <= hypotheses.centre_x_mm - demi_empreinte_x
        and hypotheses.centre_x_mm + demi_empreinte_x <= longueur
        and -largeur / 2 <= hypotheses.centre_y_mm - demi_empreinte_y
        and hypotheses.centre_y_mm + demi_empreinte_y <= largeur / 2
    ):
        raise ValueError("l'empreinte batteries doit rester entièrement sur le plancher")

    axes_x = plancher.axes_traverses()
    axes_x_charge = tuple(
        sorted({*axes_x, *(sum(paire) / 2 for paire in pairwise(axes_x))})
    )
    y_rives = (
        -largeur / 2 + plancher.section_largeur / 2,
        largeur / 2 - plancher.section_largeur / 2,
    )
    y_solives = plancher.axes_solives_i()
    axes_y_charge = tuple(sorted((*y_rives, *y_solives)))
    z = plancher.section_hauteur / 2

    noeuds: list[NoeudCalculix] = []
    noeuds_primaires: dict[tuple[float, float], int] = {}

    def nouveau_noeud(x: float, y: float) -> int:
        identifiant = len(noeuds) + 1
        noeuds.append(NoeudCalculix(identifiant, x, y, z))
        return identifiant

    def noeud_primaire(x: float, y: float) -> int:
        cle = (round(x, 6), round(y, 6))
        if cle not in noeuds_primaires:
            noeuds_primaires[cle] = nouveau_noeud(x, y)
        return noeuds_primaires[cle]

    # Tous les points de reprise surfacique sont créés dans un ordre stable.
    for x in axes_x_charge:
        for y in axes_y_charge:
            noeud_primaire(x, y)

    aire_i_mm2 = (
        2
        * plancher.largeur_membrure_solive_i
        * plancher.hauteur_membrure_solive_i
        + plancher.epaisseur_ame_solive_i
        * (
            plancher.hauteur_solives_i
            - 2 * plancher.hauteur_membrure_solive_i
        )
    )
    largeur_i_equivalente = aire_i_mm2 / plancher.hauteur_solives_i
    inertie_i_equivalente = (
        largeur_i_equivalente * plancher.hauteur_solives_i**3 / 12
    )
    module_i_longitudinal = _EI_SJ60_240_N_MM2 / inertie_i_equivalente
    module_i_cisaillement = _GA_SJ60_240_N / aire_i_mm2
    sections = (
        SectionPoutreCalculix(
            "BOIS_MASSIF_120X240",
            plancher.section_hauteur,
            plancher.section_largeur,
            hypotheses.module_bois_massif_mpa,
        ),
        SectionPoutreCalculix(
            "SJ60_240_EQUIVALENTE",
            plancher.hauteur_solives_i,
            largeur_i_equivalente,
            module_i_longitudinal,
            constantes_ingenierie=(
                module_i_longitudinal,
                1_000.0,
                1_000.0,
                0.2,
                0.2,
                0.2,
                module_i_cisaillement,
                module_i_cisaillement,
                300.0,
            ),
        ),
    )
    elements: list[ElementPoutreCalculix] = []

    def ajouter_element(debut: int, fin: int, section: str) -> None:
        elements.append(
            ElementPoutreCalculix(len(elements) + 1, debut, fin, section)
        )

    # Rives continues, avec les extrémités de la géométrie CAO.
    axes_x_rives = tuple(sorted({0.0, longueur, *axes_x_charge}))
    for y in y_rives:
        for x_debut, x_fin in pairwise(axes_x_rives):
            ajouter_element(
                noeud_primaire(x_debut, y),
                noeud_primaire(x_fin, y),
                "BOIS_MASSIF_120X240",
            )

    # Première borne volontairement rigide : les traverses partagent leurs
    # nœuds avec les rives. La portée axe-à-axe est conservative par rapport à
    # la longueur de coupe; la masse est corrigée plus bas à la longueur CAO.
    for x in axes_x:
        ligne = tuple(noeud_primaire(x, y) for y in axes_y_charge)
        for noeud_debut, noeud_fin in pairwise(ligne):
            ajouter_element(
                noeud_debut, noeud_fin, "BOIS_MASSIF_120X240"
            )

    # Les SJ60/240 partagent également les nœuds de traverse dans cette borne
    # rigide. Leur masse est ramenée à la longueur de coupe physique.
    for y in y_solives:
        for x_gauche, x_droit in pairwise(axes_x):
            milieu = noeud_primaire((x_gauche + x_droit) / 2, y)
            ajouter_element(
                noeud_primaire(x_gauche, y),
                milieu,
                "SJ60_240_EQUIVALENTE",
            )
            ajouter_element(
                milieu,
                noeud_primaire(x_droit, y),
                "SJ60_240_EQUIVALENTE",
            )

    appuis_noeuds = tuple(
        noeud_primaire(x, y)
        for x in (axes_x[0], axes_x[-1])
        for y in y_rives
    )
    appuis = (
        AppuiCalculix(appuis_noeuds[0], 1, 3),
        AppuiCalculix(appuis_noeuds[1], 2, 3),
        AppuiCalculix(appuis_noeuds[2], 3, 3),
        AppuiCalculix(appuis_noeuds[3], 3, 3),
    )

    charges_par_noeud: defaultdict[int, float] = defaultdict(float)
    masse_couches_kg = _masse_couches_kg(local, hypotheses)
    aire_plancher_mm2 = longueur * largeur
    pression_couches_n_mm2 = (
        masse_couches_kg * hypotheses.gravite_m_s2 / aire_plancher_mm2
    )
    x_empreinte = (
        hypotheses.centre_x_mm - hypotheses.empreinte_longueur_mm / 2,
        hypotheses.centre_x_mm + hypotheses.empreinte_longueur_mm / 2,
    )
    y_empreinte = (
        hypotheses.centre_y_mm - hypotheses.empreinte_largeur_mm / 2,
        hypotheses.centre_y_mm + hypotheses.empreinte_largeur_mm / 2,
    )
    aire_empreinte = (
        hypotheses.empreinte_longueur_mm * hypotheses.empreinte_largeur_mm
    )
    pression_batteries_n_mm2 = (
        hypotheses.masse_batteries_kg * hypotheses.gravite_m_s2 / aire_empreinte
    )
    cellules_x = _limites_tributaires(axes_x_charge, 0.0, longueur)
    cellules_y = _limites_tributaires(
        axes_y_charge, -largeur / 2, largeur / 2
    )
    for x in axes_x_charge:
        x_debut, x_fin = cellules_x[x]
        for y in axes_y_charge:
            y_debut, y_fin = cellules_y[y]
            aire_cellule = (x_fin - x_debut) * (y_fin - y_debut)
            charge = pression_couches_n_mm2 * aire_cellule
            aire_chargee = _intersection(
                *cellules_x[x], *x_empreinte
            ) * _intersection(
                *cellules_y[y], *y_empreinte
            )
            charge += pression_batteries_n_mm2 * aire_chargee
            charges_par_noeud[noeud_primaire(x, y)] -= charge

    # Poids propre des poutres, transformé en charges nodales consistantes.
    aire_massif_m2 = (
        plancher.section_largeur * plancher.section_hauteur * 1e-6
    )
    poids_lineique_massif_n_mm = (
        aire_massif_m2
        * hypotheses.densite_bois_massif_kg_m3
        * hypotheses.gravite_m_s2
        / 1_000
    )
    aire_membrures_m2 = (
        2
        * plancher.largeur_membrure_solive_i
        * plancher.hauteur_membrure_solive_i
        * 1e-6
    )
    aire_ame_m2 = (
        plancher.epaisseur_ame_solive_i
        * (
            plancher.hauteur_solives_i
            - 2 * plancher.hauteur_membrure_solive_i
        )
        * 1e-6
    )
    poids_lineique_i_n_mm = (
        (
            aire_membrures_m2 * hypotheses.densite_membrures_i_kg_m3
            + aire_ame_m2 * hypotheses.densite_ame_i_kg_m3
        )
        * hypotheses.gravite_m_s2
        / 1_000
    )
    coordonnees = {noeud.identifiant: noeud for noeud in noeuds}
    for element in elements:
        debut = coordonnees[element.noeud_debut]
        fin = coordonnees[element.noeud_fin]
        longueur_element = (
            (fin.x_mm - debut.x_mm) ** 2 + (fin.y_mm - debut.y_mm) ** 2
        ) ** 0.5
        poids_lineique = (
            poids_lineique_i_n_mm
            if element.section == "SJ60_240_EQUIVALENTE"
            else poids_lineique_massif_n_mm
        )
        facteur_longueur = 1.0
        if element.section == "SJ60_240_EQUIVALENTE":
            facteur_longueur = (
                plancher.longueur_solives_i / plancher.entraxe_traverses
            )
        elif abs(fin.x_mm - debut.x_mm) < 1e-9:
            facteur_longueur = plancher.longueur_traverses / (
                y_rives[1] - y_rives[0]
            )
        demi_poids = longueur_element * facteur_longueur * poids_lineique / 2
        charges_par_noeud[element.noeud_debut] -= demi_poids
        charges_par_noeud[element.noeud_fin] -= demi_poids

    charges = tuple(
        ChargeNodaleCalculix(noeud, fz_n=charge)
        for noeud, charge in sorted(charges_par_noeud.items())
        if abs(charge) > 1e-9
    )
    hypotheses_texte = (
        "statique lineaire, petites deformations",
        "4 appuis verticaux aux traverses extremes; blocages horizontaux minimaux",
        "borne de raideur: intersections SAI et EWH parfaitement rigides",
        "raideur, glissement et resistance propres des connecteurs exclus",
        "OSB non rigidifiant; il distribue seulement les charges par aires tributaires",
        "murs, fondations, fluage, vibrations, feu et ELU exclus",
        (
            f"batteries {hypotheses.masse_batteries_kg:g} kg sur "
            f"{hypotheses.empreinte_longueur_mm:g} x "
            f"{hypotheses.empreinte_largeur_mm:g} mm, centre "
            f"({hypotheses.centre_x_mm:g}, {hypotheses.centre_y_mm:g})"
        ),
        (
            f"SJ60/240 calibree a EI={_EI_SJ60_240_N_MM2:.3g} N.mm2 "
            f"et GA={_GA_SJ60_240_N:.3g} N"
        ),
    )
    return ModeleCalculix(
        nom="Plancher local batteries - POC elastique",
        noeuds=tuple(noeuds),
        sections=sections,
        elements=tuple(elements),
        equations=(),
        appuis=appuis,
        charges=charges,
        hypotheses=hypotheses_texte,
    )


def main() -> None:
    analyseur = ArgumentParser(description=__doc__)
    analyseur.add_argument("--masse-batteries", type=float, default=1_000.0)
    analyseur.add_argument("--empreinte-longueur", type=float, default=1_000.0)
    analyseur.add_argument("--empreinte-largeur", type=float, default=1_000.0)
    analyseur.add_argument("--centre-x", type=float, default=1_500.0)
    analyseur.add_argument("--centre-y", type=float, default=0.0)
    analyseur.add_argument("--amplification-deformee", type=float, default=150.0)
    analyseur.add_argument("--exporter-seulement", action="store_true")
    arguments = analyseur.parse_args()
    hypotheses = HypothesesCalculixLocal(
        masse_batteries_kg=arguments.masse_batteries,
        empreinte_longueur_mm=arguments.empreinte_longueur,
        empreinte_largeur_mm=arguments.empreinte_largeur,
        centre_x_mm=arguments.centre_x,
        centre_y_mm=arguments.centre_y,
    )
    modele = generer_modele_calculix(creer_local_batteries(), hypotheses)
    repertoire = Path("build/local_batteries/simulation_calculix")
    repertoire.mkdir(parents=True, exist_ok=True)
    fichier_inp = repertoire / "plancher_local.inp"
    if arguments.exporter_seulement:
        fichier_inp.write_text(modele.entree(), encoding="utf-8")
        print(f"Jeu CalculiX exporté : {fichier_inp}")
        return
    resultat = executer_calculix(modele, repertoire)
    deplacements, _ = lire_resultats_dat(
        (repertoire / "plancher_local.dat").read_text(encoding="utf-8")
    )
    images = generer_images_deplacement(
        modele,
        deplacements,
        repertoire,
        zone_charge=ZoneCharge(
            hypotheses.centre_x_mm - hypotheses.empreinte_longueur_mm / 2,
            hypotheses.centre_x_mm + hypotheses.empreinte_longueur_mm / 2,
            hypotheses.centre_y_mm - hypotheses.empreinte_largeur_mm / 2,
            hypotheses.centre_y_mm + hypotheses.empreinte_largeur_mm / 2,
            "Empreinte batteries",
        ),
        amplification=arguments.amplification_deformee,
    )
    print("POC CalculiX terminé — statique linéaire, non validant")
    print(f"Charge verticale : {resultat.charge_verticale_n / 1_000:.3f} kN")
    print(f"Flèche verticale maximale : {resultat.fleche_max_mm:.3f} mm")
    print(f"Réaction d'appui maximale : {resultat.reaction_max_z_n / 1_000:.3f} kN")
    print(f"Erreur d'équilibre : {resultat.erreur_equilibre_n:.6f} N")
    print(f"Résultats FreeCAD/CalculiX : {resultat.fichier_frd}")
    print(f"Carte de flèche : {images.carte_fleche}")
    print(f"Déformée amplifiée : {images.deformation_3d}")


if __name__ == "__main__":
    main()
