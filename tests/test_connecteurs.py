import unittest

from maison.structure import (
    PlanFixationEWH,
    PlanFixationSAI,
    PointeAncrageCNA4x35,
    SabotEWH219_91,
    SabotSAI500_120_2,
    VisBoisOSB4x35,
    VisConnecteurCSA5x40,
    VisPlancherOSB5x60,
)


class TestConnecteurs(unittest.TestCase):
    def test_sabot_sai500_120_2(self) -> None:
        sabot = SabotSAI500_120_2()
        forme = sabot.construire()
        boite = forme.bounding_box()

        self.assertGreater(forme.volume, 0)
        self.assertAlmostEqual(boite.min.Y, 0)
        self.assertAlmostEqual(boite.max.Y, 76)
        self.assertEqual(sabot.nombre_fixations(PlanFixationSAI.PARTIEL), 28)
        self.assertEqual(sabot.nombre_fixations(PlanFixationSAI.TOTAL), 50)
        self.assertEqual(sabot.article_bom().reference, "SIMPSON-SAI500-120-2")

    def test_sabot_refuse_une_poutre_hors_plage(self) -> None:
        with self.assertRaises(ValueError):
            SabotSAI500_120_2(largeur_interieure=125)

    def test_vis_csa5x40(self) -> None:
        vis = VisConnecteurCSA5x40()

        self.assertGreater(vis.construire().volume, 0)
        self.assertEqual(vis.article_bom().reference, "SIMPSON-CSA5.0X40")
        self.assertEqual(vis.article_bom().longueur_mm, 40)

    def test_etrier_ewh219_91(self) -> None:
        etrier = SabotEWH219_91()
        forme = etrier.construire()

        self.assertGreater(forme.volume, 0)
        self.assertEqual(
            etrier.nombre_pointes(PlanFixationEWH.BRIDES_SUPERIEURES),
            16,
        )
        self.assertEqual(
            etrier.nombre_pointes(PlanFixationEWH.BRIDES_LATERALES),
            12,
        )
        self.assertEqual(etrier.article_bom().reference, "SIMPSON-EWH219-91")

    def test_etrier_ewh_accepte_la_membrure_steico_de_90_mm(self) -> None:
        etrier = SabotEWH219_91()

        self.assertTrue(etrier.accepte_largeur_poutre(90))
        self.assertFalse(etrier.accepte_largeur_poutre(87))
        with self.assertRaises(ValueError):
            SabotEWH219_91(largeur_interieure=92)

    def test_pointe_cna4x35(self) -> None:
        pointe = PointeAncrageCNA4x35()

        self.assertEqual(pointe.article_bom().reference, "SIMPSON-CNA4.0X35")
        self.assertEqual(pointe.article_bom().longueur_mm, 35)

    def test_vis_osb_4x35(self) -> None:
        vis = VisBoisOSB4x35()

        self.assertEqual(vis.article_bom().reference, "VIS-BOIS-OSB-4X35")
        self.assertEqual(vis.article_bom().longueur_mm, 35)

    def test_vis_plancher_osb_5x60(self) -> None:
        vis = VisPlancherOSB5x60()

        self.assertEqual(vis.article_bom().reference, "VIS-PLANCHER-OSB-5X60")
        self.assertEqual(vis.article_bom().longueur_mm, 60)


if __name__ == "__main__":
    unittest.main()
