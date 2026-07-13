# Stand 2026-07-13 — Live + Backlog (Handoff fürs Handy)

> Diese Datei ist der aktuelle Steuer-/Statuspunkt. Vom Handy: `git pull`, dann Backlog unten
> abarbeiten. **Wichtig:** Code-Änderungen vom Handy landen per Commit/Push im Repo, aber die
> **Live-App wird nur am PC neu deployt** (Azure-CLI-Login liegt am PC). Ablauf siehe „Deploy" unten.

---

## ✅ LIVE — die App läuft öffentlich
- **URL:** `https://haushaltskasse.happyfield-4f41987c.germanywestcentral.azurecontainerapps.io`
- **Login:** `joerg` + dein gesetztes Passwort. HTTPS + Login-Schutz aktiv, scale-to-zero
  (erster Aufruf nach Pause = ein paar Sekunden Kaltstart).
- Azure: Container App `haushaltskasse` im Env `hhenv-gwc` (germanywestcentral), Image aus ACR
  `hhkassec1k7wx`, DB = Azure-Postgres `hh-te86ka` (westeurope).

## ✅ In dieser PC-Session erledigt
1. **Deploy nach Azure Container Apps** (scale-to-zero, HTTPS, Login) — komplett eingerichtet.
2. **Rücklagen Modell A** (Topf je Unterkategorie): Migration `workflows/allgemein_toepfe.py`
   gegen die Azure-DB ausgeführt → je Kategorie eine **„Allgemein"-Unterkategorie**, die die
   bisher kategorie-weit gebuchten Zuführungen hält. Saldierung geht jetzt auf (Auto: Σ Ukat = Topf).
   *Schon live — nur Rücklagen-Seite neu laden.*
3. **Buchungen B1** — Summenzeile über ALLE gefilterten Treffer (Netto + Einnahmen/Ausgaben).
4. **Buchungen B2** — Freitext-**Bemerkung** je Buchung (Spalte, Enter speichert).
   *(B1/B2 sind im Code, gehen live mit dem nächsten Deploy.)*

---

## 📋 BACKLOG (offen, priorisiert)

### Rücklagen-Seite
- **R1** Drilldown: Klick auf eine Unterkategorie → deren Einzelbuchungen (Buchungsseite filtert
  schon nach `unterkategorie_id`, also nur verlinken).
- **R4** „+ zurücklegen / − entnehmen" je Unterkategorie = neue `ruecklage`-Buchung (+/−, quelle
  'manuell', heutiges Datum). Braucht neuen Endpoint + Button.
- **R3** „Soll" (monatliche Zuführung) nur an EINER Stelle editierbar (Rücklagen), in Config
  read-only; klar beschriften. Aktuell doppelt editierbar.

### Buchungen
- **B3** Filter/Umschalter nach `buchungsart` (real/ruecklage/…), damit die B1-Summe nicht durch
  Rücklagen-Spiegelbuchungen verzerrt wird (aktuell summiert die Liste ALLE Arten der Treffer).

### Übersicht
- **U1** Merkzettel als eigene **Box mit Einzelposten** (statt einem Summen-Posten). Neue Spalte
  `vermoegensposten.gruppe` ('posten'|'merkzettel'), beide zählen im Saldo (`im_haushaltssaldo`).
- **U2** transparente **Saldo-Herleitung** (Wasserfall): Konten + Posten + Merkzettel + Forderungen
  − Rücklagen = „frei verfügbar", mit Vorzeichen.
- **U3** **Monatsablauf-Block** (klappbar, auf der Übersicht): je Nebenbuch **Soll vs. Ist**,
  Einnahmen oben, konsolidierter Saldo unten. Unterkategorien aufklappen + Soll editieren
  (wie Rücklagen-Accordion). `ruecklagen_baum()` wiederverwenden.
- **U4** **Stichtagssaldo**: buchungsbasierter Teil exakt (`SUM … WHERE datum_wert ≤ Stichtag`),
  Vermögensposten als zeitlos-konstant dazurechnen + klar kennzeichnen (opt. `stand_datum` je Posten).
  Datumsfeld an der Saldo-Herleitung (U2).
