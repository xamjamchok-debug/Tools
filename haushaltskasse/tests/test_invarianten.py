"""Schicht 1 (#23b): read-only-Invarianten der Geld-Logik — laufen gegen JEDE DB
(lokal gegen die echte, in CI gegen den Service-Container). Kein Schreibzugriff."""
from __future__ import annotations

from haushaltskasse.domain.saldo import haushaltssaldo, pruefe_invarianten


def test_alle_invarianten(live_cur):
    befunde = pruefe_invarianten(live_cur)
    assert befunde == [], f"Invarianten verletzt: {befunde}"


def test_saldo_formel_konsistent(live_cur):
    """Saldo == Konten + Posten − Rücklagen + Forderungen (die Formel widerspricht sich nie selbst)."""
    s = haushaltssaldo(live_cur)
    assert s["saldo_cent"] == (s["konten_cent"] + s["posten_cent"]
                               - s["ruecklagen_cent"] + s["forderung_cent"])


def test_stichtag_heute_hat_keine_zukunft(live_cur):
    """Stichtagssaldo per 9999-12-31 == KPI-Saldo (der Datumsfilter lässt nichts aus)."""
    alles = haushaltssaldo(live_cur)
    per_ende = haushaltssaldo(live_cur, stichtag="9999-12-31")
    assert alles["saldo_cent"] == per_ende["saldo_cent"]
