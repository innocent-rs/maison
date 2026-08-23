import unittest

from maison.structure import Madrier, Tasseau


class TestMadrier(unittest.TestCase):
    def test_dimensions_par_defaut(self) -> None:
        madrier = Madrier(longueur=4_000)
        taille = madrier.construire().bounding_box().size

        self.assertAlmostEqual(taille.X, 4_000)
        self.assertAlmostEqual(taille.Y, 120)
        self.assertAlmostEqual(taille.Z, 250)

    def test_dimensions_invalides(self) -> None:
        with self.assertRaises(ValueError):
            Madrier(longueur=0)

    def test_tasseau_membrure_de_poutre_i(self) -> None:
        tasseau = Tasseau(longueur=1_500)
        taille = tasseau.construire().bounding_box().size

        self.assertAlmostEqual(taille.X, 1_500)
        self.assertAlmostEqual(taille.Y, 90)
        self.assertAlmostEqual(taille.Z, 45)
        self.assertEqual(tasseau.article_bom().categorie, "Bois / tasseau")


if __name__ == "__main__":
    unittest.main()
