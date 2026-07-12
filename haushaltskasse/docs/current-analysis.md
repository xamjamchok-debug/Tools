# Analyse der bestehenden Excel-Lösung

## Excel-Datei

- **Dateiname:** Fuchsbaukasse2026_neu.xlsm
- **Format:** Excel Macro-Enabled Workbook (.xlsm)
- **Anzahl Tabellenblätter:** 33 (davon 2 Chart-Sheets, 31 Datenblätter)
- **Größte Sheets:** DKB (4,4 MB), Umsätze/Füchschen (je ~2,4 MB)

---

## Tabellenblätter (Übersicht)

### Kernblätter

| Blatt | Inhalt | Größe | Wichtig? |
|---|---|---|---|
| Übersicht | Dashboard: Kontostand DKB, alle Nebenbücher-Saldi, Depots, Schulden | A1:N794 | **Ja** |
| config | Konfiguration monatlicher Rückstellungen je Nebenbuch; mehrere Jahresspalten nebeneinander | B1:AE99 | **Ja** |
| DKB | Alle importierten DKB-Transaktionen seit ~2021; ~5.887 Zeilen | A1:Y5888 | **Ja** |
| Konten | Liste der 12 Nebenbücher mit monatlichem Betrag + Lookup-Patterns für Kategorisierung | A1:F113 | **Ja** |
| Abos | Liste der Abonnements mit Monats-/Jahresbeträgen | A3:D30 | Ja |
| Merkzettel | Notizen / offene Punkte | A1:AG50 | Nein |

### Nebenbücher (Kto- Sheets)

Jedes Nebenbuch hat ein eigenes Sheet mit Buchungshistorie (Datum, Betrag, kumulativer Saldo, Referenz-ID, Bemerkung).

| Sheet | Inhalt | Zeilen ca. | Monatl. Rückstellung |
|---|---|---|---|
| Kto-Auto | Auto: Tanken, KFZ-Steuer, ADAC, Reparaturen | 879 | 1.465 € |
| Kto-Vers | Versicherungen (Haftpflicht etc.) | 577 | 438 € |
| Kto-Kredit | Kreditraten | 681 | 2.147 € |
| Kto-NK | Nebenkosten (Grundsteuer, Strom, Abwasser, Müll…) | 531 | 320 € |
| Kto-TK | Telefon / Krankenkasse | 203 | 253 € + 125 € |
| Kto-Sport | Sport | 805 | 200 € |
| Kto-Urlaub | Urlaub | 495 | 600 € |
| Kto-Füchschen | Kinder (Füchschen) | 531 | 0 € |
| Kto-Tel | Telefon/Medien | 1.156 | — |
| Kto-Natalie | Natalies Einnahmen/Ausgaben | 864 | — |
| Kto-Inst | Sonstiges (KKH, ELB Rest) | 501 | 350 € |
| Kto-Jörg | Jörgs Eigenanteil | C3:P22 | 6.060 € |

### Pflegekonto-Bereich (Eltern in Bullay/Zell)

| Sheet | Inhalt |
|---|---|
| Pflegekonto | Buchungshistorie für Pflegekonto Eltern |
| Pivot_Pflegekonto | Auswertung Pflegekonto |
| Ausgaben_Bullay_Info | Info-Sheet für Ausgaben in Bullay |
| Pflege_251201 | Pflegeabrechnung Dezember 2025 |
| VR Zell | Daten der VR-Bank Zell |

### Auswertungs-Sheets

| Sheet | Inhalt | Größe |
|---|---|---|
| Ausgaben | Ausgabenauswertung | A3:U181 |
| Umsätze | Aggregierte Umsätze (DKB + Amazon) | A1:J147 |
| Jörg | Jörg-spezifische Auswertung | A1:W110 |
| Verlauf | Verlaufsauswertung | A1:W110 |
| Fuchsbau | Hausfinanzierung / Immobilie | A1:AO180 |
| Schulden | Schuldenübersicht | A1:AB20 |
| Forecast | Vorausschau | A1:W62 |
| Riester | Riester-Rente | A1:N8 |
| Füchschen | Chart der Füchschen-Daten | Chart |
| Chart1 | Weiterer Chart | Chart |

---

## DKB-Sheet: Spaltenstruktur

| Spalte | Name | Inhalt |
|---|---|---|
| A | Wertstellung | Datum (Excel-Serial) |
| B | Buchungstext | Art (Lastschrift, Gutschrift…) |
| C | Auftraggeber | Name des Auftraggebers/Empfängers |
| D | Betrag | Betrag |
| E | Tschibboo | Unklar (eigene Spalte, evtl. IBAN/BIC?) |
| F | Verwendungszweck | Verwendungszweck |
| G | Re 8077 Kd 14993 | Eigene Referenz-/Lookup-Spalte |
| H | Kd Nr 24131 | Eigene Lookup-Spalte |
| I | Gläubiger-ID | DKB-Feld |
| J | Mandatsreferenz | DKB-Feld |
| K | Kundenreferenz | DKB-Feld |
| L | **Unterkategorie** | **Manuell vergeben** |
| M | Saldo | Saldo nach Buchung |
| N | **Konto** | **Manuell: Ziel-Nebenbuch** |
| O | ID | Interne ID (vergeben durch Buchungs-Makro) |
| P | Bemerkung | Manuell |
| Q | in Umsätze | "x" wenn in Umsätze-Sheet übertragen |
| R | Gutschrift | Markierung Gutschriften |
| X, Y | (Formeln) | Zählformeln / Summenwerte |

