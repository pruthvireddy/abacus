"""Bounded, explicit saved-cell Phase3 report supplements.

No research producer is imported. This module chooses saved rows/columns and
renders them; it never pools rows, derives a statistic, or evaluates a policy.
The caller owns the final report and integrates add_supplements before sealing.
"""
from __future__ import annotations

import math
from phase2_publish_web import saved_heatmap_svg, text_section, value_type

CORE=("G1","G2","A20","A50","X1","X2")
SESSIONS=("Asia","London","New York","Outside")
POLICIES={"entry-gates":("G1","G2"),"ema20-support":("A20",),"ema50-support":("A50",),"earlier-exits":("X1","X2"),"other-cloud-uses":("T50",)}
TEXT={"policy","mode","control","year","session","side","leg","anchor","feature","bucket","contact_group","event","period","original_session","event_session","add_session","scenario","dimension","trade_id","episode_id","contract","timestamp","available_at","decision_at","entry_time","exit_time","status","reason","annual_drawdown_path","level","confluence_state"}
FLAGS={"full_path_known","within_year_path","financing_enforced","partial_year","conditional_population","not_calibrated_probability","not_trade_return","larger_exposure","not_equal_risk"}
RATES={"win_rate","parent_win_rate","rate","lower_bound","upper_bound","participation","adjusted_confidence"}
LABELS={
 "episodes":"Original accepted episodes","signals":"Known policy signals","original_fills":"Observed original fills","add_fills":"Observed add fills","completed":"Completed episodes","known_zero":"Known zero / no-fill episodes","unknown_execution":"Unknown execution outcomes","participation":"Original-fill participation",
 "feature_abstentions":"Unavailable-cloud abstentions","blocked":"Blocked first shadow opportunity","cancellations":"Pending-add cancellations","quantity_skips":"Original quantity skips","support_rejections":"Consumed support attempts rejected","ambiguous":"Ambiguous episodes","missed_winners":"Missed original winners","avoided_losses":"Avoided original losses",
 "rejections":"Known rejected policy actions","unknown_feature_slots":"Unknown monitored feature slots","add_attempts":"Consumed add attempts","unknown_support_abstentions":"Unknown support-prefix abstentions","add_quantity_skips":"Add quantity skips","known_outcomes":"Known episode outcomes",
 "mean_difference":"Mean policy − declared control","difference_low":"95% marginal lower","difference_high":"95% marginal upper","adjusted_low":"Within-cohort adjusted lower","adjusted_high":"Within-cohort adjusted upper","complete_pairs":"Six-core common complete pairs","missing_pairs":"Missing common pairs","block_weeks":"Calendar block weeks",
 "fills":"Actual fills","censored":"Censored fills / paths","net_dollars":"Net P&L","expectancy_dollars":"Mean completed net P&L","profit_factor":"Profit factor","closed_drawdown_dollars":"Within-year closed P&L drawdown","gross_dollars":"Raw-price gross on saved path","wins":"Net wins","losses":"Net losses","breakevens":"Net breakevens","net_r":"Net initial-risk R","r_denominator":"Valid initial-risk R legs","mfe_points":"Mean completed-leg MFE","mae_points":"Mean completed-leg MAE","holding_minutes":"Mean completed-leg hold",
 "mtm_drawdown_dollars":"Full-known floating drawdown","observed_prefix_mtm_drawdown_dollars":"Observed-prefix floating drawdown","unknown_episode_equity":"Unknown episode equity outcomes","observed_mtm_rows":"Observed floating rows","full_path_known":"Full path known","peak_notional":"Observed peak notional","peak_active_stop_risk":"Observed peak active stop risk","peak_concurrent_legs":"Observed peak concurrent legs","within_year_path":"Within-year path",
 "contact_group":"Contact number group","contacts":"Conditional contact population","distinct_episodes":"Distinct original episodes","known_events":"Known events","known_none":"Known absence","known_denominator":"Known denominator","unknown":"Unknown event outcomes","rate":"Event / known denominator","lower_bound":"All-contact lower bound","upper_bound":"All-contact upper bound","eligible_open_landmarks":"Eligible open-position landmarks","eligible_open_episodes":"Eligible open-position episodes","mean_recovery_minutes":"Mean known recovery delay","recovery_timing_denominator":"Known recovery timings","observed_recovery_timing_unknown":"Observed recovery with unknown first timing",
 "horizon_minutes":"Exact forward horizon","events":"Source events","observed":"Complete observed paths","mean_signed_points":"Mean signed forward move","mean_mfe_points":"Mean forward favorable excursion","mean_mae_points":"Mean forward adverse excursion","not_trade_return":"Price-path diagnostic only",
 "observations":"Saved observations","completed_parent_episodes":"Known completed parent episodes","unknown_parent_episodes":"Unknown parent outcomes","mean_parent_net_dollars":"Mean eventual parent net P&L","mean_low":"Parent mean 95% lower","mean_high":"Parent mean 95% upper","conditional_population":"Conditional open-position population","not_calibrated_probability":"Not calibrated probability",
 "original_session":"Original actual-entry session","event_session":"EMA signal/event session","add_session":"Actual add-entry session / unfilled",
}


