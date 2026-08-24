"""Assemblages CAO contraints, source commune de géométrie et de fabrication.

Une instance associe une pièce de nomenclature à une contrainte orientée. Le
graphe résout les formes finales et déduit une suite d'opérations à partir des
dépendances, sans maintenir une timeline séparée.
"""

from __future__ import annotations

from collections import Counter
from copy import copy
from dataclasses import dataclass
from functools import lru_cache
from gc import collect
from itertools import product
from typing import Protocol, Sequence

from build123d import Compound, Location, RigidJoint, Shape

from home_framework.nomenclature import ArticleBOM, Nomenclaturable


def formater_mm(valeur: float) -> str:
    """Formate une cote avec la typographie française."""
    if abs(valeur - round(valeur)) < 1e-6:
        return f"{round(valeur):,}".replace(",", " ")
    return f"{valeur:,.1f}".replace(",", " ").replace(".", ",")


@dataclass(frozen=True, slots=True)
class PlacementResolu:
    forme: Shape
    location: Location


class ContraintePlacement(Protocol):
    """Relation orientée capable de placer sa pièce mobile."""

    @property
    def references(self) -> tuple[str, ...]: ...

    @property
    def cle_operation(self) -> tuple[object, ...]: ...

    def resoudre(
        self,
        identifiant: str,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu: ...


@dataclass(frozen=True, slots=True)
class InstructionAssemblage:
    """Texte de fabrication porté par la déclaration CAO, jamais par le PDF."""

    identifiant: str
    titre: str
    instruction: str
    controles: tuple[str, ...] = ()


class ComposantRigide(Compound):
    """Enveloppe build123d générique portant un joint d'origine intrinsèque."""

    def __init__(self, piece: Nomenclaturable, label: str = "") -> None:
        construire = getattr(piece, "construire", None)
        if construire is None:
            raise TypeError("un composant rigide doit fournir construire()")
        try:
            forme = copy(_prototype_geometrique(piece))
        except TypeError:
            # Les extensions peuvent fournir des pièces non hachables.
            forme = construire()
        super().__init__(children=[forme], label=label)
        RigidJoint("origine", self, Location())


class ComposantLineaire(ComposantRigide):
    """Composant build123d autonome avec ses joints intrinsèques.

    Comme dans le tutoriel officiel build123d, les joints appartiennent au
    composant et se déplacent avec lui. Le moteur d'assemblage ne connaît donc
    plus la géométrie locale de ses abouts : il connecte simplement ``debut``
    et ``fin``.
    """

    def __init__(self, piece: Nomenclaturable, label: str = "") -> None:
        longueur = getattr(piece, "longueur", None)
        if longueur is None:
            raise TypeError("un composant linéaire doit fournir longueur")
        super().__init__(piece, label=label)
        RigidJoint("debut", self, Location())
        RigidJoint("fin", self, Location((longueur, 0, 0)))


@lru_cache(maxsize=256)
def _prototype_geometrique(piece: Nomenclaturable) -> Shape:
    """Construit une seule topologie locale par définition de pièce immuable."""
    construire = getattr(piece, "construire", None)
    if construire is None:
        raise TypeError("un composant rigide doit fournir construire()")
    return construire()


def _construire_composant(
    identifiant: str,
    piece: Nomenclaturable,
    joints_requis: frozenset[str] = frozenset(),
) -> Compound:
    """Utilise la fabrique spécialisée ou l'enveloppe rigide appropriée."""
    construire_composant = getattr(piece, "construire_composant", None)
    composant = (
        construire_composant()
        if construire_composant is not None
        else (
            ComposantLineaire(piece, label=identifiant)
            if joints_requis & {"debut", "fin"}
            else ComposantRigide(piece, label=identifiant)
        )
    )
    joints_manquants = joints_requis - set(composant.joints)
    if joints_manquants:
        raise ValueError(
            f"le composant {identifiant} ne fournit pas les joints "
            + ", ".join(sorted(joints_manquants))
        )
    return composant


def _construire_piece(
    identifiant: str,
    piece: Nomenclaturable,
    location: Location,
    *,
    joint_ancrage: str | None = None,
) -> PlacementResolu:
    forme = _construire_composant(identifiant, piece)
    forme.locate(location)
    if joint_ancrage is not None:
        RigidJoint(joint_ancrage, forme, location)
    return PlacementResolu(forme, location)


def _connecter_rigidement(
    identifiant: str,
    piece: Nomenclaturable,
    reference: "PiecePlacee",
    cible: Location,
    joint_mobile: str = "debut",
) -> PlacementResolu:
    """Place la pièce mobile par connexion de ``RigidJoint`` build123d."""
    forme = _construire_composant(
        identifiant,
        piece,
        frozenset((joint_mobile,)),
    )
    joint_piece = forme.joints[joint_mobile]
    joint_reference = RigidJoint(
        f"connexion_{identifiant}",
        reference.forme,
        cible,
    )
    joint_reference.connect_to(joint_piece)
    if forme.location is None:
        raise RuntimeError("le joint natif n'a pas résolu la position")
    return PlacementResolu(forme, forme.location)


@dataclass(frozen=True, slots=True)
class Ancrage:
    """Place la première pièce dans le repère global de l'assemblage."""

    location: Location

    @property
    def references(self) -> tuple[str, ...]:
        return ()

    @property
    def cle_operation(self) -> tuple[object, ...]:
        return (type(self),)

    def resoudre(
        self,
        identifiant: str,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu:
        del references
        return _construire_piece(
            identifiant,
            piece,
            self.location,
            joint_ancrage=f"ancrage_{identifiant}",
        )


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
        identifiant: str,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu:
        appui = references[self.reference]
        if appui.location is None:
            raise ValueError("la pièce de référence n'a pas de Location résolue")
        cible = appui.location * Location(self.translation)
        return _connecter_rigidement(identifiant, piece, appui, cible)


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
    prerequis: tuple[str, ...] = ()
    operation: InstructionAssemblage | None = None

    def __post_init__(self) -> None:
        if self.axe_portee not in ("X", "Y"):
            raise ValueError("l'axe de portée doit être X ou Y")
        if self.jeu_about < 0:
            raise ValueError("le jeu d'about ne peut pas être négatif")

    @property
    def references(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (self.reference_debut, self.reference_fin, *self.prerequis)
            )
        )

    @property
    def cle_operation(self) -> tuple[object, ...]:
        if self.operation is not None:
            return (InstructionAssemblage, self.operation.identifiant)
        return (
            type(self),
            self.reference_debut,
            self.reference_fin,
            self.axe_portee,
        )

    def resoudre(
        self,
        identifiant: str,
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
            position_fin = (fin_axe, self.position_transversale, self.niveau)
        else:
            origine_axe = debut.max.Y + self.jeu_about
            fin_axe = fin.min.Y - self.jeu_about
            origine = (self.position_transversale, origine_axe, self.niveau)
            rotation = (0, 0, 90)
            position_fin = (self.position_transversale, fin_axe, self.niveau)

        longueur_disponible = fin_axe - origine_axe
        if abs(longueur_piece - longueur_disponible) > 1e-6:
            raise ValueError(
                f"la longueur {longueur_piece:g} mm ne correspond pas à "
                f"l'espace contraint {longueur_disponible:g} mm"
            )
        placement = _connecter_rigidement(
            identifiant,
            piece,
            references[self.reference_debut],
            Location(origine, rotation),
        )

        # Le deuxième joint exprime le second appui. Comme la longueur a été
        # validée ci-dessus, cette seconde connexion ne doit plus déplacer la
        # pièce : elle matérialise et vérifie la relation multi-appuis.
        joint_mobile_fin = placement.forme.joints["fin"]
        joint_reference_fin = RigidJoint(
            f"connexion_{identifiant}",
            references[self.reference_fin].forme,
            Location(position_fin, rotation),
        )
        boite_avant = placement.forme.bounding_box()
        joint_reference_fin.connect_to(joint_mobile_fin)
        boite_apres = placement.forme.bounding_box()
        ecart = max(
            abs(a - b)
            for a, b in zip(
                (
                    boite_avant.min.X,
                    boite_avant.min.Y,
                    boite_avant.min.Z,
                    boite_avant.max.X,
                    boite_avant.max.Y,
                    boite_avant.max.Z,
                ),
                (
                    boite_apres.min.X,
                    boite_apres.min.Y,
                    boite_apres.min.Z,
                    boite_apres.max.X,
                    boite_apres.max.Y,
                    boite_apres.max.Z,
                ),
            )
        )
        if ecart > 1e-6:
            raise ValueError("les deux joints d'appui donnent des placements incompatibles")
        if placement.forme.location is None:
            raise RuntimeError("le second joint a supprimé la Location")
        return PlacementResolu(placement.forme, placement.forme.location)


@dataclass(frozen=True, slots=True)
class PositionSurReference:
    """Connecte l'origine d'un composant à un emplacement d'une référence."""

    reference: str
    location: Location
    prerequis: tuple[str, ...] = ()
    operation: InstructionAssemblage | None = None

    @property
    def references(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.reference, *self.prerequis)))

    @property
    def cle_operation(self) -> tuple[object, ...]:
        if self.operation is not None:
            return (InstructionAssemblage, self.operation.identifiant)
        return (type(self), self.reference)

    def resoudre(
        self,
        identifiant: str,
        piece: Nomenclaturable,
        references: dict[str, "PiecePlacee"],
    ) -> PlacementResolu:
        return _connecter_rigidement(
            identifiant,
            piece,
            references[self.reference],
            self.location,
            joint_mobile="origine",
        )


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

    @classmethod
    def ancrer(
        cls,
        identifiant: str,
        nom: str,
        piece: Nomenclaturable,
        location: Location,
        couleur: str,
    ) -> "PieceInstance":
        """Déclare une pièce fixe servant de racine à l'assemblage."""
        return cls(identifiant, nom, piece, Ancrage(location), couleur)

    @classmethod
    def parallele_a(
        cls,
        identifiant: str,
        nom: str,
        piece: Nomenclaturable,
        reference: str,
        translation: tuple[float, float, float],
        couleur: str,
    ) -> "PieceInstance":
        """Déclare une pièce parallèle décalée depuis une référence."""
        return cls(
            identifiant,
            nom,
            piece,
            DecalageParallele(reference, translation),
            couleur,
        )

    @classmethod
    def placer_sur(
        cls,
        identifiant: str,
        nom: str,
        piece: Nomenclaturable,
        reference: str,
        location: Location,
        couleur: str,
        *,
        prerequis: tuple[str, ...] = (),
        operation: InstructionAssemblage | None = None,
    ) -> "PieceInstance":
        """Déclare un composant quelconque connecté à une pièce existante."""
        return cls(
            identifiant,
            nom,
            piece,
            PositionSurReference(reference, location, prerequis, operation),
            couleur,
        )


