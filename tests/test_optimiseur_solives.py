import unittest

from optimiseur_poutres.calcul import HypothesesProjet, SECTIONS_FOURNISSEUR, optimiser
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
        self.assertTrue(resultat.meilleure_confort.assemblage_standard_compatible)
        self.assertEqual(
            resultat.meilleure_confort.depassement_sous_principale_mm,
            max(
                0,
                resultat.meilleure_confort.section.hauteur_mm
                - self.support.section.hauteur_mm,
            ),
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

    def test_module_isolant_est_conserve_et_reliquat_reporte_en_rive(self) -> None:
        projet = HypothesesProjet(
            longueur_m=6,
            largeur_m=10,
            orientation="longueur",
        )
        support = optimiser(projet).meilleure
        self.assertIsNotNone(support)

        resultat = optimiser_solives(
            projet,
            HypothesesSolives(largeur_isolant_mm=575, entraxe_max_mm=625),
            support,
        )
        meilleure = resultat.meilleure

        self.assertIsNotNone(meilleure)
        self.assertEqual(meilleure.nombre_lignes_solives, 11)
        self.assertEqual(meilleure.entraxe_mm, 625)
        self.assertEqual(meilleure.nombre_travees_modulaires, 9)
        self.assertEqual(meilleure.entraxes_rive_mm, (375,))
        self.assertEqual(meilleure.axes_mm[-1], 6_000)
        self.assertTrue(meilleure.isolant_compatible)
        self.assertFalse(meilleure.isolant_sans_recoupe)

    def test_isolant_600_utilise_le_module_650_si_autorise(self) -> None:
        resultat = optimiser_solives(
            self.projet,
            HypothesesSolives(largeur_isolant_mm=600, entraxe_max_mm=650),
            self.support,
        )
        meilleure = resultat.meilleure

        self.assertIsNotNone(meilleure)
        self.assertEqual(meilleure.entraxe_mm, 650)
        self.assertEqual(meilleure.compression_isolant_mm, 10)
        self.assertEqual(meilleure.nombre_travees_modulaires, 15)
        self.assertEqual(meilleure.entraxes_rive_mm, (250,))
        self.assertTrue(meilleure.isolant_compatible)

    def test_reliquat_trop_etroit_est_partage_entre_deux_rives(self) -> None:
        projet = HypothesesProjet(
            longueur_m=10.02,
            largeur_m=10,
            orientation="longueur",
        )
        support = optimiser(projet).meilleure
        self.assertIsNotNone(support)

        meilleure = optimiser_solives(
            projet,
            HypothesesSolives(largeur_isolant_mm=575, entraxe_max_mm=625),
            support,
        ).meilleure

        self.assertIsNotNone(meilleure)
        self.assertEqual(meilleure.entraxes_rive_mm, (322.5, 322.5))
        self.assertEqual(meilleure.nombre_travees_modulaires, 15)
        intervalles = tuple(
            droite - gauche
            for gauche, droite in zip(meilleure.axes_mm, meilleure.axes_mm[1:])
        )
        self.assertEqual(max(intervalles), meilleure.entraxe_mm)

    def test_depassement_ne_valide_pas_un_assemblage_standard(self) -> None:
        support_240 = optimiser(
            self.projet,
            sections=[SECTIONS_FOURNISSEUR[0]],
        ).meilleure
        self.assertIsNotNone(support_240)
        resultat = optimiser_solives(
            self.projet,
            self.hypotheses,
            support_240,
            [SOLIVES_FOURNISSEUR[1]],
        )

        self.assertIsNotNone(resultat.meilleure)
        self.assertGreater(resultat.meilleure.depassement_sous_principale_mm, 0)
        self.assertFalse(resultat.meilleure.assemblage_standard_compatible)

    def test_solive_300_fait_choisir_une_principale_assez_haute(self) -> None:
        systeme = optimiser_systeme_porteur(
            self.projet,
            self.hypotheses,
            sections_solives=[SOLIVES_FOURNISSEUR[1]],
        )

        self.assertIsNotNone(systeme.principales.meilleure)
        self.assertIsNotNone(systeme.solives)
        self.assertIsNotNone(systeme.solives.meilleure)
        self.assertGreaterEqual(systeme.principales.meilleure.section.hauteur_mm, 300)
        self.assertTrue(systeme.solives.meilleure.assemblage_standard_compatible)

    def test_13m50x10_atelier_exclut_le_c24_dans_le_systeme_complet(self) -> None:
        systeme = optimiser_systeme_porteur(
            HypothesesProjet(
                longueur_m=13.5,
                largeur_m=10,
                profil_usage="atelier",
                masse_permanente_kg_m2=100,
                masse_exploitation_kg_m2=250,
            ),
            self.hypotheses,
        )

        self.assertIsNotNone(systeme.principales.meilleure)
        self.assertEqual(systeme.principales.meilleure.section.nom, "140 × 320")
        self.assertEqual(systeme.principales.meilleure.portee_totale_m, 13.5)

    def test_poids_des_solives_est_reinjecte_dans_les_principales(self) -> None:
        systeme = optimiser_systeme_porteur(self.projet, self.hypotheses)

        self.assertGreater(systeme.masse_solives_kg_m2, 0)
        self.assertIsNotNone(systeme.principales.meilleure)
        self.assertIsNotNone(systeme.solives)
        self.assertIsNotNone(systeme.solives.meilleure)
        self.assertIn(systeme.principales.meilleure.section, SECTIONS_FOURNISSEUR)
        self.assertTrue(systeme.principales.meilleure.conforme)

    def test_24x12_depasse_toutes_les_longueurs_commerciales(self) -> None:
        projet = HypothesesProjet(longueur_m=24, largeur_m=12)

        systeme = optimiser_systeme_porteur(projet, self.hypotheses)

        self.assertIsNone(systeme.principales.meilleure)
        self.assertIsNone(systeme.solives)
        self.assertIsNone(systeme.cout_total_eur)

    def test_grand_plancher_sans_aboutage_n_a_pas_de_solution(self) -> None:
        projet = HypothesesProjet(longueur_m=30, largeur_m=20)

        systeme = optimiser_systeme_porteur(projet, self.hypotheses)

        self.assertIsNone(systeme.principales.meilleure)
        self.assertIsNone(systeme.solives)
        self.assertIsNone(systeme.cout_total_eur)

    def test_refuse_un_catalogue_vide(self) -> None:
        with self.assertRaises(ValueError):
            optimiser_solives(self.projet, self.hypotheses, self.support, [])


if __name__ == "__main__":
    unittest.main()
