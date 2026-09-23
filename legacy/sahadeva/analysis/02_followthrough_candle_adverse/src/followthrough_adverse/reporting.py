from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


COLORS = {4: "#005f73", 5: "#ca6702", 6: "#9b2226", 10: "#0a9396", 20: "#bb3e03"}


def _pct(value: Any) -> str:
    return "—" if pd.isna(value) else f"{100 * float(value):.2f}%"


def _num(value: Any, digits: int = 2) -> str:
    return "—" if pd.isna(value) else f"{float(value):,.{digits}f}"


def headline_table(summary: pd.DataFrame) -> pd.DataFrame:
    return summary.loc[
        summary["period"].eq("full")
        & summary["direction"].eq("all")
        & summary["prior_run_minimum"].eq(1)
    ].sort_values(["asset", "range_setting"]).reset_index(drop=True)


def _markdown_headline(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Reversals | Same-direction second candle | Conditional rate | Mean adverse ticks (95% block CI) | Median | p90 | Mean adverse price | Mean adverse gross $ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        chart = f"{row.asset} R{int(row.range_setting)}"
        lines.append(
            f"| {chart} | {int(row.total_reversals):,} | {int(row.same_direction_next_bar):,} | {_pct(row.same_direction_probability)} | "
            f"{_num(row.mean_adverse_ticks)} ({_num(row.mean_adverse_ci_low_ticks)}–{_num(row.mean_adverse_ci_high_ticks)}) | "
            f"{_num(row.median_adverse_ticks, 1)} | {_num(row.p90_adverse_ticks, 1)} | "
            f"{_num(row.mean_adverse_price)} | ${_num(row.mean_adverse_gross_dollars)} |"
        )
    return "\n".join(lines)


def _markdown_prior_three(frame: pd.DataFrame) -> str:
    prior = frame.loc[
        frame["period"].eq("full")
        & frame["direction"].eq("all")
        & frame["prior_run_minimum"].eq(3)
    ].sort_values(["asset", "range_setting"])
    lines = [
        "| Chart | Same-direction second candles | Conditional rate | Mean adverse ticks (95% block CI) | Median | p90 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in prior.itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.denominator):,} | {_pct(row.same_direction_probability)} | "
            f"{_num(row.mean_adverse_ticks)} ({_num(row.mean_adverse_ci_low_ticks)}–{_num(row.mean_adverse_ci_high_ticks)}) | "
            f"{_num(row.median_adverse_ticks, 1)} | {_num(row.p90_adverse_ticks, 1)} |"
        )
    return "\n".join(lines)


def _markdown_reference_comparison(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Mean adverse from follow-through open | Mean adverse from reversal close | Mean directional opening gap |",
        "|---|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {_num(row.mean_adverse_ticks)} | "
            f"{_num(row.adverse_from_signal_close_mean_ticks)} | {_num(row.directional_open_gap_mean_ticks)} |"
        )
    return "\n".join(lines)


def _markdown_long_short(summary: pd.DataFrame) -> str:
    side = summary.loc[
        summary["period"].eq("full")
        & summary["prior_run_minimum"].eq(1)
        & summary["direction"].isin(["long", "short"])
    ].pivot(index=["asset", "range_setting"], columns="direction", values="mean_adverse_ticks").reset_index()
    lines = ["| Chart | Long/green mean adverse | Short/red mean adverse |", "|---|---:|---:|"]
    for row in side.itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {_num(row.long)} | {_num(row.short)} |"
        )
    return "\n".join(lines)


def _markdown_time_rank_one(rankings: pd.DataFrame) -> str:
    first = rankings.loc[rankings["rank"].eq(1)].copy()
    criteria = [
        ("highest follow-through rate", "Highest rate"),
        ("most frequent", "Most frequent"),
        ("lowest mean adverse", "Lowest adverse"),
        ("highest mean favorable", "Highest favorable"),
        ("largest favorable-minus-adverse", "Largest favorable−adverse"),
        ("most confirmations", "Most confirmations"),
    ]
    lines = [
        "| Chart | Highest follow-through rate | Most frequent by reversal time | Lowest mean adverse | Highest mean favorable | Largest favorable−adverse | Most confirmations by follow-through time |",
        "|---|---|---|---|---|---|---|",
    ]
    for (asset, range_setting), chart in first.groupby(["asset", "range_setting"], observed=True):
        values = {}
        for criterion, label in criteria:
            selected = chart.loc[chart["criterion"].eq(criterion)]
            if selected.empty:
                values[label] = "—"
                continue
            row = selected.iloc[0]
            if criterion == "highest follow-through rate":
                metric = _pct(row["metric_value"])
            else:
                metric = _num(row["metric_value"])
            values[label] = f"{row['half_hour_window']} ({metric})"
        lines.append(
            f"| {asset} R{int(range_setting)} | {values['Highest rate']} | {values['Most frequent']} | "
            f"{values['Lowest adverse']} | {values['Highest favorable']} | {values['Largest favorable−adverse']} | "
            f"{values['Most confirmations']} |"
        )
    return "\n".join(lines)


def _markdown_balanced_windows(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Rank | Raw 30-minute window | Events | Active dates | Follow-through rate | Events/date | Mean adverse | Mean favorable | Favorable−adverse |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.sort_values(["asset", "range_setting", "rank"]).itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.rank)} | {row.half_hour_window} | "
            f"{int(row.conditioned_events):,} | {int(row.active_export_dates)} | {_pct(row.same_direction_probability)} | "
            f"{_num(row.conditioned_events_per_active_date)} | {_num(row.mean_adverse_ticks)} | "
            f"{_num(row.mean_favorable_ticks)} | {_num(row.mean_favorable_minus_adverse_ticks)} |"
        )
    return "\n".join(lines)


