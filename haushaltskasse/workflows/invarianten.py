"""Konsistenz-Check der Geld-Logik (#60/#23b) — read-only, jederzeit gefahrlos ausführbar.

Prüft die Invarianten aus domain/saldo.py gegen die verbundene DB und meldet Verletzungen.
Exit-Code 0 = alles konsistent, 1 = Befunde (für CI/Skript-Ketten).

    python -m haushaltskasse.workflows.invarianten
"""
from __future__ import annotations

import sys

from ..domain.saldo import haushaltssaldo, pruefe_invarianten
from ..storage.db import connect


def main() -> int:
    with connect() as conn, conn.cursor() as cur:
        s = haushaltssaldo(cur)
        print(f"[invarianten] Saldo {s['saldo_cent']/100:,.2f} € "
              f"(Konten {s['konten_cent']/100:,.2f} + Posten {s['posten_cent']/100:,.2f} "
              f"− Rücklagen {s['ruecklagen_cent']/100:,.2f} + Forderungen {s['forderung_cent']/100:,.2f})")
        befunde = pruefe_invarianten(cur)
        conn.rollback()   # sicherheitshalber — es wurde nichts geschrieben
    if befunde:
        print(f"[invarianten] {len(befunde)} VERLETZUNG(EN):")
        for b in befunde:
            print(f"  ✗ {b}")
        return 1
    print("[invarianten] OK — alle Invarianten erfüllt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