def normalized(value):
    return value.lower().replace("_","-").replace(" ","-")


def saved_scalar(column,raw):
    if raw=="":return None
    if column in TEXT:return raw
    if column in FLAGS or raw in ("True","False","true","false"):
        if raw not in ("True","False","true","false"):raise ValueError("saved boolean type")
        return raw.lower()=="true"
    value=float(raw)
    if not math.isfinite(value):raise ValueError("nonfinite saved scalar")
    return int(value) if value.is_integer() and abs(value)<2**53 else value


def saved(draft,name,selector,keys,stem):
    """Copy only used columns plus the exact saved anchor, in source order."""
    original="tables/"+name+".csv"
    headers,_=draft.inputs.table(original)
    columns=list(dict.fromkeys([*keys,*( ["anchor"] if "anchor" in headers else [])]))
    if any(key not in headers for key in columns):raise ValueError("missing frozen saved supplement column: "+name)
    return draft.copy_table(original,"tables/supp-"+normalized(stem)+".csv",selector,columns)


def column(key,source,anchor):
    year_label="Actual add-entry year" if anchor=="actual_add_fill" else "Actual leg-entry year" if anchor=="actual_leg_fill" else "EMA event year" if anchor in {"EMA_decision_event","EMA_event_year","eligible_open_position_landmark"} or anchor.startswith("phase2_saved_event_context_") else "Original-entry year"
    session_label=year_label.replace("year","session")
    label=year_label if source=="year" else session_label if source=="session" else "Actual add side" if source=="side" and anchor=="actual_add_fill" else "Actual leg side" if source=="side" and anchor=="actual_leg_fill" else "Original side" if source=="side" else LABELS.get(source,source.replace("_"," ").capitalize())
    out={"key":key,"label":label}
    if source not in TEXT and source not in FLAGS:
        out.update(format="percent" if source in RATES else "number",precision=2 if source in RATES or "mean" in source or "dollars" in source or "points" in source or source in {"difference_low","difference_high","adjusted_low","adjusted_high","profit_factor","net_r"} else 0)
        if "dollars" in source or source in {"mean_difference","individual_mean_difference","difference_low","difference_high","adjusted_low","adjusted_high","mean_low","mean_high","peak_notional","peak_active_stop_risk"}:out["unit"]="USD"
        elif "minutes" in source:out["unit"]="minutes"
        elif "points" in source:out["unit"]="GC points"
        elif source=="net_r":out["unit"]="initial-risk R"
        elif source=="block_weeks":out["unit"]="weeks"
    return out


