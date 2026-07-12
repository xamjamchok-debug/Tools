-- Haushaltskasse — PostgreSQL Schema (Azure Database for PostgreSQL, Flexible Server)
--
-- Konventionen:
--   * Beträge als BIGINT in Cent (betrag_cent) → keine Float-Rundungsfehler.
--     + = Einnahme/Zufluss, - = Ausgabe/Abfluss.
--   * Datum als DATE, Zeitstempel als TIMESTAMPTZ.
--
-- Drei-Ebenen-Modell:
--   Konto (real, trägt Realsaldo)  >  Kategorie (= Nebenbuch, 1:1, trägt Rücklage)  >  Unterkategorie (nur Auswertung)

-- ---------------------------------------------------------------------------
-- Reale Konten: wo Geld physisch liegt. Treiben den Realsaldo.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS konten (
    id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name   TEXT NOT NULL UNIQUE,
    typ    TEXT NOT NULL CHECK (typ IN ('giro','kreditkarte','tagesgeld','depot','sonstiges')),
    aktiv  BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------------
-- Kategorien = Nebenbücher (1:1). Jede Kategorie ist ein Rücklagen-Topf.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kategorien (
    id                        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                      TEXT NOT NULL UNIQUE,
    monatliche_ruecklage_cent BIGINT NOT NULL DEFAULT 0,
    ist_nebenbuch             BOOLEAN NOT NULL DEFAULT TRUE,
    aktiv                     BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------------
-- Unterkategorien = reine Auswertungsdimension INNERHALB einer Kategorie.
-- KEINE eigene Rücklage. Wachsend: KI schlägt vor, Nutzer bestätigt/ändert/ergänzt.
-- Umbenennen/Umdefinieren wirkt über apply_regeln() rückwirkend auf die Historie.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unterkategorien (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kategorie_id INTEGER NOT NULL REFERENCES kategorien(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    quelle       TEXT NOT NULL DEFAULT 'manuell' CHECK (quelle IN ('ki','manuell')),
    erstellt_am  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kategorie_id, name)
);

-- ---------------------------------------------------------------------------
-- Buchungen: alle Bewegungen. buchungsart trennt die drei Fälle:
--   'real'      Konto + Kategorie gesetzt        -> ändert Realsaldo
--   'ruecklage' nur Kategorie (Konto NULL)       -> virtuell: Zuführung(+)/Verzehr(-)/Korrektur(±)
--   'umbuchung' Konto + Gegenkonto, keine Kat.   -> Transfer, netto 0, zählt NICHT als Ausgabe
-- Empfänger wird immer gespeichert → Drill-Down bis zum Empfänger ist immer möglich.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS buchungen (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    buchungsart       TEXT NOT NULL CHECK (buchungsart IN ('real','ruecklage','umbuchung')),
    datum_wert        DATE NOT NULL,                       -- Wertstellung
    datum_buchung     DATE,                                -- Buchungstag, falls vorhanden
    betrag_cent       BIGINT NOT NULL,                     -- + Einnahme / - Ausgabe
    konto_id          INTEGER REFERENCES konten(id),       -- NULL bei reiner Rücklagenbuchung
    gegenkonto_id     INTEGER REFERENCES konten(id),       -- nur bei Umbuchung
    kategorie_id      INTEGER REFERENCES kategorien(id),   -- NULL bei Umbuchung
    unterkategorie_id INTEGER REFERENCES unterkategorien(id),
    kat_pinned        BOOLEAN NOT NULL DEFAULT FALSE,      -- Kategorie manuell fixiert
    unterkat_pinned   BOOLEAN NOT NULL DEFAULT FALSE,      -- Unterkat. manuell fixiert (Reapply lässt sie in Ruhe)
    empfaenger        TEXT,
    verwendungszweck  TEXT,
    quelle_import     TEXT,                                -- dkb / comdirect / amazon / manuell
    import_hash       TEXT UNIQUE,                         -- Dedupe bei Reimport
    bemerkung         TEXT,
    erstellt_am       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_buchungen_datum ON buchungen(datum_wert);
CREATE INDEX IF NOT EXISTS idx_buchungen_kat   ON buchungen(kategorie_id);
CREATE INDEX IF NOT EXISTS idx_buchungen_empf  ON buchungen(empfaenger);

-- ---------------------------------------------------------------------------
-- Lernende Mapping-Regeln: Muster -> Kategorie (+ optional Unterkategorie).
-- status: 'aktiv' · 'vorschlag' (KI, wartet auf Bestätigung) · 'abgelehnt' (nie anwenden).
-- Retroaktiv: Anlegen/Ändern/Bestätigen -> apply_regeln() über die Historie.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mapping_regeln (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pattern_typ       TEXT NOT NULL CHECK (pattern_typ IN ('empfaenger','verwendungszweck','iban','sepa_ref')),
    pattern           TEXT NOT NULL,                       -- Teilstring / Schlüsselwort (case-insensitive)
    kategorie_id      INTEGER REFERENCES kategorien(id),
    unterkategorie_id INTEGER REFERENCES unterkategorien(id),
    quelle            TEXT NOT NULL DEFAULT 'manuell' CHECK (quelle IN ('ki','manuell','import')),
    status            TEXT NOT NULL DEFAULT 'aktiv'   CHECK (status IN ('aktiv','vorschlag','abgelehnt')),
    confidence        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    treffer_count     INTEGER NOT NULL DEFAULT 0,
    last_used         TIMESTAMPTZ,
    erstellt_am       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pattern_typ, pattern)
);

-- ---------------------------------------------------------------------------
-- Import-Protokoll (Audit).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS import_dateien (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dateiname     TEXT NOT NULL,
    quelle        TEXT NOT NULL,
    zeilen_count  INTEGER NOT NULL DEFAULT 0,
    importiert_am TIMESTAMPTZ NOT NULL DEFAULT now()
);
