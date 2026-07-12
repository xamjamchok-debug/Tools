"""Abgrenzung: bestimmt die Buchungsart, damit Umbuchungen und Depot-Bewegungen
nicht als Ausgaben doppelt/falsch zählen.

Ergebnis je Buchung:
    'real'       echte Ein-/Ausgabe (zählt)
    'umbuchung'  Transfer zwischen eigenen Konten (zählt NICHT als Ausgabe)
    'wertpapier' Depot-/ETF-Bewegung (zählt NICHT als Haushaltsausgabe)
    'zinsen'     Kontoabschluss/Habenzinsen (Einnahme)

Die Liste der EIGENEN IBANs kommt von außen (aus der lokalen Konfiguration bzw. der
konten-Tabelle) — sie wird bewusst NICHT im Code hinterlegt (Datenschutz).
"""
from __future__ import annotations

import re

_FIRMA = re.compile(r"gmbh|\bag\b|e\.?\s?v\.?|autohaus|club|kasse|amazon|paypal|tankstelle", re.I)


def bestimme_buchungsart(b: dict, eigene_ibans: set[str], halter: re.Pattern | None = None,
                         kinder: re.Pattern | None = None) -> str:
    """halter/kinder-Muster kommen aus der lokalen Config (Personenbezug bleibt lokal).
    Ohne halter greift nur die IBAN-/Keyword-Erkennung (Regeln 1 und 2)."""
    z = f"{b['verwendungszweck']} {b['empfaenger']}".lower()
    vg = b["vorgang"].lower()

    if "wertpapier" in vg or "wpknr" in z or "isin" in z:
        return "wertpapier"
    if "kontoabschluss" in vg or "abschluss zinsen" in z:
        return "zinsen"

    # 1) sicher: Gegenkonto ist ein eigenes Konto
    if b["iban_gegen"] and b["iban_gegen"] in eigene_ibans:
        return "umbuchung"
    # 2) sicher: expliziter Übertrag auf eigenes Giro/Tagesgeld/Depot
    if re.search(r"uebertrag auf (das )?(giro|tagesgeld|depot)|umzug auf tagesgeld|\bdepot\b", z):
        return "umbuchung"
    # 3) plausibel: Übertrags-Vorgang und Gegenpart ist der Inhaber selbst (kein Kind, keine Firma)
    if halter and ("übertrag" in vg or "kontoübertrag" in vg):
        name = b["empfaenger"].lower()
        ist_kind = bool(kinder and kinder.search(name))
        if halter.search(name) and not ist_kind and not _FIRMA.search(name):
            return "umbuchung"
    return "real"
