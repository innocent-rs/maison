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

        self.assertEqual(len(elements), 47)
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

    def test_tous_les_autres_sous_ensembles_sont_desactives(self) -> None:
        self.assertTrue(self.plancher.inclure_connecteurs)
        self.assertTrue(self.plancher.inclure_solives_i)
        self.assertFalse(self.plancher.inclure_osb_caissons)
        self.assertFalse(self.plancher.inclure_isolant_caissons)
        self.assertFalse(self.plancher.inclure_osb_plancher)
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
                "MAD-120x240-L3756": 3,
                "MAD-120x240-L4800": 2,
                "SIMPSON-CNA4.0X35": 384,
                "SIMPSON-CSA5.0X40": 300,
                "SIMPSON-EWH240-61": 24,
                "SIMPSON-SAI500-120-2": 6,
                "SJI-60x240-L2212": 12,
            },
        )
        self.assertEqual(self.maison.nomenclature().nombre_pieces, 731)


if __name__ == "__main__":
    unittest.main()
