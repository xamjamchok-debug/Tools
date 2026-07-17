"""Vertragserkennung (#75) — Rhythmus messen statt historische Werte aussortieren.

Hintergrund (User 2026-07-17): „Das hattest du mal gerechnet, indem du die historischen
Werte einfach aussortierst. Das finde ich blödsinnig. Das kann ich aber auch nicht alles
manuell machen." Deshalb wird hier **nichts** aussortiert:

  * **Rhythmus** = Median der Abstände zwischen den Zahlungen (monatlich/quartalsweise/…).
  * **Betrag**   = **Median** der Zahlungen — gegen Ausreißer immun, damit fallen
    Wechselmonate (Schlussrechnung/Anlauf) von selbst raus, ohne dass jemand entscheidet,
    was ein Ausreißer ist.
  * **beendet**  = letzte Zahlung liegt mehr als 2 Rhythmen zurück. Alte Anbieter
    verschwinden dadurch **automatisch** (Strom: MAINGAU → Naturwerke → Tibber), bleiben
    aber als Historie sichtbar. Eine Regel statt Handarbeit.
  * **kein Rhythmus erkennbar** → kein Vertrag, keine Rückstellung (Judo-Extras, Arzt).

Gruppiert wird über **Empfänger + Verwendungszweck-Kern**, nicht nur über den Empfänger:
An „Gemeinde Wachtberg" hängen vier Zwecke in drei Nebenbüchern (OGS, Grundsteuer,
Abwasser, Pacht), hinter „PayPal" stecken 66 Händler.

Der Lauf **schreibt keine Soll-Werte** — er schlägt nur Verträge vor (Status 'erkannt').
Solls ändert allein der Rückstellungslauf, nach Bestätigung (User-Entscheid F).

    python -m haushaltskasse.workflows.vertraege            # dry-run
    python -m haushaltskasse.workflows.vertraege --write    # Vorschläge speichern
"""
from __future__ import annotations

import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

from ..storage.db import connect

# Rhythmus-Erkennung: erwarteter Abstand in Tagen -> Toleranz.
RHYTHMEN: list[tuple[str, int, int]] = [
    # (name, tage_soll, toleranz)
    ("monatlich", 30, 6),
    ("quartalsweise", 91, 15),
    ("halbjaehrlich", 182, 25),
    ("jaehrlich", 365, 40),
]
MONATE_JE_RHYTHMUS = {
    "monatlich": 1,
    "quartalsweise": 3,
    "halbjaehrlich": 6,
    "jaehrlich": 12,
}
MIN_ZAHLUNGEN = 2          # quartalsweise hat im Halbjahr nur 2 Zahlungen
BEENDET_NACH_RHYTHMEN = 4  # erst > 4 Rhythmen ohne Zahlung -> beendet (Kredite laufen weiter,
                           # auch wenn der Import mal 2 Monate hinterherhängt)
KERN_TOLERANZ = 0.15       # Zahlungen bis ±15 % vom Kern-Betrag gehören zum selben Vertrag
MIN_KERN_ANTEIL = 0.25     # der Kern-Betrag muss ≥25 % aller Zahlungen stellen — sonst ist es
                           # ein Alltagskauf (Lebensmittel: kein Betrag wiederholt sich dominant)


def _zweck_kern(zweck: str | None, stabile_nummern: frozenset[str] = frozenset()) -> str:
    """Verwendungszweck auf seinen stabilen Kern reduzieren.

    Heikel: Manche Nummern **wechseln** je Buchung (Transaktions-/Bestellnummern) und
    müssen weg, sonst wird jede Zahlung eine eigene Gruppe. Andere sind **stabile
    Vertragsschlüssel** und müssen bleiben, sonst verschmelzen verschiedene Verträge:

      "1050392172454/PP.4645.PP/. EasyPark GmbH …"        -> Nummer wechselt   -> raus
      "KASSENZEICHEN 741007431703/ ELTERNBEITRAEGE OGS"   -> Kassenzeichen     -> BLEIBT
      "KASSENZEICHEN 741007435928/ ELTERNBEITRAEGE OGS"      (zweites Kind!)

    Ohne diese Unterscheidung fielen beide OGS-Beiträge in eine Gruppe, der Rhythmus
    wäre "2x im Monat" und würde als unregelmäßig verworfen.

    `stabile_nummern` wird vorab je Empfänger ermittelt: Eine Nummer, die bei mehreren
    Buchungen desselben Empfängers **wiederkehrt**, ist ein Vertragsschlüssel.
    """
    if not zweck:
        return ""
    t = zweck.lower()
    # PayPal: der echte Händler steht hinter dem PP-Block -> der ist der Kern.
    m = re.search(r"pp\.\d+\.pp/\.\s*([^,]+?),\s*(?:ihr einkauf|artikel)", t)
    if m:
        return m.group(1).strip()
    t = re.sub(r"\d{1,2}\.\d{1,2}\.\d{2,4}", " ", t)  # Datumsangaben raus
    t = re.sub(r"\d+[,.]\d{2}\s*eur", " ", t)         # Beträge raus
    # Lange Nummern: stabile behalten (als Schlüssel), wechselnde entfernen.
    def _nummer(treffer: re.Match) -> str:
        n = treffer.group(0)
        return f" schluessel{n} " if n in stabile_nummern else " "
    t = re.sub(r"\d{4,}", _nummer, t)
    t = re.sub(r"[^a-zäöüß0-9 ]+", " ", t)
    return " ".join(t.split())[:60]