def _markdown_hold_summary(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Eligible confirmations | Two-more success | Success rate (95% date-block CI) | Median hold proxy | p75 | p90 | Zero-time share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.strict_eligible):,} | {int(row.strict_success):,} | "
            f"{_pct(row.strict_success_probability)} ({_pct(row.strict_success_ci_low)}–{_pct(row.strict_success_ci_high)}) | "
            f"{_num(row.strict_median_hold_proxy_minutes)} min | {_num(row.strict_p75_hold_proxy_minutes)} | "
            f"{_num(row.strict_p90_hold_proxy_minutes)} | {_pct(row.strict_zero_time_share)} |"
        )
    return "\n".join(lines)


def _markdown_eventual_hold_summary(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Eligible 20-bar windows | Pair found | Probability (95% date-block CI) | Median bars | Median time proxy | p90 time proxy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.eventual_eligible):,} | {int(row.eventual_success):,} | "
            f"{_pct(row.eventual_success_probability)} ({_pct(row.eventual_success_ci_low)}–{_pct(row.eventual_success_ci_high)}) | "
            f"{_num(row.eventual_median_bars_to_target, 1)} | {_num(row.eventual_median_hold_proxy_minutes)} min | "
            f"{_num(row.eventual_p90_hold_proxy_minutes)} min |"
        )
    return "\n".join(lines)


def _markdown_hold_balanced(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Rank | Confirmation raw-clock window | Eligible | Success rate | Median hold proxy | p75 | p90 |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in frame.sort_values(["asset", "range_setting", "rank"]).itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.rank)} | {row.half_hour_window} | "
            f"{int(row.strict_eligible):,} | {_pct(row.strict_success_probability)} | "
            f"{_num(row.strict_median_hold_proxy_minutes)} min | {_num(row.strict_p75_hold_proxy_minutes)} | "
            f"{_num(row.strict_p90_hold_proxy_minutes)} |"
        )
    return "\n".join(lines)


def _markdown_leg_summary(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Completed legs | Legs with ≥3 candles | Share | Mean duration proxy (95% date-block CI) | Median | p90 | Mean candles |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.completed_legs):,} | {int(row.legs_at_least_three):,} | "
            f"{_pct(row.share_at_least_three_of_completed)} | {_num(row.mean_duration_proxy_minutes)} min "
            f"({_num(row.mean_duration_ci_low_minutes)}–{_num(row.mean_duration_ci_high_minutes)}) | "
            f"{_num(row.median_duration_proxy_minutes)} min | {_num(row.p90_duration_proxy_minutes)} min | "
            f"{_num(row.mean_candles_in_leg)} |"
        )
    return "\n".join(lines)


def _markdown_leg_rankings(frame: pd.DataFrame) -> str:
    longest = frame.loc[frame["criterion"].eq("longest mean duration")]
    lines = [
        "| Chart | Rank | Reversal raw-clock window | Legs ≥3 | Mean duration proxy (95% CI) | Median | p90 | Mean candles |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in longest.sort_values(["asset", "range_setting", "rank"]).itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {int(row.rank)} | {row.half_hour_window} | "
            f"{int(row.legs_at_least_three):,} | {_num(row.mean_duration_proxy_minutes)} min "
            f"({_num(row.mean_duration_ci_low_minutes)}–{_num(row.mean_duration_ci_high_minutes)}) | "
            f"{_num(row.median_duration_proxy_minutes)} | {_num(row.p90_duration_proxy_minutes)} | "
            f"{_num(row.mean_candles_in_leg)} |"
        )
    return "\n".join(lines)


def _markdown_leg_clock_comparison(frame: pd.DataFrame) -> str:
    selected = frame.loc[frame["window_start"].isin(["09:30", "22:00"])]
    lines = [
        "| Chart | Reversal window | Legs ≥3 | Mean duration proxy | Median | p90 | Mean candles |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in selected.sort_values(["asset", "range_setting", "window_index"]).itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {row.half_hour_window} | {int(row.legs_at_least_three):,} | "
            f"{_num(row.mean_duration_proxy_minutes)} min | {_num(row.median_duration_proxy_minutes)} | "
            f"{_num(row.p90_duration_proxy_minutes)} | {_num(row.mean_candles_in_leg)} |"
        )
    return "\n".join(lines)


