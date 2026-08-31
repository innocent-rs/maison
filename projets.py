"""Registre des projets consommés par les outils communs de coût et débit."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atelier_mob import creer_atelier_mob
from local_batteries import creer_local_batteries
from local_batteries.debit import exporter_debit, lignes_resume_debit
from main import make_part
from maison.debit import lignes_resume_panneaux_osb
from home_framework.nomenclature import Nomenclature


FabriqueProjet = Callable[[], Any]
FabriqueNomenclature = Callable[[Any], Nomenclature]
ResumeDebit = Callable[[Any, str], tuple[str, ...]]
ExportDebit = Callable[[Any, str, Path], tuple[Path, ...]]


@dataclass(frozen=True, slots=True)
class DefinitionProjet:
    """Adapte un CAD et ses BOM aux outils transversaux du dépôt."""

    identifiant: str
    construire: FabriqueProjet
    lots: Mapping[str, FabriqueNomenclature]
    dossier_sortie: Path
    alias_lots: Mapping[str, str] | None = None
    resumer_debit: ResumeDebit | None = None
    exporter_debit: ExportDebit | None = None

    def lots_demandes(self, nom: str) -> tuple[str, ...]:
        if nom == "tous":
            return tuple(self.lots)
        nom = (self.alias_lots or {}).get(nom, nom)
        if nom not in self.lots:
            disponibles = ", ".join((*self.lots, "tous"))
            raise ValueError(
                f"lot inconnu pour {self.identifiant}: {nom} "
                f"(choix: {disponibles})"
            )
        return (nom,)

    def nomenclature(self, projet: Any, lot: str) -> Nomenclature:
        return self.lots[lot](projet)


PROJETS: dict[str, DefinitionProjet] = {
    "atelier_mob": DefinitionProjet(
        identifiant="atelier_mob",
        construire=creer_atelier_mob,
        lots={
            "fondations": lambda projet: projet.nomenclature_fondations(),
            "plancher": lambda projet: projet.nomenclature_plancher(),
            "total": lambda projet: projet.nomenclature_achats(),
        },
        dossier_sortie=Path("build/atelier_mob"),
    ),
    "maison": DefinitionProjet(
        identifiant="maison",
        construire=make_part,
        lots={
            "plancher": lambda projet: projet.nomenclature_plancher(),
            "charpente": lambda projet: projet.nomenclature_charpente(),
            "total": lambda projet: projet.nomenclature_achats(),
        },
        alias_lots={"a-frame": "charpente"},
        dossier_sortie=Path("build"),
        resumer_debit=lambda projet, lot: (
            lignes_resume_panneaux_osb(projet.plancher)
            if lot in ("plancher", "total")
            else ()
        ),
    ),
    "local_batteries": DefinitionProjet(
        identifiant="local_batteries",
        construire=creer_local_batteries,
        lots={
            "plancher": lambda projet: projet.nomenclature_achats_plancher(),
            "murs": lambda projet: projet.nomenclature_achats_murs(),
            "total": lambda projet: projet.nomenclature_achats(),
        },
        dossier_sortie=Path("build/local_batteries"),
        resumer_debit=lignes_resume_debit,
        exporter_debit=exporter_debit,
    ),
}


def resoudre_projet_et_lot(
    nom_projet: str,
    nom_lot: str,
) -> tuple[DefinitionProjet, str]:
    """Résout la sélection et conserve les anciens raccourcis de ``just``."""
    if nom_projet in PROJETS:
        return PROJETS[nom_projet], nom_lot

    maison = PROJETS["maison"]
    anciens_raccourcis = {*maison.lots, *(maison.alias_lots or {}), "tous"}
    if nom_projet in anciens_raccourcis:
        return maison, nom_projet

    disponibles = ", ".join(PROJETS)
    raise ValueError(f"projet inconnu: {nom_projet} (choix: {disponibles})")
