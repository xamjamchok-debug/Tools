"""Read-Aggregationen fürs Dashboard. Alle Funktionen nehmen einen offenen Cursor `cur`
(die App öffnet eine Verbindung pro Request). Beträge werden in Cent geführt (BIGINT),
die Formatierung nach Euro passiert in den Templates.
"""
from __future__ import annotations

from datetime import date

STICHTAG = "2025-01-01"   # erster Tag der Einzelbuchungs-Historie (davor: Startsaldo)


# ---------------------------------------------------------------------------
# Kennzahlen & Übersicht (Vermögensbilanz, Layout am FB-„Übersicht"-Blatt)
# ---------------------------------------------------------------------------
def kennzahlen(cur) -> dict:
    """Realsaldo (alles auf Konten), Rücklagen-Summe, verfügbar."""
    cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE konto_id IS NOT NULL")
    real = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE buchungsart='ruecklage'")
    rueck = cur.fetchone()[0]
    return {"real_cent": real, "ruecklagen_cent": rueck, "verfuegbar_cent": real - rueck}


def haushaltssaldo(cur) -> dict:
    """Freier Haushalts-Saldo (die FB-„Übersicht"-Zahl, Ziel ≈ −14.579 vor Amazon).

        Saldo = Σ reale Konten
              + Σ Posten mit im_haushaltssaldo (ETF, Merkzettel, Großeltern-geparkt, …)
              + Σ Forderungs-Töpfe (Natalie/Jörg, zaehlt_als='forderung')
              − Σ Rücklagen-Töpfe (zaehlt_als='ruecklage')

    Langfristige Posten (Kredit Großeltern −135.000, Riester, KfW, Deutsche Bank) stehen
    getrennt und zählen NICHT im Saldo. Reserve-/Forderungs-Stände sind Netto (inkl.
    Auto-Gegenbuchungen der Realausgaben) -> topf-verzehrende Ausgaben sind saldo-neutral.
    """
    cur.execute("SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen WHERE konto_id IS NOT NULL")
    konten = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(wert_cent),0) FROM vermoegensposten WHERE aktiv AND im_haushaltssaldo")
    posten = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(wert_cent),0) FROM vermoegensposten WHERE aktiv AND NOT im_haushaltssaldo")
    langfrist = cur.fetchone()[0]
    cur.execute("""SELECT COALESCE(SUM(b.betrag_cent),0) FROM buchungen b
                   JOIN kategorien k ON k.id=b.kategorie_id
                   WHERE b.buchungsart='ruecklage' AND k.zaehlt_als='ruecklage'""")
    ruecklagen = cur.fetchone()[0]
    cur.execute("""SELECT COALESCE(SUM(b.betrag_cent),0) FROM buchungen b
                   JOIN kategorien k ON k.id=b.kategorie_id
                   WHERE b.buchungsart='ruecklage' AND k.zaehlt_als='forderung'""")
    forderung = cur.fetchone()[0]
    return {
        "konten_cent": konten, "posten_cent": posten, "langfrist_cent": langfrist,
        "ruecklagen_cent": ruecklagen, "forderung_cent": forderung,
        "saldo_cent": konten + posten - ruecklagen + forderung,
    }


def konten_salden(cur) -> list[dict]:
    """Echtes Kontovermögen je reales Konto (Summe aller Bewegungen inkl. Startsaldo)."""
    cur.execute("""
        SELECT k.name, k.typ, COALESCE(SUM(b.betrag_cent),0) AS saldo
        FROM konten k LEFT JOIN buchungen b ON b.konto_id = k.id
        GROUP BY k.id, k.name, k.typ
        ORDER BY saldo DESC
    """)
    return [{"name": n, "typ": t, "saldo_cent": s} for n, t, s in cur.fetchall()]


