"""Lance les premiers cas de simulation comparative du plancher."""

import csv
from pathlib import Path

from main import make_part
from maison.simulation import CasAssemblage, simuler_plancher


def main() -> None:
    destination = Path("build/simulation/resultats.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)
    plancher = make_part()
    resultats = [simuler_plancher(plancher, cas) for cas in CasAssemblage]

    with destination.open("w", newline="", encoding="utf-8-sig") as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            ("cas", "charge_N", "fleche_max_mm", "reaction_totale_N", "convergence")
        )
        for resultat in resultats:
            writer.writerow(
                (
                    resultat.cas.value,
                    f"{resultat.charge_n:g}",
                    f"{resultat.fleche_max_mm:.6f}",
                    f"{resultat.somme_reactions_z_n:.6f}",
                    resultat.convergence,
                )
            )
            print(
                f"{resultat.cas.value:26} "
                f"flèche = {resultat.fleche_max_mm:.3f} mm"
            )
    print(f"Résultats écrits dans {destination}")


if __name__ == "__main__":
    main()
