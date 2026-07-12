"""Pipeline: Dateien in input/ einlesen -> Abgrenzung -> Erstkategorisierung -> Bericht.

Vorschau (kein DB-Schreiben):  python -m haushaltskasse.workflows.pipeline
Erwartet die Exporte in input/ (gitignored). Dateizuordnung über den Dateinamen.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import parser
from .abgrenzung import bestimme_buchungsart
from .kategorisierung import kategorisiere
from .lokale_config import lade_lokale_config

INPUT = Path(__file__).resolve().parent.parent.parent / "input"


def _dispatch(pfad: Path) -> list[dict]:
    name = pfad.name.lower()
    if name.endswith(".xls") and "amazon" in name:
        return parser.parse_amazon_visa(pfad)
    if "tagesgeld" in name:
        return parser.parse_comdirect(pfad, "comdirect-Tagesgeld")
    if "comdirect" in name:
        return parser.parse_comdirect(pfad, "comdirect-Giro")
    if "dkb" in name or "girokonto" in name:
        return parser.parse_dkb_giro(pfad)
    return []


def einlesen(input_dir: Path = INPUT) -> list[dict]:
    alle: list[dict] = []
    for p in sorted(input_dir.iterdir()):
        if p.suffix.lower() in (".csv", ".xls"):
            alle.extend(_dispatch(p))
    return alle


def verarbeiten(buchungen: list[dict], cfg: dict) -> list[dict]:
    for b in buchungen:
        b["buchungsart"] = bestimme_buchungsart(b, cfg["eigene_ibans"], cfg["halter"], cfg["kinder"])
        if b["buchungsart"] == "real":
            b["kategorie"], b["unterkategorie"] = kategorisiere(b, cfg["persoenliche_regeln"])
        else:
            b["kategorie"] = b["unterkategorie"] = None
    return buchungen


def _e(cent):
    return (cent or 0) / 100


def bericht(buchungen: list[dict]) -> None:
    per_konto = Counter(b["konto"] for b in buchungen)
    art = Counter(b["buchungsart"] for b in buchungen)
    summe = defaultdict(int)
    for b in buchungen:
        summe[b["buchungsart"]] += b["betrag_cent"] or 0

    print(f"Gesamt geparste Buchungen: {len(buchungen)}\n")
    print("--- Buchungen je Konto ---")
    for k, c in per_konto.most_common():
        print(f"  {c:4d}  {k}")
    print("\n--- Abgrenzung (Buchungsart) ---")
    for a in ("real", "umbuchung", "wertpapier", "zinsen"):
        print(f"  {art[a]:4d}  {a:11s}  Summe {_e(summe[a]):>12,.2f} €")

    real = [b for b in buchungen if b["buchungsart"] == "real"]
    kat = Counter((b["kategorie"], b["unterkategorie"]) for b in real if b["kategorie"])
    offen = [b for b in real if not b["kategorie"]]
    print(f"\n--- Echte Buchungen: {len(real)} | kategorisiert {len(real)-len(offen)} | offen {len(offen)} ---")
    for (k, u), c in kat.most_common(20):
        print(f"  {c:3d}  {k} / {u}")
    if offen:
        print(f"\n--- Offen ({len(offen)}) ---")
        for b in offen[:15]:
            print(f"  {b['konto']:16s} {b['datum']:10s} {_e(b['betrag_cent']):>10.2f}  {b['empfaenger'][:45]}")


if __name__ == "__main__":
    cfg = lade_lokale_config()
    if not cfg["_vorhanden"]:
        print("[hinweis] Keine lokale_config.json gefunden – Umbuchungs-Erkennung ohne Personenbezug.\n"
              "          Vorlage: workflows/lokale_config.example.json -> data/lokale_config.json\n")
    buchungen = verarbeiten(einlesen(), cfg)
    bericht(buchungen)
    sys.exit(0)
