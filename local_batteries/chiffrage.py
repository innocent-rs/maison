"""Chiffrage reproductible et comparatif des deux planchers du local."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from catalogues.prix import TARIFS
from home_framework.chiffrage import Chiffrage, ModeTarification

from .modele import creer_local_batteries, creer_local_batteries_renforce


def _euros(valeur: Decimal) -> str:
    return f"{valeur:.2f}".replace(".", ",")


@dataclass(frozen=True, slots=True)
class AchatCompare:
    reference: str
    designation: str
    quantite_renforcee: str
    quantite_optimisee: str
    cout_renforce_ttc_eur: Decimal
    cout_optimise_ttc_eur: Decimal

    @property
    def economie_ttc_eur(self) -> Decimal:
        return self.cout_renforce_ttc_eur - self.cout_optimise_ttc_eur


@dataclass(frozen=True, slots=True)
class ComparatifCouts:
    renforce: Chiffrage
    optimise: Chiffrage
    plancher_optimise: Chiffrage
    murs: Chiffrage
    achats: tuple[AchatCompare, ...]

    @property
    def economie_ttc_eur(self) -> Decimal:
        return (
            self.renforce.sous_total_renseigne_ttc_eur
            - self.optimise.sous_total_renseigne_ttc_eur
        )

    @property
    def economie_pourcent(self) -> Decimal:
        return self.economie_ttc_eur / self.renforce.sous_total_renseigne_ttc_eur * 100


def _achats_factures(chiffrage: Chiffrage) -> dict[str, tuple[str, str, Decimal]]:
    achats: dict[str, tuple[str, str, Decimal]] = {}
    for plan in chiffrage.plans_debit:
        achats[plan.reference_achat] = (
            plan.tarif.designation_achat,
            f"{plan.plan.nombre_barres} barre(s)",
            plan.cout_ttc_eur or Decimal("0"),
        )
    for ligne in chiffrage.lignes:
        if ligne.est_dans_plan_debit:
            continue
        tarif = ligne.tarif
        nombre = ligne.nombre_conditionnements or 0
        reference = ligne.ligne_bom.article.reference
        designation = ligne.ligne_bom.article.designation
        if tarif and tarif.mode is ModeTarification.LOT_LINEAIRE:
            reference = f"LOT-LINEAIRE:{tarif.url or tarif.conditionnement}"
            designation = "Tasseau Douglas 60 × 40 mm"
        achats[reference] = (
            designation,
            f"{nombre} {tarif.conditionnement if tarif else 'pièce(s)'}",
            ligne.cout_ttc_eur or Decimal("0"),
        )
    return achats


def comparer_couts() -> ComparatifCouts:
    """Compare l'ancien châssis renforcé au modèle simple devenu courant."""
    local_renforce = creer_local_batteries_renforce()
    local_optimise = creer_local_batteries()
    renforce = Chiffrage(
        "local_batteries_renforce",
        local_renforce.nomenclature_achats(),
        TARIFS,
    )
    optimise = Chiffrage(
        "local_batteries_optimise",
        local_optimise.nomenclature_achats(),
        TARIFS,
    )
    plancher_optimise = Chiffrage(
        "local_batteries_plancher",
        local_optimise.nomenclature_achats_plancher(),
        TARIFS,
    )
    murs = Chiffrage(
        "local_batteries_murs",
        local_optimise.nomenclature_achats_murs(),
        TARIFS,
    )
    anciens = _achats_factures(renforce)
    nouveaux = _achats_factures(optimise)
    achats = []
    for reference in sorted(set(anciens) | set(nouveaux)):
        ancien = anciens.get(reference, (reference, "0", Decimal("0")))
        nouveau = nouveaux.get(reference, (ancien[0], "0", Decimal("0")))
        ligne = AchatCompare(
            reference,
            nouveau[0] if reference in nouveaux else ancien[0],
            ancien[1],
            nouveau[1],
            ancien[2],
            nouveau[2],
        )
        if ligne.cout_renforce_ttc_eur != ligne.cout_optimise_ttc_eur:
            achats.append(ligne)
    return ComparatifCouts(
        renforce,
        optimise,
        plancher_optimise,
        murs,
        tuple(achats),
    )


def exporter_comparatif(
    destination: Path = Path("build/local_batteries/comparatif_couts.md"),
) -> Path:
    """Écrit les deux CSV complets et une synthèse lisible en Markdown."""
    comparatif = comparer_couts()
    destination.parent.mkdir(parents=True, exist_ok=True)
    comparatif.renforce.ecrire_csv(destination.parent / "chiffrage_renforce.csv")
    comparatif.optimise.ecrire_csv(destination.parent / "chiffrage_optimise.csv")
    lignes = [
        "# Local batteries — comparaison de coût",
        "",
        "Prix TTC de fourniture, hors livraison, main-d’œuvre, fondations, "
        "toiture, porte, bardage et équipements électriques.",
        "",
        "| Variante | Total TTC |",
        "|---|---:|",
        (
            "| Ancienne grille renforcée | "
            f"{_euros(comparatif.renforce.sous_total_renseigne_ttc_eur)} € |"
        ),
        (
            "| Plancher simple optimisé | "
            f"{_euros(comparatif.optimise.sous_total_renseigne_ttc_eur)} € |"
        ),
        (
            "| **Économie** | "
            f"**{_euros(comparatif.economie_ttc_eur)} € "
            f"({str(round(comparatif.economie_pourcent, 1)).replace('.', ',')} %)** |"
        ),
        "",
        "## Répartition de la variante retenue",
        "",
        "| Lot | Total TTC |",
        "|---|---:|",
        (
            "| Plancher complet | "
            f"{_euros(comparatif.plancher_optimise.sous_total_renseigne_ttc_eur)} € |"
        ),
        (
            "| Murs complets | "
            f"{_euros(comparatif.murs.sous_total_renseigne_ttc_eur)} € |"
        ),
        "",
        "## Achats modifiés par l'optimisation",
        "",
        "| Achat modifié | Avant | Après | Économie TTC |",
        "|---|---:|---:|---:|",
    ]
    lignes.extend(
        f"| {achat.designation} | {achat.quantite_renforcee} | "
        f"{achat.quantite_optimisee} | {_euros(achat.economie_ttc_eur)} € |"
        for achat in comparatif.achats
    )
    lignes.extend(
        (
            "",
            "Le total est calculé à partir de la BOM d’achat, des "
            "conditionnements entiers et des plans de débit. Un prix manquant "
            "reste explicitement manquant et ne devient jamais zéro.",
        )
    )
    destination.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    destination = exporter_comparatif()
    comparatif = comparer_couts()
    print(
        f"Local optimisé : {comparatif.optimise.sous_total_renseigne_ttc_eur:.2f} € TTC"
    )
    print(
        f"Économie : {comparatif.economie_ttc_eur:.2f} € TTC "
        f"({comparatif.economie_pourcent:.1f} %)"
    )
    print(f"Comparatif : {destination}")


if __name__ == "__main__":
    main()
