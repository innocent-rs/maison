import unittest

from maison.geometrie import GeometrieAFrame


class TestGeometrieAFrame(unittest.TestCase):
    def test_base_recommandee(self) -> None:
        geometrie = GeometrieAFrame()

        self.assertAlmostEqual(geometrie.hauteur_faitage, 5_196.152, places=3)
        self.assertAlmostEqual(geometrie.largeur_comptable, 3_921.539, places=3)
        self.assertAlmostEqual(
            geometrie.longueur_interieure * geometrie.largeur_comptable / 1_000_000,
            20.5,
        )

    def test_geometrie_sans_zone_comptable(self) -> None:
        with self.assertRaises(ValueError):
            GeometrieAFrame(largeur_interieure=2_000, angle_degres=45)


if __name__ == "__main__":
    unittest.main()
