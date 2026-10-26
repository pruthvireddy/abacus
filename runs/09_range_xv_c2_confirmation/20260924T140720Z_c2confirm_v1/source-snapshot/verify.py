"""Audit identities, ledger arithmetic, timing, and selected literal source rows."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd


TRACES={"ES_5":[55,1250,1654]}


def read_raw(path: Path, wanted: set[int]) -> dict[int,list[str]]:
    found={}
    with path.open(newline="") as f:
        for row_number,row in enumerate(csv.reader(f,delimiter=";"),1):
            if row_number in wanted:
                found[row_number]=row
            if len(found)==len(wanted):break
    if set(found)!=wanted:raise AssertionError("source rows missing")
    return found


def read_enhanced(path: Path, wanted: set[int]) -> dict[int,dict]:
    found={}
    with path.open(newline="") as f:
        for row in csv.DictReader(f,delimiter=";"):
            row_number=int(row["source_row"])
            if row_number in wanted:
                found[row_number]=row
            if len(found)==len(wanted):break
    if set(found)!=wanted:raise AssertionError("enhanced rows missing")
    return found


def direction(row: dict) -> int:
    a,b=float(row["open"]),float(row["close"])
    return (b>a)-(b<a)


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--stage",required=True,type=Path)
    args=parser.parse_args()
    stage=args.stage.resolve()
    root=Path(__file__).resolve().parents[2]
    audit=json.loads((stage/"audit.json").read_text())
    lock=json.loads((stage/"inputs.lock.json").read_text())
    manifest=json.loads((root/lock["manifest"]["path"]).read_text())
    specs={(x["product"],x["setting_ticks"]):x for x in manifest["files"]}
    verified={x["path"]:x["sha256"] for x in audit["verified_inputs"]}
    assert verified[lock["manifest"]["path"]]==lock["manifest"]["sha256"]
    overall=pd.read_csv(stage/"tables"/"overall.csv")
    comparison=pd.read_csv(stage/"tables"/"comparison.csv")
    age2_comparison=pd.read_csv(stage/"tables"/"age2_comparison.csv")
    periods=pd.read_csv(stage/"tables"/"period.csv")
    opportunity_table=pd.read_csv(stage/"tables"/"opportunity_overall.csv")
    prior_bins=pd.read_csv(stage/"tables"/"prior_bin.csv")
    prior_opportunities=pd.read_csv(stage/"tables"/"prior_bin_opportunity.csv")
    snapback=pd.read_csv(stage/"tables"/"snapback.csv")
    tie_sensitivity=pd.read_csv(stage/"tables"/"snapback_tie_sensitivity.csv")
    price=pd.read_csv(stage/"tables"/"price.csv")
    price_delta=pd.read_csv(stage/"tables"/"price_delta.csv")
    chart_checks={}
    all_dates={}
    traces=[]
    for key,info in audit["charts"].items():
        product,setting_text=key.split("_");setting=int(setting_text)
        spec=specs[(product,setting)]
        assert verified[spec["source_path"]]==spec["source_sha256"]
        assert verified[spec["enhanced_path"]]==spec["enhanced_sha256"]
        assert info["bars"]==spec["rows"]
        assert info["session_dates"]==spec["session_dates_with_data"]
        assert info["status_counts"]==spec["completion_proxy_status_counts"]
        sessions=info["sessions"]
        dates=[x["date"] for x in sessions]
        assert dates==sorted(set(dates))
        assert sum(x["bars"] for x in sessions)==info["bars"]
        all_dates[key]=set(dates)
        opportunities=pd.read_parquet(stage/"tables"/f"opportunities_{key}.parquet")
        ordinary=pd.read_parquet(stage/"tables"/f"ordinary_{key}.parquet")
        assert len(opportunities)==info["opportunities"]==sum(x["c1_signals"] for x in sessions)
        assert len(ordinary)==info["ordinary_pairs"]==sum(x["ordinary_pairs"] for x in sessions)
        assert (opportunities.wait_two_success<=opportunities.c2_follows).all()
        assert (opportunities.wait_two_success<=opportunities.c3_follows).all()
        assert not opportunities.loc[opportunities.common_eligible,"c1_same_second"].any()
        assert not opportunities.loc[opportunities.common_eligible,"c2_same_second"].any()
        paired=opportunities.loc[opportunities.larger_context.ne("unavailable")]
        if len(paired):
            assert (pd.to_datetime(paired.larger_completion)<pd.to_datetime(paired.c1_completion)).all()
        main=opportunities.loc[opportunities.main_prior & opportunities.common_eligible &
                               ~opportunities.gc_gap_excluded]
        candidate=main.loc[main.c2_follows]
        base=ordinary.loc[~ordinary.gc_gap_excluded]
        age2=base.loc[base.pair_run_age.eq(2)]
        assert age2.pair_run_age.eq(2).all()
        overlap=np.intersect1d(candidate.c2_source_row.to_numpy(),base.b2_source_row.to_numpy())
        assert len(overlap)==0, f"candidate leaked into ordinary baseline: {key}"
        for d in (-1,1):
            m=main.loc[main.direction==d]
            c=candidate.loc[candidate.direction==d]
            b=base.loc[base.direction==d]
            first=overall.loc[(overall["product"]==product)&(overall.setting==setting)&
                              (overall.direction==d)&overall.metric.eq("next2")].iloc[0]
            assert (int(first.numerator),int(first.denominator),int(first.baseline_numerator),
                    int(first.baseline_denominator))==(int(c.wait_two_success.sum()),len(c),
                        int(b.two_success.sum()),len(b))
            opp=opportunity_table.loc[(opportunity_table["product"]==product)&
                (opportunity_table.setting==setting)&(opportunity_table.direction==d)]
            conf=opp.loc[opp.metric.eq("c2_confirms")].iloc[0]
            wait=opp.loc[opp.metric.eq("wait_two_per_c1")].iloc[0]
            assert (int(conf.numerator),int(conf.denominator))==(len(c),len(m))
            assert (int(wait.numerator),int(wait.denominator))==(int(c.wait_two_success.sum()),len(m))
            bin_counts=prior_opportunities.loc[(prior_opportunities["product"]==product)&
                (prior_opportunities.setting==setting)&(prior_opportunities.direction==d)&
                prior_opportunities.metric.eq("c2_confirms")]
            assert len(bin_counts)==3
            assert (int(bin_counts.denominator.sum()),int(bin_counts.numerator.sum()))==(len(m),len(c))
            bin_outcomes=prior_bins.loc[(prior_bins["product"]==product)&
                (prior_bins.setting==setting)&(prior_bins.direction==d)&
                prior_bins.metric.eq("next2")]
            assert len(bin_outcomes)==3
            assert (int(bin_outcomes.denominator.sum()),int(bin_outcomes.numerator.sum()))==(
                len(c),int(c.wait_two_success.sum()))
            cells=comparison.loc[(comparison["product"]==product)&(comparison.setting==setting)&
                (comparison.direction==d)&comparison.metric.eq("next2")]
            assert (int(cells.denominator.sum()),int(cells.numerator.sum()),
                    int(cells.baseline_denominator.sum()))==(len(c),int(c.wait_two_success.sum()),len(b))
            for _,cell in cells.iterrows():
                blocks=periods.loc[(periods["product"]==product)&(periods.setting==setting)&
                    (periods.direction==d)&(periods.decision_window==cell.decision_window)&
                    periods.metric.eq("next2")]
                assert (int(blocks.numerator.sum()),int(blocks.denominator.sum()))==(
                    int(cell.numerator),int(cell.denominator))
            age2_cells=age2_comparison.loc[(age2_comparison["product"]==product)&
                (age2_comparison.setting==setting)&(age2_comparison.direction==d)&
                age2_comparison.metric.eq("next2")]
            assert int(age2_cells.baseline_denominator.sum())==len(age2.loc[age2.direction==d])
            wait_price=price.loc[(price["product"]==product)&(price.setting==setting)&
                (price.direction==d)&price.policy.eq("wait_per_c1")]
            if len(m):
                expected=c.wait_signed_ticks.sum()/len(m)
                assert abs(float(wait_price.iloc[0].mean_signed_ticks)-expected)<1e-9
                delta=price_delta.loc[(price_delta["product"]==product)&
                    (price_delta.setting==setting)&(price_delta.direction==d)].iloc[0]
                expected_delta=(c.wait_signed_ticks.sum()-m.immediate_signed_ticks.sum())/len(m)
                assert abs(float(delta.mean_signed_ticks)-expected_delta)<1e-9
            if key in {"ES_4","ES_5","GC_6","NQ_10"}:
                strict=snapback.loc[(snapback["product"]==product)&
                    (snapback.setting==setting)&(snapback.direction==d)&
                    snapback.metric.eq("c2_confirms")].iloc[0]
                strict_sensitivity=tie_sensitivity.loc[(tie_sensitivity["product"]==product)&
                    (tie_sensitivity.setting==setting)&(tie_sensitivity.direction==d)&
                    tie_sensitivity.metric.eq("c2_confirms")&
                    tie_sensitivity.sensitivity.eq("strict_no_ties")].iloc[0]
                assert (int(strict.numerator),int(strict.denominator))==(
                    int(strict_sensitivity.numerator),int(strict_sensitivity.denominator))
        chart_checks[key]={"bars":info["bars"],"session_dates":info["session_dates"],
            "c1_signals":len(opportunities),"main_opportunities":len(main),
            "c2_confirmed":len(candidate),"ordinary_pairs":len(base),
            "main_completion_or_boundary_excluded":sum(x["main_excluded_completion_or_boundary"] for x in sessions),
            "main_c1_same_second":sum(x["main_c1_same_second"] for x in sessions),
            "age2_ordinary_pairs":len(age2),
            "candidate_pairs_removed_from_ordinary":sum(x["candidate_pairs_removed_from_ordinary"] for x in sessions),
            "larger_equal_second_ties":sum(x["larger_equal_second_ties"] for x in sessions)}
        if key in TRACES:
            selected=opportunities.loc[opportunities.c1_source_row.isin(TRACES[key])]
            assert len(selected)==len(TRACES[key])
            wanted=set()
            for _,event in selected.iterrows():
                wanted.update(range(int(event.c1_source_row-event.prior_run),int(event.c1_source_row+5)))
            source=read_raw(root/spec["source_path"],wanted)
            enhanced=read_enhanced(root/spec["enhanced_path"],wanted)
            for _,event in selected.iterrows():
                row=int(event.c1_source_row)
                prior=[direction(enhanced[j]) for j in range(row-int(event.prior_run),row)]
                future=[direction(enhanced[j]) for j in range(row,row+4)]
                assert len(set(prior))==1 and prior[0]==-int(event.direction)
                assert future[0]==int(event.direction)
                assert (future[1]==future[0])==bool(event.c2_follows)
                assert (future[2]==future[0])==bool(event.c3_follows)
                assert (future[3]==future[0])==bool(event.c4_follows)
                for j in range(row-int(event.prior_run),row+4):
                    x=enhanced[j]
                    assert source[j]==[x["source_timestamp"],x["open"],x["high"],x["low"],x["close"]]
                if event.common_eligible:
                    tick=.25
                    immediate=int(event.direction)*round((float(enhanced[row+3]["open"])-
                                                           float(enhanced[row+1]["open"]))/tick)
                    assert immediate==event.immediate_signed_ticks
                    if event.c2_follows:
                        waiting=int(event.direction)*round((float(enhanced[row+4]["open"])-
                                                             float(enhanced[row+2]["open"]))/tick)
                        assert waiting==event.wait_signed_ticks
                traces.append({"chart":key,"session_date":event.session_date,"c1_source_row":row,
                    "prior_run":int(event.prior_run),"c2_source_row":row+1,
                    "c3_source_row":row+2,"c4_source_row":row+3,
                    "direction_path":f"{prior[0]}x{len(prior)},{','.join(str(x) for x in future)}",
                    "c2_confirms":bool(event.c2_follows),"wait_two_success":bool(event.wait_two_success),
                    "immediate_signed_ticks":float(event.immediate_signed_ticks),
                    "wait_signed_ticks":float(event.wait_signed_ticks) if event.c2_follows else None,
                    "c1_completion":event.c1_completion,"c2_completion":event.c2_completion})
    missing_gc={key:sorted(all_dates["ES_5"]-dates) for key,dates in all_dates.items() if key.startswith("GC_")}
    pd.DataFrame(traces).to_csv(stage/"tables"/"real_event_traces.csv",index=False)
    checks={"status":"pass","manifest_sha256":lock["manifest"]["sha256"],
            "charts":chart_checks,"gc_dates_absent_relative_to_es":missing_gc,
            "trace_count":len(traces),"checks":["input hashes and manifest row/status/session counts",
                "source row and timestamp ordering","ordinary baseline disjoint from candidates",
                "C1 opportunity and conditional denominators","period/window arithmetic",
                "exploratory age-two ordinary baseline arithmetic",
                "prespecified prior-bin and equal-second sensitivity arithmetic",
                "strict no-look-ahead larger state","price policy mean arithmetic",
                "paired wait-minus-immediate price arithmetic",
                "literal source/enhanced row and price traces"]}
    (stage/"checks.json").write_text(json.dumps(checks,indent=2)+"\n")
    print(json.dumps({"status":"pass","charts":len(chart_checks),"traces":len(traces),
                      "gc_absent_dates":missing_gc},indent=2))


if __name__=="__main__":main()
