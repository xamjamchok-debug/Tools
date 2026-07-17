# Design: Verträge & automatische Rückstellung

> **Stand 2026-07-17 · Entwurf zur Entscheidung.** Basiert auf Jörgs Vorgaben vom selben Tag.
> Kein Code gebaut — erst wenn du zustimmst.

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

## Was ich von dir bräuchte

| Frage | | Antwort |
|---|---|---|
| **A** | Vertrag → eigene Unterkategorie (Name = Vertragsname), **bündelbar per Config**? *(meine Empfehlung)* | |
| **B** | Oder Verträge ohne eigene Unterkategorie, direkt in bestehende einsortiert? | |
| **C** | Warnung bei Überschreitung: **hart** (Automatik schreibt nichts, du musst entscheiden) — oder **weich** (schreibt, warnt nur)? *(Empfehlung: hart)* | |
| **D** | Neue Verträge: **immer erst bestätigen** — oder automatisch übernehmen, wenn sie unter den Deckel passen? | |
