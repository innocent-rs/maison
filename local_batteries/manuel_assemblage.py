"""Adaptateur du manuel d'assemblage pour le projet local-batteries."""

from __future__ import annotations

from pathlib import Path

from home_framework.assemblage import (
    OperationAssemblage,
    PiecePlacee,
    formater_mm,
)
from home_framework.manuel import exporter_manuel

from .modele import LocalBatteries, creer_local_batteries


def poutres_du_plancher(local: LocalBatteries) -> tuple[PiecePlacee, ...]:
    """Expose les pièces résolues par le graphe contraint du plancher."""
    return local.plancher.assemblage_poutres().pieces


def elements_du_manuel(local: LocalBatteries) -> tuple[PiecePlacee, ...]:
    """Expose tous les composants couverts par le manuel courant."""
    return local.assemblage_plancher().pieces


def etapes_assemblage(local: LocalBatteries) -> tuple[OperationAssemblage, ...]:
    """Expose la timeline déduite des contraintes de la CAO."""
    return local.assemblage_plancher().operations()


def exporter_manuel_assemblage(
    local: LocalBatteries,
    chemin: Path | str = Path("build/local_batteries/manuel_assemblage_poutres.pdf"),
) -> Path:
    """Adapte le graphe constructif du local au renderer générique."""
    assemblage = local.assemblage_plancher()
    largeur = max(piece.forme.bounding_box().max.Y for piece in assemblage.pieces)
    largeur -= min(piece.forme.bounding_box().min.Y for piece in assemblage.pieces)
    longueur = max(piece.forme.bounding_box().max.X for piece in assemblage.pieces)
    longueur -= min(piece.forme.bounding_box().min.X for piece in assemblage.pieces)
    return exporter_manuel(
        assemblage,
        chemin,
        titre="Plancher — structure, fonds OSB et isolant",
        sous_titre=(
            f"Local batteries {formater_mm(longueur)} × "
            f"{formater_mm(largeur)} mm"
        ),
    )


def main() -> None:
    destination = exporter_manuel_assemblage(creer_local_batteries())
    print(f"Manuel d'assemblage généré : {destination}")


if __name__ == "__main__":
    main()
