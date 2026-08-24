import unittest

from maison.assemblage import AssemblageContraint, DecalageParallele, PieceInstance
from maison.structure.bois import Madrier


class TestAssemblageContraint(unittest.TestCase):
    def test_refuse_une_reference_inconnue(self) -> None:
        with self.assertRaisesRegex(ValueError, "référence inconnue"):
            AssemblageContraint(
                (
                    PieceInstance(
                        "mobile",
                        "Pièce mobile",
                        Madrier(1_000),
                        DecalageParallele("absente", (0, 1_000, 0)),
                        "brown",
                    ),
                )
            )

    def test_detecte_un_cycle_de_contraintes(self) -> None:
        with self.assertRaisesRegex(ValueError, "cycle de contraintes"):
            AssemblageContraint(
                (
                    PieceInstance(
                        "a",
                        "Pièce A",
                        Madrier(1_000),
                        DecalageParallele("b", (0, 1_000, 0)),
                        "brown",
                    ),
                    PieceInstance(
                        "b",
                        "Pièce B",
                        Madrier(1_000),
                        DecalageParallele("a", (0, -1_000, 0)),
                        "brown",
                    ),
                )
            )


if __name__ == "__main__":
    unittest.main()
