"""Independent saved Stage 3 reconciliation, including phase release checks.

Only data-reading/byte utilities are shared. Numerical producers, candidate
selection, outcome scorers and reporting modules are never imported here.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .stage3_reference import (NY, METRICS, FLAGS, HORIZONS, FIXED, require, finite,
    boundary, gate_id, gate_grid, strata, iter_reference_stream, reference_outcomes,
    reference_masks, segments, linear_quantile, week_roster, reference_uncertainty,
    candidate_assessment, independent_selection)

STATE_FIELDS = ("direction", "side", "signal_idx", "min_width", "width", "width_ratio", "width_pass", "episode_id",
    "fast_touch", "slow_touch", "penetration", "full_departure", "armed_before", "armed_after",
    "technical_candidate", "setup_candidate", "accepted", "suppression_reason", "reset_reason", "event_id", "selected_ema",
    "gate_id", "gate_family", "gate_threshold")
IDENTITY_FIELDS = ("event_id", "product", "interval_minutes", "contract", "side", "direction", "signal_idx", "timestamp",
    "signal_timestamp", "available_at", "entry_at", "reference_price", "entry_atr", "ema20", "ema50", "width", "episode_id",
    "session", "week", "year", "month", "calendar_date", "hour", "time_stratum", "touch_mode", "gate_id", "gate_family", "gate_threshold")
PATH_FIELDS = ("horizon", "horizon_minutes", "status", "censor_reason", "terminal_at", "elapsed_minutes", "crosses_closure", "same_session",
    "period_id", "fold_id", "start_embargo", "endpoint_purge", "score_eligible", "mask_reason", "atr_support", "terminal_signal_idx") + METRICS + tuple(m + "_atr" for m in METRICS) + FLAGS + tuple(m + "_attainment_" + edge for m in ("mfe", "mae") for edge in ("start", "end"))
CELL = ("product", "interval_minutes", "touch_mode")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha256(path))


def portable_pins(stage,pins):
    stage=Path(stage).resolve()
    result={}
    for pin in pins:
        path=Path(pin["path"])
        full=path.resolve() if path.is_absolute() else (stage/path).resolve()
        target=full.relative_to(stage).as_posix() if full.is_relative_to(stage) else str(full)
        value=pin|dict(path=target)
        if target in result:require(result[target]==value,"conflicting byte pin")
        result[target]=value
    values=list(result.values())
    return dict(consumed=values,records=[p for p in values if not Path(p["path"]).is_absolute()],external_records=[p for p in values if Path(p["path"]).is_absolute()])


def resolve_pin(stage,pin):return Path(pin["path"]) if Path(pin["path"]).is_absolute() else stage/pin["path"]


def recovery_dependency_pins(stage, config):
    """Check the complete recovery dependency graph before scientific reads.

    The recovery driver is execution provenance, not an alternate scientific
    reference. Its receipts and generic byte dependencies remain part of the
    development receipt and its later portable completion rechecks.
    """
    recovery = config.get("development_recovery")
    if not recovery:
        return []
    require(isinstance(recovery, dict), "frozen recovery configuration required")
    adopted_count = recovery["expected_adopted_gateways"]
    missing = recovery["expected_missing_gateways"]
    require(type(adopted_count) is int and isinstance(missing, list), "frozen recovery count inventory")
    stage = Path(stage).resolve()
    pins = {}

    def retain(pin, full):
        value = dict(path=str(full), bytes=pin["bytes"], sha256=pin["sha256"])
        require(type(value["bytes"]) is int and value["bytes"] >= 0,
                "recovery dependency byte count")
        digest = value["sha256"]
        require(isinstance(digest, str) and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest),
                "recovery dependency SHA256")
        if value["path"] in pins:
            require(pins[value["path"]] == value, "conflicting recovery dependency pin")
        pins[value["path"]] = value

    for name in ("adopted-recovery-packets.json", "development-recovery-freeze.json",
                 "development-recovery-completion.json"):
        path = stage / "provenance" / name
        require(path.is_file(), "required recovery dependency receipt absent: " + name)
        retain(record(path), path)
        receipt = json.loads(path.read_text())
        require(receipt.get("status") == "passed", "passing recovery dependency required: " + name)
        require(receipt.get("phase", "development") == "development",
                "recovery dependency phase differs: " + name)
        if name == "development-recovery-completion.json":
            require(receipt.get("phase") == "development", "explicit recovery completion phase required")
            for key, expected in (("gateway_count", adopted_count + len(missing)),
                                  ("adopted_count", adopted_count), ("missing_count", len(missing))):
                require(type(receipt.get(key)) is int and receipt[key] == expected,
                        "exact recovery completion " + key)
        for field in ("records", "external_records"):
            declared = receipt.get(field)
            require(isinstance(declared, list), "generic recovery dependency inventory required: " + name)
            for pin in declared:
                target = Path(pin["path"])
                if field == "records":
                    require(not target.is_absolute(), "recovery local dependency must be stage-relative")
                    full = (stage / target).resolve()
                    require(full.is_relative_to(stage), "recovery local dependency escapes stage")
                else:
                    require(target.is_absolute(), "recovery external dependency must be absolute")
                    full = target.resolve()
                retain(pin, full)
    for pin in pins.values():
        full = Path(pin["path"])
        require(full.is_file() and full.stat().st_size == pin["bytes"] and sha256(full) == pin["sha256"],
                "recovery dependency bytes changed before independent verification")
    return list(pins.values())


def equal(actual, expected, context):
    """Strict, lazy saved-ledger scalar comparison. No success-path repr work."""
    missing_actual, missing_expected = actual is None or bool(pd.isna(actual)), expected is None or bool(pd.isna(expected))
    if missing_actual or missing_expected:
        if missing_actual and missing_expected:
            return
    elif isinstance(expected, (bool, np.bool_)):
        if isinstance(actual, (bool, np.bool_)) and bool(actual) == bool(expected):
            return
    elif isinstance(expected, (int, np.integer)):
        if not isinstance(actual, (bool, np.bool_)) and finite(actual) and actual == int(expected):
            return
    elif isinstance(expected, (float, np.floating)):
        if not isinstance(actual, (bool, np.bool_)) and finite(actual) and math.isclose(float(actual), float(expected), rel_tol=2e-10, abs_tol=2e-10):
            return
    elif actual == expected:
        return
    raise ValueError(f"{context}: {actual!r} != {expected!r}")


def cell(raw, expected, context):
    if raw == "" and isinstance(expected,str):
        equal(raw,expected,context)
    elif raw == "":
        equal(None, expected, context)
    elif expected is None or pd.isna(expected):
        raise ValueError(context + ": undefined cell must be blank")
    elif isinstance(expected, (bool, np.bool_)):
        require(raw in ("True", "False", "true", "false"), context + ": malformed boolean")
        equal(raw in ("True", "true"), expected, context)
    elif isinstance(expected, str):
        equal(raw, expected, context)
    elif isinstance(expected, (int, np.integer)):
        from decimal import Decimal
        require(Decimal(raw)==Decimal(int(expected)), context + ": integer/discrete value must be exact")
    else:
        require(finite(float(raw)), context + ": nonfinite numeric string")
        equal(float(raw), expected, context)


def compare_frames(actual, expected, keys, fields=None, context="ledger"):
    require(not actual.duplicated(keys).any() and not expected.duplicated(keys).any(), context + ": duplicate scientific key")
    require(len(actual) == len(expected), context + ": population size")
    if keys==["signal_idx"]:
        require(actual.signal_idx.is_monotonic_increasing,"canonical technical ordinal order")
        actual=actual.reset_index(drop=True);expected=expected.reset_index(drop=True)
    else:
        actual = actual.sort_values(keys, kind="stable").reset_index(drop=True)
        expected = expected.sort_values(keys, kind="stable").reset_index(drop=True)
    fields = list(expected.columns) if fields is None else list(fields)
    require(all(k in actual and k in expected for k in list(keys) + fields), context + ": required fields")
    count = 0
    for key in dict.fromkeys(list(keys) + fields):
        a, e = actual[key], expected[key]
        am, em = a.isna().to_numpy(), e.isna().to_numpy()
        okay = am & em
        valid = ~am & ~em
        if pd.api.types.is_numeric_dtype(e.dtype) and not pd.api.types.is_bool_dtype(e.dtype):
            try:
                okay[valid] = (a[valid].to_numpy() == e[valid].to_numpy()) if pd.api.types.is_integer_dtype(e.dtype) else np.isclose(a[valid].to_numpy(float), e[valid].to_numpy(float), rtol=2e-10, atol=2e-10)
                if pd.api.types.is_bool_dtype(a.dtype):okay[valid]=False
                elif a.dtype==object:okay[valid]&=np.array([not isinstance(v,(bool,np.bool_)) for v in a[valid]],dtype=bool)
            except (ValueError, TypeError):
                pass
        else:
            okay[valid] = a[valid].to_numpy() == e[valid].to_numpy()
            if pd.api.types.is_bool_dtype(e.dtype) or (valid.any() and isinstance(e[valid].iloc[0], (bool, np.bool_))):
                if not pd.api.types.is_bool_dtype(a.dtype):
                    okay[valid] &= np.array([isinstance(v, (bool, np.bool_)) for v in a[valid]], dtype=bool)
        if not okay.all():
            i = int(np.flatnonzero(~okay)[0])
            equal(a.iloc[i], e.iloc[i], context + "/" + key + "/row" + str(i + 1))
            raise ValueError(context + "/" + key + ": vector comparison mismatch")
        count += len(a)
    return count


def reference_decisions(bars):
    """One independent scalar branch replay; all gate arm states are identical.

    This follows from consuming every selected penetration even on rejection.
    Every gate's own acceptance/width/ATR/reason/identity is reconstructed below.
    Compact state arrays avoid retaining copies of the full price roster.
    """
    product=str(bars['product'].iloc[0]);threshold=FIXED[product]
    gate = dict(gate_id=gate_id("absolute",threshold), family="absolute", threshold=threshold)
    columns=[k for k in STATE_FIELDS if k not in ("gate_id","gate_family","gate_threshold")]+["_atr14","_candidate_id"]
    state, events = {b:{k:[] for k in columns} for b in ("fast", "slow")}, {b: [] for b in ("fast", "slow")}
    for row, event in iter_reference_stream(bars, [gate]):
        branch = row["touch_mode"]
        candidate_id=(f"{product}|{int(row['interval_minutes'])}m|{row['contract']}|{pd.Timestamp(row['timestamp']).isoformat()}|{row['side']}|{branch}" if row['setup_candidate'] else None)
        for k in columns:state[branch][k].append(row.get("atr14") if k=="_atr14" else candidate_id if k=="_candidate_id" else row[k])
        if row['setup_candidate']:
            # Signal-time metadata templates are constructed for technical
            # setups, never labeled as an unapproved later gateway acceptance.
            atr=row.get('atr14')
            template=row|strata(row)|dict(event_id=candidate_id,reference_price=row['close'],entry_at=row['available_at'],
                signal_timestamp=row['timestamp'],entry_atr=float(atr) if finite(atr) and float(atr)>0 else None)
            events[branch].append({k:template[k] for k in IDENTITY_FIELDS if k in template})
    states={b:pd.DataFrame(rows) for b,rows in state.items()}
    for frame in states.values():
        for k in ("side","suppression_reason","reset_reason","selected_ema"):frame[k]=frame[k].astype("category")
    return states, {b: pd.DataFrame(rows, columns=IDENTITY_FIELDS) for b, rows in events.items()}


def expected_gate(states, causal, gate):
    expected = states.copy()
    expected["suppression_reason"]=expected.suppression_reason.astype(object)
    family, threshold = gate["family"], float(gate["threshold"])
    values = pd.to_numeric(expected.width if family == "absolute" else expected.width_ratio, errors="coerce").to_numpy(float)
    passes = np.isfinite(values) & (values + 1e-10 * max(1., abs(threshold)) >= threshold)
    expected["gate_id"], expected["gate_family"], expected["gate_threshold"] = gate["gate_id"], family, threshold
    # Ratio and width have already been independently computed on the touch bar.
    atr = pd.to_numeric(expected["_atr14"], errors="coerce").to_numpy(float)
    atr[~(np.isfinite(atr) & (atr > 0))] = np.nan
    expected["min_width"] = threshold if family == "absolute" else threshold * atr
    expected["width_pass"] = passes
    expected["accepted"] = expected.setup_candidate.to_numpy(bool) & passes
    rejection = expected.setup_candidate.to_numpy(bool) & ~passes
    expected.loc[rejection, "suppression_reason"] = "width_below_minimum"
    if family == "atr":
        expected.loc[rejection & ~np.isfinite(values), "suppression_reason"] = "atr_invalid"
    expected["event_id"]=expected["_candidate_id"].where(expected.accepted,None)
    keep = set(expected.loc[expected.accepted, "signal_idx"])
    events = causal.loc[causal.signal_idx.isin(keep)].copy()
    events["gate_id"], events["gate_family"], events["gate_threshold"] = gate["gate_id"], family, threshold
    return expected, events


def reconcile_stream(bars, technical, events, gate, branch, prepared=None):
    states, causal = reference_decisions(bars) if prepared is None else prepared
    expected, accepted = expected_gate(states[branch], causal[branch], gate)
    require(len(technical) == len(bars), "complete causal technical roster required")
    # Technical field signal_idx is the original uninterrupted 2017+ ordinal.
    fields = compare_frames(technical, expected, ["signal_idx"], STATE_FIELDS, "gateway state")
    fields += compare_frames(events, accepted, ["gate_id", "event_id"], IDENTITY_FIELDS, "gateway accepted identities")
    return dict(check="independent_full_gateway_state", status="passed", rows=len(technical), events=len(events), fields=fields), accepted


def reconcile_mapping(bars,native_five):
    """Independently index the latest scheduled completion, including bad slots."""
    interval=int(bars.interval_minutes.iloc[0])
    reference=bars.timestamp if interval==3 else bars.available_at
    positions=np.searchsorted(pd.to_datetime(native_five.available_at,utc=True).array.asi8,pd.to_datetime(reference,utc=True).array.asi8,side="right")-1
    present=positions>=0
    chosen=native_five.iloc[np.maximum(positions,0)].reset_index(drop=True)
    same=chosen.contract.to_numpy()==bars.contract.to_numpy()
    current=(pd.to_datetime(chosen.timestamp,utc=True).array.asi8==pd.to_datetime(bars.timestamp,utc=True).array.asi8) if interval==5 else np.ones(len(bars),dtype=bool)
    valid=present&same&current&chosen.usable.fillna(False).to_numpy(bool)&chosen.feature_valid.fillna(False).to_numpy(bool)
    expected=pd.DataFrame(dict(signal_idx=np.arange(len(bars)),feature_valid=valid,
        map_reason=np.where(~present,"no_completed_source",np.where(~current,"missing_current_source",np.where(~same,"contract_mismatch",np.where(~(chosen.usable.fillna(False).to_numpy(bool)&chosen.feature_valid.fillna(False).to_numpy(bool)),"invalid_latest_source","valid"))))))
    for target,source in (("feature_source_timestamp","timestamp"),("feature_available_at","available_at"),("feature_contract","contract"),("consecutive_count","consecutive_count")):
        expected[target]=chosen[source].where(present)
    expected["feature_reset"]=chosen.feature_reset.fillna(False).to_numpy(bool)&present
    expected["source_age_minutes"]=(pd.to_datetime(reference,utc=True).reset_index(drop=True)-pd.to_datetime(chosen.available_at,utc=True)).dt.total_seconds()/60
    expected.loc[~present,"source_age_minutes"]=np.nan
    for metric in ("ema20","ema50","atr14"):expected[metric]=chosen[metric].where(valid)
    actual=bars.copy();actual["signal_idx"]=np.arange(len(bars))
    count=compare_frames(actual,expected,["signal_idx"],context="latest scheduled source mapping")
    return dict(check="independent_latest_scheduled_cloud_atr_mapping",status="passed",rows=len(bars),fields=count)


def summary(group, unit="atr", support="full_absolute"):
    scored = group.loc[group.score_eligible.astype(bool)]
    if support == "common_atr_valid":
        scored = scored.loc[scored.atr_support.astype(bool)]
    complete = scored.loc[scored.status.eq("completed")]
    cols = list(METRICS) if unit == "points" else [m + "_atr" for m in METRICS]
    good = complete.loc[complete[cols].notna().all(axis=1)].copy()
    for m, col in zip(METRICS, cols):
        good[m] = good[col].astype(float)
    n, accepted = len(good), len(scored)
    r = dict(accepted=accepted, scoring_accepted=accepted, accepted_total=len(group), completed=len(complete), censored=int(scored.status.eq("censored").sum()),
        evaluable=n, normalization_missing=len(complete)-n, contributing_sessions=good.session.nunique(), contributing_weeks=good.week.nunique(),
        sparse_warning=n < 100 or good.session.nunique() < 30, start_embargo=int(group.start_embargo.sum()), endpoint_purge=int(group.endpoint_purge.sum()),
        atr_support_missing=int((group.score_eligible.astype(bool) & ~group.atr_support.astype(bool)).sum()))
    for m in METRICS:
        values = good[m].tolist()
        r.update({"mean_"+m: float(np.mean(values)) if values else None, "median_"+m: linear_quantile(values, .5),
                  "session_mean_"+m: float(good.groupby("session")[m].mean().mean()) if n else None})
        r.update({f"{m}_p{int(p*100):02d}": linear_quantile(values, p) for p in (.1, .25, .5, .75, .9, .95)})
    for flag in FLAGS:
        vals = good[flag].astype(float)
        r[flag+"_count"], r[flag+"_share"] = int(vals.sum()), float(vals.mean()) if n else None
        r["session_"+flag+"_share"] = float(vals.groupby(good.session).mean().mean()) if n else None
    favorable = int(complete.favorable.eq(True).sum())
    r.update(missing_worst_favorable_share=favorable/accepted if accepted else None,
        missing_best_favorable_share=(favorable+accepted-len(complete))/accepted if accepted else None,
        mean_elapsed_minutes=float(good.elapsed_minutes.mean()) if n else None,
        closure_crossing_completed=int(complete.crosses_closure.eq(True).sum()), same_session_completed=int(complete.same_session.eq(True).sum()))
    return r


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _cohort(frame, row):
    result = frame.loc[frame.horizon.eq(int(row["horizon"]))]
    if row.get("direction", "All") != "All":
        result = result.loc[result.side.eq(row["direction"])]
    support = row.get("support", "common_atr_valid")
    if support == "common_atr_valid":
        result = result.loc[result.atr_support.astype(bool)]
    elif support == "same_session":
        result = result.loc[result.same_session.eq(True)]
    elif support == "uninterrupted":
        result = result.loc[result.crosses_closure.eq(False)]
    elif support not in ("all", "full_absolute"):
        raise ValueError("unknown summary support: " + support)
    return result


def reconcile_summary_rows(outcomes, rows, *, baseline=None, context="summary"):
    fields = 0
    for row in rows:
        cohort = outcomes.loc[outcomes.horizon.eq(int(row["horizon"]))]
        if row.get("direction","All") != "All":cohort=cohort.loc[cohort.side.eq(row["direction"])]
        expected = summary(cohort, row["unit"],row.get("support","common_atr_valid"))
        require(set(expected).issubset(row),"complete required scientific summary columns")
        if baseline is not None:
            b = summary(_cohort(baseline, row), row["unit"])
            for m in METRICS:
                expected["baseline_mean_" + m] = b["mean_" + m]
                expected["difference_mean_"+m] = expected["mean_" + m] - b["mean_" + m] if finite(expected["mean_" + m]) and finite(b["mean_" + m]) else None
            expected["baseline_evaluable"]=b["evaluable"]
            expected["retention"] = expected["evaluable"] / b["evaluable"] if b["evaluable"] else None
        for key, value in expected.items():
            require(key in row,"complete summary/grid estimand columns")
            cell(row[key], value, context + "/" + row.get("row_id", "") + "/" + key)
            fields += 1
    return fields


def reconcile_selection(cell_outcomes, gates, config, actual_folds, actual_assessments, actual_choices, phase="development", nominee=None):
    """Recompute folds, every eligibility guard and deterministic final choice."""
    fixed = gate_id("absolute", config["minimum_width_points"][actual_choices[0]["product"]])
    expected = independent_selection(cell_outcomes, cell_outcomes[fixed], gates, config) if phase == "development" else None
    assessment_rows = expected["assessments"] if expected else [dict(**g, **candidate_assessment(cell_outcomes[g["gate_id"]], cell_outcomes[fixed], config, phase)) for g in gates]
    fields = 0
    guard_names = {"pooled_completed":"completed", "pooled_sessions":"sessions", "pooled_weeks":"weeks", "overall_improvement":"improvement"}
    for reference in assessment_rows:
        match = [r for r in actual_assessments if r["gate_id"] == reference["gate_id"]]
        require(len(match) == 1, "complete unique gateway assessment inventory")
        row = match[0]
        baseline_reference=candidate_assessment(cell_outcomes[fixed],cell_outcomes[fixed],config,phase)
        compare = dict(selection_score=reference["score"], baseline_equal_fold_score=reference["baseline_equal_fold_score"], overall_improvement=reference["improvement"], positive_folds=reference["positive_folds"], retention=reference["retention"],
            completed=reference["completed"], contributing_sessions=reference["sessions"], contributing_weeks=reference["weeks"],
            mean_terminal_delta_atr=reference["mean_terminal_delta_atr"], mean_mfe_atr=reference["mean_mfe_atr"], mean_mae_atr=reference["mean_mae_atr"], eligible=reference["eligible"],
            baseline_mean_terminal_delta_atr=baseline_reference["mean_terminal_delta_atr"],baseline_mean_mfe_atr=baseline_reference["mean_mfe_atr"],baseline_mean_mae_atr=baseline_reference["mean_mae_atr"],
            fold_count=len(reference["folds"]),fixed_gate_id=fixed,phase=phase,gate_family=reference["family"],gate_threshold=reference["threshold"])
        defined = all(finite(reference[k]) for k in ("score", "improvement", "retention", "mean_mae_atr", "mean_mfe_atr")) and all(finite(f["improvement"]) for f in reference["folds"])
        compare.update({"guard_"+guard_names.get(k,k): value for k, value in reference["guards"].items()})
        compare["guard_defined"] = defined
        compare.update({"improvement_"+f["fold_id"]: f["improvement"] for f in reference["folds"]})
        failed = [k for k in ("completed","sessions","weeks","fold_completed","fold_sessions","retention","mae","mfe","positive_folds","improvement","defined") if not compare["guard_"+k]]
        compare["failed_guards"] = ";".join(failed)
        for k,v in compare.items():
            require(k in row, "assessment required field: " + k)
            cell(row[k],v,"selection/"+reference["gate_id"]+"/"+k);fields+=1
        for fold_id in [f["fold_id"] for f in reference["folds"]]+["pooled"]:
            matches=[r for r in actual_folds if r["gate_id"]==reference["gate_id"] and r["fold_id"]==fold_id]
            require(len(matches)==1,"complete unique fold inventory")
            source=cell_outcomes[reference["gate_id"]]
            source=source.loc[source.fold_id.isin([f["fold_id"] for f in reference["folds"]])] if fold_id=="pooled" else source.loc[source.fold_id.eq(fold_id)]
            pooled=summary(source.loc[source.horizon.eq(15)],"atr","common_atr_valid")
            compare_fold={k:pooled[k] for k in ("completed","censored","contributing_sessions","contributing_weeks","scoring_accepted")}
            compare_fold.update(accepted=pooled["accepted_total"],mean_terminal_delta_atr=pooled["mean_terminal_delta"],mean_mfe_atr=pooled["mean_mfe"],mean_mae_atr=pooled["mean_mae"])
            for name,v in compare_fold.items():
                require(name in matches[0],"fold support required columns")
                cell(matches[0][name],v,"fold/"+name);fields+=1
    require(len(actual_assessments)==len(assessment_rows),"extra gateway assessment")
    require(len(actual_choices)==1,"one frozen choice per cell required")
    choice=actual_choices[0]
    if phase=="development":
        selected=expected["nominee"] or fixed
        chosen=next((r for r in assessment_rows if r["gate_id"]==expected["nominee"]),None)
        eligible=[r for r in assessment_rows if r["eligible"]];maximum=max((r["score"] for r in eligible),default=None)
        tied=[r for r in eligible if maximum-r["score"]<=float(config["selection_tie_epsilon_scale"])*max(1.,abs(maximum),abs(r["score"]))]
        for k,v in dict(nominee_gate_id=selected,selected_gate_id=selected,fixed_gate_id=fixed,
            eligible_candidates=sum(r["eligible"] for r in assessment_rows),fallback=expected["nominee"] is None,
            nomination_status="eligible_nominee" if expected["nominee"] else "no_eligible_improvement",
            highest_eligible_score=maximum,tied_to_highest_count=len(tied),selection_score=chosen["score"] if chosen else None,
            selection_improvement=chosen["improvement"] if chosen else None,selected_gate_family=chosen["family"] if chosen else "absolute",
            selected_gate_threshold=chosen["threshold"] if chosen else config["minimum_width_points"][choice["product"]]).items():
            cell(choice[k],v,"nominee/"+k);fields+=1
    else:
        chosen=next(r for r in assessment_rows if r["gate_id"]==nominee)
        passes=bool(chosen["eligible"]) and nominee != fixed
        for k,v in dict(selected_gate_id=nominee if passes else fixed,validation_passed=passes,fallback=not passes,
            validation_status="passed" if passes else "fixed_fallback_no_eligible_nominee" if nominee==fixed else "fixed_fallback_validation_failed",
            final_gate_id=nominee if passes else fixed,validation_improvement=chosen["improvement"],
            failed_validation_guards=next(r["failed_guards"] for r in actual_assessments if r["gate_id"]==nominee),
            selected_gate_family=chosen["family"] if passes else "absolute",selected_gate_threshold=chosen["threshold"] if passes else config["minimum_width_points"][choice["product"]]).items():
            cell(choice[k],v,"validation/"+k);fields+=1
    return dict(check="independent_selection_and_guards",status="passed",phase=phase,fields=fields), assessment_rows


def inventory(rows, keys, expected_keys, label):
    found = [tuple(row[k] for k in keys) for row in rows]
    require(len(found)==len(set(found)), label+": duplicate scientific key")
    require(set(found)==set(expected_keys), label+": incomplete scientific inventory")
    require(len({r.get("row_id") for r in rows})==len(rows) if rows and "row_id" in rows[0] else True,label+": duplicate row identity")


def reconcile_contrasts(rows, populations, config, phase):
    """Every saved interval is derived using direct sampled-week index gathers."""
    period=config["periods"][phase]
    roster=week_roster(period["start"],period["end"])
    cache={};fields=0
    for row in rows:
        key=tuple(row[k] for k in CELL)
        selected,fixed=populations[key]
        cohort_selected,cohort_fixed=_cohort(selected,row),_cohort(fixed,row)
        metric=row["metric"]
        if metric in METRICS and row.get("unit")=="atr":metric += "_atr"
        block=int(row.get("block_weeks","0"))
        weighting=row.get("weighting","event")
        def good(frame):return frame.loc[frame.status.eq("completed")&frame[metric].map(finite)]
        sg,fg=good(cohort_selected),good(cohort_fixed)
        def average(frame):return float(frame.groupby("session")[metric].mean().mean()) if weighting=="session" and len(frame) else float(frame[metric].mean()) if len(frame) else None
        sm,fm=average(sg),average(fg)
        support_checks=dict(selected_estimate=sm,fixed_estimate=fm,selected_evaluable=len(sg),fixed_evaluable=len(fg),selected_sessions=sg.session.nunique(),fixed_sessions=fg.session.nunique(),
            selected_weeks=sg.week.nunique(),fixed_weeks=fg.week.nunique(),identity_fallback=row["selected_gate_id"]==row["fixed_gate_id"],
            sparse_warning=len(sg)<100 or len(fg)<100 or sg.session.nunique()<30 or fg.session.nunique()<30)
        ck=key+(int(row["horizon"]),row.get("direction","All"),row.get("support","common_atr_valid"),metric,weighting,block)
        if block:
            if ck not in cache:
                cache[ck]=reference_uncertainty(cohort_selected,cohort_fixed,metric,roster,block,weighting,
                    int(config["bootstrap"]["resamples"]),int(config["bootstrap"]["seed"]),12)
            expected=cache[ck]
            adjusted=row.get("interval_kind",row.get("ci_label",row.get("interval_type"))) in ("bonferroni","bonferroni12","familywise95")
            check=dict(estimate=expected["estimate"],ci_low=expected["adjusted_low" if adjusted else "ci_low"],
                ci_high=expected["adjusted_high" if adjusted else "ci_high"],defined_draws=expected["defined_draws"],undefined_draws=expected["undefined_draws"])
            lo,hi=(.05/24,1-.05/24) if adjusted else (.025,.975)
            check.update(quantile_low=lo,quantile_high=hi,ci_level=hi-lo,resamples=int(config["bootstrap"]["resamples"]),seed=int(config["bootstrap"]["seed"]),
                week_count=len(roster),first_week=roster[0],last_week=roster[-1],primary=phase=="final" and weighting=="event" and block==4)
        else:
            def mean(frame):
                f=frame.loc[frame.status.eq("completed") & frame[metric].map(finite)]
                return float(f.groupby("session")[metric].mean().mean()) if weighting=="session" and len(f) else float(f[metric].mean()) if len(f) else None
            sm,fm=mean(cohort_selected),mean(cohort_fixed)
            check=dict(selected_estimate=sm,fixed_estimate=fm,estimate=sm-fm if finite(sm) and finite(fm) else None,ci_low=None,ci_high=None,ci_level=None,defined_draws=0,undefined_draws=0)
        check.update(support_checks)
        for name,value in check.items():
            require(name in row,"complete contrast/support/interval scientific fields")
            if name in ("quantile_low","quantile_high","ci_level") and value is not None:
                require(row[name]!="" and float(row[name])==value,"exact frozen interval constant: "+name)
            else:cell(row[name],value,"contrast/"+row.get("row_id","")+"/"+name)
            fields+=1
    return dict(check="independent_paired_period_week_uncertainty",status="passed",phase=phase,rows=len(rows),fields=fields,week_roster=roster,interval_families=len(cache))


def table_slice(path, product, interval, branch=None, gid=None):
    """Retain only one cell/gateway's original strings from a large CSV."""
    with Path(path).open(newline="",encoding="utf-8") as stream:
        reader=csv.DictReader(stream)
        return [r for r in reader if r.get("product")==product and r.get("interval_minutes")==str(interval)
            and (branch is None or r.get("touch_mode")==branch) and (gid is None or r.get("gate_id")==gid)]


