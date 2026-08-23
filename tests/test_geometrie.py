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
        self.assertAlmostEqual(geometrie.surface_comptable, 20.5)

    def test_surface_totale_plafonnee_a_20_m2(self) -> None:
        geometrie = GeometrieAFrame(surface_plancher_max=20)

        self.assertAlmostEqual(geometrie.longueur_interieure, 10_000 / 3)
        self.assertAlmostEqual(geometrie.surface_plancher, 20)
        self.assertAlmostEqual(geometrie.surface_comptable, 13.071797, places=6)
        self.assertLess(geometrie.surface_comptable, geometrie.surface_comptable_cible)

    def test_longueur_modulaire_imposee_sous_le_plafond(self) -> None:
        geometrie = GeometrieAFrame(
            largeur_interieure=7_108,
            surface_plancher_max=20,
            longueur_interieure_imposee=2_804,
        )

        self.assertEqual(geometrie.longueur_interieure, 2_804)
        self.assertAlmostEqual(geometrie.surface_plancher, 19.930832)

    def test_longueur_imposee_refusee_si_surface_depassee(self) -> None:
        with self.assertRaisesRegex(ValueError, "surface maximale"):
            GeometrieAFrame(
                largeur_interieure=7_200,
                surface_plancher_max=20,
                longueur_interieure_imposee=2_804,
            )

    def test_geometrie_sans_zone_comptable(self) -> None:
        with self.assertRaises(ValueError):
            GeometrieAFrame(largeur_interieure=2_000, angle_degres=45)


if __name__ == "__main__":
    unittest.main()
