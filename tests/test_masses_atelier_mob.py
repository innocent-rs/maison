import unittest

from atelier_mob import creer_atelier_mob


class TestMassesAtelierMob(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rapport = creer_atelier_mob().inventorier_masses()

    def test_masses_lineiques_des_bois_sont_explicites(self) -> None:
        madrier = next(
            ligne
            for ligne in self.rapport.lignes
            if ligne.reference == "MAD-120x240-L6756"
        )
        solive = next(
            ligne
            for ligne in self.rapport.lignes
            if ligne.reference.startswith("SJI-60x240")
        )
        tasseau = next(
            ligne
            for ligne in self.rapport.lignes
            if ligne.reference.startswith("TAS-60x40")
        )

        self.assertAlmostEqual(madrier.masse_lineique_kg_m, 14.4)
        self.assertAlmostEqual(solive.masse_lineique_kg_m, 4.12)
        self.assertAlmostEqual(tasseau.masse_lineique_kg_m, 1.2)

    def test_masse_totale_et_charge_surfacique_sont_agregees(self) -> None:
        self.assertAlmostEqual(self.rapport.masse_totale_kg, 4_788.446, places=3)
        self.assertAlmostEqual(
            self.rapport.masse_madriers_primaires_kg,
            1_210.2912,
        )
        self.assertAlmostEqual(
            self.rapport.charge_surfacique_hors_madriers_kN_m2,
            0.334301896,
        )
        self.assertAlmostEqual(self.rapport.masse_solives_i_kg, 634.20808)
        self.assertAlmostEqual(
            self.rapport.charge_surfacique_couches_hors_solives_kN_m2,
            0.275048741,
        )

    def test_la_verification_ajoute_les_charges_rapportees_sans_double_compter(self) -> None:
        rapport = creer_atelier_mob().verifier_structure()

        self.assertAlmostEqual(
            rapport.charge_permanente_surfacique_utilisee_kN_m2,
            self.rapport.charge_surfacique_hors_madriers_kN_m2 + 0.20,
        )
        self.assertAlmostEqual(
            rapport.charge_permanente_surfacique_solive_kN_m2,
            self.rapport.charge_surfacique_couches_hors_solives_kN_m2 + 0.20,
        )


if __name__ == "__main__":
    unittest.main()