def reconcile_quantiles(outcomes,rows):
    probabilities=sorted(set([i/10 for i in range(11)]+[.25,.75,.95]))
    expected={(str(h),s,u,m,str(p*100)) for h,s,u,m,p in itertools.product(HORIZONS,("All","Buy","Sell"),("points","atr"),METRICS,probabilities)}
    found={(r["horizon"],r["direction"],r["unit"],r["metric"],str(float(r["percentile"]))) for r in rows}
    require(found==expected and len(rows)==len(expected),"complete unique quantile grid")
    cache={};fields=0
    for r in rows:
        key=(int(r["horizon"]),r["direction"],r["unit"],r["metric"])
        if key not in cache:
            part=_cohort(outcomes,r);part=part.loc[part.score_eligible.astype(bool)&part.status.eq("completed")]
            col=r["metric"]+("_atr" if r["unit"]=="atr" else "")
            cache[key]=part[col].tolist()
        values=cache[key]
        cell(r["value"],linear_quantile(values,float(r["quantile"])),"quantile/value")
        cell(r["evaluable"],len(values),"quantile/support")
        cell(r["percentile"],float(r["quantile"])*100,"quantile/percentile")
        require(r["quantile_method"]=="linear_rank_p_times_n_minus_1","quantile method")
        fields+=4
    return fields


