"""Petit exporteur CalculiX déterministe pour les ossatures déclaratives.

Le framework produit volontairement un ``.inp`` autonome. FreeCAD peut ainsi
servir de post-processeur sans devenir une dépendance de la génération ou des
tests du modèle.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import isclose
from pathlib import Path
import re
import shutil
import subprocess
from typing import Iterable


@dataclass(frozen=True, slots=True)
class NoeudCalculix:
    identifiant: int
    x_mm: float
    y_mm: float
    z_mm: float


@dataclass(frozen=True, slots=True)
class SectionPoutreCalculix:
    """Section rectangulaire, hauteur locale verticale en premier."""

    nom: str
    hauteur_mm: float
    largeur_mm: float
    module_young_mpa: float
    coefficient_poisson: float = 0.3
    constantes_ingenierie: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if min(
            self.hauteur_mm,
            self.largeur_mm,
            self.module_young_mpa,
        ) <= 0:
            raise ValueError("la section et son module doivent être positifs")
        if not -1 < self.coefficient_poisson < 0.5:
            raise ValueError(
                "le coefficient de Poisson doit être compris entre -1 et 0,5"
            )
        if self.constantes_ingenierie is not None:
            if len(self.constantes_ingenierie) != 9:
                raise ValueError("un matériau orthotrope exige neuf constantes")
            if min(
                *self.constantes_ingenierie[:3],
                *self.constantes_ingenierie[6:],
            ) <= 0:
                raise ValueError("les modules orthotropes doivent être positifs")


@dataclass(frozen=True, slots=True)
class ElementPoutreCalculix:
    identifiant: int
    noeud_debut: int
    noeud_fin: int
    section: str


@dataclass(frozen=True, slots=True)
class EquationCalculix:
    """Égalité d'un déplacement entre deux nœuds, utilisée pour les rotules."""

    noeud_a: int
    noeud_b: int
    ddl: int

    def __post_init__(self) -> None:
        if self.ddl not in (1, 2, 3):
            raise ValueError("seules les translations 1, 2 et 3 sont liées")


@dataclass(frozen=True, slots=True)
class AppuiCalculix:
    noeud: int
    ddl_debut: int
    ddl_fin: int

    def __post_init__(self) -> None:
        if not 1 <= self.ddl_debut <= self.ddl_fin <= 6:
            raise ValueError("les degrés de liberté d'appui doivent être compris entre 1 et 6")


@dataclass(frozen=True, slots=True)
class ChargeNodaleCalculix:
    noeud: int
    fx_n: float = 0.0
    fy_n: float = 0.0
    fz_n: float = 0.0


def _nom_calculix(nom: str) -> str:
    resultat = re.sub(r"[^A-Z0-9_]", "_", nom.upper())
    if not resultat or not resultat[0].isalpha():
        resultat = f"S_{resultat}"
    return resultat[:80]


def _lignes_identifiants(identifiants: Iterable[int]) -> list[str]:
    valeurs = list(identifiants)
    return [
        ", ".join(str(valeur) for valeur in valeurs[index : index + 16])
        for index in range(0, len(valeurs), 16)
    ]


