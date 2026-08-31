"""Affiche le plancher courant de l'atelier MOB dans le viewer OCP."""

from ocp_vscode import show

from .modele import creer_atelier_mob


def main() -> None:
    atelier = creer_atelier_mob()
    elements = atelier.elements()

    print("Atelier MOB — fondations sur pieux vissés")
    print(
        f"Emprise : {atelier.geometrie.largeur_interieure:.0f} × "
        f"{atelier.geometrie.longueur_interieure:.1f} mm — "
        f"{atelier.geometrie.surface_plancher:.1f} m²"
    )
    print(
        f"Trame primaire : {atelier.plancher.nombre_traverses} traverses, "
        f"entraxe {atelier.plancher.entraxe_traverses:.1f} mm"
    )
    print(
        f"Solives en I : {atelier.plancher.nombre_solives_i} segments "
        f"SJ60/240, portée {atelier.plancher.longueur_solives_i:.1f} mm, "
        f"entraxe {atelier.plancher.entraxe_solives_i:.1f} mm"
    )
    print(
        "Composition : fond OSB 3 12 mm, fibre de bois 145 mm, "
        "plancher porteur OSB 3 R+L 22 mm"
    )
    print(
        f"Appuis : {atelier.fondations.nombre_platines} platines "
        "200 × 200 × 5 mm ; pieux et sol à dimensionner"
    )

    if elements:
        show(
            *(element.forme for element in elements),
            names=[element.nom for element in elements],
            colors=[element.couleur for element in elements],
        )


if __name__ == "__main__":
    main()