def calendar_fields(bars):
    stamp=pd.to_datetime(bars.timestamp,utc=True).dt.tz_convert(NY)
    dates=stamp.dt.tz_localize(None).dt.normalize()
    hour=stamp.dt.hour+stamp.dt.minute/60
    return pd.DataFrame(dict(year=stamp.dt.year,month=stamp.dt.strftime("%Y-%m"),week=(dates-pd.to_timedelta(dates.dt.weekday,unit="D")).dt.strftime("%Y-%m-%d"),
        hour=stamp.dt.hour,session=bars.session.astype(str),time_stratum=np.select([hour.ge(18)|hour.lt(3),hour.lt(9),hour.lt(16)],["Asia","Europe","US"],default="Late"),
        timestamp=bars.timestamp,eligible=bars.usable.fillna(False)&bars.feature_valid.fillna(False)))


def reconcile_stability(outcomes,bars,rows,config,phase):
    p=config["periods"][phase];start,end=boundary(p["start"]),boundary(p["end"])
    tech=calendar_fields(bars);tech=tech.loc[tech.timestamp.ge(start)&tech.timestamp.lt(end)]
    tech["atr14"]=bars.loc[tech.index,"atr14"]
    tech["eligible_atr"]=tech.eligible & pd.to_numeric(tech.atr14,errors="coerce").map(finite) & pd.to_numeric(tech.atr14,errors="coerce").gt(0)
    valid_values=tech.loc[tech.eligible_atr,"atr14"].tolist()
    cuts=[linear_quantile(valid_values,p) for p in (.25,.5,.75)]
    def volatility(value):
        return "Q"+str(int(np.searchsorted(cuts,float(value),side="left"))+1) if finite(value) and float(value)>0 and all(finite(c) for c in cuts) else "undefined"
    tech["volatility_bin"]=tech.atr14.map(volatility).where(tech.eligible_atr,"undefined")
    primary=outcomes.loc[outcomes.horizon.eq(15)].copy()
    primary["volatility_bin"]=primary.entry_atr.map(volatility)
    years=range(start.tz_convert(NY).year,(end-pd.Timedelta(nanoseconds=1)).tz_convert(NY).year+1)
    months=pd.period_range(start.tz_convert(NY).strftime("%Y-%m"),(end-pd.Timedelta(nanoseconds=1)).tz_convert(NY).strftime("%Y-%m"),freq="M").astype(str)
    kinds=dict(year=[str(y) for y in years],week=week_roster(p["start"],p["end"]),month=list(months),time_stratum=["Asia","Europe","US","Late"],hour=[str(h) for h in range(24)],session=sorted(tech.session.unique()),volatility_bin=["Q1","Q2","Q3","Q4","undefined"])
    expected={(k,str(v)) for k,values in kinds.items() for v in values}
    inventory(rows,["period_kind","period"],expected,"stability calendar/clock supports")
    fields=0
    groups={k:{str(v):g for v,g in primary.groupby(k,sort=False)} for k in kinds}
    coverage={k:tech.groupby(k).eligible.agg(["size","sum"]) for k in kinds}
    for c in coverage.values():c.index=c.index.astype(str)
    for r in rows:
        kind,value=r["period_kind"],r["period"]
        part=groups[kind].get(value,primary.iloc[:0]);expected_summary=summary(part,"atr","common_atr_valid")
        cov=coverage[kind].loc[value] if value in coverage[kind].index else None
        scheduled,eligible=(int(cov["size"]),int(cov["sum"])) if cov is not None else (0,0)
        expected_summary.update(scheduled_slots=scheduled,eligible_slots=eligible,unknown_signal_slots=scheduled-eligible,
            coverage_complete=scheduled>0 and scheduled==eligible,zero_event_qualification="events_observed" if expected_summary["accepted"] else "auditable_eligible_support" if eligible else "no_eligible_support")
        kind_tech=tech.loc[tech[kind].astype(str).eq(value)]
        expected_summary.update(atr_q25=cuts[0],atr_q50=cuts[1],atr_q75=cuts[2],volatility_cut_population="phase_common_eligible_mapped_atr",eligible_atr_slots=int(kind_tech.eligible_atr.sum()))
        session_fields={"accepted","completed","censored","evaluable","contributing_sessions","contributing_weeks","sparse_warning"}|{"mean_"+m for m in METRICS}|{"session_mean_"+m for m in METRICS}
        required=set(expected_summary) if kind!="session" else session_fields|{"scheduled_slots","eligible_slots","unknown_signal_slots","coverage_complete","zero_event_qualification","atr_q25","atr_q50","atr_q75","volatility_cut_population","eligible_atr_slots"}
        # Stability intentionally omits the horizon-summary exclusion overlay.
        required-=set(("scoring_accepted","accepted_total","start_embargo","endpoint_purge","atr_support_missing"))
        require(required.issubset(r),"complete required scientific stability columns")
        for k,v in expected_summary.items():
            if k in r and (kind!="session" or k in session_fields or k in ("scheduled_slots","eligible_slots","unknown_signal_slots","coverage_complete","zero_event_qualification","atr_q25","atr_q50","atr_q75","volatility_cut_population","eligible_atr_slots")):
                cell(r[k],v,"stability/"+kind+"/"+value+"/"+k);fields+=1
    return fields


