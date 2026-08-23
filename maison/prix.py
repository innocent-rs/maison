"""Base de prix locale du projet.

Renseigner les prix TTC et les conditionnements ici. Les références sont celles
de ``build/bom.csv``. Une valeur ``None`` est volontairement considérée comme
manquante par le chiffrage.

Exemples : ``Tarif.par_conditionnement("29.90", 250, "boîte de 250")``,
``Tarif.en_barres("183.30", longueur_commerciale_mm=13_000, ...)`` ou
``Tarif.en_lots_lineaires("182", longueur_du_lot_mm=20_000, ...)``. Le prix
représente toujours une unité achetée entière, jamais une longueur utile.
"""

from maison.chiffrage import Tarif


# Les prix linéaires affichés par les vendeurs sont convertis au prix de la
# barre commerciale complète ou du minimum de commande avant enregistrement.
PRIX_DOUGLAS_CONTRECOLLE_120X240_TTC_PAR_BARRE: str | None = "693.23"
PRIX_SJ60X240_TTC_PAR_BARRE: str | None = "183.30"


TARIF_DOUGLAS_CONTRECOLLE_120X240 = Tarif.en_barres(
    PRIX_DOUGLAS_CONTRECOLLE_120X240_TTC_PAR_BARRE,
    reference_achat="DOUGLAS-GT24-120x240-L13500",
    designation_achat="Douglas contrecollé GT24 120 × 240 mm — L 13 500 mm",
    longueur_commerciale_mm=13_500,
    trait_scie_mm=5,
    fournisseur="Matériaux Naturels",
    date_tarif="2026-08-23",
    url=(
        "https://www.materiaux-naturels.fr/produit/1149-"
        "bois-d-ossature-douglas-contrecolle"
    ),
    note="Barre entière ; prix arrondi depuis 13,5 m × 51,35 € TTC/m",
)

TARIF_STEICOJOIST_SJ60X240 = Tarif.en_barres(
    PRIX_SJ60X240_TTC_PAR_BARRE,
    reference_achat="STEICO-SJ60x240-L13000",
    designation_achat="STEICOjoist SJ60/240 — L 13 000 mm",
    longueur_commerciale_mm=13_000,
    trait_scie_mm=5,
    fournisseur="Matériaux Naturels",
    date_tarif="2026-08-23",
    url="https://www.materiaux-naturels.fr/produit/1070-poutre-en-i-steico-joist",
    note="Barre entière ; prix calculé depuis 13 m × 14,10 € TTC/m",
)


