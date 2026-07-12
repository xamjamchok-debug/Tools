# Neues Design — Haushaltskasse

> ⚠️ **Teilweise überholt.** Aktueller, verbindlicher Stand: `design-2026-07.md`.
> Dieses Dokument bleibt als Entscheidungshistorie (Optionsvergleich A–D) erhalten.
>
> Stand: 2026-04-24. Analyse abgeschlossen (current-analysis.md). Anforderungen in memory/project_ziele.md.

---

## Kernanforderungen (Zusammenfassung)

1. **Saldo-Drill-Down**: Warum hat sich der Saldo verändert? → sofort erkennbar, nicht 30 Min. Analyse
2. **Auto-Kategorisierung**: DKB-Transaktionen werden automatisch erkannt; neue Unterkategorien entstehen automatisch
3. **Rückstellungs-Transparenz**: Korrekturen nachvollziehbar; monatliche Rückstellungen änderbar ohne Intransparenz
4. **KI-Abfrage**: KI kennt immer den kompletten Stand; Abfragen in natürlicher Sprache
5. **Privacy**: Finanzdaten sensibel → Designentscheidung nötig (s. Designvorschläge)

---

## Designvorschläge (4 Optionen)

---

### Option A — Excel+ (Evolutionär)

**Kern:** Bestehende Excel-Struktur bleibt, wird durch ein Python-Skript als "Co-Pilot" ergänzt.

**Wie es funktioniert:**
- DKB-CSV wird per Skript importiert und auto-kategorisiert (Regex + KI-Fallback)
- Skript schreibt vorausgefüllte Vorschläge in die DKB-Tabelle; Nutzer bestätigt/korrigiert
- Rückstellungen werden durch das Skript gebucht (nicht mehr per VBA-Makro), mit Log-Datei
- Saldo-Analyse: Skript erzeugt bei Abweichung automatisch eine Erklärung ("Saldo schlechter wegen: Urlaub -2.055 €, Zahnarzt -1.242 €")
- KI-Abfrage: Skript exportiert aktuellen Stand als kompaktes JSON → an API geschickt, Antwort in Terminal

**Privacy-Modell:** Daten verlassen den Rechner nur bei explizitem KI-Aufruf. Nutzer entscheidet per Befehl.

**Vorteile:**
- Kein Lernaufwand (Excel bleibt wie bisher)
- Minimales Risiko: Altes System bleibt parallel lauffähig
- Schnell umsetzbar

**Nachteile:**
- Excel + Python = zwei Systeme, zwei Fehlerquellen
- Drill-Down bleibt begrenzt (Excel-Formeln)
- Keine echte Datenbank → kein sauberes Audit-Trail

---

### Option B — Lokale Web-App (SQLite + FastAPI + minimales Frontend)

**Kern:** Vollständiger Ersatz. Daten in SQLite-Datenbank, Oberfläche im Browser (lokal), Python-Backend.

**Wie es funktioniert:**
- Datenmodell: `buchungen`, `nebenbuecher`, `rueckstellungen`, `korrekturen` (mit Begründungsfeld)
- DKB-CSV-Import per Drag & Drop oder Datei-Upload → automatische Kategorisierung
- Dashboard zeigt: Saldo, Delta zum Vormonat, Aufschlüsselung nach Konto
- Rückstellungs-Korrekturen werden als eigene Buchungsart gespeichert (Audit-Trail)
- KI-Integration: "Explain"-Button → sendet kompakten Monats-Snapshot an KI-API → Antwort direkt im Dashboard
- Historische Daten seit 2021 migrierbar

**Privacy-Modell:** Alles lokal auf dem Rechner. KI-Aufruf optional und explizit (mit Warnung was gesendet wird).

**Vorteile:**
- Saubere Datenbasis (kein Excel-Kuddelmuddel)
- Drill-Down beliebig tief implementierbar
- Audit-Trail für alle Buchungen und Korrekturen
- KI sieht immer konsistenten, vollständigen Stand

**Nachteile:**
- Aufwändigste Option in der Entwicklung
- Browser-UI auf Windows lokal einrichten (kein Problem, aber Setup nötig)
- Migration der Altdaten braucht Zeit

---

### Option C — Python-Desktop mit DuckDB (Analyst-Ansatz)

**Kern:** Kein Browser, kein Server. Python-Skript mit DuckDB als analytische Datenbank + Rich-Terminal-UI oder Jupyter Notebook als Oberfläche.

**Wie es funktioniert:**
- DuckDB speichert alle Buchungen, Nebenbücher, Rückstellungen
- Standardabfragen als vordefinierte Funktionen: `saldo_analyse(von, bis)`, `nebenbuch_verlauf("Auto")`, `delta_erklaerung()`
- KI-Abfrage: Skript baut Kontext-String (kompakter JSON-Snapshot) und ruft API auf
- Neue Unterkategorien: KI-Vorschlag wird in Mapping-Tabelle gespeichert → nächstes Mal automatisch erkannt
- Rückstellungs-Korrekturen als eigene Buchungsart (wie Option B)