def table(draft,sections,stem,title,artifact,keys,*,anchor="original_actual_entry",filter_columns=("year","session","side"),description="",labels=None):
    """Short display keys retain exact full source keys in all bindings."""
    stem="supp-"+normalized(stem)
    if any(s["id"]==stem for s in sections):raise ValueError("duplicate supplement section")
    if not 1<=len(keys)<=12 or len(keys)!=len(set(keys)):raise ValueError("supplement column bound")
    raw=draft.copied_table(artifact);source=draft.sources[artifact]
    if len(filter_columns)>3 or any(k not in keys for k in filter_columns) or len(raw)>(1500 if filter_columns else 100):raise ValueError("supplement table/filter row bound")
    aliases={k:"c"+str(i) for i,k in enumerate(keys)}
    cols=[column(aliases[k],k,anchor) for k in keys]
    for c,k in zip(cols,keys):
        if labels and k in labels:c["label"]=labels[k]
    rows=[{aliases[k]:saved_scalar(k,r[k]) for k in keys} for r in raw]
    rowfilters=[]
    for k in filter_columns:
        f={"key":aliases[k],"label":next(c["label"] for c in cols if c["key"]==aliases[k])}
        default="combined" if k=="side" else "all" if k in {"year","session"} else None
        if k=="year" and draft.spec.view=="year" or k in {"session","event_session"} and draft.spec.view=="sessions":default=None
        if default is not None and any(row[aliases[k]]==default for row in rows):f["defaultValue"]=default
        rowfilters.append(f)
    for i,row in enumerate(rows):
        for k in keys:
            draft.bindings.append(dict(section=stem,row_index=i,key=aliases[k],source_artifact=artifact,source_row=i,source_column=k,value_type=value_type(row[aliases[k]]),original_stage_source_path=source["original_stage_source_path"],original_source_row=source["selected_source_rows"][i],original_source_column=k))
    section=dict(id=stem,kind="table",title=title,columns=cols,rows=rows)
    if rowfilters:section["rowFilters"]=rowfilters
    if description:section["description"]=description
    sections.append(section)
    assertion=dict(section=stem,source_artifact=artifact,columns=[dict(c,source_column=k) for c,k in zip(cols,keys)],filters=[dict(f,source_column=k) for f,k in zip(rowfilters,filter_columns)])
    anchors={r.get("anchor") for r in raw}
    if len(anchors)==1 and None not in anchors:assertion.update(cohort_anchor_column="anchor",cohort_anchor_value=next(iter(anchors)))
    draft.table_assertions.append(assertion)
    return artifact


def download(draft,stem,label,artifact,keys,*,population,units,scope):
    if not draft.copied_table(artifact):return
    if len(draft.downloads)>=4:raise ValueError("planned supplement download bound")
    draft.download("supp-"+normalized(stem),label,artifact,keys,population=population,units=units,scope=scope)


PARTICIPATION=["year","session","side","episodes","signals","original_fills","add_fills","completed","known_zero","unknown_execution","participation"]
DISPOSITIONS=["year","session","side","feature_abstentions","blocked","cancellations","quantity_skips","ambiguous","missed_winners","avoided_losses","rejections","unknown_feature_slots"]
FLOATING=["year","session","side","episodes","unknown_episode_equity","observed_mtm_rows","full_path_known","mtm_drawdown_dollars","observed_prefix_mtm_drawdown_dollars","peak_notional","peak_active_stop_risk","peak_concurrent_legs"]
SCENARIOS=["policy","scenario","side","episodes","complete_pairs","missing_pairs","mean_difference","baseline_net_dollars","alternative_net_dollars","known_zero","unknown_execution"]
INTERVALS=["policy","period","side","block_weeks","episodes","complete_pairs","mean_difference","difference_low","difference_high","adjusted_low","adjusted_high","adjusted_confidence"]
PROFILE=["year","session","side","bucket","observations","distinct_episodes","completed_parent_episodes","unknown_parent_episodes","mean_parent_net_dollars","parent_win_rate","mean_low","mean_high"]
CONTACT=["year","session","side","contact_group","contacts","distinct_episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound"]
CONTACT_EVENTS=("hold","tick_breach","close_break","reclaimed","cloud_flip")
FORWARD=["year","session","side","contact_group","events","distinct_episodes","observed","censored","mean_signed_points","mean_mfe_points","mean_mae_points","not_trade_return"]
TRANSITIONS=["year","side","original_session","event_session","add_session","events","distinct_episodes","add_fills"]


