"""Assemblages CAO contraints, source commune de géométrie et de fabrication.

Une instance associe une pièce de nomenclature à une contrainte orientée. Le
graphe résout les formes finales et déduit une suite d'opérations à partir des
dépendances, sans maintenir une timeline séparée.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol, Sequence

from build123d import Pos, Rot, Shape

from maison.nomenclature import ArticleBOM, Nomenclaturable


def formater_mm(valeur: float) -> str:
    """Formate une cote avec la typographie française."""
    if abs(valeur - round(valeur)) < 1e-6:
        return f"{round(valeur):,}".replace(",", " ")
    return f"{valeur:,.1f}".replace(",", " ").replace(".", ",")


@dataclass(frozen=True, slots=True)
class PlacementResolu:
    forme: Shape
    origine: tuple[float, float, float]
    rotation: tuple[float, float, float]


class ContraintePlacement(Protocol):
    """Relation orientée capable de placer sa pièce mobile."""

    @property
    def references(self) -> tuple[str, ...]: ...

    @property
    def cle_operation(self) -> tuple[object, ...]: ...

    def resoudre(
        self,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu: ...


def _construire_piece(
    piece: Nomenclaturable,
    origine: tuple[float, float, float],
    rotation: tuple[float, float, float],
) -> PlacementResolu:
    construire = getattr(piece, "construire", None)
    if construire is None:
        raise TypeError("une pièce d'assemblage doit fournir construire()")
    forme = Pos(*origine) * Rot(*rotation) * construire()
    return PlacementResolu(forme, origine, rotation)


@dataclass(frozen=True, slots=True)
class Ancrage:
    """Place la première pièce dans le repère global de l'assemblage."""

    origine: tuple[float, float, float]
    rotation: tuple[float, float, float] = (0, 0, 0)

    @property
    def references(self) -> tuple[str, ...]:
        return ()

    @property
    def cle_operation(self) -> tuple[object, ...]:
        return (type(self),)

    def resoudre(
        self,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu:
        del references
        return _construire_piece(piece, self.origine, self.rotation)


@dataclass(frozen=True, slots=True)
class DecalageParallele:
    """Copie l'orientation d'une référence avec une translation imposée."""

    reference: str
    translation: tuple[float, float, float]

    @property
    def references(self) -> tuple[str, ...]:
        return (self.reference,)

    @property
    def cle_operation(self) -> tuple[object, ...]:
        return (type(self), self.reference)

    def resoudre(
        self,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu:
        appui = references[self.reference]
        origine = tuple(
            valeur + decalage
            for valeur, decalage in zip(appui.origine, self.translation)
        )
        return _construire_piece(piece, origine, appui.rotation)


@dataclass(frozen=True, slots=True)
class EntreFaces:
    """Place une pièce entre deux faces opposées de pièces déjà résolues.

    Les composants linéaires suivent la convention du framework : leur axe
    local est X. ``axe_portee`` choisit si cet axe reste globalement X ou est
    tourné suivant Y. La cote transversale fixe alors respectivement Y ou X.
    """

    reference_debut: str
    reference_fin: str
    axe_portee: str
    position_transversale: float
    niveau: float = 0
    jeu_about: float = 0

    def __post_init__(self) -> None:
        if self.axe_portee not in ("X", "Y"):
            raise ValueError("l'axe de portée doit être X ou Y")
        if self.jeu_about < 0:
            raise ValueError("le jeu d'about ne peut pas être négatif")

    @property
    def references(self) -> tuple[str, ...]:
        return (self.reference_debut, self.reference_fin)

    @property
    def cle_operation(self) -> tuple[object, ...]:
        return (
            type(self),
            self.reference_debut,
            self.reference_fin,
            self.axe_portee,
        )

    def resoudre(
        self,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu:
        debut = references[self.reference_debut].forme.bounding_box()
        fin = references[self.reference_fin].forme.bounding_box()
        longueur_piece = getattr(piece, "longueur", None)
        if longueur_piece is None:
            raise TypeError("une pièce placée entre faces doit fournir longueur")

        if self.axe_portee == "X":
            origine_axe = debut.max.X + self.jeu_about
            fin_axe = fin.min.X - self.jeu_about
            origine = (origine_axe, self.position_transversale, self.niveau)
            rotation = (0, 0, 0)
        else:
            origine_axe = debut.max.Y + self.jeu_about
            fin_axe = fin.min.Y - self.jeu_about
            origine = (self.position_transversale, origine_axe, self.niveau)
            rotation = (0, 0, 90)

        longueur_disponible = fin_axe - origine_axe
        if abs(longueur_piece - longueur_disponible) > 1e-6:
            raise ValueError(
                f"la longueur {longueur_piece:g} mm ne correspond pas à "
                f"l'espace contraint {longueur_disponible:g} mm"
            )
        return _construire_piece(piece, origine, rotation)


@dataclass(frozen=True, slots=True)
class PieceInstance:
    """Pièce à résoudre, avec identité stable et intention de placement."""

    identifiant: str
    nom: str
    piece: Nomenclaturable
    contrainte: ContraintePlacement
    couleur: str

    def article_bom(self) -> ArticleBOM:
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class PiecePlacee:
    """Résultat CAO conservant un lien vers sa contrainte source."""

    nom: str
    piece: Nomenclaturable
    forme: Shape
    couleur: str
    identifiant: str = ""
    contrainte: ContraintePlacement | None = None
    origine: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)

    def article_bom(self) -> ArticleBOM:
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class OperationAssemblage:
    """Étape calculée depuis un groupe de contraintes équivalentes."""

    numero: int
    identifiant: str
    titre: str
    instruction: str
    nouvelles: tuple[PiecePlacee, ...]
    deja_posees: tuple[PiecePlacee, ...]
    controles: tuple[str, ...]


def _famille(article: ArticleBOM) -> str:
    return article.categorie.rsplit("/", 1)[-1].strip()


def _pluriel(texte: str, quantite: int) -> str:
    if quantite == 1:
        return texte
    premier, separateur, suite = texte.partition(" ")
    if not premier.endswith("s"):
        premier += "s"
    return premier + separateur + suite


class AssemblageContraint:
    """Graphe orienté résolvant CAO, BOM et opérations d'assemblage."""

    def __init__(self, instances: Sequence[PieceInstance]) -> None:
        self._instances = tuple(instances)
        identifiants = [instance.identifiant for instance in self._instances]
        if len(identifiants) != len(set(identifiants)):
            raise ValueError("les identifiants des pièces doivent être uniques")
        connus = set(identifiants)
        for instance in self._instances:
            inconnues = set(instance.contrainte.references) - connus
            if inconnues:
                raise ValueError(
                    f"référence inconnue pour {instance.identifiant}: "
                    + ", ".join(sorted(inconnues))
                )
        self._resolues = self._resoudre()

    @property
    def instances(self) -> tuple[PieceInstance, ...]:
        return self._instances

    @property
    def pieces(self) -> tuple[PiecePlacee, ...]:
        return self._resolues

    def _resoudre(self) -> tuple[PiecePlacee, ...]:
        resolues: dict[str, PiecePlacee] = {}
        restantes = list(self._instances)
        while restantes:
            progression = False
            for instance in tuple(restantes):
                if not set(instance.contrainte.references) <= set(resolues):
                    continue
                placement = instance.contrainte.resoudre(instance.piece, resolues)
                resolues[instance.identifiant] = PiecePlacee(
                    nom=instance.nom,
                    piece=instance.piece,
                    forme=placement.forme,
                    couleur=instance.couleur,
                    identifiant=instance.identifiant,
                    contrainte=instance.contrainte,
                    origine=placement.origine,
                    rotation=placement.rotation,
                )
                restantes.remove(instance)
                progression = True
            if not progression:
                bloquees = ", ".join(instance.identifiant for instance in restantes)
                raise ValueError(f"cycle de contraintes d'assemblage: {bloquees}")
        return tuple(resolues[i.identifiant] for i in self._instances)

    def piece(self, identifiant: str) -> PiecePlacee:
        for piece in self.pieces:
            if piece.identifiant == identifiant:
                return piece
        raise KeyError(identifiant)

    def articles(self) -> Counter[ArticleBOM]:
        return Counter(piece.article_bom() for piece in self.pieces)

    def operations(self) -> tuple[OperationAssemblage, ...]:
        """Regroupe automatiquement les contraintes ayant les mêmes appuis."""
        bases = tuple(
            piece
            for piece in self.pieces
            if isinstance(piece.contrainte, (Ancrage, DecalageParallele))
        )
        groupes: list[tuple[PiecePlacee, ...]] = []
        if bases:
            groupes.append(bases)

        groupes_par_cle: dict[tuple[object, ...], list[PiecePlacee]] = {}
        for piece in self.pieces:
            contrainte = piece.contrainte
            if not isinstance(contrainte, EntreFaces):
                continue
            groupes_par_cle.setdefault(contrainte.cle_operation, []).append(piece)
        groupes.extend(
            tuple(
                sorted(
                    groupe,
                    key=lambda piece: (
                        piece.contrainte.position_transversale
                        if isinstance(piece.contrainte, EntreFaces)
                        else 0
                    ),
                )
            )
            for groupe in groupes_par_cle.values()
        )

        # L'ordre de déclaration des pièces n'est pas une timeline. Les groupes
        # sont triés par dépendances, puis spatialement lorsque plusieurs
        # opérations indépendantes sont possibles au même niveau.
        groupe_par_piece = {
            piece.identifiant: index
            for index, groupe in enumerate(groupes)
            for piece in groupe
        }
        dependances: dict[int, set[int]] = {}
        for index, groupe in enumerate(groupes):
            dependances[index] = {
                groupe_par_piece[reference]
                for piece in groupe
                if piece.contrainte is not None
                for reference in piece.contrainte.references
                if groupe_par_piece[reference] != index
            }

        groupes_tries: list[tuple[PiecePlacee, ...]] = []
        termines: set[int] = set()
        while len(groupes_tries) < len(groupes):
            disponibles = [
                index
                for index in range(len(groupes))
                if index not in termines and dependances[index] <= termines
            ]
            if not disponibles:
                raise ValueError("cycle entre opérations d'assemblage")
            disponibles.sort(
                key=lambda index: (
                    min(piece.forme.bounding_box().min.X for piece in groupes[index]),
                    min(piece.forme.bounding_box().min.Y for piece in groupes[index]),
                )
            )
            for index in disponibles:
                groupes_tries.append(groupes[index])
                termines.add(index)

        deja_posees: tuple[PiecePlacee, ...] = ()
        operations: list[OperationAssemblage] = []
        for numero, groupe in enumerate(groupes_tries, start=1):
            operation = self._decrire_operation(numero, groupe, deja_posees)
            operations.append(operation)
            deja_posees = (*deja_posees, *groupe)
        return tuple(operations)

    def _decrire_operation(
        self,
        numero: int,
        pieces: tuple[PiecePlacee, ...],
        deja_posees: tuple[PiecePlacee, ...],
    ) -> OperationAssemblage:
        article = pieces[0].article_bom()
        famille = _pluriel(_famille(article), len(pieces))
        premiere_contrainte = pieces[0].contrainte

        if isinstance(premiere_contrainte, (Ancrage, DecalageParallele)):
            titre = f"Implanter les {famille} de référence"
            instruction = (
                f"Mettre en place les {len(pieces)} {famille} qui définissent "
                "le repère de l'assemblage."
            )
            boite_min_x = min(piece.forme.bounding_box().min.X for piece in pieces)
            boite_max_x = max(piece.forme.bounding_box().max.X for piece in pieces)
            boite_min_y = min(piece.forme.bounding_box().min.Y for piece in pieces)
            boite_max_y = max(piece.forme.bounding_box().max.Y for piece in pieces)
            controles = (
                f"{len(pieces)} × {article.designation}",
                f"Hors-tout : {formater_mm(boite_max_x - boite_min_x)} × "
                f"{formater_mm(boite_max_y - boite_min_y)} mm",
            )
            identifiant = "implantation"
        elif isinstance(premiere_contrainte, EntreFaces):
            debut = self.piece(premiere_contrainte.reference_debut)
            fin = self.piece(premiere_contrainte.reference_fin)
            titre = f"Positionner les {famille}"
            instruction = (
                f"Placer les {len(pieces)} {famille} entre « {debut.nom} » "
                f"et « {fin.nom} »."
            )
            positions = tuple(
                piece.contrainte.position_transversale
                for piece in pieces
                if isinstance(piece.contrainte, EntreFaces)
            )
            controles = (
                f"{len(pieces)} × {article.designation}",
                f"Axes {('Y' if premiere_contrainte.axe_portee == 'X' else 'X')} : "
                + " · ".join(formater_mm(position) for position in positions)
                + " mm",
                f"Jeu à chaque about : "
                f"{formater_mm(premiere_contrainte.jeu_about)} mm",
            )
            identifiant = (
                f"entre_{premiere_contrainte.reference_debut}_"
                f"{premiere_contrainte.reference_fin}"
            )
        else:
            raise TypeError("type de contrainte non pris en charge")

        return OperationAssemblage(
            numero=numero,
            identifiant=identifiant,
            titre=titre,
            instruction=instruction,
            nouvelles=pieces,
            deja_posees=deja_posees,
            controles=controles,
        )
