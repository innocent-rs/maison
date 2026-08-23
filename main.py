from ocp_vscode import show

from maison.geometrie import GeometrieAFrame
from maison.modele import MaisonAFrame
from maison.structure import CharpenteAFrame, PlancherAFrame


def make_part():
    """Construit le châssis primaire et son solivage en poutres en I."""
    geometrie = GeometrieAFrame(
        largeur_interieure=4_000,
        angle_degres=60,
        surface_comptable_cible=20.5,
        surface_plancher_max=20.0,
        longueur_interieure_imposee=4_800,
    )
    charpente = CharpenteAFrame(
        geometrie,
        entraxe_fermes=500,
        largeur_poutre_rive=120,
        niveau_appui=240,
        inclure_liaisons_pied=True,
        diametre_tirants=16,
        niveau_axes_tirants=-30,
    )
    plancher = PlancherAFrame(
        geometrie,
        section_largeur=120,
        section_hauteur=240,
        nombre_traverses=3,
        entraxe_solives_i_max=573,
        hauteur_solives_i=240,
        largeur_membrure_solives_i=60,
        epaisseur_isolant_nominale=145,
        trame_isolant_sans_decoupe=False,
        caissons_uniformes=True,
        inclure_connecteurs=True,
        inclure_solives_i=True,
        inclure_osb_caissons=True,
        inclure_isolant_caissons=False,
        inclure_osb_plancher=False,
    )
    return MaisonAFrame(plancher, charpente, inclure_charpente=False)


if __name__ == "__main__":
    maison = make_part()
    plancher = maison.plancher
    charpente = maison.charpente
    elements = maison.elements()
    geometrie = maison.geometrie

    print(
        f"Dimensions hors-tout : {geometrie.longueur_interieure:.0f} × "
        f"{geometrie.largeur_interieure:.0f} mm"
    )
    print(f"Hauteur au faîtage : {geometrie.hauteur_faitage:.0f} mm")
    print(f"Surface de plancher : {geometrie.surface_plancher:.2f} m²")
    print(f"Surface théorique ≥ 1,80 m : {geometrie.surface_comptable:.2f} m²")
    if geometrie.surface_plancher_max is not None:
        print(f"Plafond de surface totale : {geometrie.surface_plancher_max:.2f} m²")
    print(
        f"Traverses primaires : {plancher.nombre_traverses}, "
        f"entraxe {plancher.entraxe_traverses:.0f} mm"
    )
    if plancher.inclure_connecteurs:
        print(
            f"Connecteurs : {plancher.nombre_sabots} × SAI500/120/2, "
            f"plan {plancher.plan_fixation_sai.value}, "
            f"{plancher.nombre_vis_connecteurs} × CSA5.0X40"
        )
    else:
        print("Connecteurs : désactivés")
    if plancher.inclure_solives_i:
        print(
            f"Solives en I : {plancher.nombre_solives_i} segments "
            f"({plancher.nombre_lignes_solives_i} lignes × "
            f"{plancher.nombre_traverses - 1} travées), "
            f"entraxe {plancher.entraxe_solives_i:.0f} mm, "
            f"{plancher.nombre_sabots_ewh} × "
            f"EWH{plancher.hauteur_solives_i:g}/"
            f"{plancher.largeur_membrure_solives_i + 1:g}, "
            f"{plancher.nombre_pointes_ewh} × CNA4.0X35"
        )
    else:
        print("Solives en I : désactivées")
    if plancher.inclure_osb_caissons:
        print(
            f"Fonds de caisson : {plancher.nombre_panneaux_osb_caissons} × OSB 3 BD "
            f"{plancher.epaisseur_osb_caissons:g} mm, "
            f"{plancher.nombre_dalles_brutes_osb_caissons} panneaux bruts "
            f"{plancher.longueur_dalle_osb_caissons:g} × "
            f"{plancher.largeur_dalle_osb_caissons:g} mm, "
            f"{plancher.nombre_vis_osb} × vis 4X35"
        )
        print(
            f"Tasseaux de rive : {plancher.nombre_tasseaux_rive} × "
            f"{plancher.largeur_membrure_solives_i:g} × 45 mm, "
            f"L {plancher.longueur_solives_i:.2f} mm"
        )
    if plancher.inclure_isolant_caissons:
        mode_pose = (
            "sans découpe"
            if plancher.trame_isolant_sans_decoupe
            else (
                f"recoupé à {plancher.largeur_caisson_isolant:.0f} × "
                f"{plancher.longueur_caisson_isolant:.0f} mm"
            )
        )
        print(
            f"Isolation : {plancher.nombre_panneaux_isolant} × STEICOflex 036 "
            f"{plancher.epaisseur_isolant_nominale:g} × 575 × 1220 mm, "
            f"{mode_pose}"
        )
    if plancher.inclure_osb_plancher:
        print(
            f"Plancher supérieur : {plancher.nombre_panneaux_osb_plancher} "
            f"découpes OSB {plancher.epaisseur_osb_plancher:g} mm, "
            f"{plancher.nombre_dalles_brutes_osb_plancher} dalles brutes, "
            f"{plancher.nombre_vis_osb_plancher} × vis 5X60"
        )
        print(
            f"Réservations de pieds : {plancher.nombre_reservations_pieds} × "
            f"{plancher.largeur_reservation_pied:g} × "
            f"{plancher.profondeur_reservation_pied:g} mm"
        )
    if maison.inclure_charpente:
        print(
            f"Fermes en A : {charpente.nombre_fermes}, "
            f"entraxe {charpente.entraxe_fermes:.0f} mm"
        )
    else:
        print("Charpente A-frame : désactivée")

    show(
        *(element.forme for element in elements),
        names=[element.nom for element in elements],
        colors=[element.couleur for element in elements],
    )
