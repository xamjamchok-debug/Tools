"""#60 — Geldlogik-Modul: Vorzeichen-/Rollen-Regeln als Single Source of Truth.

Vorher interpretierten ≥9 Stellen die vier String-Welten (`buchungsart`, `zaehlt_als`,
`im_haushaltssaldo`/`gruppe`, `quelle_import`) unabhängig — so entstand Bug #59 (Web-Import
ohne Spiegel). Dieses Modul definiert:

  * die Konstanten (statt Streu-String-Literalen),
  * die Spiegel-Berechtigungs-Regel als EIN SQL-Fragment (`SQL_SPIEGEL_BERECHTIGT`),
  * die Haushalts-Saldo-Formel genau EINMAL (`haushaltssaldo()`),
  * die Konsistenz-Invarianten (`pruefe_invarianten()`) für Tests UND Workflow-Abschlüsse.

Regeln (fachlich, s. docs/CODE-ANALYSE-DEEP-DIVE-I.md):
  Saldo = Σ reale Konten + Σ Posten(im_haushaltssaldo) − Σ Rücklagen-Töpfe + Σ Forderungen.
  Eine topf-gedeckte Realausgabe ist saldo-neutral, weil ihr eine Spiegel-Gegenbuchung
  (Verzehr) gegenübersteht. Berechtigt für einen Spiegel ist jede Realbuchung, die NICHT aus
  den FB-Migrations-Quellen stammt, deren Kategorie die Rolle 'ruecklage' hat und die nicht
  als kreditfinanziert markiert ist.

Dieses Modul darf NUR von storage abhängen (keine dashboard-/workflows-Importe) — sonst Zirkel.
"""
from __future__ import annotations

# --- Buchungsarten (buchungen.buchungsart) ----------------------------------
ART_REAL = "real"                # Konto + Kategorie -> ändert Realsaldo
ART_RUECKLAGE = "ruecklage"      # nur Kategorie (virtuell): Zuführung/Verzehr
ART_UMBUCHUNG = "umbuchung"      # Konto + Gegenkonto, netto 0, keine Ausgabe
ART_WERTPAPIER = "wertpapier"    # Depot-Bewegung, keine Haushaltsausgabe
ART_ZINSEN = "zinsen"            # Kontoabschluss

# --- Kategorie-Rollen (kategorien.zaehlt_als) --------------------------------
ROLLE_RUECKLAGE = "ruecklage"    # Topf, wird vom Saldo ABGEZOGEN
ROLLE_FORDERUNG = "forderung"    # Person schuldet der Kasse, wird ADDIERT
ROLLE_AUSGABE = "ausgabe"        # reine Ausgaben-Kategorie ohne Topf

# --- Import-Quellen (buchungen.quelle_import) --------------------------------
QUELLE_STARTSALDO = "startsaldo"
QUELLE_SPIEGEL = "spiegel"
QUELLE_VERTEILUNG = "verteilung"
QUELLE_MANUELL = "manuell"
FB_QUELLEN = ("fb-dkb", "fb-kto", QUELLE_STARTSALDO)   # haben ihre Gegenbuchungen schon
KREDITFINANZIERT_PREFIX = "kreditfinanziert"

# --- DIE Spiegel-Berechtigungs-Regel (ein Fragment, drei Verwender) ----------
# Erwartet die Aliase b (buchungen) + k (kategorien, gejoint) und EINEN Parameter:
# list(FB_QUELLEN). Verwendet von gegenbuchung.sync_* und den Invarianten/Tests.
SQL_SPIEGEL_BERECHTIGT = """b.buchungsart='real' AND b.quelle_import <> ALL(%s)
          AND k.zaehlt_als='ruecklage'
          AND COALESCE(b.bemerkung,'') NOT ILIKE 'kreditfinanziert%%'"""


