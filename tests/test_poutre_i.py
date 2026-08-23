import unittest

from maison.structure import PoutreI


class TestPoutreI(unittest.TestCase):
    def test_dimensions_sj60_240(self) -> None:
        poutre = PoutreI(longueur=5_000)
        taille = poutre.construire().bounding_box().size

        self.assertAlmostEqual(taille.X, 5_000)
        self.assertAlmostEqual(taille.Y, 60)
        self.assertAlmostEqual(taille.Z, 240)
        self.assertAlmostEqual(poutre.hauteur_ame, 150)

    def test_volume_de_matiere(self) -> None:
        poutre = PoutreI(longueur=1_000)
        volume_attendu = 1_000 * (2 * 60 * 45 + 8 * 150)

        self.assertAlmostEqual(poutre.volume_mm3, volume_attendu)
        self.assertAlmostEqual(poutre.construire().volume, volume_attendu)

    def test_dimensions_invalides(self) -> None:
        with self.assertRaises(ValueError):
            PoutreI(longueur=1_000, hauteur=80)


if __name__ == "__main__":
    unittest.main()