def reconcile_flow(technical,bars,rows,config,phase):
    p=config["periods"][phase]
    mask=bars.timestamp.ge(boundary(p["start"]))&bars.timestamp.lt(boundary(p["end"]))
    tech=technical.loc[mask.to_numpy()].copy();roster=bars.loc[mask]
    tech["usable"]=roster.usable.to_numpy();tech["feature_valid"]=roster.feature_valid.to_numpy()
    expected={}
    for side in ("All","Buy","Sell"):
        part=tech if side=="All" else tech.loc[tech.side.eq(side)]
        counts=dict(scheduled_slots=len(part),usable_slots=int(part.usable.fillna(False).sum()),feature_valid_slots=int(part.feature_valid.fillna(False).sum()),
            eligible_slots=int((part.usable.fillna(False)&part.feature_valid.fillna(False)).sum()),accepted=int(part.accepted.sum()),technical_candidates=int(part.technical_candidate.sum()),setup_candidates=int(part.setup_candidate.sum()))
        counts.update({"suppressed:"+str(reason):int(n) for reason,n in part.suppression_reason.value_counts().items()})
        expected.update({(side,"signal",reason):n for reason,n in counts.items()})
    inventory(rows,["direction","flow_kind","reason"],expected,"technical flow")
    for r in rows:cell(r["count"],expected[(r["direction"],r["flow_kind"],r["reason"])],"signal flow count")
    return len(rows)


