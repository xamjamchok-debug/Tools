# Code-Analyse Haushaltskasse — Deep Dive I: Korrektheit der Geld-Logik

**Stand 2026-07-16 · Analyse-Ebene 2 von 3** · Fortsetzung von [CODE-ANALYSE-2026-07-16.md](CODE-ANALYSE-2026-07-16.md)

**Methodik:** Statische Analyse der Saldo-Funktionen (`queries.py`, `gegenbuchung.py`) plus
**read-only Nachrechnung gegen die Live-DB** (Revision `--0000010`, Commit `91aa679`). Alle Beträge
unten sind echte Werte aus der Produktiv-DB vom 2026-07-16 — kein Schreibzugriff.

---

## 1. Die drei Saldo-Definitionen im System

Es gibt **drei** Stellen, die „Saldo" berechnen — mit unterschiedlicher Semantik:

| Funktion | Formel | Datumsfilter | verwendet in |
|---|---|---|---|
| `haushaltssaldo()` | `Konten + Posten − Rücklagen + Forderungen` | **keiner** (alle Buchungen) | KPI-Kacheln + Wasserfall (Übersicht) |
| `haushaltssaldo_per_stichtag(d)` | dieselbe, aber `datum_wert ≤ d` | **bis Stichtag** (Posten zeitlos) | Stichtag-Box (Übersicht) |
| `kennzahlen()` | `Real − Σ alle ruecklage-Buchungen` | keiner | **nur** Konsolen-Ausgabe von `db.py` |

**Befund A (Architektur-Falle):** `kennzahlen()` summiert `buchungsart='ruecklage'` **ungefiltert** —
also inklusive der `forderung`-Kategorien (Natalie/Jörg). Es mischt damit Rücklagen und Forderungen,
was `haushaltssaldo()` bewusst trennt. Aktuell **harmlos**, weil `kennzahlen()` nur beim
`python -m …storage.db` auf die Konsole geht und **nirgends in der Web-UI** hängt. Aber: die Funktion
ist eine tickende Falle, falls sie jemand später als „verfügbar" in der UI einbindet. → *Angleichen an
`haushaltssaldo()` oder klar als Konsolen-Diagnose markieren.*

---

## 2. Verifikation der Übersicht (haushaltssaldo & Wasserfall)

Nachgerechnet gegen die Live-DB:

```
Konten (alle)            82.999,72
+ Posten (im_saldo)     −69.820,00
− Rücklagen              35.459,53
+ Forderungen             6.832,81
= SALDO (KPI)           −15.447,00
```

