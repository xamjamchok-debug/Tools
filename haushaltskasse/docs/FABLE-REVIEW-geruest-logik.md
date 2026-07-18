# Fable-Review I — Gerüst-Logik: Erkennung, Deckel, Rückstellungslauf

**Stand 2026-07-18 · Fable (read-only-Beratung) · Antwort auf Teil VIII des Auftrags**
(`AUFTRAG-FABLE-geruest-vertraege-rueckstellung.md`, Deliverable 1)

**Methodik.** Statische Code-Analyse (`workflows/vertraege.py`, `workflows/gegenbuchung.py`,
`dashboard/queries.py`, `dashboard/routes/api_vertraege.py`, `domain/saldo.py`,
`storage/schema.sql`) plus **read-only-Nachrechnung gegen die Live-DB** (Verbindung mit
`connection.read_only = TRUE` hart verriegelt, ausschließlich SELECTs; `erkenne()` wurde als
Trockenlauf ausgeführt, `speichere()` nie). Datenstand: 2.967 Realbuchungen
(2024-12-31 … 2026-07-17). Testsuite gelaufen: **18 passed, 6 skipped** (Szenario-Tests
skippen mangels `HAUSHALT_TEST_DATABASE_URL` — die read-only-Invarianten gegen die
Produktiv-DB sind alle grün).

**Kurzfassung der fünf wichtigsten Befunde:**

| # | Befund | Schwere |
|---|---|---|
| L1 | **Alle 26 bestätigten Verträge haben `monatsrate_cent = 0`** — die gesamte Deckel-/Ampel-/Reichweiten-Sicht rechnet mit Nullen und ist heute inhaltlich leer | 🔴 kritisch |
| L2 | **Die Idempotenz-Regel des #76-Designs („irgendeine Einzahlung im Monat → skip") ist an den echten Daten doppelt falsch** — sie würde Monate fälschlich überspringen UND der Zielmonat ist aus `datum_wert` nicht ableitbar | 🔴 kritisch |
| L3 | **Erkennungs-blinde Flecken:** Strom (das Flaggschiff-Beispiel des Designs!), Fitnessstudio und die KFZ-Jahresversicherungen werden strukturell **nie** erkannt | 🟠 hoch |
| L4 | **Haushaltskasse driftet ab 09/2026 sofort:** Soll 1.402, realer Verzehr Ø ≈ 3.031/Mon, Bestand 364,80 → Topf nach dem ersten Monat negativ | 🟠 hoch (Datenfrage, gatet den ersten Lauf) |
| L5 | **Loch im #76-Design: die Forderungs-Stellung.** Der Excel-Lauf stellte auch Jörg (+6.060/Mon); das neue Design deckt nur Rücklage-Nebenbücher — ungeklärt, was ab 09/2026 mit der Gehaltsforderung passiert | 🟠 hoch |
| L6 | Das Erkennungs-**Volumen** ist unkritisch: **39 Kandidaten** (31 aktiv), keine PayPal-Explosion → offene Frage 1 ist mit Daten beantwortbar: **keine neue Klasse nötig** | 🟢 Entwarnung |

---

## 1. Erkennung an echten Daten

### 1.1 Volumen (offene Frage 1) — Entwarnung mit Zahlen

`erkenne()` über die Live-Daten liefert **39 Kandidaten**: 31 aktiv (`erkannt`), 8 `beendet`;
29 monatlich, 5 quartalsweise, 5 jährlich; 1 Eingang (Kindergeld). Verteilung: Auto 6,
Füchschen 8, Haushaltskasse 4, Kredit 3, Nebenkosten 5, Sport 1, TK 1, Telefon 7, Vers 4.

**Die befürchtete PayPal-Explosion findet nicht statt.** Hinter den 220 PayPal-Buchungen
stecken **70 unterschiedliche Händler-Kerne** — aber nur **7** werden Kandidaten (EasyPark ×2,
ADAC-Versicherung, General-Anzeiger aktiv; Google, Spiegel, Adobe beendet). Der
Kern-Betrag-Filter (`_kern_zahlungen`: dominanter Betrag ±15 %, ≥25 % Anteil) frisst die
übrigen 63 Händler zuverlässig weg, weil Einkäufe keinen dominanten Betrag wiederholen.

