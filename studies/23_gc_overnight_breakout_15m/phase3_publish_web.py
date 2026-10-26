"""Explicit saved Phase 3 report projections; no backtest/statistics imports.

Reuses the already retained Study23 presentation-only CSV copying, SVG and PNG
helpers. Phase3 schemas, source maps, report selectors and interpretation stay
separate. Numeric ownership remains in the executed Study23 run.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import io
import json
import math
from pathlib import Path
import subprocess
import sys

from phase2_publish_web import (SavedInputs, PublicationDraft, json_bytes,
    sha_bytes, write_new, saved_bars_svg, saved_heatmap_svg, saved_line_svg,
    svg_start, svg_text, wrapped_svg, flow_box, flow_arrow, json_source,
    text_section, safe_relative, read_regular, value_type)
from phase3_report_supplements import add_supplements, TEXT as SAVED_TEXT_COLUMNS
from phase3_cloud_figures import add_cloud_examples

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUDY="23_gc_overnight_breakout_15m"
VERSION="study23.phase3-publication/v1"
PREFIX="gc-overnight-breakout-15m-phase3-20261013-v1"
GROUPS=("trend-context","entry-gates","ema20-support","ema50-support","earlier-exits","other-cloud-uses","methods-risk")
LABELS={"trend-context":"Trend context","entry-gates":"Entry gates","ema20-support":"EMA20 support adds","ema50-support":"EMA50 support adds","earlier-exits":"Earlier exits","other-cloud-uses":"Other cloud uses","methods-risk":"Methods and risk controls"}
STRINGS={"policy","mode","control","year","session","side","leg","anchor","feature","bucket","contact_group","event","period","original_session","event_session","add_session","scenario","dimension","trade_id","episode_id","time","exit_time","annual_drawdown_path","status","event_at"}
STRINGS.update(SAVED_TEXT_COLUMNS)
STRINGS.update({"level","confluence_state","case_id","quality_reason","decision_at","expected_slot","available_at","reason","price_cloud"})
PERCENT={"win_rate","parent_win_rate","rate","lower_bound","upper_bound","participation","adjusted_confidence"}


@dataclass(frozen=True)
class ReportSpec:
    group: str
    view: str
    @property
    def publication_id(self):return f"{PREFIX}-{self.group}-{self.view}"
    @property
    def title(self):return LABELS[self.group]+" — "+{"summary":"Summary","year":"Year-wise","sessions":"Sessions"}[self.view]


def report_specs():
    return tuple(ReportSpec(g,v) for g in GROUPS for v in (("summary",) if g=="methods-risk" else ("summary","year","sessions")))


def scalar(key,value):
    if value=="":return None
    if key in STRINGS:return value
    if value in {"True","False","true","false"}:return value.lower()=="true"
    number=float(value)
    if not math.isfinite(number):raise ValueError("nonfinite saved cell")
    return int(number) if number.is_integer() and abs(number)<2**53 else number


def columns(keys,*,anchor="original_actual_entry"):
    labels={"year":"Year","session":("Original-entry session" if anchor=="original_actual_entry" else "Original order-decision session" if anchor=="original_order_decision" else "Original entry-snapshot session" if anchor=="original_entry" else "Actual leg-entry session" if anchor=="actual_leg_fill" else "EMA event session"),"side":"Original side" if anchor!="actual_leg_fill" else "Actual leg side","mean_difference":"Mean policy − declared control","adjusted_low":"99.166667% marginal lower","adjusted_high":"99.166667% marginal upper","difference_low":"95% lower","difference_high":"95% upper","mean_low":"Conditional parent mean 95% lower","mean_high":"Conditional parent mean 95% upper","complete_pairs":"Six-core common pairs","individual_pairs":"Observed policy/control pairs","known_events":"Observed events","known_denominator":"Known denominator"}
    result=[]
    for k in keys:
        c={"key":k,"label":labels.get(k,k.replace("_"," ").capitalize())}
        if k not in STRINGS and k not in {"qualifies","financing_enforced"}:
            c.update(format="percent" if k in PERCENT else "number",precision=2 if any(w in k for w in ("mean","rate","dollars","points","difference","low","high","factor","payoff","minutes","participation")) else 0)
            if "dollars" in k or k in {"mean_difference","difference_low","difference_high","adjusted_low","adjusted_high","mean_low","mean_high"}:c["unit"]="USD"
            elif "points" in k:c["unit"]="GC points"
            elif "minutes" in k:c["unit"]="minutes"
            elif k=="net_r":c["unit"]="initial-risk R"
        result.append(c)
    return result


def filters(view,anchor):
    prefix="Original-entry" if anchor=="original_actual_entry" else "Original order-decision" if anchor=="original_order_decision" else "Original entry-snapshot" if anchor=="original_entry" else "Actual leg-entry" if anchor=="actual_leg_fill" else "EMA event"
    values=[{"key":"year","label":prefix+" year"},{"key":"session","label":prefix+" session"},{"key":"side","label":"Side","defaultValue":"combined"}]
    if view!="year":values[0]["defaultValue"]="all"
    if view!="sessions":values[1]["defaultValue"]="all"
    return values


class Draft(PublicationDraft):
    def __init__(self,*args):
        super().__init__(*args);self.table_assertions=[]
    def table(self,section,title,artifact,cols,rowfilters=None,description="",notes=None):
        section=section.lower().replace("_","-")
        raw=self.copied_table(artifact);keys=[c["key"] for c in cols]
        if len(raw)>(1500 if rowfilters else 100) or len(keys)>12:raise ValueError(f"bounded table {section}: {len(raw)}")
        source=self.sources[artifact]
        # Short display keys keep the source report bounded. Full saved column
        # names remain explicit in source bindings, labels and assertions.
        aliases={k:"c"+str(i) for i,k in enumerate(keys)}
        rows=[{aliases[k]:scalar(k,r[k]) for k in keys} for r in raw]
        for i,row in enumerate(rows):
            for k in keys:
                self.bindings.append({"section":section,"row_index":i,"key":aliases[k],"source_artifact":artifact,"source_row":i,"source_column":k,"value_type":value_type(row[aliases[k]]),"original_stage_source_path":source["original_stage_source_path"],"original_source_row":source["selected_source_rows"][i],"original_source_column":k})
        displaycols=[{**c,"key":aliases[c["key"]]} for c in cols]
        displayfilters=[{**f,"key":aliases[f["key"]]} for f in rowfilters or []]
        result={"id":section,"kind":"table","title":title,"columns":displaycols,"rows":rows}
        if rowfilters:result["rowFilters"]=displayfilters
        if description:result["description"]=description
        if notes:result["notes"]=notes
        anchors={r.get("anchor") for r in raw}
        assertion={"section":section,"source_artifact":artifact,"columns":[{**c,"key":aliases[c["key"]],"source_column":c["key"]} for c in cols],"filters":[{**f,"key":aliases[f["key"]],"source_column":f["key"]} for f in rowfilters or []]}
        if len(anchors)==1 and None not in anchors:assertion.update(cohort_anchor_column="anchor",cohort_anchor_value=next(iter(anchors)))
        self.table_assertions.append(assertion)
        return result
    def figure(self,section,title,stem,*args,**kwargs):
        return super().figure(section.lower().replace("_","-"),title,stem.lower().replace("_","-"),*args,**kwargs)
    def source_map(self):
        result=super().source_map();result["schema_version"]="study23.phase3-web-source-cells/v1";result["table_assertions"]=self.table_assertions
        for d in result["downloads"]:
            entry=next(e for e in self.download_entries if e["id"]==d["id"])
            d.update(units=entry["units"],population=entry["population"],scope=entry["scope"],column_types={c:sorted({value_type(scalar(c,r[c])) for r in self.copied_table(d["source_artifact"])}) for c in d["columns"]})
        return result


def guide_svg():
    svg=svg_start(1240,850,"Five-minute cloud: confirmed decisions and separate risk","Illustrative process only; no empirical prices or probability score.")
    flow_box(svg,45,155,355,145,"Parent entry","Frozen 15m rule. Original stop/reset schedule remains 15m.")
    flow_box(svg,435,155,355,145,"Prior cloud level","Contact candle opens after fill. Its level was already available.")
    flow_box(svg,825,155,355,145,"Confirmed close","Full 5m close confirms. Prospective order uses next opening.")
    flow_arrow(svg,401,225,434);flow_arrow(svg,791,225,824)
    flow_box(svg,45,345,545,190,"Support A20 / A50","Separate attempts: departure → first selected EMA penetration → close hold. Parent OPEN and net liquidation positive; any unknown setup prefix abstains.")
    flow_box(svg,635,345,545,190,"Earlier exit X1 / X2","X1: two closes beyond one frozen edge. X2: fresh adjacent opposing cross. Protection remains active until actual exit.")
    flow_box(svg,45,580,545,160,"Financed risk","1% start-of-day total: 50% parent / 50% reserve. Whole GC, no risk refill, max one add.")
    flow_box(svg,635,580,545,160,"Distinct diagnostic","One original + one add is extra exposure; compare 1- and 2-contract parent controls separately.")
    svg.append(wrapped_svg(45,795,"Equal EMAs are neutral. Unknown cloud does not remove known protection. Price recovery, realized profitability and capital feasibility answer different questions.",100,19));svg.append("</svg>")
    return "\n".join(svg).encode()


RULES={
"trend-context":"Confidence is conditional empirical support from the decision-time cloud, not a fitted probability. Ordering, price position, both three-change slopes, alignment duration, raw/ATR width and distance, expansion and range confluence are saved separately. Unavailable prefixes and warmup remain visible; the entry snapshot never substitutes for the earlier order snapshot.",
"entry-gates":"G1 requires directional EMA ordering and the last completed five-minute close beyond the favorable cloud edge. G2 additionally requires both three-change slopes with the trade. Gates update only at inherited fifteen-minute source submission/update times and remain frozen between updates. The first unfiltered shadow boundary event consumes the opportunity. Changed admission tied to a later shadow opening is unknown; an unavailable cloud causes separately counted abstention.",
"ema20-support":"A20 uses a full post-fill departure beyond the prior cloud, then the first later penetration of frozen prior EMA20. A strict close hold, current aligned ordering, an open parent and positive estimated net liquidation are required. The first attempt is consumed even if rejected; unavailable setup prefixes abstain. A confirmed contingent add uses the next eligible opening, cancels if the original exits before release, and keeps any already-filled add. EMA20-only contact does not consume EMA50's separate experiment.",
"ema50-support":"A50 independently uses a full post-fill departure and first later penetration of frozen prior EMA50. The confirmation, profitability, contingent next-opening order and one-attempt requirements match A20. Each original keeps its fifteen-minute reset; each add has a one-percent signal-close initial stop and a surviving five-minute entry-candle fill reset. No averaging into losses or repeated pyramiding is permitted.",
"earlier-exits":"X1 freezes the prior adverse cloud edge at the first full post-fill close beyond it; a second adjacent expected valid close beyond that same edge queues a next-opening exit. Recovery, equality or an unknown slot breaks confirmation. X2 requires a fresh aligned/neutral-to-opposed transition over adjacent valid full post-fill observations; initial opposition alone is insufficient. Both operate on winners as well as losers and preserve original protection until actual exit.",
"other-cloud-uses":"T50 only tightens protection one tick beyond the prior available EMA50. It activates prospectively, preserves tighter original protection and cannot be loosened by the parent's later reset. An already-crossed proposal queues an opening exit. Fixed overextension/width bins, midpoint/boundary confluence, repeated retests and 5/15/30/60-minute source-candle-excluded paths are exploratory diagnostics; they are not take-profit returns or more add attempts. Phase2 cloud event context is descriptive: no Phase2 trading parent was selected.",
"methods-risk":"The primary parent is the immutable Phase1 executed baseline. The first-close-seeded five-minute EMA20/50 release is verified against that parent's raw same-contract minute manifest. The optional Pine touch-marker thresholds and Study21 performance findings are not Phase3 gates. EMA monitoring uses exclusive completion and full candles after the fill upper bound. Native TradingView history and actual feed latency remain unverified."}


def assemble(draft):
    spec=draft.spec;sections=[]
    for f in ("config.json","selection.json","execution-completion.json"):draft.copy_json(f)
    draft.copy_text("protocol.md")
    def text(id,title,body):sections.append(text_section(draft,id,title,body))
    def saved(name,where=None,cols=None,target=None):return draft.copy_table("tables/"+name+".csv",target or "tables/"+name+".csv",where,cols)
    def table(id,title,artifact,keys,anchor="original_actual_entry",filtered=True,description=""):
        sections.append(draft.table(id,title,artifact,columns(keys,anchor=anchor),filters(spec.view,anchor) if filtered else None,description))
    def bars(id,title,artifact,indices,labels,value,unit="USD",percent=False):
        svg,p=saved_bars_svg(draft,artifact,indices,labels,value,title,"Saved evidence; full source counts and explicit masks remain in tables.",unit=unit,precision=1 if percent else 0,format_kind="percent" if percent else "number")
        sections.append(draft.figure(id,title,id,svg,p,alt=title+"; unavailable cells are labeled rather than plotted as zero.",caption="Exact saved values; assumed inherited costs. Cohort anchors and denominators are stated in the accompanying tables."))
    text("rule","Rule and causal timing",RULES[spec.group])
    text("population","Population, costs and comparisons","The full accepted original episode roster remains fixed. Known abstentions contribute zero and unknown execution remains unavailable. One-GC gate/exit comparisons use unchanged one-GC Phase1; financed A20/A50 use half-budget-parent controls with the source $10,000 capital. Unfunded one-plus-one diagnostics have larger exposure. Costs assume $2.50 per contract per side and one adverse tick per fill, with retained sensitivities; they are not verified broker charges. Broker time is fixed GMT+3; reporting uses New York with DST.")
    policysets={"entry-gates":("G1","G2"),"ema20-support":("A20",),"ema50-support":("A50",),"earlier-exits":("X1","X2"),"other-cloud-uses":("T50",)}
    policies=policysets.get(spec.group,())
    if spec.group=="methods-risk":
        svg=guide_svg();provenance={"kind":"illustrative","authored":True,"not_empirical":True,"source_artifact":"protocol.md","source_sha256":draft.sources["protocol.md"]["sha256"],"plotted_values":[],"settings_artifact":"config.json","settings_sha256":draft.sources["config.json"]["sha256"],"plot_encoding":{"kind":"authored-process-v1","qualification":"No empirical numerical price geometry."}}
        sections.append(draft.figure("causal-guide","Illustrative causal guide","causal-guide",svg,provenance,alt="Parent fifteen-minute entry, prior five-minute cloud contact, confirmation and prospective add or exit; separate reserved risk.",caption="Illustrative process, not performance evidence. Each confirmed action executes at a later eligible opening."))
        cols=columns(["policy","validation_complete_pairs","mean_difference","adjusted_low","completed_trades","financed_add_fills","qualifies"])
        # Configuration/selection values are exact JSON pointers, not rewritten statistics.
        sections.append(draft.json_table("selection","Frozen validation selection","selection.json",[{c["key"]:f"/candidates/{i}/{c['key']}" for c in cols} for i in range(6)],cols))
        risk=saved("risk",{"mode":("full_parent","half_parent","financed_overlay")},["policy","mode","year","session","side","episodes","known_outcomes","unknown_outcomes","net_dollars","original_fills","add_fills","original_quantity_skips","unused_reserve_dollars","mean_unused_reserve_dollars","reserve_allocation_denominator","planned_risk_overshoot_episodes","peak_notional","episode_mtm_drawdown_dollars","financing_enforced","anchor"])
        # A single all-year/session view is bounded independently of policy selectors.
        riskrows=draft.copied_table(risk);subset=[i for i,r in enumerate(riskrows) if r["year"]=="all" and r["session"]=="all" and r["side"]=="combined"]
        bars("whole-gc-feasibility","Whole-GC executable originals",risk,subset,["policy","mode"],"original_fills",unit="fills")
        table("reserved-risk","Full-budget, half-budget and add controls — net results and reserved risk",risk,["year","session","side","policy","mode","episodes","original_fills","add_fills","net_dollars","original_quantity_skips","mean_unused_reserve_dollars","planned_risk_overshoot_episodes"],description="Unused reserve is a daily planned-risk allocation, not accumulated cash or increased capital; its exact allocation denominator is retained in the selected CSV. Raw stop-distance sizing is inherited; adverse gaps, costs and exposure overruns remain in observed-risk accounting.")
        draft.download("risk-controls","Financed whole-contract controls",risk,draft.sources[risk]["columns"],population="Original-entry cohorts and separately reserved capital controls.",units="USD, whole-GC counts; financing enforced.",scope="Full-budget, half-budget and half-parent/add controls; no fractional quantity or assumed extra capital.")
    elif spec.group=="trend-context":
        for a in ("original_order_decision","original_entry"):
            for feature in ("availability","ordering","price_position","slopes","width_atr","distance_atr","aligned_duration","width_change"):
                selector={"anchor":a,"feature":feature}
                if spec.view=="summary":selector.update(year="all",session="all")
                elif spec.view=="year":selector.update(session="all")
                art=saved("profiles",selector,target=f"tables/{a}-{feature}.csv")
                keys=["year","session","side","bucket","observations","distinct_episodes","completed_parent_episodes","unknown_parent_episodes","mean_parent_net_dollars","parent_win_rate","mean_low","mean_high"]
                table(a+"-"+feature,a.replace("_"," ").capitalize()+" — "+feature.replace("_"," "),art,keys,anchor=a,description="Conditional parent outcomes; uncertainty uses episode-aligned calendar blocks, not independent repeated observations.")
                if a=="original_order_decision" and feature=="ordering":
                    rows=draft.copied_table(art);indices=[i for i,r in enumerate(rows) if r["year"]=="all" and r["session"]=="all" and r["side"]=="combined"]
                    bars("ordering-profile","Order-decision ordering profile",art,indices,["bucket"],"mean_parent_net_dollars")
        # Raw saved profiles are selected, never recalculated by the website.
    else:
        for policy in policies:
            mode="financed_overlay" if policy in {"A20","A50"} else "standardized"
            if policy!="T50":
                art=saved("paired",{"policy":policy},target=f"tables/{policy}-paired.csv")
                table(policy+"-paired",policy+" — declared control comparison",art,["year","session","side","episodes","complete_pairs","missing_pairs","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high","individual_mean_difference"])
                rows=draft.copied_table(art);idx=[i for i,r in enumerate(rows) if r["side"]=="combined" and (r["year"]!="all" and r["session"]=="all" if spec.view=="year" else r["year"]=="all" and r["session"]!="all" if spec.view=="sessions" else r["year"]=="all" and r["session"]=="all")]
                bars(policy+"-paired-chart",policy+" — paired differences",art,idx,["year"] if spec.view=="year" else ["session"] if spec.view=="sessions" else ["policy"],"mean_difference")
                draft.download(policy.lower()+"-paired",policy+" paired comparisons",art,["policy","mode","control","year","session","side","episodes","complete_pairs","missing_pairs","individual_pairs","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high","original_fills","add_fills","known_zero","unknown_execution","missed_winners","avoided_losses","anchor"],population="All original accepted episodes; six-core common mask plus observed-pair sensitivity.",units="USD per original episode, counts; ratio participation.",scope="Exact policy/control estimand; gate/exit standardized and add financed comparisons remain separate.")
            art=saved("trade-cohorts",{"policy":policy,"mode":mode,"leg":"combined"},target=f"tables/{policy}-performance.csv")
            table(policy+"-performance",policy+" — actual leg-entry performance",art,["year","session","side","fills","completed","censored","gross_dollars","net_dollars","win_rate","expectancy_dollars","profit_factor","closed_drawdown_dollars"],anchor="actual_leg_fill")
            stats=saved("trade-cohorts",{"policy":policy,"mode":mode,"leg":"combined"},target=f"tables/{policy}-excursions.csv")
            table(policy+"-excursions",policy+" — profitability and path",stats,["year","session","side","wins","losses","breakevens","net_r","r_denominator","payoff","mfe_points","mae_points","holding_minutes"],anchor="actual_leg_fill")
            if spec.view!="summary":
                table(policy+"-points-costs",policy+" — saved points, costs and risk units",stats,["year","session","side","fills","completed","censored","gross_points","net_points","cost_dollars","net_dollars","net_r","r_denominator"],anchor="actual_leg_fill",description="Quantity-weighted raw gross and net GC points, USD fees/slippage difference and saved initial-risk R. These are whole completed legs in their actual entry cohorts; incomplete and empty cohorts remain unavailable.")
            if spec.view=="summary":
                path=saved("equity",{"policy":policy,"mode":mode,"leg":"combined"},target=f"tables/{policy}-equity.csv")
                if draft.copied_table(path):
                    svg,p=saved_line_svg(draft,path,"cumulative_net_dollars",policy+" — cumulative closed P&L","Saved complete legs; unavailable future outcomes do not become zero.")
                    sections.append(draft.figure(policy+"-equity",policy+" cumulative closed P&L",policy+"-equity",svg,p,alt="Cumulative closed net P&L in USD, saved complete-leg path.",caption="Whole legs belong to their actual entry cohort; full-history path is separate from annual within-year drawdown."))
                    svg,p=saved_line_svg(draft,path,"drawdown_dollars",policy+" — closed P&L drawdown","Saved complete-leg closed P&L path; negative USD below the running peak.")
                    sections.append(draft.figure(policy+"-drawdown",policy+" closed P&L drawdown",policy+"-drawdown",svg,p,alt="Saved closed P&L drawdown in USD below the running peak; incomplete exposure remains separately qualified.",caption="Full-history closed-leg path. The floating-risk tables retain unknown full paths and separately label observed prefixes."))
            if policy in {"A20","A50"}:
                for diagnostic_mode in ("diagnostic_1plus1",):
                    diag=saved("trade-cohorts",{"policy":policy,"mode":diagnostic_mode,"leg":"combined"},target=f"tables/{policy}-extra-exposure.csv")
                    table(policy+"-extra-exposure",policy+" — one-plus-one exposure diagnostic",diag,["year","session","side","fills","completed","censored","net_dollars","win_rate","closed_drawdown_dollars"],anchor="actual_leg_fill",description="Unfunded extra exposure; not the equal-risk core comparison. One- and two-contract controls are retained in downloads.")
                    if spec.view=="summary":
                        path=saved("equity",{"policy":policy,"mode":diagnostic_mode,"leg":"combined"},target=f"tables/{policy}-diagnostic-equity.csv")
                        if draft.copied_table(path):
                            for field,label in (("cumulative_net_dollars","cumulative closed P&L"),("drawdown_dollars","closed P&L drawdown")):
                                id=policy+"-diagnostic-"+field
                                svg,p=saved_line_svg(draft,path,field,policy+" — diagnostic "+label,"Saved one-original/one-added-GC complete-leg path; larger exposure than one parent.")
                                sections.append(draft.figure(id,policy+" diagnostic "+label,id,svg,p,alt="Saved diagnostic "+label+" in USD; one original and at most one added contract.",caption="Unfunded one-plus-one exposure diagnostic. Paired one- and two-contract controls use a common complete-episode mask; extra profit does not establish equal-risk entry quality."))
                ema="20" if policy=="A20" else "50"
                contacts=saved("contacts",{"ema":ema,"contact_group":"first","event":"hold"},target=f"tables/{policy}-contact-frequency.csv")
                table(policy+"-holds",policy+" — conditional first support hold",contacts,["year","session","side","contacts","distinct_episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound","eligible_open_landmarks"],anchor="EMA_decision_event")
                if len(draft.downloads)<4:
                    risk=saved("risk",{"policy":("BASE",policy),"mode":("parent_1","parent_2","full_parent","half_parent","financed_overlay","diagnostic_1plus1")},target=f"tables/{policy}-risk-controls.csv")
                    draft.download("risk-controls","Parent and add exposure controls",risk,["policy","mode","year","session","side","episodes","known_outcomes","unknown_outcomes","net_dollars","original_fills","add_fills","original_quantity_skips","add_quantity_skips","cancellations","unused_reserve_dollars","peak_notional","episode_mtm_drawdown_dollars","financing_enforced","anchor"],population="Original-entry cohorts; exact financed and unfunded diagnostic modes.",units="USD, notional USD, whole GC and counts.",scope="Additional profits from additional contracts are not equal-risk entry quality.")
            if policy in {"X1","X2","T50"}:
                tradeoff=saved("exit-tradeoffs",{"policy":policy},target=f"tables/{policy}-tradeoffs.csv")
                table(policy+"-tradeoffs",policy+" — saved losses and surrendered profits",tradeoff,["year","session","side","complete_pairs","parent_losers","losses_reduced","loss_dollars_saved","parent_winners","winners_cut_short","profit_surrendered_dollars","mean_time_saved_minutes","mean_post_exit_favorable_points"])
                if policy=="T50":
                    table("t50-paired","T50 — exploratory paired comparison with unchanged one-GC Phase 1",tradeoff,["year","session","side","episodes","complete_pairs","missing_pairs","mean_difference","improved","deteriorated","mean_time_saved_minutes","mean_post_exit_favorable_points"],description="Observed T50/Phase1 complete pairs on all original accepted episodes. This exploratory tightening rule is outside the six-core selection and confidence family.")
    text("uncertainty","Chronology, uncertainty and limits","Policies were frozen before scoring. Development uses 2018–2020, validation 2021–2023, later assessment 2024–2025 and available partial 2026 replication. Earlier Phase1/2 and Study21 exposure means these years are not pristine holdouts. Six core contrasts use aligned four-week calendar blocks, 10,000 draws, seed 230015, pointwise 95% and Bonferroni 99.166667% marginal intervals, with one/eight-week sensitivity. The correction applies within each reported cohort, not across every subgroup or secondary diagnostic. No combined policy or optimized cloud threshold was searched. Missing values, zero-support groups and undefined ratios remain unavailable. One-minute OHLC order and modeled availability cannot prove native tick ordering or live feed latency.")
    add_supplements(draft,sections)
    add_cloud_examples(draft,sections)
    # Keep the shared uncertainty qualification after the saved evidence.
    sections.append(sections.pop(next(i for i,s in enumerate(sections) if s["id"]=="uncertainty")))
    if len(sections)>30:raise ValueError("too many report sections")
    refs=[{"id":f"source-{i}","kind":"saved-artifact","label":s["path"],"title":"Saved Phase3 source projection","runId":draft.run_id,"artifact":s["path"],"sha256":s["sha256"]} for i,s in enumerate(draft.sources.values())]
    return {"schemaVersion":"1.1","id":spec.publication_id,"title":"GC- Overnight Breakout 15M — EMA Cloud Phase 3 — "+spec.title,"summary":"Frozen five-minute EMA cloud policies and causal empirical context, with unchanged Phase1 comparisons, risk controls and explicit missingness.","publishedAt":json.loads(draft.files["execution-completion.json"])["finished_at"][:19]+"Z","source":{"producer":"sahadeva","runId":draft.run_id},"sections":sections,"references":refs,"downloads":draft.download_entries,"notes":["Saved rows only; the website does not execute research or calculate probabilities.","Phase1 and Phase2 remain available in the same study.","Whole-GC financed adds and one-plus-one exposure diagnostics answer different questions."]}


def generate(stage,node,package_root,sharp_root):
    stage=Path(stage)
    if (stage/"publications").exists():raise FileExistsError("preserve prior drafts")
    if json.loads((stage/"execution-completion.json").read_text()).get("phase3")!="computed":raise ValueError("complete Phase3 saved evidence required")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt=stage/"publication-render-attempts"/stamp;attempt.mkdir(parents=True,exist_ok=False)
    source_records=[]
    for name in ("phase3_publish_web.py","phase3_report_supplements.py","phase3_cloud_figures.py","phase3_examples.py","phase2_publish_web.py","rasterize_figures.mjs"):
        data=(HERE/name).read_bytes();relative="source/"+name
        write_new(attempt,relative,data)
        source_records.append({"path":str((attempt/relative).relative_to(stage)),"sha256":sha_bytes(data),"bytes":len(data),"workspace_path":str((HERE/name).relative_to(ROOT))})
    write_new(attempt,"presentation-source-snapshot.json",json_bytes({"run_id":stage.name,"sources":source_records,"at":datetime.now(timezone.utc).isoformat(),"scope":"Actual saved-row projection, empirical case selection and vector/raster sources retained before rendering and sealing; no policy implementation imported by the exporter."}))
    drafts=[];renders=[]
    inputs=SavedInputs(stage)
    for spec in report_specs():
        draft=Draft(inputs,stage.name,spec);report=(json.dumps(assemble(draft),ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode()
        if len(report)>2*1024*1024:raise ValueError("source report bound")
        drafts.append((draft,report))
        for figure in draft.figures:
            svg=attempt/spec.publication_id/figure["svg_path"];svg.parent.mkdir(parents=True,exist_ok=True);svg.write_bytes(draft.files[figure["svg_path"]]);renders.append({"svg":str(svg),"png":str(attempt/spec.publication_id/figure["path"])})
    inventory=attempt/"render-inventory.json";inventory.write_bytes(json_bytes(renders))
    command=[str(node),str(HERE/"rasterize_figures.mjs"),str(sharp_root),str(inventory)]
    process=subprocess.run(command,capture_output=True,text=True,timeout=240)
    (attempt/"stdout.log").write_text(process.stdout);(attempt/"stderr.log").write_text(process.stderr)
    if process.returncode:raise ValueError("retained raster attempt failed")
    runtime=json.loads(Path(str(inventory)+".runtime.json").read_text())
    result=[]
    for draft,report in drafts:
        for figure in draft.figures:draft.complete_png(figure["path"],(attempt/draft.spec.publication_id/figure["path"]).read_bytes())
        root=stage/"publications"/draft.spec.publication_id
        mapping=json_bytes(draft.source_map())
        for name,data in {**draft.files,"publication.json":report,"source-map.json":mapping}.items():write_new(root,name,data)
        # Native validation is an independent contract check, not scientific validation.
        native=[str(node),str(package_root/"scripts/publish.mjs"),"--report",str(root/"publication.json"),"--dry-run"]
        checked=subprocess.run(native,capture_output=True,text=True,timeout=90)
        write_new(root,"native-stdout.log",checked.stdout.encode());write_new(root,"native-stderr.log",checked.stderr.encode())
        receipt={"producer_version":VERSION,"run_id":stage.name,"publication_id":draft.spec.publication_id,"status":"generated-awaiting-independent-verification","report_sha256":sha_bytes(report),"publication_sha256":sha_bytes(report),"source_map_sha256":sha_bytes(mapping),"command":native,"native_result":{"returncode":checked.returncode,"status":"passed" if checked.returncode==0 else "failed","stdout_path":"native-stdout.log","stdout_sha256":sha_bytes(checked.stdout.encode()),"stderr_path":"native-stderr.log","stderr_sha256":sha_bytes(checked.stderr.encode())},"renderer":runtime,"producer_sha256":sha_bytes(Path(__file__).read_bytes()),"presentation_sources":source_records,"argv":sys.argv,"finished_at":datetime.now(timezone.utc).isoformat()}
        write_new(root,"publication-generation.json",json_bytes(receipt))
        if checked.returncode:raise ValueError("native report check failed; retained exact logs")
        result.append({"publication_id":draft.spec.publication_id,"sections":len(json.loads(report)["sections"]),"displayed_cells":len(draft.bindings),"figures":len(draft.figures),"downloads":len(draft.downloads)})
    write_new(attempt,"generation-result.json",json_bytes({"status":"generated","publications":result}))
    return result


def finalize_manifests(stage):
    results=[];stage=Path(stage);runprefix=Path("runs")/STUDY/stage.name
    for spec in report_specs():
        root=stage/"publications"/spec.publication_id;verified=json.loads(read_regular(root,"publication-verification.json"))
        if verified["status"]!="passed":raise ValueError("independent verification required")
        mapping=json.loads(read_regular(root,"source-map.json"))
        sources=[]
        for source in mapping["source_artifacts"]:
            if sha_bytes(read_regular(stage,source["original_stage_source_path"]))!=source["original_source_sha256"]:raise ValueError("source changed")
            sources.append({"path":str(runprefix/"publications"/spec.publication_id/source["path"]),"sha256":source["sha256"]})
        outputs=[{"path":str(runprefix/"publications"/spec.publication_id/path.relative_to(root)),"sha256":sha_bytes(path.read_bytes())} for path in sorted(root.rglob("*")) if path.is_file() and path.name!="publication-manifest.json"]
        manifest={"publication_id":spec.publication_id,"source_run_id":stage.name,"study_id":STUDY,"source_artifacts":sources,"outputs":outputs}
        write_new(root,"publication-manifest.json",json_bytes(manifest));results.append({"publication_id":spec.publication_id,"manifest_sha256":sha_bytes(json_bytes(manifest))})
    return {"status":"manifests-finalized","publications":results}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--stage",type=Path,required=True);p.add_argument("--node",type=Path,default=Path("/Users/ppanati/.nvm/versions/node/v24.18.0/bin/node"));p.add_argument("--sharp-root",type=Path,default=Path("/Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/node"));p.add_argument("--finalize",action="store_true");a=p.parse_args()
    print(json.dumps(finalize_manifests(a.stage) if a.finalize else generate(a.stage,a.node,ROOT/"apps/narada",a.sharp_root),indent=2))