def primary_summary(draft,sections,policies):
    headers,_=draft.inputs.table("tables/paired.csv")
    disposition=DISPOSITIONS
    for p in policies:
        source=saved(draft,"paired",{"policy":p},list(dict.fromkeys(PARTICIPATION+disposition)),p+"-participation")
        table(draft,sections,p+"-participation",p+" — original opportunity and observed participation",source,PARTICIPATION,description="Episodes are original accepted opportunities; signals, observed fills, known no-fill and unknown execution remain separate. Add fills are not original entry participation.")
        table(draft,sections,p+"-dispositions",p+" — abstentions, consumed opportunities and cancellations",source,disposition,description="Blocked first-shadow gates, unavailable cloud, canceled pending adds and quantity skips are distinct saved dispositions; they are not pooled as losses.")
        floating=saved(draft,"floating",{"policy":p,"mode":"financed_overlay" if p in {"A20","A50"} else "standardized"},FLOATING,p+"-floating")
        table(draft,sections,p+"-floating",p+" — full-known and observed-prefix floating risk",floating,FLOATING,description="Full-known drawdown is unavailable when the saved path is incomplete. Observed-prefix drawdown/notional/active stop risk remain partial-path diagnostics; full-history and within-year paths are distinguished by the Year control.")
        if p in {"A20","A50"} and draft.spec.group!="methods-risk":
            keys=["year","session","side","episodes","signals","add_attempts","support_rejections","unknown_support_abstentions","add_quantity_skips","cancellations","known_outcomes","unknown_outcomes"]
            art=saved(draft,"risk",{"policy":p,"mode":"financed_overlay"},keys,p+"-support-dispositions")
            table(draft,sections,p+"-support-dispositions",p+" — financed add attempts, rejections and unknown support",art,keys,description="Financed original-entry opportunity cohorts: signals, consumed add attempts, known support rejection, unavailable support prefix, quantity skips and cancellation are exact separate saved counts. Unknown outcomes do not become verified zero activity.")
    if policies and policies!=("T50",):
        scenario=saved(draft,"scenarios",{"policy":tuple(policies)},SCENARIOS,"scenario-sensitivity")
        table(draft,sections,"scenario-sensitivity","Saved cost and OHLC-order sensitivity",scenario,SCENARIOS,filter_columns=("policy","scenario","side"),description="The fixed accepted roster and saved scenario-specific declared controls remain unchanged. Costs and source OHLC ordering are modeled sensitivities, not realized broker proof.")
        intervals=saved(draft,"interval-sensitivities",{"policy":tuple(policies)},INTERVALS,"calendar-block-sensitivity")
        table(draft,sections,"calendar-block-sensitivity","Saved one-, four- and eight-week uncertainty",intervals,INTERVALS,filter_columns=("policy","period","side"),description="Each interval is saved for the exact development/validation/later/replication period and common mask. Within-cohort corrected marginal intervals do not claim simultaneous coverage across all subgroups.")
        download(draft,"scenario-sensitivity","Saved cost/order scenarios",scenario,SCENARIOS,population="Exact fixed original episode roster and scenario declared control.",units="Counts and USD per original episode.",scope="Unchanged modeled scenario outcomes and explicit missing pairs; no website recomputation.")
        download(draft,"calendar-block-sensitivity","Saved 1/4/8-week marginal intervals",intervals,INTERVALS,population="Six-core common original episode masks in each fixed chronological period and side.",units="USD per original episode, weeks and marginal confidence ratios.",scope="Pointwise and within-cohort multiplicity-adjusted intervals; no global subgroup correction.")


def year_heatmaps(draft,sections,policies):
    for p in policies:
        mode="financed_overlay" if p in {"A20","A50"} else "standardized"
        art=saved(draft,"trade-cohorts",{"policy":p,"mode":mode,"leg":"combined","side":"combined"},["year","session","side","net_dollars"],p+"-year-session")
        rows=draft.copied_table(art);indices=[i for i,r in enumerate(rows) if r["year"]!="all" and r["session"]!="all"]
        if not indices:continue
        title=p+" — actual leg-entry year × session net P&L"
        svg,provenance=saved_heatmap_svg(draft,art,indices,"year","session","net_dollars",title,"Saved completed-leg net USD; unavailable and zero-support cells stay unavailable.")
        sections.append(draft.figure("supp-"+normalized(p)+"-year-session",title,"supp-"+normalized(p)+"-year-session",svg,provenance,alt=title+" with exact saved USD cell labels.",caption="Actual leg-entry New York year/session, combined side. Partial 2026 is retained. Cells are saved completed-leg net P&L with assumed costs; they do not represent the paired original-entry estimand."))


