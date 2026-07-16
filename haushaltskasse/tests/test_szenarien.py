"""Schicht 2 (#23b): schreibende Szenario-Tests gegen die Wegwerf-DB
(HAUSHALT_TEST_DATABASE_URL — NIE Produktion; das Sicherheitsnetz steht im conftest)."""
from __future__ import annotations

import psycopg
import pytest

from haushaltskasse.domain.saldo import haushaltssaldo, pruefe_invarianten, summe_ruecklagen
from haushaltskasse.workflows.gegenbuchung import sync_eine, sync_gegenbuchungen

# Synthetisches DKB-CSV (Format wie echter Export): eine Tankstellen-Ausgabe −50,00 €.
# STARTER_RULES ordnen "Aral" -> Auto/Tanken zu; "Auto" hat im Seed die Rolle 'ruecklage'.
DKB_CSV = (
    '"Girokonto";"Testauszug"\n'
    '\n'
    '"Buchungsdatum";"Wertstellung";"Status";"Zahlungspflichtige*r";"Zahlungsempfänger*in";'
    '"Verwendungszweck";"Umsatztyp";"IBAN";"Betrag (€)";"Gläubiger-ID";"Mandatsreferenz";"Kundenreferenz"\n'
    '"10.07.2026";"10.07.2026";"Gebucht";"Max Muster";"Aral Tankstelle Bonn";"Tanken";"Ausgang";'
    '"DE99123412341234123499";"-50,00";"";"";"tref-1"\n'
).encode("utf-8")


def _saldo(conn) -> dict:
    with conn.cursor() as cur:
        return haushaltssaldo(cur)


def _befunde(conn) -> list[str]:
    with conn.cursor() as cur:
        return pruefe_invarianten(cur)


# ---------------------------------------------------------------------------
# #59 End-to-End: Web-Import erzeugt den Spiegel SOFORT (der Bug, den Fable fand)
# ---------------------------------------------------------------------------
def test_import_erzeugt_spiegel_sofort(test_db):
    from haushaltskasse.workflows.web_import import importiere_upload

    vorher = _saldo(test_db)
    bericht = importiere_upload("dkb-test.csv", DKB_CSV, conn=test_db)
    assert bericht["eingefuegt"] == 1, bericht

    with test_db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buchungen WHERE quelle_import='spiegel'")
        assert cur.fetchone()[0] == 1, "Import muss die Spiegel-Gegenbuchung sofort anlegen (#59)"
    # Topf-gedeckte Ausgabe ist saldo-NEUTRAL: Konten −50, Rücklagen −50 -> Saldo unverändert.
    nachher = _saldo(test_db)
    assert nachher["saldo_cent"] == vorher["saldo_cent"]
    assert nachher["konten_cent"] == vorher["konten_cent"] - 5000
    assert _befunde(test_db) == []


def test_import_ist_idempotent(test_db):
    from haushaltskasse.workflows.web_import import importiere_upload
    importiere_upload("dkb-test.csv", DKB_CSV, conn=test_db)
    bericht2 = importiere_upload("dkb-test.csv", DKB_CSV, conn=test_db)
    assert bericht2["eingefuegt"] == 0 and bericht2["uebersprungen"] == 1
    with test_db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buchungen WHERE quelle_import='spiegel'")
        assert cur.fetchone()[0] == 1
    assert _befunde(test_db) == []


# ---------------------------------------------------------------------------
# Umkategorisieren: der Spiegel folgt der Kategorie (genau EINER, nie zwei)
# ---------------------------------------------------------------------------
def _lege_realbuchung(conn, kategorie: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM kategorien WHERE name=%s", (kategorie,))
        kat_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM konten WHERE name='Giro'")
        konto_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, konto_id,
                       kategorie_id, empfaenger, quelle_import, import_hash)
                       VALUES ('real','2026-07-01',-12345,%s,%s,'Testempfänger','dkb','t-umkat-1')
                       RETURNING id""", (konto_id, kat_id))
        return cur.fetchone()[0]


def _spiegel_von(conn, bid: int) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute("""SELECT b.betrag_cent, k.name FROM buchungen b
                       JOIN kategorien k ON k.id=b.kategorie_id
                       WHERE b.spiegel_von_id=%s""", (bid,))
        return cur.fetchall()


def test_umkategorisieren_spiegel_wandert(test_db):
    bid = _lege_realbuchung(test_db, "Auto")
    with test_db.cursor() as cur:
        sync_eine(cur, bid)
    assert _spiegel_von(test_db, bid) == [(-12345, "Auto")]

    # Ziel Nicht-Topf ('ausgabe'): Spiegel verschwindet.
    with test_db.cursor() as cur:
        cur.execute("UPDATE buchungen SET kategorie_id=(SELECT id FROM kategorien WHERE name='Einnahmen') WHERE id=%s", (bid,))
        sync_eine(cur, bid)
    assert _spiegel_von(test_db, bid) == []

    # Zurück auf Topf: genau EIN Spiegel, nie zwei (verifizierter Fakt aus dem Delta).
    with test_db.cursor() as cur:
        cur.execute("UPDATE buchungen SET kategorie_id=(SELECT id FROM kategorien WHERE name='Auto') WHERE id=%s", (bid,))
        sync_eine(cur, bid)
    assert _spiegel_von(test_db, bid) == [(-12345, "Auto")]
    assert _befunde(test_db) == []


def test_sync_gegenbuchungen_idempotent(test_db):
    _lege_realbuchung(test_db, "Auto")
    with test_db.cursor() as cur:
        s1 = sync_gegenbuchungen(cur)
        s2 = sync_gegenbuchungen(cur)
    assert s1["quellen"] == s2["quellen"] == 1
    assert s2["geloescht"] == 0
    assert _befunde(test_db) == []


# ---------------------------------------------------------------------------
# Rollen & Constraints
# ---------------------------------------------------------------------------
def test_forderung_zaehlt_nicht_als_ruecklage(test_db):
    """Fable-Review B7: die Rücklagen-Summe darf Forderungen (Natalie/Jörg) nicht enthalten."""
    with test_db.cursor() as cur:
        cur.execute("""INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, kategorie_id)
                       SELECT 'ruecklage','2026-07-01',600000,id FROM kategorien WHERE name='Joerg'""")
        cur.execute("""INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, kategorie_id)
                       SELECT 'ruecklage','2026-07-01',10000,id FROM kategorien WHERE name='Auto'""")
        assert summe_ruecklagen(cur) == 10000          # nur Auto, nicht Joerg
        s = haushaltssaldo(cur)
        assert s["forderung_cent"] == 600000
        assert s["saldo_cent"] == s["konten_cent"] + s["posten_cent"] - 10000 + 600000


def test_merkzettel_muss_im_saldo_zaehlen(test_db):
    """#60: der CHECK-Constraint macht die latente Falle (Deep-Dive-I-Befund C) hart."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with test_db.cursor() as cur:
            cur.execute("""INSERT INTO vermoegensposten (name, wert_cent, im_haushaltssaldo, gruppe)
                           VALUES ('Falle', -100, FALSE, 'merkzettel')""")
    test_db.rollback()
