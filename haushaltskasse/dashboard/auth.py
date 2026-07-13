"""P0.1 — Login/Auth (Variante A): Session-Cookie + bcrypt, Single-User aus der .env.

Umgebungsvariablen (in .env):
  HAUSHALT_APP_USER            Benutzername
  HAUSHALT_APP_PASSWORD_HASH   bcrypt-Hash des Passworts
  HAUSHALT_SESSION_SECRET      Secret zum Signieren des Session-Cookies
  HAUSHALT_HTTPS_ONLY=1        Secure-Cookie erzwingen (Produktion mit HTTPS)

Hash + Secret erzeugen:  python -m haushaltskasse.dashboard.auth

Ist KEIN Passwort-Hash gesetzt, ist die Auth deaktiviert (nur lokal/Dev) — mit lauter Warnung.
Vor dem öffentlichen Deploy MUSS der Hash gesetzt sein.
"""
from __future__ import annotations

import hmac
import os
import secrets

import bcrypt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

# Routen ohne Login-Zwang
OEFFENTLICH = {"/login", "/logout", "/health", "/favicon.ico"}


def _user() -> str:
    return os.getenv("HAUSHALT_APP_USER", "")


def _hash() -> bytes:
    return os.getenv("HAUSHALT_APP_PASSWORD_HASH", "").encode()


def auth_aktiv() -> bool:
    """True, wenn Benutzer UND Passwort-Hash konfiguriert sind."""
    return bool(_user() and _hash())


def passwort_ok(user: str, passwort: str) -> bool:
    if not auth_aktiv():
        return False
    if not hmac.compare_digest((user or "").encode("utf-8"), _user().encode("utf-8")):
        return False
    try:
        return bcrypt.checkpw(passwort.encode(), _hash())
    except ValueError:
        return False


def session_secret() -> str:
    s = os.getenv("HAUSHALT_SESSION_SECRET")
    if not s:
        s = secrets.token_hex(32)
        print("[auth] WARNUNG: HAUSHALT_SESSION_SECRET nicht gesetzt -> zufälliges Secret. "
              "Sessions überleben keinen Neustart; für Produktion bitte setzen.")
    return s


def https_only() -> bool:
    return os.getenv("HAUSHALT_HTTPS_ONLY", "0") == "1"


class AuthMiddleware(BaseHTTPMiddleware):
    """Schützt alle Routen außer OEFFENTLICH/static. API -> 401, Views -> Redirect auf /login."""

    async def dispatch(self, request, call_next):
        pfad = request.url.path
        if not auth_aktiv() or pfad in OEFFENTLICH or pfad.startswith("/static"):
            return await call_next(request)
        if request.session.get("auth"):
            return await call_next(request)
        if pfad.startswith("/api/"):
            return JSONResponse({"ok": False, "fehler": "nicht angemeldet"}, status_code=401)
        return RedirectResponse("/login", status_code=303)


if __name__ == "__main__":
    import getpass

    pw = getpass.getpass("Passwort für das Dashboard: ")
    if pw != getpass.getpass("Wiederholen: "):
        raise SystemExit("Passwörter stimmen nicht überein.")
    h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    print("\n--- in die .env eintragen ---")
    print("HAUSHALT_APP_USER=DEIN_NAME")
    print(f"HAUSHALT_APP_PASSWORD_HASH={h}")
    print(f"HAUSHALT_SESSION_SECRET={secrets.token_hex(32)}")
    print("HAUSHALT_HTTPS_ONLY=1   # in Produktion (HTTPS) aktivieren")