def _stabile_nummern(zeilen: list[tuple]) -> dict[str, frozenset[str]]:
    """Je Empfänger: welche langen Nummern kehren wieder? -> Vertragsschlüssel."""
    zaehler: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for empf, zweck, *_ in zeilen:
        if not empf or not zweck:
            continue
        key = empf.strip()[:60]
        for n in set(re.findall(r"\d{4,}", zweck.lower())):
            zaehler[key][n] += 1
    return {
        empf: frozenset(n for n, c in nums.items() if c >= 2)
        for empf, nums in zaehler.items()
    }


def _monatssummen(zahlungen: list[tuple]) -> list[tuple[date, int]]:
    """Zahlungen je Monat aufsummieren.

    Zwei Beiträge im selben Monat (z. B. Essensgeld für zwei Kinder an einen Träger)
    sind für die Rückstellung EIN Monatsbetrag — nicht zwei Zahlungen im 15-Tage-Takt.
    Ohne diese Aggregation würde der Rhythmus als unregelmäßig verworfen.
    """
    je_monat: dict[tuple[int, int], int] = defaultdict(int)
    for datum, betrag, *_ in zahlungen:
        je_monat[(datum.year, datum.month)] += betrag
    return [(date(j, m, 1), summe) for (j, m), summe in sorted(je_monat.items())]


def _kern_zahlungen(zahlungen: list[tuple]) -> list[tuple]:
    """Filtert die Zahlungen auf den **wiederkehrenden Kern-Betrag** herunter.

    Der springende Punkt bei echten Verträgen mit „Rauschen":
      Judo-Club:   22 · 22 · 22 · 47(Prüfung) · 22 · 152(Lehrgang) · 22 …
                   -> Kern-Betrag 22 kehrt wieder, die Extras sind Beiwerk.
      dm-Drogerie: 12 · 46 · 9 · 33 · 7 …
                   -> kein Betrag dominiert -> kein Vertrag.

    Vorgehen: auf ganze Euro runden, häufigsten Wert (Modus) nehmen, alle Zahlungen
    im Fenster ±15 % zurückgeben. Toleranz fängt Kursschwankungen (Claude/Adobe in USD)
    und Rundungen. So überleben Abos mit leicht schwankendem Betrag, während
    Lebensmittel/Tanken (kein dominanter Wert) herausfallen.
    """
    if not zahlungen:
        return []
    euros = [round(z[1] / 100) for z in zahlungen if z[1] > 0]
    if not euros:
        return []
    modus = Counter(euros).most_common(1)[0][0]
    if modus == 0:
        return []
    fenster = max(modus * KERN_TOLERANZ, 1.0)
    return [z for z in zahlungen if abs(z[1] / 100 - modus) <= fenster]


def _rhythmus(abstaende: list[int]) -> tuple[str, int | None]:
    """Median der Abstände -> Rhythmus-Name + Tage. Unklar -> 'unregelmaessig'."""
    if not abstaende:
        return "unregelmaessig", None
    med = int(statistics.median(abstaende))
    for name, soll, tol in RHYTHMEN:
        if abs(med - soll) <= tol:
            return name, med
    return "unregelmaessig", med


