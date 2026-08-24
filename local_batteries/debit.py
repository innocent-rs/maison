"""Débit spécifique des panneaux du local batteries."""

import csv
from collections import Counter
from math import ceil, floor
from pathlib import Path

from maison.optimisation import PieceDebit, PlanDebit, optimiser_debit
from maison.structure import DalleOSB, TypeBordsOSB

from .modele import LocalBatteries


def lots_decoupes_osb(
    local: LocalBatteries,
) -> tuple[tuple[str, float, float, float, str, int], ...]:
    """Regroupe les découpes par couche, format et orientation de pose."""
    lots: Counter[tuple[str, float, float, float, str]] = Counter()
    for element in local.elements():
        if not element.nom.startswith(("OSB inférieur", "OSB supérieur")):
            continue
        couche = "inférieure" if "inférieur" in element.nom else "supérieure"
        orientation = "X" if couche == "inférieure" else "Y"
        piece = element.piece
        lots[(couche, piece.longueur, piece.largeur, piece.epaisseur, orientation)] += 1
    return tuple(
        (*dimensions, quantite)
        for dimensions, quantite in sorted(lots.items())
    )


def lignes_resume_debit(local: LocalBatteries, lot: str) -> tuple[str, ...]:
    if lot != "total":
        return ()
    lignes = [
        f"OSB-RL-675x2500x22 : {local.nombre_dalles_osb_achetees} panneau(x) brut(s)"
    ]
    for couche, longueur, largeur, _, orientation, quantite in lots_decoupes_osb(local):
        lignes.append(
            f"  {quantite} × {longueur:g} × {largeur:g} mm — "
            f"couche {couche}, sens {orientation}"
        )
    lignes.append(
        "OSB-BD-1196x2800x12 : "
        f"{local.plancher.nombre_dalles_brutes_osb_caissons} panneau(x) brut(s)"
    )
    lots_fonds: Counter[tuple[float, float]] = Counter()
    for element in local.elements():
        if element.nom.startswith("Fond OSB"):
            lots_fonds[(element.piece.longueur, element.piece.largeur)] += 1
    for (longueur, largeur), quantite in sorted(lots_fonds.items()):
        lignes.append(
            f"  {quantite} × {longueur:g} × {largeur:g} mm — "
            "fonds de caisson sur membrures basses et tasseaux de rive"
        )
    lignes.append(
        "ISOL-ISONAT-FLEX55-145x580x1220 : "
        f"{local.nombre_panneaux_isolant_achetes} panneau(x) brut(s) — "
        "40 découpes de 607,5 × 278,8 mm"
    )
    return tuple(lignes)


def plan_debit_osb(local: LocalBatteries) -> PlanDebit:
    """Optimise les coupes de 600 mm de large dans la longueur des dalles."""
    pieces = []
    for element in local.elements():
        if not element.nom.startswith(("OSB inférieur", "OSB supérieur")):
            continue
        piece = element.piece
        couche = "INF" if "inférieur" in element.nom else "SUP"
        numero = element.nom.rsplit(" ", 1)[-1]
        pieces.append(
            PieceDebit(
                reference_bom=f"OSB-{couche}-{numero}",
                designation=element.nom,
                longueur_mm=piece.longueur,
            )
        )
    plan = optimiser_debit(
        pieces,
        longueur_stock_mm=2_500,
        trait_scie_mm=5,
    )
    if plan.nombre_barres != local.nombre_dalles_osb_achetees:
        raise ValueError(
            "le nombre de dalles OSB de la BOM ne correspond pas au plan de débit"
        )
    return plan