def reconcile_mask_audit(bars,outcomes,rows,config,phase):
    specs=segments(config,phase)
    inventory(rows,["fold_id","horizon"],[(s["id"],str(h)) for s,h in itertools.product(specs,HORIZONS)],"canonical masks")
    fields=0
    for r in rows:
        spec=next(s for s in specs if s["id"]==r["fold_id"])
        start,end=boundary(spec["start"]),boundary(spec["end"])
        positions=np.flatnonzero((bars.timestamp.ge(start)&bars.timestamp.lt(end)).to_numpy())
        n=int(config["canonical_start_embargo_slots"])
        part=outcomes.loc[outcomes.fold_id.eq(spec["id"])&outcomes.horizon.eq(int(r["horizon"]))]
        expected=dict(start_utc=start.isoformat(),end_utc=end.isoformat(),canonical_slots=len(positions),embargo_requested=n,embargo_actual=min(n,len(positions)),
            first_signal_idx=int(positions[0]) if len(positions) else None,last_signal_idx=int(positions[-1]) if len(positions) else None,
            first_timestamp=bars.timestamp.iloc[positions[0]].isoformat() if len(positions) else None,
            embargo_last_timestamp=bars.timestamp.iloc[positions[min(n,len(positions))-1]].isoformat() if len(positions) and n else None,
            first_post_embargo_timestamp=bars.timestamp.iloc[positions[n]].isoformat() if len(positions)>n else None,
            last_timestamp=bars.timestamp.iloc[positions[-1]].isoformat() if len(positions) else None,
            accepted=len(part),start_embargo=int(part.start_embargo.sum()),endpoint_purge=int(part.endpoint_purge.sum()),
            excluded_start_embargo=int(part.mask_reason.eq("start_embargo").sum()),excluded_endpoint_purge=int(part.mask_reason.eq("period_endpoint_purge").sum()),
            atr_support_missing=int((part.score_eligible.astype(bool)&~part.atr_support.astype(bool)).sum()),scoring_accepted=int(part.score_eligible.sum()),
            completed=int(part.status.eq("completed").sum()),censored=int(part.status.eq("censored").sum()),excluded=int(part.status.eq("excluded").sum()))
        for k,v in expected.items():
            if k.endswith("timestamp") and r[k]!="":
                equal(pd.Timestamp(r[k]),pd.Timestamp(v),"mask audit/"+k)
            else:cell(r[k],v,"mask audit/"+k)
            fields+=1
    return fields


def reconcile_coverage(bars,rows):
    years=pd.to_datetime(bars.timestamp,utc=True).dt.tz_convert(NY).dt.year
    inventory(rows,["year"],[(str(y),) for y in sorted(years.unique())],"input annual coverage")
    fields=0
    for r in rows:
        part=bars.loc[years.eq(int(r["year"]))]
        ready=part.usable.fillna(False)&part.feature_valid.fillna(False)
        usable=part.usable.fillna(False)
        atr=pd.to_numeric(part.atr14,errors="coerce")
        expected=dict(scheduled_slots=len(part),usable_slots=int(usable.sum()),feature_ready_slots=int(ready.sum()),mapped_ready_slots=int(ready.sum()),
            atr_valid_slots=int((ready&np.isfinite(atr)&atr.gt(0)).sum()),ready_share=float(ready.mean()) if len(part) else None,usable_share=float(usable.mean()) if len(part) else None,
            unknown_signal_slots=int((~ready).sum()),contributing_sessions=part.session.nunique(),ready_sessions=part.loc[ready,"session"].nunique(),
            first_timestamp=part.timestamp.min(),last_available_at=part.available_at.max(),coverage_complete=len(part)>0 and bool(ready.all()),
            calendar_uncertified_slots=int((~part.calendar_valid.fillna(False)).sum()) if "calendar_valid" in part else 0,
            scope="causal_warmup_input_only" if int(r["year"])==2017 else "input_only")
        for k,v in expected.items():
            if isinstance(v,pd.Timestamp):equal(pd.Timestamp(r[k]),v,"coverage/"+k)
            elif k in r:cell(r[k],v,"coverage/"+k)
            fields+=1
        if "quality_counts" in r:
            require(json.loads(r["quality_counts"])=={str(k):int(v) for k,v in part.quality_reason.value_counts().items()},"annual quality exclusion inventory")
    return dict(check="independent_full_annual_input_readiness",status="passed",rows=len(rows),fields=fields)


def reconcile_neighborhoods(grid_rows,neighbor_rows):
    require(len(grid_rows)==len(neighbor_rows),"complete neighborhood row inventory")
    byid={r["row_id"]:r for r in grid_rows};require(len(byid)==len(grid_rows),"unique grid row identity")
    fields=0
    groups={}
    for r in grid_rows:groups.setdefault((_identity_tuple(r),r["horizon"],r["gate_family"]),[]).append(r)
    for g in groups.values():g.sort(key=lambda r:(float(r["gate_threshold"]),r["gate_id"]))
    for r in neighbor_rows:
        require(r["row_id"] in byid,"neighborhood source row missing")
        b=byid[r["row_id"]]
        for k,v in b.items():require(r[k]==v,"neighborhood copied source cell")
        g=groups[(_identity_tuple(r),r["horizon"],r["gate_family"])];i=next(i for i,x in enumerate(g) if x["gate_id"]==r["gate_id"])
        ns=g[max(0,i-1):min(len(g),i+2)];diff=[float(x["difference_mean_terminal_delta"]) for x in ns if x["difference_mean_terminal_delta"]!=""]
        defined=all(r[k]!="" for k in ("retention","mean_terminal_delta","mean_mae"))
        all_gates=[x for x in grid_rows if _identity_tuple(x)==_identity_tuple(r) and x["horizon"]==r["horizon"]]
        dominating=any(all(x[k]!="" for k in ("retention","mean_terminal_delta","mean_mae")) and float(x["retention"])>=float(r["retention"]) and float(x["mean_terminal_delta"])>=float(r["mean_terminal_delta"]) and float(x["mean_mae"])<=float(r["mean_mae"]) and
            (float(x["retention"])>float(r["retention"]) or float(x["mean_terminal_delta"])>float(r["mean_terminal_delta"]) or float(x["mean_mae"])<float(r["mean_mae"])) for x in all_gates) if defined else False
        expected=dict(previous_gate_id=g[i-1]["gate_id"] if i else None,next_gate_id=g[i+1]["gate_id"] if i+1<len(g) else None,neighbor_count=len(ns)-1,
            neighbor_min_improvement=min(diff) if len(diff)==len(ns) else None,stable_positive_neighborhood=len(ns)>=2 and len(diff)==len(ns) and all(x>0 for x in diff),pareto_frontier=not dominating if defined else None,
            frontier_scope="all_gate_families_same_cell_horizon")
        for k,v in expected.items():cell(r[k],v,"neighborhood/"+k);fields+=1
    return dict(check="independent_neighbor_and_frontier_definitions",status="passed",rows=len(neighbor_rows),fields=fields)


def _identity_tuple(r):return (r["product"],int(r["interval_minutes"]),r["touch_mode"])


def reconcile_weekly(rows,populations,config,phase):
    from .stage3_reference import weekly_sufficient
    p=config["periods"][phase];weeks=week_roster(p["start"],p["end"])
    expected_keys=[(c[0],str(c[1]),c[2],role,weight,w) for c,role,weight,w in itertools.product(populations,("selected","fixed"),("event","session"),weeks)]
    inventory(rows,["product","interval_minutes","touch_mode","role","weighting","week"],expected_keys,"whole period weekly sufficient statistics")
    cache={};fields=0
    for r in rows:
        key=_identity_tuple(r)+(r["role"],r["weighting"])
        if key not in cache:
            source=populations[key[:3]][0 if r["role"]=="selected" else 1]
            source=source.loc[source.horizon.eq(15)&source.atr_support.astype(bool)]
            cache[key]=weekly_sufficient(source,"terminal_delta_atr",weeks,r["weighting"])
        sums,counts=cache[key];i=weeks.index(r["week"])
        cell(r["sum"],sums[i],"weekly/sum");cell(r["count"],counts[i],"weekly/count");fields+=2
    return dict(check="independent_complete_week_sufficient_statistics",status="passed",phase=phase,rows=len(rows),fields=fields,weeks=weeks)


def contrast_inventory(rows,phase,config):
    cells=list(itertools.product(config["products"],map(str,config["interval_minutes"]),config["touch_modes"]))
    expected=[]
    for c in cells:
        for h,s,u,m,w in itertools.product(map(str,HORIZONS),("All","Buy","Sell"),("points","atr"),METRICS,("event","session")):
            expected.append(c+(h,s,u,m,w,"0","descriptive"))
        for w,block in itertools.product(("event","session"),("1","4","8")):
            expected.append(c+("15","All","atr","terminal_delta",w,block,"pointwise95"))
            if phase=="final" and w=="event":expected.append(c+("15","All","atr","terminal_delta",w,block,"bonferroni12"))
    inventory(rows,list(CELL)+["horizon","direction","unit","metric","weighting","block_weeks","interval_kind"],expected,"complete frozen comparison/interval family")


