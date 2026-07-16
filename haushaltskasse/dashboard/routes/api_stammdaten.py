"""JSON-API für Stammdaten: Soll-Beträge, Rollen, Unterkategorien, Einstellungen."""
from __future__ import annotations

import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..helpers import db, parse_euro

router = APIRouter()


@router.get("/api/unterkategorien/{kategorie_id}")
def api_unterkategorien(kategorie_id: int):
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM unterkategorien WHERE kategorie_id=%s ORDER BY name", (kategorie_id,))
        return [{"id": i, "name": n} for i, n in cur.fetchall()]


class Betrag(BaseModel):
    betrag: str      # Euro-Eingabe, z. B. "240" oder "240,50"


@router.post("/api/kategorie/{kategorie_id}/ruecklage")
def set_kat_ruecklage(kategorie_id: int, b: Betrag):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET monatliche_ruecklage_cent=%s WHERE id=%s",
                    (parse_euro(b.betrag), kategorie_id))
    return {"ok": True, "cent": parse_euro(b.betrag)}


@router.post("/api/unterkategorie/{unterkategorie_id}/ruecklage")
def set_ukat_ruecklage(unterkategorie_id: int, b: Betrag):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE unterkategorien SET monatliche_ruecklage_cent=%s WHERE id=%s",
                    (parse_euro(b.betrag), unterkategorie_id))
    return {"ok": True, "cent": parse_euro(b.betrag)}


class Wert(BaseModel):
    wert: str


@router.post("/api/einstellung/stichtag")
def set_stichtag(w: Wert):
    """#26 — Start-Abgrenzungsdatum setzen (ISO 'YYYY-MM-DD')."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", w.wert.strip()):
        return JSONResponse({"ok": False, "fehler": "Datum als JJJJ-MM-TT"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO einstellungen (schluessel, wert) VALUES ('stichtag', %s)
                       ON CONFLICT (schluessel) DO UPDATE SET wert=EXCLUDED.wert""", (w.wert.strip(),))
    return {"ok": True, "wert": w.wert.strip()}


class Rolle(BaseModel):
    zaehlt_als: str    # 'ruecklage' | 'forderung' | 'ausgabe'


@router.post("/api/kategorie/{kategorie_id}/rolle")
def set_kat_rolle(kategorie_id: int, r: Rolle):
    if r.zaehlt_als not in ("ruecklage", "forderung", "ausgabe"):
        return JSONResponse({"ok": False, "fehler": "ungültige Rolle"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET zaehlt_als=%s WHERE id=%s", (r.zaehlt_als, kategorie_id))
    return {"ok": True}


class DefaultUkat(BaseModel):
    unterkategorie_id: int | None = None


@router.post("/api/kategorie/{kategorie_id}/default_ukat")
def set_kat_default_ukat(kategorie_id: int, d: DefaultUkat):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET default_unterkategorie_id=%s WHERE id=%s",
                    (d.unterkategorie_id, kategorie_id))
    return {"ok": True}


class UkatName(BaseModel):
    name: str


@router.post("/api/unterkategorie/{unterkategorie_id}/rename")
def rename_unterkategorie(unterkategorie_id: int, u: UkatName):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE unterkategorien SET name=%s WHERE id=%s", (u.name.strip(), unterkategorie_id))
    return {"ok": True}


@router.post("/api/unterkategorie/{unterkategorie_id}/delete")
def delete_unterkategorie(unterkategorie_id: int):
    with db() as conn, conn.cursor() as cur:
        # Referenzen lösen, dann löschen (kein FK-Konflikt).
        cur.execute("UPDATE buchungen SET unterkategorie_id=NULL WHERE unterkategorie_id=%s", (unterkategorie_id,))
        cur.execute("UPDATE kategorien SET default_unterkategorie_id=NULL WHERE default_unterkategorie_id=%s", (unterkategorie_id,))
        cur.execute("UPDATE mapping_regeln SET unterkategorie_id=NULL WHERE unterkategorie_id=%s", (unterkategorie_id,))
        cur.execute("DELETE FROM unterkategorien WHERE id=%s", (unterkategorie_id,))
    return {"ok": True}


class NeueUnterkategorie(BaseModel):
    kategorie_id: int
    name: str


@router.post("/api/unterkategorie")
def neue_unterkategorie(nu: NeueUnterkategorie):
    with db() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO unterkategorien (kategorie_id, name, quelle) VALUES (%s,%s,'manuell')
                       ON CONFLICT (kategorie_id, name) DO NOTHING RETURNING id""",
                    (nu.kategorie_id, nu.name.strip()))
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s",
                        (nu.kategorie_id, nu.name.strip()))
            row = cur.fetchone()
    return {"ok": True, "id": row[0]}
