"""Résumés de débit propres au modèle principal de la maison."""

from decimal import Decimal

from maison.structure import DalleOSB, TypeBordsOSB


def lignes_resume_panneaux_osb(plancher) -> tuple[str, ...]:
    """Résume le débit rectangulaire des fonds dans les panneaux OSB bruts."""
    if not plancher.nombre_dalles_brutes_osb_caissons:
        return ()
    nombre_bruts = plancher.nombre_dalles_brutes_osb_caissons
    nombre_decoupes = plancher.nombre_panneaux_osb_caissons
    dalle = DalleOSB(
        epaisseur=plancher.epaisseur_osb_caissons,
        largeur=plancher.largeur_dalle_osb_caissons,
        longueur=plancher.longueur_dalle_osb_caissons,
        type_bords=TypeBordsOSB.BORDS_DROITS,
    )
    surface_achetee = Decimal(
        str(
            nombre_bruts
            * plancher.largeur_dalle_osb_caissons
            * plancher.longueur_dalle_osb_caissons
        )
    )
    surface_decoupes = Decimal(
        str(
            plancher.longueur_solives_i
            * (
                plancher.nombre_panneaux_osb_interieurs
                * plancher.largeur_panneaux_osb_caissons
                + plancher.nombre_panneaux_osb_rive
                * plancher.largeur_panneaux_osb_rive
            )
        )
    )
    rendement = surface_decoupes / surface_achetee * Decimal("100")
    decoupes_par_panneau = plancher.rendement_dalle_osb_caissons(
        plancher.largeur_panneaux_osb_caissons
    )
    return (
        (
            f"{dalle.article_bom().reference} : "
            f"{nombre_bruts} panneau(x) × "
            f"{plancher.longueur_dalle_osb_caissons:g} × "
            f"{plancher.largeur_dalle_osb_caissons:g} mm"
        ),
        (
            f"  {nombre_decoupes} fonds × {plancher.longueur_solives_i:g} × "
            f"{plancher.largeur_panneaux_osb_caissons:.3f} mm — "
            f"{decoupes_par_panneau} "
            f"découpes par panneau — rendement surfacique {rendement:.2f} %"
        ),
    )
