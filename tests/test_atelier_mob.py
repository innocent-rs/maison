import unittest

from atelier_mob import (
    EntretoisePoutreI,
    FondationsPieuxVisses,
    GeometrieAtelierMob,
    Madrier,
    PlatinePieuVisse,
    PoutreI,
    creer_atelier_mob,
)


class TestFondationsAtelierMob(unittest.TestCase):
    def test_platine_est_un_volume_acier_200_par_200_par_5(self) -> None:
        platine = PlatinePieuVisse()
        forme = platine.construire()

        self.assertEqual(
            (platine.longueur, platine.largeur, platine.epaisseur),
            (200, 200, 5),
        )
        self.assertAlmostEqual(forme.volume, 200 * 200 * 5)
        self.assertAlmostEqual(forme.bounding_box().min.Z, -5)
        self.assertAlmostEqual(forme.bounding_box().max.Z, 0)

    def test_fondations_ne_modelisent_que_les_platines_implantees(self) -> None:
        positions = ((-1_000, -500), (1_000, -500), (0, 500))
        fondations = FondationsPieuxVisses(positions_platines=positions)

        self.assertEqual(fondations.nombre_platines, 3)
        self.assertEqual(len(fondations.elements()), 3)
        ligne = fondations.nomenclature_achats().lignes[0]
        self.assertEqual(ligne.quantite, 3)
        self.assertEqual(ligne.article.materiau, "Acier")

    def test_configuration_initiale_aligne_les_pieux_sur_les_traverses(self) -> None:
        atelier = creer_atelier_mob()

        self.assertEqual(atelier.fondations.nombre_platines, 24)
        self.assertEqual(
            {x for x, _ in atelier.fondations.positions_platines},
            set(atelier.plancher.axes_traverses()),
        )
        self.assertEqual(
            {y for _, y in atelier.fondations.positions_platines},
            {-3_440, 0, 3_440},
        )

    def test_trame_automatique_peut_etre_desactivee(self) -> None:
        atelier = creer_atelier_mob(positions_platines=())

        self.assertEqual(atelier.fondations.elements(), ())

    def test_refuse_deux_platines_sur_le_meme_axe(self) -> None:
        with self.assertRaisesRegex(ValueError, "même axe"):
            FondationsPieuxVisses(positions_platines=((0, 0), (0, 0)))

    def test_emprise_rectangulaire_de_7m_par_15m(self) -> None:
        geometrie = GeometrieAtelierMob()

        self.assertEqual(geometrie.largeur_interieure, 7_000)
        self.assertEqual(geometrie.longueur_interieure, 15_000)
        self.assertAlmostEqual(geometrie.surface_plancher, 105)

    def test_plancher_complet_en_madriers_et_poutres_i(self) -> None:
        atelier = creer_atelier_mob()
        plancher = atelier.plancher

        self.assertEqual(plancher.nombre_traverses, 8)
        self.assertEqual(plancher.nombre_lignes_solives_i, 11)
        self.assertEqual(plancher.nombre_solives_i, 77)
        self.assertLessEqual(plancher.entraxe_solives_i, 573)
        self.assertAlmostEqual(plancher.longueur_solives_i, 1_999.142857, places=5)
        self.assertTrue(plancher.inclure_osb_caissons)
        self.assertTrue(plancher.inclure_entretoises_solives_i)
        self.assertEqual(plancher.nombre_entretoises_solives_i, 84)
        self.assertTrue(plancher.inclure_isolant_caissons)
        self.assertTrue(plancher.inclure_osb_plancher)

        pieces = plancher.assemblage_poutres().pieces
        self.assertEqual(sum(isinstance(piece.piece, Madrier) for piece in pieces), 10)
        self.assertEqual(sum(isinstance(piece.piece, PoutreI) for piece in pieces), 77)

    def test_composition_et_calepinage_du_plancher(self) -> None:
        plancher = creer_atelier_mob().plancher

        self.assertEqual(plancher.epaisseur_osb_caissons, 12)
        self.assertEqual(plancher.epaisseur_isolant_nominale, 145)
        self.assertEqual(plancher.epaisseur_osb_plancher, 22)
        self.assertEqual(plancher.nombre_panneaux_osb_caissons, 168)
        self.assertEqual(plancher.nombre_panneaux_isolant, 168)
        self.assertEqual(plancher.nombre_panneaux_osb_plancher, 98)

    def test_entretoises_coupent_les_caissons_sans_collision(self) -> None:
        plancher = creer_atelier_mob().plancher
        elements = plancher.elements()
        entretoises = [
            element
            for element in elements
            if isinstance(element.piece, EntretoisePoutreI)
        ]
        contenus_caissons = [
            element
            for element in elements
            if element.nom.startswith(("Fond OSB", "Isolant Isonat"))
        ]

        self.assertEqual(len(entretoises), 84)
        self.assertEqual(
            {round(element.forme.bounding_box().size.Y) for element in entretoises},
            {504, 530},
        )

        def boites_se_chevauchent(gauche, droite) -> bool:
            a = gauche.bounding_box()
            b = droite.bounding_box()
            return not (
                a.max.X <= b.min.X
                or a.min.X >= b.max.X
                or a.max.Y <= b.min.Y
                or a.min.Y >= b.max.Y
                or a.max.Z <= b.min.Z
                or a.min.Z >= b.max.Z
            )

        self.assertTrue(
            all(
                not boites_se_chevauchent(entretoise.forme, contenu.forme)
                or (entretoise.forme & contenu.forme).volume < 1e-6
                for entretoise in entretoises
                for contenu in contenus_caissons
            )
        )
        self.assertEqual(plancher.nombre_pointes_entretoises_2_5x80, 168)
        self.assertEqual(plancher.nombre_pointes_entretoises_3_1x90, 168)


if __name__ == "__main__":
    unittest.main()
