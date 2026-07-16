"""#61 — Audit-Log der Admin-/Write-Läufe: Kennzahlen vorher/nachher + Invarianten-Ergebnis.

Jeder --write-Lauf trägt sich in `admin_laeufe` ein — beantwortet später „was lief wann,
und war die DB danach konsistent?". Bewusst klein gehalten.
"""
from __future__ import annotations

import json

from ..domain.saldo import pruefe_invarianten
from ..storage.db import kennzahlen


def kennzahlen_json(conn) -> str:
    return json.dumps(kennzahlen(conn), default=str, ensure_ascii=False)


def protokolliere(conn, werkzeug: str, argumente: str, vorher_json: str) -> bool:
    """Am ENDE eines Write-Laufs (vor dem Commit) aufrufen: prüft die Invarianten,
    schreibt den Audit-Eintrag und gibt zurück, ob die Invarianten erfüllt sind."""
    with conn.cursor() as cur:
        befunde = pruefe_invarianten(cur)
        cur.execute("""INSERT INTO admin_laeufe
                       (werkzeug, argumente, kennzahlen_vorher, kennzahlen_nachher, invarianten_ok)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (werkzeug, argumente, vorher_json, kennzahlen_json(conn), not befunde))
    if befunde:
        print(f"[audit] {werkzeug}: {len(befunde)} Invarianten-Verletzung(en):")
        for b in befunde:
            print(f"  ✗ {b}")
    return not befunde
