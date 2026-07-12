"""Beladung der Datenbank mit Stichtag-/Startsaldo-Logik.

Grundidee (löst die Überlappung zweier Quellen ohne Doppelbuchungen):
  * Stichtag = 01.01.2025. Alles DAVOR wird je Konto/Topf zu EINEM Startsaldo
    (Eröffnungsbuchung, quelle='startsaldo', datiert 31.12.2024) zusammengefasst.
  * AB dem Stichtag werden die Einzelbuchungen geführt.
  * Invariante je Konto:  Startsaldo + Summe aller Bewegungen = tatsächlicher Kontostand.

Quellen:
  * DKB-Giro + 14 Rücklagen-Töpfe  -> Fuchsbaukasse (die gepflegte Historie)
  * comdirect-Giro / -Tagesgeld    -> Auszüge; Startsaldo aus aktuellem Kontostand rückgerechnet
  * comdirect-Depot                -> Wertpapierbewegungen (kein Bar-Startsaldo)
  * Amazon-Visa                    -> Kreditkartenausgaben (kein Startsaldo)

Aufruf:
  python -m haushaltskasse.workflows.beladung           # Vorschau + Verifikation, KEIN Schreiben
  python -m haushaltskasse.workflows.beladung --write    # TRUNCATE buchungen + neu beladen
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from ..storage.db import connect, kennzahlen
from . import parser
from .laden import _kategorie_id, _konto_id, _lade_maps, _unterkategorie_id
from .lokale_config import lade_lokale_config
from .migration_fb import _lade_fuchsbaukasse
from .pipeline import INPUT, einlesen, verarbeiten

STICHTAG = date(2025, 1, 1)          # erster Tag der Einzelbuchungs-Historie
STARTSALDO_DATUM = "2024-12-31"       # Datum der Eröffnungsbuchungen (Tag vor Stichtag)

# Konten, deren reale Historie aus der Fuchsbaukasse kommt (nicht aus den Auszügen).
FB_KONTO = "DKB-Giro"


def _vor_ab(buchungen: list[dict]) -> tuple[int, list[dict]]:
    """Teilt Buchungen am Stichtag: (Summe_vor_cent, Liste_ab_Stichtag)."""
    vor = 0
    ab: list[dict] = []
    for b in buchungen:
        if date.fromisoformat(b["datum"]) < STICHTAG:
            vor += b["betrag_cent"]
        else:
            ab.append(b)
    return vor, ab


def _kontostand_cent(pfad: Path) -> int | None:
    """Liest den 'Neuer Kontostand' aus einem comdirect-CSV-Header (Cent)."""
    try:
        text = pfad.read_text(encoding="latin-1")
    except OSError:
        return None
    m = re.search(r"Neuer Kontostand\W+([\d.]+,\d{2})", text)
    return parser._num(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Fuchsbaukasse: DKB-Giro (real) + Kto-Blätter (ruecklage)
# ---------------------------------------------------------------------------
def belade_fuchsbaukasse(cur, konten, kategorien, plan: list[dict]) -> None:
    dkb, kto = _lade_fuchsbaukasse()

    # DKB-Giro real
    start, ab = _vor_ab(dkb)
    dkb_id = konten["DKB-Giro"]
    _startsaldo(cur, "real", start, konto_id=dkb_id, bemerkung="Startsaldo DKB-Giro per 31.12.2024 (aus Fuchsbaukasse)")
    for b in ab:
        cur.execute(
            "INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, konto_id, empfaenger, "
            "verwendungszweck, quelle_import, import_hash) "
            "VALUES ('real',%s,%s,%s,%s,%s,'fb-dkb',%s) ON CONFLICT (import_hash) DO NOTHING",
            (b["datum"], b["betrag_cent"], dkb_id, b.get("empfaenger", ""),
             b.get("verwendungszweck", ""), b["import_hash"]),
        )
    plan.append({"ziel": "DKB-Giro (real)", "start": start, "einzel": len(ab),
                 "gesamt": start + sum(b["betrag_cent"] for b in ab)})

    # Kto-Blätter -> Rücklagen
    ukat_cache: dict = {}
    for kat, buchungen in sorted(kto.items()):
        kat_id = kategorien.get(kat)
        if kat_id is None:
            print(f"  [WARN] Kategorie '{kat}' fehlt in der DB – übersprungen.")
            continue
        start, ab = _vor_ab(buchungen)
        _startsaldo(cur, "ruecklage", start, kategorie_id=kat_id,
                    bemerkung=f"Startsaldo Rücklage {kat} per 31.12.2024 (aus Fuchsbaukasse)")
        for b in ab:
            ukat_id = None
            uname = b.get("unterkategorie")
            if uname:
                ukat_id = _unterkategorie_id(cur, ukat_cache, kat_id, uname)
            cur.execute(
                "INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, kategorie_id, "
                "unterkategorie_id, verwendungszweck, bemerkung, quelle_import, import_hash) "
                "VALUES ('ruecklage',%s,%s,%s,%s,%s,%s,'fb-kto',%s) ON CONFLICT (import_hash) DO NOTHING",
                (b["datum"], b["betrag_cent"], kat_id, ukat_id,
                 b.get("verwendungszweck", ""), b.get("bemerkung", ""), b["import_hash"]),
            )
        plan.append({"ziel": f"Rücklage {kat}", "start": start, "einzel": len(ab),
                     "gesamt": start + sum(b["betrag_cent"] for b in ab)})


def _startsaldo(cur, art, betrag_cent, konto_id=None, kategorie_id=None, bemerkung="") -> None:
    """Legt eine Eröffnungsbuchung an (quelle='startsaldo'), auch wenn Betrag 0 ist."""
    import_hash = f"start-{art}-{konto_id or ''}-{kategorie_id or ''}"
    cur.execute(
        "INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, konto_id, kategorie_id, "
        "verwendungszweck, quelle_import, import_hash) "
        "VALUES (%s,%s,%s,%s,%s,%s,'startsaldo',%s) ON CONFLICT (import_hash) DO NOTHING",
        (art, STARTSALDO_DATUM, betrag_cent, konto_id, kategorie_id, bemerkung, import_hash),
    )


# ---------------------------------------------------------------------------
# Auszüge: comdirect-Giro/-Tagesgeld/-Depot + Amazon-Visa
# ---------------------------------------------------------------------------
def belade_auszuege(cur, konten, kategorien, plan: list[dict]) -> None:
    cfg = lade_lokale_config()
    buchungen = verarbeiten(einlesen(), cfg)

    # Nach Konto gruppieren; DKB-Giro aus den Auszügen ignorieren (kommt aus der FB).
    pro_konto: dict[str, list[dict]] = defaultdict(list)
    for b in buchungen:
        if b["konto"] == FB_KONTO:
            continue
        pro_konto[b["konto"]].append(b)

    # Kontostände aus den comdirect-Headern (für den rückgerechneten Startsaldo).
    kontostaende: dict[str, int] = {}
    for p in INPUT.iterdir():
        if "tagesgeld" in p.name.lower():
            ks = _kontostand_cent(p)
            if ks is not None:
                kontostaende["comdirect-Tagesgeld"] = ks
        elif "comdirect" in p.name.lower() and p.suffix.lower() == ".csv":
            ks = _kontostand_cent(p)
            if ks is not None:
                kontostaende["comdirect-Giro"] = ks

    ukat_cache: dict = {}
    for konto, bs in sorted(pro_konto.items()):
        konto_id = _konto_id(cur, konten, konto)
        bewegung = sum(b["betrag_cent"] or 0 for b in bs)

        # Startsaldo nur für die comdirect-Barkonten mit bekanntem Kontostand.
        start = 0
        if konto in kontostaende:
            start = kontostaende[konto] - bewegung
            _startsaldo(cur, "real", start, konto_id=konto_id,
                        bemerkung=f"Startsaldo {konto} (rückgerechnet aus Kontostand)")

        for b in bs:
            kat_id = ukat_id = None
            if b["buchungsart"] == "real" and b.get("kategorie"):
                kat_id = _kategorie_id(cur, kategorien, b["kategorie"])
                ukat_id = _unterkategorie_id(cur, ukat_cache, kat_id, b.get("unterkategorie"))
            cur.execute(
                "INSERT INTO buchungen (buchungsart, datum_wert, betrag_cent, konto_id, "
                "kategorie_id, unterkategorie_id, empfaenger, verwendungszweck, quelle_import, import_hash) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (import_hash) DO NOTHING",
                (b["buchungsart"], b["datum"], b["betrag_cent"], konto_id, kat_id, ukat_id,
                 b["empfaenger"], b["verwendungszweck"], b["quelle"], b["import_hash"]),
            )
        plan.append({"ziel": f"{konto} ({len(bs)} Bew.)", "start": start, "einzel": len(bs),
                     "gesamt": start + bewegung, "kontostand": kontostaende.get(konto)})


# ---------------------------------------------------------------------------
# Orchestrierung
# ---------------------------------------------------------------------------
def belade(write: bool = False) -> None:
    conn = connect()
    plan: list[dict] = []
    try:
        with conn.cursor() as cur:
            konten, kategorien = _lade_maps(cur)
            if not konten or not kategorien:
                print("[FEHLER] Konten/Kategorien fehlen – zuerst 'python -m haushaltskasse.workflows.seed' ausführen.")
                return
            print(f"[beladung] Stichtag {STICHTAG.isoformat()} — Startsaldo per {STARTSALDO_DATUM}.")
            print("[beladung] TRUNCATE buchungen (Neuaufbau) ...")
            cur.execute("TRUNCATE buchungen RESTART IDENTITY CASCADE")
            belade_fuchsbaukasse(cur, konten, kategorien, plan)
            belade_auszuege(cur, konten, kategorien, plan)
            if not write:
                conn.rollback()
                print("\n[Vorschau] Rollback – nichts geschrieben. Mit --write ausführen.\n")
            else:
                conn.commit()
                print("\n[beladung] committed.\n")
        _bericht(plan)
        if write:
            print(f"\n[beladung] Kennzahlen (DB): {kennzahlen(conn)}")
    finally:
        conn.close()


def _e(cent) -> float:
    return (cent or 0) / 100


def _bericht(plan: list[dict]) -> None:
    print("--- Beladung je Ziel (Start = Eröffnung 31.12.2024, Gesamt = Endsaldo) ---")
    print(f"  {'Ziel':30s} {'Startsaldo':>13s} {'Einzel':>7s} {'Endsaldo':>13s}")
    real_sum = ruck_sum = 0
    for p in sorted(plan, key=lambda x: x["ziel"]):
        ks = p.get("kontostand")
        chk = ""
        if ks is not None:
            chk = "  OK" if ks == p["gesamt"] else f"  !=Kontostand {_e(ks):,.2f}"
        print(f"  {p['ziel']:30s} {_e(p['start']):>13,.2f} {p['einzel']:>7d} {_e(p['gesamt']):>13,.2f}{chk}")
        if p["ziel"].startswith("Rücklage"):
            ruck_sum += p["gesamt"]
        else:
            real_sum += p["gesamt"]
    print(f"\n  {'Summe real (Konten)':30s} {'':>13s} {'':>7s} {_e(real_sum):>13,.2f}")
    print(f"  {'Summe Rücklagen':30s} {'':>13s} {'':>7s} {_e(ruck_sum):>13,.2f}")
    print(f"  {'Verfügbar (real - Rücklagen)':30s} {'':>13s} {'':>7s} {_e(real_sum - ruck_sum):>13,.2f}")


if __name__ == "__main__":
    belade(write="--write" in sys.argv)
