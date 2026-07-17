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
from collections import defaultdict
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
MIN_ZAHLUNGEN = 3          # darunter ist kein Rhythmus belegbar
BEENDET_NACH_RHYTHMEN = 2  # letzte Zahlung > 2 Rhythmen her -> beendet
# Ein Vertrag zahlt immer ungefähr dasselbe. Alltagskäufe (Lebensmittel, Drogerie)
# passieren zwar auch "monatlich", schwanken aber stark -> das ist der Unterschied.
# Maß: mediane absolute Abweichung / Median. 0 = immer derselbe Betrag.
MAX_STREUUNG = 0.15
# Ein Vertrag bucht EINMAL pro Rhythmus ab. Tanken ist der Grenzfall, der die
# Streuungsprüfung überlebt (immer volltanken = ähnlicher Betrag, jeden Monat) —
# aber 3x im Monat an derselben Tankstelle ist kein Abo. 1.4 lässt Verschiebungen
# um den Monatswechsel (28./1.) durch, ohne Alltagskäufe zu erlauben.
MAX_ZAHLUNGEN_JE_PERIODE = 1.4


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


def _streuung(betraege: list[int]) -> float:
    """Wie stabil ist der Betrag? (mediane absolute Abweichung / Median)

    Unterscheidet **Vertrag** von **Alltagskauf** — und zwar an den **Einzelbeträgen**,
    nicht an der Monatssumme. Das ist der springende Punkt:

      OGS-Beitrag:  235,00 · 235,00 · 235,00 …        -> Streuung ~0    -> Vertrag
      dm-Drogerie:   12,34 ·  45,67 ·   8,90 …        -> Streuung hoch  -> Alltagskauf

    Die *Monatssumme* ist bei dm nämlich durchaus stabil (~270 €/Monat) — wer nur die
    betrachtet, hält die Drogerie für einen Vertrag und legt dafür Rücklagen an.

    Median-basiert (nicht Standardabweichung), damit einzelne Ausreißer wie
    Nachzahlungen oder Wechselmonate das Urteil nicht kippen.
    """
    med = statistics.median(betraege)
    if med == 0:
        return 1.0
    return statistics.median([abs(b - med) for b in betraege]) / abs(med)


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
          AND b.betrag_cent < 0
          AND b.unterkategorie_id IS NOT NULL
          AND COALESCE(TRIM(b.empfaenger), '') <> ''
        ORDER BY b.datum_wert
        """
    )
    zeilen = cur.fetchall()
    stabil = _stabile_nummern(zeilen)

    gruppen: dict[tuple, list] = defaultdict(list)
    for empf, zweck, datum, betrag, ukat_id, ukat, kat in zeilen:
        key = empf.strip()[:60]
        schluessel = (key, _zweck_kern(zweck, stabil.get(key, frozenset())), ukat_id)
        gruppen[schluessel].append((datum, abs(betrag), ukat, kat))

    kandidaten = []
    for (empf, kern, ukat_id), zahlungen in gruppen.items():
        if len(zahlungen) < MIN_ZAHLUNGEN:
            continue
        # Rhythmus über MONATSSUMMEN, nicht über Einzelzahlungen (s. _monatssummen).
        monate = _monatssummen(zahlungen)
        if len(monate) < MIN_ZAHLUNGEN:
            continue
        monats_daten = [m[0] for m in monate]
        abstaende = [(monats_daten[i + 1] - monats_daten[i]).days
                     for i in range(len(monats_daten) - 1)]
        rhythmus, med_tage = _rhythmus(abstaende)
        if rhythmus == "unregelmaessig":
            continue  # kein Vertrag -> keine Rückstellung

        # Entscheidend: streuen die EINZELBETRÄGE? (s. _streuung)
        streuung = _streuung([z[1] for z in zahlungen])
        if streuung > MAX_STREUUNG:
            continue  # Alltagskauf, kein Vertrag (Lebensmittel, Drogerie)

        # Bucht die Gruppe wirklich nur einmal je Rhythmus ab? (s. MAX_ZAHLUNGEN_JE_PERIODE)
        perioden = max(len(monate) / MONATE_JE_RHYTHMUS.get(rhythmus, 1), 1)
        if len(zahlungen) / perioden > MAX_ZAHLUNGEN_JE_PERIODE:
            continue  # mehrfach je Periode -> Alltagskauf (Tanken), kein Vertrag

        # Rate/Bestand rechnen aber auf der MONATSSUMME — zwei Kinder an einem Träger
        # sind ein Monatsbetrag.
        median_cent = int(statistics.median([m[1] for m in monate]))
        letzte = max(z[0] for z in zahlungen)   # echtes Datum, nicht Monatsanfang
        tage_her = (stichtag - letzte).days
        beendet = tage_her > (med_tage or 30) * BEENDET_NACH_RHYTHMEN
        naechste = letzte + timedelta(days=med_tage or 30)

        kandidaten.append(
            {
                "name": empf[:40],
                "beschreibung": kern[:60] or None,
                "unterkategorie_id": ukat_id,
                "unterkategorie": zahlungen[0][2],
                "kategorie": zahlungen[0][3],
                "muster_empfaenger": empf[:60],
                "muster_zweck": kern[:60] or None,
                "rhythmus": rhythmus,
                "betrag_median_cent": median_cent,
                "letzte_zahlung": letzte,
                "naechste_faellig": naechste,
                "status": "beendet" if beendet else "erkannt",
                "zahlungen": len(zahlungen),
                "monate": len(monate),
                "streuung": streuung,
                "monatsrate_cent": monatsrate(median_cent, rhythmus),
            }
        )
    _mache_namen_eindeutig(kandidaten)
    kandidaten.sort(key=lambda k: (k["kategorie"] or "", -k["monatsrate_cent"]))
    return kandidaten


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


def monatsrate(median_cent: int, rhythmus: str) -> int:
    """Jahresbetrag / 12 — die Rate, die je Monat zurückgelegt werden muss."""
    monate = MONATE_JE_RHYTHMUS.get(rhythmus)
    if not monate:
        return 0
    return round(median_cent * (12 / monate) / 12)


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
            # Vom User bestätigte/ignorierte Verträge bleiben unangetastet;
            # nur die gemessenen Werte werden aktualisiert.
            cur.execute(
                """UPDATE vertraege
                      SET betrag_median_cent = %s, rhythmus = %s, letzte_zahlung = %s,
                          naechste_faellig = %s,
                          status = CASE WHEN status = 'erkannt' THEN %s ELSE status END
                    WHERE id = %s""",
                (k["betrag_median_cent"], k["rhythmus"], k["letzte_zahlung"],
                 k["naechste_faellig"], k["status"], treffer[0]),
            )
            continue
        cur.execute(
            """INSERT INTO vertraege
                 (name, beschreibung, unterkategorie_id, muster_empfaenger, muster_zweck,
                  rhythmus, betrag_median_cent, letzte_zahlung, naechste_faellig, status, quelle)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'auto')""",
            (k["name"], k["beschreibung"], k["unterkategorie_id"], k["muster_empfaenger"],
             k["muster_zweck"], k["rhythmus"], k["betrag_median_cent"],
             k["letzte_zahlung"], k["naechste_faellig"], k["status"]),
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
        print(f"    {k['name'][:32]:<32} {k['rhythmus']:<14} "
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
