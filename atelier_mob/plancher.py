"""Plancher isolé de l'atelier en ossature bois."""

from home_framework.structure.plancher import PlancherBois

from .geometrie import GeometrieAtelierMob


def creer_plancher_atelier(
    geometrie: GeometrieAtelierMob,
    *,
    nombre_traverses: int = 8,
    entraxe_solives_i_max: float = 573.0,
) -> PlancherBois:
    """Crée la composition de référence du plancher de l'atelier.

    La trame comporte huit traverses primaires afin de limiter la portée libre
    des poutres en I et de conserver les joints du plancher OSB supérieur sur
    des appuis avec les dalles courantes de 2 500 mm.

    Cette configuration est une base de conception paramétrique. Les sections,
    assemblages et fondations restent à valider avec les charges réelles de
    l'atelier et les caractéristiques du sol.
    """

    return PlancherBois(
        geometrie,
        section_largeur=120,
        section_hauteur=240,
        nombre_traverses=nombre_traverses,
        entraxe_solives_i_max=entraxe_solives_i_max,
        hauteur_solives_i=240,
        largeur_membrure_solives_i=60,
        epaisseur_isolant_nominale=145,
        caissons_uniformes=True,
        inclure_connecteurs=True,
        inclure_solives_i=True,
        inclure_connecteurs_solives_i=True,
        inclure_osb_caissons=True,
        inclure_isolant_caissons=True,
        inclure_osb_plancher=True,
    )


def positions_pieux_pour_plancher(
    plancher: PlancherBois,
) -> tuple[tuple[float, float], ...]:
    """Implante trois appuis sous chaque traverse primaire.

    Les deux appuis latéraux sont centrés sous les poutres longitudinales. Le
    troisième coupe en deux la portée de la traverse. Il ne s'agit pas d'un
    dimensionnement géotechnique des pieux.
    """

    demi_ecartement = (
        plancher.geometrie.largeur_interieure - plancher.section_largeur
    ) / 2
    axes_y = (-demi_ecartement, 0.0, demi_ecartement)
    return tuple(
        (axe_x, axe_y)
        for axe_x in plancher.axes_traverses()
        for axe_y in axes_y
    )


# Nom conservé pour les consommateurs historiques du sous-projet.
ChassisPrimaireAtelier = PlancherBois
