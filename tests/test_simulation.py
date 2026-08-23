import unittest

from maison.geometrie import GeometrieAFrame
from maison.simulation import (
    CasAssemblage,
    CasCharge,
    charge_permanente_surfacique,
    simuler_plancher,
)
from maison.structure import PlancherAFrame


class TestSimulationPlancher(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plancher = PlancherAFrame(
            GeometrieAFrame(
                largeur_interieure=4_000,
                surface_plancher_max=20,
                longueur_interieure_imposee=4_800,
            ),
            section_largeur=120,
            section_hauteur=240,
            nombre_traverses=3,
            entraxe_solives_i_max=573,
            hauteur_solives_i=240,
            largeur_membrure_solives_i=60,
            epaisseur_isolant_nominale=145,
            caissons_uniformes=True,
            inclure_connecteurs=True,
            inclure_solives_i=True,
            inclure_osb_caissons=True,
            inclure_isolant_caissons=True,
            inclure_osb_plancher=True,
        )
        cls.resultats = {
            (assemblage, charge): simuler_plancher(
                cls.plancher, assemblage, cas_charge=charge
            )
            for assemblage in CasAssemblage
            for charge in CasCharge
        }

    def test_poids_des_couches_du_plancher_fini(self) -> None:
        # OSB 12 + 22 mm à 600 kg/m³ et Isonat 145 mm à 55 kg/m³.
        self.assertAlmostEqual(
            charge_permanente_surfacique(self.plancher), 0.27835875, places=8
        )

    def test_charge_de_service_equilibree(self) -> None:
        resultat = self.resultats[(CasAssemblage.ARTICULE, CasCharge.SERVICE)]

        self.assertTrue(resultat.convergence)
        self.assertAlmostEqual(
            resultat.somme_reactions_z_n, resultat.charge_totale_n, places=5
        )
        self.assertAlmostEqual(resultat.charge_totale_n, 37_981.066804992, places=5)
        self.assertGreater(resultat.reaction_max_z_n, 0)

    def test_cas_de_service_est_la_somme_lineaire_de_g_et_q(self) -> None:
        cle = CasAssemblage.ARTICULE
        permanente = self.resultats[(cle, CasCharge.PERMANENTE)]
        exploitation = self.resultats[(cle, CasCharge.EXPLOITATION)]
        service = self.resultats[(cle, CasCharge.SERVICE)]

        self.assertAlmostEqual(
            service.charge_totale_n,
            permanente.charge_totale_n + exploitation.charge_totale_n,
            places=5,
        )
        self.assertAlmostEqual(
            service.fleche_relative_poutres_rive_max_mm,
            permanente.fleche_relative_poutres_rive_max_mm
            + exploitation.fleche_relative_poutres_rive_max_mm,
            places=5,
        )

    def test_les_douze_solives_sont_maillees_en_deux(self) -> None:
        resultat = self.resultats[(CasAssemblage.ARTICULE, CasCharge.SERVICE)]

        self.assertEqual(self.plancher.nombre_solives_i, 12)
        self.assertEqual(resultat.nombre_elements_solives_i, 24)
        self.assertGreater(resultat.nombre_elements, resultat.nombre_elements_solives_i)

    def test_connecteurs_articules_assouplissent_les_traverses(self) -> None:
        rigide = self.resultats[(CasAssemblage.RIGIDE, CasCharge.SERVICE)]
        articule = self.resultats[(CasAssemblage.ARTICULE, CasCharge.SERVICE)]

        self.assertGreater(
            articule.fleche_relative_traverses_max_mm,
            rigide.fleche_relative_traverses_max_mm,
        )

    def test_solives_i_sous_la_limite_indicative(self) -> None:
        resultat = self.resultats[(CasAssemblage.ARTICULE, CasCharge.SERVICE)]

        self.assertTrue(resultat.respecte_limite_fleche_solives_i)
        self.assertLess(resultat.taux_fleche_solives_i, 1)

    def test_poutres_de_rive_sont_le_point_dimensionnant_en_fleche(self) -> None:
        resultat = self.resultats[(CasAssemblage.ARTICULE, CasCharge.SERVICE)]

        self.assertTrue(resultat.respecte_limite_fleche_poutres_rive)
        self.assertGreater(
            resultat.taux_fleche_poutres_rive,
            resultat.taux_fleche_traverses,
        )
        self.assertGreater(
            resultat.taux_fleche_poutres_rive,
            resultat.taux_fleche_solives_i,
        )


if __name__ == "__main__":
    unittest.main()
