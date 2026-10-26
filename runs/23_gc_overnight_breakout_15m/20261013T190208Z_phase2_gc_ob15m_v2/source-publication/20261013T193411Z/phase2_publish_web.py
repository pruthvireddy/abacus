"""Prepare explicit Phase 2 web projections from saved CSV/JSON evidence.

This module uses only the standard library. It does not import a research engine,
another publication producer, or calculate statistics. Planning and input checks
are read-only. Actual report generation waits for frozen saved-table schemas.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import hashlib
from html import escape
import io
import json
import math
from pathlib import Path
import textwrap
import subprocess
import sys
from typing import Any

STUDY = "23_gc_overnight_breakout_15m"
VERSION = "study23.phase2-publication/v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = "gc-overnight-breakout-15m-phase2-20261013-v1"
TABLE_INPUTS = (
    "trade-cohorts", "paired", "timing", "equity", "occurrence",
    "recovery", "level-opportunities", "transitions", "event-distribution", "interval-sensitivities",
    "scenarios", "ordering-bounds", "account", "account-capacity",
    "trades", "selected-example-bars",
)
POLICIES = {
    "q0": "reclaim-q000", "q25": "reclaim-q025",
    "q50": "reclaim-q050", "q75": "reclaim-q075",
    "limit25": "passive-q025", "limit50": "passive-q050", "limit75": "passive-q075",
    "protected_touch_hold": "protected-touch-hold",
    "protected_failed_break_reclaim": "protected-failed-break-reclaim",
    "protected_reversal": "protected-reversal",
}
TEXT_COLUMNS = {
    "policy", "year", "session", "side", "family", "anchor", "dimension",
    "broker_day", "trade_id", "status", "exit_reason", "contract",
    "entry_time", "exit_time", "entry_ny", "scenario", "horizon", "event",
    "level", "recovery_type", "transition", "from_session", "to_session",
    "mode", "day_coverage_start", "day_coverage_end", "entry_coverage_start",
    "entry_coverage_end", "period", "episode_id", "timestamp", "exit_ny",
    "baseline_comparison", "population", "first_1r_reference",
}
BOOLEAN_COLUMNS = {"partial_year", "not_realized_trade_return", "unknown_branch"}
INTEGER_COLUMNS = {
    "accepted_breakouts", "executable_fills", "completed", "censored",
    "ambiguous", "wins", "losses", "breakevens", "r_denominator", "invalid_r",
    "source_style_r_denominator", "stop_exits", "timed_exits",
    "max_losing_streak", "distinct_broker_days", "eligible_days", "valid_ranges",
    "no_trade_days", "unknown_days", "exclusions", "quantity_skips", "entry_year",
    "episodes", "complete_pairs", "missing_pairs", "no_fill", "opportunities",
    "armed", "signals", "fills", "unknown", "individual_pairs", "improved",
    "deteriorated", "equal", "missed_winners", "avoided_losses", "known_events",
    "known_none", "known_denominator", "repeat_contacts", "count",
    "eligible_loss", "original_fills", "second_fills", "completed_pairs",
    "full_recovery", "partial_recovery", "no_improvement", "further_loss",
    "opportunity_unknown", "elapsed_denominator", "repeat_known_episodes",
    "total_known_events", "unknown_time", "paired_count", "block_weeks",
    "range_recovery_successes", "range_recovery_known_denominator", "range_recovery_unknown",
    "first_1r_success_successes", "first_1r_success_known_denominator", "first_1r_success_unknown",
    "mfe_after_touch_points_denominator", "mae_after_touch_points_denominator",
    "deepest_range_fraction_denominator", "event_risk_points_denominator",
    "eligible_signals", "unknown_original_fills", "unknown_second_fills",
    "completed_financial_recovery_pairs", "net_known_episodes",
    "eligible_loss_unknown_outcome", "unknown_eligible_loss", "original_episodes",
    "known_breach_episodes", "known_no_breach_episodes", "unknown_breach_episodes",
}
PERCENT_COLUMNS = {
    "win_rate", "win_rate_low", "win_rate_high", "entry_share", "rate",
    "lower_bound", "upper_bound", "recovery_rate", "missing_pair_rate",
    "missing_rate", "participation_rate", "signal_rate", "adjusted_confidence", "share",
    "fraction", "mean_deepest_range_fraction", "range_recovery_rate", "first_1r_success_rate",
}


@dataclass(frozen=True)
class ReportSpec:
    group: str
    view: str
    title: str
    policy_keys: tuple[str, ...] = ()

    @property
    def publication_id(self) -> str:
        result = f"{PREFIX}-{self.group}-{self.view}"
        if len(result) > 80:
            raise ValueError("Planned publication ID exceeds Narada's bound")
        return result


def report_specs() -> tuple[ReportSpec, ...]:
    result = [
        ReportSpec("comparison", "summary", "Phase 2 comparison — Summary"),
        ReportSpec("comparison", "year", "Phase 2 comparison — Year-wise"),
        ReportSpec("comparison", "entry", "Phase 2 comparison — Entry sessions"),
        ReportSpec("comparison", "account-risk", "Source account and two-leg risk"),
    ]
    for group, title, key in (
        ("boundary-reclaim", "Boundary reclaim", "q0"),
        ("quarter-reclaim", "25% reclaim", "q25"),
        ("midpoint-reclaim", "Midpoint reclaim", "q50"),
        ("threequarter-reclaim", "75% reclaim", "q75"),
    ):
        for view, label in (("summary", "Summary"), ("year", "Year-wise"), ("entry", "Entry sessions")):
            result.append(ReportSpec(group, view, f"{title} — {label}", (key,)))
    for view, label in (("summary", "Summary"), ("year", "Year-wise"), ("entry", "Entry sessions")):
        result.append(ReportSpec("passive-limits", view, f"Passive limits — {label}", ("limit25", "limit50", "limit75")))
    for view, label in (("occurrence", "Occurrence"), ("trades", "Recovery and reversal trades"), ("year", "Year-wise"), ("events", "Event sessions")):
        result.append(ReportSpec("protected", view, f"Protected overnight boundary — {label}", ("protected_touch_hold", "protected_failed_break_reclaim", "protected_reversal")))
    if len(result) != 23 or len({item.publication_id for item in result}) != 23:
        raise ValueError("Invalid authored report plan")
    return tuple(result)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def safe_relative(value: str) -> Path:
    if not isinstance(value, str) or not value or any(character in value for character in "\\:#?"):
        raise ValueError("Invalid relative artifact path")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Artifact path must not escape its root")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("Artifact path contains control characters")
    return path


def read_regular(root: Path, artifact: str) -> bytes:
    relative = safe_relative(artifact)
    current = root
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Evidence root must be a real directory")
    for index, part in enumerate(relative.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError("Saved evidence symlinks are not allowed")
        if index < len(relative.parts) - 1 and not current.is_dir():
            raise ValueError("Saved evidence ancestor is not a directory")
    if not current.is_file():
        raise ValueError(f"Missing saved regular artifact: {artifact}")
    return current.read_bytes()


def saved_cell(column: str, raw: str) -> Any:
    if raw == "":
        return None
    if column in TEXT_COLUMNS:
        return raw
    if column in BOOLEAN_COLUMNS or column == "ambiguous" and raw in {"true", "false", "True", "False"}:
        if raw not in {"true", "false", "True", "False"}:
            raise ValueError(f"Invalid saved boolean: {column}")
        return raw.lower() == "true"
    if column == "bucket" and not raw.isdecimal():
        return raw
    if column in INTEGER_COLUMNS or column == "bucket":
        try:
            number = Decimal(raw)
        except InvalidOperation as error:
            raise ValueError(f"Invalid saved integer: {column}") from error
        if not number.is_finite() or number != number.to_integral_value() or abs(number) > 9007199254740991:
            raise ValueError(f"Invalid saved integer: {column}")
        return int(number)
    number = float(raw)
    if not math.isfinite(number):
        raise ValueError(f"Nonfinite saved number: {column}")
    return number


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Nonfinite saved scalar")
        return "number"
    if isinstance(value, str):
        return "string"
    raise ValueError("Only saved scalar cells may be displayed")


def csv_bytes(columns: list[str], rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row[key] for key in columns} for row in rows)
    return buffer.getvalue().encode("utf-8")


def json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with /")
    for part in pointer[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def svg_text(x: float, y: float, text: str, size: int = 22, *, color: str = "#24322d", anchor: str = "start") -> str:
    return f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(text)}</text>'


def wrapped_svg(x: float, y: float, text: str, width: int = 32, size: int = 21) -> str:
    return "".join(svg_text(x, y + index * (size + 6), line, size) for index, line in enumerate(textwrap.wrap(text, width)))


def svg_start(width: int, height: int, title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Arial, sans-serif">',
        f"<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>",
        '<rect width="100%" height="100%" fill="#fbfcf8"/>',
        svg_text(40, 55, title, 31),
        wrapped_svg(40, 94, subtitle, width=96, size=21),
    ]


def flow_box(svg: list[str], x: int, y: int, width: int, height: int, title: str, body: str, *, color: str = "#6952a3") -> None:
    svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="9" fill="#f4f0fa" stroke="{color}" stroke-width="2"/>')
    svg.append(wrapped_svg(x + 18, y + 31, title, max(12, (width - 36) // 13), 24))
    title_lines = len(textwrap.wrap(title, max(12, (width - 36) // 13)))
    svg.append(wrapped_svg(x + 18, y + 43 + title_lines * 30, body, max(14, (width - 36) // 11), 21))


def flow_arrow(svg: list[str], x1: int, y: int, x2: int) -> None:
    svg.append(f'<path d="M{x1},{y} H{x2 - 10}" fill="none" stroke="#5d7169" stroke-width="3"/>')
    svg.append(f'<path d="M{x2 - 12},{y - 6} L{x2},{y} L{x2 - 12},{y + 6}" fill="none" stroke="#5d7169" stroke-width="3"/>')


def illustrative_svg(kind: str, q: float | None = None) -> bytes:
    """Authored process diagrams; coordinates are not observed prices or outcomes."""
    if kind == "reclaim":
        if q not in {0, .25, .5, .75}:
            raise ValueError("Only frozen reclaim fractions are illustrated")
        title = {0: "Boundary reclaim", .25: "25% reclaim", .5: "Midpoint reclaim", .75: "75% reclaim"}[q]
        svg = svg_start(1240, 1230, f"Illustrative rule — {title}", "Frozen range H / M / L; direction available at original breakout-candle close b. This is a process guide, not an observed price sample.")
        for direction, top in (("Long / upper-first", 185), ("Short / lower-first", 700)):
            long = direction.startswith("Long")
            level = "H − qW" if long else "L + qW"
            inward = ("strictly below H" if long else "strictly above L") if q == 0 else (f"at or below {level}" if long else f"at or above {level}")
            outward = f"strictly {'above' if long else 'below'} {level}"
            svg.append(svg_text(40, top - 25, direction, 27, color="#246b61" if long else "#a83d4d"))
            steps = [
                ("Observe b close", "Direction becomes actionable. Observe the breakout without taking its original fill; no alternative fill on b."),
                ("Arm at later j close", f"First complete j > b closes {inward}. Preserve an uncertain prefix as unknown."),
                ("Separate reclaim k", f"First separate k > j closes {outward}. Submit a market order at that close."),
                ("Next eligible open", "Use actual next opening and retain gaps. Missing expected price is unknown; never fill at cutoff."),
            ]
            for index, (heading, body) in enumerate(steps):
                x = 40 + index * 303
                flow_box(svg, x, top, 275, 250, heading, body)
                if index < 3:
                    flow_arrow(svg, x + 275, top + 120, x + 303)
            flow_box(svg, 40, top + 275, 560, 180, "Initial stop: signal close", "The frozen percentage stop is based on the reclaim signal close and tick-rounded. It already protects the entry-candle path.")
            flow_box(svg, 650, top + 275, 550, 180, "Reset only after survival", "At a surviving entry-candle close, reset once from actual slipped fill. A same-candle stop stays final; no target or trailing stop.")
        svg.append(svg_text(40, 1204, "An opposite-boundary contact does not cancel this waiting percentage-stop policy. H10 and new filters are uncomputed.", 19))
    elif kind == "passive":
        svg = svg_start(1240, 1220, "Illustrative rule — passive interior limits", "Passive limits and confirmed reclaims answer different execution questions. No hindsight order or pooling of their outcomes.")
        for direction, top in (("Long / upper-first", 185), ("Short / lower-first", 695)):
            long = direction.startswith("Long")
            svg.append(svg_text(40, top - 25, direction, 27, color="#246b61" if long else "#a83d4d"))
            steps = [
                ("Confirm b close", "Freeze the raw quarter, midpoint or three-quarter level. Activate only after the complete original breakout candle."),
                ("Check known history", "Skip a level reached in the known post-original-fill path before submission. An ambiguous prefix stays unknown."),
                ("Submit executable limit", f"Round conservatively inward: {'floor a buy' if long else 'ceil a sell'} to the tick. The raw theoretical level remains recorded."),
                ("Opening / intrabar fill", "Retain favorable opening gaps. Intrabar fills require one tick of trade-through; touch-only is a separate sensitivity."),
            ]
            for index, (heading, body) in enumerate(steps):
                x = 40 + index * 303
                flow_box(svg, x, top, 275, 250, heading, body)
                if index < 3:
                    flow_arrow(svg, x + 275, top + 120, x + 303)
            flow_box(svg, 40, top + 275, 560, 180, "Initial stop: submitted limit", "Attach the frozen percentage stop from the executable limit. Preserve an opening gap through its stop and resulting protective exit.")
            flow_box(svg, 650, top + 275, 550, 180, "Survival, reset and cutoff", "Only a surviving entry candle resets from actual slipped fill. Expire unfilled orders at cutoff and use the inherited timed exit.")
        svg.append(svg_text(40, 1193, "Illustrative order-state timeline only; it does not assert a tick-exact price path, observed fill or financial return.", 20))
    elif kind == "protected":
        svg = svg_start(1240, 1180, "Illustrative rules — protected overnight boundary", "Protected low L follows upper-first; protected high H mirrors lower-first. Observe after actual original fill, including after its exit.")
        for direction, boundary, top in (("Upper-first / protected low L", "L", 200), ("Lower-first / protected high H", "H", 675)):
            upper = boundary == "L"
            inside, beyond = ("above L", "below L") if upper else ("below H", "above H")
            continuation, reversal = ("Buy", "Sell") if upper else ("Sell", "Buy")
            svg.append(svg_text(40, top - 25, direction, 27))
            steps = [
                ("Touch and hold", f"A later candle touches {boundary} and closes {inside}. No one-tick breach since original fill through this close. {continuation} next eligible open."),
                ("Failed break / reclaim", f"First later one-tick breach arms at j close. A separate k > j closes {inside}. {continuation} next eligible open."),
                ("Opposite reversal", f"First later complete candle closes strictly {beyond}. {reversal} next eligible open, opposite the original direction."),
            ]
            for index, (heading, body) in enumerate(steps):
                flow_box(svg, 40 + index * 402, top, 370, 270, heading, body)
            flow_box(svg, 40, top + 295, 1160, 135, "Shared execution and separate occurrence evidence", "First setup only, later candles than b, initial signal-close stop and surviving-fill reset. Descriptive touch / breach / close-break / reclaim rates use two separate horizons and retain unknown exposure.")
        svg.append(svg_text(40, 1154, "The overnight boundary is neither a swing point nor necessarily the baseline's active stop. All three policies are exploratory.", 19))
    elif kind == "financial":
        svg = svg_start(1240, 1170, "Illustrative distinction — price and financial recovery", "A return to a range level is a path diagnostic. Financial recovery requires genuinely executed legs and both legs' costs.")
        svg.append(svg_text(40, 184, "Price recovery after a protected breach", 27))
        flow_box(svg, 40, 215, 560, 190, "Touches and later close reclaims", "Track breached boundary → midpoint → original boundary. Keep unknown order, gaps, cutoff and actual event sessions.")
        flow_box(svg, 650, 215, 550, 190, "No automatic trade success", "A level reached before entry is not an executed target. Price recovery does not establish positive net P&L.")
        svg.append(svg_text(40, 474, "Executed financial recovery after a realized loss", 27))
        steps = [
            ("Loss known at signal", "Original leg is flat; its net loss is realized and known. Skip an ineligible first signal without a later attempt."),
            ("Feasible whole GC", "Split the daily budget before entry. Apply risk, leverage, margin, costs and whole-contract limits; no replenishment."),
            ("Actual later leg", "Require a genuine eligible fill. Opposite signals while the original is open are not an automatic hedge or reversal."),
        ]
        for index, (heading, body) in enumerate(steps):
            x = 40 + index * 402
            flow_box(svg, x, 510, 370, 270, heading, body)
            if index < 2:
                flow_arrow(svg, x + 370, 645, x + 402)
        flow_box(svg, 40, 835, 1160, 205, "Saved combined net outcome after both costs", "Full recovery: combined net P&L is nonnegative. Partial improvement remains negative but improves the original realized loss; no improvement and further loss stay distinct. If quantity is infeasible, show skips, no actual fills and unavailable recovery rates.")
        svg.append(svg_text(40, 1125, "Illustrative eligibility/accounting logic only. Standardized replacement profits are not source-account returns.", 20))
    else:
        raise ValueError("Unknown authored guide kind")
    svg.append("</svg>")
    return "\n".join(svg).encode("utf-8")


def saved_bars_svg(draft: "PublicationDraft", artifact: str, source_rows: list[int], label_columns: list[str], value_column: str, title: str, subtitle: str, *, unit: str, precision: int = 1, format_kind: str = "number") -> tuple[bytes, dict[str, Any]]:
    """Render saved scalar values; only coordinates/axis extents are derived."""
    raw = draft.copied_table(artifact)
    if format_kind not in {"number", "percent"}:
        raise ValueError("Chart format must be explicit")
    if not source_rows or any(index < 0 or index >= len(raw) for index in source_rows):
        raise ValueError("A saved chart needs explicit copied source rows")
    plotted = []
    for index in source_rows:
        values = {key: saved_cell(key, raw[index][key]) for key in [*label_columns, value_column]}
        value = values[value_column]
        if value is not None and value_type(value) != "number":
            raise ValueError("Bar values must be saved numbers or null")
        plotted.append({"source_row": index, "original_source_row": draft.sources[artifact]["selected_source_rows"][index], "values": values})
    numeric = [item["values"][value_column] for item in plotted if item["values"][value_column] is not None]
    low, high = min([0, *numeric]), max([0, *numeric])
    if low == high:
        low, high = -1, 1
    span = high - low
    low, high = low - span * .1, high + span * .15
    top, bottom, left, right = 165, 620, 95, 1185
    def y(value):
        return bottom - (value - low) * (bottom - top) / (high - low)
    step = (right - left) / len(plotted)
    centers = [left + step * (index + .5) for index in range(len(plotted))]
    width = min(65, step * .68)
    svg = svg_start(1240, 820, title, subtitle)
    zero = y(0)
    svg.append(f'<path d="M{left},{zero:.6f} H{right}" fill="none" stroke="#849189" stroke-width="2"/>')
    svg.append(svg_text(18, 153, unit, 19))
    for position, item in enumerate(plotted):
        values = item["values"]
        value = values[value_column]
        x = centers[position]
        label = " / ".join(str(values[key]) for key in label_columns)
        if value is None:
            svg.append(svg_text(x, zero - 15, "Not available", 16, anchor="middle"))
        else:
            end = y(value)
            svg.append(f'<rect data-source-row="{item["source_row"]}" x="{x - width / 2:.6f}" y="{min(zero, end):.6f}" width="{width:.6f}" height="{abs(end - zero):.6f}" fill="{"#246b61" if value >= 0 else "#aa6040"}"/>')
            label_value = f"{value * 100:,.{precision}f}%" if format_kind == "percent" else f"{value:,.{precision}f}"
            svg.append(svg_text(x, min(zero, end) - 12, label_value, 18, anchor="middle"))
        for line_index, line in enumerate(textwrap.wrap(label, 18)):
            svg.append(svg_text(x, bottom + 35 + line_index*21, line, 15, anchor="middle"))
    svg.append(wrapped_svg(40, 754, "Values are copied from saved evidence. An unavailable value is not plotted as zero; source counts and uncertainty remain in the accompanying tables.", 98, 19))
    svg.append("</svg>")
    encoding = {
        "kind": "bars-v1", "canvas": [1240, 820],
        "source_columns": [*label_columns, value_column],
        "value_column": value_column, "label_columns": label_columns,
        "label_precision": precision, "label_format": format_kind, "unit": unit,
        "plot_box": {"left": left, "right": right, "top": top, "bottom": bottom},
        "x_centers": centers, "bar_width": width,
        "y_domain": [low, high], "y_range": [bottom, top],
        "coordinate_precision": 6, "null_encoding": "text only; no rectangle",
    }
    return "\n".join(svg).encode("utf-8"), {
        "kind": "saved-values", "source_artifact": artifact,
        "source_sha256": draft.sources[artifact]["sha256"],
        "plotted_values": plotted, "plot_encoding": encoding,
    }


class SavedInputs:
    """Read explicit source artifacts and preserve raw CSV strings/row order."""

    def __init__(self, stage: Path):
        self.stage = Path(stage)
        self.bytes: dict[str, bytes] = {}
        self.tables: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    def read(self, artifact: str) -> bytes:
        if artifact not in self.bytes:
            self.bytes[artifact] = read_regular(self.stage, artifact)
        return self.bytes[artifact]

    def table(self, artifact: str) -> tuple[list[str], list[dict[str, str]]]:
        if artifact not in self.tables:
            reader = csv.DictReader(io.StringIO(self.read(artifact).decode("utf-8"), newline=""), strict=True)
            columns = reader.fieldnames or []
            if not columns or len(columns) != len(set(columns)):
                raise ValueError("Saved CSV needs distinct declared columns")
            rows = list(reader)
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                raise ValueError("Saved CSV row width differs from its header")
            self.tables[artifact] = (columns, rows)
        return self.tables[artifact]

    def select(self, artifact: str, where: dict[str, str | tuple[str, ...]] | None = None) -> list[int]:
        columns, rows = self.table(artifact)
        selectors = where or {}
        if any(key not in columns for key in selectors):
            raise ValueError("Selector must use an original saved column")
        return [
            index for index, row in enumerate(rows)
            if all(row[key] in expected if isinstance(expected, tuple) else row[key] == expected for key, expected in selectors.items())
        ]

    def json(self, artifact: str) -> Any:
        def invalid_constant(value: str):
            raise ValueError(f"Nonfinite saved JSON constant: {value}")
        return json.loads(self.read(artifact), parse_constant=invalid_constant)


class PublicationDraft:
    """A private in-memory projection. No file is written by this class."""

    def __init__(self, inputs: SavedInputs, run_id: str, spec: ReportSpec):
        self.inputs, self.run_id, self.spec = inputs, run_id, spec
        self.files: dict[str, bytes] = {}
        self.sources: dict[str, dict[str, Any]] = {}
        self.bindings: list[dict[str, Any]] = []
        self.claims: list[dict[str, Any]] = []
        self.figures: list[dict[str, Any]] = []
        self.downloads: list[dict[str, Any]] = []
        self.download_entries: list[dict[str, Any]] = []

    def copy_table(self, original: str, target: str, where: dict[str, str | tuple[str, ...]] | None = None, columns: list[str] | None = None) -> str:
        safe_relative(target)
        original_columns, rows = self.inputs.table(original)
        selected_columns = columns or original_columns
        if not selected_columns or len(selected_columns) != len(set(selected_columns)) or any(key not in original_columns for key in selected_columns):
            raise ValueError("Copied source columns must be exact distinct saved keys")
        selected_rows = self.inputs.select(original, where)
        data = csv_bytes(selected_columns, [rows[index] for index in selected_rows])
        if target in self.files:
            raise ValueError("Copied source path already selected")
        self.files[target] = data
        self.sources[target] = {
            "path": target, "sha256": sha_bytes(data), "kind": "csv",
            "original_stage_source_path": original,
            "original_source_sha256": sha_bytes(self.inputs.read(original)),
            "source_row_base": 0, "selected_source_rows": selected_rows,
            "columns": selected_columns,
            "selectors": {key: list(value) if isinstance(value, tuple) else value for key, value in (where or {}).items()},
        }
        return target

    def copy_json(self, original: str, target: str | None = None) -> str:
        target = target or original
        safe_relative(target)
        data = self.inputs.read(original)
        self.inputs.json(original)
        if target in self.files:
            raise ValueError("Copied JSON source path already selected")
        self.files[target] = data
        self.sources[target] = {
            "path": target, "sha256": sha_bytes(data), "kind": "json",
            "original_stage_source_path": original,
            "original_source_sha256": sha_bytes(data),
        }
        return target

    def copy_text(self, original: str, target: str | None = None) -> str:
        target = target or original
        safe_relative(target)
        data = self.inputs.read(original)
        data.decode("utf-8")
        if target in self.files:
            raise ValueError("Copied text source path already selected")
        self.files[target] = data
        self.sources[target] = {
            "path": target, "sha256": sha_bytes(data), "kind": "text",
            "original_stage_source_path": original,
            "original_source_sha256": sha_bytes(data),
        }
        return target

    def copied_table(self, artifact: str) -> list[dict[str, str]]:
        source = self.sources[artifact]
        if source["kind"] != "csv":
            raise ValueError("Expected a copied saved table")
        return list(csv.DictReader(io.StringIO(self.files[artifact].decode("utf-8"), newline="")))

    def table(self, section: str, title: str, artifact: str, columns: list[dict[str, Any]], filters: list[dict[str, Any]] | None = None, description: str = "", notes: list[str] | None = None) -> dict[str, Any]:
        keys = [column["key"] for column in columns]
        if len(keys) > 12 or len(keys) != len(set(keys)):
            raise ValueError("Display table needs at most twelve distinct columns")
        source = self.sources[artifact]
        if any(key not in source["columns"] for key in keys):
            raise ValueError("Display columns must name copied saved cells")
        raw_rows = self.copied_table(artifact)
        filters = filters or []
        if len(filters) > 3 or len({item["key"] for item in filters}) != len(filters):
            raise ValueError("At most three distinct saved-row filters")
        if len(raw_rows) > (1500 if filters else 100):
            raise ValueError("Saved table exceeds its conditional row bound")
        rows = [{key: saved_cell(key, row[key]) for key in keys} for row in raw_rows]
        for selector in filters:
            if selector["key"] not in keys:
                raise ValueError("Filter must name a displayed saved column")
            if "defaultValue" in selector and not any(row[selector["key"]] == selector["defaultValue"] for row in rows):
                raise ValueError("Filter default must name an exact saved value")
        for row_index, row in enumerate(rows):
            for key, value in row.items():
                self.bindings.append({
                    "section": section, "row_index": row_index, "key": key,
                    "source_artifact": artifact, "source_row": row_index,
                    "source_column": key, "value_type": value_type(value),
                    "original_stage_source_path": source["original_stage_source_path"],
                    "original_source_row": source["selected_source_rows"][row_index],
                    "original_source_column": key,
                })
        result = {"id": section, "kind": "table", "title": title, "columns": columns, "rows": rows}
        if filters:
            result["rowFilters"] = filters
        if description:
            result["description"] = description
        if notes:
            result["notes"] = notes
        return result

    def json_metric(self, section: str, metric_index: int, artifact: str, pointer: str, label: str, **presentation: Any) -> dict[str, Any]:
        value = json_pointer(json.loads(self.files[artifact]), pointer)
        self.bindings.append({
            "section": section, "metric_index": metric_index,
            "source_artifact": artifact, "source_pointer": pointer,
            "value_type": value_type(value),
            "original_stage_source_path": self.sources[artifact]["original_stage_source_path"],
            "original_source_pointer": pointer,
        })
        return {"label": label, "value": value, **presentation}

    def json_table(self, section: str, title: str, artifact: str, pointers: list[dict[str, str]], columns: list[dict[str, Any]]) -> dict[str, Any]:
        document = json.loads(self.files[artifact])
        rows = []
        for row_index, record in enumerate(pointers):
            row = {}
            for column in columns:
                key, pointer = column["key"], record[column["key"]]
                value = json_pointer(document, pointer)
                row[key] = value
                self.bindings.append({
                    "section": section, "row_index": row_index, "key": key,
                    "source_artifact": artifact, "source_pointer": pointer,
                    "value_type": value_type(value),
                    "original_stage_source_path": self.sources[artifact]["original_stage_source_path"],
                    "original_source_pointer": pointer,
                })
            rows.append(row)
        if len(columns) > 12 or len(rows) > 100:
            raise ValueError("JSON table exceeds ordinary table bounds")
        return {"id": section, "kind": "table", "title": title, "columns": columns, "rows": rows}

    def download(self, download_id: str, label: str, artifact: str, columns: list[str], *, population: str, units: str, scope: str) -> dict[str, Any]:
        source = self.sources[artifact]
        rows = self.copied_table(artifact)
        if len(self.downloads) >= 4 or not 1 <= len(columns) <= 24 or len(columns) != len(set(columns)):
            raise ValueError("Selected download exceeds file/column bounds")
        if not 1 <= len(rows) <= 15000 or any(key not in source["columns"] for key in columns):
            raise ValueError("Selected download needs exact saved rows/columns")
        data = csv_bytes(columns, rows)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError("Selected download exceeds filtered per-file bound")
        path = f"downloads/{download_id}.csv"
        safe_relative(path)
        if path in self.files:
            raise ValueError("Download path already selected")
        self.files[path] = data
        digest = sha_bytes(data)
        self.downloads.append({
            "id": download_id, "path": path, "source_artifact": artifact,
            "source_rows": list(range(len(rows))), "columns": columns,
            "source_sha256": source["sha256"], "sha256": digest,
            "original_stage_source_path": source["original_stage_source_path"],
            "original_source_sha256": source["original_source_sha256"],
            "original_source_rows": source["selected_source_rows"],
        })
        result = {
            "id": download_id, "path": path, "label": label,
            "description": "Exact selected saved CSV cells; no statistics recalculated.",
            "population": population, "units": units, "scope": scope,
            "mediaType": "text/csv", "sha256": digest, "rowCount": len(rows),
            "columns": columns,
            "source": {"runId": self.run_id, "artifact": artifact, "sha256": source["sha256"]},
        }
        self.download_entries.append(result)
        return result

    def figure(self, section: str, title: str, stem: str, svg: bytes, provenance: dict[str, Any], *, alt: str, caption: str) -> dict[str, Any]:
        svg_path, path = f"figures/{stem}.svg", f"figures/{stem}.png"
        safe_relative(svg_path)
        if svg_path in self.files:
            raise ValueError("Figure path already selected")
        artifact = provenance["source_artifact"]
        if artifact not in self.sources or provenance["source_sha256"] != self.sources[artifact]["sha256"]:
            raise ValueError("Figure requires an exact copied source hash")
        self.files[svg_path] = svg
        self.figures.append({
            **provenance, "section": section, "path": path,
            "svg_path": svg_path, "svg_sha256": sha_bytes(svg),
        })
        return {"id": section, "kind": "figure", "title": title, "path": path, "alt": alt, "caption": caption}

    def complete_png(self, path: str, data: bytes) -> None:
        record = next((item for item in self.figures if item["path"] == path), None)
        if record is None or not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 2 * 1024 * 1024:
            raise ValueError("Expected a declared bounded rendered PNG")
        if path in self.files:
            raise ValueError("Rendered PNG already recorded")
        total = sum(len(self.files[item["path"]]) for item in self.figures if item["path"] in self.files)
        if total + len(data) > 8 * 1024 * 1024:
            raise ValueError("Report exceeds its total raster bound")
        self.files[path] = data
        record["image_sha256"] = sha_bytes(data)

    def source_map(self) -> dict[str, Any]:
        if any("image_sha256" not in figure for figure in self.figures):
            raise ValueError("Source map cannot precede complete rendered image hashes")
        return {
            "schema_version": "study23.phase2-web-source-cells/v1",
            "run_id": self.run_id, "publication_id": self.spec.publication_id,
            "source_row_base": 0, "source_artifacts": list(self.sources.values()),
            "bindings": self.bindings, "claims": self.claims,
            "figures": self.figures, "downloads": self.downloads,
            "qualification": "Source-cell projection only; independent original-to-copy and copy-to-display verification remains separate.",
        }


LABELS = {
    "year": "Year", "session": "Session", "side": "Side", "policy": "Policy",
    "executable_fills": "Actual candidate fills", "accepted_breakouts": "Accepted fills",
    "completed": "Completed", "censored": "Censored", "unknown": "Unknown outcomes",
    "net_dollars": "Net P&L", "gross_dollars": "Raw-price gross on this path",
    "gross_points": "Gross points", "net_points": "Net points",
    "cost_dollars": "Costs", "mean_net_dollars": "Mean net P&L",
    "expectancy_r": "Mean net initial-risk R", "net_r": "Net initial-risk R",
    "r_denominator": "Valid initial-risk trades", "mean_dollars_low": "Mean P&L 95% lower",
    "mean_dollars_high": "Mean P&L 95% upper", "expectancy_r_low": "Mean R 95% lower",
    "expectancy_r_high": "Mean R 95% upper", "win_rate": "Net win rate",
    "win_rate_low": "Win rate 95% lower", "win_rate_high": "Win rate 95% upper",
    "max_drawdown_dollars": "Closed-P&L drawdown", "holding_minutes": "Mean hold",
    "episodes": "Original episodes", "complete_pairs": "Common complete pairs",
    "missing_pairs": "Missing pairs", "mean_difference": "Paired mean improvement",
    "difference_low": "Paired 95% lower", "difference_high": "Paired 95% upper",
    "adjusted_low": "Within-cohort adjusted lower", "adjusted_high": "Within-cohort adjusted upper",
    "adjusted_confidence": "Marginal confidence", "baseline_net_dollars": "Paired baseline net",
    "alternative_net_dollars": "Paired alternative net", "mean_entry_delay": "Mean entry delay",
    "mean_price_improvement": "Mean entry price improvement", "no_fill": "Known no fill",
    "missed_winners": "Missed baseline winners", "avoided_losses": "Avoided baseline losses",
    "individual_pairs": "Individual-mask pairs", "individual_mean_difference": "Individual-mask mean",
    "opportunities": "Known opportunities", "opportunity_unknown": "Unknown opportunities",
    "known_events": "Known events", "known_none": "Known absence",
    "known_denominator": "Known denominator", "rate": "Known-event rate",
    "lower_bound": "All-episode rate lower bound", "upper_bound": "All-episode rate upper bound",
    "mean_elapsed_minutes": "Mean event elapsed", "mean_exposure_minutes": "Mean scheduled exposure",
    "mean_observed_exposure_minutes": "Mean observed exposure", "repeat_contacts": "Repeat contacts",
    "original_fills": "Observed original fills", "second_fills": "Observed second fills",
    "signals": "Known signals", "eligible_signals": "Known eligible signals",
    "unknown_original_fills": "Unknown original fills", "unknown_second_fills": "Unknown second fills",
    "quantity_skips": "Known quantity skips", "net_known_episodes": "Known net episodes",
    "net_completed_known_dollars": "Known completed net only", "known_closed_net_dollars": "Known closed net only",
    "eligible_loss": "Known eligible realized losses", "unknown_eligible_loss": "Unknown loss eligibility",
    "eligible_loss_unknown_outcome": "Eligible losses with unknown recovery",
    "recovery_rate": "Full recovery / known completed recovery",
    "full_recovery_per_eligible_loss": "Full recovery / known eligible loss",
    "recovery_dollars": "Saved financial recovery P&L", "loss_recovered_dollars": "Saved loss recovered",
    "range_recovery_rate": "First-touch path range recovery",
    "first_1r_success_rate": "First-touch diagnostic 1R success",
    "mean_mfe_after_touch_points": "Observed-path mean MFE after first touch",
    "mean_mae_after_touch_points": "Observed-path mean MAE after first touch",
    "mean_deepest_range_fraction": "Observed-path mean range depth",
    "mean_event_risk_points": "Mean diagnostic risk distance",
    "entry_share": "Saved entry share", "partial_year": "Partial year",
    "validation_episodes": "Validation episodes", "common_complete_pairs": "Common validation pairs",
    "completed_fills": "Completed validation fills", "validation_mean_difference": "Validation paired mean",
    "qualifies": "Qualified", "full_quantity": "Full-budget whole quantity",
    "half_quantity": "Half-budget whole quantity",
}


def columns(keys: list[str]) -> list[dict[str, Any]]:
    result = []
    for key in keys:
        column = {"key": key, "label": LABELS.get(key, key.replace("_", " ").capitalize())}
        if key not in TEXT_COLUMNS and key not in BOOLEAN_COLUMNS and key not in {
            "qualifies", "bucket", "full_skip_reason", "half_skip_reason", "static_initial_capital_capacity_audit"
        }:
            column.update(format="percent" if key in PERCENT_COLUMNS else "number", precision=0 if key in INTEGER_COLUMNS else 2)
            if "dollars" in key or key in {"mean_difference", "difference_low", "difference_high", "adjusted_low", "adjusted_high", "lower", "upper", "adjusted_lower", "adjusted_upper", "validation_mean_difference"}:
                column["unit"] = "USD"
            elif "minutes" in key or key == "mean_entry_delay":
                column["unit"] = "minutes"
            elif "points" in key or key == "mean_price_improvement":
                column["unit"] = "GC points"
            elif key in {"net_r", "expectancy_r", "expectancy_r_low", "expectancy_r_high"}:
                column["unit"] = "initial-risk R"
        result.append(column)
    return result


def cohort_filters(view: str, *, side: str = "combined") -> list[dict[str, Any]]:
    result = [{"key": "year", "label": "Year"}, {"key": "session", "label": "Session"}, {"key": "side", "label": "Side", "defaultValue": side}]
    if view != "year":
        result[0]["defaultValue"] = "all"
    if view not in {"entry", "events"}:
        result[1]["defaultValue"] = "all"
    return result


def text_section(draft: PublicationDraft, section: str, title: str, body: str, *, sources: list[dict[str, Any]] | None = None, authored: bool = True) -> dict[str, Any]:
    draft.claims.append({
        "id": section, "target": {"section": section, "field": "body"}, "text": body,
        "authored": authored, "sources": sources or [{"source_artifact": "protocol.md"}],
    })
    return {"id": section, "kind": "text", "title": title, "body": body}


def json_source(draft: PublicationDraft, artifact: str, pointer: str) -> dict[str, Any]:
    value = json_pointer(json.loads(draft.files[artifact]), pointer)
    return {
        "source_artifact": artifact, "source_pointer": pointer, "value_type": value_type(value),
        "original_stage_source_path": draft.sources[artifact]["original_stage_source_path"],
        "original_source_pointer": pointer, "saved_value": value,
    }


def saved_line_svg(draft: PublicationDraft, artifact: str, value_column: str, title: str, subtitle: str) -> tuple[bytes, dict[str, Any]]:
    rows = draft.copied_table(artifact)
    values = [saved_cell(value_column, row[value_column]) for row in rows]
    if not rows or any(value is None for value in values):
        raise ValueError("Saved equity curve needs observed non-null values")
    low, high = min([0, *values]), max([0, *values])
    if low == high:
        low, high = -1, 1
    span = high - low
    low, high = low - span * .08, high + span * .12
    box = {"left": 100, "right": 1180, "top": 150, "bottom": 640}
    xs = [box["left"] + (box["right"] - box["left"]) * i / max(1, len(rows)-1) for i in range(len(rows))]
    ys = [box["bottom"] - (value-low) * (box["bottom"]-box["top"]) / (high-low) for value in values]
    svg = svg_start(1240, 820, title, subtitle)
    svg.append(f'<polyline data-series="{value_column}" points="{" ".join(f"{x:.6f},{y:.6f}" for x,y in zip(xs,ys))}" fill="none" stroke="#246b61" stroke-width="3"/>')
    for x, value, label in [(100, values[0], rows[0]["exit_time"]), (1180, values[-1], rows[-1]["exit_time"])]:
        svg.append(svg_text(x, 695, label[:10], 20, anchor="middle"))
        svg.append(svg_text(x, 730, f"{value:,.2f} USD", 20, anchor="middle"))
    svg.append(svg_text(30, 120, f"{high:,.0f} USD", 18))
    svg.append(svg_text(30, 656, f"{low:,.0f} USD", 18))
    svg.append(wrapped_svg(40, 775, "Saved closed-trade path in ledger order; no mark-to-market or account return. Points are not interpolated across missing observations.", 106, 18))
    svg.append("</svg>")
    plotted = [{"source_row": i, "original_source_row": draft.sources[artifact]["selected_source_rows"][i],
                "values": {key: saved_cell(key, row[key]) for key in ["trade_id", "exit_time", "policy", value_column]}} for i,row in enumerate(rows)]
    return "\n".join(svg).encode(), {
        "kind": "saved-values", "source_artifact": artifact, "source_sha256": draft.sources[artifact]["sha256"],
        "plotted_values": plotted, "plot_encoding": {
            "kind": "line-v1", "canvas": [1240,820], "value_column": value_column,
            "source_columns": ["trade_id","exit_time","policy",value_column],
            "plot_box": box, "x_positions": xs, "y_domain": [low,high], "y_range": [640,150],
            "coordinate_precision": 6, "x_order": "saved closed-trade row order",
        },
    }


def empirical_svg(draft: PublicationDraft, policy: str, outcomes: tuple[str, ...]) -> tuple[bytes, dict[str, Any]]:
    cases = json.loads(draft.files["example-selection.json"])
    selected = [(i,case) for i,case in enumerate(cases) if case["policy"] == policy and case["outcome"] in outcomes]
    if not selected or len(selected) > 4:
        raise ValueError("Expected bounded frozen earliest chronological examples")
    artifact = draft.copy_table("tables/selected-example-bars.csv", f"tables/examples-{policy}-{'candidate' if outcomes[0]=='win' else 'no-fill'}.csv",
                                {"policy": policy, "trade_id": tuple(case["trade"]["trade_id"] for _,case in selected)})
    rows = draft.copied_table(artifact)
    svg = svg_start(1240, 1400, f"{policy}: {'candidate fills' if outcomes[0]=='win' else 'known no-fill baseline outcomes'}",
                    "Saved earliest chronological cases; observed one-minute closes, actual fills and frozen stops")
    panels, plotted = [], []
    for panel_index, (case_index, case) in enumerate(selected):
        trade = case["trade"]
        indices = [i for i,row in enumerate(rows) if row["trade_id"] == trade["trade_id"]]
        if not indices:
            raise ValueError("Frozen example has no saved price bars")
        first = datetime.fromisoformat(rows[indices[0]]["timestamp"].replace("Z","+00:00")).timestamp()
        last = datetime.fromisoformat(rows[indices[-1]]["timestamp"].replace("Z","+00:00")).timestamp()
        left, top = 70 + (panel_index % 2)*610, 205 + (panel_index//2)*575
        box = {"left":left,"right":left+505,"top":top+90,"bottom":top+405}
        levels = ["range_high","range_low","midpoint"]
        numeric = [float(rows[i][key]) for i in indices for key in ["low","high"]] + [case[key] for key in levels]
        numeric += [trade[key] for key in ["entry_price","exit_price","initial_stop","reset_stop"] if trade.get(key) is not None]
        low, high = min(numeric),max(numeric)
        span = high-low or 1
        low,high = low-span*.08,high+span*.08
        def x(time):
            stamp = datetime.fromisoformat(time.replace("Z","+00:00")).timestamp()
            return box["left"]+(stamp-first)*(box["right"]-box["left"])/max(1,last-first)
        def y(value):
            return box["bottom"]-(value-low)*(box["bottom"]-box["top"])/(high-low)
        svg.append(svg_text(left,top,f'{case["side"]} — {case["outcome"].replace("_"," ")}',22))
        svg.append(svg_text(left,top+30,f'{trade["broker_day"]} / net {trade["net_dollars"]:,.2f} USD',19))
        svg.append(svg_text(left,top+57,f'{trade["contract"]}',15))
        points = " ".join(f'{x(rows[i]["timestamp"]):.6f},{y(float(rows[i]["close"])):.6f}' for i in indices)
        svg.append(f'<polyline data-example-index="{case_index}" points="{points}" fill="none" stroke="#246b61" stroke-width="2"/>')
        level_records=[]
        for key,color in [("range_high","#8f62bb"),("range_low","#8f62bb"),("midpoint","#beaccf")]:
            position=y(case[key])
            svg.append(f'<line data-example-index="{case_index}" data-level="{key}" x1="{box["left"]}" x2="{box["right"]}" y1="{position:.6f}" y2="{position:.6f}" stroke="{color}" stroke-dasharray="7 5"/>')
            level_records.append({"source_pointer":f"/{case_index}/{key}","value":case[key],"label":key})
        markers=[]
        for time_key,value_key,label,color in [("entry_time","entry_price","Fill","#277348"),("exit_time","exit_price","Exit","#aa6040")]:
            px,py=x(trade[time_key]),y(trade[value_key])
            svg.append(f'<circle data-example-index="{case_index}" data-marker="{label}" cx="{px:.6f}" cy="{py:.6f}" r="5" fill="{color}"/>')
            svg.append(svg_text(px+7,py-8,label,16,color=color))
            markers.append({"time_pointer":f"/{case_index}/trade/{time_key}","price_pointer":f"/{case_index}/trade/{value_key}",
                            "time":trade[time_key],"price":trade[value_key],"label":label})
        for key,time_key,color in [("initial_stop","initial_stop_active_at","#c07939"),("reset_stop","reset_stop_active_at","#aa6040")]:
            if trade.get(key) is None or trade.get(time_key) is None:
                continue
            end_time = trade["reset_stop_active_at"] if key=="initial_stop" and trade.get("reset_stop_active_at") else trade["exit_time"]
            start_x,end_x=x(trade[time_key]),x(end_time)
            if end_x < start_x:
                continue
            position=y(trade[key])
            svg.append(f'<line data-example-index="{case_index}" data-stop="{key}" x1="{start_x:.6f}" x2="{end_x:.6f}" y1="{position:.6f}" y2="{position:.6f}" stroke="{color}" stroke-width="2" stroke-dasharray="4 3"/>')
            level_records.append({"source_pointer":f"/{case_index}/trade/{key}","value":trade[key],"label":key,
                                  "start_time":trade[time_key],"end_time":end_time})
        svg.append(svg_text(left,top+448,f'{rows[indices[0]]["timestamp"][11:16]}–{rows[indices[-1]]["timestamp"][11:16]} UTC; {trade["exit_reason"]} exit',18))
        role = "Actual alternative trade." if case["outcome"] in {"win","loss"} else "Baseline trade shown; alternative had known no fill."
        svg.append(wrapped_svg(left,top+480,role+" Slipped fills need not lie on the close curve.",48,17))
        panels.append({"example_index":case_index,"example_id":f'{policy}:{case["side"]}:{case["outcome"]}',
                       "selection_artifact":"example-selection.json","selection_pointer":f"/{case_index}",
                       "rule":case["rule"],"trade_role":case.get("trade_role","actual_candidate"),
                       "source_rows":indices,"plot_box":box,"x_domain":[first,last],"x_range":[box["left"],box["right"]],
                       "y_domain":[low,high],"y_range":[box["bottom"],box["top"]],"levels":level_records,"markers":markers,
                       "contract":trade["contract"],"trade_id":trade["trade_id"]})
        for i in indices:
            plotted.append({"source_row":i,"original_source_row":draft.sources[artifact]["selected_source_rows"][i],
                            "values":{key:saved_cell(key,rows[i][key]) for key in ["policy","trade_id","timestamp","contract","open","high","low","close"]}})
    svg.append(wrapped_svg(40,1370,"Empirical price paths, not account returns. Purple guides are range boundaries and midpoint. Orange and red segments show saved initial and reset stops; outcomes include assumed costs.",118,17))
    svg.append("</svg>")
    return "\n".join(svg).encode(), {
        "kind":"empirical-example","source_artifact":artifact,"source_sha256":draft.sources[artifact]["sha256"],
        "selection_artifact":"example-selection.json","selection_sha256":draft.sources["example-selection.json"]["sha256"],
        "plotted_values":plotted,"plot_encoding":{"kind":"empirical-close-v1","canvas":[1240,1400],"coordinate_precision":6,"panels":panels},
    }


def assemble(draft: PublicationDraft) -> dict[str, Any]:
    spec = draft.spec
    policies = tuple(POLICIES[key] for key in spec.policy_keys) or tuple(POLICIES.values())
    for artifact in ("config.json","selection.json","assessment.json","account-settings.json","example-selection.json","execution-completion.json"):
        draft.copy_json(artifact)
    draft.copy_text("protocol.md")
    sections = []
    def text(id, title, body, **kwargs):
        sections.append(text_section(draft,id,title,body,**kwargs))
    def copy(name,where=None,target=None):
        return draft.copy_table(f"tables/{name}.csv",target or f"tables/{name}.csv",where)
    def table(id,title,artifact,keys,filters=None,description="",notes=None):
        sections.append(draft.table(id,title,artifact,columns(keys),filters,description,notes))
    def figure(id,title,svg,provenance,caption):
        sections.append(draft.figure(id,title,id,svg,provenance,alt=title+"; saved sources and interpretation are described below.",caption=caption))
    def bars(id,title,artifact,indices,label_keys,value,unit="USD",percent=False):
        svg,provenance = saved_bars_svg(draft,artifact,indices,label_keys,value,title,
                                      "Saved cells; standardized assumed-cost evidence unless labeled otherwise",
                                      unit=unit,precision=1 if percent else 0,format_kind="percent" if percent else "number")
        figure(id,title,svg,provenance,"Exact saved values. Unavailable values are not plotted as zero. The accompanying tables retain support counts and uncertainty; no research statistic is recalculated.")
    def guide(kind,q=None):
        caption = "Illustrative only: authored process and timing, not an observed market example. Frozen complete-candle availability, whole-GC sizing, assumed costs and unknown outcomes apply. Screenshot appearance informed the purple range guides; unexplained marks are not interpreted."
        figure("method-guide","Illustrative method guide",illustrative_svg(kind,q),{
            "kind":"illustrative","guide_id":kind+(f"-{q:g}" if q is not None else ""),
            "authored":True,"not_empirical":True,
            "source_artifact":"protocol.md","source_sha256":draft.sources["protocol.md"]["sha256"],
            "plotted_values":[],"settings_artifact":"config.json","settings_sha256":draft.sources["config.json"]["sha256"],
            "plot_encoding":{"kind":"authored-process-v1","qualification":"No empirical numerical price geometry."},
        },caption)
    decision = "The frozen validation decision retains the Phase 1 baseline: no primary reclaim policy qualified. Later assessment and replication were read after that decision; no rule was retuned. Passive limits and every prespecified protected-boundary replacement remain exploratory. Prior baseline exposure means these chronological partitions are not pristine holdouts."
    text("decision","Frozen decision and interpretation",decision,
         sources=[json_source(draft,"selection.json",key) for key in ["/selected_policy","/decision","/prior_baseline_exposure"]],
         authored=False)
    if spec.group == "comparison":
        candidate_columns = columns(["policy","validation_episodes","common_complete_pairs","completed_fills","validation_mean_difference","qualifies"])
        sections.append(draft.json_table("selection","Primary validation selection receipt","selection.json",
                                         [{key:f"/candidates/{i}/{key}" for key in [column["key"] for column in candidate_columns]} for i in range(4)],
                                         candidate_columns))
    if spec.view == "account-risk":
        guide("financial")
        settings = ["initial_capital","daily_equity_risk_percent","maximum_leverage","margin_percent","minimum_quantity","quantity_step"]
        items=[draft.json_metric("risk-settings",i,"account-settings.json",f"/{key}",key.replace("_"," ").capitalize(),format="number",precision=0,
                                unit="USD" if key=="initial_capital" else "%" if key in {"daily_equity_risk_percent","margin_percent"} else "contracts" if key in {"minimum_quantity","quantity_step"} else "times")
               for i,key in enumerate(settings)]
        sections.append({"id":"risk-settings","kind":"metrics","title":"Frozen executable-account settings","items":items})
        text("account-meaning","Account populations and missing prices",
             "Standardized one-contract comparisons and executable-account results are separate. Observed fills and known signals are lower-information saved counts, with unknown original/second fills and unknown outcomes displayed alongside them. Total account net is unavailable when capital or later outcomes are unknown; a known completed-only total does not fill that gap. Post-loss financial recovery requires a genuinely executed original leg to be flat, its realized net loss known at the later signal, and combined executed-leg net after both costs. Price returning to a range level does not prove financial recovery. Whole-contract quantity skips do not justify fractional contracts or larger capital.")
        modes = ("original_only","replacement_only","same_direction_concurrent_add_on","post_exit_reentry","post_realized_loss_recovery","flat_only_opposite_reversal")
        for index,mode in enumerate(modes):
            artifact=copy("account",{"mode":mode},f"tables/account-{mode}.csv")
            table(f"account-{index}",mode.replace("_"," ").capitalize(),artifact,
                  ["policy","year","session","side","signals","original_fills","second_fills","unknown_original_fills","unknown_second_fills","quantity_skips","unknown","net_dollars"],
                  cohort_filters("summary"),"Conditional Phase 1 accepted-episode cohorts; original breakout session/side, not hypothetical candidate entry sessions. Zero and unavailable values retain different meanings.")
        financial=copy("account",{"mode":"post_realized_loss_recovery"},"tables/financial-recovery.csv")
        table("financial-denominators","Financial recovery and eligibility denominators",financial,
              ["policy","year","session","side","eligible_loss","unknown_eligible_loss","eligible_loss_unknown_outcome","completed_financial_recovery_pairs","full_recovery","partial_recovery","further_loss","recovery_rate"],cohort_filters("summary"))
        table("financial-net","Financial recovery amounts and incomplete observations",financial,
              ["policy","year","session","side","no_improvement","full_recovery_per_eligible_loss","recovery_dollars","loss_recovered_dollars","mean_recovery_minutes","net_known_episodes","net_completed_known_dollars","unknown"],cohort_filters("summary"))
        capacity=copy("account-capacity")
        text("capacity-scope","Static range-price capacity certificate",
             "The capacity CSV conditions on the observed range certificate and frozen initial capital. It preserves both directions and full/half budget quantities, risk, leverage/margin constraints and skip reasons. It is a static initial-capital audit, not an executable account equity curve or a bound on missing future candidate prices.")
        draft.download("account-outcomes","Account outcomes by policy and mode",copy("account",target="tables/account-all.csv"),
                       ["policy","mode","year","session","side","episodes","signals","eligible_signals","original_fills","second_fills","unknown_original_fills","unknown_second_fills","quantity_skips","unknown","censored","net_dollars","net_known_episodes","net_completed_known_dollars","eligible_loss","completed_financial_recovery_pairs","full_recovery","partial_recovery","further_loss","recovery_rate"],
                       population="Conditional accepted Phase 1 episodes, with separate account policy/mode cohorts.",units="USD, whole GC contracts and ratio rates.",scope="Executable account; unknown capital or missing outcomes retain unavailable total net.")
        draft.download("static-capacity","Static initial-capital range certificate",capacity,draft.sources[capacity]["columns"],
                       population="Observed eligible broker-day range certificates, both directions.",units="USD, GC points, whole GC quantities.",scope="Static frozen-capital conditional capacity only; not candidate entry-price feasibility.")
    elif spec.group == "protected" and spec.view in {"occurrence","events"}:
        if spec.view=="occurrence":
            guide("protected")
        text("protected-meaning","Protected boundary, horizons and event sessions",
             "For upper-first originals, the protected level is the overnight low; the lower-first mirror uses the overnight high. These are fixed overnight boundaries, not swings. Visits before the original fill are excluded. Original-session-instance and remaining-broker-window horizons remain distinct. Known event evidence survives a later gap; known absence requires complete observation. Missing first-event timing is not an exact first timestamp. Rate bounds are all-episode known-event/missingness bounds, not confidence intervals. Recovery after a known breach is conditional price-path evidence and is not a realized trading target.")
        occurrence=copy("occurrence",{"horizon":"remaining_broker_window"} if spec.view=="events" else None)
        table("occurrence","Protected boundary event occurrence",occurrence,
              ["year","session","side","horizon","event","episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound"],
              cohort_filters("summary"),"Original fill-year/session/side cohorts. Occurrence tab retains both horizons; this event-session tab uses remaining-window occurrence context.")
        table("event-timing","Elapsed and exposure support",occurrence,
              ["year","session","side","horizon","event","known_events","elapsed_denominator","mean_elapsed_minutes","mean_elapsed_lower_minutes","mean_elapsed_upper_minutes","mean_observed_exposure_minutes","repeat_contacts"],
              cohort_filters("summary"),"Elapsed bounds reflect observed timing precision; mean observed exposure is distinct from the full scheduled horizon.")
        for index,horizon in enumerate(("original_session","remaining_broker_window")):
            recovery=copy("recovery",{"horizon":horizon},f"tables/recovery-{horizon}.csv")
            table(f"recovery-{index}",f"Conditional price recovery — {horizon.replace('_',' ')}",recovery,
                  ["year","session","side","level","event","episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound"],
                  cohort_filters("summary"),"Denominator is known breach episodes; levels are opposite boundary, midpoint and original boundary. Touch and separate close reclaim are distinct.")
            if spec.view=="events":
                distribution=copy("event-distribution",{"horizon":horizon},f"tables/event-distribution-{horizon}.csv")
                table(f"event-session-{index}",f"Actual event sessions — {horizon.replace('_',' ')}",distribution,
                      ["year","session","side","event","count","total_known_events","share","unknown_time"],cohort_filters("events"),
                      "Year and session are actual boundary-event time, unlike original-fill cohort filters above. Unknown event-time categories remain visible.")
        transition=copy("transitions",{"transition":"breakout_to_breach"},"tables/breakout-to-breach.csv")
        table("transitions","Breakout-to-breach session transitions",transition,
              ["year","side","from_session","to_session","count","unknown"],
              [{"key":"year","label":"Original breakout year","defaultValue":"all"},{"key":"side","label":"Original side","defaultValue":"combined"},{"key":"from_session","label":"Breakout session"}],
              "Rows retain actual from/to sessions and Unknown categories; year is anchored to original breakout.")
        all_rows=draft.copied_table(occurrence)
        selected=[i for i,row in enumerate(all_rows) if row["year"]=="all" and row["session"]=="all" and row["side"]=="upper-first" and row["event"]=="one_tick_breach"]
        bars("breach-frequency","Upper-first protected-low breach by horizon",occurrence,selected,["horizon"],"rate",unit="Known-event rate",percent=True)
        draft.download("occurrence","Protected occurrence and timing",occurrence,
                       ["year","session","side","horizon","event","episodes","known_events","known_none","unknown","known_denominator","rate","lower_bound","upper_bound","mean_elapsed_minutes","elapsed_denominator","mean_elapsed_lower_minutes","mean_elapsed_upper_minutes","mean_observed_exposure_minutes","repeat_contacts"],
                       population="All accepted original episodes, including censored baseline outcomes.",units="Counts, ratio rates, minutes.",scope="Post-fill price events; absence needs complete observation; not financial recovery.")
        draft.download("recovery","Remaining-window conditional price recovery", "tables/recovery-remaining_broker_window.csv",
                       ["year","session","side","horizon","level","event","episodes","known_events","known_none","unknown","known_denominator","rate","lower_bound","upper_bound","original_episodes","known_breach_episodes","known_no_breach_episodes","unknown_breach_episodes","mean_elapsed_minutes"],
                       population="Conditional known protected-boundary breach episodes.",units="Counts, ratio rates, minutes.",scope="Fixed levels and post-breach paths; not trade P&L or targets.")
    else:
        if spec.view=="summary" or spec.view=="trades":
            if spec.group=="passive-limits":
                guide("passive")
            elif spec.group=="protected":
                guide("protected")
            elif spec.policy_keys:
                guide("reclaim",{"q0":0,"q25":.25,"q50":.5,"q75":.75}[spec.policy_keys[0]])
        where = {"policy":policies}
        if spec.group=="comparison":
            # Overview tabs are explicit bounded aggregate projections. Detailed
            # cross-cohort rows remain available in each authored condition group.
            where["side"]="combined"
            if spec.view!="year":
                where["year"]="all"
            if spec.view!="entry":
                where["session"]="all"
        paired=copy("paired",where)
        cohorts=copy("trade-cohorts",where)
        selectors=cohort_filters(spec.view)
        text("masks","Paired comparisons and cohort anchors",
             "Paired tables use the original-breakout year, session and side (upper-first/lower-first); known no fill contributes a zero alternative outcome only when its path is known. Family common masks exclude missing pairs; individual-mask sensitivity is separately labeled. Candidate performance tables use actual candidate-fill New York year/session and long/short direction, and closed statistics exclude censored fills. No-fill episodes have no invented candidate entry session. A chronological policy may enter after the baseline exited; those opportunity costs remain in the paired comparison.")
        table("paired-results","Family common-mask paired improvement",paired,
              ["policy","year","session","side","episodes","complete_pairs","missing_pairs","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high"],selectors)
        table("participation","Participation and known no-fill outcomes",paired,
              ["policy","year","session","side","opportunities","opportunity_unknown","armed","signals","fills","completed","censored","no_fill"],selectors)
        table("tradeoffs","Baseline tradeoffs and timing",paired,
              ["policy","year","session","side","improved","deteriorated","equal","missed_winners","avoided_losses","mean_entry_delay","mean_price_improvement","unknown"],selectors)
        if spec.group!="passive-limits":
            table("paired-totals","Paired totals, masks and marginal confidence",paired,
                  ["policy","year","session","side","baseline_net_dollars","alternative_net_dollars","individual_pairs","individual_mean_difference","participation_rate","missing_rate","signal_rate","adjusted_confidence"],selectors)
        candidate_selectors=cohort_filters(spec.view)
        table("candidate-performance","Actual candidate fills and closed net P&L",cohorts,
              ["policy","year","session","side","executable_fills","completed","censored","net_dollars","mean_net_dollars","mean_dollars_low","mean_dollars_high","profit_factor"],candidate_selectors)
        if spec.group!="passive-limits":
            table("points-risk","Points, costs, initial-risk R and drawdown",cohorts,
              ["policy","year","session","side","gross_points","net_points","gross_dollars","cost_dollars","net_r","r_denominator","expectancy_r","max_drawdown_dollars"],candidate_selectors,
                  "Raw-price gross is on the primary execution/reset path; a full zero-cost backtest appears separately among scenarios.")
            table("candidate-outcomes","Net winners, losses and confidence",cohorts,
              ["policy","year","session","side","wins","losses","breakevens","win_rate","win_rate_low","win_rate_high","payoff_ratio","invalid_r"],candidate_selectors)
            table("trade-path","Holding time, observed excursions and coverage",cohorts,
              ["policy","year","session","side","mfe_points","mae_points","holding_minutes","stop_exits","timed_exits","max_losing_streak","entry_coverage_start","entry_coverage_end"],candidate_selectors,
                  "Minute/OHLC-estimated holding time is not tick-exact. Censoring and ambiguous excursions remain pinned in the private ledger.")
        scenario=copy("scenarios",{"policy":policies})
        table("scenarios","Costs and execution-model sensitivities",scenario,
              ["policy","scenario","episodes","fills","completed","censored","unknown","no_fill","net_dollars","paired_count","mean_difference","baseline_comparison"],
              description="Assumed cost scenarios, not actual broker charges. High/low-first ordering bounds and native fifteen-minute OHLC approximation retain their own coverage and masks; different coverage is not a fixed-population paired-profit sensitivity.")
        if spec.group!="passive-limits":
            supported=tuple(policy for policy in policies if not policy.startswith("passive-"))
            intervals=copy("interval-sensitivities",{"policy":supported},"tables/intervals.csv")
            table("interval-sensitivity","Chronological partition and block-length sensitivity",intervals,
                  ["policy","period","side","block_weeks","episodes","complete_pairs","mean_difference","lower","upper","adjusted_lower","adjusted_upper"],
                  [{"key":"period","label":"Partition","defaultValue":"overall"},{"key":"side","label":"Original side","defaultValue":"combined"},{"key":"block_weeks","label":"Block weeks","defaultValue":4}],
                  "Saved paired intervals and prespecified block lengths; validation, later assessment and partial replication remain visible even when selection retained the baseline.")
        if spec.view in {"summary","entry","trades"}:
            timing=copy("timing",{"policy":policies})
            table("timing","Actual candidate entry hour and weekday",timing,
                  ["policy","dimension","bucket","side","executable_fills","completed","censored","entry_share","net_dollars","mean_net_dollars","holding_minutes","profit_factor"],
                  [{"key":"dimension","label":"Timing view","defaultValue":"hour"},{"key":"side","label":"Actual candidate side","defaultValue":"combined"}])
        if spec.group=="passive-limits":
            opportunity=copy("level-opportunities",{"fraction":("0.25","0.5","0.75")},"tables/level-opportunities.csv")
            touch_path=copy("level-opportunities",{"fraction":("0.25","0.5","0.75"),"event":"touch"},"tables/first-touch-path.csv")
            text("level-diagnostics","Passive opportunity diagnostics and first-touch path",
                 "Touch, inward close and outward reclaim are separate opportunity-event rows. Their range recovery, diagnostic 1R and excursion columns all refer to the path after the first touch, conditional on the row's event; none starts at a candidate fill. Diagnostic 1R is the directional distance between the raw level and its frozen percent/tick-rounded stop, not a realized trade R. MFE, MAE and range-depth means include observed partial paths, so they are observed-path excursions, not complete-window maxima. These price diagnostics are not realized passive returns.")
            table("opportunity-frequency","Passive level event frequency",opportunity,
                  ["year","session","side","fraction","event","episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound"],cohort_filters(spec.view))
            table("first-touch-path","Conditional first-touch recovery and diagnostic risk",touch_path,
                  ["year","session","side","fraction","event","range_recovery_known_denominator","range_recovery_unknown","range_recovery_rate","first_1r_success_known_denominator","first_1r_success_unknown","first_1r_success_rate","mean_event_risk_points"],cohort_filters(spec.view))
            table("observed-excursions","Observed first-touch excursions and denominators",touch_path,
                  ["year","session","side","fraction","event","mean_mfe_after_touch_points","mfe_after_touch_points_denominator","mean_mae_after_touch_points","mae_after_touch_points_denominator","mean_deepest_range_fraction","deepest_range_fraction_denominator","not_realized_trade_return"],cohort_filters(spec.view))
        # All chart selectors name saved aggregate rows; no new outcome statistic.
        if spec.policy_keys and len(policies)==1:
            rows=draft.copied_table(cohorts)
            if spec.view=="year":
                indices=[i for i,row in enumerate(rows) if row["year"]!="all" and row["session"]=="all" and row["side"]=="combined"]
                label=["year"]
            elif spec.view=="entry":
                indices=[i for i,row in enumerate(rows) if row["year"]=="all" and row["session"]!="all" and row["side"]=="combined"]
                label=["session"]
            else:
                indices=[i for i,row in enumerate(rows) if row["year"]=="all" and row["session"]=="all" and row["side"]!="combined"]
                label=["side"]
            bars("cohort-net","Candidate closed net P&L by "+label[0],cohorts,indices,label,"net_dollars")
            if spec.view=="summary":
                equity=copy("equity",{"policy":policies[0]})
                for id,value,title in [("equity","cumulative_net_dollars","Saved cumulative candidate net P&L"),("drawdown","drawdown_dollars","Saved closed-P&L drawdown path")]:
                    svg,provenance=saved_line_svg(draft,equity,value,title,"Standardized one-contract closed outcomes with assumed costs")
                    figure(id,title,svg,provenance,"Exact saved closed-trade ledger path; censored outcomes are excluded. This is not source-account capital or an account return.")
        elif spec.view in {"summary","trades"}:
            rows=draft.copied_table(paired)
            indices=[i for i,row in enumerate(rows) if row["year"]=="all" and row["session"]=="all" and row["side"]=="combined"]
            bars("paired-mean","Family common-mask paired mean by policy",paired,indices,["policy"],"mean_difference")
        elif spec.view in {"year","entry"} and spec.policy_keys:
            rows=draft.copied_table(cohorts)
            for policy in policies:
                if spec.view=="year":
                    indices=[i for i,row in enumerate(rows) if row["policy"]==policy and row["year"]!="all" and row["session"]=="all" and row["side"]=="combined"]
                    label=["year"]
                else:
                    indices=[i for i,row in enumerate(rows) if row["policy"]==policy and row["year"]=="all" and row["session"]!="all" and row["side"]=="combined"]
                    label=["session"]
                bars(f"{policy}-cohort-net",policy+" — net P&L by "+label[0],cohorts,indices,label,"net_dollars")
        if spec.policy_keys and spec.view in {"summary","trades"}:
            for policy in policies:
                for suffix,outcomes in [("candidate",("win","loss")),("no-fill",("missed_baseline_win","avoided_baseline_loss"))]:
                    svg,provenance=empirical_svg(draft,policy,outcomes)
                    caption="Saved earliest chronological completed candidate net win/loss per actual direction." if suffix=="candidate" else "Saved earliest chronological known no-fill missed baseline winner and avoided baseline loser per original direction. These are unchanged baseline trades; there was no alternative fill."
                    figure(f"{policy}-{suffix}","Empirical "+policy+" "+suffix.replace("-"," ")+" examples",svg,provenance,
                           caption+" The close curve is observed one-minute evidence; slipped fills and OHLC-estimated exit-time bounds are separately saved, and need not lie on the close curve. Never inferred from screenshot prices.")
        draft.download("paired","Paired comparison and support",paired,
                       ["policy","family","year","session","side","episodes","complete_pairs","missing_pairs","opportunities","signals","fills","completed","censored","unknown","no_fill","baseline_net_dollars","alternative_net_dollars","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high","missed_winners","avoided_losses"],
                       population="Original-breakout cohorts on explicit family common masks.",units="USD, counts; rates remain ratios.",scope="Paired alternatives and known no-fill opportunity cost; missing is not zero.")
        draft.download("candidate-performance","Actual candidate performance",cohorts,
                       ["policy","year","session","side","executable_fills","completed","censored","wins","losses","breakevens","win_rate","net_dollars","gross_dollars","net_points","gross_points","cost_dollars","mean_net_dollars","mean_dollars_low","mean_dollars_high","net_r","r_denominator","expectancy_r","profit_factor","max_drawdown_dollars"],
                       population="Actual candidate-fill New York year/session/side cohorts.",units="USD, GC points, initial-risk R and ratio rates.",scope="Standardized contract; closed statistics exclude censored fills.")
        draft.download("scenarios","Cost and execution scenarios",scenario,draft.sources[scenario]["columns"],
                       population="Separate prespecified execution models and cost masks.",units="USD, GC ticks, counts.",scope="Assumed costs; native OHLC has different coverage.")
        if spec.group=="passive-limits":
            draft.download("level-opportunities","Passive first-touch opportunity diagnostics",opportunity,
                           ["year","session","side","fraction","event","episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound","range_recovery_known_denominator","range_recovery_unknown","range_recovery_rate","first_1r_success_known_denominator","first_1r_success_unknown","first_1r_success_rate","mean_mfe_after_touch_points","mfe_after_touch_points_denominator","mean_mae_after_touch_points","mae_after_touch_points_denominator","mean_deepest_range_fraction","deepest_range_fraction_denominator"],
                           population="Conditional first-touch paths on the original accepted episode roster.",units="GC points, counts and ratio rates.",scope="Observed paths may be partial; diagnostic 1R is not trade R.")
    text("uncertainty","Uncertainty, limits and deferred scope",
         "Intervals are saved block-resampling outputs with prespecified block-length sensitivity. Primary-family adjusted intervals are marginal contrasts within each reported cohort; they do not provide simultaneous coverage across all year/session/side cohorts. Protected adjusted intervals apply only to the upper-first prespecified family; mirror and combined views are unadjusted exploratory evidence. Empty cohorts and undefined profit factors/rates remain unavailable. The most recent calendar year is partial. Costs are frozen assumptions, not broker fees. Fixed broker time and New York reporting time differ. Missing minutes, stale source stretches, estimated intrabar order and contract transitions limit exact execution inference. Native TradingView equivalence is unverified. Phase 3 and H10 remain uncomputed.")
    if len(sections)>30 or len({section["id"] for section in sections})!=len(sections):
        raise ValueError(f"Report exceeds unique bounded sections: {spec.publication_id} {len(sections)}")
    # References cite immutable original cells via the exact copied artifact hash.
    references=[]
    for index,source in enumerate(draft.sources.values()):
        references.append({"id":f"source-{index}","kind":"saved-artifact","label":source["path"],
                           "title":"Saved Phase 2 source projection", "runId":draft.run_id,"artifact":source["path"],"sha256":source["sha256"]})
    if len(references)>100:
        raise ValueError("Too many explicit saved-source references")
    return {
        "schemaVersion":"1.1","id":spec.publication_id,"title":"GC- Overnight Breakout 15M — "+spec.title,
        "summary":"Phase 2 saved evidence: frozen validation retains the baseline; primary reclaim comparisons, exploratory passive/protected policies and explicit unknown outcomes remain visible.",
        "publishedAt":json.loads(draft.files["execution-completion.json"])["finished_at"][:19]+"Z",
        "source":{"producer":"sahadeva","runId":draft.run_id},"sections":sections,"references":references,
        "downloads":draft.download_entries, "notes":["Saved rows only: browser filters and tabs do not compute research statistics.",
                                  "The original Phase 1 baseline remains separately available in this study.",
                                  "Standardized one-contract P&L, price recovery diagnostics and executable account outcomes are distinct."],
    }


def check_inputs(stage: Path) -> dict[str, Any]:
    inputs = SavedInputs(stage)
    config = inputs.json("config.json")
    if config.get("schema_version") != "abacus.study23.phase2/v1" or config.get("protocol_version") != "2.0.0":
        raise ValueError("Expected frozen Phase 2 config")
    if config["run_id"] != stage.name:
        raise ValueError("Staged directory and frozen run identity disagree")
    inputs.read("protocol.md")
    inputs.json("selection.json")
    rows = {}
    for name in TABLE_INPUTS:
        columns, table = inputs.table(f"tables/{name}.csv")
        rows[name] = {"rows": len(table), "columns": len(columns)}
    return {"result": "inputs-present", "run_id": config["run_id"], "tables": rows, "publications_planned": len(report_specs()), "qualification": "Read-only presence/schema check, not numerical or publication verification."}


def owning_stage(stage: Path) -> Path:
    stage = stage.absolute()
    owning = ROOT / "work" / STUDY
    if stage.parent != owning or stage.is_symlink() or not stage.is_dir() or owning.is_symlink():
        raise ValueError("Publication writes require a new ordinary owning work-stage directory")
    return stage


def write_new(root: Path, artifact: str, data: bytes) -> None:
    path = root / safe_relative(artifact)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def generate(stage: Path, node: Path, package_root: Path) -> dict[str, Any]:
    stage=owning_stage(stage)
    check_inputs(stage)
    inputs=SavedInputs(stage)
    completion=inputs.json("execution-completion.json")
    if completion.get("phase2")!="computed" or completion.get("phase3")!="uncomputed":
        raise ValueError("Actual completed Phase 2 saved evidence is required")
    if (stage/"publications").exists():
        raise ValueError("Never replace a prepared publication; retain the prior draft attempt explicitly")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt=stage/"publication-render-attempts"/stamp
    attempt.mkdir(parents=True,exist_ok=False)
    snapshot=stage/"source-publication"/stamp
    snapshot.mkdir(parents=True,exist_ok=False)
    for source in [Path(__file__),HERE/"rasterize_figures.mjs",HERE/"tests/test_phase2_publish_web.py"]:
        write_new(snapshot,source.name,source.read_bytes())
    command={"argv":sys.argv,"cwd":str(Path.cwd()),"python":sys.version,"producer_version":VERSION,
             "exporter_sha256":sha_bytes(Path(__file__).read_bytes()),
             "renderer_sha256":sha_bytes((HERE/"rasterize_figures.mjs").read_bytes()),
             "source_snapshot":str(snapshot.relative_to(stage)),"started_at":datetime.now(timezone.utc).isoformat(),
             "scope":"Exact saved-cell projection and presentation geometry; no numerical producer imports."}
    write_new(snapshot,"command.json",json_bytes(command))
    drafts=[]
    render=[]
    # Complete all report objects and their presentation sources before any
    # canonical per-publication artifact is written.
    for spec in report_specs():
        draft=PublicationDraft(inputs,stage.name,spec)
        report=assemble(draft)
        report_data=json_bytes(report)
        if len(report_data)>2*1024*1024:
            raise ValueError("Filtered source report exceeds two MiB")
        if sum(len(draft.files[item["path"]]) for item in draft.downloads)>8*1024*1024:
            raise ValueError("Selected CSV total exceeds filtered eight MiB")
        drafts.append((draft,report_data))
        for figure in draft.figures:
            svg=attempt/spec.publication_id/figure["svg_path"]
            svg.parent.mkdir(parents=True,exist_ok=True)
            svg.write_bytes(draft.files[figure["svg_path"]])
            render.append({"svg":str(svg),"png":str(attempt/spec.publication_id/figure["path"])})
    inventory=attempt/"render-inventory.json"
    write_new(attempt,inventory.name,json_bytes(render))
    process=subprocess.run([str(node),str(snapshot/"rasterize_figures.mjs"),str(package_root),str(inventory)],
                           capture_output=True,text=True,timeout=240)
    write_new(attempt,"renderer-stdout.log",process.stdout.encode())
    write_new(attempt,"renderer-stderr.log",process.stderr.encode())
    if process.returncode:
        write_new(attempt,"failed.json",json_bytes({"returncode":process.returncode,"command":command}))
        raise ValueError("SVG rasterization failed; retained attempt logs identify the failure")
    runtime=json.loads((attempt/"render-inventory.json.runtime.json").read_text())
    for draft,_ in drafts:
        for figure in draft.figures:
            draft.complete_png(figure["path"],(attempt/draft.spec.publication_id/figure["path"]).read_bytes())
    # The finished source-map includes all final PNG hashes. Intermediate
    # reports with empty hashes are never retained as source snapshots.
    results=[]
    for draft,report_data in drafts:
        root=stage/"publications"/draft.spec.publication_id
        source_map=json_bytes(draft.source_map())
        receipt={**command,"renderer":runtime,"finished_at":datetime.now(timezone.utc).isoformat(),
                 "run_id":stage.name,"publication_id":draft.spec.publication_id,
                 "publication_sha256":sha_bytes(report_data),"source_map_sha256":sha_bytes(source_map),
                 "status":"generated-awaiting-independent-verification",
                 "renderer_inventory":str(inventory.relative_to(stage)),
                 "limits":["No scientific revalidation is performed by this exporter.","Independent transfer and visual review precede sealing."]}
        for artifact,data in {**draft.files,"publication.json":report_data,"source-map.json":source_map,"publication-generation.json":json_bytes(receipt)}.items():
            write_new(root,artifact,data)
        results.append({"publication_id":draft.spec.publication_id,"source_bytes":len(report_data),"sections":len(json.loads(report_data)["sections"]),
                        "figures":len(draft.figures),"displayed_cells":len(draft.bindings),"downloads":len(draft.downloads)})
    receipt={"run_id":stage.name,"producer_version":VERSION,"status":"generated-awaiting-independent-verification",
             "publications":results,"renderer":runtime,"source_snapshot":str(snapshot.relative_to(stage))}
    write_new(attempt,"generation-result.json",json_bytes(receipt))
    return receipt


def finalize_manifests(stage: Path) -> dict[str, Any]:
    stage=owning_stage(stage)
    check_inputs(stage)
    results=[]
    run_prefix=Path("runs")/STUDY/stage.name
    for spec in report_specs():
        root=stage/"publications"/spec.publication_id
        report=read_regular(root,"publication.json")
        mapping=json.loads(read_regular(root,"source-map.json"))
        verified=json.loads(read_regular(root,"publication-verification.json"))
        if verified.get("status")!="passed" or verified.get("publication_sha256")!=sha_bytes(report) or verified.get("source_map_sha256")!=sha_bytes(read_regular(root,"source-map.json")):
            raise ValueError("A separate passing independent verifier must bind the exact report and source map")
        sources={}
        for record in mapping["source_artifacts"]:
            if sha_bytes(read_regular(stage,record["original_stage_source_path"]))!=record["original_source_sha256"]:
                raise ValueError("Original saved source changed after projection")
            path=str(run_prefix/"publications"/spec.publication_id/safe_relative(record["path"]))
            if sha_bytes(read_regular(root,record["path"]))!=record["sha256"]:
                raise ValueError("Copied saved source changed after verification")
            sources[path]=record["sha256"]
        outputs=[]
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name!="publication-manifest.json":
                relative=str(path.relative_to(root))
                outputs.append({"path":str(run_prefix/"publications"/spec.publication_id/safe_relative(relative)),
                                "sha256":sha_bytes(read_regular(root,relative))})
        manifest={"publication_id":spec.publication_id,"source_run_id":stage.name,"study_id":STUDY,
                  "source_artifacts":[{"path":path,"sha256":digest} for path,digest in sorted(sources.items())],
                  "outputs":outputs}
        data=json_bytes(manifest)
        manifest_path=root/"publication-manifest.json"
        if manifest_path.exists():
            if read_regular(root,"publication-manifest.json")!=data:
                raise ValueError("Never overwrite a finalized publication manifest")
        else:
            write_new(root,"publication-manifest.json",data)
        results.append({"publication_id":spec.publication_id,"manifest_sha256":sha_bytes(data),"outputs":len(outputs)})
    return {"status":"manifests-finalized","run_id":stage.name,"publications":results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Print authored report plan without reading data or writing files.")
    parser.add_argument("--check-inputs", action="store_true", help="Check explicit saved inputs without writing report output.")
    parser.add_argument("--generate", action="store_true", help="Prepare new private projections after all saved evidence has completed.")
    parser.add_argument("--finalize-manifests", action="store_true", help="Pin new manifests after separate independent publication verification.")
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--node",type=Path,default=Path("/Users/ppanati/.nvm/versions/node/v24.18.0/bin/node"))
    parser.add_argument("--renderer-packages",type=Path,default=Path("/Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/node"))
    args = parser.parse_args()
    if args.plan:
        print(json.dumps({"producer_version": VERSION, "planned_reports": [item.__dict__ | {"publication_id": item.publication_id} for item in report_specs()]}, indent=2))
    elif args.check_inputs and args.stage is not None:
        print(json.dumps(check_inputs(args.stage), indent=2))
    elif args.generate and args.stage is not None:
        print(json.dumps(generate(args.stage,args.node,args.renderer_packages),indent=2))
    elif args.finalize_manifests and args.stage is not None:
        print(json.dumps(finalize_manifests(args.stage),indent=2))
    else:
        parser.error("Use --plan, --check-inputs, --generate or --finalize-manifests with the explicit staged run.")


if __name__ == "__main__":
    main()
