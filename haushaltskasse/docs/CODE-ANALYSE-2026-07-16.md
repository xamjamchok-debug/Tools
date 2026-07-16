# Code-Analyse Haushaltskasse — Schritt 1: Grobe Übersicht

**Stand 2026-07-16 · Analyse-Ebene 1 von 3** (Übersicht → Deep Dive I → Deep Dive II)

Dieses Dokument gibt den prinzipiellen Aufbau, die tragenden Struktur­entscheidungen und die
erkennbaren Risiken wieder — plus eine **Aufwandsschätzung** für die beiden geplanten Deep Dives.
Es ist bewusst auf der Flughöhe „wie ist das Ganze gebaut" gehalten; Detailbefunde (Zeile-für-Zeile,
Kanten­fälle, Saldo-Beweise) sind ausdrücklich den Deep Dives vorbehalten.

---

## 1. Was ist das Tool?

Eine **persönliche Haushaltskasse** als Web-App: FastAPI-Backend + server-gerenderte Jinja2-Seiten,
PostgreSQL als einzige Quelle der Wahrheit, deployt auf Azure Container Apps (HTTPS, Login,
scale-to-zero). Sie hat eine gewachsene Excel-„Fuchsbaukasse" abgelöst und bildet deren Logik nach:
reale Konten, zweckgebundene Rücklagen-Töpfe, Forderungen zwischen Personen, langfristige
Vermögens-/Kreditposten und ein monatlicher Finanzfluss.

**Codeumfang** (ohne `.venv`, ohne `__pycache__`):

| Bereich | Dateien | Zeilen (ca.) |
|---|---|---|
| Python gesamt | 30 | ~3.830 |
| davon `dashboard/` (Web) | 6 | ~1.530 |
| davon `workflows/` (Daten-Pipelines) | 16 | ~1.750 |
| davon `storage/` (DB-Schicht) | 2 | ~270 |
| HTML-Templates | 9 | ~950 |
| SQL-Schema | 1 | 162 |
| Doku (`docs/`) | 16 MD | — |

**Aktivität:** 57 Commits, praktisch alle in den letzten 30 Tagen — sehr junge, in schneller Iteration
entstandene Codebasis. Steuerdatei ist [`BACKLOG.md`](BACKLOG.md) (v3.0, 56 Positionen mit Reifegrad).

---

## 2. Architektur — die tragenden Schichten

```
Kontoauszüge (CSV/XLS)                Web-Browser (Handy/PC)
      │                                        │
      ▼                                        ▼
┌─────────────────────┐          ┌──────────────────────────────┐
│ workflows/          │          │ dashboard/app.py  (FastAPI)   │
│  parser  →          │          │  ~43 Routen: Views + JSON-API │
│  abgrenzung →       │          │  auth-Middleware, Sessions    │
│  kategorisierung →  │          │  queries.py (Read-Aggregate)  │
│  laden / web_import │          │  export.py (CSV)              │
└─────────┬───────────┘          └───────────────┬──────────────┘
          │                                       │
          └───────────────┬───────────────────────┘
                          ▼
              ┌────────────────────────┐
              │ storage/ (psycopg3)    │
              │  schema.sql  (8 Tab.)  │
              └───────────┬────────────┘
                          ▼
                 Azure PostgreSQL  ← einzige Quelle der Wahrheit
```

**Zwei Einstiegswege in dieselbe DB:**
1. **CLI-Workflows** (`python -m haushaltskasse.workflows.*`) — Erstbeladung, Migration aus Excel,
   Gegenbuchungs-Sync, Kategorien-Cleanup, Topf-Verteilung. Fast alle mit **Trockenlauf-Default**
   und `--write`-Schalter; mehrere sind bewusst **idempotent**.
2. **Web-Dashboard** — laufender Betrieb: Umkategorisieren, Rücklagen-Soll, Vermögensposten,
   Web-Import neuer Umsätze, Bemerkungen, CSV-Export.

Diese Doppelspur ist eine Kern-Eigenschaft (und ein Risiko, s. u.): Struktur-Migrationen laufen als
Skript am PC, der Alltag läuft im Browser — und beide schreiben in dieselben Tabellen.

---

## 3. Das Datenmodell — der eigentliche Kern

Das Modell ist der klügste und zugleich subtilste Teil des Tools. **Drei-Ebenen-Prinzip:**

> **Konto** (real, trägt Realsaldo) → **Kategorie = Nebenbuch** (1:1, trägt Rücklage) → **Unterkategorie** (nur Auswertung)

Acht Tabellen: `konten`, `kategorien`, `unterkategorien`, `einstellungen`, `vermoegensposten`,
`buchungen`, `mapping_regeln`, `import_dateien`. Beträge durchgängig als **BIGINT in Cent** (keine
Float-Fehler) — eine sehr gute Grundentscheidung.

