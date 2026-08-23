import unittest

from maison.geometrie import GeometrieAFrame
from maison.simulation import CasAssemblage, simuler_plancher
from maison.structure import PlancherAFrame


class TestSimulationPlancher(unittest.TestCase):
    def plancher_avec_connecteurs(self) -> PlancherAFrame:
        return PlancherAFrame(
            GeometrieAFrame(
                largeur_interieure=4_000,
                surface_plancher_max=20,
                longueur_interieure_imposee=4_800,
            ),
            nombre_traverses=5,
            inclure_connecteurs=True,
        )

    def test_charge_equilibree(self) -> None:
        resultat = simuler_plancher(
            self.plancher_avec_connecteurs(),
            CasAssemblage.RIGIDE,
        )

        self.assertTrue(resultat.convergence)
        self.assertAlmostEqual(resultat.somme_reactions_z_n, 1_000, places=5)
        self.assertGreater(resultat.fleche_max_mm, 0)

    def test_connecteurs_articules_plus_souples(self) -> None:
        plancher = self.plancher_avec_connecteurs()
        rigide = simuler_plancher(plancher, CasAssemblage.RIGIDE)
        articule = simuler_plancher(plancher, CasAssemblage.ARTICULE)

        self.assertGreater(articule.fleche_max_mm, rigide.fleche_max_mm)

    def test_connecteurs_articules_convergent(self) -> None:
        resultat = simuler_plancher(
            self.plancher_avec_connecteurs(),
            CasAssemblage.ARTICULE,
        )

        self.assertTrue(resultat.convergence)
        self.assertAlmostEqual(resultat.somme_reactions_z_n, 1_000, places=5)


if __name__ == "__main__":
    unittest.main()
