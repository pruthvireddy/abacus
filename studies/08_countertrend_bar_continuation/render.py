"""Render the local report solely from saved numerical tables and audit evidence."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import pandas as pd


WINDOWS = ["asia", "london_pre_ny", "ny_morning", "ny_afternoon", "transition"]
BINS = ["1-2", "3-4", "5-7", "8+"]
CHARTS = [("ES", 4), ("ES", 5), ("ES", 6), ("GC", 6), ("GC", 10), ("NQ", 10), ("NQ", 20)]


def p(value: float) -> str:
    return f"{100*value:.1f}%"


def p2(value: float) -> str:
    return f"{100*value:.2f}%"


def ci(row) -> str:
    return f"{p(row.ci_low)}–{p(row.ci_high)}"


def where(df: pd.DataFrame, **filters):
    selected = df
    for column, value in filters.items():
        selected = selected.loc[selected[column] == value]
    if len(selected) != 1:
        raise ValueError(f"expected one row for {filters}, got {len(selected)}")
    return selected.iloc[0]


def compact(row) -> str:
    return f"{p(row.probability)} ({int(row.numerator):,}/{int(row.denominator):,})"


def detailed(row) -> str:
    return (f"{compact(row)}; 95% session CI {ci(row)}; {int(row.session_dates):,} dates; "
            f"{row.events_per_session:.1f} events/date")


def inline(line: str) -> str:
    line = html.escape(line)
    line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line)
    line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
    return line


def markdown_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("|") and index+1 < len(lines) and re.match(r"^\|[- :|]+\|$", lines[index+1]):
            headers = [x.strip() for x in line.strip("|").split("|")]
            index += 2
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([x.strip() for x in lines[index].strip("|").split("|")])
                index += 1
            out.append("<div class='table-scroll'><table><thead><tr>"+
                       "".join(f"<th>{inline(x)}</th>" for x in headers)+"</tr></thead><tbody>"+
                       "".join("<tr>"+"".join(f"<td>{inline(x)}</td>" for x in row)+"</tr>" for row in rows)+
                       "</tbody></table></div>")
            continue
        if line.startswith("#"):
            level = len(line)-len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line.startswith("- "):
            if not out or not out[-1].startswith("<ul"):
                out.append("<ul>")
            out.append(f"<li>{inline(line[2:])}</li>")
            if index+1 == len(lines) or not lines[index+1].startswith("- "):
                out.append("</ul>")
        else:
            out.append(f"<p>{inline(line)}</p>")
        index += 1
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><title>RXV countertrend continuation</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{font:16px/1.5 system-ui,sans-serif;color:#182229;background:#f7f9fa;margin:0}"
            "main{max-width:1120px;margin:auto;padding:2rem}h1,h2,h3{line-height:1.2}h2{margin-top:2.5rem}"
            "p,li{max-width:90ch}.table-scroll{overflow:auto;margin:1rem 0 1.7rem}table{border-collapse:collapse;background:white;font-size:.84rem;white-space:nowrap}"
            "th,td{border:1px solid #dae0e4;padding:.38rem .55rem;text-align:right}th:first-child,td:first-child{text-align:left}"
            "th{background:#e7f0f3;position:sticky;top:0}tr:nth-child(even){background:#f2f6f7}"
            "a{color:#14627c}code{background:#eaf0f2;padding:.1rem .25rem}</style><main>"+
            "\n".join(out)+"</main></html>\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    tables = stage / "tables"
    audit = json.loads((stage / "audit.json").read_text())
    checks = json.loads((stage / "checks.json").read_text())
    assert checks["status"] == "pass"
    overall = pd.read_csv(tables / "overall.csv")
    lookup = pd.read_csv(tables / "lookup.csv")
    screen = pd.read_csv(tables / "headline_screen.csv")
    period = pd.read_csv(tables / "period.csv")
    structure = pd.read_csv(tables / "structure.csv")
    larger = pd.read_csv(tables / "larger_aggregate.csv")
    onebar = pd.read_csv(tables / "onebar_larger.csv")
    sensitivity = pd.read_csv(tables / "sensitivity.csv")
    run_lengths = pd.read_csv(tables / "run_lengths.csv")
    traces = pd.read_csv(tables / "real_event_traces.csv")
    main_cells = screen.loc[screen.prior_bin != "1-2"]
    positive = int(main_cells.noteworthy_positive.sum())
    supported = int(main_cells.supported.sum())
    negative_adjusted = int((main_cells.family_ci_high_pp < 0).sum())
    overall_rate_ranges = {}
    for metric in ("p1", "p2", "p3_given_p1"):
        values = overall.loc[overall.metric == metric, "probability"]
        overall_rate_ranges[metric] = f"{p(values.min())}–{p(values.max())}"
    aligned_onebar = onebar.loc[onebar.larger_context == "aligned"]
    aligned_ranges = {}
    for metric in ("p1", "p2"):
        values = aligned_onebar.loc[aligned_onebar.metric == metric, "probability"]
        aligned_ranges[metric] = f"{p(values.min())}–{p(values.max())}"
    gc_changes = []
    for setting in (6, 10):
        excluded = where(sensitivity, product="GC", setting=setting, sensitivity="gc_gap_excluded")
        included = where(sensitivity, product="GC", setting=setting, sensitivity="gc_gap_included")
        gc_changes.append(f"GC {setting} from {p2(excluded.probability)} to {p2(included.probability)}")
    lines = [
        "# First countertrend Range XV bar: how many more bars follow?",
        "",
        "Study `08_countertrend_bar_continuation`; long-history local run. All displayed rates come from the saved CSV tables in this bundle. This is bar-behavior evidence, not an execution or profitability test.",
        "",
        "## Answer for chart watching",
        "",
        f"After C1 closes, **the next one bar follows {overall_rate_ranges['p1']} of the time, while the next TWO bars both follow {overall_rate_ranges['p2']}** across the seven charts when bullish and bearish signals are kept separate. Two more means C2 and C3; C1 is not counted. Among C2 successes, C3 follows {overall_rate_ranges['p3_given_p1']}. These are different questions and denominators.",
        "",
        f"**No positive prior-run-length × session × direction cell passed the frozen screen** ({positive} of {len(main_cells)} main contrasts; {supported} had minimum support). Several high point estimates occur in the thin 16:00–18:00 transition. The strongest supported positive example below has a familywise interval that includes zero. {negative_adjusted} main cells had Bonferroni intervals below their chart/direction/session baselines; these are downward descriptive findings, not a trading rule. Agreement across ES or NQ settings is correlated because the settings transform the same trades.",
        "",
        "The practical read is therefore a roughly three-in-four chance of **one** more directional candle, followed by a roughly one-in-two chance of **two** more. An extended prior trend does not produce a stable, reliably higher two-more probability in this snapshot.",
        "",
        "## Outcome definitions and sample",
        "",
        "A prior trend is an uninterrupted same-direction sequence of completed non-doji bars within one inferred 18:00 New York session. A doji breaks the sequence. C1 is the first completed opposite non-doji bar. C2, C3, and C4 are the next physical bars; a doji fails continuation. A signal is observable at C1's next-bar-start completion proxy. The primary denominator requires C1, C2, and C3 to have strictly later same-session completion proxies. C4 also needs a strict completion for the three-more outcome. Session/export boundary cases and equal-second C1/C2/C3 completions are excluded, not scored as failures.",
        "",
        "Windows use C1's completion wall time and half-open boundaries: Asia 18:00–03:00, London/pre-NY 03:00–09:30, NY morning 09:30–12:00, NY afternoon 12:00–16:00, and transition 16:00–18:00. The enhanced clocks already reflect inferred New York daylight-saving time; no second conversion was applied. ATAS timezone configuration was not verified, so these labels depend on that clock interpretation. One observation never crosses an inferred session boundary.",
        "",
        "## Chart baselines by direction",
        "",
        "Each row is its own same-chart baseline (difference 0 pp). Intervals are 95% session-cluster sandwich intervals. The C2 and both outcomes use the same eligible denominator; dates and events/date apply to both.",
        "",
        "| Chart | C1 direction | C2 follows: k/n, rate [95% CI] | C2 and C3 follow: k/n, rate [95% CI] | Dates | Events/date |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for product, setting in CHARTS:
        for direction in (-1, 1):
            one = where(overall, product=product, setting=setting, direction=direction, metric="p1")
            two = where(overall, product=product, setting=setting, direction=direction, metric="p2")
            lines.append(f"| {product} {setting}RXV | {'bearish' if direction == -1 else 'bullish'} | {compact(one)} [{ci(one)}] | {compact(two)} [{ci(two)}] | {int(two.session_dates):,} | {two.events_per_session:.1f} |")
    lines += ["", "## Other requested outcomes", "",
              "Conditional C3 uses only primary-eligible C2 successes. Three more uses its own strict C4-complete denominator. Immediate resumption uses the primary denominator. Each cell shows numerator/denominator, rate, 95% interval, and session-date count; events/date and same-chart baseline identity are in the [overall numerical table](tables/overall.csv).", "",
              "| Chart; C1 | C3 follows given C2 followed | C2–C4 all follow | C2 immediately resumes old trend |",
              "|---|---:|---:|---:|"]
    for product, setting in CHARTS:
        for direction in (-1, 1):
            cells = []
            for metric in ("p3_given_p1", "p3_more", "immediate_resumption"):
                row = where(overall, product=product, setting=setting, direction=direction, metric=metric)
                cells.append(f"{compact(row)} [{ci(row)}]; {int(row.session_dates):,} dates")
            lines.append(f"| {product} {setting}; {'bearish' if direction == -1 else 'bullish'} | " + " | ".join(cells) + " |")
    lines += ["", "The same table records C2 and C3 dojis separately. Immediate resumption excludes C2 dojis.", "",
              "## Prior trend length × session lookup", "",
              "Each cell shows **P(C2 and C3 both follow C1)** with numerator/eligible denominator. Read the matching chart, direction, bin, and window row in [the full lookup](tables/lookup.csv) for P(C2), conditional P(C3), 95% intervals, session-date count, events/date, and matched baseline difference. The 1–2 bin is context; 3–4, 5–7, and 8+ were the main comparisons. The period table gives three chronological blocks. Signals are not pooled across charts.", ""]
    for product, setting in CHARTS:
        lines += [f"### {product} {setting}RXV", "",
                  "| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |",
                  "|---|---:|---:|---:|---:|---:|"]
        for direction in (-1, 1):
            for prior_bin in BINS:
                cells = []
                for window in WINDOWS:
                    row = where(lookup, product=product, setting=setting, direction=direction,
                                prior_bin=prior_bin, session_window=window, metric="p2")
                    cells.append(compact(row))
                lines.append(f"| {'Bearish' if direction == -1 else 'Bullish'}; {prior_bin} | " + " | ".join(cells) + " |")
        lines.append("")
    examples = [("ES", 5, -1, "5-7", "london_pre_ny"),
                ("GC", 10, 1, "8+", "london_pre_ny"),
                ("ES", 6, -1, "5-7", "ny_morning"),
                ("NQ", 20, -1, "8+", "ny_morning")]
    lines += ["## Detailed reads and time stability", "",
              "The baseline for these rows is **all prior-run lengths on the same chart, C1 direction, and session window**. The 95% difference interval accounts for shared session dates; the familywise interval covers the frozen 210 main comparisons. Three-block differences use 2019–2021, 2022–2023, and 2024–2026, respectively. The recent block was previously inspected in older RXV research and is not pristine out-of-sample evidence.", "",
              "| Chart; C1; prior bars; window | C2 follows | C2+C3 follows | Dates; events/date | Difference vs baseline | 95% CI for difference | Bonferroni CI | Three-block differences |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for product, setting, direction, prior_bin, window in examples:
        one = where(lookup, product=product, setting=setting, direction=direction,
                    prior_bin=prior_bin, session_window=window, metric="p1")
        two = where(lookup, product=product, setting=setting, direction=direction,
                    prior_bin=prior_bin, session_window=window, metric="p2")
        blocks = [where(period, product=product, setting=setting, direction=direction,
                        prior_bin=prior_bin, session_window=window, block=block, metric="p2")
                  for block in ("early", "middle", "recent")]
        label = f"{product} {setting}; {'bearish' if direction == -1 else 'bullish'}; {prior_bin}; {window}"
        lines.append(f"| {label} | {compact(one)} | {compact(two)} [{ci(two)}] | {int(two.session_dates):,}; {two.events_per_session:.1f} | {two.difference_pp:+.2f} pp vs {p(two.baseline_probability)} ({int(two.baseline_numerator):,}/{int(two.baseline_denominator):,}) | {two.difference_ci_low_pp:+.2f} to {two.difference_ci_high_pp:+.2f} pp | {two.family_ci_low_pp:+.2f} to {two.family_ci_high_pp:+.2f} pp | " + ", ".join(f"{x.difference_pp:+.2f}" for x in blocks) + " pp |")
    lines += ["", f"For all {len(main_cells)} cells, [headline screen](tables/headline_screen.csv) records support and the prespecified positive decision. [Period estimates](tables/period.csv) contain numerator, denominator, session dates, events/date, intervals, and matched block baseline for every cell. {negative_adjusted} downward Bonferroni intervals appear in the full screen; each also has negative differences in all three blocks. They are descriptive checks in overlapping RXV settings.", "",
              "## Candle and prior-trend structure", "",
              "The following example fixes ES 5RXV, bearish C1, a 5–7 bar prior bullish run, and London/pre-NY. It compares each prespecified feature within that same run-length group and window. These are separate one-feature splits, not a combined predictive model.", "",
              "| Feature at C1 close | Value | C2+C3 follows | 95% CI | Session dates; events/date | Difference vs matched group |",
              "|---|---|---:|---:|---:|---:|"]
    labels = {"body_ge_70":"C1 body ≥70%", "close_loc_ge_80":"C1 directional close ≥80%",
              "adverse_wick_lt_20":"C1 opening-side wick <20%", "break_prev_extreme":"C1 close beyond preceding extreme",
              "prior_opposing_wick_lt_20":"Prior mean terminal-side wick <20%",
              "prior_net_units_per_bar_ge_075":"Prior net movement ≥0.75 RXV/bar",
              "prior_pace_lt_60s":"Prior median formation proxy <60 s"}
    for feature, label in labels.items():
        for value in (True, False):
            match = structure.loc[(structure["product"] == "ES") & (structure.setting == 5) &
                                  (structure.direction == -1) & (structure.prior_bin == "5-7") &
                                  (structure.session_window == "london_pre_ny") &
                                  (structure.feature == feature) & (structure.feature_value == value)]
            if len(match):
                row = match.iloc[0]
                lines.append(f"| {label} | {value} | {compact(row)} | {ci(row)} | {int(row.session_dates):,}; {row.events_per_session:.1f} | {row.difference_pp:+.2f} pp |")
    lines += ["", "A low-contrast feature is not a useful discriminator here: favorable close location and prior net-movement threshold have almost no false cases in this example. The apparent entire-run-break effect from earlier work was largely a one-bar pullback identity, so this study tests only the immediately preceding bar's extreme. All [structure cells](tables/structure.csv), including negative and inconclusive ones, remain available.", "",
              "## Strictly prior larger-chart context", "",
              "Pairs are ES 4→5, ES 5→6, GC 6→10, and NQ 10→20. The larger bar must have a strict completion proxy **before** C1's proxy in the same inferred session. Equal-second larger completions are excluded from this primary paired table. Against means C1 opposes the latest completed larger bar; aligned means a snapback into its direction. No later larger-chart bar is attached. The table holds prior run length at 5–7 bars and shows both directions separately.", "",
              "| Pair; C1 | Context | C2+C3 follows | 95% CI | Dates; events/date | Difference vs pair/bin baseline |",
              "|---|---|---:|---:|---:|---:|"]
    for product, setting in [("ES", 4), ("ES", 5), ("GC", 6), ("NQ", 10)]:
        for direction in (-1, 1):
            for context in ("against", "aligned"):
                row = where(larger, product=product, setting=setting, direction=direction,
                            prior_bin="5-7", larger_context=context, metric="p2")
                lines.append(f"| {product} {setting}→{dict(ES={4:5,5:6}, GC={6:10}, NQ={10:20})[product][setting]}; {'bearish' if direction == -1 else 'bullish'} | {context} | {compact(row)} | {ci(row)} | {int(row.session_dates):,}; {row.events_per_session:.1f} | {row.difference_pp:+.2f} pp |")
    lines += ["", "The [session-resolved larger table](tables/larger.csv) and [all-bin larger table](tables/larger_aggregate.csv) provide their exact matched baselines and intervals. Thin aligned extended-run cells, especially GC 6 after 8+ bars, should not be generalized.", "",
              f"A one-bar opposing pullback that then aligns with the larger chart is a distinct setup. The next-bar rate in this long-history, strictly timed sample is {aligned_ranges['p1']}; the **two-more** rate is {aligned_ranges['p2']}. Its baseline is all one-bar paired signals on the same chart and direction. This must not be substituted for a first reversal after an extended trend. [The full one-bar table](tables/onebar_larger.csv) records both contexts, directions, intervals, and differences.", "",
              "## Subsequent run lengths and immediate resumption", "",
              "[The exact run-length distribution](tables/run_lengths.csv) contains every observed number of subsequent C1-direction bars, including zero, with a separate right-censor flag. Its rows provide counts, denominator, session dates, events/date, share, and 95% session-cluster intervals. For a compact example, these are ES 5RXV completed runs of exactly 0–5 more bars; longer lengths and censored rows remain in the full table.", "",
              "| C1 direction | Exact subsequent bars | Count / eligible | Share [95% CI] | Dates; events/date |",
              "|---|---:|---:|---:|---:|"]
    for direction in (-1, 1):
        for length in range(6):
            row = where(run_lengths, product="ES", setting=5, direction=direction,
                        subsequent_run_length=length, run_censored=False)
            lines.append(f"| {'bearish' if direction == -1 else 'bullish'} | {length} | {int(row.numerator):,}/{int(row.denominator):,} | {p(row.probability)} [{ci(row)}] | {int(row.session_dates):,}; {row.events_per_session:.1f} |")
    lines += ["", "A doji ends the run and is tabulated separately in the [overall outcome table](tables/overall.csv). Immediate original-trend resumption means C2 closes in the old trend's direction; a C2 doji is neither resumption nor continuation. The three-more outcome requires C2, C3, and C4, and has its own eligible denominator.", "",
              "## Same-second and GC sensitivities", "",
              f"The [sensitivity table](tables/sensitivity.csv) reintroduces equal-second larger completions using the last strictly earlier state, C1 same-second completions with strict C2/C3 horizons, then both ambiguities. These are uncertainty checks, not primary estimates. Across the four pairs, the absolute two-more rates move modestly under these choices. GC 6 and 10 also include the five excluded 2026 sessions in a separate comparison; the overall rates change: {gc_changes[0]}, and {gc_changes[1]}. Those small aggregate changes do not make the missing bars safe for a session-specific claim.", "",
              "## Input audit, exclusions, and source traces", "",
              f"The pinned long-history manifest and all {len(audit['verified_inputs'])-1} source/enhanced file hashes were checked before extraction. Enhanced timestamps were not converted again. Bar order, source-row continuity, nondecreasing starts, valid OHLC, manifest row counts, completion-status counts, and session counts were checked. The original source files were used for provenance and {len(traces)} manual row traces, never mixed into the event population.", "",
              "| Chart | Enhanced bars | Observed sessions | C1 signals | Primary eligible after GC exclusion | Excluded C1 completion | Excluded horizon/completion | Same-second C1 | Larger equal-second ties |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for product, setting in CHARTS:
        key = f"{product}_{setting}"
        item = checks["charts"][key]
        lines.append(f"| {product} {setting} | {item['rows']:,} | {item['session_dates']:,} | {item['signals']:,} | {item['eligible_primary']:,} | {item['signal_completion_excluded']:,} | {item['horizon_or_completion_excluded']:,} | {item['same_second_signals']:,} | {item['larger_equal_second_ties']:,} |")
    lines += ["", "The two GC charts each lack 2021-04-02, 2023-04-07, and 2026-04-03 relative to ES/NQ. These may reflect closures or export omission; bars were not invented. The primary GC sample excludes 2026-01-28, 02-04, 02-20, 03-19, and 04-02 because the newer exports differ materially from the older overlaps, including a documented gap on March 19. The [import/overlap audit](../../../docs/range-xv-long-history-20260924.md) found differences on 166 of 534 shared GC 6 sessions and 119 of 534 GC 10 sessions; the remaining differing dates have not been repaired or filled. Treat GC estimates as conditional on this export. The other charts are analyzed only from the long-history snapshot. See [checks](checks.json), [extraction audit](audit.json), and [input lock](inputs.lock.json).", "",
              "Three ES 5RXV signals were reconciled against literal source CSV rows and the corresponding enhanced rows:", "",
              "| Session date | C1 source row | Prior rows | C2/C3 rows | Directions (prior,C1,C2,C3) | Two-more outcome | C1 completion NY wall time | Larger equal-second tie |",
              "|---|---:|---:|---:|---|---|---|---|"]
    for _, trace in traces.iterrows():
        lines.append(f"| {trace.session_date} | {int(trace.c1_source_row):,} | {trace.prior_source_rows} | {int(trace.c2_source_row)}/{int(trace.c3_source_row)} | {trace.directions_prior_c1_c2_c3} | {bool(trace.two_more_success)} | {trace.c1_completion_wall_time} | {bool(trace.larger_equal_second_tie)} |")
    lines += ["", "For example, ES 5RXV source rows 1244–1249 are six bullish bars; row 1250 is bearish, and rows 1251–1252 are bearish. All three have strictly later within-session completion proxies, so row 1250 counts as a two-more success. Row 55 on 2019-11-04 follows seven bullish bars, but rows 56–57 turn bullish and fail. Row 1654 illustrates an equal-second larger-chart tie; its single-chart outcome remains eligible while the primary paired analysis excludes the tie. The [trace table](tables/real_event_traces.csv) pins these identities.", "",
              "## Uncertainty, multiplicity, and limits", "",
              "For each reported rate, the saved tables provide numerator, eligible denominator, distinct session dates, events/date, and a 95% interval based on session-cluster sandwich variance. Matched differences use a joint session-cluster variance. Main positive contrasts use a two-sided Bonferroni interval over 210 prespecified cells, support of at least 300 events, 100 dates, and 2 events/date, plus positive differences in all three periods with at least 30 dates each. Structure and larger-context splits are descriptive. Overlapping signals within a session and transformations of shared trades remain dependent; the cluster interval handles within-session dependence, not dependence across chart settings.", "",
              "The next-bar-start timestamp is a completion proxy, not the final trade time. Same-second order and exact intrabar sequence are unknown. Range XV construction, contracts/rolls, data-feed provenance, and ATAS timezone settings remain unverified. Year/period differences are retrospective; 2024–2026 was already studied. No probability here establishes a profitable trade. Earlier payoff work found that large failures can outweigh frequent small continuations; stops, fills, and costs are not measured here.", "",
              "## Reproduction and evidence", "",
              "The [run manifest](manifest.json) records the frozen plan/settings, input hashes, Git revision and dirty source snapshot, environment lock, exact commands, checks, and artifact hashes. The seven [Parquet event ledgers](events.manifest.json) retain event-level rows. The numeric tables are the authority for every displayed rate; this renderer only selects and formats saved rows. The study README gives the repeatable command sequence. This is a local evidence bundle and has no web publication source."]
    markdown = "\n".join(lines) + "\n"
    (stage / "report.md").write_text(markdown)
    (stage / "report.html").write_text(markdown_html(markdown))
    (stage / "metrics.json").write_text(json.dumps({
        "study_id": "08_countertrend_bar_continuation", "metric_definitions": {
            "p1": "P(C2 follows C1)", "p2": "P(C2 and C3 follow C1)",
            "p3_given_p1": "P(C3 follows C1 given C2 followed C1)",
            "p3_more": "P(C2, C3, and C4 follow C1)",
            "immediate_resumption": "P(C2 resumes original trend)"},
        "headline_screen": {"main_cells": len(main_cells), "supported": supported,
                            "noteworthy_positive": positive,
                            "negative_bonferroni_intervals": negative_adjusted},
        "numeric_authority": ["tables/overall.csv", "tables/lookup.csv", "tables/period.csv",
                              "tables/structure.csv", "tables/larger.csv", "tables/larger_aggregate.csv",
                              "tables/onebar_larger.csv", "tables/run_lengths.csv", "tables/sensitivity.csv"]
    }, indent=2) + "\n")
    print(f"report rendered: {len(lines)} lines; positive headline cells {positive}")


if __name__ == "__main__":
    main()
