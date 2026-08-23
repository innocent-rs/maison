"""Agrégation des sous-ensembles de la maison."""

from dataclasses import dataclass

from maison.nomenclature import Nomenclature
from maison.structure.charpente import CharpenteAFrame
from maison.structure.plancher import PlancherAFrame


@dataclass(frozen=True, slots=True)
class MaisonAFrame:
    plancher: PlancherAFrame
    charpente: CharpenteAFrame
    inclure_charpente: bool = True

    @property
    def geometrie(self):
        return self.plancher.geometrie

    def elements(self):
        elements = list(self.plancher.elements())
        if self.inclure_charpente:
            elements.extend(self.charpente.elements())
        return elements

    def nomenclature(self) -> Nomenclature:
        pieces = list(self.plancher.pieces_bom())
        if self.inclure_charpente:
            pieces.extend(self.charpente.elements())
        return Nomenclature(pieces)

    def nomenclature_plancher(self) -> Nomenclature:
        return self.plancher.nomenclature_achats()

    def nomenclature_charpente(self) -> Nomenclature:
        return Nomenclature(
            self.charpente.elements() if self.inclure_charpente else ()
        )

    def nomenclature_achats(self) -> Nomenclature:
        pieces = list(self.plancher.pieces_achat())
        if self.inclure_charpente:
            pieces.extend(self.charpente.elements())
        return Nomenclature(pieces)