def erkenne(cur, stichtag: date | None = None) -> list[dict]:
    """Liefert Vertrags-Kandidaten. Schreibt nichts."""
    stichtag = stichtag or date.today()
    cur.execute(
        """
        SELECT b.empfaenger, b.verwendungszweck, b.datum_wert, b.betrag_cent,
               b.unterkategorie_id, u.name, k.name
        FROM buchungen b
        LEFT JOIN unterkategorien u ON u.id = b.unterkategorie_id
        LEFT JOIN kategorien k      ON k.id = b.kategorie_id
        WHERE b.buchungsart = 'real'
          AND b.spiegel_von_id IS NULL
          AND b.betrag_cent <> 0
          AND b.unterkategorie_id IS NOT NULL
          AND COALESCE(TRIM(b.empfaenger), '') <> ''
        ORDER BY b.datum_wert
        """
    )
    zeilen = cur.fetchall()
    stabil = _stabile_nummern(zeilen)

    # Eingang und Ausgang getrennt gruppieren: das Kindergeld (+) darf nicht mit einer
    # gleichnamigen Ausgabe (−) verschmelzen. Die Richtung ist Teil der Identität.
    gruppen: dict[tuple, list] = defaultdict(list)
    for empf, zweck, datum, betrag, ukat_id, ukat, kat in zeilen:
        key = empf.strip()[:60]
        richtung = "eingang" if betrag > 0 else "ausgang"
        schluessel = (key, _zweck_kern(zweck, stabil.get(key, frozenset())), ukat_id, richtung)
        gruppen[schluessel].append((datum, abs(betrag), ukat, kat))

    kandidaten = []
    for (empf, kern, ukat_id, richtung), zahlungen in gruppen.items():
        if len(zahlungen) < MIN_ZAHLUNGEN:
            continue

        # 1. Kern-Betrag herausschälen (Extras/Rauschen ignorieren, s. _kern_zahlungen).
        kern_zahlungen = _kern_zahlungen(zahlungen)
        if len(kern_zahlungen) < MIN_ZAHLUNGEN:
            continue
        if len(kern_zahlungen) / len(zahlungen) < MIN_KERN_ANTEIL:
            continue  # kein dominanter Betrag -> Alltagskauf (Lebensmittel/Tanken)

        # 2. Rhythmus über die MONATSSUMMEN des Kerns — zwei Kinder an einem Träger
        #    im selben Monat sind EIN Monatsbetrag (Essensgeld 2×60 -> 120/Monat).
        monate = _monatssummen(kern_zahlungen)
        if len(monate) < MIN_ZAHLUNGEN:
            continue
        monats_daten = [m[0] for m in monate]
        abstaende = [(monats_daten[i + 1] - monats_daten[i]).days
                     for i in range(len(monats_daten) - 1)]
        rhythmus, med_tage = _rhythmus(abstaende)
        if rhythmus == "unregelmaessig":
            continue  # kein erkennbarer Takt -> keine Rückstellung

        median_cent = int(statistics.median([m[1] for m in monate]))
        letzte = max(z[0] for z in kern_zahlungen)
        erste = min(z[0] for z in kern_zahlungen)
        tage_her = (stichtag - letzte).days
        beendet = tage_her > (med_tage or 30) * BEENDET_NACH_RHYTHMEN
        naechste = letzte + timedelta(days=med_tage or 30)

        rate = _monatsrate(zahlungen, letzte, rhythmus, median_cent)

        kandidaten.append(
            {
                "name": empf[:40],
                "beschreibung": kern[:60] or None,
                "unterkategorie_id": ukat_id,
                "unterkategorie": zahlungen[0][2],
                "kategorie": zahlungen[0][3],
                "muster_empfaenger": empf[:60],
                "muster_zweck": kern[:60] or None,
                "richtung": richtung,
                "rhythmus": rhythmus,
                "betrag_median_cent": median_cent,
                "letzte_zahlung": letzte,
                "erste_zahlung": erste,
                "naechste_faellig": naechste,
                "status": "beendet" if beendet else "erkannt",
                "zahlungen": len(zahlungen),
                "kern_zahlungen": len(kern_zahlungen),
                "monate": len(monate),
                "med_tage": med_tage or 30,
                "monatsrate_cent": rate,
            }
        )
    kandidaten = _fuehre_fortsetzungen_zusammen(kandidaten, stichtag)
    _mache_namen_eindeutig(kandidaten)
    kandidaten.sort(key=lambda k: (k["kategorie"] or "", -k["monatsrate_cent"]))
    return kandidaten


