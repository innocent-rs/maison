import unittest

from maison.structure import PanneauIsonatFlex55


class TestPanneauIsonatFlex55(unittest.TestCase):
    def test_dimensions_nominales_et_posees(self) -> None:
        panneau = PanneauIsonatFlex55()
        taille = panneau.construire().bounding_box().size

        self.assertEqual((taille.X, taille.Y, taille.Z), (1_220, 565, 145))
        self.assertAlmostEqual(panneau.resistance_thermique_nominale, 145 / 36)
        article = panneau.article_bom()
        self.assertEqual(article.reference, "ISOL-ISONAT-FLEX55-145x580x1220")
        self.assertEqual(
            (article.longueur_mm, article.largeur_mm, article.hauteur_mm),
            (1_220, 580, 145),
        )

    def test_refuse_une_epaisseur_absente_de_la_gamme(self) -> None:
        with self.assertRaisesRegex(ValueError, "n'existe pas"):
            PanneauIsonatFlex55(epaisseur=150)


if __name__ == "__main__":
    unittest.main()
