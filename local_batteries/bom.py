"""Exporte les nomenclatures du plancher du local batteries."""

from pathlib import Path

from local_batteries import creer_local_batteries


def main() -> None:
    destination = Path("build/local_batteries")
    destination.mkdir(parents=True, exist_ok=True)

    local = creer_local_batteries()
    fabrication = local.nomenclature()
    achats = local.nomenclature_achats()
    fabrication.ecrire_csv(destination / "bom_fabrication.csv")
    achats.ecrire_csv(destination / "bom_achats.csv")

    print(
        f"BOM fabrication : {fabrication.nombre_pieces} pièces, "
        f"{len(fabrication.lignes)} articles"
    )
    print(
        f"BOM achats : {achats.nombre_pieces} unités, "
        f"{len(achats.lignes)} articles"
    )
    print(f"CSV écrits dans {destination}")


if __name__ == "__main__":
    main()
