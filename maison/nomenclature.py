"""Nomenclature (BOM) extensible des composants de la maison."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, TextIO


@dataclass(frozen=True, slots=True)
class ArticleBOM:
    """Article unitaire pouvant être regroupé dans une nomenclature."""

    reference: str
    designation: str
    categorie: str
    materiau: str
    longueur_mm: float | None = None
    largeur_mm: float | None = None
    hauteur_mm: float | None = None
    volume_mm3: float | None = None


class Nomenclaturable(Protocol):
    """Interface minimale à implémenter par toute future pièce."""

    def article_bom(self) -> ArticleBOM: ...


@dataclass(frozen=True, slots=True)
class LigneBOM:
    article: ArticleBOM
    quantite: int

    @property
    def longueur_totale_mm(self) -> float | None:
        if self.article.longueur_mm is None:
            return None
        return self.article.longueur_mm * self.quantite

    @property
    def volume_total_mm3(self) -> float | None:
        if self.article.volume_mm3 is None:
            return None
        return self.article.volume_mm3 * self.quantite


class Nomenclature:
    """Regroupe les articles identiques et exporte un BOM exploitable."""

    def __init__(self, pieces: Iterable[Nomenclaturable] = ()) -> None:
        articles: dict[ArticleBOM, int] = {}
        for piece in pieces:
            article = piece.article_bom()
            articles[article] = articles.get(article, 0) + 1
        self._lignes = tuple(
            LigneBOM(article, quantite)
            for article, quantite in sorted(
                articles.items(), key=lambda item: item[0].reference
            )
        )

    @property
    def lignes(self) -> tuple[LigneBOM, ...]:
        return self._lignes

    @property
    def nombre_pieces(self) -> int:
        return sum(ligne.quantite for ligne in self.lignes)

    def ecrire_csv(self, destination: str | Path | TextIO) -> None:
        """Exporte un CSV français, directement importable dans un tableur."""
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
                    "reference",
                    "categorie",
                    "designation",
                    "materiau",
                    "quantite",
                    "longueur_unitaire_mm",
                    "largeur_mm",
                    "hauteur_mm",
                    "longueur_totale_m",
                    "volume_unitaire_m3",
                    "volume_total_m3",
                )
            )
            for ligne in self.lignes:
                article = ligne.article
                writer.writerow(
                    (
                        article.reference,
                        article.categorie,
                        article.designation,
                        article.materiau,
                        ligne.quantite,
                        _nombre(article.longueur_mm),
                        _nombre(article.largeur_mm),
                        _nombre(article.hauteur_mm),
                        _nombre_divise(ligne.longueur_totale_mm, 1_000),
                        _nombre_divise(article.volume_mm3, 1_000_000_000),
                        _nombre_divise(ligne.volume_total_mm3, 1_000_000_000),
                    )
                )
        finally:
            if doit_fermer:
                fichier.close()


def _nombre(valeur: float | None) -> str:
    return "" if valeur is None else f"{valeur:.3f}".rstrip("0").rstrip(".")


def _nombre_divise(valeur: float | None, diviseur: float) -> str:
    return "" if valeur is None else f"{valeur / diviseur:.6f}".rstrip("0").rstrip(".")
