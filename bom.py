"""Exporte la nomenclature du projet courant."""

from pathlib import Path

from main import make_part


def main() -> None:
    destination = Path("build/bom.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)

    nomenclature = make_part().nomenclature()
    nomenclature.ecrire_csv(destination)

    print(f"BOM : {nomenclature.nombre_pieces} pièces, {len(nomenclature.lignes)} articles")
    for ligne in nomenclature.lignes:
        print(f"  {ligne.quantite:>3} × {ligne.article.designation}")
    print(f"CSV écrit dans {destination}")


if __name__ == "__main__":
    main()
