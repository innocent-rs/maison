"""Générateur de manuel PDF piloté par un assemblage CAO déclaratif."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from textwrap import wrap
from typing import Iterable, Sequence

from build123d import Compound, Drawing

from home_framework.assemblage import (
    AssemblageContraint,
    PiecePlacee,
    formater_mm,
)


LARGEUR_PAGE = 595.28
HAUTEUR_PAGE = 841.89


class _PDF:
    """Petit écrivain PDF vectoriel suffisant pour ce livrable autonome."""

    def __init__(self) -> None:
        self.pages: list[bytes] = []

    @staticmethod
    def _nombre(valeur: float) -> str:
        return f"{valeur:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _texte_pdf(texte: str) -> bytes:
        donnees = texte.encode("cp1252", errors="replace")
        return donnees.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")

    def ajouter_page(self, commandes: Sequence[bytes]) -> None:
        self.pages.append(b"\n".join(commandes))

    def texte(
        self,
        x: float,
        y: float,
        texte: str,
        taille: float = 10,
        gras: bool = False,
        couleur: tuple[float, float, float] = (0.12, 0.15, 0.18),
    ) -> bytes:
        police = b"F2" if gras else b"F1"
        r, g, b = couleur
        return (
            f"BT /{police.decode()} {self._nombre(taille)} Tf "
            f"{self._nombre(r)} {self._nombre(g)} {self._nombre(b)} rg "
            f"{self._nombre(x)} {self._nombre(HAUTEUR_PAGE - y)} Td (".encode()
            + self._texte_pdf(texte)
            + b") Tj ET"
        )

    def ligne(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        couleur: tuple[float, float, float] = (0.2, 0.25, 0.3),
        epaisseur: float = 1,
        pointille: bool = False,
    ) -> bytes:
        r, g, b = couleur
        tirets = "[4 3] 0 d" if pointille else "[] 0 d"
        return (
            f"q {self._nombre(r)} {self._nombre(g)} {self._nombre(b)} RG "
            f"{self._nombre(epaisseur)} w {tirets} "
            f"{self._nombre(x1)} {self._nombre(HAUTEUR_PAGE - y1)} m "
            f"{self._nombre(x2)} {self._nombre(HAUTEUR_PAGE - y2)} l S Q"
        ).encode()

    def rectangle(
        self,
        x: float,
        y: float,
        largeur: float,
        hauteur: float,
        couleur: tuple[float, float, float],
        contour: tuple[float, float, float] | None = None,
    ) -> bytes:
        r, g, b = couleur
        operation = "f"
        contour_cmd = ""
        if contour is not None:
            cr, cg, cb = contour
            contour_cmd = f" {self._nombre(cr)} {self._nombre(cg)} {self._nombre(cb)} RG 0.8 w"
            operation = "B"
        return (
            f"q {self._nombre(r)} {self._nombre(g)} {self._nombre(b)} rg"
            f"{contour_cmd} {self._nombre(x)} {self._nombre(HAUTEUR_PAGE - y - hauteur)} "
            f"{self._nombre(largeur)} {self._nombre(hauteur)} re {operation} Q"
        ).encode()

    def ecrire(self, chemin: Path, titre: str) -> None:
        objets: list[bytes] = []

        def ajouter(contenu: bytes) -> int:
            objets.append(contenu)
            return len(objets)

        pages_id = ajouter(b"")
        police_id = ajouter(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>"
        )
        police_grasse_id = ajouter(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>"
        )
        ids_pages: list[int] = []
        for contenu in self.pages:
            flux_id = ajouter(
                f"<< /Length {len(contenu)} >>\nstream\n".encode()
                + contenu
                + b"\nendstream"
            )
            page_id = ajouter(
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R "
                    f"/MediaBox [0 0 {LARGEUR_PAGE:.2f} {HAUTEUR_PAGE:.2f}] "
                    f"/Resources << /Font << /F1 {police_id} 0 R /F2 {police_grasse_id} 0 R >> >> "
                    f"/Contents {flux_id} 0 R >>"
                ).encode()
            )
            ids_pages.append(page_id)

        objets[pages_id - 1] = (
            f"<< /Type /Pages /Count {len(ids_pages)} /Kids ["
            + " ".join(f"{identifiant} 0 R" for identifiant in ids_pages)
            + "] >>"
        ).encode()
        info_id = ajouter(
            b"<< /Title (" + self._texte_pdf(titre) + b") /Creator (home-framework / build123d) >>"
        )
        catalogue_id = ajouter(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())

        sortie = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for identifiant, objet in enumerate(objets, start=1):
            offsets.append(len(sortie))
            sortie.extend(f"{identifiant} 0 obj\n".encode())
            sortie.extend(objet)
            sortie.extend(b"\nendobj\n")
        debut_xref = len(sortie)
        sortie.extend(f"xref\n0 {len(objets) + 1}\n".encode())
        sortie.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            sortie.extend(f"{offset:010d} 00000 n \n".encode())
        sortie.extend(
            (
                f"trailer\n<< /Size {len(objets) + 1} /Root {catalogue_id} 0 R "
                f"/Info {info_id} 0 R >>\nstartxref\n{debut_xref}\n%%EOF\n"
            ).encode()
        )
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(sortie)


def _segments_projection(
    elements: Iterable[PiecePlacee],
    *,
    dessus: bool,
) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    formes = [element.forme for element in elements]
    if not formes:
        return ()
    dessin = Drawing(
        Compound(children=formes),
        look_at=(1_500, 0, 120),
        look_from=(0, 0, 1) if dessus else (1, -1, 0.8),
        look_up=(0, 1, 0) if dessus else (0, 0, 1),
        with_hidden=False,
    )
    segments = []
    for arete in dessin.visible_lines.edges():
        sommets = arete.vertices()
        if len(sommets) < 2:
            continue
        points = [(sommet.X, sommet.Y) for sommet in sommets]
        segments.extend(zip(points, points[1:]))
    return tuple(segments)


def _dessiner_projection(
    pdf: _PDF,
    commandes: list[bytes],
    couches: Sequence[
        tuple[
            Sequence[PiecePlacee],
            tuple[float, float, float],
            float,
        ]
    ],
    toutes: Sequence[PiecePlacee],
    zone: tuple[float, float, float, float],
    *,
    dessus: bool,
) -> None:
    segments_reference = _segments_projection(toutes, dessus=dessus)
    points = [point for segment in segments_reference for point in segment]
    if not points:
        return
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    x, y, largeur, hauteur = zone
    marge = 10
    echelle = min(
        (largeur - 2 * marge) / max(max_x - min_x, 1),
        (hauteur - 2 * marge) / max(max_y - min_y, 1),
    )
    origine_x = x + (largeur - (max_x - min_x) * echelle) / 2
    origine_y = y + (hauteur - (max_y - min_y) * echelle) / 2

    for elements, couleur, epaisseur in couches:
        for (x1, y1), (x2, y2) in _segments_projection(elements, dessus=dessus):
            px1 = origine_x + (x1 - min_x) * echelle
            py1 = origine_y + (max_y - y1) * echelle
            px2 = origine_x + (x2 - min_x) * echelle
            py2 = origine_y + (max_y - y2) * echelle
            commandes.append(
                pdf.ligne(px1, py1, px2, py2, couleur, epaisseur)
            )


def _entete(pdf: _PDF, commandes: list[bytes], page: int, titre: str) -> None:
    commandes.append(pdf.rectangle(0, 0, LARGEUR_PAGE, 12, (0.92, 0.43, 0.12)))
    commandes.append(pdf.texte(40, 48, "ASSEMBLAGE CAO · MANUEL", 9, True, (0.42, 0.45, 0.48)))
    commandes.append(pdf.texte(40, 78, titre, 22, True))
    commandes.append(pdf.texte(520, 48, f"{page:02d}", 10, True, (0.42, 0.45, 0.48)))


def _pied_page(pdf: _PDF, commandes: list[bytes]) -> None:
    commandes.append(pdf.ligne(40, 801, 555, 801, (0.82, 0.84, 0.86), 0.6))
    commandes.append(
        pdf.texte(
            40,
            821,
            "POC géométrique — fixations, connecteurs et validation structurelle hors périmètre",
            8,
            False,
            (0.42, 0.45, 0.48),
        )
    )


def _lignes_texte(
    pdf: _PDF,
    commandes: list[bytes],
    x: float,
    y: float,
    texte: str,
    largeur_caracteres: int,
    taille: float = 10,
    interligne: float = 15,
) -> float:
    for ligne in wrap(texte, width=largeur_caracteres):
        commandes.append(pdf.texte(x, y, ligne, taille))
        y += interligne
    return y


def exporter_manuel(
    assemblage: AssemblageContraint,
    chemin: Path | str,
    *,
    titre: str,
    sous_titre: str,
) -> Path:
    """Rend un graphe d'assemblage quelconque sous forme de manuel PDF."""
    destination = Path(chemin)
    poutres = assemblage.pieces
    etapes = assemblage.operations()
    largeur_hors_tout = max(e.forme.bounding_box().max.Y for e in poutres) - min(
        e.forme.bounding_box().min.Y for e in poutres
    )
    longueur_hors_tout = max(e.forme.bounding_box().max.X for e in poutres) - min(
        e.forme.bounding_box().min.X for e in poutres
    )
    pdf = _PDF()

    # Couverture
    commandes: list[bytes] = []
    commandes.append(pdf.rectangle(0, 0, LARGEUR_PAGE, 250, (0.09, 0.12, 0.15)))
    commandes.append(pdf.rectangle(40, 48, 72, 7, (0.92, 0.43, 0.12)))
    commandes.append(pdf.texte(40, 100, "MANUEL D'ASSEMBLAGE", 11, True, (0.92, 0.43, 0.12)))
    commandes.append(pdf.texte(40, 142, titre, 24, True, (1, 1, 1)))
    commandes.append(
        pdf.texte(
            40,
            180,
            sous_titre,
            18,
            False,
            (0.82, 0.85, 0.88),
        )
    )
    _dessiner_projection(
        pdf,
        commandes,
        ((poutres, (0.17, 0.22, 0.27), 1.0),),
        poutres,
        (40, 285, 515, 330),
        dessus=False,
    )
    for x, valeur, libelle in (
        (40, str(len(poutres)), "composants CAO"),
        (214, str(len(etapes)), "opérations"),
        (388, formater_mm(longueur_hors_tout), "mm hors-tout"),
    ):
        commandes.append(pdf.texte(x, 680, valeur, 24, True, (0.92, 0.43, 0.12)))
        commandes.append(pdf.texte(x, 702, libelle, 9, False, (0.35, 0.39, 0.43)))
    commandes.append(
        pdf.texte(
            40,
            760,
            "Généré depuis le graphe de contraintes et les solides build123d",
            10,
            True,
        )
    )
    commandes.append(pdf.texte(40, 780, titre, 9, False, (0.42, 0.45, 0.48)))
    pdf.ajouter_page(commandes)

    # Inventaire et plan d'implantation
    commandes = []
    _entete(pdf, commandes, 2, "Inventaire et implantation")
    compte = Counter(e.article_bom().reference for e in poutres)
    articles = {e.article_bom().reference: e.article_bom() for e in poutres}
    y = 125
    commandes.append(pdf.rectangle(40, 102, 515, 30, (0.95, 0.96, 0.97)))
    commandes.append(pdf.texte(54, 122, "QTÉ", 8, True, (0.4, 0.43, 0.46)))
    commandes.append(pdf.texte(105, 122, "RÉFÉRENCE ISSUE DE LA CAO", 8, True, (0.4, 0.43, 0.46)))
    commandes.append(pdf.texte(340, 122, "DÉSIGNATION", 8, True, (0.4, 0.43, 0.46)))
    for reference, quantite in compte.items():
        article = articles[reference]
        y += 25
        commandes.append(pdf.texte(58, y, str(quantite), 11, True, (0.92, 0.43, 0.12)))
        commandes.append(pdf.texte(105, y, reference, 8, True))
        designation = article.designation.replace(" — ", ", ")
        commandes.append(pdf.texte(340, y, designation[:48], 7))
        commandes.append(pdf.ligne(40, y + 9, 555, y + 9, (0.88, 0.89, 0.9), 0.5))
    debut_plan = max(290, y + 35)
    commandes.append(
        pdf.texte(
            40,
            debut_plan - 15,
            "PLAN D'IMPLANTATION · VUE DE DESSUS",
            9,
            True,
            (0.42, 0.45, 0.48),
        )
    )
    _dessiner_projection(
        pdf,
        commandes,
        ((poutres, (0.16, 0.2, 0.24), 0.75),),
        poutres,
        (60, debut_plan, 475, 700 - debut_plan),
        dessus=True,
    )
    nombre_relations = sum(
        len(instance.contrainte.references) for instance in assemblage.instances
    )
    commandes.append(
        pdf.texte(
            65,
            735,
            f"Graphe CAO : {len(assemblage.instances)} pièces · "
            f"{nombre_relations} relations orientées · {len(etapes)} opérations",
            9,
            True,
        )
    )
    commandes.append(
        pdf.texte(
            65,
            755,
            "Ordre et regroupements déduits des références de chaque contrainte.",
            9,
        )
    )
    _pied_page(pdf, commandes)
    pdf.ajouter_page(commandes)

    # Une page par opération de pose.
    for etape in etapes:
        numero_page = etape.numero + 2
        commandes = []
        _entete(pdf, commandes, numero_page, f"Étape {etape.numero} · {etape.titre}")
        commandes.append(pdf.rectangle(40, 102, 515, 66, (0.97, 0.94, 0.9), (0.92, 0.43, 0.12)))
        commandes.append(
            pdf.texte(
                56,
                126,
                f"AJOUTER {len(etape.nouvelles)} "
                f"PIÈCE{'S' if len(etape.nouvelles) > 1 else ''}",
                9,
                True,
                (0.82, 0.31, 0.06),
            )
        )
        _lignes_texte(pdf, commandes, 56, 148, etape.instruction, 82, 9, 13)

        couches = []
        if etape.deja_posees:
            couches.append((etape.deja_posees, (0.68, 0.71, 0.73), 0.55))
        couches.append((etape.nouvelles, (0.92, 0.35, 0.08), 1.3))
        _dessiner_projection(
            pdf,
            commandes,
            tuple(couches),
            poutres,
            (40, 190, 515, 405),
            dessus=False,
        )
        commandes.append(pdf.rectangle(40, 600, 515, 145, (0.95, 0.96, 0.97)))
        commandes.append(pdf.texte(56, 625, "CONTRÔLES CAO", 9, True, (0.42, 0.45, 0.48)))
        y_controle = 648
        for controle in etape.controles:
            commandes.append(pdf.texte(58, y_controle, "• " + controle, 8))
            y_controle += 17
        commandes.append(pdf.texte(420, 758, "orange = à poser", 8, True, (0.82, 0.31, 0.06)))
        commandes.append(pdf.texte(420, 774, "gris = déjà posé", 8, False, (0.45, 0.48, 0.5)))
        _pied_page(pdf, commandes)
        pdf.ajouter_page(commandes)

    pdf.ecrire(destination, f"Manuel d'assemblage — {titre}")
    return destination
