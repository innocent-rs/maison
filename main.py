from ocp_vscode import show

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


def make_part():
    """Construit la structure paramétrique du plancher."""
    geometrie = GeometrieAFrame(
        largeur_interieure=6_000,
        angle_degres=60,
        surface_comptable_cible=20.5,
    )
    return PlancherAFrame(geometrie)


if __name__ == "__main__":
    plancher = make_part()
    elements = plancher.elements()
    geometrie = plancher.geometrie

    print(f"Dimensions intérieures : {geometrie.longueur_interieure:.0f} × 6000 mm")
    print(f"Hauteur au faîtage : {geometrie.hauteur_faitage:.0f} mm")
    print(f"Surface de plancher : {geometrie.surface_plancher:.2f} m²")
    print(f"Surface théorique ≥ 1,80 m : {geometrie.surface_comptable_cible:.2f} m²")
    print(
        f"Traverses primaires : {plancher.nombre_traverses}, "
        f"entraxe {plancher.entraxe_traverses:.0f} mm"
    )
    if plancher.inclure_solives_i:
        print(
            f"Solives en I : {plancher.nombre_solives_i}, "
            f"entraxe {plancher.entraxe_solives_i:.0f} mm"
        )
    else:
        print("Solives en I : désactivées")

    show(
        *(element.forme for element in elements),
        names=[element.nom for element in elements],
        colors=[element.couleur for element in elements],
    )
