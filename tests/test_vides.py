import unittest

from build123d import Align, Box, Pos

from home_framework import detecter_vides


class TestDetectionGeneriqueVides(unittest.TestCase):
    def test_soustrait_des_formes_sans_connaitre_leur_type(self) -> None:
        alignement = (Align.MIN, Align.MIN, Align.MIN)
        enveloppe = Box(10, 4, 4, align=alignement)
        cloison = Pos(4.5, 0, 0) * Box(1, 4, 4, align=alignement)

        rapport = detecter_vides(enveloppe, (cloison,))

        self.assertEqual(rapport.nombre_occupants, 1)
        self.assertEqual(rapport.nombre_composantes, 2)
        self.assertAlmostEqual(rapport.volume_enveloppe_m3, 160 / 1e9)
        self.assertAlmostEqual(rapport.volume_vide_m3, 144 / 1e9)
        self.assertAlmostEqual(rapport.taux_vide_pct, 90)

    def test_ignore_automatiquement_les_solides_exterieurs(self) -> None:
        enveloppe = Box(10, 10, 10)
        occupant_exterieur = Pos(100, 100, 100) * Box(2, 2, 2)

        rapport = detecter_vides(enveloppe, (occupant_exterieur,))

        self.assertEqual(rapport.nombre_occupants, 0)
        self.assertEqual(rapport.nombre_composantes, 1)
        self.assertAlmostEqual(rapport.volume_vide_m3, enveloppe.volume / 1e9)

    def test_refuse_une_enveloppe_sans_volume(self) -> None:
        with self.assertRaisesRegex(ValueError, "volume positif"):
            detecter_vides(Box(1, 1, 1).faces()[0], ())


if __name__ == "__main__":
    unittest.main()
