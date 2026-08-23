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
        self.assertEqual(self.bom.nombre_pieces, 5)
        self.assertEqual(sorted(ligne.quantite for ligne in self.bom.lignes), [2, 3])

    def test_totaux(self) -> None:
        ligne_traverses = next(
            ligne
            for ligne in self.bom.lignes
            if ligne.article.reference == "MAD-120x250-L6000"
        )
        self.assertAlmostEqual(ligne_traverses.longueur_totale_mm, 18_000)

    def test_export_csv(self) -> None:
        sortie = io.StringIO()
        self.bom.ecrire_csv(sortie)

        contenu = sortie.getvalue()
        self.assertIn("reference;categorie;designation", contenu)
        self.assertIn("MAD-120x250-L6000", contenu)


if __name__ == "__main__":
    unittest.main()
