import unittest

from projets import PROJETS, resoudre_projet_et_lot


class TestRegistreProjets(unittest.TestCase):
    def test_local_batteries_expose_sa_bom_au_framework_commun(self) -> None:
        definition = PROJETS["local_batteries"]
        projet = definition.construire()

        self.assertEqual(
            definition.lots_demandes("tous"),
            ("plancher", "murs", "total"),
        )
        self.assertEqual(
            definition.nomenclature(projet, "total").nombre_pieces,
            projet.nomenclature_achats().nombre_pieces,
        )

    def test_anciens_raccourcis_just_restent_compatibles(self) -> None:
        definition, lot = resoudre_projet_et_lot("plancher", "tous")

        self.assertEqual(definition.identifiant, "maison")
        self.assertEqual(definition.lots_demandes(lot), ("plancher",))


if __name__ == "__main__":
    unittest.main()