def write_methodology(report_dir: Path, config: dict[str, Any]) -> None:
    text = f"""# Methodology

## Question and numbering

The reversal candle is sequence position 1. Its immediately following candle is follow-through position 1 and sequence position 2—the “second green/red candle” in this study. The primary cohort contains every reversal for which that next candle exists in the same valid segment and closes with the same `sign(close-open)` direction as the reversal.

The example of three red candles followed by a green reversal is covered by the prespecified `prior_opposite_run >= 3` sensitivity. The primary result retains every reversal with at least one preceding opposite non-doji candle.

## Primary adverse movement

For the same-direction follow-through candle:

```text
green/long: follow_open - follow_low
red/short: follow_high - follow_open
```

This is the candle's adverse wick/range from its own open. It is nonnegative and uses only that candle's OHLC. The sensitivity reference uses the reversal close instead:

```text
green/long: max(0, reversal_close - follow_low)
red/short: max(0, follow_high - reversal_close)
```

Directional open gap, favorable movement from the follow-through open, and directional close progress are reported for context. These values describe bar geometry, not executable entries or profits.

## Events, boundaries, and units

A reversal is an adjacent non-doji candle whose close-minus-open direction opposes the preceding non-doji candle. Dojis and provisional export-date boundaries break adjacency. The final row of each export is omitted because completion is unverified. A missing next candle is excluded, not treated as a failure. All arithmetic uses integer CME ticks, then translates to native price and gross dollars per standard contract.

The full-period result includes all 72 export dates. Development/validation/test labels from Analysis 01 are reused only as chronological stability slices; no setting is selected or optimized in this analysis. Mean confidence intervals use {config['bootstrap']['replicates']:,} export-date block bootstrap replicates with seed {config['bootstrap']['seed']}.

## Time-of-day extension

Time-of-day results use fixed {config['time_of_day']['window_minutes']}-minute raw export-clock intervals, with the start included and the end excluded. No timezone conversion is made because the files do not identify a timezone. The exports also do not establish whether timestamps denote bar opens, closes, or another platform convention.

The signal-time table assigns events to the reversal candle timestamp and supplies the denominator needed for follow-through probability. The confirmation-time table assigns successful events to the next candle timestamp, when membership in the same-direction cohort becomes known. Rankings require at least {config['time_of_day']['minimum_conditioned_events']:,} conditioned events and {config['time_of_day']['minimum_active_export_dates']} active export dates in a window.

## Post-confirmation hold-time extension

The primary hold target requires the two bars immediately after the confirmation candle to both close in the existing reversal direction. Exact bar distance is therefore two additional bars. The raw timestamp-difference proxy runs from the confirmation candle timestamp to the second additional bar timestamp and is summarized only when the target succeeds. The success probability uses every event with two complete subsequent bars in the same provisional export-date segment.

A separate eventual-pair sensitivity searches the next {config['hold_time']['eventual_search_horizon_bars']} complete bars for the first pair of consecutive bars in the established direction and allows intervening opposite/doji bars. It requires the full search horizon so truncated boundaries are not counted as failures. Time-of-day attribution uses the confirmation candle's raw export-clock window.

## Full reversal-leg duration

The corrected leg-duration cohort starts at the reversal candle and continues through every immediately consecutive candle with the same close-minus-open direction. It ends at the final same-direction candle before the next opposite candle. A doji breaks the run under the frozen event rules. The primary duration table keeps completed legs with at least {config['leg_duration']['minimum_candles_including_reversal']} candles including the reversal. A run reaching an export-date boundary before a breaking candle is censored and excluded from duration summaries.

Leg duration is the raw timestamp difference between the reversal candle and the final same-direction candle. The exact candle count is supported, but the clock duration remains a proxy because timestamp open-versus-close meaning and timezone are unresolved. Time-of-day attribution uses the reversal candle's raw timestamp.

## Limitations

The files remain provisionally identified by their filenames as Range XV. Timezone, timestamp meaning, exact ATAS settings, bar completion metadata, data-feed provenance, and contract-adjustment history remain unresolved. GC6 is analyzed explicitly because this study covers all seven available exports; it is not called GC20 and does not resolve the missing-GC20 limitation in Analysis 01.
"""
    (report_dir / "methodology.md").write_text(text, encoding="utf-8")


def write_data_quality(report_dir: Path, audit: pd.DataFrame) -> None:
    bullets = []
    for row in audit.sort_values(["asset", "range_setting"]).itertuples(index=False):
        bullets.append(
            f"- {row.asset} R{int(row.range_setting)} `{row.source_file}`: {int(row.rows):,} rows, "
            f"{int(row.timestamp_parse_failures)} timestamp parse failures, {int(row.ohlc_failures)} OHLC failures, "
            f"{int(row.off_tick_rows)} off-tick rows, {int(row.timestamp_regressions)} timestamp regressions, "
            f"{int(row.repeated_timestamp_rows):,} rows in repeated timestamps, {int(row.doji_rows)} dojis."
        )
    text = """# Data quality

All seven available files were read without changing `data/`. Each is headerless and semicolon-delimited with five fields interpreted as timestamp/open/high/low/close. The `%Y-%d-%m %H:%M:%S` format parses every row. All OHLC rows satisfy their inequalities and all prices align to the configured exchange ticks.

""" + "\n".join(bullets) + """

Repeated timestamps are preserved in original row order. They do not affect this bar-sequence study. The final row of each file is excluded because completion cannot be verified. Provisional export-calendar dates prevent reversals and follow-through pairs from crossing a date boundary.
"""
    (report_dir / "data_quality.md").write_text(text, encoding="utf-8")


