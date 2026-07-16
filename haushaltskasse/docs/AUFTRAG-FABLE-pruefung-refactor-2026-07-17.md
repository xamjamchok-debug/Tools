# Auftrag an Fable — Gründliche Prüfung des Deep-Dive-II-Refactors (P1–P9)

**Erstellt 2026-07-17 (von Opus, für Fable-Session) · Projekt: Haushaltskasse**

Der große Refactor aus deiner eigenen Deep-Dive-II-Roadmap (P1–P9) ist inzwischen **umgesetzt,
committet und live deployt** (Commit `4ab5b9a`, Container-Revision `0000012`, `/health` bestätigt
`"version":"4ab5b9a"`). Er wurde in einer hängengebliebenen Fable-Session gebaut, von Opus
uncommittet vorgefunden, verifiziert und gelandet. **Dein Auftrag jetzt: diesen deployten Stand
kritisch gegenprüfen** — nicht bestätigend. Suche, was der Umbau übersehen, verschoben oder
kaputtgemacht hat.

---

## 0. Zuerst lesen (kanonische Quellen, in dieser Reihenfolge)

1. `docs/BACKLOG.md` (v3.7) — Steuerdatei, alle Punkte + Reifegrad. Oben der Deploy-Vermerk P1–P9.
2. `docs/CODE-ANALYSE-DEEP-DIVE-II.md` — **deine eigene Roadmap** (P1–P9). Der Soll-Zustand.
3. `docs/CODE-ANALYSE-DEEP-DIVE-I.md` — die Geld-Logik + die vier verifizierten Invarianten.
4. `docs/DELTA-2026-07-16-1620-Handy-anPC.md` — u. a. die Umkat-/Spiegel-Erkenntnis.
5. Kern-Code **im neuen Zuschnitt**: `domain/saldo.py`, `dashboard/app.py` (jetzt ~45 Z.),
   `dashboard/routes/*.py`, `dashboard/helpers.py`, `dashboard/queries.py`, `storage/db.py`,
   `storage/schema.sql`, `workflows/{web_import,gegenbuchung,reload,audit,invarianten,
   lokale_config}.py`, `dashboard/auth.py`, `.github/workflows/{ci,backup}.yml`, `tests/*`.

**Arbeitsregeln (unverändert, bindend):**
- **Nur read-only gegen die Live-DB** (`.env` → `HAUSHALT_DATABASE_URL`). SELECTs zum Nachrechnen,
  **kein** Schreibzugriff, **kein** Deploy, **keine** `--write`-Läufe.
- Read-only-Skripte ins Scratchpad, mit `PYTHONIOENCODING=utf-8 PYTHONPATH=<repo> python skript.py`.
- Ergebnis sind **MD-Dokumente (Analyse + Vorschläge)**, kein Produktivcode-Umbau. Jörg entscheidet.
- Tests laufen lassen ist erlaubt und erwünscht: `pytest haushaltskasse/tests -v` (nutzt
  `HAUSHALT_TEST_DATABASE_URL`, **nicht** die Live-DB).

---

## 1. Auftrag A — Regressions-Jagd: hat der Refactor Verhalten verändert?

Das ist der wichtigste Teil. Der Umbau hat `app.py` (640 → 45 Z.) in `dashboard/routes/` zerlegt
und die Geld-Logik nach `domain/saldo.py` gezogen. **Prüfe systematisch, ob dabei nichts verloren
ging oder sich still verändert hat:**

- **Endpoint-Vollständigkeit:** Vergleiche die Routen des alten Monolithen (git: `git show
  56b4f61:haushaltskasse/dashboard/app.py`) mit der Summe aus `routes/*.py`. Fehlt ein Endpoint?
  Hat sich ein Pfad, eine Methode, ein Query-Parameter oder ein Default geändert? Liste jede
  Abweichung.
