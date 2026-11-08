#!/usr/bin/env python3
"""Independent fixed-rule audit of four saved development comparisons.

The small exhaustive assignment below does not call the study matcher or any
selector. It verifies the already frozen one-point coordinate diagnostics, not
construction/window identity. Only gate-approved exact-date source projections
and saved predictions/comparisons are read. No prediction is rewritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
STUDY = "studies/29_verniman_level_reconstruction"
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
CONFIGS = ("P0-D1", "P0-D0", "B0-D0", "B0-D1", "B1-D0", "B1-D1")


def gap(a, b):
    a0, a1, b0, b1 = (Decimal(str(v)) for v in (*a, *b))
    return max(Decimal(0), a0-b1, b0-a1)


def exhaustive_assignment(sources, selected):
    """All small one-to-one assignments; cardinality, gap, then lexical IDs."""
    source = {s["source_id"]: s for s in sources}
    targets = {t["candidate_id"]: t for t in selected}
    if len(source) != len(sources) or len(targets) != len(selected):
        raise ValueError("unique original source and selected IDs required")
    edges = {(sid, cid): gap(s["interval"], t["interval"])
             for sid,s in source.items() for cid,t in targets.items()
             if gap(s["interval"], t["interval"]) <= Decimal(1)}
    identifiers = sorted(source)
    best_count, best_gap, optima = -1, None, []
    def visit(index, used, pairs, cost):
        nonlocal best_count, best_gap, optima
        if index == len(identifiers):
            candidate = tuple(sorted(pairs))
            if len(candidate) > best_count or len(candidate) == best_count and (best_gap is None or cost < best_gap):
                best_count, best_gap, optima = len(candidate), cost, [candidate]
            elif len(candidate) == best_count and cost == best_gap:
                optima.append(candidate)
            return
        sid = identifiers[index]
        visit(index+1, used, pairs, cost)
        for cid in sorted(targets):
            if cid not in used and (sid,cid) in edges:
                visit(index+1, used|{cid}, pairs+[(sid,cid)], cost+edges[(sid,cid)])
    visit(0,set(),[],Decimal(0))
    chosen = min(optima)
    source_orders = [s.get("order") for s in sources]
    target_orders = [t.get("rank") for t in selected]
    def valid_order(values):
        return bool(values) and all(type(v) is int and v > 0 for v in values) and len(set(values)) == len(values)
    order_known = valid_order(source_orders) and valid_order(target_orders)
    ranks = sorted((source[sid]["order"], targets[cid]["rank"]) for sid,cid in chosen) if order_known else []
    relative = all(a[1] < b[1] for a,b in zip(ranks,ranks[1:])) if len(ranks)>1 else None
    complete = (best_count == len(sources) == len(selected) and (best_count < 2 or relative)) if order_known else None
    return {"source_count":len(sources),"selected_count":len(selected),"matched_count":best_count,
        "total_interval_gap":str(best_gap),"chosen_pairs":[list(p) for p in chosen],
        "all_optimal_pairs":[list(p) for p in sorted({p for assignment in optima for p in assignment})],
        "optimal_assignment_count":len(optima),"relative_order_on_matched_subset":relative,
        "complete_coordinate_ladder":complete,"extras":len(selected)-best_count,
        "source_misses":len(sources)-best_count,
        "classification":"coordinate_only; no construction/window or source-method agreement inferred"}


def digest(path):return sha256(path.read_bytes()).hexdigest()
def pin(root,path):return {"path":str(path.relative_to(root)),"sha256":digest(path)}


def build(root,stage,gate_path):
    spec=importlib.util.spec_from_file_location("study29_phase5_independent_gate",root/STUDY/"phase5/select_sources.py")
    guard=importlib.util.module_from_spec(spec);sys.modules[spec.name]=guard;spec.loader.exec_module(guard)
    gate=guard.validate_gate(root,stage,gate_path)
    selection_path=stage/"source-selection-manifest-release13.json"
    selection=json.loads(selection_path.read_text())
    if selection["authorized_dates"]!=list(DATES) or selection["gate"]["gate"]!=gate["gate"] or selection["gate"]["status"]!="passed":
        raise ValueError("source projection must retain exact approved dates and gate identity")
    if guard.stamp(selection["selection_started_at"]) < guard.stamp(gate["recorded_at"]):
        raise ValueError("selected source intake predates the reveal gate")
    ledger_path=root/STUDY/"phase5/source-role-ledger.json"
    ledger=json.loads(ledger_path.read_text())
    batch_path=stage/"predictions-1/prediction-batch.json"
    batch=json.loads(batch_path.read_text())
    maps={r["session_date"]:r["map_artifact"] for r in batch["records"]}
    if set(maps)!=set(DATES):raise ValueError("all four saved map identities required")
    captures={r["session_date"]:r["prediction"] for r in gate["captures"]}
    if maps!=captures:raise ValueError("saved batch differs from pre-answer gate maps")
    records=[];source_pins=[];comparison_pins=[];checks=0;all_errors={p:[] for p in ("P0","B0","B1")}
    canonical_count=0
    for day in DATES:
        raw={}
        for table in ("outlooks","levels"):
            record=selection["tables"][table][day]
            path=stage/record["path"]
            if digest(path)!=record["sha256"]:raise ValueError("selected source bytes changed")
            values=json.loads(path.read_text())
            if any(str(r.get("session_date"))!=day for r in values):raise ValueError("source projection escaped exact date")
            raw[table]=values;source_pins.append(pin(root,path))
        mapped=[]
        for row in raw["levels"]:
            wanted="conditional_scenario_divider" if row["role"]=="trigger" else "ordered_"+row["side"]+"_destination"
            matches=[r for r in ledger["occurrences"] if r["source_class"]=="named_daily_plan" and
                r["session_date"]==day and r["provenance"]["source_revision_id"]==row["outlook_id"] and
                r["scenario_side"]==row["side"] and r["phase4_role"]==wanted and
                (row["role"]=="trigger" or r["source_target_order"]==row["ordinal"])]
            if len(matches)!=1:raise ValueError("canonical source occurrence not preserved uniquely")
            actual=matches[0]
            if (actual["exact_readable_source_text"]!=row["source_text"] or
                tuple(Decimal(actual[k]) for k in ("price_low","price_high"))!=tuple(Decimal(row[k]) for k in ("price_low","price_high")) or
                actual["available_at"]!=row["available_at"] or actual["directional_conditions"]!=row["conditions"]):
                raise ValueError("canonical literal price/label/availability/condition changed")
            if actual["source_window_identity_supplied"] is not None or actual["reference_period"]!="unresolved_exact_source_window":
                raise ValueError("unsupported source window must remain unresolved")
            mapped.append((row,actual));canonical_count+=1
        local=guard.pinned(root,maps[day]);prediction=json.loads(local.read_text())
        comparison_path=stage/"saved-analysis-1"/(day+".json")
        comparison=json.loads(comparison_path.read_text());comparison_pins.append(pin(root,comparison_path))
        if any(comparison["map"].get(k)!=v for k,v in maps[day].items()) or comparison["map"]["session_date"]!=day:
            raise ValueError("saved comparison map identity differs")
        if comparison["source_ledger"]!=pin(root,ledger_path):
            raise ValueError("saved comparison source ledger identity differs")
        if comparison["selection_recomputed"] is not False or comparison["candidate_inputs_modified"] is not False:
            raise ValueError("comparison must not rerun selection or alter candidates")
        sessions=[]
        for outlook in raw["outlooks"]:
            revision=outlook["source_revision_id"]
            rows=[(r,a) for r,a in mapped if r["outlook_id"]==revision]
            triggers=[r for r,a in rows if r["role"]=="trigger"]
            intervals={tuple(Decimal(r[k]) for k in ("price_low","price_high")) for r in triggers}
            common=len(intervals)==1 and {r["side"] for r in triggers}=={"bullish","bearish"}
            cutoff=guard.stamp(day+"T09:25:00-04:00")
            updated=outlook.get("source_claimed_updated_at") or outlook.get("source_claimed_updated")
            after=guard.stamp(updated)>cutoff if updated else None
            session={"source_revision_id":revision,"title":outlook.get("title"),"common_divider":common,
                "source_divider_interval":[str(v) for v in next(iter(intervals))] if common else None,
                "source_claimed_updated":updated,"claimed_update_after_cutoff":after,
                "historical_available_at":outlook.get("available_at"),"historical_preopen_content_established":False,
                "literal_branches":{},"policies":{}}
            for side in ("bullish","bearish"):
                session["literal_branches"][side]=[{"source_label":r["source_label"],"interval":[r["price_low"],r["price_high"]],"order":r["ordinal"]} for r,a in sorted(rows,key=lambda pair:pair[0]["ordinal"]) if r["side"]==side and r["role"]=="target"]
            for config in CONFIGS:
                selected=prediction["selections"][config];pivot=selected["pivot"]
                item={"pivot_signed_boundary_error":None,"pivot_interval_gap":None,"branches":{}}
                if common and pivot.get("candidate"):
                    low,high=next(iter(intervals));candidate=pivot["candidate"]
                    error=Decimal(str(candidate["price"]))-low if low==high else None
                    item["pivot_signed_boundary_error"]=str(error) if error is not None else None
                    item["pivot_interval_gap"]=str(gap((low,high),candidate["interval"]))
                    existing=comparison["analysis"][config]["pivot"]["coordinate_only_diagnostic"]
                    if Decimal(existing["pivot_signed_point_or_boundary_error"])!=error:raise ValueError("saved pivot diagnostic differs")
                    if Decimal(existing["pivot_interval_gap_points"])!=Decimal(item["pivot_interval_gap"]):raise ValueError("saved pivot interval-gap diagnostic differs")
                    if config.endswith("-D1") and error is not None:all_errors[config.split("-")[0]].append(abs(error))
                    checks+=2
                if comparison["analysis"][config]["pivot"]["strict_decomposition"]["status"]!="not_estimable":
                    raise ValueError("unknown source pivot identity cannot become primary accuracy")
                for side in ("bullish","bearish"):
                    sources=[{"source_id":a["level_id"],"interval":[r["price_low"],r["price_high"]],"order":r["ordinal"]} for r,a in rows if r["side"]==side and r["role"]=="target"]
                    targets=[{"candidate_id":t["candidate"]["candidate_id"],"interval":t["candidate"]["interval"],"rank":t["rank"]} for t in selected[side]["targets"]]
                    actual=exhaustive_assignment(sources,targets)
                    saved=comparison["analysis"][config][side]["coordinate_only_diagnostic"]
                    for key in ("source_count","selected_count","matched_count","complete_coordinate_ladder","relative_order_on_matched_subset"):
                        if actual[key]!=saved[key]:raise ValueError("saved coordinate diagnostic differs: "+key)
                        checks+=1
                    if Decimal(actual["total_interval_gap"])!=Decimal(saved["total_interval_gap"]):raise ValueError("saved coordinate total gap differs")
                    chosen=sorted([[r["source_id"],r["candidate_id"]] for r in saved["assignments"]])
                    if actual["chosen_pairs"]!=chosen:raise ValueError("saved maximum-cardinality/minimum-gap/lexical assignment differs")
                    checks+=2
                    if comparison["analysis"][config][side]["strict_decomposition"]["status"]!="not_estimable":raise ValueError("unknown exact source identity cannot become primary accuracy")
                    item["branches"][side]=actual
                session["policies"][config]=item
            sessions.append(session)
        records.append({"session_date":day,"plan_revision_count":len(raw["outlooks"]),"map":maps[day],"comparisons":pin(root,comparison_path),"source_strata":sessions})
    means={p:{"comparable_dates":len(v),"mean_absolute_boundary_error":str(sum(v)/len(v)) if v else None,"point_within_one":sum(x<=1 for x in v)} for p,v in all_errors.items()}
    return {"schema":"abacus.study29.phase5.independent-comparison-audit/v1","recorded_at":datetime.now(timezone.utc).isoformat(),
        "status":"passed","implementation":"independent exhaustive one-to-one assignment; no study matcher or selector called",
        "matching_contract":"one point interval gap; maximum cardinality, minimum total gap, then original lexical IDs",
        "gate":gate["gate"],"source_selection":pin(root,selection_path),"source_ledger":pin(root,ledger_path),
        "selected_source_pins":source_pins,"comparison_pins":comparison_pins,"canonical_role_occurrences_checked":canonical_count,
        "saved_metric_checks":checks,"pivot_descriptive_summary":means,"records":records,
        "primary_source_window_outcome":"not estimable; no exact supported windows supplied",
        "primary_accuracy_inferred_from_coordinates":False,"predictions_modified":False,
        "source_method_reconstruction_claimed":False,"audit_code":pin(root,Path(__file__).resolve())}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=ROOT);p.add_argument("--stage",type=Path,required=True);p.add_argument("--gate",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    root=a.root.resolve()
    def absolute(x):return x.resolve() if x.is_absolute() else (root/x).resolve()
    stage,gate_path,output=map(absolute,(a.stage,a.gate,a.output))
    if output.exists() or output.parent!=stage:raise ValueError("fresh explicit-stage audit receipt required")
    result=build(root,stage,gate_path)
    with output.open("x") as f:json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps({"status":result["status"],"metric_checks":result["saved_metric_checks"],"source_roles":result["canonical_role_occurrences_checked"],"pivot_summary":result["pivot_descriptive_summary"]},indent=2))


if __name__=="__main__":main()
