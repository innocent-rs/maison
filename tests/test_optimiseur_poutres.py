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
        self.assertAlmostEqual(resultat.cout_bois_eur, 1620)
        self.assertEqual(resultat.nombre_pieux_total, 18)
        self.assertAlmostEqual(resultat.cout_appuis_eur, 9_000)
        self.assertAlmostEqual(resultat.cout_eur, 10_620)

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
        self.assertEqual(resultat.nombre_pieux_intermediaires, 8)
        self.assertEqual(resultat.nombre_pieux_rive, 8)
        self.assertEqual(resultat.nombre_pieux_total, 16)
        self.assertAlmostEqual(resultat.cout_appuis_eur, 8_000)

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
            resultat.reaction_pieu_max_elu_kN,
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

    def test_profils_de_fleche_appliquent_leur_diviseur(self) -> None:
        self.assertEqual(HypothesesProjet(profil_fleche="atelier").limite_fleche_diviseur, 250)
        self.assertEqual(HypothesesProjet(profil_fleche="maison").limite_fleche_diviseur, 300)
        self.assertEqual(
            HypothesesProjet(profil_fleche="maison_fragile").limite_fleche_diviseur,
            400,
        )
        self.assertEqual(HypothesesProjet(profil_fleche="toiture").limite_fleche_diviseur, 200)
        self.assertEqual(
            HypothesesProjet(
                profil_fleche="personnalise",
                limite_fleche_diviseur=350,
            ).limite_fleche_diviseur,
            350,
        )

    def test_plan_de_pieux_contient_toujours_les_quatre_angles(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(longueur_m=10, largeur_m=10),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=3,
        )

        self.assertEqual(len(resultat.pieux), resultat.nombre_pieux_total)
        self.assertEqual(
            {(p.x_m, p.y_m) for p in resultat.pieux if p.type_appui == "angle"},
            {(0.0, 0.0), (10.0, 0.0), (0.0, 10.0), (10.0, 10.0)},
        )

    def test_reactions_individuelles_distinguent_rive_et_interieur(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(longueur_m=10, largeur_m=10),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=2,
        )
        angle = next(p for p in resultat.pieux if p.type_appui == "angle")
        interieur = max(resultat.pieux, key=lambda p: p.reaction_elu_kN)

        self.assertEqual(interieur.type_appui, "intermediaire")
        self.assertGreater(interieur.reaction_elu_kN, angle.reaction_elu_kN)
        self.assertAlmostEqual(
            interieur.reaction_elu_kN,
            resultat.reaction_pieu_max_elu_kN,
        )

    def test_compression_sur_platine_est_verifiee(self) -> None:
        resultat = evaluer_configuration(
            HypothesesProjet(),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=4,
        )

        self.assertGreater(resultat.contrainte_compression_appui_mpa, 0)
        self.assertGreater(resultat.resistance_compression_appui_mpa, 0)
        self.assertAlmostEqual(
            resultat.taux_compression_appui,
            resultat.contrainte_compression_appui_mpa
            / resultat.resistance_compression_appui_mpa,
        )

    def test_vibration_est_indicative_et_absente_pour_toiture(self) -> None:
        maison = evaluer_configuration(
            HypothesesProjet(profil_fleche="maison"),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=4,
        )
        toiture = evaluer_configuration(
            HypothesesProjet(profil_fleche="toiture"),
            self.section,
            "longueur",
            nombre_poutres=4,
            nombre_travees=4,
        )

        self.assertGreater(maison.frequence_propre_hz, 0)
        self.assertGreater(maison.fleche_sous_1kn_mm, 0)
        self.assertIsNotNone(maison.taux_vibration)
        self.assertIsNone(toiture.taux_vibration)
        self.assertIsNone(toiture.vibration_respectee)

    def test_optimisation_expose_trois_objectifs(self) -> None:
        resultat = optimiser(HypothesesProjet())

        self.assertIsNotNone(resultat.meilleure)
        self.assertIsNotNone(resultat.moins_de_pieux)
        self.assertIsNotNone(resultat.meilleure_marge)
        self.assertLessEqual(
            resultat.moins_de_pieux.nombre_pieux_total,
            resultat.meilleure.nombre_pieux_total,
        )
        self.assertLessEqual(
            resultat.meilleure_marge.taux_dimensionnant,
            resultat.meilleure.taux_dimensionnant,
        )

    def test_refuse_une_section_vide(self) -> None:
        with self.assertRaises(ValueError):
            optimiser(HypothesesProjet(), [])


