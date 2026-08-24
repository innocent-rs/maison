"""Optimise et exporte les débits des produits linéaires du projet."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from maison.debit import lignes_resume_panneaux_osb
from home_framework.chiffrage import Chiffrage, ModeTarification
from catalogues.prix import TARIFS
from projets import resoudre_projet_et_lot


def _mm(valeur: Decimal) -> str:
    texte = f"{valeur:f}"
    return texte.rstrip("0").rstrip(".") if "." in texte else texte


def lignes_resume_lots_lineaires(chiffrage: Chiffrage) -> tuple[str, ...]:
    """Résume les achats imposant une quantité linéaire minimale."""
    lignes: list[str] = []
    for ligne in chiffrage.lignes:
        tarif = ligne.tarif
        if not tarif or tarif.mode is not ModeTarification.LOT_LINEAIRE:
            continue
        assert ligne.longueur_utile_m is not None
        assert ligne.longueur_achetee_m is not None
        surplus = ligne.longueur_achetee_m - ligne.longueur_utile_m
        nombre = ligne.nombre_conditionnements
        assert nombre is not None
        cout = (
            f"{ligne.cout_ttc_eur:.2f} € TTC"
            if ligne.cout_ttc_eur is not None
            else "prix à renseigner"
        )
        lignes.append(
            f"{ligne.ligne_bom.article.reference} : "
            f"{nombre} × {tarif.conditionnement} — "
            f"utile {ligne.longueur_utile_m:g} m ; "
            f"acheté {ligne.longueur_achetee_m:g} m ; "
            f"surplus {surplus:g} m — {cout}"
        )
    return tuple(lignes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projet",
        default="maison",
        help="projet à optimiser (maison ou local_batteries)",
    )
    parser.add_argument(
        "--lot",
        default="plancher",
        help="lot du projet à optimiser",
    )
    arguments = parser.parse_args()
    try:
        definition, lot_demande = resoudre_projet_et_lot(
            arguments.projet,
            arguments.lot,
        )
        lots = definition.lots_demandes(lot_demande)
    except ValueError as erreur:
        parser.error(str(erreur))
    if len(lots) != 1:
        parser.error("l'optimisation demande un lot unique")
    lot = lots[0]
    projet = definition.construire()
    identifiant_lot = (
        lot if definition.identifiant == "maison" else definition.identifiant
    )
    chiffrage = Chiffrage(
        identifiant_lot,
        definition.nomenclature(projet, lot),
        TARIFS,
    )
    lignes_panneaux = (
        definition.resumer_debit(projet, lot)
        if definition.resumer_debit
        else ()
    )
    lignes_lots_lineaires = lignes_resume_lots_lineaires(chiffrage)
    destination = definition.dossier_sortie / f"debit_{lot}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    chiffrage.ecrire_debits_csv(destination)
    fichiers_specifiques = (
        definition.exporter_debit(projet, lot, definition.dossier_sortie)
        if definition.exporter_debit
        else ()
    )

    if (
        not chiffrage.plans_debit
        and not lignes_panneaux
        and not lignes_lots_lineaires
    ):
        print(f"{lot} : aucun produit à optimiser")
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
    for ligne in lignes_panneaux:
        print(ligne)
    for ligne in lignes_lots_lineaires:
        print(ligne)
    print(f"CSV écrit dans {destination}")
    for fichier in fichiers_specifiques:
        print(f"CSV spécifique écrit dans {fichier}")


if __name__ == "__main__":
    main()
