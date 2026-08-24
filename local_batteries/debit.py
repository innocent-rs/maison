"""Débit spécifique des panneaux du local batteries."""

import csv
from collections import Counter
from math import ceil, floor
from pathlib import Path

from home_framework.optimisation import PieceDebit, PlanDebit, optimiser_debit
from home_framework.structure import DalleOSB, TypeBordsOSB

from .modele import LocalBatteries


def lots_decoupes_osb(
    local: LocalBatteries,
) -> tuple[tuple[str, float, float, float, str, int], ...]:
    """Regroupe les découpes par couche, format et orientation de pose."""
    lots: Counter[tuple[str, float, float, float, str]] = Counter()
    for element in local.elements():
        if not element.nom.startswith("OSB porteur"):
            continue
        couche = "porteuse"
        orientation = "X"
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
        f"{local.plancher.nombre_dalles_brutes_osb_caissons + local.murs.nombre_panneaux_osb_achetes} "
        "panneau(x) brut(s)"
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
    lots_murs: Counter[tuple[float, float]] = Counter()
    for element in local.murs.elements():
        if " OSB " in element.nom:
            lots_murs[(element.piece.largeur, element.piece.hauteur)] += 1
    for (largeur, hauteur), quantite in sorted(lots_murs.items()):
        lignes.append(
            f"  {quantite} × {largeur:g} × {hauteur:g} mm — voile OSB des murs"
        )
    lignes.append(
        "ISOL-ISONAT-FLEX55-145x580x1220 : "
        f"{local.nombre_panneaux_isolant_achetes + local.murs.nombre_panneaux_isolant_achetes} "
        "panneau(x) brut(s)"
    )
    lignes.append("  plancher : 10 panneaux — 40 découpes de 607,5 × 278,8 mm")
    lignes.append("  murs : 37 panneaux — 48 découpes, selon CSV spécifique")
    return tuple(lignes)


def calepinage_osb_murs(
    local: LocalBatteries,
) -> tuple[tuple[str, tuple[tuple[float, float, str], ...]], ...]:
    """Affecte les seize découpes murales à dix panneaux OSB bruts."""
    hauteur = local.murs.hauteur_ossature
    haut_porte = hauteur - local.murs.hauteur_porte_tableau
    plan = (
        ("Mur arrière 1", ((1_196.0, hauteur, "ARR-1"),)),
        ("Mur arrière 2", ((1_196.0, hauteur, "ARR-2"),)),
        (
            "Mur arrière 3 + mur droit 3 + porte",
            (
                (608.0, hauteur, "ARR-3"),
                (304.0, hauteur, "DRO-3"),
                (225.0, haut_porte, "PORTE-HAUT-1"),
                (225.0, haut_porte, "PORTE-HAUT-2"),
                (225.0, haut_porte, "PORTE-HAUT-3"),
                (225.0, haut_porte, "PORTE-HAUT-4"),
            ),
        ),
        ("Mur gauche 1", ((1_196.0, hauteur, "GAU-1"),)),
        ("Mur gauche 2", ((1_196.0, hauteur, "GAU-2"),)),
        (
            "Mur gauche 3 + mur droit 4",
            ((608.0, hauteur, "GAU-3"), (304.0, hauteur, "DRO-4")),
        ),
        ("Mur droit 1", ((1_196.0, hauteur, "DRO-1"),)),
        ("Mur droit 2", ((1_196.0, hauteur, "DRO-2"),)),
        ("Façade porte gauche", ((1_050.0, hauteur, "PORTE-G"),)),
        ("Façade porte droite", ((1_050.0, hauteur, "PORTE-D"),)),
    )
    if len(plan) != local.murs.nombre_panneaux_osb_achetes:
        raise ValueError("le calepinage OSB des murs ne correspond pas à la BOM")
    return plan