**Befund B (✅ #9 behoben & verifiziert):** Nach dem heutigen Deploy geht die Wasserfall-Tabelle
**cent-genau** auf. Nachgerechnet:

```
Merkzettel-Summe          −670,00
Posten-im-Saldo-Summe  −69.150,00
Summe                  −69.820,00   ==  Posten(im_saldo)  −69.820,00   ✓ Differenz 0,00
Wasserfall (K−R+MZ+F+P) −15.447,00   ==  SALDO            −15.447,00   ✓ Differenz 0,00
```

Der frühere Bug #9 („Posten fehlen", Merkzettel steckten doppelt in „Posten") ist durch den
Umbau von heute geschlossen — die Herleitung ist jetzt lückenlos.

**Befund C (⚠ latente Konsistenz-Falle, mittel):** Die Tabelle geht nur deshalb auf, weil zwei
Funktionen **unterschiedliche Diskriminatoren** verwenden, die momentan zufällig deckungsgleich sind:

- `haushaltssaldo()` bildet `Posten` über `WHERE im_haushaltssaldo = TRUE`.
- `uebersicht()` teilt dieselben Posten über `gruppe = 'merkzettel'` vs. `im_haushaltssaldo` auf.

Solange **jeder** Merkzettel-Posten `im_haushaltssaldo = TRUE` hat, gilt
`Merkzettel + Posten = Σ im_saldo` und alles stimmt (aktuell erfüllt — verifiziert). **Aber:** ein
einziger Merkzettel-Posten mit `im_haushaltssaldo = FALSE` würde in der Tabelle mitgezählt, im
KPI-Saldo aber fehlen → die Herleitung kippt lautlos. Es gibt **keinen** DB-Constraint, der das
verhindert. → *Empfehlung: beide Sichten über denselben Diskriminator führen, oder Invariante
`gruppe='merkzettel' ⇒ im_haushaltssaldo` per CHECK/Test absichern.*

**Befund D (🟢 UX, niedrig):** Die heute neu eingeführten Kacheln zeigen **negative** Werte:
„Posten" −69.150 (dominiert von *Anlage Großeltern* −72.975 = geparktes geliehenes Geld) und
„Merkzettel" −670. Fachlich korrekt, aber die Kachel-Namen suggerieren Vermögen. → *Erwägen:
Kachel-Untertitel („enthält geparkte Großeltern-Mittel") oder Umbenennung.*

---

## 3. Bug #52 — reproduziert und ursächlich zerlegt (🐞 hoch)

Die driftende Differenz zwischen KPI-Kachel und Stichtag-Box ist real und **exakt herleitbar**:

```
SALDO KPI (alle Buchungen)      −15.447,00
SALDO per Stichtag „heute"      −16.193,86
DRIFT                              +746,86
```

**Ursache — verifiziert:** In der DB liegen **11 Buchungen mit `datum_wert = 31.07.2026`**
(Monatsende, in der Zukunft relativ zu heute 16.07.), Gesamtsumme +11.373,14. Deren Beitrag zum
KPI-Saldo, den die Stichtag-Box (≤ heute) *nicht* sieht:

| Zukunfts-Anteil | Betrag | Wirkung im Saldo |
|---|---|---|
| auf realen Konten | 0,00 | — (keine) |
| Rücklage-Zuführungen (`zaehlt_als='ruecklage'`) | 5.313,14 | **− 5.313,14** (wird abgezogen) |
| Forderung Jörg (`zaehlt_als='forderung'`) | 6.060,00 | **+ 6.060,00** (wird addiert) |
| **Netto-Drift** | | **+ 746,86** |

Das reproduziert die Backlog-Beschreibung (#52) exakt: die KPI-Kachel **nimmt die auf Monatsende
vordatierten Zuführungen vorweg** (Gehalts-Forderung Jörg + Topf-Zuführungen), die per „heute" noch
nicht fällig sind.

**Die eigentliche Frage ist fachlich, nicht technisch:** *Welche Zahl ist „wahr"?*
- Variante 1 — **KPI stichtaggenau machen** (Backlog-Vorschlag): KPI zählt nur `≤ heute` → Saldo
  −16.193,86. Konsistent mit der Stichtag-Box, aber der Monatsplan „fehlt" bis zum 31.
- Variante 2 — **Zukunfts-Buchungen gar nicht vordatieren**: die Monatszuführung erst am Fälligkeitstag
  buchen. Beseitigt die Drift an der Wurzel, ändert aber den Buchungs-Workflow.
- Variante 3 — **Drift bewusst ausweisen** („inkl. Monatsplan +746,86").

→ *Entscheidung des Nutzers nötig. Ohne diese Klärung ist jeder Code-Fix nur eine halbe Antwort.*

---

## 4. Gegenbuchungs-/Spiegel-Mechanik (✅ intakt)

Die Verzehr-Automatik (`gegenbuchung.py`, `spiegel_von_id`) ist das Herz der Saldo-Neutralität:
eine topf-gedeckte Realausgabe erzeugt eine gespiegelte `ruecklage`-Gegenbuchung, sodass
`Konten − Rücklagen` per Saldo 0 bleibt. Integritäts-Check gegen die Live-DB:

```
verwaiste Spiegel (Quelle gelöscht):   0
doppelte Spiegel (>1 je Realbuchung):  0
Rücklagen-Töpfe mit negativem Stand:   0
```

**Befund E (✅):** Die Spiegel-Integrität ist sauber — kein verwaister/doppelter Spiegel, kein Topf
im Minus. Die Idempotenz-Logik (`ON CONFLICT (import_hash)`, `import_hash = spiegel-<id>`) hält.
Die dokumentierte Reihenfolge-Falle (nach `beladung --write` zwingend `gegenbuchung --write` +
`allgemein_toepfe --write`) bleibt jedoch **manuelles Herrschaftswissen** ohne Code-Guard.

---

## 5. Reporting-Konsistenz (✅ mit einer sauberen Konvention)

`ausgaben_je_kategorie`, `monatsverlauf`, `pivot`, `top_empfaenger` schließen alle konsistent
`quelle_import = 'startsaldo'` aus und filtern `buchungsart='real'` — sie zeigen **Bewegungen im
Zeitraum**, nicht Bestände. Die Saldo-Funktionen dagegen zählen den Startsaldo mit (Gesamtstand).
Das ist eine **bewusste, konsistent umgesetzte** Trennung (Bewegung vs. Bestand), kein Bug. Die
SQL-Injection-Oberfläche ist sauber abgesichert (Whitelist-Maps für `sort`/`modus`/`ebene`,
ansonsten parametrisierte Queries).

---

## 6. Befund-Übersicht & Empfehlungen

| # | Befund | Schwere | Status |
|---|---|---|---|
| B | Wasserfall geht cent-genau auf (#9) | — | ✅ behoben, verifiziert |
| C | Konsistenz-Falle `gruppe` vs. `im_haushaltssaldo` | 🟡 mittel | offen (latent) |
| #52 | KPI vs. Stichtag driften +746,86 (vordatierte Zuführungen) | 🔴 hoch | reproduziert, **Fachentscheid nötig** |
| A | `kennzahlen()` mischt Rücklage+Forderung | 🟢 niedrig | harmlos (Konsole), Falle |
| D | „Posten"/„Merkzettel"-Kacheln negativ, missverständlich | 🟢 niedrig | UX |
| E | Spiegel-Integrität, keine neg. Töpfe | — | ✅ sauber |
| — | Migrations-Reihenfolge ohne Code-Guard | 🟡 mittel | offen (Betrieb → Deep Dive II) |

**Konkrete nächste Schritte (empfohlene Reihenfolge):**
1. **#52 fachlich klären** (Variante 1/2/3 oben) — größter Hebel, blockiert den sauberen Fix.
2. **Regressionstest-Set als pytest** (löst zugleich #23b/V1b) — die vier hier von Hand geprüften
   Invarianten automatisieren:
   - `Wasserfall == haushaltssaldo` (Herleitung geht auf),
   - `Σ Merkzettel + Σ Posten-im-Saldo == Σ im_haushaltssaldo` (Befund C),
   - `0 verwaiste + 0 doppelte Spiegel`,
   - `kein Rücklagen-Topf < 0` (bzw. bewusste Ausnahmeliste).
   Diese laufen gegen eine **Wegwerf-DB mit Fixtures**, nicht gegen Produktion.
3. **Befund C entschärfen:** `haushaltssaldo()` und `uebersicht()` auf denselben Diskriminator ziehen.
4. **`kennzahlen()`** an `haushaltssaldo()` angleichen oder als Diagnose kennzeichnen.

---

## 7. Gesamtbewertung Geld-Logik

Das Rechenwerk ist **im Kern solide**: Cent-Arithmetik, saubere Vorzeichen-Trennung über `zaehlt_als`,
funktionierende Spiegel-Neutralität, injection-sichere Queries. Die verbleibenden Probleme sind
**nicht** falsche Arithmetik, sondern **zwei Definitions-Inkonsistenzen** (KPI vs. Stichtag; `gruppe`
vs. `im_haushaltssaldo`) und das **fehlende Testnetz**. Beide sind gut adressierbar — die Drift #52
braucht zuerst eine *fachliche* Entscheidung, dann ist der Code-Fix klein. Das größte strukturelle
Risiko bleibt, dass diese Invarianten heute **nur manuell** (wie in diesem Deep Dive) geprüft werden.

*→ Deep Dive II (Struktur & Betrieb) auf Freigabe: app.py-Schnitt, CI/CD mit Test-Gate, Backup,
Datenschutz-Lücke `lokale_config` im Container.*
