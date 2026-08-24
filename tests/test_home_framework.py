import unittest
from pathlib import Path

from build123d import Location

from home_framework.assemblage import AssemblageContraint, ComposantLineaire
from home_framework.nomenclature import ArticleBOM
from maison.assemblage import AssemblageContraint as AssemblageHistorique
from maison.nomenclature import ArticleBOM as ArticleHistorique
from home_framework.structure.bois import Madrier


class TestFrontiereHomeFramework(unittest.TestCase):
    def test_framework_ne_depend_d_aucun_projet(self) -> None:
        racine = Path(__file__).parents[1] / "home_framework"
        sources = "\n".join(
            chemin.read_text(encoding="utf-8")
            for chemin in racine.rglob("*.py")
        )

        self.assertNotIn("from maison", sources)
        self.assertNotIn("from local_batteries", sources)
        self.assertNotIn("from catalogues", sources)

    def test_projets_ne_se_dependant_pas_mutuellement(self) -> None:
        racine = Path(__file__).parents[1]
        sources_maison = "\n".join(
            chemin.read_text(encoding="utf-8")
            for chemin in (racine / "maison").rglob("*.py")
        )
        sources_local = "\n".join(
            chemin.read_text(encoding="utf-8")
            for chemin in (racine / "local_batteries").rglob("*.py")
        )

        self.assertNotIn("from local_batteries", sources_maison)
        self.assertNotIn("from maison", sources_local)

    def test_anciens_imports_restent_des_facades_compatibles(self) -> None:
        self.assertIs(AssemblageHistorique, AssemblageContraint)
        self.assertIs(ArticleHistorique, ArticleBOM)

    def test_composant_lineaire_porte_ses_joints_intrinseques(self) -> None:
        composant = ComposantLineaire(Madrier(1_000), label="test")
        autre = ComposantLineaire(Madrier(1_000), label="autre")

        self.assertEqual(set(composant.joints), {"origine", "debut", "fin"})
        self.assertEqual(tuple(composant.joints["debut"].location.position), (0, 0, 0))
        self.assertEqual(tuple(composant.joints["fin"].location.position), (1_000, 0, 0))

        composant.locate(Location((100, 200, 300)))
        self.assertEqual(
            tuple(composant.joints["fin"].location.position),
            (1_100, 200, 300),
        )
        self.assertEqual(
            tuple(autre.joints["fin"].location.position),
            (1_000, 0, 0),
        )


if __name__ == "__main__":
    unittest.main()
