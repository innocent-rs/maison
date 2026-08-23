import unittest

from maison.structure import DalleOSB


class TestDalleOSB(unittest.TestCase):
    def test_toutes_les_epaisseurs_disponibles(self) -> None:
        for epaisseur in (12, 15, 18, 22):
            with self.subTest(epaisseur=epaisseur):
                dalle = DalleOSB(epaisseur=epaisseur)
                taille = dalle.construire().bounding_box().size

                self.assertAlmostEqual(taille.X, 2_500)
                self.assertAlmostEqual(taille.Y, 675)
                self.assertAlmostEqual(taille.Z, epaisseur)

    def test_epaisseur_invalide(self) -> None:
        with self.assertRaisesRegex(ValueError, "épaisseur indisponible"):
            DalleOSB(epaisseur=20)

    def test_article_bom(self) -> None:
        article = DalleOSB(epaisseur=22).article_bom()

        self.assertEqual(article.reference, "OSB-675x2500x22")
        self.assertEqual(article.volume_mm3, 37_125_000)


if __name__ == "__main__":
    unittest.main()
