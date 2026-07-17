"""Seiten (GET) + Login/Logout/Health + Web-Import — alles, was HTML rendert."""
from __future__ import annotations

import re

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import auth
from .. import queries as q
from ..helpers import TEMPLATES, app_version, db, parse_euro

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, **app_version()}


@router.get("/releasenotes", response_class=HTMLResponse)
def view_releasenotes(request: Request):
    """Detaillierte Release Notes — was in jeder Version dazukam (Jörg-Wunsch)."""
    return TEMPLATES.TemplateResponse(request, "releasenotes.html",
                                      {"request": request, "tab": "releasenotes"})


@router.get("/backlog", response_class=HTMLResponse)
def backlog_board():
    """Das Roadmap-Board (aus docs/BACKLOG.md generiert) direkt in der App zeigen."""
    from pathlib import Path
    pfad = Path(__file__).resolve().parents[2] / "docs" / "backlog-board.html"
    try:
        return HTMLResponse(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return HTMLResponse("<p>Backlog-Board nicht gefunden.</p>", status_code=404)


# ---------------------------------------------------------------------------
# Auth (P0.1) — Login/Logout
# ---------------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return TEMPLATES.TemplateResponse(
        request, "login.html", {"request": request, "fehler": None, "auth_aktiv": auth.auth_aktiv()})


@router.post("/login")
def login_post(request: Request, username: str = Form(""), password: str = Form("")):
    if auth.passwort_ok(username, password):
        request.session["auth"] = True
        return RedirectResponse("/", status_code=303)
    return TEMPLATES.TemplateResponse(
        request, "login.html",
        {"request": request, "fehler": "Benutzername oder Passwort falsch.", "auth_aktiv": auth.auth_aktiv()},
        status_code=401)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------------------
# Views (GET)
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def view_uebersicht(request: Request, stichtag: str = ""):
    with db() as conn, conn.cursor() as cur:
        u = q.uebersicht(cur)
        baum = q.ruecklagen_baum(cur)   # für die aufklappbare Rücklagen-Sicht in der Übersicht
        st = None
        if stichtag and re.fullmatch(r"\d{4}-\d{2}-\d{2}", stichtag.strip()):
            st = q.haushaltssaldo_per_stichtag(cur, stichtag.strip())
        ctx = {"request": request, "tab": "uebersicht", "u": u, "baum": baum,
               "st": st, "stichtag": stichtag}
    return TEMPLATES.TemplateResponse(request, "uebersicht.html", ctx)


@router.get("/ruecklagen", response_class=HTMLResponse)
def view_ruecklagen(request: Request):
    with db() as conn, conn.cursor() as cur:
        baum = q.ruecklagen_baum(cur)
    soll_summe = sum(k["soll_cent"] for k in baum) + sum(
        u["soll_cent"] for k in baum for u in k["unterkategorien"])
    return TEMPLATES.TemplateResponse(
        request, "ruecklagen.html",
        {"request": request, "tab": "ruecklagen", "baum": baum, "soll_summe_cent": soll_summe})


@router.get("/nebenbuch/{kategorie_id}", response_class=HTMLResponse)
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


@router.get("/buchungen", response_class=HTMLResponse)
def view_buchungen(request: Request, konto: str = "", kategorie_id: str = "",
                   unterkategorie_id: str = "", offen: str = "", suche: str = "",
                   von: str = "", bis: str = "", betrag_min: str = "", betrag_max: str = "",
                   alle: str = "", sort: str = "datum", richtung: str = "desc", seite: int = 1):
    limit, offset = 200, (max(seite, 1) - 1) * 200
    kid = int(kategorie_id) if kategorie_id.isdigit() else None
    uid = int(unterkategorie_id) if unterkategorie_id.isdigit() else None
    bmin = parse_euro(betrag_min) if betrag_min.strip() else None
    bmax = parse_euro(betrag_max) if betrag_max.strip() else None
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


@router.get("/reports", response_class=HTMLResponse)
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


@router.get("/config", response_class=HTMLResponse)
def view_config(request: Request):
    with db() as conn, conn.cursor() as cur:
        fluss = q.config_fluss(cur)
        stichtag = q.stichtag(cur)
    return TEMPLATES.TemplateResponse(request, "config.html",
                                      {"request": request, "tab": "config", "fluss": fluss,
                                       "stichtag": stichtag})


@router.get("/import", response_class=HTMLResponse)
def view_import(request: Request):
    return TEMPLATES.TemplateResponse(request, "import.html",
                                      {"request": request, "tab": "import", "bericht": None})


@router.post("/import", response_class=HTMLResponse)
async def do_import(request: Request, datei: UploadFile = File(...)):
    from ...workflows.web_import import importiere_upload
    daten = await datei.read()
    try:
        bericht = importiere_upload(datei.filename or "unbekannt", daten)
    except Exception as e:
        bericht = {"datei": datei.filename, "erkannt": False, "fehler": f"{type(e).__name__}: {e}",
                   "geparst": 0, "eingefuegt": 0, "uebersprungen": 0}
    return TEMPLATES.TemplateResponse(request, "import.html",
                                      {"request": request, "tab": "import", "bericht": bericht})


@router.get("/vertraege", response_class=HTMLResponse)
def view_vertraege(request: Request):
    """#75 — Verträge je Nebenbuch: Gebühr, Rhythmus, Beschreibung, Zuordnung.

    Zeigt zusätzlich die Deckelprüfung: fordern die bestätigten Verträge mehr als das
    Config-Soll des Nebenbuchs, ist das entweder eine harte Warnung oder — wenn für das
    Nebenbuch erlaubt — eine bewusste Schiefstellung mit Reichweiten-Angabe.
    """
    with db() as conn, conn.cursor() as cur:
        daten = q.vertraege(cur)
        kats = q.kategorien_mit_unterkategorien(cur)
        umsaetze = q.zuordenbare_buchungen(cur)
    return TEMPLATES.TemplateResponse(
        request, "vertraege.html",
        {"request": request, "tab": "vertraege", "daten": daten, "kats": kats,
         "umsaetze": umsaetze})


@router.post("/vertraege/erkennen", response_class=HTMLResponse)
def do_vertraege_erkennen(request: Request):
    """On-Demand-Erkennung (User-Entscheid F: Komfort, kein Pflichtweg).

    Legt nur Vorschläge an (`erkannt`) und aktualisiert die gemessenen Werte.
    Bestätigte/ignorierte Verträge bleiben unangetastet, Soll-Werte werden NICHT verändert.
    """
    from ...workflows.vertraege import erkenne, speichere
    with db() as conn, conn.cursor() as cur:
        neu = speichere(cur, erkenne(cur))
    return RedirectResponse(f"/vertraege?neu={neu}", status_code=303)
