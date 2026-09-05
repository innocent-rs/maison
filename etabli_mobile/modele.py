"""Base paramétrique de l'établi mobile et premiers rangements."""

from dataclasses import dataclass
from math import dist, sqrt
from typing import ClassVar

from build123d import Align, Box, Part, Plane, Pos, Shape

from home_framework.nomenclature import ArticleBOM, Nomenclature


Point3D = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ProfileAluminium45x90:
    """Profilé 45 × 90 orienté avec sa grande dimension verticale."""

    longueur: float
    largeur: float = 45.0
    hauteur: float = 90.0
    masse_lineique_kg_m: float = 3.0
    materiau: str = "Aluminium extrudé, série à définir"

    def __post_init__(self) -> None:
        if self.longueur <= 0:
            raise ValueError("la longueur du profilé doit être positive")
        if min(self.largeur, self.hauteur) <= 0:
            raise ValueError("la section du profilé doit être positive")
        if self.masse_lineique_kg_m <= 0:
            raise ValueError("la masse linéique doit être positive")

    @property
    def masse_kg(self) -> float:
        return self.longueur / 1_000 * self.masse_lineique_kg_m

    def construire(self) -> Part:
        """Construit le profilé suivant X, depuis son extrémité de départ."""
        return Box(
            self.longueur,
            self.largeur,
            self.hauteur,
            align=(Align.MIN, Align.CENTER, Align.CENTER),
        )

    def construire_entre(
        self,
        debut: Point3D,
        fin: Point3D,
        normale: Point3D,
    ) -> Shape:
        """Oriente la coupe entre deux nœuds dans un plan donné."""
        longueur_reelle = dist(debut, fin)
        if abs(longueur_reelle - self.longueur) > 1e-6:
            raise ValueError("la longueur du profilé ne correspond pas aux nœuds")
        direction = tuple(b - a for a, b in zip(debut, fin))
        plan = Plane(origin=debut, x_dir=direction, z_dir=normale)
        return plan.location * self.construire()

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"PROFIL-ALU-{self.largeur:g}x{self.hauteur:g}-L{self.longueur:.1f}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Profilé aluminium {self.largeur:g} × {self.hauteur:g} mm"
                f" — L {self.longueur:.1f} mm"
            ),
            categorie="Structure / profilé aluminium",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            # La section réelle dépend de la série commerciale à sélectionner.
            volume_mm3=None,
        )


@dataclass(frozen=True, slots=True)
class RenfortDiagonal45x90:
    """Renfort 45 × 90 à 45° avec deux coupes biaises opposées."""

    longueur_axe: float
    largeur: float = 45.0
    hauteur: float = 90.0
    masse_lineique_kg_m: float = 3.0
    materiau: str = "Aluminium extrudé, série à définir"
    angle_coupes_degres: float = 45.0

    def __post_init__(self) -> None:
        if self.longueur_axe <= self.largeur:
            raise ValueError("le renfort est trop court pour deux coupes à 45°")
        if min(self.largeur, self.hauteur, self.masse_lineique_kg_m) <= 0:
            raise ValueError("la section et la masse linéique doivent être positives")

    @property
    def longueur(self) -> float:
        """Longueur de débit mesurée entre les deux pointes longues."""
        return self.longueur_axe + self.largeur

    @property
    def longueur_pointe_courte(self) -> float:
        return self.longueur_axe - self.largeur

    @property
    def masse_kg(self) -> float:
        # Les deux triangles retirés par les coupes biaises se compensent :
        # la masse correspond à la longueur sur l'axe, et non à la pointe longue.
        return self.longueur_axe / 1_000 * self.masse_lineique_kg_m

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"RENFORT-ALU-{self.largeur:g}x{self.hauteur:g}-"
            f"45DEG-L{self.longueur:.1f}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Renfort aluminium {self.largeur:g} × {self.hauteur:g} mm, "
                f"2 coupes à 45° — pointe longue {self.longueur:.1f} mm"
            ),
            categorie="Structure / renfort diagonal",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.largeur,
            hauteur_mm=self.hauteur,
            volume_mm3=None,
        )


