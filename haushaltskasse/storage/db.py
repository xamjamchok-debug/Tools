"""SQLite-Zugriffsschicht der Haushaltskasse.

Aufruf zum Initialisieren:  python -m haushaltskasse.storage.db
Die DB-Datei liegt unter haushaltskasse/data/haushaltskasse.db (gitignored, bleibt lokal).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_STORAGE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _STORAGE_DIR.parent / "data"
DB_PATH = _DATA_DIR / "haushaltskasse.db"
SCHEMA_PATH = _STORAGE_DIR / "schema.sql"


def connect() -> sqlite3.Connection:
    """Öffnet eine Verbindung mit aktivierten Foreign Keys und Row-Zugriff per Name."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Legt alle Tabellen idempotent an (CREATE TABLE IF NOT EXISTS)."""
    own = conn is None
    conn = conn or connect()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    if own:
        conn.close()


def kennzahlen(conn: sqlite3.Connection | None = None) -> dict:
    """Liefert die Kern-Kennzahlen: Realsaldo, Summe Rücklagen, verfügbarer Saldo (in Euro).

    Realsaldo        = Summe aller 'real'-Buchungen (Konten).
    Summe Rücklagen  = Summe aller 'ruecklage'-Buchungen (Zuführung - Verzehr ± Korrektur).
    Verfügbar        = Realsaldo - Summe Rücklagen.
    Umbuchungen zählen nicht (netto 0).
    """
    own = conn is None
    conn = conn or connect()
    try:
        real = conn.execute(
            "SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE buchungsart='real'"
        ).fetchone()[0]
        ruecklagen = conn.execute(
            "SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE buchungsart='ruecklage'"
        ).fetchone()[0]
        return {
            "realsaldo": round(real / 100, 2),
            "summe_ruecklagen": round(ruecklagen / 100, 2),
            "verfuegbarer_saldo": round((real - ruecklagen) / 100, 2),
        }
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    init_db()
    print(f"[db] Schema angelegt/aktualisiert: {DB_PATH}")
    print(f"[db] Kennzahlen: {kennzahlen()}")
