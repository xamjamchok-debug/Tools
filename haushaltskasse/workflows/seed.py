"""Seed: legt Stammdaten an — Konten und Kategorien (Nebenbücher) mit Rückstellungen.

Aufruf:  python -m haushaltskasse.workflows.seed
Braucht eine erreichbare DB (HAUSHALT_DATABASE_URL) mit angelegtem Schema (storage/db.py).

Kategorie-NAMEN sind generisch und stehen hier. Die monatlichen Rückstellungs-BETRÄGE
(personenbezogen) kommen aus data/lokale_config.json -> "ruecklagen": {"Auto": 240, ...}.
"""
from __future__ import annotations

from ..storage.db import connect, init_db
from .lokale_config import lade_lokale_config

# Reale Konten: (Name, Typ)
KONTEN = [
    ("DKB-Giro", "giro"),
    ("comdirect-Giro", "giro"),
    ("comdirect-Tagesgeld", "tagesgeld"),
    ("comdirect-Depot", "depot"),
    ("Amazon-Visa", "kreditkarte"),
]

# Kanonische Kategorien (= Nebenbücher). Namen wie sie die Kategorisierung ausgibt.
KATEGORIEN = [
    "Haushaltskasse", "Auto", "Sport", "Urlaub", "Füchschen", "Kinder",
    "Nebenkosten", "Telefon", "TK", "Vers", "Kredit", "Inst",
    "Jörg", "Natalie", "Einnahmen",
]


def seed(conn=None) -> None:
    own = conn is None
    conn = conn or connect()
    cfg = lade_lokale_config()
    ruecklagen = cfg.get("ruecklagen", {}) if isinstance(cfg, dict) else {}
    try:
        with conn.cursor() as cur:
            for name, typ in KONTEN:
                cur.execute(
                    "INSERT INTO konten (name, typ) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                    (name, typ),
                )
            for name in KATEGORIEN:
                cent = round(float(ruecklagen.get(name, 0)) * 100)
                cur.execute(
                    "INSERT INTO kategorien (name, monatliche_ruecklage_cent) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET monatliche_ruecklage_cent = EXCLUDED.monatliche_ruecklage_cent",
                    (name, cent),
                )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM konten")
            nk = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM kategorien")
            nkat = cur.fetchone()[0]
        print(f"[seed] Konten: {nk} | Kategorien: {nkat}"
              + ("" if ruecklagen else "  (Rückstellungsbeträge: keine lokale_config -> 0)"))
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    init_db()      # Schema sicherstellen
    seed()
