"""JSON-API rund um Buchungen: Umkategorisieren, Bemerkung, manuelle Topf-Bewegungen."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...workflows.gegenbuchung import sync_eine
from ..helpers import db, parse_euro

router = APIRouter()


class Zuordnung(BaseModel):
    kategorie_id: int | None = None
    unterkategorie_id: int | None = None


@router.post("/api/buchung/{buchung_id}/kategorie")
def set_kategorie(buchung_id: int, z: Zuordnung):
    with db() as conn, conn.cursor() as cur:
        ukat = z.unterkategorie_id
        # Keine Unterkategorie gewählt -> Default-Unterkategorie der Kategorie verwenden.
        if ukat is None and z.kategorie_id is not None:
            cur.execute("SELECT default_unterkategorie_id FROM kategorien WHERE id=%s", (z.kategorie_id,))
            row = cur.fetchone()
            if row and row[0]:
                ukat = row[0]
        cur.execute("""
            UPDATE buchungen
            SET kategorie_id=%s, unterkategorie_id=%s,
                kat_pinned=TRUE, unterkat_pinned = (%s IS NOT NULL)
            WHERE id=%s
        """, (z.kategorie_id, ukat, z.unterkategorie_id, buchung_id))
        # Gegenbuchung folgt der neuen Kategorie (alter Spiegel weg, neuer im richtigen Topf).
        sync_eine(cur, buchung_id)
    return {"ok": True}


class Bemerkung(BaseModel):
    bemerkung: str = ""


@router.post("/api/buchung/{buchung_id}/bemerkung")
def set_bemerkung(buchung_id: int, b: Bemerkung):
    with db() as conn, conn.cursor() as cur:
        text = b.bemerkung.strip() or None
        cur.execute("UPDATE buchungen SET bemerkung=%s WHERE id=%s", (text, buchung_id))
    return {"ok": True}


# --- Manuelle Rücklagen-Bewegungen (virtuell, kein reales Konto berührt) -----------
class TopfBuchung(BaseModel):
    kategorie_id: int
    unterkategorie_id: int | None = None
    betrag: str                       # Euro, immer positiv eingegeben
    richtung: str = "ein"             # 'ein' = reservieren (+, senkt freien Saldo) · 'aus' = freigeben (−)
    bemerkung: str = ""


@router.post("/api/topf/buchen")
def topf_buchen(t: TopfBuchung):
    """Rücklage eines Topfs (oder Untertopfs) manuell erhöhen/reduzieren. Reine
    'ruecklage'-Buchung ohne konto_id -> der Realsaldo bleibt gleich, nur der freie
    Haushalts-Saldo verschiebt sich (Einbuchen bindet Geld, Ausbuchen gibt es frei)."""
    cent = abs(parse_euro(t.betrag))
    if cent == 0:
        return JSONResponse({"ok": False, "fehler": "Betrag ist 0"}, status_code=400)
    signed = cent if t.richtung == "ein" else -cent
    notiz = t.bemerkung.strip() or ("Rücklage eingebucht" if signed > 0 else "Rücklage ausgebucht")
    with db() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent,
                                   kategorie_id, unterkategorie_id, quelle_import, bemerkung)
            VALUES ('ruecklage', CURRENT_DATE, %s, %s, %s, 'manuell', %s)
        """, (signed, t.kategorie_id, t.unterkategorie_id, notiz))
    return {"ok": True, "cent": signed}


class Umbuchung(BaseModel):
    von_kategorie_id: int
    nach_kategorie_id: int
    betrag: str
    bemerkung: str = ""


@router.post("/api/topf/umbuchen")
def topf_umbuchen(u: Umbuchung):
    """Betrag zwischen zwei Nebenbüchern umbuchen: zwei gespiegelte 'ruecklage'-Buchungen
    (−X vom Quell-Topf, +X in den Ziel-Topf). Summe der Rücklagen bleibt gleich ->
    der freie Gesamtsaldo ändert sich NICHT, nur die beiden Topf-Salden verschieben sich."""
    cent = abs(parse_euro(u.betrag))
    if cent == 0:
        return JSONResponse({"ok": False, "fehler": "Betrag ist 0"}, status_code=400)
    if u.von_kategorie_id == u.nach_kategorie_id:
        return JSONResponse({"ok": False, "fehler": "Quelle und Ziel sind identisch"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM kategorien WHERE id IN (%s, %s)",
                    (u.von_kategorie_id, u.nach_kategorie_id))
        namen = {i: n for i, n in cur.fetchall()}
        if len(namen) < 2:
            return JSONResponse({"ok": False, "fehler": "Topf nicht gefunden"}, status_code=400)
        von_n, nach_n = namen[u.von_kategorie_id], namen[u.nach_kategorie_id]
        basis = u.bemerkung.strip()
        cur.execute("""INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent,
                       kategorie_id, quelle_import, bemerkung)
                       VALUES ('ruecklage', CURRENT_DATE, %s, %s, 'manuell', %s)""",
                    (-cent, u.von_kategorie_id, basis or f"Umbuchung → {nach_n}"))
        cur.execute("""INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent,
                       kategorie_id, quelle_import, bemerkung)
                       VALUES ('ruecklage', CURRENT_DATE, %s, %s, 'manuell', %s)""",
                    (cent, u.nach_kategorie_id, basis or f"Umbuchung ← {von_n}"))
    return {"ok": True, "cent": cent}
