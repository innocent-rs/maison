"""Application Flask de l'optimiseur de poutraison."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from flask import Flask, render_template, request

from .calcul import (
    CatalogueSection,
    DIAMETRE_PLATINE_PIEU_MM,
    HypothesesProjet,
    PROFILS_FLECHE,
    SECTIONS_FOURNISSEUR,
    optimiser,
)


CHAMPS_NOMBRES = (
    "longueur_m",
    "largeur_m",
    "masse_permanente_kg_m2",
    "masse_exploitation_kg_m2",
    "masse_ajoutee_totale_kg",
    "masse_volumique_kg_m3",
    "entraxe_max_m",
    "e_moyen_mpa",
    "g_moyen_mpa",
    "fm_k_mpa",
    "fv_k_mpa",
    "kmod",
    "kdef",
    "psi2",
    "gamma_m",
)


def _nombre(valeur: str, libelle: str) -> float:
    try:
        return float(valeur.strip().replace(",", "."))
    except (AttributeError, ValueError) as erreur:
        raise ValueError(f"« {libelle} » n'est pas un nombre valide") from erreur


def _lire_hypotheses(formulaire: Any) -> HypothesesProjet:
    valeurs = {champ: _nombre(formulaire.get(champ, ""), champ) for champ in CHAMPS_NOMBRES}
    profil_fleche = formulaire.get("profil_fleche", "maison")
    if profil_fleche == "personnalise":
        valeurs["limite_fleche_diviseur"] = _nombre(
            formulaire.get("limite_fleche_diviseur", ""),
            "limite de flèche personnalisée",
        )
    elif profil_fleche in PROFILS_FLECHE:
        valeurs["limite_fleche_diviseur"] = PROFILS_FLECHE[profil_fleche]
    else:
        raise ValueError("le profil de flèche est invalide")
    valeurs["profil_fleche"] = profil_fleche
    valeurs["orientation"] = formulaire.get("orientation", "auto")
    valeurs["inclure_poids_propre"] = formulaire.get("inclure_poids_propre") == "on"
    return HypothesesProjet(**valeurs)


def _lire_sections(formulaire: Any) -> list[CatalogueSection]:
    noms = formulaire.getlist("section_nom")
    largeurs = formulaire.getlist("section_largeur")
    hauteurs = formulaire.getlist("section_hauteur")
    prix = formulaire.getlist("section_prix")
    longueurs = formulaire.getlist("section_longueur_max")
    actives = set(formulaire.getlist("section_active"))
    tailles = {len(noms), len(largeurs), len(hauteurs), len(prix), len(longueurs)}
    if len(tailles) != 1:
        raise ValueError("le catalogue de sections est incomplet")
    sections = []
    for index, nom in enumerate(noms):
        if str(index) not in actives:
            continue
        sections.append(
            CatalogueSection(
                nom=nom,
                largeur_mm=_nombre(largeurs[index], f"largeur de {nom}"),
                hauteur_mm=_nombre(hauteurs[index], f"hauteur de {nom}"),
                prix_eur_m=_nombre(prix[index], f"prix de {nom}"),
                longueur_max_m=_nombre(longueurs[index], f"longueur maximale de {nom}"),
            )
        )
    if not sections:
        raise ValueError("sélectionnez au moins une section")
    return sections


def _catalogue_formulaire(formulaire: Any) -> list[dict[str, Any]]:
    if not formulaire:
        return [{**asdict(section), "active": True} for section in SECTIONS_FOURNISSEUR]
    noms = formulaire.getlist("section_nom")
    largeurs = formulaire.getlist("section_largeur")
    hauteurs = formulaire.getlist("section_hauteur")
    prix = formulaire.getlist("section_prix")
    longueurs = formulaire.getlist("section_longueur_max")
    actives = set(formulaire.getlist("section_active"))
    return [
        {
            "nom": nom,
            "largeur_mm": largeurs[i] if i < len(largeurs) else "",
            "hauteur_mm": hauteurs[i] if i < len(hauteurs) else "",
            "prix_eur_m": prix[i] if i < len(prix) else "",
            "longueur_max_m": longueurs[i] if i < len(longueurs) else "",
            "active": str(i) in actives,
        }
        for i, nom in enumerate(noms)
    ]


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.from_mapping(test_config)

    @app.route("/", methods=("GET", "POST"))
    def index():
        erreur = None
        statut = 200
        if request.method == "GET":
            hypotheses = HypothesesProjet()
            valeurs = asdict(hypotheses)
            catalogue = _catalogue_formulaire(None)
            resultat = optimiser(hypotheses)
        else:
            valeurs = request.form.to_dict()
            valeurs["inclure_poids_propre"] = request.form.get("inclure_poids_propre") == "on"
            catalogue = _catalogue_formulaire(request.form)
            try:
                hypotheses = _lire_hypotheses(request.form)
                sections = _lire_sections(request.form)
                resultat = optimiser(hypotheses, sections)
                valeurs = asdict(hypotheses)
            except ValueError as exception:
                erreur = str(exception)
                resultat = None
                statut = 400
        return (
            render_template(
                "optimiseur.html",
                valeurs=valeurs,
                catalogue=catalogue,
                resultat=resultat,
                platine_pieu_mm=DIAMETRE_PLATINE_PIEU_MM,
                erreur=erreur,
            ),
            statut,
        )

    return app


def main() -> None:
    create_app().run(host="127.0.0.1", port=5051, debug=False)


if __name__ == "__main__":
    main()
