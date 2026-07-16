"""Erzeugt das ITEMS-Array in backlog-board.html neu aus BACKLOG.md.

So kann das Board nie wieder gegenüber der Steuerdatei veralten. Der HTML-Rahmen
(CSS/JS/Statistik) bleibt unangetastet — nur das Datenarray zwischen
`var ITEMS = [` und `];` wird ersetzt.

    python haushaltskasse/docs/gen_backlog_board.py

Reifegrad-Mapping (höchste erreichte Stufe zählt):
    💡→0 Idee · 📐→1 Designed · 🔨→2 Entwickelt · 🚀→3 Deployed · 👁→4 Validiert
Flags: ⭐ prio · 🐞 bug · ❓ klaerung · 🎨 design · 🔄 umbau
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
BACKLOG = DOCS / "BACKLOG.md"
BOARD = DOCS / "backlog-board.html"

STAGE_BY_ICON = [("👁", 4), ("🚀", 3), ("🔨", 2), ("📐", 1), ("💡", 0)]
FLAGS = [("⭐", "prio"), ("🐞", "bug"), ("❓", "klaerung"), ("🎨", "design"), ("🔄", "umbau")]


def stage_und_flags(reifegrad: str):
    stage = 0
    for icon, s in STAGE_BY_ICON:      # höchste vorhandene Stufe
        if icon in reifegrad:
            stage = s
            break
    flags = [name for icon, name in FLAGS if icon in reifegrad]
    return stage, flags


def js(s: str) -> str:
    return s.strip().replace("\\", "\\\\").replace("'", "\\'")


def parse_backlog() -> list[str]:
    zeilen = BACKLOG.read_text(encoding="utf-8").splitlines()
    items, warnungen = [], []
    for ln in zeilen:
        if not ln.startswith("|"):
            continue
        parts = ln.split("|")
        if len(parts) != 7:                       # äußere + 5 Spalten = 7 Teile
            continue                              # Kopf/Trenner/kaputte Zeile
        nr, bereich, kurz, umsetzung, reifegrad = (p.strip() for p in parts[1:6])
        if nr in ("Nr", "") or set(nr) <= set("-: "):
            continue
        if "|" in kurz or "|" in umsetzung:
            warnungen.append(f"Zeile {nr}: enthält '|' im Text — bitte prüfen")
        stage, flags = stage_und_flags(reifegrad)
        nr_js = nr if nr.isdigit() else f"'{js(nr)}'"
        flags_js = "[" + ",".join(f"'{f}'" for f in flags) + "]"
        items.append(
            f"    [{nr_js},'{js(bereich)}','{js(kurz)}','{js(umsetzung)}',"
            f"{stage},{flags_js},'','{js(reifegrad)}'],")
    for w in warnungen:
        print("  ! " + w)
    return items


def splice(items: list[str]) -> None:
    html = BOARD.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(html) if "var ITEMS = [" in l)
    end = next(i for i in range(start + 1, len(html)) if html[i].strip() == "];")
    neu = html[: start + 1] + items + html[end:]
    BOARD.write_text("\n".join(neu) + "\n", encoding="utf-8")
    print(f"  {len(items)} Items geschrieben (Array-Zeilen {start+2}..{start+1+len(items)}).")


if __name__ == "__main__":
    items = parse_backlog()
    if len(items) < 20:
        sys.exit(f"Nur {len(items)} Items geparst — verdächtig, Abbruch.")
    splice(items)
    print("  backlog-board.html aktualisiert.")
