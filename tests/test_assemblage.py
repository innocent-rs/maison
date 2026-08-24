import unittest

from home_framework.assemblage import (
    AssemblageContraint,
    DecalageParallele,
    PieceInstance,
    TrameEntreFaces,
)
from home_framework.structure.bois import Madrier


class TestAssemblageContraint(unittest.TestCase):
    def test_deploie_une_trame_cartesienne_declarative(self) -> None:
        trame = TrameEntreFaces(
            prefixe_identifiant="poutre",
            nom_piece="Poutre",
            piece=Madrier(900),
            couleur="brown",
            axes=(100, 200),
            appuis=(("a", "b"), ("b", "c")),
            axe_portee="X",
            jeu_about=3,
        )

        instances = trame.instances()

        self.assertEqual(
            [instance.identifiant for instance in instances],
            ["poutre_01_1", "poutre_01_2", "poutre_02_1", "poutre_02_2"],
        )
        self.assertEqual(
            [instance.contrainte.references for instance in instances],
            [("a", "b"), ("b", "c"), ("a", "b"), ("b", "c")],
        )

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
