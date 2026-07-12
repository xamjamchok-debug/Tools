import hashlib
from pathlib import Path

import chardet
import pandas as pd


def detect_encoding(filepath: str | Path) -> str:
    with open(filepath, "rb") as f:
        raw = f.read(10_000)
    return chardet.detect(raw).get("encoding") or "utf-8"


def parse_dkb_csv(filepath: str | Path) -> pd.DataFrame:
    """DKB-CSV importieren. Überspringt Bank-Header, normalisiert Datumsfelder."""
    enc = detect_encoding(filepath)
    with open(filepath, encoding=enc, errors="replace") as f:
        lines = f.readlines()

    # DKB-CSV hat Metadatenzeilen oben; Daten beginnen nach der Kopfzeile
    start = next(
        (i for i, l in enumerate(lines) if "Wertstellung" in l or "Buchungstag" in l), 0
    )
    df = pd.read_csv(
        filepath,
        encoding=enc,
        sep=";",
        skiprows=start,
        decimal=",",
        thousands=".",
        on_bad_lines="skip",
    )
    df.columns = [c.strip() for c in df.columns]
    df = _normalize_dates(df)
    df["_hash"] = df.apply(_row_hash, axis=1)
    return df


def parse_generic_csv(filepath: str | Path, sep: str = ";") -> pd.DataFrame:
    enc = detect_encoding(filepath)
    df = pd.read_csv(filepath, encoding=enc, sep=sep, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    df["_hash"] = df.apply(_row_hash, axis=1)
    return df


def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if any(kw in col.lower() for kw in ("datum", "date", "stellung")):
            try:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
            except Exception:
                pass
    return df


def _row_hash(row: pd.Series) -> str:
    return hashlib.sha256(str(row.values).encode()).hexdigest()[:16]
