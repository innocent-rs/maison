import io
import unittest

from maison.geometrie import GeometrieAFrame
from maison.structure import PlancherAFrame


class TestNomenclature(unittest.TestCase):
    def setUp(self) -> None:
        self.plancher = PlancherAFrame(GeometrieAFrame())
        self.bom = self.plancher.nomenclature()

    def test_regroupe_les_coupes_identiques(self) -> None:
        self.assertEqual(len(self.bom.lignes), 4)
        self.assertEqual(self.bom.nombre_pieces, 311)
        self.assertEqual(
            sorted(ligne.quantite for ligne in self.bom.lignes),
            [2, 3, 6, 300],
        )

    def test_totaux(self) -> None:
        ligne_traverses = next(
            ligne
            for ligne in self.bom.lignes
            if ligne.article.reference == "MAD-120x250-L5756"
        )
        self.assertAlmostEqual(ligne_traverses.longueur_totale_mm, 17_268)

    def test_export_csv(self) -> None:
        sortie = io.StringIO()
        self.bom.ecrire_csv(sortie)

        contenu = sortie.getvalue()
        self.assertIn("reference;categorie;designation", contenu)
        self.assertIn("MAD-120x250-L5756", contenu)
        self.assertIn("SIMPSON-SAI500-120-2", contenu)
        self.assertIn("SIMPSON-CSA5.0X40", contenu)

    def test_bom_avec_solives_i_et_ewh(self) -> None:
        plancher = PlancherAFrame(GeometrieAFrame(), inclure_solives_i=True)
        lignes = {ligne.article.reference: ligne for ligne in plancher.nomenclature().lignes}

        self.assertEqual(lignes["SIMPSON-EWH219-91"].quantite, 44)
        self.assertEqual(lignes["SIMPSON-CNA4.0X35"].quantite, 704)
        ligne_solives = next(
            ligne
            for reference, ligne in lignes.items()
            if reference.startswith("SJI-90x220")
        )
        self.assertEqual(ligne_solives.quantite, 22)

    def test_bom_avec_fonds_de_caisson_osb(self) -> None:
        plancher = PlancherAFrame(
            GeometrieAFrame(),
            inclure_solives_i=True,
            inclure_osb_caissons=True,
        )
        lignes = {ligne.article.reference: ligne for ligne in plancher.nomenclature().lignes}
        lignes_osb = [
            ligne
            for reference, ligne in lignes.items()
            if reference.startswith("OSB-FOND-")
        ]

        self.assertEqual(sorted(ligne.quantite for ligne in lignes_osb), [4, 20])
        self.assertEqual(lignes["VIS-BOIS-OSB-4X35"].quantite, 768)
        ligne_tasseaux = next(
            ligne
            for reference, ligne in lignes.items()
            if reference.startswith("TAS-90x45-")
        )
        self.assertEqual(ligne_tasseaux.quantite, 4)

    def test_bom_de_la_trame_modulaire_isolee(self) -> None:
        plancher = PlancherAFrame(
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
            inclure_osb_plancher=True,
        )
        lignes = {
            ligne.article.reference: ligne for ligne in plancher.nomenclature().lignes
        }

        self.assertEqual(
            lignes["ISOL-STEICOFLEX036-120x575x1220"].quantite,
            24,
        )
        self.assertEqual(lignes["VIS-BOIS-OSB-4X35"].quantite, 384)
        lignes_osb = [
            ligne
            for reference, ligne in lignes.items()
            if reference.startswith("OSB-FOND-562x1214x12")
        ]
        self.assertEqual(sum(ligne.quantite for ligne in lignes_osb), 24)
        lignes_osb_plancher = [
            ligne
            for reference, ligne in lignes.items()
            if reference.startswith("OSB-PLANCHER-")
        ]
        self.assertEqual(sum(ligne.quantite for ligne in lignes_osb_plancher), 22)
        self.assertEqual(lignes["VIS-PLANCHER-OSB-5X60"].quantite, 483)


if __name__ == "__main__":
    unittest.main()
