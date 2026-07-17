# Arbeitsliste: Empfängerspezifische Unterkategorien

> **Für dich zum Durcharbeiten.** Trag in **`OK?`** ein `x` (so machen) · `-` (nein) · `?` (reden wir drüber),
> und schreib in **`Bemerkung`** was du willst. Ich baue daraus direkt die Mapping-Regeln.
> Du musst nicht alles ausfüllen — leer heißt „Vorschlag passt".
>
> **Stand 2026-07-17.** Anders als frühere Vorschläge ist das hier **nicht geraten**: Alle Empfänger
> unten sind die **echten Empfänger aus der Live-DB**, mit Anzahl Buchungen (`n`) seit 01/2025.
> Personennamen sind bewusst weggelassen (Datenschutz — die Datei liegt in Git), Firmen stehen drin.

---

## Dein Prinzip (aus deinen eigenen Worten)

> „Es wird Empfänger geben, die man lieber bündelt, aber auch Empfänger, wo das statthaft ist,
> die einzeln zu sehen."

| | **Bündeln** (ein Topf) | **Einzeln** (eigene Unterkategorie) |
|---|---|---|
| **Wann** | Empfänger sind austauschbar, Alltag, nur die Summe zählt | eigene Verpflichtung/Vertrag, einer Person zuordenbar, Verlauf wichtig |
| **Dein Beispiel** | „ob das jetzt EDEKA, Aldi oder Lidl ist" → ein Untertopf | „Fitnessstudio, ob das bei der Natalie, Mainz oder von den Kindern ist" → verschiedene |
| **Dein Beispiel 2** | „Essensgeld für Kita und Essensgeld für Schule ist eine Unterkategorie" | „die OGS-Gebühren ist eine andere" |

Kurz: **Vertrag / Person / Verlauf → einzeln. Austauschbar / Alltag / Summe → bündeln.**

---

## 1. Sport — hier wolltest du **einzeln**

