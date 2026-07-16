"""Backlog #28 / #R6: den Sammel-Topf „Allgemein" je Nebenbuch auf die sprechenden
Unterkategorie-Töpfe verteilen.

Bei der Migration (`allgemein_toepfe.py`) landeten alle kategorie-weiten Zuführungen im
Auffang-Topf „Allgemein". Dieses Skript liest je Nebenbuch den aktuellen Allgemein-Stand
und verteilt ihn nach den %-Anteilen aus `docs/untertopf-verteilung-vorschlag.md` auf die
Ziel-Unterkategorien — als **netto-neutrale Umbuchung** (Allgemein −Anteil / Untertopf +Anteil,
`buchungsart='ruecklage'`, `quelle_import='verteilung'`). Der Kategorie-Topf bleibt also gleich,
nur feiner aufgeschlüsselt.

Eigenschaften:
  * **Trockenlauf per Default** — zeigt je Nebenbuch, was verteilt würde. Erst `--write` schreibt.
  * **Idempotent**: ist für eine Kategorie schon eine Verteilung gebucht (`quelle_import='verteilung'`),
    wird sie übersprungen. Ein zweiter Lauf ist ein No-Op.
  * **Cent-genau**: die Anteile werden per Largest-Remainder gerundet, sodass Σ Verteilung == Allgemein-Stand
    (auch bei negativem Stand). Der Rest-Cent geht an den größten Anteil.
  * **`--soll`** (optional): setzt zusätzlich das monatliche Soll je Untertopf = Kategorie-Soll × Anteil
    (speist #39). Ohne die Flag bleiben die Soll-Werte unangetastet.

Die %-Anteile unten sind ein begründeter Startpunkt aus der Excel-Historie — **im Trockenlauf
prüfen und ggf. hier justieren**, bevor mit `--write` gebucht wird. Offene Punkte (mit dem User
noch zu klären, s. Backlog #28):
  * „Urlaub" ist reisebasiert (ZIEL: nur „Urlaub allgemein") → hier bewusst NICHT verteilt.
  * „Garten & Außenanlage" liegt in der Live-Struktur unter „Inst" (nicht Nebenkosten) → hier so.
  * Sport: fifi/Robbie noch offen — ggf. eigener Anteil.

    python -m haushaltskasse.workflows.allgemein_verteilen                 # Trockenlauf
    python -m haushaltskasse.workflows.allgemein_verteilen --write         # buchen
    python -m haushaltskasse.workflows.allgemein_verteilen --write --soll  # + Soll setzen
"""
from __future__ import annotations

import argparse
import sys

from ..storage.db import connect

REST_NAME = "Allgemein"
QUELLE = "verteilung"

# ---------------------------------------------------------------------------
# %-Anteile je Nebenbuch. Schlüssel = Kategorie-Name (wie live nach #50),
# Werte = Liste (Unterkategorie-Name, Anteil in %). Summe je Kategorie = 100.
# Fehlende Ziel-Unterkategorien werden angelegt. „Urlaub" fehlt bewusst (reisebasiert).
# ---------------------------------------------------------------------------
VERTEILUNG: dict[str, list[tuple[str, float]]] = {
    "Auto": [
        ("Tanken", 45), ("Reparatur & Werkstatt", 25), ("KFZ-Steuer", 15),
        ("Finanzierung/Leasing", 10), ("Zweirad", 5),
    ],
    "Vers": [
        ("KFZ-Versicherung", 40), ("Leben/BU (RLV)", 25), ("Haftpflicht", 12),
        ("Hausrat", 10), ("Gebäude", 8), ("Rechtsschutz", 5),
    ],
    "Nebenkosten": [
        ("Wasser/Abwasser", 37), ("Strom", 32), ("Grundsteuer", 16),
        ("Müll", 10), ("Schornsteinfeger", 5),
    ],
    "Sport": [
        ("Fitnessstudio", 45), ("Verein/Mitgliedschaft", 30),
        ("Kurse & Training", 20), ("Ausrüstung", 5),
    ],
    "Füchschen": [
        ("Betreuung (OGS/Kita)", 45), ("Schulbedarf", 20),
        ("Ausstattung & Anschaffung", 15), ("Kindergarten", 15), ("Freizeit", 5),
    ],
    "Telefon": [
        ("Mobilfunk & Internet", 45), ("Streaming & Software", 30),
        ("Rundfunkbeitrag", 10), ("Zeitung/Medien", 10), ("sonstige Abos", 5),
    ],
    "TK": [
        ("Private KV (DKV)", 70), ("Krankenkasse (TK)", 12),
        ("Arzt & Zahnarzt", 10), ("Apotheke", 8),
    ],
    "Kredit": [
        ("Immobilienkredit (Deutsche Bank)", 90), ("KfW-Darlehen", 10),
    ],
    "Inst": [
        ("Handwerker", 43), ("PV/Solar", 19), ("Möbel & Einrichtung", 14),
        ("Baumaterial", 14), ("Garten & Außenanlage", 5), ("sonstige Anschaffung", 5),
    ],
    "Haushaltskasse": [
        ("Lebensmittel", 45), ("Amazon/Konsum", 20), ("Auswärts essen", 15),
        ("Drogerie", 12), ("Bäcker", 5), ("Bargeld", 3),
    ],
}


