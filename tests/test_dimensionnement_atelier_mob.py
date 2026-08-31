import unittest

from atelier_mob import (
    HypothesesEurocode5,
    StatutVerification,
    creer_atelier_mob,
)


class TestDimensionnementEurocode5Atelier(unittest.TestCase):
    def setUp(self) -> None:
        self.atelier = creer_atelier_mob()

    def test_configuration_courante_reste_proche_de_la_fleche_finale_limite(self) -> None:
        rapport = self.atelier.verifier_structure()
        finale = next(
            verification
            for verification in rapport.verifications
            if verification.element.startswith("Traverse")
            and verification.critere == "flèche finale avec fluage"
        )

        self.assertEqual(finale.statut, StatutVerification.CONFORME)
        self.assertAlmostEqual(finale.taux_utilisation, 0.979, places=3)
        self.assertTrue(rapport.conforme_calculs)
        self.assertFalse(rapport.validation_automatique)

    def test_forfait_gk_peut_remplacer_le_calcul_detaille(self) -> None:
        rapport = self.atelier.verifier_structure(
            HypothesesEurocode5(charge_permanente_surfacique_kN_m2=0.60)
        )

        self.assertFalse(rapport.conforme_calculs)
        self.assertEqual(rapport.charge_permanente_surfacique_utilisee_kN_m2, 0.60)

    def test_elu_separe_flexion_cisaillement_et_appui(self) -> None:
        rapport = self.atelier.verifier_structure()
        taux = {
            verification.critere: verification.taux_utilisation
            for verification in rapport.verifications
        }

        self.assertAlmostEqual(taux["flexion"], 0.813, places=3)
        self.assertAlmostEqual(taux["cisaillement"], 0.396, places=3)
        self.assertAlmostEqual(
            taux["compression perpendiculaire (kc,90 = 1,0)"],
            0.887,
            places=3,
        )

    def test_steico_utilise_les_resistances_et_rigidites_eta(self) -> None:
        rapport = self.atelier.verifier_structure(
            HypothesesEurocode5(charge_ponctuelle_solive_kN=0)
        )
        solive = {
            verification.critere: verification
            for verification in rapport.verifications
            if verification.element == "STEICOjoist SJ60/240"
        }

        self.assertAlmostEqual(
            solive["moment résistant"].capacite,
            0.8 * 12.94 / 1.2,
        )
        self.assertAlmostEqual(
            solive["effort tranchant résistant"].capacite,
            0.45 * 16.08 / 1.3,
        )
        self.assertEqual(
            solive["effort tranchant résistant"].statut,
            StatutVerification.CONFORME,
        )

    def test_charge_machine_peut_faire_echouer_une_solive(self) -> None:
        rapport = self.atelier.verifier_structure(
            HypothesesEurocode5(charge_ponctuelle_solive_kN=15)
        )

        self.assertTrue(
            any(
                verification.element == "STEICOjoist SJ60/240"
                and verification.statut is StatutVerification.NON_CONFORME
                for verification in rapport.verifications
            )
        )

    def test_poutres_de_rive_restent_non_verifiees_sans_charges_de_toiture(self) -> None:
        rapport = self.atelier.verifier_structure()

        self.assertTrue(
            any(
                verification.element.startswith("Poutres longitudinales")
                and verification.statut is StatutVerification.NON_VERIFIE
                for verification in rapport.verifications
            )
        )
        self.assertTrue(any("murs/toiture" in reserve for reserve in rapport.reserves))

    def test_poutres_de_rive_sont_calculees_quand_les_actions_sont_connues(self) -> None:
        rapport = self.atelier.verifier_structure(
            HypothesesEurocode5(
                charge_ponctuelle_solive_kN=0,
                charge_permanente_mur_toiture_kN_m=2,
                charge_variable_toiture_kN_m=1,
            )
        )

        rive = next(
            verification
            for verification in rapport.verifications
            if verification.element.startswith("Poutres longitudinales")
        )
        self.assertEqual(rive.statut, StatutVerification.CONFORME)
        self.assertIsNotNone(rive.taux_utilisation)

    def test_refuse_une_classe_de_service_non_couverte_par_eta(self) -> None:
        with self.assertRaisesRegex(ValueError, "classes de service 1 ou 2"):
            HypothesesEurocode5(classe_service=3)


if __name__ == "__main__":
    unittest.main()