def plan_debit_osb(local: LocalBatteries) -> PlanDebit:
    """Optimise les coupes de 600 mm de large dans la longueur des dalles."""
    pieces = []
    for element in local.elements():
        if not element.nom.startswith("OSB porteur"):
            continue
        piece = element.piece
        numero = element.nom.rsplit(" ", 1)[-1]
        pieces.append(
            PieceDebit(
                reference_bom=f"OSB-PORTEUR-{numero}",
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

    destination_osb_murs = dossier / "debit_osb_murs_total.csv"
    with destination_osb_murs.open(
        "w", newline="", encoding="utf-8-sig"
    ) as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            (
                "reference_achat",
                "panneau",
                "affectation",
                "decoupes_largeur_x_hauteur_mm",
                "references_decoupes",
                "trait_scie_mm",
                "calepinage",
            )
        )
        for numero, (affectation, decoupes) in enumerate(
            calepinage_osb_murs(local), start=1
        ):
            writer.writerow(
                (
                    dalle_contreventement.article_bom().reference,
                    numero,
                    affectation,
                    " + ".join(
                        f"{largeur:g} × {hauteur:g}"
                        for largeur, hauteur, _ in decoupes
                    ),
                    " + ".join(reference for _, _, reference in decoupes),
                    "5",
                    (
                        "bandes 608 + 304 en hauteur ; quatre coupes de porte "
                        "superposées dans la bande de 274 mm"
                        if numero == 3
                        else "bandes verticales"
                    ),
                )
            )

    destination_isolant = dossier / "debit_isolant_plancher_total.csv"
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

    destination_isolant_murs = dossier / "debit_isolant_murs_total.csv"
    decoupes_isolant = []
    for element in local.murs.elements():
        if " isolant " not in element.nom:
            continue
        piece = element.piece
        decoupes_isolant.append(
            (
                element.nom,
                piece.largeur_decoupe,
                piece.hauteur_decoupe,
            )
        )
    with destination_isolant_murs.open(
        "w", newline="", encoding="utf-8-sig"
    ) as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            (
                "reference_achat",
                "panneau",
                "quantite_decoupes",
                "largeur_decoupe_mm",
                "hauteur_decoupe_mm",
                "references_decoupes",
                "calepinage",
            )
        )
        par_nom = {decoupe[0]: decoupe for decoupe in decoupes_isolant}
        noms_groupes = {
            f"Mur droit isolant {rangee}.{index}"
            for rangee in (1, 2)
            for index in (5, 6)
        }
        noms_groupes.update(
            nom
            for nom, _, _ in decoupes_isolant
            if nom.startswith("Façade porte isolant")
        )
        groupes: list[tuple[tuple[str, float, float], ...]] = [
            (decoupe,)
            for decoupe in decoupes_isolant
            if decoupe[0] not in noms_groupes
        ]
        for rangee in (1, 2):
            groupes.append(
                (
                    par_nom[f"Mur droit isolant {rangee}.5"],
                    par_nom[f"Mur droit isolant {rangee}.6"],
                )
            )
        decoupes_etroites = [
            decoupe
            for decoupe in decoupes_isolant
            if decoupe[0].startswith("Façade porte isolant ")
            and "haut" not in decoupe[0]
        ]
        groupes.extend(
            tuple(decoupes_etroites[index : index + 2])
            for index in range(0, len(decoupes_etroites), 2)
        )
        groupes.append(
            tuple(
                decoupe
                for decoupe in decoupes_isolant
                if decoupe[0].startswith("Façade porte isolant haut")
            )
        )

        for numero_panneau, groupe in enumerate(groupes, start=1):
            writer.writerow(
                (
                    "ISOL-ISONAT-FLEX55-145x580x1220",
                    numero_panneau,
                    len(groupe),
                    " + ".join(f"{largeur:g}" for _, largeur, _ in groupe),
                    " + ".join(f"{hauteur:g}" for _, _, hauteur in groupe),
                    " + ".join(nom for nom, _, _ in groupe),
                    "découpes regroupées dans un panneau",
                )
            )
        if len(groupes) != local.murs.nombre_panneaux_isolant_achetes:
            raise ValueError("le débit isolant des murs ne correspond pas à la BOM")
    return (
        destination,
        destination_fonds,
        destination_osb_murs,
        destination_isolant,
        destination_isolant_murs,
    )
