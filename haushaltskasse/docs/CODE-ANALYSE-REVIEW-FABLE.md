# Code-Analyse Haushaltskasse — Fable-Review: Gegencheck von Übersicht + Deep Dive I

**Stand 2026-07-16 · Reviewer: Fable (unabhängige Zweitprüfung der Opus-Analysen)**
Geprüfte Dokumente: [CODE-ANALYSE-2026-07-16.md](CODE-ANALYSE-2026-07-16.md) (Schritt 1) ·
[CODE-ANALYSE-DEEP-DIVE-I.md](CODE-ANALYSE-DEEP-DIVE-I.md) (Deep Dive I).
**Methodik:** eigene read-only-Nachrechnung gegen die Live-DB (identischer Stand: Commit `10106be`
lokal, App-Revision `--0000011`) + vollständige Lektüre der Workflow-Schicht, die Deep Dive I nur
teilweise gelesen hatte (`beladung.py`, `web_import.py`, `allgemein_toepfe.py`, `abgrenzung.py`,
`kategorisierung.py`, `auth.py`). Kein Schreibzugriff.

---

## 1. Nachrechnung der Deep-Dive-I-Zahlen — **alle bestätigt**

| Behauptung (Deep Dive I) | Meine Nachrechnung | Verdikt |
|---|---|---|
| Wasserfall geht cent-genau auf (Saldo −15.447,00) | Konten 82.999,72 + Posten −69.820,00 − Rück 35.459,53 + Ford 6.832,81 = **−15.447,00**; MZ −670,00 + PS −69.150,00 = −69.820,00, Diff **0,00** | ✅ bestätigt |
| #52-Drift +746,86 = −5.313,14 Zuführungen + 6.060,00 Forderung | Zukunft (>heute): 10 Rücklage-Buchungen 5.313,14 · 1 Forderungs-Buchung 6.060,00 · 0 auf realen Konten → Drift **746,86** | ✅ exakt bestätigt |
| Spiegel: 0 verwaist, 0 doppelt | 0 / 0; zusätzlich geprüft: Σ Spiegel (56 Stk, −4.441,84) == Σ berechtigte Realbuchungen (56 Stk, −4.441,84), **Diff 0,00** | ✅ bestätigt + verschärft |
| `kennzahlen()` mischt Rücklagen+Forderungen (Befund A) | 42.292,34 − 35.459,53 = **6.832,81 = exakt die Forderungssumme** — die Mischung ist quantifiziert. Hinweis: `python -m …storage.db` druckt diese gemischten Zahlen nach **jedem** Schema-Lauf; die dort angezeigte „summe_ruecklagen" ist also stets um die Forderungen zu hoch | ✅ bestätigt, konkretisiert |
| Konsistenz-Falle `gruppe` vs. `im_haushaltssaldo` latent (Befund C) | 0 Merkzettel mit `im_haushaltssaldo=FALSE` — aktuell erfüllt, weiterhin durch nichts erzwungen | ✅ bestätigt (latent) |

