# Vorschlag: Verteilung der Untertöpfe (Modell A vervollständigen, #R6/#28)

> Problem: Bei der Migration (`allgemein_toepfe.py`) landeten alle Zuführungen je Nebenbuch im
> Sammel-Topf **„Allgemein"** — die Untertopf-Salden sind dadurch „kraut und rüben".
> Ziel: den aktuellen Topf-Stand je Nebenbuch **sinnvoll auf die neuen Unterkategorien verteilen**
> (Namen s. `unterkategorien-vorschlag.md`).

## Methode
Die exakten aktuellen Topf-Salden liegen in der Azure-DB (hier in der Cloud nicht erreichbar).
Deshalb hier **Anteile in %** — die man auf den echten „Allgemein"-Stand je Nebenbuch anwendet:

1. je Nebenbuch den aktuellen **„Allgemein"-Topf-Stand** lesen,
2. mit den %-Anteilen unten auf die Unterkategorie-Töpfe **aufteilen** (Umbuchung Allgemein → Untertopf),
3. dieselben Anteile geben auch einen Startwert fürs **monatliche Soll** je Unterkategorie
   (Nebenbuch-Soll aus Config × Anteil) → speist #39.

**Herleitung der Anteile:** grob aus dem historischen Ausgaben-Mix der alten Kto-Blätter
(welche Unterposition wie viel Gewicht hatte). **Startvorschlag — bitte an echten Zahlen justieren.**
Lumpige Töpfe (Urlaub, Instandhaltung) sind naturgemäß unsicher.

---

## Vorschlag je Nebenbuch (Anteil in %)

**Auto**
| Unterkategorie | Anteil |
|---|--:|
| Tanken | 45 % |
| Reparatur & Werkstatt | 25 % |
| KFZ-Steuer | 15 % |
| Finanzierung/Leasing | 10 % |
| Zweirad / sonstiges | 5 % |

**Versicherung**
| Unterkategorie | Anteil |
|---|--:|
| KFZ-Versicherung | 40 % |
| Leben/BU (RLV) | 25 % |
| Haftpflicht | 12 % |
| Hausrat | 10 % |
| Gebäude | 8 % |
| Rechtsschutz | 5 % |

**Nebenkosten**
| Unterkategorie | Anteil |
|---|--:|
| Wasser/Abwasser | 35 % |
| Strom | 30 % |
| Grundsteuer | 15 % |
| Müll | 10 % |
| Schornsteinfeger | 5 % |
| Garten & Außenanlage | 5 % |

**Sport**  *(fifi/Robbie noch klären → ggf. eigener Anteil)*
| Unterkategorie | Anteil |
|---|--:|
| Fitnessstudio | 45 % |
| Verein/Mitgliedschaft | 30 % |
| Kurse & Training | 20 % |
| Ausrüstung | 5 % |

**Füchschen (Kinder)**
| Unterkategorie | Anteil |
|---|--:|
| Betreuung (OGS/Kita) | 45 % |
| Schulbedarf | 20 % |
| Ausstattung & Anschaffung | 15 % |
| Kindergarten | 15 % |
| Freizeit | 5 % |

**Telefon/Medien**
| Unterkategorie | Anteil |
|---|--:|
| Mobilfunk & Internet | 45 % |
| Streaming & Software | 30 % |
| Rundfunkbeitrag | 10 % |
| Zeitung/Medien | 10 % |
| sonstige Abos | 5 % |

**Krankenkasse/Gesundheit (TK)**  *(DKV dominiert klar)*
| Unterkategorie | Anteil |
|---|--:|
| Private KV (DKV) | 70 % |
| Krankenkasse (TK) | 12 % |
| Arzt & Zahnarzt | 10 % |
| Apotheke | 8 % |

**Kredit**  *(Immobilienkredit dominiert)*
| Unterkategorie | Anteil |
|---|--:|
| Immobilienkredit (Deutsche Bank) | 90 % |
| KfW-Darlehen | 10 % |

**Instandhaltung**  *(sehr lumpig — Anteile nur grob)*
| Unterkategorie | Anteil |
|---|--:|
| Handwerker | 45 % |
| PV/Solar | 20 % |
| Möbel & Einrichtung | 15 % |
| Baumaterial | 15 % |
| sonstige Anschaffung | 5 % |

**Urlaub**  *(trip-basiert, sehr lumpig — evtl. lieber pro Reise, s. Naming-Doc)*
| Unterkategorie | Anteil |
|---|--:|
| Flüge | 40 % |
| Unterkunft | 35 % |
| Vor Ort | 20 % |
| Reise sonstiges | 5 % |

**Haushaltskasse**
| Unterkategorie | Anteil |
|---|--:|
| Lebensmittel | 45 % |
| Amazon/Konsum | 20 % |
| Auswärts essen | 15 % |
| Drogerie | 12 % |
| Bäcker | 5 % |
| Bargeld | 3 % |

---

## Umsetzung (Vorschlag)
Wenn du die Anteile bestätigst/justierst, baue ich ein idempotentes Skript
`workflows/allgemein_verteilen.py`:
- liest je Nebenbuch den **„Allgemein"-Topf-Stand**,
- legt die Unterkategorien an (falls nicht vorhanden),
- bucht `Allgemein → Untertopf` gemäß Anteil (als `ruecklage`-Umbuchung, quelle 'migration'),
- setzt optional das monatliche Soll je Untertopf (Nebenbuch-Soll × Anteil).
- **Trockenlauf zuerst** (nur anzeigen), dann `--write`.

**Wichtig:** Zahlen justieren wir an den echten Salden — die %-Werte oben sind ein begründeter
Startpunkt aus der Excel-Historie, kein exaktes Abbild.
