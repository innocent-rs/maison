import unittest

from optimiseur_poutres.calcul import HypothesesProjet, optimiser
from optimiseur_poutres.solives import (
    COUT_SABOT_EWH_EUR,
    HypothesesSolives,
    SOLIVES_FOURNISSEUR,
    evaluer_solives,
    optimiser_solives,
    optimiser_systeme_porteur,
)


class TestOptimiseurSolives(unittest.TestCase):
    def setUp(self) -> None:
        self.projet = HypothesesProjet(longueur_m=10, largeur_m=10)
        self.support = optimiser(self.projet).meilleure
        self.assertIsNotNone(self.support)
        self.hypotheses = HypothesesSolives()

    def test_catalogue_reproduit_les_trois_references_vendues(self) -> None:
        self.assertEqual(
            [s.nom for s in SOLIVES_FOURNISSEUR],
            ["SJ60/240", "SJ60/300", "SJ90/360"],
        )
        sj60_240 = SOLIVES_FOURNISSEUR[0]
        self.assertEqual(sj60_240.prix_eur_m, 14.10)
        self.assertEqual(sj60_240.ei_moyen_kNm2, 709)
        self.assertEqual(sj60_240.ga_moyen_MN, 3.18)

    def test_portee_des_solives_est_entraxe_des_principales(self) -> None:
        resultat = optimiser_solives(self.projet, self.hypotheses, self.support)

        self.assertIsNotNone(resultat.meilleure)
        self.assertAlmostEqual(resultat.meilleure.portee_m, self.support.entraxe_m)
        self.assertLessEqual(resultat.meilleure.entraxe_mm, 625)

    def test_segments_sabots_longueur_et_cout_sont_coherents(self) -> None:
        resultat = evaluer_solives(
            self.projet,
            self.hypotheses,
            self.support,
            SOLIVES_FOURNISSEUR[0],
            nombre_lignes_solives=18,
        )

        self.assertEqual(
            resultat.nombre_segments,
            18 * (self.support.nombre_poutres - 1),
        )
        self.assertEqual(resultat.nombre_sabots, 2 * resultat.nombre_segments)
        self.assertAlmostEqual(
            resultat.cout_sabots_eur,
            resultat.nombre_sabots * COUT_SABOT_EWH_EUR,
        )
        self.assertAlmostEqual(
            resultat.longueur_totale_m,
            18 * self.support.largeur_repartie_m,
        )

    def test_rapprocher_les_solives_reduit_les_taux(self) -> None:
        section = SOLIVES_FOURNISSEUR[0]
        large = evaluer_solives(
            self.projet, self.hypotheses, self.support, section, 18
        )
        serre = evaluer_solives(
            self.projet, self.hypotheses, self.support, section, 26
        )

        self.assertLess(serre.taux_flexion, large.taux_flexion)
        self.assertLess(serre.taux_cisaillement, large.taux_cisaillement)
        self.assertLess(serre.taux_fleche, large.taux_fleche)

    def test_classe_de_service_2_est_plus_severe_en_cisaillement(self) -> None:
        section = SOLIVES_FOURNISSEUR[0]
        classe_1 = evaluer_solives(
            self.projet,
            HypothesesSolives(classe_service=1),
            self.support,
            section,
            18,
        )
        classe_2 = evaluer_solives(
            self.projet,
            HypothesesSolives(classe_service=2),
            self.support,
            section,
            18,
        )

        self.assertGreater(classe_2.taux_cisaillement, classe_1.taux_cisaillement)

    def test_cas_10x10_produit_une_solution_complete(self) -> None:
        resultat = optimiser_solives(self.projet, self.hypotheses, self.support)
        meilleure = resultat.meilleure

        self.assertIsNotNone(meilleure)
        self.assertEqual(meilleure.section.nom, "SJ60/240")
        self.assertEqual(meilleure.nombre_lignes_solives, 17)
        self.assertEqual(meilleure.nombre_segments, 51)
        self.assertEqual(meilleure.nombre_sabots, 102)
        self.assertTrue(meilleure.conforme)
        self.assertEqual(meilleure.largeur_vide_isolant_mm, 565)
        self.assertEqual(meilleure.compression_isolant_mm, 10)
        self.assertTrue(meilleure.isolant_compatible)
        self.assertGreater(meilleure.frequence_propre_hz, 0)
        self.assertGreater(meilleure.fleche_sous_1kn_mm, 0)
        self.assertEqual(resultat.meilleure_confort.section.nom, "SJ60/300")
        self.assertLessEqual(resultat.meilleure_confort.taux_vibration, 1)
        self.assertGreater(resultat.meilleure_confort.cout_eur, meilleure.cout_eur)
        self.assertEqual(
            resultat.meilleure_confort.depassement_sous_principale_mm,
            resultat.meilleure_confort.section.hauteur_mm
            - self.support.section.hauteur_mm,
        )

    def test_isolant_600_signale_une_recoupe_avec_entraxe_625(self) -> None:
        resultat = optimiser_solives(
            self.projet,
            HypothesesSolives(largeur_isolant_mm=600),
            self.support,
        )

        self.assertEqual(resultat.meilleure.largeur_vide_isolant_mm, 565)
        self.assertEqual(resultat.meilleure.compression_isolant_mm, 35)
        self.assertFalse(resultat.meilleure.isolant_compatible)

    def test_poids_des_solives_est_reinjecte_dans_les_principales(self) -> None:
        systeme = optimiser_systeme_porteur(self.projet, self.hypotheses)

        self.assertGreater(systeme.masse_solives_kg_m2, 0)
        self.assertIsNotNone(systeme.principales.meilleure)
        self.assertIsNotNone(systeme.solives)
        self.assertIsNotNone(systeme.solives.meilleure)
        self.assertEqual(systeme.principales.meilleure.section.nom, "120 × 240")
        self.assertTrue(systeme.principales.meilleure.conforme)

    def test_refuse_un_catalogue_vide(self) -> None:
        with self.assertRaises(ValueError):
            optimiser_solives(self.projet, self.hypotheses, self.support, [])


if __name__ == "__main__":
    unittest.main()
