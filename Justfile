set shell := ["bash", "-euo", "pipefail", "-c"]

pidfile := ".ocp-vscode.pid"
logfile := ".ocp-vscode.log"

# Lance le viewer en arrière-plan sur http://127.0.0.1:3939/viewer
server:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -f "{{pidfile}}" ]]; then
        pid="$(<"{{pidfile}}")"
        if kill -0 "$pid" 2>/dev/null; then
            echo "Le serveur tourne déjà (PID $pid)"
            exit 0
        fi
    fi
    nohup python -m ocp_vscode \
        --host 127.0.0.1 \
        --port 3939 \
        --tree_width 240 \
        >"{{logfile}}" 2>&1 &
    pid=$!
    echo "$pid" >"{{pidfile}}"
    for _ in {1..40}; do
        if curl --silent --fail http://127.0.0.1:3939/viewer >/dev/null; then
            echo "Viewer lancé (PID $pid) : http://127.0.0.1:3939/viewer"
            exit 0
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi
        sleep 0.25
    done
    echo "Le serveur n'a pas démarré; consultez {{logfile}}" >&2
    unlink "{{pidfile}}"
    exit 1

# Arrête le viewer lancé avec `just server`
kill:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ ! -f "{{pidfile}}" ]]; then
        echo "Aucun serveur enregistré"
        exit 0
    fi
    pid="$(<"{{pidfile}}")"
    if [[ -r "/proc/$pid/cmdline" ]] && tr '\0' ' ' <"/proc/$pid/cmdline" | grep -q "ocp_vscode"; then
        kill "$pid"
        echo "Viewer arrêté (PID $pid)"
    else
        echo "Le PID $pid ne correspond pas au viewer; aucun processus arrêté"
    fi
    unlink "{{pidfile}}"

# Construit puis envoie le modèle au viewer
run:
    python main.py

# Affiche le local batteries 3 × 3 m avec son plancher et ses murs
local-batteries:
    python -m local_batteries.main

# Affiche l'état courant de l'atelier en ossature bois
atelier-mob:
    python -m atelier_mob.main

# Lance le calculateur web de flèche GT24 sur http://127.0.0.1:5050
atelier-mob-fleche:
    python -m atelier_mob.webapp

# Pré-vérifie le plancher de l'atelier aux ELU/ELS selon l'Eurocode 5
atelier-mob-verification:
    python -m atelier_mob.verification

# Exporte les couches GLB puis lance le viewer Three.js sur http://127.0.0.1:8080
atelier-mob-viewer:
    python atelier_mob_viewer/serve.py

# Régénère uniquement les couches 3D consommées par le viewer Three.js
atelier-mob-viewer-export:
    python atelier_mob_viewer/export_model.py

# Exporte les nomenclatures du local batteries
local-batteries-bom:
    python -m local_batteries.bom

# Chiffre le local courant et compare l'ancien plancher renforcé
local-batteries-chiffrage:
    python -m local_batteries.chiffrage

# Génère le POC de manuel PDF depuis la CAO des poutres du plancher
local-batteries-manuel:
    python -m local_batteries.manuel_assemblage

# Calcule le POC élastique du plancher; options après `--`, par exemple
# `just local-batteries-simulation -- --empreinte-longueur 1200`.
local-batteries-simulation *args:
    python -m local_batteries.simulation {{args}}

# Lance les tests du modèle paramétrique
test:
    python -m unittest discover -s tests

# Génère la nomenclature chiffrable dans build/bom.csv
bom:
    python bom.py

# Chiffre un projet avec le catalogue commun ; les anciens lots restent admis
chiffrage projet="maison" lot="tous":
    python chiffrer.py --projet {{projet}} --lot {{lot}}

# Optimise les coupes d'un projet dans les produits commerciaux communs
optimiser projet="maison" lot="plancher":
    python optimiser.py --projet {{projet}} --lot {{lot}}

# Compare les premiers cas de charge du châssis primaire
simulate:
    python simulate.py
