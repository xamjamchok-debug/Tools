# Stand & To-Dos — Session 2026-07-18

**Snapshot dieser Session · 2026-07-18 · Branch `claude/statusupdate-gyso6v`**

> Was in **dieser** Session fertig, halbfertig oder frisch designt wurde — als Grundlage, die
> offenen Punkte jetzt gezielt abzuräumen. Kanonische Steuerdatei bleibt `BACKLOG.md` (v3.23);
> dieses Dokument ist der Delta-Stand von heute + die konkrete To-Do-Liste.

---

## 1. In dieser Session erledigt (committet, **noch nicht live**)

| # | Was | Datei | Zustand |
|---|---|---|---|
| Board-Bug | **Aufklappen springt nicht mehr weg** — der Detail-Toggle löste einen Fokus-Scroll unter der Sticky-Kopfleiste aus („Filter geht weg / springt aus dem Fokus"). Fix: `pointerdown`-`preventDefault` + Scroll-Position sichern + `scroll-margin-top`. | `docs/backlog-board.html` | ✅ committet/gepusht |
| Board-Bug | **Erledigte Punkte (#48 etc.) erscheinen jetzt als erledigt** statt als stufenloses „Idee" (0 Pips). Generator erkennt „✅ erledigt/geschlossen/obsolet" → Flag `erledigt` + `stage=4`; Board rendert durchgestrichen/abgeblendet + grüner „✅ Erledigt"-Chip + Summary-Filter. | `docs/gen_backlog_board.py`, `docs/backlog-board.html` | ✅ committet/gepusht |

> ⚠️ **Deploy nötig:** Das Board wird von der App unter **`/backlog`** ausgeliefert
> (`routes/views.py:28` liest `docs/backlog-board.html`). Die Fixes sind also erst nach dem
> **nächsten App-Deploy** sichtbar — sie hängen im selben Stau wie #88 (s. u.).

## 2. In dieser Session neu erstellt (Design-/Auftragsdokumente)

- **`docs/AUFTRAG-FABLE-geruest-vertraege-rueckstellung.md`** — kanonisches Design des Kern-Gerüsts
  (Vertragserkennung → Zuordnung → Rückstellung ableiten → Konfiguration → Rückstellungslauf +
  Gegenbuchung) **+ Fable-Beratungsauftrag** mit zwei Deliverables (Logik/Daten read-only gegen die
  DB · App-Design nur für Abgleich- und Schiefstellungs-Sicht).
- **Dieses Dokument** (`docs/STAND-2026-07-18-session-todos.md`).

## 3. In dieser Session präzisiert (Erkenntnisse, kein Code)

- **Code-Ist-Stand des Gerüsts erhoben** (gegen den echten Code, nicht nur das Backlog): Erkennung
  (`workflows/vertraege.py`, Trigger `views.py:218`), Zuordnung (`routes/api_vertraege.py`, #78),
  die Deckel-/Schiefstellungs-**Sicht** (`queries.vertraege()` queries.py:506) und der **Verzehr**
  (`workflows/gegenbuchung.py`) **stehen bereits**. Es fehlen die **Soll-Übernahme + Deckel-
  Durchsetzung als Vorgang (#82)** und der **monatliche Rückstellungslauf (#76)**.
- **Handy-Machbarkeit geklärt:** DB-Workflows (#76/#82) sind **vom Handy auslösbar** — GitHub
  Actions hat das DB-Secret (`backup.yml`, `workflow_dispatch`); als dispatchbare Action mit
  Trockenlauf-Default. **UI live bringen** geht **nicht** vom Handy, solange **#62 (OIDC-Auto-
  Deploy)** nicht eingerichtet ist (Deploy-Job in `ci.yml` rot).

---

## 4. To-Dos — jetzt gut abräumbar (priorisiert)

### 🔴 Deploy-Stau auflösen (blockiert von #62)
Committet/gebaut, aber nicht live:
- **#88** — „Neuer Vertrag" (manueller Budget-Topf) + „Einnahmen" aus Config raus (🔨 gebaut).
- **Board-Fixes** (dieser Session, s. o.).
→ **Entweder** einmal manuell am PC deployen, **oder** zuerst **#62** einrichten (danach alles
  handy-deploybar).

### 🔴 #62 — OIDC-Auto-Deploy einrichten (der Enabler)
Einmalig ~20–30 Min am PC / Azure-Portal: App-Registration + Federated Credential + die 3
GitHub-`vars` (`AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID`). Danach deployt jeder Merge auf
`master` automatisch — **die Voraussetzung, damit die konzertierte Aktion ganz vom Handy geht.**

### 🔴 #76 — Rückstellungslauf bauen (dringendster Fachpunkt, jetzt spec'd)
`workflows/rueckstellung.py`: 1×/Monat, je Nebenbuch Rate auf Untertopf / Rest auf Allgemein,
Deckelprüfung, `quelle_import='rueckstellung'`, **idempotent je Nebenbuch/Monat**, **rückwirkend**,
Trockenlauf-Default, Protokoll in `admin_laeufe`. **Algorithmus + Testreferenz** (die 8 centgenauen
31.07.-Buchungen) stehen in `AUFTRAG-FABLE-geruest-vertraege-rueckstellung.md`, Teil IV.
**Handy-nativ** als `workflow_dispatch`-Action baubar; kein Deploy nötig. Erster echter Lauf
frühestens **09/2026** (August ist vorab gestellt, bleibt unangetastet).

### 🟡 #82 — Großer Config-Abgleich (Soll-Übernahme + Deckel-Durchsetzung)
Logik designt, **UX offen → Fable-Deliverable 2**. Workflow-Teil (Soll schreiben, Deckel prüfen)
handy-machbar; interaktiver Abgleich braucht die UI (→ Deploy).

### 🟡 #84 — Untertopf-Drop-Ziele + „erkannt"-Haken auf dem Verträge-Reiter
UI-Ausbau, hängt am Deploy. Ergänzt #88.

### 🟢 Kleinere offene Bugs (gute „Aufräum"-Kandidaten)
- **#65** — Pin auf der Übersicht verschiebt die Zeilenausrichtung (feste Icon-Spalte).
- **#85** — Vermögensposten brauchen ein Gültig-/Wertdatum (Stichtags-Auswertung).
- **#15** — Salden nach Migration final gegenprüfen.
- **#87** — Release-Log mit Sekunden-Zeitstempel je Release (💡 offen).

---

## 5. Nächster Design-Auftrag (parallel, durch Fable)

**`AUFTRAG-FABLE-geruest-vertraege-rueckstellung.md`** — Fable berät das Gerüst kritisch, zwei
Deliverables: (1) **Logik & Architektur** read-only gegen die Live-DB (Erkennung an echten Daten,
Deckel-Reconciliation, #76 gegenrechnen, offene Frage „Allgemein→vertragsbasiert"); (2) **App-
Design** nur für die zwei undesignten Flächen (#82-Abgleich-Screen, Schiefstellung/Reichweite).
**#76 wird nicht gegatet** — reif, hat die Deadline, wird parallel gebaut.

---

## 6. Bewusst geparkt (nicht diese Session)

- **Kategorien-Feinarbeit** #70b/#71/#72/#73 (Müller-Fehlbuchung, PayPal-Händler auflösen,
  Versicherungs-Ist-Stand) — DB-Writes, warten auf Jörgs Durchsicht/OK.
- **#67** Monatsbewegung Δ je Unterkonto · **#70/F6** Sport bündeln vs. einzeln — Design/Klärung.
