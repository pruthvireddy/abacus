"""Render a local session-overlay report from saved numerical evidence only."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import pandas as pd


CHARTS = (("ES", 4), ("ES", 5), ("ES", 6), ("GC", 6), ("GC", 10),
          ("NQ", 10), ("NQ", 20))
SEGMENTS = ("asia", "london", "new_york")
LABELS = {"asia": "Asia", "london": "London/pre-NY", "new_york": "New York"}


def one(frame: pd.DataFrame, **where):
    out = frame
    for key, value in where.items():
        out = out.loc[out[key].eq(value)]
    if len(out) != 1:
        raise ValueError(f"expected one row for {where}, found {len(out)}")
    return out.iloc[0]


def pct(value: float) -> str:
    return f"{value:.2f}%"


def signed(value: float, unit: str) -> str:
    return f"{value:+.2f} {unit}"


def inline(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return value


def as_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out, index = [], 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and re.match(r"^\|[- :|]+\|$", lines[index + 1]):
            headers = [x.strip() for x in line.strip("|").split("|")]
            index += 2
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([x.strip() for x in lines[index].strip("|").split("|")])
                index += 1
            out.append("<div class='scroll'><table><thead><tr>" +
                       "".join(f"<th>{inline(x)}</th>" for x in headers) +
                       "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{inline(x)}</td>" for x in row) +
                               "</tr>" for row in rows) + "</tbody></table></div>")
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line.startswith("- "):
            if index == 0 or not lines[index - 1].startswith("- "):
                out.append("<ul>")
            out.append(f"<li>{inline(line[2:])}</li>")
            if index + 1 == len(lines) or not lines[index + 1].startswith("- "):
                out.append("</ul>")
        else:
            out.append(f"<p>{inline(line)}</p>")
        index += 1
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>Range XV session overlay</title><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<style>body{font:16px/1.55 system-ui,sans-serif;background:#f7f9fa;color:#17232a;margin:0}"
        "main{max-width:1200px;margin:auto;padding:2rem}h1,h2{line-height:1.2}h2{margin-top:2.4rem}"
        "p,li{max-width:94ch}.scroll{overflow:auto;margin:1rem 0 1.7rem}"
        "table{border-collapse:collapse;background:white;font-size:.86rem;white-space:nowrap}"
        "th,td{border:1px solid #d5e0e4;padding:.42rem .6rem;text-align:right}"
        "th:first-child,td:first-child{text-align:left}th{background:#e7f1f4;position:sticky;top:0}"
        "tr:nth-child(even){background:#f0f5f7}a{color:#12617a}code{background:#eaf0f2;padding:.1rem .25rem}"
        "</style><main>" + "\n".join(out) + "</main></html>\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    stage = args.stage.resolve()
    tables = stage / "tables"
    checks = json.loads((stage / "checks.json").read_text())
    audit = json.loads((stage / "audit.json").read_text())
    assert checks["status"] == "pass"
    frames = {name: pd.read_csv(tables / f"{name}.csv") for name in (
        "07_summary", "07_period", "08_summary", "08_period", "08_prior_bin",
        "09_summary", "09_period", "09_opportunity", "09_age_two")}
    s07, s08, s09 = frames["07_summary"], frames["08_summary"], frames["09_summary"]
    p09, o09 = frames["09_period"], frames["09_opportunity"]
    w08 = s08.loc[s08.standout].sort_values(["product", "setting", "direction", "segment"])
    w09 = s09.loc[s09.standout].sort_values(["product", "setting", "direction", "segment"])
    specific = s09.loc[s09.segment_specific]
    if len(specific) != 1:
        raise ValueError("report example requires one segment-specific cell")
    x = specific.iloc[0]
    identity = {"product": x["product"], "setting": int(x.setting),
                "direction": int(x.direction), "segment": x.segment}
    immediate = one(o09, **identity, metric="immediate_mean_ticks")
    wait = one(o09, **identity, metric="wait_mean_ticks_per_c1")
    price_delta = one(o09, **identity, metric="wait_minus_immediate_ticks")
    age_two = one(frames["09_age_two"], **identity)
    immediate_success = one(o09, **identity, metric="immediate_two_per_c1")
    wait_success = one(o09, **identity, metric="wait_two_per_c1")
    overall_wait_negative = int((o09.loc[o09.segment.isin(SEGMENTS) &
        o09.metric.eq("wait_mean_ticks_per_c1"), "estimate"] < 0).sum())
    wait_count = int((o09.segment.isin(SEGMENTS) &
                      o09.metric.eq("wait_mean_ticks_per_c1")).sum())
    positive_07 = s07.loc[s07.screened & s07.estimate.gt(0)].sort_values(
        "estimate", ascending=False)
    lines = [
        "# Asia, London, and New York across the last three Range XV studies", "",
        "Study `10_range_xv_session_overlay`. This is an exploratory overlay on immutable saved events from studies 07–09. Their samples and outcome horizons differ; none of the rates or tick means below are pooled across studies.", "",
        "## Answer", "",
        f"**Study 07:** {int(s07.standout.sum())} of {int(s07.screened.sum())} candidate-price contrasts meets the exploratory segment screen after a two-tick round-trip haircut. Only {len(positive_07)} candidate segment has a positive net point estimate, and its familywise lower interval is below zero. No Asia, London, or New York price edge stands out.", "",
        f"**Study 08:** {len(w08)} of {int(s08.screened.sum())} chart/direction segments have a higher C2+C3 continuation rate than that chart and direction's other two named segments under the exploratory screen. All {len(w08)} are NQ 10RXV; the lifts are small. These are bar-count differences, not returns.", "",
        f"**Study 09:** {len(w09)} of {int(s09.screened.sum())} broad segments beat an ordinary same-direction two-bar pair on C3+C4 continuation. Only {len(specific)} also beats the confirmed candidate's other two segments after its separate familywise screen: {x['product']} {int(x.setting)}RXV {'bearish' if x.direction == -1 else 'bullish'} in {LABELS[x.segment]}. Its C3+C4 rate is {pct(x.estimate)} ({int(x.numerator):,}/{int(x.denominator):,}), {signed(x.ordinary_difference, 'pp')} above ordinary pairs and {signed(x.other_difference, 'pp')} above confirmed candidates in Asia plus New York. The wait-policy mean signed chart-price proxy remains negative in {overall_wait_negative} of {wait_count} named-segment chart/direction cells.", "",
        "These are selected historical reads. NQ settings in studies 08 and 09 reuse underlying trades, and study 07's short history overlaps the long-history studies. The inferred ATAS/New York clock needs direct configuration verification; a fresh unseen export is required to validate a segment rule.", "",
        "## Segment and inference rules", "",
        "Use strict decision-time completion in inferred New York wall time: Asia 18:00–03:00; London/pre-NY 03:00–09:30; New York 09:30–16:00. The 16:00–18:00 transition is retained in each summary CSV but excluded from the three-way screen. These are half-open windows. Study 08 is grouped at C1 completion; study 09's confirmed/ordinary comparison at C2/B2 completion, while its per-original-C1 opportunity/price table uses C1 completion. Study 07's wait and early policies share the original signal's completion segment.", "",
        "Minimum support is 300 candidate events on 100 session dates with at least two events/date. Each of three chronological blocks must have at least 30 candidate dates and a positive contrast for a standout. Session-cluster sandwich intervals use shared-date joint scores for contrasts. Separate two-sided Bonferroni families cover 27 study 07 idea/product/segment comparisons, 42 study 08 segment-vs-other comparisons, 42 study 09 candidate-vs-ordinary comparisons, and 42 study 09 segment-vs-other comparisons. The correction limits a search within each family, but does not turn previously inspected data into prospective confirmation.", "",
        "## Study 07: chart-price payoff after two ticks", "",
        "Each cell below is candidate mean net ticks per original opportunity, followed by its difference from the original same-idea control in ticks. The wait policy retains unconfirmed opportunities with zero return and no cost. [Complete summary](tables/07_summary.csv) gives opportunities, executed trades, dates, gross means, ordinary and familywise intervals, and transition rows; [development/validation/final rows](tables/07_period.csv) preserve stability and negative results.", "",
        "| Product; idea | Asia net; Δ | London net; Δ | New York net; Δ |",
        "|---|---:|---:|---:|",
    ]
    for product in ("ES", "GC", "NQ"):
        for idea in ("pullback", "exhaustion", "quiet_breakout"):
            cells = []
            for label in SEGMENTS:
                row = one(s07, product=product, idea=idea, segment=label)
                cells.append(f"{row.estimate:+.2f}; {row.difference:+.2f} ({int(row.denominator):,})")
            lines.append(f"| {product}; {idea.replace('_', ' ')} | " + " | ".join(cells) + " |")
    if len(positive_07):
        best = positive_07.iloc[0]
        lines += ["", f"The highest net point estimate is {best['product']} {best.idea.replace('_', ' ')} in {LABELS[best.segment]}: {signed(best.estimate, 'ticks')} per opportunity. Its 27-comparison candidate net interval is [{best.candidate_net_family_low:+.2f}, {best.candidate_net_family_high:+.2f}] ticks; the candidate-minus-control family interval is [{best.family_ci_low:+.2f}, {best.family_ci_high:+.2f}] ticks. This does not pass the screen.", ""]
    lines += ["Study 07's saved payoff outcomes were computed on the earlier export-clock bytes. The [clock migration record](../../../docs/migration/range-xv-clock-normalization-20260924.json) documents that session dates and completion statuses did not change. This overlay joins each saved signal index to the same row in its current normalized enhanced file and uses only the corrected completion wall time for the segment label. The quiet-breakout cohort and half-hour calibration still reflect the old clock and need a separate corrected-clock study. The study 07 date span is shorter than studies 08/09.", "",
              "## Study 08: first countertrend C1 after 3+ bars", "",
              "The following rows passed the **exploratory** segment-vs-other screen for P(C2 and C3 both follow C1). Rates and differences use percentage points; the interval is corrected across 42 comparisons. [All chart/direction/segment rows](tables/08_summary.csv), [three periods](tables/08_period.csv), and [prior-run bins](tables/08_prior_bin.csv) include negative and unsupported cells.", "",
              "| Chart; C1 direction | Segment | Successes/eligible | Rate | Versus other two segments [familywise CI] |",
              "|---|---|---:|---:|---:|"]
    for _, row in w08.iterrows():
        lines.append(f"| {row['product']} {int(row.setting)}RXV; {'bearish' if row.direction == -1 else 'bullish'} | {LABELS[row.segment]} | {int(row.numerator):,}/{int(row.denominator):,} | {pct(row.estimate)} | {signed(row.difference, 'pp')} [{row.family_ci_low:+.2f}, {row.family_ci_high:+.2f}] |")
    lines += ["", "NQ 10RXV is one chart setting, and its bullish/bearish segments share the same underlying trades. The selected differences are under two percentage points. No prior-run-length × session × direction cell passed study 08's original frozen 210-cell screen; this combined three-segment overlay answers a different, exploratory question.", "",
              "## Study 09: C2 confirmation and ordinary two-bar pairs", "",
              "Each cell shows P(C3 and C4 follow after C2 confirms) and its percentage-point difference from the ordinary B1/B2 baseline in that segment. [Full candidate and baseline table](tables/09_summary.csv) has counts, dates, uncertainty, segment-vs-other differences, and transition; [period rows](tables/09_period.csv) show chronology.", "",
              "| Chart; C2 direction | Asia rate; Δ ordinary | London rate; Δ ordinary | New York rate; Δ ordinary |",
              "|---|---:|---:|---:|"]
    for product, setting in CHARTS:
        for direction in (-1, 1):
            cells = []
            for label in SEGMENTS:
                row = one(s09, product=product, setting=setting,
                          direction=direction, segment=label)
                cells.append(f"{pct(row.estimate)} ({row.ordinary_difference:+.2f} pp)")
            lines.append(f"| {product} {setting}; {'bearish' if direction == -1 else 'bullish'} | " +
                         " | ".join(cells) + " |")
    lines += ["", "The rows passing the candidate-vs-ordinary familywise and three-period screen are:", "",
              "| Chart; direction | Segment | Successes/decisions | Δ ordinary [familywise CI] | Δ other segments [familywise CI] | Segment-specific? |",
              "|---|---|---:|---:|---:|---|"]
    for _, row in w09.iterrows():
        lines.append(f"| {row['product']} {int(row.setting)}; {'bearish' if row.direction == -1 else 'bullish'} | {LABELS[row.segment]} | {int(row.numerator):,}/{int(row.denominator):,} | {row.ordinary_difference:+.2f} [{row.ordinary_family_ci_low:+.2f}, {row.ordinary_family_ci_high:+.2f}] pp | {row.other_difference:+.2f} [{row.other_family_ci_low:+.2f}, {row.other_family_ci_high:+.2f}] pp | {'yes' if row.segment_specific else 'no'} |")
    periods = p09.loc[p09["product"].eq(x["product"]) & p09.setting.eq(x.setting) &
        p09.direction.eq(x.direction) & p09.segment.eq(x.segment)]
    periods = periods.set_index("block").loc[["early", "middle", "recent"]]
    lines += ["", f"For the one segment-specific row, the other-segment differences in 2019–2021, 2022–2023, and 2024–2026 are {', '.join(f'{v:+.2f}' for v in periods.other_difference)} pp. These periods were previously inspected. The corresponding ordinary-pair differences are {', '.join(f'{v:+.2f}' for v in periods.ordinary_difference)} pp.", "",
              f"The post-result run-age diagnostic restricts ordinary B2 bars to exactly bar two of their run. In the selected {LABELS[x.segment]} row, that ordinary baseline is {pct(age_two.baseline_estimate)}, leaving a {signed(age_two.difference, 'pp')} candidate difference with an ordinary 95% session-cluster interval [{age_two.difference_ci_low:+.2f}, {age_two.difference_ci_high:+.2f}] pp. [All run-age-two segment rows](tables/09_age_two.csv) are retained. This restriction was introduced after study 09's primary result and does not validate the selected segment.", "",
              "### Common original C1 opportunity and chart-price check", "",
              f"At {x['product']} {int(x.setting)}RXV {'bearish' if x.direction == -1 else 'bullish'} C1 decisions in {LABELS[x.segment]}, the immediate C2+C3 directional success rate is {pct(immediate_success.estimate)} ({int(immediate_success.numerator):,}/{int(immediate_success.denominator):,}); confirmation plus C3+C4 is {pct(wait_success.estimate)} ({int(wait_success.numerator):,}/{int(wait_success.denominator):,}) per original C1. They are different two-bar horizons. The immediate open-to-open proxy averages {signed(immediate.estimate, 'ticks')} per C1 [{immediate.ci_low:+.2f}, {immediate.ci_high:+.2f}], while the wait proxy, assigning zero to unconfirmed C1s, averages {signed(wait.estimate, 'ticks')} [{wait.ci_low:+.2f}, {wait.ci_high:+.2f}]. The paired wait-minus-immediate mean is {signed(price_delta.estimate, 'ticks')} [{price_delta.ci_low:+.2f}, {price_delta.ci_high:+.2f}]. [All segment opportunity and price rows](tables/09_opportunity.csv) are retained. These are unadjusted chart references, not fills or strategy returns.", "",
              "## Audit and use", "",
              f"The [checks](checks.json) pass for {checks['verified_input_files']} pinned files, including sealed event ledgers and the normalized short-history clock files. Nine study 07 signals were spot-traced to corrected source rows; full event-row, source-clock, session-date, and strict-completion identity were checked during mapping. Study 07 whole-cohort payoff arithmetic reconciles to its original report tables; 08 and 09 session totals, chronological rows, and 09 price means reconcile to their sealed saved tables. [Extraction audit](audit.json) records mapped counts and traces; the [input lock](inputs.lock.json) and [run manifest](manifest.json) record identities and artifact hashes.", "",
              "GC export gaps and differing 2026 sessions remain as disclosed by studies 08/09. The ATAS timezone, feed, and contract settings were not independently verified. Session labels are conditional on the documented clock inference. A fresh, unseen export with those settings verified is the next validation gate; study 07's quiet-breakout condition also requires a corrected-clock rerun before a session claim about that idea.", "",
              "Source evidence: [study 07](../../07_range_xv_edge_candidates/20260924T004900Z_rxv07/report.md), [study 08](../../08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/report.md), and [study 09](../../09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/report.md). This bundle is local research and was not published to a website."]
    markdown = "\n".join(lines) + "\n"
    (stage / "report.md").write_text(markdown)
    (stage / "report.html").write_text(as_html(markdown))
    (stage / "metrics.json").write_text(json.dumps({
        "study_id": "10_range_xv_session_overlay", "status": "exploratory",
        "screens": audit["screens"], "numeric_authority": [f"tables/{name}.csv" for name in frames],
        "segment_definitions": {"asia": "18:00-03:00", "london": "03:00-09:30",
                                "new_york": "09:30-16:00", "transition": "16:00-18:00"}}, indent=2) + "\n")
    (stage / "advice.md").write_text(
        "# Dated interpretation — 2026-09-24\n\n" +
        f"No study 07 price candidate passes the three-segment screen after two ticks (`tables/07_summary.csv`). " +
        f"Study 08 has {len(w08)} small NQ 10RXV continuation differences versus other named segments (`tables/08_summary.csv`). " +
        f"Study 09 has {len(w09)} C2-confirmed differences versus ordinary pairs, but only " +
        f"{len(specific)} is also segment-specific: {x['product']} {int(x.setting)}RXV " +
        f"{'bearish' if x.direction == -1 else 'bullish'} in {LABELS[x.segment]} " +
        "(`tables/09_summary.csv`). Its wait-policy chart-price mean per original C1 is negative " +
        "(`tables/09_opportunity.csv`). These retrospective, correlated chart settings are " +
        "not a validated trading rule. Verify ATAS clock/feed/contract settings and use a fresh " +
        "unseen export before testing a prespecified session filter. Study 07 quiet-breakout " +
        "calibration needs a separate corrected-clock rerun.\n")
    print(f"rendered report: 07={int(s07.standout.sum())}, 08={len(w08)}, "
          f"09={len(w09)}, specific={len(specific)}")


if __name__ == "__main__":
    main()
