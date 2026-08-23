import unittest

from maison.geometrie import GeometrieAFrame
from maison.structure import CharpenteAFrame


class TestCharpenteAFrame(unittest.TestCase):
    def setUp(self) -> None:
        self.charpente = CharpenteAFrame(
            GeometrieAFrame(
                largeur_interieure=7_108,
                longueur_interieure_imposee=2_804,
            ),
            niveau_appui=272,
        )

    def test_six_fermes_a_entraxe_500_mm(self) -> None:
        self.assertEqual(self.charpente.nombre_fermes, 6)
        self.assertEqual(
            self.charpente.axes_fermes(),
            (152, 652, 1_152, 1_652, 2_152, 2_652),
        )
        self.assertEqual(self.charpente.retrait_fermes_extremes, 152)
        self.assertEqual(len(self.charpente.elements()), 12)

    def test_geometrie_des_arbaletriers(self) -> None:
        self.assertAlmostEqual(self.charpente.largeur_entre_axes_pieds, 6_988)
        self.assertAlmostEqual(self.charpente.longueur_arbaletrier, 6_988)
        self.assertAlmostEqual(
            self.charpente.hauteur_faitage_interieure,
            272 + 3_494 * 3**0.5,
        )
        self.assertAlmostEqual(
            self.charpente.niveau_haut_faitage,
            self.charpente.hauteur_faitage_interieure + 250,
        )
        for element in self.charpente.elements():
            boite = element.forme.bounding_box()
            self.assertAlmostEqual(boite.size.X, 120)
            self.assertAlmostEqual(boite.min.Z, 272)

    def test_bom_regroupe_les_douze_arbaletriers(self) -> None:
        references = {
            element.article_bom().reference for element in self.charpente.elements()
        }
        self.assertEqual(len(references), 1)
        self.assertTrue(next(iter(references)).startswith("ARB-120x250-A60-LD7234_51"))


if __name__ == "__main__":
    unittest.main()
