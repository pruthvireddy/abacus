"""Saved-ledger summaries and paired calendar-block percentile uncertainty."""
import itertools
import json
import numpy as np
import pandas as pd
from .calendar import week
from .spec import PERIODS, PRODUCTS, MODES, HORIZONS, SETTINGS
from .events import select_events
from .execution import EXTENSIONS
from .storage import save_csv, save_json, sha, utc_now

class Bootstrap:
    def __init__(self, start, end, block_weeks=4, replicates=10000, seed=20261008):
        first=pd.Timestamp(week(start));last=pd.Timestamp(week(end))
        self.weeks=pd.date_range(first,last,freq="W-MON").strftime("%Y-%m-%d").tolist()
        self.block_weeks=block_weeks
        self.map={w:i//block_weeks for i,w in enumerate(self.weeks)}
        self.blocks=(len(self.weeks)+block_weeks-1)//block_weeks
        rng=np.random.default_rng(seed)
        draws=rng.integers(0,self.blocks,size=(replicates,self.blocks))
        self.weights=np.stack([np.bincount(d,minlength=self.blocks) for d in draws]).astype(float)
        self.replicates=replicates

    def distribution(self, frame, value="delta"):
        sums=np.zeros(self.blocks);counts=np.zeros(self.blocks)
        f=frame.loc[frame[value].notna(),["week",value]]
        for w,g in f.groupby("week"):
            if w not in self.map:
                raise AssertionError("Outcome outside frozen split")
            k=self.map[w];sums[k]+=g[value].sum();counts[k]+=len(g)
        denominator=self.weights@counts
        result=np.divide(self.weights@sums,denominator,out=np.full(self.replicates,np.nan),where=denominator>0)
        if np.count_nonzero(counts)<2:
            result[:]=np.nan
        return result,int(np.count_nonzero(counts))

def interval(draws,coverage=.95):
    finite=draws[np.isfinite(draws)]
    if len(finite)<2:
        return (np.nan,np.nan)
    tail=(1-coverage)/2
    return tuple(np.quantile(finite,[tail,1-tail]))

def path_summary(accepted, outcomes, bootstrap=None):
    rows=outcomes[outcomes.event_id.isin(accepted.event_id)]
    g=rows[rows.completed].merge(accepted[["event_id","day","week"]],on="event_id",validate="one_to_one")
    n=len(g);entered=int(rows.entered.sum())
    out={"accepted":len(accepted),"entered":entered,"completed_N":n,"entry_cancelled":len(accepted)-entered,"censored_entered":entered-n,"sessions":g.day.nunique(),"favorable_N":int(g.favorable.sum()),"favorable_share":g.favorable.mean(),"literal_above_share":g.literal_above.mean(),"defended_share":g.defended.mean(),"MFE_gt_MAE_share":g.mfe_gt_mae.mean(),"favorable_lower_bound_entered":g.favorable.sum()/entered if entered else np.nan,"favorable_upper_bound_entered":(g.favorable.sum()+entered-n)/entered if entered else np.nan,"mean_delta":g.delta.mean(),"mean_delta_points":g.delta_points.mean(),"mean_MAE":g.mae.mean(),"mean_MFE":g.mfe.mean(),"session_balanced_delta":g.groupby("day").delta.mean().mean(),"sparse":n<100 or g.day.nunique()<30}
    for name in ("mae","mfe","delta"):
        for q,label in ((.5,"median"),(.75,"q75"),(.9,"q90")):
            out[f"{name}_{label}"]=g[name].quantile(q)
    for name in ("mae","mfe","favorable","literal_above","defended"):
        out["session_balanced_"+name]=g.groupby("day")[name].mean().mean()
    if bootstrap:
        draws,support=bootstrap.distribution(g)
        out["ci95_low"],out["ci95_high"]=interval(draws)
        out["support_blocks"]=support
        out["undefined_bootstrap_draws"]=int(np.isnan(draws).sum())
        for name in ("mae","mfe","favorable"):
            distribution,_=bootstrap.distribution(g,name)
            out[name+"_ci95_low"],out[name+"_ci95_high"]=interval(distribution)
        session_means=g.groupby(["day","week"],as_index=False).delta.mean()
        distribution,_=bootstrap.distribution(session_means)
        out["session_balanced_ci95_low"],out["session_balanced_ci95_high"]=interval(distribution)
    return out

def policy_summary(s,t,bootstrap=None):
    completed=s[s.net_R.notna()]
    entered=t[t.entered] if len(t) else t
    resolved=entered[entered.net_R.notna()] if len(entered) else entered
    values=completed.sort_values("day").net_R.to_numpy()
    curve=np.r_[0,np.cumsum(values)]
    positives=resolved.net_R.clip(lower=0).sum() if len(resolved) else 0
    negative=-resolved.net_R.clip(upper=0).sum() if len(resolved) else 0
    out={"eligible_sessions":len(s),"scorable_sessions":len(completed),"unresolved_sessions":int(s.unresolved.sum()),"mean_net_R_per_session":completed.net_R.mean(),"session_net_R_sum":completed.net_R.sum(),"entered_trades":len(entered),"resolved_trades":len(resolved),"unresolved_trades":len(entered)-len(resolved),"cancelled_entries":len(t)-len(entered),"ambiguous_trades":int(entered.ambiguous.sum()) if len(entered) else 0,"occupancy_skips":int(s.occupancy_skips.sum()),"mean_net_R_per_trade":resolved.net_R.mean() if len(resolved) else np.nan,"median_net_R_per_trade":resolved.net_R.median() if len(resolved) else np.nan,"net_USD_resolved_trades":resolved.net_USD.sum() if len(resolved) else 0,"gross_USD_resolved_trades":resolved.gross_USD.sum() if len(resolved) else 0,"profit_factor_R":positives/negative if negative else np.nan,"cost_budget_USD_per_resolved_trade":resolved.gross_USD.mean() if len(resolved) else np.nan,"completed_session_drawdown_R":float(max(np.maximum.accumulate(curve)-curve)),"median_holding_minutes":resolved.holding_minutes.median() if len(resolved) else np.nan,"mean_holding_minutes":resolved.holding_minutes.mean() if len(resolved) else np.nan,"sparse":len(resolved)<100 or len(completed)<30}
    for label in ("target","stop","stop_gap","timeout","unresolved_missing_path_or_1600_open"):
        out[label+"_N"]=int((entered.reason==label).sum()) if len(entered) else 0
    if len(resolved):
        months=resolved.assign(month=resolved.day.str[:7]).groupby("month").net_R.sum()
        out["best_month_net_R"]=months.max()
        out["best_month_share_signed_total"]=months.max()/resolved.net_R.sum() if resolved.net_R.sum()!=0 else np.nan
    if bootstrap:
        draws,support=bootstrap.distribution(completed,"net_R")
        out["ci95_low"],out["ci95_high"]=interval(draws)
        out["support_blocks"]=support
        out["undefined_bootstrap_draws"]=int(np.isnan(draws).sum())
    return out

POLICY_KEYS=["pair","mode","extension","fee_USD","slippage_ticks","target","delay","touch","order_assumption","window"]

def baseline_policy_mask(frame, mode=None, order=None):
    sel=(frame.pair=="3")&(frame.extension=="core")&(frame.fee_USD==10)&(frame.slippage_ticks==1)&(frame.target=="3R")&(frame.delay==0)&~frame.touch&(frame.window=="main")
    if mode:sel&=frame["mode"]==mode
    if order:sel&=frame.order_assumption==order
    return sel

def summarize(work):
    if not (work/"scoring-complete.json").exists():raise RuntimeError("Scoring prerequisite absent")
    boot={s:Bootstrap(a,b) for s,(a,b) in PERIODS.items()}
    horizon_rows,extension_rows,policy_rows,annual_rows,weekly_rows,threshold_rows,stability_rows,contrast_rows,compare_rows,annual_policy_rows,tail_rows=[] ,[],[],[],[],[],[],[],[],[],[]
    coverage_all=[]
    joint_rows=[]
    daily_rows=[]
    monthly_rows=[]
    for product in PRODUCTS:
        events=pd.read_parquet(work/"private"/f"events_{product}.parquet")
        outcomes=pd.read_parquet(work/"private"/f"outcomes_{product}.parquet")
        ordering=pd.read_parquet(work/"private"/f"ordering_{product}.parquet")
        trades=pd.read_parquet(work/"private"/f"trades_{product}.parquet")
        sessions=pd.read_parquet(work/"private"/f"policy_sessions_{product}.parquet")
        coverage=pd.read_csv(work/"tables"/f"coverage_{product}.csv",dtype={"day":str})
        coverage_all.append(coverage)
        ds=sessions[baseline_policy_mask(sessions)&sessions["mode"].isin(("none","alignment"))]
        daily_rows.extend(ds[["product","day","week","year","split","mode","order_assumption","entered","ambiguous","unresolved","net_R","net_USD"]].to_dict("records"))
        final_ev=select_events(events,"3","alignment")
        final_ev=final_ev[final_ev.split=="final_evaluation"]
        joint=outcomes[(outcomes.horizon==15)&outcomes.completed&outcomes.event_id.isin(final_ev.event_id)]
        bins=[0,.5,1,2,3,5,np.inf]
        hist,_,_=np.histogram2d(joint.mae,joint.mfe,bins=[bins,bins])
        for i,j in itertools.product(range(6),repeat=2):
            joint_rows.append({"table_id":"T12","product":product,"split":"final_evaluation","pair":"3","mode":"alignment","horizon":15,"MAE_bin_low":bins[i],"MAE_bin_high":bins[i+1] if np.isfinite(bins[i+1]) else "inf","MFE_bin_low":bins[j],"MFE_bin_high":bins[j+1] if np.isfinite(bins[j+1]) else "inf","N":int(hist[i,j]),"completed_N":len(joint)})
        for split,pair,mode,side,h in itertools.product(PERIODS,("2","3","4"),MODES,("both","long","short"),(*HORIZONS,0)):
            ev=select_events(events,pair,mode)
            ev=ev[ev.split==split]
            if side!="both":ev=ev[ev.side==side]
            summary=path_summary(ev,outcomes[outcomes.horizon==h],boot[split])
            none=select_events(events,pair,"none")
            none=none[none.split==split]
            if side!="both":none=none[none.side==side]
            eligible_N=int(coverage.loc[coverage.split==split,"eligible"].sum())
            horizon_rows.append({"table_id":"T01","product":product,"split":split,"pair":pair,"mode":mode,"side":side,"horizon":h,"elapsed_minutes":h*5 if h else np.nan,"eligible_sessions":eligible_N,"accepted_per_eligible_session":len(ev)/eligible_N if eligible_N else np.nan,"filter_acceptance":len(ev)/len(none) if len(none) else np.nan,**summary})
        print(f"{product}: complete core horizon grid summarized",flush=True)
        extension_specs=[(ext,"3","alignment","main") for ext in EXTENSIONS]+[("core",pair,mode,"main") for pair,mode in itertools.product(("control225","control325"),("none","alignment"))]+[("continuation","4","alignment","main")]+[("core","3",mode,"session") for mode in ("none","alignment")]
        for split,(ext,pair,mode,win) in itertools.product(PERIODS,extension_specs):
            ev=select_events(events,pair,mode,ext,win,product)
            ev=ev[ev.split==split]
            extension_rows.append({"table_id":"T02","product":product,"split":split,"extension":ext,"pair":pair,"mode":mode,"window":win,"horizon":15,**path_summary(ev,outcomes[outcomes.horizon==15],boot[split])})
        for keys,s in sessions.groupby(POLICY_KEYS,dropna=False,sort=False):
            selector=np.ones(len(trades),dtype=bool)
            for key,value in zip(POLICY_KEYS,keys):selector&=trades[key]==value
            t=trades[selector]
            for split in PERIODS:
                policy_rows.append({"table_id":"T03","product":product,"split":split,**dict(zip(POLICY_KEYS,keys)),**policy_summary(s[s.split==split],t[t.split==split],boot[split])})
        print(f"{product}: fixed policy and cost tables summarized",flush=True)
        for year in range(2010,2027):
            annual_boot=Bootstrap(max(f"{year}-01-01","2010-06-07"),min(f"{year}-12-31","2026-09-18"))
            c=coverage[coverage.year==year]
            for pair,mode,side in itertools.product(("2","3","4"),MODES,("both","long","short")):
                ev=select_events(events,pair,mode)
                ev=ev[ev.year==year]
                if side!="both":ev=ev[ev.side==side]
                annual_rows.append({"table_id":"T04","product":product,"year":year,"split":c.split.iloc[0],"period_end":"2026-09-18" if year==2026 else f"{year}-12-31","pair":pair,"mode":mode,"side":side,"horizon":15,"exclusion_share":1-c.eligible.mean(),**path_summary(ev,outcomes[outcomes.horizon==15],annual_boot)})
            for mode in ("none","alignment"):
                s=sessions[baseline_policy_mask(sessions,mode,"stop_first")&(sessions.year==year)]
                t=trades[baseline_policy_mask(trades,mode,"stop_first")&trades.day.str.startswith(str(year))]
                annual_policy_rows.append({"table_id":"T05","product":product,"year":year,"mode":mode,"split":c.split.iloc[0],**policy_summary(s,t,annual_boot)})
        for split in PERIODS:
            c=coverage[(coverage.split==split)&coverage.eligible]
            for month in sorted(set(c.day.str[:7])):
                start=max(month+"-01",PERIODS[split][0])
                end=min((pd.Timestamp(month+"-01")+pd.offsets.MonthEnd()).strftime("%Y-%m-%d"),PERIODS[split][1])
                bm=Bootstrap(start,end)
                for mode in ("none","alignment"):
                    mev=select_events(events,"3",mode)
                    mev=mev[mev.day.str.startswith(month)]
                    ms=sessions[baseline_policy_mask(sessions,mode,"stop_first")&sessions.day.str.startswith(month)]
                    mt=trades[baseline_policy_mask(trades,mode,"stop_first")&trades.day.str.startswith(month)]
                    ps=path_summary(mev,outcomes[outcomes.horizon==15],bm)
                    rs=policy_summary(ms,mt,bm)
                    monthly_rows.append({"table_id":"T14","product":product,"split":split,"month":month,"mode":mode,"completed_N":ps["completed_N"],"sessions":ps["sessions"],"mean_delta":ps["mean_delta"],"delta_ci95_low":ps["ci95_low"],"delta_ci95_high":ps["ci95_high"],"path_support_blocks":ps["support_blocks"],"scorable_policy_sessions":rs["scorable_sessions"],"mean_net_R_per_session":rs["mean_net_R_per_session"],"policy_ci95_low":rs["ci95_low"],"policy_ci95_high":rs["ci95_high"],"policy_support_blocks":rs["support_blocks"],"sparse":ps["sparse"]})
            weeks=sorted({week(d) for d in c.day})
            for mode in ("none","alignment"):
                ev=select_events(events,"3",mode);ev=ev[ev.split==split]
                path=outcomes[outcomes.horizon==15]
                for w in [*weeks,"TOTAL"]:
                    one=ev if w=="TOTAL" else ev[ev.week==w]
                    res=path_summary(one,path)
                    partial=w!="TOTAL" and ((w==week(PERIODS[split][0]) and pd.Timestamp(PERIODS[split][0]).weekday()!=0) or (w==week(PERIODS[split][1]) and pd.Timestamp(PERIODS[split][1]).weekday()<4))
                    weekly_rows.append({"table_id":"T06","product":product,"split":split,"mode":mode,"week":w,"eligible_sessions":len(c) if w=="TOTAL" else int(sum(week(d)==w for d in c.day)),"partial_week":partial,**res})
            base=select_events(events,"3","none");base=base[base.split==split]
            for mode in MODES:
                passing=base if mode=="none" else base[base[mode].fillna(False)]
                failing=base.iloc[:0] if mode=="none" else base[base[mode]==False]
                complete=outcomes[(outcomes.horizon==15)&outcomes.completed]
                joined=complete.merge(base[["event_id","week","day"]],on="event_id")
                pass_g=joined[joined.event_id.isin(passing.event_id)]
                fail_g=joined[joined.event_id.isin(failing.event_id)]
                dist_base,_=boot[split].distribution(joined)
                dist_pass,_=boot[split].distribution(pass_g)
                dist_fail,_=boot[split].distribution(fail_g)
                low,high=interval(dist_pass-dist_base)
                fl,fh=interval(dist_pass-dist_fail)
                compare_rows.append({"table_id":"T07","product":product,"split":split,"pair":"3","mode":mode,"accepted_base":len(base),"accepted_pass":len(passing),"accepted_fail":len(failing),"completed_pass":len(pass_g),"completed_fail":len(fail_g),"pass_mean_delta":pass_g.delta.mean(),"fail_mean_delta":fail_g.delta.mean(),"none_mean_delta":joined.delta.mean(),"pass_minus_none":pass_g.delta.mean()-joined.delta.mean(),"contrast_ci95_low":low,"contrast_ci95_high":high,"pass_minus_fail":pass_g.delta.mean()-fail_g.delta.mean(),"pass_fail_ci95_low":fl,"pass_fail_ci95_high":fh})
            for block in (1,4,8):
                bs=boot[split] if block==4 else Bootstrap(*PERIODS[split],block_weeks=block)
                complete=outcomes[(outcomes.horizon==15)&outcomes.completed].merge(base[["event_id","week","alignment"]],on="event_id")
                passing=complete[complete.alignment.fillna(False)]
                a,sa=bs.distribution(passing);b,sb=bs.distribution(complete)
                diff=a-b
                l,h=interval(diff);fl,fh=interval(diff,1-.05/6)
                contrast_rows.append({"table_id":"T08","product":product,"split":split,"endpoint":"path_delta_ATR","order_assumption":"independent_paths","block_weeks":block,"estimate":passing.delta.mean()-complete.delta.mean(),"ci95_low":l,"ci95_high":h,"family_low":fl,"family_high":fh,"N_none":len(complete),"N_alignment":len(passing),"support_blocks":min(sa,sb),"undefined_draws":int(np.isnan(diff).sum()),"units":"ATR per completed event"})
                for order in ("stop_first","target_first"):
                    sp=sessions[sessions.split==split]
                    none=sp[baseline_policy_mask(sp,"none",order)]
                    aligned=sp[baseline_policy_mask(sp,"alignment",order)]
                    paired=none[["day","week","net_R"]].merge(aligned[["day","net_R"]],on="day",suffixes=("_none","_align"),validate="one_to_one")
                    paired["delta"]=paired.net_R_align-paired.net_R_none
                    ds,support=bs.distribution(paired)
                    l,h=interval(ds);fl,fh=interval(ds,1-.05/6)
                    contrast_rows.append({"table_id":"T08","product":product,"split":split,"endpoint":"policy_net_R_per_session","order_assumption":order,"block_weeks":block,"estimate":paired.delta.mean(),"ci95_low":l,"ci95_high":h,"family_low":fl,"family_high":fh,"N_none":len(none),"N_alignment":len(aligned),"paired_scorable_N":int(paired.delta.notna().sum()),"support_blocks":support,"undefined_draws":int(np.isnan(ds).sum()),"units":"net R per paired scorable eligible session"})
            for pair,mode,h in itertools.product(("2","3","4"),MODES,HORIZONS):
                ev=select_events(events,pair,mode);ev=ev[ev.split==split]
                for threshold in (.5,1,2):
                    g=ordering[(ordering.horizon==h)&(ordering.threshold_ATR==threshold)&ordering.event_id.isin(ev.event_id)]
                    counts=g.order.value_counts().to_dict()
                    threshold_rows.append({"table_id":"T09","product":product,"split":split,"pair":pair,"mode":mode,"horizon":h,"favorable_threshold_ATR":threshold,"adverse_threshold_ATR":1,"accepted":len(ev),"entered_N":int((g.order!="entry_cancelled").sum()),"complete_minute_paths_N":int(g.complete_minute_path.sum()),**{name:counts.get(name,0) for name in ("favorable_first","adverse_first","same_minute_ambiguous","neither","censored","entry_cancelled")},"median_time_MFE_minute":g.loc[g.complete_minute_path,"MFE_first_interval_minute"].median(),"median_time_MAE_minute":g.loc[g.complete_minute_path,"MAE_first_interval_minute"].median(),"prior_close_hit_completed_share":g.loc[g.complete_minute_path,"prior_close_hit"].mean(),"opposite_pivot_hit_completed_share":g.loc[g.complete_minute_path,"opposite_pivot_hit"].mean()})
            aligned=select_events(events,"3","alignment");aligned=aligned[aligned.split==split]
            aligned["entry_bin"]=pd.cut(aligned.entry_minute_NY,[570,600,630,660,690],right=False,labels=("0930-1000","1000-1030","1030-1100","1100-1130"))
            for dimension in ("entry_bin","prior_range_tertile","atr_tertile","side"):
                aligned[dimension]=aligned[dimension].astype("string").fillna("undefined")
                for tag,g in aligned.groupby(dimension,observed=True):
                    stability_rows.append({"table_id":"T10","product":product,"split":split,"dimension":dimension,"tag":str(tag),"pair":"3","mode":"alignment","horizon":15,**path_summary(g,outcomes[outcomes.horizon==15],boot[split])})
            tail=outcomes[(outcomes.horizon==15)&outcomes.completed&outcomes.event_id.isin(aligned.event_id)]
            values=tail.delta.to_numpy();order=np.argsort(np.abs(values))[::-1]
            tail_rows.append({"table_id":"T11","product":product,"split":split,"completed_N":len(tail),"mean_delta":tail.delta.mean(),"mean_without_largest_absolute_event":np.mean(values[order[1:]]) if len(values)>1 else np.nan,"mean_without_largest_absolute_1pct":np.mean(values[order[max(1,int(np.ceil(len(values)*.01))):]]) if len(values)>1 else np.nan,"top5_absolute_share":np.abs(values[order[:5]]).sum()/np.abs(values).sum() if np.abs(values).sum() else np.nan})
        print(f"{product}: annual, weekly, uncertainty and controls saved to summaries",flush=True)
    outputs={"horizons":horizon_rows,"extensions":extension_rows,"policy":policy_rows,"annual":annual_rows,"annual_policy":annual_policy_rows,"weekly":weekly_rows,"cloud_comparisons":compare_rows,"primary_contrasts":contrast_rows,"threshold_ordering":threshold_rows,"stability":stability_rows,"tail_diagnostics":tail_rows,"joint_excursions":joint_rows,"daily_reference":daily_rows,"monthly":monthly_rows}
    for name,rows in outputs.items():save_csv(work/"tables"/(name+".csv"),pd.DataFrame(rows))
    coverage=pd.concat(coverage_all,ignore_index=True)
    audit=[]
    for keys,g in coverage.groupby(["product","split","year"],sort=False):
        audit.append({"table_id":"T00","product":keys[0],"split":keys[1],"year":keys[2],"candidate_weekdays":len(g),"eligible_sessions":int(g.eligible.sum()),"HLC_valid_sessions":int(g.HLC_valid.sum()),"strict_HLC_sessions":int(g.HLC_strict.sum()),"roll_sessions":int(g.roll_session.sum()),"source_degraded_sessions":int(g.condition_degraded.sum()),"holiday_shortened_sessions":int(g.holiday.sum()),"expected_minutes":int(g.expected_minutes.sum()),"observed_minutes":int(g.observed_minutes.sum()),"source_minute_coverage":g.observed_minutes.sum()/g.expected_minutes.sum(),"outside_calendar_minutes":int(g.outside_calendar_minutes.sum()),"reassigned_source_minutes":int(g.reassigned_source_minutes.sum()),"complete_5m":int(g.full_5m.sum()),"partial_5m":int(g.partial_5m.sum()),"main_window_observed_minutes":int(g.main_window_minutes.sum()),"eligible_incomplete_window_sessions":int((g.eligible&~g.signal_window_complete).sum())})
    save_csv(work/"tables/coverage_summary.csv",pd.DataFrame(audit))
    exclusions=[]
    for _,r in coverage.iterrows():
        for reason in str(r.eligible_reasons).split(";"):
            if reason and reason!="nan":exclusions.append({"product":r["product"],"split":r.split,"year":r.year,"reason":reason})
    save_csv(work/"tables/exclusions.csv",pd.DataFrame(exclusions).groupby(["product","split","year","reason"]).size().reset_index(name="N_overlapping_reasons"))
    table_index={f"T{i:02}":{"artifact":f"tables/{name}.csv","sha256":sha(work/"tables"/(name+".csv")),"rows":len(rows)} for i,(name,rows) in enumerate(outputs.items(),1)}
    table_index["T00"]={"artifact":"tables/coverage_summary.csv","sha256":sha(work/"tables/coverage_summary.csv"),"rows":len(audit)}
    save_json(work/"metrics.json",{"schema":"study20-metrics-1","generated_at":utc_now(),"tables":table_index,"metric_definitions":{"path":"ATR-normalized per-event observations; delta signed, MAE/MFE nonnegative; completed-case means; frozen confirmation ATR14", "policy":"assumed-fill one-contract replay; net R divided by entry-fill-to-stop risk; completed-case scorable session mean includes observed valid no-trade zeros", "uncertainty":"10000 paired fixed calendar-block percentile draws; 4 weeks main, 1/8 weeks sensitivity; 6 primary Bonferroni intervals", "missing":"CSV empty is undefined; measured zero is 0; missing unbounded prices have no invented continuous bounds", "horizon0":"separate terminal close at 16:00; variable elapsed time", "drawdown":"observed cumulative scorable-session net R drawdown; unresolved days omitted, no full-history bound"}})
    save_json(work/"summarization-complete.json",{"completed_at":utc_now()})
