"""JSON-API für Verträge (#75): bestätigen, ignorieren, umhängen, Stammdaten pflegen.

Grundregel (User-Entscheid D, 2026-07-17): **„Vertrag erst nach Bestätigung."** Die
Erkennung legt nur Vorschläge an (`status='erkannt'`); erst ein `bestaetigt` hier lässt
einen Vertrag in die Soll-Rechnung eingehen.

Keiner dieser Endpunkte bucht etwas — Rückstellungen entstehen ausschließlich im
monatlichen Rücklagenlauf (User-Entscheid F: Erkennen ≠ Ändern ≠ Buchen).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..helpers import db, parse_euro

router = APIRouter()

ERLAUBTE_STATUS = {"erkannt", "bestaetigt", "beendet", "ignoriert"}
ERLAUBTE_RHYTHMEN = {"monatlich", "quartalsweise", "halbjaehrlich", "jaehrlich", "unregelmaessig"}


class StatusWechsel(BaseModel):
    status: str


@router.post("/api/vertrag/{vertrag_id}/status")
def api_status(vertrag_id: int, body: StatusWechsel):
    if body.status not in ERLAUBTE_STATUS:
        return JSONResponse({"ok": False, "fehler": "unbekannter Status"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vertraege SET status=%s WHERE id=%s", (body.status, vertrag_id))
        if cur.rowcount == 0:
            return JSONResponse({"ok": False, "fehler": "Vertrag nicht gefunden"}, status_code=404)
    return {"ok": True, "status": body.status}


class Feld(BaseModel):
    wert: str


@router.post("/api/vertrag/{vertrag_id}/name")
def api_name(vertrag_id: int, body: Feld):
    name = body.wert.strip()
    if not name:
        return JSONResponse({"ok": False, "fehler": "Name darf nicht leer sein"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vertraege SET name=%s WHERE id=%s", (name[:60], vertrag_id))
    return {"ok": True, "wert": name[:60]}


@router.post("/api/vertrag/{vertrag_id}/beschreibung")
def api_beschreibung(vertrag_id: int, body: Feld):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vertraege SET beschreibung=%s WHERE id=%s",
                    (body.wert.strip()[:200] or None, vertrag_id))
    return {"ok": True, "wert": body.wert.strip()[:200]}


@router.post("/api/vertrag/{vertrag_id}/rhythmus")
def api_rhythmus(vertrag_id: int, body: Feld):
    if body.wert not in ERLAUBTE_RHYTHMEN:
        return JSONResponse({"ok": False, "fehler": "unbekannter Rhythmus"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vertraege SET rhythmus=%s WHERE id=%s", (body.wert, vertrag_id))
    return {"ok": True, "wert": body.wert}


@router.post("/api/vertrag/{vertrag_id}/betrag")
def api_betrag(vertrag_id: int, body: Feld):
    """Gebühr je Fälligkeit (nicht je Monat) — die Monatsrate rechnet die Anzeige."""
    cent = parse_euro(body.wert)
    if cent is None:
        return JSONResponse({"ok": False, "fehler": "Betrag nicht lesbar"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vertraege SET betrag_median_cent=%s WHERE id=%s", (abs(cent), vertrag_id))
    return {"ok": True, "cent": abs(cent)}


class Umhaengen(BaseModel):
    unterkategorie_id: int


@router.post("/api/vertrag/{vertrag_id}/unterkategorie")
def api_unterkategorie(vertrag_id: int, body: Umhaengen):
    """Vertrag auf eine andere Unterkategorie umhängen = **bündeln**.

    Mehrere Verträge auf derselben Unterkategorie teilen sich einen Topf — genau so
    überlebt „Strom" den Anbieterwechsel (MAINGAU/Naturwerke/Tibber → ein Topf).
    """
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM unterkategorien WHERE id=%s", (body.unterkategorie_id,))
        if not cur.fetchone():
            return JSONResponse({"ok": False, "fehler": "Unterkategorie unbekannt"}, status_code=400)
        cur.execute("UPDATE vertraege SET unterkategorie_id=%s WHERE id=%s",
                    (body.unterkategorie_id, vertrag_id))
    return {"ok": True}


class Schalter(BaseModel):
    erlaubt: bool


@router.post("/api/nebenbuch/{kategorie_id}/schiefstellung")
def api_schiefstellung(kategorie_id: int, body: Schalter):
    """Schiefstellung je Nebenbuch bewusst erlauben (User 2026-07-17).

    Füchschen: Soll 0, Verträge ~475/Monat, Bestand ~15.000 → „kann gerne abgeknabbert
    werden". Ohne diesen Schalter würde die harte Warnung dort jeden Monat blockieren,
    obwohl alles richtig ist.
    """
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET schiefstellung_erlaubt=%s WHERE id=%s",
                    (body.erlaubt, kategorie_id))
        if cur.rowcount == 0:
            return JSONResponse({"ok": False, "fehler": "Nebenbuch nicht gefunden"}, status_code=404)
    return {"ok": True, "erlaubt": body.erlaubt}
