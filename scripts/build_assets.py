"""Generate the profile README artwork in ../assets.

Text is converted to outlines so the SVGs render identically everywhere
(GitHub serves README images through a proxy that cannot load web fonts).

    pip install fonttools uharfbuzz
    python scripts/build_assets.py

Fonts: Inter Display and JetBrains Mono (both SIL OFL). Override the
paths with INTER_DIR / JBMONO_DIR if they live elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
INTER = Path(os.environ.get("INTER_DIR", "/usr/share/fonts/opentype/inter"))
JB = Path(os.environ.get("JBMONO_DIR", "/usr/share/fonts/truetype/jetbrains-mono"))

# Colour tokens. Each signal colour carries one meaning across every image.
INK = "#0D1626"
GRID = "#16233A"
LINE = "#2A3B57"
TEXT = "#E6EDF7"
MUTED = "#8CA0BD"
SKY = "#7DD3FC"  # data moving through the system
AMBER = "#FBBF24"  # model output: probabilistic, untrusted until checked
GREEN = "#6EE7A8"  # deterministic check: the code that decides

KIND = {"data": SKY, "model": AMBER, "check": GREEN}


class Font:
    def __init__(self, path: Path):
        blob = hb.Blob.from_file_path(str(path))
        self.hb_font = hb.Font(hb.Face(blob))
        self.tt = TTFont(str(path))
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm

    def shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text: str, size: float, tracking: float = 0) -> float:
        _, pos = self.shape(text)
        scale = size / self.upem
        return sum(p.x_advance for p in pos) * scale + tracking * max(len(pos) - 1, 0)

    def path(self, text: str, size: float, x: float, y: float, tracking: float = 0) -> str:
        infos, pos = self.shape(text)
        scale = size / self.upem
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        cx = x
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            t = (scale, 0, 0, -scale, cx + p.x_offset * scale, y - p.y_offset * scale)
            self.glyphs[name].draw(TransformPen(pen, t))
            cx += p.x_advance * scale + tracking
        return pen.getCommands()


DISPLAY_BOLD = Font(INTER / "InterDisplay-Bold.otf")
DISPLAY_SEMI = Font(INTER / "InterDisplay-SemiBold.otf")
DISPLAY_MED = Font(INTER / "InterDisplay-Medium.otf")
BODY = Font(INTER / "Inter-Regular.otf")
MONO = Font(JB / "JetBrainsMono-Regular.ttf")
MONO_MED = Font(JB / "JetBrainsMono-Medium.ttf")


def txt(font: Font, s: str, size: float, x: float, y: float, fill: str,
        anchor: str = "start", tracking: float = 0, extra: str = "") -> str:
    if anchor != "start":
        w = font.width(s, size, tracking)
        x -= w / 2 if anchor == "middle" else w
    return f'<path d="{font.path(s, size, x, y, tracking)}" fill="{fill}"{extra}/>'


def wrap(font: Font, s: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and font.width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def dot_grid(w: int, h: int, step: int = 24) -> str:
    return (
        f'<pattern id="g" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<circle cx="1" cy="1" r="1" fill="{GRID}"/></pattern>'
        f'<rect width="{w}" height="{h}" fill="url(#g)"/>'
    )


def svg(w: int, h: int, title: str, body: str, style: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">'
        f"<title id=\"t\">{title}</title>"
        + (f"<style>{style}</style>" if style else "")
        + body
        + "</svg>\n"
    )


# --------------------------------------------------------------------------
# Hero: one trace, from model output to an approved action.
# --------------------------------------------------------------------------

def hero() -> str:
    W, H = 1200, 400
    pad = 64
    parts = [
        f'<defs><clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
        f'<radialGradient id="glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate(1040 300) scale(520 260)">'
        f'<stop offset="0" stop-color="{GREEN}" stop-opacity=".10"/>'
        f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient></defs>',
        '<g clip-path="url(#c)">',
        f'<rect width="{W}" height="{H}" fill="{INK}"/>',
        dot_grid(W, H),
        f'<rect width="{W}" height="{H}" fill="url(#glow)" class="glow"/>',
        "</g>",
        f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="17.5" fill="none" stroke="{LINE}"/>',
        txt(DISPLAY_BOLD, "Sahvendra", 76, pad - 4, 128, TEXT, tracking=-1.6),
        txt(DISPLAY_MED, "AI may propose. Deterministic code decides.", 28, pad - 1, 178, SKY, tracking=-.2),
        txt(BODY, "Backend and systems engineer at IIT Kharagpur, building agents, RAG", 18, pad, 218, MUTED),
        txt(BODY, "pipelines and payment gateways that stay inside rules you can audit.", 18, pad, 244, MUTED),
    ]

    # Legend: explains the colour code used in every image on the profile.
    lx, ly = W - pad, 70
    legend = [("model output", AMBER), ("data", SKY), ("deterministic check", GREEN)]
    for i, (label, col) in enumerate(legend):
        y = ly + i * 24
        parts.append(txt(MONO, label, 13, lx - 18, y + 4.5, MUTED, anchor="end"))
        parts.append(f'<circle cx="{lx - 5}" cy="{y}" r="4.5" fill="{col}"/>')

    # The trace.
    steps = [
        ("agent intent", "model"),
        ("retrieve", "data"),
        ("grade", "model"),
        ("verify sha-256", "check"),
        ("policy", "check"),
        ("approved", "check"),
    ]
    ty = 326
    size = 15
    node_pad = 18
    widths = [MONO_MED.width(s, size) + node_pad * 2 for s, _ in steps]
    gap = (W - 2 * pad - sum(widths)) / (len(steps) - 1)
    xs, x = [], pad
    for w in widths:
        xs.append(x)
        x += w + gap

    cycle = 8.0
    travel = 5.2
    arrive = [(xs[i] + widths[i] / 2 - (xs[0] + widths[0] / 2)) for i in range(len(steps))]
    span = arrive[-1]

    parts.append(
        f'<line x1="{xs[0] + widths[0]/2:.1f}" y1="{ty}" x2="{xs[-1] + widths[-1]/2:.1f}" y2="{ty}" '
        f'stroke="{LINE}" stroke-width="2" stroke-dasharray="2 6" stroke-linecap="round"/>'
    )

    css = [
        f"@keyframes run{{0%{{transform:translateX(0)}}{travel/cycle*100:.2f}%,100%{{transform:translateX({span:.1f}px)}}}}",
        ".pk{animation:run %.1fs cubic-bezier(.45,0,.55,1) infinite}" % cycle,
        "@keyframes pkc{0%%,%.2f%%{fill:%s}%.2f%%,100%%{fill:%s}}"
        % (arrive[2] / span * travel / cycle * 100 + 2, AMBER, arrive[3] / span * travel / cycle * 100, GREEN),
        ".pk circle.core{animation:pkc %.1fs linear infinite}" % cycle,
        "@keyframes done{0%%,%.2f%%{opacity:0}%.2f%%,96%%{opacity:1}100%%{opacity:0}}"
        % (travel / cycle * 100, travel / cycle * 100 + 3),
        ".done{animation:done %.1fs ease-out infinite}" % cycle,
    ]

    # The packet travels behind the nodes, so it shows only on the wires.
    x_start = xs[0] + widths[0] / 2
    parts.append(
        f'<g class="pk"><circle cx="{x_start:.1f}" cy="{ty}" r="11" fill="{TEXT}" opacity=".08"/>'
        f'<circle class="core" cx="{x_start:.1f}" cy="{ty}" r="5" fill="{GREEN}"/></g>'
    )

    for i, ((label, kind), x0, w) in enumerate(zip(steps, xs, widths)):
        col = KIND[kind]
        on = arrive[i] / span * travel / cycle * 100 if span else 0
        css.append(
            f"@keyframes n{i}{{0%,{max(on-1,0):.2f}%{{opacity:.28}}{on:.2f}%,94%{{opacity:1}}100%{{opacity:.28}}}}"
            f".n{i}{{animation:n{i} {cycle}s ease-out infinite}}"
        )
        last = i == len(steps) - 1
        parts.append(
            f'<g class="n{i}">'
            f'<rect x="{x0:.1f}" y="{ty-21}" width="{w:.1f}" height="42" rx="{21 if last else 8}" '
            f'fill="{INK}" stroke="{col}" stroke-width="1.5"/>'
            + txt(MONO_MED, label, size, x0 + w / 2, ty + 5.5, col if last else TEXT, anchor="middle")
            + "</g>"
        )

    parts.append(
        '<g class="done">'
        + txt(MONO, "every claim traced to its source", 13, xs[-1] + widths[-1], ty + 46, GREEN,
              anchor="end", extra=' opacity=".85"')
        + "</g>"
    )

    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}.pk{transform:translateX(%.1fpx)}}" % span)
    return svg(W, H, "Sahvendra: AI may propose. Deterministic code decides.", "".join(parts), "".join(css))


# --------------------------------------------------------------------------
# Project cards: each one shows its own pipeline in the same colour code.
# --------------------------------------------------------------------------

PROJECTS = [
    {
        "slug": "signalpost-agent",
        "name": "Signalpost Agent",
        "desc": "Autonomous research agent that emits deterministic claims, each verified "
                "against the Brønnøysund company registry and pinned to SHA-256 byte provenance.",
        "trace": [("research", "model"), ("registry", "check"), ("sha-256", "check")],
        "tech": "Python, uv",
    },
    {
        "slug": "corrective-rag",
        "name": "Corrective RAG Analyzer",
        "desc": "Academic paper analyser that grades its own retrievals, falls back to web "
                "search when they are weak, and checks answers for hallucination.",
        "trace": [("retrieve", "data"), ("grade", "model"), ("web fallback", "data"), ("check", "check")],
        "tech": "FastAPI, LangGraph, FAISS",
    },
    {
        "slug": "vilr",
        "name": "VILR",
        "desc": "Zero-trust authorization gateway for agent-driven payments. The AI states "
                "an intent; a deterministic policy engine decides whether money moves.",
        "trace": [("intent", "model"), ("opa policy", "check"), ("pay", "check")],
        "tech": "Python, Redis, OPA, Docker",
    },
    {
        "slug": "udp-media",
        "name": "UDP Media Delivery",
        "desc": "Reliable real-time media over UDP, recovering from packet loss and "
                "reordering while staying inside a strict delay budget.",
        "trace": [("packet", "data"), ("detect loss", "data"), ("recover", "check")],
        "tech": "C, Python, Make",
    },
    {
        "slug": "rate-limiter",
        "name": "Rate-Limiter",
        "desc": "High-throughput distributed rate limiting with token buckets, sliding "
                "windows and idempotency keys, backed by Redis.",
        "trace": [("request", "data"), ("token bucket", "check"), ("allow / 429", "check")],
        "tech": "Python, Redis",
    },
]


def card(p: dict) -> str:
    W, H = 600, 236
    pad = 30
    parts = [
        f'<defs><clipPath id="c"><rect width="{W}" height="{H}" rx="12"/></clipPath></defs>',
        '<g clip-path="url(#c)">',
        f'<rect width="{W}" height="{H}" fill="{INK}"/>',
        dot_grid(W, H),
        "</g>",
        f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="11.5" fill="none" stroke="{LINE}"/>',
        txt(DISPLAY_SEMI, p["name"], 26, pad - 1, 54, TEXT, tracking=-.3),
        txt(MONO, p["tech"], 12.5, W - pad, 52, MUTED, anchor="end"),
    ]
    for i, line in enumerate(wrap(BODY, p["desc"], 15, W - 2 * pad)[:3]):
        parts.append(txt(BODY, line, 15, pad, 88 + i * 23, MUTED))

    ty, size, npad, arrow = 192, 12.5, 12, 26
    x = pad
    for i, (label, kind) in enumerate(p["trace"]):
        col = KIND[kind]
        w = MONO_MED.width(label, size) + npad * 2
        parts.append(
            f'<rect x="{x:.1f}" y="{ty-15}" width="{w:.1f}" height="30" rx="7" fill="{INK}" stroke="{col}" stroke-width="1.25"/>'
            + txt(MONO_MED, label, size, x + w / 2, ty + 4.5, TEXT, anchor="middle")
        )
        x += w
        if i < len(p["trace"]) - 1:
            parts.append(
                f'<path d="M{x+6:.1f} {ty}H{x+arrow-8:.1f}m-4-4 4 4-4 4" fill="none" stroke="{MUTED}" '
                f'stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>'
            )
            x += arrow
    return svg(W, H, f'{p["name"]}: {p["desc"]}', "".join(parts))


def main() -> None:
    (OUT / "projects").mkdir(parents=True, exist_ok=True)
    (OUT / "hero.svg").write_text(hero(), encoding="utf-8")
    for p in PROJECTS:
        (OUT / "projects" / f'{p["slug"]}.svg').write_text(card(p), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