@dataclass(frozen=True, slots=True)
class TrameEntreFaces:
    """Déclaration cartésienne d'une trame de composants entre appuis."""

    prefixe_identifiant: str
    nom_piece: str
    piece: Nomenclaturable
    couleur: str
    axes: tuple[float, ...]
    appuis: tuple[tuple[str, str], ...]
    axe_portee: str
    niveau: float = 0
    jeu_about: float = 0
    noms_axes: tuple[str, ...] | None = None
    prerequis: tuple[str, ...] = ()
    operation: InstructionAssemblage | None = None

    def __post_init__(self) -> None:
        if not self.axes or not self.appuis:
            raise ValueError("une trame doit contenir des axes et des appuis")
        if self.noms_axes is not None and len(self.noms_axes) != len(self.axes):
            raise ValueError("les noms d'axes ne correspondent pas à la trame")

    def instances(self) -> tuple[PieceInstance, ...]:
        resultat: list[PieceInstance] = []
        appui_unique = len(self.appuis) == 1
        for (index_axe, axe), (index_portee, appuis) in product(
            enumerate(self.axes, start=1),
            enumerate(self.appuis, start=1),
        ):
            suffixe = (
                f"{index_axe:02d}"
                if appui_unique
                else f"{index_axe:02d}_{index_portee}"
            )
            if self.noms_axes is not None:
                nom = self.noms_axes[index_axe - 1]
            elif appui_unique:
                nom = f"{self.nom_piece} {index_axe:02d}"
            else:
                nom = f"{self.nom_piece} {index_axe:02d}.{index_portee}"
            resultat.append(
                PieceInstance(
                    identifiant=f"{self.prefixe_identifiant}_{suffixe}",
                    nom=nom,
                    piece=self.piece,
                    contrainte=EntreFaces(
                        *appuis,
                        axe_portee=self.axe_portee,
                        position_transversale=axe,
                        niveau=self.niveau,
                        jeu_about=self.jeu_about,
                        prerequis=self.prerequis,
                        operation=self.operation,
                    ),
                    couleur=self.couleur,
                )
            )
        return tuple(resultat)


