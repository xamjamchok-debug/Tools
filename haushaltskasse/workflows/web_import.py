"""I1 — Web-Import: eine hochgeladene Kontoauszug-Datei parsen, abgrenzen, kategorisieren und
in die DB schreiben (Dedupe über import_hash → wiederholter Import legt nichts doppelt an).

Dateizuordnung wie in der Pipeline über den Dateinamen (dkb/girokonto, comdirect, tagesgeld, amazon).
Ohne lokale_config.json (z. B. im Container) läuft die Umbuchungs-Erkennung ohne Personenbezug —
die betroffenen Buchungen lassen sich danach im Dashboard nachkategorisieren.
"""
from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path

from ..storage.db import connect
from .abgrenzung import bestimme_buchungsart
from .kategorisierung import kategorisiere
from .laden import _kategorie_id, _konto_id, _lade_maps, _unterkategorie_id
from .lokale_config import lade_lokale_config
from .pipeline import _dispatch


def importiere_upload(dateiname: str, daten: bytes, conn=None) -> dict:
    """Parst die hochgeladene Datei und schreibt die Buchungen dedupliziert in die DB.
    Gibt einen Bericht zurück (geparst / eingefügt / übersprungen / offen / je Konto)."""
    own = conn is None
    conn = conn or connect()
    try:
        cfg = lade_lokale_config()
        with tempfile.TemporaryDirectory() as td:
            pfad = Path(td) / dateiname          # Originalname → Dispatch nach Dateiname
            pfad.write_bytes(daten)
            roh = _dispatch(pfad)

        if not roh:
            return {"datei": dateiname, "erkannt": False, "geparst": 0, "eingefuegt": 0,
                    "uebersprungen": 0, "real": 0, "offen": 0, "konten": {},
                    "hinweis": "Dateiname nicht erkannt — erwartet: dkb/girokonto, comdirect, tagesgeld oder amazon."}

        for b in roh:
            b["buchungsart"] = bestimme_buchungsart(b, cfg["eigene_ibans"], cfg["halter"], cfg["kinder"])
            if b["buchungsart"] == "real":
                b["kategorie"], b["unterkategorie"] = kategorisiere(b, cfg["persoenliche_regeln"])
            else:
                b["kategorie"] = b["unterkategorie"] = None

        eingefuegt = uebersprungen = dubletten = 0
        ukat_cache: dict = {}
        with conn.cursor() as cur:
            konten, kategorien = _lade_maps(cur)
            # Fachlicher Dedupe (quelle-UNABHÄNGIG, Multiset): erkennt auch migrierte Bestände
            # (z. B. fb-dkb) als Dublette und lässt echte Mehrfachbuchungen desselben Tags zu.
            cur.execute("SELECT datum_wert, betrag_cent, konto_id, COALESCE(empfaenger,'') "
                        "FROM buchungen WHERE konto_id IS NOT NULL")
            bestand = Counter((str(d), bt, k, e) for d, bt, k, e in cur.fetchall())
            for b in roh:
                konto_id = _konto_id(cur, konten, b["konto"])
                schluessel = (str(b["datum"]), b["betrag_cent"], konto_id, b.get("empfaenger") or "")
                if bestand.get(schluessel, 0) > 0:       # schon vorhanden (auch aus Migration) → überspringen
                    bestand[schluessel] -= 1
                    dubletten += 1
                    uebersprungen += 1
                    continue
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
                if cur.rowcount:
                    eingefuegt += 1
                else:
                    uebersprungen += 1
        conn.commit()

        real = [b for b in roh if b["buchungsart"] == "real"]
        offen = [b for b in real if not b.get("kategorie")]
        return {"datei": dateiname, "erkannt": True, "geparst": len(roh), "eingefuegt": eingefuegt,
                "uebersprungen": uebersprungen, "real": len(real), "offen": len(offen),
                "config_fehlt": not cfg["_vorhanden"],
                "konten": dict(Counter(b["konto"] for b in roh))}
    finally:
        if own:
            conn.close()
