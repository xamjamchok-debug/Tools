# Design: Verträge & automatische Rückstellung

> **Stand 2026-07-17 · Entwurf zur Entscheidung.** Basiert auf Jörgs Vorgaben vom selben Tag.
> Kein Code gebaut — erst wenn du zustimmst.

---

## 🔒 Grundprinzipien (Jörg 2026-07-17, unverhandelbar)

Diese drei Sätze gelten über allem anderen — sie definieren, was der Rücklagensaldo *ist*:

1. **Der Rücklagensaldo bleibt, wie er ist.** Er wird NUR angefasst, wenn (a) Jörg es manuell tut
   oder (b) der monatliche **Rückstellungslauf** ihn bildet. Kein Import, keine Erkennung, keine
   Zuordnung, kein automatischer Prozess verändert den Saldo. (Deckt sich mit #76: Verzehr läuft
   automatisch, Einzahlung nur durch den Lauf oder von Hand.)

2. **Nicht verteiltes Budget liegt auf der Position „Allgemein"** je Nebenbuch. Das ist der Rest
   des Nebenbuch-Solls, der (noch) keinem Untertopf/Vertrag zugeordnet ist. Er kann später verteilt
   ODER für **unregelmäßige Zahlungen** verwendet werden (Puffer). „Allgemein" ist damit kein
   Fehler, sondern der bewusste Sammel-/Puffertopf. (Vgl. #77: S-Töpfe = Allgemein.)

3. **Alle Buchungen eines Nebenbuchs zusammen sollen die Rücklage bilden.** Stimmt die Summe der
   tatsächlichen Buchungen nicht mit der gebildeten Rücklage überein, muss es eine **Wahrnehmung**
   (sichtbare Anzeige/Warnung) geben. Jörg behandelt sie dann bewusst — indem er **entweder eine
   Überbuchung akzeptiert ODER die Rücklage erhöht**. Nie still automatisch ausgleichen.

---

## Deine drei Vorgaben

1. **Rückstellung auf erkanntem Rhythmus** — nicht manuell gepflegt, nicht geschätzt.
2. **Verträge als eigenes Ding**, die man Unterkategorien/Nebenbüchern zuweist. Ein Vertrag hat
   erstmal eine eigene Unterkategorie mit seinem Namen, ist aber **konfigurierbar bündelbar** zu
   einer übergreifenden Unterkategorie.
3. **⚠️ Die Steuerung darf nicht verloren gehen:** *„Wenn Du automatisch saldierst, müssen wir
   schauen, dass wir aus dem konfigurierten Volumen, was ich diesem Nebenbuch gebe, nicht
   rausgehen. Da muss ich dringend Warnung haben … wenn wir das automatisch machen, hab ich diese
   Steuerungssicht nicht mehr."*

---

## Punkt 3 zuerst — die Steuerung. **Der Deckel existiert schon.**

Das ist die wichtigste Erkenntnis: **Die Struktur, die du willst, ist bereits in der DB.**

| Feld | Bedeutung | Wer setzt es |
|---|---|---|
| `kategorien.monatliche_ruecklage_cent` | **dein Volumen je Nebenbuch** = die Steuerung | **DU, in der Config** |
| `unterkategorien.monatliche_ruecklage_cent` | Soll je Untertopf | heute: du · künftig: Vorschlag der Automatik |
| `kategorien.default_unterkategorie_id` | der Auffang-Topf | du |

Und die bereits geltende Regel lautet:

```
Rest-Soll(Default-Unterkat) = Nebenbuch-Soll − Σ(explizite Unterkat-Soll)
```

**Damit ist die Warnung fast geschenkt:** Wenn die erkannten Verträge zusammen mehr fordern als
dein Nebenbuch-Volumen hergibt, wird dieser **Rest negativ**. Das ist exakt das Signal
„die Automatik will aus deinem konfigurierten Volumen raus".

### Die Regel, die daraus folgt (**das Herzstück**)

> **Die Automatik darf rechnen und vorschlagen — aber niemals das Nebenbuch-Soll ändern.
> Dein Config-Wert ist der Deckel. Passt der Vorschlag nicht darunter, gibt es eine Warnung
> und die Automatik schreibt nichts.**

Drei Fälle:

| Fall | Σ(Verträge) vs. dein Nebenbuch-Soll | Was passiert |
|---|---|---|
| ✅ **passt** | Summe < Volumen | Rest bleibt positiv → geht in den Default-Topf. Alles gut. |
| ⚠️ **eng** | Summe ≈ Volumen (>90 %) | Hinweis: „Puffer fast weg" |
| 🛑 **Überschreitung** | Summe > Volumen | **WARNUNG + keine automatische Änderung.** Anzeige: welche Verträge, wieviel fehlt. **Du entscheidest:** Volumen erhöhen · Vertrag in ein anderes Nebenbuch · Vertrag ignorieren |

**Deine Steuerungssicht bleibt damit vollständig erhalten** — du siehst sogar mehr als heute:
nicht nur „ich habe X € vorgesehen", sondern **„X € vorgesehen, die laufenden Verträge fordern Y,
Differenz Z"**. Das ist genau die Über-/Unterschuss-Sicht, die du bei den Untertöpfen wolltest.

---

## Punkt 2 — Verträge: **ja, und zwar aus einem Grund, der alles andere löst**

**Deine Idee ist richtig.** Das stärkste Argument dafür ist dein eigenes Dauerproblem:

> **Stromanbieter wechseln ständig.** In den Daten: MAINGAU → Naturwerke → Tibber.
> **Fitnessstudios ebenso:** die alten (fifi/Robbie) → das heutige.

Heute ist der **Anbietername der Anker** — und der ist instabil. Deshalb musste man alte Werte
„aussortieren". **Mit Verträgen verschwindet das Problem:**

```
Nebenbuch  "Nebenkosten"
  └─ Unterkategorie "Strom"          ← stabil, HIER liegt der Rücklagen-Topf
       ├─ Vertrag "MAINGAU"     [beendet 05/2025]   ← zählt nicht mehr fürs Soll
       ├─ Vertrag "Naturwerke"  [beendet 04/2026]   ← zählt nicht mehr fürs Soll
       └─ Vertrag "Tibber"      [aktiv, monatlich]  ← liefert die Rate
```

**Damit löst sich deine Kritik von selbst.** Niemand sortiert mehr historische Werte aus:
Die alten Verträge sind **`beendet`** (weil seit >2 Rhythmen keine Zahlung kam) und zählen
deshalb nicht fürs Soll — **bleiben aber für die Historie sichtbar**. Das ist eine Regel,
kein Handgriff.

### Die Rollenteilung

| | **Vertrag** | **Unterkategorie** |
|---|---|---|
| Lebensdauer | **zeitlich begrenzt** (fängt an, hört auf) | **stabil** über Anbieterwechsel hinweg |
| Hat | Rhythmus, Betrag, nächste Fälligkeit, Anbieter, Status | den **Rücklagen-Topf** |
| Zweck | **Erkennung** — woher kommt die Rate? | **Buchhaltung** — wo liegt das Geld? |
| Anzahl | **N Verträge** | **→ 1 Unterkategorie** |

### Deine Frage: eigene Unterkategorie je Vertrag — oder direkt bündeln?

> *„Verträge haben für sich erst mal eine Unterkategorie, die gleich dem Vertragsnamen ist, aber
> ggf. werden sie gebündelt konfigurierbar zu einer übergreifenden Unterkategorie. Wär das was —
> oder soll man's direkt zulassen, dass die Verträge für sich untergehen?"*

**Empfehlung: dein erster Vorschlag.** Also: Ein neu erkannter Vertrag legt **standardmäßig eine
eigene Unterkategorie mit seinem Namen** an — und du kannst ihn **per Config auf eine bestehende
Unterkategorie umhängen** (= bündeln). Gründe:

- **Es ist genau deine Faustregel, nur automatisch.** Tibber „einzeln" ist ein Vertrag → eigene
  Unterkat. Aldi/Lidl/EDEKA sind gar keine Verträge (kein Rhythmus!) → tauchen hier nie auf.
  **Die Bündelfrage stellt sich nur noch bei echten Verträgen** — und da ist Bündeln der Sonderfall
  (Anbieterwechsel), nicht der Normalfall.
- **Nichts geht verloren:** Wenn du drei Stromverträge auf „Strom" bündelst, bleibt die
  Vertragsebene darunter erhalten — du siehst weiterhin, welcher Anbieter wann was kostete.
- Die Alternative („Verträge gehen in Unterkategorien auf") würde die Anbieter-Historie platt
  machen und **genau das Aussortier-Problem zurückbringen**.

> ⚠️ **Ein Vorbehalt:** Wenn jeder Vertrag automatisch eine Unterkategorie erzeugt, drohen bei ~66
> PayPal-Händlern + Abos schnell **sehr viele Untertöpfe**. Deshalb: Eine Unterkategorie entsteht
> **nur bei erkanntem Rhythmus** (echter Vertrag), und du **bestätigst** neue Verträge einmal,
> bevor sie einen Topf bekommen. Kein Wildwuchs.

---

## Punkt 1 — die Erkennung (Kurzfassung, Details in der Arbeitsliste, Abschnitt 8)

| Schritt | Regel |
|---|---|
| Rhythmus | Abstände messen → monatlich / quartalsweise / jährlich (**getestet, funktioniert**) |
| Betrag | **Median** der letzten Zahlungen → Ausreißer/Wechselmonate fallen von selbst raus |
| Läuft noch? | letzte Zahlung > 2 Rhythmen her → **`beendet`** (kein manuelles Aussortieren) |
| Rate | `Jahresbetrag ÷ 12` |
| Ziel-Bestand | `Rate × Monate bis zur nächsten Fälligkeit` |
| kein Rhythmus | **kein Vertrag, keine Rückstellung** → Puffer (Judo-Extras, Arzt, Konsum) |

**Wichtig:** Verträge erkennen sich über **Empfänger + Verwendungszweck** — nicht nur Empfänger.
Beleg: An „Gemeinde Wachtberg" hängen vier Zwecke in **drei verschiedenen Nebenbüchern**
(OGS → Füchschen · Grundsteuer → Nebenkosten · Abwasser → Nebenkosten · Pacht). Ohne den Zweck
ist das nicht trennbar. Gleiches bei PayPal (66 Händler hinter einem Namen).

---

## Vorgeschlagene Tabelle (Entwurf)

```sql
CREATE TABLE vertraege (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                TEXT NOT NULL,                    -- "Tibber", "OGS Kind 1"
    unterkategorie_id   INTEGER NOT NULL REFERENCES unterkategorien(id),  -- N:1 -> hier liegt der Topf
    muster_empfaenger   TEXT,                             -- ILIKE-Muster (Langform!)
    muster_zweck        TEXT,                             -- entscheidend bei Gemeinde/PayPal
    rhythmus            TEXT CHECK (rhythmus IN ('monatlich','quartalsweise','halbjaehrlich','jaehrlich','unregelmaessig')),
    betrag_median_cent  BIGINT,                           -- Median, nicht Mittelwert
    letzte_zahlung      DATE,
    naechste_faellig    DATE,
    status              TEXT NOT NULL DEFAULT 'erkannt'   -- erkannt -> bestaetigt | beendet | ignoriert
                        CHECK (status IN ('erkannt','bestaetigt','beendet','ignoriert')),
    quelle              TEXT NOT NULL DEFAULT 'auto' CHECK (quelle IN ('auto','manuell')),
    erstellt_am         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**An `buchungen` ändert sich nichts** — die hängen weiter an der Unterkategorie. Der Vertrag ist
die Erkennungs-/Planungsebene darüber. (Optional später `buchungen.vertrag_id` für Pins.)

---

## Ablauf im Betrieb

1. **Erkennen** (nach jedem Import): Verträge vorschlagen → Status `erkannt`.
2. **Du bestätigst** einmal je Vertrag: Name, Ziel-Unterkategorie (bündeln?), Rhythmus stimmt?
   → `bestaetigt`. Falsche → `ignoriert`.
3. **Soll berechnen:** je Unterkategorie = Σ(Raten der `bestaetigt`-Verträge).
4. **🛑 Deckel prüfen:** Σ(Unterkat-Soll) je Nebenbuch **gegen dein Config-Volumen**.
   Überschreitung → **Warnung, kein Schreiben.**
5. **Erst nach deinem OK** werden die Unterkat-Solls geschrieben (Trockenlauf zuerst, wie immer).
6. Verzehr bei Fälligkeit läuft über die vorhandene Gegenbuchungs-Mechanik.

---

---

# 🛑 Der fehlende Kern: **der monatliche Rücklagenlauf**

> **Jörg, 2026-07-17:** „Im Excel gab es doch eine Funktion, die Rücklage heißt. Die hat auf die
> Nebenbücher jeden Monat die per Config geplanten Rücklagen eingezahlt. **Das hast du noch gar
> nicht.** … Diese virtuellen Buchungen will ich **einmal im Monat anstoßen** und sagen: okay,
> jetzt bilde die Rücklagen für den nächsten Monat."

## ⚠️ Befund (geprüft 2026-07-17): **Er hat recht — und es ist dringend**

Es gibt **keinen** Rückstellungs-/Einzahl-Workflow. In `workflows/` existiert nichts dergleichen.
Die Zahlen bestätigen es:

| Quelle der `ruecklage`-Buchungen | + (Einzahlung) | − (Verzehr) | Zeitraum |
|---|---|---|---|
| **`fb-kto`** (= **Excel-Beladung**) | **328** | 1281 | 2025-01-02 … **2026-07-31** |
| `spiegel` (automatischer Verzehr beim Import) | 4 | 58 | ab 2026-07-04 |
| `manuell` | 67 | 25 | 2026-07 |
| `startsaldo` | 12 | 0 | 2024-12-31 |

**Alle Einzahlungen kommen aus der Excel-Beladung** — und die reicht bis **31.07.2026**.
Der **Verzehr läuft dagegen automatisch weiter** (Spiegel bei jedem Import).

> ### 🛑 **Sobald die Excel-Daten enden, wird nur noch entnommen und nie mehr eingezahlt.**
> Die Töpfe leeren sich, der Haushaltssaldo driftet — **nicht** wegen eines Rechenfehlers, sondern
> weil die zentrale Funktion der alten Excel-Kasse in der App fehlt. **Das ist der wichtigste
> offene Punkt — vor Verträgen, vor Kategorien.**

### ✅ Entwarnung zum Zeitpunkt (Jörg, 2026-07-17): **es driftet erst ab September**

> Jörg: *„Ich habe noch den besonderen Trick gemacht, dass wir jetzt einen Monat in Urlaub fahren
> und ich die Rücklagen für den nächsten Monat, für den **August**, schon gestellt habe. Deswegen
> siehst du diese vordatierten Werte. **Das kommt jetzt nur einmal vor** … ich ging davon aus, dass
> ich das im Urlaub nicht machen kann. **Dennoch möchte ich die jetzige Rückstellung behalten.**"*

**Die August-Rücklage ist bereits gestellt** (noch Excel-basiert, bewusst vorgezogen wegen Urlaub).
**⇒ Der Drift beginnt erst ab 09/2026**, nicht im August. Etwas Luft — der Punkt bleibt aber Nr. 1.

**🚫 Nicht anfassen:** Diese Stellung bleibt **unverändert** (Jörgs ausdrücklicher Wunsch —
„sonst verwirrt mich das nur noch mehr").

### 🎁 Und sie ist die **Bauanleitung** für den Lauf

Die 10 Buchungen vom **31.07.2026** (`quelle_import='fb-kto'`, alle auf **Allgemein**) zeigen
exakt, wie der Excel-Lauf rechnete — **8 von 10 stimmen centgenau mit dem Config-Soll**:

| Nebenbuch | gestellt 31.07. | Config-Soll | |
|---|---|---|---|
| Auto · Inst · Jörg · Kredit · Sport · Telefon · TK · Vers | = Soll | = Soll | ✅ **exakt** |
| Nebenkosten | 300,00 | 320,00 | ⚠️ 20 weniger |
| Urlaub | 1.250,14 | 600,00 | ⚠️ 650,14 mehr (Urlaubs-Sonderzahlung?) |
| **Haushaltskasse** | **— nicht gestellt** | **1.402,00** | ⚠️ **fehlt ganz** |
| Füchschen | — | **0,00** | ⚠️ kein Soll hinterlegt |

**Damit ist der Lauf testbar:** Nachbau muss für 08/2026 dieselben Zahlen produzieren.
Und die Regel „alles auf Allgemein" bestätigt Jörgs Beschreibung — es gibt ja noch keine Verträge.

**Offene Fragen aus dem Vergleich** (nicht dringend, aber vor dem ersten echten Lauf zu klären):
- **Haushaltskasse** hat Soll 1.402, wurde aber **nie gestellt** — Absicht (laufende Ausgaben statt
  Rücklage) oder Lücke?
- **Füchschen** hat **Soll 0**, obwohl OGS + Essensgeld monatlich rund 475 € fest laufen — soll das
  Nebenbuch ein Soll bekommen, oder laufen Kinderkosten bewusst ohne Rücklage?
- Nebenkosten/Urlaub: waren die Abweichungen Absicht (Sonderzahlung) oder Handkorrekturen?

## Die „Position Rücklage" — **brauchen wir nicht** (Jörgs eigene Erkenntnis)

> Jörg: *„Auf der Position Rücklage, das ist im Prinzip — **oder nehmen wir die raus, die Position
> Rücklage?** Die wirkt pro Untertopf, und wenn es nicht auf einen Untertopf verteilbar ist, dann
> geht es in die Position Allgemein."*

**Genau. Kein eigener Topf „Rücklage".** Die Rücklage ist **kein Topf, sondern ein Vorgang**:
ein monatlicher Lauf, der Geld **auf die Untertöpfe** legt. Ein Zwischentopf „Rücklage" würde
dasselbe Geld nur doppelt darstellen.

## Wie der Lauf rechnet

Einmal im Monat, **von Jörg angestoßen** (nicht automatisch), je Nebenbuch:

```
1. Je bestätigtem Vertrag:   Untertopf += Vertragsrate        (virtuelle + Buchung)
2. Rest nach Allgemein:      Allgemein += Config-Soll(NB) − Σ(Vertragsraten)
3. 🛑 Deckelprüfung:         Σ(Vertragsraten) > Config-Soll(NB)?
                             -> WARNUNG, NICHTS wird gebucht, Jörg entscheidet
```

**Schritt 2 ist exakt die bereits geltende Regel** `Rest-Soll(Default) = Nebenbuch-Soll −
Σ(Unterkat-Soll)` — nur wird sie jetzt gebucht statt nur gerechnet. Und **Allgemein ist zugleich
der Ausgang** für alles Unkategorisierte („es gibt keinen Vertrag von der Einmalzahlung").

**Wirkung auf die Verträge:** Der zurückgelegte Saldo je Vertrag steigt monatlich um die Rate —
„jetzt gibt es wieder eine Zahlung für das Google-Abo" ist damit gedeckt. Kommt die echte Zahlung,
verzehrt der Spiegel den Topf wieder. **Beides zusammen ergibt eine ruhige Nulllinie**, statt dass
der Topf nur nach unten läuft.

| Eigenschaft | Wert |
|---|---|
| Buchungsart | `ruecklage`, **virtuell** (kein reales Geld — Jörg: „nicht im Sinne von realem Geld") |
| `quelle_import` | **neu: `rueckstellung`** — trennscharf von `fb-kto`/`spiegel`/`manuell` |
| Auslöser | **manuell, 1×/Monat** („bilde die Rücklagen für den nächsten Monat") |
| Idempotenz | **Pflicht** — zweimal im selben Monat drücken darf **nicht** doppelt buchen |
| Trockenlauf | Default, wie bei allen Workflows |
| Nachvollzieh­barkeit | Lauf wird in `admin_laeufe` protokolliert (#61) |

> ⚠️ **Achtung Historie — der erste echte Lauf darf frühestens 09/2026 buchen.**
> Der Juli kam aus `fb-kto`, und **der August ist bereits vorab gestellt** (Jörgs Urlaubs-Trick,
> gebucht am 31.07.). Ein Lauf für 08/2026 würde den August **doppelt** befüllen.
> **Pflicht:** Der Lauf prüft je Nebenbuch/Monat, ob **schon eine Einzahlung existiert** —
> egal aus welcher Quelle (`fb-kto`, `manuell`, `rueckstellung`) — und überspringt sie dann.

---

## Was ich von dir bräuchte

| Frage | | Antwort |
|---|---|---|
| **A** | Vertrag → eigene Unterkategorie (Name = Vertragsname), **bündelbar per Config**? | ✅ **ja** (2026-07-17) |
| **B** | ~~Verträge ohne eigene Unterkategorie?~~ | ❌ verworfen |
| **C** | Warnung bei Überschreitung **hart** (nichts wird geschrieben)? | ✅ **hart** (2026-07-17) |
| **D** | Neue Verträge immer erst bestätigen? | ✅ **ja — „Vertrag erst nach Bestätigung"** (2026-07-17) |
| **E** | **Position „Rücklage" als Topf** | ❌ **raus** — Rücklage ist ein Vorgang, kein Topf (2026-07-17) |
| **F** | **Wann neu rechnen?** | ✅ **entschieden — „Erkennen ≠ Ändern", s. u.** (2026-07-17) |
| **G** | Rücklagenlauf: fehlende Monate **nachholen**? | ✅ **JA, doch** — Jörg hat revidiert: *„Okay, dann machen wir es anders. Dann muss es rückwirkend gehen. Du hast recht."* (2026-07-17). Sonst fehlt die Rücklage dauerhaft. **Aber:** nur fehlende Monate, nie einen schon gestellten überschreiben (Idempotenz-Prüfung je Nebenbuch/Monat bleibt Pflicht) |

---

# Frage F entschieden: **Erkennen ≠ Ändern**

> Jörgs Frage: *„Wann soll diese Seite aufgebaut werden mit Verträgen, aus denen dann die
> Config-Werte bespeist werden, aus denen dann die Rückstellungen gebucht werden?
> On Demand bei jedem Import · zum Monats-Rolleinsatz · zum Rücklagenlauf?"*

Die Kette ist **Verträge → Config-Werte (Unterkat-Solls) → gebuchte Rückstellung**. Diese drei
Vorgänge laufen **unterschiedlich schnell** und dürfen deshalb nicht zusammenfallen:

| Vorgang | Wann | Schreibt |
|---|---|---|
| **1. Vertragserkennung** (Rhythmus/Betrag/beendet?) | **bei jedem Import**, automatisch mit | **nichts** — nur Vorschläge, Status `erkannt` |
| **2. Soll-Übernahme** (Vertragsraten → Unterkat-Soll) | **nur beim Rücklagenlauf**, Schritt 1, **mit Bestätigung** | Unterkat-Solls |
| **3. Rücklagenlauf** (Solls → virtuelle Buchungen) | **1×/Monat, Jörg drückt**, Schritt 2 | `ruecklage`-Buchungen |

### Warum die Solls **nicht** beim Import angefasst werden dürfen

Ein Import kommt **mitten im Monat und oft mehrmals**. Würden die Solls dabei springen, hätte der
laufende Monat plötzlich eine andere Basis als beim Rücklagenlauf — **die Zahlen würden unter Jörg
wackeln**. Genau das wäre der Verlust der Steuerungssicht, den er verhindern will.

> **Regel: Solls sind zwischen zwei Rücklagenläufen stabil.** Nur der Lauf ändert sie, und nur nach
> Bestätigung. **Der Import darf informieren, nicht verändern.**

### Der Rücklagenlauf = der monatliche Moment der Wahrheit

```
Schritt 1:  "Diese Verträge sind neu / geändert / beendet.  Soll übernehmen?"  -> Jörg entscheidet
Schritt 2:  Deckelprüfung gegen das Config-Nebenbuch-Soll
            -> passt?          dann buchen                                      -> Jörg drückt
            -> Überschreitung? 🛑 WARNUNG, es wird nichts gebucht
```

**„Monats-Rolleinsatz" und „Rücklagenlauf" sind dasselbe Ereignis** — nicht trennen. Sonst passieren
zwei Dinge im selben Zeitraum, und bei einer Abweichung ist nicht mehr erkennbar, welches sie
verursacht hat.

**Zusätzlich:** ein **On-Demand-Knopf** „Verträge jetzt neu erkennen" — reiner Komfort, kein
Pflichtweg, ändert ebenfalls keine Solls.

### G revidiert: **doch rückwirkend** — aber nie doppelt

> Jörg zuerst: *„Nein, nicht rückwirkend. Auf keinen Fall."* → nach dem Hinweis, dass die Rücklage
> dann **dauerhaft fehlt**: *„Okay, dann machen wir es anders. **Dann muss es rückwirkend gehen.
> Du hast recht.**"*

**Der Lauf holt fehlende Monate nach.** Regeln dazu:

- Er bucht **je Nebenbuch/Monat genau einmal** — die Idempotenz-Prüfung bleibt Pflicht und schützt
  auch Jörgs vorab gestellten August (`fb-kto`, 31.07.).
- Er **überschreibt nie** einen bereits gestellten Monat, egal aus welcher Quelle.
- Er zeigt vorher **welche Monate er nachholen würde** — Trockenlauf, dann Jörgs OK.
- Anzeige bleibt: *„Letzter Lauf: September 2026 · seitdem 2 Monate offen"*

---

# 🔀 Schiefstellung: Fluss ≠ Bestand (Jörgs Ergänzung 2026-07-17)

> *„Es gibt ja wirklich den Fall, dass wir auch **per Config schon Schiefstellung erlauben** wollen.
> Heißt, wir sehen, wir haben laufende Posten, die ein **negatives Monats-Soll** erwirken, und
> **akzeptieren das aber**. Das muss schon gehen. Füchschen sind das beste Beispiel: Da haben wir
> über die Jahre virtuell **15.000 €** Rücklagen aufgebaut … **das kann gerne abgeknabbert werden**.
> Bei TK sind es knapp 1.500 — da wäre es erlaubt, wenn wir auf Sicht ein negatives Saldo mit dem
> Monat einfahren, weil es ja noch **Spielraum** gibt."*

**Das deckt eine Lücke im Deckel-Konzept:** Der Deckel prüft den **Monatsfluss** (Σ Vertragsraten
gegen Config-Soll). **Bestand** ist etwas anderes — und bei manchen Nebenbüchern ist die
Unterdeckung **gewollt**:

| Nebenbuch | Config-Soll | laufende Verträge | Bestand | gewollt? |
|---|---|---|---|---|
| **Füchschen** | **0** | OGS + Essensgeld ≈ **475/Monat** | **~15.000** | ✅ **ja — soll abschmelzen.** Kindergeld zahlt ein, die Posten zahlen aus |
| **TK** | 125 | Beiträge + Apotheke | ~1.500 | ✅ ja — Spielraum vorhanden |
| Auto, Vers, … | gesetzt | ≈ Soll | normal | ❌ hier wäre Unterdeckung ein Fehler |

Ohne Schalter würde die harte Warnung bei Füchschen **jeden Monat blockieren**, obwohl alles
richtig ist.

### Lösung: ein Schalter je Nebenbuch

```sql
ALTER TABLE kategorien ADD COLUMN schiefstellung_erlaubt BOOLEAN NOT NULL DEFAULT FALSE;
```

| `schiefstellung_erlaubt` | Verhalten bei Σ(Raten) > Config-Soll |
|---|---|
| **FALSE** *(Default)* | 🛑 **harte Warnung, nichts wird gebucht** — Jörg entscheidet (wie vereinbart) |
| **TRUE** *(Füchschen, TK)* | ✅ **Lauf bucht**, zeigt aber die **Unterdeckung + Reichweite** an |

**Und die wirklich nützliche Zahl dabei — die Reichweite:**

```
Unterdeckung/Monat = Σ(Vertragsraten) − Config-Soll
Reichweite         = Bestand ÷ Unterdeckung
```

> Beispiel Füchschen: *„Unterdeckung 475 €/Monat · Bestand 15.000 € · **reicht noch ~31 Monate**"*

Damit ist die Schiefstellung **kein blinder Fleck, sondern eine gesteuerte Ansage** — Jörg sieht,
wie lange der Puffer trägt, statt nur „passt/passt nicht". Genau die Steuerungssicht, die er will.
