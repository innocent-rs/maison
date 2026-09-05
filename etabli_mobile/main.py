"""Affiche le châssis courant de l'établi mobile dans le viewer OCP."""

from ocp_vscode import show

from .modele import creer_etabli_mobile


def main() -> None:
    etabli = creer_etabli_mobile()
    chassis = etabli.chassis
    elements = etabli.elements()

    print("Établi mobile — base et deux supports Qbrick System ONE")
    print(
        f"Cadre bas : {chassis.longueur:g} × {chassis.profondeur:g} × "
        f"{chassis.hauteur_profile:g} mm, profilés "
        f"{chassis.largeur_profile:g} × {chassis.hauteur_profile:g} mm"
    )
    print(
        f"Renforts diagonaux : {len(chassis.elements_renforts())}, "
        f"recul {chassis.recul_renfort_angle:g} mm"
    )
    print(f"Implantations de roues prévues : {len(chassis.positions_roues())}")
    print(
        f"Poids des profilés : {chassis.masse_profiles_kg:.2f} kg "
        f"({chassis.masse_lineique_kg_m:g} kg/m)"
    )
    plateau = etabli.plateaux_qbrick[0]
    masse_cp = sum(support.masse_kg for support in etabli.plateaux_qbrick)
    print(
        f"Supports CP : {len(etabli.plateaux_qbrick)} découpes "
        f"{plateau.longueur:g} × {plateau.profondeur:g} × "
        f"{plateau.epaisseur:g} mm, masse indicative totale {masse_cp:.2f} kg"
    )
    print(
        f"Qbrick System ONE : {len(etabli.modules_qbrick_one)} enveloppes "
        f"{etabli.modules_qbrick_one[0].longueur:g} × "
        f"{etabli.modules_qbrick_one[0].profondeur:g} × "
        f"{etabli.modules_qbrick_one[0].hauteur:g} mm"
    )
    print(
        "Hors modèle : pieds, cadre supérieur, roulettes et "
        "fixations Qbrick System ONE"
    )

    show(
        *(element.forme for element in elements),
        names=[element.nom for element in elements],
        colors=[element.couleur for element in elements],
    )


if __name__ == "__main__":
    main()
