"""Lädt lokale, personenbezogene Konfiguration aus haushaltskasse/data/lokale_config.json.

Diese Datei liegt im gitignorten data/-Verzeichnis und enthält:
  * eigene_ibans          – Liste der eigenen Konto-IBANs (für Umbuchungs-Erkennung)
  * halter_regex          – Muster für den/die Kontoinhaber
  * kinder_regex          – Muster für die Kinder (damit deren Konten nicht als Umbuchung gelten)
  * persoenliche_regeln   – Kategorisierungs-Regeln mit Personenbezug (Vorrang vor STARTER_RULES)

Vorlage: workflows/lokale_config.example.json. Ohne die Datei läuft alles weiter,
nur ohne Personenbezug (weniger Umbuchungen automatisch erkannt).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_PFAD = Path(__file__).resolve().parent.parent / "data" / "lokale_config.json"


def lade_lokale_config() -> dict:
    cfg = json.loads(_PFAD.read_text(encoding="utf-8")) if _PFAD.exists() else {}
    persoenlich = [
        (re.compile(r["muster"], re.I), r["kategorie"], r["unterkategorie"])
        for r in cfg.get("persoenliche_regeln", [])
    ]
    return {
        "eigene_ibans": set(cfg.get("eigene_ibans", [])),
        "halter": re.compile(cfg["halter_regex"], re.I) if cfg.get("halter_regex") else None,
        "kinder": re.compile(cfg["kinder_regex"], re.I) if cfg.get("kinder_regex") else None,
        "persoenliche_regeln": persoenlich,
        "_vorhanden": _PFAD.exists(),
    }
