# Auftrag an Fable — Review der Code-Analyse + Deep Dive II

**Erstellt 2026-07-16 (von Opus, für Fable-Session) · Projekt: Haushaltskasse**

Du (Fable) übernimmst zwei Aufgaben an der Haushaltskasse-Codebasis. Du startest mit frischem
Kontext — lies zuerst die unten genannten kanonischen Quellen, dann arbeite die zwei Aufträge ab.
**Der Nutzer (Jörg) hat drei Bewertungen abgegeben, die als Leitplanken gelten — sie stehen in
Abschnitt 3 und sind bindend für deine Vorschläge.**

---

## 0. Zuerst lesen (kanonische Quellen, in dieser Reihenfolge)

1. `haushaltskasse/docs/BACKLOG.md` (v3.4) — die Steuerdatei, alle 58 Punkte mit Reifegrad.
2. `haushaltskasse/docs/CODE-ANALYSE-2026-07-16.md` — **Schritt 1** (grobe Übersicht + Risiken), die du reviewen sollst.
3. `haushaltskasse/docs/CODE-ANALYSE-DEEP-DIVE-I.md` — **Deep Dive I** (Geld-Logik, read-only gegen Live-DB verifiziert), den du ebenfalls reviewen sollst.
4. Kern-Code: `storage/schema.sql`, `dashboard/queries.py`, `dashboard/app.py`, `workflows/gegenbuchung.py`, `workflows/beladung.py`, `workflows/allgemein_toepfe.py`, `workflows/allgemein_verteilen.py`, `workflows/kategorie_cleanup.py`.

**Arbeitsregeln:**
- **Nur read-only gegen die Live-DB** (Connection kommt aus `.env` → `HAUSHALT_DATABASE_URL`). Wie in Deep Dive I: SELECTs zum Nachrechnen, **kein** Schreibzugriff, **kein** Deploy, **keine** Migrations-Skripte mit `--write`.
- Für read-only-Checks: Skript ins Scratchpad legen und mit `PYTHONPATH` auf das Repo-Root laufen lassen (Muster: das war in Deep Dive I so gemacht — `PYTHONIOENCODING=utf-8 PYTHONPATH=<repo> python skript.py`).
- Deine Ergebnisse sind **Analyse + Vorschläge als MD-Dokumente**, kein Produktivcode-Umbau. Jörg entscheidet danach, was umgesetzt wird.

---

## 1. Auftrag A — Gegencheck von Übersicht (Schritt 1) + Deep Dive I

Prüfe die beiden bestehenden Analyse-Dokumente **kritisch**, nicht bestätigend. Konkret:

- **Rechne die zentralen Zahlen aus Deep Dive I selbst nach** (read-only gegen die Live-DB): geht der Wasserfall wirklich cent-genau auf? Stimmt die #52-Drift-Zerlegung (+746,86 = −5.313,14 Rücklage-Zuführung + 6.060,00 Forderung Jörg)? Sind Spiegel wirklich 0 verwaist / 0 doppelt?
- **Suche nach übersehenen Fehlern.** Deep Dive I hat vier Invarianten geprüft — gibt es weitere Saldo-Pfade, die driften können? Prüfe insbesondere: die drei Saldo-Definitionen (`kennzahlen()` vs. `haushaltssaldo()` vs. `haushaltssaldo_per_stichtag()`), die Behandlung von `buchungsart IN ('wertpapier','zinsen')` im Saldo, die Reports-Filter (`quelle_import <> 'startsaldo'`), und ob die Konsistenz-Falle „`gruppe` vs. `im_haushaltssaldo`" (Deep Dive I, Befund C) wirklich nur latent ist.
- **Bewerte, ob die Risiko-Einstufung in Schritt 1 angemessen ist** — zu hoch/zu niedrig? Fehlt ein Risiko?
- **Ergebnis:** `docs/CODE-ANALYSE-REVIEW-FABLE.md` — je Befund: bestätigt / widerlegt / ergänzt, mit deiner Nachrechnung als Beleg. Sei explizit, wenn du etwas anders siehst als Opus.

---

## 2. Auftrag B — Deep Dive II erstellen (Struktur, Betrieb & Wartbarkeit)

Das ist der Haupt-Auftrag: die noch fehlende dritte Analyse-Ebene. **Fokus: nicht die Rechen-Korrektheit
(das war Deep Dive I), sondern wie der Code gebaut ist und wie der Betrieb läuft.** Erarbeite
**konkrete, priorisierte Vorschläge** (nicht nur Befunde) zu:

1. **`app.py`-Monolith** (652 Zeilen, 35 Routen, Logik + Web-Handler + Pydantic-Modelle in einer Datei) — konkreter Schnitt-Vorschlag (Router-Aufteilung, Service-Schicht), inkl. grober Aufwandsschätzung.
2. **Import-Pipeline** (CLI `pipeline.py` vs. Web `web_import.py`): Robustheit von Dedupe/Abgrenzung, die `lokale_config`-Lücke im Container (grobe Abgrenzung ohne IBANs, Backlog #22), Amazon-Parser noch `.xls` (Merker: auf CSV umstellen).
3. **Deploy & Betrieb**: heute manuell + PC-gebunden (ACR-Build, `APP_VERSION` von Hand). Vorschlag für **GitHub-Actions-Auto-Deploy mit Test-Gate** (löst zugleich #23b/V1b „Tests" und den Handy-Workflow). Beachte Leitplanke 3.2 unten.
4. **Backup** (aktuell keins, #33): pg_dump/Restore-Konzept, Rhythmus, Ablageort.
5. **Datenschutz-Struktur**: die Trennung private Daten ↔ Git ist heute reine Disziplin (`.env`, `lokale_config.json` gitignored). Härtungs-Optionen. Beachte Leitplanke 3.1 unten.
6. **Test-Strategie**: das in Deep Dive I vorgeschlagene pytest-Invarianten-Set konkretisieren — **inkl. der offenen Frage, woher eine Test-DB kommt** (lokale Postgres? Docker/Testcontainers? read-only-Invarianten gegen die Live-DB?). Das ist der Blocker für #23b — bitte einen umsetzbaren Weg vorschlagen.

**Ergebnis:** `docs/CODE-ANALYSE-DEEP-DIVE-II.md` — priorisierte Roadmap, je Punkt: Problem, Vorschlag, Aufwand (grob), Abhängigkeiten. Wenn sinnvoll, aus den Vorschlägen neue Backlog-Punkte ableiten und in `BACKLOG.md` eintragen (Version hochzählen).

---

## 3. Leitplanken des Nutzers (bindend)

Jörg hat die drei „Hoch"-Risiken aus Schritt 1 kommentiert. Deine Vorschläge müssen das respektieren:

### 3.1 Zwei Einstiegswege in die DB (CLI-Workflows + Web) — **kein Abschaffen, sondern Härten**
> Jörg: *„bewerte ich als Deploy-/Admin-Zugang — brauchen wir, sonst auch keine Bereinigungsläufe möglich … ggf. absichern, härten."*

Der doppelte Zugang (CLI-Skripte + Web-Dashboard) ist **gewollt** — die CLI-Workflows sind der
Admin-/Wartungszugang (Migration, Gegenbuchungs-Sync, Cleanup, Topf-Verteilung), ohne den keine
Bereinigungsläufe möglich wären. **Stelle ihn nicht in Frage.** Erarbeite stattdessen
**Härtungs-Vorschläge**: z. B. Trockenlauf-Pflicht (ist bei den meisten schon so), Audit/Logging der
Write-Läufe, Schutz gegen versehentliches `beladung --write` (TRUNCATE!), ggf. Bestätigungs-Prompt
oder Backup-vor-Write, klare Trennung „Alltag im Web / Struktureingriffe nur CLI".

### 3.2 Vorzeichen-/Rollen-Logik ist fragil und verstreut — **hohe Priorität, Jörg teilt die Sorge**
> Jörg: *„das gefällt mir auch gar nicht."*

Die Bedeutung von `zaehlt_als`, `buchungsart`, den Spiegel-Buchungen und `im_haushaltssaldo` greift
über mehrere Dateien ineinander; ein falsches Vorzeichen verschiebt den Saldo lautlos (Bug-Klasse
#52/#9, Deep-Dive-I-Befund C). **Das ist der wichtigste inhaltliche Auftrag.** Erarbeite konkrete
Vorschläge zur **Entschärfung**: z. B. die Saldo-/Vorzeichen-Logik an **einer** Stelle konsolidieren
(single source of truth), einheitlicher Diskriminator (`gruppe` vs. `im_haushaltssaldo` angleichen),
Invarianten als automatische Tests (die 4 aus Deep Dive I + weitere), evtl. eine kleine Typ-/Enum-Schicht
statt String-Vergleichen. Ziel: Änderungen an der Geld-Logik dürfen kein Blindflug mehr sein.

### 3.3 Migrations-Reihenfolge ist Herrschaftswissen — **verständlich erklären + in Code gießen**
> Jörg: *„versteh ich nicht, aber ok …"*

Hintergrund (bitte in Deep Dive II **verständlich** erklären): Das Skript `beladung --write` leert die
Buchungstabelle und lädt neu (TRUNCATE + Reimport). Danach sind die automatisch erzeugten
Gegenbuchungen (Topf-Verzehr, `gegenbuchung`) und die Topf-Zuordnungen (`allgemein_toepfe`) **weg** und
müssen zwingend erneut laufen — sonst stimmen Rollen und Salden nicht mehr. Diese Reihenfolge lebt heute
nur in Handover-Dokumenten und im Kopf. **Vorschlag erarbeiten**, wie man das in Code gießt: z. B. ein
einziges Orchestrierungs-Kommando `python -m …workflows.reload`, das die Schritte in der richtigen
Reihenfolge (Trockenlauf → Bestätigung → beladung → gegenbuchung → allgemein_toepfe) selbst ausführt,
sodass niemand die Reihenfolge mehr von Hand kennen muss.

---

## 4. Deliverables & Abschluss

- `docs/CODE-ANALYSE-REVIEW-FABLE.md` (Auftrag A)
- `docs/CODE-ANALYSE-DEEP-DIVE-II.md` (Auftrag B)
- ggf. neue Backlog-Punkte in `BACKLOG.md` (Version hochzählen, Reifegrad 💡/📐)
- Am Ende committen + pushen (Branch `claude/status-update-bpmbn2` oder ein neuer `YYYY-MM-DD-…`-Branch;
  Commit-Konvention wie im Repo, Co-Authored-By-Zeile). **Nicht deployen** — reine Analyse.

Wenn etwas unklar ist oder du auf einen echten Bug stößt (nicht nur Struktur), halte es im jeweiligen
Dokument fest und markiere es als „für Jörg zu entscheiden".