**Datenhygiene besser als befürchtet:** 0 pathologische Zeilen (`ruecklage` mit Konto, `umbuchung`
mit Kategorie, `real` ohne Konto, Unterkategorie↔fremde Kategorie — alle 0). Der `__TEST_POSTEN__`
steht wie dokumentiert auf `aktiv=FALSE` (#53 bleibt „löschen, aber harmlos").

---

## 2. Übersehene Befunde (neu — das Wesentliche dieses Reviews)

### 🔴 F1 — Web-Import erzeugt KEINE Spiegel-Gegenbuchungen (echter Bug, empirisch belegt)

`web_import.importiere_upload()` fügt Realbuchungen ein, ruft aber **nie** `sync_eine`/
`sync_gegenbuchungen` auf. Eine per Web importierte, topf-pflichtige Ausgabe (Rücklagen-Kategorie)
steht damit **ohne Verzehr-Spiegel** in der DB — sie senkt den Haushalts-Saldo, obwohl sie
topf-gedeckt und damit saldo-neutral sein müsste. Der Spiegel entsteht erst, wenn (a) am PC
`gegenbuchung --write` läuft oder (b) die Buchung im Dashboard umkategorisiert wird (`sync_eine`).

**Empirischer Beleg aus der Live-DB:** 51 von 56 Spiegeln wurden **mehr als 1 Stunde nach** ihrer
Quellbuchung erstellt (Quellen vom 12.–16.07.) — d. h. die per Web importierten Buchungen saßen
tagelang spiegellos in der DB, bis der heutige CLI-Lauf sie nachzog. Der aktuelle Bestand ist sauber
(0 fehlende Spiegel), **aber der nächste Handy-Import reißt die Lücke wieder auf.**

Das trifft genau den Kern-Workflow (Import vom Handy, PC nur gelegentlich). Deep Dive I hat die
Spiegel-*Integrität* geprüft (bestanden), aber nicht die Spiegel-*Erzeugung* auf dem Web-Pfad.
**Fix ist klein:** am Ende von `importiere_upload()` das idempotente `sync_gegenbuchungen(cur)`
aufrufen (gleiche Transaktion). → als Backlog **#59** aufgenommen.

### 🔴 F2 — `beladung --write` zerstört manuelle Daten unwiederbringlich (Risiko #3 aus Schritt 1 ist UNTERSCHÄTZT)

Schritt 1 beschreibt das Risiko als „nach TRUNCATE müssen `gegenbuchung` + `allgemein_toepfe` erneut
laufen". Das ist zu milde. `beladung --write` macht `TRUNCATE buchungen RESTART IDENTITY CASCADE`
und lädt **nur** aus Fuchsbaukasse + `input/`-Auszügen neu. **Nicht wiederherstellbar** sind dann:

- alle **manuellen Buchungen** aus dem Dashboard (`/api/topf/buchen`, `/api/topf/umbuchen`, `quelle='manuell'`),
- alle per Web **importierten** Buchungen, deren Quelldateien nicht (mehr) in `input/` liegen,
- alle **Bemerkungen**, **kat_pinned/unterkat_pinned**-Fixierungen und **Umkategorisierungen**,
- alle `verteilung`-Buchungen (#28), sobald sie existieren.

Die beiden idempotenten Nachläufe stellen davon **nichts** wieder her — sie rekonstruieren nur
Rollen und Auto-Spiegel. Seit dem User-Entscheid „**die DB ist die Quelle der Wahrheit**" ist
`beladung` damit ein **Altlast-Werkzeug, dessen `--write` die kanonische Quelle zerstört**. Es wird
im Alltag nicht mehr gebraucht (Neuimporte laufen über den Web-Import) — es muss aber auch nicht
gelöscht werden, sondern **verriegelt** (siehe Deep Dive II, Leitplanke 3.3). Zusatz-Detail: das
TRUNCATE läuft auch im *Dry-Run* (mit Rollback) und hält währenddessen einen exklusiven Lock auf
`buchungen` — ein parallel laufendes Dashboard blockiert solange.

### 🟡 F3 — Saldo-Korrektheit hängt an der Kategorisierungs-Vollständigkeit (systemisch, bisher nirgends ausgesprochen)

**815 unkategorisierte Realbuchungen** (Netto +266.081,25) liegen in der DB. Für den Saldo gilt:
eine unkategorisierte Ausgabe bekommt keinen Spiegel — sie senkt den Saldo voll, auch wenn sie
eigentlich topf-gedeckt wäre. Erst die (spätere) Kategorisierung macht sie rückwirkend neutral.
Der Saldo ist also **nur so richtig wie der Kategorisierungs-Stand**. Kein Bug, aber eine
Systemeigenschaft, die man kennen muss — und ein Argument, #20 (KI-Kategorisierung) höher zu
priorisieren als „💡 Idee". Die positive Summe zeigt: der Großteil sind Einnahmen/Transfers, aber
die Ausgaben darunter verzerren den Saldo heute still.

### 🟢 F4 — Umbuchungs-Asymmetrie: Netto +13.083,47 statt 0 (erklärbar, dokumentierenswert)

57 `umbuchung`-Buchungen summieren sich auf +13.083,47 — Transfers sind also überwiegend
**einseitig** erfasst (die Gegenseite liegt außerhalb der Datenabdeckung: vor dem Stichtag im
Startsaldo konsolidiert, oder das Gegenkonto liefert keine Auszüge, z. B. Kreditkarten-Ausgleich).
**Kein Saldo-Fehler** — das Geld auf den erfassten Konten ist korrekt gezählt. Aber die Intuition
„Umbuchungen netto 0" gilt hier nicht; wer die Zahl je prüft, soll das wissen.

### 🟢 F5 — Kleinere Ergänzungen

- **`_match_db` verbreitert die Teilstring-Falle:** eine `empfaenger`-Regel, die im Empfänger nicht
  trifft, wird zusätzlich gegen `empfaenger+verwendungszweck` geprüft (`or pat.search(gesamt)`).
  Die dokumentierten Fallen (`arag`→„Garage") wirken so auch im Verwendungszweck. Bewusst prüfen,
  ob das gewollt ist.
- **Schlafender Stichtag-Default:** `einstellungen.stichtag = 2026-05-01`, die Code-Konstante
  `STICHTAG = "2025-01-01"` dient als Signatur-Default der Report-Funktionen. Alle *heutigen* Aufrufer
  lösen korrekt über `q.stichtag(cur)` auf — ein künftiger Aufrufer, der den Default nutzt, rechnet
  still ab 2025-01-01. Kleine Falle, kostenloser Fix (Default `None` + explizit auflösen).
- **Auth-Fallbacks:** ohne `HAUSHALT_APP_PASSWORD_HASH` startet die App **ohne Login** (nur Warnung);
  ohne `SESSION_SECRET` wird ein Zufalls-Secret erzeugt (Sessions sterben beim Neustart). Für den
  Container heute beides gesetzt — aber ein Deploy mit verlorener Env-Var würde die App **offen**
  ins Netz stellen. Härtung: bei `HAUSHALT_HTTPS_ONLY=1` ohne Hash **abbrechen statt warnen**.

---

## 3. Bewertung der Risiko-Einstufung aus Schritt 1

| Risiko (Schritt 1) | Einstufung | Mein Verdikt |
|---|---|---|
| 1. Keine Tests | 🔴 hoch | ✅ angemessen — bleibt Risiko Nr. 1. F1 ist genau die Fehlerklasse, die ein Invarianten-Test (`Σ Spiegel == Σ berechtigte Realbuchungen`, hier B2) sofort gefangen hätte |
| 2. Vorzeichen-Logik fragil/verstreut | 🔴 hoch | ✅ angemessen; F1 liefert den Praxisbeleg: die Spiegel-Pflicht ist an 2 von 3 Schreibpfaden implementiert (CLI ✓, Umkategorisieren ✓, Web-Import ✗) — genau das Streuungs-Problem |
| 3. Migrations-Reihenfolge Herrschaftswissen | 🔴 hoch | ⬆ **unterschätzt** — es geht nicht nur um Reihenfolge, sondern um **irreversiblen Datenverlust** (F2). `beladung --write` würde heute die kanonische Quelle zerstören |
| 4–7 (Monolith, Deploy, Doppelspur, Datenschutz) | 🟡 mittel | ✅ angemessen; zur Doppelspur: von Jörg als gewollter Admin-Zugang bestätigt → Behandlung als „Härten statt Abschaffen" ist richtig (Deep Dive II) |
| 8–10 (xlrd, Teilstring, Testdaten) | 🟢 niedrig | ✅ angemessen; Teilstring-Falle durch F5/`_match_db` etwas breiter als beschrieben |

**Fehlendes Risiko (neu):** die **stille Saldo-Abhängigkeit vom Kategorisierungs-Stand** (F3) —
gehört als eigener Punkt in die Risikoliste, Einstufung 🟡.

## 4. Gesamturteil

Beide Dokumente sind **fachlich korrekt** — jede nachgerechnete Zahl stimmt cent-genau, kein Befund
musste widerlegt werden. Die Lücken liegen dort, wo Deep Dive I nicht hingeschaut hat: auf den
**Schreibpfaden** (Web-Import ohne Spiegel-Sync, `beladung`-Datenverlust) statt auf dem *Bestand*.
Konsequenz für die Empfehlungs-Reihenfolge aus Deep Dive I: **vor** den Regressionstests zuerst den
Ein-Zeilen-Fix #59 (Spiegel-Sync im Web-Import) — er schließt die einzige Lücke, die im Alltag
laufend neu entsteht. Details und Umsetzungsvorschläge: [CODE-ANALYSE-DEEP-DIVE-II.md](CODE-ANALYSE-DEEP-DIVE-II.md).