TARIFS: dict[str, Tarif] = {
    "ARB-120x250-A60-LD4126_51": Tarif(
        note="Produit commercial de l'arbalétrier à définir"
    ),
    "FERRURE-PIED-AFRAME-PROV-120": Tarif(
        note="Pièce provisoire : tarif seulement après dimensionnement"
    ),
    "ISOL-ISONAT-FLEX55-145x580x1220": Tarif.par_conditionnement(
        "48.48",
        quantite=4,
        conditionnement="colis de 4 panneaux",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit-decl/4739-"
            "isonat-flex-55-plus-h-panneau-laine-de-bois-145mm-0.58x1.22m-"
        ),
        note=(
            "2,8304 m² par colis ; tarif promotionnel de 17,13 € TTC/m² "
            "valable jusqu'au 31/08/2026"
        ),
    ),
    "KIT-TIRANT-AFRAME-M16-L4000": Tarif(
        note="Kit complet avec tige, platines, écrous et réglage"
    ),
    "MAD-120x240-L3756": TARIF_DOUGLAS_CONTRECOLLE_120X240,
    "MAD-120x240-L4800": TARIF_DOUGLAS_CONTRECOLLE_120X240,
    "OSB-BD-1196x2800x12": Tarif.par_conditionnement(
        "28.16",
        quantite=1,
        conditionnement="panneau",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit-decl/6572-"
            "panneau-osb-3-sans-formaldehyde-ajoute-12mm-bd-2800x1196mm"
        ),
        note="Panneau entier ; 3,3488 m² à 8,41 € TTC/m², arrondi au centime",
    ),
    "OSB-RL-675x2500x22": Tarif.par_conditionnement(
        "27.51",
        quantite=1,
        conditionnement="panneau",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit-decl/4930-"
            "panneau-osb-3-sans-formaldehyde-ajoute-22mm-rl-2500x675mm"
        ),
        note="Panneau entier rainuré-languetté pour le plancher supérieur",
    ),
    "SIMPSON-CNA4.0X35": Tarif.par_conditionnement(
        "11.88",
        quantite=250,
        conditionnement="boîte de 250",
        fournisseur="Maxoutil",
        date_tarif="2026-08-23",
        url=(
            "https://www.maxoutil.com/pointe-crantee-o-4mm-simpson-pour-"
            "sabot-cna-731500.html"
        ),
        note="Deux boîtes nécessaires pour les 384 pointes des étriers EWH",
    ),
    "SIMPSON-CSA5.0X40": Tarif.par_conditionnement(
        "39.56",
        quantite=250,
        conditionnement="boîte de 250",
        fournisseur="Maxoutil",
        date_tarif="2026-08-23",
        url="https://www.maxoutil.com/importcat29229.html",
        note="Deux boîtes nécessaires pour les 300 vis du plan de fixation total",
    ),
    "SIMPSON-EWH240-61": Tarif.par_conditionnement(
        "7.30",
        quantite=1,
        conditionnement="pièce",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit/1738-"
            "sabot-en-u-etrier-de-charpente-simpson-strong"
        ),
        note="Deux étriers par segment de poutre en I",
    ),
    "SIMPSON-SAI500-120-2": Tarif.par_conditionnement(
        "7.09",
        quantite=1,
        conditionnement="pièce",
        fournisseur="Maxoutil",
        date_tarif="2026-08-23",
        url=(
            "https://www.maxoutil.com/sabot-a-ailes-interieures-t500-"
            "l-120-h-190-mm-simpson-sai500-120-2.html"
        ),
        note="Six sabots, un à chaque about des trois traverses",
    ),
    "SJI-60x240-L2212": TARIF_STEICOJOIST_SJ60X240,
    "TAS-60x40-L2212": Tarif.en_lots_lineaires(
        "182.00",
        longueur_du_lot_mm=20_000,
        conditionnement="commande minimale de 20 ml",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit-decl/5687-"
            "lambourde-en-douglas--60x40mm-rabotee-2-faces-seche"
        ),
        note=(
            "Minimum fournisseur de 20 ml à 9,10 € TTC/ml ; "
            "longueurs de livraison non publiées"
        ),
    ),
    "SPAX-0191010400355": Tarif.par_conditionnement(
        "28.00",
        quantite=1_000,
        conditionnement="boîte de 1 000",
        fournisseur="SPAX / tarif communiqué par le maître d'ouvrage",
        date_tarif="2026-08-23",
        url=(
            "https://www.spax.com/de-de/p/universalschraube-teilgewinde-"
            "senkkopf-t-star-plus-4cut-wirox.html"
        ),
        note="Référence fabricant 0191010400355 ; filetage partiel de 23 mm",
    ),
    "KLIMAS-KMWHT-6X160": Tarif.par_conditionnement(
        "27.50",
        quantite=100,
        conditionnement="boîte de 100",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit/1873-"
            "vis-torx-construction-bois-charpente"
        ),
        note=(
            "Plan provisoire : fixation latérale des lambourdes de rive, "
            "entraxe maximal 300 mm"
        ),
    ),
    "KLIMAS-KMWHT-5X60": Tarif.par_conditionnement(
        "10.80",
        quantite=200,
        conditionnement="boîte de 200",
        fournisseur="Matériaux Naturels",
        date_tarif="2026-08-23",
        url=(
            "https://www.materiaux-naturels.fr/produit-decl/8653-"
            "vis-torx-construction-bois-charpente-5x60"
        ),
        note="Trois boîtes nécessaires pour les 568 vis du plancher OSB",
    ),
}