def _fuehre_fortsetzungen_zusammen(kandidaten: list[dict], stichtag: date) -> list[dict]:
    """Denselben Vertrag zusammenführen, wenn der Verwendungszweck mittendrin wechselt.

    Ab Juni ändert die Bank bei manchen Buchungen den Zweck-Text (Kindergeld, der große
    Deutsche-Bank-Kredit) — dadurch entstünden zwei Verträge à 777 bzw. à 1542, die sich
    beim Bestätigen **doppeln** würden. Zusammengeführt wird nur, wenn: gleicher
    Empfänger + Topf + Richtung, Betrag ±10 %, und die Zeiträume **nicht überlappen**
    (der eine läuft aus, wo der andere beginnt). Zwei parallele Tranchen (Kredit 299 UND
    305, beide Jan–Mai) überlappen -> bleiben getrennt.
    """
    # Empfänger-Anfang statt Volltext: Kindergeld verliert ab Juni den Zusatz „Fuchskaule 27",
    # ist aber derselbe Zahler. 12 Zeichen trennen „MAINGAU Ener" von „Tibber Deuts" (bleiben
    # getrennt), fassen aber „Hemmerling, " und „Deutsche Ban" je zusammen.
    def _praefix(k):
        return k["muster_empfaenger"][:12].lower()

    kandidaten.sort(key=lambda k: (_praefix(k), k["unterkategorie_id"],
                                   k["richtung"], k["erste_zahlung"]))
    ergebnis: list[dict] = []
    for k in kandidaten:
        ziel = None
        for e in ergebnis:
            if (_praefix(e) == _praefix(k)
                    and e["unterkategorie_id"] == k["unterkategorie_id"]
                    and e["richtung"] == k["richtung"]
                    and abs(e["betrag_median_cent"] - k["betrag_median_cent"])
                        <= 0.10 * max(e["betrag_median_cent"], k["betrag_median_cent"])
                    and k["erste_zahlung"] > e["letzte_zahlung"]):   # zeitlich anschließend
                ziel = e
                break
        if ziel is None:
            ergebnis.append(k)
            continue
        # k ist die Fortsetzung von ziel -> Kennzahlen des jüngeren Laufs übernehmen.
        ziel["zahlungen"] += k["zahlungen"]
        ziel["kern_zahlungen"] += k["kern_zahlungen"]
        ziel["letzte_zahlung"] = k["letzte_zahlung"]
        ziel["naechste_faellig"] = k["naechste_faellig"]
        ziel["muster_zweck"] = k["muster_zweck"]   # der aktuelle Zweck-Text
        ziel["monatsrate_cent"] = k["monatsrate_cent"]   # Rate aus dem jüngeren Fenster
        tage_her = (stichtag - ziel["letzte_zahlung"]).days
        ziel["status"] = "beendet" if tage_her > ziel["med_tage"] * BEENDET_NACH_RHYTHMEN else "erkannt"
    return ergebnis


def _mache_namen_eindeutig(kandidaten: list[dict]) -> None:
    """Gleicher Empfänger + gleicher Untertopf -> Betrag an den Namen hängen.

    Sonst stünden zwei ununterscheidbare "Gemeinde Wachtberg" untereinander (die beiden
    OGS-Beiträge für zwei Kinder). Der Betrag ist das, woran der User sie erkennt.
    Nur ein Label — er kann es auf der Seite überschreiben.
    """
    zaehler: dict[tuple[str, int], int] = defaultdict(int)
    for k in kandidaten:
        zaehler[(k["name"], k["unterkategorie_id"])] += 1
    for k in kandidaten:
        if zaehler[(k["name"], k["unterkategorie_id"])] > 1:
            k["name"] = f"{k['name'][:30]} ({k['betrag_median_cent'] / 100:.2f} €)"


def _monatsrate(zahlungen: list[tuple], letzte: date, rhythmus: str, median_cent: int) -> int:
    """Monatliche Rückstellung — je nach Rhythmus verschieden hergeleitet.

    **monatlich:** Gesamtabfluss der letzten ~6 Monate ÷ Anzahl dieser Monate. Über ALLE
    Zahlungen (inkl. Sonderzahlungen), nicht nur den Kern — Jörg will die tatsächliche
    Belastung zurücklegen. Judo hat seit 02/2026 drei Kinder à 22 = 66/Monat plus
    Sonderzahlungen -> ~74. Das aktuelle Fenster ignoriert die alte Ein-Kind-Zeit.

    **quartalsweise/halb-/jährlich:** ein sauberer Einzelbetrag je Fälligkeit ÷ Perioden-
    monate (Grundsteuer 234 € pro Quartal -> 78 €/Monat). Hier führt „Summe ÷ Monate zu
    einem Fensterfehler, weil der Zufall entscheidet, wie viele Fälligkeiten ins Fenster
    fallen — deshalb rhythmusbasiert.
    """
    monate_je = MONATE_JE_RHYTHMUS.get(rhythmus)
    if not monate_je:
        return 0
    if monate_je > 1:                        # quartalsweise und seltener
        return round(median_cent / monate_je)
    grenze = letzte - timedelta(days=185)    # monatlich: echtes 6-Monats-Fenster
    fenster = [z for z in zahlungen if z[0] > grenze]
    if not fenster:
        return median_cent
    summe = sum(z[1] for z in fenster)
    monate = len({(z[0].year, z[0].month) for z in fenster})
    return round(summe / max(monate, 1))


