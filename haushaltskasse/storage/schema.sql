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
    -- Rolle im Haushalts-Saldo:
    --   'ruecklage' = echter Rücklagen-Topf, wird vom freien Saldo ABGEZOGEN (Standard).
    --   'forderung' = Person schuldet der Kasse (Natalie/Jörg) -> wird ADDIERT (+).
    --   'ausgabe'   = reine Ausgaben-Kategorie ohne Topf-Charakter.
    zaehlt_als                TEXT NOT NULL DEFAULT 'ruecklage'
                              CHECK (zaehlt_als IN ('ruecklage','forderung','ausgabe')),
    aktiv                     BOOLEAN NOT NULL DEFAULT TRUE
);
ALTER TABLE kategorien ADD COLUMN IF NOT EXISTS zaehlt_als TEXT NOT NULL DEFAULT 'ruecklage';
-- default_unterkategorie_id verweist auf unterkategorien und wird deshalb erst NACH deren
-- CREATE hinzugefügt (siehe unten). Sonst scheitert die frische DB an der Vorwärts-Referenz.

-- ---------------------------------------------------------------------------
-- Unterkategorien = reine Auswertungsdimension INNERHALB einer Kategorie.
-- KEINE eigene Rücklage. Wachsend: KI schlägt vor, Nutzer bestätigt/ändert/ergänzt.
-- Umbenennen/Umdefinieren wirkt über apply_regeln() rückwirkend auf die Historie.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unterkategorien (
    id                        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kategorie_id              INTEGER NOT NULL REFERENCES kategorien(id) ON DELETE CASCADE,
    name                      TEXT NOT NULL,
    monatliche_ruecklage_cent BIGINT NOT NULL DEFAULT 0,   -- Soll-Rückstellung je Unterkategorie
    quelle                    TEXT NOT NULL DEFAULT 'manuell' CHECK (quelle IN ('ki','manuell')),
    erstellt_am               TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kategorie_id, name)
);
-- Nachrüstung für bestehende DBs (Spalte kam später dazu):
ALTER TABLE unterkategorien ADD COLUMN IF NOT EXISTS monatliche_ruecklage_cent BIGINT NOT NULL DEFAULT 0;
-- #39: Unterkategorie zählt im Monats-Finanzfluss als EINNAHME (z. B. Gehalt, Taschengeld).
ALTER TABLE unterkategorien ADD COLUMN IF NOT EXISTS ist_einnahme BOOLEAN NOT NULL DEFAULT FALSE;

-- #26: Allgemeine Einstellungen (key/value). 'stichtag' = Start-Abgrenzungsdatum (davor: Startsaldo).
CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT NOT NULL
);
INSERT INTO einstellungen (schluessel, wert) VALUES ('stichtag', '2025-01-01')
    ON CONFLICT (schluessel) DO NOTHING;

-- Default-Unterkategorie je Kategorie (Rest-Auffang): jetzt anlegen, da unterkategorien existiert.
ALTER TABLE kategorien ADD COLUMN IF NOT EXISTS default_unterkategorie_id INTEGER REFERENCES unterkategorien(id);