@dataclass(frozen=True, slots=True)
class PlateauContreplaque:
    """Plateau rectangulaire posé sur la face supérieure des profilés."""

    longueur: float
    profondeur: float
    epaisseur: float = 12.0
    densite_kg_m3: float = 650.0
    materiau: str = "Contreplaqué, essence et qualité à définir"

    def __post_init__(self) -> None:
        if min(self.longueur, self.profondeur, self.epaisseur) <= 0:
            raise ValueError("les dimensions du plateau doivent être positives")
        if self.densite_kg_m3 <= 0:
            raise ValueError("la densité du contreplaqué doit être positive")

    @property
    def volume_mm3(self) -> float:
        return self.longueur * self.profondeur * self.epaisseur

    @property
    def masse_kg(self) -> float:
        return self.volume_mm3 / 1_000_000_000 * self.densite_kg_m3

    def construire(self) -> Part:
        return Box(
            self.longueur,
            self.profondeur,
            self.epaisseur,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"CP-{self.longueur:g}x{self.profondeur:g}x{self.epaisseur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Plateau contreplaqué {self.longueur:g} × "
                f"{self.profondeur:g} × {self.epaisseur:g} mm"
            ),
            categorie="Plateau / contreplaqué",
            materiau=self.materiau,
            longueur_mm=self.longueur,
            largeur_mm=self.profondeur,
            hauteur_mm=self.epaisseur,
            volume_mm3=self.volume_mm3,
        )


