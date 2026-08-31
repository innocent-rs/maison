import unittest

from atelier_mob import creer_atelier_mob


class TestDiagnosticThermiqueAtelierMob(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.atelier = creer_atelier_mob()
        cls.rapport = cls.atelier.analyser_vides()

    def test_soustrait_toutes_les_pieces_volumiques_de_l_enveloppe(self) -> None:
        self.assertEqual(self.rapport.nombre_occupants, 339)
        self.assertEqual(self.rapport.nombre_composantes, 1)
        self.assertEqual(len(self.rapport.composantes[0].forme.solids()), 1)

    def test_quantifie_le_volume_non_isole(self) -> None:
        self.assertAlmostEqual(self.rapport.volume_enveloppe_m3, 19.845)
        self.assertAlmostEqual(self.rapport.volume_vide_m3, 4.07004396)
        self.assertAlmostEqual(self.rapport.taux_vide_pct, 20.5091658352)

    def test_le_vide_couvre_toute_la_structure_sans_deborder_des_parements(self) -> None:
        boite = self.rapport.composantes[0].forme.bounding_box()

        self.assertAlmostEqual(boite.min.Z, 51)
        self.assertAlmostEqual(boite.max.Z, 240)
        self.assertAlmostEqual(boite.min.X, 0)
        self.assertAlmostEqual(boite.max.X, 15_000)


if __name__ == "__main__":
    unittest.main()