def vermoegensposten(cur) -> list[dict]:
    cur.execute("""
        SELECT id, name, wert_cent, art, sortierung, notiz
        FROM vermoegensposten WHERE aktiv ORDER BY sortierung, name
    """)
    return [{"id": i, "name": n, "wert_cent": w, "art": a, "sortierung": s, "notiz": z}
            for i, n, w, a, s, z in cur.fetchall()]


def uebersicht(cur) -> dict:
    """Alles fürs Übersichts-Tab, auf Basis des freien Haushalts-Saldos (haushaltssaldo()).

    Blöcke: reale Konten · Rücklagen-Töpfe (aktueller Netto-Stand) · Forderungen
    (Natalie/Jörg) · Posten im Saldo (ETF, Merkzettel, Anlage Großeltern) · langfristige
    Posten (Kredit Großeltern, Riester, KfW, Deutsche Bank — separat, NICHT im Saldo).
    """
    hs = haushaltssaldo(cur)
    konten = konten_salden(cur)

    cur.execute("""SELECT id, name, wert_cent, art, notiz, im_haushaltssaldo
                   FROM vermoegensposten WHERE aktiv ORDER BY im_haushaltssaldo DESC, name""")
    posten_saldo, posten_langfrist = [], []
    for i, n, w, a, z, im in cur.fetchall():
        (posten_saldo if im else posten_langfrist).append(
            {"id": i, "name": n, "wert_cent": w, "art": a, "notiz": z})

    # Töpfe mit aktuellem Netto-Stand (inkl. Auto-Gegenbuchungen), getrennt nach Rolle.
    cur.execute("""
        SELECT k.name, k.zaehlt_als,
               COALESCE((SELECT SUM(b.betrag_cent) FROM buchungen b
                         WHERE b.kategorie_id=k.id AND b.buchungsart='ruecklage'),0) AS ist
        FROM kategorien k
        WHERE k.aktiv AND k.zaehlt_als IN ('ruecklage','forderung')
        ORDER BY k.zaehlt_als, k.name""")
    ruecklagen_toepfe, forderungen = [], []
    for n, za, ist in cur.fetchall():
        (forderungen if za == "forderung" else ruecklagen_toepfe).append(
            {"name": n, "ist_cent": ist})

    return {**hs, "konten": konten,
            "posten_saldo": posten_saldo, "posten_langfrist": posten_langfrist,
            "ruecklagen_toepfe": ruecklagen_toepfe, "forderungen": forderungen}


# ---------------------------------------------------------------------------
# Rücklagen-Baum: Kategorie -> Unterkategorien, je mit Soll und Ist
# ---------------------------------------------------------------------------
def ruecklagen_baum(cur) -> list[dict]:
    """Je Kategorie: Soll (monatlich), Ist-Saldo (aus ruecklage-Buchungen) und die Unterkategorien."""
    cur.execute("""
        SELECT k.id, k.name, k.monatliche_ruecklage_cent,
               COALESCE((SELECT SUM(b.betrag_cent) FROM buchungen b
                         WHERE b.kategorie_id = k.id AND b.buchungsart='ruecklage'), 0) AS ist
        FROM kategorien k WHERE k.aktiv ORDER BY k.name
    """)
    kats = [{"id": i, "name": n, "soll_cent": soll, "ist_cent": ist, "unterkategorien": []}
            for i, n, soll, ist in cur.fetchall()]
    kat_by_id = {k["id"]: k for k in kats}

    cur.execute("""
        SELECT u.id, u.kategorie_id, u.name, u.monatliche_ruecklage_cent,
               COALESCE((SELECT SUM(b.betrag_cent) FROM buchungen b
                         WHERE b.unterkategorie_id = u.id AND b.buchungsart='ruecklage'), 0) AS ist
        FROM unterkategorien u ORDER BY u.name
    """)
    for i, kid, n, soll, ist in cur.fetchall():
        if kid in kat_by_id:
            kat_by_id[kid]["unterkategorien"].append(
                {"id": i, "name": n, "soll_cent": soll, "ist_cent": ist})
    return kats


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def ausgaben_je_kategorie(cur, von: str = STICHTAG, bis: str | None = None) -> list[dict]:
    """Reale Ausgaben/Einnahmen je Kategorie im Zeitraum (Startsaldo ausgeschlossen)."""
    bis = bis or date.today().isoformat()
    cur.execute("""
        SELECT COALESCE(k.name,'(nicht zugeordnet)') AS kat,
               SUM(b.betrag_cent) FILTER (WHERE b.betrag_cent < 0) AS ausgaben,
               SUM(b.betrag_cent) FILTER (WHERE b.betrag_cent > 0) AS einnahmen,
               COUNT(*) AS n
        FROM buchungen b LEFT JOIN kategorien k ON k.id = b.kategorie_id
        WHERE b.buchungsart='real' AND b.quelle_import <> 'startsaldo'
          AND b.datum_wert >= %s AND b.datum_wert <= %s
        GROUP BY 1 ORDER BY COALESCE(SUM(b.betrag_cent) FILTER (WHERE b.betrag_cent < 0),0)
    """, (von, bis))
    return [{"kategorie": k, "ausgaben_cent": a or 0, "einnahmen_cent": e or 0, "n": n}
            for k, a, e, n in cur.fetchall()]


