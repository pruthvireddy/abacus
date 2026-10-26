"""Run the frozen Range XV study into a new, unsealed work directory."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil

import pandas as pd

from src.engine import (PRIMARY, barrier_bounds, digest, extract_product, load_chart,
                        summarize_events, verify_inputs)


def csv_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.6f")


def markdown_table(frame: pd.DataFrame) -> str:
    def cell(value: object) -> str:
        if pd.isna(value):
            return "—"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value).replace("|", "\\|")
    headers = [str(x) for x in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in frame.itertuples(index=False, name=None))
    return "\n".join(lines)


def html_table(frame: pd.DataFrame) -> str:
    return frame.to_html(index=False, border=0, classes="results", na_rep="—", escape=True,
                         float_format=lambda x: f"{x:.3f}")


def fmt_view(frame: pd.DataFrame) -> pd.DataFrame:
    wanted = ["product", "idea", "cohort", "split", "opportunities", "trades", "sessions",
              "mean_ticks", "mean_net_2_ticks", "p05_ticks", "break_even_cost_ticks_per_trade"]
    return frame[wanted].copy()


def make_figure(summary: pd.DataFrame, path: Path) -> None:
    rows = []
    for product in ("ES", "NQ", "GC"):
        for idea in PRIMARY:
            cohort = PRIMARY[idea][0]
            row = summary.query("product == @product and idea == @idea and cohort == @cohort and split == 'all'")
            if len(row):
                rows.append((f"{product} {idea.replace('_', ' ')}", float(row.iloc[0]["mean_net_2_ticks"])))
    width, height, zero, scale = 900, 440, 480, 22
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Two tick cost screen by asset and idea">',
             '<rect width="100%" height="100%" fill="#fcfcfa"/>',
             '<text x="25" y="32" font-size="19" font-family="sans-serif" fill="#14202b">Mean return after 2-tick cost · ticks/opportunity</text>',
             f'<line x1="{zero}" y1="50" x2="{zero}" y2="420" stroke="#222"/>']
    for i, (label, value) in enumerate(rows):
        y = 70 + 39 * i
        end = zero + scale * value
        x = min(zero, end)
        w = max(1, abs(end - zero))
        color = "#087c67" if value >= 0 else "#b2473e"
        parts.extend([f'<text x="25" y="{y+16}" font-size="14" font-family="sans-serif">{escape(label)}</text>',
                      f'<rect x="{x:.2f}" y="{y}" width="{w:.2f}" height="21" fill="{color}"/>',
                      f'<text x="{max(600,end+8):.2f}" y="{y+16}" font-size="13" font-family="sans-serif">{value:.2f}</text>'])
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id.replace("_", "").replace("-", "").isalnum():
        raise ValueError("run ID must use letters, digits, underscores, or hyphens")
    root = Path(__file__).resolve().parents[2]
    study = Path(__file__).resolve().parent
    stage = root / "work" / study.name / args.run_id
    if stage.exists() or (root / "runs" / study.name / args.run_id).exists():
        raise FileExistsError(stage)
    protocol = json.loads((study / "protocol-1.0.1.json").read_text())
    lock = json.loads((study / "inputs.lock.json").read_text())
    verified = verify_inputs(root, lock)
    stage.mkdir(parents=True)
    (stage / "tables").mkdir()
    (stage / "figures").mkdir()
    shutil.copy2(study / "protocol-1.0.1.json", stage)
    shutil.copy2(study / "inputs.lock.json", stage)
    (stage / "input-verification.json").write_text(json.dumps(verified, indent=2) + "\n")
    audits = []
    for record in lock["files"]:
        if record.get("primary"):
            print(f"extracting {record['product']}...", flush=True)
            audits.append(extract_product(root, record, protocol, stage))
    (stage / "extraction-audit.json").write_text(json.dumps(audits, indent=2) + "\n")
    events = pd.concat([pd.read_parquet(stage / f"events_{product}.parquet") for product in protocol["primary_charts"]], ignore_index=True)
    secondary = pd.concat([pd.read_parquet(stage / f"secondary_{product}.parquet") for product in protocol["primary_charts"]], ignore_index=True)
    summary, contrast, metrics = summarize_events(events, protocol)
    csv_table(summary, stage / "tables/primary_summary.csv")
    csv_table(contrast, stage / "tables/primary_contrasts.csv")
    secondary["net_2_ticks"] = secondary["return_ticks"] - 2 * secondary["traded"].astype(int)
    secondary_summary = secondary.groupby(["product", "idea", "cohort", "horizon_bars", "split"], dropna=False).agg(
        opportunities=("return_ticks", "size"), trades=("traded", "sum"), sessions=("session_date", "nunique"),
        mean_ticks=("return_ticks", "mean"), p05_ticks=("return_ticks", lambda x: x.quantile(.05)),
        mean_adverse_ticks=("adverse_ticks", "mean"), mean_net_2_ticks=("net_2_ticks", "mean")).reset_index()
    csv_table(secondary_summary, stage / "tables/secondary_horizons.csv")
    subgroup_rows = []
    for key, group in events.groupby(["product", "idea", "cohort"]):
        declared_masks = [
            ("export_clock_0930_1030", group["opening_hour"]),
            ("strong_body_small_adverse_wick",
             (group["body_fraction"] >= protocol["idea_1"]["quality_body_min"]) &
             (group["adverse_wick_fraction"] < protocol["idea_1"]["quality_adverse_wick_max"])),
        ]
        for name, mask in declared_masks:
            if name.startswith("strong") and key[1] != "pullback":
                continue
            part = group.loc[mask]
            subgroup_rows.append({"product": key[0], "idea": key[1], "cohort": key[2], "subgroup": name,
                                  "opportunities": len(part), "sessions": part["session_date"].nunique(),
                                  "mean_ticks": part["return_ticks"].mean() if len(part) else None,
                                  "mean_net_2_ticks": (part["return_ticks"] - 2 * part["traded"].astype(int)).mean() if len(part) else None,
                                  "p05_ticks": part["return_ticks"].quantile(.05) if len(part) else None})
    subgroups = pd.DataFrame(subgroup_rows)
    csv_table(subgroups, stage / "tables/declared_subgroups.csv")
    bounds = []
    for record in lock["files"]:
        if record.get("primary"):
            product = record["product"]
            chart = protocol["primary_charts"][product]
            data = load_chart(root / record["path"], chart["tick_size"], protocol["excluded_partial_session"])
            bounds.append(barrier_bounds(events.loc[events["product"] == product], data, chart["setting"],
                                         protocol["stop_target_diagnostic"]["stop_units"]))
    bounds_frame = pd.concat(bounds, ignore_index=True)
    csv_table(bounds_frame, stage / "tables/stop_target_bounds.csv")
    metrics["event_rows"] = len(events)
    metrics["secondary_event_rows"] = len(secondary)
    metrics["run_id"] = args.run_id
    metrics["computed_utc"] = datetime.now(timezone.utc).isoformat()
    (stage / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    make_figure(summary, stage / "figures/two_tick_cost_screen.svg")
    all_rows = fmt_view(summary.loc[summary["split"] == "all"])
    screen = pd.DataFrame(metrics["candidate_screens"])
    passing_count = int(screen["provisional_candidate"].sum())
    contrast_all = contrast.loc[contrast["split"] == "all", ["product", "idea", "gross_difference_ticks", "difference_ticks", "lower", "upper", "n_sessions"]]
    report = f"""# Range XV edge candidates — {args.run_id}

