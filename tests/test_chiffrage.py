import io
import unittest
from decimal import Decimal

from main import make_part
from maison.chiffrage import Chiffrage, Tarif
from maison.geometrie import GeometrieAFrame
from maison.nomenclature import ArticleBOM, LotBOM, Nomenclature
from maison.prix import TARIFS
from maison.structure import PlancherAFrame


class TestChiffrage(unittest.TestCase):
    def test_arrondit_au_conditionnement_superieur(self) -> None:
        article = ArticleBOM(
            reference="VIS-TEST",
            designation="Vis de test",
            categorie="Fixation",
            materiau="Acier",
        )
        nomenclature = Nomenclature((LotBOM(article, 11),))
        chiffrage = Chiffrage(
            "test",
            nomenclature,
            {
                "VIS-TEST": Tarif.par_conditionnement(
                    "5.25",
                    quantite=10,
                    conditionnement="boîte de 10",
                )
            },
        )

        ligne = chiffrage.lignes[0]
        self.assertEqual(ligne.nombre_conditionnements, 2)
        self.assertEqual(ligne.cout_ttc_eur, Decimal("10.50"))
        self.assertTrue(chiffrage.est_complet)

    def test_tarification_par_barre_achete_des_pieces_entieres(self) -> None:
        article = ArticleBOM(
            reference="BOIS-TEST",
            designation="Bois de test",
            categorie="Bois",
            materiau="Bois",
            longueur_mm=3_750,
        )
        nomenclature = Nomenclature((LotBOM(article, 2),))
        chiffrage = Chiffrage(
            "test",
            nomenclature,
            {
                "BOIS-TEST": Tarif.en_barres(
                    "70",
                    reference_achat="BOIS-STOCK-L6000",
                    designation_achat="Bois de test — L 6000 mm",
                    longueur_commerciale_mm=6_000,
                    trait_scie_mm=5,
                )
            },
        )

        plan = chiffrage.plans_debit[0]
        self.assertEqual(plan.plan.nombre_barres, 2)
        self.assertEqual(plan.longueur_achetee_m, Decimal("12"))
        self.assertEqual(plan.cout_ttc_eur, Decimal("140"))

    def test_un_prix_manquant_ne_devient_pas_zero(self) -> None:
        article = ArticleBOM("MANQUANT", "Test", "Test", "Test")
        chiffrage = Chiffrage("test", Nomenclature((LotBOM(article, 2),)), {})

        self.assertFalse(chiffrage.est_complet)
        self.assertEqual(chiffrage.references_manquantes, ("MANQUANT",))
        self.assertIsNone(chiffrage.lignes[0].cout_ttc_eur)
        self.assertEqual(chiffrage.sous_total_renseigne_ttc_eur, Decimal("0"))

    def test_export_signale_explicitement_les_lignes_incompletes(self) -> None:
        article = ArticleBOM("MANQUANT", "Test", "Test", "Test")
        chiffrage = Chiffrage(
            "plancher",
            Nomenclature((LotBOM(article, 1),)),
            {},
        )
        sortie = io.StringIO()

        chiffrage.ecrire_csv(sortie)

        self.assertIn(
            "prix_unitaire_ttc_eur;cout_ttc_eur",
            sortie.getvalue(),
        )
        self.assertIn("À RENSEIGNER", sortie.getvalue())
        self.assertIn("INCOMPLET", sortie.getvalue())

    def test_bom_achat_remplace_les_decoupes_osb_par_les_dalles(self) -> None:
        plancher = PlancherAFrame(
            GeometrieAFrame(
                largeur_interieure=4_000,
                surface_plancher_max=20,
                longueur_interieure_imposee=4_800,
            ),
            nombre_traverses=5,
            entraxe_solives_i_max=573,
            caissons_uniformes=True,
            inclure_solives_i=True,
            inclure_osb_caissons=True,
            inclure_isolant_caissons=True,
            inclure_osb_plancher=True,
        )
        quantites = {
            ligne.article.reference: ligne.quantite
            for ligne in plancher.nomenclature_achats().lignes
        }

        self.assertEqual(quantites["OSB-675x2500x12"], 14)
        self.assertEqual(quantites["OSB-675x2500x22"], 15)
        self.assertFalse(
            any(reference.startswith("OSB-FOND-") for reference in quantites)
        )
        self.assertFalse(
            any(reference.startswith("OSB-PLANCHER-") for reference in quantites)
        )

    def test_configuration_active_ne_chiffre_que_le_plancher_primaire(self) -> None:
        maison = make_part()
        references_plancher = {
            ligne.article.reference
            for ligne in maison.nomenclature_plancher().lignes
        }
        references_charpente = {
            ligne.article.reference
            for ligne in maison.nomenclature_charpente().lignes
        }

        self.assertEqual(
            references_plancher,
            {
                "MAD-120x240-L3756",
                "MAD-120x240-L4800",
                "SIMPSON-CNA4.0X35",
                "SIMPSON-CSA5.0X40",
                "SIMPSON-EWH240-61",
                "SIMPSON-SAI500-120-2",
                "SJI-60x240-L2212",
            },
        )
        self.assertEqual(references_charpente, set())

    def test_cinq_poutres_representent_20_868_metres_utiles(self) -> None:
        maison = make_part()
        longueur = sum(
            Decimal(str(ligne.longueur_totale_mm))
            for ligne in maison.nomenclature_plancher().lignes
            if ligne.article.reference.startswith("MAD-")
        )

        self.assertEqual(longueur / Decimal("1000"), Decimal("20.868"))

    def test_cinq_poutres_achetent_deux_barres_commerciales(self) -> None:
        maison = make_part()
        chiffrage = Chiffrage(
            "plancher",
            maison.nomenclature_plancher(),
            TARIFS,
        )

        self.assertEqual(len(chiffrage.plans_debit), 2)
        plan = next(
            plan
            for plan in chiffrage.plans_debit
            if plan.reference_achat.startswith("DOUGLAS-")
        )
        self.assertEqual(plan.plan.nombre_barres, 2)
        self.assertEqual(plan.longueur_achetee_m, Decimal("27"))
        self.assertEqual(plan.cout_ttc_eur, Decimal("1386.46"))
        self.assertEqual(
            chiffrage.sous_total_renseigne_ttc_eur,
            Decimal("2256.98"),
        )

    def test_fixations_simpson_sont_arrondies_aux_conditionnements(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )
        lignes = {
            ligne.ligne_bom.article.reference: ligne
            for ligne in chiffrage.lignes
        }

        sabots = lignes["SIMPSON-SAI500-120-2"]
        vis = lignes["SIMPSON-CSA5.0X40"]
        self.assertEqual(sabots.ligne_bom.quantite, 6)
        self.assertEqual(sabots.nombre_conditionnements, 6)
        self.assertEqual(sabots.cout_ttc_eur, Decimal("42.54"))
        self.assertEqual(vis.ligne_bom.quantite, 300)
        self.assertEqual(vis.nombre_conditionnements, 2)
        self.assertEqual(vis.cout_ttc_eur, Decimal("79.12"))

    def test_poutres_i_et_fixations_sont_achetees_entieres(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )
        lignes = {
            ligne.ligne_bom.article.reference: ligne
            for ligne in chiffrage.lignes
        }
        plan = next(
            plan
            for plan in chiffrage.plans_debit
            if plan.reference_achat.startswith("STEICO-")
        )

        self.assertEqual(plan.plan.nombre_barres, 3)
        self.assertEqual(plan.longueur_achetee_m, Decimal("39"))
        self.assertEqual(plan.cout_ttc_eur, Decimal("549.90"))
        self.assertEqual(lignes["SIMPSON-EWH240-61"].ligne_bom.quantite, 24)
        self.assertEqual(lignes["SIMPSON-EWH240-61"].cout_ttc_eur, Decimal("175.20"))
        self.assertEqual(lignes["SIMPSON-CNA4.0X35"].ligne_bom.quantite, 384)
        self.assertEqual(lignes["SIMPSON-CNA4.0X35"].nombre_conditionnements, 2)
        self.assertEqual(lignes["SIMPSON-CNA4.0X35"].cout_ttc_eur, Decimal("23.76"))

    def test_lot_desactive_est_signale_comme_vide(self) -> None:
        chiffrage = Chiffrage("charpente", Nomenclature(), {})
        sortie = io.StringIO()

        chiffrage.ecrire_csv(sortie)

        self.assertTrue(chiffrage.est_vide)
        self.assertIn("AUCUN ARTICLE", sortie.getvalue())

    def test_tarif_refuse_un_conditionnement_invalide(self) -> None:
        with self.assertRaises(ValueError):
            Tarif(quantite_par_conditionnement=0)
        with self.assertRaises(ValueError):
            Tarif(prix_unitaire_ttc_eur="-0.01")

    def test_tarif_en_barres_exige_une_longueur_bom(self) -> None:
        article = ArticleBOM("SANS-LONGUEUR", "Test", "Test", "Test")
        with self.assertRaisesRegex(ValueError, "n'a pas de longueur"):
            Chiffrage(
                "test",
                Nomenclature((LotBOM(article, 1),)),
                {
                    "SANS-LONGUEUR": Tarif.en_barres(
                        "10",
                        reference_achat="STOCK-L6000",
                        designation_achat="Stock de test",
                        longueur_commerciale_mm=6_000,
                    )
                },
            )


if __name__ == "__main__":
    unittest.main()
