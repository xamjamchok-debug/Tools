# Das zentrale Gerüst: Vertragserkennung → Zuordnung → Rückstellung → Gegenbuchung

**Design- & Beratungsdokument · Stand 2026-07-18 · für eine Fable-Session zur Beratung**

> **Zweck.** Dies ist das kanonische Design des **Kern-Gerüsts** der Haushalts-App und
> zugleich ein **Beratungsauftrag an Fable**. Es beschreibt (1) den **fachlichen Bedarf**
> (Jörgs Anwendungsfälle, Grenzkriterien, Unklarheiten), (2) das **Software-Design**
> (Datenmodell, Lauf-Logik), (3) den **echten Ist-Stand im Code** und (4) einen präzisen
> **Prüfauftrag**. Fable soll das Gerüst **kritisch beraten** — Logik/Architektur **und**
> App-Design — nicht bestätigen.
>
> **Kanonische Quellen daneben:** `BACKLOG.md` (v3.23, Steuerdatei) · `vertraege-und-
> rueckstellung-design.md` (das Vorgänger-Design mit Jörgs Entscheidungen A–G) ·
> `CODE-ANALYSE-DEEP-DIVE-I.md` (die vier Saldo-Invarianten) · `CODE-ANALYSE-DEEP-DIVE-II.md`
> (Refactor-Roadmap P1–P9, umgesetzt).

---

## Teil I — Der fachliche Bedarf (Anwendungsfälle)

Die App bildet eine private Haushaltskasse ab, die vorher in Excel lief. Das **Herzstück der
alten Excel-Kasse** war ein Kreislauf, den die App vollständig nachbauen muss:

> **Geld wird monatlich *zurückgelegt* (Rückstellung/Einzahlung) und bei *echten Zahlungen
> wieder verzehrt* (Gegenbuchung). Die Differenz je „Nebenbuch" (= Kategorie mit eigenem
> Rücklagen-Topf) ist der Rücklagensaldo. Er soll ruhig um eine Nulllinie schwingen, nicht
> nach unten weglaufen.**

Daraus fünf zusammenhängende Bausteine — **das Gerüst**:

1. **Vertragserkennung** — wiederkehrende Zahlungen als „Verträge" erkennen (Rhythmus + Betrag
   aus der echten Historie), damit die Rückstellung nicht geschätzt oder von Hand gepflegt wird.
2. **Vertragszuordnung** — Buchungen einem Vertrag/Behälter zuweisen (bündeln), Verträge
   Unterkategorien/Nebenbüchern zuordnen, manuelle Behälter anlegen.
3. **Rückstellung ableiten** — aus den bestätigten Verträgen die Soll-Werte je Untertopf
   berechnen und (nach Bestätigung) in die Config übernehmen.
4. **Konfiguration der Rückstellung** — Jörgs **Steuerung**: das Volumen je Nebenbuch ist der
   **Deckel**; Überschreitung erzeugt eine Warnung; bewusste **Schiefstellung** ist erlaubt.
5. **Rückstellungslauf + Gegenbuchung** — monatlich (manuell angestoßen) die geplanten
   Rücklagen **einzahlen**; echte Zahlungen **verzehren** sie über die Spiegel-/Gegenbuchung.

### Die fachlichen Treiber (warum es so und nicht anders sein muss)

