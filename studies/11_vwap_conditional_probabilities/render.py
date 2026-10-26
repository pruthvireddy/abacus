"""Render report, chart specification, and SVG figures from saved evidence."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.features import PRODUCTS, SCALE, load_features
from src.outcomes import _dynamic_zones, load_source_year


def pct(value, digits=1):
    return "n/a" if pd.isna(value) else f"{100 * float(value):.{digits}f}%"


def ci(row):
    return f"{pct(row.ci_low)}–{pct(row.ci_high)}"


def brier_reading(row) -> str:
    delta = row.brier_difference
    interval = (row.difference_ci_low, row.difference_ci_high)
    if interval[1] < 0:
        return f"improved by {-delta:.4f} Brier ({-row.relative_error_reduction * 100:.1f}% relative); interval excludes zero"
    if interval[0] > 0:
        return f"worsened by {delta:.4f} Brier; interval excludes zero"
    return f"changed by {delta:+.4f} Brier; interval includes zero"


def md_table(headers, rows):
    clean = lambda value: str(value).replace("|", "\\|")
    return ("| " + " | ".join(map(clean, headers)) + " |\n| " +
            " | ".join(["---"] * len(headers)) + " |\n" +
            "\n".join("| " + " | ".join(map(clean, row)) + " |" for row in rows) + "\n")


class Document:
    def __init__(self):
        self.md, self.html = [], []

    def heading(self, text, level=2):
        self.md.append("#" * level + " " + text + "\n")
        self.html.append(f"<h{level}>{escape(text)}</h{level}>")

    def para(self, text):
        self.md.append(text + "\n")
        self.html.append(f"<p>{escape(text)}</p>")

    def table(self, headers, rows):
        self.md.append(md_table(headers, rows))
        self.html.append("<div class='table-wrap'><table><thead><tr>" +
                         "".join(f"<th>{escape(str(value))}</th>" for value in headers) +
                         "</tr></thead><tbody>" +
                         "".join("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) +
                                 "</tr>" for row in rows) + "</tbody></table></div>")

    def image(self, path, caption):
        self.md.append(f"![{caption}]({path})\n")
        self.html.append(f"<figure><img src='{escape(path)}' alt='{escape(caption)}'>"
                         f"<figcaption>{escape(caption)}</figcaption></figure>")

    def links(self, pairs):
        self.md.append(" · ".join(f"[{label}]({path})" for label, path in pairs) + "\n")
        self.html.append("<p class='links'>" + " · ".join(
            f"<a href='{escape(path)}'>{escape(label)}</a>" for label, path in pairs) + "</p>")

    def write(self, stage: Path):
        (stage / "report.md").write_text("\n".join(self.md) + "\n")
        css = """body{font:16px/1.55 system-ui,-apple-system,sans-serif;color:#172a36;background:#f5f8fa;max-width:1180px;margin:auto;padding:32px}h1,h2,h3{color:#103a50}h1{font-size:2.1rem}h2{margin-top:2.2rem;border-bottom:1px solid #cbd8de;padding-bottom:.25rem}p{max-width:100ch}.table-wrap{overflow-x:auto;background:#fff;border:1px solid #d8e2e7;border-radius:8px;margin:1rem 0}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:.5rem .65rem;border-bottom:1px solid #e3eaee;text-align:left;white-space:nowrap}th{background:#eaf2f5}tr:nth-child(even){background:#f8fafb}figure{background:#fff;padding:1rem;border:1px solid #d8e2e7;border-radius:8px;margin:1rem 0}img{max-width:100%;height:auto}figcaption{font-size:.85rem;color:#526b79}a{color:#075b80}.links{line-height:2.1}footer{margin-top:3rem;color:#526b79;font-size:.85rem}"""
        html = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>VWAP conditional probabilities</title><style>" + css +
                "</style></head><body>" + "\n".join(self.html) +
                "<footer>Offline exploratory research · conditional price paths, not trading win rates or profitability.</footer></body></html>")
        (stage / "report.html").write_text(html)


