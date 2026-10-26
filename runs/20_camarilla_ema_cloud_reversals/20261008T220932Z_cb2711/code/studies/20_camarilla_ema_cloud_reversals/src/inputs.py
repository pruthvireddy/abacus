"""Read-only input hash, lineage, mapping and observation-quality audit."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from abacus_bhishma.continuous_loader import open_continuous_dataset, price_to_float
from abacus_bhishma.paths import load_workspace_paths
from .calendar import assign_days, expected, holidays, max_missing_run, stamp, previous_weekday
from .core import FIVE, MINUTE, indicator_segment
from .storage import sha, save_json, save_csv
from .spec import split_for, PRODUCTS

def aggregate(minutes):
    b = minutes.assign(ts=minutes.ts.to_numpy() // FIVE * FIVE)
    out = b.groupby("ts", sort=True).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"), count=("ts", "size"), first=("minute_ts", "first"), last=("minute_ts", "last"), contract=("contract", "first"), contracts=("contract", "nunique"), instrument_id=("instrument_id", "first"), valid=("valid", "all"), raw_symbol=("raw_symbol", "first")).reset_index()
    out["complete"] = (out["count"] == 5) & (out["first"] == out.ts) & (out["last"] == out.ts + 4 * MINUTE) & out.valid & (out.contracts == 1)
    return out

def load_minutes(root, product):
    columns = ["ts_event", "session_date", "instrument_id", "raw_symbol", "roll_id", "mapping_start", "mapping_end", "open", "high", "low", "close", "volume"]
    f = open_continuous_dataset(root, product, "unadjusted").to_table(columns=columns).to_pandas().sort_values("ts_event").reset_index(drop=True)
    if f.ts_event.duplicated().any():
        raise AssertionError("Duplicate source timestamps")
    f["ts"] = f.ts_event.astype("int64")
    f["minute_ts"] = f.ts
    f["source_day"] = f.session_date.astype(str)
    f["day"] = assign_days(f.ts.to_numpy())
    f["contract"] = f.raw_symbol + "@" + f.roll_id.astype(str)
    for c in ("raw_symbol", "source_day", "day", "contract"):
        f[c] = f[c].astype("category")
    for c in ("open", "high", "low", "close"):
        f[c] = price_to_float(f[c].to_numpy())
    f["valid"] = np.isfinite(f[["open", "high", "low", "close"]]).all(axis=1) & (f.high >= f[["open", "low", "close"]].max(axis=1)) & (f.low <= f[["open", "high", "close"]].min(axis=1))
    return f.drop(columns=["ts_event", "session_date", "mapping_start", "mapping_end"])

def verify_inputs(work, workspace):
    paths = load_workspace_paths(workspace)
    root = paths.publication_root
    manifests = ["volume_lead_unadjusted_v1", "tv_indicators__dridr_ohlcv_5m__v1"]
    records, seen = [], set()
    for name in manifests:
        p = root / "catalog/datasets" / (name + ".json")
        m = json.loads(p.read_text())
        records.append({"role": "manifest", "path": str(p.relative_to(root)), "sha256": sha(p), "bytes": p.stat().st_size})
        for r in m["output_files"] + [x for x in m.get("source_files", []) if x["path"].endswith(("condition.json", ".json"))]:
            if r["path"] in seen:
                continue
            seen.add(r["path"])
            p = root / r["path"]
            actual = sha(p)
            if actual != r["sha256"] or p.stat().st_size != r["bytes"]:
                raise AssertionError(f"Input identity failed: {r['path']}")
            records.append({**r, "role": "consumed_partition_or_lineage", "verified": True})
    p = root / "catalog/calendars/cme_fixed_clock_session_v1.json"
    records.append({"role": "calendar_reference", "path": str(p.relative_to(root)), "sha256": sha(p), "bytes": p.stat().st_size})
    m5 = json.loads((root / "catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json").read_text())
    # price_adjustment in each released 5m bucket is the cross-check translation.
    source_lock = json.loads((workspace / "studies/20_camarilla_ema_cloud_reversals/inputs.lock.json").read_text())
    for r in source_lock["sources"]:
        p = (workspace if r["root_alias"] == "workspace_root" else root) / r["path"]
        if sha(p) != r["sha256"]:
            raise AssertionError(f"Source hash failed: {p}")
    save_json(work / "inputs.lock.json", {"schema_version": "study-execution-lock-1", "root_resolution": {"publication_root": str(root), "workspace_root": str(workspace)}, "sources": source_lock["sources"], "market_datasets": manifests, "files": records, "certification": "hash and retained lineage verified; mapping arrival times and individual annual holiday schedules unavailable"})
    return root, m5

def crosscheck(raw_bars, root, manifest, product):
    files = [root / f["path"] for f in manifest["output_files"] if f"product={product}/" in f["path"]]
    published = pd.concat([pq.ParquetFile(p).read().to_pandas() for p in files], ignore_index=True)
    published["ts"] = published.ts_event.astype("int64")
    joined = raw_bars.merge(published, on="ts", how="outer", suffixes=("_raw", "_release"), indicator=True)
    paired = joined[joined._merge == "both"]
    clean = paired[~paired.is_mixed_contract_bar & ~paired.is_mixed_adjustment_bar]
    count_bad = int((paired["count"] != paired.source_bar_count).sum())
    volume_bad = int((paired.volume_raw != paired.volume_release).sum())
    price_bad = 0
    for c in ("open", "high", "low", "close"):
        price_bad += int((np.abs(clean[c + "_raw"] - (clean[c + "_release"] - clean.price_adjustment) * 1e-9) > 1e-7).sum())
    identity_bad = int((clean.instrument_id_raw != clean.instrument_id_release).sum())
    result = {"product": product, "raw_buckets": len(raw_bars), "released_buckets": len(published), "paired": len(paired), "unpaired": int((joined._merge != "both").sum()), "count_mismatch": count_bad, "volume_mismatch": volume_bad, "OHLC_translation_mismatch": price_bad, "identity_mismatch": identity_bad, "mixed_excluded_from_price_check": len(paired) - len(clean)}
    if any(result[x] for x in ("unpaired", "count_mismatch", "volume_mismatch", "OHLC_translation_mismatch", "identity_mismatch")):
        raise AssertionError(f"Aggregation/lineage cross-check failed: {result}")
    return result

def prepare_product(work, root, product, manifest):
    f = load_minutes(root, product)
    print(f"{product}: {len(f):,} primary source rows", flush=True)
    check = crosscheck(aggregate(f), root, manifest, product)
    print(f"{product}: full aggregation/lineage cross-check passed", flush=True)
    master = pq.ParquetFile(root / "data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet").read().to_pandas()
    master = master[master["product"] == product]
    rolled = pq.ParquetFile(root / "data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet").read().to_pandas()
    rolled = rolled[rolled["product"] == product]
    for row in master.itertuples():
        sel = f[f.roll_id == row.roll_id]
        assert (sel.raw_symbol == row.raw_symbol).all() and (sel.instrument_id == row.instrument_id).all()
        assert (sel.ts >= stamp(pd.Timestamp(row.mapping_start) - pd.Timedelta(days=1), 1080)).all()
        assert (sel.ts < stamp(pd.Timestamp(row.mapping_end) - pd.Timedelta(days=1), 1080)).all()
    hs = holidays(product)
    condition = json.loads((root / "data/raw/databento/GLBX.MDP3/ohlcv-1m/GLBX-20260920-577W4VCSK7/condition.json").read_text())
    bad_dates = {r["date"] for r in condition if r["condition"] not in ("available", "holiday")}
    chunks, audits, expected_all, feature_schedule = [], [], [], []
    groups = {day: g for day, g in f.groupby("day", sort=False, observed=True)}
    for day_index, day in enumerate(pd.bdate_range("2010-06-07", "2026-09-18").strftime("%Y-%m-%d")):
        ex = expected(product, day)
        g = groups.get(day, f.iloc[:0])
        selected = g[g.ts.isin(ex)].copy()
        present = np.isin(ex, selected.ts.to_numpy())
        valid = bool(selected.valid.all()) and len(selected) > 0
        firstlast = bool(present[:5].all() and present[-5:].all())
        coverage = len(selected) / len(ex)
        condition_bad = bool(set(pd.to_datetime([ex[0], ex[-1]], utc=True).strftime("%Y-%m-%d")) & bad_dates)
        contract = selected.contract.iloc[0] if len(selected) else None
        stable = selected.contract.nunique() == 1
        reason = []
        if day in hs:
            reason.append("holiday_or_shortened")
        if condition_bad:
            reason.append("retrospective_source_degradation")
        if coverage < .99:
            reason.append("prior_HLC_coverage_below_99pct")
        if not firstlast:
            reason.append("prior_HLC_edge_missing")
        missingrun = max_missing_run(present)
        if missingrun > 5:
            reason.append("prior_HLC_missing_run_over_5")
        if not stable:
            reason.append("prior_HLC_contract_change_or_absent")
        if not valid:
            reason.append("prior_HLC_invalid_OHLC")
        isroll = day in set(rolled.effective_session_date.astype(str))
        b = aggregate(selected)
        if len(b):
            b["day"] = day
            chunks.append(b)
        audits.append({"product": product, "day": day, "year": int(day[:4]), "split": split_for(day), "expected_minutes": len(ex), "observed_minutes": len(selected), "coverage": coverage, "outside_calendar_minutes": len(g) - len(selected), "reassigned_source_minutes": int((selected.source_day != day).sum()), "max_missing_run": missingrun, "first_last_complete": firstlast, "contract": contract, "roll_session": isroll, "holiday": day in hs, "condition_degraded": condition_bad, "HLC_valid": not reason, "HLC_strict": not reason and coverage == 1, "HLC_reasons": ";".join(reason), "high": selected.high.max(), "low": selected.low.min(), "close": selected.close.iloc[-1] if len(selected) else np.nan, "full_5m": int(b.complete.sum()), "partial_5m": int((~b.complete).sum()), "main_window_minutes": int(((selected.ts >= stamp(day, 570)) & (selected.ts < stamp(day, 690))).sum())})
        expected_all.append(ex)
        # All observations on named holiday schedules are retained in features.
        # Holiday absences are treated as scheduled closures, never synthetic bars.
        feature_schedule.append(ex if day not in hs else selected.ts.to_numpy())
        if day_index % 1000 == 999:
            print(f"{product}: {day_index+1} calendar weekdays audited", flush=True)
    selected_minutes = f[f.ts.isin(np.concatenate(expected_all))].copy().reset_index(drop=True)
    bars = pd.concat(chunks, ignore_index=True).sort_values("ts").reset_index(drop=True)
    schedule = np.concatenate(feature_schedule)
    positions = np.searchsorted(schedule, bars["first"].to_numpy())
    # Unknown missing intervals between two observed bars; scheduled closures omitted.
    previous_last = np.searchsorted(schedule, bars["last"].to_numpy())
    gaps = np.r_[0, positions[1:] - previous_last[:-1] - 1]
    reset = (bars.contract != bars.contract.shift()).to_numpy() | (gaps > 5) | ~bars.valid.to_numpy()
    # A >5 minute missing run inside a bar or before it is impossible with 5m bins;
    # inter-bar runs above are counted in expected scheduled minute space.
    bars["segment"] = np.cumsum(reset)
    bars["fast"], bars["slow"], bars["atr"] = np.nan, np.nan, np.nan
    for _, group in bars.groupby("segment", sort=False):
        fast, slow, atr = indicator_segment(group.high.to_numpy(), group.low.to_numpy(), group.close.to_numpy())
        bars.loc[group.index, "fast"] = fast
        bars.loc[group.index, "slow"] = slow
        bars.loc[group.index, "atr"] = atr
    bars["preceding"] = bars.groupby("segment").cumcount()
    # Rolling prior observations only: feature-quality gating cannot read confirmation future.
    for n, name in ((250, "seed"), (500, "seed500")):
        count = bars["count"].shift().rolling(n, min_periods=n).sum()
        starts = bars["first"].shift(n).to_numpy()
        ends = bars["last"].shift().to_numpy()
        safe_starts = np.nan_to_num(starts, nan=0).astype(np.int64)
        safe_ends = np.nan_to_num(ends, nan=0).astype(np.int64)
        denom = np.searchsorted(schedule, safe_ends, side="right") - np.searchsorted(schedule, safe_starts)
        bars[name + "_coverage"] = count / np.maximum(1, denom)
        bars[name + "_valid"] = (bars.preceding >= n) & (bars[name + "_coverage"] >= .99) & (bars.atr > 0)
    bars["available_at"] = bars.ts + FIVE
    print(f"{product}: full-stream EMA/ATR features prepared without outcome labels", flush=True)
    bars["minute_NY"] = pd.to_datetime(bars.ts, utc=True).dt.tz_convert("America/New_York").dt.hour * 60 + pd.to_datetime(bars.ts, utc=True).dt.tz_convert("America/New_York").dt.minute
    bars["fast_slope"] = bars.fast - bars.groupby("segment").fast.shift(5)
    bars["slow_slope"] = bars.slow - bars.groupby("segment").slow.shift(5)
    bars["relative_volume"] = bars.volume / bars.groupby("segment").volume.transform(lambda v: v.shift().rolling(20).mean())
    audit = pd.DataFrame(audits)
    prior = audit.set_index("day")
    bar_groups = {day: g for day, g in bars.groupby("day", sort=False)}
    for row in audit.itertuples():
        pd_day = previous_weekday(row.day)
        p = prior.loc[pd_day] if pd_day in prior.index else None
        daybars = bar_groups.get(row.day, bars.iloc[:0])
        bs = daybars[daybars.minute_NY == 565]
        reasons = []
        if row.holiday:
            reasons.append("current_holiday_or_shortened")
        if row.condition_degraded:
            reasons.append("current_retrospective_source_degradation")
        if row.roll_session:
            reasons.append("roll_session")
        if p is None or not p.HLC_valid:
            reasons.append("invalid_immediately_prior_session")
        if p is not None and p.contract != row.contract:
            reasons.append("prior_contract_mismatch")
        if len(bs) != 1 or not bool(bs.iloc[0].seed_valid):
            reasons.append("prewindow_feature_unavailable")
        audit.loc[row.Index, "eligible"] = not reasons
        audit.loc[row.Index, "eligible_reasons"] = ";".join(reasons)
        audit.loc[row.Index, "prior_day"] = pd_day
        audit.loc[row.Index, "prior_coverage"] = p.coverage if p is not None else np.nan
        if p is not None:
            for key in ("high", "low", "close"):
                audit.loc[row.Index, "prior_" + key] = p[key]
        audit.loc[row.Index, "strict_prior"] = p is not None and p.HLC_strict
        main = daybars[(daybars.minute_NY >= 565) & (daybars.minute_NY < 690)]
        audit.loc[row.Index, "signal_window_complete"] = len(main) == 25 and bool(main.complete.all())
        audit.loc[row.Index, "strict_eligible"] = not reasons and bool(p.HLC_strict) and bool(bs.iloc[0].seed_coverage == 1)
        audit.loc[row.Index, "warm500_eligible"] = not reasons and bool(bs.iloc[0].seed500_valid)
        ext_start = 495 if product == "GC" else 565
        ext_end = 620 if product == "GC" else 960
        ext = daybars[(daybars.minute_NY >= ext_start) & (daybars.minute_NY < ext_end)]
        pre = daybars[daybars.minute_NY == ext_start]
        base_reasons = [r for r in reasons if r != "prewindow_feature_unavailable"]
        audit.loc[row.Index, "session_eligible"] = not base_reasons and len(pre) == 1 and bool(pre.iloc[0].seed_valid)
        audit.loc[row.Index, "session_window_complete"] = len(ext) == (ext_end - ext_start) // 5 and bool(ext.complete.all())
    audit["eligible"] = audit.eligible.astype(bool)
    save_csv(work / "tables" / f"coverage_{product}.csv", audit)
    cache = work / "private"
    cache.mkdir(exist_ok=True)
    selected_minutes[["ts", "day", "open", "high", "low", "close", "volume", "contract", "valid"]].to_parquet(cache / f"minutes_{product}.parquet", index=False)
    bars.to_parquet(cache / f"bars_{product}.parquet", index=False)
    save_json(work / f"audit_{product}.json", {"aggregation_crosscheck": check, "mapping_intervals_checked": len(master), "mapping_transitions_checked": len(rolled), "mapping_arrival_certified": False, "bad_condition_dates": sorted(bad_dates), "feature_availability": "modeled completion, not vendor arrival", "calendar_regimes": "CME notices verified; holiday rules modeled and conservative", "eligible_sessions": int(audit.eligible.sum())})
    print(f"{product}: input audit complete; {int(audit.eligible.sum()):,} eligible sessions; no strategy outcomes scored", flush=True)
    return audit