@dataclass(frozen=True, slots=True)
class ModeleCalculix:
    nom: str
    noeuds: tuple[NoeudCalculix, ...]
    sections: tuple[SectionPoutreCalculix, ...]
    elements: tuple[ElementPoutreCalculix, ...]
    equations: tuple[EquationCalculix, ...]
    appuis: tuple[AppuiCalculix, ...]
    charges: tuple[ChargeNodaleCalculix, ...]
    hypotheses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        ids_noeuds = {noeud.identifiant for noeud in self.noeuds}
        ids_elements = {element.identifiant for element in self.elements}
        noms_sections = {section.nom for section in self.sections}
        if len(ids_noeuds) != len(self.noeuds):
            raise ValueError("les identifiants de nœuds doivent être uniques")
        if len(ids_elements) != len(self.elements):
            raise ValueError("les identifiants d'éléments doivent être uniques")
        if len(noms_sections) != len(self.sections):
            raise ValueError("les noms de sections doivent être uniques")
        if any(
            element.noeud_debut not in ids_noeuds
            or element.noeud_fin not in ids_noeuds
            for element in self.elements
        ):
            raise ValueError("un élément référence un nœud absent")
        if any(element.section not in noms_sections for element in self.elements):
            raise ValueError("un élément référence une section absente")
        noeuds_references = {
            *(appui.noeud for appui in self.appuis),
            *(charge.noeud for charge in self.charges),
            *(equation.noeud_a for equation in self.equations),
            *(equation.noeud_b for equation in self.equations),
        }
        if not noeuds_references <= ids_noeuds:
            raise ValueError("une condition référence un nœud absent")
        if not self.appuis:
            raise ValueError("le modèle doit avoir au moins un appui")

    @property
    def charge_verticale_n(self) -> float:
        """Valeur positive de la résultante descendante."""
        return -sum(charge.fz_n for charge in self.charges)

    def entree(self) -> str:
        """Rend le jeu de données CalculiX en unités cohérentes N–mm–MPa."""
        lignes = [
            "*HEADING",
            self.nom,
            "** Unites coherentes : N, mm, MPa",
            *(f"** HYPOTHESE: {hypothese}" for hypothese in self.hypotheses),
            "*NODE, NSET=NALL",
        ]
        lignes.extend(
            f"{n.identifiant}, {n.x_mm:.9g}, {n.y_mm:.9g}, {n.z_mm:.9g}"
            for n in self.noeuds
        )

        for section in self.sections:
            nom = _nom_calculix(section.nom)
            elements = [e for e in self.elements if e.section == section.nom]
            lignes.append(f"*ELEMENT, TYPE=B31, ELSET={nom}")
            lignes.extend(
                f"{e.identifiant}, {e.noeud_debut}, {e.noeud_fin}"
                for e in elements
            )
            lignes.append(f"*MATERIAL, NAME=MAT_{nom}")
            if section.constantes_ingenierie is None:
                lignes.extend(
                    (
                        "*ELASTIC",
                        (
                            f"{section.module_young_mpa:.9g}, "
                            f"{section.coefficient_poisson:.9g}"
                        ),
                    )
                )
            else:
                constantes = section.constantes_ingenierie
                lignes.extend(
                    (
                        "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
                        ", ".join(f"{valeur:.9g}" for valeur in constantes[:8]),
                        f"{constantes[8]:.9g}",
                    )
                )
            lignes.extend(
                (
                    (
                        f"*BEAM SECTION, ELSET={nom}, MATERIAL=MAT_{nom}, "
                        "SECTION=RECT"
                    ),
                    f"{section.hauteur_mm:.9g}, {section.largeur_mm:.9g}",
                    "0., 0., 1.",
                )
            )

        for equation in self.equations:
            lignes.extend(
                (
                    "*EQUATION",
                    "2",
                    (
                        f"{equation.noeud_a}, {equation.ddl}, 1., "
                        f"{equation.noeud_b}, {equation.ddl}, -1."
                    ),
                )
            )

        lignes.append("*NSET, NSET=APPUIS")
        lignes.extend(_lignes_identifiants(appui.noeud for appui in self.appuis))
        lignes.append("*BOUNDARY")
        lignes.extend(
            f"{appui.noeud}, {appui.ddl_debut}, {appui.ddl_fin}"
            for appui in self.appuis
        )
        lignes.extend(("*STEP", "*STATIC", "*CLOAD"))
        for charge in self.charges:
            for ddl, valeur in enumerate(
                (charge.fx_n, charge.fy_n, charge.fz_n), start=1
            ):
                if not isclose(valeur, 0.0, abs_tol=1e-12):
                    lignes.append(f"{charge.noeud}, {ddl}, {valeur:.12g}")
        lignes.extend(
            (
                "*NODE PRINT, NSET=NALL",
                "U",
                "*NODE PRINT, NSET=APPUIS, TOTALS=YES",
                "RF",
                "*NODE FILE, NSET=NALL",
                "U",
                "*EL FILE",
                "S",
                "*END STEP",
            )
        )
        return "\n".join(lignes) + "\n"


@dataclass(frozen=True, slots=True)
class ResultatCalculix:
    charge_verticale_n: float
    somme_reactions_z_n: float
    erreur_equilibre_n: float
    fleche_max_mm: float
    noeud_fleche_max: int
    reaction_max_z_n: float
    nombre_noeuds: int
    nombre_elements: int
    fichier_inp: str
    fichier_frd: str

    def dictionnaire(self) -> dict[str, float | int | str]:
        return {
            champ: getattr(self, champ)
            for champ in self.__dataclass_fields__
        }