Aktuell liegt alles in nur zwei Töpfen. Dein Wunsch („kann ruhig jeder Empfänger eine
Unterkategorie sein, dann sieht man's deutlicher") ist hier direkt umsetzbar:

**Jörgs Zuordnung (2026-07-17), mit den Daten abgeglichen — passt lückenlos:**

| Empfänger (echt) | Betrag/Rhythmus lt. DB | **Unterkategorie neu** | für wen | OK? | Bemerkung |
|---|---|---|---|:--:|---|
| 1. Godesberger Judo Club e.V. | Beitrag regelmäßig + Extras (Prüfungen/Lehrgänge?) | **Judo** | Kinder | | |
| Sportverein Wachtberg 1922 e.V. | 2× | **SV Wachtberg** | Kinder | | |
| Meckenheimer Sportverein e.V. | seit 03/2026 | **Tanzverein** | Kind (mittleres) | | |
| *(Kampfsportverein)* | monatlich, wechselnder Beitrag | **Kampfsport Natalie** | Natalie | | |
| *(Fitnessstudio, Einzelperson als Empfänger)* | **monatlich durchgehend seit 03/2025** | **Fitnessstudio Jörg** | du | | |
| *(Schwimmbad, Eintritte, spontan)* | — | **Sport sonstige** | alle | | |

> ✅ **Geklärt (Jörg, 2026-07-17):** „Es gibt nicht *den* Fitnessempfänger, es gibt verschiedene
> Sportvereine: Judoclub + SV Wachtberg für die Kinder · Tanzverein Meckenheim · Natalie
> Kampfsport · ich im Fitnessstudio. **Die kannst du gerne einzeln als Unterkategorie haben.**"
> → Alle fünf sind in den Daten eindeutig identifizierbar. **„Studio Mainz" war ein Verhörer**
> der Spracheingabe (vermutlich „Natalie, **meins** oder von den Kindern").
> ⚠️ Beim Judo-Club gibt es neben dem regelmäßigen Beitrag **viele unregelmäßige Einzelbeträge**
> (Gürtelprüfungen? Lehrgänge? Turniere?) — für die Rückstellung zählt nur der **regelmäßige**
> Teil, der Rest ist unplanbar. Genau das muss die Automatik unterscheiden können (s. Abschnitt 8).

---

## 2. Kinder (Füchschen) — Essen vs. Betreuung: **geklärt** ✅

Dein Wunsch: „nicht alles zusammen nur auf Kinderkosten, sondern da gebündelt die Essenskosten und
die Betreuungskosten". **Der Verwendungszweck löst das eindeutig auf** — deine Beträge haben
gepasst, nur beim Träger hattest du dich vertan:

| Empfänger (echt) | Zweck lt. DB | Rhythmus | **Unterkategorie neu** | OK? | Bemerkung |
|---|---|---|---|:--:|---|
| **Gemeinde Wachtberg** *(Kassenzeichen A)* | „ELTERNBEITRAEGE **OGS** BERKUM" | monatlich, 08/25 erhöht | **Betreuung OGS (Kind 1)** | | |
| **Gemeinde Wachtberg** *(Kassenzeichen B)* | „ELTERNBEITRAEGE **OGS** BERKUM" | monatlich, 08/25 erhöht | **Betreuung OGS (Kind 2)** | | |
| **Katholische Jugendagentur Bonn** | „OGS-…" | **2× im Monat** (2 Kinder) | **Essensgeld (Schule)** | | |
| **KJF gGmbH** | „**Essensgeld** \<jüngstes Kind\>" | monatlich | **Essensgeld (Kita)** | | |
| Rhein-Sieg-Kreis Kreiskasse | „Elternbeitrag KiGa…" | monatlich **bis 08/2025** | **Kita-Beitrag** *(ausgelaufen)* | | |
| Kath. Jugendagentur / KJA Bonn | „…Oster-/Sommerferien" | 2–3× im Jahr | **Ferienbetreuung** | | |
| Grundschule Berkum | „\<Kind\>, 4a" | einmalig | **Schule sonstiges** | | |
| je Kind (3 Daueraufträge) | — | monatlich | **Taschengeld je Kind** | | |
| Kindergeld (Zufluss) | — | monatlich | *bleibt* | | |

> ✅ **Korrektur zu deiner Annahme:** Du sagtest *„Essensgeld ist bei der Gemeinde"* — **ist es
> nicht.** Die Gemeinde macht die **OGS-Betreuung** (zwei Kassenzeichen = zwei Kinder, Beträge
> exakt in deiner Größenordnung „200 oder 100 € plus, jeweils"). Das **Essensgeld** läuft über die
> **Katholische Jugendagentur** (2× im Monat = deine „Zweitzahlung für die beiden Großen")
> und die **KJF** (Zweck sagt wörtlich „Essensgeld" = dein „KJ irgendwas, 50–60 €").
> Deine Beträge stimmten alle — nur der Träger war ein anderer.
>
> ⚠️ **Wichtig für die Automatik:** Bei **Gemeinde Wachtberg** hängen an EINEM Empfänger **vier
> völlig verschiedene Zwecke**: OGS-Beiträge (Kinder) · **Grundsteuer/Straßenreinigung** ·
> **Schmutz-/Niederschlagswassergebühr** (beide Nebenkosten, liegen dort auch richtig) · eine
> Pachtzahlung. **Der Empfängername reicht als Anker nicht** — die Regel muss auf den
> **Verwendungszweck** (bzw. das Kassenzeichen) gehen. Gleiches Muster wie bei PayPal.
> ❓ **Taschengeld je Kind einzeln** (3 Töpfe) oder ein Topf? Nach deiner Regel (Person
> zuordenbar) wäre einzeln richtig.
> ❓ **Grundsteuer** liegt unter Nebenkosten → *Ver-/Entsorgung*. Eigener Topf „Grundsteuer"?

---

## 3. Lebensmittel & Alltag — hier wolltest du **bündeln**

Dein Beispiel: „ob das jetzt EDEKA, Aldi oder Lidl ist, würd ich auf einen Untertopf machen."
Das ist heute schon so und passt. **Aber zwei Dinge stimmen nicht:**

| Empfänger (echt) | n | heute | **Vorschlag neu** | Modus | OK? | Bemerkung |
|---|---|---|---|---|:--:|---|
| Lidl, ALDI SÜD, EDEKA, REWE | 77/58/45/42/10 | Lebensmittel | *bleibt* **Lebensmittel** | Bündeln | | |
| Gilgens, Schäfer, Kamps, Merzenich (Bäcker) | 40/11/7/5 | Lebensmittel | **Bäcker** *(eigener Topf?)* | Bündeln | | |
| dm-drogerie | 176 | Drogerie | *bleibt* **Drogerie** | Bündeln | | |
| 🐞 **Müller** (VISA-Kartenzahlung im Laden) | **50** | ❌ *Nebenkosten → Ver-/Entsorgung* | **Drogerie** (zu dm) | Bündeln | | |
| AMAZON PAYMENTS / AMAZON EU / AMZN Mktp | 354/97/6 | Amazon/Konsum | *bleibt* (s. Frage unten) | Bündeln | | |
| ❓ **PayPal** (Empfänger verdeckt!) | **115** | PayPal (unklar) | *s. Abschnitt 6* | — | | |

> 🐞 **Das ist ein echter Fehler:** „Müller" (50 Buchungen) hängt unter **Nebenkosten/Ver-/Entsorgung**.
> Der Verwendungszweck ist aber jedes Mal *„VISA Debitkartenumsatz"* — das ist die **Drogerie Müller**,
> kein Entsorger (Müllgebühren zahlt man nicht mit der Karte im Laden). Das verfälscht deine
> Nebenkosten. **Soll ich das umbuchen?** → OK?-Spalte.
> ❓ **Bäcker**: eigener Topf oder in Lebensmittel mit rein? (n=63 zusammen, also durchaus sichtbar)

---

## 4. Versicherungen — dein „da stimmt was nicht" bestätigt sich

Du wolltest selbst nachschauen. Hier ist der **Ist-Stand aus der DB**, das spart dir das Suchen:

| Empfänger (echt) | n | heute | Auffällig? | OK? | Bemerkung |
|---|---|---|---|:--:|---|
| Zurich Dt. Herold Lebensversicherung | 19 | Vers → Leben/BU (RLV) | ok, monatlich | | |
| HUK-COBURG-LEBENSVERSICHERUNG | 2 | Vers → Leben/BU (RLV) | ok, jährlich | | |
| HUK24 AG | 4 | Vers → Haftpflicht | ok | | |
| ADAC Autoversicherung AG *(2 Schreibweisen)* | 5 | Vers → KFZ-Versicherung | Dublette zusammenführen | | |
| ARAG SE | **1** | Vers → Rechtsschutz | nur 1× (10/2025) — jährlich, 2026 offen? | | |
| Provinzial Versicherung AG | **1** | Vers → Gebäude | nur 1× (09/2025) — jährlich, 2026 offen? | | |
| ✅ HanseMerkur — **Brillenversicherung** | 5 | Vers → *Sonstige Versicherung* | **Vorschlag: eigener Topf „Brillen/Sehhilfe"** | | |
| Envivas *Krankenzusatz* | 19 | **TK** → Krankenkasse | bleibt (s. u.) | | |
| ❌ **Hausrat** | **0** | — | **fehlt komplett** | | |

> ✅ **Korrektur (Jörg, 2026-07-17):** *„HanseMerkur ist keine Krankenzusatzversicherung, das ist
> die **Brillenversicherung**."* — Damit ist **mein vorheriger Befund hinfällig.** Ich hatte
> behauptet, du hättest „zwei gleichartige Krankenzusatz-Versicherungen in zwei Kategorien".
> Stimmt nicht: Envivas = Krankenzusatz (gehört zu **TK**), HanseMerkur = Brillen. **Kein
> Widerspruch, keine Umbuchung nötig.** Der Firmenname („HanseMerkur *Speziale
> Krankenversicherung* AG") hatte mich in die Irre geführt — genau deshalb diese Liste.
> ❓ **Was bleibt:** Sie liegt in *Sonstige Versicherung*. Nach deiner Regel (je Police = eigene
> Unterkategorie) wäre **„Brillen/Sehhilfe"** sauberer. Und: gehört sie fachlich eher zu
> **TK/Gesundheit** als zu *Vers*? Deine Entscheidung.
> ❓ **Hausrat fehlt** — hast du keine, oder läuft sie über einen Empfänger, den ich nicht als
> Versicherung erkenne? (Bei Gebäudeversicherung + Haus wäre Hausrat üblich.)
> ❓ **Deine alte Frage: KFZ-Versicherung unter *Auto* oder unter *Vers*?** Heute: *Vers*.
> Für *Auto* spricht „alle Autokosten auf einen Blick", für *Vers* „alle Policen auf einen Blick".
> ⚠️ **Achtung Automatik:** *ADAC-Mitgliedschaft* (Auto) und *ADAC Autoversicherung* (Vers) sind
> **zwei verschiedene Sachen** — ein Muster `adac` würde beide fangen. Ich trenne sie sauber.

---

## 5. Verträge, die einzeln bleiben (nur bestätigen)

Hier ist heute schon alles einzeln und nach deiner Regel richtig — nur gegenlesen:

| Bereich | Empfänger (echt) | Vorschlag | OK? | Bemerkung |
|---|---|---|:--:|---|
| Mobilfunk/Internet | Telekom (18), Telefonica (18), 1&1 (12) | je Anbieter einzeln | | |
| Streaming/Software | Amazon Digital (44), Amazon Media (33), Audible (9), Adobe (9), YouTube (5), Anthropic (4), Microsoft, Google Play | **je Dienst einzeln** (kündbar!) | | |
| Rundfunk | WDR | einzeln | | |
| Strom | Naturwerke (25), **MAINGAU (9)**, Tibber (2) | **ein Topf „Strom"** — Anbieter wechseln ständig | | |
| Wasser | enewa (19) | einzeln *(geprüft: ist wirklich Wasser)* | | |
| Müll | RSAG (6), Gemeinde Wachtberg (21) | einzeln | | |
| Kredite | Deutsche Bank (67), KfW (2) | je Kredit einzeln | | |
| Krankenkasse | Envivas (19) | s. Abschnitt 4 | | |
| Apotheke | Forum Apotheke (53) + 5 weitere | **bündeln** (austauschbar) | | |
| Tanken | Shell (48), Aral, Agip, ED | **bündeln** (austauschbar) | | |
| Auto | ADAC-Mitgliedschaft (2), Autohaus Meures (2) | einzeln | | |

---

## 6. PayPal — **gelöst, entgegen der ersten Einschätzung** ✅

> **Jörg (2026-07-17):** „PayPal und Amazon werden Problem sein … das werd ich wahrscheinlich immer
> manuell machen müssen, weil da kann alles Mögliche dahinter sein. **Details siehst Du ja nicht.**"
>
> **Nachgeprüft — bei PayPal stimmt das zum Glück nicht.** Der Händler steht **im Verwendungszweck**,
> in einem festen Format:
> `1050392172454/PP.4645.PP/. EasyPark GmbH, Ihr Einkauf bei EasyPark GmbH`
>
> **Testlauf über alle 220 PayPal-Buchungen: 217 automatisch aufgelöst = 98 %.**
> Dahinter stecken nur **66 verschiedene Händler** — also ~66 Regeln statt 220× manuell klicken,
> und sie greifen **dauerhaft auch bei jedem künftigen Import**.

**Die echten Händler hinter PayPal:**

| Händler | n | → Kategorie/Unterkategorie | OK? | Bemerkung |
|---|---|---|:--:|---|
| **EasyPark GmbH** | **54** | Auto → **Parken** *(heute schon richtig!)* | | |
| Google Payment Ireland *(2 Schreibweisen)* | 46 | ❓ **Telefon → Streaming & Software?** | | |
| SPIEGEL-Verlag | 13 | Telefon → **Presse** *(neuer Topf?)* | | |
| Adobe Systems Software Ireland | 11 | Telefon → Streaming & Software | | |
| Verlag Der Tagesspiegel | 8 | Telefon → **Presse** | | |
| General-Anzeiger Bonn | 2 | Telefon → **Presse** | | |
| DB Vertrieb GmbH | 4 | ❓ **Bahn/Reise — wohin?** | | |
| Verifone Payments | 5 | ❓ unklar (Zahlungsdienstleister) | | |
| Tchibo, eBay, AliExpress, Coolblue, Tractive, Distriphot, RE-INvent, Sellhelp, Kompf, Aura Home, TRADEINN, Muller Online | je 1–3 | Haushaltskasse → **Konsum/Onlinekauf** | | |
| OpenAI Ireland | 2 | Telefon → Streaming & Software | | |
| Sportograf | 2 | Sport? | | |
| ADAC Autoversicherung | 2 | Vers → KFZ-Versicherung | | |
| *3 Buchungen* | 3 | nicht auflösbar (u. a. „ADD TO BALANCE" = PayPal-Aufladung) | | |

> ✅ **Mein Fehlalarm zurückgenommen:** Ich hatte vermutet, die 54 PayPal-Buchungen unter
> *Auto/Parken* seien eine Fehlregel. **Sind sie nicht** — das ist **EasyPark**, die Park-App.
> Die Zuordnung ist korrekt und bleibt.
> ❓ **Google Payment (46×)** ist der größte Brocken: Play-Store-Käufe/Abos. Sollen die alle in
> einen Topf („Google/Apps"), oder störts dich, dass da Verschiedenes drinsteckt?
> ❓ **Presse** (Spiegel + Tagesspiegel + General-Anzeiger = 23×) — eigener Topf oder zu den Abos?

---

## 6b. Amazon — **hier hast du recht: bleibt manuell** ⚠️

Bei Amazon steht **kein Händler und kein Artikel** im Verwendungszweck, nur die Bestellnummer:

```
302-1391286-9493130 AMZN Mktp DE 324IZX6BHJC04RES
Sonstige Ausgaben / Sonstige Ausgaben
```

Bei **457 Amazon-Buchungen** (Payments 354 + EU 97 + Mktp 6) ist das viel. Deine Einschätzung
stimmt: aus der Bankbuchung allein ist nicht erkennbar, ob das Klopapier, ein Buch oder ein
Werkzeug war.

**Aber es gibt einen Ausweg — die Bestellnummer ist ein Schlüssel:**

| Möglichkeit | Was das heißt | OK? | Bemerkung |
|---|---|:--:|---|
| **A** — Amazon-Bestellexport nutzen | Amazon liefert eine CSV mit **Bestellnummer + Artikelname**. Über die Bestellnummer (steht ja in der Buchung!) ließe sich der Artikel automatisch dranhängen → Kategorie wird ableitbar. **Setzt voraus, dass du den Export ziehst.** | | |
| **B** — Bemerkungsfeld manuell | Du schreibst bei Bedarf selbst dazu, was es war (Feld existiert schon) | | |
| **C** — Sammeltopf „Amazon/Konsum" lassen | wie heute | | |

> 💡 **A ist realistisch** — der Amazon-Umsatzexport steht ohnehin auf der Liste (der alte
> `.xls`-Parser soll auf CSV umgestellt werden). Wenn du den Export einmal ziehst, kann ich testen,
> ob die Bestellnummern zusammenpassen. **Willst du das?**

---

> ✅ **Bestätigt (Jörg, 2026-07-17):** *„MAINGAU war ein Stromanbieter gewesen in der Historie."*
> → gehört korrekt in den Strom-Topf, ist nur nicht mehr aktuell (letzte Buchung 05/2025).
> Für den **Soll-Wert** zählt nur der laufende Anbieter — die alten sind reine Historie.
> ✅ **Ebenfalls geprüft:** `enewa` ist **kein** Stromanbieter, sondern **Wasser** (im
> Verwendungszweck steht wörtlich „Wasser 25.00 EUR") → Zuordnung stimmt.

---

## 7. Was mir sonst aufgefallen ist (nur zur Info)

- **103 Empfänger ohne Kategorie** — das ist der große Rest, den wir noch nicht zugeordnet haben.
  Viele davon sind Zahlungen zwischen euren eigenen Konten (dein Name in ~8 Schreibweisen).
- **Schreibweisen-Dubletten** überall: `ALDI.SUeD` vs `ALDI.SUED`, `PayPal Europe S.a.r.l.` vs
  `PayPal (Europe) S.a r.l.`, `KJA Bonn gGmbH` vs `KJA Bonn GmbH`. Meine Regeln fangen das ab.
- Kategorie **„Einnahmen"** hat noch 3 Buchungen, obwohl der Einnahmen-Block laut deiner
  Entscheidung entfallen ist. Schaue ich mir an, wenn du willst.

---

---

# 8. Der eigentliche Punkt: Rückstellungen automatisch bilden

> **Jörg, 2026-07-17 — bestätigt:** „**Insgesamt ist nicht das Ziel, alle Empfänger eine
> Unterkategorie zu geben, sondern die sinnvoll zu bündeln.**"
>
> ✅ **Bestätigt.** Die Faustregel oben gilt, nicht „einzeln um jeden Preis". Sport wird einzeln,
> **weil** es vier verschiedene Verpflichtungen für vier verschiedene Personen sind (Vertrag +
> Person + Verlauf → einzeln). Lebensmittel bleiben **ein** Topf. Unterkategorien sind kein
> Selbstzweck — sie müssen die Rückstellung tragen können.

## Was du willst

> „Wichtig wird es, wenn wir viele Unterkategorien haben, dass wir sauber die **Rückstellung
> automatisiert** belegen. Die Idee ist, dass man für den Betrachtungszeitraum **regelmäßige
> Buchungen — monatlich, quartalsweise, jährlich** — so viel Rückstellung bildet, dass sie dann
> wieder **verzehrt** werden von den erwarteten Ausgaben."
>
> „Das hattest du mal gerechnet, indem du **die historischen Werte einfach aussortierst. Das finde
> ich blödsinnig.** Das kann ich aber auch nicht alles manuell machen."

**Die Kritik trifft zu.** Bisher steckte in den Vorschlägen zweimal Handarbeit drin, die nicht
skaliert: die alten Studios wurden „aussortiert, kommen ja nicht mehr vor", und Wechselmonate mit
Mini-Beträgen wurden als Ausreißer weggelassen. Bei 5 Töpfen geht das. Bei 40 nicht mehr.

## Was stattdessen funktioniert: **Vertragserkennung statt Aussortieren**

Nichts wird aussortiert — der **Rhythmus wird gemessen**. Aus Datum + Betrag je Empfänger/Zweck:

| Schritt | Wie | Beleg (heute schon getestet) |
|---|---|---|
| **1. Rhythmus erkennen** | Abstände zwischen den Buchungen messen | funktioniert bereits: OGS-Beiträge → `MONATLICH`, Grundsteuer → `~alle 122 Tage` = **quartalsweise**, Versicherungen → `JÄHRLICH` |
| **2. Betrag bestimmen** | **Median** der letzten Zahlungen, nicht Mittelwert | Median ist gegen Ausreißer immun → **Wechselmonate müssen nicht mehr aussortiert werden**, sie fallen von selbst raus |
| **3. Läuft der Vertrag noch?** | letzte Buchung älter als **2 Rhythmen** → beendet | die alten Studios verschwinden **automatisch**, ohne dass jemand sie „aussortiert". Neue Verträge tauchen von selbst auf |
| **4. Rückstellung** | `Monatsrate = Jahresbetrag ÷ 12` · `Ziel-Bestand = Rate × Monate bis zur nächsten Fälligkeit` | monatlich Gezahltes braucht fast keinen Topf, Jährliches muss angespart werden |
| **5. Verzehr** | bei Fälligkeit wird der Topf durch die Ausgabe geleert | Mechanik existiert schon (Gegenbuchung/Spiegel) |
| **6. Unregelmäßiges** | erkennt sich selbst: kein Rhythmus → **keine** Rückstellung | z. B. Judo-Extras, Arztrechnungen — die gehören in einen Puffer, nicht in einen Vertragstopf |

**Der Kern:** Schritt 3 ersetzt das manuelle Aussortieren. Ein Vertrag ist „tot", wenn seit zwei
Rhythmen nichts kam — das ist eine Regel, kein Handgriff. Und Schritt 2 (Median) erledigt die
Ausreißer, ohne dass jemand entscheidet, was ein Ausreißer ist.

## Was Finanzguru macht (angesehen, 2026-07-17)

Finanzgurus Kernfeature ist genau **Schritt 1–3**: Die App durchsucht die Kontoumsätze, erkennt
wiederkehrende Zahlungen automatisch als „Verträge" (Abos, Versicherungen, Mobilfunk, Fitness),
zeigt je Vertrag den Betrag, **die nächste Abbuchung** und die Kündigungsfrist. Korrigiert man eine
Kategorie, lernt sie dazu. In der Plus-Version (2,99 €/Monat) prognostiziert sie daraus den
**Kontostand** der nächsten Wochen.

**Was wir übernehmen sollten:** die Vertragserkennung als eigenes Objekt — nicht nur „Buchung hat
Kategorie", sondern „**hinter diesen Buchungen steckt ein Vertrag mit Rhythmus X und Betrag Y, die
nächste Fälligkeit ist am Z**". Genau das fehlt heute.

**Wo dein Ansatz weiter geht:** Finanzguru **prognostiziert** nur den Kontostand — es **bildet keine
Rückstellungen**. Deine Fuchsbaukasse legt das Geld je Topf tatsächlich zurück und verzehrt es bei
Fälligkeit. Das ist der Schritt, den die App nicht macht. Die Erkennung klauen wir, die
Topf-Mechanik hast du schon.

| | OK? | Bemerkung |
|---|:--:|---|
| **Vertragserkennung so bauen** (Rhythmus messen, Median, „tot nach 2 Rhythmen") | | |
| Erkannte Verträge zeigst du dir an und **bestätigst/korrigierst** sie einmal | | |
| Daraus **automatisch** die Soll-Werte je Untertopf | | |

> ❓ **Eine Rückfrage, damit ich dich nicht falsch verstehe:** Mit „die historischen Werte
> aussortieren ist blödsinnig" meinst du — das **manuelle Wegwerfen alter/untypischer Zahlungen**
> (alte Studios, Wechselmonate), weil das bei vielen Töpfen nicht mehr geht? Dann ist der Weg oben
> die Antwort. **Oder** meinst du etwas anderes: dass alte Werte **mitzählen** sollen, statt
> ignoriert zu werden?

---

## Wenn du durch bist

Sag einfach „fertig" — ich lese die Datei, baue die Mapping-Regeln und rechne vorher aus, wie viele
Buchungen sich verschieben würden. **Nichts wird geschrieben, bevor du den Trockenlauf gesehen hast.**

**Reihenfolge, die ich vorschlage:**
1. **Regeln auf den Verwendungszweck** statt nur auf den Empfänger (PayPal, Gemeinde Wachtberg) —
   ohne das greift bei den größten Brocken gar nichts.
2. Die Unterkategorien aus dieser Liste anlegen + Historie nachziehen (Trockenlauf zuerst).
3. **Dann** die Vertragserkennung (Abschnitt 8) — sie braucht die sauberen Unterkategorien als Basis.
