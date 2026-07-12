# Handoff — Weitermachen am Desktop-PC (Azure + Beladung)

> Stand: 2026-07-12. Diese Session lief in der Cloud (nur zum Bauen). Der **Code** ist im Repo,
> die **privaten Daten** (Exporte, IBANs, DB) sind bewusst NICHT im Repo und werden am PC neu bereitgestellt.

## Wo wir stehen

- Branch: **`claude/status-update-bpmbn2`** (alles gepusht).
- Datenmodell (PostgreSQL) + Storage-Schicht: `haushaltskasse/storage/`
- Import-Pipeline: `haushaltskasse/workflows/` (parser, abgrenzung, kategorisierung, pipeline, seed, laden)
- **Komplette Kette lokal gegen echtes Postgres getestet:** 148 Buchungen, Umbuchungen/Wertpapiere
  korrekt abgegrenzt, 101/101 Realbuchungen kategorisiert, Dedupe beim Reimport funktioniert.

## Was am PC zu tun ist (Reihenfolge)

### 0. Repo holen
```
git clone <repo>        # oder: git pull
git checkout claude/status-update-bpmbn2
python -m venv .venv && . .venv/Scripts/activate   # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 1. Azure PostgreSQL anlegen
Anleitung: `haushaltskasse/docs/` bzw. der Chat — Flexible Server, Burstable **B1ms**, 32 GiB,
Region *Germany West Central*, Datenbank **haushaltskasse**, eigene Client-IP in der Firewall.
(~15–20 Min, meist Warten. Server stoppen wenn ungenutzt → ~4 €/Monat.)

### 2. Secrets & lokale Config (bleiben lokal, nie ins Git)
`.env` im Repo-Root (Vorlage: `.env.example`):
```
HAUSHALT_DATABASE_URL=postgresql://hhadmin:DEIN_PW@DEIN_SERVER.postgres.database.azure.com:5432/haushaltskasse?sslmode=require
ANTHROPIC_API_KEY=sk-ant-...
```
`haushaltskasse/data/lokale_config.json` (Vorlage: `haushaltskasse/workflows/lokale_config.example.json`):
- `eigene_ibans` — deine Konto-IBANs (für Umbuchungs-Erkennung)
- `halter_regex` / `kinder_regex` — dein Name / die Namen der Kinder
- `persoenliche_regeln` — z. B. Kinder → Kinder/Taschengeld-Sparen
- `ruecklagen` — monatliche Rückstellung je Kategorie (aus dem config-Blatt)

### 3. Export-Dateien nach `input/` legen
Aus OneDrive die Umsatz-Exporte kopieren (bleiben lokal, `input/` ist gitignored):
- DKB-Giro-CSV, comdirect-Giro-CSV, comdirect-Tagesgeld-CSV, Amazon-Visa-.xls
Dateizuordnung erfolgt über den Dateinamen (dkb/comdirect/tagesgeld/amazon).

### 4. Schema → Seed → Beladung
```
python -m haushaltskasse.storage.db        # Schema anlegen (in Azure)
python -m haushaltskasse.workflows.seed     # Konten + Kategorien + Rückstellungen
python -m haushaltskasse.workflows.laden     # Buchungen laden (idempotent, dedupliziert)
python -m haushaltskasse.workflows.pipeline  # optional: Vorschau-Bericht ohne DB
```

## Offene nächste Aufgaben (Reihenfolge für die PC-Session)

1. **Azure einrichten** (Schritt 1) und Verbindung testen: `python -m haushaltskasse.storage.db`
2. **Seed + Beladung** gegen Azure (Schritt 4) — deine echten Daten in die Cloud-DB.
3. **Amazon-Produktdaten** (optional): Bestell-/Produktexport, um die opaken `AMZN Mktp DE`
   den echten Produkten/Unterkategorien zuzuordnen (sonst per Bemerkung/KI-Vorschlag).
4. **Dashboard** bauen: Real-/verfügbarer Saldo, Nebenbuch-Verlauf, Top-Unterkategorien,
   Budget (Rückstellung) vs. Ist. (FastAPI + einfache Web-UI, Port 3000.)
5. **KI-Review-Loop**: unbekannte/niedrig-confidente Buchungen → Haiku-Vorschlag →
   annehmen/ablehnen/umdefinieren → wird zur Regel (mapping_regeln), Historie rückwirkend.

## Wichtige Design-Entscheidungen (Kontext)

- **Storage:** Azure Database for PostgreSQL (Cloud, relational, aggregations-tauglich).
- **Drei Ebenen:** Konto (real) > Kategorie/Nebenbuch (1:1, trägt Rücklage) > Unterkategorie (nur Auswertung, rückwirkend).
- **Abgrenzung:** Umbuchung nur bei eigenem Gegenkonto (IBAN) oder explizitem Übertrag; Wertpapiere/Zinsen separat.
- **Große Einmalkäufe 2026:** Opel e-Combo (~37k), e-Frontera (~27k), PV-Anlage (~27k) → Kategorie „Anschaffungen".
- **Privacy:** IBANs, Namen, Beträge, Exporte, DB — alles lokal/gitignored. Nur generischer Code im Repo.
- Details: `design-2026-07.md`, `current-analysis.md`.
