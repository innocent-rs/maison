"""Optimise et exporte les débits des produits linéaires du projet."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from main import make_part
from maison.chiffrage import Chiffrage
from maison.prix import TARIFS


LOTS = ("plancher", "charpente", "total")


def nomenclature_du_lot(nom: str, maison):
    if nom == "plancher":
        return maison.nomenclature_plancher()
    if nom == "charpente":
        return maison.nomenclature_charpente()
    return maison.nomenclature_achats()


def _mm(valeur: Decimal) -> str:
    texte = f"{valeur:f}"
    return texte.rstrip("0").rstrip(".") if "." in texte else texte


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lot",
        choices=(*LOTS, "a-frame"),
        default="plancher",
        help="lot à optimiser ; a-frame est un alias de charpente",
    )
    arguments = parser.parse_args()
    lot = "charpente" if arguments.lot == "a-frame" else arguments.lot

    maison = make_part()
    chiffrage = Chiffrage(lot, nomenclature_du_lot(lot, maison), TARIFS)
    destination = Path("build") / f"debit_{lot}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    chiffrage.ecrire_debits_csv(destination)

    if not chiffrage.plans_debit:
        print(f"{lot} : aucun produit configuré en barre commerciale")
        print(f"CSV écrit dans {destination}")
        return

    for plan_chiffre in chiffrage.plans_debit:
        plan = plan_chiffre.plan
        print(
            f"{plan_chiffre.reference_achat} : {plan.nombre_barres} barre(s) × "
            f"{_mm(plan.longueur_stock_mm)} mm"
        )
        for barre in plan.barres:
            coupes = " + ".join(_mm(piece.longueur_mm) for piece in barre.pieces)
            print(
                f"  barre {barre.numero}: {coupes} mm — "
                f"{barre.nombre_traits} trait(s) — chute {_mm(barre.chute_mm)} mm"
            )
        cout = (
            f"{plan_chiffre.cout_ttc_eur:.2f} € TTC"
            if plan_chiffre.cout_ttc_eur is not None
            else "prix à renseigner"
        )
        print(
            f"  acheté {plan.longueur_achetee_mm / Decimal('1000')} m ; "
            f"utile {plan.longueur_utile_mm / Decimal('1000')} m ; "
            f"rendement {plan.taux_utilisation * Decimal('100'):.2f} % ; {cout}"
        )
    print(f"CSV écrit dans {destination}")


if __name__ == "__main__":
    main()
