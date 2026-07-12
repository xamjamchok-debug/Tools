"""Beladung: geparste + verarbeitete Buchungen in die Datenbank schreiben.

Aufruf:  python -m haushaltskasse.workflows.laden
Voraussetzung: Schema angelegt (storage/db.py) und Seed gelaufen (seed.py).
Liest die Exporte aus input/, grenzt ab, kategorisiert und schreibt in buchungen.
Dedupliziert über import_hash (erneuter Lauf legt nichts doppelt an).
"""
from __future__ import annotations

from ..storage.db import connect
from .lokale_config import lade_lokale_config
from .pipeline import einlesen, verarbeiten


def _lade_maps(cur):
    cur.execute("SELECT name, id FROM konten")
    konten = dict(cur.fetchall())
    cur.execute("SELECT name, id FROM kategorien")
    kategorien = dict(cur.fetchall())
    return konten, kategorien


def _konto_id(cur, konten, name):
    if name not in konten:
        cur.execute("INSERT INTO konten (name, typ) VALUES (%s,'sonstiges') "
                    "ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
        row = cur.fetchone()
        cur.execute("SELECT id FROM konten WHERE name=%s", (name,))
        konten[name] = cur.fetchone()[0]
    return konten[name]


def _kategorie_id(cur, kategorien, name):
    if name not in kategorien:
        cur.execute("INSERT INTO kategorien (name) VALUES (%s) "
                    "ON CONFLICT (name) DO NOTHING", (name,))
        cur.execute("SELECT id FROM kategorien WHERE name=%s", (name,))
        kategorien[name] = cur.fetchone()[0]
    return kategorien[name]


def _unterkategorie_id(cur, cache, kategorie_id, name):
    if not name:
        return None
    key = (kategorie_id, name)
    if key not in cache:
        cur.execute("INSERT INTO unterkategorien (kategorie_id, name, quelle) VALUES (%s,%s,'ki') "
                    "ON CONFLICT (kategorie_id, name) DO NOTHING", (kategorie_id, name))
        cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s", (kategorie_id, name))
        cache[key] = cur.fetchone()[0]
    return cache[key]


def laden(conn=None) -> None:
    own = conn is None
    conn = conn or connect()
    cfg = lade_lokale_config()
    buchungen = verarbeiten(einlesen(), cfg)
    eingefuegt = uebersprungen = 0
    ukat_cache: dict = {}
    try:
        with conn.cursor() as cur:
            konten, kategorien = _lade_maps(cur)
            for b in buchungen:
                konto_id = _konto_id(cur, konten, b["konto"])
                kat_id = ukat_id = None
                if b["buchungsart"] == "real" and b.get("kategorie"):
                    kat_id = _kategorie_id(cur, kategorien, b["kategorie"])
                    ukat_id = _unterkategorie_id(cur, ukat_cache, kat_id, b.get("unterkategorie"))
                cur.execute(
                    "INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, konto_id, "
                    "kategorie_id, unterkategorie_id, empfaenger, verwendungszweck, quelle_import, import_hash) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (import_hash) DO NOTHING",
                    (b["buchungsart"], b["datum"], b["betrag_cent"], konto_id, kat_id, ukat_id,
                     b["empfaenger"], b["verwendungszweck"], b["quelle"], b["import_hash"]),
                )
                if cur.rowcount:
                    eingefuegt += 1
                else:
                    uebersprungen += 1
        conn.commit()
        print(f"[laden] eingefügt: {eingefuegt} | übersprungen (schon vorhanden): {uebersprungen}")
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    laden()
    from ..storage.db import kennzahlen
    print(f"[laden] Kennzahlen: {kennzahlen()}")