def add_sessions(draft,sections,p):
    for mode,label in (("financed_overlay","Financed equal-risk"),("diagnostic_1plus1","Unfunded one-plus-one diagnostic")):
        keys=["year","session","side","fills","completed","censored","net_dollars","win_rate","expectancy_dollars","profit_factor","closed_drawdown_dollars","distinct_episodes"]
        extra=["year","session","side","wins","losses","breakevens","net_r","r_denominator","mfe_points","mae_points","holding_minutes","gross_dollars"]
        art=saved(draft,"trade-cohorts",{"policy":p,"mode":mode,"leg":"add"},list(dict.fromkeys(keys+extra)),p+"-"+mode+"-add-only")
        table(draft,sections,p+"-"+mode+"-add-only",p+" — "+label+" actual ADD-only entry performance",art,keys,anchor="actual_add_fill",description="These saved cohorts use each actual add fill’s New York year/session/side. They exclude original legs and cannot replace the original-entry paired comparison.")
        table(draft,sections,p+"-"+mode+"-add-excursions",p+" — "+label+" ADD-only paths",art,extra,anchor="actual_add_fill",description="Completed add legs only; undefined R/ratios and censored fills remain unavailable. The one-plus-one mode adds exposure and is not the financed core.")
    transition_keys=["policy","mode",*TRANSITIONS]
    for original_session in SESSIONS:
        art=saved(draft,"transitions",{"policy":p,"mode":"financed_overlay","original_session":original_session},transition_keys,p+"-transition-"+original_session)
        table(draft,sections,p+"-transition-"+original_session,p+" — original "+original_session+" → EMA event → actual add entry",art,TRANSITIONS,anchor="EMA_event_year",filter_columns=("year","event_session","side"),description="Year is the EMA event year; original session is fixed in this section. Destination is the actual add-entry session, or the saved unfilled category. No session is invented for an unfilled add; these are event transitions, not financial recovery.")
    if len(draft.downloads)<4:
        art=saved(draft,"transitions",{"policy":p,"mode":("financed_overlay","diagnostic_1plus1")},transition_keys,p+"-all-transitions")
        download(draft,"add-transitions",p+" original/event/add session transitions",art,transition_keys,population="Original episodes with a saved policy event; original, event and actual add entry anchors remain separate.",units="Known saved event, episode and fill counts.",scope="Financed and larger-exposure diagnostic modes; unfilled category preserved exactly.")


def exposure_controls(draft,sections,p):
    keys=["year","session","side","control","episodes","complete_pairs","missing_pairs","alternative_net_dollars","control_net_dollars","mean_difference","individual_pairs","individual_mean_difference"]
    complete=["policy","mode",*keys,"total_difference","larger_exposure","not_equal_risk"]
    art=saved(draft,"exposure-controls",{"policy":p},complete,p+"-exposure-controls")
    table(draft,sections,p+"-exposure-controls",p+" — unfunded one-plus-one versus one- and two-contract parents",art,keys,labels={"complete_pairs":"Common three-path complete episodes","individual_pairs":"Observed alternative/control pairs"},description="Exact same-roster common mask across one-plus-one alternative, one-contract parent and two-contract parent. These are larger-exposure diagnostics with no confidence interval or core selection role; original-entry Year/Session/Side differs from actual ADD-only entry cohorts.")
    if draft.spec.view!="summary" and len(draft.downloads)<4:
        download(draft,"exposure-controls",p+" paired larger-exposure controls",art,complete,population="Fixed original episodes with a common three-path mask and separate observed alternative/control pair sensitivity.",units="USD per original episode, USD totals, counts and exposure flags.",scope="Unfunded one-plus-one compared separately with unchanged one- and two-contract parent paths. Not the equal-risk financed core; no CI or selection claim.")