# ---------------------------------------------------------------------------
# Saldo-Komponenten (jede genau einmal definiert)
# ---------------------------------------------------------------------------
def summe_konten(cur, bis: str | None = None) -> int:
    """Σ aller Buchungen auf realen Konten (inkl. Startsaldo/Umbuchung/Wertpapier/Zinsen —
    das ist das tatsächlich liegende Geld). Optional stichtaggenau (datum_wert <= bis)."""
    if bis:
        cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen "
                    "WHERE konto_id IS NOT NULL AND datum_wert<=%s", (bis,))
    else:
        cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE konto_id IS NOT NULL")
    return cur.fetchone()[0]


def _summe_rolle(cur, rolle: str, bis: str | None = None) -> int:
    sql = """SELECT COALESCE(SUM(b.betrag_cent),0) FROM buchungen b
             JOIN kategorien k ON k.id=b.kategorie_id
             WHERE b.buchungsart='ruecklage' AND k.zaehlt_als=%s"""
    params: list = [rolle]
    if bis:
        sql += " AND b.datum_wert<=%s"
        params.append(bis)
    cur.execute(sql, params)
    return cur.fetchone()[0]


def summe_ruecklagen(cur, bis: str | None = None) -> int:
    """Σ der Rücklagen-Töpfe (nur Rolle 'ruecklage' — Forderungen zählen hier NICHT)."""
    return _summe_rolle(cur, ROLLE_RUECKLAGE, bis)


def summe_forderungen(cur, bis: str | None = None) -> int:
    """Σ der Forderungs-Töpfe (Natalie/Jörg)."""
    return _summe_rolle(cur, ROLLE_FORDERUNG, bis)


def summe_posten_im_saldo(cur) -> int:
    """Σ aktiver Vermögensposten im Haushaltssaldo (zeitlos — Posten haben keine Historie)."""
    cur.execute("SELECT COALESCE(SUM(wert_cent),0) FROM vermoegensposten WHERE aktiv AND im_haushaltssaldo")
    return cur.fetchone()[0]


def summe_langfrist(cur) -> int:
    cur.execute("SELECT COALESCE(SUM(wert_cent),0) FROM vermoegensposten WHERE aktiv AND NOT im_haushaltssaldo")
    return cur.fetchone()[0]


def haushaltssaldo(cur, stichtag: str | None = None) -> dict:
    """DIE Saldo-Formel (einzige Definition):
        Saldo = Konten + Posten(im_saldo) − Rücklagen + Forderungen.
    Ohne `stichtag` über alle Buchungen (KPI-Sicht inkl. vordatiertem Monatsplan, s. #52);
    mit `stichtag` buchungsseitig exakt bis dahin (Posten bleiben zeitlos-konstant)."""
    konten = summe_konten(cur, stichtag)
    posten = summe_posten_im_saldo(cur)
    ruecklagen = summe_ruecklagen(cur, stichtag)
    forderung = summe_forderungen(cur, stichtag)
    d = {
        "konten_cent": konten, "posten_cent": posten,
        "ruecklagen_cent": ruecklagen, "forderung_cent": forderung,
        "saldo_cent": konten + posten - ruecklagen + forderung,
        "realsaldo_cent": konten,
        "langfrist_cent": summe_langfrist(cur),
    }
    if stichtag:
        d["datum"] = stichtag
    return d