**Wichtig:** Buchungstag fehlt als eigene Spalte! Nur Wertstellung ist importiert.

---

## Konten-Sheet: Struktur

Das Konten-Sheet (A1:F113) hat **zwei überlagerte Tabellen** auf demselben Sheet:

**Tabelle 1 – Nebenbuch-Definitionen (Spalten D–F, Zeilen 1–12):**

| Konto-Name (D) | Monatsrückstellung (E) | Kürzel (F) |
|---|---|---|
| Auto | 1.465 € | Auto |
| Füchschen | 0 € | 0 |
| KKH, ELB Rest | 350 € | Inst |
| Jörg | 6.060 € | Jörg |
| Kredite | 2.147 € | Kredite |
| Natalie | — | — |
| Nebenkosten | 320 € | Nebenkosten |
| Sport | 200 € | Sport |
| Telefon | 253 € | Telefon |
| Krankenkasse | 125 € | Krankenkasse |
| Urlaub | 600 € | Urlaub |
| Haftpflicht/Vers. | 438 € | Haftpflicht |

**Tabelle 2 – Lookup-Patterns (Spalten A–B, Zeilen 1–113):**
- Spalte A: DKB-Verwendungszweck-Schlüsselwörter (z.B. "Agip", "KKH", "Autokredit", "Netflix", "Prime", "Abo", IBAN-Nummern, Transaktions-IDs)
- Spalte B: Weitere Lookup-Keys (Amazon-Order-IDs, weitere DKB-IDs)
- → Diese werden (vermutlich) für Auto-Kategorisierung genutzt, aber die Verknüpfung zum Ziel-Konto fehlt in der Tabelle! Das Ziel fehlt in Spalte C.

---

## VBA-Makros

Makro-Namen: `Rueckstellung`, `buch`, `get_letzte_zeile`, `aktualisiere`, `erzeuge_kontenliste_2020`, `check`, `neu`, `Beenden_Click`

### Makro: `Rueckstellung`
- **Zweck:** Monatliche Rückstellungen erzeugen
- **Auslöser:** Manuell per Formular; Datumseingabe via InputBox
- **Ablauf:**
  1. Liest `Sheets("config").Cells(i, 2)` → Konto-Name
  2. Liest `Sheets("config").Cells(i, 4)` → Betrag
  3. Öffnet das jeweilige Kto- Sheet (`Worksheets("Kto-" & konto)`)
  4. Findet letzte Zeile (via `get_letzte_zeile`)
  5. Schreibt: Datum + Betrag + kumulativer Saldo + "Rückstellung zum [Datum]"
  6. Unload Me (Formular schließen)
- **Fehlerbehandlung:** MsgBox bei "Konto fehlt"

### Makro: `buch` (Buchung)
- **Zweck:** DKB-Transaktionen den Nebenbüchern zuweisen
- **Auslöser:** Manuell nach CSV-Import und manueller Kategorisierung
- **Ablauf:**
  1. Iteriert über DKB-Sheet (bis Zeile 6000)
  2. Prüft: Unterkategorie (Spalte L/15) != "" UND Konto (Spalte N) != ""
  3. Ermittelt Ziel-Sheet: "Kto-" + Konto-Wert
  4. Schreibt in Kto-Sheet: Datum, Betrag, Saldo, Auftraggeber, Verwendungszweck, Unterkategorie, Bemerkung
  5. Schreibt in Umsätze-Sheet: Quelle="dkb", alle Felder
  6. Markiert Zeile in DKB-Sheet als verarbeitet: Spalte Q = "x"
- **Fehlerbehandlung:** MsgBox bei "Kategorie fehlt", "Sheet fehlt"
- **Hinweis:** Makro referenziert auch ein "Amazon"-Sheet (Amazo-Bestellungen als eigene Quelle), das in der aktuellen Datei nicht mehr existiert

### Makro: `aktualisiere`
- **Zweck:** Übersicht-Sheet mit letzten Kontoständen aktualisieren
- Liest letzte Zeile aus Kto-Sheets und überträgt in Übersicht

---

## Abos-Sheet

Die Abos-Tabelle (A3:D30) enthält:
- Spalte A: Transaktions-IDs / Lookup-Keys (Amazon-Order-IDs, SEPA-Refs)
- Spalte B: Monatsbetrag
- Spalte C: Jahresbetrag
- Spalte D: Weitere Referenz
- Zeile 30: Summen (92,89 €/Monat = 958,76 €/Jahr)