def ausgaben_je_unterkategorie(cur, kategorie: str, von: str = STICHTAG, bis: str | None = None) -> list[dict]:
    bis = bis or date.today().isoformat()
    cur.execute("""
        SELECT COALESCE(u.name,'(ohne Unterkategorie)') AS ukat,
               SUM(b.betrag_cent) AS summe, COUNT(*) AS n
        FROM buchungen b JOIN kategorien k ON k.id = b.kategorie_id
        LEFT JOIN unterkategorien u ON u.id = b.unterkategorie_id
        WHERE b.buchungsart='real' AND b.quelle_import <> 'startsaldo'
          AND k.name = %s AND b.datum_wert >= %s AND b.datum_wert <= %s
        GROUP BY 1 ORDER BY SUM(b.betrag_cent)
    """, (kategorie, von, bis))
    return [{"unterkategorie": u, "summe_cent": s or 0, "n": n} for u, s, n in cur.fetchall()]


def monatsverlauf(cur, von: str = STICHTAG) -> list[dict]:
    """Ausgaben/Einnahmen je Monat (reale Buchungen, ohne Startsaldo)."""
    cur.execute("""
        SELECT to_char(date_trunc('month', b.datum_wert), 'YYYY-MM') AS monat,
               SUM(b.betrag_cent) FILTER (WHERE b.betrag_cent < 0) AS ausgaben,
               SUM(b.betrag_cent) FILTER (WHERE b.betrag_cent > 0) AS einnahmen
        FROM buchungen b
        WHERE b.buchungsart='real' AND b.quelle_import <> 'startsaldo' AND b.datum_wert >= %s
        GROUP BY 1 ORDER BY 1
    """, (von,))
    return [{"monat": m, "ausgaben_cent": a or 0, "einnahmen_cent": e or 0} for m, a, e in cur.fetchall()]


def top_empfaenger(cur, von: str = STICHTAG, limit: int = 20) -> list[dict]:
    cur.execute("""
        SELECT COALESCE(NULLIF(empfaenger,''),'(leer)') AS empf, SUM(betrag_cent) AS summe, COUNT(*) n
        FROM buchungen
        WHERE buchungsart='real' AND betrag_cent < 0 AND quelle_import <> 'startsaldo' AND datum_wert >= %s
        GROUP BY 1 ORDER BY SUM(betrag_cent) LIMIT %s
    """, (von, limit))
    return [{"empfaenger": e, "summe_cent": s, "n": n} for e, s, n in cur.fetchall()]


