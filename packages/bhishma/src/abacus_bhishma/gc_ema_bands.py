"""Publish the causal five-minute GC EMA deviation-band feature release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import provenance as _provenance
from .provenance import sha256_file as sha256
from .publication_safety import check_absent, check_path, write_new_bytes


SOURCE_ID = "tv_indicators__dridr_ohlcv_5m__v1"
DATASET_ID = "gc_ema_deviation_bands__1.0.0"
FEATURE_SET = "gc_ema_deviation_bands"
VERSION = "1.0.0"
PRICE_SCALE = 1e-9


def band_values(close: np.ndarray, length: int = 225, multiplier: float = 3.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pine-compatible seeded EMA and biased rolling residual dispersion."""
    close = np.asarray(close, dtype=np.float64)
    if close.ndim != 1 or not len(close) or not np.isfinite(close).all():
        raise ValueError("close must be a nonempty finite one-dimensional array")
    if length < 2 or multiplier <= 0:
        raise ValueError("invalid band parameters")
    ema = pd.Series(close).ewm(alpha=2.0 / (length + 1), adjust=False).mean().to_numpy()
    residual = close - ema
    sigma = pd.Series(residual).rolling(length, min_periods=length).std(ddof=0).to_numpy()
    lower = ema - multiplier * sigma
    return ema, sigma, lower


def publish(root: Path) -> Path:
    root = root.resolve()
    manifest_path = root / "catalog/datasets" / f"{SOURCE_ID}.json"
    request_path = root / "requests/inbox" / f"{DATASET_ID}.yaml"
    pine_path = root / "catalog/indicators/gc_hac_levels_bands__20260925.pine"
    output = root / "data/features/bars/5m" / f"feature_set={FEATURE_SET}" / f"version={VERSION}"
    stage = root / "work/bhishma" / DATASET_ID
    catalog = root / "catalog/datasets" / f"{DATASET_ID}.json"
    indicator = root / "catalog/indicators" / f"{DATASET_ID}.json"
    quality = root / "reports/quality" / f"{DATASET_ID}.md"
    metadata = (catalog, indicator, quality)
    for path in (output, stage, *metadata, *(p.with_name(p.name + ".part") for p in metadata)):
        check_absent(path, root)
    source = json.loads(manifest_path.read_text())
    records = [x for x in source["output_files"] if "/product=GC/" in x["path"]]
    records.sort(key=lambda x: int(x["path"].split("year=")[1].split("/")[0]))
    if len(records) != 17:
        raise ValueError("expected 17 pinned GC year partitions")
    frames = []
    source_hashes = []
    for record in records:
        path = root / record["path"]
        if sha256(path) != record["sha256"]:
            raise ValueError(f"source hash mismatch: {path}")
        frame = pq.read_table(path, columns=["ts_event", "session_date", "close"]).to_pandas()
        if not frame.ts_event.is_monotonic_increasing:
            raise ValueError(f"source timestamps out of order: {path}")
        frame["year"] = int(record["path"].split("year=")[1].split("/")[0])
        frames.append(frame)
        source_hashes.append({"path": record["path"], "sha256": record["sha256"]})
    data = pd.concat(frames, ignore_index=True)
    if data.ts_event.duplicated().any() or not data.ts_event.is_monotonic_increasing:
        raise ValueError("GC source timestamps must be unique and ordered")
    ema, sigma, lower = band_values(data.close.to_numpy() * PRICE_SCALE)
    data["ema_base_225"] = ema
    data["residual_sigma_225"] = sigma
    data["lower_outer_3sigma"] = lower
    data["available_at"] = data.ts_event + pd.Timedelta(minutes=5)
    check_absent(stage, root)
    stage.mkdir(parents=True)
    declared_sources = _provenance.publication_sources(Path(__file__), ("provenance.py", "publication_safety.py", "paths.py"))
    retained = _provenance.retain_sources(
        stage / "provenance",
        declared_sources,
        artifact_id=DATASET_ID, root=root,
    )
    outputs = []
    for year, group in data.groupby("year", sort=True):
        target = stage / "product=GC" / f"year={year}" / "part-000.parquet"
        target.parent.mkdir(parents=True)
        table = pa.Table.from_pandas(group[["ts_event", "session_date", "available_at", "ema_base_225", "residual_sigma_225", "lower_outer_3sigma"]], preserve_index=False)
        pq.write_table(table, target, compression="zstd")
        outputs.append({"path": str((output / "product=GC" / f"year={year}" / "part-000.parquet").relative_to(root)),
                        "sha256": sha256(target), "bytes": target.stat().st_size,
                        "rows": len(group), "year": int(year)})
    if sum(x["rows"] for x in outputs) != len(data) or np.count_nonzero(np.isfinite(lower)) != len(data) - 224:
        raise ValueError("release row or warm-up count mismatch")
    _provenance.verify_retained_sources(stage / "provenance", declared_sources, retained)
    for path in (output, *metadata, *(p.with_name(p.name + ".part") for p in metadata)):
        check_absent(path, root)
    check_path(stage, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage.rename(output)
    payload = {
        "dataset_id": DATASET_ID, "feature_set": FEATURE_SET, "version": VERSION,
        "source_dataset_id": SOURCE_ID,
        "source_manifest": {"path": str(manifest_path.relative_to(root)), "sha256": sha256(manifest_path)},
        "source_partitions": source_hashes,
        "request": {"path": str(request_path.relative_to(root)), "sha256": sha256(request_path)},
        "indicator_source": {"path": str(pine_path.relative_to(root)), "sha256": sha256(pine_path)},
        "formula": "EMA225 seeded first close; population STDEV225(close-EMA225); lower=EMA225-3*sigma",
        "timestamp_label": "bar_open_utc", "available_at": "bar_open_plus_five_minutes",
        "price_units": "GC points", "point_in_time_certified": False,
        "rows": len(data), "warmup_null_rows": 224,
        "coverage_start": data.ts_event.iloc[0].isoformat(),
        "coverage_end": data.ts_event.iloc[-1].isoformat(),
        "output_files": outputs,
        "retained_provenance": dict(retained, path=str((output / "provenance").relative_to(root))),
        "limitations": ["Final backward-adjusted continuous snapshot incorporates later roll information.",
                        "Volume-led continuous series is not guaranteed to match TradingView's GC chart.",
                        "Absent source bars are not filled; partial source bars remain present and flagged in the source release."],
    }
    write_new_bytes(catalog, (json.dumps(payload, indent=2) + "\n").encode(), root)
    write_new_bytes(indicator, (json.dumps({"name": "GC HAC EMA deviation bands", "version": VERSION,
                                     "pine_source": payload["indicator_source"],
                                     "feature_manifest": {"path": str(catalog.relative_to(root)), "sha256": sha256(catalog)},
                                     "parameters": {"ema_length": 225, "residual_lookback": 225, "outer_sigma": 3.0}}, indent=2) + "\n").encode(), root)
    write_new_bytes(quality, (f"# GC EMA deviation bands {VERSION}\n\n"
                       f"Validated {len(data):,} rows across {len(outputs)} GC year partitions. "
                       f"The first 224 bands are null. All source partition hashes matched the pinned source manifest. "
                       f"Output partitions are checksummed in [the release manifest](../../catalog/datasets/{DATASET_ID}.json).\n\n"
                       "The final adjusted snapshot is retrospective and may differ from TradingView. "
                       "No missing bars were filled.\n").encode(), root)
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(publish(args.root))


if __name__ == "__main__":
    main()
