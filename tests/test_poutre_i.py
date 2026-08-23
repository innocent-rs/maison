import unittest

from maison.structure import PoutreI


class TestPoutreI(unittest.TestCase):
    def test_dimensions_sj90_360(self) -> None:
        poutre = PoutreI(longueur=5_000)
        taille = poutre.construire().bounding_box().size

        self.assertAlmostEqual(taille.X, 5_000)
        self.assertAlmostEqual(taille.Y, 90)
        self.assertAlmostEqual(taille.Z, 360)
        self.assertAlmostEqual(poutre.hauteur_ame, 270)

    def test_volume_de_matiere(self) -> None:
        poutre = PoutreI(longueur=1_000)
        volume_attendu = 1_000 * (2 * 90 * 45 + 8 * 270)

        self.assertAlmostEqual(poutre.volume_mm3, volume_attendu)
        self.assertAlmostEqual(poutre.construire().volume, volume_attendu)

    def test_dimensions_invalides(self) -> None:
        with self.assertRaises(ValueError):
            PoutreI(longueur=1_000, hauteur=80)


if __name__ == "__main__":
    unittest.main()
