import unittest
from itertools import pairwise

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


class TestPlancherAFrame(unittest.TestCase):
    def plancher_modulaire(
        self,
        inclure_osb_plancher: bool = False,
    ) -> PlancherAFrame:
        return PlancherAFrame(
            GeometrieAFrame(
                largeur_interieure=7_108,
                surface_plancher_max=20,
                longueur_interieure_imposee=2_804,
            ),
            entraxe_solives_i_max=573,
            trame_isolant_sans_decoupe=True,
            inclure_solives_i=True,
            inclure_osb_caissons=True,
            inclure_isolant_caissons=True,
            inclure_osb_plancher=inclure_osb_plancher,
        )

    def test_chassis_primaire(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())

        self.assertEqual(plancher.nombre_traverses, 3)
        self.assertEqual(len(plancher.elements()), 11)
        self.assertAlmostEqual(
            plancher.entraxe_traverses,
            (
                plancher.geometrie.longueur_interieure
                - plancher.section_largeur
                - 2 * plancher.retrait_connecteur_par_about
            )
            / 2,
        )
        self.assertEqual(
            [element.nom for element in plancher.elements()[2:5]],
            ["Traverse haute", "Traverse milieu", "Traverse basse"],
        )
    def test_solives_i_optionnelles(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame(), inclure_solives_i=True)

        self.assertEqual(plancher.nombre_lignes_solives_i, 11)
        self.assertEqual(plancher.nombre_solives_i, 22)
        self.assertLessEqual(plancher.entraxe_solives_i, 500)
        self.assertEqual(plancher.nombre_sabots_ewh, 44)
        self.assertEqual(plancher.nombre_pointes_ewh, 704)
        self.assertEqual(
            len(plancher.elements()),
            11 + plancher.nombre_solives_i + plancher.nombre_sabots_ewh,
        )

    def test_solives_i_relient_les_traverses_et_affleurent_le_plancher(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame(), inclure_solives_i=True)
        solives = [
            element for element in plancher.elements() if element.nom.startswith("Solive")
        ]
        premiere = solives[0].forme.bounding_box()

        self.assertAlmostEqual(premiere.size.X, plancher.longueur_solives_i)
        self.assertAlmostEqual(premiere.size.Y, 90)
        self.assertAlmostEqual(premiere.max.Z, plancher.niveau_haut_traverses)
        self.assertAlmostEqual(premiere.min.Z, 30)
        self.assertEqual(len(plancher.axes_solives_i()), 11)
        self.assertEqual(len(plancher.debuts_travees_solives_i()), 2)
        self.assertEqual(plancher.jeu_ewh_par_about, 3)

        traverses = [
            element
            for element in plancher.elements()
            if element.nom.startswith("Traverse")
        ]
        self.assertTrue(
            all(
                (solive.forme & traverse.forme).volume == 0
                for solive in solives
                for traverse in traverses
            )
        )

        etriers = [
            element
            for element in plancher.elements()
            if element.nom.startswith("Étrier EWH")
        ]
        self.assertTrue(
            all(
                element.forme.bounding_box().min.Z >= 0
                and element.forme.bounding_box().max.Z <= plancher.section_hauteur
                for element in etriers
            )
        )

    def test_connecteurs_de_solives_i_optionnels(self) -> None:
        plancher = PlancherAFrame(
            GeometrieAFrame(),
            inclure_solives_i=True,
            inclure_connecteurs_solives_i=False,
        )

        self.assertEqual(plancher.nombre_sabots_ewh, 0)
        self.assertEqual(plancher.nombre_pointes_ewh, 0)
        self.assertEqual(plancher.jeu_ewh_par_about, 0)
        self.assertAlmostEqual(
            plancher.longueur_solives_i,
            plancher.entraxe_traverses - plancher.section_largeur,
        )

    def test_fonds_osb_des_caissons_interieurs(self) -> None:
        plancher = PlancherAFrame(
            GeometrieAFrame(),
            inclure_solives_i=True,
            inclure_osb_caissons=True,
        )
        elements = plancher.elements()
        panneaux = [
            element for element in elements if element.nom.startswith("Fond OSB")
        ]
        etriers = [
            element for element in elements if element.nom.startswith("Étrier EWH")
        ]
        sabots_sai = [
            element for element in elements if element.nom.startswith("Sabot SAI")
        ]
        solives = [
            element for element in elements if element.nom.startswith("Solive en I")
        ]
        premier = panneaux[0].forme.bounding_box()

        self.assertEqual(plancher.nombre_panneaux_osb_interieurs, 20)
        self.assertEqual(plancher.nombre_panneaux_osb_rive, 4)
        self.assertEqual(plancher.nombre_panneaux_osb_caissons, 24)
        self.assertEqual(plancher.nombre_vis_par_panneau_osb, 32)
        self.assertEqual(plancher.nombre_vis_osb, 768)
        self.assertEqual(len(panneaux), 24)
        self.assertAlmostEqual(premier.size.Y, 479)
        self.assertAlmostEqual(premier.min.Z, 75)
        self.assertAlmostEqual(premier.max.Z, 87)
        panneaux_interieurs = [
            element for element in panneaux if "de rive" not in element.nom
        ]
        self.assertTrue(
            all(
                (panneau.forme & etrier.forme).volume < 1e-6
                for panneau in panneaux_interieurs
                for etrier in etriers
            )
        )
        self.assertTrue(
            all(
                (panneau.forme & solive.forme).volume < 1e-6
                for panneau in panneaux
                for solive in solives
            )
        )
        panneaux_rive = [
            element for element in panneaux if "de rive" in element.nom
        ]
        self.assertEqual(len(panneaux_rive), 4)
        self.assertTrue(
            all(not panneau.piece.avec_encoches for panneau in panneaux_rive)
        )
        self.assertTrue(
            all(
                (panneau.forme & sabot.forme).volume < 1e-6
                for panneau in panneaux_rive
                for sabot in sabots_sai
            )
        )
        self.assertTrue(
            all(
                abs(panneau.forme.bounding_box().size.Y - 423) < 1e-6
                for panneau in panneaux_rive
            )
        )

    def test_quatre_tasseaux_portent_les_caissons_de_rive(self) -> None:
        plancher = PlancherAFrame(
            GeometrieAFrame(surface_plancher_max=20),
            inclure_solives_i=True,
            inclure_osb_caissons=True,
        )
        tasseaux = [
            element
            for element in plancher.elements()
            if element.nom.startswith("Tasseau de rive")
        ]

        self.assertEqual(plancher.nombre_tasseaux_rive, 4)
        self.assertEqual(len(tasseaux), 4)
        for element in tasseaux:
            boite = element.forme.bounding_box()
            self.assertAlmostEqual(boite.size.X, plancher.longueur_solives_i)
            self.assertAlmostEqual(boite.size.Y, 90)
            self.assertAlmostEqual(boite.size.Z, 45)
            self.assertAlmostEqual(boite.min.Z, 30)
            self.assertAlmostEqual(boite.max.Z, 75)

    def test_trame_modulaire_steicoflex_sans_decoupe(self) -> None:
        plancher = self.plancher_modulaire()
        axes = plancher.axes_solives_i()
        isolants = [
            element
            for element in plancher.elements()
            if element.nom.startswith("Isolant STEICOflex")
        ]

        self.assertEqual(plancher.nombre_lignes_solives_i, 11)
        self.assertEqual(plancher.nombre_solives_i, 22)
        self.assertEqual(len(axes), 11)
        self.assertTrue(
            all(abs(droite - gauche - 573) < 1e-6 for gauche, droite in pairwise(axes))
        )
        self.assertEqual(plancher.largeur_caisson_isolant, 565)
        self.assertEqual(plancher.longueur_caisson_isolant, 1_220)
        self.assertEqual(plancher.hauteur_caisson_isolant, 118)
        self.assertEqual(plancher.longueur_solives_i, 1_214)
        self.assertEqual(plancher.largeur_panneaux_osb_caissons, 562)
        self.assertEqual(plancher.largeur_panneaux_osb_rive, 562)
        self.assertEqual(plancher.nombre_panneaux_isolant, 24)
        self.assertEqual(len(isolants), 24)
        self.assertTrue(
            all(
                (
                    isolant.forme.bounding_box().size.X,
                    isolant.forme.bounding_box().size.Y,
                    isolant.forme.bounding_box().size.Z,
                )
                == (1_220, 565, 118)
                for isolant in isolants
            )
        )
        self.assertEqual(plancher.nombre_vis_par_panneau_osb, 16)
        self.assertEqual(plancher.nombre_vis_osb, 384)

    def test_plancher_osb_22_mm_sur_tous_les_appuis(self) -> None:
        plancher = self.plancher_modulaire(inclure_osb_plancher=True)
        panneaux = [
            element
            for element in plancher.elements()
            if element.nom.startswith("Plancher OSB supérieur")
        ]
        largeurs = [round(element.forme.bounding_box().size.X, 6) for element in panneaux]
        longueurs = [round(element.forme.bounding_box().size.Y, 6) for element in panneaux]

        self.assertEqual(plancher.nombre_panneaux_osb_plancher, 22)
        self.assertEqual(len(panneaux), 22)
        self.assertEqual(largeurs.count(675), 18)
        self.assertEqual(largeurs.count(104), 4)
        self.assertEqual(longueurs.count(1_835), 6)
        self.assertEqual(longueurs.count(1_719), 12)
        self.assertEqual(longueurs.count(1_262), 2)
        self.assertEqual(longueurs.count(689), 2)
        self.assertEqual(plancher.nombre_dalles_brutes_osb_plancher, 17)
        self.assertEqual(plancher.nombre_vis_osb_plancher, 483)
        self.assertTrue(
            all(
                element.forme.bounding_box().min.Z == 250
                and element.forme.bounding_box().max.Z == 272
                for element in panneaux
            )
        )
        surface = sum(
            element.forme.bounding_box().size.X
            * element.forme.bounding_box().size.Y
            for element in panneaux
        )
        self.assertAlmostEqual(surface / 1_000_000, 19.930832)

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

        plancher_limite = PlancherAFrame(
            GeometrieAFrame(surface_plancher_max=20),
            inclure_solives_i=True,
            inclure_osb_caissons=True,
        )
        boites = [element.forme.bounding_box() for element in plancher_limite.elements()]
        longueur = max(boite.max.X for boite in boites) - min(
            boite.min.X for boite in boites
        )
        largeur = max(boite.max.Y for boite in boites) - min(
            boite.min.Y for boite in boites
        )
        self.assertLessEqual(longueur * largeur / 1_000_000, 20)

    def test_sections_et_assemblages(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())
        poutre_gauche, _, traverse_haute, traverse_milieu, _ = plancher.elements()[:5]

        self.assertEqual(
            (
                poutre_gauche.piece.largeur,
                poutre_gauche.piece.hauteur,
            ),
            (120, 250),
        )
        self.assertAlmostEqual(
            poutre_gauche.forme.volume,
            poutre_gauche.piece.construire().volume,
        )
        self.assertAlmostEqual(
            traverse_haute.forme.volume,
            traverse_haute.piece.construire().volume,
        )
        self.assertEqual(traverse_milieu.piece.longueur, 5_756)
        self.assertEqual(plancher.retrait_connecteur_par_about, 2)
        self.assertAlmostEqual(traverse_milieu.forme.bounding_box().min.Y, -2_878)
        self.assertAlmostEqual(traverse_milieu.forme.bounding_box().max.Y, 2_878)
        self.assertEqual(plancher.niveau_haut_traverses, 250)

    def test_sabots_aux_six_abouts(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame())
        sabots = plancher.elements()[5:11]

        self.assertEqual(plancher.nombre_sabots, 6)
        self.assertEqual(plancher.nombre_vis_connecteurs, 300)
        self.assertEqual(len(sabots), 6)
        self.assertTrue(all("Sabot SAI" in element.nom for element in sabots))

    def test_connecteurs_optionnels(self) -> None:
        plancher = PlancherAFrame(
            GeometrieAFrame(),
            inclure_connecteurs=False,
        )

        self.assertEqual(len(plancher.elements()), 5)
        self.assertEqual(plancher.nombre_sabots, 0)
        self.assertEqual(plancher.nombre_vis_connecteurs, 0)
        self.assertEqual(plancher.longueur_traverses, 5_760)


if __name__ == "__main__":
    unittest.main()
