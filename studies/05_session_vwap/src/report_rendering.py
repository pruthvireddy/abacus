"""Offline presentation of precomputed VWAP study tables and saved evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json
import re
import struct
import zlib

import pandas as pd

LABELS = {"B": "Return after departure", "A": "First outside-2σ fade",
          "C": "First VWAP retest bounce"}


def _fmt(value, percent=False):
    if value is None or pd.isna(value):
        return "—"
    if percent:
        return f"{100 * value:.1f}%"
    return f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"


def write_figure(stage: Path, cards: pd.DataFrame) -> None:
    """Small offline SVG of the exhaustive primary A/C barrier outcomes."""
    (stage / "figures").mkdir(exist_ok=True)
    colors = {"favorable": "#2b8a6e", "adverse": "#cf604a",
              "neither": "#a4afc0", "ambiguous": "#8a6cb3"}
    labels = {"A": "Outside 2σ fade", "C": "First retest bounce"}
    parts = ["<svg xmlns='http://www.w3.org/2000/svg' width='900' height='250' viewBox='0 0 900 250'>",
             "<rect width='900' height='250' fill='#fff'/>",
             "<text x='30' y='30' font-size='20' font-family='system-ui' fill='#16223a'>30-minute barrier outcomes</text>"]
    for order, strategy in enumerate(("A", "C")):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        y = 75 + 70 * order
        parts.append(f"<text x='30' y='{y+16}' font-size='15' font-family='system-ui' fill='#16223a'>{labels[strategy]}</text>")
        left = 210
        for name in ("favorable", "adverse", "neither", "ambiguous"):
            width = 620 * int(row[name]) / row.evaluable if row.evaluable else 0
            parts.append(f"<rect x='{left:.2f}' y='{y}' width='{width:.2f}' height='28' fill='{colors[name]}'/>")
            left += width
        parts.append(f"<text x='840' y='{y+19}' font-size='13' font-family='system-ui' fill='#16223a'>n={row.evaluable:,}</text>")
    x = 30
    for name in ("favorable", "adverse", "neither", "ambiguous"):
        parts.append(f"<rect x='{x}' y='210' width='12' height='12' fill='{colors[name]}'/>")
        parts.append(f"<text x='{x+18}' y='221' font-size='13' font-family='system-ui' fill='#16223a'>{name.title()}</text>")
        x += 155
    parts.append("</svg>")
    (stage / "figures/barrier-outcomes.svg").write_text("".join(parts))
    # A compact PNG copy is selected explicitly for Narada's raster-only contract.
    width, height = 900, 250
    pixels = bytearray([255, 255, 255] * width * height)
    rgb = {"favorable": (43, 138, 110), "adverse": (207, 96, 74),
           "neither": (164, 175, 192), "ambiguous": (138, 108, 179)}
    def rect(x0, y0, x1, y1, color):
        for yy in range(y0, y1):
            start = (yy * width + x0) * 3
            pixels[start:start + (x1 - x0) * 3] = bytes(color) * (x1 - x0)
    for order, strategy in enumerate(("A", "C")):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        y = 70 + 70 * order
        x = 180
        cumulative = 0
        for name in ("favorable", "adverse", "neither", "ambiguous"):
            cumulative += int(row[name])
            end = min(800, 180 + round(620 * cumulative / row.evaluable)) if row.evaluable else x
            if end > x:
                rect(x, y, end, y + 32, rgb[name])
            x = end
    for i, name in enumerate(("favorable", "adverse", "neither", "ambiguous")):
        rect(180 + i * 155, 215, 205 + i * 155, 230, rgb[name])
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    scanlines = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3]
                         for y in range(height))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))
    (stage / "figures/barrier-outcomes.png").write_bytes(png)


def write_report(stage: Path, cards: pd.DataFrame, breaks: pd.DataFrame,
                 horizons: pd.DataFrame, cycles: pd.DataFrame, controls: pd.DataFrame,
                 samples: pd.DataFrame, events: pd.DataFrame, windows: pd.DataFrame) -> None:
    audit = json.loads((stage / "source-audit.json").read_text())
    checked_bars = sum(int(item.get("feature_bars_reconciled", 0)) for item in audit)
    checked_refs = sum(int(item.get("references_audited", 0)) for item in audit)
    lines = ["# Three session VWAP statistical studies", "",
             "Price-path evidence from the pinned Session-Anchored VWAP 1.0.0 release. "
             "Commission, slippage, latency, order type, and position sizing are unspecified. "
             "These are conditional movement observations, not net profitability.", "",
             "## Three-candidate scorecard", "",
             "| Candidate | Evaluable / events | Distinct product-sessions | Primary outcome | 95% session bootstrap interval |",
             "|---|---:|---:|---:|---:|"]
    for strategy in ("B", "A", "C"):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        label = LABELS[strategy]
        interval = f"{_fmt(row.ci_low, True)}–{_fmt(row.ci_high, True)}" if pd.notna(row.ci_low) else "unavailable"
        lines.append(f"| {label} | {row.evaluable:,} / {row.events:,} | {row.sessions:,} | "
                     f"{row.successes:,}/{row.evaluable:,} ({_fmt(row.rate, True)}) | {interval} |")
    lines += ["", "The scorecard pools seven overlapping anchor/window views and two correlated timeframes. "
              "Counts are events within those views; the session column deduplicates product × date. "
              "The bootstrap resamples shared session dates, retaining the correlated views and products together.", "",
              "![Exhaustive 30-minute barrier outcomes for A and C](figures/barrier-outcomes.svg)", "",
              "## Coverage and sample construction", "",
              f"The saved windows table contains {len(windows):,} product × date × timeframe × anchor/window views. "
              f"The pinned publication includes {windows[['product','session_date']].drop_duplicates().shape[0]:,} "
              "eligible product-days. Its retrospective eligibility audit excludes incomplete product-days; "
              "this cannot be used as an entry-time filter. `tables/eligibility.csv` has year-by-year candidate, "
              "included, excluded, and overlapping reason counts. See `tables/cycles.csv` for mature windows, "
              "already-away/fresh departures, no-departure windows, unqualified first touches, gaps, and cycles.", "",
              f"Source reconciliation verified {checked_bars:,} published feature bars and {checked_refs:,} "
              "evaluable event reference opens against the pinned unadjusted one-minute data. "
              "The source audit also checked exclusive-close availability and adjustment constancy by session.", "",
              "## Exact setup definitions", "",
              "See `protocol-1.0.0.md`. Features are known at exclusive bar close; paths begin at the following "
              "unadjusted one-minute open as an idealized observation, not a guaranteed fill. "
              "B is the first close at least 1σ and four ticks away in each view. "
              "A uses the first published close exit outside 2σ per rearmed excursion. C requires a meaningful "
              "departure, ten elapsed minutes of completed same-side closes, and the first causal VWAP-zone touch. "
              "No C touch-bar extreme counts as post-signal movement.", "",
              "## Frequency and denominators", "",
              "`tables/scorecards.csv`, `tables/breakdowns.csv`, and `tables/cycles.csv` give event, evaluable, "
              "eligible-window, mature-window, departure-window, and distinct-session denominators. "
              "`tables/departure_classes.csv` separates already-away and fresh B departures. "
              "`tables/window_populations.csv` retains no-departure windows by product, year, split, timeframe, "
              "anchor, and observation window. "
              "`tables/exclusions.csv` counts zero-follow-up, discontinuity, late, and already-at-target cases; "
              "the event evidence retains their individual flags.", "",
              f"Meaningful first departures occurred in {int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].departure_windows):,} "
              f"of {len(windows):,} eligible views; these views share dates and price paths. "
              "The remaining views had no qualifying departure.", "",
              "## Return time and movement", "",
              "`tables/horizons.csv` shows 10/30/60-minute return or barrier curves, signed movement, and "
              "full-horizon MFE/MAE; it also provides a common 60-minute-capable cohort. "
              "B nonreturners remain in window-end denominators and are censored in time-to-return summaries. "
              "Departures already at the frozen target on the reference open remain visible and receive no fresh-return credit. "
              "`tables/return_survival.csv` retains returners and censored nonreturners in descriptive survival curves; "
              "interpreting those curves as population return times would require independent administrative censoring "
              "conditional on departure time and other context, which this study does not establish. "
              "Conditional median return time among successes is not an expected waiting time for all departures. "
              "Saved event times are zero-based one-minute bar offsets; intraminute contact times are unknown. "
              "Frozen and evolving VWAP contacts are independent observations; saved events include actual price "
              "retracement and VWAP movement. Pre-return adverse extension has lower/upper bounds because "
              "the order of extremes inside the one-minute contact bar is unknown.", "",
              f"For B, {int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].h30_frozen_returns):,} "
              f"of {int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].h30_n):,} "
              "30-minute-capable departures returned to frozen VWAP within 30 minutes; "
              f"{int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].evolving_returns):,} "
              "had evolving-VWAP contact by window end. The median observed wait among frozen returners "
              f"was {_fmt(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].conditional_return_median_minutes)} minutes. "
              "Globex full-session outcomes allow much longer follow-up than local-window outcomes, so the "
              "window-end return rate is strongly horizon dependent.", "",
              "## Favorable, adverse, timeout, and ambiguous outcomes", "",
              "A and C use equal 0.5σ barriers rounded up to whole ticks. The four outcomes are exhaustive among "
              "evaluable events. Ambiguity remains in the denominator, with optimistic success bounds reported. "
              "An open beyond a barrier is flagged as an open-gap first passage. "
              "Full-horizon excursions can occur after the first barrier and should not be read as capturable under "
              "a stopped policy. `tables/paths.csv` contrasts full-horizon and pre-barrier excursions plus "
              "window-end outcomes. `tables/sensitivity.csv` contains the one-at-a-time barrier and fixed-tick grids; "
              "`tables/threshold_times.csv` records descriptive full-window movement-threshold times without a stop; "
              "`tables/warmup_sensitivity.csv` compares the 20-, 30-, and 40-minute full reruns.", "",
              "A and C both have more adverse-first than favorable-first outcomes at the primary barrier. "
              "For C, the approach-side close confirmation subset is in `tables/subsets.csv`; "
              "it does not replace the all-touch primary population. The warm-up and barrier grids are "
              "sensitivity descriptions, not optimized settings.", "",
              "## Baseline comparisons", ""]
    for row in controls[(controls["product"] == "ALL") &
                        (controls.barrier_definition == "half_sigma")].itertuples(index=False):
        ci = (f"; shared-date bootstrap interval {_fmt(row.ci_low_conditional_overlap, True)}–"
              f"{_fmt(row.ci_high_conditional_overlap, True)}" if pd.notna(row.ci_low_conditional_overlap) else "")
        lines.append(f"- {row.split} — {row.treated} versus {row.control}: {row.matched_treated if pd.notna(row.matched_treated) else 'unmatched'} "
                     f"matched treated events; observed difference {_fmt(row.difference, True)}{ci}. "
                     f"{row.claim_status}.")
    lines += ["", "Matching bins for hour, anchor age, and sigma are learned from development data. "
              "The A extreme and 1–2σ controls have disjoint distance support by design; remaining distance "
              "differences, unmatched counts, and a common fixed 8-tick barrier comparison are in "
              "`tables/baselines.csv`. These observational contrasts "
              "have session bootstrap intervals conditional on the observed matching overlap and weights. "
              "They do not establish a familywise-adjusted advantage.", "",
              "The pooled A half-sigma contrast is small and its 2024 and final-period intervals include zero. "
              "With a common fixed 8-tick barrier, A trails its control in the final period. "
              "C has no stable advantage over near approaches; first C retests do not outperform later ones "
              "in the final period. Neither candidate has a demonstrated incremental edge.", "",
              "## Calendar and chronological stability", "",
              "`tables/breakdowns.csv` separates product, timeframe, anchor/window, direction, development, "
              "validation, final evaluation, and calendar year. `tables/stability.csv` aligns the three splits "
              "in one row per product/timeframe/anchor/window. Sparse and degenerate intervals are flagged. "
              "The final period is chronological, but prior unseen status is not certified. "
              "Two agreeing timeframes are correlated observations.", "",
              "Pooled view-level primary rates by period:", "",
              "| Candidate | Development | 2024 validation | 2025–2026 final |",
              "|---|---:|---:|---:|"]
    period_rows = breaks[breaks.breakdown == "product+timeframe+anchor+window+split"]
    for strategy in ("B", "A", "C"):
        rates = []
        for period in ("development", "validation", "final"):
            part = period_rows[(period_rows.strategy == strategy) & (period_rows.split == period)]
            rates.append(_fmt(part.successes.sum() / part.evaluable.sum(), True))
        lines.append(f"| {LABELS[strategy]} | {' | '.join(rates)} |")
    lines += ["",
              "## Representative examples", "",
              "`tables/examples.csv` selects the earliest timestamp in each product × candidate × outcome class. "
              "Each row links to the stable event ID in retained Parquet evidence. These are deterministic "
              "illustrations, not hand-picked successes.", "",
              "| Product | Candidate | Class | Signal (UTC) | Event ID |",
              "|---|---|---|---|---|"]
    for _, example in samples.sort_values(["product", "strategy", "class"]).iterrows():
        lines.append(f"| {example['product']} | {example['strategy']} | {example['class']} | "
                     f"{example['signal_ts']} | `{example['event_id']}` |")
    lines += ["",
              "## Limitations and research advice", "",
              "No net trading conclusion follows from a return rate or movement barrier rate. "
              "Execution research still needs order type, spread/slippage, commission, latency, position size, "
              "overlap handling, and fill behavior at gaps and touched levels. Broad segment grids and controls "
              "are exploratory. The eligibility audit selects complete days retrospectively. "
              "See `advice.md` for candidate-specific dated interpretation.", "",
              "## Reproduce", "",
              "From the workspace root with the locked environment installed, choose a new unique ID and run "
              "`.venv/bin/python studies/05_session_vwap/run.py --run-id <id> --workers 3`, "
              "`.venv/bin/python studies/05_session_vwap/enrich.py --run-id <id> --workers 3`, "
              "`.venv/bin/python studies/05_session_vwap/audit.py --run-id <id>`, and "
              "`.venv/bin/python studies/05_session_vwap/summarize.py --run-id <id>`. "
              "Reproduce warm-up sensitivities with fresh IDs and `--warmup 20` or `--warmup 40`, then run "
              "`warmup_sensitivity.py` with those IDs. Review checks before sealing; never reuse a completed ID. "
              "The manifest records exact code and input hashes.", "",
              "## Saved evidence", "",
              "[Scorecards](tables/scorecards.csv) · [All tables](tables/) · "
              "[Metrics](metrics.json) · [Event evidence manifest](events.manifest.json) · "
              "[Input verification](input-verification.json) · [Source audit](source-audit.json) · "
              "[Denominator audit](denominator-audit.json) · [Run manifest](manifest.json)", ""]
    markdown = "\n".join(lines)
    (stage / "report.md").write_text(markdown)
    html_parts = []
    def inline_html(value: str) -> str:
        escaped = escape(value)
        return re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                      lambda match: f"<a href='{escape(match.group(2), quote=True)}'>{match.group(1)}</a>",
                      escaped)
    in_table = False
    for line in lines:
        if line.startswith("|"):
            cells = [escape(cell.strip()) for cell in line.strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            if not in_table:
                html_parts.append("<table><thead><tr>" + "".join(f"<th>{cell}</th>" for cell in cells) + "</tr></thead><tbody>")
                in_table = True
            else:
                html_parts.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
            continue
        if in_table:
            html_parts.append("</tbody></table>")
            in_table = False
        if not line:
            continue
        if line.startswith("#"):
            level = min(3, len(line) - len(line.lstrip("#")))
            html_parts.append(f"<h{level}>{escape(line.lstrip('# '))}</h{level}>")
        elif line.startswith("!["):
            html_parts.append("<figure><img src='figures/barrier-outcomes.svg' alt='Exhaustive 30-minute barrier outcomes for A and C' width='900'></figure>")
        elif line.startswith("- "):
            html_parts.append(f"<p class='bullet'>• {inline_html(line[2:])}</p>")
        else:
            html_parts.append(f"<p>{inline_html(line)}</p>")
    if in_table:
        html_parts.append("</tbody></table>")
    body = "\n".join(html_parts)
    (stage / "report.html").write_text("<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>Three VWAP statistical studies</title><style>body{font:16px/1.55 system-ui;max-width:1000px;"
        "margin:3rem auto;padding:0 1.5rem;color:#16223a}p{white-space:pre-wrap}h1,h2{margin-top:2rem}"
        "table{border-collapse:collapse;width:100%}th,td{padding:.6rem;border-bottom:1px solid #ccd3de;text-align:left}"
        "th{background:#edf1f6}.bullet{margin:.3rem 0 0 1rem}img{max-width:100%}"
        "</style><main>" + body + "</main></html>\n")


def write_publication(stage: Path, cards: pd.DataFrame) -> None:
    rows = []
    for strategy in ("B", "A", "C"):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        rows.append({"candidate": LABELS[strategy], "events": int(row.events),
                     "evaluable": int(row.evaluable), "successes": int(row.successes),
                     "rate": float(row.rate) if pd.notna(row.rate) else None,
                     "sessions": int(row.sessions),
                     "ciLow": float(row.ci_low) if pd.notna(row.ci_low) else None,
                     "ciHigh": float(row.ci_high) if pd.notna(row.ci_high) else None})
    pub = {"schemaVersion": "1.0", "id": f"vwap-three-{stage.name.lower().replace('_','-')}",
           "title": "Three session VWAP statistical studies",
           "summary": "Price-path outcomes for return after departure, first outside-2σ fades, and first VWAP retest bounces.",
           "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "source": {"producer": "sahadeva", "runId": stage.name},
           "sections": [{"id": "scorecard", "title": "Three-candidate scorecard", "kind": "table",
                         "columns": [{"key": "candidate", "label": "Candidate"},
                                     {"key": "events", "label": "Events"},
                                     {"key": "evaluable", "label": "Evaluable"},
                                     {"key": "sessions", "label": "Product-sessions"},
                                     {"key": "successes", "label": "Primary successes"},
                                     {"key": "rate", "label": "Primary rate", "format": "percent"},
                                     {"key": "ciLow", "label": "95% low", "format": "percent"},
                                     {"key": "ciHigh", "label": "95% high", "format": "percent"}],
                         "rows": rows},
                        {"id": "barrier-outcomes", "title": "A/C barrier outcomes", "kind": "figure",
                         "path": "figures/barrier-outcomes.png",
                         "alt": "Two stacked bars: first outside-2-sigma fade above, first VWAP retest bounce below. Green is favorable first, coral adverse first, gray neither, purple ambiguous.",
                         "caption": "Top: A fade. Bottom: C bounce. Green favorable first; coral adverse first; gray neither; purple ordering ambiguous. Each bar uses its own evaluable-event denominator."},
                        {"id": "scope", "title": "Scope and limits", "kind": "text",
                         "body": "Seven correlated anchor/window views on ES, NQ, and GC at 2m and 5m. These are statistical price paths, not net trading profits. See the saved report and tables for denominators, uncertainty, baselines, and exclusions."}],
           "notes": ["95% intervals resample shared session dates; anchor and timeframe views are correlated.",
                     "Local publication source only; hosted publication requires separate authorization."]}
    (stage / "publication.json").write_text(json.dumps(pub, indent=2) + "\n")