**Privacy-Modell:** Komplett lokal. KI-Aufruf per explizitem Befehl `hk ask "Warum ist Saldo schlechter?"`.

**Vorteile:**
- Sehr flexibel für Analysen (DuckDB ist analytisch stark)
- Kein UI-Aufwand
- Gut für Power-User / jemanden der die Kommandozeile nicht scheut

**Nachteile:**
- Kein grafisches Dashboard → Zahlen im Terminal
- Hohe Einstiegshürde wenn Natalie das System auch nutzen soll
- Weniger intuitiv für tägliche Nutzung

---

### Option D — Notion / Obsidian + Automatisierungs-Skript (Hybrid)

**Kern:** Daten bleiben in einer Markdown/Datenbank-basierten Notizen-App (Obsidian oder Notion), Python-Skript als Importer/Aggregator.

**Wie es funktioniert:**
- Obsidian: Jedes Nebenbuch = eine Seite mit Tabelle + Verlaufsdiagramm
- Skript importiert DKB-CSV → kategorisiert → schreibt in Obsidian-Dateien
- Übersicht als Obsidian-Dashboard-Page (Dataview Plugin)
- KI: Obsidian AI-Plugins oder externer Aufruf

**Privacy-Modell:** Bei Obsidian lokal. Bei Notion: Cloud (Datenschutzproblem für Finanzdaten!).

**Vorteile:**
- Obsidian ist auf dem Rechner vorhanden (wenn genutzt)
- Markdown = versionierbar in Git
- Geringe Entwicklungsarbeit für Grundfunktion

**Nachteile:**
- Obsidian ist kein Buchhaltungs-Tool → viele Workarounds nötig
- Keine echte Datenbankintegration
- Notion scheidet aus (Privacy)
- Saldo-Formel müsste in Dataview nachgebaut werden → fragil

---

## Vergleich auf einen Blick

| Kriterium | A Excel+ | B Web-App | C DuckDB | D Obsidian |
|---|---|---|---|---|
| Entwicklungsaufwand | Gering | Hoch | Mittel | Mittel |
| Drill-Down Saldo | Begrenzt | ★★★ | ★★★ | ★★ |
| Audit-Trail Korrekturen | Nein | ★★★ | ★★★ | ★★ |
| Auto-Kategorisierung | ★★ | ★★★ | ★★★ | ★★ |
| KI-Integration | ★★ | ★★★ | ★★★ | ★ |
| Privacy (lokal) | ★★★ | ★★★ | ★★★ | ★ (Notion) / ★★★ (Obsidian) |
| Einstiegshürde Nutzung | Keine | Gering | Hoch | Gering |
| Migration Altdaten | Einfach | Mittel | Mittel | Schwer |

---

## Entscheidung (2026-04-24)

**Option A + B parallel** — A als sofortige Verbesserung, B als langfristige Ziel-Lösung.

- A läuft weiter auf dem bestehenden Excel-System, wird schrittweise durch Python-Skripte ergänzt
- B wird parallel aufgebaut; sobald funktionsfähig → Ablösung von A
- C und D verworfen

---

## Nächste Schritte

### Track A — Excel+ (kurzfristig)

- [ ] Python-Skript: DKB-CSV-Import mit Auto-Kategorisierung (Regex auf Auftraggeber/Verwendungszweck)
- [ ] Mapping-Tabelle: Payee → Kategorie + Konto (aus vorhandenen Konten-Lookup-Patterns extrahieren)
- [ ] Skript: Saldo-Delta-Erklärung erzeugen ("Warum schlechter?")
- [ ] Skript: Rückstellungs-Log statt VBA-Makro (mit Begründungsfeld)

### Track B — Lokale Web-App (mittelfristig)

- [ ] Datenmodell definieren: `buchungen`, `nebenbuecher`, `rueckstellungen`, `korrekturen`
- [ ] SQLite-Schema aufsetzen + Migration der Altdaten (ab 2021)
- [ ] FastAPI-Backend: CSV-Import, Kategorisierung, Rückstellungs-Buchung
- [ ] Minimal-Frontend: Dashboard (Saldo, Delta, Drill-Down je Konto)
- [ ] KI-Integration: Explain-Button → kompakter Snapshot → API-Aufruf
- [ ] Pflegekonto als eigener Bereich (getrennt vom Haushalt, aber in derselben App)

### Offene Entscheidungen

- [x] Privacy: **Claude API mit explizitem Consent** — Daten werden nur gesendet wenn Nutzer aktiv "Explain" auslöst; UI zeigt vorher an was gesendet wird
- [x] Historische Daten: **Nein** — Altdaten bleiben in Excel, Track B startet frisch
- [x] Natalie: **Später** — jetzt für Jörg allein; UI so bauen dass Natalie später problemlos einsteigen kann (keine Wegwerfentscheidungen beim UI-Design)
- [x] Pflegekonto: **Von Anfang an mitplanen** — Datenmodell von Beginn an für separaten Pflegekonto-Bereich vorbereiten; eigene Buchungshistorie, getrennt vom Haushalt aber in derselben App
