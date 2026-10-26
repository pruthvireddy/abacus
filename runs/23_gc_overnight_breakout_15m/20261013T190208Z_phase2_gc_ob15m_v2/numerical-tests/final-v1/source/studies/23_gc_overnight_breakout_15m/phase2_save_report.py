"""Save a scientific synthesis using explicit Phase2 saved rows only."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STUDY="23_gc_overnight_breakout_15m"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def shown(value):
    return "Unavailable" if value in (None,"") else str(value)


def prepare(stage):
    stage=Path(stage).resolve()
    if not stage.is_relative_to(ROOT/"work"/STUDY) or stage==ROOT/"work"/STUDY:
        raise ValueError("owning unsealed stage required")
    if (ROOT/"runs"/STUDY/stage.name).exists():raise FileExistsError("completed run immutable")
    for name in ("report.md","report.html","advice.md","report-source-map.json"):
        if (stage/name).exists():raise FileExistsError("fresh synthesis required")
    metrics=json.loads((stage/"metrics.json").read_text())
    for name,pin in metrics["tables"].items():
        if sha(stage/"tables"/(name+".csv"))!=pin["sha256"]:raise ValueError("saved table drift")
    selection=json.loads((stage/"selection.json").read_text())
    assessment=json.loads((stage/"assessment.json").read_text())
    text="""Phase2 preserves the unchanged Phase1 baseline and uses all accepted original breakout episodes, including censored trades. Primary inward-reclaim comparisons use one common complete-day mask. Known no-fill is zero; unknown execution remains unavailable. Protected-low results use all upper-first episodes; protected-high mirrors are explicit. Actual-entry trade performance has a different cohort anchor from original-breakout paired and occurrence results.

Protected low is the frozen overnight range low, and protected high is the frozen overnight range high. Touch, one-tick breach and completed-candle closing break are separate. Same-session rates have shorter and unequal exposure; remaining-window occurrence continues after the original leg exits. Price touches/reclaims to the breached boundary, midpoint or original boundary are diagnostics rather than target fills or financial recovery.

All standardized trades use one GC contract, unadjusted same-contract prices, 15-minute confirmed decisions and observed one-minute OHLC execution approximations. The primary assumed fees are $2.50 per contract per side plus one adverse tick per fill. Signal-close initial 1% stops reset once from actual fill only at a surviving entry candle close; passive stops initially reference the submitted executable limit. Gap fills and protective exits remain executed. There is no profit target or optimized management. Assumed costs are not the user's broker charges.

Actual account experiments separately use $10,000 initial capital, 1% start-of-day risk, 10x leverage, 5% margin and whole contracts. Two-leg allocations split risk equally without replenishment or a third attempt. Financial recovery requires actual executed legs and an original realized net loss known at the first qualifying signal. Unknown equity and fills remain unavailable; observed quantity skips do not prove missing setups were infeasible. Standardized replacement profits are not source-account returns.

Development 2018–2020 and validation 2021–2023 preceded the hashed selection. Later 2024–2025 assessment and qualified available 2026 replication followed without retuning. Published baseline years are exposed, not pristine holdouts. Four-week aligned calendar block intervals use 10,000 draws and seed230015, with one/eight-week sensitivities; four primary contrasts use 98.75% marginal intervals and three upper-first protected contrasts use 98.333333%. Mirrors and subgroups remain exploratory.

