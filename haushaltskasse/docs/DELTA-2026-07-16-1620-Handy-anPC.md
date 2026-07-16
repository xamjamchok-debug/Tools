# Delta Handy-Session → PC — 2026-07-16 16:20 UTC

> **PC ist führend.** Diese Datei ist rein informativ: sie fasst zusammen, was in der
> Handy/Cloud-Session (Branch `claude/status-update-bpmbn2`) gebaut und **ermittelt** wurde,
> damit der PC den Stand kennt. Es wurde **nur lokal gegen Wegwerf-Postgres getestet**, die
> echte Azure-DB nicht angefasst.

## 1. Neu ermittelte Erkenntnis (das eigentliche Wissens-Delta)

**Umkategorisieren erzeugt genau EINE Gegenbuchung, nicht zwei.**
Am Code verifiziert (`dashboard/app.py:346` `set_kategorie` → `gegenbuchung.sync_eine`):

1. `DELETE FROM buchungen WHERE spiegel_von_id = <Buchung>` — alte Spiegelbuchung weg,
2. genau **eine** neue Spiegelbuchung im richtigen Topf angelegt (folgt der neuen Kategorie).

Es gibt also **immer nur eine** Spiegel-Gegenbuchung pro Realbuchung. Effekt = „raus aus nb1,
rein in nb2", aber technisch als *löschen + neu anlegen*, nicht als zwei sich aufsummierende
Einträge → kein Doppelzählen, nb1 bleibt sauber. Feinheiten:
- Ziel ist **Nicht-Topf** (Rolle 'ausgabe'/'forderung'): alter Spiegel weg, **kein** neuer.
- **Historische FB-Buchungen** (`quelle_import` ∈ FB_QUELLEN) und **kreditfinanziert**:
  nie ein Spiegel (deckt sich mit der früheren Q3-Erklärung).
- Gilt nur für Import-/neue Realbuchungen mit Topf-Kategorie.

## 2. In dieser Session gebaut (liegt im Branch; PC hat teils schon überschrieben)

| Commit | Inhalt | Stand ggü. PC |
|---|---|---|
| `c5e5510` | **#47** `ist_einnahme` raus, `config_fluss` klassifiziert Einnahme am **Vorzeichen** (Planwert>0=Einnahme; Rolle schlägt Vorzeichen). Checkbox+JS+Endpoint entfernt · **#28** `allgemein_verteilen.py` | #47 unberührt · #28 s. u. |
| `8de516d` | `HANDOVER-2026-07-16-anPC.md` (Deploy-/Migrations-Reihenfolge) | teils überholt durch PC |
| `d9c2dc7` | `REMOTE-CONTROL-Handy-PC.md` (Remote Control erklärt) | neu, unberührt |

## 3. Status meiner Bausteine gegen den aktuellen PC-Stand

- **#47 (Vorzeichen statt `ist_einnahme`)** — gebaut & lokal getestet. **Annahme, die der PC
  prüfen/bestätigen muss:** negativ/0-Soll-„Ausgabe"-Kategorien bleiben in „Weitere" (zählen
  NICHT im Monats-Saldo) → die validierte #39-Formel bleibt unverändert. Bitte mit dem neuen
  **#58** (Forderungen im Config-Monatsfluss als „Einnahmen" führen) abgleichen — beide fassen
  `config_fluss` an.

- **#28 `allgemein_verteilen.py`** — PC hat den **%-Ansatz verworfen** (soll datenbasiert werden).
  Das ist nachvollziehbar. **Wiederverwendbar** aus dem Skript bleibt die Mechanik, nur die
  Betrags-**Quelle** muss getauscht werden:
  - netto-neutrale Umbuchung Allgemein → Untertopf (zwei `ruecklage`-Zeilen, `quelle='verteilung'`),
  - Cent-genaue Largest-Remainder-Rundung (`_verteile_cent`), Summe == Allgemein-Stand,
  - Idempotenz (überspringt Kategorien, die schon `quelle='verteilung'` tragen),
  - Trockenlauf-Default, `--write`, optional `--soll`.

  Für „datenbasiert statt %": die `VERTEILUNG`-%-Tabelle durch je Untertopf berechnete
  Zielbeträge ersetzen (aus Zahlungsrhythmus/Fälligkeit je Vertrag, analog zur validierten
  Soll-Formel `Zielbestand = Jahresbetrag × Monate seit letzter Zahlung ÷ 12`). Die Umbuchungs-
  und Rundungslogik kann 1:1 bleiben.

- **#46 / #49 / #54 (Migrationen)** — Skripte fertig, am PC je Trockenlauf → `--write`:
  `gegenbuchung` (Einnahmen ohne Topf, Haushaltskasse als Eigentopf), `kategorie_cleanup`
  (Kindergeld 3→1, „Kinder" raus, Sparen→Füchschen). Beide idempotent & salden-schonend.

## 4. Offene Punkte (unverändert, für den PC)
- #47-Annahme bestätigen (s. o.), ggf. Abgleich mit #58.
- #28 datenbasiert statt %: Konzept steht, Umbuchungsmechanik ist da; Betragsherleitung fehlt.
- #28-Details weiter offen: Urlaub (reisebasiert → nicht verteilt), Garten (unter „Inst"), fifi/Robbie.
