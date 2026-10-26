#!/usr/bin/env python3
"""Render original educational SVG diagrams to small, static PNG files offline.

Uses only Python's standard library and Narada's existing Node/Sharp dependency.
These diagrams are hypothetical teaching aids, not source-manual illustrations
or evidence of strategy performance. Run in a fresh work/ output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
PAPER = "#f4f2ec"
WHITE = "#fffefa"
NAVY = "#253d35"
TEAL = "#16766f"
ORANGE = "#b96739"
MUTED = "#65736b"
LINE = "#d2d8cd"


def text(x: int, y: int, value: str, size: int = 28, color: str = NAVY,
         weight: int = 400, anchor: str = "start") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


def line(x1: int, y1: int, x2: int, y2: int, color: str = LINE,
         width: int = 2, dashed: bool = False, arrow: bool = False) -> str:
    dash = ' stroke-dasharray="11 10"' if dashed else ""
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{width}"{dash}{marker}/>')


def rect(x: int, y: int, width: int, height: int, fill: str = WHITE) -> str:
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'rx="14" fill="{fill}" stroke="{LINE}" stroke-width="2"/>')


def circle(x: int, y: int, color: str, radius: int = 8) -> str:
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>'


def path(points: list[tuple[int, int]], color: str, dashed: bool = False) -> str:
    d = "M " + " L ".join(f"{x} {y}" for x, y in points)
    dash = ' stroke-dasharray="13 11"' if dashed else ""
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="6" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash}/>')


def svg(title: str, subtitle: str, body: str, height: int) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="{height}" viewBox="0 0 1400 {height}">
<title>{escape(title)}</title>
<desc>{escape(subtitle)}</desc>
<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M 0 0 L 9 4.5 L 0 9" fill="{MUTED}"/></marker></defs>
<rect width="1400" height="{height}" fill="{PAPER}"/>
<g font-family="Arial, Helvetica, sans-serif">
{text(54, 66, title, 42, weight=600)}
{text(54, 113, subtitle, 26, MUTED)}
{body}
</g></svg>'''


def impulse_pullback() -> str:
    parts = [rect(48, 156, 642, 554), rect(710, 156, 642, 554)]
    parts.extend([text(78, 209, "Bullish illustration", 31, TEAL, 600),
                  text(740, 209, "Bearish illustration", 31, ORANGE, 600)])
    parts.extend([line(110, 655, 640, 655, MUTED, arrow=True),
                  line(774, 655, 1304, 655, MUTED, arrow=True),
                  text(375, 689, "Time", 23, MUTED, anchor="middle"),
                  text(1039, 689, "Time", 23, MUTED, anchor="middle")])
    parts.extend([line(140, 550, 610, 550, LINE, dashed=True),
                  line(140, 280, 610, 280, LINE, dashed=True),
                  path([(140, 550), (220, 470), (260, 495), (340, 365),
                        (370, 395), (440, 280)], TEAL),
                  path([(440, 280), (480, 335), (505, 318), (550, 425)], ORANGE),
                  path([(550, 425), (582, 352), (615, 240)], MUTED, dashed=True),
                  circle(140, 550, TEAL), circle(440, 280, TEAL), circle(550, 425, ORANGE),
                  text(108, 597, "Origin", 27), text(375, 256, "Extreme", 27),
                  text(462, 476, "Pullback", 27)])
    parts.extend([line(804, 290, 1274, 290, LINE, dashed=True),
                  line(804, 560, 1274, 560, LINE, dashed=True),
                  path([(804, 290), (884, 370), (924, 345), (1004, 475),
                        (1034, 445), (1104, 560)], ORANGE),
                  path([(1104, 560), (1144, 505), (1169, 522), (1214, 415)], TEAL),
                  path([(1214, 415), (1246, 488), (1279, 600)], MUTED, dashed=True),
                  circle(804, 290, ORANGE), circle(1104, 560, ORANGE), circle(1214, 415, TEAL),
                  text(780, 260, "Origin", 27), text(1040, 605, "Extreme", 27),
                  text(1170, 383, "Pullback", 27)])
    parts.extend([text(54, 763, "Impulse: first move  ·  Pullback: retracement", 25, MUTED),
                  text(54, 803, "Dashed line: one possible continuation; the path may also fail or reverse.", 25, MUTED)])
    return svg("Impulse and pullback", "Hypothetical paths · no forecast or measured probability", "\n".join(parts), 840)


def decision_workflow() -> str:
    parts = []
    steps = [("Observe", "Read the context", TEAL),
             ("Define plan", "Set conditions", NAVY),
             ("Confirm", "Check the setup", TEAL),
             ("Execute", "Record the action", ORANGE),
             ("Review", "Compare to plan", NAVY)]
    for i, (label, detail, color) in enumerate(steps):
        x = 54 + i * 258
        parts.extend([rect(x, 206, 228, 190), circle(x + 32, 245, color, 16),
                      text(x + 32, 253, str(i + 1), 22, WHITE, 600, "middle"),
                      text(x + 22, 307, label, 31, color, 600),
                      text(x + 22, 358, detail, 22, MUTED)])
        if i < 4:
            parts.append(line(x + 235, 302, x + 253, 302, MUTED, 2, arrow=True))
    parts.extend([rect(54, 459, 745, 118), rect(824, 459, 516, 118),
                  text(80, 502, "Before execution", 28, TEAL, 600),
                  text(80, 546, "Planned levels can change as context changes.", 25, MUTED),
                  text(850, 502, "After execution", 28, ORANGE, 600),
                  text(850, 546, "Recorded execution stays fixed.", 25, MUTED),
                  text(54, 652, "A general decision process; no indicator mechanics or entry rules are implied.", 25, MUTED)])
    return svg("From observation to review", "Generic workflow · keep the plan and the execution record distinct", "\n".join(parts), 706)


def position_sizing() -> str:
    parts = [rect(54, 189, 773, 373), rect(963, 274, 377, 214),
             text(440, 240, "Cash risk budget", 34, TEAL, 600, "middle"),
             text(440, 294, "planned cash-loss allowance", 25, MUTED, anchor="middle"),
             line(113, 331, 768, 331, NAVY, 3),
             text(440, 388, "Cash risk per unit", 34, ORANGE, 600, "middle"),
             text(440, 443, "entry-to-stop distance", 28, anchor="middle"),
             text(440, 486, "× cash value per price unit", 28, anchor="middle"),
             text(440, 530, "use the same currency as the risk budget", 23, MUTED, anchor="middle"),
             text(894, 397, "=", 57, MUTED, anchor="middle"),
             text(1151, 359, "Position size", 35, NAVY, 600, "middle"),
             text(1151, 416, "in tradable units", 28, MUTED, anchor="middle"),
             text(54, 640, "Conceptual sizing · before fees/slippage", 27, TEAL, 600),
             text(54, 688, "Tradable increments and instrument conventions still apply.", 25, MUTED),
             text(54, 734, "This relationship does not choose a risk budget, stop level, or trade.", 25, MUTED)]
    return svg("The position-sizing relationship", "A conceptual calculation · no numerical example or investment recommendation", "\n".join(parts), 782)


ASSETS = [
    ("structure", "Impulse and pullback", impulse_pullback,
     "Two hypothetical price paths label origin, extreme and pullback in bullish and bearish directions. Dashed paths show possible continuation without forecasting it."),
    ("workflow", "From observation to review", decision_workflow,
     "Observe, define plan, confirm, execute and review. Planned levels may change before execution, while recorded execution stays fixed."),
    ("sizing", "The position-sizing relationship", position_sizing,
     "Position size equals cash risk budget divided by cash risk per unit. Cash risk per unit uses stop distance and cash value per price unit, before fees and slippage."),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory under workspace work/")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "work"):
        parser.error("output must be staged under workspace work/")
    if output.exists():
        parser.error("output already exists; use a fresh directory")
    node = shutil.which("node")
    sharp = ROOT / "apps/narada/node_modules/sharp"
    if not node or not sharp.is_dir():
        parser.error("requires Node and Narada's already-installed Sharp; no packages are installed by this tool")
    info = subprocess.run([node, "-e", "process.stdout.write(JSON.stringify({node:process.version,sharp:require(process.argv[1]).versions}));", str(sharp)],
                          check=True, capture_output=True, text=True)
    renderer = json.loads(info.stdout)
    render_js = """const sharp=require(process.argv[1]);
