import unittest

from maison.structure import Madrier


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


if __name__ == "__main__":
    unittest.main()