> **Antwort auf Frage 1: Es braucht KEINE Klasse „regelmäßig, Händler egal".** Die
> Bestätigungsliste ist ~31 Zeilen lang, nicht 80. Die real existierenden Fehltreffer
> (Shell/Tanken 204 €-Rate, SumUp-Eisdiele, historische ALDI-Perioden) sind einzeln
> ignorierbar bzw. laufen über Jörgs manuelle Budget-Töpfe (#88) — genau wie im
> Vorgänger-Design entschieden. Eine zusätzliche Klasse würde Komplexität für ein Problem
> bauen, das die Daten nicht zeigen.

Einschränkung: Das gilt für **diese** Datenlage. Der Filter ist scharf genug, dass er auch
echte Verträge frisst — siehe 1.2.

### 1.2 Erkennungs-blinde Flecken (Befund L3) — hier trägt das Design nicht

Drei Klassen von echten Verträgen sind für die Erkennung **strukturell unsichtbar**:

**(a) Strom — ausgerechnet das Flaggschiff-Beispiel.** Naturwerke (25 Buchungen, fester
Abschlag 78 + 116 €/Monat über 13 Monate) und Tibber (2 Buchungen) tauchen in keinem
Kandidaten auf. Ursache in `_zweck_kern()`: Der Zweck lautet `„Abschlag Strom 04 25 VK …"` —
**der Monats-Token `04 25` (Leerzeichen-getrennt) wird nicht entfernt** (die Regex strippt nur
`\d{1,2}\.\d{1,2}\.\d{2,4}` mit Punkten). Jeder Monat bekommt dadurch einen eigenen
Zweck-Kern → jede Gruppe hat nur 1 Monat → fällt unter `MIN_ZAHLUNGEN`. Dasselbe beim
Fitnessstudio (17 × 53,00 €/Monat, Frank Habermann): `„Nr 1 LF M-Nr 501 Beitrag 03 25 53 00"` —
Monats-Token, rotierender Kurz-Zähler (`lf`→`lg`→`lh`…) und der **Betrag in Leerzeichen-Form**
(`53 00`) machen jeden Monat zur eigenen Gruppe. **Das Aussortier-Problem, das die Verträge
lösen sollten (MAINGAU → Naturwerke → Tibber), ist im Live-System nie angekommen.**

Tibber hat ein zweites, tieferes Problem: **nutzungsbasierte Abrechnung** (8,47 €, 59,66 €, …).
Ein dynamischer Stromtarif wiederholt nie einen Betrag — der Modus-Filter (±15 %) schließt
verbrauchsabgerechnete Verträge **prinzipiell** aus, egal wie gut der Zweck normalisiert wird.

**(b) Jahresversicherungen mit Beitragssprüngen.** ADAC-KFZ (größte Einzelposition im
Nebenbuch Vers): 1.064,18 (2025) → 1.686,98 (2026), gleiche Vertragsnummer — der Sprung
von 58 % liegt außerhalb der ±15 %-Toleranz, es überlebt nur eine Zahlung → kein Kandidat.
Dazu zwei neue KFZ-Verträge mit je 1 Zahlung (1.318,14 / 1.051,51). Ergebnis: **KFZ-Versicherung
≈ 235–330 €/Monat fehlt komplett in der Vertrags-Sicht**, während Vers-Soll 398 dagegen steht.
ARAG (578,04, 1×) und Provinzial (491,00, 1×) analog: mit `MIN_ZAHLUNGEN = 2` braucht ein
jährlicher Vertrag **zwei Jahre Historie**, bevor er erkennbar wird.

> **Antwort auf Frage 3 (Einmal-Verträge):** Nicht die Erkennung aufweichen, sondern die
> Klasse akzeptieren: jährliche Versicherungen und verbrauchsabgerechnete Verträge (Strom)
> sind **manuelle Verträge** (#88: anlegen, Rhythmus jährlich/monatlich, Rate = Jahresbetrag ÷ 12
> bzw. Ø-Verbrauch). Dazu gehört eine **Wahrnehmung im Abgleich**: „Empfänger mit großer
> Einzelzahlung (> X €) ohne Vertrag" — die drei KFZ-Zahlungen, ARAG und Provinzial wären
> damit sichtbar statt still unversorgt. Die `_zweck_kern`-Lücke (Leerzeichen-Monats-Token)
> ist davon unabhängig ein **billiger Fix** mit großem Effekt (Naturwerke/Fitness würden sofort
> erkannt): zusätzlich `\b\d{1,2} \d{2}\b`-Token und `\d{1,3} \d{2}`-Betragsform strippen.

**(c) Empfänger-Normalisierung fehlt.** Drei belegte Doppelungen: EasyPark existiert
**zweimal** als bestätigter Vertrag (#43, #45), weil der PayPal-Empfänger in zwei
Padding-Varianten vorkommt (`…S.C.A` exakt vs. `…S.C.A     ` als 60-Zeichen-Schnitt eines
längeren Feldes — `strip()` erwischt nur Außenränder). ALDI `SUED`/`SUeD` sind zwei Verträge.
Google flattert zwischen `ltd.` und `limited` (26 + 20 Buchungen, zeitlich verzahnt → die
Fortsetzungs-Zusammenführung greift nicht, weil sich die Perioden überlappen). Empfehlung:
vor dem Gruppieren Empfänger normalisieren (lowercase, Umlaut-Transliteration,
Mehrfach-Whitespace kollabieren, `[^a-z0-9 ]` raus) — die Muster-Identität in `speichere()`
dann über die normalisierte Form führen (einmalige Daten-Migration der 41 Bestandszeilen nötig).

### 1.3 Teilstring-Falle (arag ↔ Garage) — Entwarnung, mit einem Vorbehalt

**Es gibt heute keinen ILIKE-Matcher.** `muster_empfaenger`/`muster_zweck` werden an genau
zwei Stellen benutzt: als **exakter** Identitätsschlüssel in `speichere()` (`=`-Vergleich +
UNIQUE-Index) und als Anzeige in `queries.vertraege()`. Kein Codepfad ordnet Buchungen per
Muster einem Vertrag zu — `buchungen.vertrag_id` wird ausschließlich manuell gesetzt (Stand
heute: **0 von 2.967 Buchungen zugeordnet**, das Drag&Drop-Feature ist praktisch ungenutzt,
die 📎-Anzeige zeigt überall nichts). Die arag↔Garage-Falle **kann heute nicht auftreten**.

Vorbehalt: Sobald jemand Auto-Zuordnung baut (naheliegender nächster Schritt, wenn die
📎-Zahlen leben sollen), ist die Falle sofort da — die real gespeicherten Muster enthalten
bereits 3 Teilstring-Paare (PayPal kurz/lang, ALDI-Varianten). Der Schutz „Langform" trägt
nur, solange die Normalisierung aus 1.2(c) existiert. Bis dahin: dokumentierte Regel
„Muster sind Identität, nie Matching" in den Code-Kommentar von `schema.sql` aufnehmen.

### 1.4 `beendet`-Heuristik und Fortsetzungs-Zusammenführung

Die 8 als `beendet` erkannten Kandidaten sind alle plausibel (alte ALDI-Perioden,
ausgelaufene PayPal-Abos, Kiga-Beitrag bis 08/2025, Niederschlagswasser bis 12/2025).
`BEENDET_NACH_RHYTHMEN = 4` ist mit dem Import-Rhythmus verträglich. Die
Fortsetzungs-Zusammenführung (12-Zeichen-Präfix, ±10 %, nicht überlappend) hat an den
Live-Daten korrekt **nicht** fusioniert, wo sie nicht sollte (Kredit-Tranchen 299/305 parallel)
— und die drei Deutsche-Bank-Tranchen summieren auf **2.146,34 ≈ Config-Soll 2.147** des
Nebenbuchs Kredit: die Erkennung reproduziert hier Jörgs Excel-Zahl fast centgenau. Das ist
der stärkste Beleg, dass der Kern der Heuristik trägt.

Zwei Detail-Anmerkungen: (1) `_mache_namen_eindeutig` hängt den Betrag an — dadurch ändert
sich der **Name** eines Vertrags, wenn sich der Median ändert; da die Identität am Muster
hängt, ist das nur kosmetisch, aber im UI verwirrend („Shell (219,40 €)"). (2) Ein durch
Fortsetzung fusionierter Kandidat übernimmt `muster_zweck` des jüngeren Laufs — dadurch kann
sich der Identitätsschlüssel ändern und eine **neue** Zeile neben der alten bestätigten
entstehen. Aktuell kein Treffer (39/39 Kandidaten matchen bestehende Zeilen, nur 2 Altzeilen
ohne frischen Kandidaten), aber der Mechanismus ist fragil — beobachten.

---

## 2. Deckel-Mathematik (Befund L1 — der kritischste Punkt)

### 2.1 Die Deckel-Sicht rechnet heute mit Nullen

`queries.vertraege()` summiert `monatsrate_cent` der **bestätigten** Verträge. In der DB:

> **Alle 26 bestätigten Verträge haben `monatsrate_cent = 0`.**

Ursache (Code, kein Datenunfall): Die Verträge wurden bestätigt, **bevor** die Spalte
`monatsrate_cent` eingeführt wurde (Schema-Nachrüstung `DEFAULT 0`). `speichere()`
aktualisiert die Rate seither nur bei `status = 'erkannt'` — bestätigte behalten „Jörgs
manuellen Wert", der nie existierte. Folge in der Live-Sicht: `summe_ausgang_cent = 0` in
**jedem** Nebenbuch, `rest = Config-Soll`, Ampel überall „ok", keine einzige Warnung, keine
Reichweite. **Die Deckel-/Schiefstellungs-Steuerung, das Herzstück von Baustein 4, ist heute
eine leere Kulisse** — und ein #76-Lauf auf dieser Basis würde schlicht das komplette Soll
nach Allgemein buchen (= Status quo reproduzieren, ohne dass es jemand merkt).

**Empfehlung (zweiteilig):**
1. **Regel-Ergänzung zu Entscheid F:** `monatsrate_cent = 0` bei einem bestätigten Vertrag
   gilt als „**nie gesetzt**", nicht als „Jörg will 0". `speichere()` darf eine 0-Rate auch
   bei `bestaetigt` mit dem Erkennungsvorschlag füllen (`CASE WHEN monatsrate_cent = 0 …`).
   Wer wirklich 0 will, setzt den Vertrag auf `ignoriert` oder trägt manuell z. B. 1 Cent-los
   per Status. (Alternative: eigenes NULL-Semantik-Feld — mehr Aufwand, gleicher Effekt.)
2. **Backfill als erste „Wahrnehmung" des #82-Abgleichs:** „26 bestätigte Verträge ohne
   Rate — Vorschlagswerte übernehmen?" mit Zeile-für-Zeile-Anzeige. Kein stiller Fix.

### 2.2 Was der Deckel nach dem Backfill zeigen würde (nachgerechnet)

Frische Erkennungs-Raten je Nebenbuch (nur aktive Ausgänge) gegen das Config-Soll:

| Nebenbuch | Σ Raten (erkannt) | Config-Soll | Rest | Bewertung |
|---|---:|---:|---:|---|
| Auto | 241,43 | 240,00 | **−1,43** | 🛑 knapp drüber — aber getrieben vom **Fehltreffer Shell/Tanken (204,07)**; ohne Shell: Rest +203 |
| Füchschen | 478,50 aus / 777,00 ein | 0,00 | **+298,50** | ok — Kindergeld deckt die Ausgänge (s. 4.2) |
| Haushaltskasse | 40,00 | 1.402,00 | +1.362,00 | grün — **und trotzdem leert sich der Topf** (s. 2.4) |
| Kredit | 2.146,34 | 2.147,00 | +0,66 | ✅ centgenau — Vorzeigefall |
| Nebenkosten | 138,89 | 320,00 | +181,11 | grün — **aber Strom (~120–190) fehlt wegen L3** |
| Sport | 73,71 | 200,00 | +126,29 | grün — Fitnessstudio (53) fehlt wegen L3 |
| TK | 36,24 | 125,00 | +88,76 | ok |
| Telefon | 116,88 | 253,00 | +136,12 | ok |
| Vers | 101,15 | 398,00 | +296,85 | grün — **KFZ-Versicherung (~235–330) fehlt wegen L3** |
| Urlaub / Inst | — | 600 / 400 | = Soll | keine Verträge (plausibel: Spar-Ziele) |

Zwei strukturelle Erkenntnisse daraus:

**(a) Die Ampel ist bei Konsum-Nebenbüchern blind.** Haushaltskasse: Rest +1.362 „grün",
realer Verzehr aber Ø 3.031/Mon. Der Deckel vergleicht **Vertragsraten** mit dem Soll — den
Alltags-Verzehr (Lebensmittel, Amazon), der denselben Topf leert, sieht er nicht. Für
Nebenbücher, deren Ausgaben überwiegend NICHT vertragsförmig sind, braucht der Abgleich eine
**zweite Kennzahl: Ø Ist-Verzehr der letzten 3 Monate vs. Soll** (liegt als Datum vor, ist
eine Query). Sonst wird die wichtigste Schieflage des Systems (L4) von der Steuerungssicht
nie angezeigt. → in den #82-Screen aufgenommen (siehe App-Design-Dokument).

**(b) Solange L3 nicht behoben ist, sind die grünen Reste von Nebenkosten/Vers/Sport
falsch-positiv** — die fehlenden Verträge (Strom, KFZ, Fitness) verbrauchen den Rest real.
Reihenfolge daher: erst `_zweck_kern`-Fix + manuelle Jahresverträge, dann dem Deckel trauen.

### 2.3 Rest-Soll-Regel und Unterkategorie-Solls

Die dokumentierte Regel `Rest-Soll(Default) = NB-Soll − Σ(Unterkat-Solls)` ist praktisch
ungenutzt: Nur **drei** Unterkategorien tragen überhaupt ein eigenes Soll (Vers/Gebäude 45,
Vers/Versicherung 50, Vers/Haftpflicht 25 — Summe 120 von 398). Alle anderen Nebenbücher
steuern ausschließlich über das Kategorie-Soll. Das ist kein Fehler, aber es heißt: **der
„große Config-Abgleich" (#82) startet auf einer fast leeren Unterkat-Soll-Landschaft** — die
Soll-Übernahme aus Verträgen schreibt also erstmalig flächig Unterkat-Solls und macht die
Rest-Regel scharf. Vorsicht vor Doppelpflege: Vers hat dann sowohl handgesetzte
Unterkat-Solls als auch Vertragsraten in denselben Untertöpfen (Haftpflicht: Soll 25 vs.
Raten 21,40) — der Abgleich muss definieren, **wer gewinnt** (Empfehlung: Vertragsrate
gewinnt, handgesetztes Unterkat-Soll wird zur Wahrnehmung „ersetzt 25 durch 21,40?").

### 2.4 Vier konkrete Daten-Schiefstände, die der Lauf treffen würde

1. **Haushaltskasse hat keine `default_unterkategorie_id`** (einziges Nebenbuch ohne).
   Lauf-Schritt 3 („Rest → Allgemein") hat dort kein Ziel → Crash oder stiller Skip. Vor dem
   ersten Lauf setzen; der Lauf selbst sollte fehlende Defaults als harten Fehler melden.
2. **`ruecklage`-Buchungen ohne Unterkategorie** (verletzt Prinzip 2 „Unverteiltes liegt auf
   Allgemein"): Haushaltskasse +1.675,00, Inst +699,90, Telefon +532,02, Auto +203,00,
   Urlaub +40,00 — Reste der manuellen Juli-Migration. Gehören als Wahrnehmung in den
   Abgleich („auf Allgemein einsortieren?").
3. **Bestands-Verteilung nach der Juli-Migration (#77) ist ideal für den Übergang:** Die
   Untertopf-Bestände sind fast überall ≈ 0, die Masse liegt auf Allgemein (Auto 1.571,75,
   Füchschen 14.619,98, TK 1.480,00 …). Genau darauf baut die Übergangsregel in 3.4.
4. **Der Bestand in `queries.vertraege()` zählt je `kategorie_id` über alle
   `ruecklage`-Buchungen** — inklusive Forderungs-Kategorien, falls dort je Verträge
   entstehen (heute nicht der Fall). Unkritisch, aber eine `zaehlt_als='ruecklage'`-Klausel
   wäre sauberer.

---

## 3. #76-Design gegengerechnet

### 3.1 Die Referenz trägt — und liefert nebenbei den historischen Marker

Die 10 Buchungen vom 31.07.2026 (`fb-kto`, alle auf Allgemein) wurden reproduziert:
**8 von 10 centgenau = Config-Soll** (Auto 240 · Inst 400 · Jörg 6.060 · Kredit 2.147 ·
Sport 200 · Telefon 253 · TK 125 · Vers 398), Nebenkosten 300 (−20), Urlaub 1.250,14
(+650,14), Haushaltskasse und Füchschen fehlen. Bestätigt.

Wichtiger Nebenfund: **Die Excel-Stellungen sind in den Daten markiert** — jede trägt
`verwendungszweck = 'Rückstellung am <Timestamp>'`. Damit sind **19 historische Läufe**
(24.01.2025 … 31.07.2026) exakt identifizierbar, inklusive des Doppel-Laufs am 27.06.2026
(16:06 für Juli, gebucht 30.06; 16:16 für August, gebucht 31.07 — Jörgs Urlaubs-Trick, beide
im selben Excel-Sitzungslauf). Der Nachbau-Test für #76 kann sich auf diese Marker stützen.

### 3.2 Idempotenz (Befund L2): die Design-Regel ist an den echten Daten falsch

Das Design sagt: *„existiert für (Nebenbuch, Monat) schon eine Einzahlung (egal welche
Quelle) → skip."* Zwei Probleme, beide mit Daten belegt:

**(a) False-Skip.** „Einzahlung" ≙ positive `ruecklage`-Buchung — davon gibt es in fast
jedem Monat welche, die **keine Stellungen** sind: Erstattungen (PayPal-Rückzahlung +200,
Amazon-Retouren +9,99 …), ab Juli automatisch auch **Spiegel-Zuführungen** realer Eingänge
(belegt: Cashback +0,43 vom 15.07. hat `spiegel=1`). Beispiel April 2026: kein Excel-Lauf im
April (der 30.03.-Lauf war der April-Lauf), aber Auto +119,00 und Urlaub +6,48 als
Erstattungs-Zeilen — die Design-Regel hätte den April als „gestellt" markiert. Künftig würde
**jede Kindergeld-Zahlung Füchschen für den Monat sperren** und jede Retoure ihr Nebenbuch.
Die Rücklage fehlt dann still — genau der Drift, den #76 verhindern soll.

**(b) Zielmonat ≠ Kalendermonat von `datum_wert`.** Die 19 Excel-Läufe liegen auf dem 24.01.,
25.02., 31.03., 24.04., 26.05., 24.06., 02.08., 01.09., 29.09., 05.11., 26.11., 03.01.,
01.02., 03.03., 30.03., 09.05., 26.05., 30.06., 31.07. — mal Monatsanfang, mal -ende, zwei
Läufe im selben Kalendermonat (Sep/Nov 25, Mär/Mai 26), gar keiner im Jul/Okt/Dez 25 und
Apr 26. **Aus `datum_wert` lässt sich der Zielmonat einer Stellung nicht rekonstruieren.**
Jede kalendermonatsbasierte Prüfung rät.

**Empfehlung — Idempotenz ausschließlich über eigene Artefakte + Anker:**

```
1. quelle_import = 'rueckstellung' und import_hash = 'rueckstellung-<kategorie_id>-<JJJJ-MM>'
   (Zielmonat EXPLIZIT im Hash; UNIQUE-Constraint auf import_hash existiert bereits
   → ON CONFLICT DO NOTHING ist die gesamte Idempotenz, wie beim Spiegel-Muster).
2. Anker in einstellungen: 'rueckstellung_start' = '2026-09'.
   Der Lauf holt rückwirkend NUR Monate >= Anker nach. Alles davor ist Excel-Territorium
   und per Definition gestellt — Jörgs vorab gestellter August (31.07., fb-kto) ist damit
   KONSTRUKTIV unantastbar, ohne dass irgendeine Heuristik ihn erkennen muss.
3. datum_wert = 1. des Zielmonats (Konvention; der fachliche Schlüssel bleibt der Hash).
   Nebeneffekt: beseitigt die #52-Drift-Quelle „vordatierte Zuführungen" für die Zukunft.
4. Fremde Quellen werden für die Idempotenz IGNORIERT. Schutz vor Doppelung mit manuellen
   Stellungen ist Aufgabe des Trockenlaufs (zeigt vorhandene manuelle +Buchungen des
   Zielmonats als Hinweis), nicht einer automatischen Skip-Regel.
```

Das ersetzt die Design-Regel — Entscheid G (rückwirkend, nie doppelt) bleibt vollständig
erfüllt, wird aber deterministisch statt heuristisch.

### 3.3 Reproduziert der Lauf die Referenz? Ja — unter zwei Bedingungen

Mit Rate-Backfill (2.1) und Rest-Regel bucht der Lauf je Nebenbuch **in Summe exakt das
Config-Soll** — identisch mit den 8 centgenauen Referenzwerten; nur die Aufteilung wird
vertragsfein statt „alles auf Allgemein". Die Abweichler Nebenkosten/Urlaub sind
Handanpassungen (4.3), Haushaltskasse/Füchschen Datenfragen (4.1/4.2). Bedingungen:

1. **Eingang-Verträge dürfen im Lauf NICHT gebucht werden** (nur Ausgänge). Das Kindergeld
   (+777, Vertrag #71 `eingang`) fließt ab Ende der FB-Beladung **automatisch** als
   Spiegel-Zuführung in den Topf (positiver Real-Eingang in Rücklage-Kategorie →
   `SQL_SPIEGEL_BERECHTIGT` kennt kein Vorzeichen; an dkb-/amazon-Buchungen bereits belegt).
   Würde der Lauf zusätzlich die Eingang-Rate stellen, käme das Kindergeld **doppelt** an.
   Eingänge gehören nur in die Netto-Sicht des Deckels (wo sie schon sind). Das steht so
   in keinem der Design-Dokumente — es muss als harte Regel in #76.
2. **Forderungs-Nebenbücher (Befund L5) explizit ausklammern und entscheiden.** Der
   Excel-Lauf stellte in allen 19 Läufen auch **Jörg** (+5.775 … +6.204, Soll 6.060) und
   vereinzelt Natalie; monatlich dagegen der Ausgleich −6.304,33 (Gehaltseingang). Beides
   endet mit der FB-Beladung. #76 sagt dazu nichts; `queries.vertraege()` kennt nur
   Nebenbücher mit Verträgen. Würde der Lauf Forderungen mit stellen, wüchse die Forderung
   +6.060/Mon **ohne Ausgleichsmechanik** → der Haushaltssaldo (Formel: + Forderungen)
   inflationiert. Empfehlung: **Forderungs-Kategorien im ersten Ausbau nicht stellen**,
   Bestand einfriert bei ~5.983 (kein Drift, nur stehende Größe), und die
   Gehalts-/Forderungsmechanik als eigenes Thema designen. Das gehört als bewusste
   Entscheidung zu Jörg — nicht als stiller Nebeneffekt.

### 3.4 Übergang „alles auf Allgemein" → vertragsbasiert (offene Frage 2) — EINE Regel

> **Stichtagsregel: „Bestände bleiben liegen — Raten gehen fein — Perioden-Verträge
> bekommen eine einmalige Startdotierung per Binnen-Umbuchung."**
>
> 1. **Keine rückwirkende Umverteilung.** Alle vor 09/2026 gestellten Beträge bleiben, wo
>    sie sind — auf Allgemein. Das ist kein Kompromiss, sondern Prinzip 2: Allgemein IST der
>    bewusste Puffer. (Die Daten stützen das: nach der Juli-Migration #77 sind die
>    Untertopf-Bestände ohnehin ≈ 0, die Masse liegt bereits sauber auf Allgemein.)
> 2. **Ab dem ersten Lauf (Anker 2026-09)** fließt je bestätigtem Ausgangs-Vertrag die Rate
>    auf seinen Untertopf, der Rest aufs Allgemein des Nebenbuchs. Monatliche Verträge sind
>    damit sofort im Gleichgewicht (Rate rein, Verzehr raus, Nulllinie).
> 3. **Nur für nicht-monatliche Verträge** (quartalsweise/jährlich) schlägt der erste Lauf
>    (bzw. der #82-Abgleich) eine **einmalige Startdotierung** vor:
>    `Untertopf ← Umbuchung aus Allgemein über Rate × (Monate seit letzter Fälligkeit)`,
>    gedeckelt auf den Allgemein-Bestand. Trockenlauf, Jörg bestätigt je Zeile.
>    Ohne diesen Schritt läuft z. B. die HUK-Jahresrechnung (751,51, fällig 03/2027) auf
>    einen Untertopf auf, der bis dahin nur 6 × 62,63 = 375,78 angespart hat → Untertopf
>    tief negativ, während der angesparte Rest „falsch" in Allgemein liegt.
>
> **Warum das mit Prinzip 1 verträglich ist:** Die Startdotierung ist eine reine
> **Binnen-Umbuchung innerhalb des Nebenbuchs** (Allgemein −X, Untertopf +X). Der
> Rücklagensaldo des Nebenbuchs — die Größe, die Prinzip 1 schützt — ändert sich um exakt 0.
> Und sie passiert nur auf Jörgs Bestätigung im Abgleich, nicht automatisch. Die
> Umbuchungs-Mechanik existiert bereits (Rücklagen-Reiter, „Umbuchen zwischen Töpfen").

Verworfene Alternativen, der Vollständigkeit halber: *rückwirkend fein umverteilen* (18
Monate Historie umbuchen — hoher Aufwand, verfälscht die Historie, Nutzen nur kosmetisch)
und *gar nichts dotieren* (Perioden-Verträge starten strukturell unterdeckt, jede
Jahresrechnung reißt den Untertopf ins Minus und erzeugt Fehl-Warnungen ein Jahr lang).

### 3.5 Offene Fragen 4 und 5 (Warnung hart · Reichweite)

**Frage 4 — „hart" heißt: nur das betroffene Nebenbuch pausiert.** Ein globaler Stopp würde
wegen eines einzigen roten Nebenbuchs (nach 2.2 wäre das heute Auto — wegen eines
*Fehltreffers*) die Rücklage aller anderen Nebenbücher verhindern; genau die Drift, die der
Lauf beseitigen soll, entstünde selektiv weiter. Die 19 Excel-Läufe zeigen zudem, dass Jörg
immer **je Nebenbuch** justiert hat, nie alles-oder-nichts. Der Trockenlauf zeigt das rote
Nebenbuch mit Grund; der Write-Lauf bucht die grünen und lässt das rote mit 🛑 stehen
(nachholbar per G, sobald gelöst).

**Frage 5 — Reichweite je Nebenbuch messen, nicht je Untertopf.** Der Bestand liegt real auf
Allgemein (14.620 von 14.620 bei Füchschen); Untertopf-Bestände sind heute ≈ 0 und nach dem
Übergang monatelang klein. Eine Untertopf-Reichweite wäre Scheinpräzision. `queries.vertraege()`
macht es bereits richtig (Bestand je `kategorie_id`).

---

## 4. Datenfragen 8–10 (aus den Daten beantwortet)

### 4.1 Frage 8 — Haushaltskasse: Lücke, und zwar die gefährlichste (Befund L4)

Haushaltskasse kommt in **keinem einzigen** der 19 Excel-Läufe vor — sie war bis zur
#77-Migration (Juli: +112.917,29 manuell eingebucht, sofort gegen 112.552 Alt-Verzehr
verrechnet, Rest-Bestand **364,80**) schlicht kein Topf; die Ausgaben liefen als
„laufende Ausgaben" am Rücklagensystem vorbei. **Jetzt ist sie ein Topf mit
Auto-Verzehr** — realer Abfluss 2026: −2.239 … −5.438, **Ø −3.031/Monat** — aber Soll 1.402
und faktisch ohne Bestand. Ab 09/2026 heißt das: **der Topf ist nach dem ersten Monat
~−1.600 und fällt danach jeden Monat weiter.** Zusätzlich fehlt die Default-Unterkategorie
(2.4.1), d. h. selbst die 1.402 wüssten nicht, wohin.
**Vor dem ersten Lauf zwingend entscheiden:** Soll auf ~2.900–3.100 anheben (ehrliches
Budget; verschiebt den Config-Monats-Saldo sichtbar um ~−1.600) ODER bewusst
`schiefstellung_erlaubt` + realistisches Teilsoll — dann zeigt die Reichweite sofort „~0
Monate" und macht die Unterdeckung wenigstens sichtbar. Stillschweigend so lassen ist die
einzige falsche Option.

### 4.2 Frage 9 — Füchschen: Soll 0 ist konsistent, Design-Zahl zu pessimistisch

Das Kindergeld (+777/Mon) wurde in der Excel-Welt als Einzahlung geführt und kommt in der
App-Welt **automatisch** wieder: als Spiegel-Zuführung des realen Eingangs (3.3.1). Realer
Netto-Fluss 2026: +178 / −8.611 (Februar-Sonderausgabe) / +28 / +178 / +178 / −111 / −234 —
**ohne den Februar ≈ −171/Mon Grundrauschen** (nicht −475: die Design-Rechnung
„OGS+Essensgeld ≈ 475" ignoriert den Kindergeld-Eingang). Bestand 14.619,98,
`schiefstellung_erlaubt` ist bereits gesetzt. **Soll 0 kann bleiben**; die ehrliche
Reichweiten-Anzeige ist „Netto ≈ −171/Mon (zzgl. Sonderausgaben) · reicht ~85 Monate", nicht
„31 Monate". Reichweite sollte deshalb auf dem **realen Netto-Fluss** (Ø 3–6 Monate) beruhen
können, nicht nur auf `Σ Raten − Soll` — sonst steht bei Füchschen dauerhaft eine falsche Zahl.

### 4.3 Frage 10 — Nebenkosten −20 / Urlaub +650: systematisch, nicht Ausreißer

Die 19 Excel-Läufe zeigen: Jörg hat **fast jeden Monat von Hand justiert**. Nebenkosten
wurde gestellt mit 288 / 355 / 647 / 379 / 399 / 350 / 423 / 399 / 458 / 359 / 399 / 1.142 /
299 / 78 / 75 / −68 / 200 / 250 / 300 — der „−20" vom 31.07. ist schlicht der jüngste
Handgriff einer durchgängigen Praxis. Urlaub analog: 587 … 1.000er-Serien, 7.491,82
(Feb 26), 2.500, 1.762, 1.250,14, dazu einmal „Rückstellung Ziele" +2.522,10 — Urlaub ist
ein **Ziel-Spar-Topf** mit unregelmäßigen Sonderzuführungen, kein Fest-Raten-Topf.
**Konsequenz fürs Design (wichtig):** Das fixe Config-Soll des #76-Laufs ist gegenüber der
gelebten Excel-Praxis eine **Verhaltensänderung** — Excel war „Vorschlag + monatliche
Handkorrektur", die App wird „fixes Soll + Ausnahme ist eine bewusste manuelle Buchung".
Das ist die richtige Richtung (Prinzip 3: nie still ausgleichen), aber der #82-Abgleich muss
diese Justier-Geste ersetzen, und der Lauf-Trockenlauf sollte je Nebenbuch den
Vormonatswert anzeigen, damit Jörg Abweichungsbedarf **vor** dem Buchen erkennt. Für
Sonderzuführungen (Urlaub) reicht die bestehende manuelle ＋-Buchung im Rücklagen-Reiter —
keine Sonderlogik im Lauf bauen.

---

## 5. Bewertung der Entscheidungen A–G und Prinzipien (#80)

| Entscheid | Bewertung |
|---|---|
| **A** eigene Unterkat je Vertrag | ⚠️ **Design und Code widersprechen sich — zugunsten des Codes entscheiden.** Die Erkennung legt **keine** eigene Unterkategorie an; sie hängt den Vertrag an die bestehende Unterkategorie seiner Buchungen (`unterkategorie_id` aus der Gruppierung). De facto teilen sich Verträge bestehende Auswertungs-Untertöpfe (3 DB-Kredit-Tranchen → „Immobilienkredit"). Das funktioniert, vermeidet Topf-Wildwuchs und hat die Live-Daten nie gestört. Empfehlung: **Doku an die Realität anpassen** („Vertrag zeigt auf eine Unterkategorie; Default ist die Unterkategorie seiner Buchungen"), nicht den Code ans Papier. |
| **C** Warnung hart | ✅ trägt — präzisiert auf „hart je Nebenbuch" (3.5). |
| **D** erst bestätigen | ✅ trägt; Volumen beherrschbar (31 aktive Kandidaten). |
| **E** kein Topf „Rücklage" | ✅ trägt uneingeschränkt. |
| **F** Erkennen ≠ Ändern | ✅ trägt — mit der Rate-0-Lücke aus 2.1: „bestätigt = eingefroren" friert auch nie gesetzte Raten ein. Regel ergänzen (0 = nicht gesetzt). |
| **G** rückwirkend, nie doppelt | ✅ trägt — aber nur mit deterministischer Idempotenz (Hash + Anker, 3.2), nicht mit der Monats-Heuristik des Designs. |
| **Prinzip 1–3** | ✅ tragen. Prinzip 2 ist heute durch NULL-Unterkat-Buchungen verletzt (2.4.2) — Wahrnehmung, kein Konzeptfehler. Die Übergangs-Startdotierung (3.4) ist mit Prinzip 1 verträglich (Binnen-Umbuchung, NB-Saldo unverändert). |

---

## 6. Priorisierte Empfehlungen (kompakt)

1. **#76 bauen wie geplant, aber mit drei Korrekturen am Design:** Idempotenz über
   `import_hash + Anker 2026-09` statt Monats-Heuristik (3.2) · nur Ausgangs-Verträge
   stellen (3.3.1) · Forderungs-Nebenbücher ausklammern und als offene Entscheidung an Jörg
   (3.3.2). Warnung hart = je Nebenbuch (3.5).
2. **Rate-Backfill vor dem ersten Lauf** (2.1) — sonst bucht der Lauf faktisch „alles auf
   Allgemein" und niemand merkt es. Als erste Wahrnehmung in #82.
3. **Datenfragen vor dem ersten Lauf lösen:** Haushaltskasse-Soll (+ Default-Unterkat!)
   ist die dringendste (4.1); Füchschen kann bleiben (4.2); Nebenkosten/Urlaub sind
   Arbeitsweise, keine Fehler (4.3).
4. **`_zweck_kern`-Fix** (Leerzeichen-Monats-/Betrags-Token) + Empfänger-Normalisierung —
   billig, holt Strom/Fitness in die Erkennung und beseitigt die EasyPark/ALDI-Dubletten (1.2).
5. **Jahres-/Verbrauchs-Verträge als manuelle Verträge etablieren** (KFZ, ARAG, Provinzial,
   Tibber) mit Wahrnehmung „große Einzelzahlung ohne Vertrag" (1.2b).
6. **Übergang nach der Stichtagsregel** (3.4): Bestände bleiben, Raten gehen fein,
   Startdotierung für Perioden-Verträge per bestätigter Binnen-Umbuchung.

*Alle Zahlen dieses Dokuments stammen aus der Live-DB vom 2026-07-18 (read-only) bzw. aus
dem Trockenlauf von `erkenne()`. Kein Schreibzugriff, kein Deploy, keine Config-Änderung.*