_LIGNE_VECTEUR = re.compile(
    r"^\s*(\d+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s*$"
)


def lire_resultats_dat(
    contenu: str,
) -> tuple[
    dict[int, tuple[float, ...]],
    dict[int, tuple[float, ...]],
]:
    """Lit les blocs ``U`` et ``RF`` ASCII demandés par :class:`ModeleCalculix`."""
    deplacements: dict[int, tuple[float, ...]] = {}
    reactions: dict[int, tuple[float, ...]] = {}
    destination: dict[int, tuple[float, ...]] | None = None
    for ligne in contenu.splitlines():
        minuscule = ligne.lower()
        if "displacements (vx,vy,vz)" in minuscule:
            destination = deplacements
            continue
        if "forces (fx,fy,fz)" in minuscule and "total force" not in minuscule:
            destination = reactions
            continue
        correspondance = _LIGNE_VECTEUR.match(ligne)
        if correspondance and destination is not None:
            destination[int(correspondance.group(1))] = tuple(
                float(correspondance.group(index)) for index in range(2, 5)
            )
        elif not ligne.strip() and destination:
            destination = None
    if not deplacements:
        raise ValueError("aucun déplacement trouvé dans le fichier .dat")
    if not reactions:
        raise ValueError("aucune réaction trouvée dans le fichier .dat")
    return deplacements, reactions


def executer_calculix(
    modele: ModeleCalculix,
    repertoire: Path,
    nom_fichier: str = "plancher_local",
    executable: str = "ccx",
) -> ResultatCalculix:
    """Écrit, exécute et contrôle un calcul statique CalculiX."""
    repertoire.mkdir(parents=True, exist_ok=True)
    fichier_inp = repertoire / f"{nom_fichier}.inp"
    fichier_inp.write_text(modele.entree(), encoding="utf-8")
    chemin_executable = shutil.which(executable)
    if chemin_executable is None:
        raise RuntimeError(
            "CalculiX (ccx) est introuvable; entrez dans `nix develop` "
            "ou passez un chemin d'exécutable."
        )
    execution = subprocess.run(
        [chemin_executable, nom_fichier],
        cwd=repertoire,
        capture_output=True,
        text=True,
        check=False,
    )
    (repertoire / f"{nom_fichier}.log").write_text(
        execution.stdout + execution.stderr,
        encoding="utf-8",
    )
    if execution.returncode != 0:
        raise RuntimeError(
            f"CalculiX a échoué avec le code {execution.returncode}; "
            f"voir {nom_fichier}.log"
        )
    fichier_dat = repertoire / f"{nom_fichier}.dat"
    fichier_frd = repertoire / f"{nom_fichier}.frd"
    deplacements, reactions = lire_resultats_dat(
        fichier_dat.read_text(encoding="utf-8")
    )
    noeud_max = min(deplacements, key=lambda tag: deplacements[tag][2])
    charges_z = {charge.noeud: charge.fz_n for charge in modele.charges}
    # ``RF`` contient l'effort interne au nœud bloqué. Si une ``CLOAD`` agit
    # directement sur ce même nœud, la réaction d'appui vaut RF - CLOAD.
    reactions_z = {
        noeud: reaction[2] - charges_z.get(noeud, 0.0)
        for noeud, reaction in reactions.items()
    }
    somme_reactions = sum(reactions_z.values())
    erreur = somme_reactions - modele.charge_verticale_n
    tolerance = max(1e-3, modele.charge_verticale_n * 1e-7)
    if abs(erreur) > tolerance:
        raise RuntimeError(
            "les réactions CalculiX ne sont pas en équilibre avec les charges "
            f"({somme_reactions:.6f} N contre {modele.charge_verticale_n:.6f} N)"
        )
    resultat = ResultatCalculix(
        charge_verticale_n=modele.charge_verticale_n,
        somme_reactions_z_n=somme_reactions,
        erreur_equilibre_n=erreur,
        fleche_max_mm=abs(deplacements[noeud_max][2]),
        noeud_fleche_max=noeud_max,
        reaction_max_z_n=max(reactions_z.values()),
        nombre_noeuds=len(modele.noeuds),
        nombre_elements=len(modele.elements),
        fichier_inp=str(fichier_inp),
        fichier_frd=str(fichier_frd),
    )
    (repertoire / f"{nom_fichier}_resultats.json").write_text(
        json.dumps(resultat.dictionnaire(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return resultat