-- ---------------------------------------------------------------------------
-- Vermögensposten: externe Werte, die NICHT aus Buchungen ableitbar sind
-- (Depot-/ETF-Marktwert, Kredite KfW/Deutsche Bank, Riester-Steuerschuld,
-- Kredit an Großeltern). Werden in der Übersicht mitgerechnet, im Dashboard gepflegt.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vermoegensposten (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    wert_cent   BIGINT NOT NULL DEFAULT 0,               -- + Vermögen / - Schuld
    art         TEXT NOT NULL DEFAULT 'vermoegen' CHECK (art IN ('vermoegen','schuld')),
    -- TRUE  = zählt im Haushalts-Saldo (ETF, Merkzettel, Großeltern-geparkt, Forderungen).
    -- FALSE = langfristige Vermögens-/Kreditebene (Kredit Großeltern −135.000, Riester,
    --         KfW, Deutsche-Bank, Auto/PV) — NICHT im Haushalts-Saldo, separater Block.
    im_haushaltssaldo BOOLEAN NOT NULL DEFAULT TRUE,
    sortierung  INTEGER NOT NULL DEFAULT 100,
    notiz       TEXT,
    aktiv       BOOLEAN NOT NULL DEFAULT TRUE,
    erstellt_am TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE vermoegensposten ADD COLUMN IF NOT EXISTS im_haushaltssaldo BOOLEAN NOT NULL DEFAULT TRUE;
-- #39/U1: Gruppe für die Darstellung. 'merkzettel' = eigene Box (künftige/reservierte Kosten),
-- 'posten' = normale Vermögens-/Saldo-Posten. Beide zählen wie bisher (im_haushaltssaldo entscheidet).
ALTER TABLE vermoegensposten ADD COLUMN IF NOT EXISTS gruppe TEXT NOT NULL DEFAULT 'posten';
-- #60: Konsistenz-Falle hart machen (Deep-Dive-I-Befund C): ein Merkzettel-Posten MUSS im
-- Haushaltssaldo zählen, sonst kippt die Übersicht-Herleitung lautlos. DROP+ADD = idempotent.
ALTER TABLE vermoegensposten DROP CONSTRAINT IF EXISTS chk_merkzettel_im_saldo;
ALTER TABLE vermoegensposten ADD CONSTRAINT chk_merkzettel_im_saldo
    CHECK (gruppe <> 'merkzettel' OR im_haushaltssaldo);

-- ---------------------------------------------------------------------------
-- Buchungen: alle Bewegungen. buchungsart trennt die drei Fälle:
--   'real'      Konto + Kategorie gesetzt        -> ändert Realsaldo
--   'ruecklage' nur Kategorie (Konto NULL)       -> virtuell: Zuführung(+)/Verzehr(-)/Korrektur(±)
--   'umbuchung' Konto + Gegenkonto, keine Kat.   -> Transfer, netto 0, zählt NICHT als Ausgabe
-- Empfänger wird immer gespeichert → Drill-Down bis zum Empfänger ist immer möglich.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS buchungen (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- real/ruecklage/umbuchung wie oben, plus wertpapier (Depot) und zinsen (Kontoabschluss).
    -- wertpapier/zinsen zaehlen nicht als Haushaltsausgabe (siehe kennzahlen()).
    buchungsart       TEXT NOT NULL CHECK (buchungsart IN ('real','ruecklage','umbuchung','wertpapier','zinsen')),
    datum_wert        DATE NOT NULL,                       -- Wertstellung
    datum_buchung     DATE,                                -- Buchungstag, falls vorhanden
    betrag_cent       BIGINT NOT NULL,                     -- + Einnahme / - Ausgabe
    konto_id          INTEGER REFERENCES konten(id),       -- NULL bei reiner Rücklagenbuchung
    gegenkonto_id     INTEGER REFERENCES konten(id),       -- nur bei Umbuchung
    kategorie_id      INTEGER REFERENCES kategorien(id),   -- NULL bei Umbuchung
    unterkategorie_id INTEGER REFERENCES unterkategorien(id),
    kat_pinned        BOOLEAN NOT NULL DEFAULT FALSE,      -- Kategorie manuell fixiert
    unterkat_pinned   BOOLEAN NOT NULL DEFAULT FALSE,      -- Unterkat. manuell fixiert (Reapply lässt sie in Ruhe)
    -- Verknüpfung Verzehr-Gegenbuchung -> Realbuchung. Eine 'ruecklage'-Buchung mit
    -- spiegel_von_id ist der automatische Spiegel einer Realbuchung (wird NIE von Hand
    -- bearbeitet). Ändert sich die Kategorie der Realbuchung, wird der Spiegel neu erzeugt.
    spiegel_von_id    INTEGER REFERENCES buchungen(id) ON DELETE CASCADE,
    empfaenger        TEXT,
    verwendungszweck  TEXT,
    quelle_import     TEXT,                                -- dkb / comdirect / amazon / manuell
    import_hash       TEXT UNIQUE,                         -- Dedupe bei Reimport
    bemerkung         TEXT,
    erstellt_am       TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE buchungen ADD COLUMN IF NOT EXISTS spiegel_von_id INTEGER REFERENCES buchungen(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_buchungen_datum   ON buchungen(datum_wert);
CREATE INDEX IF NOT EXISTS idx_buchungen_kat     ON buchungen(kategorie_id);
CREATE INDEX IF NOT EXISTS idx_buchungen_empf    ON buchungen(empfaenger);
CREATE INDEX IF NOT EXISTS idx_buchungen_spiegel ON buchungen(spiegel_von_id);

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

-- ---------------------------------------------------------------------------
-- #61: Audit-Log der Admin-/Write-Läufe (CLI-Workflows). Beantwortet „was lief wann?"
-- Kennzahlen vorher/nachher als JSON-Text (realsaldo, ruecklagen, forderungen …).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_laeufe (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    werkzeug           TEXT NOT NULL,
    argumente          TEXT,
    kennzahlen_vorher  TEXT,
    kennzahlen_nachher TEXT,
    invarianten_ok     BOOLEAN,
    gestartet          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- #75: Verträge — die Erkennungs-/Planungsebene über den Unterkategorien.
--
-- Warum eine eigene Ebene? Der Anbieter ist KEIN stabiler Anker (Strom:
-- MAINGAU -> Naturwerke -> Tibber). Ein Vertrag ist zeitlich begrenzt und
-- liefert Rhythmus + Rate; die Unterkategorie darüber bleibt stabil und trägt
-- den Rücklagen-Topf. N Verträge -> 1 Unterkategorie ("Strom").
--
-- Damit entfällt das manuelle Aussortieren alter Werte (User 2026-07-17:
-- "die historischen Werte einfach aussortieren finde ich blödsinnig"):
-- Ein Vertrag ist 'beendet', wenn seit > 2 Rhythmen keine Zahlung kam — eine
-- Regel statt Handarbeit. Die Historie bleibt sichtbar.
--
-- An `buchungen` ändert sich nichts; der Vertrag ist Metadaten darüber.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vertraege (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                TEXT NOT NULL,                      -- "Tibber", "OGS Kind 1"
    beschreibung        TEXT,                               -- Freitext (User-Wunsch: Reiter-Spalte)
    -- N:1 -> hier liegt der Rücklagen-Topf. Mehrere Verträge dürfen auf dieselbe
    -- Unterkategorie zeigen (= "bündeln", User-Entscheid A 2026-07-17).
    unterkategorie_id   INTEGER NOT NULL REFERENCES unterkategorien(id) ON DELETE CASCADE,
    -- Erkennungsmuster: Empfänger reicht NICHT (an "Gemeinde Wachtberg" hängen
    -- vier Zwecke in drei Nebenbüchern; hinter "PayPal" stecken 66 Händler).
    muster_empfaenger   TEXT,
    muster_zweck        TEXT,
    rhythmus            TEXT NOT NULL DEFAULT 'unregelmaessig'
                        CHECK (rhythmus IN ('monatlich','quartalsweise','halbjaehrlich','jaehrlich','unregelmaessig')),
    betrag_median_cent  BIGINT NOT NULL DEFAULT 0,          -- Median, nicht Mittelwert (Ausreißer!)
    letzte_zahlung      DATE,
    naechste_faellig    DATE,
    -- erkannt -> vom User bestätigt (Entscheid D: "Vertrag erst nach Bestätigung")
    -- beendet -> letzte Zahlung > 2 Rhythmen her; zählt NICHT mehr fürs Soll
    -- ignoriert -> Fehlerkennung, nie wieder vorschlagen
    status              TEXT NOT NULL DEFAULT 'erkannt'
                        CHECK (status IN ('erkannt','bestaetigt','beendet','ignoriert')),
    quelle              TEXT NOT NULL DEFAULT 'auto' CHECK (quelle IN ('auto','manuell')),
    erstellt_am         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vertraege_ukat   ON vertraege(unterkategorie_id);
CREATE INDEX IF NOT EXISTS idx_vertraege_status ON vertraege(status);

-- Identität eines Vertrags ist sein ERKENNUNGSMUSTER, nicht sein Name: Die beiden
-- OGS-Beiträge heißen beide "Gemeinde Wachtberg" und liegen im selben Untertopf —
-- unterschieden werden sie allein durch das Kassenzeichen im Zweck (= zwei Kinder).
-- Mit UNIQUE(name, unterkategorie_id) überschrieb das zweite Kind das erste.
-- COALESCE, weil UNIQUE sonst mehrere NULL-Zwecke nebeneinander zuließe.
DROP INDEX IF EXISTS idx_vertraege_identitaet;
ALTER TABLE vertraege DROP CONSTRAINT IF EXISTS vertraege_name_unterkategorie_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_vertraege_identitaet
    ON vertraege (muster_empfaenger, COALESCE(muster_zweck, ''), unterkategorie_id);

-- #75: Schiefstellung je Nebenbuch bewusst erlauben (User 2026-07-17).
-- FALSE (Default): fordern die Verträge mehr als das Config-Soll -> harte Warnung,
--   der Rückstellungslauf schreibt NICHTS.
-- TRUE: Unterdeckung ist gewollt, der Topf soll abschmelzen -> Lauf bucht und
--   weist Unterdeckung + Reichweite (Bestand / Unterdeckung) aus.
-- Beispiel Füchschen: Soll 0, Verträge ~475/Monat, Bestand ~15.000 (Kindergeld
-- zahlt ein, die Posten zahlen aus) -> "kann gerne abgeknabbert werden".
ALTER TABLE kategorien ADD COLUMN IF NOT EXISTS schiefstellung_erlaubt BOOLEAN NOT NULL DEFAULT FALSE;