def write_report(
    report_dir: Path,
    config: dict[str, Any],
    summary: pd.DataFrame,
    audit: pd.DataFrame,
    run_id: str,
    signal_time: pd.DataFrame,
    time_rankings: pd.DataFrame,
    balanced_windows: pd.DataFrame,
    hold_summary: pd.DataFrame,
    hold_rankings: pd.DataFrame,
    hold_balanced_windows: pd.DataFrame,
) -> None:
    headline = headline_table(summary)
    table = _markdown_headline(headline)
    prior_three_table = _markdown_prior_three(summary)
    reference_table = _markdown_reference_comparison(headline)
    side_table = _markdown_long_short(summary)
    time_rank_table = _markdown_time_rank_one(time_rankings)
    balanced_table = _markdown_balanced_windows(balanced_windows)
    hold_summary_table = _markdown_hold_summary(hold_summary)
    eventual_hold_table = _markdown_eventual_hold_summary(hold_summary)
    hold_balanced_table = _markdown_hold_balanced(hold_balanced_windows)
    observations = []
    for row in headline.itertuples(index=False):
        observations.append(
            f"- **{row.asset} R{int(row.range_setting)}:** mean adverse movement was {_num(row.mean_adverse_ticks)} ticks "
            f"({_num(row.mean_adverse_price)} native price units; ${_num(row.mean_adverse_gross_dollars)} gross), "
            f"with median {_num(row.median_adverse_ticks, 1)} and p90 {_num(row.p90_adverse_ticks, 1)} ticks. "
            f"The next candle closed in the reversal direction in {_pct(row.same_direction_probability)} of eligible reversals "
            f"({int(row.same_direction_next_bar):,}/{int(row.eligible_next_bar):,})."
        )
    text = f"""# Adverse movement of the second same-direction candle

Run `{run_id}`. This analysis covers all seven available filename-labeled Range XV exports: ES 4/5/6, GC 6/10, and NQ 10/20.

## Definition

The reversal is the first green/red candle after the opposite run. The immediately following candle is the **second same-direction candle including the reversal**. Results condition on that candle also closing in the reversal direction. The primary adverse movement is measured from that follow-through candle's own open: open-to-low for green/long and high-to-open for red/short.

## Full-period results

{table}

The denominator for mean adverse movement is the number of same-direction second candles, not all reversals. The conditional rate column shows how frequently a reversal reached that cohort. Confidence intervals resample provisional export dates and account for within-date dependence.

## Chart-level summary

{chr(10).join(observations)}

## Three-or-more preceding opposite candles

This sensitivity matches the example of at least three red candles followed by a green reversal, or vice versa.

{prior_three_table}

The prior-run ≥3 cohort has slightly lower adverse movement than the all-reversal cohort in every chart, but the range-size ordering is unchanged.

## Reference-point sensitivity

All values below are ticks. A positive directional opening gap means the second candle opened favorably relative to the reversal close.

{reference_table}

## Long versus short

{side_table}

Long/green and short/red means are close within every chart, so the combined-direction results are not being driven by only one reversal direction.

## Time of day: 30-minute raw-clock windows

The files do not identify their timezone or whether a timestamp marks a bar's open or close, so these are **raw export-clock windows**, not ET or CT. Intervals are start-inclusive and end-exclusive. “Most frequent” is normalized as conditioned events per active export date; it is not just the largest raw count. Values in parentheses below are the winning metric: shares for rate, events/date for frequency, and ticks for movement.

{time_rank_table}

There is no single objectively “best” time: a window can be frequent but have more adverse movement, or have attractive geometry but fewer occurrences. The balanced shortlist below uses a transparent rule: among supported reversal-time windows, retain those at or above that chart's median follow-through rate and event frequency, require positive mean favorable-minus-adverse movement, then rank by favorable-minus-adverse movement.

{balanced_table}

These rankings are descriptive selections from the same sample, not out-of-sample timing rules. The full tables preserve every half-hour, including low-activity and inactive windows. The confirmation-time table is the appropriate reference for when the follow-through condition becomes observable.

## Hold time after confirmation: two more same-direction candles

The primary definition is strict: the next two bars after confirmation must both close in the established direction. The time value is the raw timestamp difference from confirmation to the second additional bar. It is a proxy, not verified elapsed holding time, because the exports do not say whether bar timestamps mark opens or closes. A zero value means tied timestamps; it was preserved rather than replaced with an invented duration.

{hold_summary_table}

Time is summarized only among strict successes. The success rate is shown separately to prevent a fast-looking successful subset from hiding frequent failures.

### Best-supported 30-minute confirmation windows

The shortlist requires at least {config['hold_time']['minimum_eligible_events_per_window']} eligible confirmations, {config['hold_time']['minimum_successes_per_window']} successes, and {config['hold_time']['minimum_active_export_dates']} active export dates. A balanced candidate must have at least its chart's median success rate and no more than its chart's median hold proxy among supported windows. Rankings use median, then p90, then success rate.

{hold_balanced_table}

### Eventual-pair sensitivity

This alternative asks how long it takes to encounter the first two-bar same-direction pair anywhere within the next {config['hold_time']['eventual_search_horizon_bars']} bars, allowing intervening bars.

{eventual_hold_table}

## Interpretation

Larger range settings generally allow larger adverse movement inside the second candle. The result should therefore be compared in ticks, native price, and dollars—not raw points across assets. The separate long/short table checks directional symmetry, and the prior-run table shows whether the three-opposite-candle example differs from the all-reversal cohort.

This is a conditional bar-geometry estimate. Selecting only second candles that ultimately close in the reversal direction uses their close to define the cohort; it is not a real-time entry filter and does not establish profitability. The signal-close sensitivity can differ from the own-open result because Range XV bars may open away from the reversal close.

## Outputs

- [All summary slices](tables/all_summary.csv)
- [Headline all-reversal results](tables/headline.csv)
- [Long and short results](tables/long_short.csv)
- [Prior-run sensitivity](tables/prior_run_sensitivity.csv)
- [Chronological stability](tables/chronological_stability.csv)
- [Independent real-event reconciliation](tables/manual_reconciliation.csv)
- [All 30-minute reversal-time windows](tables/time_of_day_signal_30min.csv)
- [All 30-minute confirmation-time windows](tables/time_of_day_confirmation_30min.csv)
- [Top three windows by criterion](tables/time_of_day_rankings_30min.csv)
- [Balanced supported windows](tables/time_of_day_balanced_windows_30min.csv)
- [Post-confirmation hold-time summary](tables/hold_time_summary.csv)
- [All 30-minute hold-time windows](tables/hold_time_by_confirmation_30min.csv)
- [Hold-time rankings](tables/hold_time_rankings_30min.csv)
- [Balanced hold-time windows](tables/hold_time_balanced_windows_30min.csv)
- [Independent hold-time reconciliation](tables/hold_time_manual_reconciliation.csv)
- [Full reversal-leg duration report](leg_duration_report.md)
- [Full reversal-leg summary](tables/leg_duration_summary.csv)
- [All reversal-leg 30-minute windows](tables/leg_duration_by_reversal_30min.csv)
- [Methodology](methodology.md)
- [Data quality](data_quality.md)
- [Run manifest](run_manifest.json)

Figures: [mean adverse movement](figures/mean_adverse.svg), [median and p90](figures/adverse_distribution.svg), [long versus short](figures/long_short.svg), [prior-run sensitivity](figures/prior_run_sensitivity.svg), [chronological stability](figures/chronological_stability.svg), [30-minute follow-through-rate heatmap](figures/time_of_day_followthrough_rate.svg), and [30-minute hold-time heatmap](figures/hold_time_30min.svg).
"""
    (report_dir / "report.md").write_text(text, encoding="utf-8")
    _write_html(report_dir, headline, text, run_id)


