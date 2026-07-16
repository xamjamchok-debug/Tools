# Handover an PC — 2026-07-16 (aus Handy/Cloud-Session)

> Branch `claude/status-update-bpmbn2`, alles committet & gepusht. Am PC: `git pull`, dann
> **deployen + Migrationen fahren + testen**. Diese Session lief in der Cloud (Code gebaut &
> lokal gegen Wegwerf-Postgres getestet), die **echte Azure-DB wurde nicht angefasst**.

Neu in dieser Session (oben = neuste), zwei Pakete:

**Paket 2 (heute):**
- `c5e5510` **#47 + #28** — Einnahme am Vorzeichen (`ist_einnahme` raus) · `allgemein_verteilen.py`

**Paket 1 (davor, noch nicht deployed):**
- `df93fde` **#56** Konto „Bar" — Abheben (Umbuchung Giro→Bar) + Ausgeben (Realbuchung + Topf-Verzehr)
- `bbd388c` **#23 + #55 + #9** — Versionsanzeige · Import nutzt DB-Regeln · Übersicht-Wasserfall
- `e3a6197` **#54** Haushaltskasse als Eigentopf
- `kategorie_cleanup.py` **#49** (war schon im Branch)

---

## Was am PC zu tun ist

### 1. Holen
```
git checkout claude/status-update-bpmbn2 && git pull
```
Kein Schema-Änderungsbedarf (alles nutzt vorhandene Spalten). Sicherheitshalber idempotent:
```
python -m haushaltskasse.storage.db     # nur ALTER ... IF NOT EXISTS, ändert keine Daten
```

### 2. Deployen (Live-App) — **mit APP_VERSION!**
```
$env:PYTHONIOENCODING="utf-8"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
& $az acr build -r hhkassec1k7wx -t haushaltskasse:latest . --no-logs
& $az containerapp update -g haushaltskasse-rg -n haushaltskasse `
    --image hhkassec1k7wx.azurecr.io/haushaltskasse:latest `
    --set-env-vars APP_VERSION=$(git rev-parse --short HEAD)
```
⚠️ **`--set-env-vars APP_VERSION=…` ist Pflicht** — sonst zeigt der Footer `dev` (#23). Genau dafür
ist #23 gebaut: nach dem Deploy im Footer prüfen, dass die kurze SHA passt.

### 3. Migrationen auf der Live-DB — **jede zuerst Trockenlauf, dann `--write`**
Reihenfolge einhalten (Cleanup vor Gegenbuchung vor Verteilung):

```
# #49 Kategorien-Cleanup: Kindergeld 3→1 (Einnahme), „Kinder" raus, Sparen→Füchschen
python -m haushaltskasse.workflows.kategorie_cleanup
python -m haushaltskasse.workflows.kategorie_cleanup --write

# #46 + #54: „Einnahmen" ohne Topf, „Haushaltskasse" als Eigentopf, Spiegel-Buchungen neu
python -m haushaltskasse.workflows.gegenbuchung
python -m haushaltskasse.workflows.gegenbuchung --write

# #28 Allgemein-Topf je Nebenbuch auf Untertöpfe verteilen  — TROCKENLAUF GENAU ANSEHEN
python -m haushaltskasse.workflows.allgemein_verteilen
python -m haushaltskasse.workflows.allgemein_verteilen --write        # optional: + --soll
```
Alle drei sind **idempotent** und salden-schonend: der Cleanup verschiebt nur Zuordnungen
(prüft die Rücklagen-Salden am Ende), die Verteilung bucht **netto-neutral** (Kategorie-Topf
bleibt konstant, nur Allgemein → Untertöpfe). Ein zweiter Lauf ist jeweils ein No-Op.

`--soll` bei #28 setzt zusätzlich das monatliche Soll je Untertopf = Kategorie-Soll × Anteil
(speist #39). Ohne die Flag bleiben die Soll-Werte unangetastet.

---

## Vor `allgemein_verteilen --write`: drei Punkte kurz prüfen
Die %-Anteile in `allgemein_verteilen.VERTEILUNG` sind ein begründeter Startpunkt aus der
Excel-Historie, **kein exaktes Abbild**. Im Trockenlauf steht je Nebenbuch, was verteilt würde.
Bewusst so entschieden (bei Bedarf im Skript justieren / mir Bescheid geben):
- **Urlaub** → **nicht** verteilt (reisebasiert, bleibt im Allgemein-Topf).
- **Garten & Außenanlage** → unter **„Inst"** einsortiert (nicht Nebenkosten).
- **fifi/Robbie** (Sport) → noch ungeklärt, ggf. eigener Anteil.

---

## Was zu testen ist (nach Deploy + Migration)

### #23 Versionsanzeige
- [ ] Footer zeigt `v <kurze-SHA>`; `/health` liefert dieselbe Version als JSON.

### #9 Übersicht-Wasserfall
- [ ] Konten − Rücklagen − Merkzettel = **Frei verfügbar**; + Forderungen + Posten = **Haushalts-Saldo**.
- [ ] Die Rechnung geht sichtbar auf (keine „fehlenden Posten" mehr).

### #56 Konto „Bar"
- [ ] Karte „Bargeld" auf der Übersicht. **Abheben** (Betrag + Konto) → Giro −, Bar +, netto 0.
- [ ] **Ausgeben** (Betrag) → Bar −, Haushaltskasse-Topf verzehrt sich.

### #55 Import
- [ ] Neuer DKB-Import: **Kredite (Deutsche Bank/deuba/kfw) werden jetzt zugeordnet** (0 offen bei bekannten).

### #47 Config — Einnahme am Vorzeichen
- [ ] In Config **keine „Einnahme?"-Checkbox** mehr bei den Unterkategorien.
- [ ] Kategorie mit Rolle „Ausgabe/kein Topf" **und positivem Soll** erscheint im Block **Einnahmen**;
      Rücklagen-Töpfe bleiben trotz positivem Soll bei **Ausgaben**.
- [ ] Monats-Saldo = Einnahmen + Forderungen − Ausgaben rechnet wie vorher.

### #49 / #46 / #54 (nach den Migrationen)
- [ ] Nur **eine** Kategorie „Kindergeld" (als Einnahme, unter Füchschen); Kategorie „Kinder" ist weg.
- [ ] „Haushaltskasse" zählt als eigener Rücklagen-Topf; „Einnahmen" ist **kein** Topf mehr.

### #28 (nach der Verteilung)
- [ ] Rücklagen-/Nebenbuch-Ansicht: „Allgemein" je Nebenbuch nahe 0, die Untertöpfe gefüllt;
      der Kategorie-Gesamttopf ist **unverändert**.

### Regression
- [ ] Übersicht, Reports (Pivot), Config, Buchungen laden wie gehabt.

---

## Offen / nächste Baustellen (nicht in diesem Paket)
- **Annahme in #47 bestätigen:** negativ/0-Soll-„Ausgabe"-Kategorien bleiben in „Weitere"
  (zählen NICHT im Monats-Saldo) — die validierte #39-Formel ist damit unverändert. Wenn du
  geplante Nicht-Topf-Ausgaben (negatives Soll) im Saldo willst, sag Bescheid → Folgeänderung.
- **#28-Feinschliff:** %-Werte an den echten Salden justieren; fifi/Robbie & Urlaub-Detail klären.
- Ältere UI-Wünsche noch offen: Umbuchungen aus der Buchungsliste raus, Reports-Filter nach
  Nebenbuch/Multiselect, Übersicht-Rücklagen doppelklickbar.
