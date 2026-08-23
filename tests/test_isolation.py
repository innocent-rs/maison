import unittest

from maison.structure import PanneauSTEICOflex036


class TestPanneauSTEICOflex036(unittest.TestCase):
    def test_dimensions_nominales_et_posees(self) -> None:
        panneau = PanneauSTEICOflex036()
        taille = panneau.construire().bounding_box().size

        self.assertEqual((taille.X, taille.Y, taille.Z), (1_220, 565, 118))
        self.assertAlmostEqual(panneau.resistance_thermique_nominale, 10 / 3)
        article = panneau.article_bom()
        self.assertEqual(article.reference, "ISOL-STEICOFLEX036-120x575x1220")
        self.assertEqual(
            (article.longueur_mm, article.largeur_mm, article.hauteur_mm),
            (1_220, 575, 120),
        )


if __name__ == "__main__":
    unittest.main()