Inputs end September18,2026, so 2026 is partial. Strict range completeness, roll barriers and uncertified holiday candidates reduce support. Missing later evidence remains censored. Live mapping receipt timing, annual holiday certification, tick ordering and native TradingView replay remain unverified. Closed-P&L drawdown excludes floating account equity. Phase3 EMA/cloud management and new filter searches remain uncomputed."""
    text+="\n\nThe requested recovery-delay supplement measures time from the first known protected one-tick breach to recovery, with source-OHLC estimates and conservative time bounds. Its source and inputs were frozen separately after policy execution and before these derived measurements. It changes no order, P&L, comparison mask or selection; mean delays condition on known recovery timings and are not survival probabilities. Original breakout-to-event elapsed time remains a separate metric. Canonical ledgers retain censored-only observed holding time omitted from the common CSV columns. Raw gap-entry metadata uses exact float inequality and may reflect binary price noise; it is not a one-tick gap certificate."
    md=["# GC- Overnight Breakout 15M — Phase 2", "", "Run: `"+stage.name+"`; protocol `2.0.0`. Baseline: `20261013T142537Z_phase1_gc_ob15m_v1`.", "",text,"", "Saved validation decision: `"+selection["decision"]+"`; selected policy: `"+shown(selection["selected_policy"])+"`.","", "Saved later assessment: `"+assessment["decision"]+"`.",""]
    body=["<h1>GC- Overnight Breakout 15M — Phase 2</h1>","<p>Run: "+html.escape(stage.name)+"; protocol2.0.0.</p>",*("<p>"+html.escape(p)+"</p>" for p in text.split("\n\n")),"<p>Validation: "+html.escape(selection["decision"])+". Selected: "+html.escape(shown(selection["selected_policy"]))+". Later: "+html.escape(assessment["decision"])+".</p>"]
    bindings=[]
    table_paths={}
    def table(name,title,where,columns,source_path=None):
        relative=source_path or "tables/"+name+".csv"
        path=stage/relative;table_paths[name]=relative
        with path.open(newline="") as f:rows=list(csv.DictReader(f))
        chosen=[(i,r) for i,r in enumerate(rows) if all(r[k]==v for k,v in where.items())]
        if not chosen:raise ValueError("saved zero-support cohorts must exist: "+title)
        md.extend(["## "+title,"","| "+" | ".join(columns)+" |","| "+" | ".join("---" for _ in columns)+" |"])
        body.append("<h2>"+html.escape(title)+"</h2><div class=scroll><table><thead><tr>"+"".join("<th>"+html.escape(c)+"</th>" for c in columns)+"</tr></thead><tbody>")
        for i,row in chosen:
            values=[shown(row[c]) for c in columns]
            md.append("| "+" | ".join(v.replace("|","\\|") for v in values)+" |")
            body.append("<tr>"+"".join("<td>"+html.escape(v)+"</td>" for v in values)+"</tr>")
            bindings.extend(dict(table=name,source_row=i,source_column=c,value=row[c],rendered=shown(row[c])) for c in columns)
        md.extend(["","Source: `"+relative+"`; selectors `"+json.dumps(where,sort_keys=True)+"`.",""])
        body.append("</tbody></table></div>")
    allrow={"year":"all","session":"all","side":"combined"}
    table("paired","Primary original-breakout comparisons — net USD per accepted day",dict(allrow,family="primary"),["policy","episodes","complete_pairs","missing_pairs","fills","completed","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high"])
    table("trade-cohorts","Actual candidate entry performance — all conditions",allrow,["policy","executable_fills","completed","censored","wins","losses","breakevens","net_dollars","mean_net_dollars","profit_factor","max_drawdown_dollars"])
    for side in ("upper-first","lower-first"):
        table("occurrence","Protected boundary occurrence — "+side,{"year":"all","session":"all","side":side},["horizon","event","episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound","mean_exposure_minutes","mean_elapsed_minutes"])
        table("paired","Protected exploratory replacements — "+side,{"year":"all","session":"all","side":side,"family":"protected"},["policy","episodes","complete_pairs","missing_pairs","fills","completed","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high"])
        table("time-recovery","Time after protected breach — "+side,{"year":"all","session":"all","side":side},["horizon","level","event","known_breach_episodes","known_recoveries","unknown_recovery","unknown_recovery_time","mean_delay_minutes_source_estimate","mean_delay_minutes_lower","mean_delay_minutes_upper","delay_minutes_source_estimate_denominator"],"additional/time-recovery/time-recovery.csv")
    table("account","Actual source-account experiments — original-breakout cohorts",allrow,["policy","mode","episodes","signals","eligible_loss","original_fills","second_fills","quantity_skips","completed_pairs","full_recovery","unknown","net_dollars"])
    publications=[]
    for path in sorted((stage/"publications").glob("*/publication.json")):
        report=json.loads(path.read_text())
        if report["source"]["runId"]!=stage.name:raise ValueError("report belongs to another run")
        publications.append(dict(id=report["id"],title=report["title"],source=str(path.relative_to(stage)),sha256=sha(path)))
    if len(publications)!=23:raise ValueError("exact23 prepared sources required")
    md.extend(["## Prepared publication sources",""])
    body.append("<h2>Prepared publication sources</h2><ul>")
    for p in publications:
        md.append("- ["+p["title"]+"]("+p["source"]+")")
        body.append('<li><a href="'+p["source"]+'">'+html.escape(p["title"])+"</a></li>")
    body.append("</ul>")
    (stage/"report.md").write_text("\n".join(md)+"\n")
    (stage/"report.html").write_text('<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>GC- Overnight Breakout 15M — Phase 2</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:auto;padding:24px;color:#24242b}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px;white-space:nowrap}.scroll{overflow-x:auto}</style><main>'+"\n".join(body)+"</main></html>\n")
    (stage/"advice.md").write_text("# Phase2 interpretation — "+datetime.now(timezone.utc).date().isoformat()+"\n\nSaved validation decision: `"+selection["decision"]+"`; selected rule: `"+shown(selection["selected_policy"])+"`. Later assessment: `"+assessment["decision"]+"`. These decisions use the frozen criteria, rather than filled-only rankings.\n\n"+text+"\n\nExact aggregate evidence and cohort masks are in report.md and the selected saved tables. Negative and inconclusive conditions remain in all23 prepared publications. This evidence does not authorize a live trade or a new optimized filter.\n")
    mapping={"status":"prepared","tables":{name:{"path":relative,"sha256":sha(stage/relative)} for name,relative in table_paths.items()},"bindings":bindings,"selection":{"path":"selection.json","sha256":sha(stage/"selection.json")},"assessment":{"path":"assessment.json","sha256":sha(stage/"assessment.json")},"publications":publications,"outputs":{name:sha(stage/name) for name in ("report.md","report.html","advice.md")}}
    (stage/"report-source-map.json").write_text(json.dumps(mapping,indent=2,allow_nan=False)+"\n")
    return {"status":"prepared","cells":len(bindings),"publications":len(publications)}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    print(json.dumps(prepare(parser.parse_args().stage)))
