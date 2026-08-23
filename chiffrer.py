"""Génère les chiffrages du plancher, de la charpente ou du projet complet."""

from __future__ import annotations

import argparse
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


def generer(nom: str, destination: Path, maison) -> Chiffrage:
    chiffrage = Chiffrage(nom, nomenclature_du_lot(nom, maison), TARIFS)
    chiffrage.ecrire_csv(destination)
    if chiffrage.plans_debit:
        chiffrage.ecrire_debits_csv(destination.with_name(f"debit_{nom}.csv"))
    return chiffrage


def lignes_recapitulatif_achats(chiffrage: Chiffrage) -> tuple[str, ...]:
    """Construit le récapitulatif terminal de toutes les unités à acheter."""
    lignes: list[str] = []
    for plan_chiffre in chiffrage.plans_debit:
        tarif = plan_chiffre.tarif
        cout = (
            f"{plan_chiffre.cout_ttc_eur:.2f} € TTC"
            if plan_chiffre.cout_ttc_eur is not None
            else "prix à renseigner"
        )
        lignes.append(
            f"  {plan_chiffre.plan.nombre_barres:>3} × barre — "
            f"{tarif.designation_achat} [{plan_chiffre.reference_achat}] "
            f"— {cout}"
        )

    for ligne in chiffrage.lignes:
        if ligne.est_dans_plan_debit:
            continue
        article = ligne.ligne_bom.article
        tarif = ligne.tarif
        nombre = ligne.nombre_conditionnements
        assert nombre is not None
        conditionnement = tarif.conditionnement if tarif else "pièce"
        cout = (
            f"{ligne.cout_ttc_eur:.2f} € TTC"
            if ligne.cout_ttc_eur is not None
            else "prix à renseigner"
        )
        besoin = (
            f" ({ligne.ligne_bom.quantite} nécessaires)"
            if tarif and tarif.quantite_par_conditionnement > 1
            else ""
        )
        lignes.append(
            f"  {nombre:>3} × {conditionnement} — {article.designation} "
            f"[{article.reference}]{besoin} — {cout}"
        )
    return tuple(lignes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lot",
        choices=(*LOTS, "tous", "a-frame"),
        default="tous",
        help="lot à chiffrer ; a-frame est un alias de charpente",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="renvoie un code d'erreur si au moins un tarif manque",
    )
    arguments = parser.parse_args()

    lot_demande = "charpente" if arguments.lot == "a-frame" else arguments.lot
    lots = LOTS if lot_demande == "tous" else (lot_demande,)
    destination = Path("build")
    destination.mkdir(parents=True, exist_ok=True)
    maison = make_part()

    incomplet = False
    for lot in lots:
        fichier = destination / f"chiffrage_{lot}.csv"
        chiffrage = generer(lot, fichier, maison)
        incomplet |= not chiffrage.est_complet
        if chiffrage.est_vide:
            print(f"{lot:10} : désactivé — aucun article — {fichier}")
            continue
        print(
            f"{lot:10} : {chiffrage.sous_total_renseigne_ttc_eur:.2f} € TTC "
            f"— {len(chiffrage.references_manquantes)} référence(s) sans prix "
            f"— {fichier}"
        )
        print("  Achats :")
        for ligne in lignes_recapitulatif_achats(chiffrage):
            print(ligne)
        if chiffrage.plans_debit:
            print(f"  Plan de débit : {destination / f'debit_{lot}.csv'}")

    if arguments.strict and incomplet:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
