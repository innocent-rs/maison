"""Commande de pré-vérification Eurocode 5 de l'atelier MOB."""

from .modele import creer_atelier_mob


def main() -> int:
    rapport = creer_atelier_mob().verifier_structure()
    print("Atelier MOB — pré-vérification Eurocode 5")
    print(
        f"Actions caractéristiques : Gk = "
        f"{rapport.charge_permanente_surfacique_solive_kN_m2:.3f} kN/m² de couches, "
        f"{rapport.charge_permanente_surfacique_utilisee_kN_m2:.3f} kN/m² sur "
        f"les traverses avec les solives "
        f"(pièces + {rapport.hypotheses.charge_permanente_rapportee_kN_m2:g} "
        f"kN/m² rapportés), "
        f"Qk = {rapport.hypotheses.charge_exploitation_surfacique_kN_m2:g} kN/m²"
    )
    print(
        f"Masse installée du plancher : {rapport.masses.masse_totale_kg:.1f} kg, "
        f"dont {rapport.masses.masse_madriers_primaires_kg:.1f} kg de madriers"
    )
    print("Masses par famille de pièces :")
    for ligne in rapport.masses.lignes:
        lineique = (
            ""
            if ligne.masse_lineique_kg_m is None
            else f", {ligne.masse_lineique_kg_m:.3g} kg/m"
        )
        print(
            f"- {ligne.quantite} × {ligne.reference}: "
            f"{ligne.masse_unitaire_kg:.3f} kg/pièce{lineique}, "
            f"total {ligne.masse_totale_kg:.1f} kg"
        )
    print(
        f"Classe de service {rapport.hypotheses.classe_service}, "
        f"durée {rapport.hypotheses.duree_charge_variable.value}"
    )
    for ligne in rapport.lignes_resume():
        print(ligne)
    if not rapport.conforme_calculs:
        return 1
    return 0 if rapport.validation_automatique else 2


if __name__ == "__main__":
    raise SystemExit(main())
