import unittest

from local_batteries import creer_local_batteries
from local_batteries.debit import calepinage_fonds_caissons, plan_debit_osb


class TestLocalBatteries(unittest.TestCase):
    def setUp(self) -> None:
        self.local = creer_local_batteries()
        self.plancher = self.local.plancher

    def test_emprise_de_neuf_metres_carres(self) -> None:
        self.assertEqual(self.local.geometrie.largeur_interieure, 3_000)
        self.assertEqual(self.local.geometrie.longueur_interieure, 3_000)
        self.assertEqual(self.local.geometrie.surface_plancher, 9.0)

    def test_trame_porteuse_tres_serree(self) -> None:
        self.assertEqual(self.plancher.nombre_traverses, 5)
        self.assertEqual(self.plancher.nombre_lignes_solives_i, 9)
        self.assertEqual(self.plancher.nombre_solives_i, 36)
        self.assertLessEqual(self.plancher.entraxe_solives_i, 300)
        self.assertEqual(self.plancher.longueur_solives_i, 593)

    def test_reutilise_les_sections_du_projet_principal(self) -> None:
        nomenclature = {
            ligne.article.reference: ligne
            for ligne in self.local.nomenclature_achats().lignes
        }
        self.assertEqual(nomenclature["MAD-120x240-L3000"].quantite, 2)
        self.assertEqual(nomenclature["MAD-120x240-L2756"].quantite, 5)
        self.assertEqual(nomenclature["SJI-60x240-L593"].quantite, 36)

    def test_double_couche_osb_croisee(self) -> None:
        osb = [
            element
            for element in self.local.elements()
            if element.nom.startswith(("OSB inférieur", "OSB supérieur"))
        ]
        couche_inferieure = [e for e in osb if "inférieur" in e.nom]
        couche_superieure = [e for e in osb if "supérieur" in e.nom]

        self.assertEqual(len(couche_inferieure), 12)
        self.assertEqual(len(couche_superieure), 10)
        self.assertTrue(
            all(e.forme.bounding_box().min.Z == 240 for e in couche_inferieure)
        )
        self.assertTrue(
            all(e.forme.bounding_box().min.Z == 262 for e in couche_superieure)
        )

    def test_joints_osb_sont_en_quinconce_et_sur_les_appuis(self) -> None:
        osb = [
            element
            for element in self.local.elements()
            if element.nom.startswith(("OSB inférieur", "OSB supérieur"))
        ]
        couche_inferieure = [e for e in osb if "inférieur" in e.nom]
        couche_superieure = [e for e in osb if "supérieur" in e.nom]

        joints_x_par_rangee: dict[float, set[float]] = {}
        for element in couche_inferieure:
            boite = element.forme.bounding_box()
            axe_y = round((boite.min.Y + boite.max.Y) / 2, 6)
            joints = joints_x_par_rangee.setdefault(axe_y, set())
            joints.update(
                round(x, 6)
                for x in (boite.min.X, boite.max.X)
                if 0 < x < 3_000
            )
        self.assertEqual(
            tuple(joints_x_par_rangee.values()),
            ({1_500.0}, {781.0, 2_219.0}, {1_500.0}, {781.0, 2_219.0}, {1_500.0}),
        )

        joints_y_par_colonne: dict[float, set[float]] = {}
        for element in couche_superieure:
            boite = element.forme.bounding_box()
            axe_x = round((boite.min.X + boite.max.X) / 2, 6)
            joints = joints_y_par_colonne.setdefault(axe_x, set())
            joints.update(
                round(y, 6)
                for y in (boite.min.Y, boite.max.Y)
                if -1_500 < y < 1_500
            )
        self.assertEqual(
            tuple(joints_y_par_colonne.values()),
            (
                {830.4},
                {-830.4},
                {830.4},
                {-830.4},
                {830.4},
            ),
        )

    def test_bom_achats_remplace_les_decoupes_par_dalles_brutes(self) -> None:
        lignes = self.local.nomenclature_achats().lignes
        references = {ligne.article.reference: ligne.quantite for ligne in lignes}

        self.assertFalse(
            any(reference.startswith("OSB-PLANCHER-") for reference in references)
        )
        self.assertEqual(references["OSB-RL-675x2500x22"], 14)
        self.assertEqual(references["OSB-BD-1196x2800x12"], 3)
        self.assertEqual(references["ISOL-ISONAT-FLEX55-145x580x1220"], 10)
        self.assertEqual(references["SPAX-0191010400355"], 320)
        self.assertEqual(references["TAS-60x40-L593"], 8)
        self.assertEqual(references["KLIMAS-KMWHT-6X160"], 24)

    def test_plan_debit_osb_tient_dans_quatorze_dalles(self) -> None:
        plan = plan_debit_osb(self.local)

        self.assertEqual(plan.nombre_barres, 14)
        self.assertEqual(plan.nombre_pieces, 22)
        self.assertTrue(all(barre.chute_mm >= 0 for barre in plan.barres))

    def test_isolant_remplit_les_quarante_caissons(self) -> None:
        isolants = [
            element
            for element in self.local.elements()
            if element.nom.startswith("Isolant Isonat")
        ]

        self.assertEqual(len(isolants), 40)
        self.assertTrue(
            all(
                round(element.forme.bounding_box().size.X, 6) == 599
                and round(element.forme.bounding_box().size.Y, 6) == 268.8
                and element.forme.bounding_box().min.Z == 51
                and element.forme.bounding_box().max.Z == 196
                for element in isolants
            )
        )

    def test_fonds_osb_sont_inseres_dans_les_caissons(self) -> None:
        panneaux = [
            element
            for element in self.local.elements()
            if element.nom.startswith("Fond OSB")
        ]

        self.assertEqual(len(panneaux), 40)
        self.assertTrue(
            all(
                element.forme.bounding_box().size.X == 593
                and round(element.forme.bounding_box().size.Y, 6) == 265.8
                and element.forme.bounding_box().min.Z == 39
                and element.forme.bounding_box().max.Z == 51
                for element in panneaux
            )
        )
        self.assertEqual(calepinage_fonds_caissons(self.local), (16, 16, 8))

    def test_tasseaux_ne_sont_necessaires_que_sur_les_deux_rives(self) -> None:
        tasseaux = [
            element
            for element in self.local.elements()
            if element.nom.startswith("Tasseau de rive")
        ]

        self.assertEqual(len(tasseaux), 8)
        self.assertTrue(
            all(
                element.forme.bounding_box().size.X == 593
                and element.forme.bounding_box().max.Z == 39
                for element in tasseaux
            )
        )


if __name__ == "__main__":
    unittest.main()
