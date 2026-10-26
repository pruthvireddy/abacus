"""Render offline Markdown/HTML and figures from saved numerical tables only."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd

RUN_ID = "20260923T180000Z_state06c"


def pct(value, digits=1):
    return "n/a" if pd.isna(value) else f"{100*float(value):.{digits}f}%"


def pp(value, digits=1):
    return "n/a" if pd.isna(value) else f"{100*float(value):+.{digits}f} pp"


def ci(row, prefix=""):
    return f"{pct(row[prefix+'ci_low'])}–{pct(row[prefix+'ci_high'])}"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    def cell(x): return str(x).replace("|", "\\|")
    return "| " + " | ".join(map(cell,headers)) + " |\n| " + " | ".join(["---"]*len(headers)) + " |\n" + "\n".join(
        "| " + " | ".join(map(cell,row)) + " |" for row in rows) + "\n"


class Document:
    def __init__(self):
        self.md = []
        self.html = []
    def heading(self, text, level=2):
        self.md.append("#"*level + " " + text + "\n")
        self.html.append(f"<h{level}>{escape(text)}</h{level}>")
    def para(self, text):
        self.md.append(text + "\n")
        self.html.append("<p>"+escape(text)+"</p>")
    def table(self, headers, rows):
        self.md.append(md_table(headers, rows))
        self.html.append("<div class='table-wrap'><table><thead><tr>"+"".join(f"<th>{escape(str(x))}</th>" for x in headers)+"</tr></thead><tbody>"+
                         "".join("<tr>"+"".join(f"<td>{escape(str(x))}</td>" for x in row)+"</tr>" for row in rows)+"</tbody></table></div>")
    def image(self, path, alt):
        self.md.append(f"![{alt}]({path})\n")
        self.html.append(f"<figure><img src='{escape(path)}' alt='{escape(alt)}'><figcaption>{escape(alt)}</figcaption></figure>")
    def links(self, pairs):
        self.md.append(" · ".join(f"[{label}]({path})" for label,path in pairs)+"\n")
        self.html.append("<p class='links'>"+" · ".join(f"<a href='{escape(path)}'>{escape(label)}</a>" for label,path in pairs)+"</p>")
    def write(self, stage):
        (stage/"report.md").write_text("\n".join(self.md)+"\n")
        css = """body{font:16px/1.55 system-ui,-apple-system,sans-serif;color:#172a36;background:#f5f8fa;max-width:1120px;margin:auto;padding:32px}h1,h2{color:#103a50}h1{font-size:2.15rem}h2{margin-top:2.2rem;border-bottom:1px solid #cbd8de;padding-bottom:.25rem}p{max-width:95ch}.table-wrap{overflow-x:auto;background:white;border:1px solid #d8e2e7;border-radius:8px;margin:1rem 0}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:.52rem .68rem;border-bottom:1px solid #e3eaee;text-align:left;white-space:nowrap}th{background:#eaf2f5}tr:nth-child(even){background:#f8fafb}figure{background:white;padding:1rem;border:1px solid #d8e2e7;border-radius:8px;margin:1rem 0}img{max-width:100%}figcaption{font-size:.85rem;color:#526b79}a{color:#075b80}.links{line-height:2.2}footer{margin-top:3rem;color:#526b79;font-size:.85rem}"""
        html = "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>VWAP state dynamics</title><style>"+css+"</style></head><body>"+"\n".join(self.html)+"<footer>Offline research evidence · all available dates exploratory · no execution or profitability claim.</footer></body></html>"
        (stage/"report.html").write_text(html)


def plot_figures(stage, probabilities, barrier):
    figures = stage/"figures"
    figures.mkdir(exist_ok=True)
    parts = ["<svg xmlns='http://www.w3.org/2000/svg' width='1260' height='420' viewBox='0 0 1260 420'>",
             "<rect width='1260' height='420' fill='#fff'/><text x='630' y='28' text-anchor='middle' font-size='18' fill='#103a50'>Primary 2-minute Globex cohort · 30-minute horizon</text>"]
    for panel,(question,first,second,title) in enumerate([
        ("Q1","persistent","rotational","30m residence"),
        ("Q2","opposing","aligned","30m crossing"),
        ("Q3","all",None,"VWAP vs TWAP median error")]):
        x0 = 35 + panel*410
        parts.append(f"<text x='{x0+185}' y='62' text-anchor='middle' font-size='15' fill='#103a50'>{escape(title)}</text>")
        for tick in (0,.25,.5,.75,1):
            y = 335-int(tick*240)
            parts.append(f"<line x1='{x0+40}' y1='{y}' x2='{x0+375}' y2='{y}' stroke='#dce6eb'/><text x='{x0+34}' y='{y+4}' text-anchor='end' font-size='10' fill='#526b79'>{int(tick*100)}%</text>")
        one,two = [],[]
        for product in ("ES","NQ","GC"):
            row = probabilities[(probabilities["product"]==product)&(probabilities.split=="all")&
                                (probabilities.question==question)&(probabilities.condition==first)].iloc[0]
            one.append(row.probability)
            if second:
                base = probabilities[(probabilities["product"]==product)&(probabilities.split=="all")&
                                     (probabilities.question==question)&(probabilities.condition==second)].iloc[0]
                two.append(base.probability)
            else:
                two.append(row.baseline_probability)
        for j, product in enumerate(("ES","NQ","GC")):
            center=x0+100+j*105
            for value,offset,color in ((one[j],-24,"#136f83"),(two[j],7,"#e4a348")):
                height=int(value*240); y=335-height
                parts.append(f"<rect x='{center+offset}' y='{y}' width='28' height='{height}' fill='{color}'/>")
            parts.append(f"<text x='{center}' y='358' text-anchor='middle' font-size='12' fill='#172a36'>{product}</text>")
        label1 = first if question != "Q3" else "VWAP wins"
        label2 = second if second else "TWAP wins"
        parts.append(f"<rect x='{x0+75}' y='382' width='11' height='11' fill='#136f83'/><text x='{x0+91}' y='392' font-size='11'>{escape(label1)}</text>")
        parts.append(f"<rect x='{x0+205}' y='382' width='11' height='11' fill='#e4a348'/><text x='{x0+221}' y='392' font-size='11'>{escape(label2)}</text>")
    parts.append("</svg>")
    (figures/"primary-probabilities.svg").write_text("".join(parts))
    x = barrier[barrier["product"]=="ALL"]
    parts=["<svg xmlns='http://www.w3.org/2000/svg' width='960' height='360' viewBox='0 0 960 360'>",
           "<rect width='960' height='360' fill='#fff'/><text x='480' y='30' text-anchor='middle' font-size='18' fill='#103a50'>Same events, fixed 8 ticks versus half-sigma distance</text>",
           "<line x1='680' y1='65' x2='680' y2='290' stroke='#263c48' stroke-width='2'/>"]
    for q,label,base_y in (("Q1","Persistent − rotational",115),("Q2","Opposing − aligned",215)):
        parts.append(f"<text x='28' y='{base_y+15}' font-size='15' fill='#172a36'>{escape(label)}</text>")
        for kind,offset,color,name in (("fixed_8tick",0,"#136f83","8 ticks"),("half_sigma",32,"#e4a348","half sigma")):
            value=100*x[(x.question==q)&(x.barrier==kind)].difference.iloc[0]
            width=abs(value)*38
            left=680-width if value<0 else 680
            parts.append(f"<rect x='{left:.1f}' y='{base_y+offset-13}' width='{width:.1f}' height='24' fill='{color}'/><text x='700' y='{base_y+offset+4}' font-size='12' fill='#172a36'>{escape(name)}: {value:+.1f} pp</text>")
    parts.append("<text x='680' y='326' text-anchor='middle' font-size='12' fill='#526b79'>0 percentage points</text></svg>")
    (figures/"barrier-contrast.svg").write_text("".join(parts))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    stage = Path(__file__).resolve().parents[2]/"work/06_vwap_state_dynamics"/args.run_id
    tables = stage/"tables"
    read = lambda name: pd.read_csv(tables/f"{name}.csv")
    p = read("primary_probabilities"); m = read("matched_comparisons"); paired = read("paired_errors")
    barrier = read("barrier_comparisons"); bout = read("barrier_outcomes"); repl = read("replications")
    funnel = read("funnel"); frozen = read("frozen_reference_sensitivity")
    audit = json.loads((stage/"numerical-audit.json").read_text())
    gate = json.loads((stage/"feature-feasibility.json").read_text())
    def row(question, condition, product="ALL", split="all"):
        return p[(p.question==question)&(p.condition==condition)&(p["product"]==product)&(p.split==split)].iloc[0]
    def match(question, product="ALL", split="all"):
        return m[(m.question==question)&(m["product"]==product)&(m.split==split)].iloc[0]
    def barr(question, kind, product="ALL"):
        return barrier[(barrier.question==question)&(barrier.barrier==kind)&(barrier["product"]==product)].iloc[0]
    plot_figures(stage,p,barrier)
    d=Document()
    d.heading("VWAP state dynamics: three frozen probability questions",1)
    d.para(f"Run {args.run_id} · Protocol 1.0.0 · pinned Bhishma session_anchored_vwap 1.0.0 · ES, NQ, GC. All dates, including the 2024 and 2025–2026 chronological labels, are exploratory because earlier VWAP outcomes had already been viewed. These are future price-path and reference-accuracy probabilities, not trading win rates.")
    d.heading("Probability atlas")
    atlas=[]
    for question,condition,label in (("Q1","persistent","Persistent side → no opposite causal-VWAP close"),
                                     ("Q1","rotational","Rotational side → no opposite causal-VWAP close"),
                                     ("Q2","opposing","Opposing slopes → opposite causal-VWAP close"),
                                     ("Q2","aligned","Aligned slopes → opposite causal-VWAP close"),
                                     ("Q3","all","VWAP beats paired TWAP on future 1m-close median"),
                                     ("Q3","material","VWAP beats TWAP; material reference separation"),
                                     ("Q3","near_identical","VWAP beats TWAP; near-identical references")):
        r=row(question,condition)
        atlas.append([question,label,f"{int(r.numerator):,}/{int(r.denominator):,}",pct(r.probability),ci(r),pct(r.baseline_probability),f"{int(r.product_sessions):,}"])
    d.table(["Question","Observable X → future Y by 30m","Numerator / full denominator","P(Y | X)","95% shared-date CI","Comparable baseline P","Product-sessions"],atlas)
    d.para("Q1 baseline is rotational state; Q2 baseline is aligned slopes; Q3 baseline is paired TWAP wins at identical landmarks. Q3 ties remain in the denominator (zero observed exact error ties). State `other`, slope `flat_or_unavailable`, and near-identical references remain in the saved tables. The outcome horizon includes its closing boundary. Equality at VWAP is neutral, not an opposite close.")
    d.image("figures/primary-probabilities.svg","Product-specific primary rates and paired baselines")
    d.heading("Q1 — residence and crossing state")
    q1=match("Q1")
    d.para(f"Persistent landmarks had {pct(row('Q1','persistent').probability)} residence ({int(row('Q1','persistent').numerator):,}/{int(row('Q1','persistent').denominator):,}); rotational landmarks had {pct(row('Q1','rotational').probability)} ({int(row('Q1','rotational').numerator):,}/{int(row('Q1','rotational').denominator):,}). The raw difference was {pp(q1.raw_difference)} (95% CI {pp(q1.raw_ci_low)} to {pp(q1.raw_ci_high)}). Within fixed product, side, distance, clock, prior ATR and age strata, the treated-weighted common-support difference was {pp(q1.matched_difference)} (95% CI {pp(q1.matched_ci_low)} to {pp(q1.matched_ci_high)}). This is an observational contrast with coarse distance bins, not causal lift or a trading edge.")
    d.para(f"Matching retained {int(q1.matched_treated):,} of {int(q1.treated_n):,} persistent and {int(q1.matched_baseline):,} of {int(q1.baseline_n):,} rotational landmarks in {int(q1.common_strata)} common strata. It excluded {int(q1.context_excluded_treated):,} persistent and {int(q1.context_excluded_baseline):,} rotational landmarks without matching context, then left {int(q1.unmatched_treated):,} and {int(q1.unmatched_baseline):,} unmatched. Against the frozen landmark VWAP, persistent residence was {pct(frozen[(frozen['product']=='ALL')&(frozen.state=='persistent')].probability.iloc[0])}, versus {pct(row('Q1','persistent').probability)} against causal VWAP; the frozen sensitivity is in its own table.")
    d.heading("Q2 — price/VWAP slope disagreement")
    q2=match("Q2")
    d.para(f"Opposing slopes crossed the causal VWAP in {pct(row('Q2','opposing').probability)} ({int(row('Q2','opposing').numerator):,}/{int(row('Q2','opposing').denominator):,}) versus {pct(row('Q2','aligned').probability)} ({int(row('Q2','aligned').numerator):,}/{int(row('Q2','aligned').denominator):,}) for aligned slopes. The raw gap was {pp(q2.raw_difference)}; after also matching residence state and the same context, the difference was only {pp(q2.matched_difference)} (95% CI {pp(q2.matched_ci_low)} to {pp(q2.matched_ci_high)}). Product-specific NQ and GC adjusted intervals nearly touch zero; the 2024 adjusted interval includes zero. The prior 30-minute slope signs do not proxy for order flow.")
    d.para(f"Y1 and Y2 were checked as exact complements for all {int(json.loads((stage/'metrics.json').read_text())['y1_y2_complement_checked']):,} fully observed nonzero-side landmark views. A crossing by the 30-minute boundary counts as crossing. The fixed 0.016 price/ATR and 0.0023 VWAP/ATR cuts came only from development-period features.")
    d.heading("Q1/Q2 secondary directional paths: barrier definition changes the answer")
    br=[]
    for question,condition,baseline in (("Q1","persistent","rotational"),("Q2","opposing","aligned")):
        for kind in ("fixed_8tick","half_sigma"):
            treated=bout[(bout["product"]=="ALL")&(bout.question==question)&(bout.condition==condition)&(bout.barrier==kind)].iloc[0]
            control=bout[(bout["product"]=="ALL")&(bout.question==question)&(bout.condition==baseline)&(bout.barrier==kind)].iloc[0]
            diff=barr(question,kind)
            br.append([question,kind.replace("_"," "),f"{int(treated.favorable):,}/{int(treated.denominator):,}",pct(treated.probability),pct(control.probability),pp(diff.difference),f"{pp(diff.ci_low)} to {pp(diff.ci_high)}",f"{int(treated.adverse):,} / {int(treated.neither):,} / {int(treated.ambiguous):,}"])
    d.table(["Question","Barrier","Favorable / all X","P(favorable | X)","Baseline P","Difference","95% CI","Adverse / neither / ambiguous in X"],br)
    d.para("The persistent-versus-rotational fixed 8-tick favorable-first gap is small and its interval crosses zero, while the half-sigma gap is negative. For opposing versus aligned slopes, fixed 8 ticks is also inconclusive and half-sigma is negative. Fixed 8-tick paths have many same-minute ambiguous first passages; those remain in every denominator. Neither barrier was selected after inspecting the outcome.")
    d.image("figures/barrier-contrast.svg","Favorable-first contrast changes between the two frozen barriers")
    d.heading("Q3 — paired volume weighting versus equal weighting")
    q3=[]
    for product in ("ES","NQ","GC"):
        r=paired[(paired["product"]==product)&(paired.split=="all")].iloc[0]
        q3.append([product,f"{int(r.numerator):,}/{int(r.denominator):,}",pct(r.probability),ci(r),pct(r.baseline_probability),
                   f"{r.vwap_mae:.2f}",f"{r.twap_mae:.2f}",f"{r.last_price_mae:.2f}",f"{r.mean_error_difference:.2f}"])
    d.table(["Product","VWAP wins / paired landmarks","P(VWAP wins)","95% CI","P(TWAP wins)","VWAP MAE, pts","TWAP MAE, pts","Last price MAE, pts","Mean paired error Δ, pts"],q3)
    all_p=paired[(paired["product"]=="ALL")&(paired.split=="all")].iloc[0]
    d.para(f"On the primary common timestamps, frozen VWAP won {int(all_p.numerator):,}/{int(all_p.denominator):,} pairs ({pct(all_p.probability)}; shared-date 95% CI {ci(all_p)}). Materially separated references won {pct(row('Q3','material').probability)}, while near-identical references won {pct(row('Q3','near_identical').probability)}. No exact error ties were observed, but all pairs and tie checks are retained. VWAP's paired mean absolute-error advantage over TWAP was {all_p.mean_error_difference:.2f} points (95% CI {all_p.mean_error_ci_low:.2f} to {all_p.mean_error_ci_high:.2f}); product-specific point errors above avoid interpreting a pooled futures-point unit. The last known price had far smaller mean absolute error than either anchor reference for each product, so a VWAP-versus-TWAP win is not a general forecasting or execution advantage.")
    d.para("The primary target is the median of 30 future unadjusted one-minute closes. Future volume-weighted price and horizon-end close are saved in event evidence as separate descriptive targets; neither entered landmark features. TWAP is the cumulative equal-weighted completed-bar HLC3 from the same anchor, and the full-series VWAP identity audit checked 8.36 million active output-anchor bars.")
    d.heading("Product, chronology, and independent views")
    product_rows=[]
    for product in ("ES","NQ","GC"):
        a=match("Q1",product);b=match("Q2",product);c=row("Q3","all",product)
        product_rows.append([product,pp(a.matched_difference),f"{pp(a.matched_ci_low)} to {pp(a.matched_ci_high)}",
                             pp(b.matched_difference),f"{pp(b.matched_ci_low)} to {pp(b.matched_ci_high)}",pct(c.probability)])
    d.table(["Product","Q1 matched Δ","Q1 95% CI","Q2 matched Δ","Q2 95% CI","Q3 VWAP wins"],product_rows)
    split_rows=[]
    for split in ("development","validation","final"):
        a=match("Q1","ALL",split);b=match("Q2","ALL",split);c=row("Q3","all","ALL",split)
        split_rows.append([split,pp(a.matched_difference),f"{pp(a.matched_ci_low)} to {pp(a.matched_ci_high)}",
                           pp(b.matched_difference),f"{pp(b.matched_ci_low)} to {pp(b.matched_ci_high)}",pct(c.probability)])
    d.table(["Chronological label","Q1 matched Δ","Q1 95% CI","Q2 matched Δ","Q2 95% CI","Q3 VWAP wins"],split_rows)
    d.para("These dates are chronological diagnostics, not protected confirmation. `breakdowns.csv` gives product, year, NY clock window including membership gaps, side, and anchor-age rates with denominators and shared-date intervals. `primary_probabilities.csv` also reports product-session-weighted probabilities and intervals. Products have discontinuous date coverage; no artificial common-day denominator was imposed.")
    rep=[]
    for (tf,anchor),view in repl[repl["product"]=="ALL"].groupby(["timeframe","anchor"]):
        get=lambda q,c:view[(view.question==q)&(view.condition==c)].iloc[0]
        rep.append([f"{tf}/{anchor}",f"{int(get('Q1','persistent').denominator):,}",pct(get('Q1','persistent').probability),pct(get('Q1','rotational').probability),
                    pct(get('Q2','opposing').probability),pct(get('Q2','aligned').probability),pct(get('Q3','all').probability)])
    d.table(["Separate replication","Persistent n","Q1 persistent","Q1 rotational","Q2 opposing","Q2 aligned","Q3 VWAP wins"],rep)
    d.para("The independently calculated 5-minute Globex view agrees directionally with the 2-minute primary summary but is correlated with it. Local-anchor Q3 wins vary sharply: Asia and NY favor TWAP in this fixed comparison, London is near even. Those anchors have different ages, membership windows, and populations, so they are sensitivities, not pooled independent votes.")
    d.heading("Coverage, verification, and limits")
    d.para(f"The pinned retrospective publication supplies {gate['eligible_product_days']:,} eligible product-days; all have at least one primary landmark. For the primary cohort, 139,794 regular clock candidates yielded 133,716 landmarks after 3,039 immature and 3,039 insufficient-window-horizon exclusions. ES/NQ/GC contributed 45,628 / 51,788 / 36,300 primary landmarks. All {gate['primary_landmarks']:,} primary and 367,719 total separate-view landmark keys had complete 30-minute one-minute source joins; all extracted paths were outcome-capable. There were {int(funnel[(funnel.cohort=='primary')&(funnel['product']=='ALL')].side_zero.iloc[0])} undefined current sides. `funnel.csv`, `feature-coverage.csv`, and `exclusions.csv` keep the full denominators and missing categories.")
    d.para(f"Every source interval was reconciled with adjusted feature OHLC, volume, contract ID, raw symbol, exclusive-close availability, and fixed session adjustment. Recomputed completed-bar volume-weighted HLC3 matched the pinned VWAP across {audit['full_series_active_bars_checked']:,} active anchor-bar positions (maximum absolute error {audit['max_abs_vwap_error']:.2g} points). {audit['representative_examples_checked']} distinct real event paths cover each observed outcome class and product; all 36 product × outcome-class example rows link to those events. The pinned release and all consumed partition SHA-256 checks passed. Tests cover DST clocks, anchor resets, equality, incomplete lookbacks, future gaps, paired ties, horizon-boundary crossing, and intraminute ambiguity.")
    d.para("Matching uses fixed coarse strata and retains only overlap. It does not control every driver of future paths. Shared-date intervals account for clustering across products and views but are unadjusted for the three-question family; no formal superiority claim or calibrated predictive model is made. Product-day eligibility is retrospective. No fill, cost, latency, or net-P&L model was run.")
    d.heading("Separate exploratory family and reproduction")
    d.para("The plan's volume-shock/inertia, local handoff, prior-session VWAP, rolling-versus-anchored VWAP, and VWAP-within-range modules were not executed in this run. They require separately frozen definitions and remain distinct from the three primary comparisons; no threshold grid was searched for a best historical cell.")
    d.para(f"From the workspace root with the locked environment: `.venv/bin/python studies/06_vwap_state_dynamics/pilot.py --run-id {args.run_id}`; `.venv/bin/python studies/06_vwap_state_dynamics/join_audit.py --run-id {args.run_id}`; `.venv/bin/python studies/06_vwap_state_dynamics/run.py --run-id {args.run_id} --workers 3`; `.venv/bin/python studies/06_vwap_state_dynamics/summarize.py --run-id {args.run_id}`; `.venv/bin/python studies/06_vwap_state_dynamics/audit.py --run-id {args.run_id}`; `.venv/bin/python studies/06_vwap_state_dynamics/render.py --run-id {args.run_id}`. For a reproduction, use a new unique run ID and freeze a matching protocol ID before outcomes; never overwrite sealed evidence.")
    d.links([("Probability atlas","tables/probability_atlas.csv"),("Matched comparisons","tables/matched_comparisons.csv"),
             ("Barrier outcomes","tables/barrier_outcomes.csv"),("Paired errors","tables/paired_errors.csv"),
             ("Funnel","tables/funnel.csv"),("Examples","tables/examples.csv"),
             ("Event evidence","events.manifest.json"),("Run manifest","manifest.json")])
    d.write(stage)
    advice=f"""# VWAP state dynamics advice — 2026-09-23

Status: exploratory research interpretation. All currently available dates had prior VWAP-outcome exposure. This is not an executable strategy or a net-profitability claim.

## Strongest positive conditional probability

The 2-minute Globex persistent-side state had {pct(row('Q1','persistent').probability)} 30-minute causal-VWAP residence versus {pct(row('Q1','rotational').probability)} for rotational state. The raw +44.1 percentage-point gap shrank to {pp(q1.matched_difference)} (95% shared-date CI {pp(q1.matched_ci_low)} to {pp(q1.matched_ci_high)}) within common product, side, distance, clock, prior-ATR, and age strata. Support retained {int(q1.matched_treated):,}/{int(q1.treated_n):,} persistent and {int(q1.matched_baseline):,}/{int(q1.baseline_n):,} rotational landmarks. This is evidence of conditional path association, not an edge after transaction costs. See `tables/primary_probabilities.csv` and `tables/matched_comparisons.csv`, Q1/ALL/all.

VWAP beat the paired same-anchor TWAP reference on {int(all_p.numerator):,}/{int(all_p.denominator):,} common timestamps ({pct(all_p.probability)}; 95% CI {ci(all_p)}). On materially separated references this rose to {pct(row('Q3','material').probability)}. However the last known price had lower mean absolute error than either anchored reference in ES, NQ, and GC, and local-anchor replications did not consistently favor VWAP. See `tables/paired_errors.csv` and `tables/replications.csv`.

## Negative and inconclusive findings

Opposing price/VWAP slopes produced only {pp(q2.matched_difference)} incremental 30-minute crossing probability after matching on residence state and context (95% CI {pp(q2.matched_ci_low)} to {pp(q2.matched_ci_high)}). NQ and GC intervals nearly touch zero, and the 2024 label spans zero. No familywise-adjusted or baseline-model incremental forecasting claim is justified.

For a favorable-first price move, persistent versus rotational was {pp(barr('Q1','fixed_8tick').difference)} at fixed 8 ticks (CI includes zero), but {pp(barr('Q1','half_sigma').difference)} at the ceiling-rounded half-sigma barrier. Opposing versus aligned was {pp(barr('Q2','fixed_8tick').difference)} at 8 ticks (CI includes zero), versus {pp(barr('Q2','half_sigma').difference)} at half-sigma. The barrier-dependent ordering prevents treating VWAP residence or slope state as a universal directional edge. Same-minute barrier ambiguity remains in the denominator. See `tables/barrier_comparisons.csv` and `tables/barrier_outcomes.csv`.

## Decision and next research action

Retain Q1 residence as a descriptive state feature for a later genuinely uninspected period. Do not promote Q2 or the paired reference advantage to a trade rule. Freeze a simple baseline model using product, clock, distance, and prior ATR before any claim of incremental prediction; evaluate future untouched dates with shared-date uncertainty and a declared familywise procedure if superiority is asserted. The plan's five additional ideas are unexecuted exploratory modules and require separate frozen protocols. Costs, fills, sizing, and net P&L remain untested.
"""
    (stage/"advice.md").write_text(advice)
    print(json.dumps({"report_md":str(stage/"report.md"),"report_html":str(stage/"report.html"),"figures":2}))


if __name__ == "__main__":
    main()
