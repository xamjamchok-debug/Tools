# Backlog — Haushaltskasse

**Version 1.2 · Stand 2026-07-14**

Kanonische Liste aller Änderungen & offenen TODOs (Status, Kurzbeschreibung, Umsetzungsweise).
Live-Status + Deploy-Anleitung: [STAND-2026-07-13-live.md](STAND-2026-07-13-live.md).
Bei jeder inhaltlichen Änderung dieser Datei die Version hochzählen (1.0 → 1.1 → …).

**✅ Live & vom User getestet (Deploy cb3, 2026-07-14):** #6 Dezimal-Fix · #12 R1 Nebenbuch · #14 R3 Rücklagen read-only · #17 B3 Buchungen nur real · #27 Fluss-Spalten weg.

**📦 NÄCHSTES PAKET (zusammen bauen, EIN Deploy):** #39 Config-Monatsfluss (+ C1 einklappbar) · #26 Start-Abgrenzungsdatum konfigurierbar · #41 Nebenbuch sortierbar · #34/O2 Excel-Export.

**Legende:** ✅ live · 🔧 Code fertig, Deploy ausstehend · 📋 offen (Backlog) · 🐞 Bug · ❓ Klärung offen

| Nr | Bereich | Kurzbeschreibung | Umsetzungsweise | Status |
|----|---------|------------------|-----------------|--------|
| 1 | Deploy | App online von überall (HTTPS, Login) | Azure Container Apps, scale-to-zero, Image aus ACR `hhkassec1k7wx`, DB Azure-Postgres | ✅ live |
| 2 | Auth | Login-Schutz `joerg` + Passwort | Session-Cookie + bcrypt | ✅ live |
| 3 | Rücklagen | **Modell A**: Topf je Unterkategorie, Saldierung geht auf | Migration `allgemein_toepfe.py`: NULL-Rücklagen → „Allgemein"-Topf je Kategorie | ✅ live |
| 4 | Buchungen | **B1** Saldo/Summe über alle gefilterten Treffer | `queries.buchungen` liefert Summen + Summenzeile im Template | ✅ live |
| 5 | Buchungen | **B2** Freitext-Bemerkung je Buchung | Schema-Spalte `bemerkung` + Endpoint `/api/buchung/{id}/bemerkung` + editierbare Zelle | ✅ live |
| 6 | Bug | **Dezimal-Fehler bei Posten** (Beträge ×100 beim Editieren) | `_parse_euro` neu: letzter `.`/`,` = Dezimaltrenner (beide Notationen), getestet | 🔧 Deploy offen |
| 7 | Infra | Deploy-Fix (charmap-Crash, `:latest` erzeugt keine neue Revision) | `az acr build --no-logs`; Update per **Image-Digest** statt Tag | ✅ gelöst |
| 8 | Übersicht | **U1** Merkzettel als eigene Box mit Einzelposten | Neue Spalte `vermoegensposten.gruppe`, eigene Box + Summe | 📋 offen |
| 9 | Übersicht | **U2** transparente Saldo-Herleitung (bis „frei verfügbar") | Wasserfall-Tabelle aus `haushaltssaldo()`-Komponenten | 📋 offen |
| 10 | Übersicht | **U3** Monatsablauf-Block (Soll vs. Ist, klappbar) | Neuer Accordion-Block, `ruecklagen_baum()` wiederverwenden | 📋 offen |
| 11 | Übersicht | **U4** stichtagsbezogener Gesamtsaldo | Buchungen exakt per `datum_wert≤Stichtag`; Posten zeitlos-konstant + gekennzeichnet | 📋 offen |
| 12 | Rücklagen | **R1** Doppelklick aufs **Nebenbuch** → dessen Rücklagen-/Gegenbuchungen mit laufendem Saldo (wie altes Kto-Blatt), optional Filter Unterkategorie | Getrennte Nebenbuch-Sicht (`buchungsart='ruecklage'`) via `/nebenbuch/{id}`, `queries.nebenbuch()` | 🔧 Code fertig, Deploy offen |
| 13 | Rücklagen | **R4** „+ zurücklegen / − entnehmen" je Topf (= ein-/ausbuchen) | Neuer Endpoint → manuelle `ruecklage`-Buchung (+/−) | 📋 offen |
| 14 | Rücklagen/Config | **R3** „Soll" nur an EINER Stelle editierbar (**Config**), **Rücklagen read-only** (Konto-Sicht) | Rücklagen-Soll auf read-only umgestellt; Editieren nur in Config | 🔧 Rücklagen read-only fertig · 📋 Config-Ausbau (39) |
| 15 | Rücklagen | Saldierung nach Migration prüfen (dein Bug-Report) | Nach Hard-Refresh verifizieren; sonst gezielt nachsehen | 🐞 zu prüfen |
| 16 | Buchungen | Posten/Rücklagen in Buchungsliste verwirrend | Erklären/kennzeichnen; ggf. mit B3 ausblenden | ❓ Klärung |
| 17 | Buchungen | **B3** Buchungsliste **standardmäßig nur reale Buchungen** (Rücklagen/Spiegel raus, falsches Vorzeichen) · **B4** besser filtern | Default `konto_id IS NOT NULL`, Umschalter „inkl. Rücklagen"; B4-Filter erweitern (Mehrfachauswahl, Chips) | 🔧 B3 fertig · 📋 B4 |
| 18 | Config | **C1** Config-Seite **einklappbar** (Accordion) | Klappbare Nebenbücher (Teil von 39) | 📋 offen |
| 19 | Einnahmen | **E1** Einnahmen explizit im Monatsablauf + eigene Sicht | Zufluss/Gehalt getrennt zeigen, in Saldo einrechnen (Teil von U3) | 📋 offen |
| 20 | Kategorien | **K1** schlauere Kategorien/Unterkategorien | KI-gestützt, lernende `mapping_regeln`, Vorschläge bestätigen | 📋 offen |
| 21 | Analyse | **P2** freie Query + Pivot-Ausbau | Read-only SQL-Konsole und/oder KI-Prompt→SQL; Pivot in Reports erweitern | 📋 offen |
| 22 | Import | **I1** Import neuer Umsätze über die Weboberfläche | CSV-Upload → `pipeline.py`, dedupe, kategorisieren, Gegenbuchungen; Amazon noch `.xls` | 📋 → in Umsetzung (jetzt gewünscht) |
| 23 | Betrieb | **V1** sichtbare Versionsnummer + automatisierte Tests | Version im Footer (Env-Var); pytest für Queries/Saldo/Endpoints | 🔧/📋 |
| 24 | Betrieb | **P0.3** Azure-Kostenanzeige in der Seite | Cost-Management-API / Schätzung + Warnschwelle | 📋 offen |
| 25 | Analyse | **U5** Veränderung **Stichtag X → Y** (Mittelfluss-Überblick), Default nach Import | Delta = Saldo(Y)−Saldo(X) gesamt + Zufluss/Abfluss je Konto/Kategorie/Topf im Intervall; nach Import automatisch X=Stand-vor-Import, Y=jetzt | 📋 offen |
| 26 | Zeitraum | **Start-Abgrenzungsdatum konfigurierbar** (statt hart 01.01.2025) | `STICHTAG` in **Config** einstellbar (z. B. auf 01.01.2026 belegen), im **Header/Footer sichtbar** anzeigen; wirkt auf Rücklagen/Reports/Nebenbuch | 📋 im nächsten Paket |
| 27 | Rücklagen | **Zufluss/Abfluss-Spalten ENTFERNEN** — falsch (Datumsfilter wirkt nicht) und nicht gebraucht; nur Ist-Saldo je Topf zeigen | Spalten raus aus `ruecklagen_baum`/Template; Bewegungen über R1-Doppelklick | 🔧 Code fertig, Deploy offen |
| 28 | Rücklagen | **Untertöpfe richtig befüllen** (nicht alles in „Allgemein") | Zuführungen sinnvoll auf Unterkategorie-Töpfe verteilen (Verteillogik/manuell) statt Sammel-„Allgemein"; Modell A vervollständigen | 📋 offen |
| 29 | Nachbau | **Verlauf-, Schulden- & Fuchsbau-Blatt nachbauen** (aus alter Excel) | Je ein Dashboard-Bereich: Verlauf (Salden-Zeitreihe je Nebenbuch), Schulden (Kreditübersicht), Fuchsbau (Immobilie/Finanzierung) | 📋 offen |
| 30 | Zeitraum/Config | **Verlauf etc. pro Jahr fortschreiben** | Jahresweise Fortschreibung/Snapshots je Nebenbuch, über Config gesteuert (Jahresspalten wie im alten config-Blatt) | 📋 offen |
| 31 | Analyse | **Diagramme** | Grafische Auswertungen (Verlauf, Ausgaben je Kat, Monatsvergleich); Skill `dataviz`, self-contained (CSP) | 📋 offen |
| 32 | Übersicht | **Stichtage für Merkzettel** | Merkzettel-/Vermögensposten mit Stichtag/Fälligkeit versehen (baut auf U1/U4 auf) | 📋 offen |
| 33 | Betrieb | **Backup** | Regelmäßige DB-Sicherung (pg_dump / Azure-Backup) + dokumentierter Rückspielweg | 📋 offen |
| 34 | Export | **Export nach Excel** | Buchungen/Reports/Salden als `.xlsx` (openpyxl) exportieren | 📋 offen |
| 35 | Datenmodell | **Logik für Großeltern nachbauen** (Pflegekonto/Kredit) | Separater Pflegekonto-Bereich + Kredit Großeltern (−135.000), getrennte Buchführung wie im alten Modell | 📋 offen |
| 36 | Demo | **Anonymisierte Show-Site** | Öffentliche Demo mit anonymisierten/synthetischen Daten (keine echten Beträge/Namen/IBANs) | 📋 offen |
| 37 | Konten | **Eigenes Girokonto in die Berechnungen aufnehmen** | Persönliches Girokonto als reales Konto ergänzen (Startsaldo + Import), damit Real-/Haushaltssaldo vollständig sind | 📋 offen |
| 38 | Getrennte Sicht | **Pendant „Großeltern"** zur Haushaltskasse | Ähnliche, reduzierte Logik, komplett getrennt dargestellt (eigener Bereich/Datensatz); baut auf N5 auf | 📋 offen |
| 39 | Config | **Config = monatliche Finanzfluss-Sicht** (editierbar): Einnahmen (Jörg/Natalie) − Ausgaben je Nebenbuch→Unterkategorie, einklappbar, **Monats-Saldo** auf einen Blick | **Einnahmen-Modell GEKLÄRT (2026-07-14):** je Person mehrere als **„Einnahme" markierte Unterkategorien** in Jörg/Natalie (Gehalt, Taschengeld, …) → neues Unterkat-Kennzeichen `zaehlt_als='einnahme'`. Monats-Saldo = Σ Einnahme-Soll − Σ Ausgaben-Soll; Plan-Soll getrennt vom historischen Ist-Topf | 📋 Design geklärt, baubereit |
| 40 | Finanzplanung | **10-Jahres-Verlaufsplanung** — Absprung aus Config: wie sich Einnahmen/Ausgaben/Haushalts-Rücklagen über die Jahre ändern; füllbare Tabelle + Diagramm; „wo stehen wir saldoseitig in 5/10 Jahren" | Explizite Jahres-Plan-Tabelle (neues Datenmodell) + Chart (dataviz); **Design später** | 📋 offen (nicht jetzt) |
| 41 | Rücklagen | **Nebenbuch-Ansicht sortierbar** (Default: neueste oben) | Klickbare Spaltenköpfe in `nebenbuch.html` / `queries.nebenbuch` (Datum/Betrag/…), Default `datum desc` | 📋 im nächsten Paket |
