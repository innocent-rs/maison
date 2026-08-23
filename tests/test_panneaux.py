import unittest

from maison.structure import DalleOSB, PanneauFondCaissonOSB, PanneauPlancherOSB


class TestDalleOSB(unittest.TestCase):
    def test_toutes_les_epaisseurs_disponibles(self) -> None:
        for epaisseur in (12, 15, 18, 22):
            with self.subTest(epaisseur=epaisseur):
                dalle = DalleOSB(epaisseur=epaisseur)
                taille = dalle.construire().bounding_box().size

                self.assertAlmostEqual(taille.X, 2_500)
                self.assertAlmostEqual(taille.Y, 675)
                self.assertAlmostEqual(taille.Z, epaisseur)

    def test_epaisseur_invalide(self) -> None:
        with self.assertRaisesRegex(ValueError, "épaisseur indisponible"):
            DalleOSB(epaisseur=20)

    def test_article_bom(self) -> None:
        article = DalleOSB(epaisseur=22).article_bom()

        self.assertEqual(article.reference, "OSB-675x2500x22")
        self.assertEqual(article.volume_mm3, 37_125_000)

    def test_fond_caisson_avec_encoches_ewh(self) -> None:
        panneau = PanneauFondCaissonOSB(
            epaisseur=12,
            largeur=479,
            longueur=2_428,
        )
        forme = panneau.construire()
        volume_plein = 479 * 2_428 * 12

        self.assertAlmostEqual(
            forme.volume,
            volume_plein - 4 * 82 * 47 * 12,
        )
        self.assertEqual(panneau.article_bom().categorie, "Panneaux / découpe OSB")

    def test_fond_caisson_de_rive_rectangulaire(self) -> None:
        panneau = PanneauFondCaissonOSB(
            epaisseur=12,
            largeur=423,
            longueur=1_479,
            avec_encoches=False,
        )

        self.assertAlmostEqual(panneau.construire().volume, 423 * 1_479 * 12)
        self.assertEqual(panneau.volume_mm3, 423 * 1_479 * 12)
        self.assertTrue(panneau.article_bom().reference.endswith("-RECT"))

    def test_panneau_plancher_osb_22_mm(self) -> None:
        panneau = PanneauPlancherOSB(
            epaisseur=22,
            largeur=675,
            longueur=1_835,
        )
        taille = panneau.construire().bounding_box().size

        self.assertEqual((taille.X, taille.Y, taille.Z), (1_835, 675, 22))
        self.assertEqual(
            panneau.article_bom().reference,
            "OSB-PLANCHER-675x1835x22",
        )


if __name__ == "__main__":
    unittest.main()
