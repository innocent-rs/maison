"""Chiffrage d'une nomenclature à partir d'une base de tarifs explicite."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import ceil
from pathlib import Path
from typing import Mapping, TextIO

from maison.nomenclature import LigneBOM, Nomenclature
from maison.optimisation import PieceDebit, PlanDebit, optimiser_debit


class ModeTarification(StrEnum):
    CONDITIONNEMENT = "conditionnement"
    BARRE_COMMERCIALE = "barre_commerciale"
    LOT_LINEAIRE = "lot_lineaire"


@dataclass(frozen=True, slots=True)
class Tarif:
    """Prix TTC unitaire d'une référence BOM.

    Le prix représente toujours une unité réellement achetée : une pièce, une
    boîte, une barre commerciale complète ou un lot de longueur minimale. En
    mode ``BARRE_COMMERCIALE``, le nombre de barres est déterminé par le plan de
    débit. Un prix à ``None`` conserve le mode et les informations fournisseur
    sans inclure silencieusement la ligne dans le total.
    """

    prix_unitaire_ttc_eur: Decimal | str | float | None = None
    mode: ModeTarification | str = ModeTarification.CONDITIONNEMENT
    quantite_par_conditionnement: int = 1
    conditionnement: str = "pièce"
    fournisseur: str = ""
    date_tarif: str = ""
    url: str = ""
    note: str = ""
    reference_achat: str = ""
    designation_achat: str = ""
    longueur_commerciale_mm: Decimal | str | float | None = None
    longueur_par_conditionnement_mm: Decimal | str | float | None = None
    trait_scie_mm: Decimal | str | float = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ModeTarification(self.mode))
        if self.quantite_par_conditionnement <= 0:
            raise ValueError("le conditionnement doit contenir au moins une pièce")
        if (
            self.mode is ModeTarification.BARRE_COMMERCIALE
            and self.quantite_par_conditionnement != 1
        ):
            raise ValueError("une barre n'utilise pas de conditionnement")
        if (
            self.mode is ModeTarification.LOT_LINEAIRE
            and self.quantite_par_conditionnement != 1
        ):
            raise ValueError("un lot linéaire est défini par sa longueur")
        if self.prix_unitaire_ttc_eur is not None:
            prix = Decimal(str(self.prix_unitaire_ttc_eur))
            if prix < 0:
                raise ValueError("un prix ne peut pas être négatif")
            object.__setattr__(self, "prix_unitaire_ttc_eur", prix)
        trait_scie = Decimal(str(self.trait_scie_mm))
        if trait_scie < 0:
            raise ValueError("le trait de scie ne peut pas être négatif")
        object.__setattr__(self, "trait_scie_mm", trait_scie)
        if self.longueur_commerciale_mm is not None:
            longueur = Decimal(str(self.longueur_commerciale_mm))
            if longueur <= 0:
                raise ValueError("la longueur commerciale doit être positive")
            object.__setattr__(self, "longueur_commerciale_mm", longueur)
        if self.longueur_par_conditionnement_mm is not None:
            longueur_lot = Decimal(str(self.longueur_par_conditionnement_mm))
            if longueur_lot <= 0:
                raise ValueError("la longueur d'un lot doit être positive")
            object.__setattr__(
                self,
                "longueur_par_conditionnement_mm",
                longueur_lot,
            )
        if self.mode is ModeTarification.BARRE_COMMERCIALE:
            if not self.reference_achat:
                raise ValueError("une barre commerciale exige une référence d'achat")
            if self.longueur_commerciale_mm is None:
                raise ValueError("une barre commerciale exige une longueur de stock")
            if not self.designation_achat:
                object.__setattr__(self, "designation_achat", self.reference_achat)
        if (
            self.mode is ModeTarification.LOT_LINEAIRE
            and self.longueur_par_conditionnement_mm is None
        ):
            raise ValueError("un lot linéaire exige une longueur de conditionnement")

    @classmethod
    def par_conditionnement(
        cls,
        prix_ttc_du_conditionnement: Decimal | str | float | None = None,
        quantite: int = 1,
        conditionnement: str = "pièce",
        **informations,
    ) -> Tarif:
        return cls(
            prix_unitaire_ttc_eur=prix_ttc_du_conditionnement,
            mode=ModeTarification.CONDITIONNEMENT,
            quantite_par_conditionnement=quantite,
            conditionnement=conditionnement,
            **informations,
        )

    @classmethod
    def en_barres(
        cls,
        prix_ttc_par_barre: Decimal | str | float | None,
        *,
        reference_achat: str,
        designation_achat: str,
        longueur_commerciale_mm: Decimal | str | float,
        trait_scie_mm: Decimal | str | float = 0,
        **informations,
    ) -> Tarif:
        """Tarifie des coupes regroupées dans des barres entières optimisées."""
        return cls(
            prix_unitaire_ttc_eur=prix_ttc_par_barre,
            mode=ModeTarification.BARRE_COMMERCIALE,
            conditionnement="barre commerciale",
            reference_achat=reference_achat,
            designation_achat=designation_achat,
            longueur_commerciale_mm=longueur_commerciale_mm,
            trait_scie_mm=trait_scie_mm,
            **informations,
        )

    @classmethod
    def en_lots_lineaires(
        cls,
        prix_ttc_du_lot: Decimal | str | float | None,
        *,
        longueur_du_lot_mm: Decimal | str | float,
        conditionnement: str,
        **informations,
    ) -> Tarif:
        """Tarifie une longueur minimale imposée sans inventer des barres."""
        return cls(
            prix_unitaire_ttc_eur=prix_ttc_du_lot,
            mode=ModeTarification.LOT_LINEAIRE,
            conditionnement=conditionnement,
            longueur_par_conditionnement_mm=longueur_du_lot_mm,
            **informations,
        )

    @property
    def est_renseigne(self) -> bool:
        return self.prix_unitaire_ttc_eur is not None


class CatalogueTarifs(Mapping[str, Tarif]):
    """Catalogue commun mêlant références exactes et familles de coupes.

    Les règles de famille évitent de recopier un tarif pour chaque longueur
    générée par le CAD. Elles sont évaluées uniquement lorsqu'aucune référence
    exacte n'existe.
    """

    def __init__(
        self,
        tarifs_exacts: Mapping[str, Tarif],
        familles: tuple[tuple[str, Tarif], ...] = (),
    ) -> None:
        self._tarifs_exacts = dict(tarifs_exacts)
        self._familles = tuple(
            (re.compile(motif), tarif) for motif, tarif in familles
        )

    def __getitem__(self, reference: str) -> Tarif:
        if reference in self._tarifs_exacts:
            return self._tarifs_exacts[reference]
        correspondances = tuple(
            tarif
            for motif, tarif in self._familles
            if motif.fullmatch(reference)
        )
        if not correspondances:
            raise KeyError(reference)
        if len(correspondances) > 1:
            raise ValueError(
                f"plusieurs familles de tarifs correspondent à {reference}"
            )
        return correspondances[0]

    def __iter__(self) -> Iterator[str]:
        return iter(self._tarifs_exacts)

    def __len__(self) -> int:
        return len(self._tarifs_exacts)


@dataclass(frozen=True, slots=True)
class LigneChiffrage:
    lot: str
    ligne_bom: LigneBOM
    tarif: Tarif | None

    @property
    def nombre_conditionnements(self) -> int | None:
        if self.tarif and self.tarif.mode is ModeTarification.BARRE_COMMERCIALE:
            return None
        if self.tarif and self.tarif.mode is ModeTarification.LOT_LINEAIRE:
            longueur_totale = self.ligne_bom.longueur_totale_mm
            if longueur_totale is None:
                raise ValueError(
                    f"{self.ligne_bom.article.reference} n'a pas de longueur "
                    "pour être acheté en lot linéaire"
                )
            assert self.tarif.longueur_par_conditionnement_mm is not None
            return ceil(
                Decimal(str(longueur_totale))
                / self.tarif.longueur_par_conditionnement_mm
            )
        quantite_par_lot = (
            self.tarif.quantite_par_conditionnement if self.tarif else 1
        )
        return ceil(self.ligne_bom.quantite / quantite_par_lot)

    @property
    def quantite_facturee(self) -> Decimal:
        if self.est_dans_plan_debit:
            raise ValueError(
                "la quantité facturée est portée par le plan de débit groupé"
            )
        assert self.nombre_conditionnements is not None
        return Decimal(self.nombre_conditionnements)

    @property
    def unite_facturation(self) -> str:
        if self.est_dans_plan_debit:
            return "plan de débit"
        return self.tarif.conditionnement if self.tarif else "pièce"

    @property
    def cout_ttc_eur(self) -> Decimal | None:
        if (
            self.tarif is None
            or not self.tarif.est_renseigne
            or self.est_dans_plan_debit
        ):
            return None
        assert self.tarif.prix_unitaire_ttc_eur is not None
        return self.tarif.prix_unitaire_ttc_eur * self.quantite_facturee

    @property
    def longueur_utile_m(self) -> Decimal | None:
        longueur = self.ligne_bom.longueur_totale_mm
        if longueur is None:
            return None
        return Decimal(str(longueur)) / Decimal("1000")

    @property
    def longueur_achetee_m(self) -> Decimal | None:
        if not self.tarif or self.tarif.mode is not ModeTarification.LOT_LINEAIRE:
            return None
        assert self.tarif.longueur_par_conditionnement_mm is not None
        assert self.nombre_conditionnements is not None
        return (
            self.tarif.longueur_par_conditionnement_mm
            * self.nombre_conditionnements
            / Decimal("1000")
        )

    @property
    def est_dans_plan_debit(self) -> bool:
        return bool(
            self.tarif
            and self.tarif.mode is ModeTarification.BARRE_COMMERCIALE
        )


@dataclass(frozen=True, slots=True)
class PlanDebitChiffre:
    """Plan de débit et coût d'achat de ses barres commerciales."""

    lot: str
    tarif: Tarif
    plan: PlanDebit

    @property
    def reference_achat(self) -> str:
        return self.tarif.reference_achat

    @property
    def longueur_achetee_m(self) -> Decimal:
        return self.plan.longueur_achetee_mm / Decimal("1000")

    @property
    def cout_ttc_eur(self) -> Decimal | None:
        if not self.tarif.est_renseigne:
            return None
        assert self.tarif.prix_unitaire_ttc_eur is not None
        return self.tarif.prix_unitaire_ttc_eur * self.plan.nombre_barres


