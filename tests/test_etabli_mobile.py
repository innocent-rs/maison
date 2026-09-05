import unittest
from itertools import combinations

from etabli_mobile import (
    ChassisEtabliMobile,
    ModuleQbrickOne,
    PlateauContreplaque,
    ProfileAluminium45x90,
    RenfortDiagonal45x90,
    creer_etabli_mobile,
)


class TestEtabliMobile(unittest.TestCase):
    def test_configuration_initiale_est_le_cadre_bas_de_1700_mm(self) -> None:
        etabli = creer_etabli_mobile()

        self.assertEqual(
            (etabli.chassis.longueur, etabli.chassis.profondeur),
            (1_700, 385),
        )
        self.assertFalse(hasattr(etabli, "famille_rangement"))
        self.assertFalse(hasattr(etabli.chassis, "hauteur"))
        self.assertEqual(
            (etabli.chassis.largeur_profile, etabli.chassis.hauteur_profile),
            (45, 90),
        )

    def test_longueur_superieure_a_1700_mm_est_refusee(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 700"):
            creer_etabli_mobile(longueur=1_701)

    def test_chassis_contient_deux_traverses_qbrick_et_douze_renforts(self) -> None:
        chassis = ChassisEtabliMobile()

        self.assertEqual(len(chassis.elements_perimetre()), 4)
        traverses = chassis.elements_traverses_qbrick()
        self.assertEqual(len(traverses), 2)
        self.assertEqual(
            [traverse.forme.center().X for traverse in traverses],
            [-287.5, 287.5],
        )
        self.assertTrue(
            all(traverse.piece.longueur == 295 for traverse in traverses)
        )
        self.assertEqual(len(chassis.elements_renforts()), 12)
        self.assertEqual(len(chassis.elements()), 18)

    def test_aucune_coupe_ne_depasse_la_longueur_transportable(self) -> None:
        chassis = ChassisEtabliMobile()

        self.assertLessEqual(
            max(element.piece.longueur for element in chassis.elements()),
            1_700,
        )

    def test_renforts_couvrent_angles_et_traverses_qbrick(self) -> None:
        noms = {element.nom for element in ChassisEtabliMobile().elements_renforts()}

        self.assertEqual(
            noms,
            {
                "Renfort angle avant gauche",
                "Renfort angle arrière gauche",
                "Renfort angle avant droit",
                "Renfort angle arrière droit",
                "Renfort traverse Qbrick 1 avant gauche",
                "Renfort traverse Qbrick 1 arrière gauche",
                "Renfort traverse Qbrick 1 avant droit",
                "Renfort traverse Qbrick 1 arrière droit",
                "Renfort traverse Qbrick 2 avant gauche",
                "Renfort traverse Qbrick 2 arrière gauche",
                "Renfort traverse Qbrick 2 avant droit",
                "Renfort traverse Qbrick 2 arrière droit",
            },
        )

    def test_renforts_ont_deux_coupes_a_45_degres(self) -> None:
        renforts = ChassisEtabliMobile().elements_renforts()

        self.assertTrue(
            all(
                isinstance(element.piece, RenfortDiagonal45x90)
                and element.piece.angle_coupes_degres == 45
                and abs(element.piece.longueur_axe - 115 * 2**0.5) < 1e-6
                and abs(element.piece.longueur - (115 * 2**0.5 + 45)) < 1e-6
                for element in renforts
            )
        )

    def test_renforts_ne_se_croisent_pas(self) -> None:
        renforts = ChassisEtabliMobile().elements_renforts()

        self.assertTrue(
            all(
                (gauche.forme & droite.forme).volume < 1e-6
                for gauche, droite in combinations(renforts, 2)
            )
        )

    def test_huit_roues_sont_alignees_sur_les_quatre_traverses(self) -> None:
        chassis = ChassisEtabliMobile()

        self.assertEqual(len(chassis.positions_roues()), 8)
        self.assertEqual(
            {x for x, _ in chassis.positions_roues()},
            {-827.5, -287.5, 287.5, 827.5},
        )
        self.assertEqual(
            {y for _, y in chassis.positions_roues()},
            {-170, 170},
        )

    def test_enveloppe_complete_respecte_les_dimensions(self) -> None:
        chassis = ChassisEtabliMobile()
        formes = [element.forme for element in chassis.elements()]
        xmin = min(forme.bounding_box().min.X for forme in formes)
        xmax = max(forme.bounding_box().max.X for forme in formes)
        ymin = min(forme.bounding_box().min.Y for forme in formes)
        ymax = max(forme.bounding_box().max.Y for forme in formes)
        zmin = min(forme.bounding_box().min.Z for forme in formes)
        zmax = max(forme.bounding_box().max.Z for forme in formes)

        self.assertAlmostEqual(xmax - xmin, 1_700)
        self.assertAlmostEqual(ymax - ymin, 385)
        self.assertAlmostEqual(zmax - zmin, 90)

    def test_nomenclature_inclut_les_renforts(self) -> None:
        etabli = creer_etabli_mobile()

        self.assertEqual(etabli.nomenclature_chassis().nombre_pieces, 18)
        self.assertEqual(etabli.nomenclature_achats().nombre_pieces, 22)
        self.assertEqual(len(etabli.nomenclature_achats().lignes), 5)

    def test_cp_est_limite_aux_deux_empreintes_qbrick(self) -> None:
        etabli = creer_etabli_mobile()
        supports = etabli.elements_plateaux_qbrick()

        self.assertEqual(len(supports), 2)
        self.assertTrue(
            all(
                isinstance(element.piece, PlateauContreplaque)
                for element in supports
            )
        )
        self.assertEqual(
            [
                (
                    element.piece.longueur,
                    element.piece.profondeur,
                    element.piece.epaisseur,
                )
                for element in supports
            ],
            [(585, 385, 12), (585, 385, 12)],
        )
        self.assertEqual(
            [element.forme.center().X for element in supports],
            [-557.5, 557.5],
        )
        traverses = etabli.chassis.elements_traverses_qbrick()
        faces_interieures_traverses_x = [
            traverses[0].forme.bounding_box().max.X,
            traverses[1].forme.bounding_box().min.X,
        ]
        aretes_interieures_x = [
            supports[0].forme.bounding_box().max.X,
            supports[1].forme.bounding_box().min.X,
        ]
        self.assertEqual(faces_interieures_traverses_x, aretes_interieures_x)
        self.assertTrue(
            all(element.forme.bounding_box().min.Z == 90 for element in supports)
        )
        self.assertTrue(
            all(element.forme.bounding_box().max.Z == 102 for element in supports)
        )
        self.assertAlmostEqual(
            sum(plateau.masse_kg for plateau in etabli.plateaux_qbrick),
            3.51351,
        )

    def test_deux_qbrick_one_occupent_les_deux_moitiees_du_chassis(self) -> None:
        etabli = creer_etabli_mobile()
        modules = etabli.elements_qbrick_one()

        self.assertEqual(len(modules), 2)
        self.assertTrue(
            all(isinstance(element.piece, ModuleQbrickOne) for element in modules)
        )
        self.assertEqual(
            [
                (
                    element.piece.longueur,
                    element.piece.profondeur,
                    element.piece.hauteur,
                )
                for element in modules
            ],
            [(585, 385, 301), (585, 385, 301)],
        )
        self.assertEqual(
            [element.forme.center().X for element in modules],
            [-557.5, 557.5],
        )
        self.assertEqual(
            [
                (
                    element.forme.bounding_box().min.X,
                    element.forme.bounding_box().max.X,
                )
                for element in modules
            ],
            [(-850, -265), (265, 850)],
        )
        self.assertTrue(
            all(element.forme.bounding_box().min.Z == 102 for element in modules)
        )

    def test_masse_structure_connue_inclut_les_deux_supports_cp(self) -> None:
        etabli = creer_etabli_mobile()

        self.assertAlmostEqual(
            etabli.masse_structure_connue_kg,
            etabli.chassis.masse_profiles_kg + 3.51351,
        )

    def test_poids_profiles_est_chiffre_avec_une_hypothese_parametrable(self) -> None:
        chassis = ChassisEtabliMobile()
        longueur_debit_mm = 2 * 1_700 + 4 * 295 + 12 * (115 * 2**0.5 + 45)
        longueur_equivalente_masse_mm = 2 * 1_700 + 4 * 295 + 12 * 115 * 2**0.5

        self.assertAlmostEqual(chassis.longueur_totale_debit_mm, longueur_debit_mm)
        self.assertAlmostEqual(
            chassis.masse_profiles_kg,
            longueur_equivalente_masse_mm / 1_000 * 3,
        )
        self.assertAlmostEqual(
            ChassisEtabliMobile(masse_lineique_kg_m=2).masse_profiles_kg,
            longueur_equivalente_masse_mm / 1_000 * 2,
        )

    def test_dimensions_invalides_sont_refusees(self) -> None:
        with self.assertRaisesRegex(ValueError, "longueur"):
            ChassisEtabliMobile(longueur=90)
        with self.assertRaisesRegex(ValueError, "longueur"):
            ProfileAluminium45x90(0)
        with self.assertRaisesRegex(ValueError, "chevaucheraient"):
            ChassisEtabliMobile(recul_renfort_angle=400)
        with self.assertRaisesRegex(ValueError, "se croiseraient"):
            ChassisEtabliMobile(recul_renfort_angle=116)


if __name__ == "__main__":
    unittest.main()
