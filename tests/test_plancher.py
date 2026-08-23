import unittest

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


class TestPlancherAFrame(unittest.TestCase):
    def test_chassis_primaire(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())

        self.assertEqual(plancher.nombre_traverses, 3)
        self.assertEqual(len(plancher.elements()), 5)
        self.assertAlmostEqual(
            plancher.entraxe_traverses,
            (plancher.geometrie.longueur_interieure - plancher.section_largeur) / 2,
        )
        self.assertEqual(
            [element.nom for element in plancher.elements()[2:5]],
            ["Traverse haute", "Traverse milieu", "Traverse basse"],
        )
    def test_solives_i_optionnelles(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame(), inclure_solives_i=True)

        self.assertEqual(plancher.nombre_solives_i, 11)
        self.assertLessEqual(plancher.entraxe_solives_i, 500)
        self.assertEqual(len(plancher.elements()), 5 + plancher.nombre_solives_i)

    def test_encombrement(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())
        boites = [element.forme.bounding_box() for element in plancher.elements()]

        xmin = min(boite.min.X for boite in boites)
        xmax = max(boite.max.X for boite in boites)
        ymin = min(boite.min.Y for boite in boites)
        ymax = max(boite.max.Y for boite in boites)

        self.assertAlmostEqual(xmin, 0)
        self.assertAlmostEqual(xmax, plancher.geometrie.longueur_interieure)
        self.assertAlmostEqual(ymin, -plancher.geometrie.largeur_interieure / 2)
        self.assertAlmostEqual(ymax, plancher.geometrie.largeur_interieure / 2)

    def test_sections_et_assemblages(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())
        poutre_gauche, _, traverse_haute, traverse_milieu, _ = plancher.elements()

        self.assertEqual(
            (
                poutre_gauche.piece.largeur,
                poutre_gauche.piece.hauteur,
            ),
            (120, 250),
        )
        self.assertLess(
            poutre_gauche.forme.volume,
            poutre_gauche.piece.construire().volume,
        )
        self.assertLess(
            traverse_haute.forme.volume,
            traverse_haute.piece.construire().volume,
        )
        self.assertEqual(traverse_milieu.piece.longueur, 6_000)
        self.assertEqual(plancher.niveau_haut_traverses, 250)


if __name__ == "__main__":
    unittest.main()
