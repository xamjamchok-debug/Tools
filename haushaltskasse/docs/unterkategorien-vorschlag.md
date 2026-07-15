# Vorschlag: bessere Unterkategorien + Mapping (Umsatz → Nebenbuch / Unterkategorie)

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
| **Auto** | Tanken · KFZ-Steuer · Reparatur & Werkstatt · Finanzierung/Leasing · Zweirad · Mietwagen · Anschaffung | S-Auto, R-Auto, H-Auto |
| **Versicherung** | KFZ-Versicherung · Haftpflicht · Hausrat · Rechtsschutz · Leben/BU (RLV) · Gebäude | S-Vers, Haftpflicht |
| **Nebenkosten** | Wasser/Abwasser · Strom · Grundsteuer · Müll · Schornsteinfeger · Garten & Außenanlage | S-NK, Abwasser |
| **Sport** | Fitnessstudio · Verein/Mitgliedschaft · Kurse & Training · Ausrüstung | S-Sport, R-Sport |
| **Urlaub** | Flüge · Unterkunft · Vor Ort (Verpflegung/Aktivität) · Reise sonstiges | S-Urlaub, Bar |
| **Füchschen (Kinder)** | Betreuung (OGS/Kita) · Kindergarten · Schulbedarf · Ausstattung & Anschaffung · Freizeit | S-Füchschen, Kiga etc |
| **Telefon/Medien** | Mobilfunk & Internet · Streaming & Software · Rundfunkbeitrag · Zeitung/Medien · sonstige Abos | Abo, S-Tel |
| **Instandhaltung** | Handwerker · PV/Solar · Möbel & Einrichtung · Baumaterial · sonstige Anschaffung | S-Inst, H-Inst |
| **Krankenkasse/Gesundheit (TK)** | Private KV (DKV) · Krankenkasse (TK) · Apotheke · Arzt & Zahnarzt | S-TK, tk |
| **Kredit** | Immobilienkredit (Deutsche Bank) · KfW-Darlehen · Sondertilgung/Zinsen | S-Kredit, deuba |
| **Haushaltskasse** | Lebensmittel · Drogerie · Bäcker · Auswärts essen · Amazon/Konsum · Bargeld | Konsum, Edeka/Aldi, S-… |

---

## Mapping-Tabelle: Empfänger/Muster → Nebenbuch / Unterkategorie

*(die wichtigsten wiederkehrenden Umsätze; der Rest wird über die Lernregeln + KI-Vorschlag ergänzt)*

| Erkennung (Empfänger / Verwendungszweck enthält) | Nebenbuch | Unterkategorie |
|---|---|---|
| Shell, Aral, Agip, bft, Esso, „Tankstelle" | Auto | Tanken |
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
| „Garten", „Holz", „Mauer", „Rollos", „Markise" | Nebenkosten | Garten & Außenanlage |
| FITPARK, HEALTHCITY, Powerplate, „Fitness" | Sport | Fitnessstudio |
| Godesberger Judo Club, SSF, „Jahresbeitrag", „Verein" | Sport | Verein/Mitgliedschaft |
| Frank … Habermann (Fitness Club Berkum), „Training", „Kurs" | Sport | Kurse & Training |
| Thai Airways, 2C2P, „Airways", „Flug", Lufthansa, Ryanair | Urlaub | Flüge |
| „Hotel", „monte da quinta", Booking.com (Übernachtung) | Urlaub | Unterkunft |
| „Portugal", „Südtirol", „Fuerte" (Vor-Ort-Ausgaben) | Urlaub | Vor Ort |
| Gemeinde Wachtberg „Elternbeiträge OGS", Katholische Jugendagentur, KJF | Füchschen | Betreuung (OGS/Kita) |
| „Kindergarten", „Kita" | Füchschen | Kindergarten |
| Rhein-Sieg-Kreis (Schule), „Schulbedarf" | Füchschen | Schulbedarf |
| Amazon (Kinderartikel), „Radanhänger", „Chariot", Bottosso | Füchschen | Ausstattung & Anschaffung |
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

## Offene Punkte / Klärung
- **Sport:** „fifi" und „Robbie" tauchen groß auf — Personen/Kurse? Bitte einordnen (Trainer? Kind?).
- **Urlaub:** evtl. lieber **pro Reise** (z. B. „Südtirol 2020") statt fixer Unterkategorien? Deine Wahl.
- **Nebenkosten vs. Instandhaltung:** „Garten/Holz/Mauer" stehen im alten NK-Blatt, sind aber eher
  Instandhaltung — verschieben oder als NK/„Garten & Außenanlage" lassen?
- **Amazon** verteilt sich über viele Nebenbücher — hier hilft später die Bemerkung/KI je Bestellung.
