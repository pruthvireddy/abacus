"""Feature-only feasibility gate.  No future one-minute paths are opened."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.features import (
    ANCHORS, LOCAL_ANCHORS, PRODUCTS, YEARS, extract_corridor_candidates,
    extract_departure_landmarks, load_features, prior_atr, select_corridor_events,
    verify_pins,
)


def quantiles(series: pd.Series, probabilities=(.1, .25, .5, .75, .9)) -> dict:
    clean = series.dropna()
    return {str(p): float(v) for p, v in clean.quantile(probabilities).items()} if len(clean) else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    publication_root = load_workspace_paths(workspace).publication_root
    study = workspace / "studies/11_vwap_conditional_probabilities"
    stage = workspace / "work/11_vwap_conditional_probabilities" / args.run_id
    if stage.exists():
        raise FileExistsError(stage)
    (stage / "features").mkdir(parents=True)
    lock = json.loads((study / "inputs.lock.json").read_text())
    verification = verify_pins(publication_root, lock)
    (stage / "input-verification.json").write_text(json.dumps(verification, indent=2) + "\n")

    coverage_rows: list[dict] = []
    atr_rows: list[dict] = []
    all_ab: list[pd.DataFrame] = []
    all_corridors: list[pd.DataFrame] = []
    totals: Counter = Counter()
    for product in PRODUCTS:
        two = pd.concat(
            [load_features(publication_root, product, year, "2m") for year in YEARS[product]],
            ignore_index=True,
        )
        atr_by_day = prior_atr(two)
        for session_day, value in atr_by_day.items():
            atr_rows.append({"product": product, "session_date": str(session_day),
                             "year": session_day.year, "prior_atr14": value})
        for timeframe, frame in (
            (2, two),
            (5, pd.concat(
                [load_features(publication_root, product, year, "5m") for year in YEARS[product]],
                ignore_index=True,
            )),
        ):
            ab_rows: list[dict] = []
            corridor_rows: list[dict] = []
            for session_day, day in frame.groupby("session_date", sort=False):
                atr = atr_by_day.get(session_day, np.nan)
                ab_anchors = ANCHORS if timeframe == 2 else ("globex",)
                for anchor in ab_anchors:
                    records, counts = extract_departure_landmarks(day, anchor, timeframe, atr)
                    ab_rows.extend(records)
                    coverage_rows.append({"domain": "AB", "product": product,
                                          "session_date": str(session_day),
                                          "timeframe": f"{timeframe}m", "anchor": anchor,
                                          "rows": len(records), **dict(counts)})
                    totals.update({f"AB_{product}_{timeframe}m_{anchor}_{key}": value
                                   for key, value in counts.items()})
                for anchor in LOCAL_ANCHORS:
                    records, counts = extract_corridor_candidates(day, anchor, timeframe, atr)
                    corridor_rows.extend(records)
                    coverage_rows.append({"domain": "C", "product": product,
                                          "session_date": str(session_day),
                                          "timeframe": f"{timeframe}m", "anchor": anchor,
                                          "rows": len(records), **dict(counts)})
                    totals.update({f"C_{product}_{timeframe}m_{anchor}_{key}": value
                                   for key, value in counts.items()})
            ab = pd.DataFrame(ab_rows)
            corridors = pd.DataFrame(corridor_rows)
            ab.to_parquet(stage / "features" / f"landmarks_ab_{product}_{timeframe}m.parquet", index=False)
            corridors.to_parquet(stage / "features" / f"candidates_c_{product}_{timeframe}m.parquet", index=False)
            all_ab.append(ab)
            all_corridors.append(corridors)
            print(json.dumps({"product": product, "timeframe": f"{timeframe}m",
                              "ab_checkpoints": len(ab), "corridor_candidates": len(corridors)}), flush=True)

    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(stage / "feature-coverage.csv", index=False)
    atr_frame = pd.DataFrame(atr_rows)
    atr_frame.to_csv(stage / "prior-atr.csv", index=False)
    ab_all = pd.concat(all_ab, ignore_index=True)
    c_all = pd.concat(all_corridors, ignore_index=True)
    primary_ab = ab_all[ab_all.timeframe == "2m"].copy()
    primary_c = c_all[c_all.timeframe == "2m"].copy()
    development_ab = primary_ab[primary_ab.split == "development"]
    development_c = primary_c[primary_c.split == "development"]
    development_atr = atr_frame[(atr_frame.year <= 2023) & atr_frame.prior_atr14.notna()]

    support_rows = []
    for tick_floor in (4, 8, 12, 16):
        for sigma_floor in (0., .10, .25, .50):
            selected, suppressed = select_corridor_events(primary_c, tick_floor, sigma_floor)
            for product in ("ALL", *PRODUCTS):
                for anchor in ("ALL", *LOCAL_ANCHORS):
                    part = selected
                    if product != "ALL":
                        part = part[part["product"] == product]
                    if anchor != "ALL":
                        part = part[part.session_anchor == anchor]
                    support_rows.append({
                        "min_ticks": tick_floor, "min_day_sigma": sigma_floor,
                        "product": product, "session_anchor": anchor,
                        "events": len(part),
                        "product_sessions": int(part[["product", "session_date"]].drop_duplicates().shape[0]),
                        "shared_dates": int(part.session_date.nunique()),
                        "suppressed_all_products_anchors": suppressed,
                    })
    support = pd.DataFrame(support_rows)
    support.to_csv(stage / "corridor-threshold-support.csv", index=False)

    atr_terciles = {
        product: [float(x) for x in development_atr[development_atr["product"] == product]
                  .prior_atr14.quantile([1 / 3, 2 / 3]).to_numpy()]
        for product in PRODUCTS
    }
    feasibility = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule": "Feature-only gate: no future price path or target outcome was opened.",
        "release_id": "session_anchored_vwap__1.0.0",
        "primary_ab_checkpoints": int(len(primary_ab)),
        "primary_ab_episodes": int(primary_ab.episode_id.nunique()),
        "primary_ab_product_sessions": int(primary_ab[["product", "session_date"]].drop_duplicates().shape[0]),
        "primary_corridor_base_candidates": int(len(primary_c)),
        "primary_corridor_product_sessions": int(primary_c[["product", "session_date"]].drop_duplicates().shape[0]),
        "five_minute_ab_checkpoints": int((ab_all.timeframe == "5m").sum()),
        "five_minute_corridor_candidates": int((c_all.timeframe == "5m").sum()),
        "development_ab_distance_sigma_quantiles": quantiles(development_ab.absolute_distance_sigma),
        "development_ab_elapsed_minutes_quantiles": quantiles(development_ab.elapsed_without_return_minutes),
        "development_ab_max_excursion_sigma_quantiles": quantiles(development_ab.max_excursion_sigma),
        "development_ab_context_available_fraction": float(development_ab.context_available.mean()) if len(development_ab) else None,
        "development_corridor_width_ticks_quantiles_by_product": {
            product: quantiles(development_c[development_c["product"] == product].corridor_width_ticks)
            for product in PRODUCTS
        },
        "development_corridor_width_day_sigma_quantiles_by_product": {
            product: quantiles(development_c[development_c["product"] == product].corridor_width_day_sigma)
            for product in PRODUCTS
        },
        "development_corridor_position_quantiles": quantiles(development_c.position_from_day),
        "development_corridor_slope_context_fraction": float(development_c.slope_context_available.mean()) if len(development_c) else None,
        "development_prior_atr14_terciles": atr_terciles,
        "feature_counts": dict(totals),
        "threshold_support_table": "corridor-threshold-support.csv",
    }
    (stage / "feature-feasibility.json").write_text(json.dumps(feasibility, indent=2) + "\n")
    print(json.dumps({key: feasibility[key] for key in (
        "primary_ab_checkpoints", "primary_ab_episodes", "primary_corridor_base_candidates",
        "five_minute_ab_checkpoints", "five_minute_corridor_candidates")}, indent=2))


if __name__ == "__main__":
    main()

