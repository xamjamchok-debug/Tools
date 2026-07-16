"""#61 — Orchestrierter Neuaufbau: die korrekte Migrations-Kette in EINEM Kommando.

Hintergrund (Leitplanke Jörg / Fable-Review F2): `beladung --write` leert die Buchungstabelle
und lädt aus FB + input/ neu. Danach fehlen zwingend die Auto-Gegenbuchungen und die
„Allgemein"-Topf-Zuordnungen — die Reihenfolge der Reparaturläufe war bisher Kopfwissen.
Dieses Kommando führt die Kette selbst aus, in der einzig richtigen Reihenfolge, und prüft
am Ende die Invarianten. Niemand muss die Reihenfolge mehr kennen.

    python -m haushaltskasse.workflows.reload             # Vorschau (alle Trockenläufe)
    python -m haushaltskasse.workflows.reload --write     # fragt einmal nach, dann alles
    python -m haushaltskasse.workflows.reload --write --ja   # ohne Rückfrage (Automation)

Die beladung-Verriegelung gilt auch hier: existieren nicht-reproduzierbare Daten (manuelle
Buchungen, Web-Importe, Verteilungen), bricht der Lauf ab, außer es wird zusätzlich
--zerstoere-manuelle-daten übergeben — vorher ein Backup ziehen (pg_dump / #33).
"""
from __future__ import annotations

import sys

from ..storage.db import connect
from . import allgemein_toepfe, beladung, gegenbuchung
from .invarianten import main as invarianten_main


def reload(write: bool = False, ja: bool = False, zerstoeren_ok: bool = False) -> int:
    schritte = "beladung → gegenbuchung → allgemein_toepfe → invarianten"
    print(f"[reload] Kette: {schritte}\n")

    if not write:
        print("[reload] === VORSCHAU (alle Schritte als Trockenlauf) ===\n")
        beladung.belade(write=False)
        gegenbuchung.lauf(write=False)
        with connect() as conn, conn.cursor() as cur:
            allgemein_toepfe.migriere(cur, write=False)
        print("\n[reload] Vorschau beendet — mit --write ausführen.")
        return 0

    if not ja:
        antwort = input(f"[reload] Kette '{schritte}' JETZT SCHREIBEND ausführen? (ja/nein) ")
        if antwort.strip().lower() != "ja":
            print("[reload] abgebrochen.")
            return 1

    print("\n[reload] 1/4 beladung --write ...")
    beladung.belade(write=True, zerstoeren_ok=zerstoeren_ok)
    print("\n[reload] 2/4 gegenbuchung --write ...")
    gegenbuchung.lauf(write=True)
    print("\n[reload] 3/4 allgemein_toepfe --write ...")
    with connect() as conn, conn.cursor() as cur:
        res = allgemein_toepfe.migriere(cur, write=True)
        conn.commit()
        print(f"  {len(res)} Kategorien migriert.")
    print("\n[reload] 4/4 Invarianten prüfen ...")
    return invarianten_main()


if __name__ == "__main__":
    sys.exit(reload(write="--write" in sys.argv, ja="--ja" in sys.argv,
                    zerstoeren_ok="--zerstoere-manuelle-daten" in sys.argv))
