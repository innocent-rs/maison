"""Génère le chiffrage de tout projet enregistré, avec le catalogue commun."""

from __future__ import annotations

import argparse
from pathlib import Path

from home_framework.chiffrage import Chiffrage, ModeTarification
from catalogues.prix import TARIFS
from projets import resoudre_projet_et_lot


def generer(nom: str, destination: Path, nomenclature) -> Chiffrage:
    chiffrage = Chiffrage(nom, nomenclature, TARIFS)
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
        if tarif and tarif.mode is ModeTarification.LOT_LINEAIRE:
            assert ligne.longueur_utile_m is not None
            assert ligne.longueur_achetee_m is not None
            besoin = (
                f" ({ligne.longueur_utile_m:g} ml utiles ; "
                f"{ligne.longueur_achetee_m:g} ml achetés)"
            )
        else:
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
        "--projet",
        default="maison",
        help="projet à chiffrer (maison ou local_batteries)",
    )
    parser.add_argument(
        "--lot",
        default="tous",
        help="lot du projet à chiffrer, ou tous",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="renvoie un code d'erreur si au moins un tarif manque",
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

    destination = definition.dossier_sortie
    destination.mkdir(parents=True, exist_ok=True)
    projet = definition.construire()

    incomplet = False
    for lot in lots:
        fichier = destination / f"chiffrage_{lot}.csv"
        identifiant_lot = (
            lot if definition.identifiant == "maison" else definition.identifiant
        )
        chiffrage = generer(
            identifiant_lot,
            fichier,
            definition.nomenclature(projet, lot),
        )
        incomplet |= not chiffrage.est_complet
        if chiffrage.est_vide:
            print(
                f"{definition.identifiant}/{lot} : "
                f"désactivé — aucun article — {fichier}"
            )
            continue
        print(
            f"{definition.identifiant}/{lot} : "
            f"{chiffrage.sous_total_renseigne_ttc_eur:.2f} € TTC "
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
