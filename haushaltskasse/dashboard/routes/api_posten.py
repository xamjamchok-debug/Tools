"""JSON-API für Vermögensposten (Posten im Saldo, Merkzettel, Langfrist)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..helpers import db, parse_euro

router = APIRouter()


class Posten(BaseModel):
    id: int | None = None
    name: str
    betrag: str
    art: str = "vermoegen"    # 'vermoegen' | 'schuld'
    notiz: str | None = None
    gruppe: str = "posten"    # 'posten' | 'merkzettel' (U1)


@router.post("/api/vermoegensposten")
def upsert_posten(p: Posten):
    cent = parse_euro(p.betrag)
    gruppe = p.gruppe if p.gruppe in ("posten", "merkzettel") else "posten"
    with db() as conn, conn.cursor() as cur:
        if p.id:
            cur.execute("UPDATE vermoegensposten SET name=%s, wert_cent=%s, art=%s, notiz=%s WHERE id=%s",
                        (p.name.strip(), cent, p.art, p.notiz, p.id))
            pid = p.id
        else:
            cur.execute("""INSERT INTO vermoegensposten (name, wert_cent, art, notiz, gruppe)
                           VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (name) DO UPDATE SET wert_cent=EXCLUDED.wert_cent, art=EXCLUDED.art,
                           notiz=EXCLUDED.notiz, gruppe=EXCLUDED.gruppe RETURNING id""",
                        (p.name.strip(), cent, p.art, p.notiz, gruppe))
            pid = cur.fetchone()[0]
    return {"ok": True, "id": pid, "cent": cent}


@router.post("/api/vermoegensposten/{posten_id}/delete")
def delete_posten(posten_id: int):
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE vermoegensposten SET aktiv=FALSE WHERE id=%s", (posten_id,))
    return {"ok": True}