def publication_expectations(final,nominees,decisions,grid):
    """Independent wording reconstruction; no renderer import or claim trust."""
    family=[(i,r) for i,r in enumerate(final,1) if r['direction']=='All' and r['horizon']=='15' and r['unit']=='atr' and r['weighting']=='event' and r['metric']=='terminal_delta' and r['block_weeks']=='4' and r['interval_kind']=='bonferroni12']
    cells={(p,str(i),b) for p,i,b in itertools.product(('ES','GC','NQ'),(3,5),('fast','slow'))}
    inventory([r for _,r in family],list(CELL),cells,'primary claim twelve-cell family')
    defined=[r for _,r in family if r['ci_low']!='' and r['ci_high']!='']
    zero=sum(float(r['ci_low'])<=0<=float(r['ci_high']) for r in defined)
    above=sum(float(r['ci_low'])>0 for r in defined);below=sum(float(r['ci_high'])<0 for r in defined)
    headline=(f'The twelve prespecified final H15 comparisons have {zero} adjusted intervals including zero, {above} entirely above zero, {below} entirely below zero and {12-len(defined)} undefined. '
        'These compare each frozen gateway’s own accepted observations with its fixed-width baseline; they do not establish executable profitability.')
    claims=[]
    for index,row in family:
        def number(key):return 'undefined' if row[key]=='' else format(float(row[key]),'.4f')
        kind='identity fallback' if row['identity_fallback'] in ('True','true') else 'validated gateway'
        text=(f"{row['product']} {row['interval_minutes']}m {row['touch_mode']}: {kind} {row['selected_gate_id']} versus {row['fixed_gate_id']}; final H15 normalized terminal difference {number('estimate')}, "
            f"four-week Bonferroni interval [{number('ci_low')}, {number('ci_high')}], selected/fixed completed ATR-valid observations {row['selected_evaluable']}/{row['fixed_evaluable']}, undefined draws {row['undefined_draws']}.")
        claims.append((index,row,text))
    inventory(nominees,list(CELL),cells,'development nominee claim support');inventory(decisions,list(CELL),cells,'validation decision claim support')
    nominated=[r for r in nominees if r['nomination_status']=='eligible_nominee'];absolute=sum(r['selected_gate_family']=='absolute' for r in nominated);atr=sum(r['selected_gate_family']=='atr' for r in nominated)
    passed=sum(r['validation_passed'] in ('True','true') for r in decisions);failed=[r for r in decisions if r['validation_status']=='fixed_fallback_validation_failed'];guards={}
    for row in failed:
        for token in row['failed_validation_guards'].split(';'):
            if token:guards[token]=guards.get(token,0)+1
    guard_text=', '.join(f'{k}={v}' for k,v in sorted(guards.items())) or 'none'
    h15=[r for r in grid if r['horizon']=='15'];require(len(h15)==192,'complete H15 development narrative support')
    def extent(key):
        values=[float(r[key]) for r in h15 if r[key]!='']
        return f'[{min(values):.4f}, {max(values):.4f}]' if values else 'undefined'
    counts=[int(r['evaluable']) for r in h15]
    selection=(f'Development produced {len(nominated)} eligible nominees: {absolute} absolute-width and {atr} ATR-ratio gateways; {12-len(nominated)} cells retained the fixed baseline because no candidate passed every guard. '
        f'Validation passed {passed} nominees and rejected {len(failed)} eligible development nominees. Final fixed fallbacks total {12-passed}. Failed validation guard counts among rejected nominees are {guard_text}; a nominee may fail multiple guards. '
        f'Across the 192 development H15 gateway cells, completed ATR-valid support ranges from {min(counts)} to {max(counts)}. Same-H fixed-baseline retention ranges {extent("retention")}, normalized terminal improvement {extent("difference_mean_terminal_delta")} and normalized mean MAE {extent("mean_mae")}. '
        'These ranges describe both gateway families and all failures; they do not select a global optimum. The exact grid, fold supports, guard failures and neighboring thresholds remain in the private saved tables.')
    return family,headline,claims,selection


def reconcile_final_assessment(stage):
    """Reconstruct the interpretation frozen before recent-phase scoring."""
    stage=Path(stage).resolve();path=stage/'provenance/final-assessment.json'
    if not path.exists():return None
    observed=[record(path),record(stage/'config.json')];saved=json.loads(path.read_text());config=json.loads((stage/'config.json').read_text())
    _,rows=read_csv(stage/'tables/S3-T14_final_effects.csv')
    primary=[r for r in rows if r['horizon']=='15' and r['direction']=='All' and r['unit']=='atr' and r['metric']=='terminal_delta' and r['weighting']=='event' and r['block_weeks']=='4' and r['interval_kind']=='bonferroni12']
    inventory(primary,list(CELL),itertools.product(('ES','GC','NQ'),('3','5'),('fast','slow')),'frozen final assessment family')
    classification=dict(includes_zero=0,above_zero=0,below_zero=0,undefined=0)
    for row in primary:
        key='undefined' if row['ci_low']=='' or row['ci_high']=='' else 'above_zero' if float(row['ci_low'])>0 else 'below_zero' if float(row['ci_high'])<0 else 'includes_zero'
        classification[key]+=1
    text=(f"The twelve prespecified final H15 comparisons have {classification['includes_zero']} adjusted intervals including zero, {classification['above_zero']} entirely above zero, {classification['below_zero']} entirely below zero and {classification['undefined']} undefined. "
        'These compare each frozen gateway’s own accepted observations with its fixed-width baseline; they do not establish executable profitability.')
    require(saved['status']=='frozen_final_assessment_before_recent' and saved['period']=='final','explicit frozen final assessment scope')
    require(saved['primary_rows']==primary and saved['classification']==classification and saved['conclusion']==text,'independent frozen final assessment values/classification/conclusion')
    require(saved['family']==config['primary_comparison_family'],'frozen final assessment declared family')
    expected={'tables/S3-T14_final_effects.csv','provenance/independent-final.json'}
    require({p['path'] for p in saved['records']}==expected and len(saved['records'])==2,'frozen final assessment predecessor pins')
    for pin in saved['records']:
        actual=record(resolve_pin(stage,pin));require(actual['sha256']==pin['sha256'] and actual['bytes']==pin['bytes'],'frozen final assessment input byte identity');observed.append(actual)
    predecessor=json.loads((stage/'provenance/independent-final.json').read_text())
    require(predecessor['status']=='passed' and predecessor['phase']=='final','independently passed final evidence before interpretation freeze')
    for pin in observed:require(Path(pin['path']).stat().st_size==pin['bytes'] and sha256(pin['path'])==pin['sha256'],'frozen final assessment bytes changed during verification')
    return dict(check='independent_frozen_final_assessment',status='passed',classification=classification,conclusion=text,**portable_pins(stage,observed))