def other_profiles(draft,sections):
    features=("width_atr","distance_atr","width_change",*(f"confluence_ema{ema}_{level}" for ema in (20,50) for level in ("H","L","M")))
    for feature in features:
        art=saved(draft,"profiles",{"anchor":"eligible_open_position_landmark","feature":feature},PROFILE,"open-"+feature)
        table(draft,sections,"open-"+feature,"Open-position landmarks — "+feature.replace("_"," "),art,PROFILE,anchor="eligible_open_position_landmark",description="Conditional open-position observations and distinct original episodes, with eventual saved parent outcomes. Repeated landmarks are not independent trades or a calibrated probability; confluence is the frozen source flag.")
    keys=["anchor","feature",*PROFILE]
    # Four selected CSV files may each contain more columns than a display table.
    # A saved feature/bucket roster can exceed 15,000 rows; explicit partitions
    # keep all selected columns and rows within the existing CSV bound.
    for name,partition in (("shape",features[:3]),("confluence",features[3:])):
        selected=saved(draft,"profiles",{"anchor":"eligible_open_position_landmark","feature":partition},keys,"open-"+name+"-download")
        download(draft,"open-"+name,"Open-position "+name+" conditional profiles",selected,keys,population="Eligible open-position landmarks and deduplicated original episode outcome support.",units="Observations, distinct episodes, USD, ratios; fixed source buckets.",scope="Exploratory conditional descriptive profiles, not independent entry confidence or optimized thresholds.")
    floating=saved(draft,"floating",{"policy":"T50","mode":"standardized"},FLOATING,"t50-floating")
    table(draft,sections,"t50-floating","T50 exploratory tightening — full-known and observed-prefix floating risk",floating,FLOATING,description="Saved original-entry cohorts for the exploratory one-contract tightening policy. Full-path unknowns keep total floating drawdown unavailable; observed prefix exposure is a separate diagnostic.")
    display=["level","confluence_state","event","side","contacts","distinct_episodes","known_events","known_denominator","unknown","rate","lower_bound","upper_bound"]
    complete=["ema","level","confluence_state","event","year","session","side","anchor","contacts","distinct_episodes","known_events","known_none","unknown","known_denominator","rate","lower_bound","upper_bound","conditional_population"]
    for ema in (20,50):
        art=saved(draft,"confluence",{"ema":str(ema),"year":"all","session":"all"},complete,f"ema{ema}-confluence-rates")
        table(draft,sections,f"ema{ema}-confluence-rates",f"EMA{ema} — frozen H/L/M confluence event rates",art,display,anchor="EMA_decision_event",filter_columns=("level","event","side"),description="All-year/all-contact-session summary: the selected prior EMA's frozen H/L/M confluence is yes/no/unknown in each saved row. Hold, tick breach, close break, price reclaim and adjacent confirmed cloud flip use separate known denominators. Repeated contacts are conditional events, not independent trades or extra add attempts.")
        full=saved(draft,"confluence",{"ema":str(ema)},complete,f"ema{ema}-confluence-download")
        download(draft,f"ema{ema}-confluence",f"EMA{ema} H/L/M confluence event rates — all saved cohorts",full,complete,population="Frozen prior selected-EMA confluence at EMA contact-event Year/Session and original side.",units="Contacts, distinct original episodes, known counts and ratios.",scope="Yes/no/unknown confluence; hold/tick-breach/close-break/reclaim/cloud-flip separate event populations. Price events are not financial recovery or realized returns.")
    path_keys=["year","session","side","bucket","observations","distinct_episodes","completed_parent_episodes","unknown_parent_episodes","mean_parent_net_dollars","mean_parent_mfe_points","mean_parent_mae_points","mean_parent_holding_minutes"]
    for feature in ("distance_atr","width_atr","width_change"):
        art=saved(draft,"profiles",{"anchor":"original_entry","feature":feature},path_keys,"original-entry-"+feature+"-path")
        table(draft,sections,"original-entry-"+feature+"-path","Original entry snapshot — "+feature.replace("_"," ")+" and subsequent whole-parent path",art,path_keys,anchor="original_entry",description="Fixed original-entry cloud bins and saved completed Phase1 whole-parent net/MFE/MAE/hold means from the actual original entry. Excursions and holding time are source OHLC approximations. These whole-parent paths do not measure only the path after a later EMA contact; source-candle-excluded post-contact paths are reported separately in the Year-wise view.")


