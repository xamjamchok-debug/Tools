"""FastAPI-Dashboard der Haushaltskasse.

Start:  python -m haushaltskasse.dashboard.app       (Port 3000)
        http://localhost:3000

Vier Tabs: Übersicht · Rücklagen · Buchungen · Reports. Die DB ist die Quelle der Wahrheit;
Umkategorisieren, Rücklagen-Soll und Vermögensposten werden hier direkt bearbeitet.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from ..storage.db import connect
from ..workflows.gegenbuchung import sync_eine
from . import auth
from . import export as xp
from . import queries as q

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app = FastAPI(title="Haushaltskasse")

# Reihenfolge wichtig: SessionMiddleware zuletzt hinzufügen -> läuft ZUERST und füllt
# request.session, bevor die AuthMiddleware sie liest.
app.add_middleware(auth.AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=auth.session_secret(),
                   https_only=auth.https_only(), same_site="lax")


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------
@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _euro(cent) -> str:
    """Cent -> '1.234,56 €' (deutsche Schreibweise)."""
    cent = cent or 0
    s = f"{cent / 100:,.2f}"                       # 1,234.56
    return s.replace(",", "␟").replace(".", ",").replace("␟", ".") + " €"


def _parse_euro(text) -> int:
    """Euro-Eingabe -> Cent (int). Robust für beide Notationen, weil die UI Werte mit
    Punkt-Dezimal anzeigt (`round(2)` -> '72.5'), der Nutzer aber auch deutsch tippt ('72,50').

    '240' -> 24000 · '72.5' -> 7250 · '240,50' -> 24050 · '1.234,56 €' -> 123456 · '1,234.56' -> 123456.
    Regel: der zuletzt stehende '.' oder ',' ist der Dezimaltrenner, alle anderen sind Tausender.
    """
    if text is None:
        return 0
    s = str(text).replace("€", "").replace(" ", "").strip()
    if not s:
        return 0
    neg = s.startswith("-")
    s = s.lstrip("+-")
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_comma > last_dot:            # Komma ist Dezimaltrenner (deutsch): 1.234,56
        s = s.replace(".", "").replace(",", ".")
    else:                                # Punkt ist Dezimaltrenner (englisch/UI): 1,234.56 / 72.5
        s = s.replace(",", "")
    cent = round(float(s) * 100)
    return -cent if neg else cent


def _eurozahl(cent) -> str:
    """Cent -> '1.234,56' — deutsch, aber OHNE €-Zeichen: für editierbare Felder.

    Muss deutsch sein, sonst steht in der Maske '-2775.0' (#6). `_parse_euro` liest beide
    Notationen zurück, der Rundlauf Anzeige -> Eingabe -> Speichern bleibt also heil.
    """
    return _euro(cent).removesuffix(" €")


TEMPLATES.env.filters["euro"] = _euro
TEMPLATES.env.filters["eurozahl"] = _eurozahl


def _stichtag_global() -> str:
    """#26 — Start-Abgrenzungsdatum für Anzeige im Footer (jede Seite)."""
    try:
        with db() as conn, conn.cursor() as cur:
            return q.stichtag(cur)
    except Exception:
        return q.STICHTAG


TEMPLATES.env.globals["stichtag_global"] = _stichtag_global


def _app_version() -> dict:
    """#23 V1a — welcher Stand ist live? Werte setzt der Deploy per Env-Var
    (`--set-env-vars APP_VERSION=$(git rev-parse --short HEAD) APP_BUILD_TIME=...`).
    Container-Revision liefert Azure automatisch als CONTAINER_APP_REVISION."""
    return {
        "version": os.getenv("APP_VERSION", "dev"),
        "build": os.getenv("APP_BUILD_TIME", ""),
        "revision": os.getenv("CONTAINER_APP_REVISION", ""),
    }


TEMPLATES.env.globals["app_version"] = _app_version


# ---------------------------------------------------------------------------
# Auth (P0.1) — Login/Logout/Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, **_app_version()}


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return TEMPLATES.TemplateResponse(
        request, "login.html", {"request": request, "fehler": None, "auth_aktiv": auth.auth_aktiv()})


@app.post("/login")
def login_post(request: Request, username: str = Form(""), password: str = Form("")):
    if auth.passwort_ok(username, password):
        request.session["auth"] = True
        return RedirectResponse("/", status_code=303)
    return TEMPLATES.TemplateResponse(
        request, "login.html",
        {"request": request, "fehler": "Benutzername oder Passwort falsch.", "auth_aktiv": auth.auth_aktiv()},
        status_code=401)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------------------
# Views (GET)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def view_uebersicht(request: Request, stichtag: str = ""):
    import re
    with db() as conn, conn.cursor() as cur:
        u = q.uebersicht(cur)
        st = None
        if stichtag and re.fullmatch(r"\d{4}-\d{2}-\d{2}", stichtag.strip()):
            st = q.haushaltssaldo_per_stichtag(cur, stichtag.strip())
        ctx = {"request": request, "tab": "uebersicht", "u": u, "st": st, "stichtag": stichtag}
    return TEMPLATES.TemplateResponse(request, "uebersicht.html", ctx)


@app.get("/ruecklagen", response_class=HTMLResponse)
def view_ruecklagen(request: Request):
    with db() as conn, conn.cursor() as cur:
        baum = q.ruecklagen_baum(cur)
    soll_summe = sum(k["soll_cent"] for k in baum) + sum(
        u["soll_cent"] for k in baum for u in k["unterkategorien"])
    return TEMPLATES.TemplateResponse(
        request, "ruecklagen.html",
        {"request": request, "tab": "ruecklagen", "baum": baum, "soll_summe_cent": soll_summe})


@app.get("/nebenbuch/{kategorie_id}", response_class=HTMLResponse)
def view_nebenbuch(request: Request, kategorie_id: int, unterkategorie_id: str = "",
                   sort: str = "datum", richtung: str = "desc"):
    uid = int(unterkategorie_id) if unterkategorie_id.isdigit() else None
    if sort not in q.NB_SORT:
        sort = "datum"
    richtung = "asc" if richtung == "asc" else "desc"
    with db() as conn, conn.cursor() as cur:
        nb = q.nebenbuch(cur, kategorie_id, unterkategorie_id=uid, sort=sort, richtung=richtung)
    return TEMPLATES.TemplateResponse(
        request, "nebenbuch.html", {"request": request, "tab": "ruecklagen", "nb": nb})


@app.get("/buchungen", response_class=HTMLResponse)
def view_buchungen(request: Request, konto: str = "", kategorie_id: str = "",
                   unterkategorie_id: str = "", offen: str = "", suche: str = "",
                   von: str = "", bis: str = "", betrag_min: str = "", betrag_max: str = "",
                   alle: str = "", sort: str = "datum", richtung: str = "desc", seite: int = 1):
    limit, offset = 200, (max(seite, 1) - 1) * 200
    kid = int(kategorie_id) if kategorie_id.isdigit() else None
    uid = int(unterkategorie_id) if unterkategorie_id.isdigit() else None
    bmin = _parse_euro(betrag_min) if betrag_min.strip() else None
    bmax = _parse_euro(betrag_max) if betrag_max.strip() else None
    if sort not in q.SORT_SPALTEN:
        sort = "datum"
    richtung = "asc" if richtung == "asc" else "desc"
    with db() as conn, conn.cursor() as cur:
        rows, gesamt, summen = q.buchungen(
            cur, konto=konto or None, kategorie_id=kid, unterkategorie_id=uid,
            nur_offen=(offen == "1"), suche=suche or None, von=von or None, bis=bis or None,
            betrag_min_cent=bmin, betrag_max_cent=bmax, nur_reale_konten=(alle != "1"),
            sort=sort, richtung=richtung, limit=limit, offset=offset)
        kats = q.kategorien_mit_unterkategorien(cur)
        cur.execute("SELECT name FROM konten ORDER BY name")
        konten = [r[0] for r in cur.fetchall()]
    ukats_flat = [{"id": u["id"], "label": f'{k["name"]} / {u["name"]}'}
                  for k in kats for u in k["unterkategorien"]]
    return TEMPLATES.TemplateResponse(request, "buchungen.html", {
        "request": request, "tab": "buchungen", "rows": rows, "gesamt": gesamt, "summen": summen,
        "kats": kats, "konten": konten, "ukats_flat": ukats_flat, "seite": max(seite, 1),
        "sort": sort, "richtung": richtung,
        "f": {"konto": konto, "kategorie_id": kategorie_id, "unterkategorie_id": unterkategorie_id,
              "offen": offen, "suche": suche, "von": von, "bis": bis,
              "betrag_min": betrag_min, "betrag_max": betrag_max, "alle": alle}})


@app.get("/reports", response_class=HTMLResponse)
def view_reports(request: Request, von: str = "", bis: str = "",
                 modus: str = "ausgabe", ebene: str = "kategorie"):
    if modus not in ("ausgabe", "einnahme", "netto"):
        modus = "ausgabe"
    if ebene not in ("kategorie", "unterkategorie"):
        ebene = "kategorie"
    with db() as conn, conn.cursor() as cur:
        von = von or q.stichtag(cur)      # #26: Default-Von aus den Einstellungen
        piv = q.pivot(cur, von=von, bis=bis or None, modus=modus, ebene=ebene)
        top = q.top_empfaenger(cur, von=von)
    return TEMPLATES.TemplateResponse(request, "reports.html", {
        "request": request, "tab": "reports", "piv": piv, "top": top,
        "von": von, "bis": bis, "modus": modus, "ebene": ebene})


@app.get("/config", response_class=HTMLResponse)
def view_config(request: Request):
    with db() as conn, conn.cursor() as cur:
        fluss = q.config_fluss(cur)
        stichtag = q.stichtag(cur)
    return TEMPLATES.TemplateResponse(request, "config.html",
                                      {"request": request, "tab": "config", "fluss": fluss,
                                       "stichtag": stichtag})


@app.get("/import", response_class=HTMLResponse)
def view_import(request: Request):
    return TEMPLATES.TemplateResponse(request, "import.html",
                                      {"request": request, "tab": "import", "bericht": None})


@app.post("/import", response_class=HTMLResponse)
async def do_import(request: Request, datei: UploadFile = File(...)):
    from ..workflows.web_import import importiere_upload
    daten = await datei.read()
    try:
        bericht = importiere_upload(datei.filename or "unbekannt", daten)
    except Exception as e:
        bericht = {"datei": datei.filename, "erkannt": False, "fehler": f"{type(e).__name__}: {e}",
                   "geparst": 0, "eingefuegt": 0, "uebersprungen": 0}
    return TEMPLATES.TemplateResponse(request, "import.html",
                                      {"request": request, "tab": "import", "bericht": bericht})


# ---------------------------------------------------------------------------
# CSV-Export je Sicht (#34/O2). CSV statt xlsx: keine openpyxl-Abhängigkeit, und jede
# Sicht exportiert exakt das, was auf dem Schirm steht (inkl. Filter, Abschnitte, Summen).
# ---------------------------------------------------------------------------
def _heute() -> str:
    from datetime import date
    return date.today().isoformat()


@app.get("/export/uebersicht.csv")
def export_uebersicht():
    with db() as conn, conn.cursor() as cur:
        u = q.uebersicht(cur)
    return xp.antwort(xp.uebersicht_zeilen(u, _heute()), "uebersicht.csv")


@app.get("/export/ruecklagen.csv")
def export_ruecklagen():
    with db() as conn, conn.cursor() as cur:
        baum = q.ruecklagen_baum(cur)
    return xp.antwort(xp.ruecklagen_zeilen(baum, _heute()), "ruecklagen.csv")


@app.get("/export/reports.csv")
def export_reports(von: str = "", bis: str = "", modus: str = "ausgabe",
                   ebene: str = "kategorie"):
    """Gleiche Parameter wie /reports — der Export folgt der eingestellten Pivot-Sicht."""
    if modus not in ("ausgabe", "einnahme", "netto"):
        modus = "ausgabe"
    if ebene not in ("kategorie", "unterkategorie"):
        ebene = "kategorie"
    with db() as conn, conn.cursor() as cur:
        stichtag = q.stichtag(cur)
        p = q.pivot(cur, von=von or stichtag, bis=bis or None, modus=modus, ebene=ebene)
    titel = f"{modus}, je {ebene}"
    return xp.antwort(xp.pivot_zeilen(p, titel, _heute()), "reports.csv")


@app.get("/export/buchungen.csv")
def export_buchungen(konto: str = "", kategorie_id: str = "", unterkategorie_id: str = "",
                     offen: str = "", suche: str = "", von: str = "", bis: str = "",
                     betrag_min: str = "", betrag_max: str = "", alle: str = "",
                     sort: str = "datum", richtung: str = "desc"):
    """Die (gefilterte) Buchungsliste als CSV. Gleiche Filter wie /buchungen."""
    kid = int(kategorie_id) if kategorie_id.isdigit() else None
    uid = int(unterkategorie_id) if unterkategorie_id.isdigit() else None
    bmin = _parse_euro(betrag_min) if betrag_min.strip() else None
    bmax = _parse_euro(betrag_max) if betrag_max.strip() else None
    if sort not in q.SORT_SPALTEN:
        sort = "datum"
    richtung = "asc" if richtung == "asc" else "desc"
    with db() as conn, conn.cursor() as cur:
        rows, gesamt, summen = q.buchungen(
            cur, konto=konto or None, kategorie_id=kid, unterkategorie_id=uid,
            nur_offen=(offen == "1"), suche=suche or None, von=von or None, bis=bis or None,
            betrag_min_cent=bmin, betrag_max_cent=bmax, nur_reale_konten=(alle != "1"),
            sort=sort, richtung=richtung, limit=100000, offset=0)
    return xp.antwort(xp.buchungen_zeilen(rows, gesamt, summen, _heute()), "buchungen.csv")


@app.get("/api/unterkategorien/{kategorie_id}")
def api_unterkategorien(kategorie_id: int):
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM unterkategorien WHERE kategorie_id=%s ORDER BY name", (kategorie_id,))
        return [{"id": i, "name": n} for i, n in cur.fetchall()]


# ---------------------------------------------------------------------------
# Editieren (POST/JSON) — DB ist die Quelle der Wahrheit
# ---------------------------------------------------------------------------
class Zuordnung(BaseModel):
    kategorie_id: int | None = None
    unterkategorie_id: int | None = None


@app.post("/api/buchung/{buchung_id}/kategorie")
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


@app.post("/api/buchung/{buchung_id}/bemerkung")
def set_bemerkung(buchung_id: int, b: Bemerkung):
    with db() as conn, conn.cursor() as cur:
        text = b.bemerkung.strip() or None
        cur.execute("UPDATE buchungen SET bemerkung=%s WHERE id=%s", (text, buchung_id))
    return {"ok": True}


class Betrag(BaseModel):
    betrag: str      # Euro-Eingabe, z. B. "240" oder "240,50"


@app.post("/api/kategorie/{kategorie_id}/ruecklage")
def set_kat_ruecklage(kategorie_id: int, b: Betrag):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET monatliche_ruecklage_cent=%s WHERE id=%s",
                    (_parse_euro(b.betrag), kategorie_id))
    return {"ok": True, "cent": _parse_euro(b.betrag)}