def speichere(cur, kandidaten: list[dict]) -> int:
    """Vorschläge anlegen. Bestehende (bestaetigt/ignoriert) NICHT überschreiben.

    Wiedererkannt wird über das **Muster**, nicht über den Namen: Die beiden
    OGS-Beiträge heißen beide "Gemeinde Wachtberg" und liegen im selben Untertopf —
    nur das Kassenzeichen im Zweck trennt sie (zwei Kinder). Über den Namen gesucht,
    überschrieb das zweite Kind das erste.
    """
    neu = 0
    for k in kandidaten:
        cur.execute(
            """SELECT id, status FROM vertraege
                WHERE muster_empfaenger = %s
                  AND COALESCE(muster_zweck, '') = COALESCE(%s, '')
                  AND unterkategorie_id = %s""",
            (k["muster_empfaenger"], k["muster_zweck"], k["unterkategorie_id"]),
        )
        treffer = cur.fetchone()
        if treffer:
            # Vom User bestätigte/ignorierte Verträge bleiben unangetastet; die Rate wird
            # nur bei 'erkannt' überschrieben (bestätigte behalten Jörgs manuellen Wert).
            cur.execute(
                """UPDATE vertraege
                      SET betrag_median_cent = %s, rhythmus = %s, letzte_zahlung = %s,
                          naechste_faellig = %s,
                          monatsrate_cent = CASE WHEN status = 'erkannt' THEN %s ELSE monatsrate_cent END,
                          status = CASE WHEN status = 'erkannt' THEN %s ELSE status END
                    WHERE id = %s""",
                (k["betrag_median_cent"], k["rhythmus"], k["letzte_zahlung"],
                 k["naechste_faellig"], k["monatsrate_cent"], k["status"], treffer[0]),
            )
            continue
        cur.execute(
            """INSERT INTO vertraege
                 (name, beschreibung, unterkategorie_id, muster_empfaenger, muster_zweck,
                  richtung, rhythmus, betrag_median_cent, monatsrate_cent, letzte_zahlung,
                  naechste_faellig, status, quelle)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'auto')""",
            (k["name"], k["beschreibung"], k["unterkategorie_id"], k["muster_empfaenger"],
             k["muster_zweck"], k["richtung"], k["rhythmus"], k["betrag_median_cent"],
             k["monatsrate_cent"], k["letzte_zahlung"], k["naechste_faellig"], k["status"]),
        )
        neu += 1
    return neu


def main() -> None:
    write = "--write" in sys.argv
    con = connect()
    cur = con.cursor()
    kandidaten = erkenne(cur)

    print(f"[vertraege] {len(kandidaten)} Vertrags-Kandidaten erkannt:\n")
    kat = None
    for k in kandidaten:
        if k["kategorie"] != kat:
            kat = k["kategorie"]
            print(f"  ### {kat}")
        marker = " [BEENDET]" if k["status"] == "beendet" else ""
        pfeil = "＋ EIN" if k["richtung"] == "eingang" else "－ aus"
        print(f"    {k['name'][:32]:<32} {pfeil} {k['rhythmus']:<14} "
              f"{k['betrag_median_cent']/100:>9.2f} € -> Rate {k['monatsrate_cent']/100:>8.2f} €/Mon"
              f"  ({k['zahlungen']}x, zuletzt {k['letzte_zahlung']}){marker}")
        print(f"        -> {k['kategorie']} / {k['unterkategorie']}")

    if write:
        neu = speichere(cur, kandidaten)
        con.commit()
        print(f"\n  GESPEICHERT: {neu} neue Vorschläge (Status 'erkannt'), Rest aktualisiert.")
        print("  Bestätigte/ignorierte Verträge wurden nicht überschrieben.")
    else:
        print("\n  DRY-RUN — nichts geschrieben. Mit  --write  speichern.")
    con.close()


if __name__ == "__main__":
    main()
