import unittest
from decimal import Decimal

from home_framework.optimisation import PieceDebit, optimiser_debit


class TestOptimisationDebit(unittest.TestCase):
    def test_plan_optimal_des_cinq_poutres(self) -> None:
        pieces = [
            *(PieceDebit("MAD-L4800", "Madrier", 4_800) for _ in range(2)),
            *(PieceDebit("MAD-L3756", "Madrier", 3_756) for _ in range(3)),
        ]

        plan = optimiser_debit(pieces, longueur_stock_mm=13_500, trait_scie_mm=5)

        self.assertEqual(plan.nombre_barres, 2)
        self.assertEqual(plan.nombre_pieces, 5)
        self.assertEqual(plan.longueur_utile_mm, Decimal("20868"))
        self.assertEqual(plan.longueur_achetee_mm, Decimal("27000"))
        self.assertEqual(plan.longueur_traits_mm, Decimal("15"))
        self.assertEqual(plan.chute_totale_mm, Decimal("6117"))
        self.assertEqual(
            [tuple(piece.longueur_mm for piece in barre.pieces) for barre in plan.barres],
            [
                (Decimal("4800"), Decimal("4800"), Decimal("3756")),
                (Decimal("3756"), Decimal("3756")),
            ],
        )

    def test_refuse_une_piece_plus_longue_que_le_stock(self) -> None:
        with self.assertRaisesRegex(ValueError, "dépasse la longueur commerciale"):
            optimiser_debit(
                [PieceDebit("TROP-LONG", "Pièce trop longue", 13_501)],
                longueur_stock_mm=13_500,
            )

    def test_plan_vide_ne_consomme_aucune_barre(self) -> None:
        plan = optimiser_debit([], longueur_stock_mm=13_500, trait_scie_mm=5)

        self.assertEqual(plan.nombre_barres, 0)
        self.assertEqual(plan.longueur_achetee_mm, 0)


if __name__ == "__main__":
    unittest.main()
