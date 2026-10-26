"""Feature-only feasibility gate; no future outcomes or future price paths."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.features import PRODUCTS, YEARS, ANCHORS, extract_day, load_features, prior_atr, verify_pins


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    root = load_workspace_paths(workspace).publication_root
    study = workspace / "studies/06_vwap_state_dynamics"
    stage = workspace / "work/06_vwap_state_dynamics" / args.run_id
    if stage.exists():
        raise FileExistsError(stage)
    (stage / "features").mkdir(parents=True)
    lock = json.loads((study / "inputs.lock.json").read_text())
    (stage / "input-verification.json").write_text(json.dumps(verify_pins(root, lock), indent=2) + "\n")
    totals = Counter()
    year_counts = []
    for product in PRODUCTS:
        two = pd.concat([load_features(root, product, year, "2m") for year in YEARS[product]], ignore_index=True)
        atr = prior_atr(two)
        for timeframe, frame in ((2, two), (5, pd.concat([load_features(root, product, year, "5m") for year in YEARS[product]], ignore_index=True))):
            rows = []
            for day, group in frame.groupby("session_date", sort=False):
                for anchor in ANCHORS:
                    if anchor != "globex" and timeframe == 5:
                        continue  # 5m sensitivity uses Globex only, separate from local 2m replications.
                    records, counts = extract_day(group, anchor, timeframe, atr.get(day, np.nan))
                    rows.extend(records)
                    totals.update({f"{product}_{timeframe}m_{anchor}_{k}": v for k, v in counts.items()})
                    year_counts.append({"product": product, "year": day.year, "session_date": str(day),
                                        "timeframe": f"{timeframe}m", "anchor": anchor,
                                        "landmarks": len(records), **dict(counts)})
            out = pd.DataFrame(rows)
            out.to_parquet(stage / "features" / f"landmarks_{product}_{timeframe}m.parquet", index=False)
            print(product, timeframe, len(out), flush=True)
    counts = pd.DataFrame(year_counts)
    counts.to_csv(stage / "feature-coverage.csv", index=False)
    primary = pd.concat([pd.read_parquet(stage / "features" / f"landmarks_{p}_2m.parquet") for p in PRODUCTS])
    primary = primary[primary.anchor == "globex"]
    dev = primary[primary.split == "development"]
    summary = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "rule": "Feature-only gate: no future price or outcome loaded",
               "eligible_product_days": int(counts[(counts.timeframe == "2m") & (counts.anchor == "globex")].shape[0]),
               "primary_landmarks": len(primary), "primary_days_with_landmarks": int(primary[["product", "session_date"]].drop_duplicates().shape[0]),
               "primary_states": primary.state.value_counts().to_dict(),
               "development_states": dev.state.value_counts().to_dict(),
               "development_abs_price_slope_atr_quantiles": dev.price_slope_atr.abs().quantile([.1,.25,.5,.75]).to_dict(),
               "development_abs_vwap_slope_atr_quantiles": dev.vwap_slope_atr.abs().quantile([.1,.25,.5,.75]).to_dict(),
               "development_abs_vwap_twap_ticks_quantiles_by_product": {p: dev[dev["product"] == p].vwap_minus_twap_ticks.abs().quantile([.1,.25,.5,.75]).to_dict() for p in PRODUCTS},
               "development_distance_sigma_quantiles_by_product": {p: dev[dev["product"] == p].signed_distance_sigma.abs().quantile([.25,.5,.75]).to_dict() for p in PRODUCTS},
               "development_atr_quantiles_by_product": {p: dev[dev["product"] == p].prior_atr14.quantile([1/3,2/3]).to_dict() for p in PRODUCTS},
               "max_vwap_identity_error": float(primary.vwap_identity_error.abs().max()),
               "current_side_counts": primary.side.value_counts().to_dict(),
               "clock_counts": primary.clock_window.value_counts().to_dict(),
               "feature_counts": dict(totals)}
    (stage / "feature-feasibility.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
