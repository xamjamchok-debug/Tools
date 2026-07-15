"""Backlog #46/#28: Unterkategorien auf sprechende Klarnamen konsolidieren.

Führt die historisch gewachsenen Unterkategorien (Excel-Kürzel `S-Vers`, Case-Dubletten
`abo`/`Abo`, Einzel-Abos als eigene Unterkategorie) auf die Zielstruktur aus
`docs/unterkategorien-vorschlag.md` zusammen und legt die Erkennungsmuster als
`mapping_regeln` ab.

Ablauf (jede Phase idempotent, Default = Trockenlauf):

    1. `--phase struktur`  Zielunterkategorien anlegen, Altnamen zusammenführen
                           (Buchungen umhängen, leere Alt-Unterkategorie löschen).
    2. `--phase regeln`    Empfänger-Muster als `mapping_regeln` schreiben.
    3. `--phase apply`     Regeln retroaktiv auf die Historie anwenden
                           (respektiert `unterkat_pinned`).

    python -m haushaltskasse.workflows.unterkategorien --phase struktur
    python -m haushaltskasse.workflows.unterkategorien --phase struktur --write

Vorher ein Backup ziehen — Phase 1 hängt Buchungen um und löscht Unterkategorien.
Beträge stehen bewusst NICHT in diesem Modul: die Soll-Werte werden nachgelagert aus
den dann korrekt zugeordneten Buchungen berechnet (`untertoepfe.py`).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from ..storage import db

# ---------------------------------------------------------------------------
# Zielstruktur je Nebenbuch (Klarnamen, keine H-/R-/S-Präfixe).
# "Allgemein" bleibt überall als Sammel-/Anspartopf bestehen.
# ---------------------------------------------------------------------------
ZIEL: dict[str, list[str]] = {
    "Auto": [
        "Tanken", "Parken", "Knöllchen", "KFZ-Steuer", "Reparatur & Werkstatt",
        "Finanzierung/Leasing", "Zweirad", "Mietwagen", "Anschaffung",
    ],
    "Vers": [
        "KFZ-Versicherung", "Haftpflicht", "Hausrat", "Rechtsschutz",
        "Leben/BU (RLV)", "Gebäude", "Sonstige Versicherung",
    ],
    "Nebenkosten": [
        "Wasser/Abwasser", "Strom", "Grundsteuer", "Müll", "Schornsteinfeger",
    ],
    "Sport": ["Fitnessstudio", "Verein/Mitgliedschaft", "Kurse & Training", "Ausrüstung"],
    "Telefon": [
        "Mobilfunk & Internet", "Streaming & Software", "Rundfunkbeitrag",
        "Zeitung/Medien", "sonstige Abos",
    ],
    "Inst": [
        "Handwerker", "PV/Solar", "Möbel & Einrichtung", "Baumaterial",
        "Garten & Außenanlage", "sonstige Anschaffung",
    ],
    "TK": ["Private KV (DKV)", "Krankenkasse (TK)", "Apotheke", "Arzt & Zahnarzt"],
    "Kredit": ["Immobilienkredit (Deutsche Bank)", "KfW-Darlehen", "Autokredit", "Zinsen"],
    # Urlaub: pro Reise (User 2026-07-15) -> Reise-Unterkategorien entstehen laufend,
    # hier nur der neutrale Anspartopf. Bestehende Reise-Namen bleiben unangetastet.
    "Urlaub": ["Urlaub allgemein"],
}

# ---------------------------------------------------------------------------
# Zusammenführung: alter Unterkategorie-Name -> Zielname (je Nebenbuch).
# Case-insensitiver Abgleich. Nicht gelistete Altnamen bleiben unangetastet und
# werden am Ende als "offen" gemeldet (bewusst: lieber stehenlassen als falsch mergen).
# ---------------------------------------------------------------------------
MERGE: dict[str, dict[str, str]] = {
    "Auto": {
        "Tanken": "Tanken",
        "Parken": "Parken",
        "Knöllchen": "Knöllchen",
        "KFZ-Steuer": "KFZ-Steuer",
        "Autokredit": "Finanzierung/Leasing",
        "Anschaffung/Leasing": "Finanzierung/Leasing",
        "Roller, Rad": "Zweirad",
    },
    "Vers": {
        "AutoVers": "KFZ-Versicherung",
        "Haftpflicht": "Haftpflicht",
        "Hausrat": "Hausrat",
        "Gebäude": "Gebäude",
        "RLV": "Leben/BU (RLV)",
        "zurich": "Leben/BU (RLV)",
        "Envivas": "Sonstige Versicherung",
        "H-Vers": "Sonstige Versicherung",
    },
    "Nebenkosten": {
        "Abwasser": "Wasser/Abwasser",
        "Trinkwasser": "Wasser/Abwasser",
        "Strom": "Strom",
        "Grundsteuer": "Grundsteuer",
        "Müll": "Müll",
        "Schornsteinfeger": "Schornsteinfeger",
    },
    "Sport": {
        "Verein/Fitness": "Fitnessstudio",
    },
    "Telefon": {
        "DSL": "Mobilfunk & Internet",
        "Handy": "Mobilfunk & Internet",
        "Mobilfunk/Festnetz": "Mobilfunk & Internet",
        "web.de": "Mobilfunk & Internet",
        "web": "Mobilfunk & Internet",
        "gez": "Rundfunkbeitrag",
        "spiegel": "Zeitung/Medien",
        "Tagesspiegel": "Zeitung/Medien",
        # Einzel-Abos -> ein Topf
        "abo": "sonstige Abos",
        "Abo": "sonstige Abos",
        "Abo/Medien": "sonstige Abos",
        "SW": "Streaming & Software",
        "adobe": "Streaming & Software",
        "google": "Streaming & Software",
        "chatgpt": "Streaming & Software",
        "ms 365": "Streaming & Software",
        "Audible": "Streaming & Software",
        "Kindle unlimited": "Streaming & Software",
        "Amazon Music unlimited": "Streaming & Software",
        "Ultra Chords": "Streaming & Software",
        "Video": "Streaming & Software",
    },
    "Inst": {
        "Garten": "Garten & Außenanlage",
    },
    "TK": {
        "Apotheke": "Apotheke",
        "Krankenversicherung": "Krankenkasse (TK)",
    },
    "Kredit": {
        "deuba": "Immobilienkredit (Deutsche Bank)",
        "kfw": "KfW-Darlehen",
        "Autokredit": "Autokredit",
        "Zinsen": "Zinsen",
    },
    "Urlaub": {
        "Freizeit/Reise": "Urlaub allgemein",
    },
}

# ---------------------------------------------------------------------------
# Erkennungsmuster -> (Nebenbuch, Zielunterkategorie). Teilstring, case-insensitiv.
# Bewusst nur Firmen/Institutionen — keine Privatpersonen (die pflegt der Nutzer in der UI).
# Strom/Gas: Anbieter wechseln häufig (enewa -> Naturwerke -> Tibber -> RheinEnergie -> ...),
# deshalb möglichst breite Liste; der Anbietername ist KEIN stabiler Anker.
# ---------------------------------------------------------------------------
REGELN: list[tuple[str, str, str]] = [
    # --- Auto
    # Achtung Teilstring-Fallen: 'esso' steckt in "Espresso", 'arag' in "Garage",
    # 'eon ' in "Leon " -> solche Muster nur in eindeutiger Langform aufnehmen.
    ("shell", "Auto", "Tanken"), ("aral", "Auto", "Tanken"), ("esso station", "Auto", "Tanken"),
    ("agip", "Auto", "Tanken"), ("tankstelle", "Auto", "Tanken"),
    ("apcoa", "Auto", "Parken"), ("contipark", "Auto", "Parken"), ("q-park", "Auto", "Parken"),
    ("parkhaus", "Auto", "Parken"), ("parkgebühr", "Auto", "Parken"),
    ("paybyphone", "Auto", "Parken"), ("easypark", "Auto", "Parken"),
    ("bundeskasse", "Auto", "KFZ-Steuer"),
    # --- Versicherung
    ("adac autovers", "Vers", "KFZ-Versicherung"), ("huk24", "Vers", "Haftpflicht"),
    ("huk-coburg-lebens", "Vers", "Leben/BU (RLV)"),
    ("zurich deutscher herold", "Vers", "Leben/BU (RLV)"),
    ("provinzial", "Vers", "Gebäude"), ("arag se", "Vers", "Rechtsschutz"),
    ("hansemerkur", "Vers", "Sonstige Versicherung"),
    ("adac zuhause", "Vers", "Sonstige Versicherung"),
    # --- Nebenkosten (Stromanbieter wechseln staendig -> breite Liste)
    ("enewa", "Nebenkosten", "Wasser/Abwasser"),
    ("naturwerke", "Nebenkosten", "Strom"), ("tibber", "Nebenkosten", "Strom"),
    ("rheinenergie", "Nebenkosten", "Strom"), ("octopus", "Nebenkosten", "Strom"),
    ("vattenfall", "Nebenkosten", "Strom"), ("maingau", "Nebenkosten", "Strom"),
    ("e.on", "Nebenkosten", "Strom"), ("stadtwerke", "Nebenkosten", "Strom"),
    ("rsag", "Nebenkosten", "Müll"), ("abfallwirtschaft", "Nebenkosten", "Müll"),
    ("schornsteinfeger", "Nebenkosten", "Schornsteinfeger"),
    # --- Sport
    ("judo club", "Sport", "Verein/Mitgliedschaft"),
    ("sportverein", "Sport", "Verein/Mitgliedschaft"),
    ("fitpark", "Sport", "Fitnessstudio"), ("healthcity", "Sport", "Fitnessstudio"),
    ("powerplate", "Sport", "Fitnessstudio"),
    # --- Telefon/Medien
    ("telekom", "Telefon", "Mobilfunk & Internet"),
    ("telefonica", "Telefon", "Mobilfunk & Internet"),
    ("vodafone", "Telefon", "Mobilfunk & Internet"),
    ("1+1 mail", "Telefon", "Mobilfunk & Internet"),
    ("congstar", "Telefon", "Mobilfunk & Internet"),
    ("rundfunk", "Telefon", "Rundfunkbeitrag"),
    ("beitragsservice", "Telefon", "Rundfunkbeitrag"),
    ("westdeutscher rundfunk", "Telefon", "Rundfunkbeitrag"),
    ("netflix", "Telefon", "Streaming & Software"), ("spotify", "Telefon", "Streaming & Software"),
    ("adobe", "Telefon", "Streaming & Software"), ("audible", "Telefon", "Streaming & Software"),
    ("anthropic", "Telefon", "Streaming & Software"), ("microsoft", "Telefon", "Streaming & Software"),
    ("google play", "Telefon", "Streaming & Software"),
    ("amazon digital", "Telefon", "Streaming & Software"),
    ("amazon media", "Telefon", "Streaming & Software"),
    ("youtube", "Telefon", "Streaming & Software"),
    ("spiegel", "Telefon", "Zeitung/Medien"), ("tagesspiegel", "Telefon", "Zeitung/Medien"),
    ("general-anzeiger", "Telefon", "Zeitung/Medien"),
    # --- TK
    ("dkv", "TK", "Private KV (DKV)"),
    ("techniker krankenkasse", "TK", "Krankenkasse (TK)"),
    ("apotheke", "TK", "Apotheke"),
    # --- Kredit
    ("kfw", "Kredit", "KfW-Darlehen"),
    ("deutsche bank", "Kredit", "Immobilienkredit (Deutsche Bank)"),
]


# ---------------------------------------------------------------------------
def _kat_ids(cur) -> dict[str, int]:
    cur.execute("SELECT name, id FROM kategorien")
    return {n: i for n, i in cur.fetchall()}


def _ukat_index(cur) -> dict[int, dict[str, int]]:
    """kategorie_id -> {lower(name): id}"""
    cur.execute("SELECT kategorie_id, name, id FROM unterkategorien")
    idx: dict[int, dict[str, int]] = defaultdict(dict)
    for kid, name, uid in cur.fetchall():
        idx[kid][name.strip().lower()] = uid
    return idx


def _hole_oder_lege_an(cur, kid: int, name: str, write: bool, idx) -> int | None:
    vorhanden = idx[kid].get(name.strip().lower())
    if vorhanden:
        return vorhanden
    if not write:
        print(f"      + neu anlegen: {name!r}")
        return None
    cur.execute(
        """INSERT INTO unterkategorien (kategorie_id, name, quelle) VALUES (%s,%s,'manuell')
           ON CONFLICT (kategorie_id, name) DO NOTHING RETURNING id""",
        (kid, name),
    )
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT id FROM unterkategorien WHERE kategorie_id=%s AND name=%s", (kid, name))
        row = cur.fetchone()
    idx[kid][name.strip().lower()] = row[0]
    print(f"      + angelegt: {name!r} (id={row[0]})")
    return row[0]


def phase_struktur(conn, write: bool) -> None:
    """Zielunterkategorien anlegen + Altnamen zusammenführen."""
    with conn.cursor() as cur:
        kats = _kat_ids(cur)
        idx = _ukat_index(cur)
        offen: list[str] = []

        for katname, ziele in ZIEL.items():
            kid = kats.get(katname)
            if not kid:
                print(f"  ! Kategorie {katname!r} existiert nicht — übersprungen")
                continue
            print(f"\n  === {katname} ===")
            for z in ziele:
                _hole_oder_lege_an(cur, kid, z, write, idx)

            merge = {k.lower(): v for k, v in MERGE.get(katname, {}).items()}
            cur.execute(
                """SELECT id, name, monatliche_ruecklage_cent FROM unterkategorien
                   WHERE kategorie_id=%s ORDER BY name""", (kid,))
            for uid, uname, _soll in cur.fetchall():
                low = uname.strip().lower()
                ziel = merge.get(low)
                if ziel is None:
                    if low not in {z.lower() for z in ziele} and low != "allgemein":
                        offen.append(f"{katname}/{uname}")
                    continue
                if ziel.lower() == low:
                    continue                      # Name schon korrekt
                ziel_id = idx[kid].get(ziel.lower())
                if not ziel_id:
                    if not write:
                        print(f"      ~ {uname!r} -> {ziel!r} (Ziel wird in --write angelegt)")
                    continue
                if ziel_id == uid:
                    continue
                cur.execute("SELECT COUNT(*) FROM buchungen WHERE unterkategorie_id=%s", (uid,))
                n = cur.fetchone()[0]
                print(f"      ~ {uname!r} -> {ziel!r}  ({n} Buchungen umhängen)")
                if write:
                    cur.execute(
                        "UPDATE buchungen SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                        (ziel_id, uid))
                    cur.execute(
                        "UPDATE mapping_regeln SET unterkategorie_id=%s WHERE unterkategorie_id=%s",
                        (ziel_id, uid))
                    cur.execute(
                        "UPDATE kategorien SET default_unterkategorie_id=%s WHERE default_unterkategorie_id=%s",
                        (ziel_id, uid))
                    cur.execute("DELETE FROM unterkategorien WHERE id=%s", (uid,))
                    # pop statt del: Case-Dubletten ('abo' und 'Abo') teilen sich denselben
                    # kleingeschriebenen Index-Schlüssel — der zweite Merge fände ihn sonst nicht mehr.
                    idx[kid].pop(low, None)

        if offen:
            print("\n  --- unangetastet (kein Merge-Ziel definiert, bitte prüfen) ---")
            for o in sorted(offen):
                print(f"      ? {o}")


def phase_regeln(conn, write: bool) -> None:
    """Erkennungsmuster als mapping_regeln ablegen (idempotent)."""
    with conn.cursor() as cur:
        kats = _kat_ids(cur)
        idx = _ukat_index(cur)
        neu = akt = fehlt = 0
        for pattern, katname, ukatname in REGELN:
            kid = kats.get(katname)
            if not kid:
                fehlt += 1
                continue
            uid = idx[kid].get(ukatname.lower())
            if not uid:
                print(f"    ! {pattern!r}: Zielunterkategorie {katname}/{ukatname!r} fehlt "
                      f"(erst Phase 'struktur' schreiben)")
                fehlt += 1
                continue
            cur.execute("SELECT id, unterkategorie_id FROM mapping_regeln "
                        "WHERE pattern_typ='empfaenger' AND pattern=%s", (pattern,))
            row = cur.fetchone()
            if row and row[1] == uid:
                akt += 1
                continue
            if not write:
                print(f"    + {pattern!r} -> {katname}/{ukatname}")
                neu += 1
                continue
            cur.execute(
                """INSERT INTO mapping_regeln (pattern_typ, pattern, kategorie_id,
                       unterkategorie_id, quelle, status)
                   VALUES ('empfaenger', %s, %s, %s, 'manuell', 'aktiv')
                   ON CONFLICT (pattern_typ, pattern)
                   DO UPDATE SET kategorie_id=EXCLUDED.kategorie_id,
                                 unterkategorie_id=EXCLUDED.unterkategorie_id,
                                 status='aktiv'""",
                (pattern, kid, uid))
            neu += 1
        print(f"\n  Regeln: {neu} neu/aktualisiert · {akt} unverändert · {fehlt} ohne Ziel")


def phase_apply(conn, write: bool) -> None:
    """Regeln retroaktiv anwenden. Gepinnte Unterkategorien bleiben unberührt."""
    with conn.cursor() as cur:
        cur.execute("""SELECT r.pattern, r.kategorie_id, r.unterkategorie_id, k.name, u.name
                       FROM mapping_regeln r
                       JOIN kategorien k ON k.id = r.kategorie_id
                       JOIN unterkategorien u ON u.id = r.unterkategorie_id
                       WHERE r.status='aktiv' AND r.pattern_typ='empfaenger'
                       ORDER BY length(r.pattern) DESC""")
        regeln = cur.fetchall()
        if not regeln:
            print("  Keine aktiven Regeln — erst Phase 'regeln' laufen lassen.")
            return
        gesamt = 0
        for pattern, kid, uid, katname, ukatname in regeln:
            cur.execute(
                """SELECT COUNT(*) FROM buchungen
                   WHERE empfaenger ILIKE %s AND NOT unterkat_pinned
                     AND (unterkategorie_id IS DISTINCT FROM %s)
                     AND buchungsart IN ('real','ruecklage')""",
                (f"%{pattern}%", uid))
            n = cur.fetchone()[0]
            if not n:
                continue
            print(f"    {pattern:<28} -> {katname}/{ukatname:<26} {n:>4} Buchungen")
            gesamt += n
            if write:
                cur.execute(
                    """UPDATE buchungen SET unterkategorie_id=%s, kategorie_id=%s
                       WHERE empfaenger ILIKE %s AND NOT unterkat_pinned
                         AND (unterkategorie_id IS DISTINCT FROM %s)
                         AND buchungsart IN ('real','ruecklage')""",
                    (uid, kid, f"%{pattern}%", uid))
                cur.execute("""UPDATE mapping_regeln SET treffer_count = treffer_count + %s,
                                      last_used = now()
                               WHERE pattern_typ='empfaenger' AND pattern=%s""", (n, pattern))
        print(f"\n  Summe: {gesamt} Buchungen betroffen")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Unterkategorien konsolidieren (#46)")
    ap.add_argument("--phase", choices=["struktur", "regeln", "apply"], required=True)
    ap.add_argument("--write", action="store_true", help="Änderungen wirklich schreiben")
    args = ap.parse_args(argv)

    modus = "SCHREIBEN" if args.write else "TROCKENLAUF (nichts wird geändert)"
    print(f"=== Phase {args.phase!r} — {modus} ===")

    conn = db.connect()
    try:
        {"struktur": phase_struktur, "regeln": phase_regeln, "apply": phase_apply}[args.phase](
            conn, args.write)
        if args.write:
            conn.commit()
            print("\n>>> committed.")
        else:
            conn.rollback()
            print("\n>>> Trockenlauf beendet — mit --write ausführen.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