class TestWebOptimiseurPoutres(unittest.TestCase):
    def setUp(self) -> None:
        self.client = create_app({"TESTING": True}).test_client()

    @staticmethod
    def _formulaire_valide() -> dict[str, str | list[str]]:
        hypotheses = HypothesesProjet()
        data = {nom: str(getattr(hypotheses, nom)) for nom in (
            "longueur_m", "largeur_m", "masse_permanente_kg_m2",
            "masse_exploitation_kg_m2", "masse_ajoutee_totale_kg",
            "masse_volumique_kg_m3", "entraxe_max_m",
            "limite_fleche_diviseur", "e_moyen_mpa", "g_moyen_mpa",
            "fm_k_mpa", "fv_k_mpa", "fc90_k_mpa", "kc90", "kmod",
            "kdef", "psi2", "gamma_m",
        )}
        data.update({
            "longueur_m": "6,0",
            "orientation": "auto",
            "profil_usage": "maison",
            "profil_fleche": "maison",
            "inclure_poids_propre": "on",
            "section_active": "0",
            "section_nom": "100 × 200",
            "section_largeur": "100",
            "section_hauteur": "200",
            "section_prix": "29,02",
            "section_longueur_max": "13",
            "entraxe_solives_max_mm": "625",
            "classe_service_solives": "2",
            "limite_fleche_solives_diviseur": "350",
            "largeur_isolant_mm": "575",
            "inclure_sabots": "on",
            "solive_active": ["0", "1", "2"],
            "solive_prix": ["14,10", "14,40", "20,30"],
        })
        return data

    def test_page_initiale_presente_une_optimisation(self) -> None:
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("CHOIX LE MOINS CHER CONFORME", reponse.text)
        self.assertIn("Flèche finale", reponse.text)
        self.assertIn("Solives en I", reponse.text)
        self.assertIn("CHOIX DE SOLIVES LE MOINS CHER CONFORME", reponse.text)
        self.assertIn("Plan à l’échelle", reponse.text)
        meilleure = optimiser(HypothesesProjet()).meilleure
        self.assertIsNotNone(meilleure)
        self.assertEqual(meilleure.nombre_pieux_rive, 2 * meilleure.nombre_poutres)
        self.assertEqual(
            reponse.text.count('class="platine-pieu"'),
            meilleure.nombre_pieux_total,
        )
        self.assertIn("dont les 4 coins", reponse.text)

    def test_formulaire_invalide_est_explique(self) -> None:
        reponse = self.client.post("/", data={})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Entrée invalide", reponse.text)

    def test_formulaire_complet_accepte_les_decimales_francaises(self) -> None:
        reponse = self.client.post("/", data=self._formulaire_valide())
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("CHOIX LE MOINS CHER CONFORME", reponse.text)
        self.assertNotIn('name="nombre_lignes_appui_max"', reponse.text)

    def test_bouton_solives_rouvre_le_bon_onglet(self) -> None:
        data = self._formulaire_valide()
        data["onglet_actif"] = "solives"
        reponse = self.client.post("/", data=data)

        self.assertEqual(reponse.status_code, 200)
        self.assertIn('data-onglet-initial="solives"', reponse.text)
        self.assertIn("Trame complète à l’échelle", reponse.text)
        self.assertIn("automatiquement réinjecté dans G", reponse.text)

    def test_sabots_peuvent_etre_exclus_du_chiffrage(self) -> None:
        data = self._formulaire_valide()
        data.pop("inclure_sabots")
        data["onglet_actif"] = "solives"
        reponse = self.client.post("/", data=data)

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("0 sabots estimés", reponse.text)

    def test_solive_plus_haute_affiche_le_depassement_et_le_sabot(self) -> None:
        data = self._formulaire_valide()
        data["solive_active"] = ["1"]
        data["onglet_actif"] = "solives"
        reponse = self.client.post("/", data=data)

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Solive plus haute que la poutre principale", reponse.text)
        self.assertIn("EWH 300/61", reponse.text)

    def test_isolant_600_affiche_l_adaptation_necessaire(self) -> None:
        data = self._formulaire_valide()
        data["largeur_isolant_mm"] = "600"
        data["onglet_actif"] = "solives"
        reponse = self.client.post("/", data=data)

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("CALEPINAGE ISOLANT 600 MM", reponse.text)
        self.assertIn("prévoir une recoupe", reponse.text)

    def test_export_csv_contient_coordonnees_et_reactions(self) -> None:
        reponse = self.client.post(
            "/export/pieux.csv",
            data=self._formulaire_valide(),
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.mimetype, "text/csv")
        self.assertIn("implantation-pieux.csv", reponse.headers["Content-Disposition"])
        self.assertTrue(reponse.data.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"reaction_elu_kN", reponse.data)
        self.assertIn(b"P01;angle;", reponse.data)

    def test_export_pdf_produit_un_vrai_document(self) -> None:
        reponse = self.client.post(
            "/export/rapport.pdf",
            data=self._formulaire_valide(),
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.mimetype, "application/pdf")
        self.assertIn("rapport-poutres-pieux.pdf", reponse.headers["Content-Disposition"])
        self.assertTrue(reponse.data.startswith(b"%PDF"))
        self.assertGreater(len(reponse.data), 5_000)


if __name__ == "__main__":
    unittest.main()
