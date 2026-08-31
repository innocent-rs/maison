"""Régénère les couches puis sert le viewer avec la bibliothèque standard."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from export_model import export_viewer_model


PROJECT_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Viewer Three.js de l’atelier MOB")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="sert les fichiers GLB existants sans régénérer le modèle",
    )
    args = parser.parse_args()

    if not args.no_export:
        manifest = export_viewer_model()
        print(f"Modèle régénéré : {manifest}")

    handler = partial(SimpleHTTPRequestHandler, directory=PROJECT_DIR)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Viewer disponible sur http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nViewer arrêté")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
