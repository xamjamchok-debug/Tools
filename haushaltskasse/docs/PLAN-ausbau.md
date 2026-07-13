# Ausbauplan Haushaltskasse — Online + Analyse-Features

> Stand: 2026-07-13. Erstellt am PC, Fortsetzung vom Android-Handy geplant (claude.ai/code am
> selben Repo `github.com/xamjamchok-debug/Tools`, Branch `claude/status-update-bpmbn2`).
> Vor Gerätewechsel: committen + pushen; auf dem anderen Gerät: `git pull`.
>
> **Arbeitsweise vom Handy:** Diese Datei ist die Steuerdatei. Jede erledigte Teilaufgabe hier
> abhaken (`- [x]`) und im Commit vermerken. Reihenfolge = Priorität; P0 zuerst.

---

## Kontext / aktueller Stand (Was steht schon?)

- **DB:** Azure-Postgres `hh-te86ka` (RG `haushaltskasse-rg`, germanywestcentral), DB `haushaltskasse`,
  ~4648 Buchungen ab Stichtag 01.01.2025, Startsalden je Konto/Topf.
- **Dashboard:** FastAPI + Jinja2, `haushaltskasse/dashboard/app.py`, aktuell an `0.0.0.0:3000`.
  Erreichbar im WLAN über `http://<PC-IP>:3000` (localhost geht am Handy naturgemäß nicht).
- **Tabs heute:** Übersicht (Haushaltssaldo-Formel), Rücklagen (Soll/Ist), Buchungen (Filter+Umkategorisieren),
  Reports (Ausgaben je Kat, Monatsverlauf, Top-Empfänger), Config (Rollen, Soll, Default-Unterkat, Unterkats CRUD).
- **Saldo-Mechanik:** `workflows/gegenbuchung.py` erzeugt Spiegel-Buchungen (`spiegel_von_id`),
  `queries.haushaltssaldo()` = kanonische Formel. Rollen `kategorien.zaehlt_als`.
- **Dateien:** `dashboard/{app.py,queries.py,templates/*}`, `storage/{db.py,schema.sql}`, `workflows/*`.

---

## P0 — Online-Erreichbarkeit von überall (DRINGEND)

Ziel: Zugriff aufs Dashboard unterwegs über das Internet (nicht nur Heimnetz), mit Login-Schutz,
weil private Finanzdaten. HTTPS zwingend.

### P0.1 Auth / Login (MUSS vor Public-Deploy stehen)  ✅ ERLEDIGT (Variante A)
Umgesetzt: `dashboard/auth.py` (Session-Cookie + bcrypt, Single-User aus `.env`), Middleware schützt
alle Routen außer `/login`, `/logout`, `/health`. Login-/Logout-Routen + `login.html`, Abmelden im Menü.
Hash/Secret erzeugen: `python -m haushaltskasse.dashboard.auth`. Mit TestClient verifiziert.
- [x] Login vor die ganze App gehängt — Variante A (Session-Cookie + gehashtes Passwort, `bcrypt`),
  Middleware die alle Routen außer `/login`/`/logout`/`/health` schützt (API → 401, Views → Redirect).
- [x] Secure-Cookie-Flags: `HttpOnly` + `SameSite=Lax` gesetzt; `Secure` via `HAUSHALT_HTTPS_ONLY=1`
  (in Produktion aktivieren). Session signiert über `HAUSHALT_SESSION_SECRET`.

### P0.2 Deployment-Ziel wählen + einrichten
> **Vorbereitet (Code):** `Dockerfile` + `.dockerignore` im Repo-Root, `$PORT`-Support in `app.py`,
> Schritt-für-Schritt-Anleitung in `haushaltskasse/docs/DEPLOY.md` (Variante A App Service Code +
> Variante C Container Apps). Der eigentliche Azure-Deploy ist interaktiv am PC zu machen.
- [x] `Dockerfile` bzw. `startup`-Command + `requirements.txt` geprüft (uvicorn, Port aus `$PORT`).
- [ ] Variante festlegen (Empfehlung: **Azure App Service für Linux, Container oder Code-Deploy**,
      gleiche Subscription/RG wie die DB → interne Verbindung zur Postgres, spart Egress + einfacher Firewall):
  - **A App Service (Code, Python):** `az webapp up` / Deploy aus GitHub. Uvicorn/Gunicorn Startcommand.
    Günstigster Plan B1 (~13 €/Mon) oder F1 Free (eingeschränkt, schläft ein).
  - **B App Service (Container):** eigenes `Dockerfile`, Image in Azure Container Registry. Mehr Kontrolle.
  - **C Azure Container Apps:** scale-to-zero (zahlt fast nichts bei Nichtnutzung), etwas mehr Setup.
  - **Empfehlung:** **A** zum Start (am wenigsten Reibung), später ggf. C für Kostenoptimierung.
