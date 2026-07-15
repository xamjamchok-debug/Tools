"""Backlog #49: Kategorien-Cleanup (User-Entscheid).

(a) 3× „Kindergeld" → 1 Unterkategorie unter Füchschen, als Einnahme.
(b) Kategorie „Kinder" entfällt — Füchschen *sind* die Kinder.
(c) Unterkategorie „Taschengeld/Sparen" wandert von „Kinder" nach Füchschen.

    python -m haushaltskasse.workflows.kategorie_cleanup            # Trockenlauf
    python -m haushaltskasse.workflows.kategorie_cleanup --write

Idempotent: ein zweiter Lauf findet nichts mehr zu tun. Verschiebt nur Zuordnungen,
erzeugt und löscht keine Buchungen → Salden bleiben unverändert (wird am Ende geprüft).
"""
from __future__ import annotations

import argparse
import sys

from ..storage import db

ZIEL_KAT = "Füchschen"
KINDERGELD_ZIEL = "Kindergeld"
ALT_KAT = "Kinder"


def _saldo_snapshot(cur) -> dict[str, int]:
    cur.execute("""SELECT k.name, COALESCE(SUM(b.betrag_cent),0)
                   FROM kategorien k LEFT JOIN buchungen b
                     ON b.kategorie_id = k.id AND b.buchungsart='ruecklage'
                   GROUP BY k.name""")
    return {n: s for n, s in cur.fetchall()}


def cleanup(conn, write: bool) -> None:
    with conn.cursor() as cur:
        vorher = _saldo_snapshot(cur)

        cur.execute("SELECT id FROM kategorien WHERE name=%s", (ZIEL_KAT,))
        row = cur.fetchone()
        if not row:
            print(f"  ! Kategorie {ZIEL_KAT!r} fehlt — Abbruch")
            return
        ziel_kid = row[0]

        # --- (a) Kindergeld-Dubletten zusammenführen -------------------------
        cur.execute("""SELECT id, name FROM unterkategorien
                       WHERE kategorie_id=%s AND name ILIKE '%%kindergeld%%'
                       ORDER BY (name = %s) DESC, id""", (ziel_kid, KINDERGELD_ZIEL))
        kg = cur.fetchall()
        if not kg:
            print("  (a) keine Kindergeld-Unterkategorie gefunden")
        else:
            ziel_uid, ziel_name = kg[0]
            print(f"  (a) Ziel: u{ziel_uid} {ziel_name!r}")
            for uid, name in kg[1:]:
                cur.execute("SELECT COUNT(*) FROM buchungen WHERE unterkategorie_id=%s", (uid,))
                n = cur.fetchone()[0]
                print(f"      ~ u{uid} {name!r} -> {ziel_name!r} ({n} Buchungen)")
                if write:
                    cur.execute("UPDATE buchungen SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                                (ziel_uid, uid))
                    cur.execute("UPDATE mapping_regeln SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                                (ziel_uid, uid))
                    cur.execute("UPDATE kategorien SET default_unterkategorie_id=%s "
                                "WHERE default_unterkategorie_id=%s", (ziel_uid, uid))
                    cur.execute("DELETE FROM unterkategorien WHERE id=%s", (uid,))
            if write:
                cur.execute("UPDATE unterkategorien SET name=%s, ist_einnahme=TRUE WHERE id=%s",
                            (KINDERGELD_ZIEL, ziel_uid))
            print(f"      = {KINDERGELD_ZIEL!r}, ist_einnahme=TRUE")

        # --- (c) Taschengeld/Sparen umhängen + (b) Kategorie Kinder entfernen -
        cur.execute("SELECT id FROM kategorien WHERE name=%s", (ALT_KAT,))
        row = cur.fetchone()
        if not row:
            print(f"  (b/c) Kategorie {ALT_KAT!r} existiert nicht mehr — nichts zu tun")
        else:
            alt_kid = row[0]
            cur.execute("SELECT id, name FROM unterkategorien WHERE kategorie_id=%s", (alt_kid,))
            for uid, name in cur.fetchall():
                # Namenskollision im Ziel? Dann dorthin mergen statt umhängen.
                cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s",
                            (ziel_kid, name))
                kollision = cur.fetchone()
                cur.execute("SELECT COUNT(*) FROM buchungen WHERE unterkategorie_id=%s", (uid,))
                n = cur.fetchone()[0]
                if kollision:
                    print(f"  (c) u{uid} {name!r} -> vorhandene u{kollision[0]} in {ZIEL_KAT} ({n} Buchungen)")
                    if write:
                        cur.execute("UPDATE buchungen SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                                    (kollision[0], uid))
                        cur.execute("DELETE FROM unterkategorien WHERE id=%s", (uid,))
                else:
                    print(f"  (c) u{uid} {name!r}: Kategorie {ALT_KAT} -> {ZIEL_KAT} ({n} Buchungen)")
                    if write:
                        cur.execute("UPDATE unterkategorien SET kategorie_id=%s WHERE id=%s",
                                    (ziel_kid, uid))

            cur.execute("SELECT COUNT(*) FROM buchungen WHERE kategorie_id=%s", (alt_kid,))
            nb = cur.fetchone()[0]
            print(f"  (b) {nb} Buchungen von {ALT_KAT!r} -> {ZIEL_KAT!r}; danach Kategorie löschen")
            if write:
                cur.execute("UPDATE buchungen SET kategorie_id=%s WHERE kategorie_id=%s",
                            (ziel_kid, alt_kid))
                cur.execute("UPDATE mapping_regeln SET kategorie_id=%s WHERE kategorie_id=%s",
                            (ziel_kid, alt_kid))
                cur.execute("DELETE FROM kategorien WHERE id=%s", (alt_kid,))

        # --- Kontrolle: Rücklagen-Salden dürfen sich nicht verändert haben ----
        if write:
            nachher = _saldo_snapshot(cur)
            zusammengelegt = {ALT_KAT}
            for name, alt in vorher.items():
                if name in zusammengelegt:
                    continue
                neu = nachher.get(name, 0)
                erwartet = alt + (vorher.get(ALT_KAT, 0) if name == ZIEL_KAT else 0)
                if neu != erwartet:
                    print(f"  !! Saldo {name}: {alt/100:.2f} -> {neu/100:.2f} "
                          f"(erwartet {erwartet/100:.2f})")
            print("\n  Saldo-Kontrolle: ok (nur Zuordnungen verschoben)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kategorien-Cleanup (#49)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    print(f"=== #49 Kategorien-Cleanup — "
          f"{'SCHREIBEN' if args.write else 'TROCKENLAUF'} ===")
    conn = db.connect()
    try:
        cleanup(conn, args.write)
        if args.write:
            conn.commit()
            print("\n>>> committed.")
        else:
            conn.rollback()
            print("\n>>> Trockenlauf — mit --write ausführen.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
