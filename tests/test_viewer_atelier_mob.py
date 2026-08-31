import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from atelier_mob_viewer.export_model import export_viewer_model


class TestExportViewerAtelierMob(unittest.TestCase):
    def test_exporte_la_couche_de_vides_sans_modifier_la_masse(self) -> None:
        with TemporaryDirectory() as repertoire:
            manifest_path = export_viewer_model(Path(repertoire))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            void_analysis = manifest["summary"]["voidAnalysis"]
            layer = next(
                item
                for item in manifest["layers"]
                if item["id"] == "vides_structure"
            )

            self.assertEqual(len(manifest["layers"]), 11)
            self.assertEqual(manifest["project"]["objectCount"], 813)
            self.assertEqual(void_analysis["componentCount"], 1)
            self.assertEqual(void_analysis["occupantCount"], 339)
            self.assertEqual(void_analysis["analysisEnvelopeVolumeM3"], 19.845)
            self.assertEqual(void_analysis["uninsulatedVoidVolumeM3"], 4.07)
            self.assertEqual(void_analysis["voidRatePercent"], 20.51)
            self.assertTrue(layer["diagnostic"])
            self.assertFalse(layer["visible"])
            self.assertIsNone(layer["massKg"])
            self.assertEqual(
                (Path(repertoire) / layer["file"]).read_bytes()[:4],
                b"glTF",
            )
            self.assertAlmostEqual(
                manifest["summary"]["modeledMassKg"],
                sum(item["massKg"] or 0 for item in manifest["layers"]),
            )


if __name__ == "__main__":
    unittest.main()
