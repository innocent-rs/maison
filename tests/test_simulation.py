import unittest

from main import make_part
from maison.simulation import CasAssemblage, simuler_plancher


class TestSimulationPlancher(unittest.TestCase):
    def test_charge_equilibree(self) -> None:
        resultat = simuler_plancher(make_part(), CasAssemblage.RIGIDE)

        self.assertTrue(resultat.convergence)
        self.assertAlmostEqual(resultat.somme_reactions_z_n, 1_000, places=5)
        self.assertGreater(resultat.fleche_max_mm, 0)

    def test_connecteurs_articules_plus_souples(self) -> None:
        rigide = simuler_plancher(make_part(), CasAssemblage.RIGIDE)
        articule = simuler_plancher(make_part(), CasAssemblage.ARTICULE)

        self.assertGreater(articule.fleche_max_mm, rigide.fleche_max_mm)

    def test_connecteurs_articules_convergent(self) -> None:
        resultat = simuler_plancher(make_part(), CasAssemblage.ARTICULE)

        self.assertTrue(resultat.convergence)
        self.assertAlmostEqual(resultat.somme_reactions_z_n, 1_000, places=5)


if __name__ == "__main__":
    unittest.main()
