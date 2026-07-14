# Backlog — Haushaltskasse

**Version 1.4 · Stand 2026-07-14**

Kanonische Liste aller Änderungen & offenen TODOs (Kurzbeschreibung, Umsetzungsweise, **Reifegrad**).
Live-Status + Deploy-Anleitung: [STAND-2026-07-13-live.md](STAND-2026-07-13-live.md).
Bei jeder inhaltlichen Änderung dieser Datei die Version hochzählen (1.0 → 1.1 → …).

**Reifegrad-Stufen:** 💡 Idee (nur notiert) → 📐 Designed (Konzept geklärt) → 🔨 Entwickelt (Code fertig, lokal getestet) → 🚀 Deployed (live) → 👁 Validiert (vom User live geprüft/getestet). Sonderstatus: 🐞 Bug · ❓ Klärung offen · ⭐ Priorität.

**⭐ Nächste Prioritäten (User 2026-07-14):** #8 U1 Merkzettel-Box · #11 U4 stichtagsbezogener Saldo · #22 I1 Import neuer Umsätze.

| Nr | Bereich | Kurzbeschreibung | Umsetzungsweise | Reifegrad |
|----|---------|------------------|-----------------|-----------|
| 1 | Deploy | App online von überall (HTTPS, Login) | Azure Container Apps, scale-to-zero, Image aus ACR `hhkassec1k7wx`, DB Azure-Postgres | 👁 Validiert |
| 2 | Auth | Login-Schutz `joerg` + Passwort | Session-Cookie + bcrypt | 👁 Validiert |
| 3 | Rücklagen | **Modell A**: Topf je Unterkategorie, Saldierung geht auf | Migration `allgemein_toepfe.py`: NULL-Rücklagen → „Allgemein"-Topf je Kategorie | 👁 Validiert |
| 4 | Buchungen | **B1** Saldo/Summe über alle gefilterten Treffer | `queries.buchungen` liefert Summen + Summenzeile im Template | 🚀 Deployed |
| 5 | Buchungen | **B2** Freitext-Bemerkung je Buchung | Schema-Spalte `bemerkung` + Endpoint `/api/buchung/{id}/bemerkung` + editierbare Zelle | 🚀 Deployed |
| 6 | Bug | **Dezimal-Fehler bei Posten** (Beträge ×100 beim Editieren) | `_parse_euro` neu: letzter `.`/`,` = Dezimaltrenner (beide Notationen) | 👁 Validiert |
| 7 | Infra | Deploy-Fix (charmap-Crash, `:latest` erzeugt keine neue Revision) | `az acr build --no-logs`; Update per **Image-Digest** statt Tag | 👁 Validiert |
| 8 | Übersicht | **U1** Merkzettel als eigene Box mit Einzelposten | Neue Spalte `vermoegensposten.gruppe`, eigene Box + Summe | ⭐ 📐 Designed |
| 9 | Übersicht | **U2** transparente Saldo-Herleitung (bis „frei verfügbar") | Wasserfall-Tabelle aus `haushaltssaldo()`-Komponenten | 📐 Designed |
| 10 | Übersicht | **U3** Monatsablauf-Block (Soll vs. Ist, klappbar) | Neuer Accordion-Block, `ruecklagen_baum()` wiederverwenden (verwandt mit #39) | 📐 Designed |
| 11 | Übersicht | **U4** stichtagsbezogener Gesamtsaldo | Buchungen exakt per `datum_wert≤Stichtag`; Posten zeitlos-konstant + gekennzeichnet | ⭐ 📐 Designed |
| 12 | Rücklagen | **R1** Doppelklick aufs **Nebenbuch** → Rücklagen-/Gegenbuchungen mit laufendem Saldo (altes Kto-Blatt), optional Filter Unterkategorie | Getrennte Nebenbuch-Sicht (`buchungsart='ruecklage'`) via `/nebenbuch/{id}`, `queries.nebenbuch()` | 👁 Validiert |
| 13 | Rücklagen | **R4** „+ zurücklegen / − entnehmen" je Topf (= ein-/ausbuchen) | Neuer Endpoint → manuelle `ruecklage`-Buchung (+/−) | 📐 Designed |
| 14 | Rücklagen/Config | **R3** „Soll" nur an EINER Stelle editierbar (**Config**), **Rücklagen read-only** | Rücklagen-Soll read-only; Editieren nur in Config | 👁 Validiert |
| 15 | Rücklagen | Saldierung nach Migration prüfen (dein Bug-Report „Salden Kappes") | Nach Hard-Refresh verifizieren; sonst gezielt nachsehen | 🐞 offen |
| 16 | Buchungen | Posten/Rücklagen in Buchungsliste verwirrend | Erklären/kennzeichnen; via B3 ausgeblendet | ❓ Klärung |
| 17 | Buchungen | **B3** Buchungsliste **standardmäßig nur reale Buchungen** · **B4** besser filtern | Default nur echte Konten, Umschalter „inkl. Rücklagen"; B4-Filter erweitern | 👁 B3 Validiert · 💡 B4 |
| 18 | Config | **C1** Config-Seite **einklappbar** (Accordion) | Klappbare Nebenbücher (via #39 umgesetzt) | 🚀 Deployed |
| 19 | Einnahmen | **E1** Einnahmen explizit (Kennzeichen je Unterkat, in Monatssaldo) | Einnahme-Kennzeichen `ist_einnahme` + Config-Fluss (via #39); eigene Übersicht-Sicht noch offen | 🚀 Deployed (Teil) |
| 20 | Kategorien | **K1** schlauere Kategorien/Unterkategorien | KI-gestützt, lernende `mapping_regeln`, Vorschläge bestätigen | 💡 Idee |
| 21 | Analyse | **P2** freie Query + Pivot-Ausbau | Read-only SQL-Konsole und/oder KI-Prompt→SQL; Pivot erweitern | 💡 Idee |
| 22 | Import | **I1** Import neuer Umsätze über die Weboberfläche | CSV-Upload → `pipeline.py`, dedupe, kategorisieren, Gegenbuchungen; Amazon noch `.xls` | ⭐ 📐 Designed |
| 23 | Betrieb | **V1** sichtbare Versionsnummer + automatisierte Tests | Version im Footer (Env-Var); pytest für Queries/Saldo/Endpoints | 💡 Idee |
| 24 | Betrieb | **P0.3** Azure-Kostenanzeige in der Seite | Cost-Management-API / Schätzung + Warnschwelle | 💡 Idee |
| 25 | Analyse | **U5** Veränderung **Stichtag X → Y** (Mittelfluss-Überblick), Default nach Import | Delta = Saldo(Y)−Saldo(X) + Zufluss/Abfluss je Konto/Kategorie/Topf; nach Import X=vor-Import, Y=jetzt | 📐 Designed |
| 26 | Zeitraum | **Start-Abgrenzungsdatum konfigurierbar** (statt hart 01.01.2025) | `STICHTAG` in **Config** editierbar (z. B. 01.01.2026), im **Footer sichtbar**; Reports-Default | 🚀 Deployed |
| 27 | Rücklagen | **Zufluss/Abfluss-Spalten ENTFERNEN** — falsch & nicht gebraucht; nur Ist-Saldo je Topf | Spalten raus aus `ruecklagen_baum`/Template; Bewegungen über R1 | 👁 Validiert |
| 28 | Rücklagen | **Untertöpfe richtig befüllen** (nicht alles in „Allgemein") | Zuführungen sinnvoll auf Unterkategorie-Töpfe verteilen statt Sammel-„Allgemein" | 💡 Idee |
| 29 | Nachbau | **Verlauf-, Schulden- & Fuchsbau-Blatt nachbauen** (aus alter Excel) | Je ein Bereich: Verlauf (Salden-Zeitreihe), Schulden (Kreditübersicht), Fuchsbau (Immobilie) | 💡 Idee |
| 30 | Zeitraum/Config | **Verlauf etc. pro Jahr fortschreiben** | Jahresweise Fortschreibung/Snapshots je Nebenbuch, über Config gesteuert | 💡 Idee |
| 31 | Analyse | **Diagramme** | Grafische Auswertungen (Verlauf, Ausgaben je Kat, Monatsvergleich); Skill `dataviz`, CSP-konform | 💡 Idee |
| 32 | Übersicht | **Stichtage für Merkzettel** | Merkzettel-/Vermögensposten mit Stichtag/Fälligkeit (baut auf U1/U4 auf) | 💡 Idee |
| 33 | Betrieb | **Backup** | Regelmäßige DB-Sicherung (pg_dump / Azure-Backup) + Rückspielweg | 💡 Idee |
| 34 | Export | **Export nach Excel** (Buchungen) | `/export/buchungen.xlsx` (openpyxl), gefilterte Liste; Reports/Salden später | 🚀 Deployed |
| 35 | Datenmodell | **Logik für Großeltern nachbauen** (Pflegekonto/Kredit) | Separater Pflegekonto-Bereich + Kredit Großeltern (−135.000), getrennte Buchführung | 💡 Idee |
| 36 | Demo | **Anonymisierte Show-Site** | Öffentliche Demo mit anonymisierten/synthetischen Daten | 💡 Idee |
| 37 | Konten | **Eigenes Girokonto in die Berechnungen aufnehmen** | Persönliches Girokonto als reales Konto ergänzen (Startsaldo + Import) | 💡 Idee |
| 38 | Getrennte Sicht | **Pendant „Großeltern"** zur Haushaltskasse | Ähnliche, reduzierte Logik, komplett getrennt (eigener Bereich/Datensatz); baut auf #35 auf | 💡 Idee |
| 39 | Config | **Config = monatliche Finanzfluss-Sicht** (Einnahmen − Ausgaben = Monats-Saldo, eingeklappt) | `config_fluss`: Einnahmen=Kategorien mit Einnahme-Unterkats / Ausgaben='ruecklage'; Einnahme-Kennzeichen `ist_einnahme`; aufklappen=Pflege | 🚀 Deployed |
| 40 | Finanzplanung | **10-Jahres-Verlaufsplanung** — Absprung aus Config; füllbare Tabelle + Diagramm | Jahres-Plan-Tabelle (neues Datenmodell) + Chart (dataviz); Design später | 💡 Idee (nicht jetzt) |
| 41 | Rücklagen | **Nebenbuch-Ansicht sortierbar** (Default: neueste oben) | Klickbare Spaltenköpfe in `nebenbuch.html` / `queries.nebenbuch` (NB_SORT), Saldo bleibt chronologisch | 🚀 Deployed |