Computed {metrics['computed_utc']}. Chart-price research on the seven pinned ATAS exports; three primary charts. All calendar blocks were previously inspected by earlier studies, so the last block is retrospective.

**Result: {passing_count} of 9 primary idea-by-asset comparisons pass the declared candidate screen.** The development block calibrates the quiet-period threshold and is in-sample. The later blocks use that prior calibration, but were already viewed in earlier research.

## Primary results

One- or three-future-bar signed open-to-open returns in ticks, using the next bar start as the signal-completion proxy. Net figures deduct two ticks per executed round trip. Wait-policy opportunities that never confirm remain in its denominator with zero return and no cost.

{markdown_table(all_rows)}

## Matched contrasts

The difference is candidate minus control after two ticks per executed trade. Session-cluster bootstrap intervals use 99.44% familywise coverage for the nine primary comparisons. Differing opportunity populations are not causal matches.

The pullback baseline includes the extreme-break candidate, as specified in the original plan. The nonbreak complement is shown as descriptive context; it is much smaller on these Range XV charts.

{markdown_table(contrast_all)}

## Prespecified screen

Requires positive two-tick net return and net contrast in validation and final blocks, positive two-tick return after removing the most profitable 1% of sessions, and a positive familywise lower interval.

{markdown_table(screen)}

