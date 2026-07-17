"""FastAPI-Dashboard der Haushaltskasse — App-Setup (P8-Schnitt).

Start:  python -m haushaltskasse.dashboard.app       (Port 3000)
        http://localhost:3000

Die Routen leben in routes/ (Views · Buchungs-API · Stammdaten-API · Posten-API · Exporte),
die gemeinsamen Bausteine (db(), Euro-Formate, Templates) in helpers.py. Die DB ist die
Quelle der Wahrheit; die Geld-/Saldo-Regeln kommen aus domain/saldo.py (#60).
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from . import auth
from .routes import api_buchungen, api_posten, api_stammdaten, api_vertraege, exports, views

auth.erzwinge_produktions_config()   # #63: in Produktion ohne Auth-Config -> Start verweigern

app = FastAPI(title="Haushaltskasse")

# Reihenfolge wichtig: SessionMiddleware zuletzt hinzufügen -> läuft ZUERST und füllt
# request.session, bevor die AuthMiddleware sie liest.
app.add_middleware(auth.AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=auth.session_secret(),
                   https_only=auth.https_only(), same_site="lax")

app.include_router(views.router)
app.include_router(api_buchungen.router)
app.include_router(api_stammdaten.router)
app.include_router(api_posten.router)
app.include_router(api_vertraege.router)
app.include_router(exports.router)


if __name__ == "__main__":
    import os
    # Standard: im Heimnetz erreichbar (0.0.0.0) -> Handy/Laptop via http://<PC-IP>:3000.
    # Nur-lokal:  HAUSHALT_DASHBOARD_HOST=127.0.0.1 setzen.
    host = os.getenv("HAUSHALT_DASHBOARD_HOST", "0.0.0.0")
    # PORT wird von Azure App Service / Container Apps gesetzt; sonst 3000 (lokal).
    port = int(os.getenv("PORT") or os.getenv("HAUSHALT_DASHBOARD_PORT", "3000"))
    print(f"[dashboard] http://localhost:{port}  (im WLAN: http://<PC-IP>:{port})")
    uvicorn.run(app, host=host, port=port)
