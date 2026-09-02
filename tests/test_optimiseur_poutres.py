import unittest

from optimiseur_poutres.calcul import (
    CatalogueSection,
    HypothesesProjet,
    evaluer_configuration,
    optimiser,
)
from optimiseur_poutres.webapp import create_app


class TestCalculOptimiseurPoutres(unittest.TestCase):
    def setUp(self) -> None:
        self.section = CatalogueSection("100 × 200", 100, 200, 30, 13)

    def test_entraxe_et_cout(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(longueur_m=6, largeur_m=4),
            self.section,
            "longueur",
            9,
        )
        self.assertAlmostEqual(resultat.entraxe_m, 0.5)
        self.assertAlmostEqual(resultat.longueur_totale_m, 54)
        self.assertAlmostEqual(resultat.cout_eur, 1620)

    def test_fleche_finale_applique_le_fluage(self) -> None:
        hypotheses = HypothesesProjet(
            kdef=0.8,
            psi2=0.3,
            inclure_poids_propre=False,
        )
        resultat = evaluer_configuration(hypotheses, self.section, "largeur", 11)
        attendu = resultat.fleche_g_mm * 1.8 + resultat.fleche_q_mm * 1.24
        self.assertAlmostEqual(resultat.fleche_finale_mm, attendu)

    def test_deux_poutres_de_rive_reprennent_chacune_une_demi_largeur(self) -> None:
        hypotheses = HypothesesProjet(
            longueur_m=4,
            largeur_m=2,
            masse_permanente_kg_m2=100,
            masse_exploitation_kg_m2=0,
            inclure_poids_propre=False,
            entraxe_max_m=0,
        )
        resultat = evaluer_configuration(hypotheses, self.section, "longueur", 2)
        self.assertAlmostEqual(resultat.charge_g_kN_m, 0.981)

    def test_optimisation_retient_une_solution_conforme_et_la_moins_chere(self) -> None:
        sections = [
            CatalogueSection("petite", 200, 500, 50, 13),
            CatalogueSection("grande", 300, 800, 180, 13),
        ]
        resultat = optimiser(
            HypothesesProjet(longueur_m=10, largeur_m=10),
            sections,
        )
        self.assertIsNotNone(resultat.meilleure)
        self.assertTrue(resultat.meilleure.conforme)
        couts = [c.cout_eur for c in resultat.configurations if c.conforme]
        self.assertEqual(resultat.meilleure.cout_eur, min(couts))

    def test_carre_10x10_n_invente_pas_des_poutres_tous_les_42_mm(self) -> None:
        resultat = optimiser(HypothesesProjet(longueur_m=10, largeur_m=10))

        for configuration in resultat.configurations:
            largeur_m = configuration.section.largeur_mm / 1_000
            self.assertGreaterEqual(configuration.entraxe_m + 1e-12, largeur_m)

    def test_carre_10x10_ajoute_des_appuis_et_reduit_la_portee(self) -> None:
        resultat = optimiser(
            HypothesesProjet(
                longueur_m=10,
                largeur_m=10,
                entraxe_max_m=4,
            )
        )

        self.assertIsNotNone(resultat.meilleure)
        self.assertGreater(resultat.meilleure.nombre_lignes_appui_intermediaires, 0)
        self.assertLess(resultat.meilleure.portee_m, 10)
        self.assertAlmostEqual(
            resultat.meilleure.portee_m,
            10 / resultat.meilleure.nombre_travees,
        )
        self.assertAlmostEqual(
            resultat.meilleure.cout_eur,
            resultat.meilleure.cout_bois_eur + resultat.meilleure.cout_appuis_eur,
        )

    def test_pieux_sont_chiffres_a_500_euros_piece(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(longueur_m=10, largeur_m=10),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=3,
        )

        self.assertEqual(resultat.nombre_lignes_appui_intermediaires, 2)
        self.assertEqual(resultat.nombre_appuis_ponctuels, 8)
        self.assertAlmostEqual(resultat.cout_appuis_eur, 4_000)

    def test_pieu_interieur_reprend_les_deux_demi_reactions(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(longueur_m=10, largeur_m=10),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=2,
        )
        charge_elu = 1.35 * resultat.charge_g_kN_m + 1.5 * resultat.charge_q_kN_m

        self.assertAlmostEqual(
            resultat.reaction_appui_intermediaire_elu_kN,
            charge_elu * resultat.portee_m,
        )
        self.assertAlmostEqual(resultat.capacite_appui_kN, 49.05)

    def test_pieu_trop_faible_rend_la_configuration_non_conforme(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(masse_exploitation_kg_m2=2_000),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=4,
        )

        self.assertFalse(resultat.conforme)
        self.assertIn("capacité statique du pieu vissé", resultat.contraintes)

    def test_refuse_une_section_vide(self) -> None:
        with self.assertRaises(ValueError):
            optimiser(HypothesesProjet(), [])


class TestWebOptimiseurPoutres(unittest.TestCase):
    def setUp(self) -> None:
        self.client = create_app({"TESTING": True}).test_client()

    def test_page_initiale_presente_une_optimisation(self) -> None:
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("CHOIX LE MOINS CHER CONFORME", reponse.text)
        self.assertIn("Flèche finale", reponse.text)
        self.assertIn("Solives en I hors calcul", reponse.text)
        self.assertIn("Plan à l’échelle", reponse.text)
        self.assertEqual(reponse.text.count('class="platine-pieu"'), 10)

    def test_formulaire_invalide_est_explique(self) -> None:
        reponse = self.client.post("/", data={})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Entrée invalide", reponse.text)

    def test_formulaire_complet_accepte_les_decimales_francaises(self) -> None:
        hypotheses = HypothesesProjet()
        data = {nom: str(getattr(hypotheses, nom)) for nom in (
            "longueur_m", "largeur_m", "masse_permanente_kg_m2",
            "masse_exploitation_kg_m2", "masse_ajoutee_totale_kg",
            "masse_volumique_kg_m3", "entraxe_max_m",
            "limite_fleche_diviseur", "e_moyen_mpa", "g_moyen_mpa",
            "fm_k_mpa", "fv_k_mpa", "kmod", "kdef", "psi2", "gamma_m",
        )}
        data.update({
            "longueur_m": "6,0",
            "orientation": "auto",
            "inclure_poids_propre": "on",
            "section_active": "0",
            "section_nom": "100 × 200",
            "section_largeur": "100",
            "section_hauteur": "200",
            "section_prix": "29,02",
            "section_longueur_max": "13",
        })
        reponse = self.client.post("/", data=data)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("CHOIX LE MOINS CHER CONFORME", reponse.text)
        self.assertNotIn('name="nombre_lignes_appui_max"', reponse.text)


if __name__ == "__main__":
    unittest.main()
