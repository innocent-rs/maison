"""Exports traçables de l'optimisation, sans état serveur."""

from __future__ import annotations

from csv import writer
from io import BytesIO, StringIO

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .calcul import DIAMETRE_PLATINE_PIEU_MM, ResultatOptimisation
from .solives import ResultatOptimisationSolives


def csv_pieux(resultat: ResultatOptimisation) -> bytes:
    configuration = resultat.meilleure
    if configuration is None:
        raise ValueError("aucune configuration conforme à exporter")
    flux = StringIO()
    tableau = writer(flux, delimiter=";", lineterminator="\n")
    tableau.writerow(
        (
            "pieu",
            "type",
            "x_m",
            "y_m",
            "reaction_els_kN",
            "reaction_elu_kN",
            "capacite_kN",
            "utilisation_pct",
            "niveau",
        )
    )
    for pieu in configuration.pieux:
        tableau.writerow(
            (
                pieu.identifiant,
                pieu.type_appui,
                f"{pieu.x_m:.3f}",
                f"{pieu.y_m:.3f}",
                f"{pieu.reaction_els_kN:.3f}",
                f"{pieu.reaction_elu_kN:.3f}",
                f"{configuration.capacite_appui_kN:.3f}",
                f"{pieu.taux_capacite * 100:.1f}",
                pieu.niveau,
            )
        )
    return ("\ufeff" + flux.getvalue()).encode("utf-8")


