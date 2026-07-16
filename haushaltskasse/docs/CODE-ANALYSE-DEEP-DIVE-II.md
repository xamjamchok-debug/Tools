# Code-Analyse Haushaltskasse — Deep Dive II: Struktur, Betrieb & Wartbarkeit

**Stand 2026-07-16 · Analyse-Ebene 3 von 3 · Autor: Fable**
Vorgänger: [Übersicht](CODE-ANALYSE-2026-07-16.md) · [Deep Dive I (Geld-Logik)](CODE-ANALYSE-DEEP-DIVE-I.md) ·
[Fable-Review](CODE-ANALYSE-REVIEW-FABLE.md). **Reine Analyse mit Vorschlägen — kein Code geändert.**

Jörgs drei Leitplanken sind eingearbeitet: der doppelte DB-Zugang (CLI + Web) wird **gehärtet, nicht
abgeschafft** (§4) · die Vorzeichen-/Rollen-Logik wird **konsolidiert** (§2, wichtigster Punkt) ·
die Migrations-Reihenfolge wird **erklärt und in Code gegossen** (§4).

---

## 0. Roadmap auf einen Blick (priorisiert)

| Prio | Vorschlag | Löst | Aufwand* | Hängt an |
|---|---|---|---|---|
| **P1** | Spiegel-Sync im Web-Import (Bugfix, ~3 Zeilen) | Review-Befund F1, #59 | 0,25 | — |
| **P2** | Geldlogik-Modul `saldo.py` (single source of truth) | Leitplanke 3.2, #60 | 1–2 | — |
| **P3** | pytest-Invarianten + Szenario-Tests (Test-DB: s. §3) | #23b, Blindflug-Ende | 1–2 | P2 sinnvoll vorher |
| **P4** | GitHub-Actions: Test-Gate + Auto-Deploy | #62, PC-Bindung, Handy-Workflow | 1 | P3 (Gate braucht Tests) |
| **P5** | `reload`-Orchestrierung + `beladung`-Verriegelung | Leitplanke 3.3, Review-F2, #61 | 0,5–1 | — |
| **P6** | Backup: Azure-PITR verifizieren + wöchentlicher `pg_dump` | #33 | 0,5 | — |
| **P7** | Auth-Härtung (fail-hard) + Datenschutz-Absicherung | #63 | 0,5 | — |
| **P8** | `app.py`-Schnitt in Router-Pakete | Monolith-Risiko | 1–2 | am besten nach P2/P3 |
| **P9** | Import-Pipeline-Pflege (lokale_config→DB, Amazon-CSV, `_match_db`) | #22-Rest, Merker | 0,5–1 | — |