@app.post("/api/unterkategorie/{unterkategorie_id}/ruecklage")
def set_ukat_ruecklage(unterkategorie_id: int, b: Betrag):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE unterkategorien SET monatliche_ruecklage_cent=%s WHERE id=%s",
                    (_parse_euro(b.betrag), unterkategorie_id))
    return {"ok": True, "cent": _parse_euro(b.betrag)}


# --- Manuelle Rücklagen-Bewegungen (virtuell, kein reales Konto berührt) -----------
class TopfBuchung(BaseModel):
    kategorie_id: int
    unterkategorie_id: int | None = None
    betrag: str                       # Euro, immer positiv eingegeben
    richtung: str = "ein"             # 'ein' = reservieren (+, senkt freien Saldo) · 'aus' = freigeben (−)
    bemerkung: str = ""


@app.post("/api/topf/buchen")
def topf_buchen(t: TopfBuchung):
    """Rücklage eines Topfs (oder Untertopfs) manuell erhöhen/reduzieren. Reine
    'ruecklage'-Buchung ohne konto_id -> der Realsaldo bleibt gleich, nur der freie
    Haushalts-Saldo verschiebt sich (Einbuchen bindet Geld, Ausbuchen gibt es frei)."""
    cent = abs(_parse_euro(t.betrag))
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


