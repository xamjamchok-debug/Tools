"""Smoke-Tests (#23b): alle Seiten + Exporte antworten mit 200 (read-only GETs).
Lokal gegen die echte DB (gefahrlos), in CI gegen den frisch initialisierten Container."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

SEITEN = ["/health", "/", "/ruecklagen", "/vertraege", "/buchungen", "/reports", "/config",
          "/import", "/releasenotes", "/login", "/export/uebersicht.csv", "/export/ruecklagen.csv",
          "/export/reports.csv", "/export/buchungen.csv"]


@pytest.fixture(scope="module")
def client():
    try:
        from haushaltskasse.dashboard.app import app
    except Exception as e:
        pytest.skip(f"App nicht startbar: {e}")
    return TestClient(app)


@pytest.mark.parametrize("pfad", SEITEN)
def test_seite_antwortet(client, pfad, live_cur):   # live_cur: skippt sauber ohne DB
    r = client.get(pfad)
    assert r.status_code == 200, f"{pfad} -> {r.status_code}"


def test_health_traegt_version(client):
    daten = client.get("/health").json()
    assert daten["ok"] is True
    assert "version" in daten