**Problem:** Kein Klarname für das Abo! Nur technische Transaktions-IDs. Man sieht nicht, welches Abo das ist (nur anhand der Amazon-ID oder SEPA-Ref).

---

## Kategorien

### Ausgaben-Kategorien (Konto = Ziel-Nebenbuch)
- Auto, Krankenkasse, Telefon, Nebenkosten, Sport, Versicherungen (Haftpflicht), Urlaub, Kredite, Füchschen, Natalie, Jörg, Inst

### Unterkategorien (Beispiele aus Konten-Lookup-Tabelle)
- Auto: Tanken (Agip, bft Tankstelle), Autokredit, KFZ-Steuer, ADAC, Peugeot Bank (REF. PSA-BANK…)
- Abos: Netflix, Prime, Youtube, Tagesspiegel, FAZ, Spiegel, Adobe, Tchibo, Plan (Hilfswerk?), Apple
- Nebenkosten: Grundsteuer (KASSENZEICHEN), Strom (ABPlan… Vattenfall), Wasser, Rhein-Sieg-Kreis
- Sonstiges: KKH, KJA Bonn GmbH, JUDO Club, OGS-Beitrag

---

## Formeln / Automatiken

1. **Kumulativer Saldo in Kto-Sheets:** Jede Zeile = vorheriger Saldo + neuer Betrag
2. **Übersicht-Dashboard:** Verweist auf letzte Zeilen der Kto-Sheets (via `aktualisiere`-Makro)
3. **Zählformeln DKB:** Spalten X, Y zählen offenbar noch nicht verarbeitete / kategorisierte Einträge
4. **Pivot-Tabelle Pflegekonto:** Auswertung über Pivot_Pflegekonto-Sheet

---

## Schwachstellen

### 1. Manuelle Kategorisierung ist zeitaufwändig und fehleranfällig
- Für jede Transaktion in der DKB-Tabelle müssen manuell zwei Felder gesetzt werden: Unterkategorie (L) + Konto (N)
- Der Konten-Sheet hat zwar Lookup-Patterns (Spalten A, B), aber die Zielzuweisung fehlt in Spalte C → Patterns werden entweder gar nicht genutzt oder das Makro ist anders implementiert als gedacht
- Bei ~5.887 Zeilen über ~5 Jahre = viel manuelle Arbeit

### 2. Kein Abo-Klarnamen-Mapping
- Abos-Sheet enthält nur technische IDs, keine Klarnamen wie "Netflix", "Spotify" etc.
- Der Konten-Lookup hat Keywords wie "Netflix", "Prime", "Adobe" — aber ohne systematische Verknüpfung

### 3. Pflegekonto-Querverbuchung
- Pflegekonto für Eltern ist als eigenständiger Bereich integriert, aber Querverbuchungen (was wurde für wen vorgestreckt?) erzeugen Komplexität
- Separate Sheets, aber keine klare Trennung vom Haushalt

### 4. Config-Sheet unübersichtlich
- Mehrere Jahreskonfigurationen nebeneinander in Spalten (B bis AE = 30 Spalten!)
- Schwer zu überblicken, welche Konfiguration aktiv ist

### 5. DKB-Sheet fehlt Buchungstag
- Nur Wertstellung importiert, Buchungstag fehlt → Zeitliche Sortierung evtl. inkonsistent

### 6. Amazon-Sheet fehlt
- VBA-Makro referenziert ein "Amazon"-Sheet, das nicht mehr existiert → potenzieller Makro-Fehler

### 7. 33 Blätter = schwer zu navigieren
- Zu viele Blätter für effiziente tägliche Nutzung

### 8. Kein Versionsmanagement / Backup-Mechanismus
- Als .xlsm gespeichert, kein automatischer Backup, keine Rückgängig-Funktion über Makro-Grenzen hinweg

### 9. "Tschibboo" - unklar
- Spalte E im DKB-Sheet mit unklarem Zweck

---

## Was unbedingt erhalten bleiben muss

1. **Rückstellungs-Logik:** Das Herzstück. Virtuelle Nebenbücher die monatlich befüllt werden, um Jahres-/Quartalsausgaben gleichmäßig zu verteilen. **Must-have.**
2. **Kategorisierungs-Workflows:** Buchungen → Konto zuweisen. Aber deutlich automatisierter.
3. **Übersicht-Dashboard:** Aggregierte Sicht auf alle Konten und Nebenbücher.
4. **DKB-CSV-Import:** Transaktionsdaten kommen von der DKB als CSV.
5. **Pflegekonto-Integration:** Muss weiterhin separate Buchführung für Eltern ermöglichen.
6. **Abos-Übersicht:** Welche Abos laufen, was kosten sie monatlich/jährlich.
7. **Historische Daten:** Daten seit ~Oktober 2021 vorhanden und sollen zugänglich bleiben.
