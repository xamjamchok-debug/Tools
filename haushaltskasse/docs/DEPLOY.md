# Deploy — Haushaltskasse-Dashboard ins Internet (P0.2)

> Ziel: Dashboard von überall erreichbar, mit HTTPS und Login (P0.1). DB bleibt die schon
> laufende Azure-Postgres (`hh-te86ka`, RG `haushaltskasse-rg`, germanywestcentral).
> **Vor dem Deploy:** Login-Env muss gesetzt sein (siehe unten), sonst ist die App offen!

Zwei Wege — **A (App Service, Code)** ist am einfachsten, **C (Container Apps)** ist im Leerlauf
am billigsten. Beide liefern automatisch HTTPS auf einer `*.azure…`-Domain.

---

## Gemeinsam: benötigte App-Einstellungen (Umgebungsvariablen)

Diese Werte werden als **App Settings** gesetzt (NICHT in den Code!):

| Variable | Wert |
|---|---|
| `HAUSHALT_DATABASE_URL` | `postgresql://USER:PW@hh-te86ka.postgres.database.azure.com:5432/haushaltskasse?sslmode=require` |
| `HAUSHALT_APP_USER` | dein Login-Name |
| `HAUSHALT_APP_PASSWORD_HASH` | bcrypt-Hash (`python -m haushaltskasse.dashboard.auth`) |
| `HAUSHALT_SESSION_SECRET` | langer Zufallswert (gleicher Befehl gibt einen aus) |
| `HAUSHALT_HTTPS_ONLY` | `1` |

**Postgres-Firewall:** In der Postgres-Ressource → *Netzwerk* → **„Zugriff von Azure-Diensten
erlauben"** aktivieren (damit der App-Dienst die DB erreicht, ohne feste IP). Alternativ VNet.

---

## Variante A — App Service (Code, Python)  ⭐ empfohlen zum Start

### A1. Web App anlegen (Portal)
- *Ressource erstellen* → **Web-App**
- Resource Group: `haushaltskasse-rg` · Region: `Germany West Central` (wie die DB)
- Veröffentlichen: **Code** · Runtime: **Python 3.12** · Betriebssystem: **Linux**
- Plan: **B1** (~13 €/Mon) — oder **F1 Free** zum Testen (schläft ein, eng limitiert)

### A2. Startbefehl setzen
Web-App → *Konfiguration* → *Allgemeine Einstellungen* → **Startbefehl**:
```
python -m uvicorn haushaltskasse.dashboard.app:app --host 0.0.0.0 --port $PORT
```

### A3. App-Einstellungen eintragen
Web-App → *Umgebungsvariablen / Konfiguration* → die Tabelle oben eintragen. Zusätzlich:
```
SCM_DO_BUILD_DURING_DEPLOYMENT = 1      # baut requirements.txt beim Deploy
```

### A4. Code deployen
- **Aus GitHub** (bequem): Web-App → *Deployment Center* → GitHub → Repo `xamjamchok-debug/Tools`,
  Branch `claude/status-update-bpmbn2`. Jeder Push deployt automatisch.
- **Oder CLI:** im Repo `az webapp up --name <appname> --resource-group haushaltskasse-rg --runtime PYTHON:3.12`

### A5. Absichern
- Web-App → *Konfiguration* → **„HTTPS Only" = An**.
- Aufrufen: `https://<appname>.azurewebsites.net` → Login-Seite muss erscheinen.

---

## Variante C — Azure Container Apps (scale-to-zero, im Leerlauf ~0 €)

Nutzt das mitgelieferte `Dockerfile`.

### C1. Image bauen & in Registry schieben
```
az acr create -g haushaltskasse-rg -n <registryname> --sku Basic
az acr build -r <registryname> -t haushaltskasse:latest .
```

### C2. Container App erstellen
```
az containerapp env create -g haushaltskasse-rg -n hh-env -l germanywestcentral
az containerapp create -g haushaltskasse-rg -n haushaltskasse \
  --environment hh-env --image <registryname>.azurecr.io/haushaltskasse:latest \
  --registry-server <registryname>.azurecr.io \
  --target-port 8000 --ingress external --min-replicas 0 --max-replicas 1 \
  --env-vars HAUSHALT_DATABASE_URL=... HAUSHALT_APP_USER=... HAUSHALT_APP_PASSWORD_HASH=... \
             HAUSHALT_SESSION_SECRET=... HAUSHALT_HTTPS_ONLY=1
```
`--min-replicas 0` = fährt bei Nichtnutzung runter (Kaltstart wenige Sekunden). HTTPS ist am
Ingress automatisch an. Aufrufen: die von der Container App ausgegebene `*.azurecontainerapps.io`-URL.

---

## Kosten
- **A:** App-Plan B1 ~13 €/Mon fix + Postgres. F1 gratis aber schläft ein/limitiert.
- **C:** zahlt im Leerlauf fast nichts; nur bei Nutzung. Etwas mehr Setup (Image/Registry).
- **Postgres** in beiden Fällen: bei Nichtnutzung stoppen spart (~4 €/Mon), siehe HANDOFF.

## Merker
- Ohne gesetztes `HAUSHALT_APP_PASSWORD_HASH` ist die App **ohne Login offen** — vor Public-Deploy zwingend setzen.
- `HAUSHALT_SESSION_SECRET` fest setzen (sonst werden Logins bei jedem Neustart ungültig).