@app.post("/api/topf/umbuchen")
def topf_umbuchen(u: Umbuchung):
    """Betrag zwischen zwei Nebenbüchern umbuchen: zwei gespiegelte 'ruecklage'-Buchungen
    (−X vom Quell-Topf, +X in den Ziel-Topf). Summe der Rücklagen bleibt gleich ->
    der freie Gesamtsaldo ändert sich NICHT, nur die beiden Topf-Salden verschieben sich."""
    cent = abs(_parse_euro(u.betrag))
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


class Wert(BaseModel):
    wert: str


@app.post("/api/einstellung/stichtag")
def set_stichtag(w: Wert):
    """#26 — Start-Abgrenzungsdatum setzen (ISO 'YYYY-MM-DD')."""
    import re
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", w.wert.strip()):
        return JSONResponse({"ok": False, "fehler": "Datum als JJJJ-MM-TT"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO einstellungen (schluessel, wert) VALUES ('stichtag', %s)
                       ON CONFLICT (schluessel) DO UPDATE SET wert=EXCLUDED.wert""", (w.wert.strip(),))
    return {"ok": True, "wert": w.wert.strip()}


class Rolle(BaseModel):
    zaehlt_als: str    # 'ruecklage' | 'forderung' | 'ausgabe'


@app.post("/api/kategorie/{kategorie_id}/rolle")
def set_kat_rolle(kategorie_id: int, r: Rolle):
    if r.zaehlt_als not in ("ruecklage", "forderung", "ausgabe"):
        return JSONResponse({"ok": False, "fehler": "ungültige Rolle"}, status_code=400)
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET zaehlt_als=%s WHERE id=%s", (r.zaehlt_als, kategorie_id))
    return {"ok": True}


class DefaultUkat(BaseModel):
    unterkategorie_id: int | None = None


@app.post("/api/kategorie/{kategorie_id}/default_ukat")
def set_kat_default_ukat(kategorie_id: int, d: DefaultUkat):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE kategorien SET default_unterkategorie_id=%s WHERE id=%s",
                    (d.unterkategorie_id, kategorie_id))
    return {"ok": True}


class UkatName(BaseModel):
    name: str


@app.post("/api/unterkategorie/{unterkategorie_id}/rename")
def rename_unterkategorie(unterkategorie_id: int, u: UkatName):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE unterkategorien SET name=%s WHERE id=%s", (u.name.strip(), unterkategorie_id))
    return {"ok": True}


@app.post("/api/unterkategorie/{unterkategorie_id}/delete")
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


@app.post("/api/unterkategorie")
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


class Posten(BaseModel):
    id: int | None = None
    name: str
    betrag: str
    art: str = "vermoegen"    # 'vermoegen' | 'schuld'
    notiz: str | None = None
    gruppe: str = "posten"    # 'posten' | 'merkzettel' (U1)


@app.post("/api/vermoegensposten")
def upsert_posten(p: Posten):
    cent = _parse_euro(p.betrag)
    gruppe = p.gruppe if p.gruppe in ("posten", "merkzettel") else "posten"
    with db() as conn, conn.cursor() as cur:
        if p.id:
            cur.execute("UPDATE vermoegensposten SET name=%s, wert_cent=%s, art=%s, notiz=%s WHERE id=%s",
                        (p.name.strip(), cent, p.art, p.notiz, p.id))
            pid = p.id
        else:
            cur.execute("""INSERT INTO vermoegensposten (name, wert_cent, art, notiz, gruppe)
                           VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (name) DO UPDATE SET wert_cent=EXCLUDED.wert_cent, art=EXCLUDED.art,
                           notiz=EXCLUDED.notiz, gruppe=EXCLUDED.gruppe RETURNING id""",
                        (p.name.strip(), cent, p.art, p.notiz, gruppe))
            pid = cur.fetchone()[0]
    return {"ok": True, "id": pid, "cent": cent}


@app.post("/api/vermoegensposten/{posten_id}/delete")
def delete_posten(posten_id: int):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vermoegensposten SET aktiv=FALSE WHERE id=%s", (posten_id,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# #56 Bargeld: KEIN eigenes Bar-Konto mehr (User-Entscheid 2026-07-16). Die
# Bargeldabhebung kommt als normale Giro-Buchung aus dem Import; der Bargeld-
# bestand wird als Vermögensposten „Bar" (im_haushaltssaldo) MANUELL gepflegt
# (bei Abhebung hoch, bei Verbrauch runter) — Posten sind im Dashboard bereits
# editierbar, deshalb braucht es hier keinen eigenen Endpoint.
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import os
    # Standard: im Heimnetz erreichbar (0.0.0.0) -> Handy/Laptop via http://<PC-IP>:3000.
    # Nur-lokal:  HAUSHALT_DASHBOARD_HOST=127.0.0.1 setzen.
    host = os.getenv("HAUSHALT_DASHBOARD_HOST", "0.0.0.0")
    # PORT wird von Azure App Service / Container Apps gesetzt; sonst 3000 (lokal).
    port = int(os.getenv("PORT") or os.getenv("HAUSHALT_DASHBOARD_PORT", "3000"))
    print(f"[dashboard] http://localhost:{port}  (im WLAN: http://<PC-IP>:{port})")
    uvicorn.run(app, host=host, port=port)
