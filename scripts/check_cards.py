"""Fail loudly on anything that would render wrong or go missing.

Every failure guarded here is silent in build_assets.py: wrap() drops any
description past three lines, an over-wide trace row runs off the card edge,
an unescaped character makes the SVG unparseable, and a README pointing at a
slug the script no longer writes is a broken image on the live profile.

Run from the repository root, as a script so that scripts/ is on sys.path:

    python3 scripts/check_cards.py
"""

from __future__ import annotations

import pathlib
import re
import sys
import xml.etree.ElementTree as ET

from build_assets import BODY, DISPLAY_SEMI, MONO_MED, OUT, PROJECTS, card, wrap

W, PAD, NPAD, ARROW = 600, 30, 12, 26
INNER = W - 2 * PAD
DESC_SIZE, TRACE_SIZE, NAME_SIZE, TECH_SIZE = 15, 12.5, 26, 12.5
HEAD_GAP = 24


def problems(p: dict) -> list[str]:
    out = []

    lines = wrap(BODY, p["desc"], DESC_SIZE, INNER)
    if len(lines) > 3:
        out.append(f"desc wraps to {len(lines)} lines, card draws only 3 "
                   f"(drop ~{len(' '.join(lines[3:]))} chars)")

    row = sum(MONO_MED.width(label, TRACE_SIZE) + 2 * NPAD for label, _ in p["trace"])
    row += ARROW * (len(p["trace"]) - 1)
    if row > INNER:
        out.append(f"trace row {row:.0f}px wide, card fits {INNER}px")

    head = (DISPLAY_SEMI.width(p["name"], NAME_SIZE)
            + MONO_MED.width(p["tech"], TECH_SIZE) + HEAD_GAP)
    if head > INNER:
        out.append(f"name + tech {head:.0f}px wide, card fits {INNER}px")

    bad = [k for _, k in p["trace"] if k not in ("data", "model", "check")]
    if bad:
        out.append(f"unknown trace kinds {bad}")

    return out


def renders(p: dict) -> list[str]:
    """Render the card and parse it, so unescaped copy cannot ship."""
    try:
        ET.fromstring(card(p))
    except ET.ParseError as exc:
        return [f"renders to unparseable SVG ({exc}) — check & < > in name/desc/tech"]
    return []


def readme_refs() -> list[str]:
    """Every referenced card must exist, and every card must be referenced."""
    readme = pathlib.Path("README.md")
    if not readme.exists():
        return ["README.md not found — run from the repository root"]

    refs = set(re.findall(r'src="(assets/[^"]+)"', readme.read_text(encoding="utf-8")))
    out = []

    for ref in sorted(refs):
        if not pathlib.Path(ref).exists():
            out.append(f"README references {ref}, which no script writes (broken image)")

    expected = {f"{OUT.name}/projects/{p['slug']}.svg" for p in PROJECTS}
    for ref in sorted(expected - refs):
        out.append(f"{ref} is generated but the README never shows it")

    carddir = pathlib.Path(OUT / "projects")
    if carddir.exists():
        for f in sorted(carddir.iterdir()):
            rel = f"{OUT.name}/projects/{f.name}"
            if rel not in expected:
                out.append(f"{rel} is left over — no PROJECTS entry generates it")

    return out


def main() -> int:
    failed = False
    for p in PROJECTS:
        for msg in problems(p) + renders(p):
            print(f"FAIL {p['slug']}: {msg}", file=sys.stderr)
            failed = True

    for msg in readme_refs():
        print(f"FAIL readme: {msg}", file=sys.stderr)
        failed = True

    if failed:
        return 1
    print(f"ok: {len(PROJECTS)} cards, README refs consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
