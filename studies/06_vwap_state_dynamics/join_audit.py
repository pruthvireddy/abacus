"""Feature-only one-minute key and coverage audit; no future OHLC is loaded."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from abacus_bhishma.continuous_loader import open_continuous_dataset
from abacus_bhishma.paths import load_workspace_paths
from src.features import PRODUCTS, YEARS


def audit_year(root: Path, product: str, year: int, frame: pd.DataFrame) -> dict:
    dataset = open_continuous_dataset(root, product)
    filt = ((pc.field("session_date") >= pa.scalar(pd.Timestamp(year, 1, 1).date(), pa.date32())) &
            (pc.field("session_date") < pa.scalar(pd.Timestamp(year + 1, 1, 1).date(), pa.date32())))
    source = dataset.to_table(columns=["ts_event", "session_date", "instrument_id", "raw_symbol"], filter=filt).to_pandas()
    source = source.sort_values("ts_event").reset_index(drop=True)
    times = source.ts_event.astype("int64").to_numpy()
    landmarks = frame.landmark_ts.astype("int64").to_numpy()
    pos = np.searchsorted(times, landmarks)
    valid = pos + 29 < len(source)
    capped = np.minimum(pos, max(0, len(source)-1))
    end = np.minimum(pos+29, max(0, len(source)-1))
    if len(source):
        valid &= (times[capped] == landmarks)
        valid &= (times[end] == landmarks + 29 * 60 * 1_000_000_000)
        gaps = np.zeros(len(source), dtype=int)
        gaps[1:] = np.diff(times) != 60 * 1_000_000_000
        cum = np.cumsum(gaps)
        valid &= cum[end] == cum[capped]
        valid &= source.instrument_id.to_numpy()[capped] == frame.instrument_id.to_numpy()
        valid &= source.instrument_id.to_numpy()[end] == frame.instrument_id.to_numpy()
        valid &= source.raw_symbol.to_numpy()[capped] == frame.raw_symbol.to_numpy()
        valid &= source.raw_symbol.to_numpy()[end] == frame.raw_symbol.to_numpy()
        valid &= source.session_date.to_numpy()[capped] == frame.session_date.map(pd.Timestamp).dt.date.to_numpy()
        valid &= source.session_date.to_numpy()[end] == frame.session_date.map(pd.Timestamp).dt.date.to_numpy()
    else:
        valid[:] = False
    return {"product": product, "year": year, "landmarks": len(frame),
            "source_30m_key_capable": int(valid.sum()),
            "source_30m_key_missing_or_discontinuous": int((~valid).sum()),
            "by_view": frame.assign(key_capable=valid).groupby(["timeframe", "anchor"]).key_capable.agg(["sum", "count"]).reset_index().to_dict("records")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    root = load_workspace_paths(workspace).publication_root
    stage = workspace / "work/06_vwap_state_dynamics" / args.run_id
    results = []
    for product in PRODUCTS:
        frame = pd.concat([pd.read_parquet(stage / "features" / f"landmarks_{product}_{tf}.parquet") for tf in ("2m", "5m")], ignore_index=True)
        for year in YEARS[product]:
            subset = frame[frame.year == year]
            results.append(audit_year(root, product, year, subset))
    (stage / "feature-source-key-audit.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"landmarks": sum(x["landmarks"] for x in results),
                      "key_capable": sum(x["source_30m_key_capable"] for x in results)}))


if __name__ == "__main__":
    main()
