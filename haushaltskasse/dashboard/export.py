"""CSV-Export für alle vier Sichten (#34/O2 erweitert).

Excel-tauglich: Semikolon als Trenner, UTF-8 **mit BOM** (sonst zerlegt Excel die Umlaute)
und deutsche Dezimalkommas ohne Tausenderpunkt (sonst liest Excel Beträge als Text).

Die Exporte spiegeln bewusst die jeweilige Bildschirm-Sicht inklusive Abschnitten und
Summenzeilen — nicht die rohen Tabellen.
"""
from __future__ import annotations

import csv
import io

from fastapi.responses import StreamingResponse

Zeile = list[object]


def euro(cent) -> str:
    """Cent -> '1234,56' (deutsches Dezimalkomma, kein Tausenderpunkt -> Excel erkennt es als Zahl)."""
    return f"{(cent or 0) / 100:.2f}".replace(".", ",")


def antwort(zeilen: list[Zeile], dateiname: str) -> StreamingResponse:
    buf = io.StringIO()
    schreiber = csv.writer(buf, delimiter=";", lineterminator="\r\n",
                           quoting=csv.QUOTE_MINIMAL)
    for z in zeilen:
        schreiber.writerow(z)
    daten = ("﻿" + buf.getvalue()).encode("utf-8")      # BOM für Excel
    return StreamingResponse(
        io.BytesIO(daten), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'})


# ---------------------------------------------------------------------------
def uebersicht_zeilen(u: dict, stand: str) -> list[Zeile]:
    z: list[Zeile] = [["Haushaltskasse — Übersicht", f"Stand {stand}"], []]

    z.append(["Kennzahl", "Betrag €"])
    z.append(["Freier Haushalts-Saldo (Liquidität nach Reservierungen)", euro(u["saldo_cent"])])
    z.append(["Realsaldo (echtes Geld auf allen Konten)", euro(u["realsaldo_cent"])])
    z.append(["Rücklagen gebunden", euro(u["ruecklagen_cent"])])
    z.append(["Forderungen (Natalie/Jörg)", euro(u["forderung_cent"])])
    z += [[], ["Konten", "Betrag €"]]
    for k in u["konten"]:
        z.append([k["name"], euro(k["saldo_cent"])])
    z.append(["Summe Konten", euro(u["konten_cent"])])

    z += [[], ["Rücklagen-Topf", "Ist €"]]
    for t in u["ruecklagen_toepfe"]:
        z.append([t["name"], euro(t["ist_cent"])])
    z.append(["Summe Rücklagen", euro(u["ruecklagen_cent"])])

    z += [[], ["Forderung", "Ist €"]]
    for f in u["forderungen"]:
        z.append([f["name"], euro(f["ist_cent"])])

    z += [[], ["Posten im Saldo", "Wert €", "Notiz"]]
    for p in u["posten_saldo"]:
        z.append([p["name"], euro(p["wert_cent"]), p.get("notiz") or ""])
    z.append(["Summe Posten im Saldo", euro(u["posten_saldo_summe_cent"]), ""])

    z += [[], ["Merkzettel", "Wert €", "Notiz"]]
    for m in u["merkzettel"]:
        z.append([m["name"], euro(m["wert_cent"]), m.get("notiz") or ""])
    z.append(["Summe Merkzettel", euro(u["merkzettel_summe_cent"]), ""])

    z += [[], ["Langfristig (NICHT im Haushalts-Saldo)", "Wert €", "Notiz"]]
    for p in u["posten_langfrist"]:
        z.append([p["name"], euro(p["wert_cent"]), p.get("notiz") or ""])
    z.append(["Summe langfristig", euro(u["langfrist_cent"]), ""])
    return z


def ruecklagen_zeilen(baum: list[dict], stand: str) -> list[Zeile]:
    z: list[Zeile] = [["Haushaltskasse — Rücklagen", f"Stand {stand}"], []]
    z.append(["Ebene", "Nebenbuch", "Unterkategorie", "Soll monatlich €", "Ist Topf €"])
    soll_ges = ist_ges = 0
    for k in baum:
        z.append(["Nebenbuch", k["name"], "", euro(k["soll_cent"]), euro(k["ist_cent"])])
        soll_ges += k["soll_cent"]
        ist_ges += k["ist_cent"]
        for u in k["unterkategorien"]:
            z.append(["  Untertopf", k["name"], u["name"], euro(u["soll_cent"]), euro(u["ist_cent"])])
    z.append([])
    z.append(["Summe", "", "", euro(soll_ges), euro(ist_ges)])
    return z


def pivot_zeilen(p: dict, titel: str, stand: str) -> list[Zeile]:
    z: list[Zeile] = [[f"Haushaltskasse — Reports ({titel})", f"Stand {stand}"], []]
    kopf: Zeile = ["Kategorie/Unterkategorie"] + list(p["monate"]) + ["Summe €"]
    z.append(kopf)
    for zeile in p["zeilen"]:
        werte = [euro(zeile["monate"].get(m, 0)) for m in p["monate"]]
        z.append([zeile["label"]] + werte + [euro(zeile["summe"])])
    z.append([])
    summen = [euro(p["spalten_summe"].get(m, 0)) for m in p["monate"]]
    z.append(["Summe"] + summen + [euro(p["gesamt"])])
    return z


def buchungen_zeilen(rows: list[dict], gesamt: int, summen: dict, stand: str) -> list[Zeile]:
    z: list[Zeile] = [["Haushaltskasse — Buchungen", f"Stand {stand}", f"{gesamt} Treffer"], []]
    z.append(["Datum", "Konto", "Art", "Kategorie", "Unterkategorie", "Empfänger",
              "Verwendungszweck", "Betrag €", "Bemerkung"])
    for r in rows:
        z.append([str(r["datum"]), r["konto"] or "", r["buchungsart"], r["kategorie"] or "",
                  r["unterkategorie"] or "", r["empfaenger"] or "", r["verwendungszweck"] or "",
                  euro(r["betrag_cent"]), r["bemerkung"] or ""])
    z.append([])
    z.append(["", "", "", "", "", "", f"Netto ({gesamt} Treffer)",
              euro(summen["netto_cent"]), ""])
    if "einnahmen_cent" in summen:
        z.append(["", "", "", "", "", "", "davon Einnahmen", euro(summen["einnahmen_cent"]), ""])
    if "ausgaben_cent" in summen:
        z.append(["", "", "", "", "", "", "davon Ausgaben", euro(summen["ausgaben_cent"]), ""])
    return z
