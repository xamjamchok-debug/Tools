"""PostgreSQL-Zugriffsschicht der Haushaltskasse (Azure Database for PostgreSQL).

Verbindung kommt aus der Umgebungsvariable HAUSHALT_DATABASE_URL, z. B.:
    postgresql://adminuser:PASSWORT@servername.postgres.database.azure.com:5432/haushaltskasse?sslmode=require

Schema anlegen:  python -m haushaltskasse.storage.db
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg

_STORAGE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = _STORAGE_DIR / "schema.sql"


def _load_dotenv() -> None:
    """Lädt die `.env` aus der Projektwurzel in os.environ (nur fehlende Keys überschreiben nichts).

    So funktionieren alle Einstiegspunkte (Dashboard, Beladung, Gegenbuchung) mit einem
    einzigen Befehl, ohne HAUSHALT_DATABASE_URL vorher manuell exportieren zu müssen.
    """
    env = _STORAGE_DIR.parent.parent / ".env"   # haushaltskasse/storage -> Repo-Wurzel
    if not env.exists():
        return
    for zeile in env.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile and not zeile.startswith("#") and "=" in zeile:
            schluessel, wert = zeile.split("=", 1)
            os.environ.setdefault(schluessel.strip(), wert.strip().strip('"').strip("'"))


_load_dotenv()


def _dsn() -> str:
    dsn = os.getenv("HAUSHALT_DATABASE_URL")
    if not dsn:
        raise EnvironmentError(
            "HAUSHALT_DATABASE_URL nicht gesetzt — Postgres-Connection-String in .env eintragen "
            "(Format s. .env.example)."
        )
    return dsn


def connect() -> psycopg.Connection:
    """Öffnet eine Verbindung zur Azure-Postgres-Datenbank (SSL wird über den DSN erzwungen)."""
    return psycopg.connect(_dsn())


def init_db(conn: psycopg.Connection | None = None) -> None:
    """Legt alle Tabellen idempotent an (CREATE TABLE IF NOT EXISTS)."""
    own = conn is None
    conn = conn or connect()
    try:
        script = SCHEMA_PATH.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            # psycopg3 führt pro execute() ein Statement aus → Skript in Statements aufteilen.
            for stmt in _split_statements(script):
                cur.execute(stmt)
        conn.commit()
    finally:
        if own:
            conn.close()


def kennzahlen(conn: psycopg.Connection | None = None) -> dict:
    """Kern-Kennzahlen in Euro: Realsaldo, Summe Rücklagen, Forderungen, verfügbarer Saldo.

    Realsaldo       = Summe ALLER Buchungen auf realen Konten (konto_id gesetzt) —
                      inkl. Startsaldo, Umbuchungen, Wertpapiere, Zinsen. Das ist das
                      tatsächlich auf den Konten liegende Vermögen (Rücklagen sind
                      virtuell und haben konto_id = NULL, zählen hier nicht mit).
    Summe Rücklagen = nur echte Rücklagen-Töpfe (Rolle 'ruecklage') — Fable-Review Befund B7:
                      vorher zählten die Forderungen (Natalie/Jörg) hier fälschlich mit.
    Forderungen     = Rolle 'forderung', separat ausgewiesen.
    Verfügbar       = Realsaldo - Summe Rücklagen (was nicht in Töpfen gebunden ist).
    """
    from ..domain import saldo as _saldo   # lazy: vermeidet Import-Zirkel beim Paket-Init
    own = conn is None
    conn = conn or connect()
    try:
        with conn.cursor() as cur:
            real = _saldo.summe_konten(cur)
            ruecklagen = _saldo.summe_ruecklagen(cur)
            forderungen = _saldo.summe_forderungen(cur)
        return {
            "realsaldo": round(real / 100, 2),
            "summe_ruecklagen": round(ruecklagen / 100, 2),
            "forderungen": round(forderungen / 100, 2),
            "verfuegbarer_saldo": round((real - ruecklagen) / 100, 2),
        }
    finally:
        if own:
            conn.close()


def _split_statements(script: str) -> list[str]:
    """Zerlegt das Schema-Skript an ';' in einzelne Statements.

    Zeilenkommentare (ab '--') werden VOR dem Split entfernt, damit ein Semikolon
    in einem Kommentar kein Statement zerreißt. Das Schema hat keine '--' in String-Literalen.
    """
    ohne_kommentar = "\n".join(re.sub(r"--.*$", "", zeile) for zeile in script.splitlines())
    return [s.strip() for s in ohne_kommentar.split(";") if s.strip()]


if __name__ == "__main__":
    init_db()
    print("[db] Schema angelegt/aktualisiert in der Azure-Postgres-Datenbank.")
    print(f"[db] Kennzahlen: {kennzahlen()}")