# ---------------------------------------------------------------------------
# Invarianten — die Regeln, die IMMER gelten müssen (Tests + Workflow-Abschluss)
# ---------------------------------------------------------------------------
def pruefe_invarianten(cur) -> list[str]:
    """Prüft die Konsistenz-Invarianten der Geld-Logik. Rückgabe: Liste der Verletzungen
    (leer = alles konsistent). Read-only. Quelle der Regeln: Deep Dive I + Fable-Review."""
    befunde: list[str] = []

    # 1. Posten-Aufteilung: Σ Merkzettel + Σ übrige Posten(im_saldo) == Σ Posten(im_saldo)
    cur.execute("SELECT COALESCE(SUM(wert_cent),0) FROM vermoegensposten WHERE aktiv AND gruppe='merkzettel'")
    mz = cur.fetchone()[0]
    cur.execute("""SELECT COALESCE(SUM(wert_cent),0) FROM vermoegensposten
                   WHERE aktiv AND im_haushaltssaldo AND gruppe<>'merkzettel'""")
    ps = cur.fetchone()[0]
    gesamt = summe_posten_im_saldo(cur)
    if mz + ps != gesamt:
        befunde.append(f"Wasserfall-Drift: Merkzettel {mz} + Posten {ps} != im_saldo {gesamt}")

    # 2. Jeder Merkzettel-Posten zählt im Saldo (sonst kippt die Herleitung lautlos)
    cur.execute("SELECT COUNT(*) FROM vermoegensposten WHERE aktiv AND gruppe='merkzettel' AND NOT im_haushaltssaldo")
    n = cur.fetchone()[0]
    if n:
        befunde.append(f"{n} Merkzettel-Posten mit im_haushaltssaldo=FALSE")

    # 3. Spiegel-Integrität: keine verwaisten, keine doppelten
    cur.execute("""SELECT COUNT(*) FROM buchungen s WHERE s.spiegel_von_id IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM buchungen b WHERE b.id=s.spiegel_von_id)""")
    n = cur.fetchone()[0]
    if n:
        befunde.append(f"{n} verwaiste Spiegel-Buchungen")
    cur.execute("""SELECT COUNT(*) FROM (SELECT spiegel_von_id FROM buchungen
                   WHERE spiegel_von_id IS NOT NULL GROUP BY spiegel_von_id HAVING COUNT(*)>1) x""")
    n = cur.fetchone()[0]
    if n:
        befunde.append(f"{n} Realbuchungen mit doppeltem Spiegel")

    # 4. Spiegel-Vollständigkeit: jede berechtigte Realbuchung hat genau einen Spiegel
    #    (genau die Lücke aus Bug #59 — Web-Import ohne Sync)
    cur.execute(f"""SELECT COUNT(*), COALESCE(SUM(b.betrag_cent),0) FROM buchungen b
                    JOIN kategorien k ON k.id=b.kategorie_id
                    WHERE {SQL_SPIEGEL_BERECHTIGT}
                      AND NOT EXISTS (SELECT 1 FROM buchungen s WHERE s.spiegel_von_id=b.id)""",
                (list(FB_QUELLEN),))
    n, s = cur.fetchone()
    if n:
        befunde.append(f"{n} berechtigte Realbuchungen OHNE Spiegel (Summe {s/100:,.2f} €)")

    # 5. Spiegel-Summe == Summe der berechtigten Realbuchungen
    cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE quelle_import='spiegel'")
    sp = cur.fetchone()[0]
    cur.execute(f"""SELECT COALESCE(SUM(b.betrag_cent),0) FROM buchungen b
                    JOIN kategorien k ON k.id=b.kategorie_id
                    WHERE {SQL_SPIEGEL_BERECHTIGT}""", (list(FB_QUELLEN),))
    ber = cur.fetchone()[0]
    if sp != ber:
        befunde.append(f"Σ Spiegel {sp/100:,.2f} != Σ berechtigte Realbuchungen {ber/100:,.2f}")

    # 6. Keine pathologischen Zeilen
    for beschreibung, sql in (
        ("ruecklage-Buchungen MIT Konto", "SELECT COUNT(*) FROM buchungen WHERE buchungsart='ruecklage' AND konto_id IS NOT NULL"),
        ("umbuchung-Buchungen MIT Kategorie", "SELECT COUNT(*) FROM buchungen WHERE buchungsart='umbuchung' AND kategorie_id IS NOT NULL"),
        ("real-Buchungen OHNE Konto", "SELECT COUNT(*) FROM buchungen WHERE buchungsart='real' AND konto_id IS NULL"),
        ("Buchungen mit Unterkategorie fremder Kategorie",
         """SELECT COUNT(*) FROM buchungen b JOIN unterkategorien u ON u.id=b.unterkategorie_id
            WHERE b.kategorie_id IS NOT NULL AND u.kategorie_id <> b.kategorie_id"""),
    ):
        cur.execute(sql)
        n = cur.fetchone()[0]
        if n:
            befunde.append(f"{n} {beschreibung}")

    return befunde
