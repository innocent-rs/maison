"""Application Flask de l'optimiseur de poutraison."""

from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
from typing import Any

from flask import Flask, Response, render_template, request, send_file

from .calcul import (
    CatalogueSection,
    DIAMETRE_PLATINE_PIEU_MM,
    HypothesesProjet,
    PROFILS_FLECHE,
    SECTIONS_FOURNISSEUR,
)
from .exports import csv_pieux, pdf_rapport
from .solives import (
    CatalogueSolive,
    HypothesesSolives,
    SOLIVES_FOURNISSEUR,
    optimiser_systeme_porteur,
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
    "fc90_k_mpa",
    "kc90",
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
    valeurs["profil_usage"] = formulaire.get("profil_usage", "maison")
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


def _lire_hypotheses_solives(formulaire: Any) -> HypothesesSolives:
    def valeur_ou_defaut(nom: str, defaut: float) -> float:
        valeur = formulaire.get(nom)
        return defaut if valeur in (None, "") else _nombre(valeur, nom)

    classe_service = valeur_ou_defaut("classe_service_solives", 2)
    if not classe_service.is_integer():
        raise ValueError("la classe de service des solives doit être 1 ou 2")
    largeur_isolant = valeur_ou_defaut("largeur_isolant_mm", 575)
    if not largeur_isolant.is_integer():
        raise ValueError("la largeur d'isolant doit être 575 mm, 600 mm ou désactivée")
    inclure_sabots = (
        formulaire.get("inclure_sabots") == "on"
        if formulaire.get("entraxe_solives_max_mm") not in (None, "")
        else True
    )
    return HypothesesSolives(
        entraxe_max_mm=valeur_ou_defaut("entraxe_solives_max_mm", 625),
        classe_service=int(classe_service),
        limite_fleche_diviseur=valeur_ou_defaut(
            "limite_fleche_solives_diviseur", 350
        ),
        largeur_isolant_mm=int(largeur_isolant),
        inclure_sabots=inclure_sabots,
    )


def _lire_sections_solives(formulaire: Any) -> list[CatalogueSolive]:
    prix = formulaire.getlist("solive_prix")
    if not prix:
        return list(SOLIVES_FOURNISSEUR)
    actives = set(formulaire.getlist("solive_active"))
    if len(prix) != len(SOLIVES_FOURNISSEUR):
        raise ValueError("le catalogue de solives est incomplet")
    sections = [
        CatalogueSolive(
            nom=section.nom,
            largeur_mm=section.largeur_mm,
            hauteur_mm=section.hauteur_mm,
            prix_eur_m=_nombre(prix[index], f"prix de {section.nom}"),
            poids_kg_m=section.poids_kg_m,
            moment_caracteristique_kNm=section.moment_caracteristique_kNm,
            cisaillement_caracteristique_kN=section.cisaillement_caracteristique_kN,
            ei_moyen_kNm2=section.ei_moyen_kNm2,
            ga_moyen_MN=section.ga_moyen_MN,
            longueur_max_m=section.longueur_max_m,
        )
        for index, section in enumerate(SOLIVES_FOURNISSEUR)
        if str(index) in actives
    ]
    if not sections:
        raise ValueError("sélectionnez au moins une section de solive")
    return sections


def _catalogue_solives_formulaire(formulaire: Any) -> list[dict[str, Any]]:
    prix = formulaire.getlist("solive_prix") if formulaire else []
    actives = set(formulaire.getlist("solive_active")) if formulaire else set()
    return [
        {
            **asdict(section),
            "prix_eur_m": prix[index] if index < len(prix) else section.prix_eur_m,
            "active": not formulaire or str(index) in actives,
        }
        for index, section in enumerate(SOLIVES_FOURNISSEUR)
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
            hypotheses_solives = HypothesesSolives()
            valeurs = asdict(hypotheses)
            valeurs_solives = asdict(hypotheses_solives)
            catalogue = _catalogue_formulaire(None)
            catalogue_solives = _catalogue_solives_formulaire(None)
            systeme = optimiser_systeme_porteur(
                hypotheses,
                hypotheses_solives,
            )
            resultat = systeme.principales
            resultat_solives = systeme.solives
            masse_solives_kg_m2 = systeme.masse_solives_kg_m2
            onglet_actif = "principales"
        else:
            valeurs = request.form.to_dict()
            valeurs["inclure_poids_propre"] = request.form.get("inclure_poids_propre") == "on"
            valeurs_solives = request.form.to_dict()
            valeurs_solives["inclure_sabots"] = request.form.get("inclure_sabots") == "on"
            catalogue = _catalogue_formulaire(request.form)
            catalogue_solives = _catalogue_solives_formulaire(request.form)
            onglet_actif = request.form.get("onglet_actif", "principales")
            try:
                hypotheses = _lire_hypotheses(request.form)
                hypotheses_solives = _lire_hypotheses_solives(request.form)
                sections = _lire_sections(request.form)
                sections_solives = _lire_sections_solives(request.form)
                systeme = optimiser_systeme_porteur(
                    hypotheses,
                    hypotheses_solives,
                    sections,
                    sections_solives,
                )
                resultat = systeme.principales
                resultat_solives = systeme.solives
                masse_solives_kg_m2 = systeme.masse_solives_kg_m2
                valeurs = asdict(hypotheses)
                valeurs_solives = asdict(hypotheses_solives)
            except ValueError as exception:
                erreur = str(exception)
                resultat = None
                resultat_solives = None
                masse_solives_kg_m2 = 0.0
                statut = 400
        return (
            render_template(
                "optimiseur.html",
                valeurs=valeurs,
                catalogue=catalogue,
                catalogue_solives=catalogue_solives,
                resultat=resultat,
                resultat_solives=resultat_solives,
                masse_solives_kg_m2=masse_solives_kg_m2,
                valeurs_solives=valeurs_solives,
                onglet_actif=onglet_actif,
                platine_pieu_mm=DIAMETRE_PLATINE_PIEU_MM,
                erreur=erreur,
            ),
            statut,
        )

    @app.post("/export/pieux.csv")
    def exporter_pieux():
        try:
            systeme = optimiser_systeme_porteur(
                _lire_hypotheses(request.form),
                _lire_hypotheses_solives(request.form),
                _lire_sections(request.form),
                _lire_sections_solives(request.form),
            )
            contenu = csv_pieux(systeme.principales)
        except ValueError as exception:
            return Response(str(exception), status=400, mimetype="text/plain")
        return Response(
            contenu,
            headers={"Content-Disposition": "attachment; filename=implantation-pieux.csv"},
            content_type="text/csv; charset=utf-8",
        )

    @app.post("/export/rapport.pdf")
    def exporter_rapport():
        try:
            hypotheses = _lire_hypotheses(request.form)
            systeme = optimiser_systeme_porteur(
                hypotheses,
                _lire_hypotheses_solives(request.form),
                _lire_sections(request.form),
                _lire_sections_solives(request.form),
            )
            contenu = pdf_rapport(systeme.principales, systeme.solives)
        except ValueError as exception:
            return Response(str(exception), status=400, mimetype="text/plain")
        return send_file(
            BytesIO(contenu),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="rapport-poutres-pieux.pdf",
        )

    return app


def main() -> None:
    create_app().run(host="127.0.0.1", port=5051, debug=False)


if __name__ == "__main__":
    main()