def other_paths(draft,sections,*,forward=True):
    view_selector={"session":"all"} if draft.spec.view=="year" else {"year":"all"}
    sections.append(text_section(draft,"supp-event-view-scope","Event cohort display and complete downloads","This Year-wise view shows annual all-session event/path cohorts; this Sessions view shows all-year event-session cohorts. Selected CSVs retain every saved year × event session × original side row. The EMA event anchor remains separate from actual add entry and original entry; no probabilities or returns are pooled by the website."))
    for ema in (20,50):
        for event in CONTACT_EVENTS:
            art=saved(draft,"contacts",{"ema":str(ema),"event":event,**view_selector},["ema","event",*CONTACT],f"ema{ema}-contacts-{event}")
            table(draft,sections,f"ema{ema}-contacts-{event}",f"EMA{ema} — {event.replace('_',' ')} by first/repeated contact",art,CONTACT,anchor="EMA_decision_event",description="All/first/second/third-or-more/unknown contact groups are explicit saved overlapping populations. Reclaim is conditional on known tick-breached contacts; hold, tick breach and closing break use their own declared denominators.")
        timing=["year","session","side","contact_group","contacts","known_events","known_denominator","unknown","mean_recovery_minutes","recovery_timing_denominator","observed_recovery_timing_unknown"]
        art=saved(draft,"contacts",{"ema":str(ema),"event":"reclaimed",**view_selector},timing,f"ema{ema}-recovery-timing")
        table(draft,sections,f"ema{ema}-recovery-timing",f"EMA{ema} — known recovery timing and unknown first timing",art,timing,anchor="EMA_decision_event",description="Mean minutes from the saved contact close to known first later close reclaim of the frozen contact level. Conditional known timings are not survival probabilities. Observed recovery with unknown first timing remains separately counted.")
        for horizon in ((5,15,30,60) if forward else ()):
            art=saved(draft,"forward",{"ema":str(ema),"horizon_minutes":str(horizon),**view_selector},["ema","horizon_minutes",*FORWARD],f"ema{ema}-forward-{horizon}")
            table(draft,sections,f"ema{ema}-forward-{horizon}",f"EMA{ema} — exact {horizon}-minute source-candle-excluded path",art,FORWARD,anchor="EMA_decision_event",description="Forward price paths begin after the source contact candle closes. Complete observed paths and censored paths are separate; signed/favorable/adverse GC-point excursions are not realized trade returns or executable targets.")
    for ema in (20,50):
        if forward:
            cols=["ema","horizon_minutes",*FORWARD]
            art=saved(draft,"forward",{"ema":str(ema)},cols,f"ema{ema}-forward-download")
            download(draft,f"ema{ema}-forward",f"EMA{ema} exact forward paths, all four horizons",art,cols,population="Saved first/repeated/unknown EMA contact cohorts and distinct original episodes.",units="GC points, counts and minutes; source candle excluded.",scope="Exact 5/15/30/60-minute observed versus censored price paths; not realized returns.")
        cols=["ema","event",*CONTACT,"mean_recovery_minutes","recovery_timing_denominator","observed_recovery_timing_unknown","eligible_open_landmarks","eligible_open_episodes"]
        art=saved(draft,"contacts",{"ema":str(ema)},cols,f"ema{ema}-contact-download")
        download(draft,f"ema{ema}-contacts",f"EMA{ema} first/repeated contact and recovery support",art,cols,population="Saved contact groups with event-specific known denominators and open-position landmark support.",units="Counts, ratios and known-event mean minutes.",scope="Hold/tick-breach/close-break/reclaim are separate conditional price events; unknowns remain explicit.")