def verify_publication(stage):
    """Complete predeclared selectors, exact strings and independent prose."""
    import html
    stage=Path(stage)
    publication=json.loads((stage/'publication.json').read_text());bindings=json.loads((stage/'source-bindings.json').read_text())
    require(bindings['publication_sha256']==sha256(stage/'publication.json'),'publication hash binding')
    assessment=reconcile_final_assessment(stage)
    require((stage/'publication.json').stat().st_size<=96*1024,'publication source byte budget')
    transfer_paths={stage/name for name in ('publication.json','source-bindings.json','report.md','report.html','advice.md')}
    transfer_paths.update(stage/b['source_path'] for b in bindings['cells']+bindings['claims']+bindings['downloads'])
    transfer_paths.update(stage/b['download_path'] for b in bindings['downloads'])
    transfer_paths.update(stage/b['path'] for b in bindings['figures'])
    transfer_paths.update(stage/source['path'] for b in bindings['figures'] for source in b['sources'])
    transfer_paths.update(stage/source['path'] for source in bindings['selection_claim']['sources'])
    transfer_paths.update(Path(pin['path']) for pin in bindings.get('baseline_sources',[]))
    observed=[record(path) for path in sorted(transfer_paths)]
    if assessment:observed.extend(record(resolve_pin(stage,pin)) for pin in assessment['consumed'])
    sections={s['id']:s for s in publication['sections']};require(len(sections)==len(publication['sections']),'unique publication sections')
    paths={k:'tables/'+name for k,name in dict(final='S3-T14_final_effects.csv',validation='S3-T14_validation_effects.csv',recent='S3-T14_recent_effects.csv',decisions='S3-T13_validation_decisions.csv',nominees='S3-T13_development_nominees.csv',grid='S3-T11_development_grid.csv',horizons='S3-T02_final_horizon_scorecard.csv',coverage='S3-T00_coverage.csv').items()}
    raw={k:read_csv(stage/path)[1] for k,path in paths.items()}
    family,headline,claims,selection=publication_expectations(raw['final'],raw['nominees'],raw['decisions'],raw['grid'])
    choice={tuple(r[k] for k in CELL):r for r in raw['decisions']}
    indexed=lambda key,predicate:[i for i,r in enumerate(raw[key],1) if predicate(r)]
    primary=lambda r:r['direction']=='All' and r['horizon']=='15' and r['unit']=='atr' and r['weighting']=='event' and r['metric']=='terminal_delta' and r['block_weeks']=='4' and r['interval_kind']=='pointwise95'
    sensitivity=indexed('final',lambda r:r['horizon']=='15' and r['direction']=='All' and r['unit']=='atr' and r['metric']=='terminal_delta' and r['weighting']=='event' and r['interval_kind'] in ('pointwise95','bonferroni12'))
    full_horizons=indexed('horizons',lambda r:r['direction']=='All' and r['unit']=='atr' and r['support']=='common_atr_valid' and r['gate_id']==choice[tuple(r[k] for k in CELL)]['selected_gate_id'])
    require(len(full_horizons)==168,'all fourteen downloaded horizons')
    expected_tables={'primary-final':('final',[i for i,_ in family]),'primary-sensitivity':('final',sensitivity),'choices':('decisions',list(range(1,13))),
        'effects-validation':('validation',indexed('validation',primary)),'effects-recent':('recent',indexed('recent',primary))}
    for branch in ('fast','slow'):
        expected_tables['horizons-'+branch]=('horizons',[i for i in full_horizons if raw['horizons'][i-1]['touch_mode']==branch and int(raw['horizons'][i-1]['horizon']) in (1,15,30,100)])
    require({b['section_id'] for b in bindings['cells']}==set(expected_tables) and len(bindings['cells'])==len(expected_tables),'complete public table selector inventory')
    require({s['id'] for s in publication['sections'] if s['kind']=='table'}==set(expected_tables),'complete publication table inventory')
    counts=dict(cells=0,downloads=0,claims=0,figures=0)
    for binding in bindings['cells']:
        key,indices=expected_tables[binding['section_id']];path=stage/binding['source_path']
        require(binding['source_path']==paths[key] and binding['source_rows']==indices,'public exact frozen table selector')
        require(sha256(path)==binding['source_sha256'],'public source hash');rows=raw[key];section=sections[binding['section_id']];selected=[rows[i-1] for i in indices]
        require(binding['row_ids']==[r['row_id'] for r in selected],'public row identity selectors')
        require(len(section['rows'])==len(selected) and len(selected)<=100 and len(binding['columns'])<=12,'public table population/budget')
        require([c['key'] for c in section['columns']]==binding['columns'],'public column selectors')
        for public,row in zip(section['rows'],selected):
            require(set(public)==set(binding['columns']),'public exact column inventory')
            for col in binding['columns']:
                expected=(float(row[col]) if col in binding.get('numeric_columns',[]) else row[col]) if row[col]!='' else None
                require(public[col]==expected,'public cell exact saved value conversion');counts['cells']+=1
    expected_downloads={'primary-effects':('final',sensitivity),'frozen-choices':('decisions',list(range(1,13))),'selected-horizon-scorecard':('horizons',full_horizons),'coverage-support':('coverage',list(range(1,len(raw['coverage'])+1)))}
    require({b['download_id'] for b in bindings['downloads']}==set(expected_downloads) and len(bindings['downloads'])==4,'complete four download selectors')
    declarations={d['id']:d for d in publication['downloads']};require(set(declarations)==set(expected_downloads),'complete publication download inventory')
    for binding in bindings['downloads']:
        key,indices=expected_downloads[binding['download_id']];source=stage/binding['source_path'];destination=stage/binding['download_path'];declaration=declarations[binding['download_id']]
        require(binding['source_path']==paths[key] and binding['source_rows']==indices,'download exact frozen selector')
        require(sha256(source)==binding['source_sha256'] and sha256(destination)==binding['download_sha256'],'download source bytes')
        columns,actual=read_csv(destination);require(columns==binding['columns'] and len(columns)<=24 and len(actual)<=1000 and destination.stat().st_size<=256*1024,'download columns/budget')
        expected=[{c:raw[key][i-1][c] for c in columns} for i in indices];require(actual==expected,'download exact original strings')
        require(declaration['columns']==columns and declaration['rowCount']==len(actual) and declaration['sha256']==sha256(destination) and declaration['path']==binding['download_path'],'download declaration exact saved values')
        counts['downloads']+=len(actual)*len(columns)
    require(sum((stage/b['download_path']).stat().st_size for b in bindings['downloads'])<=512*1024,'combined download budget')
    require(publication['summary']==headline,'independent aggregate headline wording')
    aggregate=bindings['aggregate_claim'];require(aggregate['text']==headline and aggregate['source_path']==paths['final'] and aggregate['source_rows']==[i for i,_ in family] and aggregate['source_sha256']==sha256(stage/paths['final']),'independent aggregate claim binding')
    require(sections['findings']['body']==headline+'\n\n'+'\n\n'.join(text for _,_,text in claims),'independent complete findings wording')
    require(len(bindings['claims'])==12 and {b['source_row'] for b in bindings['claims']}=={i for i,_ in family},'complete primary claim source selectors')
    md=(stage/'report.md').read_text();advice=(stage/'advice.md').read_text();offline=(stage/'report.html').read_text()
    for text in (headline,selection):require(text in md and text in advice and html.escape(text) in offline,'aggregate/selection offline advice transfer')
    require(headline in sections['advice']['body'],'aggregate advice publication transfer')
    require(sections['selection-results']['body']==selection,'independent development and validation interpretation')
    require(bindings['selection_claim']['text']==selection,'selection claim binding wording')
    require(bindings['selection_claim']['sources']==[dict(path=paths[k],sha256=sha256(stage/paths[k])) for k in ('nominees','decisions','grid')],'selection claim source identities')
    claim_lookup={i:(row,text) for i,row,text in claims}
    for binding in bindings['claims']:
        row,text=claim_lookup[binding['source_row']];require(binding['source_path']==paths['final'] and binding['source_sha256']==sha256(stage/paths['final']),'claim source bytes')
        require(binding['text']==text and binding['section_id']=='findings','independent individual claim wording')
        for k,v in binding['values'].items():require(row[k]==v,'claim exact source value')
        require(text in md and text in advice and html.escape(text) in offline,'claim offline advice transfer');counts['claims']+=1
    expected_figures={name+'.png' for name in ('development_heatmaps','retention_risk_frontiers','horizon_response','neighborhood_stability','frozen_choice_evaluation','calendar_coverage')}
    require({Path(b['path']).name for b in bindings['figures']}==expected_figures and len(bindings['figures'])==6,'complete frozen figure inventory')
    require({Path(s['path']).name for s in publication['sections'] if s['kind']=='figure'}==expected_figures,'complete publication figure inventory')
    for binding in bindings['figures']:
        require(sha256(stage/binding['path'])==binding['sha256'] and (stage/binding['path']).stat().st_size<=2*1024*1024,'figure bytes/budget')
        for source in binding['sources']:
            require(sha256(stage/source['path'])==source['sha256'],'figure source bytes');_,rows=read_csv(stage/source['path'])
            require(all(0<int(i)<=len(rows) for i in source['rows']),'figure row selectors')
            require(source['row_ids']==[rows[int(i)-1]['row_id'] for i in source['rows']],'figure exact row identity selectors')
            require(all(c in rows[0] for c in source['columns']) if rows else not source['rows'],'figure column selectors')
        counts['figures']+=1
    require(sum((stage/b['path']).stat().st_size for b in bindings['figures'])<=8*1024*1024,'combined figure budget')
    for pin in bindings.get('baseline_sources',[]):require(sha256(pin['path'])==pin['sha256'],'private cross-run baseline byte identity')
    for pin in observed:require(Path(pin['path']).stat().st_size==pin['bytes'] and sha256(pin['path'])==pin['sha256'],'report transfer bytes changed during verification')
    return dict(check='exact_saved_publication_transfer',status='passed',**counts,**portable_pins(stage,observed))