def calepinage_fonds_caissons(local: LocalBatteries) -> tuple[int, ...]:
    """Répartit les fonds dans une grille 2D sur les panneaux OSB BD."""
    fonds = [
        element
        for element in local.elements()
        if element.nom.startswith("Fond OSB")
    ]
    if not fonds:
        return ()
    longueur = fonds[0].piece.longueur
    largeur = fonds[0].piece.largeur
    trait_scie = 5
    colonnes = floor((2_800 + trait_scie) / (longueur + trait_scie))
    rangees = floor((1_196 + trait_scie) / (largeur + trait_scie))
    capacite = colonnes * rangees
    nombre_panneaux = ceil(len(fonds) / capacite)
    repartition = tuple(
        min(capacite, len(fonds) - numero * capacite)
        for numero in range(nombre_panneaux)
    )
    if nombre_panneaux != local.plancher.nombre_dalles_brutes_osb_caissons:
        raise ValueError(
            "le nombre de panneaux OSB BD ne correspond pas au calepinage 2D"
        )
    return repartition


def exporter_debit(local: LocalBatteries, lot: str, dossier: Path) -> tuple[Path, ...]:
    if lot != "total":
        return ()
    destination = dossier / "debit_panneaux_total.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    dalle = DalleOSB(
        epaisseur=22,
        largeur=675,
        longueur=2_500,
        type_bords=TypeBordsOSB.RAINURE_LANGUETTE,
    )
    plan = plan_debit_osb(local)
    with destination.open("w", newline="", encoding="utf-8-sig") as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            (
                "reference_achat",
                "panneau",
                "longueur_stock_mm",
                "largeur_stock_mm",
                "coupes_longueur_mm",
                "largeur_decoupes_mm",
                "references_decoupes",
                "nombre_traits",
                "trait_scie_mm",
                "chute_longitudinale_mm",
            )
        )
        for panneau in plan.barres:
            writer.writerow(
                (
                    dalle.article_bom().reference,
                    panneau.numero,
                    f"{panneau.longueur_stock_mm:g}",
                    "675",
                    " + ".join(f"{piece.longueur_mm:g}" for piece in panneau.pieces),
                    "600",
                    " + ".join(piece.reference_bom for piece in panneau.pieces),
                    panneau.nombre_traits,
                    f"{panneau.trait_scie_mm:g}",
                    f"{panneau.chute_mm:g}",
                )
            )

    destination_fonds = dossier / "debit_fonds_caissons_total.csv"
    dalle_contreventement = DalleOSB(
        epaisseur=12,
        largeur=1_196,
        longueur=2_800,
        type_bords=TypeBordsOSB.BORDS_DROITS,
    )
    fonds = [
        element
        for element in local.elements()
        if element.nom.startswith("Fond OSB")
    ]
    longueur_fond = fonds[0].piece.longueur
    largeur_fond = fonds[0].piece.largeur
    repartition_fonds = calepinage_fonds_caissons(local)
    with destination_fonds.open(
        "w", newline="", encoding="utf-8-sig"
    ) as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            (
                "reference_achat",
                "panneau",
                "longueur_stock_mm",
                "largeur_stock_mm",
                "quantite_fonds",
                "longueur_fond_mm",
                "largeur_fond_mm",
                "trait_scie_mm",
                "calepinage",
            )
        )
        for numero, quantite in enumerate(repartition_fonds, start=1):
            writer.writerow(
                (
                    dalle_contreventement.article_bom().reference,
                    numero,
                    "2800",
                    "1196",
                    quantite,
                    f"{longueur_fond:g}",
                    f"{largeur_fond:g}",
                    "5",
                    "grille 4 × 4" if quantite == 16 else "grille 4 × 2",
                )
            )

    destination_isolant = dossier / "debit_isolant_total.csv"
    with destination_isolant.open(
        "w", newline="", encoding="utf-8-sig"
    ) as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            (
                "reference_achat",
                "panneau",
                "quantite_decoupes",
                "longueur_decoupe_mm",
                "largeur_decoupe_mm",
                "epaisseur_mm",
                "calepinage",
            )
        )
        for numero in range(1, local.nombre_panneaux_isolant_achetes + 1):
            writer.writerow(
                (
                    "ISOL-ISONAT-FLEX55-145x580x1220",
                    numero,
                    4,
                    "607.5",
                    "278.8",
                    "145",
                    "grille 2 × 2, surcote de compression incluse",
                )
            )
    return (
        destination,
        destination_fonds,
        destination_isolant,
    )
