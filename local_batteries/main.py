"""Affiche le plancher et les murs du local batteries dans le viewer OCP."""

from ocp_vscode import show

from local_batteries import creer_local_batteries


def main() -> None:
    local = creer_local_batteries()
    plancher = local.plancher
    elements = local.elements()

    print("Local batteries : 3 000 × 3 000 mm — 9,00 m²")
    print(
        "Châssis : 2 madriers de rive + "
        f"{plancher.nombre_traverses} traverses en 120 × 240 mm"
    )
    print(
        f"Poutres en I : {plancher.nombre_solives_i} tronçons SJ60/240, "
        f"{plancher.nombre_lignes_solives_i} lignes, "
        f"entraxe {plancher.entraxe_solives_i:.1f} mm"
    )
    print("Plancher supérieur : 1 couche d’OSB 3 R+L de 22 mm")
    print("Isolation : Isonat Flex 55 de 145 mm entre les poutres en I")
    print(
        "Fonds de caisson : OSB 3 BD de 12 mm sur membrures basses "
        "et tasseaux de rive"
    )
    print(
        "Murs : ossature Douglas 45 × 145 mm, H 2 575 mm, "
        "OSB extérieur et Isonat 145 mm"
    )
    print("Entrée : une réservation centrée de 900 × 2 150 mm, sans fenêtre")
    print(f"Cible de charge batteries : {local.charge_batteries_kg:.0f} kg")

    show(
        *(element.forme for element in elements),
        names=[element.nom for element in elements],
        colors=[element.couleur for element in elements],
    )


if __name__ == "__main__":
    main()