def verify_bundle(stage, phase="complete"):
    """Read retained ledgers exclusively, independently close the requested gate.

    Phase gates are immutable predecessors checked by root before any following
    phase can execute. This function never requests a producer or calculates a
    path outside the phase-specific event inventory already authorized and saved.
    """
    stage=Path(stage).resolve()
    require(phase in ("development","validation","final","recent","complete"),"explicit verification phase")
    config=json.loads((stage/"config.json").read_text())
    sources=[record(Path(__file__).with_name(name)) for name in ("stage3_reference.py","stage3_reconcile.py")]
    recovery_pins=recovery_dependency_pins(stage,config) if phase in ("development","complete") else []
    if phase=="complete":
        checks=[];pins={p["path"]:p for p in portable_pins(stage,recovery_pins)["consumed"]};phase_pins=[]
        for current in ("development","validation","final","recent"):
            path=stage/f"provenance/independent-{current}.json"
            receipt=json.loads(path.read_text())
            require(receipt.get("status")=="passed" and receipt.get("phase")==current,"passing independent predecessor phase required")
            phase_pins.append(record(path));checks.extend(receipt["checks"])
            for pin in receipt["consumed"]:
                if pin["path"] in pins:require(pins[pin["path"]]==pin,"phase input/source identity changed")
                pins[pin["path"]]=pin
            for pin in receipt["pins"]:require(Path(pin["path"]).stat().st_size==pin["bytes"] and sha256(pin["path"])==pin["sha256"],"verified phase checker source changed")
        for pin in pins.values():require(resolve_pin(stage,pin).stat().st_size==pin["bytes"] and sha256(resolve_pin(stage,pin))==pin["sha256"],"verified phase source/input/output bytes changed")
        assessment=reconcile_final_assessment(stage)
        if assessment:
            checks.append(assessment)
            for pin in assessment["consumed"]:
                if pin["path"] in pins:require(pins[pin["path"]]==pin,"final-assessment/numerical byte pin disagreement")
                pins[pin["path"]]=pin
        for current in ("validation","final","recent"):
            _,rows=read_csv(stage/"tables"/f"S3-T14_{current}_effects.csv");contrast_inventory(rows,current,config)
        if (stage/"publication.json").exists():
            transfer=verify_publication(stage);checks.append(transfer)
            for pin in transfer["consumed"]:
                if pin["path"] in pins:require(pins[pin["path"]]==pin,"report/numerical byte pin disagreement")
                pins[pin["path"]]=pin
        return dict(schema_version="study21.stage3-independent/v1",status="passed",phase=phase,checks=checks,**portable_pins(stage,list(pins.values())+phase_pins),
            pins=sources,scope="All independently passed chronological phase calculations retained through exact source/input/output identity rechecks; complete twelve-cell uncertainty family and selected report transfer when present.",
            independent_uncertainty=[c for c in checks if c["check"] in ("independent_paired_period_week_uncertainty","independent_complete_week_sufficient_statistics")])
    phases=("development","validation","final","recent") if phase=="complete" else (phase,)
    consumed=[record(stage/name) for name in ("config.json","protocol.md","inputs.lock.json","baseline.lock.json","mapped.manifest.json")]+recovery_pins
    checks=[]
    def read(r):
        path=Path(r["path"]);path=path if path.is_absolute() else stage/path
        require(path.stat().st_size==r["bytes"] and sha256(path)==r["sha256"],"retained ledger bytes")
        frame=pd.read_parquet(path)
        require(len(frame)==r.get("row_count",r.get("rows")),"retained ledger row count")
        consumed.append(record(path));return frame
    for current in phases:
        acceptance_path=stage/f"acceptance-{current}.manifest.json"
        phase_path=stage/f"stage3-{current}.manifest.json"
        acceptance=json.loads(acceptance_path.read_text());phase_manifest=json.loads(phase_path.read_text())
        records=acceptance["records"]+phase_manifest["records"]
        consumed.extend([record(acceptance_path),record(phase_path)])
        for t in phase_manifest["tables"]:
            path=stage/t["path"];require(path.stat().st_size==t["bytes"] and sha256(path)==t["sha256"],"saved numerical table bytes")
            consumed.append(record(path))
        require(records,"requested phase retained ledger inventory absent")
        choice_path=stage/"tables"/("S3-T13_development_nominees.csv" if current=="development" else "S3-T13_validation_decisions.csv" if current in ("final","recent") else "S3-T13_development_nominees.csv")
        consumed.append(record(choice_path))
        _,choice_rows=read_csv(choice_path)
        inventory(choice_rows,list(CELL),itertools.product(config["products"],map(str,config["interval_minutes"]),config["touch_modes"]),"complete twelve-cell frozen choices")
        bychoice={_identity_tuple(r):r for r in choice_rows}
        populations={};grid_rows=[];neighbor_rows=[]
        for product,interval in itertools.product(config["products"],config["interval_minutes"]):
            local=[r for r in records if r["product"]==product and int(r["interval_minutes"])==interval]
            bars_records=[r for r in local if r["role"]=="bars"]
            require(len(bars_records)==1,"one complete causal bar roster required")
            bars=read(bars_records[0])
            workspace=Path(__file__).resolve().parents[3]
            lock=json.loads((stage/"inputs.lock.json").read_text())
            delivery_path=Path(lock["delivery"]["path"])
            if not delivery_path.is_absolute():delivery_path=workspace/delivery_path
            require(sha256(delivery_path)==lock["delivery"]["sha256"],"new immutable delivery identity")
            delivery=json.loads(delivery_path.read_text())
            native_record=next(r for r in delivery["output_files"] if r["product"]==product and int(r["interval_minutes"])==5)
            from abacus_bhishma.paths import load_workspace_paths
            publication_root=load_workspace_paths(workspace).publication_root
            native_record=native_record|dict(path=str(publication_root/native_record["path"]))
            native=read(native_record)
            checks.append(reconcile_mapping(bars,native));consumed.append(record(delivery_path))
            # One scan per cell and table; the full quantile grid is large.
            cell_tables={Path(t["path"]).name:table_slice(stage/t["path"],product,interval) for t in phase_manifest["tables"]}
            grouped_tables={name:{} for name in cell_tables}
            for name,table in cell_tables.items():
                for row in table:grouped_tables[name].setdefault((row.get("touch_mode"),row.get("gate_id")),[]).append(row)
            causal_bars=bars.loc[bars.available_at.le(boundary(config["periods"][current]["end"]))].reset_index(drop=True)
            prepared=reference_decisions(causal_bars)
            cov_path=stage/"tables/S3-T00_coverage.csv"
            checks.append(reconcile_coverage(bars,table_slice(cov_path,product,interval)))
            consumed.append(record(cov_path))
            cell_paths={};cell_events={}
            for branch in ("fast","slow"):
                tech=[r for r in local if r["role"]=="technical" and r.get("touch_mode",r.get("branch"))==branch]
                require(tech,"technical gateway roster absent")
                choice=bychoice[(product,interval,branch)]
                fixed=gate_id("absolute",config["minimum_width_points"][product])
                expected_ids={g["gate_id"] for g in gate_grid(config,product)} if current=="development" else {choice["nominee_gate_id"] if current=="validation" else choice["selected_gate_id"],fixed}
                require({r["gate_id"] for r in tech}==expected_ids and len(tech)==len(expected_ids),"complete explicitly authorized gateway inventory")
                gates=[];accepted={};actual_paths={}
                for r in tech:
                    gate=next((g for g in gate_grid(config,product) if g["gate_id"]==r["gate_id"]),None)
                    require(gate is not None,"unknown gateway")
                    siblings=[s for s in local if s.get("touch_mode",s.get("branch"))==branch and s.get("gate_id")==r["gate_id"]]
                    er=[s for s in siblings if s["role"]=="events"];orr=[s for s in siblings if s["role"]=="outcomes"]
                    require(len(er)==len(orr)==1,"exact events/outcomes gateway inventory")
                    receipt,causal=reconcile_stream(causal_bars,read(r),read(er[0]),gate,branch,prepared)
                    checks.append(receipt|dict(period=current,product=product,interval_minutes=interval,touch_mode=branch,gate_id=gate["gate_id"]))
                    p=config["periods"][current]
                    scoped=causal.loc[causal.timestamp.ge(boundary(p["start"])) & causal.timestamp.lt(boundary(p["end"]))]
                    accepted[gate["gate_id"]]=scoped;gates.append(gate);actual_paths[gate["gate_id"]]=orr[0]
                # Only physical signals accepted by at least one approved saved
                # gateway are scored; no unapproved later candidate is inspected.
                union=pd.concat(list(accepted.values()),ignore_index=True).drop_duplicates("event_id")
                expected=reference_outcomes(bars,union,config,current,HORIZONS).set_index(["event_id","horizon"],drop=False)
                baseline_path=read(actual_paths[fixed])
                branch_full={}
                for gate in gates:
                    gid=gate["gate_id"];actual=read(actual_paths[gid])
                    ids=set(accepted[gid].event_id)
                    selected=expected.loc[expected.event_id.isin(ids)].reset_index(drop=True).copy()
                    selected["gate_id"],selected["gate_family"],selected["gate_threshold"]=gid,gate["family"],gate["threshold"]
                    fields=compare_frames(actual,selected,["gate_id","event_id","horizon"],IDENTITY_FIELDS+PATH_FIELDS,"independent approved paths")
                    checks.append(dict(check="independent_all_forward_paths_and_masks",status="passed",period=current,product=product,interval_minutes=interval,touch_mode=branch,gate_id=gid,rows=len(actual),fields=fields))
                    cell_paths[(branch,gid)]=actual.loc[actual.horizon.eq(15)].copy()
                    branch_full[gid]=actual if current!="development" else actual.loc[actual.horizon.eq(15)].copy()
                    def rows(name):return grouped_tables[name].get((branch,gid),[])
                    support_names=("common_atr_valid","full_absolute") if gate["family"]=="absolute" else ("common_atr_valid",)
                    sr=rows(f"S3-T02_{current}_horizon_scorecard.csv")
                    inventory(sr,["horizon","direction","unit","support"],itertools.product(map(str,HORIZONS),("All","Buy","Sell"),("points","atr"),support_names),"complete horizon summary")
                    table_fields=reconcile_summary_rows(actual,sr,context="horizon summaries")
                    table_fields+=reconcile_quantiles(actual,rows(f"S3-T03_{current}_quantiles.csv"))
                    table_fields+=reconcile_stability(actual,bars,rows(f"S3-T04_{current}_stability.csv"),config,current)
                    expected_tech,_=expected_gate(prepared[0][branch],prepared[1][branch],gate)
                    table_fields+=reconcile_flow(expected_tech,causal_bars,rows(f"S3-T01_{current}_flow.csv"),config,current)
                    table_fields+=reconcile_mask_audit(bars,actual,rows(f"S3-T16_{current}_masks.csv"),config,current)
                    if current=="development":
                        gr=rows("S3-T11_development_grid.csv")
                        inventory(gr,["horizon"],[(str(h),) for h in HORIZONS],"full development gate horizon grid")
                        table_fields+=reconcile_summary_rows(actual,gr,baseline=baseline_path,context="full development grid")
                        grid_rows.extend(gr);neighbor_rows.extend(rows("S3-T15_neighborhood_frontiers.csv"))
                    checks.append(dict(check="independent_complete_summary_quantile_calendar_flow_masks",status="passed",period=current,product=product,interval_minutes=interval,touch_mode=branch,gate_id=gid,fields=table_fields))
                if current in ("development","validation"):
                    folds=[r for r in cell_tables[f"S3-T12_{current}_fold_eligibility.csv"] if r["touch_mode"]==branch]
                    supports=[r for r in folds if r["record_kind"]=="fold_support"]
                    assessments=[r for r in folds if r["record_kind"]=="candidate_assessment"]
                    fold_ids=[f["id"] for f in config["development_folds" if current=="development" else "validation_folds"]]+["pooled"]
                    inventory(supports,["gate_id","fold_id"],itertools.product(expected_ids,fold_ids),"complete candidate fold supports")
                    inventory(assessments,["gate_id"],[(g,) for g in expected_ids],"complete candidate eligibility assessments")
                    decisions=[r for r in cell_tables["S3-T13_development_nominees.csv" if current=="development" else "S3-T13_validation_decisions.csv"] if r["touch_mode"]==branch]
                    receipt,_=reconcile_selection({g:cell_paths[(branch,g)] for g in expected_ids},gates,config,supports,assessments,decisions,current,choice["nominee_gate_id"])
                    checks.append(receipt|dict(product=product,interval_minutes=interval,touch_mode=branch))
                if current!="development":
                    selected_id=choice["nominee_gate_id"] if current=="validation" else choice["selected_gate_id"]
                    populations[(product,interval,branch)]=(branch_full[selected_id],branch_full[fixed])
                cell_events[branch]=gates
            print(json.dumps(dict(independent_stage3_cell="passed",phase=current,product=product,interval_minutes=interval)),flush=True)
        if current=="development":
            checks.append(reconcile_neighborhoods(grid_rows,neighbor_rows))
            require(len(grid_rows)==2688,"exact2688 scientific development grid cells")
        else:
            _,effects=read_csv(stage/"tables"/f"S3-T14_{current}_effects.csv")
            contrast_inventory(effects,current,config)
            checks.append(reconcile_contrasts(effects,populations,config,current))
            _,weekly=read_csv(stage/"tables"/f"S3-weekly-{current}.csv")
            checks.append(reconcile_weekly(weekly,populations,config,current))
    if phase=="complete" and (stage/"publication.json").exists():checks.append(verify_publication(stage))
    for pin in consumed:require(sha256(pin["path"])==pin["sha256"] and Path(pin["path"]).stat().st_size==pin["bytes"],"input bytes changed during independent verification")
    for pin in sources:require(sha256(pin["path"])==pin["sha256"],"independent checker source changed during execution")
    return dict(schema_version="study21.stage3-independent/v1",status="passed",phase=phase,checks=checks,
        **portable_pins(stage,consumed),pins=sources,scope="Independent full causal gateway states, carried identities, every authorized saved scalar path/mask, complete scientific table inventories, selection/validation/fallback, neighborhoods/frontiers and period uncertainty; selected report transfer when available.")
