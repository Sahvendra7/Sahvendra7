"""Fail loudly on card content that would render wrong.

Both failure modes here are silent in build_assets.py: wrap() drops any
description past three lines, and an over-wide trace row just runs off the
card edge. Run this before build_assets.py.
"""

from __future__ import annotations

import sys

from build_assets import BODY, DISPLAY_SEMI, MONO_MED, PROJECTS, wrap

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


def main() -> int:
    failed = False
    for p in PROJECTS:
        for msg in problems(p):
            print(f"FAIL {p['slug']}: {msg}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print(f"ok: {len(PROJECTS)} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
