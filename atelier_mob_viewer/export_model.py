"""Exporte le plancher atelier_mob en couches glTF pour le viewer Three.js."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import sys

from build123d import Compound, export_gltf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from atelier_mob.modele import creer_atelier_mob  # noqa: E402


OUTPUT_DIR = Path(__file__).resolve().parent / "public" / "models"


@dataclass(frozen=True, slots=True)
class LayerDefinition:
    id: str
    label: str
    description: str
    color: str
    piece_types: tuple[str, ...]
    explode_offset_m: float = 0.0
    visible: bool = True


LAYERS = (
    LayerDefinition(
        "fondations",
        "Platines de fondation",
        "Platines acier des 24 pieux vissés",
        "#54748c",
        ("PlatinePieuVisse",),
        explode_offset_m=-1.6,
    ),
    LayerDefinition(
        "poutres_primaires",
        "Poutres primaires",
        "Longrines de rive et huit traverses en 120 × 240 mm",
        "#9b5d35",
        ("Madrier",),
    ),
    LayerDefinition(
        "connecteurs_primaires",
        "Sabots des traverses",
        "Connecteurs Simpson SAI entre traverses et longrines",
        "#68737d",
        ("SabotSAI500_120_2",),
    ),
    LayerDefinition(
        "solives_i",
        "Solives en I",
        "Solives STEICOjoist SJ60/240 entre les traverses",
        "#d6ae73",
        ("PoutreI",),
        explode_offset_m=0.8,
    ),
    LayerDefinition(
        "entretoises_i",
        "Entretoises en I",
        "Une rangée pleine hauteur au milieu de chaque travée",
        "#ad7958",
        ("EntretoisePoutreI",),
        explode_offset_m=0.8,
    ),
    LayerDefinition(
        "connecteurs_solives",
        "Étriers des solives",
        "Étriers Simpson EWH aux abouts des solives en I",
        "#82909a",
        ("SabotEWH",),
        explode_offset_m=0.8,
    ),
    LayerDefinition(
        "tasseaux",
        "Tasseaux de rive",
        "Appuis 60 × 40 mm sous les fonds de caisson latéraux",
        "#b77a45",
        ("Tasseau",),
        explode_offset_m=0.8,
    ),
    LayerDefinition(
        "fonds_osb",
        "Fonds de caisson OSB",
        "Panneaux OSB de 12 mm sous l’isolation",
        "#b88a50",
        ("PanneauFondCaissonOSB",),
        explode_offset_m=-0.8,
    ),
    LayerDefinition(
        "isolant",
        "Isolant",
        "Panneaux Isonat Flex 55 de 145 mm",
        "#c9bd72",
        ("PanneauIsonatFlex55",),
        explode_offset_m=1.6,
    ),
    LayerDefinition(
        "osb_superieur",
        "OSB supérieur",
        "Dalles de plancher OSB de 22 mm",
        "#d47a2b",
        ("PanneauPlancherOSB",),
        explode_offset_m=2.4,
    ),
)


def _mass_metadata(atelier, elements_by_layer):
    report = atelier.inventorier_masses()
    report_by_reference = {line.reference: line for line in report.lignes}
    hypotheses = report.hypotheses

    metadata = {}
    for layer in LAYERS:
        elements = elements_by_layer[layer.id]
        references = {element.piece.article_bom().reference for element in elements}
        report_lines = [
            report_by_reference[reference]
            for reference in references
            if reference in report_by_reference
        ]
        mass_kg = sum(line.masse_totale_kg for line in report_lines)

        if layer.id == "fondations":
            mass_kg = sum(
                element.piece.volume_mm3
                / 1_000_000_000
                * hypotheses.masse_volumique_acier_kg_m3
                for element in elements
            )

        linear_masses = {
            line.masse_lineique_kg_m
            for line in report_lines
            if line.masse_lineique_kg_m is not None
        }
        unit_mass = None
        if len(report_lines) == 1 and report_lines[0].quantite:
            unit_mass = report_lines[0].masse_unitaire_kg

        metadata[layer.id] = {
            "massKg": round(mass_kg, 3),
            "linearMassKgM": (
                round(next(iter(linear_masses)), 3)
                if len(linear_masses) == 1
                else None
            ),
            "unitMassKg": round(unit_mass, 3) if unit_mass is not None else None,
        }

    return metadata, report


def export_viewer_model(output_dir: Path = OUTPUT_DIR) -> Path:
    """Génère un GLB par couche et retourne le chemin du manifeste JSON."""

    atelier = creer_atelier_mob()
    elements = tuple(atelier.elements())
    elements_by_layer = {
        layer.id: [
            element
            for element in elements
            if type(element.piece).__name__ in layer.piece_types
        ]
        for layer in LAYERS
    }

    classified = sum(len(items) for items in elements_by_layer.values())
    if classified != len(elements):
        classified_types = {name for layer in LAYERS for name in layer.piece_types}
        missing = Counter(
            type(element.piece).__name__
            for element in elements
            if type(element.piece).__name__ not in classified_types
        )
        raise RuntimeError(f"pièces sans couche viewer : {dict(missing)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    mass_metadata, mass_report = _mass_metadata(atelier, elements_by_layer)
    rapport_vides = atelier.analyser_vides()

    manifest_layers = []
    for layer in LAYERS:
        layer_elements = elements_by_layer[layer.id]
        file_name = f"{layer.id}.glb"
        compound = Compound(
            children=[element.forme for element in layer_elements],
            label=layer.label,
        )
        export_gltf(
            compound,
            output_dir / file_name,
            binary=True,
            linear_deflection=0.1,
            angular_deflection=0.15,
        )
        manifest_layers.append(
            {
                "id": layer.id,
                "label": layer.label,
                "description": layer.description,
                "color": layer.color,
                "file": file_name,
                "count": len(layer_elements),
                "visible": layer.visible,
                "explodeOffsetM": layer.explode_offset_m,
                **mass_metadata[layer.id],
            }
        )

    modeled_mass = sum(layer["massKg"] for layer in manifest_layers)
    void_file_name = "vides_structure.glb"
    export_gltf(
        Compound(
            children=[
                composante.forme
                for composante in rapport_vides.composantes
            ],
            label="Vides détectés dans l’enveloppe du plancher",
        ),
        output_dir / void_file_name,
        binary=True,
        linear_deflection=0.1,
        angular_deflection=0.15,
    )
    manifest_layers.append(
        {
            "id": "vides_structure",
            "label": "Vides détectés",
            "description": (
                "Résultat automatique : enveloppe intérieure moins toutes "
                "les pièces volumiques du plancher"
            ),
            "color": "#d94b64",
            "file": void_file_name,
            "count": rapport_vides.nombre_composantes,
            "visible": False,
            "explodeOffsetM": 0.8,
            "massKg": None,
            "linearMassKgM": None,
            "unitMassKg": None,
            "opacity": 0.38,
            "diagnostic": True,
            "volumeM3": round(rapport_vides.volume_vide_m3, 3),
            "voidRatePercent": round(rapport_vides.taux_vide_pct, 2),
        }
    )
    foundation_mass = mass_metadata["fondations"]["massKg"]
    manifest = {
        "project": {
            "name": "Atelier MOB — plancher bois",
            "widthM": atelier.geometrie.largeur_interieure / 1_000,
            "lengthM": atelier.geometrie.longueur_interieure / 1_000,
            "objectCount": len(elements),
            "coordinateUnit": "m",
        },
        "summary": {
            "modeledMassKg": round(modeled_mass, 3),
            "floorMassIncludingFastenersKg": round(
                mass_report.masse_totale_kg,
                3,
            ),
            "foundationPlatesMassKg": foundation_mass,
            "totalMassIncludingFastenersKg": round(
                mass_report.masse_totale_kg + foundation_mass,
                3,
            ),
            "floorAreaM2": round(mass_report.surface_plancher_m2, 3),
            "voidAnalysis": {
                "method": "Pré-diagnostic géométrique — pas un calcul psi ISO 10211",
                "componentCount": rapport_vides.nombre_composantes,
                "occupantCount": rapport_vides.nombre_occupants,
                "analysisEnvelopeVolumeM3": round(
                    rapport_vides.volume_enveloppe_m3,
                    3,
                ),
                "uninsulatedVoidVolumeM3": round(
                    rapport_vides.volume_vide_m3,
                    3,
                ),
                "voidRatePercent": round(
                    rapport_vides.taux_vide_pct,
                    2,
                ),
            },
        },
        "layers": manifest_layers,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> None:
    manifest_path = export_viewer_model()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(
        f"Viewer exporté : {manifest['project']['objectCount']} objets, "
        f"{len(manifest['layers'])} couches -> {manifest_path}"
    )


if __name__ == "__main__":
    main()