**Drei tragende Ideen, die man verstanden haben muss:**

- **`buchungsart` trennt drei Welten:** `real` (Konto+Kategorie, ändert Realsaldo) ·
  `ruecklage` (nur Kategorie, virtuell — Zuführung/Verzehr) · `umbuchung` (Konto+Gegenkonto,
  netto 0, keine Ausgabe). Dazu `wertpapier`/`zinsen` als Sonderfälle.
- **Spiegel-Buchungen (`spiegel_von_id`):** Jede berechtigte Realausgabe erzeugt automatisch eine
  verknüpfte `ruecklage`-Gegenbuchung, die den zugehörigen Topf **verzehrt** — dadurch ist eine
  topf-gedeckte Ausgabe **saldo-neutral**. Diese Automatik (`gegenbuchung.py`) ist das Herzstück
  und wird bei jedem Umkategorisieren im Dashboard nachgezogen (`sync_eine`).
- **`zaehlt_als` steuert das Vorzeichen im Saldo:** `ruecklage` wird **abgezogen**, `forderung`
  (Natalie/Jörg) **addiert**, `ausgabe` ist topf-los. Die kanonische Formel steht in
  `queries.haushaltssaldo()`: `Konten + Posten − Rücklagen + Forderungen`.

**Lernende Kategorisierung:** `mapping_regeln` (Muster→Kategorie, retroaktiv anwendbar) + generische
Starter-Regeln + optional KI (`anthropic`). Aktuell 64 aktive Regeln.

---

## 4. Stärken

- **Sauber getrenntes Cent-Datenmodell** mit ausführlich dokumentiertem Schema — das SQL erklärt
  sich fast selbst.
- **Idempotente, trockenlauf-sichere Migrations-Skripte.** Die riskanten Struktur­eingriffe sind
  entschärft (erst Vorschau, dann `--write`, zweiter Lauf = No-Op).
- **Klare Read-/Write-Trennung** im Dashboard: `queries.py` liest, `app.py` schreibt, `export.py`
  formatiert. Kein ORM-Overhead, direktes psycopg3.
- **Nachvollziehbarkeit bis zum Empfänger** (jede Buchung speichert `empfaenger`/`verwendungszweck`)
  und **Dedupe beim Reimport** (`import_hash`).
- **Disziplinierte Doku:** BACKLOG als Reifegrad-Steuerung, Handover-Dokumente, festgehaltenes
  Domänenwissen — für ein Ein-Personen-Projekt außergewöhnlich gut gepflegt.

---

## 5. Prinzipielle Schwierigkeiten & Risiken

Nach Schweregrad geordnet — das sind die Punkte, die die Deep Dives verifizieren/quantifizieren sollen.

### 🔴 Hoch

