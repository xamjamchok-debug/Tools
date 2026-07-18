# Fable-Review II — App-Design: der #82-Abgleich-Screen und die Reichweiten-Anzeige

**Stand 2026-07-18 · Fable (read-only-Beratung) · Antwort auf Teil VIII des Auftrags, Deliverable 2**
Gestaltet im Stil der bestehenden Templates (`base.html`: helle Weiß-Blau-Gelb-Papier-Optik,
CSS-Tokens `--accent #2e6ca6`, `--hi #d8a21a`, `--pos/--neg`, `.card`/`.pill`/`.hinweis`),
handy-tauglich nach dem Muster des Verträge-Reiters (Antippen statt Hover, sticky Banner,
`@media (max-width:820px)`-Umbruch).

**Datengrundlage:** Alle hier verwendeten Kennzahlen existieren bereits als Queries
(`queries.vertraege()`, Rücklagen-Baum) oder sind einfache Ergänzungen. Die konkreten
Wahrnehmungs-Typen stammen aus den Live-Befunden des Logik-Reviews
(`FABLE-REVIEW-geruest-logik.md`, dort L1–L5, 2.4, 4.1–4.3).

**Betriebshinweis:** Beide Flächen sind Frontend → sie brauchen einen Deploy (#62 OIDC ist
rot, Deploy nur manuell am PC). Der #76-Lauf selbst bleibt davon unabhängig als
GitHub-Action dispatchbar. Der Abgleich sollte deshalb NICHT als Blocker vor #76 gebaut
werden, sondern parallel — der Lauf-Trockenlauf (Action-Log) ist das Sicherheitsnetz,
solange der Screen fehlt.

---

## Teil 1 — Der #82-Abgleich-Screen: „Abgleich" (Wahrnehmungen lösen)

### 1.1 Das Konzept in einem Satz

