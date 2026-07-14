# Handover an PC — 2026-07-14 (aus Handy/Cloud-Session)

> Branch `claude/status-update-bpmbn2`, alles committet & gepusht. Am PC: `git pull`, dann
> deployen + testen. Diese Session lief in der Cloud (Code gebaut & lokal gegen Wegwerf-Postgres
> getestet), die **echte Azure-DB wurde nicht angefasst**.

Letzter Commit: `902482d`. Neu in dieser Session (oben = neuste):
- `902482d` Backlog-Dublette bereinigt
- `0631808` **R3 korrigiert** — Rücklagen read-only, Editieren nur in Config
- `a9de96b` **B3 + R5 + R1** — Buchungen nur real · Rücklagen ohne Fluss · Nebenbuch-Ansicht
- `445fc08` / `a92cf17` Backlog präzisiert/erweitert

---

## Was am PC zu tun ist

### 1. Holen
```
git checkout claude/status-update-bpmbn2 && git pull
```
Neue Templates: `nebenbuch.html`. Kein Schema-Änderungsbedarf für diese Commits
(die neuen Sachen nutzen vorhandene Spalten). Sicherheitshalber idempotent:
```
python -m haushaltskasse.storage.db     # nur ALTER ... IF NOT EXISTS, ändert keine Daten
```

### 2. Deployen (Live-App)
Wie gehabt (PowerShell, aus Repo-Wurzel):
```
$env:PYTHONIOENCODING="utf-8"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
& $az acr build -r hhkassec1k7wx -t haushaltskasse:latest . --no-logs
& $az containerapp update -g haushaltskasse-rg -n haushaltskasse --image hhkassec1k7wx.azurecr.io/haushaltskasse:latest
```

### Lokal vs. Deploy testen
Für diese reinen UI-/Query-Änderungen kannst du **direkt live deployen und dort testen** — der lokale
Lauf (`python -m haushaltskasse.dashboard.app`) bringt hier wenig Mehrwert, weil keine Migration/keine
riskante Datenänderung dabei ist. Also: **deployen, dann die Checkliste unten durchgehen.**

---

## Was zu testen ist (die 3 neuen Sachen)

### Buchungen — nur reale Konten (B3)
- [ ] Buchungen-Seite zeigt **nur echte Konto-Bewegungen**; die virtuellen Rücklagen-Gegenbuchungen
      (falsches Vorzeichen) sind **weg**.
- [ ] Checkbox **„inkl. Rücklagen"** blendet sie wieder ein; die Summenzeile zählt entsprechend.

### Rücklagen — read-only + Ist-Topf (R3, R5)
- [ ] Soll-Beträge sind **nicht mehr editierbar** (nur Anzeige); Hinweis „pflegst du in Config".
- [ ] **Keine Zufluss/Abfluss-Spalten** mehr — nur Soll + Ist-Topf. Kompakter.
- [ ] Auf-/zuklappen der Unterkategorien geht wie gehabt.

### Nebenbuch-Ansicht per Doppelklick (R1)
- [ ] **Doppelklick auf ein Nebenbuch** (Rücklagen-Seite) öffnet `/nebenbuch/…` mit dessen
      Rücklagenbuchungen und **laufendem Saldo** (wie altes Kto-Blatt).
- [ ] Doppelklick auf eine **Unterkategorie** öffnet dieselbe Ansicht, auf die Unterkategorie gefiltert.
- [ ] Der Unterkategorie-Filter oben in der Nebenbuch-Ansicht wirkt; Saldo unten passt.

### Regression
- [ ] Übersicht, Reports (Pivot), Config laden wie gehabt.

---

## Offene Entscheidung (blockiert die nächsten zwei Baustellen)

Bevor **#39 Config = Monats-Finanzfluss-Sicht** und **#22 Web-Import** gebaut werden, brauche ich
eine Antwort — **Einnahmen-Modellierung**:

> Für den Monats-Saldo (Einnahmen − Ausgaben): Sind die zwei Einnahme-Töpfe die bestehenden
> Kategorien **„Jörg" und „Natalie"** (mit positivem Monatsbetrag), oder sollen dafür eigene
> Einträge **„Einkommen Jörg / Natalie"** angelegt werden?
> Vorschlag: neue Rolle **„Einnahme"**, Jörg/Natalie als Einnahme markiert;
> **Monats-Saldo = Σ Einnahmen − Σ Ausgaben-Soll**.

Sobald das geklärt ist:
- **#39** Config zur editierbaren Monatssicht ausbauen (Einnahmen oben, Ausgaben je Nebenbuch→Unterkat
  einklappbar, Monats-Saldo + Gesamtsaldo; Absprung-Knopf für #40).
- **#22** Import neuer Umsätze über die Weboberfläche (Upload → Pipeline → dedupe → Report).
- **#40** 10-Jahres-Verlaufsplanung bleibt bewusst später.

---

## Backlog & Status
- Übersicht/Status: `docs/AENDERUNGEN-2026-07-13.md` (40 Punkte, nach Status)
- Detail + Deploy: `docs/STAND-2026-07-13-live.md`
- Diese Session hat #12 (R1), #14 (R3 read-only), #17 (B3), #27 (Fluss weg) auf „🔧 Code fertig,
  Deploy offen" gebracht — mit dem Deploy oben gehen sie live.