def phase2_context(draft,sections):
    headers,rows=draft.inputs.table("tables/profiles.csv")
    anchors=tuple(sorted({r["anchor"] for r in rows if r["anchor"].startswith("phase2_saved_event_context_")}))
    if not anchors:return
    sections.append(text_section(draft,"supp-phase2-context-scope","Saved Phase2 event context only","These cloud snapshots use the retained Phase2 event availability anchor. No Phase2 trading parent was selected. Midpoint and protected-high/low event context describes available state and conditional parent support; it does not create a recovery trade or an entry-gate replication."))
    keys=["anchor","bucket","year","session","side","observations","distinct_episodes","completed_parent_episodes","unknown_parent_episodes","mean_parent_net_dollars","parent_win_rate","not_calibrated_probability"]
    for feature in ("availability","ordering"):
        art=saved(draft,"profiles",{"anchor":anchors,"feature":feature,"year":"all"},keys,"phase2-"+feature)
        table(draft,sections,"phase2-"+feature,"Phase2 retained midpoint / protected-boundary event — "+feature,art,keys,anchor="phase2_saved_event_context_",description="Saved event anchor stays in each row; Year is the available Phase2 event year. All-year display retains session/side context; full annual/event cohorts remain in the selected CSV.")
    cols=["anchor","feature","bucket","year","session","side","observations","distinct_episodes","completed_parent_episodes","unknown_parent_episodes","mean_parent_net_dollars","parent_win_rate","conditional_population","not_calibrated_probability"]
    for feature in ("availability","ordering"):
        art=saved(draft,"profiles",{"anchor":anchors,"feature":feature},cols,"phase2-"+feature+"-download")
        download(draft,"phase2-"+feature,"Phase2 saved event-anchor "+feature+" profiles",art,cols,population="Retained Phase2 midpoint/protected-high/low event snapshots; no trading parent replication.",units="Observations, original episodes, USD and ratios.",scope="Exact annual/event-session/side and unknown-state saved profiles; descriptive context only.")


def methods(draft,sections):
    primary_summary(draft,sections,CORE)
    # Every policy and mode is retained separately; no new all-policy aggregate.
    paths=["mode","year","session","side","episodes","unknown_episode_equity","observed_mtm_rows","full_path_known","mtm_drawdown_dollars","observed_prefix_mtm_drawdown_dollars"]
    exposure=["mode","year","session","side","peak_notional","peak_active_stop_risk","peak_concurrent_legs","within_year_path"]
    art=saved(draft,"floating",{"policy":"BASE"},list(dict.fromkeys(paths+exposure)),"baseline-floating-controls")
    table(draft,sections,"baseline-floating-controls","Parent budget/exposure controls — known versus prefix floating risk",art,paths,description="Exact full/half-budget and unfunded one-/two-contract parent modes. Mode remains visible; floating-risk paths keep their own saved unknown masks.")
    table(draft,sections,"baseline-floating-exposure","Parent controls — observed notional, stop risk and concurrent legs",art,exposure,description="Observed peak exposures retain the saved full-path-known and unknown-equity context in the preceding table; no unseen exposure is inferred from a known prefix.")


def add_supplements(draft,sections):
    """Append the frozen explicit view-specific projections in memory only."""
    group,view=draft.spec.group,draft.spec.view
    policies=POLICIES.get(group,())
    if group=="methods-risk":methods(draft,sections)
    elif group=="trend-context":
        if view=="summary":
            cols=["anchor","feature",*PROFILE]
            for anchor in ("original_order_decision","original_entry"):
                art=saved(draft,"profiles",{"anchor":anchor,"feature":("availability","ordering","price_position","slopes")},cols,anchor+"-profiles-download")
                download(draft,anchor+"-profiles",anchor.replace("_"," ").capitalize()+" conditional profiles",art,cols,population="Distinct original episodes conditioned on their saved decision-time cloud state.",units="Counts, USD and ratios; four-week episode-aligned marginal intervals.",scope="Earlier order snapshot and entry snapshot remain separate; confidence is descriptive support, not calibrated probability.")
    elif group=="other-cloud-uses":
        if view=="summary":other_profiles(draft,sections)
        elif view=="year":other_paths(draft,sections);year_heatmaps(draft,sections,policies)
        else:other_paths(draft,sections,forward=False);phase2_context(draft,sections)
    elif view=="summary":primary_summary(draft,sections,policies)
    elif view=="year":year_heatmaps(draft,sections,policies)
    elif group in {"ema20-support","ema50-support"}:add_sessions(draft,sections,policies[0])
    if group in {"ema20-support","ema50-support"}:exposure_controls(draft,sections,policies[0])
    limit=30 if any(s["id"]=="uncertainty" for s in sections) else 29
    if len(sections)>limit or len(draft.figures)>12 or len(draft.downloads)>4:raise ValueError("planned supplement leaves no room for final uncertainty or exceeds report assets")
    return sections
