"""Lance les cas de service du plancher fini et exporte leurs indicateurs."""

import csv
from pathlib import Path

from main import make_part
from maison.simulation import CasAssemblage, CasCharge, simuler_plancher


def _oui_non(valeur: bool) -> str:
    return "oui" if valeur else "non"


def main() -> None:
    destination = Path("build/simulation/resultats.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)
    plancher = make_part()
    resultats = [
        simuler_plancher(plancher, assemblage, cas_charge=charge)
        for assemblage in CasAssemblage
        for charge in CasCharge
    ]

    with destination.open("w", newline="", encoding="utf-8-sig") as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            (
                "assemblage",
                "cas_charge",
                "G_surfacique_kN_m2",
                "Q_surfacique_kN_m2",
                "poids_structure_N",
                "charge_totale_N",
                "fleche_globale_mm",
                "fleche_poutres_rive_mm",
                "limite_poutres_rive_mm",
                "taux_poutres_rive",
                "poutres_rive_conformes",
                "fleche_traverses_mm",
                "limite_traverses_mm",
                "taux_traverses",
                "traverses_conformes",
                "fleche_solives_i_mm",
                "limite_solives_i_mm",
                "taux_solives_i",
                "solives_i_conformes",
                "reaction_max_N",
                "reaction_totale_N",
                "noeuds",
                "elements",
                "elements_solives_i",
                "convergence",
            )
        )
        for resultat in resultats:
            writer.writerow(
                (
                    resultat.cas.value,
                    resultat.cas_charge.value,
                    f"{resultat.charge_permanente_surfacique_kN_m2:.6f}",
                    f"{resultat.charge_exploitation_kN_m2:.6f}",
                    f"{resultat.poids_propre_structure_n:.6f}",
                    f"{resultat.charge_totale_n:.6f}",
                    f"{resultat.fleche_max_mm:.6f}",
                    f"{resultat.fleche_relative_poutres_rive_max_mm:.6f}",
                    f"{resultat.limite_fleche_poutres_rive_mm:.6f}",
                    f"{resultat.taux_fleche_poutres_rive:.6f}",
                    _oui_non(resultat.respecte_limite_fleche_poutres_rive),
                    f"{resultat.fleche_relative_traverses_max_mm:.6f}",
                    f"{resultat.limite_fleche_traverses_mm:.6f}",
                    f"{resultat.taux_fleche_traverses:.6f}",
                    _oui_non(resultat.respecte_limite_fleche_traverses),
                    f"{resultat.fleche_relative_solives_i_max_mm:.6f}",
                    f"{resultat.limite_fleche_solives_i_mm:.6f}",
                    f"{resultat.taux_fleche_solives_i:.6f}",
                    _oui_non(resultat.respecte_limite_fleche_solives_i),
                    f"{resultat.reaction_max_z_n:.6f}",
                    f"{resultat.somme_reactions_z_n:.6f}",
                    resultat.nombre_noeuds,
                    resultat.nombre_elements,
                    resultat.nombre_elements_solives_i,
                    resultat.convergence,
                )
            )
            if resultat.cas_charge == CasCharge.SERVICE:
                print(
                    f"{resultat.cas.value:26} "
                    f"rive = {resultat.fleche_relative_poutres_rive_max_mm:.2f}/"
                    f"{resultat.limite_fleche_poutres_rive_mm:.2f} mm "
                    f"({_oui_non(resultat.respecte_limite_fleche_poutres_rive)}), "
                    f"traverse = {resultat.fleche_relative_traverses_max_mm:.2f}/"
                    f"{resultat.limite_fleche_traverses_mm:.2f} mm "
                    f"({_oui_non(resultat.respecte_limite_fleche_traverses)}), "
                    f"SJ60 = {resultat.fleche_relative_solives_i_max_mm:.2f}/"
                    f"{resultat.limite_fleche_solives_i_mm:.2f} mm "
                    f"({_oui_non(resultat.respecte_limite_fleche_solives_i)})"
                )
    print(f"Résultats écrits dans {destination}")


if __name__ == "__main__":
    main()