sharp(process.argv[2]).png({compressionLevel:9,palette:true,quality:100,dither:0}).toFile(process.argv[3]).then(info=>process.stdout.write(JSON.stringify(info))).catch(error=>{console.error(error);process.exit(1);});"""
    output.mkdir(parents=True)
    inventory = []
    for slug, title, make_svg, alt in ASSETS:
        vector = output / f"{slug}.svg"
        raster = output / f"{slug}.png"
        vector.write_text(make_svg() + "\n", encoding="utf-8")
        render = subprocess.run([node, "-e", render_js, str(sharp), str(vector), str(raster)],
                                check=True, capture_output=True, text=True)
        png_info = json.loads(render.stdout)
        if raster.stat().st_size >= 150 * 1024:
            raise RuntimeError(f"{raster.name} exceeds the static asset budget")
        inventory.append({"file": raster.name, "title": title, "alt": alt,
                          "width": png_info["width"], "height": png_info["height"],
                          "bytes": raster.stat().st_size, "sha256": digest(raster),
                          "svg_file": vector.name, "svg_sha256": digest(vector),
                          "origin": "Original Abacus educational diagram; no source image reproduced"})
    metadata = {"schema_version": 1, "purpose": "Original static reading-companion teaching diagrams",
                "generator": str(Path(__file__).relative_to(ROOT)), "generator_sha256": digest(Path(__file__)),
                "python": platform.python_version(), "renderer": renderer,
                "fonts": "Arial, Helvetica, sans-serif; resolved by local SVG rasterizer",
                "npm_lock_sha256": digest(ROOT / "apps/narada/package-lock.json"),
                "generator_argv": sys.argv,
                "reproduction_command": "UV_CACHE_DIR=/private/tmp/abacus-manual24-uv ./scripts/uv run --locked --no-sync python studies/24_trader_assistant_manual/illustrate.py --output <fresh-work-directory>/figures",
                "asset_budget_bytes_each": 150 * 1024, "assets": inventory}
    (output / "assets.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "assets": [{"file": a["file"], "bytes": a["bytes"]} for a in inventory]}))


if __name__ == "__main__":
    main()
