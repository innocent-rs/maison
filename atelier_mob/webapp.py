"""Webapp Flask locale pour explorer la flèche des poutres GT24."""

from dataclasses import asdict
from typing import Any

from flask import Flask, render_template, request

from .fleche import HypothesesFleche, ResultatFleche, calculer_fleche


CHAMPS_NUMERIQUES = (
    "portee_mm",
    "largeur_mm",
    "hauteur_mm",
    "module_young_mpa",
    "module_cisaillement_mpa",
    "coefficient_cisaillement",
    "masse_volumique_kg_m3",
    "charge_permanente_kN_m2",
    "charge_exploitation_kN_m2",
    "largeur_tributaire_m",
    "charge_ponctuelle_kN",
    "limite_fleche_diviseur",
)


def _nombre(valeur: str) -> float:
    try:
        return float(valeur.strip().replace(",", "."))
    except ValueError as erreur:
        raise ValueError(f"« {valeur} » n'est pas un nombre valide") from erreur


def _hypotheses_depuis_formulaire(formulaire: Any) -> HypothesesFleche:
    valeurs = {
        champ: _nombre(formulaire.get(champ, ""))
        for champ in CHAMPS_NUMERIQUES
    }
    valeurs["inclure_poids_propre"] = formulaire.get("inclure_poids_propre") == "on"
    return HypothesesFleche(**valeurs)


def _graphique(resultat: ResultatFleche) -> dict[str, Any]:
    largeur, hauteur = 920, 250
    gauche, droite, haut, bas = 42, 18, 30, 38
    largeur_utile = largeur - gauche - droite
    hauteur_utile = hauteur - haut - bas
    fleche_max = max(resultat.service.fleche_totale_mm, 1e-9)
    points = " ".join(
        f"{gauche + x / resultat.hypotheses.portee_mm * largeur_utile:.2f},"
        f"{haut + fleche / fleche_max * hauteur_utile:.2f}"
        for x, fleche in resultat.profil_service
    )
    return {
        "largeur": largeur,
        "hauteur": hauteur,
        "gauche": gauche,
        "droite": droite,
        "haut": haut,
        "bas": bas,
        "largeur_utile": largeur_utile,
        "hauteur_utile": hauteur_utile,
        "points": points,
    }


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Fabrique l'application afin qu'elle reste simple à tester."""
    app = Flask(__name__)
    if test_config:
        app.config.from_mapping(test_config)

    @app.route("/", methods=("GET", "POST"))
    def index():
        erreur = None
        statut = 200
        if request.method == "POST":
            valeurs_formulaire = request.form.to_dict()
            try:
                hypotheses = _hypotheses_depuis_formulaire(request.form)
                resultat = calculer_fleche(hypotheses)
                valeurs_formulaire = asdict(hypotheses)
            except ValueError as exception:
                erreur = str(exception)
                resultat = None
                statut = 400
        else:
            hypotheses = HypothesesFleche()
            valeurs_formulaire = asdict(hypotheses)
            resultat = calculer_fleche(hypotheses)

        return (
            render_template(
                "fleche.html",
                valeurs=valeurs_formulaire,
                resultat=resultat,
                graphique=_graphique(resultat) if resultat else None,
                erreur=erreur,
            ),
            statut,
        )

    return app


def main() -> None:
    create_app().run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
