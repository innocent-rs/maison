import shutil
import tempfile
import unittest
from pathlib import Path

from home_framework.simulation import (
    AppuiCalculix,
    ChargeNodaleCalculix,
    ElementPoutreCalculix,
    ModeleCalculix,
    NoeudCalculix,
    SectionPoutreCalculix,
    ZoneCharge,
    executer_calculix,
    generer_images_deplacement,
    lire_resultats_dat,
)
from local_batteries import creer_local_batteries
from local_batteries.simulation import (
    HypothesesCalculixLocal,
    generer_modele_calculix,
)


class TestExportCalculix(unittest.TestCase):
    def test_entree_minimale_est_autonome(self) -> None:
        modele = ModeleCalculix(
            nom="Console test",
            noeuds=(
                NoeudCalculix(1, 0, 0, 0),
                NoeudCalculix(2, 1_000, 0, 0),
            ),
            sections=(SectionPoutreCalculix("BOIS", 240, 120, 11_000),),
            elements=(ElementPoutreCalculix(1, 1, 2, "BOIS"),),
            equations=(),
            appuis=(AppuiCalculix(1, 1, 6),),
            charges=(ChargeNodaleCalculix(2, fz_n=-1_000),),
        )

        entree = modele.entree()

        self.assertIn("*ELEMENT, TYPE=B31, ELSET=BOIS", entree)
        self.assertIn("*BEAM SECTION", entree)
        self.assertIn("*STATIC", entree)
        self.assertIn("2, 3, -1000", entree)
        self.assertIn("*EL FILE\nS", entree)
        self.assertAlmostEqual(modele.charge_verticale_n, 1_000)

    def test_lecture_des_deplacements_et_reactions(self) -> None:
        contenu = """
 displacements (vx,vy,vz) for set NALL and time  0.1000000E+01

         1  0.000000E+00  0.000000E+00  0.000000E+00
         2  0.000000E+00  0.000000E+00 -1.250000E+00

 forces (fx,fy,fz) for set APPUIS and time  0.1000000E+01

         1  0.000000E+00  0.000000E+00  1.000000E+03

"""

        deplacements, reactions = lire_resultats_dat(contenu)

        self.assertEqual(deplacements[2][2], -1.25)
        self.assertEqual(reactions[1][2], 1_000)


class TestCalculixLocalBatteries(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.local = creer_local_batteries()
        cls.modele = generer_modele_calculix(cls.local)

    def test_maillage_est_derive_de_la_trame_cao(self) -> None:
        plancher = self.local.plancher
        coordonnees = {
            (round(noeud.x_mm, 6), round(noeud.y_mm, 6))
            for noeud in self.modele.noeuds
        }

        self.assertEqual(len(self.modele.noeuds), 22)
        self.assertEqual(len(self.modele.elements), 26)
        self.assertEqual(
            sum(e.section == "SJ60_240_EQUIVALENTE" for e in self.modele.elements),
            2 * plancher.nombre_solives_i,
        )
        self.assertTrue(
            all(
                (round(x, 6), round(y, 6)) in coordonnees
                for x in plancher.axes_traverses()
                for y in plancher.axes_solives_i()
            )
        )

    def test_la_tonne_de_batteries_ajoute_exactement_son_poids(self) -> None:
        modele_1kg = generer_modele_calculix(
            self.local, HypothesesCalculixLocal(masse_batteries_kg=1)
        )
        difference = self.modele.charge_verticale_n - modele_1kg.charge_verticale_n

        self.assertAlmostEqual(difference, 999 * 9.81, places=6)
        self.assertAlmostEqual(self.modele.charge_verticale_n, 14_086.249498584)

    def test_hypotheses_critiques_sont_dans_le_fichier(self) -> None:
        entree = self.modele.entree()

        self.assertIn("intersections SAI et EWH parfaitement rigides", entree)
        self.assertIn("OSB non rigidifiant", entree)
        self.assertIn("batteries 1000 kg sur 1000 x 1000 mm", entree)

    def test_empreinte_hors_plancher_est_refusee(self) -> None:
        with self.assertRaisesRegex(ValueError, "entièrement sur le plancher"):
            generer_modele_calculix(
                self.local,
                HypothesesCalculixLocal(
                    empreinte_longueur_mm=1_000,
                    centre_x_mm=250,
                ),
            )

    def test_genere_les_deux_images_de_fleche(self) -> None:
        deplacements = {
            noeud.identifiant: (
                0.0,
                0.0,
                -max(
                    0.01,
                    1.5
                    * (1 - abs(noeud.x_mm - 1_500) / 1_500)
                    * (1 - abs(noeud.y_mm) / 1_500),
                ),
            )
            for noeud in self.modele.noeuds
        }
        with tempfile.TemporaryDirectory() as dossier:
            images = generer_images_deplacement(
                self.modele,
                deplacements,
                Path(dossier),
                ZoneCharge(1_000, 2_000, -500, 500, "Batteries"),
            )
            carte = images.carte_fleche.read_bytes()
            deformee = images.deformation_3d.read_bytes()

        self.assertTrue(carte.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(deformee.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(carte), 10_000)
        self.assertGreater(len(deformee), 10_000)

    @unittest.skipUnless(shutil.which("ccx"), "CalculiX absent du PATH")
    def test_calculix_resout_et_equilibre_le_poc(self) -> None:
        with tempfile.TemporaryDirectory() as dossier:
            resultat = executer_calculix(self.modele, Path(dossier))

        self.assertAlmostEqual(
            resultat.somme_reactions_z_n,
            resultat.charge_verticale_n,
            delta=0.002,
        )
        self.assertGreater(resultat.fleche_max_mm, 0)
        self.assertTrue(Path(resultat.fichier_frd).name.endswith(".frd"))


if __name__ == "__main__":
    unittest.main()