1. **Keine automatisierten Tests.** Kein einziger `test_*.py`. Die gesamte Korrektheit — insbesondere
   die Saldo- und Vorzeichen-Logik — wird **manuell gegen die echte Produktiv-DB** geprüft. Bei einem
   Tool, dessen Kernwert die *rechnerische Richtigkeit* ist, ist das das größte strukturelle Risiko.
   (Als Backlog #23b/V1b erkannt, aber „Idee".)
2. **Vorzeichen-/Rollen-Logik ist fragil und über mehrere Stellen verstreut.** Die Bedeutung von
   `zaehlt_als`, `buchungsart`, den Spiegel-Buchungen und den Posten-Flags (`im_haushaltssaldo`)
   greift ineinander; ein falsches Vorzeichen verschiebt den Saldo lautlos. Es gibt bereits offene
   Bugs dieser Klasse (#52 KPI-Kacheln vs. Stichtagssaldo driften; #9 „Posten fehlen"). Ohne Tests
   ist jede Änderung hier ein Blindflug.
3. **Migrations-Reihenfolge ist manuelles Herrschaftswissen.** Nach `beladung --write` (TRUNCATE!)
   müssen zwingend `gegenbuchung` und `allgemein_toepfe` erneut laufen, sonst sind Rollen/Gegen­buchungen
   weg. Diese Reihenfolge lebt in Handover-Dokumenten und im Kopf, nicht im Code.

### 🟡 Mittel

4. **`app.py` ist ein 652-Zeilen-Monolith** mit ~43 Routen, Helpern, Pydantic-Modellen und Business-Logik
   in einer Datei. Noch beherrschbar, aber die Grenze ist erreicht; die Bar-Konto-Logik (gerade wieder
   im Umbau) zeigt, wie Features hier anwachsen.
5. **Deploy ist manuell und PC-gebunden.** ACR-Build + Container-Update von Hand, `APP_VERSION` muss
   manuell gesetzt werden (sonst zeigt der Footer `dev`). Genau dafür wurde #23 gebaut — der Bedarf
   belegt das Risiko. Kein CI/CD, kein automatischer Test-Gate.
6. **Doppelspur DB-Zugriff (CLI + Web) ohne Transaktions-Klammer über beide.** Zwei parallele
   Claude-Sessions im selben OneDrive-Working-Tree haben schon einmal fremde Änderungen mitcommittet
   (dokumentiert). Auf Datenebene fehlt eine Sperre gegen konkurrierende Schreiber.
7. **Datenschutz strukturell heikel.** Private Beträge/IBANs/Namen dürfen nie in Code/Git — die
   Trennung über `.env`, `lokale_config.json` (gitignored) und DB funktioniert, ist aber eine reine
   Disziplin-Grenze. Im Container fehlt `lokale_config`, wodurch der Web-Import gröber abgrenzt (#22).

### 🟢 Niedrig / Aufräumen

8. **Fragile Parser-Abhängigkeit** (`xlrd` für Amazon-.xls; Umstellung auf CSV als Merker offen).
9. **Teilstring-Fallen in `mapping_regeln`** (z. B. `arag` matcht „Garage") — dokumentiert, aber
   dauerhaft wirksam auf künftige Importe.
10. **Testdaten in Produktiv-DB** (`__TEST_POSTEN__`, #53) und tote Felder (`ist_einnahme` bleibt nach
    #47 „harmlos" liegen).

---

## 6. Kostenschätzung für die Deep Dives

„Kosten" hier als **Aufwand** (Analyse-Sessions je ~1–2 h fokussierter Arbeit) plus dem, was jeweils
als belastbares Ergebnis herauskommt. Reine Lese-/Analyse-Arbeit, kein Produktiv-Schreiben.

### Deep Dive I — Korrektheit der Geld-Logik (empfohlen zuerst)
**Fokus:** Die rechnerische Wahrheit end-to-end verifizieren — das größte Risiko aus §5.
- Saldo-Formel, Vorzeichen und Spiegel-Buchungen Zeile für Zeile gegen das Datenmodell prüfen.
- Die vier Sichten (Übersicht, Rücklagen, Reports, Stichtag) auf Konsistenz abgleichen; die
  offenen Bugs #9/#52 reproduzieren und die Ursache exakt belegen.
- Idempotenz & Reihenfolge der Migrations-Skripte an einer Wegwerf-DB durchspielen.
- **Ergebnis:** belegte Bug-Liste mit Reproduktion + ein Minimal-Set an Regressionstests als
  Vorschlag (Saldo-Invarianten).
- **Aufwand:** **mittel–hoch, ~2–3 Sessions.** Erfordert eine lokale Wegwerf-Postgres zum Nachrechnen.

### Deep Dive II — Struktur, Betrieb & Wartbarkeit
**Fokus:** Alles um den Code herum, das die Weiterentwicklung bremst oder gefährdet.
- `app.py`-Monolith: Schnitt-Vorschlag (Router-Aufteilung, Service-Schicht).
- Import-Pipeline CLI vs. Web: Dubletten-/Abgrenzungs-Robustheit, `lokale_config`-Lücke im Container.
- Deploy/CI: Vorschlag für GitHub-Actions-Auto-Deploy inkl. Test-Gate (löst #23/#33/#23b gemeinsam).
- Datenschutz- und Backup-Konzept (pg_dump/Restore, #33).
- **Ergebnis:** priorisierte Refactoring- & Betriebs-Roadmap mit Aufwand je Punkt.
- **Aufwand:** **mittel, ~1–2 Sessions.** Rein lesend, keine DB nötig.

### Gesamt
| Deep Dive | Aufwand | DB nötig | Priorität |
|---|---|---|---|
| I — Geld-Logik & Korrektheit | ~2–3 Sessions | ja (Wegwerf) | **hoch** |
| II — Struktur & Betrieb | ~1–2 Sessions | nein | mittel |

**Empfehlung:** Mit **Deep Dive I** beginnen — dort sitzt das eigentliche Risiko (rechnerische
Richtigkeit ohne Testnetz). Deep Dive II liefert danach die Roadmap, um genau das (Tests, CI, Backup)
strukturell abzusichern.

---

*Nächster Schritt auf Freigabe: Deep Dive I. Sag Bescheid, ob der Zuschnitt oben passt oder ob ein
anderer Schwerpunkt (z. B. UI/UX, KI-Kategorisierung, Kostenoptimierung Azure) vorgezogen werden soll.*