def line_svg(path: Path, title: str, panels: list[tuple[str, list[tuple[str, list[float]]]]],
             xlabels: list[str], ylabel="Probability"):
    width, height = 1280, 420
    panel_width = (width - 80) / len(panels)
    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
             f"<rect width='{width}' height='{height}' fill='white'/><text x='{width / 2}' y='26' text-anchor='middle' font-size='18' fill='#103a50'>{escape(title)}</text>"]
    colors = ["#136f83", "#e4a348", "#7d5ba6", "#3d8b5b"]
    for panel_index, (panel_title, series) in enumerate(panels):
        x0 = 55 + panel_index * panel_width
        plot_width = panel_width - 45
        parts.append(f"<text x='{x0 + plot_width / 2}' y='54' text-anchor='middle' font-size='14' fill='#103a50'>{escape(panel_title)}</text>")
        for tick in np.linspace(0, 1, 5):
            y = 330 - tick * 240
            parts.append(f"<line x1='{x0}' y1='{y}' x2='{x0 + plot_width}' y2='{y}' stroke='#dce6eb'/><text x='{x0 - 5}' y='{y + 4}' text-anchor='end' font-size='9' fill='#526b79'>{int(tick * 100)}%</text>")
        for series_index, (label, values) in enumerate(series):
            points = []
            for index, value in enumerate(values):
                if value is None or not np.isfinite(value):
                    continue
                x = x0 + (index + .5) * plot_width / len(xlabels)
                y = 330 - value * 240
                points.append(f"{x:.1f},{y:.1f}")
                parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='{colors[series_index % len(colors)]}'/>")
            if len(points) > 1:
                parts.append(f"<polyline points='{' '.join(points)}' fill='none' stroke='{colors[series_index % len(colors)]}' stroke-width='2'/>")
            parts.append(f"<rect x='{x0 + 5 + series_index * 90}' y='365' width='10' height='10' fill='{colors[series_index % len(colors)]}'/><text x='{x0 + 20 + series_index * 90}' y='374' font-size='9'>{escape(label)}</text>")
        for index, label in enumerate(xlabels):
            x = x0 + (index + .5) * plot_width / len(xlabels)
            parts.append(f"<text x='{x:.1f}' y='348' text-anchor='middle' font-size='8' fill='#526b79'>{escape(label)}</text>")
    parts.append(f"<text x='14' y='210' transform='rotate(-90 14 210)' text-anchor='middle' font-size='11' fill='#526b79'>{escape(ylabel)}</text></svg>")
    path.write_text("".join(parts))


def stacked_svg(path: Path, title: str, data: list[tuple[str, list[float]]], labels: list[str]):
    width, height = 840, 360
    colors = ["#136f83", "#e4a348", "#8c9aa3", "#b56f6f"]
    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
             f"<rect width='{width}' height='{height}' fill='white'/><text x='{width / 2}' y='28' text-anchor='middle' font-size='18' fill='#103a50'>{escape(title)}</text>"]
    for tick in np.linspace(0, 1, 5):
        y = 285 - tick * 210
        parts.append(f"<line x1='80' y1='{y}' x2='790' y2='{y}' stroke='#dce6eb'/><text x='72' y='{y + 4}' text-anchor='end' font-size='10'>{int(tick * 100)}%</text>")
    bar_width = 120
    for index, (name, values) in enumerate(data):
        x, bottom = 130 + index * 210, 285
        for class_index, value in enumerate(values):
            block = value * 210
            bottom -= block
            parts.append(f"<rect x='{x}' y='{bottom:.1f}' width='{bar_width}' height='{block:.1f}' fill='{colors[class_index]}'/>")
        parts.append(f"<text x='{x + bar_width / 2}' y='307' text-anchor='middle' font-size='12'>{escape(name)}</text>")
    for index, label in enumerate(labels):
        x = 110 + index * 170
        parts.append(f"<rect x='{x}' y='330' width='10' height='10' fill='{colors[index]}'/><text x='{x + 15}' y='339' font-size='10'>{escape(label)}</text>")
    parts.append("</svg>")
    path.write_text("".join(parts))