- **Geld-Logik-Äquivalenz:** `domain/saldo.py` soll *single source of truth* sein (P2-Ziel).
  Prüfe, ob `queries.py`, `db.kennzahlen()` und `gegenbuchung.py` wirklich **dieselben** SQL-
  Fragmente/Regeln benutzen — oder ob irgendwo noch eine eigene, abweichende WHERE-Klausel steht
  (Streu-Strings `'startsaldo'`, `'ruecklage'`, FB_QUELLEN …). Jede verbliebene Doppelung ist ein
  Befund.
- **Bugfix B7 nachrechnen:** `kennzahlen()` weist Forderungen jetzt separat aus (nicht mehr in
  `summe_ruecklagen`). Rechne die drei Größen (Realsaldo, Rücklagen, Forderungen) read-only nach
  und vergleiche mit `queries.haushaltssaldo()` — sind sie konsistent, oder gibt es jetzt zwei
  Wahrheiten?
- **Die vier Invarianten aus Deep Dive I** erneut gegen die Live-DB fahren (Spiegel: 0 verwaist /
  0 doppelt; Wasserfall cent-genau; #52-Drift-Zerlegung; Rücklagen = Σ Untertöpfe). Halten sie
  **nach** dem Refactor + nach der Schema-Migration (neuer CHECK, `admin_laeufe`) noch?
- **Ergebnis-Teil A:** je Befund bestätigt/widerlegt/neu, mit Nachrechnung als Beleg.

## 2. Auftrag B — Sind P1–P9 wirklich fertig, oder nur „da"?

Für **jeden** Punkt: umgesetzt wie in Deep Dive II entworfen? Vollständig? Laufzeit-erprobt oder nur
importierbar? Konkret die Zweifelsfälle:

- **P1 Web-Import-Spiegelfix:** Ruft `importiere_upload()` wirklich `sync_gegenbuchungen(cur)` in
  **derselben** Transaktion vor dem Commit, und **nicht** `korrigiere_stammdaten` (das liest die
  lokale Excel-FB, die es im Container nicht gibt)? Ist es idempotent bei erneutem Import?
- **P2 `domain/saldo.py`:** s. Auftrag A. Zusätzlich: ist die Abstraktion zu dünn/zu dick? Fehlt
  ein Diskriminator (`buchungsart` wertpapier/zinsen, `gruppe` vs. `im_haushaltssaldo`)?
- **P3/P4 Tests + CI:** Die CI ist **grün** (2 Runs). Aber: decken die Tests die Invarianten
  wirklich ab, oder sind es Attrappen? Welche 6 sind lokal *skipped* und laufen sie in CI (echtes
  Postgres) durch? Fehlen Tests für die riskanten Pfade (Umkategorisieren→Spiegel, Web-Import,
  config_fluss-Klassifikation)?
- **P5 `reload.py`/`audit.py`/`admin_laeufe`:** Wird der Audit-Lauf tatsächlich geschrieben und die
  Invarianten-Prüfung ausgeführt? Verriegelt `beladung` gegen versehentliches TRUNCATE? (Bisher
  gebaut, aber **nicht** laufzeit-erprobt — sag, ob es hält.)
- **P6 Backup (`backup.yml`):** Der wöchentliche `pg_dump` ist **noch nie gelaufen**. Prüfe den
  Workflow auf Fallstricke: Firewall-Öffnen/Schließen (`always()`), Secret `HAUSHALT_DATABASE_URL`,
  Artefakt-Retention. Ist der PITR-Claim (14 Tage) belegt/belegbar?
- **P7 Auth fail-hard:** `erzwinge_produktions_config()` läuft beim **Import** (`app.py:19`). Gibt es
  einen Pfad, auf dem die App in Produktion doch ohne Login hochkommt (z. B. `HTTPS_ONLY` nicht
  gesetzt, aber öffentlich erreichbar)? Ist die Fehlermeldung deutlich genug?
- **P8 Router-Schnitt:** s. Auftrag A (Vollständigkeit).
- **P9 `lokale_config` Datei-ODER-DB:** **Datenschutz-Fokus.** Wenn die persönliche Config
  (IBANs, Namens-Regex) in die DB-Tabelle `einstellungen` gespiegelt wird (`--push`) — taucht sie
  irgendwo wieder auf, wo sie nicht hingehört? Prüfe: CSV-Exporte, Reports, `admin_laeufe`-JSON,
  Logs, die read-only-SQL-Konsole (falls #21 existiert). Ein Leck hier ist ein ernster Befund.

## 3. Auftrag C — Zwei offene Betriebspunkte bewerten

1. **Auto-Deploy von `master` via OIDC** (`.github/workflows/ci.yml`, deploy-Job): der Test-Job ist
   grün, der **deploy-Job wurde nie ausgeführt** (läuft nur auf `master`). Prüfe, ob die
   GitHub-`vars` `AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID` und die OIDC-Federation überhaupt
   eingerichtet sind, und beschreibe **exakt**, was fehlt, damit ein Merge auf `master` sauber
   deployt (ohne dass Jörg raten muss). **Nur beschreiben, nicht ausführen.**
2. **`lokale_config --push`:** ist im Container noch nicht passiert → der Web-Import grenzt ohne
   IBANs nur grob ab (#22-Rest, #55). Bewerte Risiko/Reihenfolge und ob `--push` sicher ist.

## 4. Auftrag D — Fachfrage Config-Monatsfluss (offen, Jörg-Entscheid nötig)

`queries.config_fluss` klassifiziert seit **#47** am **Vorzeichen** des Soll (Rolle schlägt
Vorzeichen): Rücklage→Ausgaben, Forderung→Forderungen, sonst Soll>0→Einnahmen. Aktueller Live-Stand:
Einnahmen = leer, Forderungen = Jörg (+6.060) & Natalie (0), Ausgaben = alle Rücklagen-Töpfe.

Jörgs Wunsch (2026-07-17, noch unscharf, **bitte als Vorschlag ausarbeiten, nicht umsetzen**):
„Einnahmen raus — Kindergeld; Natalie und Kindergeld in Forderungen." Offene Punkte, die du klären/
durchdenken sollst:
- **Kindergeld** ist heute eine *Unterkategorie* von Füchschen (Rolle ruecklage), mit
  `ist_einnahme=TRUE`. Soll es eine **Forderung** werden (Geld, das den Kindern gehört, analog
  Natalie/Jörg)? Das kollidiert mit **#49** (Kategorie „Kinder" wurde bewusst entfernt, alles unter
  Füchschen). Wie löst man das ohne Wiedergänger-Kategorie?
- Verhältnis zu **#58** („Forderungen im Config-Monatsfluss als Einnahmen führen") und **#47**
  (Vorzeichen) — die drei Wünsche müssen zu **einer** widerspruchsfreien Klassifikations-Regel
  zusammengeführt werden. Schlag genau **eine** Regel vor, mit Beispiel-Zeilen und dem resultierenden
  Monats-Saldo.
- **Ergebnis-Teil D:** ein Abschnitt „config_fluss v2" mit der vorgeschlagenen Regel + Migrations-/
  Datenschritten (welche Kategorie/Rolle/Soll ändert sich), damit Jörg nur noch Ja/Nein sagt.

---

## 5. Deliverables

- `docs/CODE-ANALYSE-REVIEW-REFACTOR-FABLE.md` — Aufträge A–C, je Befund bestätigt/widerlegt/neu
  mit Beleg; am Ende eine **priorisierte Restpunkt-Liste** (was ist wirklich noch offen, wie
  dringend).
- `docs/config-fluss-v2-vorschlag.md` — Auftrag D.
- **Sei explizit, wenn du etwas anders siehst als Opus.** Der Refactor ist live — ein übersehener
  Regressions-Befund ist wertvoller als zehn Bestätigungen.