\* Aufwand in Arbeitssessions à ~1–2 h. **Empfohlene Reihenfolge: P1 sofort, dann P2→P3→P4 als
zusammenhängender Block („nie wieder Blindflug"), P5–P7 unabhängig einschiebbar, P8/P9 danach.**

---

## 1. P1 — Spiegel-Sync im Web-Import (der Pflicht-Quick-Win)

**Problem** (Review-Befund F1, empirisch belegt): `importiere_upload()` legt Realbuchungen an, ruft
aber nie die Gegenbuchungs-Synchronisation auf. Topf-pflichtige Ausgaben aus einem Handy-Import
verfälschen den Saldo, bis am PC `gegenbuchung --write` läuft.

**Vorschlag:** Am Ende von `importiere_upload()` — in derselben Transaktion, vor dem `commit()` —
`sync_gegenbuchungen(cur)` aufrufen (aus `workflows.gegenbuchung`, ist idempotent und schnell).
Der Import-Bericht bekommt eine Zeile „n Gegenbuchungen erzeugt". Damit ist der Web-Pfad dem
CLI-Pfad gleichgestellt. *Achtung: nur `sync_gegenbuchungen`, **nicht** `korrigiere_stammdaten` —
letzteres liest die lokale Excel-FB, die es im Container nicht gibt.*

---

## 2. P2 — Die Vorzeichen-/Rollen-Logik konsolidieren (Leitplanke 3.2, Kernstück)

**Problem, präzise:** Die Geld-Semantik steckt heute in **vier String-Welten**, die an ≥ 9 Stellen
unabhängig interpretiert werden:

| Diskriminator | Werte | interpretiert in |
|---|---|---|
| `buchungsart` | real/ruecklage/umbuchung/wertpapier/zinsen | queries (6×), gegenbuchung, beladung, web_import, app.py |
| `zaehlt_als` | ruecklage/forderung/ausgabe | queries (4×), gegenbuchung, config_fluss |
| `im_haushaltssaldo` + `gruppe` | bool + posten/merkzettel | haushaltssaldo(), uebersicht(), export |
| `quelle_import` | fb-dkb/fb-kto/startsaldo/spiegel/verteilung/manuell/… | gegenbuchung (FB_QUELLEN), Reports-Filter, Dedupe |

Jede Stelle schreibt die WHERE-Klausel selbst. Der Web-Import-Bug (P1) ist genau so entstanden:
die „jede berechtigte Realbuchung braucht einen Spiegel"-Regel war an zwei von drei Schreibpfaden
implementiert, am dritten vergessen.

**Vorschlag — neues Modul `haushaltskasse/domain/saldo.py`** (bewusst klein, kein Framework):

1. **Konstanten/Enums statt Streu-Strings:** `Buchungsart`, `Rolle`, `FB_QUELLEN`, `QUELLE_SPIEGEL`
   … einmal definiert, überall importiert (heute definiert z. B. `gegenbuchung.py` die FB_QUELLEN,
   und `queries.py` schreibt `'startsaldo'` als Literal).
2. **SQL-Bausteine als benannte Fragmente:** z. B. `SQL_BERECHTIGT_FUER_SPIEGEL` (die vollständige
   Bedingung aus `sync_gegenbuchungen`), `SQL_RUECKLAGEN_SUMME`, `SQL_FORDERUNGS_SUMME`,
   `SQL_POSTEN_IM_SALDO`. `queries.py`, `gegenbuchung.py` und die Tests verwenden **dieselben**
   Fragmente — eine Änderung an der Regel ändert alle Verwender gleichzeitig.
3. **Die Saldo-Formel genau einmal:** `haushaltssaldo(cur, stichtag=None)` wandert hierher;
   `queries.haushaltssaldo()` und `haushaltssaldo_per_stichtag()` werden dünne Aufrufer desselben
   Codes (heute: zwei fast identische Funktionen, die auseinanderdriften können).
   `db.kennzahlen()` wird entweder darauf umgestellt oder als „Diagnose (mischt Forderungen)" markiert.
4. **Diskriminator vereinheitlichen** (Deep-Dive-I-Befund C): Entscheidung nötig —
   Vorschlag: `im_haushaltssaldo` bleibt die *einzige* Saldo-Wahrheit, `gruppe` ist *reine Anzeige*;
   dazu ein CHECK-Constraint `(gruppe <> 'merkzettel' OR im_haushaltssaldo)` in `schema.sql`,
   der die latente Falle hart macht statt latent.
5. **Invarianten als Funktionen** (`pruefe_invarianten(cur) -> list[str]`): die vier aus Deep Dive I
   + „Σ Spiegel == Σ berechtigte Realbuchungen" (Review-B2). Aufrufbar aus Tests **und** als
   Abschluss-Check jedes Write-Workflows (Härtung §4).

**Nicht** vorgeschlagen: ORM, Migration auf SQLAlchemy o. ä. — der rohe psycopg-Stil ist konsistent
und schnell; das Problem ist die Streuung, nicht das SQL.

**Aufwand:** 1–2 Sessions (mechanisches Umziehen + gezieltes Nachtesten der vier Sichten).

---

## 3. P3 — Test-Strategie inkl. Antwort auf die Test-DB-Frage (#23b)

**Zwei Schichten, zwei DB-Quellen:**

**Schicht 1 — Invarianten-Checks (read-only, DB-agnostisch).** Die `pruefe_invarianten()` aus P2
laufen gegen *jede* DB, auch die echte: (1) Wasserfall == Saldo · (2) Σ Merkzettel + Σ Posten ==
Σ im_saldo · (3) 0 verwaiste/doppelte Spiegel · (4) kein Rücklagen-Topf < 0 (bzw. Whitelist) ·
(5) Σ Spiegel == Σ berechtigte Realbuchungen · (6) 0 pathologische Zeilen (Review-B4).
Als `pytest`-Datei UND als CLI (`python -m haushaltskasse.workflows.invarianten`) — Letzteres kann
Jörg jederzeit gegen die Live-DB laufen lassen („Ist gerade alles konsistent?").

**Schicht 2 — Szenario-Tests (schreibend, Wegwerf-DB).** Fixture baut Schema via `init_db()`, sät
Minimal-Stammdaten (2 Konten, 3 Kategorien mit allen drei Rollen, 1 Posten je Gruppe) und spielt
Szenarien: Import → Spiegel entsteht (hätte P1 gefangen) · Umkategorisieren → Spiegel wandert ·
Umkategorisieren auf 'ausgabe' → Spiegel verschwindet · `kategorie_cleanup` 2× → No-Op ·
Saldo-Neutralität einer topf-gedeckten Ausgabe.

**Woher kommt die Wegwerf-DB? Empfehlung: gar nicht lokal lösen, sondern in CI.**
GitHub Actions bietet Postgres als Service-Container nativ an (`services: postgres:16` + Health-Check,
`HAUSHALT_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test`). Kein Docker auf dem PC
nötig, nichts zu installieren, jede Push löst die Tests aus. **Lokal** bleiben zwei Optionen für
Bedarfsfälle: (a) Docker Desktop, falls vorhanden (`docker run -e POSTGRES_PASSWORD=x -p 5433:5432
postgres:16-alpine`), oder (b) nur Schicht 1 gegen die Live-DB laufen lassen (read-only, gefahrlos).
Die Handy-Cloud-Sessions haben ohnehin schon „Wegwerf-Postgres" benutzt — derselbe Mechanismus.

**Aufwand:** 1–2 Sessions (Schicht 1 ist in Stunden fertig, da die Queries aus Deep Dive I/diesem
Review schon existieren; Schicht 2 braucht die Fixtures).

---

## 4. P5 — Betriebshärtung: `reload`-Orchestrierung + Verriegelung (Leitplanken 3.1 + 3.3)

**Erst die verständliche Erklärung** (Jörg: „versteh ich nicht, aber ok"):

> Es gibt ein Altwerkzeug `beladung`, das die Datenbank **komplett leert** und aus den alten Quellen
> (Excel-Fuchsbaukasse + Kontoauszugs-Dateien) **neu befüllt**. Es stammt aus der Migrations-Zeit, als
> die Excel die Wahrheit war und die DB nur eine Kopie. Nach so einem Neuaufbau fehlen alle Dinge,
> die *nur* in der DB lebten: die automatischen Gegenbuchungen und die „Allgemein"-Topf-Zuordnungen —
> deshalb mussten danach immer zwei Reparatur-Skripte laufen, und zwar in dieser Reihenfolge. Das war
> das „Herrschaftswissen". **Inzwischen ist aber die DB selbst die Wahrheit** (dein Entscheid): sie
> enthält manuelle Buchungen, Bemerkungen, Umkategorisierungen und Web-Importe, die in keiner Excel
> und keiner Datei mehr stehen. Ein heutiger `beladung --write` würde die **unwiederbringlich löschen**
> — die Reparatur-Skripte stellen davon nichts wieder her (Review-Befund F2). Das Werkzeug ist also
> vom „gefährlich, wenn falsche Reihenfolge" zum „gefährlich, überhaupt" geworden.

**Vorschläge (Härten, nicht abschaffen — Leitplanke 3.1):**

1. **Verriegelung von `beladung --write`:** Abbruch mit Erklärung, wenn die DB Buchungen enthält,
   die beim Reload verloren gingen (`quelle_import IN ('manuell','verteilung','spiegel') OR
   bemerkung IS NOT NULL OR kat_pinned` und nicht aus FB-Quellen). Override nur mit explizitem
   Flag `--zerstoere-manuelle-daten` **plus** automatischem `pg_dump` davor (P6-Baustein).
2. **Ein Orchestrierungs-Kommando `python -m haushaltskasse.workflows.reload`:** führt die korrekte
   Kette selbst aus — Trockenläufe aller Schritte, Anzeige, eine einzige Bestätigung, dann
   `beladung → gegenbuchung → allgemein_toepfe` in fester Reihenfolge, am Ende `pruefe_invarianten()`.
   Niemand muss die Reihenfolge mehr kennen; das Wissen steht im Code.
3. **Audit-Log für Write-Läufe:** kleine Tabelle `admin_laeufe` (werkzeug, args, zeit, kennzahlen
   vorher/nachher). Jeder `--write`-Lauf trägt sich ein — beantwortet später „was lief wann?".
4. **Invarianten-Check als Abschluss jedes Write-Workflows** (aus P2/P3): Skripte drucken am Ende
   „Invarianten: OK" oder brechen mit klarer Meldung ab (vor dem Commit → Rollback).
5. **Trockenlauf-Konvention vereinheitlichen:** alle Workflows haben sie schon — nur `beladung`
   truncated auch im Dry-Run (transaktional + Rollback, aber mit exklusivem Lock, der das Dashboard
   blockiert). Im Dry-Run auf eine reine Zähl-/Vorschau-Abfrage umstellen.

**Aufwand:** 0,5–1 Session.

---

## 5. P4 — Deploy & Betrieb: GitHub Actions mit Test-Gate (#62)

**Problem:** Deploy ist manuell + PC-gebunden (Azure-CLI-Login nur dort), `APP_VERSION` von Hand,
kein Gate. Handy-Sessions können bauen, aber nicht ausrollen.

**Vorschlag — ein Workflow `.github/workflows/deploy.yml`:**
1. **Trigger:** Push auf `master` (bzw. manueller `workflow_dispatch` für Branches).
2. **Job 1 „test":** Checkout → Python + Abhängigkeiten → Postgres-Service-Container (§3) →
   `pytest`. Schlägt er fehl, endet der Lauf hier — **das Test-Gate**.
3. **Job 2 „deploy"** (nur nach grünem Job 1): Azure-Login per **OIDC/Federated Credentials**
   (kein Passwort-Secret; einmalig App-Registrierung + Rollenzuweisung auf die RG) →
   `az acr build -r hhkassec1k7wx …` → `az containerapp update … --set-env-vars
   APP_VERSION=${GITHUB_SHA::7}` per **Image-Digest**. Genau die heutigen PC-Schritte, automatisiert —
   inklusive der Fallstricke, die schon dokumentiert sind (Digest statt Tag, APP_VERSION Pflicht).
4. **Ergebnis:** committen + pushen (auch vom Handy) reicht; `/health` zeigt danach die neue SHA.
   Der PC bleibt als Admin-Zugang für CLI-Workflows — nur das *Deployen* wandert in die Cloud.

**Aufwand:** ~1 Session (der Azure-OIDC-Setup ist der einzige fummelige Teil, einmalig).

---

## 6. P6 — Backup (#33): erst verifizieren, dann ergänzen

**Wichtig zu wissen:** Azure Database for PostgreSQL **Flexible Server macht automatisch tägliche
Backups mit Point-in-Time-Restore** (Standard-Aufbewahrung 7 Tage, konfigurierbar bis 35). Es gibt
also vermutlich *schon heute* ein Backup — es weiß nur niemand genau.

1. **Verifizieren (15 min):** `az postgres flexible-server show -g haushaltskasse-rg -n hh-te86ka
   --query backup` — Aufbewahrung prüfen, ggf. auf 14–35 Tage erhöhen. Einmal einen Restore auf
   einen *neuen* Server durchspielen (das ist der eigentliche Test).
2. **Ergänzen — logischer Dump für „für immer":** PITR schützt vor Unfällen der letzten Tage, nicht
   vor „Konto/Abo weg" oder „Fehler erst nach 6 Wochen bemerkt". Vorschlag: wöchentlicher `pg_dump`
   als GitHub-Actions-Cron (Dump → verschlüsselt als Workflow-Artefakt mit 90 Tagen Aufbewahrung
   oder in einen Azure-Storage-Container). Alternativ manuell am PC monatlich; wichtig ist der Rhythmus.
3. **Kopplung an P5:** die `beladung`-Verriegelung nutzt denselben `pg_dump`-Baustein („Backup vor
   destruktivem Lauf").

**Aufwand:** 0,5 Session.

---

## 7. P7 — Datenschutz & Auth härten

1. **Fail-hard statt Warnung** (Review-F5): wenn `HAUSHALT_HTTPS_ONLY=1` (= Produktion) und kein
   `HAUSHALT_APP_PASSWORD_HASH` gesetzt ist → App **verweigert den Start**. Heute würde ein Deploy
   mit verlorener Env-Var die Finanzdaten offen ins Internet stellen (nur eine Konsolen-Warnung).
   Gleiches für `SESSION_SECRET`.
2. **Secret-Scan als Gate:** `gitleaks` (o. ä.) als erster Schritt im CI-Workflow (P4) — fängt
   versehentlich committete IBANs/Beträge/Connection-Strings, bevor sie im Remote landen. Die
   bisherige Disziplin-Grenze bekommt ein Netz.
3. **`lokale_config` in die DB** (#22-Verbesserung, schließt zugleich die Container-Lücke des
   Imports): eigene Tabelle `lokale_config` (eigene IBANs, Halter-/Kinder-Muster), gepflegt über
   die Config-Seite, gelesen von `web_import`/`abgrenzung`. Die Datei bleibt als lokaler Fallback.
   Damit erkennt auch der Container-Import Umbuchungen personenbezogen — heute grenzt er gröber ab.
4. **Kein Handlungsbedarf:** Session-Cookie (signiert, lax, https-only), bcrypt, timing-sicherer
   Vergleich — die Auth selbst ist solide gebaut.

**Aufwand:** 0,5 Session (1–3); Punkt 3 ist Teil von P9, wenn man ihn dort mitnimmt.

---

## 8. P8 — `app.py`-Schnitt (Monolith)

**Befund:** 652 Zeilen, 35 Routen, drei Verantwortungen (Views, JSON-API, Helfer/Modelle) in einer
Datei. Noch beherrschbar, aber jedes Feature verlängert sie (Bar-Konto kam und ging mit je ~70 Zeilen).

**Vorschlag (FastAPI-`APIRouter`, rein mechanisch):**

```
dashboard/
  app.py            # nur noch: App-Setup, Middleware, include_router(…)  (~60 Zeilen)
  helpers.py        # db(), _euro, _parse_euro, _eurozahl, Template-Filter
  routes/
    views.py        # die 8 GET-Seiten (/, /ruecklagen, /buchungen, …)
    api_buchungen.py# Kategorie/Bemerkung/Topf buchen+umbuchen
    api_stammdaten.py# Soll, Rolle, Default-Ukat, Unterkat-CRUD, Stichtag
    api_posten.py   # Vermögensposten upsert/delete
    exports.py      # die 4 CSV-Routen
```

Schreibende Geschäftslogik (heute SQL in den POST-Handlern) wandert mittelfristig in ein
`dashboard/writes.py` neben `queries.py` — als Gegenstück Lesen/Schreiben; das kann aber schrittweise
passieren (immer wenn ein Handler ohnehin angefasst wird). **Timing:** nach P2/P3 — mit Tests im
Rücken ist der mechanische Umzug risikolos; davor wäre er genau der Blindflug, den wir beenden wollen.

**Aufwand:** 1–2 Sessions.

---

## 9. P9 — Import-Pipeline-Pflege

1. **Amazon-Parser `.xls` → CSV** (bestehender Merker): `_dispatch` um `.csv`+„amazon" erweitern,
   Spaltenmapping prüfen, danach `xlrd` aus den Requirements. Wartet darauf, dass ein CSV-Export
   als Muster vorliegt.
2. **`_match_db`-Verbreiterung** (Review-F5): den `or pat.search(gesamt)`-Fallback entfernen oder
   auf `pattern_typ='verwendungszweck'` beschränken — sonst wirken Empfänger-Regeln unbeabsichtigt
   auf den Verwendungszweck (Teilstring-Fallen wie `arag`→„Garage" werden breiter).
3. **`lokale_config` → DB** (siehe P7.3).
4. **Dedupe:** der Multiset-Dedupe (Datum+Betrag+Konto) ist nach dem v2-Fix solide; keine Änderung
   empfohlen. Der doppelte Boden (`import_hash` UNIQUE) bleibt.

**Aufwand:** 0,5–1 Session (Punkt 1 erst, wenn ein Amazon-CSV vorliegt).

---

## 10. Neue/aktualisierte Backlog-Punkte

In `BACKLOG.md` (v3.6) eingetragen: **#59** Spiegel-Sync im Web-Import (🐞, P1) · **#60**
Geldlogik-Modul `saldo.py` (📐, P2) · **#61** `reload`-Orchestrierung + `beladung`-Verriegelung
(📐, P5) · **#62** GitHub-Actions Test-Gate + Auto-Deploy (📐, P4) · **#63** Auth fail-hard +
Secret-Scan (📐, P7). Aktualisiert: **#23b** (Test-Strategie konkretisiert, 📐) · **#33** (Backup:
PITR verifizieren + pg_dump, 📐).

## 11. Schlussbemerkung

Die Codebasis ist für ihr Alter (< 1 Monat) bemerkenswert diszipliniert — die Probleme sind nicht
Schlamperei, sondern **fehlende Netze unter einer schnell gewachsenen, korrekten Konstruktion**.
Die drei größten Hebel greifen ineinander: P2 macht die Geld-Regeln *einmalig*, P3 macht sie
*prüfbar*, P4 macht die Prüfung *unumgehbar*. Danach ist die Klasse von Fehlern, die Jörg zu Recht
beunruhigt (lautlose Vorzeichen-/Spiegel-Fehler), strukturell abgedeckt — nicht nur aktuell abwesend.
