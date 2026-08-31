"""Application du détecteur générique de vides au plancher de l'atelier."""

from build123d import Align, Box, Pos, Shape

from home_framework.structure.plancher import PlancherBois
from home_framework.vides import RapportVides, detecter_vides


def enveloppe_analyse_plancher(plancher: PlancherBois) -> Shape:
    """Délimite le volume fermé entre les deux parements du plancher."""

    niveau_bas_solives = (
        plancher.niveau_haut_traverses - plancher.hauteur_solives_i
    )
    niveau_interieur_fond = (
        niveau_bas_solives
        + plancher.hauteur_membrure_solive_i
        + plancher.epaisseur_osb_caissons
    )
    hauteur = plancher.niveau_haut_traverses - niveau_interieur_fond
    return Pos(
        0,
        -plancher.geometrie.largeur_interieure / 2,
        niveau_interieur_fond,
    ) * Box(
        plancher.geometrie.longueur_interieure,
        plancher.geometrie.largeur_interieure,
        hauteur,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )


def analyser_vides_structure(plancher: PlancherBois) -> RapportVides:
    """Soustrait automatiquement chaque pièce du volume intérieur du plancher."""

    return detecter_vides(
        enveloppe_analyse_plancher(plancher),
        (element.forme for element in plancher.elements()),
    )
