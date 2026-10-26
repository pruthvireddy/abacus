"""Render the study 09 local report from saved CSV and audit artifacts only."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import pandas as pd


CHARTS=[("ES",4),("ES",5),("ES",6),("GC",6),("GC",10),("NQ",10),("NQ",20)]
WINDOWS=["asia","london_pre_ny","ny_morning","ny_afternoon","transition"]
WINDOW_LABELS={"asia":"Asia","london_pre_ny":"London/pre-NY","ny_morning":"NY morning",
               "ny_afternoon":"NY afternoon","transition":"Transition"}


def pct(value: float, decimals: int = 1) -> str:
    return f"{100*value:.{decimals}f}%"


def interval(row) -> str:
    return f"{pct(row.ci_low)}–{pct(row.ci_high)}"


def row_of(frame: pd.DataFrame, **filters):
    selected=frame
    for column,value in filters.items():
        selected=selected.loc[selected[column]==value]
    if len(selected)!=1:
        raise ValueError(f"expected one row for {filters}; found {len(selected)}")
    return selected.iloc[0]


def rate(row) -> str:
    return f"{pct(row.probability)} ({int(row.numerator):,}/{int(row.denominator):,})"


def escape_inline(line: str) -> str:
    line=html.escape(line)
    line=re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m:f'<a href="{html.escape(m.group(2),quote=True)}">{m.group(1)}</a>',line)
    line=re.sub(r"\*\*([^*]+)\*\*",r"<strong>\1</strong>",line)
    line=re.sub(r"`([^`]+)`",r"<code>\1</code>",line)
    return line


def as_html(markdown: str) -> str:
    lines=markdown.splitlines();out=[];index=0
    while index<len(lines):
        line=lines[index]
        if not line.strip():
            index+=1;continue
        if line.startswith("|") and index+1<len(lines) and re.match(r"^\|[- :|]+\|$",lines[index+1]):
            headers=[x.strip() for x in line.strip("|").split("|")]
            index+=2;rows=[]
            while index<len(lines) and lines[index].startswith("|"):
                rows.append([x.strip() for x in lines[index].strip("|").split("|")]);index+=1
            out.append("<div class='table-scroll'><table><thead><tr>"+
                "".join(f"<th>{escape_inline(x)}</th>" for x in headers)+"</tr></thead><tbody>"+
                "".join("<tr>"+"".join(f"<td>{escape_inline(x)}</td>" for x in row)+"</tr>" for row in rows)+
                "</tbody></table></div>")
            continue
        if line.startswith("#"):
            level=len(line)-len(line.lstrip("#"))
            out.append(f"<h{level}>{escape_inline(line[level:].strip())}</h{level}>")
        elif line.startswith("- "):
            if index==0 or not lines[index-1].startswith("- "):out.append("<ul>")
            out.append(f"<li>{escape_inline(line[2:])}</li>")
            if index+1==len(lines) or not lines[index+1].startswith("- "):out.append("</ul>")
        else:
            out.append(f"<p>{escape_inline(line)}</p>")
        index+=1
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><title>RXV C2 confirmation</title>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<style>body{font:16px/1.5 system-ui,sans-serif;color:#182229;background:#f7f9fa;margin:0}"
        "main{max-width:1180px;margin:auto;padding:2rem}h1,h2,h3{line-height:1.2}h2{margin-top:2.5rem}"
        "p,li{max-width:94ch}.table-scroll{overflow:auto;margin:1rem 0 1.7rem}table{border-collapse:collapse;background:white;font-size:.84rem;white-space:nowrap}"
        "th,td{border:1px solid #dae0e4;padding:.38rem .55rem;text-align:right}th:first-child,td:first-child{text-align:left}"
        "th{background:#e7f0f3;position:sticky;top:0}tr:nth-child(even){background:#f2f6f7}"
        "a{color:#14627c}code{background:#eaf0f2;padding:.1rem .25rem}</style><main>"+
        "\n".join(out)+"</main></html>\n")


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--stage",required=True,type=Path)
    args=parser.parse_args();stage=args.stage.resolve();tables=stage/"tables"
    checks=json.loads((stage/"checks.json").read_text())
    audit=json.loads((stage/"audit.json").read_text())
    assert checks["status"]=="pass"
    frames={name:pd.read_csv(tables/f"{name}.csv") for name in (
        "overall","comparison","period","opportunity_overall","opportunity_window",
        "opportunity_period","price","price_delta","headline_screen","age2_overall",
        "age2_comparison","age2_period","snapback","gc_sensitivity",
        "prior_bin","prior_bin_opportunity","snapback_tie_sensitivity",
        "real_event_traces")}
    overall=frames["overall"];comparison=frames["comparison"];period=frames["period"]
    opportunities=frames["opportunity_overall"];price=frames["price"]
    screen=frames["headline_screen"];age2=frames["age2_comparison"]
    traces=frames["real_event_traces"]
    winners=screen.loc[screen.noteworthy_positive].sort_values(
        ["product","setting","direction","decision_window"])
    negative_price=int((frames["price_delta"].mean_signed_ticks<0).sum())
    confirmed_range=overall.loc[overall.metric=="next2","probability"]
    confirmation_range=opportunities.loc[opportunities.metric=="c2_confirms","probability"]
    immediate_range=opportunities.loc[opportunities.metric=="immediate_two_per_c1","probability"]
    wait_range=opportunities.loc[opportunities.metric=="wait_two_per_c1","probability"]
    lines=[
        "# Does waiting for C2 improve a first countertrend reversal read?", "",
        "Study `09_range_xv_c2_confirmation`; new long-history local run. All rates and price values below are selected from the saved numerical CSVs. This is a retrospective chart-behavior comparison, not an execution study.","",
        "## Answer", "",
        f"A C2 candle confirms the first countertrend C1 after 3+ prior trend bars in **{pct(confirmation_range.min())}–{pct(confirmation_range.max())}** of common eligible C1 opportunities. Once C2 confirms, the next **two** candles, C3 and C4, both follow in **{pct(confirmed_range.min())}–{pct(confirmed_range.max())}** of decisions across charts and directions. This is a later two-bar horizon than the C2+C3 outcome observed at C1.","",
        f"The frozen candidate-versus-ordinary screen finds **{len(winners)} of {len(screen)}** positive chart/direction/session-window contrasts, with {int(screen.supported.sum())} cells meeting minimum support. The positives are concentrated in GC and bearish NQ 10RXV, usually about 1–2 percentage points above ordinary two-bar states. The post-result check against ordinary pairs that are also exactly two bars old reduces, but does not erase, those example differences. This age-matched check is exploratory and cannot validate the selected cells.","",
        f"Waiting is selective: on the same original C1 opportunity set, the rate of an immediate two-bar directional success is **{pct(immediate_range.min())}–{pct(immediate_range.max())}**, while a C2 confirmation followed by **two additional** bars occurs **{pct(wait_range.min())}–{pct(wait_range.max())}** of the time. Waiting skips non-confirming opportunities and shifts the measured horizon by one bar. The signed open-to-open chart-price proxy for the wait policy is negative on average in every chart/direction. Its difference from the immediate proxy is negative in {negative_price} of {len(frames['price_delta'])} chart/direction cases. These numbers do not show a profitable trade.","",
        "## Frozen definitions", "",
        "C1 is the first non-doji bar opposite an uninterrupted prior run within one inferred 18:00 New York session. Main signals have at least three prior bars. C2 confirms only if it closes in C1's direction. At C2's strictly later next-bar-start completion proxy, ask whether C3 and C4 both close in that direction. C1 and C2 are excluded from those two future bars. A doji fails continuation. C1 through C4 must each have a strict within-session completion proxy, so C5's start is available for the price proxy. Equal-second and session/export-boundary cases are excluded, not counted as failures.","",
        "Ordinary B1/B2 pairs are adjacent same-direction non-doji bars observed at B2 completion, excluding the main C1/C2 candidate pairs. Their B3/B4 outcome uses the same strict completion rule. The baseline is matched within chart, direction, and decision-time window; it includes both early and mature ordinary runs. The exploratory age-two baseline restricts B2 to exactly bar two of its run. Neither comparison is causal.","",
        "The enhanced timestamps are already inferred New York wall time; no second conversion was applied. Half-open decision windows are Asia 18:00–03:00, London/pre-NY 03:00–09:30, NY morning 09:30–12:00, NY afternoon 12:00–16:00, and transition 16:00–18:00. Daylight saving is reflected in those stored wall times. ATAS timezone configuration remains unverified, so the labels are conditional on the clock interpretation.","",
        "## C2 decision: chart and direction baselines", "",
        "Candidate and ordinary rates below share the C2/B2 decision horizon. Each candidate rate has a 95% session-cluster interval. The ordinary baseline and the difference are in the [full overall table](tables/overall.csv), with numerator, denominator, dates, events/date, both intervals, and the joint session-cluster difference interval. Charts remain separate because settings of one product share trades.","",
        "| Chart | C2 direction | C3 follows | C3+C4 both follow | Ordinary B3+B4 | Difference | Candidate dates; events/date |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for product,setting in CHARTS:
        for d in (-1,1):
            one=row_of(overall,product=product,setting=setting,direction=d,metric="next1")
            two=row_of(overall,product=product,setting=setting,direction=d,metric="next2")
            lines.append(f"| {product} {setting}RXV | {'bearish' if d==-1 else 'bullish'} | {rate(one)} [{interval(one)}] | {rate(two)} [{interval(two)}] | {pct(two.baseline_probability)} ({int(two.baseline_numerator):,}/{int(two.baseline_denominator):,}) | {two.difference_pp:+.2f} pp [{two.difference_ci_low_pp:+.2f}, {two.difference_ci_high_pp:+.2f}] | {int(two.session_dates):,}; {two.events_per_session:.1f} |")
    lines += ["", "The [full overall table](tables/overall.csv) also has P(C4 follows | C3 followed), with its smaller conditional denominator and interval. The matched baseline has the analogous B4|B3 outcome. [Prior-run bins](tables/prior_bin.csv) retain the prespecified 3–4, 5–7, and 8+ candidate splits, and [bin opportunity counts](tables/prior_bin_opportunity.csv) preserve their original C1 denominators; these are descriptive and share the overall ordinary baseline.","",
              "## Decision-time session lookup", "",
              "Each cell shows the candidate probability that C3 and C4 both follow C2 and its difference in percentage points from the ordinary two-bar baseline. The [full 70-cell comparison](tables/comparison.csv) records all numerator/denominator, dates, events/date, intervals, and baseline values; [period rows](tables/period.csv) show 2019–2021, 2022–2023, and 2024–2026 separately.","",
              "| Chart; C2 direction | Asia | London/pre-NY | NY morning | NY afternoon | Transition |",
              "|---|---:|---:|---:|---:|---:|"]
    for product,setting in CHARTS:
        for d in (-1,1):
            cells=[]
            for window in WINDOWS:
                x=row_of(screen,product=product,setting=setting,direction=d,decision_window=window)
                cells.append(f"{pct(x.probability)} ({x.difference_pp:+.2f} pp)")
            lines.append(f"| {product} {setting}; {'bearish' if d==-1 else 'bullish'} | "+" | ".join(cells)+" |")
    lines += ["", "## Supported positive contrasts and run-age check", "",
              "The prespecified positive screen requires at least 300 candidates, 100 session dates, and 2 candidates/date; a two-sided Bonferroni lower interval above zero across 70 contrasts; and positive differences in all three chronological periods with at least 30 candidate dates each. The post-result age-two comparison is shown for diagnosis with ordinary 95% intervals only. It was not in the frozen screen.","",
              "| Chart; C2; window | C3+C4 follows [95% CI] | Dates; events/date | Ordinary rate; Δ and familywise CI | Three period Δ (pp) | Age-two ordinary; Δ [95% CI] |",
              "|---|---:|---:|---:|---:|---:|"]
    for _,x in winners.iterrows():
        product,setting,d,window=x["product"],int(x.setting),int(x.direction),x.decision_window
        blocks=[row_of(period,product=product,setting=setting,direction=d,
                       decision_window=window,block=b,metric="next2") for b in ("early","middle","recent")]
        age=row_of(age2,product=product,setting=setting,direction=d,
                   decision_window=window,metric="next2")
        lines.append(f"| {product} {setting}; {'bearish' if d==-1 else 'bullish'}; {WINDOW_LABELS[window]} | {rate(x)} [{interval(x)}] | {int(x.session_dates):,}; {x.events_per_session:.1f} | {pct(x.baseline_probability)}; {x.difference_pp:+.2f} pp [{x.family_ci_low_pp:+.2f}, {x.family_ci_high_pp:+.2f}] | "+", ".join(f"{b.difference_pp:+.2f}" for b in blocks)+f" | {pct(age.baseline_probability)} ({int(age.baseline_numerator):,}/{int(age.baseline_denominator):,}); {age.difference_pp:+.2f} pp [{age.difference_ci_low_pp:+.2f}, {age.difference_ci_high_pp:+.2f}] |")
    lines += ["", "[All age-two results](tables/age2_comparison.csv), including negatives and sparse windows, are retained. GC and NQ positives are small relative to the roughly 40% ordinary two-more rate. ES shows no positive cell under the frozen screen. The periods are historical, and the recent years were already inspected in earlier RXV work; a new export is needed before treating any cell as a validated rule.","",
              "## What waiting costs per original C1", "",
              "The following table keeps **every** strictly eligible main C1 in the denominator. C2 confirmation is the fraction for which the wait policy would act. Immediate success means C2 and C3 follow C1; wait success means C2 confirms and C3 and C4 follow. The horizons differ by one candle. Each cell shows numerator/denominator, rate, and 95% session-cluster interval; the dates and event density apply to the common C1 sample.","",
              "| Chart; C1 direction | C2 confirms | Immediate two after C1 | Wait confirms + two after C2 | Dates; C1/date |",
              "|---|---:|---:|---:|---:|"]
    for product,setting in CHARTS:
        for d in (-1,1):
            identity=dict(product=product,setting=setting,direction=d)
            confirm=row_of(opportunities,**identity,metric="c2_confirms")
            immediate=row_of(opportunities,**identity,metric="immediate_two_per_c1")
            wait=row_of(opportunities,**identity,metric="wait_two_per_c1")
            lines.append(f"| {product} {setting}; {'bearish' if d==-1 else 'bullish'} | {rate(confirm)} [{interval(confirm)}] | {rate(immediate)} [{interval(immediate)}] | {rate(wait)} [{interval(wait)}] | {int(confirm.session_dates):,}; {confirm.events_per_session:.1f} |")
    lines += ["", "C2 failures and dojis remain visible in [opportunity outcomes](tables/opportunity_overall.csv). That table also reports P(C3 returns to the original trend | C2 did not confirm), with its conditional numerator, denominator, session dates, event density, and interval. [C1-window](tables/opportunity_window.csv) and [period](tables/opportunity_period.csv) tables preserve the full opportunity-set counts.","",
              "## Two-bar chart-price movement and adverse excursion", "",
              "Immediate uses C2 open→C4 open and C2/C3 extrema; wait uses C3 open→C5 open and C3/C4 extrema. These are chart references, **not fills**. The wait-per-C1 mean assigns zero movement to opportunities without confirmation. Mean signed ticks and its 95% session-cluster interval are shown below; the paired wait-minus-immediate interval uses each original C1. The [price table](tables/price.csv) includes medians, 5th-percentile movement, and mean/median/90th-percentile maximum adverse excursion for each policy. [Paired differences](tables/price_delta.csv) retain the exact mean and interval.","",
              "| Chart; C1 | Immediate mean ticks [95% CI] | Wait mean per C1 [95% CI] | Wait − immediate [95% CI] | Wait confirmed p05 ticks; median/90th MAE ticks |",
              "|---|---:|---:|---:|---:|"]
    for product,setting in CHARTS:
        for d in (-1,1):
            identity=dict(product=product,setting=setting,direction=d)
            immediate=row_of(price,**identity,policy="immediate_per_c1")
            wait=row_of(price,**identity,policy="wait_per_c1")
            confirmed=row_of(price,**identity,policy="wait_confirmed")
            delta=row_of(frames["price_delta"],**identity)
            lines.append(f"| {product} {setting}; {'bearish' if d==-1 else 'bullish'} | {immediate.mean_signed_ticks:+.2f} [{immediate.mean_ci_low:+.2f}, {immediate.mean_ci_high:+.2f}] | {wait.mean_signed_ticks:+.2f} [{wait.mean_ci_low:+.2f}, {wait.mean_ci_high:+.2f}] | {delta.mean_signed_ticks:+.2f} [{delta.mean_ci_low:+.2f}, {delta.mean_ci_high:+.2f}] | {confirmed.p05_signed_ticks:.0f}; {confirmed.median_mae_ticks:.0f}/{confirmed.p90_mae_ticks:.0f} |")
    lines += ["", "A positive bar-count difference does not imply a price advantage. Medians on confirmed decisions are positive in many charts while mean signed ticks are negative, showing an unfavorable tail in this proxy. The data lack bid/ask, fees, slippage, exact completions, and intrabar order. The two policies also act at different times and have different exposure. No stop or target outcome is inferred.","",
              "## One-bar aligned snapbacks are a separate setup", "",
              "For paired charts, the latest larger bar must have completed strictly before C1 and point in C1's direction; equal-second larger ties are excluded. One-bar aligned snapbacks have a higher C2 confirmation frequency, but their post-C2 two-more rates remain close to ordinary pairs. This secondary context must not be used as the first-reversal-after-3+ rate. [Full snapback estimates](tables/snapback.csv) include numerator, denominator, date count, event density, intervals, and ordinary baseline comparisons. [Equal-second tie sensitivity](tables/snapback_tie_sensitivity.csv) shows the same rates with ties included and for ties alone, using only the latest strictly prior larger state in every case.","",
              "| Pair; C1 direction | C2 confirms | C3+C4 follows after confirmation | Ordinary two-bar baseline |",
              "|---|---:|---:|---:|"]
    for product,setting in [("ES",4),("ES",5),("GC",6),("NQ",10)]:
        for d in (-1,1):
            identity=dict(product=product,setting=setting,direction=d,context="onebar_aligned")
            c2=row_of(frames["snapback"],**identity,metric="c2_confirms")
            later=row_of(frames["snapback"],**identity,metric="next2")
            lines.append(f"| {product} {setting}; {'bearish' if d==-1 else 'bullish'} | {rate(c2)} [{interval(c2)}] | {rate(later)} [{interval(later)}] | {pct(later.baseline_probability)} |")
    lines += ["", "## Data audit, sensitivity, and traces", "",
              "The pinned manifest and all source/enhanced hashes were checked before extraction. All seven enhanced files passed row count, session-date count, completion-status count, source-row continuity, nondecreasing start time, and OHLC checks. No bars were filled. The table shows counts after the five declared GC session exclusions; completion/boundary exclusions were counted before GC removal.","",
              "| Chart | Bars | Observed session dates | C1 signals | Main eligible C1 | C2 confirmed | Ordinary pairs | Main completion/boundary exclusions |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for product,setting in CHARTS:
        x=checks["charts"][f"{product}_{setting}"]
        lines.append(f"| {product} {setting} | {x['bars']:,} | {x['session_dates']:,} | {x['c1_signals']:,} | {x['main_opportunities']:,} | {x['c2_confirmed']:,} | {x['ordinary_pairs']:,} | {x['main_completion_or_boundary_excluded']:,} |")
    lines += ["", "Both GC charts lack 2021-04-02, 2023-04-07, and 2026-04-03 relative to ES/NQ; the files alone do not prove whether those dates were closed or omitted. The primary GC sample excludes 2026-01-28, 02-04, 02-20, 03-19, and 04-02 due to documented differences from older exports, including a major March 19 gap. [GC re-inclusion estimates](tables/gc_sensitivity.csv) change the aggregate candidate rates modestly; other differing GC overlap sessions remain a limitation. See the [long-history audit](../../../docs/range-xv-long-history-20260924.md), [checks](checks.json), [extraction audit](audit.json), and [input lock](inputs.lock.json).", "",
              "Three ES 5RXV C1 events were reconciled with literal source and enhanced CSV rows, including C2–C4 direction and the two open-to-open price proxies when eligible:","",
              "| Session | C1 source row; prior run | C2/C3/C4 rows | Direction path | C2 confirms; later two succeed | C1/C2 completion wall time |",
              "|---|---:|---:|---|---|---|"]
    for _,x in traces.iterrows():
        lines.append(f"| {x.session_date} | {int(x.c1_source_row):,}; {int(x.prior_run)} | {int(x.c2_source_row)}/{int(x.c3_source_row)}/{int(x.c4_source_row)} | {x.direction_path} | {bool(x.c2_confirms)}; {bool(x.wait_two_success)} | {x.c1_completion}; {x.c2_completion} |")
    lines += ["", "The [trace table](tables/real_event_traces.csv) records source-row identities and signed ticks. The original ATAS clock is preserved as `source_timestamp`; the normalized wall time remains inferred from a fixed UTC−04 export-clock pattern, not independently confirmed ATAS settings.","",
              "## Inference and use", "",
              "Each reported probability in the saved tables has its numerator, eligible denominator, distinct session-date count, events/date, and 95% session-cluster sandwich interval. Matched differences use a joint session-cluster score. The frozen headline family contains 70 candidate-versus-ordinary comparisons, corrected with two-sided Bonferroni intervals. Window-level support requires at least 300 candidates, 100 dates, and 2 events/date, plus a positive difference in all three historical periods with at least 30 dates. These are repeated historical reads, not independent experiments; chart settings of the same product and overlapping events remain dependent. The post-result age-two check is exploratory and unadjusted.","",
              "A fresh, genuinely unseen Range XV export with ATAS timezone, session, contract/roll, and feed settings verified is the next validation gate. The present result is a modest chart-state difference in GC and bearish NQ 10RXV, with no evidence that waiting improves a trade after price, costs, and execution are considered.","",
              "## Reproduction and retained evidence", "",
              "The [run manifest](manifest.json) records exact commands, frozen settings, source snapshot, Git/environment identity, input hashes, exclusions, checks, and artifact hashes. The [event manifest](events.manifest.json) identifies the seven C1 opportunity ledgers and seven ordinary-pair ledgers retained in this run. All displayed outcomes derive from the saved numerical tables. This bundle is local research; no web publication was prepared."]
    markdown="\n".join(lines)+"\n"
    (stage/"report.md").write_text(markdown)
    (stage/"report.html").write_text(as_html(markdown))
    (stage/"metrics.json").write_text(json.dumps({
        "study_id":"09_range_xv_c2_confirmation",
        "metric_definitions":{"next1":"P(C3 follows after C2 confirms)",
            "next2":"P(C3 and C4 follow after C2 confirms)",
            "second_given_first":"P(C4 follows given C3 followed)",
            "c2_confirms":"P(C2 follows C1 per original C1)",
            "immediate_two_per_c1":"P(C2 and C3 follow per original C1)",
            "wait_two_per_c1":"P(C2 confirms, C3 and C4 follow per original C1)"},
        "headline_screen":{"comparisons":len(screen),"supported":int(screen.supported.sum()),
                           "noteworthy_positive":len(winners)},
        "age_two_baseline_status":"post-result exploratory sensitivity",
        "numeric_authority":[f"tables/{name}.csv" for name in frames if name!="real_event_traces"]
    },indent=2)+"\n")
    print(f"rendered {len(lines)} lines; {len(winners)} positive headline cells")


if __name__=="__main__":main()