- [ ] `Dockerfile` bzw. `startup`-Command + `requirements.txt` prüfen (uvicorn/gunicorn, port aus `$PORT`).
- [ ] `HAUSHALT_DATABASE_URL` als App-Setting im App Service (nicht im Code), SSL-Modus für Postgres an.
- [ ] Postgres-Firewall: „Azure-Dienste erlauben" ODER VNet-Integration statt PC-IP-Whitelist.
- [ ] HTTPS erzwingen (App Service macht TLS automatisch auf `*.azurewebsites.net`; „HTTPS Only" an).
- [ ] Optional: eigener Domainname später.

### P0.3 Kostenübersicht + Feedback in der Seite
- [ ] Eigener kleiner Tab/Kachel „Betrieb/Kosten": zeigt geschätzte Azure-Monatskosten (Postgres B1ms + App-Plan).
- [ ] Möglichst per **Azure Cost Management API** live die aufgelaufenen Kosten des Monats ziehen und anzeigen;
      Fallback: statische Schätzung + „Server stoppen"-Hinweis.
- [ ] Regelmäßiges Feedback: kleiner Job/Anzeige, der bei Login die aktuellen Monatskosten + Trend zeigt
      (Warnschwelle konfigurierbar).
- [ ] Spar-Hinweis dokumentieren: Postgres bei Nichtnutzung stoppen (~4 €/Mon), App-Plan-Größe.

---

## P1 — Rücklagenseite kompakter + Fluss sichtbar

Datei: `dashboard/templates/ruecklagen.html`, Query: `dashboard/queries.py`.

- [ ] **Unterkategorien aufklappbar** (Accordion/Tree): Kategorie-Zeile zeigt Summe, Klick klappt die
      Unterkategorien auf/zu → kompaktere Übersicht. Zustand (auf/zu) merken (localStorage genügt).
- [ ] **Fluss je Unterkategorie sichtbar machen:** pro Unter-/Kategorie nicht nur Soll/Ist-Saldo, sondern
      **Einnahmen (Zufluss)** und **Ausgaben (Abfluss)** im Zeitraum getrennt anzeigen (2 Spalten + Netto).
- [ ] Summen je Kategorie automatisch aus den Unterkategorien rollen; Gesamtsumme oben.

---

## P1 — Default-Unterkategorie = Rest-Auffüllung des Soll (Korrektur!)

**Richtiges Verständnis (frühere Umsetzung war falsch):** Die Default-Unterkategorie ist kein
„Fallback-Ziel beim Kategorisieren", sondern der **Auffang-Rest, der die Soll-Lücke schließt.**

Beispiel: Kategorie „Versicherung" Soll **1.000 €**. Davon verteilt auf Unterkats: Autoversicherung 300 €.
Rest **700 €** soll automatisch der **Standard-Unterkategorie** zugeschlagen werden, damit die Summe der
Unterkat-Soll wieder **1.000 €** ergibt und die Lücke sichtbar/aufgefüllt ist.

- [ ] Datenmodell: je Kategorie ein **Kategorie-Soll** (Gesamt) UND je Unterkategorie ein **Soll**.
      Genau eine Unterkategorie je Kategorie ist als **Default/Rest** markiert (`default_unterkategorie_id`
      existiert schon in `kategorien` — Semantik hier neu belegen: „Rest-Auffang").
- [ ] Berechnung: `Rest-Soll(Default-Unterkat) = Kategorie-Soll − Σ(explizit gesetzte Unterkat-Soll)`.
      Anzeige der Lücke: wenn Kategorie-Soll noch nicht voll auf Unterkats verteilt, Differenz farbig zeigen.
- [ ] In Rücklagen- und Config-Ansicht: Kategorie-Soll setzbar, Unterkat-Soll setzbar, Default-Rest read-only
      berechnet. Warnung wenn Σ Unterkat-Soll > Kategorie-Soll (Überbelegung).
- [ ] Klarstellen/Trennen vom früheren „Default beim Umkategorisieren" (in `set_kategorie`): das ist eine
      ANDERE Funktion und sollte nicht mit dem Rest-Auffang-Feld kollidieren → ggf. zwei getrennte Felder.

---

## P1 — Buchungen: frei sortieren & filtern

Datei: `dashboard/templates/buchungen.html`, `queries.py` (Buchungsliste).  ✅ ERLEDIGT

- [x] **Sortierung nach jeder Spalte** (Datum, Betrag, Empfänger, Konto, Kategorie, Unterkategorie)
      auf-/absteigend per Spaltenkopf-Klick, mit ▲/▼-Anzeige. ORDER BY aus Whitelist (`q.SORT_SPALTEN`).
- [x] **Filter je Spalte:** Datum (Von–Bis), Betrag (Min–Max €), Text (Empfänger/Zweck), Konto,
      Kategorie, Unterkategorie. Kombinierbar.
- [x] Serverseitig, sauber parametrisiert (SQL-Injection-Test bestanden). Paginierung (200/Seite).
- [x] Filter/Sortierung im GET-Formular → stehen in der URL (teilbar, per Reload stabil).
- Offen (später): Unterkategorie-**Mehrfach**auswahl (aktuell Einzelauswahl).

---

## P1 — Reporting umbauen: Pivot / Monatsvergleich + Drilldown

Datei: `dashboard/templates/reports.html`, `queries.py`.  ✅ ERLEDIGT (Kern)

- [x] **Pivot-Monatsvergleich:** Zeilen = Kategorien **oder** Unterkategorien (umschaltbar),
      Spalten = Monate, Zellen = Ausgabe/Einnahme/Netto (umschaltbar). Query `q.pivot()`.
- [x] **Konfigurierbar:** Zeitraum (Von–Bis), Aggregat (Ausgabe/Einnahme/Netto), Ebene (Kat/Unterkat).
      — Offen (später): Mehrfachauswahl *welche* Kategorien in die Pivot kommen.
- [x] **Entwicklung über Monate** visuell: Sparkline-Balken je Zeile über die Monate.
- [x] **Drilldown per Doppelklick:** Zelle (Kategorie × Monat) bzw. Zeile öffnet die gefilterte
      P1-Buchungsliste (`/buchungen?kategorie_id=…&von=…&bis=…`, Unterkat/offen berücksichtigt).
- [x] Summenzeile je Monat (Spalten-Summe) + Zeilensumme + Gesamt.

---

## P2 — Freie Recherche auf dem Datenstand (SQL / KI / Text-Prompt)

Ziel: ad-hoc Fragen an die Daten stellen, ohne fertigen Report.

- [ ] **SQL-Konsole (read-only):** Eingabefeld → Query gegen die DB, Ergebnis als Tabelle.
      Hart auf `SELECT` beschränken (nur Read-Only-DB-Rolle / Query-Whitelist), Timeout, Row-Limit.
- [ ] **KI-/Text-Prompt-Interface:** natürliche Frage → LLM erzeugt SQL gegen das bekannte Schema
      (`storage/schema.sql` als Kontext) → Ausführung read-only → Ergebnis + generiertes SQL anzeigen.
      LLM: Anthropic-Client (`shared/llm_client.py` prüfen), aktuelles Claude-Modell. Guardrails:
      nur SELECT, Schema-Whitelist, Ergebnis-Limit. Kostenhinweis (Token) beachten.
- [ ] Gespeicherte Abfragen / Verlauf (optional).

---

## Querschnitt / Reihenfolge-Empfehlung fürs Handy

1. **P0.1 + P0.2** Login + Azure-Deploy → sobald das steht, ist alles Weitere auch unterwegs testbar.
2. **P0.3** Kostenanzeige.
3. **P1 Buchungen (Sort/Filter)** — kleinste, klar abgegrenzte Verbesserung, gutes Warm-up.
4. **P1 Reporting-Pivot + Drilldown** (nutzt die Buchungsliste wieder).
5. **P1 Rücklagen-Accordion + Fluss.**
6. **P1 Default-Unterkategorie (Rest-Auffüllung)** — Datenmodell sauber trennen.
7. **P2 Freie Recherche (SQL/KI).**

## Offene Entscheidungen (User)
- Deploy-Variante: App Service Code (A) vs. Container Apps scale-to-zero (C)?
- Auth: eigenes Passwort-Login (A) vs. Azure Easy Auth/Entra (B)?
- KI-Recherche: gewünscht, oder reicht read-only SQL-Konsole?

## Nicht vergessen (aus altem Memory)
- Merker: `parse_amazon_visa` von `.xls` (xlrd) auf CSV umstellen, sobald Amazon als CSV exportiert wird.
- Bei erneutem `beladung --write` (TRUNCATE): danach `gegenbuchung --write` erneut laufen (Rollen idempotent).
- Datenschutz: private Beträge/IBANs/Namen NIE im Code — immer aus DB/lokaler FB lesen.