def calibration_svg(path: Path, calibration: pd.DataFrame):
    """Render primary-class reliability curves against the perfect-calibration line."""
    width, height = 1280, 420
    panel_width = (width - 80) / 3
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        f"<rect width='{width}' height='{height}' fill='white'/><text x='{width / 2}' y='26' text-anchor='middle' font-size='18' fill='#103a50'>Evaluation reliability: mean predicted versus observed</text>",
    ]
    eval_aug = calibration[(calibration.split == "evaluation") & (calibration.model == "augmented")]
    for panel_index, (question, outcome) in enumerate((("A", "return"), ("B", "return_first"), ("C", "day_first"))):
        subset = eval_aug[(eval_aug.question == question) &
                          (eval_aug.outcome_class == outcome)].sort_values("mean_predicted")
        x0 = 55 + panel_index * panel_width
        plot_width = panel_width - 45
        parts.append(f"<text x='{x0 + plot_width / 2}' y='54' text-anchor='middle' font-size='14' fill='#103a50'>{question} · {escape(outcome)}</text>")
        for tick in np.linspace(0, 1, 5):
            x = x0 + tick * plot_width
            y = 330 - tick * 240
            parts.append(f"<line x1='{x0}' y1='{y}' x2='{x0 + plot_width}' y2='{y}' stroke='#dce6eb'/>")
            parts.append(f"<line x1='{x}' y1='90' x2='{x}' y2='330' stroke='#eef3f5'/>")
            parts.append(f"<text x='{x0 - 5}' y='{y + 4}' text-anchor='end' font-size='9' fill='#526b79'>{int(tick * 100)}%</text>")
            parts.append(f"<text x='{x}' y='348' text-anchor='middle' font-size='9' fill='#526b79'>{int(tick * 100)}%</text>")
        parts.append(f"<line x1='{x0}' y1='330' x2='{x0 + plot_width}' y2='90' stroke='#8c9aa3' stroke-dasharray='5 4'/>")
        points = []
        for row in subset.itertuples(index=False):
            x = x0 + float(row.mean_predicted) * plot_width
            y = 330 - float(row.observed_rate) * 240
            points.append(f"{x:.1f},{y:.1f}")
            radius = 3.0 + min(4.0, np.log10(max(1, int(row.rows))) / 2)
            parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{radius:.1f}' fill='#136f83'/>")
        if len(points) > 1:
            parts.append(f"<polyline points='{' '.join(points)}' fill='none' stroke='#136f83' stroke-width='2'/>")
    parts.append("<text x='640' y='382' text-anchor='middle' font-size='11' fill='#526b79'>Mean predicted probability</text>")
    parts.append("<text x='14' y='210' transform='rotate(-90 14 210)' text-anchor='middle' font-size='11' fill='#526b79'>Observed rate</text>")
    parts.append("<text x='640' y='405' text-anchor='middle' font-size='9' fill='#526b79'>Dot size reflects rows; dashed line is perfect calibration.</text></svg>")
    path.write_text("".join(parts))


def chart_example_svg(path: Path, event: pd.Series, source: pd.DataFrame,
                      feature: pd.DataFrame, caption: str):
    start = event.forecast_ts
    index = int(source.ts_event.searchsorted(start))
    future = source.iloc[index:index + 30]
    closes = future.close.to_numpy(dtype=float) * SCALE
    day_low, day_high = _dynamic_zones(feature, future, "globex", float(event.tick))
    session_low, session_high = _dynamic_zones(feature, future, event.session_anchor, float(event.tick))
    day_curve = (day_low + day_high) / 2
    session_curve = (session_low + session_high) / 2
    values = np.concatenate([closes, day_curve, session_curve,
                             [event.day_target_unadjusted, event.session_target_unadjusted]])
    lower, upper = float(np.nanmin(values)), float(np.nanmax(values))
    pad = max(float(event.tick) * 3, (upper - lower) * .08)
    lower, upper = lower - pad, upper + pad
    width, height = 960, 360
    x = lambda i: 60 + i * 840 / 29
    y = lambda value: 300 - (value - lower) * 230 / (upper - lower)
    poly = lambda array: " ".join(f"{x(i):.1f},{y(value):.1f}" for i, value in enumerate(array))
    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
             f"<rect width='{width}' height='{height}' fill='white'/><text x='480' y='24' text-anchor='middle' font-size='16' fill='#103a50'>{escape(caption)}</text>"]
    for target, color, label in ((event.day_target_unadjusted, "#136f83", "frozen day"),
                                 (event.session_target_unadjusted, "#e4a348", "frozen session")):
        parts.append(f"<line x1='60' y1='{y(target):.1f}' x2='900' y2='{y(target):.1f}' stroke='{color}' stroke-dasharray='6 4'/><text x='905' y='{y(target) + 4:.1f}' font-size='10' fill='{color}'>{label}</text>")
    parts.extend([
        f"<polyline points='{poly(day_curve)}' fill='none' stroke='#136f83' stroke-width='2'/>",
        f"<polyline points='{poly(session_curve)}' fill='none' stroke='#e4a348' stroke-width='2'/>",
        f"<polyline points='{poly(closes)}' fill='none' stroke='#172a36' stroke-width='2'/>",
        "<text x='60' y='326' font-size='10' fill='#526b79'>forecast</text>",
        "<text x='900' y='326' text-anchor='end' font-size='10' fill='#526b79'>30m deadline</text>",
        f"<text x='60' y='344' font-size='10' fill='#526b79'>{escape(str(event.event_id))} · RETROSPECTIVE · {escape(str(event.frozen_outcome))}</text>",
        "</svg>",
    ])
    path.write_text("".join(parts))


