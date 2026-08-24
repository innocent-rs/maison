import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build123d import Location

from local_batteries import creer_local_batteries
from local_batteries.debit import (
    calepinage_fonds_caissons,
    calepinage_osb_murs,
    plan_debit_osb,
)
from local_batteries.manuel_assemblage import (
    elements_du_manuel,
    etapes_assemblage,
    exporter_manuel_assemblage,
    poutres_du_plancher,
)
from home_framework.assemblage import (
    Ancrage,
    AssemblageContraint,
    DecalageParallele,
    EntreFaces,
)
from home_framework.structure.bois import Madrier, PoutreI


class TestLocalBatteries(unittest.TestCase):
    def setUp(self) -> None:
        self.local = creer_local_batteries()
        self.plancher = self.local.plancher

    def test_emprise_de_neuf_metres_carres(self) -> None:
        self.assertEqual(self.local.geometrie.largeur_interieure, 3_000)
        self.assertEqual(self.local.geometrie.longueur_interieure, 3_000)
        self.assertEqual(self.local.geometrie.surface_plancher, 9.0)

    def test_trame_porteuse_simple(self) -> None:
        self.assertEqual(self.plancher.nombre_traverses, 2)
        self.assertEqual(self.plancher.nombre_lignes_solives_i, 4)
        self.assertEqual(self.plancher.nombre_solives_i, 4)
        self.assertLessEqual(self.plancher.entraxe_solives_i, 600)
        self.assertEqual(self.plancher.longueur_solives_i, 2_750)

    def test_reutilise_les_sections_du_projet_principal(self) -> None:
        nomenclature = {
            ligne.article.reference: ligne
            for ligne in self.local.nomenclature_achats().lignes
        }
        self.assertEqual(nomenclature["MAD-120x240-L3000"].quantite, 2)
        self.assertEqual(nomenclature["MAD-120x240-L2756"].quantite, 2)
        self.assertEqual(nomenclature["SJI-60x240-L2750"].quantite, 4)

    def test_manuel_assemblage_couvre_le_plancher_fini(self) -> None:
        poutres = poutres_du_plancher(self.local)
        elements = elements_du_manuel(self.local)

        self.assertEqual(len(poutres), 8)
        self.assertTrue(
            all(isinstance(element.piece, (Madrier, PoutreI)) for element in poutres)
        )
        self.assertEqual(len(elements), 52)
        self.assertEqual(
            [len(etape.nouvelles) for etape in etapes_assemblage(self.local)],
            [2, 4, 2, 8, 4, 2, 5, 15, 10],
        )

    def test_sabots_osb_et_isolant_forment_une_chaine_de_dependances(self) -> None:
        assemblage = self.local.assemblage_plancher()
        instances = {
            instance.identifiant: instance for instance in assemblage.instances
        }

        self.assertEqual(
            instances["sabot_sai_01_gauche"].contrainte.references,
            ("rive_gauche",),
        )
        self.assertIn(
            "sabot_sai_01_gauche",
            instances["traverse_01"].contrainte.references,
        )
        self.assertEqual(
            instances["ewh_01_1_debut"].contrainte.references,
            ("traverse_01",),
        )
        self.assertIn(
            "ewh_01_1_debut",
            instances["solive_01"].contrainte.references,
        )
        self.assertIn(
            "solive_02",
            instances["fond_osb_01_1"].contrainte.references,
        )
        self.assertEqual(
            instances["isolant_local_01_1_1"].contrainte.references,
            ("fond_osb_rive_gauche_1",),
        )
        self.assertIn(
            "isolant_local_01_1_1",
            instances["osb_porteur_01"].contrainte.references,
        )
        self.assertEqual(
            [operation.identifiant for operation in assemblage.operations()],
            [
                "implantation",
                "sabots_sai",
                "traverses",
                "etriers_ewh",
                "entre_traverse_01_traverse_02",
                "tasseaux_rive",
                "fonds_osb",
                "isolant_caissons",
                "osb_porteur",
            ],
        )

    def test_contraintes_poutres_gouvernent_cao_bom_et_timeline(self) -> None:
        assemblage = self.plancher.assemblage_poutres()
        instances = {instance.identifiant: instance for instance in assemblage.instances}

        self.assertIsInstance(instances["rive_gauche"].contrainte, Ancrage)
        self.assertEqual(
            instances["rive_droite"].contrainte,
            DecalageParallele("rive_gauche", (0, 2_880, 0)),
        )
        self.assertEqual(
            instances["traverse_01"].contrainte.references,
            ("rive_gauche", "rive_droite"),
        )
        self.assertEqual(
            instances["solive_01"].contrainte.references,
            ("traverse_01", "traverse_02"),
        )
        self.assertTrue(
            all(
                isinstance(instance.contrainte, EntreFaces)
                for identifiant, instance in instances.items()
                if identifiant.startswith(("traverse_", "solive_"))
            )
        )

        articles_graphe = {
            article.reference: quantite
            for article, quantite in assemblage.articles().items()
        }
        self.assertEqual(
            articles_graphe,
            {
                "MAD-120x240-L3000": 2,
                "MAD-120x240-L2756": 2,
                "SJI-60x240-L2750": 4,
            },
        )
        self.assertEqual(
            [operation.identifiant for operation in assemblage.operations()],
            [
                "implantation",
                "entre_rive_gauche_rive_droite",
                "entre_traverse_01_traverse_02",
            ],
        )
        self.assertEqual(
            [
                operation.identifiant
                for operation in AssemblageContraint(
                    tuple(reversed(assemblage.instances))
                ).operations()
            ],
            [operation.identifiant for operation in assemblage.operations()],
        )

    def test_assemblage_utilise_les_joints_rigides_build123d(self) -> None:
        assemblage = self.plancher.assemblage_poutres()
        gauche = assemblage.piece("rive_gauche")
        droite = assemblage.piece("rive_droite")
        traverse = assemblage.piece("traverse_01")
        solive = assemblage.piece("solive_01")

        self.assertTrue(all(isinstance(piece.location, Location) for piece in assemblage.pieces))
        self.assertIn("ancrage_rive_gauche", gauche.forme.joints)
        self.assertIs(
            gauche.forme.joints["connexion_rive_droite"].connected_to,
            droite.forme.joints["debut"],
        )
        self.assertIs(
            gauche.forme.joints["connexion_traverse_01"].connected_to,
            traverse.forme.joints["debut"],
        )
        self.assertIs(
            droite.forme.joints["connexion_traverse_01"].connected_to,
            traverse.forme.joints["fin"],
        )
        self.assertIs(
            traverse.forme.joints["connexion_solive_01"].connected_to,
            solive.forme.joints["debut"],
        )

    def test_manuel_assemblage_est_un_pdf_de_onze_pages(self) -> None:
        with TemporaryDirectory() as dossier:
            chemin = exporter_manuel_assemblage(
                self.local,
                Path(dossier) / "manuel.pdf",
            )
            contenu = chemin.read_bytes()

        self.assertTrue(contenu.startswith(b"%PDF-1.4"))
        self.assertTrue(contenu.rstrip().endswith(b"%%EOF"))
        self.assertEqual(contenu.count(b"/Type /Page "), 11)

    def test_couche_osb_porteuse_unique(self) -> None:
        osb = [
            element
            for element in self.local.elements()
            if element.nom.startswith("OSB porteur")
        ]

        self.assertEqual(len(osb), 10)
        self.assertFalse(
            any(
                element.nom.startswith("OSB supérieur")
                for element in self.local.elements()
            )
        )
        self.assertTrue(
            all(e.forme.bounding_box().min.Z == 240 for e in osb)
        )
        self.assertTrue(
            all(e.forme.bounding_box().max.Z == 262 for e in osb)
        )

    def test_joint_about_osb_est_sur_une_solive(self) -> None:
        osb = [
            element
            for element in self.local.elements()
            if element.nom.startswith("OSB porteur")
        ]

        joints_y = {
            round(y, 6)
            for element in osb
            for y in (
                element.forme.bounding_box().min.Y,
                element.forme.bounding_box().max.Y,
            )
            if -1_500 < y < 1_500
        }
        self.assertEqual(
            joints_y,
            {round(self.plancher.axes_solives_i()[-1], 6)},
        )

    def test_bom_achats_remplace_les_decoupes_par_dalles_brutes(self) -> None:
        lignes = self.local.nomenclature_achats().lignes
        references = {ligne.article.reference: ligne.quantite for ligne in lignes}

        self.assertFalse(
            any(reference.startswith("OSB-PLANCHER-") for reference in references)
        )
        self.assertEqual(references["OSB-RL-675x2500x22"], 7)
        self.assertEqual(references["KLIMAS-KMWHT-5X60"], 200)
        self.assertNotIn("KLIMAS-KMWHT-5X80", references)
        self.assertEqual(references["OSB-BD-1196x2800x12"], 13)
        self.assertEqual(references["ISOL-ISONAT-FLEX55-145x580x1220"], 49)
        self.assertEqual(references["SPAX-0191010400355"], 1_130)
        self.assertEqual(references["TAS-60x40-L2750"], 2)
        self.assertEqual(references["KLIMAS-KMWHT-6X160"], 20)

    def test_plan_debit_osb_tient_dans_sept_dalles(self) -> None:
        plan = plan_debit_osb(self.local)

        self.assertEqual(plan.nombre_barres, 7)
        self.assertEqual(plan.nombre_pieces, 10)
        self.assertTrue(all(barre.chute_mm >= 0 for barre in plan.barres))

    def test_isolant_remplit_les_cinq_caissons(self) -> None:
        isolants = [
            element
            for element in self.local.elements()
            if element.nom.startswith("Isolant Isonat")
        ]

        self.assertEqual(len(isolants), 15)
        self.assertEqual(
            sorted(
                round(element.forme.bounding_box().size.X, 6)
                for element in isolants
            ),
            [316.0] * 5 + [1_220.0] * 10,
        )
        self.assertTrue(
            all(
                round(element.forme.bounding_box().size.Y, 6) == 545.6
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

        self.assertEqual(len(panneaux), 5)
        self.assertTrue(
            all(
                element.forme.bounding_box().size.X == 2_750
                and round(element.forme.bounding_box().size.Y, 6) == 542.6
                and element.forme.bounding_box().min.Z == 39
                and element.forme.bounding_box().max.Z == 51
                for element in panneaux
            )
        )
        self.assertEqual(calepinage_fonds_caissons(self.local), (2, 2, 1))

    def test_tasseaux_ne_sont_necessaires_que_sur_les_deux_rives(self) -> None:
        tasseaux = [
            element
            for element in self.local.elements()
            if element.nom.startswith("Tasseau de rive")
        ]

        self.assertEqual(len(tasseaux), 2)
        self.assertTrue(
            all(
                element.forme.bounding_box().size.X == 2_750
                and element.forme.bounding_box().max.Z == 39
                for element in tasseaux
            )
        )

    def test_ossature_bois_forme_un_volume_unique_de_trois_metres(self) -> None:
        murs = self.local.murs.elements()

        self.assertEqual(self.local.murs.hauteur_ossature, 2_575)
        self.assertEqual(self.local.murs.hauteur_libre_ossature, 2_440)
        self.assertEqual(min(e.forme.bounding_box().min.X for e in murs), -12)
        self.assertEqual(max(e.forme.bounding_box().max.X for e in murs), 3_012)
        self.assertEqual(min(e.forme.bounding_box().min.Y for e in murs), -1_512)
        self.assertEqual(max(e.forme.bounding_box().max.Y for e in murs), 1_512)
        self.assertEqual(min(e.forme.bounding_box().min.Z for e in murs), 262)
        self.assertEqual(max(e.forme.bounding_box().max.Z for e in murs), 2_837)

    def test_facade_ne_comporte_qu_une_porte_standard(self) -> None:
        murs = self.local.murs
        panneaux = [
            element
            for element in murs.elements()
            if element.nom.startswith("Façade porte OSB")
        ]

        self.assertEqual(murs.largeur_porte_tableau, 900)
        self.assertEqual(murs.hauteur_porte_tableau, 2_150)
        self.assertEqual(len(panneaux), 6)
        self.assertFalse(
            any("fenêtre" in element.nom.lower() for element in murs.elements())
        )
        for element in panneaux:
            boite = element.forme.bounding_box()
            self.assertTrue(
                boite.max.X <= murs.debut_porte
                or boite.min.X >= murs.fin_porte
                or boite.min.Z >= murs.niveau_sol + murs.hauteur_porte_tableau
            )

    def test_debit_osb_mural_reemploie_les_chutes_au_dessus_de_la_porte(self) -> None:
        plan = calepinage_osb_murs(self.local)

        self.assertEqual(len(plan), 10)
        self.assertEqual(sum(len(decoupes) for _, decoupes in plan), 16)
        self.assertEqual(
            sum(
                reference.startswith("PORTE-HAUT")
                for _, decoupes in plan
                for _, _, reference in decoupes
            ),
            4,
        )

    def test_tous_les_joints_verticaux_osb_muraux_sont_sur_un_montant(self) -> None:
        for nom, axe, minimum, maximum in (
            ("Mur arrière", "X", 0, 3_000),
            ("Mur gauche", "Y", -1_500, 1_500),
            ("Mur droit", "Y", -1_500, 1_500),
        ):
            panneaux = [
                element
                for element in self.local.murs.elements()
                if element.nom.startswith(f"{nom} OSB")
            ]
            montants = [
                element.forme.bounding_box()
                for element in self.local.murs.elements()
                if element.nom.startswith(f"{nom} montant")
            ]
            joints = {
                coordonnee
                for panneau in panneaux
                for coordonnee in (
                    getattr(panneau.forme.bounding_box().min, axe),
                    getattr(panneau.forme.bounding_box().max, axe),
                )
                if minimum < coordonnee < maximum
            }
            for joint in joints:
                self.assertTrue(
                    any(
                        getattr(montant.min, axe) <= joint
                        <= getattr(montant.max, axe)
                        for montant in montants
                    ),
                    f"joint {nom} à {joint:g} mm sans montant",
                )

    def test_isolation_murale_utilise_trente_sept_panneaux(self) -> None:
        isolants = [
            element
            for element in self.local.murs.elements()
            if " isolant " in element.nom
        ]

        self.assertEqual(len(isolants), 48)
        self.assertEqual(self.local.murs.nombre_panneaux_isolant_achetes, 37)

    def test_bom_ossature_est_debite_dans_la_famille_commune(self) -> None:
        references = {
            ligne.article.reference: ligne.quantite
            for ligne in self.local.nomenclature_achats().lignes
        }

        self.assertEqual(references["BO-MOB-45x145-L3000"], 5)
        self.assertEqual(references["BO-MOB-45x145-L2710"], 6)
        self.assertEqual(references["BO-MOB-45x145-L2440"], 27)
        self.assertEqual(references["BO-MOB-45x145-L2105"], 2)
        self.assertEqual(references["BO-MOB-45x145-L1050"], 2)
        self.assertEqual(references["BO-MOB-45x145-L990"], 2)
        self.assertEqual(references["BO-MOB-45x145-L190"], 3)
        self.assertEqual(references["KLIMAS-KMWHT-6X100"], 200)


if __name__ == "__main__":
    unittest.main()
