"""CSV-Export je Sicht (#34/O2). CSV statt xlsx: keine openpyxl-Abhängigkeit, und jede
Sicht exportiert exakt das, was auf dem Schirm steht (inkl. Filter, Abschnitte, Summen)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from .. import export as xp
from .. import queries as q
from ..helpers import db, parse_euro

router = APIRouter()


def _heute() -> str:
    return date.today().isoformat()


@router.get("/export/uebersicht.csv")
def export_uebersicht():
    with db() as conn, conn.cursor() as cur:
        u = q.uebersicht(cur)
    return xp.antwort(xp.uebersicht_zeilen(u, _heute()), "uebersicht.csv")


@router.get("/export/ruecklagen.csv")
def export_ruecklagen():
    with db() as conn, conn.cursor() as cur:
        baum = q.ruecklagen_baum(cur)
    return xp.antwort(xp.ruecklagen_zeilen(baum, _heute()), "ruecklagen.csv")


@router.get("/export/reports.csv")
def export_reports(von: str = "", bis: str = "", modus: str = "ausgabe",
                   ebene: str = "kategorie"):
    """Gleiche Parameter wie /reports — der Export folgt der eingestellten Pivot-Sicht."""
    if modus not in ("ausgabe", "einnahme", "netto"):
        modus = "ausgabe"
    if ebene not in ("kategorie", "unterkategorie"):
        ebene = "kategorie"
    with db() as conn, conn.cursor() as cur:
        stichtag = q.stichtag(cur)
        p = q.pivot(cur, von=von or stichtag, bis=bis or None, modus=modus, ebene=ebene)
    titel = f"{modus}, je {ebene}"
    return xp.antwort(xp.pivot_zeilen(p, titel, _heute()), "reports.csv")


@router.get("/export/buchungen.csv")
def export_buchungen(konto: str = "", kategorie_id: str = "", unterkategorie_id: str = "",
                     offen: str = "", suche: str = "", von: str = "", bis: str = "",
                     betrag_min: str = "", betrag_max: str = "", alle: str = "",
                     sort: str = "datum", richtung: str = "desc"):
    """Die (gefilterte) Buchungsliste als CSV. Gleiche Filter wie /buchungen."""
    kid = int(kategorie_id) if kategorie_id.isdigit() else None
    uid = int(unterkategorie_id) if unterkategorie_id.isdigit() else None
    bmin = parse_euro(betrag_min) if betrag_min.strip() else None
    bmax = parse_euro(betrag_max) if betrag_max.strip() else None
    if sort not in q.SORT_SPALTEN:
        sort = "datum"
    richtung = "asc" if richtung == "asc" else "desc"
    with db() as conn, conn.cursor() as cur:
        rows, gesamt, summen = q.buchungen(
            cur, konto=konto or None, kategorie_id=kid, unterkategorie_id=uid,
            nur_offen=(offen == "1"), suche=suche or None, von=von or None, bis=bis or None,
            betrag_min_cent=bmin, betrag_max_cent=bmax, nur_reale_konten=(alle != "1"),
            sort=sort, richtung=richtung, limit=100000, offset=0)
    return xp.antwort(xp.buchungen_zeilen(rows, gesamt, summen, _heute()), "buchungen.csv")
