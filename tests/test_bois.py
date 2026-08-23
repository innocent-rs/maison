import unittest

from maison.structure import Arbaletrier, Madrier, Tasseau


class TestMadrier(unittest.TestCase):
    def test_dimensions_par_defaut(self) -> None:
        madrier = Madrier(longueur=4_000)
        taille = madrier.construire().bounding_box().size

        self.assertAlmostEqual(taille.X, 4_000)
        self.assertAlmostEqual(taille.Y, 120)
        self.assertAlmostEqual(taille.Z, 240)

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

    def test_arbaletrier_coupe_a_60_degres(self) -> None:
        arbaletrier = Arbaletrier(longueur_axe=6_988, angle_degres=60)

        self.assertAlmostEqual(arbaletrier.angle_coupe_pied_axe, 60)
        self.assertAlmostEqual(arbaletrier.angle_coupe_faitage_axe, 30)
        self.assertAlmostEqual(arbaletrier.longueur_debit, 7_234.5063509)
        self.assertAlmostEqual(arbaletrier.largeur_appui_pied, 120)
        self.assertAlmostEqual(arbaletrier.longueur_relief_interieur, 85.4922678)
        self.assertLess(
            arbaletrier.construire().volume,
            6_988 * 120 * 250,
        )


if __name__ == "__main__":
    unittest.main()
