"""#77 — die alten S-Präfix-Unterkategorien in „Allgemein" zusammenführen.

Die #50-Migration hat „Allgemein" NEBEN den alten S-Töpfen angelegt, statt sie zu
verschmelzen (S-Tel, S-Sport, S-TK …). Jörg 2026-07-17: „S-Tel ist falsch, die Summe der
Unterkategorien muss das Nebenbuch ergeben." Dieser Lauf hängt alle Buchungen (real UND
ruecklage) sowie mapping_regeln von den S-Töpfen auf die Default-Unterkategorie („Allgemein")
des jeweiligen Nebenbuchs um und löscht die leeren S-Töpfe.

**Saldo-neutral** (Prinzip 1): Umhängen bleibt innerhalb desselben Nebenbuchs, die
kategorie-weite Ruecklage-Summe ändert sich nicht — wird nach dem Lauf geprüft.

    python -m haushaltskasse.workflows.s_merge            # dry-run
    python -m haushaltskasse.workflows.s_merge --write    # ausführen
"""
from __future__ import annotations

import sys

from ..storage.db import connect


def _kat_salden(cur) -> dict[int, int]:
    cur.execute("""SELECT kategorie_id, COALESCE(SUM(betrag_cent),0)
                   FROM buchungen WHERE buchungsart='ruecklage' GROUP BY kategorie_id""")
    return dict(cur.fetchall())


def merge(cur, write: bool) -> list[dict]:
    # S-Töpfe je Nebenbuch + dessen Default-(Allgemein-)Topf.
    cur.execute("""
        SELECT u.id, u.name, u.kategorie_id, k.name, k.default_unterkategorie_id
        FROM unterkategorien u JOIN kategorien k ON k.id = u.kategorie_id
        WHERE u.name LIKE 'S-%'
        ORDER BY k.name, u.name
    """)
    ergebnis = []
    for uid, uname, kid, kname, default_id in cur.fetchall():
        if default_id is None or default_id == uid:
            ergebnis.append({"kat": kname, "topf": uname, "status": "ÜBERSPRUNGEN (kein Default)"})
            continue
        cur.execute("SELECT COUNT(*) FROM buchungen WHERE unterkategorie_id=%s", (uid,))
        n_buch = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM mapping_regeln WHERE unterkategorie_id=%s", (uid,))
        n_regel = cur.fetchone()[0]
        if write:
            cur.execute("UPDATE buchungen SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                        (default_id, uid))
            cur.execute("UPDATE mapping_regeln SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                        (default_id, uid))
            cur.execute("UPDATE vertraege SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                        (default_id, uid))
            cur.execute("DELETE FROM unterkategorien WHERE id=%s", (uid,))
        ergebnis.append({"kat": kname, "topf": uname, "buchungen": n_buch, "regeln": n_regel,
                         "status": "→ Allgemein"})
    return ergebnis


def main() -> None:
    write = "--write" in sys.argv
    con = connect()
    cur = con.cursor()
    vorher = _kat_salden(cur)
    res = merge(cur, write)

    print(f"[s_merge] {'AUSGEFÜHRT' if write else 'DRY-RUN'} — {len(res)} S-Töpfe:")
    for r in res:
        extra = f"{r.get('buchungen','?')} Buchungen, {r.get('regeln','?')} Regeln" if "buchungen" in r else ""
        print(f"  {r['kat']:<14} {r['topf']:<14} {r['status']}  {extra}")

    if write:
        nachher = _kat_salden(cur)
        drift = [(k, vorher.get(k, 0), nachher.get(k, 0))
                 for k in set(vorher) | set(nachher) if vorher.get(k, 0) != nachher.get(k, 0)]
        if drift:
            print("\n  ⚠️ SALDO-DRIFT (dürfte NICHT sein) — Rollback!")
            for k, v, n in drift:
                print(f"    Kategorie {k}: {v/100:.2f} → {n/100:.2f}")
            con.rollback()
        else:
            con.commit()
            print("\n  ✓ Saldo je Nebenbuch unverändert. Committed.")
    else:
        print("\n  Mit  --write  ausführen.")
    con.close()


if __name__ == "__main__":
    main()
