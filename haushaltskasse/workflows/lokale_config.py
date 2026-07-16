"""Lädt lokale, personenbezogene Konfiguration — aus Datei ODER DB (#22-Container-Lücke).

Quelle 1 (PC): haushaltskasse/data/lokale_config.json (gitignored). Enthält:
  * eigene_ibans          – Liste der eigenen Konto-IBANs (für Umbuchungs-Erkennung)
  * halter_regex          – Muster für den/die Kontoinhaber
  * kinder_regex          – Muster für die Kinder (damit deren Konten nicht als Umbuchung gelten)
  * persoenliche_regeln   – Kategorisierungs-Regeln mit Personenbezug (Vorrang vor STARTER_RULES)

Quelle 2 (Container): dieselben Daten als JSON in `einstellungen` (Schlüssel 'lokale_config').
Die Datei bleibt führend; die DB ist die Brücke in den Container, wo die Datei fehlt und der
Web-Import sonst nur grob abgrenzen kann. NIE im Code/Git — nur Datei (gitignored) oder DB.

Einmalig am PC in die DB spiegeln (und nach jeder Änderung der Datei):
    python -m haushaltskasse.workflows.lokale_config --push
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_PFAD = Path(__file__).resolve().parent.parent / "data" / "lokale_config.json"
_DB_SCHLUESSEL = "lokale_config"


def _kompiliere(cfg: dict, quelle: str) -> dict:
    persoenlich = [
        (re.compile(r["muster"], re.I), r["kategorie"], r["unterkategorie"])
        for r in cfg.get("persoenliche_regeln", [])
    ]
    return {
        "eigene_ibans": set(cfg.get("eigene_ibans", [])),
        "halter": re.compile(cfg["halter_regex"], re.I) if cfg.get("halter_regex") else None,
        "kinder": re.compile(cfg["kinder_regex"], re.I) if cfg.get("kinder_regex") else None,
        "persoenliche_regeln": persoenlich,
        "ruecklagen": cfg.get("ruecklagen", {}),  # {Kategoriename: Euro/Monat}
        "_vorhanden": bool(cfg),
        "_quelle": quelle if cfg else "keine",
    }


def lade_lokale_config(cur=None) -> dict:
    """Datei zuerst (PC), sonst DB (Container, wenn ein Cursor übergeben wird), sonst leer."""
    if _PFAD.exists():
        return _kompiliere(json.loads(_PFAD.read_text(encoding="utf-8")), "datei")
    if cur is not None:
        try:
            cur.execute("SELECT wert FROM einstellungen WHERE schluessel=%s", (_DB_SCHLUESSEL,))
            row = cur.fetchone()
            if row and row[0]:
                return _kompiliere(json.loads(row[0]), "db")
        except Exception:
            pass   # Tabelle/Schlüssel fehlt -> wie „keine Config" weiterlaufen
    return _kompiliere({}, "keine")


def push_in_db() -> None:
    """Spiegelt die lokale Datei in die einstellungen-Tabelle (Upsert)."""
    from ..storage.db import connect
    if not _PFAD.exists():
        raise SystemExit(f"[lokale_config] Datei fehlt: {_PFAD}")
    roh = _PFAD.read_text(encoding="utf-8")
    json.loads(roh)   # validieren, bevor es in die DB geht
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO einstellungen (schluessel, wert) VALUES (%s,%s)
                       ON CONFLICT (schluessel) DO UPDATE SET wert=EXCLUDED.wert""",
                    (_DB_SCHLUESSEL, roh))
        conn.commit()
    print(f"[lokale_config] in DB gespiegelt ({len(roh)} Zeichen) — Container-Import nutzt sie jetzt.")


if __name__ == "__main__":
    if "--push" in sys.argv:
        push_in_db()
    else:
        cfg = lade_lokale_config()
        print(f"[lokale_config] Quelle: {cfg['_quelle']} · IBANs: {len(cfg['eigene_ibans'])} · "
              f"persönliche Regeln: {len(cfg['persoenliche_regeln'])}")
        print("Mit  --push  in die DB spiegeln (für den Container-Import).")
