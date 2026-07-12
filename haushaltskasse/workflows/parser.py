"""Parser für die Kontoauszugs-Formate der verschiedenen Quellen.

Jeder Parser liefert eine Liste normalisierter Buchungen (dict) mit einheitlichen Feldern:
    quelle, konto, datum (ISO), betrag_cent, empfaenger, verwendungszweck, iban_gegen, vorgang
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from pathlib import Path


def _num(s: str) -> int | None:
    """Deutschen Betrag ('-1.234,56 €') in Cent (int) umwandeln."""
    s = (s or "").replace("€", "").replace("EUR", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s) * 100)
    except ValueError:
        return None


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip())


def _iso(datum: str) -> str:
    """'10.07.26' oder '08.07.2026' -> '2026-07-10'."""
    datum = datum.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(datum, fmt).date().isoformat()
        except ValueError:
            continue
    return datum


def _hash(*teile) -> str:
    return hashlib.sha1("|".join(str(t) for t in teile).encode("utf-8")).hexdigest()[:16]


def _buchung(quelle, konto, datum, betrag_cent, empfaenger, zweck, iban_gegen="", vorgang="", ref=""):
    return {
        "quelle": quelle,
        "konto": konto,
        "datum": _iso(datum),
        "betrag_cent": betrag_cent,
        "empfaenger": _norm(empfaenger),
        "verwendungszweck": _norm(zweck),
        "iban_gegen": iban_gegen.strip(),
        "vorgang": _norm(vorgang),
        "import_hash": _hash(quelle, _iso(datum), betrag_cent, _norm(empfaenger)[:40], ref or _norm(zweck)[:40]),
    }


def parse_dkb_giro(path: str | Path, konto="DKB-Giro") -> list[dict]:
    """DKB-Girokonto-CSV (UTF-8, ';', Kopfzeilen oben)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.startswith('"Buchungsdatum"'))
    rdr = csv.reader(io.StringIO("".join(lines[start:])), delimiter=";", quotechar='"')
    next(rdr)  # Header
    out = []
    for r in rdr:
        if len(r) < 9 or not r[0].strip():
            continue
        empf = _norm(r[4]) if _num(r[8]) and _num(r[8]) < 0 else _norm(r[3])
        out.append(_buchung("dkb", konto, r[0], _num(r[8]), empf or _norm(r[3]),
                            r[5], iban_gegen=r[7], vorgang=r[6], ref=(r[11] if len(r) > 11 else "")))
    return out


def parse_comdirect(path: str | Path, konto: str) -> list[dict]:
    """comdirect-CSV (Latin-1, ';'). Gegenpartei + IBAN stehen im Buchungstext."""
    lines = Path(path).read_text(encoding="latin-1").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.startswith('"Buchungstag"'))
    rdr = csv.reader(io.StringIO("".join(lines[start:])), delimiter=";", quotechar='"')
    next(rdr)
    out = []
    for r in rdr:
        if len(r) < 5 or not r[0].strip():
            continue
        text = _norm(r[3])
        iban = (re.search(r"(DE\d{20})", text) or [None])[0] if re.search(r"(DE\d{20})", text) else ""
        gm = re.search(r"(?:Auftraggeber|Empf\w*nger)\s*:\s*(.+?)(?:Kto/IBAN|Buchungstext|Ref\.|$)", text)
        gegen = _norm(gm.group(1)) if gm else text[:60]
        out.append(_buchung("comdirect", konto, r[0], _num(r[4]), gegen, text,
                            iban_gegen=iban or "", vorgang=r[2], ref=text[-24:]))
    return out


def parse_amazon_visa(path: str | Path, konto="Amazon-Visa") -> list[dict]:
    """Amazon-Visa-Umsätze (altes .xls, via xlrd)."""
    import xlrd

    sh = xlrd.open_workbook(str(path)).sheet_by_index(0)
    hdr = next(r for r in range(sh.nrows) if str(sh.cell_value(r, 0)).strip() == "Datum")
    out = []
    for r in range(hdr + 1, sh.nrows):
        datum = str(sh.cell_value(r, 0)).strip()
        if not datum:
            continue
        betr = _num(str(sh.cell_value(r, 6)))
        if betr is None:
            continue
        desc = _norm(sh.cell_value(r, 3))
        bank_kat = _norm(str(sh.cell_value(r, 4)) + " / " + str(sh.cell_value(r, 5)))
        out.append(_buchung("amazon", konto, datum, betr, desc, bank_kat, ref=desc))
    return out
