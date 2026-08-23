import io
import unittest

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


class TestNomenclature(unittest.TestCase):
    def setUp(self) -> None:
        self.plancher = PlancherAFrame(GeometrieAFrame())
        self.bom = self.plancher.nomenclature()

    def test_regroupe_les_coupes_identiques(self) -> None:
        self.assertEqual(len(self.bom.lignes), 2)
        self.assertEqual(self.bom.nombre_pieces, self.plancher.nombre_solives + 2)
        self.assertEqual(sorted(ligne.quantite for ligne in self.bom.lignes), [2, 10])

    def test_totaux(self) -> None:
        ligne_solives = next(
            ligne for ligne in self.bom.lignes if ligne.quantite == 10
        )
        self.assertAlmostEqual(ligne_solives.longueur_totale_mm, 57_600)

    def test_export_csv(self) -> None:
        sortie = io.StringIO()
        self.bom.ecrire_csv(sortie)

        contenu = sortie.getvalue()
        self.assertIn("reference;categorie;designation", contenu)
        self.assertIn("MAD-120x250-L5760", contenu)


if __name__ == "__main__":
    unittest.main()