class Chiffrage:
    """Vue chiffrée d'un lot, avec détection des tarifs manquants."""

    def __init__(
        self,
        lot: str,
        nomenclature: Nomenclature,
        tarifs: Mapping[str, Tarif],
    ) -> None:
        self.lot = lot
        self._lignes = tuple(
            LigneChiffrage(lot, ligne, tarifs.get(ligne.article.reference))
            for ligne in nomenclature.lignes
        )
        self._plans_debit = self._construire_plans_debit()

    def _construire_plans_debit(self) -> tuple[PlanDebitChiffre, ...]:
        groupes: dict[str, tuple[Tarif, list[PieceDebit]]] = {}
        for ligne in self.lignes:
            tarif = ligne.tarif
            if not ligne.est_dans_plan_debit or tarif is None:
                continue
            longueur = ligne.ligne_bom.article.longueur_mm
            if longueur is None:
                raise ValueError(
                    f"{ligne.ligne_bom.article.reference} n'a pas de longueur "
                    "pour être débité dans une barre"
                )
            if tarif.reference_achat in groupes:
                tarif_groupe, pieces = groupes[tarif.reference_achat]
                if tarif != tarif_groupe:
                    raise ValueError(
                        f"configuration incohérente pour {tarif.reference_achat}"
                    )
            else:
                pieces = []
                groupes[tarif.reference_achat] = (tarif, pieces)
            pieces.extend(
                PieceDebit(
                    reference_bom=ligne.ligne_bom.article.reference,
                    designation=ligne.ligne_bom.article.designation,
                    longueur_mm=longueur,
                )
                for _ in range(ligne.ligne_bom.quantite)
            )

        plans = []
        for reference in sorted(groupes):
            tarif, pieces = groupes[reference]
            assert tarif.longueur_commerciale_mm is not None
            plan = optimiser_debit(
                pieces,
                longueur_stock_mm=tarif.longueur_commerciale_mm,
                trait_scie_mm=tarif.trait_scie_mm,
            )
            plans.append(PlanDebitChiffre(self.lot, tarif, plan))
        return tuple(plans)

    @property
    def lignes(self) -> tuple[LigneChiffrage, ...]:
        return self._lignes

    @property
    def plans_debit(self) -> tuple[PlanDebitChiffre, ...]:
        return self._plans_debit

    @property
    def references_manquantes(self) -> tuple[str, ...]:
        return tuple(
            ligne.ligne_bom.article.reference
            for ligne in self.lignes
            if ligne.tarif is None or not ligne.tarif.est_renseigne
        )

    @property
    def est_complet(self) -> bool:
        return not self.references_manquantes

    @property
    def est_vide(self) -> bool:
        return not self.lignes

    @property
    def sous_total_renseigne_ttc_eur(self) -> Decimal:
        couts_directs = sum(
            (
                ligne.cout_ttc_eur
                for ligne in self.lignes
                if ligne.cout_ttc_eur is not None
            ),
            start=Decimal("0"),
        )
        couts_barres = sum(
            (
                plan.cout_ttc_eur
                for plan in self.plans_debit
                if plan.cout_ttc_eur is not None
            ),
            start=Decimal("0"),
        )
        return couts_directs + couts_barres

    def ecrire_csv(self, destination: str | Path | TextIO) -> None:
        """Exporte les quantités, conditionnements et coûts en CSV français."""
        doit_fermer = not hasattr(destination, "write")
        fichier = (
            Path(destination).open("w", newline="", encoding="utf-8-sig")
            if doit_fermer
            else destination
        )
        try:
            writer = csv.writer(fichier, delimiter=";")
            writer.writerow(
                (
                    "lot",
                    "reference",
                    "categorie",
                    "designation",
                    "quantite_bom",
                    "longueur_totale_m",
                    "mode_tarification",
                    "quantite_par_conditionnement",
                    "longueur_unite_achat_m",
                    "nombre_conditionnements",
                    "quantite_facturee",
                    "longueur_achetee_m",
                    "unite_facturation",
                    "prix_unitaire_ttc_eur",
                    "cout_ttc_eur",
                    "fournisseur",
                    "date_tarif",
                    "url",
                    "note",
                    "statut",
                )
            )
            for ligne in self.lignes:
                article = ligne.ligne_bom.article
                tarif = ligne.tarif
                dans_plan = ligne.est_dans_plan_debit
                writer.writerow(
                    (
                        ligne.lot,
                        article.reference,
                        article.categorie,
                        article.designation,
                        ligne.ligne_bom.quantite,
                        _nombre_divise(
                            ligne.ligne_bom.longueur_totale_mm,
                            Decimal("1000"),
                        ),
                        tarif.mode.value if tarif else "conditionnement",
                        tarif.quantite_par_conditionnement if tarif else 1,
                        _nombre_divise(
                            (
                                tarif.longueur_par_conditionnement_mm
                                if tarif
                                and tarif.mode is ModeTarification.LOT_LINEAIRE
                                else None
                            ),
                            Decimal("1000"),
                        ),
                        "" if dans_plan else ligne.nombre_conditionnements or "",
                        "" if dans_plan else _nombre(ligne.quantite_facturee),
                        "" if dans_plan else _nombre_optionnel(ligne.longueur_achetee_m),
                        ligne.unite_facturation,
                        _euros(tarif.prix_unitaire_ttc_eur if tarif else None),
                        _euros(ligne.cout_ttc_eur),
                        tarif.fournisseur if tarif else "",
                        tarif.date_tarif if tarif else "",
                        tarif.url if tarif else "",
                        tarif.note if tarif else "",
                        (
                            "PLAN DE DÉBIT"
                            if dans_plan and tarif and tarif.est_renseigne
                            else "chiffré"
                            if ligne.cout_ttc_eur is not None
                            else "À RENSEIGNER"
                        ),
                    )
                )
            for plan_chiffre in self.plans_debit:
                tarif = plan_chiffre.tarif
                plan = plan_chiffre.plan
                writer.writerow(
                    (
                        self.lot,
                        plan_chiffre.reference_achat,
                        "Achat / barre commerciale",
                        tarif.designation_achat,
                        plan.nombre_barres,
                        _nombre_divise(
                            plan.longueur_achetee_mm,
                            Decimal("1000"),
                        ),
                        ModeTarification.BARRE_COMMERCIALE.value,
                        1,
                        _nombre_divise(
                            tarif.longueur_commerciale_mm,
                            Decimal("1000"),
                        ),
                        plan.nombre_barres,
                        plan.nombre_barres,
                        _nombre_divise(
                            plan.longueur_achetee_mm,
                            Decimal("1000"),
                        ),
                        "barre",
                        _euros(tarif.prix_unitaire_ttc_eur),
                        _euros(plan_chiffre.cout_ttc_eur),
                        tarif.fournisseur,
                        tarif.date_tarif,
                        tarif.url,
                        (
                            f"{plan.nombre_pieces} pièces ; "
                            f"{_nombre(plan.chute_totale_mm)} mm de chute ; "
                            f"rendement {_pourcentage(plan.taux_utilisation)}"
                        ),
                        "chiffré" if plan_chiffre.cout_ttc_eur is not None else "À RENSEIGNER",
                    )
                )
            writer.writerow(())
            writer.writerow(
                (
                    self.lot,
                    "SOUS-TOTAL-RENSEIGNE",
                    "",
                    "Sous-total TTC des seules lignes renseignées",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    _euros(self.sous_total_renseigne_ttc_eur),
                    "",
                    "",
                    "",
                    "",
                    (
                        "AUCUN ARTICLE"
                        if self.est_vide
                        else "COMPLET" if self.est_complet else "INCOMPLET"
                    ),
                )
            )
        finally:
            if doit_fermer:
                fichier.close()

    def ecrire_debits_csv(self, destination: str | Path | TextIO) -> None:
        """Exporte une ligne par barre avec les coupes et la chute restante."""
        doit_fermer = not hasattr(destination, "write")
        fichier = (
            Path(destination).open("w", newline="", encoding="utf-8-sig")
            if doit_fermer
            else destination
        )
        try:
            writer = csv.writer(fichier, delimiter=";")
            writer.writerow(
                (
                    "lot",
                    "reference_achat",
                    "barre",
                    "longueur_stock_mm",
                    "coupes_mm",
                    "references_bom",
                    "longueur_pieces_mm",
                    "nombre_traits",
                    "trait_scie_mm",
                    "longueur_traits_mm",
                    "chute_mm",
                    "taux_utilisation",
                )
            )
            for plan_chiffre in self.plans_debit:
                for barre in plan_chiffre.plan.barres:
                    writer.writerow(
                        (
                            self.lot,
                            plan_chiffre.reference_achat,
                            barre.numero,
                            _nombre(barre.longueur_stock_mm),
                            " + ".join(
                                _nombre(piece.longueur_mm)
                                for piece in barre.pieces
                            ),
                            " + ".join(
                                piece.reference_bom for piece in barre.pieces
                            ),
                            _nombre(barre.longueur_pieces_mm),
                            barre.nombre_traits,
                            _nombre(barre.trait_scie_mm),
                            _nombre(barre.longueur_traits_mm),
                            _nombre(barre.chute_mm),
                            _pourcentage(
                                barre.longueur_pieces_mm
                                / barre.longueur_stock_mm
                            ),
                        )
                    )
        finally:
            if doit_fermer:
                fichier.close()


def _euros(valeur: Decimal | str | float | None) -> str:
    if valeur is None:
        return ""
    return f"{Decimal(str(valeur)):.2f}"


def _nombre(valeur: Decimal | int | float) -> str:
    texte = f"{Decimal(str(valeur)):f}"
    return texte.rstrip("0").rstrip(".") if "." in texte else texte


def _nombre_divise(
    valeur: Decimal | float | None,
    diviseur: Decimal,
) -> str:
    if valeur is None:
        return ""
    return _nombre(Decimal(str(valeur)) / diviseur)


def _nombre_optionnel(valeur: Decimal | None) -> str:
    return "" if valeur is None else _nombre(valeur)


def _pourcentage(valeur: Decimal) -> str:
    return f"{valeur * Decimal('100'):.2f} %"
