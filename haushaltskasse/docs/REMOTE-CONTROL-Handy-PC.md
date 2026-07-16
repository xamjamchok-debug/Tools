# Remote Control — PC-Session vom Handy steuern

> Kurz: **`/remote-control` startet man auf dem PC, nicht in dieser Cloud-Session.**
> Danach verbindet sich das Handy mit der laufenden PC-Session.

## Warum `/remote-control` in der Handy/Cloud-Session „not available" sagt

Es sind **zwei verschiedene Session-Arten** im Spiel:

| | Cloud-Session (Handy/Web) | PC-Session (Terminal) |
|---|---|---|
| Läuft auf | Anthropic-**Cloud** (claude.ai/code) | **deinem PC** (lokal) |
| Dateizugriff / Deploy | nein — baut Code & pusht nach GitHub | ja — lokales Dateisystem, Azure-Deploy |
| Startet Remote Control? | **nein** (läuft schon in der Cloud) | **ja** |

Remote Control „exponiert" eine **lokale** Session fürs Handy. Diese Cloud-Session läuft aber
gar nicht lokal — deshalb gibt es hier nichts zu exponieren, und `/remote-control` ist hier
nicht verfügbar. Das ist kein Fehler, sondern die falsche Session-Art.

## Setup — Schritt für Schritt

### 1. Handy: Claude-App installieren
- iOS App Store / Android Play Store → **„Claude by Anthropic"**.
- Mit **demselben Account** anmelden wie am PC.
- Tipp: am **PC** im Claude-Code-Terminal `/mobile` eingeben → zeigt einen QR-Code zum App-Download.

### 2. PC: Remote Control starten
Im Claude-Code-Terminal auf dem PC eine der drei Varianten:

```
/remote-control              # in einer LAUFENDEN Session (übernimmt den Verlauf)
claude --remote-control      # neue interaktive Session, lokal weiter tippbar
claude remote-control        # reiner Server-Modus, wartet auf Handy-Verbindung
```

Der PC zeigt danach eine **Session-URL** und (Leertaste drücken) einen **QR-Code**.
Optional Name vergeben: `/remote-control Haushaltskasse`.

### 3. Handy: verbinden
- **QR-Code** vom PC mit dem Handy scannen → öffnet die Session direkt in der App, **oder**
- in der Claude-App unten **„Code"** antippen → Session in der Liste wählen
  (Computer-Symbol mit **grünem Punkt** = online).

Ab jetzt steuerst du die **PC-Session vom Handy** — inkl. Azure-Deploy, weil die Befehle
auf dem PC laufen. Beide Oberflächen (PC-Terminal + Handy) bleiben synchron; du kannst
abwechselnd von beiden schreiben.

## Voraussetzungen
- Am PC per `/login` mit dem **claude.ai-Account** angemeldet (kein API-Key, kein
  `ANTHROPIC_API_KEY`/`ANTHROPIC_BASE_URL` gesetzt).
- Pro/Max ok; bei Team/Enterprise muss ein Owner Remote Control unter
  <https://claude.ai/admin-settings/claude-code> freischalten.

## Grenzen / gut zu wissen
- Der **PC muss anbleiben** (Terminal offen, `claude`-Prozess läuft). Schläft der PC oder ist
  er länger als ~10 Min ohne Netz → Session endet, dann am PC neu `claude remote-control`.
- **Nur eine** Remote-Control-Session pro interaktivem Prozess (für mehrere: Server-Modus).
- Manche Befehle sind **nur lokal** (`/plugin`, `/resume`). `/model`, `/effort`, `/config`
  u. a. funktionieren vom Handy, wenn man den Wert als Argument mitgibt (z. B. `/model sonnet`).
- **Push-Benachrichtigungen**: bei aktiver Remote-Control-Session kann Claude aufs Handy pushen
  (z. B. „Tests fertig"). Am PC via `/config` → „Push when Claude decides" / „…actions required".

## Abgrenzung: Remote Control vs. diese Cloud-Session
- **Remote Control** = laufende **lokale** PC-Arbeit von unterwegs weitersteuern (lokales
  Dateisystem, MCP, Deploy). Start: `claude remote-control` **am PC**.
- **Claude Code on the web** (diese Session) = Aufgabe ohne lokales Setup in der Cloud starten,
  Code bauen & nach GitHub pushen; **kein** lokaler Deploy.

Für unseren Ablauf heißt das: Code bauen/pushen passiert hier in der Cloud (Branch
`claude/status-update-bpmbn2`), **deployen + DB-Migrationen** laufen auf dem PC — dorthin
kommst du bequem per Remote Control vom Handy.
