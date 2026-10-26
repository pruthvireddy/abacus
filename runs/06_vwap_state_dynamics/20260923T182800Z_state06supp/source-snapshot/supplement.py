"""Stage exploratory reporting additions from an immutable parent event ledger."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from src.features import digest
from src.reporting import classify


def clock_label(halfhour: int) -> str:
    if 36 <= halfhour < 40:
        return "pre_asia_gap"
    if halfhour >= 40 or halfhour < 6:
        return "asia"
    if halfhour < 18:
        return "london"
    if halfhour < 19:
        return "pre_ny_gap"
    if halfhour < 32:
        return "ny"
    if halfhour < 36:
        return "post_ny_gap"
    raise ValueError(halfhour)


def probability(frame: pd.DataFrame, label: str, rng: np.random.Generator) -> dict:
    n=len(frame)
    if not n:
        return {"numerator":0,"denominator":0,"probability":None,"ci_low":None,"ci_high":None,
                "product_sessions":0,"shared_dates":0}
    wins=int(frame[label].sum())
    by_date=frame.groupby("session_date")[label].agg(["sum","count"])
    weights=rng.multinomial(len(by_date),np.full(len(by_date),1/len(by_date)),size=400)
    draws=(weights@by_date["sum"].to_numpy())/(weights@by_date["count"].to_numpy())
    return {"numerator":wins,"denominator":n,"probability":wins/n,
            "ci_low":float(np.quantile(draws,.025)),"ci_high":float(np.quantile(draws,.975)),
            "product_sessions":int((frame["product"]+":"+frame.session_date).nunique()),
            "shared_dates":len(by_date)}


def fmt(value):
    return "n/a" if pd.isna(value) else f"{100*value:.1f}%"


def markdown(headers,rows):
    return "| "+" | ".join(headers)+" |\n| "+" | ".join(["---"]*len(headers))+" |\n"+"\n".join(
        "| "+" | ".join(map(str,row))+" |" for row in rows)+"\n"


def html_table(headers,rows):
    return ("<div class='table-wrap'><table><thead><tr>"
            + "".join(f"<th>{escape(str(x))}</th>" for x in headers)
            + "</tr></thead><tbody>"
            + "".join("<tr>"+"".join(f"<td>{escape(str(x))}</td>" for x in row)+"</tr>" for row in rows)
            + "</tbody></table></div>")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args()
    workspace=Path(__file__).resolve().parents[2]
    study=workspace/"studies/06_vwap_state_dynamics"
    parent_id="20260923T180000Z_state06c"
    parent=workspace/"runs/06_vwap_state_dynamics"/parent_id
    stage=workspace/"work/06_vwap_state_dynamics"/args.run_id
    if stage.exists():raise FileExistsError(stage)
    protocol=json.loads((study/"protocol-1.1.0.json").read_text())
    if protocol["status"]!="frozen_exploratory_supplement" or protocol["parent_run_id"]!=parent_id:
        raise ValueError("supplement protocol must be frozen against parent")
    ledger=json.loads((parent/"events.manifest.json").read_text())
    if ledger["row_count"]!=367719:raise ValueError("parent ledger count changed")
    for part in ledger["partitions"]:
        if digest(parent/part["path"])!=part["sha256"]:
            raise ValueError(f"parent event changed: {part['path']}")
    (stage/"tables").mkdir(parents=True)
    (stage/"figures").mkdir()
    for file in (parent/"tables").glob("*.csv"):
        shutil.copy2(file,stage/"tables"/file.name)
    for file in (parent/"figures").glob("*.svg"):
        shutil.copy2(file,stage/"figures"/file.name)
    for name in ("inputs.lock.json","input-verification.json"):
        shutil.copy2(parent/name,stage/name)
    for name in ("protocol-1.1.0.json","protocol-1.1.0.md"):
        shutil.copy2(study/name,stage/name)
    config={**protocol,"run_id":args.run_id,"started_at_utc":datetime.now(timezone.utc).isoformat(),
            "parent_manifest_sha256":digest(parent/"manifest.json"),
            "parent_events_manifest_sha256":digest(parent/"events.manifest.json")}
    (stage/"config.json").write_text(json.dumps(config,indent=2)+"\n")
    (stage/"events.manifest.json").write_text(json.dumps({"location":str(parent.relative_to(workspace)/"events"),
        "format":"Parquet","retention":"referenced_immutable_parent_run",
        "parent_run_id":parent_id,"parent_manifest_sha256":digest(parent/"manifest.json"),
        "parent_events_manifest_sha256":digest(parent/"events.manifest.json"),
        "row_count":ledger["row_count"],"partitions":ledger["partitions"]},indent=2)+"\n")
    events=pd.concat([pd.read_parquet(parent/part["path"]) for part in ledger["partitions"]],ignore_index=True)
    if len(events)!=367719 or events.event_id.duplicated().any():raise ValueError("parent events changed")
    base_config=json.loads((parent/"config.json").read_text())
    events=classify(events,base_config)
    primary=events[(events.timeframe=="2m")&(events.anchor=="globex")].copy()
    primary["explicit_clock"] = primary.local_halfhour.map(clock_label)
    if len(primary)!=133716:raise ValueError("primary count changed")
    rng=np.random.default_rng(607)
    # First-cross times: a noncross is censored and never assigned an event time.
    first=[]
    for product in ("ALL","ES","NQ","GC"):
        view=primary if product=="ALL" else primary[primary["product"]==product]
        for state in ("persistent","rotational","other"):
            part=view[view.state==state]
            crossed=part.first_cross_minute.dropna()
            first.append({"product":product,"state":state,"landmarks":len(part),
                "crossers":len(crossed),"noncross_censored_at_30m":len(part)-len(crossed),
                "cross_probability":len(crossed)/len(part),
                "first_cross_median_minutes_among_crossers":float(crossed.median()) if len(crossed) else None,
                "first_cross_q25_minutes_among_crossers":float(crossed.quantile(.25)) if len(crossed) else None,
                "first_cross_q75_minutes_among_crossers":float(crossed.quantile(.75)) if len(crossed) else None})
    pd.DataFrame(first).to_csv(stage/"tables/first_cross_time.csv",index=False)
    # Clock membership gaps are named explicitly. Every rate is exploratory.
    clock=[]
    order=("pre_asia_gap","asia","london","pre_ny_gap","ny","post_ny_gap")
    for product in ("ALL","ES","NQ","GC"):
        view=primary if product=="ALL" else primary[primary["product"]==product]
        for name in order:
            at=view[view.explicit_clock==name]
            for question,col,conditions,outcome in (
                ("Q1","state",("persistent","rotational"),"y1_residence"),
                ("Q2","slope_class",("opposing","aligned"),"y2_cross"),
                ("Q3",None,("all",),"vwap_win")):
                for condition in conditions:
                    part=at if col is None else at[at[col]==condition]
                    clock.append({"product":product,"clock_label":name,"question":question,
                        "condition":condition,**probability(part,outcome,rng)})
    clock_df=pd.DataFrame(clock)
    for (product,name),part in clock_df.groupby(["product","clock_label"]):
        for question,base in (("Q1","rotational"),("Q2","aligned")):
            baseline=part[(part.question==question)&(part.condition==base)].probability.iloc[0]
            mask=(clock_df["product"]==product)&(clock_df.clock_label==name)&(clock_df.question==question)
            clock_df.loc[mask,"baseline_probability"]=baseline
        mask=(clock_df["product"]==product)&(clock_df.clock_label==name)&(clock_df.question=="Q3")
        clock_df.loc[mask,"baseline_probability"]=1-clock_df.loc[mask,"probability"]
    clock_df.to_csv(stage/"tables/explicit_clock_windows.csv",index=False)
    # Prespecified Q3 secondary targets at identical timestamps.
    secondary=[]
    for (timeframe,anchor),cohort in events.groupby(["timeframe","anchor"]):
        for product in ("ALL","ES","NQ","GC"):
            view=cohort if product=="ALL" else cohort[cohort["product"]==product]
            adjustment=view.price_adjustment.to_numpy(dtype=float)*1e-9
            vwap=view.vwap.to_numpy(dtype=float)-adjustment
            twap=view.twap.to_numpy(dtype=float)-adjustment
            last=view.close.to_numpy(dtype=float)-adjustment
            for target_name,target_col in (("future_volume_weighted_1m_close","future_volume_weighted_price"),
                                           ("horizon_end_1m_close","future_end_close")):
                target=view[target_col].to_numpy(dtype=float)
                ve=np.abs(target-vwap);te=np.abs(target-twap);le=np.abs(target-last)
                temporary=view[["product","session_date"]].copy()
                temporary["vwap_win"]=ve<te-1e-8
                info=probability(temporary,"vwap_win",rng)
                secondary.append({"timeframe":timeframe,"anchor":anchor,"product":product,
                    "target":target_name,**info,"twap_wins":int(np.sum(te<ve-1e-8)),
                    "ties":int(np.sum(np.abs(ve-te)<=1e-8)),"vwap_mae_points":float(ve.mean()),
                    "twap_mae_points":float(te.mean()),"last_price_mae_points":float(le.mean()),
                    "mean_paired_error_difference_points":float((ve-te).mean())})
    secondary_df=pd.DataFrame(secondary)
    if (secondary_df.numerator+secondary_df.twap_wins+secondary_df.ties!=secondary_df.denominator).any():
        raise ValueError("secondary paired classes not exhaustive")
    secondary_df["baseline_probability"]=secondary_df.twap_wins/secondary_df.denominator
    secondary_df.to_csv(stage/"tables/secondary_paired_targets.csv",index=False)
    # These are descriptive feature distributions; no threshold or signal is selected.
    desc=[]
    for product in ("ALL","ES","NQ","GC"):
        view=primary if product=="ALL" else primary[primary["product"]==product]
        for cls in ("opposing","aligned","flat_or_unavailable"):
            part=view[view.slope_class==cls]
            desc.append({"product":product,"slope_class":cls,"landmarks":len(part),
                "median_abs_price_slope_prior_atr":float(part.price_slope_atr.abs().median()),
                "median_abs_vwap_slope_prior_atr":float(part.vwap_slope_atr.abs().median()),
                "median_signed_vwap_acceleration_points":float(part.vwap_acceleration.median()),
                "median_anchor_cumulative_volume":float(part.cumulative_volume.median()),
                "median_recent_30m_volume_share":float(part.recent_volume_share.median())})
    pd.DataFrame(desc).to_csv(stage/"tables/feature_descriptives.csv",index=False)
    # A full offline report includes the unchanged primary text and appended exploratory tables.
    main_md=(parent/"report.md").read_text()
    main_html=(parent/"report.html").read_text()
    first_df=pd.DataFrame(first)
    first_rows=[]
    for state in ("persistent","rotational","other"):
        r=first_df[(first_df["product"]=="ALL")&(first_df.state==state)].iloc[0]
        first_rows.append([state,f"{int(r.crossers):,}/{int(r.landmarks):,}",f"{int(r.noncross_censored_at_30m):,}",
                           f"{r.first_cross_median_minutes_among_crossers:.0f}",
                           f"{r.first_cross_q25_minutes_among_crossers:.0f}–{r.first_cross_q75_minutes_among_crossers:.0f}"])
    clock_rows=[]
    for name in order:
        view=clock_df[(clock_df["product"]=="ALL")&(clock_df.clock_label==name)]
        g=lambda q,c:view[(view.question==q)&(view.condition==c)].iloc[0]
        clock_rows.append([name,f"{int(g('Q3','all').denominator):,}",fmt(g('Q1','persistent').probability),
                           fmt(g('Q1','rotational').probability),fmt(g('Q2','opposing').probability),
                           fmt(g('Q2','aligned').probability),fmt(g('Q3','all').probability)])
    target_rows=[]
    for target in ("future_volume_weighted_1m_close","horizon_end_1m_close"):
        for product in ("ES","NQ","GC"):
            r=secondary_df[(secondary_df.timeframe=="2m")&(secondary_df.anchor=="globex")&
                           (secondary_df["product"]==product)&(secondary_df.target==target)].iloc[0]
            target_rows.append([target,product,f"{int(r.numerator):,}/{int(r.denominator):,}",fmt(r.probability),
                                f"{fmt(r.ci_low)}–{fmt(r.ci_high)}",fmt(r.baseline_probability),
                                str(int(r.ties)),f"{r.mean_paired_error_difference_points:.2f}"])
    sections=[
        ("First opposite-close crossing time", "Crossing time is measured at completed 2-minute closes among crossers. Noncrossers are censored at the 30-minute horizon and excluded from conditional time quartiles, while remaining in the all-landmark crossing denominator.",
         ["Q1 state","Crossers / all landmarks","No cross by 30m","Median min among crossers","Q25–Q75 min among crossers"],first_rows),
        ("Explicit local clock and membership gaps", "These clock strata were reported after primary outcome inspection and are exploratory. Gap labels refer to the landmark instant; the preceding feature bar can belong to an adjacent published membership window at the exact boundary.",
         ["NY local clock period","Landmarks","Q1 persistent","Q1 rotational","Q2 opposing","Q2 aligned","Q3 VWAP wins"],clock_rows),
        ("Q3 secondary paired targets", "The primary unweighted future median remains the prespecified Q3 target. The following two targets are fixed secondary sensitivities on the same landmarks and translated unadjusted contract coordinates. Ties remain explicit and last-price errors are in the saved table.",
         ["Future target","Product","VWAP wins / all","P(VWAP wins)","95% shared-date CI","P(TWAP wins)","Ties","Mean VWAP−TWAP error, pts"],target_rows)]
    add_md="\n## Exploratory reporting supplement 1.1.0\n\nThese additions were calculated from the unchanged sealed parent event ledger after primary outcomes had been viewed. They are descriptive, not new primary tests or protected confirmation.\n"
    add_html="<section><h2>Exploratory reporting supplement 1.1.0</h2><p>These additions were calculated from the unchanged sealed parent event ledger after primary outcomes had been viewed. They are descriptive, not new primary tests or protected confirmation.</p>"
    for title,prose,headers,rows in sections:
        add_md+=f"\n### {title}\n\n{prose}\n\n"+markdown(headers,rows)+"\n"
        add_html+=f"<h3>{escape(title)}</h3><p>{escape(prose)}</p>"+html_table(headers,rows)
    add_md+="\nFull product and clock denominators, feature magnitudes, and all separate replication target rows: [first-cross timing](tables/first_cross_time.csv), [explicit clock windows](tables/explicit_clock_windows.csv), [secondary paired targets](tables/secondary_paired_targets.csv), [feature descriptives](tables/feature_descriptives.csv). The [parent run](../20260923T180000Z_state06c/report.html) remains immutable.\n"
    add_html+="<p class='links'><a href='tables/first_cross_time.csv'>First-cross timing</a> · <a href='tables/explicit_clock_windows.csv'>Explicit clock windows</a> · <a href='tables/secondary_paired_targets.csv'>Secondary paired targets</a> · <a href='tables/feature_descriptives.csv'>Feature descriptives</a> · <a href='../20260923T180000Z_state06c/report.html'>Immutable parent run</a></p></section>"
    (stage/"report.md").write_text(main_md+add_md)
    (stage/"report.html").write_text(main_html.replace("<footer>",add_html+"<footer>"))
    (stage/"advice.md").write_text((parent/"advice.md").read_text()+"\n## 2026-09-23 exploratory reporting supplement\n\nFirst-cross timing, explicit clock gaps, and secondary paired targets are in this run's report and tables. They do not change the parent primary decision or establish an execution edge.\n")
    metrics=json.loads((parent/"metrics.json").read_text())
    metrics.update({"run_id":args.run_id,"parent_run_id":parent_id,"protocol_version":"1.1.0",
        "supplement_status":"exploratory_after_primary_outcomes_viewed",
        "supplement_tables":["first_cross_time","explicit_clock_windows","secondary_paired_targets","feature_descriptives"]})
    (stage/"metrics.json").write_text(json.dumps(metrics,indent=2,default=str)+"\n")
    (stage/"parent-verification.json").write_text(json.dumps({"parent_run_id":parent_id,
        "parent_manifest_sha256":digest(parent/"manifest.json"),
        "parent_events_manifest_sha256":digest(parent/"events.manifest.json"),
        "event_rows":len(events),"event_partitions_verified":len(ledger["partitions"]),
        "source":str(parent.relative_to(workspace))},indent=2)+"\n")
    print(json.dumps({"run_id":args.run_id,"parent_events":len(events),"clock_rows":len(clock_df),
        "secondary_rows":len(secondary_df),"first_cross_rows":len(first_df)}))


if __name__=="__main__":main()
