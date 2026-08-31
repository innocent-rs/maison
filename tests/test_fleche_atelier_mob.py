import unittest

from atelier_mob.fleche import HypothesesFleche, calculer_fleche
from atelier_mob.webapp import create_app


class TestCalculFlecheGT24(unittest.TestCase):
    def test_charge_repartie_retrouve_la_formule_euler_bernoulli(self) -> None:
        hypotheses = HypothesesFleche(
            portee_mm=3_000,
            largeur_mm=120,
            hauteur_mm=240,
            module_young_mpa=11_000,
            charge_permanente_kN_m2=1,
            charge_exploitation_kN_m2=0,
            largeur_tributaire_m=1,
            inclure_poids_propre=False,
        )
        resultat = calculer_fleche(hypotheses).permanente
        inertie = 120 * 240**3 / 12
        attendu = 5 * 1 * 3_000**4 / (384 * 11_000 * inertie)

        self.assertAlmostEqual(resultat.fleche_flexion_mm, attendu)
        self.assertAlmostEqual(
            resultat.fleche_cisaillement_mm,
            1 * 3_000**2 / (8 * 690 * (5 / 6) * 120 * 240),
        )

    def test_charge_centrale_est_affectee_au_cas_q(self) -> None:
        resultat = calculer_fleche(
            HypothesesFleche(
                charge_permanente_kN_m2=0,
                charge_exploitation_kN_m2=0,
                charge_ponctuelle_kN=10,
                inclure_poids_propre=False,
            )
        )

        self.assertEqual(resultat.permanente.fleche_totale_mm, 0)
        self.assertGreater(resultat.exploitation.fleche_totale_mm, 0)
        self.assertAlmostEqual(
            resultat.exploitation.fleche_totale_mm,
            resultat.service.fleche_totale_mm,
        )

    def test_superposition_g_plus_q(self) -> None:
        resultat = calculer_fleche(HypothesesFleche())

        self.assertAlmostEqual(
            resultat.service.fleche_totale_mm,
            resultat.permanente.fleche_totale_mm
            + resultat.exploitation.fleche_totale_mm,
        )
        self.assertAlmostEqual(
            resultat.profil_service[len(resultat.profil_service) // 2][1],
            resultat.service.fleche_totale_mm,
        )

    def test_refuse_les_entrees_non_physiques(self) -> None:
        with self.assertRaises(ValueError):
            HypothesesFleche(portee_mm=0)
        with self.assertRaises(ValueError):
            HypothesesFleche(charge_exploitation_kN_m2=-1)


class TestWebappFlecheGT24(unittest.TestCase):
    def setUp(self) -> None:
        self.client = create_app({"TESTING": True}).test_client()

    def test_page_initiale_affiche_un_resultat(self) -> None:
        reponse = self.client.get("/")

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Flèche d’une poutre", reponse.text)
        self.assertIn("Résultat de service", reponse.text)

    def test_formulaire_accepte_les_decimales_francaises(self) -> None:
        reponse = self.client.post(
            "/",
            data={
                "portee_mm": "3000",
                "largeur_mm": "120",
                "hauteur_mm": "240",
                "module_young_mpa": "11000",
                "module_cisaillement_mpa": "690",
                "coefficient_cisaillement": "0,833333",
                "masse_volumique_kg_m3": "500",
                "charge_permanente_kN_m2": "0,5",
                "charge_exploitation_kN_m2": "1,5",
                "largeur_tributaire_m": "3,5",
                "charge_ponctuelle_kN": "0",
                "limite_fleche_diviseur": "300",
                "inclure_poids_propre": "on",
            },
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("G + Q", reponse.text)

    def test_formulaire_invalide_retourne_400_sans_planter(self) -> None:
        reponse = self.client.post("/", data={})

        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Entrée invalide", reponse.text)


if __name__ == "__main__":
    unittest.main()