def _verteile_cent(stand: int, anteile: list[float]) -> list[int]:
    """Largest-Remainder-Rundung: verteilt `stand` (Cent, auch negativ) auf die Anteile,
    sodass die Summe exakt `stand` ergibt. Rest-Cent gehen an die größten Bruchteile."""
    gesamt = sum(anteile)
    roh = [stand * a / gesamt for a in anteile]
    basis = [int(x) for x in roh]                      # Richtung 0 abgeschnitten
    rest = stand - sum(basis)                          # noch zu verteilende Cent (Vorzeichen von stand)
    schritt = 1 if rest >= 0 else -1
    # Indizes nach größtem Rundungsrest sortieren (bei negativem Stand kleinster zuerst)
    ordnung = sorted(range(len(anteile)), key=lambda i: roh[i] - basis[i], reverse=(rest >= 0))
    for k in range(abs(rest)):
        basis[ordnung[k % len(basis)]] += schritt
    return basis


def _ukat_id(cur, kid: int, name: str, write: bool) -> int | None:
    cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s", (kid, name))
    row = cur.fetchone()
    if row:
        return row[0]
    if not write:
        return None                                    # im Trockenlauf nicht anlegen
    cur.execute("""INSERT INTO unterkategorien (kategorie_id, name, quelle)
                   VALUES (%s,%s,'manuell')
                   ON CONFLICT (kategorie_id, name) DO NOTHING""", (kid, name))
    cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s", (kid, name))
    return cur.fetchone()[0]


def _buche_umbuchung(cur, kid: int, allgemein_uid: int, ziel_uid: int, betrag: int) -> None:
    """Netto-neutrale Umbuchung Allgemein → Zieltopf (zwei ruecklage-Zeilen)."""
    for uid, cent in ((ziel_uid, betrag), (allgemein_uid, -betrag)):
        cur.execute("""INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent,
                       kategorie_id, unterkategorie_id, quelle_import, bemerkung)
                       VALUES ('ruecklage', CURRENT_DATE, %s, %s, %s, %s,
                               'Verteilung Allgemein-Topf (#28)')""",
                    (cent, kid, uid, QUELLE))


def verteile(conn, write: bool, soll: bool) -> None:
    with conn.cursor() as cur:
        for katname, dist in VERTEILUNG.items():
            cur.execute("SELECT id, monatliche_ruecklage_cent FROM kategorien WHERE name=%s", (katname,))
            row = cur.fetchone()
            if not row:
                print(f"  {katname:<16} — Kategorie fehlt, übersprungen")
                continue
            kid, kat_soll = row[0], row[1] or 0

            # schon verteilt? -> idempotent überspringen
            cur.execute("SELECT COUNT(*) FROM buchungen WHERE kategorie_id=%s AND quelle_import=%s",
                        (kid, QUELLE))
            if cur.fetchone()[0]:
                print(f"  {katname:<16} — bereits verteilt, übersprungen")
                continue

            allgemein_uid = _ukat_id(cur, kid, REST_NAME, write)
            if allgemein_uid is None:
                print(f"  {katname:<16} — kein Allgemein-Topf, übersprungen")
                continue
            cur.execute("""SELECT COALESCE(SUM(betrag_cent),0) FROM buchungen
                           WHERE buchungsart='ruecklage' AND unterkategorie_id=%s""", (allgemein_uid,))
            stand = int(cur.fetchone()[0])   # SUM(bigint) kommt als Decimal zurück
            if stand == 0:
                print(f"  {katname:<16} — Allgemein-Stand 0,00 €, nichts zu verteilen")
                continue

            namen = [n for n, _ in dist]
            betraege = _verteile_cent(stand, [a for _, a in dist])
            print(f"  {katname:<16} — Allgemein {stand/100:>11,.2f} € → {len(dist)} Töpfe:")
            for (name, pct), cent in zip(dist, betraege):
                ziel_uid = _ukat_id(cur, kid, name, write)
                marke = "" if ziel_uid else "  (neu)"
                print(f"      {name:<30} {pct:>4.0f}%  {cent/100:>11,.2f} €{marke}")
                if write:
                    _buche_umbuchung(cur, kid, allgemein_uid, ziel_uid, cent)
                    if soll and kat_soll:
                        anteil_soll = round(kat_soll * pct / sum(a for _, a in dist))
                        cur.execute("UPDATE unterkategorien SET monatliche_ruecklage_cent=%s WHERE id=%s",
                                    (anteil_soll, ziel_uid))
    if write:
        conn.commit()
    else:
        conn.rollback()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Allgemein-Topf verteilen (#28)")
    ap.add_argument("--write", action="store_true", help="Verteilung buchen (sonst Trockenlauf)")
    ap.add_argument("--soll", action="store_true", help="zusätzlich monatliches Soll je Topf setzen")
    args = ap.parse_args(argv)
    print(f"=== #28 Allgemein-Topf verteilen — "
          f"{'SCHREIBEN' if args.write else 'TROCKENLAUF'}{' + Soll' if args.soll else ''} ===")
    conn = connect()
    try:
        verteile(conn, args.write, args.soll)
    finally:
        conn.close()
    if not args.write:
        print("\n  Zahlen prüfen, dann mit  --write  buchen.")
    else:
        print("\n>>> gebucht.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
