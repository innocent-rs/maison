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

# Lance les tests du modèle paramétrique
test:
    python -m unittest discover -s tests

# Génère la nomenclature chiffrable dans build/bom.csv
bom:
    python bom.py

# Compare les premiers cas de charge du châssis primaire
simulate:
    python simulate.py