## Supporting evidence

- `tables/primary_summary.csv`: chronological blocks, 1/2/4-tick cost sensitivities, delay sensitivity, lower tail, loss rates, adverse movement, cost break-even, and session concentration.
- `tables/secondary_horizons.csv`: declared one-, three-, and five-bar horizons where applicable.
- `tables/declared_subgroups.csv`: signal body/wick subgroup and 09:30–10:30 **export-clock** subgroup; export timezone is unverified.
- `tables/stop_target_bounds.csv`: stop-first and target-first bounds for bars touching both, with arbitrary chart-unit barriers.
- `events_*.parquet` and `secondary_*.parquet`: event ledgers; `extraction-audit.json`: raw and accepted counts plus incomplete-horizon exclusions.

## Interpretation limits

No exact completion timestamps, verified timezone, bid/ask, fill sequence, or intrabar event order are available. The next bar's start is only a completion proxy, and opens are chart-price references. These outputs cannot establish a sustainable executable edge. Fresh unseen exports and fill-level verification are required for that claim.
"""
    (stage / "report.md").write_text(report)
    sections = [("Primary results", all_rows), ("Matched net contrasts", contrast_all),
                ("Prespecified screen", screen), ("Stop/target bounds", bounds_frame)]
    html = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>Range XV edge candidates</title>",
            "<style>body{font:16px system-ui;margin:2rem auto;max-width:1100px;color:#16202a;background:#fcfcfa}table{border-collapse:collapse;display:block;overflow-x:auto;font-size:13px;margin:1.2rem 0}td,th{padding:7px 9px;border-bottom:1px solid #ddd;text-align:right;white-space:nowrap}th{background:#eaf0ef}h1,h2{color:#163d44}p{line-height:1.5}img{max-width:100%}</style>",
            f"<h1>Range XV edge candidates</h1><p>Run {escape(args.run_id)} · chart-price research · export timezone unverified.</p>",
            f"<p><strong>Result: {passing_count} of 9 primary comparisons pass the declared candidate screen.</strong> All calendar blocks were previously inspected; the development block also calibrates the quiet-period threshold.</p>",
            "<p>Full observed sessions are primary. The three primary charts are ES 6RXV, NQ 20RXV, and GC 20RXV. Net returns include a two-tick round-trip cost screen.</p>",
            "<img src='figures/two_tick_cost_screen.svg' alt='Mean return after two-tick cost by product and idea'>"]
    for title, frame in sections:
        html.extend([f"<h2>{escape(title)}</h2>", html_table(frame)])
    html.append("<p>See <a href='report.md'>report.md</a>, tables, and event ledgers for timing, tails, split results, and limitations.</p></html>")
    (stage / "report.html").write_text("\n".join(html) + "\n")
    passing = screen.loc[screen["provisional_candidate"]]
    passed = ", ".join(f"{r.product} {r.idea}" for r in passing.itertuples(index=False)) or "None"
    advice = f"# Advice as of {datetime.now(timezone.utc).date()}\n\nProvisional candidates under the frozen chart-price screen: **{passed}**.\n\nSee [primary metrics](tables/primary_summary.csv), [contrasts](tables/primary_contrasts.csv), and [candidate screens](metrics.json). Any passing row remains exploratory because earlier studies inspected these dates, and the exports lack fill and completion-time evidence. Do not present it as a sustainable trading edge.\n"
    (stage / "advice.md").write_text(advice)
    print(stage)


if __name__ == "__main__":
    main()
