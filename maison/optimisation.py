"""Optimisation des débits dans des barres commerciales de longueur fixe."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import ceil
from typing import Iterable


def _decimal(valeur: Decimal | str | float | int) -> Decimal:
    return Decimal(str(valeur))


@dataclass(frozen=True, slots=True)
class PieceDebit:
    """Une pièce demandée par la BOM avant débit du produit commercial."""

    reference_bom: str
    designation: str
    longueur_mm: Decimal | str | float

    def __post_init__(self) -> None:
        longueur = _decimal(self.longueur_mm)
        if longueur <= 0:
            raise ValueError("la longueur d'une pièce à débiter doit être positive")
        object.__setattr__(self, "longueur_mm", longueur)


@dataclass(frozen=True, slots=True)
class BarreDebit:
    """Répartition des pièces dans une barre commerciale."""

    numero: int
    longueur_stock_mm: Decimal
    trait_scie_mm: Decimal
    pieces: tuple[PieceDebit, ...]

    @property
    def longueur_pieces_mm(self) -> Decimal:
        return sum(
            (piece.longueur_mm for piece in self.pieces),
            start=Decimal("0"),
        )

    @property
    def nombre_traits(self) -> int:
        return max(0, len(self.pieces) - 1)

    @property
    def longueur_traits_mm(self) -> Decimal:
        return self.trait_scie_mm * self.nombre_traits

    @property
    def longueur_consommee_mm(self) -> Decimal:
        return self.longueur_pieces_mm + self.longueur_traits_mm

    @property
    def chute_mm(self) -> Decimal:
        return self.longueur_stock_mm - self.longueur_consommee_mm


@dataclass(frozen=True, slots=True)
class PlanDebit:
    """Plan optimal pour un produit disponible dans une longueur fixe."""

    longueur_stock_mm: Decimal
    trait_scie_mm: Decimal
    barres: tuple[BarreDebit, ...]

    @property
    def nombre_barres(self) -> int:
        return len(self.barres)

    @property
    def nombre_pieces(self) -> int:
        return sum(len(barre.pieces) for barre in self.barres)

    @property
    def longueur_utile_mm(self) -> Decimal:
        return sum(
            (barre.longueur_pieces_mm for barre in self.barres),
            start=Decimal("0"),
        )

    @property
    def longueur_achetee_mm(self) -> Decimal:
        return self.longueur_stock_mm * self.nombre_barres

    @property
    def longueur_traits_mm(self) -> Decimal:
        return sum(
            (barre.longueur_traits_mm for barre in self.barres),
            start=Decimal("0"),
        )

    @property
    def chute_totale_mm(self) -> Decimal:
        return sum(
            (barre.chute_mm for barre in self.barres),
            start=Decimal("0"),
        )

    @property
    def taux_utilisation(self) -> Decimal:
        if not self.longueur_achetee_mm:
            return Decimal("0")
        return self.longueur_utile_mm / self.longueur_achetee_mm


def optimiser_debit(
    pieces: Iterable[PieceDebit],
    longueur_stock_mm: Decimal | str | float,
    trait_scie_mm: Decimal | str | float = 0,
) -> PlanDebit:
    """Minimise exactement le nombre de barres commerciales identiques.

    Le trait de scie est compté entre deux pièces adjacentes. Le problème est
    transformé en bin packing classique en ajoutant un trait à chaque pièce et
    à la capacité de chaque barre.
    """

    longueur_stock = _decimal(longueur_stock_mm)
    trait_scie = _decimal(trait_scie_mm)
    if longueur_stock <= 0:
        raise ValueError("la longueur commerciale doit être positive")
    if trait_scie < 0:
        raise ValueError("le trait de scie ne peut pas être négatif")

    pieces_triees = tuple(
        sorted(
            pieces,
            key=lambda piece: (piece.longueur_mm, piece.reference_bom),
            reverse=True,
        )
    )
    if not pieces_triees:
        return PlanDebit(longueur_stock, trait_scie, ())
    trop_longues = [
        piece for piece in pieces_triees if piece.longueur_mm > longueur_stock
    ]
    if trop_longues:
        piece = trop_longues[0]
        raise ValueError(
            f"{piece.reference_bom} ({piece.longueur_mm} mm) dépasse la "
            f"longueur commerciale de {longueur_stock} mm"
        )

    capacite = longueur_stock + trait_scie
    longueurs_effectives = tuple(
        piece.longueur_mm + trait_scie for piece in pieces_triees
    )
    borne_basse = ceil(sum(longueurs_effectives, Decimal("0")) / capacite)

    for nombre_barres in range(borne_basse, len(pieces_triees) + 1):
        contenu: list[list[PieceDebit]] = [[] for _ in range(nombre_barres)]
        capacites_restantes = [capacite for _ in range(nombre_barres)]

        def placer(index: int) -> bool:
            if index == len(pieces_triees):
                return True

            piece = pieces_triees[index]
            longueur = longueurs_effectives[index]
            capacites_vues: set[Decimal] = set()
            candidats = sorted(
                range(nombre_barres),
                key=lambda numero: capacites_restantes[numero] - longueur,
            )
            for numero in candidats:
                restante = capacites_restantes[numero]
                if restante < longueur or restante in capacites_vues:
                    continue
                capacites_vues.add(restante)
                contenu[numero].append(piece)
                capacites_restantes[numero] -= longueur
                if placer(index + 1):
                    return True
                capacites_restantes[numero] += longueur
                contenu[numero].pop()
                if restante == capacite:
                    break
            return False

        if placer(0):
            barres = tuple(
                BarreDebit(
                    numero=index,
                    longueur_stock_mm=longueur_stock,
                    trait_scie_mm=trait_scie,
                    pieces=tuple(pieces_barre),
                )
                for index, pieces_barre in enumerate(
                    (pieces_barre for pieces_barre in contenu if pieces_barre),
                    start=1,
                )
            )
            return PlanDebit(longueur_stock, trait_scie, barres)

    raise RuntimeError("aucun plan de débit trouvé")