@dataclass(frozen=True, slots=True)
class PiecePlacee:
    """Résultat CAO conservant un lien vers sa contrainte source."""

    nom: str
    piece: Nomenclaturable
    forme: Shape
    couleur: str
    identifiant: str = ""
    contrainte: ContraintePlacement | None = None
    location: Location | None = None

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
        # Les joints natifs se référencent mutuellement. Libérer les anciens
        # graphes avant d'en résoudre un nouveau évite d'accumuler leur CAO.
        collect()
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

    @classmethod
    def declarer(
        cls,
        *declarations: PieceInstance | TrameEntreFaces,
    ) -> "AssemblageContraint":
        """Déploie des instances unitaires et des trames déclaratives."""
        instances: list[PieceInstance] = []
        for declaration in declarations:
            if isinstance(declaration, PieceInstance):
                instances.append(declaration)
            else:
                instances.extend(declaration.instances())
        return cls(instances)

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
                placement = instance.contrainte.resoudre(
                    instance.identifiant,
                    instance.piece,
                    resolues,
                )
                resolues[instance.identifiant] = PiecePlacee(
                    nom=instance.nom,
                    piece=instance.piece,
                    forme=placement.forme,
                    couleur=instance.couleur,
                    identifiant=instance.identifiant,
                    contrainte=instance.contrainte,
                    location=placement.location,
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
            if not isinstance(contrainte, (EntreFaces, PositionSurReference)):
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
        instruction_declaree = getattr(premiere_contrainte, "operation", None)

        if instruction_declaree is not None:
            articles = Counter(piece.article_bom() for piece in pieces)
            return OperationAssemblage(
                numero=numero,
                identifiant=instruction_declaree.identifiant,
                titre=instruction_declaree.titre,
                instruction=instruction_declaree.instruction,
                nouvelles=pieces,
                deja_posees=deja_posees,
                controles=(
                    *(
                        f"{quantite} × {article_groupe.designation}"
                        for article_groupe, quantite in articles.items()
                    ),
                    *instruction_declaree.controles,
                ),
            )

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
        elif isinstance(premiere_contrainte, PositionSurReference):
            reference = self.piece(premiere_contrainte.reference)
            titre = f"Positionner les {famille}"
            instruction = (
                f"Placer les {len(pieces)} {famille} sur « {reference.nom} »."
            )
            controles = (f"{len(pieces)} × {article.designation}",)
            identifiant = f"sur_{premiere_contrainte.reference}"
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
