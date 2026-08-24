import io
import unittest
from decimal import Decimal

from chiffrer import lignes_recapitulatif_achats
from local_batteries import creer_local_batteries
from main import make_part
from maison.chiffrage import Chiffrage, Tarif
from maison.geometrie import GeometrieAFrame
from maison.nomenclature import ArticleBOM, LotBOM, Nomenclature
from maison.prix import TARIFS
from maison.structure import PlancherAFrame
from optimiser import lignes_resume_lots_lineaires, lignes_resume_panneaux_osb


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

    def test_tarification_par_lot_lineaire_arrondit_la_longueur(self) -> None:
        article = ArticleBOM(
            reference="TASSEAU-TEST",
            designation="Tasseau de test",
            categorie="Bois",
            materiau="Bois",
            longueur_mm=2_200,
        )
        tarif = Tarif.en_lots_lineaires(
            "182",
            longueur_du_lot_mm=20_000,
            conditionnement="minimum de 20 ml",
        )
        chiffrage = Chiffrage(
            "test",
            Nomenclature((LotBOM(article, 10),)),
            {"TASSEAU-TEST": tarif},
        )

        ligne = chiffrage.lignes[0]
        self.assertEqual(ligne.longueur_utile_m, Decimal("22"))
        self.assertEqual(ligne.nombre_conditionnements, 2)
        self.assertEqual(ligne.longueur_achetee_m, Decimal("40"))
        self.assertEqual(ligne.cout_ttc_eur, Decimal("364"))

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

        self.assertEqual(quantites["OSB-BD-1196x2800x12"], 6)
        self.assertEqual(quantites["OSB-RL-675x2500x22"], 28)
        self.assertFalse(
            any(reference.startswith("OSB-FOND-") for reference in quantites)
        )
        self.assertFalse(
            any(reference.startswith("OSB-PLANCHER-") for reference in quantites)
        )

    def test_configuration_active_chiffre_aussi_les_fonds_de_caisson(self) -> None:
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
                "ISOL-ISONAT-FLEX55-145x580x1220",
                "KLIMAS-KMWHT-5X60",
                "MAD-120x240-L3756",
                "MAD-120x240-L4800",
                "KLIMAS-KMWHT-6X160",
                "OSB-BD-1196x2800x12",
                "OSB-RL-675x2500x22",
                "SPAX-0191010400355",
                "SIMPSON-CNA4.0X35",
                "SIMPSON-CSA5.0X40",
                "SIMPSON-EWH240-61",
                "SIMPSON-SAI500-120-2",
                "SJI-60x240-L2212",
                "TAS-60x40-L2212",
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
            Decimal("3448.50"),
        )

    def test_catalogue_commun_resout_les_nouvelles_longueurs_de_coupe(self) -> None:
        self.assertIs(TARIFS["MAD-120x240-L3000"], TARIFS["MAD-120x240-L2756"])
        self.assertIs(TARIFS["SJI-60x240-L593"], TARIFS["SJI-60x240-L2212"])
        self.assertIs(TARIFS["TAS-60x40-L593"], TARIFS["TAS-60x40-L2212"])

    def test_local_batteries_utilise_le_chiffrage_commun(self) -> None:
        chiffrage = Chiffrage(
            "local_batteries",
            creer_local_batteries().nomenclature_achats(),
            TARIFS,
        )

        self.assertTrue(chiffrage.est_complet)
        self.assertEqual(len(chiffrage.plans_debit), 2)
        self.assertEqual(
            chiffrage.sous_total_renseigne_ttc_eur,
            Decimal("3396.64"),
        )

    def test_plancher_osb_achete_quatorze_dalles_et_trois_boites(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )
        lignes = {
            ligne.ligne_bom.article.reference: ligne
            for ligne in chiffrage.lignes
        }

        osb = lignes["OSB-RL-675x2500x22"]
        self.assertEqual(osb.ligne_bom.quantite, 14)
        self.assertEqual(osb.nombre_conditionnements, 14)
        self.assertEqual(osb.cout_ttc_eur, Decimal("385.14"))

        vis = lignes["KLIMAS-KMWHT-5X60"]
        self.assertEqual(vis.ligne_bom.quantite, 568)
        self.assertEqual(vis.nombre_conditionnements, 3)
        self.assertEqual(vis.cout_ttc_eur, Decimal("32.40"))

    def test_isonat_achete_sept_colis_de_quatre_panneaux(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )
        ligne = next(
            ligne
            for ligne in chiffrage.lignes
            if ligne.ligne_bom.article.reference
            == "ISOL-ISONAT-FLEX55-145x580x1220"
        )

        self.assertEqual(ligne.ligne_bom.quantite, 28)
        self.assertEqual(ligne.nombre_conditionnements, 7)
        self.assertEqual(ligne.cout_ttc_eur, Decimal("339.36"))

    def test_fonds_de_caisson_achetent_sept_panneaux_bd_entiers(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )
        ligne = next(
            ligne
            for ligne in chiffrage.lignes
            if ligne.ligne_bom.article.reference == "OSB-BD-1196x2800x12"
        )

        self.assertEqual(ligne.ligne_bom.quantite, 7)
        self.assertEqual(ligne.nombre_conditionnements, 7)
        self.assertEqual(ligne.cout_ttc_eur, Decimal("197.12"))

    def test_spax_et_lambourdes_respectent_leurs_conditionnements(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )
        lignes = {
            ligne.ligne_bom.article.reference: ligne
            for ligne in chiffrage.lignes
        }

        spax = lignes["SPAX-0191010400355"]
        self.assertEqual(spax.ligne_bom.quantite, 420)
        self.assertEqual(spax.nombre_conditionnements, 1)
        self.assertEqual(spax.cout_ttc_eur, Decimal("28.00"))

        lambourdes = lignes["TAS-60x40-L2212"]
        self.assertEqual(lambourdes.ligne_bom.quantite, 4)
        self.assertEqual(lambourdes.longueur_utile_m, Decimal("8.848"))
        self.assertEqual(lambourdes.nombre_conditionnements, 1)
        self.assertEqual(lambourdes.longueur_achetee_m, Decimal("20"))
        self.assertEqual(lambourdes.cout_ttc_eur, Decimal("182.00"))

        vis_lambourdes = lignes["KLIMAS-KMWHT-6X160"]
        self.assertEqual(vis_lambourdes.ligne_bom.quantite, 32)
        self.assertEqual(vis_lambourdes.nombre_conditionnements, 1)
        self.assertEqual(vis_lambourdes.cout_ttc_eur, Decimal("27.50"))
        self.assertTrue(chiffrage.est_complet)

    def test_optimiseur_resume_le_debit_des_panneaux_bd_actifs(self) -> None:
        contenu = "\n".join(lignes_resume_panneaux_osb(make_part().plancher))

        self.assertIn("7 panneau(x) × 2800 × 1196 mm", contenu)
        self.assertIn("14 fonds × 2212", contenu)
        self.assertIn("2 découpes par panneau", contenu)

    def test_optimiseur_resume_le_minimum_lineaire_des_lambourdes(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )

        contenu = "\n".join(lignes_resume_lots_lineaires(chiffrage))

        self.assertIn("TAS-60x40-L2212", contenu)
        self.assertIn("utile 8.848 m", contenu)
        self.assertIn("acheté 20 m", contenu)
        self.assertIn("surplus 11.152 m", contenu)

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

    def test_recapitulatif_terminal_affiche_tous_les_achats(self) -> None:
        chiffrage = Chiffrage(
            "plancher",
            make_part().nomenclature_plancher(),
            TARIFS,
        )

        contenu = "\n".join(lignes_recapitulatif_achats(chiffrage))

        for reference in (
            "DOUGLAS-GT24-120x240-L13500",
            "ISOL-ISONAT-FLEX55-145x580x1220",
            "KLIMAS-KMWHT-5X60",
            "KLIMAS-KMWHT-6X160",
            "OSB-BD-1196x2800x12",
            "OSB-RL-675x2500x22",
            "SPAX-0191010400355",
            "STEICO-SJ60x240-L13000",
            "SIMPSON-CNA4.0X35",
            "SIMPSON-CSA5.0X40",
            "SIMPSON-EWH240-61",
            "SIMPSON-SAI500-120-2",
            "TAS-60x40-L2212",
        ):
            self.assertIn(reference, contenu)
        self.assertIn("384 nécessaires", contenu)
        self.assertIn("300 nécessaires", contenu)
        self.assertIn("8.848 ml utiles ; 20 ml achetés", contenu)

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
        with self.assertRaises(ValueError):
            Tarif.en_lots_lineaires(
                "10",
                longueur_du_lot_mm=0,
                conditionnement="lot",
            )

    def test_tarif_en_lot_lineaire_exige_une_longueur_bom(self) -> None:
        article = ArticleBOM("SANS-LONGUEUR", "Test", "Test", "Test")
        chiffrage = Chiffrage(
            "test",
            Nomenclature((LotBOM(article, 1),)),
            {
                "SANS-LONGUEUR": Tarif.en_lots_lineaires(
                    "10",
                    longueur_du_lot_mm=20_000,
                    conditionnement="minimum de 20 ml",
                )
            },
        )

        with self.assertRaisesRegex(ValueError, "n'a pas de longueur"):
            _ = chiffrage.lignes[0].nombre_conditionnements

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