| Treiber | Bedeutung |
|---|---|
| **Anbieterwechsel** | Strom: MAINGAU → Naturwerke → Tibber. Fitness: fifi/Robbie → heute. Der *Anbietername* ist ein instabiler Anker; die *Unterkategorie* („Strom") ist stabil und trägt den Topf. Verträge lösen das „historische Werte aussortieren" durch die Regel **`beendet`** (keine Zahlung seit > N Rhythmen). |
| **Regelmäßig ≠ Vertrag** | ALDI/DM/Lebensmittel/Kosmetik sind regelmäßig, aber **keine Verträge** (kein fester Rhythmus/Gebühr). Sie brauchen einen **manuellen Budget-/Sammeltopf** mit Betrag ohne Rhythmus — sonst erzeugt die Erkennung Fehltreffer. |
| **Steuerungssicht darf nicht verloren gehen** | Jörg: *„Wenn Du automatisch saldierst, müssen wir schauen, dass wir aus dem konfigurierten Volumen, das ich diesem Nebenbuch gebe, nicht rausgehen. Da muss ich dringend Warnung haben."* → Der **Config-Deckel** je Nebenbuch ist unantastbar; die Automatik **rechnet und schlägt vor, ändert aber nie das Nebenbuch-Soll**. |
| **Schiefstellung ist manchmal gewollt** | Füchschen (Kinder): Soll 0, aber OGS+Essensgeld ≈ 475 €/Mon, Bestand ~15.000 € — **soll bewusst abschmelzen** (Kindergeld zahlt ein, Posten zahlen aus). TK: ~1.500 € Puffer, Unterdeckung erlaubt. Also braucht es einen **Schalter je Nebenbuch** + eine **Reichweiten-Anzeige** (Bestand ÷ Unterdeckung). |
| **Virtuelles Geld** | Rücklagen sind **kein reales Geld**, sondern eine Planungsschicht auf den realen Konten. Die Rückstellung bucht **virtuelle** `ruecklage`-Zeilen. |

---

## Teil II — Das Gerüst: die fünf Bausteine

Für jeden Baustein: **Zweck · Ist-Stand (mit Datei) · Soll · Grenzkriterien · offene Fragen.**

### Baustein 1 — Vertragserkennung

- **Zweck:** wiederkehrende Zahlungen automatisch als Verträge vorschlagen (Rhythmus, Median-
  Betrag, Status), damit Rückstellungsbeträge aus echten Daten stammen.
- **Ist-Stand — weitgehend gebaut & live:** `workflows/vertraege.py` (`erkenne()`) misst Abstände
  → Rhythmus (`RHYTHMEN`), nimmt den **Median** der Monatssummen als Betrag, setzt `beendet` bei
  letzter Zahlung > `BEENDET_NACH_RHYTHMEN` Rhythmen, führt **Fortsetzungen zusammen**
  (`_fuehre_fortsetzungen_zusammen`, Anbieterwechsel), macht Namen eindeutig, rechnet die
  **Monatsrate** (`_monatsrate`). Erkennung ist **beim Import verdrahtet**: `routes/views.py:218`
  ruft `speichere(cur, erkenne(cur))`.
- **Soll:** Erkennung schreibt **nur Vorschläge** (Status `erkannt`), verändert nie Salden/Solls.
- **Grenzkriterien:** Matching über **Empfänger + Verwendungszweck** (nicht nur Empfänger —
  „Gemeinde Wachtberg" = 4 Zwecke in 3 Nebenbüchern; PayPal = 66 Händler hinter einem Namen).
  Teilstring-Falle (`arag` matcht „G**arag**e") → Muster in Langform.
- **Offene Fragen:** (a) Verträge, die nur **1×** vorkommen (ARAG/Provinzial jährlich) → kein
  messbarer Rhythmus; wie behandeln? (b) **Volumen** — sollen wirklich ~66 PayPal-Händler je ein
  Vertrag werden (→ lange Bestätigungsliste)? Oder eine Klasse „regelmäßig, Händler egal"
  (Sammeltopf), die nie Vertrag wird? **(Diese Frage ist noch offen — s. Teil VI.)**

### Baustein 2 — Vertragszuordnung

- **Zweck:** Buchungen einem Behälter zuordnen (viele → einer = bündeln); Verträge einer
  Unterkategorie zuweisen bzw. auf eine übergreifende bündeln; **manuelle** Behälter anlegen.
- **Ist-Stand — gebaut & live (#78):** `routes/api_vertraege.py` bietet vollen CRUD:
  `POST /api/vertrag` (manuell anlegen), `.../status`, `.../name`, `.../beschreibung`,
  `.../rhythmus`, `.../betrag`, `.../monatsrate`, `.../unterkategorie` (umhängen = bündeln),
  `.../buchung/{id}` (Buchung zuordnen). Verträge-Reiter mit **Drag&Drop und Tipp-Zuordnung**
  (Handy-tauglich). Buchungen tragen `buchungen.vertrag_id`.
- **Soll (offen, #84/#88):** auch **bloße Budget-Untertöpfe** (Lebensmittel/Kosmetik/Allgemein)
  als **Drop-Ziele** auf dem Reiter; erkannte Verträge sichtbar mit **„erkannt"-Haken**.
  **`#88` ist gebaut, aber noch nicht deployt** („Neuer Vertrag" + „Einnahmen" aus Config raus).
- **Grenzkriterien:** Zuordnung ändert Kat/Unterkat der Buchung, **nie** den Rücklagensaldo
  (Prinzip 1). Vertrag = Behälter, `buchungen` hängen an der Unterkategorie, nicht am Vertrag.
- **Offene Fragen:** Bündeln als Normalfall oder Ausnahme? (Design: **Ausnahme** — eigener
  Untertopf je Vertrag als Default, bündeln nur bei Anbieterwechsel.)

### Baustein 3 — Rückstellung ableiten (Soll-Übernahme)

- **Zweck:** aus den **bestätigten** Verträgen je Unterkategorie das Soll berechnen
  (`Σ Vertragsraten`) und — **nach Jörgs Bestätigung** — in `unterkategorien.monatliche_
  ruecklage_cent` übernehmen.
- **Ist-Stand — nur die *Sicht*, nicht der *Vorgang*:** `queries.vertraege()` (queries.py:506)
  berechnet je Nebenbuch die Vertragsraten (Aus-/Eingang), das Config-Soll, den
  Schiefstellungs-Schalter und den Ist-Bestand (für die Reichweite) und speist damit den
  Verträge-Reiter. **Es gibt aber keinen Workflow, der das abgeleitete Soll persistiert.**
- **Soll (fehlt, Teil von #82):** ein **Abgleich-Schritt**, der die Soll-Übernahme
  vorschlägt (Trockenlauf), den Deckel prüft und erst nach OK schreibt.
- **Grenzkriterien:** **Erkennen ≠ Ändern** (Frage F). Solls sind **zwischen zwei
  Rückstellungsläufen stabil**; ein Import darf **informieren, nicht verändern**.
- **Offene Fragen:** s. Baustein 4 (Deckel) + Teil VI.

### Baustein 4 — Konfiguration der Rückstellung (Deckel + Schiefstellung)

- **Zweck:** Jörgs Steuerung erhalten. Das **Config-Volumen je Nebenbuch**
  (`kategorien.monatliche_ruecklage_cent`) ist der **Deckel**. Bereits geltende Regel:
  `Rest-Soll(Default-Unterkat) = Nebenbuch-Soll − Σ(explizite Unterkat-Solls)`. Wird der Rest
  negativ → die Verträge fordern mehr als das Volumen → **Warnsignal**.
- **Ist-Stand — Schema + Sicht da, Durchsetzung fehlt:** `kategorien.schiefstellung_erlaubt`
  (BOOLEAN, Default FALSE) existiert im Schema (`storage/schema.sql`). `queries.vertraege()`
  liefert `soll_cent`, `summe_ausgang_cent`, `schiefstellung_erlaubt` und den Bestand → die
  **Deckel-/Reichweiten-Anzeige** ist als Datensicht vorhanden.
- **Soll (fehlt):** die **Durchsetzung** im Abgleich/Lauf — drei Fälle: ✅ passt (Rest positiv,
  in Default-Topf) · ⚠️ eng (> 90 %, Hinweis) · 🛑 Überschreitung → **harte Warnung, kein
  Schreiben** (außer `schiefstellung_erlaubt` = TRUE, dann buchen **mit** Unterdeckungs-/
  Reichweiten-Anzeige `Reichweite = Bestand ÷ Unterdeckung/Monat`).
- **Grenzkriterien:** Der Deckel prüft **Monatsfluss** (Σ Raten vs. Soll). **Bestand** ist eine
  zweite Dimension — Unterdeckung ist bei Füchschen/TK **gewollt**, bei Auto/Vers ein **Fehler**.
- **Offene Fragen:** Warnung „hart" heißt: gar nichts wird gebucht, oder nur der überschreitende
  Nebenbuch pausiert? Wo wird Bestand für die Reichweite gemessen (je Nebenbuch/je Untertopf)?

### Baustein 5 — Rückstellungslauf + Gegenbuchung

- **Zweck:** monatlich (**manuell** von Jörg angestoßen) die geplanten Rücklagen **einzahlen**;
  echte Zahlungen **verzehren** sie automatisch (Spiegel/Gegenbuchung).
- **Ist-Stand — Verzehr da, Einzahlung fehlt (🛑 #76):** die **Gegenbuchung/Verzehr** existiert
  (`workflows/gegenbuchung.py` — Spiegelbuchungen, Rollen/Flags) und läuft bei jedem Import
  automatisch. **Der Einzahl-/Rückstellungslauf existiert NICHT** — `workflows/rueckstellung.py`
  gibt es nicht. Bisher kamen **alle** Einzahlungen aus der Excel-Beladung (`quelle_import=
  'fb-kto'`, reicht bis 31.07.2026). **⇒ Ab 09/2026 wird nur noch verzehrt, nie eingezahlt →
  die Töpfe leeren sich, der Saldo driftet.** (August ist bewusst vorab gestellt — bleibt
  unangetastet.)
- **Soll (fehlt, #76):** `workflows/rueckstellung.py` — 1×/Monat, je Nebenbuch: je bestätigtem
  Vertrag `Untertopf += Rate`; Rest `Allgemein += Config-Soll(NB) − Σ Raten`; Deckelprüfung;
  `quelle_import='rueckstellung'`; **idempotent je Nebenbuch/Monat**; **rückwirkend** (fehlende
  Monate nachholen, nie einen gestellten überschreiben); Trockenlauf-Default; Protokoll in
  `admin_laeufe` (existiert via #61, `workflows/audit.py`).
- **Grenzkriterien:** kein eigener Topf „Rücklage" (die Rücklage ist ein **Vorgang**, kein Topf).
  Erster echter Lauf **frühestens 09/2026** (Juli aus `fb-kto`, August vorab gestellt).
- **Offene Fragen:** Übergang „alles auf Allgemein" → „vertragsbasiert verteilt" — s. Teil VI.

---

## Teil III — Grundprinzipien (Jörg, unverhandelbar, #80)

1. **Der Rücklagensaldo bleibt, wie er ist.** Er ändert sich NUR durch (a) Jörg manuell oder
   (b) den monatlichen Rückstellungslauf. Kein Import, keine Erkennung, keine Zuordnung fasst
   ihn an.
2. **Nicht verteiltes Budget liegt auf „Allgemein"** je Nebenbuch — bewusster Sammel-/Puffertopf
   für Unregelmäßiges, kein Fehler.
3. **Alle Buchungen eines Nebenbuchs zusammen bilden die Rücklage.** Stimmt es nicht, gibt es eine
   **Wahrnehmung** (sichtbare Anzeige), die Jörg bewusst löst — **Überbuchung akzeptieren ODER
   Rücklage erhöhen**. **Nie still automatisch ausgleichen.**

Jörgs Entscheidungen A–G (aus `vertraege-und-rueckstellung-design.md`) gelten als getroffen:
**A** eigene Unterkat je Vertrag, bündelbar · **C** Warnung hart · **D** Verträge erst bestätigen ·
**E** keine Position „Rücklage" (Vorgang, kein Topf) · **F** Erkennen ≠ Ändern (Solls nur beim
Lauf, mit Bestätigung; Import informiert nur) · **G** rückwirkend nachholen, aber nie doppelt.

---

## Teil IV — Software-Design

### Datenmodell (IST, in `storage/schema.sql`)

```
vertraege(
  id, name, unterkategorie_id → unterkategorien(id),   -- N:1, hier liegt der Topf
  muster_empfaenger, muster_zweck,                      -- ILIKE, Langform
  rhythmus CHECK(monatlich|quartalsweise|halbjaehrlich|jaehrlich|unregelmaessig),
  betrag_median_cent, letzte_zahlung, naechste_faellig,
  status CHECK(erkannt|bestaetigt|beendet|ignoriert),
  quelle CHECK(auto|manuell),
  richtung CHECK(ausgang|eingang) DEFAULT 'ausgang',    -- Kindergeld = eingang
  monatsrate_cent BIGINT DEFAULT 0,                     -- die Rückstellungsrate (editierbar)
  beschreibung
)
buchungen.vertrag_id → vertraege(id) ON DELETE SET NULL   -- Pin einer Buchung an einen Vertrag
kategorien.schiefstellung_erlaubt BOOLEAN DEFAULT FALSE   -- Deckel-Ausnahme je Nebenbuch
```

Steuer-Felder (bestehend): `kategorien.monatliche_ruecklage_cent` (Deckel/Volumen je Nebenbuch),
`unterkategorien.monatliche_ruecklage_cent` (Soll je Untertopf), `kategorien.default_unterkategorie_id`
(Auffang-Topf „Allgemein").

### Der Rückstellungslauf (SOLL, `workflows/rueckstellung.py`, zu bauen)

```
Einmal/Monat, von Jörg angestoßen, je Nebenbuch (Trockenlauf-Default):
1. Idempotenz:   existiert für (Nebenbuch, Monat) schon eine Einzahlung? (egal welche quelle) → skip
2. Je bestätigtem Vertrag:   Untertopf += monatsrate_cent            (virtuelle +ruecklage-Zeile)
3. Rest nach Allgemein:      Allgemein += Config-Soll(NB) − Σ(Raten) (= die geltende Rest-Soll-Regel)
4. Deckelprüfung:            Σ(Raten) > Config-Soll(NB)?
                               schiefstellung_erlaubt=FALSE → 🛑 Warnung, NICHTS buchen
                               schiefstellung_erlaubt=TRUE  → buchen + Unterdeckung/Reichweite zeigen
5. Rückwirkend:              fehlende Monate seit letztem Lauf nachholen (je NB/Monat genau 1×)
6. Protokoll:                Lauf in admin_laeufe (audit.py); quelle_import='rueckstellung'
```

Wiederverwenden statt neu bauen: `queries.vertraege()` (Deckel/Reichweite-Sicht) · `audit.py`/
`admin_laeufe` (Protokoll #61) · `gegenbuchung.py` (Verzehr) · `domain/saldo.py` (Vorzeichen-/
Rollen-Logik, single source #60) · das Trockenlauf-/Idempotenz-Muster aus `s_merge.py`/
`kategorie_cleanup.py`/`allgemein_verteilen.py`.

### Testreferenz (das Orakel für #76)

Die 10 Buchungen vom **31.07.2026** (`quelle_import='fb-kto'`, alle auf **Allgemein**) zeigen, wie
der Excel-Lauf rechnete — **8 von 10 centgenau = Config-Soll** (Auto, Inst, Jörg, Kredit, Sport,
Telefon, TK, Vers). Nebenkosten (−20), Urlaub (+650,14 Sonderzahlung?), Haushaltskasse (1.402 nie
gestellt), Füchschen (Soll 0) weichen ab — **das sind Datenfragen, keine Baufehler** (Teil VI).
Der Nachbau muss für 08/2026 dieselben Zahlen produzieren (aber **nicht** buchen — August ist da).

---

## Teil V — Abhängigkeiten & Reihenfolge

```
#80 Grundprinzipien ──────── Leitplanke über allem
        │
#75 Verträge (Erkennung+Schema)  ✅ gebaut/live (vertraege.py, Schema, queries.vertraege)
        │
#78 Verträge-Reiter (Zuordnung)  ✅ deployt   ── #88 (Neuer Vertrag) 🔨 gebaut, wartet auf Deploy
        │                                       ── #84 (Untertopf-Drop-Ziele) 💡 offen
        ▼
#82 Großer Config-Abgleich       📐 designt, NICHT gebaut  (Soll-Übernahme + Deckel-Durchsetzung
        │                                                    + interaktive „Wahrnehmungen")
        ▼
#76 Rückstellungslauf            🛑 FEHLT KOMPLETT — dringendster Punkt (Drift ab 09/2026)
```

**Betriebliche Realität (wichtig für „geht das übers Handy?"):**

- **Code entwickeln + pushen:** ✅ in der Cloud-Session.
- **DB-Workflows ausführen** (#76 Lauf, #82 Abgleich): ✅ **handy-machbar** — GitHub Actions hat
  das DB-Secret (`backup.yml` nutzt `secrets.HAUSHALT_DATABASE_URL` + `workflow_dispatch`). Als
  **dispatchbare Action mit Trockenlauf-Default** vom Handy auslösbar.
- **UI live bringen** (#84, #88, alles Frontend): ❌ **aktuell nicht** — der Deploy-Job in
  `.github/workflows/ci.yml` ist rot (OIDC-Vars `AZURE_CLIENT_ID/TENANT/SUBSCRIPTION` fehlen,
  #62). Deploy geht nur manuell am PC. **Einmal #62 einrichten → danach alles handy-deploybar.**

---

## Teil VI — Offene Fragestellungen & Unklarheiten (konsolidiert)

**Design-/Logik-offen (Jörg oder Fable):**

1. **Erkennungs-Volumen.** ~66 PayPal-Händler + Abos je einzeln bestätigen (lange Liste) — oder
   eine Klasse „regelmäßig, Händler egal" (Sammeltopf Presse/Google), die nie Vertrag wird?
   Entscheidet, ob die Bestätigungsliste 15 oder 80 Zeilen lang ist.
2. **Übergang Allgemein → vertragsbasiert.** Der erste vertrags-bewusste Lauf zieht Geld aus
   „Allgemein" in einzelne Untertöpfe. Wie verträgt sich das mit den schon auf Allgemein
   gebuchten Monaten? (Rückwirkend umverteilen? Nur ab dem nächsten Lauf? Bestand bleibt, nur
   künftige Raten gehen fein?) **Einziger echter Logik-Übergang, der nirgends gezeichnet ist.**
3. **Einmal-Verträge ohne messbaren Rhythmus** (ARAG/Provinzial jährlich, 1 Zahlung) — als
   `unregelmaessig` verwerfen oder manuell als jährlich bestätigen lassen?
4. **Warnung „hart"** — global nichts buchen oder nur den betroffenen Nebenbuch pausieren?
5. **Reichweite** — Bestand je Nebenbuch oder je Untertopf messen?

**App-Design-offen (bestes Feld für Fable):**

6. **Der #82-Abgleich-Screen** ist **nirgends gezeichnet.** Die Logik steht (Deckel, Überbuchung
   akzeptieren vs. Soll erhöhen), aber wie eine „Wahrnehmung" konkret aussieht (Screen? Liste?
   inline in Config? Nebenbuch für Nebenbuch?) fehlt völlig.
7. **Schiefstellung/Reichweite-Anzeige** — wie wird „Unterdeckung 475 €/Mon · reicht ~31 Monate"
   dargestellt, ohne die Übersicht zu überfrachten?

**Datenfragen (nur Jörg, gaten den ersten echten Lauf, nicht den Bau):**

8. Haushaltskasse Soll 1.402 nie gestellt — Absicht (laufende Ausgaben) oder Lücke?
9. Füchschen Soll 0 trotz ~475 €/Mon fest — bewusst ohne Rücklage (Schiefstellung) oder Soll setzen?
10. Nebenkosten (−20) / Urlaub (+650) — Sonderzahlung/Handkorrektur oder systematisch?

---

## Teil VII — Ist-Stand im Code (Gerüst → Datei → Status)

| Baustein | Datei(en) | Status |
|---|---|---|
| 1 Vertragserkennung | `workflows/vertraege.py` (`erkenne`), Trigger `routes/views.py:218` | ✅ gebaut & live |
| 2 Vertragszuordnung | `routes/api_vertraege.py` (CRUD), Reiter #78 | ✅ gebaut & live |
| 2 (Zusatz) Neuer Vertrag / Drop-Ziele | #88 `POST /api/vertrag` (🔨 nicht deployt) · #84 (💡 offen) | ⚠️ teils offen |
| 3 Rückstellung ableiten (Soll-Übernahme) | *Sicht* in `queries.vertraege()` (queries.py:506) | ⚠️ nur Sicht, **kein Vorgang** |
| 4 Deckel + Schiefstellung | Schema `schiefstellung_erlaubt`, `queries.vertraege()` | ⚠️ Sicht da, **Durchsetzung fehlt** |
| 5a Gegenbuchung/Verzehr | `workflows/gegenbuchung.py` | ✅ gebaut & live |
| 5b **Rückstellungslauf (Einzahlung)** | `workflows/rueckstellung.py` | 🛑 **existiert nicht (#76)** |
| Protokoll/Audit | `workflows/audit.py`, Tabelle `admin_laeufe` | ✅ da (#61) |
| Deploy-Weg | `.github/workflows/ci.yml` (deploy), `backup.yml` (DB-Secret) | ⚠️ Auto-Deploy rot (OIDC #62) |

**Kurzfassung:** Erkennung, Zuordnung, die Deckel-/Schiefstellungs-**Sicht** und der **Verzehr**
stehen. Es fehlen (a) die **Soll-Übernahme + Deckel-Durchsetzung als Vorgang** (#82) und (b) der
**monatliche Rückstellungslauf** (#76) — der dringendste Punkt.

---

## Teil VIII — Auftrag an Fable

**Berate kritisch, in zwei präzise abgegrenzten Deliverables. Bestätige nicht — suche, was trägt
und was nicht.**

### Deliverable 1 — Logik & Architektur (read-only gegen die Live-DB)
`docs/FABLE-REVIEW-geruest-logik.md`
- **Erkennung an echten Daten prüfen:** Laufen die `RHYTHMEN`/Median/`beendet`-Heuristiken sauber
  über die realen Buchungen? Wie viele Verträge/Fehltreffer entstehen (v. a. **PayPal 220**,
  **Gemeinde Wachtberg**, jährliche Versicherungen)? Kollidieren `muster_empfaenger`/`muster_zweck`
  (Teilstring-Falle)? → belastbare Zahl zum **Volumen** (offene Frage 1).
- **Deckel-Mathematik reconcilen:** Stimmt `queries.vertraege()` (Σ Raten vs. Config-Soll,
  Reichweite) mit den tatsächlichen Config-Soll je Nebenbuch überein? Wo entstehen Schiefstellungen?
- **#76-Design gegenrechnen:** Reproduziert der geplante Lauf die **8 centgenauen 31.07.-Werte**?
  Hält die Idempotenz Jörgs vorab gestellten August? Ist der **Allgemein→vertragsbasiert-Übergang**
  (offene Frage 2) sauber lösbar — schlag **eine** konkrete Regel vor.
- **Datenfragen 8–10** aus den Daten beantworten, soweit möglich.

### Deliverable 2 — App-Design (nur die zwei undesignten Flächen)
`docs/FABLE-REVIEW-geruest-appdesign.md`
- **Der #82-Abgleich-Screen** („Wahrnehmungen"): wie geht Jörg **Nebenbuch für Nebenbuch** durch
  und löst jede Abweichung (Überbuchung akzeptieren ODER Soll erhöhen)? Konkreter Screen/Flow,
  **handy-tauglich**, im Stil der bestehenden Templates (`dashboard/templates/*.html`, helle
  Weiß-Blau-Gelb-Optik).
- **Schiefstellung/Reichweite-Anzeige**: „Unterdeckung X/Mon · reicht ~N Monate" ohne Überfrachtung.

### Arbeitsregeln (bindend)
- **Nur read-only gegen die Live-DB** (`.env` → `HAUSHALT_DATABASE_URL`). SELECTs zum Nachrechnen —
  **kein** Schreibzugriff, **kein** Deploy, **keine** `--write`-Läufe.
- Read-only-Skripte ins Scratchpad, `PYTHONIOENCODING=utf-8 PYTHONPATH=<repo> python skript.py`.
- Ergebnis = **MD-Dokumente** (Analyse + Vorschläge), **kein** Produktivcode-Umbau. Jörg entscheidet.
- Tests laufen lassen erwünscht: `pytest haushaltskasse/tests -v` (nutzt `HAUSHALT_TEST_DATABASE_URL`).
- **Nicht anfassen:** die vorab gestellte August-Rücklage (31.07., `fb-kto`); die Grundprinzipien
  #80; die getroffenen Entscheidungen A–G (nur bewerten, nicht umwerfen — aber **explizit
  widersprechen, wenn etwas nicht trägt**, das ist wertvoller als Bestätigung).
- **#76 nicht gaten:** Der Rückstellungslauf ist reif und hat die Deadline — Fable berät ihn,
  blockiert ihn aber nicht; er wird parallel gebaut.