# ---------------------------------------------------------------------------
# Buchungsliste (filterbar) + Stammdaten für Dropdowns
# ---------------------------------------------------------------------------
def buchungen(cur, konto: str | None = None, kategorie_id: int | None = None,
              nur_offen: bool = False, suche: str | None = None,
              von: str | None = None, bis: str | None = None,
              limit: int = 200, offset: int = 0) -> tuple[list[dict], int]:
    where = ["b.quelle_import <> 'startsaldo'"]
    params: list = []
    if konto:
        where.append("kt.name = %s"); params.append(konto)
    if kategorie_id is not None:
        where.append("b.kategorie_id = %s"); params.append(kategorie_id)
    if nur_offen:
        where.append("b.kategorie_id IS NULL AND b.buchungsart='real'")
    if suche:
        where.append("(b.empfaenger ILIKE %s OR b.verwendungszweck ILIKE %s)")
        params += [f"%{suche}%", f"%{suche}%"]
    if von:
        where.append("b.datum_wert >= %s"); params.append(von)
    if bis:
        where.append("b.datum_wert <= %s"); params.append(bis)
    w = " AND ".join(where)

    cur.execute(f"SELECT COUNT(*) FROM buchungen b LEFT JOIN konten kt ON kt.id=b.konto_id WHERE {w}", params)
    gesamt = cur.fetchone()[0]

    cur.execute(f"""
        SELECT b.id, b.datum_wert, b.betrag_cent, b.buchungsart, kt.name AS konto,
               b.kategorie_id, k.name AS kategorie, b.unterkategorie_id, u.name AS unterkategorie,
               b.empfaenger, b.verwendungszweck, b.kat_pinned
        FROM buchungen b
        LEFT JOIN konten kt ON kt.id = b.konto_id
        LEFT JOIN kategorien k ON k.id = b.kategorie_id
        LEFT JOIN unterkategorien u ON u.id = b.unterkategorie_id
        WHERE {w}
        ORDER BY b.datum_wert DESC, b.id DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    cols = ["id", "datum", "betrag_cent", "buchungsart", "konto", "kategorie_id", "kategorie",
            "unterkategorie_id", "unterkategorie", "empfaenger", "verwendungszweck", "kat_pinned"]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows, gesamt


def config_baum(cur) -> list[dict]:
    """Pflegemaske: alle Nebenbücher mit Rolle (zaehlt_als), Soll, Default-Unterkategorie
    und ihren Unterkategorien (Name + Soll)."""
    cur.execute("""SELECT id, name, zaehlt_als, monatliche_ruecklage_cent, default_unterkategorie_id
                   FROM kategorien WHERE aktiv ORDER BY name""")
    kats = [{"id": i, "name": n, "zaehlt_als": z, "soll_cent": s, "default_ukat_id": d,
             "unterkategorien": []} for i, n, z, s, d in cur.fetchall()]
    by_id = {k["id"]: k for k in kats}
    cur.execute("""SELECT id, kategorie_id, name, monatliche_ruecklage_cent, quelle
                   FROM unterkategorien ORDER BY name""")
    for i, kid, n, s, qu in cur.fetchall():
        if kid in by_id:
            by_id[kid]["unterkategorien"].append(
                {"id": i, "name": n, "soll_cent": s, "quelle": qu})
    return kats


def kategorien_mit_unterkategorien(cur) -> list[dict]:
    """Für die Umkategorisieren-Dropdowns: alle Kategorien mit ihren Unterkategorien."""
    cur.execute("SELECT id, name FROM kategorien WHERE aktiv ORDER BY name")
    kats = [{"id": i, "name": n, "unterkategorien": []} for i, n in cur.fetchall()]
    by_id = {k["id"]: k for k in kats}
    cur.execute("SELECT id, kategorie_id, name FROM unterkategorien ORDER BY name")
    for i, kid, n in cur.fetchall():
        if kid in by_id:
            by_id[kid]["unterkategorien"].append({"id": i, "name": n})
    return kats