def pdf_rapport(
    resultat: ResultatOptimisation,
    resultat_solives: ResultatOptimisationSolives | None = None,
) -> bytes:
    configuration = resultat.meilleure
    if configuration is None:
        raise ValueError("aucune configuration conforme à exporter")
    flux = BytesIO()
    with PdfPages(flux) as pdf:
        figure = Figure(figsize=(8.27, 11.69))
        axe = figure.subplots()
        axe.axis("off")
        hypotheses = resultat.hypotheses
        lignes = [
            "TRAME — RAPPORT DE PRÉ-DIMENSIONNEMENT",
            "",
            f"Surface : {hypotheses.longueur_m:.2f} × {hypotheses.largeur_m:.2f} m ({hypotheses.surface_m2:.2f} m²)",
            f"Usage : {hypotheses.profil_usage} · confort : {hypotheses.profil_fleche} (L/{hypotheses.limite_fleche_diviseur:.0f})",
            f"Charges : G {hypotheses.masse_permanente_kg_m2:.1f} kg/m² · Q {hypotheses.masse_exploitation_kg_m2:.1f} kg/m²",
            "",
            f"Choix : {configuration.section.nom} mm · {configuration.nombre_poutres} poutres",
            f"Travées : {configuration.nombre_travees} × {configuration.portee_m:.2f} m · entraxe {configuration.entraxe_m:.3f} m",
            f"Pieux : {configuration.nombre_pieux_total} dont {configuration.nombre_pieux_rive} aux rives",
            f"Coût : {configuration.cout_bois_eur:.0f} € bois + {configuration.cout_appuis_eur:.0f} € pieux = {configuration.cout_eur:.0f} €",
            "",
            f"Flèche finale : {configuration.fleche_finale_mm:.2f} / {configuration.limite_fleche_mm:.2f} mm ({configuration.taux_fleche * 100:.0f} %)",
            f"Flexion ELU : {configuration.taux_flexion * 100:.0f} % · cisaillement ELU : {configuration.taux_cisaillement * 100:.0f} %",
            f"Pieu max. : {configuration.reaction_pieu_max_elu_kN:.2f} / {configuration.capacite_appui_kN:.2f} kN ({configuration.taux_appui * 100:.0f} %)",
            f"Compression bois/platine : {configuration.taux_compression_appui * 100:.0f} %",
            f"Vibration indicative : {configuration.frequence_propre_hz:.1f} Hz · w1kN {configuration.fleche_sous_1kn_mm:.2f} mm",
            "",
            "LIMITES",
            "Calcul analytique de poutres principales simplement appuyées. Solives en I, diaphragme,",
            "liaisons, arrachement, sol, corrosion, feu, séisme et stabilité globale hors calcul.",
            "La capacité de 5 t du pieu est une hypothèse à confirmer avec le fournisseur et le sol.",
        ]
        axe.text(0.06, 0.96, "\n".join(lignes), va="top", fontsize=10, linespacing=1.55)
        pdf.savefig(figure)

        if resultat_solives and resultat_solives.meilleure:
            solives = resultat_solives.meilleure
            figure_solives = Figure(figsize=(8.27, 11.69))
            axe_solives = figure_solives.subplots()
            axe_solives.axis("off")
            total_systeme = configuration.cout_eur + solives.cout_eur
            lignes_solives = [
                "V2 — SOLIVES EN I",
                "",
                f"Choix : STEICOjoist {solives.section.nom}",
                f"Portée : {solives.portee_m:.3f} m entre poutres principales",
                f"Trame : {solives.nombre_lignes_solives} lignes · entraxe courant {solives.entraxe_mm:.0f} mm",
                (
                    f"Rives ajustées : {len(solives.entraxes_rive_mm)} à "
                    + " / ".join(f"{valeur:.0f}" for valeur in solives.entraxes_rive_mm)
                    + " mm"
                    if solives.entraxes_rive_mm
                    else "Rives : même module que la trame courante"
                ),
                f"Vide entre membrures : {solives.largeur_vide_isolant_mm:.0f} mm"
                + (
                    f" · serrage isolant {solives.compression_isolant_mm:.0f} mm"
                    if solives.compression_isolant_mm is not None
                    else ""
                ),
                f"Dépassement sous les principales : {solives.depassement_sous_principale_mm:.0f} mm",
                f"Débit : {solives.nombre_segments} segments · {solives.longueur_totale_m:.1f} m",
                f"Sabots estimés : {solives.nombre_sabots} · réaction ELU max. {solives.reaction_sabot_elu_kN:.2f} kN",
                "",
                f"Flèche finale : {solives.fleche_finale_mm:.2f} / {solives.limite_fleche_mm:.2f} mm ({solives.taux_fleche * 100:.0f} %)",
                f"Flexion ELU : {solives.moment_elu_kNm:.2f} / {solives.moment_resistant_kNm:.2f} kN·m ({solives.taux_flexion * 100:.0f} %)",
                f"Cisaillement ELU : {solives.effort_tranchant_elu_kN:.2f} / {solives.effort_tranchant_resistant_kN:.2f} kN ({solives.taux_cisaillement * 100:.0f} %)",
                f"Vibration indicative : {solives.frequence_propre_hz:.1f} Hz · w1kN {solives.fleche_sous_1kn_mm:.2f} mm",
                "",
                f"Coût solives : {solives.cout_solives_eur:.0f} €",
                f"Coût estimatif sabots : {solives.cout_sabots_eur:.0f} €",
                f"Total structure porteuse : {total_systeme:.0f} €",
                "",
                "LIMITES V2",
                "Les segments de solive sont simplement appuyés entre poutres principales.",
                "Les sabots sont comptés mais leur référence, fixation et résistance ne sont pas vérifiées.",
                "Une solive plus haute que son porteur sort du détail EWH standard retenu et exige un détail justifié.",
                "Panneaux, entretoises, anti-dévers, renforts d'âme et charges localisées hors calcul.",
            ]
            axe_solives.text(
                0.06,
                0.96,
                "\n".join(lignes_solives),
                va="top",
                fontsize=10,
                linespacing=1.55,
            )
            pdf.savefig(figure_solives)

        figure_plan = Figure(figsize=(8.27, 8.27))
        plan = figure_plan.subplots()
        plan.set_aspect("equal")
        plan.add_patch(
            Rectangle(
                (0, 0),
                configuration.largeur_repartie_m,
                configuration.portee_totale_m,
                facecolor="#f3f0e8",
                edgecolor="#34413c",
            )
        )
        largeur_poutre_m = configuration.section.largeur_mm / 1_000
        for colonne in range(configuration.nombre_poutres):
            x = colonne * configuration.entraxe_m
            plan.add_patch(
                Rectangle(
                    (x - largeur_poutre_m / 2, 0),
                    largeur_poutre_m,
                    configuration.portee_totale_m,
                    facecolor="#bd6f42",
                    alpha=0.75,
                )
            )
        couleurs = {"marge": "#58b78e", "vigilance": "#efa061", "depasse": "#e06358"}
        platine_m = DIAMETRE_PLATINE_PIEU_MM / 1_000
        for pieu in configuration.pieux:
            plan.add_patch(
                Rectangle(
                    (pieu.x_m - platine_m / 2, pieu.y_m - platine_m / 2),
                    platine_m,
                    platine_m,
                    facecolor=couleurs[pieu.niveau],
                    edgecolor="white",
                    linewidth=0.8,
                    zorder=3,
                )
            )
            plan.text(pieu.x_m, pieu.y_m + platine_m * 0.75, pieu.identifiant, ha="center", fontsize=5)
        marge = platine_m
        plan.set_xlim(-marge, configuration.largeur_repartie_m + marge)
        plan.set_ylim(configuration.portee_totale_m + marge, -marge)
        plan.set_title("Plan des poutres et pieux — platines 200 × 200 mm à l'échelle")
        plan.set_xlabel("x (m)")
        plan.set_ylabel("y (m)")
        plan.grid(alpha=0.15)
        pdf.savefig(figure_plan)

        for debut in range(0, len(configuration.pieux), 32):
            page = Figure(figsize=(11.69, 8.27))
            axe_table = page.subplots()
            axe_table.axis("off")
            lot = configuration.pieux[debut : debut + 32]
            cellules = [
                [
                    p.identifiant,
                    p.type_appui,
                    f"{p.x_m:.3f}",
                    f"{p.y_m:.3f}",
                    f"{p.reaction_els_kN:.2f}",
                    f"{p.reaction_elu_kN:.2f}",
                    f"{p.taux_capacite * 100:.0f} %",
                ]
                for p in lot
            ]
            table = axe_table.table(
                cellText=cellules,
                colLabels=("Pieu", "Type", "x (m)", "y (m)", "ELS (kN)", "ELU (kN)", "Taux"),
                loc="center",
                cellLoc="center",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.25)
            axe_table.set_title("Implantation et descente de charges", pad=20)
            pdf.savefig(page)
    return flux.getvalue()
