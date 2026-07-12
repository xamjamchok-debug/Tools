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
    """Kern-Kennzahlen in Euro: Realsaldo, Summe Rücklagen, verfügbarer Saldo.

    Realsaldo       = Summe aller 'real'-Buchungen (Konten).
    Summe Rücklagen = Summe aller 'ruecklage'-Buchungen (Zuführung - Verzehr ± Korrektur).
    Verfügbar       = Realsaldo - Summe Rücklagen.  Umbuchungen zählen nicht (netto 0).
    """
    own = conn is None
    conn = conn or connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE buchungsart='real'")
            real = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE buchungsart='ruecklage'")
            ruecklagen = cur.fetchone()[0]
        return {
            "realsaldo": round(real / 100, 2),
            "summe_ruecklagen": round(ruecklagen / 100, 2),
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
