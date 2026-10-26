"""Independent full-series VWAP identity and deterministic real-path audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.features import ANCHORS, PRODUCTS, YEARS, SCALE, load_features
from src.outcomes import load_source_year


def identity(frame: pd.DataFrame) -> tuple[int, float]:
    checked = 0
    maximum = 0.
    for _, day in frame.groupby("session_date", sort=False):
        price = (day.high.to_numpy(dtype=float) + day.low.to_numpy(dtype=float) +
                 day.close.to_numpy(dtype=float)) * SCALE / 3
        volume = day.volume.to_numpy(dtype=float)
        for anchor in ANCHORS:
            active = day[f"{anchor}_anchor_active"].to_numpy(dtype=bool)
            if not active.any():
                continue
            p, v = price[active], volume[active]
            cumulative = np.cumsum(v)
            predicted = np.divide(np.cumsum(p*v), cumulative, out=np.full(len(p), np.nan), where=cumulative>0)
            published = day.loc[active, f"{anchor}_vwap"].to_numpy(dtype=float)
            use = np.isfinite(predicted) & np.isfinite(published)
            if use.any():
                error = float(np.max(np.abs(predicted[use]-published[use])))
                maximum = max(maximum,error)
                checked += int(use.sum())
                if error > 2e-6:
                    raise ValueError(f"full VWAP identity failed: {anchor} {day.session_date.iloc[0]} {error}")
    return checked, maximum


def independent_barrier(path: pd.DataFrame, side: int, ticks: int, tick: float) -> str:
    if side == 0:
        return "unavailable"
    reference = path.open.iloc[0]*SCALE
    favorable = reference + side*ticks*tick
    adverse = reference - side*ticks*tick
    for _, bar in path.iterrows():
        opening = bar["open"]*SCALE
        if side*(opening-favorable) >= -1e-8:
            return "favorable"
        if side*(opening-adverse) <= 1e-8:
            return "adverse"
        far = (bar["high"] if side > 0 else bar["low"])*SCALE
        near = (bar["low"] if side > 0 else bar["high"])*SCALE
        a = side*(far-favorable) >= -1e-8
        b = side*(near-adverse) <= 1e-8
        if a and b:
            return "ambiguous"
        if a:
            return "favorable"
        if b:
            return "adverse"
    return "neither"


def audit_example(event: pd.Series, feature: pd.DataFrame, source: pd.DataFrame) -> dict:
    t = event.landmark_ts
    s = source[(source.ts_event >= t) & (source.ts_event < t+pd.Timedelta(minutes=30))]
    if len(s) != 30 or not (s.ts_event.diff().iloc[1:] == pd.Timedelta(minutes=1)).all():
        raise ValueError(f"example source path gap: {event.event_id}")
    i = int(event.feature_index)
    f = feature.iloc[i+1:i+16]
    adjustment = event.price_adjustment*SCALE
    closes = s.close.to_numpy(dtype=float)[1::2]*SCALE
    if not np.allclose(closes, f.close.to_numpy(dtype=float)*SCALE-adjustment, atol=1e-8, rtol=0):
        raise ValueError(f"example feature/source close mismatch: {event.event_id}")
    vwap = f.globex_vwap.to_numpy(dtype=float)-adjustment
    side = int(event.side)
    crossed = np.flatnonzero(side*(closes-vwap) < -1e-8)
    y2 = bool(len(crossed))
    if bool(event.y2_cross) != y2 or bool(event.y1_residence) == y2:
        raise ValueError(f"example crossing mismatch: {event.event_id}")
    first = (int(crossed[0])+1)*2 if len(crossed) else None
    stored = None if pd.isna(event.first_cross_minute) else int(event.first_cross_minute)
    if first != stored:
        raise ValueError(f"example first crossing mismatch: {event.event_id}")
    fixed = independent_barrier(s, side, 8, float(event.tick))
    half = independent_barrier(s, side, int(event.half_sigma_ticks), float(event.tick))
    if fixed != event.barrier_8tick or half != event.barrier_half_sigma:
        raise ValueError(f"example barrier mismatch: {event.event_id}")
    target = float(np.median(s.close.to_numpy(dtype=float)*SCALE))
    if abs(target-event.future_median) > 1e-8:
        raise ValueError(f"example median mismatch: {event.event_id}")
    v_err = abs(target-(event.vwap-adjustment))
    t_err = abs(target-(event.twap-adjustment))
    if abs(v_err-event.vwap_error) > 1e-8 or abs(t_err-event.twap_error) > 1e-8:
        raise ValueError(f"example paired error mismatch: {event.event_id}")
    return {"event_id": event.event_id, "product": event["product"], "session_date": event.session_date,
            "y2_cross": y2, "first_cross_minute": first, "fixed_8tick": fixed,
            "half_sigma": half, "future_median": target, "vwap_error": v_err, "twap_error": t_err}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    root = load_workspace_paths(workspace).publication_root
    stage = workspace / "work/06_vwap_state_dynamics" / args.run_id
    examples = pd.read_csv(stage / "tables/examples.csv")
    example_ids = set(examples.event_id)
    example_checks = []
    identity_rows = []
    for product in PRODUCTS:
        for year in YEARS[product]:
            source = None
            for timeframe in ("2m", "5m"):
                feature = load_features(root, product, year, timeframe)
                count, error = identity(feature)
                identity_rows.append({"product": product, "year": year, "timeframe": timeframe,
                                      "active_bars_checked": count, "max_abs_vwap_error": error})
                if timeframe != "2m":
                    continue
                selected = examples[(examples["product"] == product) & (examples.event_id.str.contains(f":{year}-"))]
                if selected.empty:
                    continue
                source = load_source_year(root, product, year)
                events = pd.read_parquet(stage / "events" / f"events_{product}_2m_{year}.parquet")
                by_day_f = {str(day): group.reset_index(drop=True) for day,group in feature.groupby("session_date", sort=False)}
                by_day_s = {str(day): group.reset_index(drop=True) for day,group in source.groupby("session_date", sort=False)}
                for event_id in selected.event_id.unique():
                    event = events[events.event_id == event_id].iloc[0]
                    example_checks.append(audit_example(event, by_day_f[event.session_date], by_day_s[event.session_date]))
                    example_ids.remove(event_id)
    if example_ids:
        raise ValueError(f"missing example IDs: {sorted(example_ids)[:3]}")
    (stage / "tables/example-audit.csv").write_text(pd.DataFrame(example_checks).to_csv(index=False))
    result = {"full_series_active_bars_checked": int(sum(x["active_bars_checked"] for x in identity_rows)),
              "max_abs_vwap_error": max(x["max_abs_vwap_error"] for x in identity_rows),
              "representative_examples_checked": len(example_checks),
              "identity_by_partition": identity_rows}
    (stage / "numerical-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "identity_by_partition"}))


if __name__ == "__main__":
    main()
