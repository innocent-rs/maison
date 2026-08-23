import unittest

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


class TestPlancherAFrame(unittest.TestCase):
    def test_entraxe_et_nombre_elements(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())

        self.assertLessEqual(plancher.entraxe_reel, 600)
        self.assertEqual(len(plancher.elements()), plancher.nombre_solives + 2)

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


if __name__ == "__main__":
    unittest.main()
