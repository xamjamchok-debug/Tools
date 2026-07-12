"""Regelbasierte Erstkategorisierung: Buchung -> (Kategorie, Unterkategorie).

STARTER_RULES sind generische Händler-/Muster-Regeln (kein Personenbezug) und dürfen
ins Repo. Persönliche Regeln (z. B. Namen der Kinder für 'Taschengeld/Sparen') werden
zur Laufzeit aus der lokalen Konfiguration ergänzt und VOR den Starter-Regeln geprüft.

Ist keine Regel sicher, wird (None, None) geliefert -> Fall landet im Review, wo die KI
vorschlägt und der Nutzer annimmt/ablehnt/umdefiniert. Bestätigungen werden zu neuen Regeln.
"""
from __future__ import annotations

import re

# (Muster, Kategorie, Unterkategorie) — Reihenfolge = Priorität, erste Übereinstimmung gewinnt.
STARTER_RULES: list[tuple[str, str, str]] = [
    # Lebensmittel / Drogerie / Alltag
    (r"lidl|edeka|aldi|rewe|kaufland|penny|netto|sch[aä]fer|stadtbrotb[aä]cker|b[aä]cker|obsthof", "Haushaltskasse", "Lebensmittel"),
    (r"dm.?drogerie|drogerie|m[uü]e?ller wachtberg", "Haushaltskasse", "Drogerie"),
    (r"sumup|restaurant|café|cafe|imbiss", "Haushaltskasse", "Auswärts"),
    (r"deutsche post|dhl|hermes", "Haushaltskasse", "Porto/Versand"),
    # Auto
    (r"aral|agip|bft|shell|esso|tankstelle|tanken", "Auto", "Tanken"),
    (r"easypark|parkhaus|parken", "Auto", "Parken"),
    (r"autohaus|opel|peugeot|leasing|kfz-steuer", "Auto", "Anschaffung/Leasing"),
    (r"adac", "Auto", "ADAC"),
    # Kinder / Schule / Betreuung
    (r"elternbeitr[aä]ge ogs|katholische jugendagentur|kjf|\bogs\b|lernstudio|kiga|essensgeld", "Füchschen", "Schule/Betreuung"),
    (r"familienkasse|kindergeld", "Füchschen", "Kindergeld (Einnahme)"),
    # Sport / Freizeit / Urlaub
    (r"judo|fitness|habermann|sportverein", "Sport", "Verein/Fitness"),
    (r"booking\.com|fraport|erlebnispark|freizeitpark|grodo", "Urlaub", "Freizeit/Reise"),
    # Wohnen / Nebenkosten / Versicherung
    (r"schmutzwasser|abwasser|niederschlagswasser|enewa|trinkwasser|m[uü]ll|grundsteuer|strom|vattenfall", "Nebenkosten", "Ver-/Entsorgung"),
    (r"envivas|krankenvers", "TK", "Krankenversicherung"),
    (r"apotheke", "TK", "Apotheke"),
    (r"zurich|lebensvers|haftpflicht|hausrat|geb[aä]udevers|rlv", "Vers", "Versicherung"),
    # Telefon / Mobilfunk / Festnetz / Internet
    (r"telekom|telefonica|vodafone|\bo2\b|1&1|1und1|congstar", "Telefon", "Mobilfunk/Festnetz"),
    # Medien / Abos
    (r"general-anzeiger|tagesspiegel|\bfaz\b|spiegel|netflix|spotify|youtube|audible|adobe|1\+1 mail", "Telefon", "Abo/Medien"),
    # Amazon / Konsum
    (r"amazon|amzn", "Haushaltskasse", "Amazon/Konsum"),
    (r"paypal", "Haushaltskasse", "PayPal (unklar)"),
    # Kredit / Zinsen / Bonus (Entscheidungen 2026-07-12)
    (r"dkb ag.*abrechnung|kontoüberziehung|zinsen f[uü]r einger[aä]umte", "Kredit", "Zinsen"),
    (r"girokonto\W*pr[aä]mie|startgutschrift|eingel[oö]ste .*punkte", "Einnahmen", "Bonus"),
    (r"geb[uü]hr f[uü]r travel|kartengeb[uü]hr", "Haushaltskasse", "Kartengebühr"),
]


def _compile(rules):
    return [(re.compile(p, re.I), k, u) for p, k, u in rules]


_STARTER = _compile(STARTER_RULES)


def kategorisiere(b: dict, persoenliche_rules: list | None = None):
    """Gibt (kategorie, unterkategorie) zurück oder (None, None), wenn nichts sicher passt.

    persoenliche_rules: optionale, lokal geladene (kompilierte) Regeln mit Vorrang
    (z. B. Kinder-Namen -> Kinder/Taschengeld-Sparen).
    """
    text = f"{b['empfaenger']} {b['verwendungszweck']}"
    for pat, kat, unter in (persoenliche_rules or []):
        if pat.search(text):
            return kat, unter
    for pat, kat, unter in _STARTER:
        if pat.search(text):
            return kat, unter
    return None, None
