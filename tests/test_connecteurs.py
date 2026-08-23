import unittest

from maison.structure import (
    FerrurePiedAFrame,
    KitTirantAFrame,
    PlanFixationEWH,
    PlanFixationSAI,
    PointeAncrageCNA4x35,
    SabotEWH,
    SabotSAI500_120_2,
    VisBoisOSB4x35,
    VisConnecteurCSA5x40,
    VisPlancherOSB5x60,
    VisTasseauKlimas6x160,
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

    def test_etrier_ewh240_61(self) -> None:
        etrier = SabotEWH()
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
        self.assertEqual(etrier.article_bom().reference, "SIMPSON-EWH240-61")

    def test_etrier_ewh_accepte_la_membrure_steico_de_90_mm(self) -> None:
        etrier = SabotEWH()

        self.assertTrue(etrier.accepte_largeur_poutre(60))
        self.assertFalse(etrier.accepte_largeur_poutre(57))
        with self.assertRaises(ValueError):
            SabotEWH(largeur_interieure=62)

    def test_pointe_cna4x35(self) -> None:
        pointe = PointeAncrageCNA4x35()

        self.assertEqual(pointe.article_bom().reference, "SIMPSON-CNA4.0X35")
        self.assertEqual(pointe.article_bom().longueur_mm, 35)

    def test_vis_osb_4x35(self) -> None:
        vis = VisBoisOSB4x35()

        self.assertEqual(vis.article_bom().reference, "SPAX-0191010400355")
        self.assertEqual(vis.article_bom().longueur_mm, 35)

    def test_vis_structurelle_des_tasseaux_6x160(self) -> None:
        vis = VisTasseauKlimas6x160()

        self.assertEqual(vis.article_bom().reference, "KLIMAS-KMWHT-6X160")
        self.assertEqual(vis.article_bom().longueur_mm, 160)

    def test_vis_plancher_osb_5x60(self) -> None:
        vis = VisPlancherOSB5x60()

        self.assertEqual(vis.article_bom().reference, "KLIMAS-KMWHT-5X60")
        self.assertEqual(vis.article_bom().longueur_mm, 60)

    def test_ferrure_pied_a_frame_provisoire(self) -> None:
        ferrure = FerrurePiedAFrame()
        forme = ferrure.construire()
        boite = forme.bounding_box()

        self.assertGreater(forme.volume, 0)
        self.assertAlmostEqual(forme.volume, ferrure.volume_mm3)
        self.assertAlmostEqual(boite.min.Y, 0)
        self.assertAlmostEqual(boite.max.Y, 200)
        self.assertEqual(
            ferrure.article_bom().reference,
            "FERRURE-PIED-AFRAME-PROV-120",
        )

    def test_tirant_a_frame_provisoire(self) -> None:
        tirant = KitTirantAFrame(longueur=4_000, diametre=16)
        forme = tirant.construire()
        boite = forme.bounding_box()

        self.assertGreater(forme.volume, 0)
        self.assertAlmostEqual(boite.size.X, 4_000)
        self.assertAlmostEqual(boite.size.Y, 16)
        self.assertEqual(
            tirant.article_bom().reference,
            "KIT-TIRANT-AFRAME-M16-L4000",
        )


if __name__ == "__main__":
    unittest.main()