**Ein eigener Reiter „Abgleich", der Nebenbuch für Nebenbuch durch einen Stapel von
Wahrnehmungs-Karten führt; jede Karte ist eine Abweichung mit genau zwei bis drei großen
Entscheidungs-Buttons — nichts wird still ausgeglichen, jede Entscheidung schreibt sofort
(mit Undo-Flash), und der Fortschritt ist sichtbar („Nebenbuch 3 von 11 · 2 offen").**

Kein Modal-Wizard, kein Formular-Grab: **Karten-Stapel je Nebenbuch**, weil (a) Jörg den
Abgleich als „konzentrierten, eigenen Arbeitsschritt … Nebenbuch für Nebenbuch" definiert
hat, (b) Karten mit 2–3 Buttons das einzige Muster sind, das auf dem Handy ohne Zoomen
funktioniert, und (c) der Bestand an Wahrnehmungen beim ersten Abgleich groß ist (heute
real: 26 × Rate-0, 5 × NULL-Unterkat, 1 × fehlende Default-Unterkat, 3–5 × Deckel/Verzehr,
~5 × „große Einzelzahlung ohne Vertrag" — ein einziger langer Screen wäre erschlagend).

### 1.2 Informationsarchitektur

```
Nav:  Übersicht · Rücklagen · Verträge · Abgleich (7) · Buchungen · Reports · Config · Import
                                        └── Badge = Zahl offener Wahrnehmungen (wie „Vorschläge
                                            warten" auf dem Verträge-Reiter; 0 → kein Badge)

/abgleich                     Einstieg: Nebenbuch-Liste mit Ampel + Zähler (der „Laufzettel")
/abgleich?kat=<id>            Detail: Karten-Stapel EINES Nebenbuchs
```

Zwei Ebenen genügen. Der Einstieg ist der Laufzettel („wo stehe ich?"), das Detail ist die
Arbeit („was entscheide ich?"). Zurück-Pfeil oben links, nächstes Nebenbuch unten rechts —
so entsteht der „Nebenbuch für Nebenbuch"-Pfad, ohne dass ein Wizard den Zustand halten muss
(alles ist URL-adressierbar, F5-fest, Handy-Back-Button funktioniert).

### 1.3 Ebene 1 — der Laufzettel

```
┌──────────────────────────────────────────────────────────┐
│ Abgleich                                                 │
│ Verträge + Töpfe gegen deine Config — jede Abweichung    │
│ bewusst lösen, nichts wird still ausgeglichen.           │
│                                                          │
│ ▸ Zuletzt vollständig abgeglichen: 2026-08-02 · 18:40    │
│   [ Vor dem Rückstellungslauf: 0 offene 🛑 nötig ]       │
│                                                          │
│  Nebenbuch        Soll/Mon   Raten   Ist-Verzehr  offen  │
│  ────────────────────────────────────────────────────────│
│  🛑 Haushaltskasse 1.402,00   40,00   Ø 3.031/Mon    3  ▸│
│  🛑 Auto             240,00  241,43   Ø   310/Mon    2  ▸│
│  ⚠️ Vers             398,00  101,15   Ø   380/Mon    2  ▸│
│  ✅ Kredit         2.147,00 2.146,34  Ø 2.146/Mon    –  ▸│
│  ✅ Füchschen (schief) 0,00  −298,50  Ø   171/Mon    –  ▸│
│  …                                                       │
└──────────────────────────────────────────────────────────┘
```

- Eine Zeile je Rücklage-Nebenbuch (Rolle `ruecklage`; Forderungen tauchen hier bewusst
  nicht auf — s. Logik-Review 3.3.2). Tap auf die Zeile → Ebene 2.
- Sortierung: 🛑 zuerst, dann ⚠️, dann ✅ — der Nutzer arbeitet automatisch von oben.
- **Neue Spalte „Ist-Verzehr"** (Ø der realen Abflüsse, 3 Monate): schließt die im
  Logik-Review (2.2a) belegte Blindheit der Raten-Ampel bei Konsum-Nebenbüchern.
  Haushaltskasse wird dadurch überhaupt erst rot — mit der reinen Raten-Ampel wäre sie grün.
- Die Kopfzeile trägt das Gate für #76: „vor dem Lauf müssen 0 harte Wahrnehmungen offen
  sein" — als Information, nicht als technische Sperre (der Lauf selbst prüft den Deckel
  ohnehin je Nebenbuch; Entscheid C).

### 1.4 Ebene 2 — der Karten-Stapel eines Nebenbuchs

Kopf (sticky, wie das Zuordnungs-Banner im Verträge-Reiter):

```
┌──────────────────────────────────────────────────────────┐
│ ← Abgleich    Haushaltskasse         Nebenbuch 3 von 11  │
│ Soll 1.402,00 · Raten 40,00 · Ist-Verzehr Ø 3.031,00     │
│ Bestand 364,80 · [🛑 2 offen · 1 erledigt]               │
└──────────────────────────────────────────────────────────┘
```

Darunter die Karten, **eine pro Wahrnehmung**, jeweils: Befund in einem Satz (Zahlen fett),
Konsequenz in einem Halbsatz, 2–3 Buttons. Beispiele mit den echten Live-Fällen:

**Karte Typ A — Deckel/Verzehr-Abweichung (das Kernstück, Prinzip 3):**

```
┌──────────────────────────────────────────────────────────┐
│ 🛑 Topf leert sich                                       │
│ Ist-Verzehr Ø **3.031 €/Mon** liegt **1.629 €** über dem │
│ Soll (1.402). Bestand 364,80 → rechnerisch ~0 Monate.    │
│                                                          │
│ [ Soll anheben auf … (Vorschlag 3.031) ]   ← primär      │
│ [ Schiefstellung erlauben (Topf darf abschmelzen) ]      │
│ [ später entscheiden ]                                   │
└──────────────────────────────────────────────────────────┘
```

- „Soll anheben" öffnet **inline** ein vorbefülltes Zahlenfeld (Vorschlag = Ø-Verzehr,
  überschreibbar) und schreibt `kategorien.monatliche_ruecklage_cent` über den bestehenden
  Config-Endpoint. Kein Absprung in den Config-Reiter — der Kontext bleibt.
- „Schiefstellung erlauben" = der existierende Schalter (`POST /api/nebenbuch/{id}/schiefstellung`),
  danach zeigt die Karte sofort die Reichweiten-Zeile (Teil 2) als Bestätigung.
- „später" verschiebt ans Ende des Stapels (Session-lokal) — erledigt nichts, erlaubt aber
  Weiterarbeiten. Die Wahrnehmung bleibt gezählt.

**Karte Typ B — Soll-Übernahme (Baustein 3, „Trockenlauf der Rückstellung ableiten"):**

```
┌──────────────────────────────────────────────────────────┐
│ ⚠️ 26 bestätigte Verträge ohne Rückstellungs-Rate        │
│ Beim Bestätigen gab es das Rate-Feld noch nicht — die    │
│ Deckel-Rechnung läuft dadurch mit 0.                     │
│  Telekom          Vorschlag 70,70 €/Mon   [✓] [ändern]   │
│  Judo-Club        Vorschlag 73,71 €/Mon   [✓] [ändern]   │
│  … (aufklappbar, je Zeile einzeln bestätigbar)           │
│ [ Alle 26 Vorschläge übernehmen ]                        │
└──────────────────────────────────────────────────────────┘
```

Dasselbe Karten-Muster trägt später die laufende Soll-Übernahme („Vertrag neu/geändert/
beendet — Soll übernehmen?") aus Entscheid F, Schritt 1 des Lauf-Moments.

**Karte Typ C — Hygiene-Wahrnehmungen** (je eine Karte pro Befund-Klasse):
- „**+1.675,00** liegen ohne Untertopf im Nebenbuch — auf *Allgemein* einsortieren?"
  `[ Nach Allgemein ] [ anders zuordnen… ]` (Live-Befund 2.4.2; Prinzip 2).
- „Haushaltskasse hat **keinen Auffang-Topf (Allgemein)** — anlegen und als Default setzen?"
  `[ Anlegen ]` (Live-Befund 2.4.1 — ohne den kann der Lauf den Rest nicht buchen).
- „**3 große Einzelzahlungen ohne Vertrag** (ADAC-KFZ 1.686,98 · ARAG 578,04 · Provinzial
  491,00) — als jährlichen Vertrag anlegen?" `[ Vertrag anlegen (vorbefüllt) ] [ ignorieren ]`
  → ruft den bestehenden `POST /api/vertrag` mit Rate = Betrag ÷ 12 (Logik-Review 1.2b).
- „Untertopf-Soll **25,00** (Haftpflicht, Hand) ≠ Vertragsraten **21,40** — Rate übernehmen
  oder Handwert behalten?" (Logik-Review 2.3).

**Karte Typ D — Übergangs-Startdotierung** (einmalig, vor dem ersten Lauf; Logik-Review 3.4):

```
┌──────────────────────────────────────────────────────────┐
│ 💡 Startdotierung für Jahres-/Quartalsverträge           │
│ HUK Leben (jährlich, fällig 03/2027): bisher Angespartes │
│ liegt auf Allgemein. Vorschlag: **250,52** aus Allgemein │
│ in den Untertopf umbuchen (4 Monate × 62,63).            │
│ Nebenbuch-Saldo ändert sich dadurch NICHT.               │
│ [ Umbuchen ]  [ überspringen ]                           │
└──────────────────────────────────────────────────────────┘
```

Nutzt die vorhandene Topf-Umbuchen-Mechanik des Rücklagen-Reiters — kein neuer Buchungstyp.

### 1.5 Interaktions-Regeln (die den Flow „handy-tauglich" machen)

1. **Eine Entscheidung = ein Tap = sofort geschrieben**, quittiert über den vorhandenen
   `flash()`-Toast („Soll Haushaltskasse → 3.000,00 ✓"). Kein Sammel-Submit: Abbrechbarkeit
   pro Karte ist wichtiger als Transaktionalität über den ganzen Stapel (jede Einzelaktion
   ist für sich konsistent — Config-Wert, Schalter, Umbuchung, Vertrag).
2. **Erledigte Karten kollabieren** zu einer 1-Zeilen-Quittung mit `[rückgängig]`, wo das
   trivial ist (Soll-Wert, Schalter). Nicht-trivial Rückholbares (Umbuchung) verweist auf
   den Rücklagen-Reiter.
3. **„Fertig"-Zustand eines Nebenbuchs** = 0 offene Karten → große grüne Quittungskarte
   `✅ Haushaltskasse abgeglichen` + Button `[ Weiter: Auto (2 offen) → ]`. Der Pfad
   Nebenbuch-für-Nebenbuch entsteht durch diesen einen Button — mehr Wizard braucht es nicht.
4. **Wahrnehmungen werden berechnet, nicht gespeichert.** Jede Karte ist das Ergebnis einer
   Query über den Ist-Zustand (Rate=0? Rest<0? NULL-Unterkat-Summe≠0? …). Gelöst =
   Bedingung verschwunden. Damit gibt es keinen Wahrnehmungs-Store, der mit der Realität
   auseinanderlaufen kann, und der Screen ist nach jedem Import automatisch aktuell.
   Einzige Persistenz: „später entscheiden"-Reihenfolge (Session) und der Zeitstempel des
   letzten vollständigen Abgleichs (`einstellungen`-Key, für den Laufzettel-Kopf).
5. **Kein Auto-Vorschlag wird ohne Tap geschrieben** — Prinzip 3 wörtlich. Auch „Alle 26
   übernehmen" ist ein expliziter Tap mit Zahlenliste davor.

### 1.6 Was bewusst NICHT auf diesen Screen gehört

- **Buchungen zuordnen / Verträge bestätigen** — bleibt auf dem Verträge-Reiter (dort
  existiert das Muster bereits). Der Abgleich verlinkt hin („6 Vorschläge warten → Verträge"),
  dupliziert es aber nicht.
- **Der Rückstellungslauf selbst** — bleibt Action/CLI mit Trockenlauf (#76). Der Abgleich
  bereitet ihn vor (Gate-Zeile im Kopf), löst ihn aber nicht aus, solange der Deploy-Weg
  (#62) nicht steht. Später kann ein `[ Lauf-Vorschau ansehen ]`-Link dazukommen.
- **Forderungs-Nebenbücher** (Jörg/Natalie) — eigenes, noch offenes Thema (Logik-Review L5);
  sie hier zu zeigen würde suggerieren, der Abgleich löse auch das.

---

## Teil 2 — Schiefstellung/Reichweite anzeigen, ohne zu überfrachten

### 2.1 Grundsatz: eine Zahl, ein Format, drei Orte — und nur bei Unterdeckung

Die Reichweite erscheint **ausschließlich, wenn ein Nebenbuch tatsächlich unterdeckt ist**
(`rest_cent < 0`). Nebenbücher im Gleichgewicht zeigen nichts — das ist der ganze Trick
gegen Überfrachtung. Einheitliches Kompakt-Format überall:

```
−171 €/Mon · reicht ~85 Mon        (schiefstellung_erlaubt = TRUE  → gelb/gold, ruhig)
−1.629 €/Mon · reicht ~0 Mon 🛑    (schiefstellung_erlaubt = FALSE → rot, laut)
```

Als wiederverwendbares Jinja-Makro (`reichweite_pill(k)`), gestylt wie die vorhandenen
Pills: `pill schief` (Gold `--hi` auf `--hi-soft`) für gewollte Schiefstellung,
`pill warn` (Rot) für ungewollte. **Gold = „gesteuert", Rot = „handeln"** — dieselbe
Semantik, die die Optik schon hat (Gold markiert im UI „hier bist du/bewusst gesetzt").

**Berechnung ehrlich machen (Logik-Review 4.2):** Reichweite = Bestand ÷ Unterdeckung, aber
die Unterdeckung sollte `max(|rest_cent|, Ø realer Netto-Abfluss 3 Mon)` verwenden, sobald
Ist-Daten da sind — sonst zeigt Füchschen dauerhaft die zu pessimistische Vertrags-Rechnung
(„31 Monate") statt der echten (~85) und Haushaltskasse gar nichts, obwohl sie das lauteste
Problem ist. Tooltip/Langform nennt beide Komponenten.

### 2.2 Die drei Orte

**(1) Verträge-Reiter** (existiert schon in Langform): Die Deckel-Tabelle je Nebenbuch
behält ihre Zeilen; die Bestand/Reichweite-Zeile übernimmt das Pill-Format. Keine Änderung
der Struktur — nur Vereinheitlichung.

**(2) Rücklagen-Reiter** (der Ort, wo Jörg Bestände anschaut): hinter dem Ist-Topf der
Nebenbuch-Zeile dieselbe Pill — nur bei Unterdeckung, sonst nichts:

```
Füchschen    0,00    14.619,98  [−171/Mon · ~85 Mon]   ＋ －
TK         125,00     1.323,72                          ＋ －
```

Eine Pill in einer bestehenden Tabellenzeile, kein neues Layout-Element. Auf dem Handy
(<820px) rutscht sie unter den Betrag (`display:block`), die Tabelle bleibt schmal.

**(3) Übersicht (KPI-Ebene): bewusst KEINE eigene Kachel.** Nur wenn mindestens ein
Nebenbuch **ungewollt** unterdeckt ist (rot), erscheint eine einzeilige `hinweis warnung`-Box
unter den KPIs: „🛑 Haushaltskasse leert sich (−1.629 €/Mon, reicht ~0 Monate) → Abgleich".
Gewollte Schiefstellungen (Füchschen) erscheinen auf der Übersicht **gar nicht** — sie sind
gesteuert und brauchen keine tägliche Aufmerksamkeit. Das ist die Überfrachtungs-Grenze:
**Rot eskaliert bis zur Übersicht, Gold bleibt in Rücklagen/Verträgen/Abgleich.**

### 2.3 Mini-Sketch (Pill-Markup im Stil der bestehenden Tokens)

```html
{% macro reichweite_pill(k) %}
  {% if k.rest_cent < 0 %}
    <span class="pill {{ 'schief' if k.schiefstellung_erlaubt else 'warn' }}"
          title="Unterdeckung {{ (-k.rest_cent)|euro }}/Monat · Bestand {{ k.bestand_cent|euro }}
                 {%- if not k.schiefstellung_erlaubt %} · Schiefstellung NICHT erlaubt — der
                 Rückstellungslauf pausiert dieses Nebenbuch{% endif %}">
      {{ k.rest_cent|euro }}/Mon ·
      {% if k.reichweite_monate is not none %}reicht ~{{ k.reichweite_monate }} Mon{% else %}kein Bestand{% endif %}
      {% if not k.schiefstellung_erlaubt %} 🛑{% endif %}
    </span>
  {% endif %}
{% endmacro %}
```

(`pill.schief`/`pill.warn` existieren bereits in `vertraege.html` — für die Wiederverwendung
in Rücklagen/Übersicht gehören sie nach `base.html` verschoben.)

---

## Teil 3 — Umsetzungsreihenfolge (Vorschlag, minimal-invasiv)

| Schritt | Inhalt | Aufwand |
|---|---|---|
| 1 | `reichweite_pill`-Makro + Pills nach `base.html`; Einbau Rücklagen-Reiter + Übersicht-Warnbox | klein |
| 2 | `/abgleich` Ebene 1 (Laufzettel) — nur Lesen: `queries.vertraege()` + Ø-Ist-Verzehr-Query | klein |
| 3 | Ebene 2 mit den Karten-Typen A (Deckel/Verzehr) und B (Rate-Backfill) — die zwei, die #76 wirklich gaten | mittel |
| 4 | Karten C (Hygiene) und D (Startdotierung) | mittel |
| 5 | Badge in der Nav + `einstellungen`-Zeitstempel „zuletzt abgeglichen" | klein |

Schritte 1–3 reichen, damit der erste echte Rückstellungslauf (09/2026) auf abgeglichener
Basis läuft; 4–5 sind Komfort. Alles nutzt bestehende Endpoints bzw. triviale neue
(`POST /api/abgleich/rate-backfill`, `POST /api/abgleich/startdotierung` als dünne Hüllen um
vorhandene Mechanik) — kein neues Datenmodell außer einem `einstellungen`-Key.

*Read-only-Beratung; nichts hiervon ist gebaut oder deployt. Jörg entscheidet.*
