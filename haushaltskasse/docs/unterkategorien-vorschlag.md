# Vorschlag: bessere Unterkategorien + Mapping (Umsatz → Nebenbuch / Unterkategorie)

> **STATUS (2026-07-15): Vom User angenommen — Umsetzung LÄUFT.** Backlog **#46**.
> Klärungen des Users eingearbeitet (s. Abschnitt „Geklärt" unten).
> Soll-Werte je Unterkategorie werden **datenbasiert** hergeleitet (Rhythmus + Fälligkeit aus
> der Zahlungshistorie), nicht prozentual geschätzt — Methode s. `untertopf-verteilung-vorschlag.md`.

> Ziel: sprechende Unterkategorien statt der übernommenen Kürzel (`S-Auto`, `R-NK`, `S-Füchschen` …).
> Quelle: die alten Excel-„Kto-"Blätter (Spalte „Was") + Konten-Blatt-Zuordnung. Basis-Stand 2026-07.
> Keine €-Beträge hier (Datenschutz) — nur Struktur + Erkennungsmuster.

## Prinzip
- **Nebenbuch (Kategorie)** = der Rücklagen-Topf (Auto, Versicherung, …). Bleibt.
- **Unterkategorie** = *wofür* das Geld innerhalb des Topfs — **sprechender Klarname**, keine Präfixe.
- Die Präfixe **H-/R-/S-** waren ein Makro-Behelf (Haben/Rückstellung/Soll) → **fallen weg.**
- Erkennung läuft über Empfänger/Verwendungszweck (die „Muster"-Spalte unten) und wird zu
  lernenden `mapping_regeln`.

---

## Neue Unterkategorien je Nebenbuch

| Nebenbuch | Unterkategorien (neu, sprechend) | ersetzt u. a. |
|---|---|---|
| **Auto** | Tanken · **Parken** · KFZ-Steuer · Reparatur & Werkstatt · Finanzierung/Leasing · Zweirad · Mietwagen · Anschaffung | S-Auto, R-Auto, H-Auto |
| **Versicherung** | KFZ-Versicherung · Haftpflicht · Hausrat · Rechtsschutz · Leben/BU (RLV) · Gebäude | S-Vers, Haftpflicht |
| **Nebenkosten** | Wasser/Abwasser · Strom · Grundsteuer · Müll · Schornsteinfeger | S-NK, Abwasser |
| **Sport** | Fitnessstudio · Verein/Mitgliedschaft · Kurse & Training · Ausrüstung | S-Sport, R-Sport |
| **Urlaub** | **je Reise eine Unterkategorie** (neutral benannt: „Reiseziel Jahr", z. B. „Portugal 2026") · **Urlaub allgemein** (neutraler Anspartopf, solange keine Reise feststeht) | S-Urlaub, Bar |
| **Füchschen (= die Kinder)** | Betreuung (OGS/Kita) · Kindergarten · Schulbedarf · Ausstattung & Anschaffung · Freizeit · **Sparen/Taschengeld** · **Kindergeld (Einnahme)** | S-Füchschen, Kiga etc · Kategorie „Kinder" entfällt |
| **Telefon/Medien** | Mobilfunk & Internet · Streaming & Software · Rundfunkbeitrag · Zeitung/Medien · sonstige Abos | Abo, S-Tel |
| **Instandhaltung** | Handwerker · PV/Solar · Möbel & Einrichtung · Baumaterial · **Garten & Außenanlage** · sonstige Anschaffung | S-Inst, H-Inst, Garten (aus NK) |
| **Krankenkasse/Gesundheit (TK)** | Private KV (DKV) · Krankenkasse (TK) · Apotheke · Arzt & Zahnarzt | S-TK, tk |
| **Kredit** | Immobilienkredit (Deutsche Bank) · KfW-Darlehen · Sondertilgung/Zinsen | S-Kredit, deuba |
| **Haushaltskasse** | Lebensmittel · Drogerie · Bäcker · Auswärts essen · Amazon/Konsum · Bargeld | Konsum, Edeka/Aldi, S-… |

---

## Mapping-Tabelle: Empfänger/Muster → Nebenbuch / Unterkategorie

*(die wichtigsten wiederkehrenden Umsätze; der Rest wird über die Lernregeln + KI-Vorschlag ergänzt)*

| Erkennung (Empfänger / Verwendungszweck enthält) | Nebenbuch | Unterkategorie |
|---|---|---|
| Shell, Aral, Agip, bft, Esso, „Tankstelle" | Auto | Tanken |
| „Parkhaus", „Parken", APCOA, Contipark, Q-Park, „Parkgebühr", „Parkschein", PaybyPhone, EasyPark | Auto | **Parken** |
| Bundeskasse … KFZ, „KFZ-Steuer" | Auto | KFZ-Steuer |
| Copart, „kupplung", „Werkstatt", „Reparatur", „Schlüssel", Stellantis | Auto | Reparatur & Werkstatt |
| Autokredit, „an Kredit PV", Leasing, PSA/Peugeot Bank | Auto | Finanzierung/Leasing |
| „Roller", „Rad" | Auto | Zweirad |
| „Mietwagen", Sixt, Europcar | Auto | Mietwagen |
| ADAC Autovers, HUK, HUK24, „AutoVers" | Versicherung | KFZ-Versicherung |
| „Haftpflicht", ARAG (Privat) | Versicherung | Haftpflicht |
| „Hausrat" | Versicherung | Hausrat |
| ARAG (Rechtsschutz) | Versicherung | Rechtsschutz |
| Zurich Deutscher Herold, HUK-Coburg Leben, „RLV", „BU" | Versicherung | Leben/BU (RLV) |
| Provinzial, „Gebäude" | Versicherung | Gebäude |
| Gemeinde Wachtberg (Schmutz-/Abwasser), enewa, Naturwerke, „Trinkwasser" | Nebenkosten | Wasser/Abwasser |
| Vattenfall, „Strom", Stadtwerke Strom | Nebenkosten | Strom |
| Gemeinde Wachtberg „Grundsteuer", „Kassenzeichen … Grundsteuer" | Nebenkosten | Grundsteuer |
| „Müll", Abfallwirtschaft, Rhein-Sieg (Abfall) | Nebenkosten | Müll |
| „Schornsteinfeger" | Nebenkosten | Schornsteinfeger |
| „Garten", „Holz", „Mauer", „Rollos", „Markise" | **Instandhaltung** | Garten & Außenanlage |
| FITPARK, HEALTHCITY, Powerplate, „Fitness", **fifi, Robbie** (beides Fitness-Studios) | Sport | Fitnessstudio |
| Godesberger Judo Club, SSF, „Jahresbeitrag", „Verein" | Sport | Verein/Mitgliedschaft |
| Frank … Habermann (Fitness Club Berkum), „Training", „Kurs" | Sport | Kurse & Training |
| Thai Airways, 2C2P, „Airways", „Flug", Lufthansa, Ryanair, „Hotel", Booking.com, „monte da quinta" | Urlaub | → **die Unterkategorie der jeweiligen Reise** (Zuordnung über Reisezeitraum/Ziel, nicht über die Ausgabenart) |
| Gemeinde Wachtberg „Elternbeiträge OGS", Katholische Jugendagentur, KJF | Füchschen | Betreuung (OGS/Kita) |
| „Kindergarten", „Kita" | Füchschen | Kindergarten |
| Rhein-Sieg-Kreis (Schule), „Schulbedarf" | Füchschen | Schulbedarf |
| Amazon (Kinderartikel), „Radanhänger", „Chariot", Bottosso | Füchschen | Ausstattung & Anschaffung |
| Familienkasse, „Kindergeld" | Füchschen | Kindergeld (**Einnahme**, +) |
| „Spar" an Kinderkonten (Taschengeld/Sparen) | Füchschen | Sparen/Taschengeld |
| Telekom, Telefonica, Vodafone, o2, 1&1, congstar | Telefon/Medien | Mobilfunk & Internet |
| Amazon Digital, Adobe, Office 365, Audible, Netflix, Spotify, Claude | Telefon/Medien | Streaming & Software |
| WDR, „Rundfunk", GEZ, Beitragsservice | Telefon/Medien | Rundfunkbeitrag |
| FAZ, Spiegel, Tagesspiegel, General-Anzeiger | Telefon/Medien | Zeitung/Medien |
| MI SolarEnergy, „PV", „Solar" | Instandhaltung | PV/Solar |
| Ilges, Fritzdorf, Schiffmann, „Handwerker", „Fenster" | Instandhaltung | Handwerker |
| IKEA, „Möbel" | Instandhaltung | Möbel & Einrichtung |
| DKV | TK | Private KV (DKV) |
| Techniker Krankenkasse, „TK Emma", „TK" | TK | Krankenkasse (TK) |
| Apotheke (Fortuna, Rheingold, easyApotheke, Forum) | TK | Apotheke |
| „Zahnarzt", „Ortho", „Hausarzt", Arztpraxis | TK | Arzt & Zahnarzt |
| Deutsche Bank, Postbank, „deuba", „pB kredit", „DB kredit" | Kredit | Immobilienkredit (Deutsche Bank) |
| KfW | Kredit | KfW-Darlehen |
| Edeka, Aldi, Lidl, Rewe, Kaufland, Penny, Netto | Haushaltskasse | Lebensmittel |
| dm, Müller (Drogerie) | Haushaltskasse | Drogerie |
| Bäcker, Stadtbrotbäcker, Schäfer, „Brot" | Haushaltskasse | Bäcker |
| Restaurant, SumUp, Café, Imbiss | Haushaltskasse | Auswärts essen |
| Amazon (Konsum), AMZN Mktp | Haushaltskasse | Amazon/Konsum |

## Geklärt (User, 2026-07-15)
- **Sport / „fifi" & „Robbie":** beides **Fitness-Studios** → Unterkategorie *Fitnessstudio*.
  **Die alten kommen nicht mehr vor** — also nur fürs Mapping der Historie relevant, sie brauchen
  **kein laufendes monatliches Soll**. Für die Rücklage zählt nur das aktuell laufende Studio.
- **Urlaub:** **pro Reise**, neutral benannt („Ziel Jahr"), plus einen neutralen Anspartopf
  *Urlaub allgemein*, solange keine konkrete Reise feststeht. Die Ausgabenart (Flug/Hotel/vor Ort)
  wird **nicht** mehr zur Unterkategorie — sie ist bei einer Reise ohnehin gemischt.
- **Garten & Instandhaltung bleiben zusammen:** „Garten/Holz/Mauer" wandert vom alten NK-Blatt
  nach **Instandhaltung** → Nebenkosten enthält nur noch die laufenden Versorger/Abgaben.

## Offen
- **Amazon** verteilt sich über viele Nebenbücher — hier hilft später die Bemerkung/KI je Bestellung.

---

# Nachtrag: Entscheidungsprinzip „Bündeln vs. Einzeln" (aus der Handy-Session 2026-07-17)

> **Herkunft:** Die Handy-Session (Branch `claude/subcategory-reserve-visibility-yvsqlx`) lief auf
> dem alten `master` und kannte diese Datei nicht — sie hat einen eigenen Vorschlag geschrieben.
> Der ist inhaltlich größtenteils von #50 überholt, **aber dieses Prinzip und die Fragen F1–F5
> existieren nur dort** und sind hier gerettet. Der Rest des Handy-Dokuments wurde verworfen.

## Die Faustregel

Bisher landete vieles pauschal in großen Töpfen. Die Leitfrage je Empfänger: **bekommt er eine
eigene Unterkategorie — oder wandert er in einen Sammeltopf?**

| Frage | Ja → **Einzeln** | Nein → **Bündeln** |
|---|---|---|
| Ist es eine **eigene Verpflichtung**, die man einzeln beobachten/kündigen will? | eigener Vertrag, Police, Mitgliedschaft | spontaner Alltagskauf |
| Ist es einer **bestimmten Person** zuordenbar (welches Kind, Natalie…)? | ja, Zuordnung ist relevant | egal, wer |
| Ist der Empfänger mit anderen im selben Zweck **austauschbar**? | nein, spezifisch | ja, beliebig ersetzbar |
| Will ich den **Verlauf je Empfänger** sehen? | ja | Summe reicht |
| Wie **häufig** und **gleichartig** sind die Buchungen? | selten/vertraglich | häufig/gleichartig |

> Kurz: **Verpflichtung / Person / Verlauf wichtig → einzeln.**
> **Austauschbar / Alltag / nur Summe zählt → bündeln.**

Beispiele aus Jörgs eigener Formulierung: Lebensmittel → **bündeln** (ob EDEKA, Aldi oder Lidl ist
egal). Fitnessstudios → **einzeln** (Natalie, Mainz und die Kinder sind verschiedene Verpflichtungen).
Kinder: **Essensgeld** (Kita + Schule zusammen) getrennt von **Betreuung** (OGS-/Kita-Gebühr) —
nicht alles pauschal auf „Kinderkosten".

## ✅ Sport/Fitness: von Jörg entschieden (2026-07-17) — **einzeln**

*(Vorher hier fälschlich als „offener Widerspruch F6" geführt — der war keiner. Jörgs Original-Input
vom 2026-07-17 enthält die Entscheidung wörtlich; sie kam nur über die Handy-Übergabe verstümmelt an.)*

> „Ich will die Unterkategorien erweitern. Also wenn wir verschiedene Fitnessstudios haben oder
> Sportclubs, kann ruhig **jeder Empfänger eine Unterkategorie** sein. Das find ich gar nicht
> schlecht, **dann sieht man's deutlicher**." — Jörg, 2026-07-17

**Das überschreibt** den älteren Stand „Geklärt 2026-07-15" (fifi & Robbie → *eine* Unterkategorie
*Fitnessstudio*). Keine Meinungsänderung im Konflikt, sondern eine **Präzisierung**: die alten
Studios sind Historie, für die laufenden gilt **einzeln je Empfänger**.
Umsetzung → [unterkategorien-empfaenger-arbeitsliste.md](unterkategorien-empfaenger-arbeitsliste.md),
Abschnitt 1. Betrifft #50 (live) = Nachjustierung, kein Neubau.

## Offene Fragen (bitte direkt hier beantworten)

| # | Frage | Antwort (Jörg) | Anmerkung aus dem PC-Stand |
|---|---|---|---|
| F1 | KFZ-Versicherung: unter **Auto** oder unter **Versicherungen**? | | offen — betrifft #69 |
| F2 | Betreuung Kinder: **je Kind** getrennt oder ein gemeinsamer Topf? | | offen |
| F3 | Welche **Versicherungs-Policen** existieren aktuell konkret? | | = #69, Ist-Stand aus der Live-DB ziehen |
| F4 | Sollen **Lebensmittel/Drogerie** als laufende Bereiche geführt werden? | | **erledigt** — stehen oben schon als Unterkats unter *Haushaltskasse* |
| F5 | Fehlt eine Kategorie, die du dir schon lange wünschst? | | offen |
| F6 | ~~Sport: bündeln oder einzeln?~~ | **einzeln** | ✅ **entschieden 2026-07-17**, s. o. — war nie offen |

> **Alle noch offenen Fragen stehen jetzt gebündelt in
> [unterkategorien-empfaenger-arbeitsliste.md](unterkategorien-empfaenger-arbeitsliste.md)** —
> dort mit den **echten Empfängern aus der DB** und Bemerkungsspalte zum Durcharbeiten.
> Diese Datei hier ist der ältere Konzeptstand (#50, umgesetzt).
