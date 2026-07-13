"""Migration zu Topf-Modell A (Topf JE Unterkategorie).

Problem vorher: Zuführungen (Startsaldo-Topffüllung) waren kategorie-weit gebucht
(unterkategorie_id IS NULL), die Verzehre fein je Unterkategorie. Dadurch summierten sich
die Unterkategorie-Ist-Stände NICHT zum Kategorie-Topf (Bsp. Auto: gesamt +865, aber
Tanken −4185, der Rest +6702 unsichtbar unter „ohne Unterkategorie").

Lösung: je Kategorie mit solchen Buchungen eine Unterkategorie **„Allgemein"** anlegen und
alle `buchungsart='ruecklage'` mit `unterkategorie_id IS NULL` dorthin umhängen. Danach gilt
Kategorie-Topf = Σ Unterkategorie-Töpfe (geht immer sauber auf). „Allgemein" wird zugleich die
Default-/Rest-Unterkategorie der Kategorie.

Idempotent: erneuter Lauf findet keine NULL-ruecklage-Buchungen mehr → No-Op.
Nach erneutem `beladung --write` (TRUNCATE) erneut laufen lassen.

    python -m haushaltskasse.workflows.allgemein_toepfe            # dry-run
    python -m haushaltskasse.workflows.allgemein_toepfe --write    # ausführen
"""
from __future__ import annotations

import sys

from ..storage.db import connect

REST_NAME = "Allgemein"


def migriere(cur, write: bool = False) -> list[dict]:
    cur.execute("""
        SELECT b.kategorie_id, k.name, COUNT(*), SUM(b.betrag_cent)
        FROM buchungen b JOIN kategorien k ON k.id = b.kategorie_id
        WHERE b.buchungsart='ruecklage' AND b.unterkategorie_id IS NULL AND b.kategorie_id IS NOT NULL
        GROUP BY b.kategorie_id, k.name ORDER BY k.name
    """)
    betroffen = cur.fetchall()
    ergebnis = []
    for kid, kname, n, netto in betroffen:
        # 1) „Allgemein"-Unterkategorie sicherstellen
        cur.execute("""INSERT INTO unterkategorien (kategorie_id, name, quelle)
                       VALUES (%s, %s, 'manuell')
                       ON CONFLICT (kategorie_id, name) DO NOTHING""", (kid, REST_NAME))
        cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s", (kid, REST_NAME))
        uid = cur.fetchone()[0]
        # 2) Kategorie-Default (Rest-Auffang) auf „Allgemein", falls noch keiner gesetzt
        cur.execute("""UPDATE kategorien SET default_unterkategorie_id=%s
                       WHERE id=%s AND default_unterkategorie_id IS NULL""", (uid, kid))
        # 3) kategorie-weite ruecklage-Buchungen der „Allgemein"-Unterkategorie zuordnen
        cur.execute("""UPDATE buchungen SET unterkategorie_id=%s
                       WHERE buchungsart='ruecklage' AND unterkategorie_id IS NULL AND kategorie_id=%s""",
                    (uid, kid))
        ergebnis.append({"kategorie": kname, "unterkategorie_id": uid, "buchungen": n,
                         "netto_cent": netto})
    if not write:
        cur.connection.rollback()
    return ergebnis


def main() -> None:
    write = "--write" in sys.argv
    con = connect()
    cur = con.cursor()
    res = migriere(cur, write=write)
    if write:
        con.commit()
    modus = "AUSGEFÜHRT" if write else "DRY-RUN (nichts geändert)"
    print(f"[allgemein_toepfe] {modus} — {len(res)} Kategorien:")
    for r in res:
        print(f"  {r['kategorie']:<28} → 'Allgemein' (ukat {r['unterkategorie_id']}): "
              f"{r['buchungen']} Buchungen, netto {r['netto_cent']/100:>11.2f} €")
    if not write and res:
        print("\n  Mit  --write  ausführen.")
    con.close()


if __name__ == "__main__":
    main()