def _markdown_leg_sessions(frame: pd.DataFrame) -> str:
    lines = [
        "| Chart | Session (raw clock) | T≥3 legs | Mean minutes (95% block CI) | Median | p90 | Mean candles | T≥3 share |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.sort_values(["asset", "range_setting", "session_order"]).itertuples(index=False):
        lines.append(
            f"| {row.asset} R{int(row.range_setting)} | {row.session} ({row.session_window}) | "
            f"{int(row.legs_at_least_three):,} | {_num(row.mean_duration_proxy_minutes)} "
            f"({_num(row.mean_duration_ci_low_minutes)}–{_num(row.mean_duration_ci_high_minutes)}) | "
            f"{_num(row.median_duration_proxy_minutes)} | {_num(row.p90_duration_proxy_minutes)} | "
            f"{_num(row.mean_candles_in_leg)} | {_pct(row.share_at_least_three_of_completed)} |"
        )
    return "\n".join(lines)


def write_leg_duration_report(
    report_dir: Path,
    config: dict[str, Any],
    run_id: str,
    summary: pd.DataFrame,
    time_table: pd.DataFrame,
    session_table: pd.DataFrame,
    rankings: pd.DataFrame,
) -> None:
    summary_table = _markdown_leg_summary(summary)
    session_summary = _markdown_leg_sessions(session_table)
    rankings_table = _markdown_leg_rankings(rankings)
    clock_comparison = _markdown_leg_clock_comparison(time_table)
    text = f"""# Reversal-leg duration

Run `{run_id}`. This report covers ES 4/5/6, GC 6/10, and NQ 10/20 from the seven available filename-labeled Range XV exports.

## Definition

A leg starts with the reversal candle. That candle is position 1. Every immediately following candle with the same `sign(close-open)` direction remains in the leg. The leg ends at the last same-direction candle before the next opposite candle. Dojis break runs under the frozen study definition.

The analysis below keeps completed legs with at least three candles including the reversal (`T ≥ 3`). Legs that reach a provisional export-date boundary before another opposite candle are censored and excluded, not assigned a duration of zero. Duration is the raw timestamp difference from the reversal candle to the final same-direction candle.

## Overall duration of completed three-or-more-candle legs

{summary_table}

The mean is the requested average. Median and p90 show skew: a smaller number of slow legs can lift the mean. Mean confidence intervals use {config['bootstrap']['replicates']:,} export-date block bootstrap replicates.

## Session duration breakdown

Sessions are assigned using the reversal candle's raw timestamp. The configured intervals are half-open; Asia crosses midnight. They are raw export-clock proxies, not verified ET sessions, because the files contain no timezone metadata.

{session_summary}

## Longest average duration by reversal time

The table reports the top three supported 30-minute windows per chart. A supported window has at least {config['leg_duration']['minimum_qualifying_legs_per_window']} qualifying legs across at least {config['leg_duration']['minimum_active_export_dates']} export dates.

{rankings_table}

## Morning versus 22:00 example

{clock_comparison}

## Interpretation limits

The exact result is the number of consecutive same-direction range candles. Clock values are raw timestamp-difference proxies. The files do not identify timezone or whether timestamps mark bar opens or closes. Repeated timestamps are retained, so some completed legs have zero recorded duration. No intrabar duration is invented.

These are same-color candle legs, not guaranteed profitable price paths. Open gaps and wick movement can differ from candle direction.

## Outputs

- [All 30-minute windows](tables/leg_duration_by_reversal_30min.csv)
- [Overall chart summary](tables/leg_duration_summary.csv)
- [Session duration breakdown](tables/leg_duration_by_session.csv)
- [Time-window rankings](tables/leg_duration_rankings_30min.csv)
- [Independent real-event reconciliation](tables/leg_duration_manual_reconciliation.csv)
- [Time-of-day figure](figures/leg_duration_30min.svg)
- [Methodology](methodology.md)
- [Run manifest](run_manifest.json)
"""
    (report_dir / "leg_duration_report.md").write_text(text, encoding="utf-8")
    table = summary.to_html(index=False, border=0, classes="data", float_format=lambda x: f"{x:.3f}")
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reversal-leg duration — {html.escape(run_id)}</title><style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1120px;margin:36px auto;padding:0 24px;color:#18212b;line-height:1.5}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{padding:7px;border-bottom:1px solid #d9dfe4;text-align:right}}th:first-child,td:first-child{{text-align:left}}img{{max-width:100%;border:1px solid #d9dfe4}}.note{{background:#f3f6f8;padding:14px;border-left:4px solid #3c6e71}}pre{{white-space:pre-wrap;font-family:system-ui}}</style></head>
<body><h1>Reversal-leg duration</h1><p class="note">Completed same-direction legs with at least three candles including the reversal. Raw timestamp-difference proxy.</p>{table}<section><h2>Time of day</h2><img src="figures/leg_duration_30min.svg" alt="Mean reversal-leg duration by 30-minute raw-clock window"></section><h2>Full narrative</h2><pre>{html.escape(text)}</pre></body></html>"""
    (report_dir / "leg_duration_report.html").write_text(document, encoding="utf-8")


def _write_html(report_dir: Path, headline: pd.DataFrame, report_text: str, run_id: str) -> None:
    columns = [
        "asset", "range_setting", "total_reversals", "same_direction_next_bar",
        "same_direction_probability", "mean_adverse_ticks", "mean_adverse_ci_low_ticks",
        "mean_adverse_ci_high_ticks", "median_adverse_ticks", "p90_adverse_ticks",
        "mean_adverse_price", "mean_adverse_gross_dollars",
    ]
    table = headline[columns].to_html(index=False, border=0, classes="data", float_format=lambda x: f"{x:.3f}")
    figures = "".join(
        f'<section><h2>{html.escape(title)}</h2><img src="figures/{name}" alt="{html.escape(title)}"></section>'
        for title, name in (
            ("Mean adverse movement", "mean_adverse.svg"),
            ("Median and p90 adverse movement", "adverse_distribution.svg"),
            ("Long versus short", "long_short.svg"),
            ("Prior-run sensitivity", "prior_run_sensitivity.svg"),
            ("Chronological stability", "chronological_stability.svg"),
            ("30-minute follow-through rate", "time_of_day_followthrough_rate.svg"),
            ("30-minute post-confirmation hold time", "hold_time_30min.svg"),
        )
    )
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Second-candle adverse movement — {html.escape(run_id)}</title><style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1120px;margin:36px auto;padding:0 24px;color:#18212b;line-height:1.5}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{padding:7px;border-bottom:1px solid #d9dfe4;text-align:right}}th:first-child,td:first-child{{text-align:left}}img{{max-width:100%;border:1px solid #d9dfe4}}.note{{background:#f3f6f8;padding:14px;border-left:4px solid #3c6e71}}pre{{white-space:pre-wrap;font-family:system-ui}}</style></head>
<body><h1>Adverse movement of the second same-direction candle</h1><p class="note">Conditional bar-geometry analysis; not an executable strategy or profit estimate.</p>{table}{figures}<h2>Full narrative</h2><pre>{html.escape(report_text)}</pre></body></html>"""
    (report_dir / "report.html").write_text(document, encoding="utf-8")


def _save_bar_chart(
    path: Path,
    frame: pd.DataFrame,
    value_columns: list[tuple[str, str]],
    title: str,
    y_label: str,
) -> None:
    width, height = 1080, 620
    left, top, plot_w, plot_h = 90, 75, 930, 440
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        f'<text x="28" y="34" font-family="system-ui" font-size="20" font-weight="600">{html.escape(title)}</text>',
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fafafa" stroke="#d8dde2"/>',
    ]
    values = []
    for column, _ in value_columns:
        values.extend(pd.to_numeric(frame[column], errors="coerce").dropna().tolist())
    ymax = max(values) * 1.15 if values else 1
    for tick in range(6):
        value = ymax * tick / 5
        y = top + plot_h - plot_h * tick / 5
        lines += [
            f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#e4e8eb"/>',
            f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="system-ui" font-size="11">{value:.1f}</text>',
        ]
    group_w = plot_w / max(1, len(frame))
    bar_w = group_w * 0.65 / max(1, len(value_columns))
    series_colors = ["#005f73", "#ca6702", "#6b7280", "#7c3aed"]
    for i, row in enumerate(frame.itertuples(index=False)):
        chart = f"{row.asset} R{int(row.range_setting)}"
        center = left + (i + 0.5) * group_w
        for j, (column, label) in enumerate(value_columns):
            value = float(getattr(row, column))
            height_value = value / ymax * plot_h
            x = center - len(value_columns) * bar_w / 2 + j * bar_w
            color = COLORS.get(int(row.range_setting), "#345") if len(value_columns) == 1 else series_colors[j % len(series_colors)]
            lines.append(f'<rect x="{x:.1f}" y="{top+plot_h-height_value:.1f}" width="{bar_w-2:.1f}" height="{height_value:.1f}" fill="{color}"/>')
        lines.append(f'<text x="{center:.1f}" y="{top+plot_h+24}" text-anchor="middle" font-family="system-ui" font-size="12">{html.escape(chart)}</text>')
    for j, (_, label) in enumerate(value_columns):
        color = COLORS.get(4, "#005f73") if len(value_columns) == 1 else series_colors[j % len(series_colors)]
        lines += [f'<rect x="{left+j*180}" y="{height-50}" width="14" height="14" fill="{color}"/>', f'<text x="{left+20+j*180}" y="{height-38}" font-family="system-ui" font-size="12">{html.escape(label)}</text>']
    lines.append(f'<text x="20" y="{top+plot_h/2}" transform="rotate(-90 20 {top+plot_h/2})" text-anchor="middle" font-family="system-ui" font-size="12">{html.escape(y_label)}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_time_heatmap(path: Path, signal_time: pd.DataFrame) -> None:
    charts = signal_time[["asset", "range_setting"]].drop_duplicates().sort_values(["asset", "range_setting"])
    width, height = 1280, 360
    left, top, plot_w, row_h = 95, 72, 1120, 28
    values = pd.to_numeric(signal_time["same_direction_probability"], errors="coerce")
    low = float(values.quantile(0.05))
    high = float(values.quantile(0.95))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        low, high = 0.0, 1.0
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="28" y="32" font-family="system-ui" font-size="20" font-weight="600">Same-direction follow-through rate by reversal candle raw clock</text>',
        '<text x="28" y="52" font-family="system-ui" font-size="12" fill="#4b5563">30-minute windows; timezone and timestamp meaning unresolved</text>',
    ]
    cell_w = plot_w / 48
    for row_index, chart in enumerate(charts.itertuples(index=False)):
        y = top + row_index * row_h
        lines.append(f'<text x="{left-8}" y="{y+18}" text-anchor="end" font-family="system-ui" font-size="12">{chart.asset} R{int(chart.range_setting)}</text>')
        subset = signal_time.loc[
            signal_time["asset"].eq(chart.asset) & signal_time["range_setting"].eq(chart.range_setting)
        ].set_index("window_index")
        for window_index in range(48):
            value = subset.at[window_index, "same_direction_probability"] if window_index in subset.index else np.nan
            if pd.isna(value):
                color = "#eceff1"
            else:
                fraction = min(1.0, max(0.0, (float(value) - low) / (high - low)))
                red = int(238 - 204 * fraction)
                green = int(246 - 91 * fraction)
                blue = int(250 - 91 * fraction)
                color = f"#{red:02x}{green:02x}{blue:02x}"
            x = left + window_index * cell_w
            lines.append(f'<rect x="{x:.1f}" y="{y}" width="{cell_w+0.2:.1f}" height="22" fill="{color}" stroke="#fff" stroke-width="0.5"/>')
    axis_y = top + len(charts) * row_h + 7
    for window_index in range(0, 49, 4):
        x = left + window_index * cell_w
        label = f"{(window_index // 2) % 24:02d}:00"
        lines.append(f'<line x1="{x:.1f}" y1="{axis_y-5}" x2="{x:.1f}" y2="{axis_y}" stroke="#6b7280"/>')
        lines.append(f'<text x="{x:.1f}" y="{axis_y+16}" text-anchor="middle" font-family="system-ui" font-size="10">{label}</text>')
    lines.append(f'<text x="{left}" y="{height-22}" font-family="system-ui" font-size="11" fill="#4b5563">Paler = lower rate; darker = higher rate. Scale clipped to cross-chart 5th–95th percentiles ({100*low:.1f}%–{100*high:.1f}%).</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_hold_time_heatmap(path: Path, hold_time: pd.DataFrame) -> None:
    charts = hold_time[["asset", "range_setting"]].drop_duplicates().sort_values(["asset", "range_setting"])
    width, height = 1280, 360
    left, top, plot_w, row_h = 95, 72, 1120, 28
    supported = hold_time.loc[hold_time["strict_success"].ge(100)]
    values = pd.to_numeric(supported["strict_median_hold_proxy_minutes"], errors="coerce")
    cap = float(values.quantile(0.95)) if len(values.dropna()) else 1.0
    cap = cap if np.isfinite(cap) and cap > 0 else 1.0
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="28" y="32" font-family="system-ui" font-size="20" font-weight="600">Median proxy time to two more same-direction bars</text>',
        '<text x="28" y="52" font-family="system-ui" font-size="12" fill="#4b5563">By confirmation candle raw-clock window; successful strict continuations only</text>',
    ]
    cell_w = plot_w / 48
    for row_index, chart in enumerate(charts.itertuples(index=False)):
        y = top + row_index * row_h
        lines.append(f'<text x="{left-8}" y="{y+18}" text-anchor="end" font-family="system-ui" font-size="12">{chart.asset} R{int(chart.range_setting)}</text>')
        subset = hold_time.loc[
            hold_time["asset"].eq(chart.asset) & hold_time["range_setting"].eq(chart.range_setting)
        ].set_index("window_index")
        for window_index in range(48):
            if window_index not in subset.index or int(subset.at[window_index, "strict_success"]) < 100:
                color = "#eceff1"
            else:
                value = float(subset.at[window_index, "strict_median_hold_proxy_minutes"])
                fraction = min(1.0, max(0.0, value / cap))
                red = int(236 - 42 * fraction)
                green = int(248 - 158 * fraction)
                blue = int(244 - 119 * fraction)
                color = f"#{red:02x}{green:02x}{blue:02x}"
            x = left + window_index * cell_w
            lines.append(f'<rect x="{x:.1f}" y="{y}" width="{cell_w+0.2:.1f}" height="22" fill="{color}" stroke="#fff" stroke-width="0.5"/>')
    axis_y = top + len(charts) * row_h + 7
    for window_index in range(0, 49, 4):
        x = left + window_index * cell_w
        label = f"{(window_index // 2) % 24:02d}:00"
        lines.append(f'<line x1="{x:.1f}" y1="{axis_y-5}" x2="{x:.1f}" y2="{axis_y}" stroke="#6b7280"/>')
        lines.append(f'<text x="{x:.1f}" y="{axis_y+16}" text-anchor="middle" font-family="system-ui" font-size="10">{label}</text>')
    lines.append(f'<text x="{left}" y="{height-22}" font-family="system-ui" font-size="11" fill="#4b5563">Paler = shorter; darker = longer. Gray has fewer than 100 strict successes. Color scale capped at {cap:.2f} minutes.</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_leg_duration_heatmap(path: Path, leg_time: pd.DataFrame) -> None:
    charts = leg_time[["asset", "range_setting"]].drop_duplicates().sort_values(["asset", "range_setting"])
    width, height = 1280, 360
    left, top, plot_w, row_h = 95, 72, 1120, 28
    supported = leg_time.loc[leg_time["legs_at_least_three"].ge(100)]
    values = pd.to_numeric(supported["mean_duration_proxy_minutes"], errors="coerce")
    cap = float(values.quantile(0.95)) if len(values.dropna()) else 1.0
    cap = cap if np.isfinite(cap) and cap > 0 else 1.0
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="28" y="32" font-family="system-ui" font-size="20" font-weight="600">Mean duration of completed reversal legs with at least three candles</text>',
        '<text x="28" y="52" font-family="system-ui" font-size="12" fill="#4b5563">By reversal candle raw-clock window; timestamp-difference proxy in minutes</text>',
    ]
    cell_w = plot_w / 48
    for row_index, chart in enumerate(charts.itertuples(index=False)):
        y = top + row_index * row_h
        lines.append(f'<text x="{left-8}" y="{y+18}" text-anchor="end" font-family="system-ui" font-size="12">{chart.asset} R{int(chart.range_setting)}</text>')
        subset = leg_time.loc[
            leg_time["asset"].eq(chart.asset) & leg_time["range_setting"].eq(chart.range_setting)
        ].set_index("window_index")
        for window_index in range(48):
            if window_index not in subset.index or int(subset.at[window_index, "legs_at_least_three"]) < 100:
                color = "#eceff1"
            else:
                value = float(subset.at[window_index, "mean_duration_proxy_minutes"])
                fraction = min(1.0, max(0.0, value / cap))
                red = int(237 - 82 * fraction)
                green = int(246 - 136 * fraction)
                blue = int(255 - 71 * fraction)
                color = f"#{red:02x}{green:02x}{blue:02x}"
            x = left + window_index * cell_w
            lines.append(f'<rect x="{x:.1f}" y="{y}" width="{cell_w+0.2:.1f}" height="22" fill="{color}" stroke="#fff" stroke-width="0.5"/>')
    axis_y = top + len(charts) * row_h + 7
    for window_index in range(0, 49, 4):
        x = left + window_index * cell_w
        label = f"{(window_index // 2) % 24:02d}:00"
        lines.append(f'<line x1="{x:.1f}" y1="{axis_y-5}" x2="{x:.1f}" y2="{axis_y}" stroke="#6b7280"/>')
        lines.append(f'<text x="{x:.1f}" y="{axis_y+16}" text-anchor="middle" font-family="system-ui" font-size="10">{label}</text>')
    lines.append(f'<text x="{left}" y="{height-22}" font-family="system-ui" font-size="11" fill="#4b5563">Paler = shorter mean duration; darker = longer. Gray has fewer than 100 qualifying legs. Scale capped at {cap:.2f} minutes.</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_figures(
    report_dir: Path,
    summary: pd.DataFrame,
    signal_time: pd.DataFrame,
    hold_time: pd.DataFrame,
    leg_time: pd.DataFrame,
) -> None:
    figures = report_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    full = headline_table(summary)
    _save_bar_chart(figures / "mean_adverse.svg", full, [("mean_adverse_ticks", "Mean adverse")], "Mean adverse movement of the same-direction second candle", "Exchange ticks")
    _save_bar_chart(figures / "adverse_distribution.svg", full, [("median_adverse_ticks", "Median"), ("p90_adverse_ticks", "p90")], "Adverse movement distribution", "Exchange ticks")
    side = summary.loc[summary["period"].eq("full") & summary["prior_run_minimum"].eq(1) & summary["direction"].isin(["long", "short"])].pivot(index=["asset", "range_setting"], columns="direction", values="mean_adverse_ticks").reset_index()
    _save_bar_chart(figures / "long_short.svg", side, [("long", "Long"), ("short", "Short")], "Mean adverse movement by reversal direction", "Exchange ticks")
    prior = summary.loc[summary["period"].eq("full") & summary["direction"].eq("all")].pivot(index=["asset", "range_setting"], columns="prior_run_minimum", values="mean_adverse_ticks").reset_index().rename(columns={1: "prior1", 2: "prior2", 3: "prior3"})
    _save_bar_chart(figures / "prior_run_sensitivity.svg", prior, [("prior1", "Prior ≥1"), ("prior2", "Prior ≥2"), ("prior3", "Prior ≥3")], "Prior opposite-run sensitivity", "Mean adverse ticks")
    chrono = summary.loc[summary["period"].isin(["development", "validation", "test"]) & summary["direction"].eq("all") & summary["prior_run_minimum"].eq(1)].copy()
    chrono = chrono.pivot(index=["asset", "range_setting"], columns="period", values="mean_adverse_ticks").reset_index()
    _save_bar_chart(figures / "chronological_stability.svg", chrono, [("development", "Development"), ("validation", "Validation"), ("test", "Test")], "Chronological stability of mean adverse movement", "Exchange ticks")
    _save_time_heatmap(figures / "time_of_day_followthrough_rate.svg", signal_time)
    _save_hold_time_heatmap(figures / "hold_time_30min.svg", hold_time)
    _save_leg_duration_heatmap(figures / "leg_duration_30min.svg", leg_time)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
