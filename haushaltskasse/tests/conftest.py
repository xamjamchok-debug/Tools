"""Fixtures für die Haushaltskasse-Tests (#23b).

Zwei DB-Rollen:
  * HAUSHALT_TEST_DATABASE_URL  — Wegwerf-DB für SCHREIBENDE Szenario-Tests. Wird je
    Testlauf komplett geleert und mit Minimal-Stammdaten neu aufgebaut. NIEMALS die
    Produktions-DSN hier eintragen! Fehlt die Variable, werden die Szenario-Tests geskippt.
    Lokal: eigene Datenbank `haushaltskasse_test` auf demselben Server. CI: Service-Container.
  * HAUSHALT_DATABASE_URL — nur für die read-only-Invarianten/Smoke-Tests (gefahrlos).
"""
from __future__ import annotations

import os

import psycopg
import pytest

TEST_DSN = os.getenv("HAUSHALT_TEST_DATABASE_URL", "")

# Sicherheitsnetz: die Test-DB muss "test" im Namen tragen — schützt davor, versehentlich
# die Produktions-DSN einzutragen (die Fixtures LÖSCHEN alle Tabellen!).
if TEST_DSN and "test" not in TEST_DSN.rsplit("/", 1)[-1].split("?")[0].lower():
    raise RuntimeError("HAUSHALT_TEST_DATABASE_URL zeigt nicht auf eine *test*-Datenbank — Abbruch.")

TABELLEN = ("admin_laeufe", "import_dateien", "mapping_regeln", "buchungen",
            "vermoegensposten", "einstellungen", "unterkategorien", "kategorien", "konten")


def _frisches_schema(conn) -> None:
    from haushaltskasse.storage.db import init_db
    with conn.cursor() as cur:
        for t in TABELLEN:
            cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    conn.commit()
    init_db(conn)


def _seed_minimal(conn) -> None:
    """Minimal-Stammdaten: 2 Konten, je Rolle 1 Kategorie (+Unterkategorien), 1 Posten je Gruppe."""
    with conn.cursor() as cur:
        cur.execute("INSERT INTO konten (name, typ) VALUES ('Giro','giro'), ('Tagesgeld','tagesgeld')")
        cur.execute("""INSERT INTO kategorien (name, zaehlt_als, monatliche_ruecklage_cent)
                       VALUES ('Auto','ruecklage',20000), ('Joerg','forderung',600000),
                              ('Einnahmen','ausgabe',0)""")
        cur.execute("SELECT id FROM kategorien WHERE name='Auto'")
        auto = cur.fetchone()[0]
        cur.execute("INSERT INTO unterkategorien (kategorie_id, name) VALUES (%s,'Tanken'), (%s,'Allgemein')",
                    (auto, auto))
        cur.execute("""INSERT INTO vermoegensposten (name, wert_cent, art, im_haushaltssaldo, gruppe)
                       VALUES ('ETF', 700000, 'vermoegen', TRUE, 'posten'),
                              ('Urlaubs-Merker', -50000, 'schuld', TRUE, 'merkzettel'),
                              ('Kredit', -1000000, 'schuld', FALSE, 'posten')""")
    conn.commit()


@pytest.fixture(scope="session", autouse=True)
def _schema_falls_leer():
    """CI-Bootstrap: zeigt HAUSHALT_DATABASE_URL auf einen leeren Service-Container,
    wird das Schema angelegt. Auf einer bestehenden DB (Tabellen da) passiert NICHTS."""
    from haushaltskasse.storage.db import connect, init_db
    try:
        conn = connect()
    except Exception:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.buchungen')")
            fehlt = cur.fetchone()[0] is None
        if fehlt:
            init_db(conn)
    finally:
        conn.close()


@pytest.fixture()
def test_db():
    """Frische Wegwerf-DB mit Minimal-Stammdaten (schreibende Szenario-Tests)."""
    if not TEST_DSN:
        pytest.skip("HAUSHALT_TEST_DATABASE_URL nicht gesetzt — Szenario-Tests übersprungen")
    conn = psycopg.connect(TEST_DSN)
    _frisches_schema(conn)
    _seed_minimal(conn)
    yield conn
    conn.close()


@pytest.fixture()
def live_cur():
    """Read-only-Cursor auf die per HAUSHALT_DATABASE_URL verbundene DB (Invarianten/Smoke).
    Die Transaktion wird am Ende IMMER zurückgerollt."""
    from haushaltskasse.storage.db import connect
    try:
        conn = connect()
    except Exception as e:  # keine DB konfiguriert -> skippen statt scheitern
        pytest.skip(f"HAUSHALT_DATABASE_URL nicht nutzbar: {e}")
    cur = conn.cursor()
    yield cur
    conn.rollback()
    conn.close()