- **U5** **Veränderung Stichtag X → Y (Mittelfluss-Überblick)** — was hat sich zwischen zwei
  Stichtagen geändert: Delta-Saldo gesamt + Zufluss/Abfluss je Konto/Kategorie/Topf im Intervall.
  **Default nach Import** neuer Umsätze (X = Stand vor Import, Y = jetzt) → sofortiger Überblick,
  welches Geld wohin geflossen ist. Baut auf U4 + I1 auf.

### Config
- **C1** Config-Seite: Kategorien **einklappbar** machen (Accordion wie Rücklagen), kompakter.

### Übersicht/Monatsablauf – Einnahmen
- **E1** **Einnahmen explizit aufnehmen** im Monatsablauf (U3) UND als eigene Sicht: Zufluss/Gehalt
  je Zeitraum getrennt zeigen, in den konsolidierten Saldo einrechnen. (Teil von U3, hier als
  eigener Merkpunkt, damit es nicht untergeht.)

### Sonstiges
- **I1** **Import neuer Umsätze** über die Weboberfläche (DKB/comdirect/Amazon-CSV hochladen →
  `workflows/pipeline.py` läuft, dedupe, kategorisieren). Merker: `parse_amazon_visa` noch auf .xls
  → auf CSV umstellen, sobald Amazon als CSV kommt.
- **K1** **Schlauere Kategorien/Unterkategorien** — bessere (KI-gestützte) Zuordnung, lernende
  Mapping-Regeln (`mapping_regeln`-Tabelle existiert schon), Vorschläge bestätigen.
- **B4** **Besser filtern** (Buchungen) — mehr/kombinierbare Filter, Mehrfachauswahl Unterkategorie,
  Filter-Chips; zusammen mit B3 (Buchungsart-Filter).
- **P2** **Freie Query + Pivot + Ein-/Auszahlen** — freie Recherche (read-only SQL-Konsole und/oder
  KI-Text-Prompt→SQL), Pivot-Report ausbauen (Basis in Reports vorhanden), „Einzahlen/Auszahlen" =
  manuelle Zuführung/Entnahme auf Töpfe (deckt sich mit R4).
- **V1** **Versionierung + Tests** — App-Version/Build-Stempel in der UI anzeigen (sichtbar machen,
  welche Version live ist), ggf. Daten-Snapshots/Historie; dazu automatisierte Tests (pytest) für
  Queries/Saldo-Formeln/Endpoints, damit Änderungen abgesichert sind.
- **P0.3** Azure-Kostenanzeige in der Seite (ACR Basic ~5 $/Mon fix, Postgres, Container ~0 im Leerlauf).

---

## 🚀 Deploy (nur am PC, Azure-CLI-Login liegt hier)
Nach Code-Änderungen (auch nach `git pull` von Handy-Commits):
```
# im Repo-Root, PowerShell:
$env:PYTHONIOENCODING="utf-8"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
& $az acr build -r hhkassec1k7wx -t haushaltskasse:latest . --no-logs   # --no-logs vermeidet den charmap-Crash
& $az containerapp update -g haushaltskasse-rg -n haushaltskasse --image hhkassec1k7wx.azurecr.io/haushaltskasse:latest
```
> **`--no-logs` ist wichtig:** ohne es crasht die Windows-Konsole (cp1252) beim Log-Streaming
> (`UnicodeEncodeError: charmap`). Der Build läuft dann zwar serverseitig durch, aber der
> `update`-Schritt wird übersprungen. Status sonst prüfen: `az acr task list-runs -r hhkassec1k7wx --top 1 -o table`.
> **Empfehlung fürs Handy-Arbeiten:** GitHub-Actions-Auto-Deploy einrichten (Service Principal +
> Secret + Workflow), dann deployt jeder Push automatisch — dann brauchst du den PC-Schritt nicht mehr.

## Technische Merker
- **az-CLI** nicht im PATH → voller Pfad (oben). Vor `acr build`/langen az-Ausgaben immer
  `PYTHONIOENCODING=utf-8` setzen (sonst `charmap`-Crash beim Log-Streaming).
- **Nach `beladung --write`** (TRUNCATE) IMMER erneut: `gegenbuchung --write` UND
  `allgemein_toepfe --write` (beide idempotent).
- Datenschutz: private Beträge/IBANs/Namen nur aus DB/lokaler `.env` — nie im Code/Git.
