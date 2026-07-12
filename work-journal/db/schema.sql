-- Work Journal Datenbankschema

CREATE TABLE IF NOT EXISTS eintraege (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    datum        DATE NOT NULL DEFAULT (date('now')),
    typ          TEXT NOT NULL CHECK(typ IN ('gespräch','lernen','arbeitszeit','abwesenheit','notiz')),
    inhalt       TEXT NOT NULL,
    person       TEXT,
    tags         TEXT,
    von          TIME,
    bis          TIME,
    erstellt_am  DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_datum  ON eintraege(datum);
CREATE INDEX IF NOT EXISTS idx_typ    ON eintraege(typ);
CREATE INDEX IF NOT EXISTS idx_person ON eintraege(person);
