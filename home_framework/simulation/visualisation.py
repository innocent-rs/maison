"""Rendus statiques des résultats CalculiX sans dépendre de FreeCAD."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from .calculix import ModeleCalculix


@dataclass(frozen=True, slots=True)
class ZoneCharge:
    x_debut_mm: float
    x_fin_mm: float
    y_debut_mm: float
    y_fin_mm: float
    nom: str = "Empreinte de charge"


@dataclass(frozen=True, slots=True)
class ImagesDeplacement:
    carte_fleche: Path
    deformation_3d: Path
    amplification: float


def _preparer_matplotlib():
    # Évite toute écriture dans ~/.config dans les shells reproductibles/CI.
    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(Path(tempfile.gettempdir()) / "home-framework-matplotlib"),
    )
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    return matplotlib, plt


def generer_images_deplacement(
    modele: ModeleCalculix,
    deplacements: dict[int, tuple[float, ...]],
    repertoire: Path,
    zone_charge: ZoneCharge | None = None,
    amplification: float = 150.0,
) -> ImagesDeplacement:
    """Génère une heat map de flèche et une vue 3D déformée amplifiée."""
    if amplification <= 0:
        raise ValueError("l'amplification de la déformée doit être positive")
    ids_noeuds = {noeud.identifiant for noeud in modele.noeuds}
    if not ids_noeuds <= deplacements.keys():
        raise ValueError("les déplacements ne couvrent pas tous les nœuds du modèle")

    matplotlib, plt = _preparer_matplotlib()
    from matplotlib import patches
    from matplotlib.lines import Line2D
    from matplotlib.tri import Triangulation

    repertoire.mkdir(parents=True, exist_ok=True)
    fichier_carte = repertoire / "carte_fleche_verticale.png"
    fichier_deformee = repertoire / "deformee_3d.png"
    coordonnees = {noeud.identifiant: noeud for noeud in modele.noeuds}

    # Les éventuels nœuds doublés des futures rotules sont regroupés pour la
    # triangulation, en conservant la flèche descendante la plus défavorable.
    points: dict[tuple[float, float], float] = {}
    for noeud in modele.noeuds:
        cle = (noeud.x_mm / 1_000, noeud.y_mm / 1_000)
        fleche = max(0.0, -deplacements[noeud.identifiant][2])
        points[cle] = max(points.get(cle, 0.0), fleche)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    fleches = list(points.values())
    fleche_max = max(fleches)
    if fleche_max <= 0:
        raise ValueError("aucune flèche descendante n'est disponible")
    triangulation = Triangulation(xs, ys)
    normalisation = matplotlib.colors.Normalize(vmin=0.0, vmax=fleche_max)
    palette = matplotlib.colormaps["turbo"]

    figure, axe = plt.subplots(figsize=(11.5, 9), constrained_layout=True)
    contours = axe.tricontourf(
        triangulation,
        fleches,
        levels=24,
        cmap=palette,
        norm=normalisation,
    )
    for element in modele.elements:
        debut = coordonnees[element.noeud_debut]
        fin = coordonnees[element.noeud_fin]
        est_solive_i = "SJ" in element.section.upper()
        axe.plot(
            (debut.x_mm / 1_000, fin.x_mm / 1_000),
            (debut.y_mm / 1_000, fin.y_mm / 1_000),
            color="#20252b" if not est_solive_i else "#59636e",
            linewidth=1.35 if not est_solive_i else 0.7,
            alpha=0.72,
            zorder=3,
        )
    if zone_charge is not None:
        rectangle = patches.Rectangle(
            (zone_charge.x_debut_mm / 1_000, zone_charge.y_debut_mm / 1_000),
            (zone_charge.x_fin_mm - zone_charge.x_debut_mm) / 1_000,
            (zone_charge.y_fin_mm - zone_charge.y_debut_mm) / 1_000,
            facecolor="none",
            edgecolor="white",
            linewidth=2.2,
            linestyle="--",
            label=zone_charge.nom,
            zorder=5,
        )
        axe.add_patch(rectangle)
    appuis = [coordonnees[appui.noeud] for appui in modele.appuis]
    axe.scatter(
        [noeud.x_mm / 1_000 for noeud in appuis],
        [noeud.y_mm / 1_000 for noeud in appuis],
        marker="^",
        s=90,
        facecolor="white",
        edgecolor="#20252b",
        linewidth=1.2,
        label="Appuis",
        zorder=6,
    )
    noeud_max = max(
        modele.noeuds,
        key=lambda noeud: max(0.0, -deplacements[noeud.identifiant][2]),
    )
    axe.scatter(
        noeud_max.x_mm / 1_000,
        noeud_max.y_mm / 1_000,
        marker="x",
        s=110,
        color="white",
        linewidth=2.4,
        zorder=7,
    )
    axe.annotate(
        f"max {fleche_max:.3f} mm",
        (noeud_max.x_mm / 1_000, noeud_max.y_mm / 1_000),
        xytext=(12, 12),
        textcoords="offset points",
        color="white",
        weight="bold",
        bbox={"boxstyle": "round,pad=0.3", "fc": "#20252b", "alpha": 0.8},
        zorder=8,
    )
    barre = figure.colorbar(contours, ax=axe, shrink=0.82, pad=0.025)
    barre.set_label("Flèche descendante réelle (mm)")
    axe.set_title("Plancher local batteries — carte de flèche verticale")
    axe.set_xlabel("X — longueur (m)")
    axe.set_ylabel("Y — largeur (m)")
    axe.set_aspect("equal")
    axe.legend(loc="upper right", framealpha=0.92)
    axe.text(
        0.0,
        -0.09,
        "POC élastique — cette carte montre les déplacements, pas une probabilité de rupture.",
        transform=axe.transAxes,
        fontsize=9,
        color="#4d5660",
    )
    figure.savefig(fichier_carte, dpi=180, facecolor="white")
    plt.close(figure)

    figure = plt.figure(figsize=(12, 8.5), constrained_layout=True)
    axe_3d = figure.add_subplot(111, projection="3d")
    for element in modele.elements:
        debut = coordonnees[element.noeud_debut]
        fin = coordonnees[element.noeud_fin]
        fleche_debut = max(0.0, -deplacements[debut.identifiant][2])
        fleche_fin = max(0.0, -deplacements[fin.identifiant][2])
        couleur = palette(
            normalisation((fleche_debut + fleche_fin) / 2)
        )
        axe_3d.plot(
            (debut.x_mm / 1_000, fin.x_mm / 1_000),
            (debut.y_mm / 1_000, fin.y_mm / 1_000),
            (
                deplacements[debut.identifiant][2] * amplification / 1_000,
                deplacements[fin.identifiant][2] * amplification / 1_000,
            ),
            color=couleur,
            linewidth=1.8 if "SJ" not in element.section.upper() else 1.0,
        )
    limites_x = (min(xs), max(xs))
    limites_y = (min(ys), max(ys))
    contour_plancher_x = (
        limites_x[0], limites_x[1], limites_x[1], limites_x[0], limites_x[0]
    )
    contour_plancher_y = (
        limites_y[0], limites_y[0], limites_y[1], limites_y[1], limites_y[0]
    )
    axe_3d.plot(
        contour_plancher_x,
        contour_plancher_y,
        (0, 0, 0, 0, 0),
        color="#9aa3ad",
        linestyle=":",
        linewidth=1.2,
    )
    if zone_charge is not None:
        zx = (
            zone_charge.x_debut_mm / 1_000,
            zone_charge.x_fin_mm / 1_000,
            zone_charge.x_fin_mm / 1_000,
            zone_charge.x_debut_mm / 1_000,
            zone_charge.x_debut_mm / 1_000,
        )
        zy = (
            zone_charge.y_debut_mm / 1_000,
            zone_charge.y_debut_mm / 1_000,
            zone_charge.y_fin_mm / 1_000,
            zone_charge.y_fin_mm / 1_000,
            zone_charge.y_debut_mm / 1_000,
        )
        axe_3d.plot(zx, zy, (0, 0, 0, 0, 0), color="black", linestyle="--")
    axe_3d.set_title(
        f"Déformée verticale amplifiée ×{amplification:g} — flèche réelle max {fleche_max:.3f} mm"
    )
    axe_3d.set_xlabel("X (m)")
    axe_3d.set_ylabel("Y (m)")
    axe_3d.set_zlabel("Déplacement amplifié (m)")
    axe_3d.view_init(elev=27, azim=-58)
    axe_3d.set_box_aspect((1, 1, 0.32))
    scalaire = matplotlib.cm.ScalarMappable(norm=normalisation, cmap=palette)
    scalaire.set_array([])
    barre = figure.colorbar(scalaire, ax=axe_3d, shrink=0.68, pad=0.08)
    barre.set_label("Flèche descendante réelle (mm)")
    axe_3d.legend(
        handles=[
            Line2D(
                [0], [0], color="#9aa3ad", linestyle=":", label="Plan non déformé"
            )
        ],
        loc="upper left",
    )
    figure.savefig(fichier_deformee, dpi=180, facecolor="white")
    plt.close(figure)
    return ImagesDeplacement(fichier_carte, fichier_deformee, amplification)
