"""Check staged evidence, including an independent source-bar spot recount."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import run_phase

import numpy as np
import pandas as pd

from run import BAR_COLUMNS, load_pinned


def verify(stage: Path) -> dict:
    if sys.flags.optimize:
        raise ValueError("Study 12 scientific verification requires ordinary Python")
    root = Path(__file__).resolve().parents[2]
    lock = json.loads((stage / "inputs.lock.json").read_text())
    ledger = pd.read_parquet(stage / "tables/events.parquet")
    cohorts = pd.read_csv(stage / "tables/cohorts.csv")
    yearly = pd.read_csv(stage / "tables/yearly.csv")
    assert len(yearly) == 17 * 5 * 7
    assert len(ledger) == int(cohorts.accepted_signals.sum()) * 7
    assert set(yearly.year) == set(range(2010, 2027))
    assert set(yearly.cooldown) == {0, 5, 10, 20, 30}
    assert set(yearly.horizon) == {5, 10, 15, 20, 30, 50, 100}
    for _, row in yearly.iterrows():
        excluded = sum(int(row[name]) for name in (
            "insufficient_future_bars", "time_gap", "partial_or_mixed_bar",
            "contract_change", "adjustment_change"))
        assert int(row.valid_n) + excluded == int(row.accepted_signals)
    for cooldown in (0, 5, 10, 20, 30):
        signals = ledger.loc[(ledger.cooldown == cooldown) & (ledger.horizon == 5), "signal_ts_utc"]
        assert signals.is_unique
        assert signals.is_monotonic_increasing
    bars = load_pinned(root, lock["source_bars"], BAR_COLUMNS, "dridr_ohlcv_5m")
    lookup = pd.Series(np.arange(len(bars)), index=bars.ts_event.astype(str))
    valid = ledger.loc[ledger.status == "valid"]
    sample = valid.iloc[np.linspace(0, len(valid) - 1, 31, dtype=int)]
    for row in sample.itertuples():
        signal = pd.Timestamp(row.signal_ts_utc)
        index = int(lookup.loc[str(signal)])
        following = bars.iloc[index + 1:index + row.horizon + 1]
        adj = float(bars.price_adjustment.iloc[index])
        entry = (float(following.open.iloc[0]) - adj) * 1e-9
        lows = (following.low.to_numpy(dtype=float) - adj) * 1e-9
        highs = (following.high.to_numpy(dtype=float) - adj) * 1e-9
        terminal = (float(following.close.iloc[-1]) - adj) * 1e-9 - entry
        np.testing.assert_allclose([row.entry_unadjusted, row.mae_points, row.mfe_points, row.terminal_points],
                                   [entry, max(0., entry - lows.min()), max(0., highs.max() - entry), terminal],
                                   atol=1e-8, rtol=0)
    return {"status": "pass", "statistic_cells": len(yearly),
            "cohort_horizon_rows": len(ledger), "source_recounted_events": len(sample),
            "checks": ["complete 17x5x7 grid", "cohort and exclusion accounting",
                       "unique ordered signal timestamps", "31 independent unadjusted source-bar path recounts"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    study = Path(__file__).resolve().parent
    result = run_phase(study.parents[1], study.name, args.stage, "verification",
                       lambda: verify(args.stage.absolute()))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
