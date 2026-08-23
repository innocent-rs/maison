import unittest

from main import make_part


class TestModeleCourant(unittest.TestCase):
    def setUp(self) -> None:
        self.maison = make_part()
        self.plancher = self.maison.plancher

    def test_emprise_ronde_sous_20_m2(self) -> None:
        self.assertEqual(self.maison.geometrie.largeur_interieure, 4_000)
        self.assertEqual(self.maison.geometrie.longueur_interieure, 4_800)
        self.assertEqual(self.maison.geometrie.surface_plancher, 19.2)

    def test_configuration_active_contient_poutres_et_solives_i(self) -> None:
        elements = self.maison.elements()

        self.assertEqual(len(elements), 107)
        self.assertEqual(
            [element.nom for element in elements[:5]],
            [
                "Poutre longitudinale gauche",
                "Poutre longitudinale droite",
                "Traverse haute",
                "Traverse milieu",
                "Traverse basse",
            ],
        )
        self.assertTrue(
            all(element.nom.startswith("Sabot SAI") for element in elements[5:11])
        )
        self.assertEqual(self.plancher.axes_traverses(), (62, 2_400, 4_738))
        self.assertEqual(self.plancher.longueur_traverses, 3_756)
        self.assertEqual(self.plancher.nombre_sabots, 6)
        self.assertEqual(self.plancher.nombre_vis_connecteurs, 300)
        self.assertEqual(self.plancher.nombre_lignes_solives_i, 6)
        self.assertEqual(self.plancher.nombre_solives_i, 12)
        self.assertEqual(self.plancher.longueur_solives_i, 2_212)
        self.assertEqual(self.plancher.nombre_sabots_ewh, 24)
        self.assertEqual(self.plancher.nombre_pointes_ewh, 384)

    def test_fonds_de_caisson_et_isolant_actifs(self) -> None:
        self.assertTrue(self.plancher.inclure_connecteurs)
        self.assertTrue(self.plancher.inclure_solives_i)
        self.assertTrue(self.plancher.inclure_osb_caissons)
        self.assertEqual(self.plancher.nombre_panneaux_osb_caissons, 14)
        self.assertEqual(self.plancher.nombre_dalles_brutes_osb_caissons, 7)
        self.assertEqual(self.plancher.nombre_tasseaux_rive, 4)
        self.assertEqual(self.plancher.nombre_vis_tasseaux_rive, 32)
        self.assertEqual(self.plancher.nombre_vis_osb, 420)
        self.assertTrue(self.plancher.inclure_isolant_caissons)
        self.assertEqual(self.plancher.epaisseur_isolant_nominale, 145)
        self.assertEqual(self.plancher.hauteur_caisson_isolant, 150)
        self.assertEqual(self.plancher.nombre_segments_isolant_par_caisson, 2)
        self.assertEqual(self.plancher.longueur_segment_isolant, 1_109)
        self.assertAlmostEqual(
            self.plancher.largeur_decoupe_isolant,
            540.285714,
            places=6,
        )
        self.assertEqual(self.plancher.longueur_decoupe_segment_isolant, 1_119)
        self.assertEqual(self.plancher.nombre_panneaux_isolant, 28)
        isolants = [
            element
            for element in self.maison.elements()
            if element.nom.startswith("Isolant Isonat")
        ]
        self.assertEqual(len(isolants), 28)
        for isolant in isolants:
            boite = isolant.forme.bounding_box()
            self.assertAlmostEqual(boite.size.X, 1_109)
            self.assertAlmostEqual(boite.size.Y, 530.285714, places=6)
            self.assertAlmostEqual(boite.size.Z, 145)
            self.assertAlmostEqual(boite.min.Z, 51)
            self.assertAlmostEqual(boite.max.Z, 196)
        self.assertTrue(self.plancher.inclure_osb_plancher)
        self.assertEqual(self.plancher.epaisseur_osb_plancher, 22)
        self.assertEqual(self.plancher.nombre_panneaux_osb_plancher, 14)
        self.assertEqual(self.plancher.nombre_dalles_brutes_osb_plancher, 14)
        self.assertEqual(self.plancher.nombre_vis_osb_plancher, 568)
        self.assertEqual(
            self.plancher.bandes_x_osb_plancher(),
            ((0, 2_400), (2_400, 4_800)),
        )
        self.assertEqual(
            self.plancher.limites_y_osb_plancher()[1:-1],
            self.plancher.axes_solives_i(),
        )
        self.assertFalse(self.maison.inclure_charpente)
        self.assertEqual(self.maison.nomenclature_charpente().nombre_pieces, 0)

    def test_bom_active_contient_poutres_solives_et_fixations(self) -> None:
        lignes = {
            ligne.article.reference: ligne.quantite
            for ligne in self.maison.nomenclature().lignes
        }

        self.assertEqual(
            lignes,
            {
                "ISOL-ISONAT-FLEX55-145x580x1220": 28,
                "KLIMAS-KMWHT-5X60": 568,
                "MAD-120x240-L3756": 3,
                "MAD-120x240-L4800": 2,
                "OSB-FOND-BD-527_286x2212x12": 10,
                "OSB-FOND-BD-527_286x2212x12-RECT": 4,
                "OSB-PLANCHER-538_286x2400x22": 10,
                "OSB-PLANCHER-654_286x2400x22": 4,
                "SIMPSON-CNA4.0X35": 384,
                "SIMPSON-CSA5.0X40": 300,
                "SIMPSON-EWH240-61": 24,
                "SIMPSON-SAI500-120-2": 6,
                "SJI-60x240-L2212": 12,
                "KLIMAS-KMWHT-6X160": 32,
                "TAS-60x40-L2212": 4,
                "SPAX-0191010400355": 420,
            },
        )
        self.assertEqual(self.maison.nomenclature().nombre_pieces, 1_811)


if __name__ == "__main__":
    unittest.main()
