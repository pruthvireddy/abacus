"""Execute the pinned GC outer-band excursion study into a new work stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import run_phase

import pandas as pd
from abacus_bhishma.feature_loader import load_gc_5m_release

from src.engine import analyze, summarize


COOLDOWNS = [0, 5, 10, 20, 30]
HORIZONS = [5, 10, 15, 20, 30, 50, 100]
BAR_COLUMNS = ["ts_event", "session_date", "open", "high", "low", "close",
               "raw_symbol", "price_adjustment", "source_bar_count", "is_partial_bar",
               "is_mixed_contract_bar", "is_mixed_adjustment_bar", "contains_roll"]
FEATURE_COLUMNS = ["ts_event", "available_at", "lower_outer_3sigma"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_pinned(root: Path, record: dict, columns: list[str], release: str) -> pd.DataFrame:
    path = root / record["manifest_path"]
    if sha256(path) != record["sha256"]:
        raise ValueError(f"manifest hash mismatch: {path}")
    manifest = json.loads(path.read_text())
    partitions = [x for x in manifest["output_files"] if "/product=GC/" in x["path"]]
    partitions.sort(key=lambda x: int(x["path"].split("year=")[1].split("/")[0]))
    if len(partitions) != 17:
        raise ValueError("expected 17 pinned GC partitions")
    for item in partitions:
        data_path = root / item["path"]
        if sha256(data_path) != item["sha256"]:
            raise ValueError(f"partition hash mismatch: {data_path}")
    return load_gc_5m_release(root, release, version="1.0.0", columns=columns).to_pandas()


def execute(stage: Path, study: Path, root: Path) -> None:
    lock = json.loads((study / "inputs.lock.json").read_text())
    pine = root / lock["pine_source"]["path"]
    if sha256(pine) != lock["pine_source"]["sha256"]:
        raise ValueError("Pine source hash mismatch")
    bars = load_pinned(root, lock["source_bars"], BAR_COLUMNS, "dridr_ohlcv_5m")
    bands = load_pinned(root, lock["band_features"], FEATURE_COLUMNS, "gc_ema_deviation_bands")
    ledger, cohort = analyze(bars, bands, COOLDOWNS, HORIZONS)
    if ledger.empty:
        raise ValueError("no signals found; investigate input alignment")
    stats = summarize(ledger, cohort)
    tables = stage / "tables"
    tables.mkdir()
    ledger.to_parquet(tables / "events.parquet", compression="zstd", index=False)
    cohort.to_csv(tables / "cohorts.csv", index=False, float_format="%.10f")
    stats.to_csv(tables / "yearly.csv", index=False, float_format="%.10f")
    config = {"study_id": study.name, "protocol_version": "1.0.0", "product": "GC",
              "signal": "completed_adjusted_close_lte_adjusted_lower_outer_3sigma",
              "entry": "next_complete_five_minute_bar_unadjusted_open",
              "cooldown_bars": COOLDOWNS, "horizons_bars": HORIZONS,
              "year_basis": "signal_bar_close_America/New_York",
              "price_units": "GC points", "tick_size": 0.1,
              "require_contiguous_complete_single_contract_and_adjustment": True,
              "source_snapshot_is_point_in_time_certified": False,
              "study_yaml_sha256": sha256(study / "study.yaml"),
              "plan_sha256": sha256(study / "plan.md")}
    (stage / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    (stage / "inputs.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    statuses = {k: int(v) for k, v in ledger.status.value_counts().items()}
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "input_bar_rows": len(bars), "input_band_rows": len(bands),
               "observed_years": sorted(map(int, stats.year.unique())),
               "cohort_horizon_rows": len(ledger),
               "status_counts_across_cooldowns_and_horizons": statuses,
               "statistic_rows": len(stats),
               "definitions": {"mae_points": "max(0, next open - min future low)",
                               "mfe_points": "max(0, max future high - next open)",
                               "terminal_points": "last future close - next open",
                               "mean_ci": "approximate 95% normal cluster interval by ISO week; unadjusted for multiple comparisons"}}
    (stage / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"stage": str(stage), "rows": len(bars),
                      "signals_c0": int(cohort.loc[cohort.cooldown == 0, "accepted_signals"].sum()),
                      "ledger_rows": len(ledger), "valid": statuses.get("valid", 0)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    study = Path(__file__).resolve().parent
    root = study.parents[1]
    run_phase(root, study.name, args.stage, "execution",
              lambda: execute(args.stage.absolute(), study, root))


if __name__ == "__main__":
    main()