@dataclass(frozen=True, slots=True)
class ModuleQbrickOne:
    """Enveloppe simplifiée d'un module Qbrick System ONE.

    Le gabarit par défaut de 585 × 385 × 301 mm correspond au ONE 350 2.0
    VARIO. Les détails du couvercle, des poignées et des connecteurs ne sont
    pas modélisés.
    """

    longueur: float = 585.0
    profondeur: float = 385.0
    hauteur: float = 301.0
    fabricant: str = "Qbrick System"
    gamme: str = "ONE"

    def __post_init__(self) -> None:
        if min(self.longueur, self.profondeur, self.hauteur) <= 0:
            raise ValueError(
                "les dimensions du module Qbrick System ONE doivent être positives"
            )

    def construire(self) -> Part:
        # Enveloppe volontairement simple : le verrouillage inférieur et les
        # poignées dépendront de la référence finalement retenue.
        return Box(
            self.longueur,
            self.profondeur,
            self.hauteur,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    def article_bom(self) -> ArticleBOM:
        reference = (
            f"QBRICK-SYSTEM-ONE-A-DEFINIR-"
            f"{self.longueur:g}x{self.profondeur:g}x{self.hauteur:g}"
        ).replace(".", "_")
        return ArticleBOM(
            reference=reference,
            designation=(
                f"Module Qbrick System ONE, référence à définir — "
                f"enveloppe {self.longueur:g} × {self.profondeur:g} × "
                f"{self.hauteur:g} mm"
            ),
            categorie="Rangement / caisse modulaire",
            materiau="Polymère renforcé et quincaillerie",
            longueur_mm=self.longueur,
            largeur_mm=self.profondeur,
            hauteur_mm=self.hauteur,
            volume_mm3=None,
        )


@dataclass(frozen=True, slots=True)
class ElementEtabli:
    """Pièce placée de la base, commune à la vue CAO et à la BOM."""

    nom: str
    piece: (
        ProfileAluminium45x90
        | RenfortDiagonal45x90
        | PlateauContreplaque
        | ModuleQbrickOne
    )
    forme: Shape
    couleur: str = "lightgray"

    def article_bom(self) -> ArticleBOM:
        return self.piece.article_bom()


@dataclass(frozen=True, slots=True)
class ChassisEtabliMobile:
    """Cadre bas renforcé recevant les caisses et huit roues."""

    LONGUEUR_MAXIMALE_MM: ClassVar[float] = 1_700.0

    longueur: float = 1_700.0
    profondeur: float = 385.0
    largeur_profile: float = 45.0
    hauteur_profile: float = 90.0
    longueur_module_qbrick: float = 585.0
    recul_renfort_angle: float = 115.0
    masse_lineique_kg_m: float = 3.0

    def __post_init__(self) -> None:
        if min(self.longueur, self.profondeur) <= 0:
            raise ValueError("les dimensions du châssis doivent être positives")
        if self.longueur > self.LONGUEUR_MAXIMALE_MM:
            raise ValueError("la longueur du châssis ne doit pas dépasser 1 700 mm")
        if min(self.largeur_profile, self.hauteur_profile) <= 0:
            raise ValueError("la section du profilé doit être positive")
        if self.longueur_module_qbrick <= 0:
            raise ValueError("la longueur du module Qbrick doit être positive")
        if self.recul_renfort_angle <= 0:
            raise ValueError("le recul des renforts d'angle doit être positif")
        if self.masse_lineique_kg_m <= 0:
            raise ValueError("la masse linéique doit être positive")
        if self.longueur <= 2 * self.largeur_profile:
            raise ValueError("la longueur doit dépasser deux sections de profilé")
        if self.profondeur <= 2 * self.largeur_profile:
            raise ValueError("la profondeur doit dépasser deux sections de profilé")
        if 2 * self.longueur_module_qbrick > self.longueur:
            raise ValueError("les deux modules Qbrick se chevaucheraient")
        portee_maximale = min(
            self.longueur - 2 * self.largeur_profile,
            self.profondeur - 2 * self.largeur_profile,
        ) / 2
        if self.recul_renfort_angle > portee_maximale:
            raise ValueError("les renforts d'angle se chevaucheraient")
        largeur_baie_minimale = min(
            self.profondeur - 2 * self.largeur_profile,
            self.longueur_module_qbrick - 2 * self.largeur_profile,
            self.longueur - 2 * self.longueur_module_qbrick,
        )
        encombrement_renforts = (
            2 * self.recul_renfort_angle + self.largeur_profile * sqrt(2)
        )
        if encombrement_renforts > largeur_baie_minimale:
            raise ValueError("les renforts d'une baie se croiseraient")

    @property
    def longueur_traverses(self) -> float:
        return self.profondeur - 2 * self.largeur_profile

    def _element_entre(
        self,
        nom: str,
        debut: Point3D,
        fin: Point3D,
        normale: Point3D,
        *,
        couleur: str = "lightgray",
    ) -> ElementEtabli:
        piece = ProfileAluminium45x90(
            dist(debut, fin),
            self.largeur_profile,
            self.hauteur_profile,
            self.masse_lineique_kg_m,
        )
        return ElementEtabli(
            nom=nom,
            piece=piece,
            forme=piece.construire_entre(debut, fin, normale),
            couleur=couleur,
        )

    def _renfort_45_entre(
        self,
        nom: str,
        debut: Point3D,
        fin: Point3D,
        limites_baie: tuple[float, float, float, float],
    ) -> ElementEtabli:
        """Crée un profilé surlong puis le coupe aux deux faces de la baie."""
        longueur_axe = dist(debut, fin)
        piece = RenfortDiagonal45x90(
            longueur_axe,
            self.largeur_profile,
            self.hauteur_profile,
            self.masse_lineique_kg_m,
        )
        direction = tuple((b - a) / longueur_axe for a, b in zip(debut, fin))
        depart_surlong = tuple(
            coordonnee - self.largeur_profile * composante
            for coordonnee, composante in zip(debut, direction)
        )
        plan = Plane(origin=depart_surlong, x_dir=direction, z_dir=(0, 0, 1))
        brut = plan.location * Box(
            longueur_axe + 2 * self.largeur_profile,
            self.largeur_profile,
            self.hauteur_profile,
            align=(Align.MIN, Align.CENTER, Align.CENTER),
        )
        xmin, xmax, ymin, ymax = limites_baie
        volume_baie = Pos(xmin, ymin, 0) * Box(
            xmax - xmin,
            ymax - ymin,
            self.hauteur_profile,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        return ElementEtabli(
            nom=nom,
            piece=piece,
            forme=brut & volume_baie,
            couleur="slategray",
        )

    def elements_perimetre(self) -> tuple[ElementEtabli, ...]:
        """Retourne les quatre profilés du rectangle inférieur."""
        s = self.largeur_profile
        h = self.hauteur_profile
        demi_x = (self.longueur - s) / 2
        demi_y = (self.profondeur - s) / 2
        elements: list[ElementEtabli] = []
        z = h / 2

        for cote, y in (("avant", -demi_y), ("arriere", demi_y)):
            elements.append(
                self._element_entre(
                    f"Longeron {cote}",
                    (-self.longueur / 2, y, z),
                    (self.longueur / 2, y, z),
                    (0, 0, 1),
                )
            )

        for cote, x in (("gauche", -demi_x), ("droite", demi_x)):
            elements.append(
                self._element_entre(
                    f"Traverse {cote}",
                    (x, -self.longueur_traverses / 2, z),
                    (x, self.longueur_traverses / 2, z),
                    (0, 0, 1),
                )
            )

        return tuple(elements)

    def positions_modules_qbrick(self) -> tuple[float, float]:
        """Place les Qbrick au ras des deux extrémités du châssis."""
        retrait = self.longueur_module_qbrick / 2
        return (-self.longueur / 2 + retrait, self.longueur / 2 - retrait)

    def positions_traverses_qbrick(self) -> tuple[float, float]:
        """Place toute la largeur de chaque traverse sous le support en CP."""
        position_arete_cp = self.longueur / 2 - self.longueur_module_qbrick
        position_axe = position_arete_cp + self.largeur_profile / 2
        return (-position_axe, position_axe)

    def elements_traverses_qbrick(self) -> tuple[ElementEtabli, ...]:
        """Ajoute une traverse sous l'arête intérieure de chaque support CP."""
        z = self.hauteur_profile / 2
        return tuple(
            self._element_entre(
                f"Traverse sous Qbrick {index}",
                (x, -self.longueur_traverses / 2, z),
                (x, self.longueur_traverses / 2, z),
                (0, 0, 1),
            )
            for index, x in enumerate(self.positions_traverses_qbrick(), start=1)
        )

    def elements_renforts(self) -> tuple[ElementEtabli, ...]:
        """Renforce les angles extérieurs et les deux traverses Qbrick."""
        s = self.largeur_profile
        h = self.hauteur_profile
        demi_x_interieur = self.longueur / 2 - s
        demi_y_interieur = self.profondeur / 2 - s
        z = h / 2
        recul = self.recul_renfort_angle
        elements: list[ElementEtabli] = []

        for nom_x, signe_x in (("gauche", -1), ("droit", 1)):
            x_exterieur = signe_x * demi_x_interieur
            for nom_y, signe_y in (("avant", -1), ("arrière", 1)):
                y_longeron = signe_y * demi_y_interieur
                y_interieur = signe_y * (demi_y_interieur - recul)
                elements.append(
                    self._renfort_45_entre(
                        f"Renfort angle {nom_y} {nom_x}",
                        (
                            x_exterieur - signe_x * recul,
                            y_longeron,
                            z,
                        ),
                        (x_exterieur, y_interieur, z),
                        (
                            -demi_x_interieur,
                            demi_x_interieur,
                            -demi_y_interieur,
                            demi_y_interieur,
                        ),
                    )
                )

        for index, centre_x in enumerate(
            self.positions_traverses_qbrick(),
            start=1,
        ):
            for nom_x, signe_x in (("gauche", -1), ("droit", 1)):
                x_face = centre_x + signe_x * s / 2
                limites_x = (
                    (-demi_x_interieur, x_face)
                    if signe_x < 0
                    else (x_face, demi_x_interieur)
                )
                for nom_y, signe_y in (("avant", -1), ("arrière", 1)):
                    y_longeron = signe_y * demi_y_interieur
                    y_interieur = signe_y * (demi_y_interieur - recul)
                    elements.append(
                        self._renfort_45_entre(
                            f"Renfort traverse Qbrick {index} {nom_y} {nom_x}",
                            (x_face + signe_x * recul, y_longeron, z),
                            (x_face, y_interieur, z),
                            (
                                limites_x[0],
                                limites_x[1],
                                -demi_y_interieur,
                                demi_y_interieur,
                            ),
                        )
                    )
        return tuple(elements)

    def positions_roues(self) -> tuple[tuple[float, float], ...]:
        """Axes prévus : une paire sous chacune des quatre traverses."""
        demi_x = (self.longueur - self.largeur_profile) / 2
        demi_y = (self.profondeur - self.largeur_profile) / 2
        axes_x = (-demi_x, *self.positions_traverses_qbrick(), demi_x)
        return tuple(
            (x, y)
            for x in axes_x
            for y in (-demi_y, demi_y)
        )

    @property
    def longueur_totale_debit_mm(self) -> float:
        return sum(element.piece.longueur for element in self.elements())

    @property
    def masse_profiles_kg(self) -> float:
        """Masse des profilés seuls, calculée avec l'hypothèse linéique."""
        return sum(element.piece.masse_kg for element in self.elements())

    def elements(self) -> tuple[ElementEtabli, ...]:
        return (
            self.elements_perimetre()
            + self.elements_traverses_qbrick()
            + self.elements_renforts()
        )

    def nomenclature(self) -> Nomenclature:
        return Nomenclature(self.elements())


@dataclass(frozen=True, slots=True)
class EtabliMobile:
    """Châssis bas et supports dédiés à deux modules Qbrick System ONE."""

    chassis: ChassisEtabliMobile
    plateaux_qbrick: tuple[PlateauContreplaque, PlateauContreplaque]
    modules_qbrick_one: tuple[ModuleQbrickOne, ModuleQbrickOne]

    def __post_init__(self) -> None:
        if len(self.modules_qbrick_one) != 2:
            raise ValueError(
                "l'établi doit recevoir exactement deux modules Qbrick System ONE"
            )
        if len(self.plateaux_qbrick) != len(self.modules_qbrick_one):
            raise ValueError("chaque module Qbrick doit avoir son plateau dédié")
        epaisseurs = {plateau.epaisseur for plateau in self.plateaux_qbrick}
        if len(epaisseurs) != 1:
            raise ValueError("les plateaux Qbrick doivent avoir la même épaisseur")
        for plateau, module in zip(self.plateaux_qbrick, self.modules_qbrick_one):
            if (
                plateau.longueur != module.longueur
                or plateau.profondeur != module.profondeur
            ):
                raise ValueError(
                    "chaque plateau doit suivre exactement l'empreinte de son "
                    "module Qbrick"
                )
            if module.longueur > self.chassis.longueur / 2:
                raise ValueError(
                    "les deux modules Qbrick System ONE se chevaucheraient"
                )
            if module.longueur != self.chassis.longueur_module_qbrick:
                raise ValueError(
                    "les traverses doivent reprendre les extrémités des modules Qbrick"
                )
            if module.profondeur != self.chassis.profondeur:
                raise ValueError(
                    "la profondeur du châssis doit suivre exactement l'empreinte Qbrick"
                )

    def elements_plateaux_qbrick(self) -> tuple[ElementEtabli, ...]:
        """Place une découpe de contreplaqué sous chaque module Qbrick."""
        centres_x = self.chassis.positions_modules_qbrick()
        return tuple(
            ElementEtabli(
                nom=f"Support contreplaqué Qbrick {index}",
                piece=plateau,
                forme=(
                    Pos(x, 0, self.chassis.hauteur_profile)
                    * plateau.construire()
                ),
                couleur="burlywood",
            )
            for index, (x, plateau) in enumerate(
                zip(centres_x, self.plateaux_qbrick), start=1
            )
        )

    def elements_qbrick_one(self) -> tuple[ElementEtabli, ...]:
        """Place les modules contre les deux extrémités du châssis."""
        z = self.chassis.hauteur_profile + self.plateaux_qbrick[0].epaisseur
        centres_x = self.chassis.positions_modules_qbrick()
        return tuple(
            ElementEtabli(
                nom=f"Qbrick System ONE {index}",
                piece=module,
                forme=Pos(x, 0, z) * module.construire(),
                couleur="darkslategray",
            )
            for index, (x, module) in enumerate(
                zip(centres_x, self.modules_qbrick_one), start=1
            )
        )

    def elements(self) -> tuple[ElementEtabli, ...]:
        return (
            self.chassis.elements()
            + self.elements_plateaux_qbrick()
            + self.elements_qbrick_one()
        )

    def nomenclature_chassis(self) -> Nomenclature:
        return self.chassis.nomenclature()

    def nomenclature_achats(self) -> Nomenclature:
        return Nomenclature(self.elements())

    @property
    def masse_structure_connue_kg(self) -> float:
        """Masse des profilés et du CP, hors caisses, fixations et roues."""
        return self.chassis.masse_profiles_kg + sum(
            plateau.masse_kg for plateau in self.plateaux_qbrick
        )


def creer_etabli_mobile(
    *,
    longueur: float = 1_700.0,
    profondeur: float = 385.0,
    epaisseur_supports_cp: float = 12.0,
    hauteur_qbrick_one: float = 301.0,
) -> EtabliMobile:
    """Crée la base et deux modules Qbrick avec leurs supports en CP."""
    modules_qbrick_one = (
        ModuleQbrickOne(hauteur=hauteur_qbrick_one),
        ModuleQbrickOne(hauteur=hauteur_qbrick_one),
    )
    chassis = ChassisEtabliMobile(
        longueur=longueur,
        profondeur=profondeur,
        longueur_module_qbrick=modules_qbrick_one[0].longueur,
    )
    return EtabliMobile(
        chassis=chassis,
        plateaux_qbrick=(
            PlateauContreplaque(
                longueur=modules_qbrick_one[0].longueur,
                profondeur=modules_qbrick_one[0].profondeur,
                epaisseur=epaisseur_supports_cp,
            ),
            PlateauContreplaque(
                longueur=modules_qbrick_one[1].longueur,
                profondeur=modules_qbrick_one[1].profondeur,
                epaisseur=epaisseur_supports_cp,
            ),
        ),
        modules_qbrick_one=modules_qbrick_one,
    )
