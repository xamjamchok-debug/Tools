"""Haushaltskasse-Paket.

Lädt beim Import automatisch die .env aus dem Repo-Root, damit alle
`python -m haushaltskasse.*`-Befehle HAUSHALT_DATABASE_URL / ANTHROPIC_API_KEY
finden, ohne dass die Variablen von Hand exportiert werden müssen.
"""
from pathlib import Path

try:
    from dotenv import load_dotenv

    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)
except ImportError:
    # python-dotenv nicht installiert — Variablen müssen dann aus der Umgebung kommen.
    pass