def plot_all(stage: Path, root: Path, tables: dict[str, pd.DataFrame]) -> list[str]:
    figures = stage / "figures"
    figures.mkdir(exist_ok=True)
    a = tables["a"]
    elapsed_order = ["<20", "20-39", "40-59", "60-119", "120-239", "240+"]
    distance_order = ["<0.75", "0.75-1.25", "1.25-2", "2+"]
    panels = []
    for product in PRODUCTS:
        subset = a[(a["product"] == product) & (a.facet == "distance_x_elapsed")]
        series = []
        for distance in distance_order:
            values = []
            for elapsed in elapsed_order:
                row = subset[subset.facet_value == f"{distance}|{elapsed}"]
                values.append(None if row.empty else float(row.probability.iloc[0]))
            series.append((distance, values))
        panels.append((product, series))
    line_svg(figures / "remaining-return-by-elapsed.svg",
             "Frozen VWAP return within 30m by elapsed survival and current distance · pooled anchors",
             panels, elapsed_order)

    for key, title, labels, filename in (
        ("b", "Return versus further 0.5-sigma extension", ["return", "extension", "neither", "ambiguous"], "return-versus-extension.svg"),
        ("c", "Day VWAP versus session-VWAP reclaim", ["day", "session", "neither", "ambiguous"], "day-session-corridor.svg"),
    ):
        table = tables[key]
        classes = (["return_first", "extension_first", "neither", "ambiguous"] if key == "b"
                   else ["day_first", "session_first", "neither", "ambiguous"])
        data = []
        for product in PRODUCTS:
            values = []
            for name in classes:
                row = table[(table["product"] == product) & (table.anchor == "ALL") &
                            (table.split == "all") & (table.facet == "overall") &
                            (table.outcome_class == name)].iloc[0]
                values.append(float(row.probability))
            data.append((product, values))
        stacked_svg(figures / filename, title, data, labels)

    calibration_svg(figures / "calibration.svg", tables["calibration"])

    corridor = tables["c"]
    for facet, order, title, filename in (
        ("position_bin", ["day_quarter", "day_middle", "session_middle", "session_quarter"],
         "Day-VWAP-first probability by starting corridor position",
         "corridor-by-position.svg"),
        ("width_bin", ["0.25-0.5", "0.5-0.75", "0.75-1", "1+"],
         "Day-VWAP-first probability by corridor width (day sigma)",
         "corridor-by-width.svg"),
    ):
        panels = []
        for product in PRODUCTS:
            subset = corridor[(corridor["product"] == product) & (corridor.anchor == "ALL") &
                              (corridor.split == "all") & (corridor.facet == facet) &
                              (corridor.outcome_class == "day_first")]
            values = []
            for value in order:
                row = subset[subset.facet_value == value]
                values.append(None if row.empty else float(row.probability.iloc[0]))
            panels.append((product, [("day first", values)]))
        line_svg(figures / filename, title, panels, order)

    timing = tables["timing"]
    resolved = timing[(timing["product"] != "ALL") & timing.outcome_class.isin(
        ["return_first", "extension_first", "day_first", "session_first"])]
    panels = []
    for domain in ("B", "C"):
        series = []
        for outcome, part in resolved[resolved.domain == domain].groupby("outcome_class"):
            values = [float(part[part["product"] == product].first_event_minute_median.iloc[0]) / 30
                      if not part[part["product"] == product].empty else None for product in PRODUCTS]
            series.append((outcome, values))
        panels.append((domain, series))
    line_svg(figures / "time-to-event.svg", "Median first resolved minute (fraction of 30m horizon)",
             panels, list(PRODUCTS), ylabel="Fraction of horizon")

    examples = tables["examples"]
    event_paths = []
    desired = [("day_first", "success"), ("session_first", "failure")]
    third = "neither" if (examples.outcome == "neither").any() else "ambiguous"
    desired.append((third, "unresolved" if third == "neither" else "ambiguous"))
    for outcome, label in desired:
        choice = examples[(examples.domain == "C") & (examples.outcome == outcome)].sort_values("forecast_ts").iloc[0]
        event_file = stage / "events" / choice.source_partition
        event = pd.read_parquet(event_file)
        event = event[event.event_id == choice.event_id].iloc[0]
        source = load_source_year(root, event["product"], int(event.year))
        source = source[source.session_date.astype(str) == event.session_date].reset_index(drop=True)
        feature = load_features(root, event["product"], int(event.year), event.timeframe)
        feature = feature[feature.session_date.astype(str) == event.session_date].reset_index(drop=True)
        filename = f"chart-example-{label}.svg"
        caption = f"{label.title()} example · {event['product']} {event.session_date} {event.session_anchor} · {event.frozen_outcome}"
        chart_example_svg(figures / filename, event, source, feature, caption)
        event_paths.append(filename)
    return event_paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    stage = workspace / "work/11_vwap_conditional_probabilities" / args.run_id
    root = load_workspace_paths(workspace).publication_root
    tables_dir = stage / "tables"
    read = lambda name: pd.read_csv(tables_dir / f"{name}.csv")
    tables = {
        "atlas": read("probability_atlas"), "a": read("question_a_rates"),
        "b": read("question_b_outcomes"), "c": read("question_c_outcomes"),
        "scores": read("model_scores"), "calibration": read("calibration"),
        "timing": read("timing_movements"), "sensitivity": read("timeframe_sensitivity"),
        "updates": read("updated_corridor"), "examples": read("examples"),
        "geometry": read("barrier_geometry"), "funnel": read("funnel"),
    }
    example_figures = plot_all(stage, root, tables)
    atlas, a, b, c, scores = (tables[name] for name in ("atlas", "a", "b", "c", "scores"))

    def overall_a(product, metric="frozen_return_30"):
        return a[(a["product"] == product) & (a.anchor == "ALL") & (a.split == "all") &
                 (a.facet == "overall") & (a.metric == metric)].iloc[0]

    def overall_class(table, product, outcome):
        return table[(table["product"] == product) & (table.anchor == "ALL") &
                     (table.split == "all") & (table.facet == "overall") &
                     (table.outcome_class == outcome)].iloc[0]

    d = Document()
    d.heading("VWAP conditional probabilities", 1)
    d.para(f"Run {args.run_id} · frozen protocol 1.0.0 · pinned session_anchored_vwap 1.0.0. The primary population uses two-minute features and unadjusted one-minute future paths; five-minute calculations are a correlated sensitivity. All historical periods are exploratory because earlier VWAP outcomes were already viewed. These are conditional price-path probabilities, not trading win rates or profitability claims.")
    d.heading("Executive interpretation")
    atlas_rows = []
    for _, row in atlas.iterrows():
        atlas_rows.append([row.question, row["product"], row.future_event,
                           f"{int(row.numerator):,}/{int(row.denominator):,}", pct(row.probability), ci(row),
                           f"{int(row.episodes):,}", f"{int(row.product_sessions):,}"])
    d.table(["Question", "Product", "Future event", "Numerator/denominator", "Rate", "95% shared-week CI", "Episodes/events", "Product-sessions"], atlas_rows)
    d.para("The useful chart candidates are the directly measured, deadline-specific event probabilities with adequate support: remaining 30-minute frozen-return probability, the full four-class return/extension race, and the full four-class day/session corridor race. Pooled rows are descriptive only; chart lookup must remain product-specific. Added path conditions are judged by chronological Brier score below, not by whichever historical cell has the highest rate.")

    d.heading("Question A — remaining probability of returning to VWAP")
    a_rows = []
    for product in PRODUCTS:
        frozen = overall_a(product)
        evolving = overall_a(product, "evolving_return_30")
        contribution = overall_a(product, "evolving_without_frozen_30")
        deadline = overall_a(product, "frozen_return_window")
        a_rows.append([product, pct(frozen.probability), ci(frozen), pct(evolving.probability),
                       pct(contribution.probability), pct(deadline.probability),
                       f"{int(frozen.episodes):,}", f"{int(frozen.denominator):,}"])
    d.table(["Product", "Frozen return ≤30m", "95% CI", "Evolving return ≤30m",
             "Evolving-only ≤30m", "Frozen by window end", "Episodes", "Checkpoint rows"], a_rows)
    d.para("Each row is conditional on a fresh departure episode still surviving under the causal evolving-VWAP definition at a regular checkpoint. The window-end rate uses the same 30-minute-capable checkpoint cohort but a longer, variable deadline. Evolving-only contact quantifies how often reference movement changes the answer without price reaching the checkpoint-frozen level.")
    d.image("figures/remaining-return-by-elapsed.svg",
            "Remaining frozen-return probability versus elapsed survival within fixed current-distance bins; anchors are pooled only for this secondary visualization.")

    d.heading("Question B — frozen VWAP return versus further extension")
    b_rows = []
    for product in PRODUCTS:
        values = [overall_class(b, product, name) for name in
                  ("return_first", "extension_first", "neither", "ambiguous")]
        geometry = tables["geometry"][tables["geometry"]["product"] == product].iloc[0]
        b_rows.append([product, *(pct(value.probability) for value in values),
                       f"{geometry.return_distance_points_median:.2f} / {geometry.return_distance_ticks_median:.0f} / {geometry.return_distance_sigma_median:.2f}",
                       f"{geometry.extension_distance_points_median:.2f} / {geometry.extension_distance_ticks_median:.0f} / {geometry.extension_distance_sigma_median:.2f}",
                       f"{int(values[0].denominator):,}"])
    d.table(["Product", "Return first", "Extension first", "Neither", "Ambiguous",
             "Median return distance, points / ticks / sigma",
             "Median extension distance, points / ticks / sigma", "Rows"], b_rows)
    d.para("The return and extension barriers are unequal, so 50% is not a neutral benchmark. Opening gaps are assigned to the crossed destination and flagged; a one-minute bar touching both destinations remains ambiguous. Full-horizon favorable/adverse movement and target-conditional timing are saved separately in timing_movements.csv.")
    d.image("figures/return-versus-extension.svg", "Exhaustive return-versus-extension outcomes by product.")
    d.image("figures/time-to-event.svg", "Median time to first resolved destination; unresolved rows remain outside the conditional timing median.")

    d.heading("Question C — day VWAP versus active-session VWAP")
    c_rows = []
    for product in PRODUCTS:
        values = [overall_class(c, product, name) for name in
                  ("day_first", "session_first", "neither", "ambiguous")]
        c_rows.append([product, *(pct(value.probability) for value in values),
                       f"{int(values[0].episodes):,}", f"{int(values[0].product_sessions):,}"])
    d.table(["Product", "Day VWAP first", "Session reclaim first", "Neither", "Ambiguous",
             "Events", "Product-sessions"], c_rows)
    d.para("Events require a completed-close session-VWAP failure, both anchors mature, price strictly between rounded destination zones, at least eight ticks and 0.25 day sigma of separation, and full 30-minute capacity. The fixed 30-minute lockout suppressed repeated crossings without consulting future outcomes. Position and corridor width are baseline geometry, not evidence of VWAP attraction by themselves.")
    d.image("figures/day-session-corridor.svg", "Exhaustive frozen day/session corridor outcomes by product.")
    d.image("figures/corridor-by-position.svg",
            "Day-VWAP-first probability versus starting location; the nearer boundary is baseline geometry, not attraction.")
    d.image("figures/corridor-by-width.svg",
            "Day-VWAP-first probability versus day-sigma corridor separation; product panels remain separate.")
    updates = tables["updates"]
    update_rows = []
    for elapsed in (10, 20):
        for product in PRODUCTS:
            row = updates[(updates["product"] == product) & (updates.anchor == "ALL") &
                          (updates.elapsed_minutes == elapsed) & (updates.facet == "overall") &
                          (updates.outcome_class == "day_first")].iloc[0]
            update_rows.append([f"{elapsed}m", product, pct(row.probability), ci(row),
                                f"{int(row.denominator):,}"])
    d.table(["Unresolved checkpoint", "Product", "Day first by original deadline", "95% CI", "Still-at-risk rows"], update_rows)
    d.para("These update rows are measured only among events unresolved at 10 or 20 minutes, with the original frozen targets and original 30-minute deadline. They are not the event-time frequency reused as an update.")

    d.heading("Incremental prediction beyond geometry and clock")
    score_rows = []
    for question in ("A", "B", "C"):
        row = scores[(scores.question == question) & (scores.split == "evaluation") &
                     (scores["product"] == "ALL")].iloc[0]
        score_rows.append([question, f"{row.baseline_brier:.4f}", f"{row.augmented_brier:.4f}",
                           f"{row.brier_difference:+.4f}",
                           f"{row.difference_ci_low:+.4f} to {row.difference_ci_high:+.4f}",
                           pct(row.specific_augmented_coverage), brier_reading(row)])
    d.table(["Question", "Baseline Brier", "Augmented Brier", "Δ augmented−baseline",
             "95% shared-week CI", "Specific-context coverage", "Interpretation"], score_rows)
    d.para("Every prediction was learned only from development dates. The baseline uses geometry, product/anchor, clock, time remaining, anchor age where applicable, and prior-only volatility. Added A/B context is elapsed survival, residence/slope class, and observed maximum excursion; added C context is prior hold, slope agreement, and corridor trend. Cells below 100 development observations fall back to the baseline. No three-question familywise superiority claim is made.")
    d.image("figures/calibration.svg", "Observed event rates across augmented-model evaluation probability bins.")

    d.heading("Chronology, five-minute sensitivity, and coverage")
    sensitivity = tables["sensitivity"]
    sens_rows = []
    for product in PRODUCTS:
        values = []
        for timeframe in ("2m", "5m"):
            a_rate = sensitivity[(sensitivity.timeframe == timeframe) & (sensitivity["product"] == product) &
                                 (sensitivity.metric == "A_frozen_return_30")].iloc[0]
            b_rate = sensitivity[(sensitivity.timeframe == timeframe) & (sensitivity["product"] == product) &
                                 (sensitivity.metric == "B_return_first")].iloc[0]
            c_rate = sensitivity[(sensitivity.timeframe == timeframe) & (sensitivity["product"] == product) &
                                 (sensitivity.metric == "C_day_first")].iloc[0]
            values.extend([pct(a_rate.probability), pct(b_rate.probability), pct(c_rate.probability)])
        sens_rows.append([product, *values])
    d.table(["Product", "A 2m", "B 2m", "C 2m", "A 5m", "B 5m", "C 5m"], sens_rows)
    d.para("Two- and five-minute views are independent calculations of the same underlying market history, not independent samples. ES/NQ cover eligible dates from 2021-06-28 through 2026-09-18; GC covers 2016-02-11 through 2026-09-18 with discontinuous eligible coverage. The release contributes 3,039 retrospectively complete product-days. All current dates are exploratory; 2024 and 2025–2026 are chronological diagnostics only.")
    funnel = tables["funnel"]
    coverage_rows = []
    for domain in ("AB", "C"):
        for product in PRODUCTS:
            row = funnel[(funnel.domain == domain) & (funnel.timeframe == "2m") &
                         (funnel["product"] == product)].iloc[0]
            coverage_rows.append([domain, product, f"{int(row.rows):,}",
                                  f"{int(row.outcome_capable):,}",
                                  f"{int(row.outcome_unavailable):,}",
                                  f"{int(row.episodes_or_events):,}",
                                  f"{int(row.product_sessions):,}"])
    d.table(["Population", "Product", "Constructed rows", "Outcome-capable",
             "Unavailable", "Episodes/events", "Product-sessions"], coverage_rows)
    d.para("The 21 unavailable primary A/B rows placed the checkpoint close inside its tick-rounded return zone and remain null rather than observed failures. All selected primary corridor events had complete future evidence. Feature-gate counts and all threshold alternatives are retained in the feasibility and corridor-support artifacts.")

    d.heading("Mechanically selected chart examples")
    for filename, caption in zip(example_figures, ("Earliest day-VWAP-first event", "Earliest session-reclaim-first event", "Earliest unresolved or ambiguous event")):
        d.image(f"figures/{filename}", caption + "; targets and paths are retrospective and percentages are not overlaid.")
    d.para("Examples are selected by earliest forecast timestamp within their outcome class, not for visual attractiveness. Solid curves are causal evolving VWAPs; dashed lines are event-time frozen destinations. The examples illustrate state handling, not representative profitability.")

    d.heading("Limitations and chart decision")
    d.para("Checkpoint rows within an episode, anchors on the same product-day, products on a shared week, and the two timeframes are dependent. Week-block intervals preserve those rows together but do not eliminate observational confounding. Complete-day eligibility is retrospective. One-minute OHLC cannot order two intraminute touches, so ambiguity is retained. Price references are translated to unadjusted contract coordinates, but no fills, costs, latency, overlap policy, sizing, stop, or P&L are modeled.")
    d.para("A future chart may show only product-specific estimates with adequate development support, explicit forecast time/deadline, all competing outcome probabilities including unresolved/ambiguous mass, and hoverable numerator/denominator/interval/baseline/history. Sparse or unavailable states should show no percentage. Conditions whose evaluation Brier score fails to improve geometry should be omitted from the default state panel even if a raw subgroup rate looks attractive.")
    d.links([("Protocol", "protocol-1.0.0.md"), ("Probability atlas", "tables/probability_atlas.csv"),
             ("Model scores", "tables/model_scores.csv"), ("Calibration", "tables/calibration.csv"),
             ("Examples", "tables/examples.csv"), ("Event manifest", "events.manifest.json"),
             ("Chart-display specification", "chart-display-spec.md"), ("Run manifest", "manifest.json")])
    d.write(stage)

    evaluation = {row.question: row for _, row in scores[(scores.split == "evaluation") &
                                                          (scores["product"] == "ALL")].iterrows()}
    advice = f"""# VWAP conditional-probability advice — 2026-09-24

Status: exploratory conditional-behavior evidence. No current date is a pristine holdout; no trade execution or profitability conclusion is authorized.

## Retain for a chart prototype

Retain the product-specific, deadline-explicit raw probabilities for A, B, and C when support is adequate. They directly answer observable path questions and preserve unresolved/ambiguous mass. The product-level estimates and shared-week intervals are in `tables/probability_atlas.csv`; detailed clock, distance, geometry, and session populations are in the three question tables.

Question A's evolving-only rate must accompany any evolving-VWAP label so users can see how often the reference moved into contact without price reaching the frozen checkpoint level. Question B must show both actual distances because its unequal barriers make 50% meaningless. Question C must show corridor position/width and the geometry baseline; a nearer boundary winning more often is not evidence of attraction.

## Added context decision

- A: {brier_reading(evaluation['A'])} on the combined 2024–2026 chronological evaluation; specific added-context cells covered {pct(evaluation['A'].specific_augmented_coverage)} of rows.
- B: {brier_reading(evaluation['B'])}; specific added-context cells covered {pct(evaluation['B'].specific_augmented_coverage)}.
- C: {brier_reading(evaluation['C'])}; specific added-context cells covered {pct(evaluation['C'].specific_augmented_coverage)}.

Only context that improves earlier-history probability error with useful coverage should enter a default panel. Otherwise use the geometry/clock estimate and leave the attractive raw subgroup in the research report.

## Omit or keep exploratory

Do not display pooled cross-product probabilities, sparse fine-grid cells, a binary winner with neither/ambiguous discarded, or a return rate without its deadline/reference. Do not translate any target-event probability into a trading win rate. The five-minute view is sensitivity, not confirmation. Later genuinely uninspected data should record forecasts at the timestamp and test calibration without rewriting prior values.
"""
    (stage / "advice.md").write_text(advice)

    spec = f"""# Future TradingView chart-display specification

This is a specification only. No Pine indicator was created or modified.

## Visual hierarchy

- Draw day (Globex) VWAP and the currently active Asia, London, or NY VWAP as the two main evolving curves. Suppress a local curve outside its published membership or before maturity.
- Draw at most two active frozen destination levels. A/B uses checkpoint-frozen VWAP and the frozen 0.5-sigma extension. C uses event-time frozen day VWAP and session VWAP. Frozen levels must use a different dash style from evolving curves.
- Put labels at the common deadline edge, not indefinitely into the future. Never move a frozen target after forecast creation.

## Compact current-state panel

Show product, anchor/session, forecast timestamp, deadline, elapsed episode/event time, current distance, target distances in ticks/points/sigma, support, and the product-specific outcome vector. A shows frozen-return, no-return, and separately evolving-only contact. B and C show all four mutually exclusive classes, including neither and ambiguous. Percentages must sum to the displayed cohort definition, not to an edited winner-only subset.

Label the estimate `event-time` at departure/corridor creation and `updated conditional` at later ten-minute checkpoints. The update must identify its smaller still-at-risk denominator and original deadline. Historical event-time values remain frozen in replay; later updates append records rather than rewriting them.

## State transitions

- `ACTIVE`: forecast created from completed, available bars; targets and deadline visible.
- `REACHED — DAY/RETURN/EXTENSION/SESSION`: first destination and first-event time retained; fade the reached line but do not replace the original percentage.
- `AMBIGUOUS`: both destinations touched in one one-minute bar; show neither as winner.
- `EXPIRED — NEITHER`: deadline passed with neither destination.
- `UNAVAILABLE`: immature anchor, missing context/path, contract change, clock gap, insufficient horizon, or sparse estimator support. Show the reason, not 0%.

## Hover details

Each probability exposes population, condition, future event, horizon, numerator/denominator, distinct episodes/events, product-sessions, shared weeks, 95% interval, geometry baseline, Brier comparison, chronological rates, release/version, and history cutoff. A hover names frozen versus causal-evolving contact. B hover lists both unequal distances. C hover lists corridor position, width, orientation, session, and the eight-tick/0.25-day-sigma gate.

Do not show an augmented-context value when its development cell has fewer than 100 observations; fall back visibly to the geometry baseline. Before anchor age 30 minutes, suppress all estimates. Before anchor age 60 minutes, path/slope context is unavailable and cannot be inferred from later history.

## Historical examples

The mechanically selected retrospective examples are `figures/{example_figures[0]}`, `figures/{example_figures[1]}`, and `figures/{example_figures[2]}`. They illustrate reached, failed/reclaimed, and unresolved/ambiguous handling using actual computed targets and paths. They are not curated trade examples and contain no invented percentages.

## Research and replay integrity

Persist forecast timestamp, deadline, frozen prices, outcome vector, support/interval/baseline, model version, and eventual state. Evolving curves may continue to update causally, but prior forecasts and frozen targets must never be recalculated from later bars or backward-adjustment changes. Mark all current historical overlays `RETROSPECTIVE`; these dates are exploratory and the estimates are conditional event frequencies, not trade win rates.
"""
    (stage / "chart-display-spec.md").write_text(spec)
    print(json.dumps({"figures": len(list((stage / "figures").glob("*.svg"))),
                      "report": str(stage / "report.md"),
                      "chart_spec": str(stage / "chart-display-spec.md")}))


if __name__ == "__main__":
    main()
