from ocp_vscode import show

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


def make_part():
    """Construit la structure paramétrique du plancher."""
    geometrie = GeometrieAFrame(
        largeur_interieure=7_108,
        angle_degres=60,
        surface_comptable_cible=20.5,
        surface_plancher_max=20.0,
        longueur_interieure_imposee=2_804,
    )
    return PlancherAFrame(
        geometrie,
        entraxe_solives_i_max=573,
        trame_isolant_sans_decoupe=True,
        inclure_solives_i=True,
        inclure_osb_caissons=True,
        inclure_isolant_caissons=True,
    )


if __name__ == "__main__":
    plancher = make_part()
    elements = plancher.elements()
    geometrie = plancher.geometrie

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
            f"({plancher.nombre_lignes_solives_i} lignes × 2 travées), "
            f"entraxe {plancher.entraxe_solives_i:.0f} mm, "
            f"{plancher.nombre_sabots_ewh} × EWH219/91, "
            f"{plancher.nombre_pointes_ewh} × CNA4.0X35"
        )
    else:
        print("Solives en I : désactivées")
    if plancher.inclure_osb_caissons:
        print(
            f"Fonds de caisson : {plancher.nombre_panneaux_osb_caissons} × OSB "
            f"{plancher.epaisseur_osb_caissons:g} mm, "
            f"{plancher.nombre_vis_osb} × vis 4X35"
        )
        print(
            f"Tasseaux de rive : {plancher.nombre_tasseaux_rive} × 90 × 45 mm, "
            f"L {plancher.longueur_solives_i:.2f} mm"
        )
    if plancher.inclure_isolant_caissons:
        print(
            f"Isolation : {plancher.nombre_panneaux_isolant} × STEICOflex 036 "
            "120 × 575 × 1220 mm, sans découpe"
        )

    show(
        *(element.forme for element in elements),
        names=[element.nom for element in elements],
        colors=[element.couleur for element in elements],
    )
