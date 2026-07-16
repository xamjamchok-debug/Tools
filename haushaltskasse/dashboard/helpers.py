"""Gemeinsame Bausteine des Dashboards: DB-Kontext, Euro-Formate, Templates (P8-Schnitt).

Vorher lebte all das im app.py-Monolithen; die Router (routes/*.py) importieren es von hier.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from fastapi.templating import Jinja2Templates

from ..storage.db import connect

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@contextmanager
def db():
    """Eine Verbindung pro Request: Commit bei Erfolg, Rollback bei Fehler."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def euro(cent) -> str:
    """Cent -> '1.234,56 €' (deutsche Schreibweise)."""
    cent = cent or 0
    s = f"{cent / 100:,.2f}"                       # 1,234.56
    return s.replace(",", "␟").replace(".", ",").replace("␟", ".") + " €"


def parse_euro(text) -> int:
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


def eurozahl(cent) -> str:
    """Cent -> '1.234,56' — deutsch, aber OHNE €-Zeichen: für editierbare Felder.

    Muss deutsch sein, sonst steht in der Maske '-2775.0' (#6). `parse_euro` liest beide
    Notationen zurück, der Rundlauf Anzeige -> Eingabe -> Speichern bleibt also heil.
    """
    return euro(cent).removesuffix(" €")


def stichtag_global() -> str:
    """#26 — Start-Abgrenzungsdatum für Anzeige im Footer (jede Seite)."""
    from . import queries as q
    try:
        with db() as conn, conn.cursor() as cur:
            return q.stichtag(cur)
    except Exception:
        return q.STICHTAG


def app_version() -> dict:
    """#23 V1a — welcher Stand ist live? Werte setzt der Deploy per Env-Var
    (`--set-env-vars APP_VERSION=$(git rev-parse --short HEAD) APP_BUILD_TIME=...`).
    Container-Revision liefert Azure automatisch als CONTAINER_APP_REVISION."""
    return {
        "version": os.getenv("APP_VERSION", "dev"),
        "build": os.getenv("APP_BUILD_TIME", ""),
        "revision": os.getenv("CONTAINER_APP_REVISION", ""),
    }


TEMPLATES.env.filters["euro"] = euro
TEMPLATES.env.filters["eurozahl"] = eurozahl
TEMPLATES.env.globals["stichtag_global"] = stichtag_global
TEMPLATES.env.globals["app_version"] = app_version
