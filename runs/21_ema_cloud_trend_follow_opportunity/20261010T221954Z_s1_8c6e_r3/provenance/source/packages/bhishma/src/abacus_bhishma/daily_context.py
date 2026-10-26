"""Publish and read immutable TradingView daily context snapshots.

The exported indicator values are passed through, not recalculated. Completed
bars become available at their exported bar-close timestamp. This is a snapshot
of chart exports, not a point-in-time history of later revisions.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .paths import resolve_publication_root
from . import provenance as _provenance
from .provenance import sha256_file as _sha256
from .publication_safety import check_absent, check_path, write_new_bytes

DATASET_ID = "tradingview_daily_context__1.0.0"
VERSION = "1.0.0"
FEATURE_SET = "tradingview_daily_context"
SOURCE_FILES = {
    "XAUUSD": ("OANDA_XAUUSD, 1D_f22ba.csv", "OANDA:XAUUSD", "spot gold"),
    "SI": ("COMEX_SI1!, 1D_b3290.csv", "COMEX:SI1!", "continuous silver futures"),
    "CL": ("NYMEX_CL1!, 1D_5ccb5.csv", "NYMEX:CL1!", "continuous crude oil futures"),
    "GC": ("COMEX_GC1!, 1D_98abc.csv", "COMEX:GC1!", "continuous gold futures"),
    "ES": ("CME_MINI_ES1!, 1D_2a487.csv", "CME_MINI:ES1!", "continuous E-mini S&P 500 futures"),
    "NQ": ("CME_MINI_NQ1!, 1D_78788.csv", "CME_MINI:NQ1!", "continuous E-mini Nasdaq-100 futures"),
    "GVZ": ("CBOE_DLY_GVZ, 1D_97b48.csv", "CBOE_DLY:GVZ", "gold volatility index"),
    "VIX": ("TVC_VIX, 1D_78d2e.csv", "TVC:VIX", "S&P 500 volatility index"),
    "VXN": ("CBOE_DLY_VXN, 1D_24419.csv", "CBOE_DLY:VXN", "Nasdaq-100 volatility index"),
}
SOURCE_COLUMNS = (
    "time", "open", "high", "low", "close", "ema20", "ema50", "sma200",
    "bb20_mid", "bb20_upper_2sd", "bb20_lower_2sd", "atr14", "atr14_pct",
    "rsi14", "adx14", "plus_di14", "minus_di14", "bb20_percent_b",
    "bb20_bandwidth_pct", "donchian20_prior_high", "donchian20_prior_low",
    "donchian55_prior_high", "donchian55_prior_low", "rv5_annualized_pct",
    "rv20_annualized_pct", "rv5_rv20_ratio", "roc5_pct", "roc20_pct",
    "roc60_pct", "volume_raw", "volume_prior20_mean", "rvol20_prior",
    "macd_12_26", "macd_signal9", "macd_hist", "macd_hist_atr14",
    "dist_ema20_atr", "dist_ema50_atr", "dist_sma200_atr",
    "ema20_slope5_atr", "bar_confirmed", "warmup1000_complete", "is_1d",
    "bar_open_unix_s", "bar_close_unix_s", "trading_day_utc_unix_s", "Volume",
)
INTEGER_COLUMNS = {"time", "bar_open_unix_s", "bar_close_unix_s", "trading_day_utc_unix_s"}
BOOLEAN_COLUMNS = {"bar_confirmed", "warmup1000_complete", "is_1d"}
DAY_SECONDS = 86_400


def _day(seconds: int) -> date:
    return datetime.fromtimestamp(seconds, timezone.utc).date()


def output_schema() -> pa.Schema:
    fields = [
        pa.field("asset", pa.string(), False),
        pa.field("source_symbol", pa.string(), False),
        pa.field("trading_day", pa.date32(), False),
        pa.field("available_at", pa.timestamp("s", tz="UTC"), False),
    ]
    for name in SOURCE_COLUMNS:
        data_type = (
            pa.int64() if name in INTEGER_COLUMNS else
            pa.bool_() if name in BOOLEAN_COLUMNS else pa.float64()
        )
        fields.append(pa.field(name, data_type, name not in INTEGER_COLUMNS | BOOLEAN_COLUMNS))
    return pa.schema(fields, metadata={
        b"dataset_id": DATASET_ID.encode(),
        b"version": VERSION.encode(),
        b"timeframe": b"1d",
        b"available_at_semantics": b"exported bar_close_unix_s; completed bars only",
        b"indicator_provenance": b"source supplied; formulas not independently verified",
    })


def _parse_source(path: Path, asset: str, symbol: str) -> tuple[pa.Table, dict]:
    output: list[dict] = []
    raw_count = 0
    unconfirmed = 0
    last_open = None
    last_close = None
    seen_days: set[int] = set()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
            raise ValueError(f"unexpected columns in {path}")
        for line, source in enumerate(reader, 2):
            raw_count += 1
            if None in source or any(value is None for value in source.values()):
                raise ValueError(f"malformed CSV row {line} in {path}")
            if source["bar_confirmed"] not in {"0", "1"}:
                raise ValueError(f"invalid confirmation flag at {path}:{line}")
            opened = int(source["bar_open_unix_s"])
            closed = int(source["bar_close_unix_s"])
            day_seconds = int(source["trading_day_utc_unix_s"])
            if (
                opened != int(source["time"]) or closed <= opened or
                day_seconds % DAY_SECONDS or source["is_1d"] != "1" or
                (last_open is not None and opened <= last_open) or
                (last_close is not None and closed <= last_close) or
                day_seconds in seen_days
            ):
                raise ValueError(f"invalid bar identity at {path}:{line}")
            last_open = opened
            last_close = closed
            seen_days.add(day_seconds)
            if source["bar_confirmed"] == "0":
                unconfirmed += 1
                continue
            if unconfirmed:
                raise ValueError(f"confirmed bar after unconfirmed bar at {path}:{line}")
            row = {
                "asset": asset,
                "source_symbol": symbol,
                "trading_day": _day(day_seconds),
                "available_at": datetime.fromtimestamp(closed, timezone.utc),
            }
            for name in SOURCE_COLUMNS:
                value = source[name]
                if name in INTEGER_COLUMNS:
                    row[name] = int(value)
                elif name in BOOLEAN_COLUMNS:
                    if value not in {"0", "1"}:
                        raise ValueError(f"invalid boolean {name} at {path}:{line}")
                    row[name] = value == "1"
                else:
                    number = float(value) if value else None
                    if number is not None and not math.isfinite(number):
                        raise ValueError(f"nonfinite value {name} at {path}:{line}")
                    row[name] = number
            output.append(row)
    if not output:
        raise ValueError(f"no completed bars in {path}")
    table = pa.Table.from_pylist(output, schema=output_schema())
    return table, {
        "raw_rows": raw_count,
        "published_rows": len(output),
        "excluded_unconfirmed_rows": unconfirmed,
        "first_trading_day": output[0]["trading_day"].isoformat(),
        "last_completed_trading_day": output[-1]["trading_day"].isoformat(),
        "null_counts": {name: table[name].null_count for name in SOURCE_COLUMNS if table[name].null_count},
    }


def publish_daily_context(input_dir: Path | str, project_root: Path | str) -> Path:
    """Publish nine exact raw CSV copies and one immutable Parquet per asset."""
    source_dir = Path(input_dir)
    root = Path(project_root).resolve()
    feature_root = root / f"data/features/bars/1d/feature_set={FEATURE_SET}/version={VERSION}"
    manifest_path = root / "catalog/datasets" / f"{DATASET_ID}.json"
    schema_path = root / "catalog/schemas" / f"{DATASET_ID}.json"
    metadata = (manifest_path, schema_path)
    for path in (feature_root, *metadata, *(p.with_name(p.name + ".part") for p in metadata)):
        check_absent(path, root)
    raw_parent = root / "data/raw/tradingview/chart_exports/1d"
    check_path(raw_parent, root, directory=True)
    sources = {asset: source_dir / filename for asset, (filename, _, _) in SOURCE_FILES.items()}
    for path in sources.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hashes = {asset: _sha256(path) for asset, path in sources.items()}
    batch_hash = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()[:12]
    batch_id = f"{datetime.now(timezone.utc):%Y%m%d}-{batch_hash}"
    raw_root = raw_parent / batch_id
    temp_feature = feature_root.with_name(f".{FEATURE_SET}-{batch_hash}.part")
    for path in (raw_root, temp_feature, raw_root / "batch_manifest.json",
                 raw_root / "batch_manifest.json.part", *(raw_root / p.name for p in sources.values())):
        check_absent(path, root)
    temp_feature.mkdir(parents=True)
    declared_sources = _provenance.publication_sources(Path(__file__), ("provenance.py", "publication_safety.py", "paths.py"))
    retained = _provenance.retain_sources(
        temp_feature / "provenance",
        declared_sources,
        artifact_id=DATASET_ID, root=root,
    )
    asset_records = {}
    try:
        for asset, (filename, symbol, description) in SOURCE_FILES.items():
            table, profile = _parse_source(sources[asset], asset, symbol)
            output = temp_feature / f"asset={asset}" / "part-000.parquet"
            output.parent.mkdir(parents=True)
            pq.write_table(table, output, compression="zstd")
            asset_records[asset] = {
                "source_symbol": symbol,
                "description": description,
                "source_filename": filename,
                "source_path": str((raw_root / filename).relative_to(root)),
                "source_sha256": source_hashes[asset],
                "source_bytes": sources[asset].stat().st_size,
                "output_path": str((feature_root / f"asset={asset}" / "part-000.parquet").relative_to(root)),
                "output_sha256": _sha256(output),
                "output_bytes": output.stat().st_size,
                **profile,
            }
        check_absent(raw_root, root)
        raw_root.mkdir(parents=True)
        for asset, path in sources.items():
            destination = raw_root / path.name
            check_absent(destination, root)
            with path.open("rb") as incoming, destination.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            if _sha256(destination) != source_hashes[asset]:
                raise ValueError(f"raw copy hash mismatch: {destination}")
        raw_batch = {
            "batch_id": batch_id,
            "source": "TradingView chart CSV exports downloaded to local Downloads",
            "files": [
                {"asset": asset, "filename": item["source_filename"], "sha256": item["source_sha256"], "bytes": item["source_bytes"]}
                for asset, item in asset_records.items()
            ],
        }
        write_new_bytes(raw_root / "batch_manifest.json", (json.dumps(raw_batch, indent=2) + "\n").encode(), root)
        _provenance.verify_retained_sources(temp_feature / "provenance", declared_sources, retained)
        for path in (feature_root, *metadata, *(p.with_name(p.name + ".part") for p in metadata)):
            check_absent(path, root)
        check_path(temp_feature, root)
        feature_root.parent.mkdir(parents=True, exist_ok=True)
        temp_feature.rename(feature_root)
        schema_document = {
            "dataset_id": DATASET_ID,
            "version": VERSION,
            "fields": [{"name": field.name, "arrow_type": str(field.type), "nullable": field.nullable} for field in output_schema()],
            "source_columns": list(SOURCE_COLUMNS),
            "null_semantics": "Empty source cells become null; no forward fill or interpolation.",
            "available_at": "Exported bar_close_unix_s. No same-day final value before this instant.",
        }
        write_new_bytes(schema_path, (json.dumps(schema_document, indent=2) + "\n").encode(), root)
        manifest = {
            "dataset_id": DATASET_ID,
            "version": VERSION,
            "feature_set": FEATURE_SET,
            "source_batch_id": batch_id,
            "source_batch_manifest": str((raw_root / "batch_manifest.json").relative_to(root)),
            "source_batch_manifest_sha256": _sha256(raw_root / "batch_manifest.json"),
            "schema_path": str(schema_path.relative_to(root)),
            "schema_sha256": _sha256(schema_path),
            "indicator_spec": f"catalog/indicators/{DATASET_ID}.json",
            "publication_policy": "Completed source bars only; six unconfirmed terminal bars retained in raw.",
            "join_policy": "Match by available_at <= lower-timeframe timestamp; never forward-fill a missing trading day by date without an explicit stale-data policy.",
            "indicator_policy": "Source-supplied values, not recomputed or independently formula-verified.",
            "assets": asset_records,
            "retained_provenance": dict(retained, path=str((feature_root / "provenance").relative_to(root))),
        }
        write_new_bytes(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode(), root)
    except Exception:
        # Preserve useful failed-stage/raw/partial-final evidence for inspection.
        # A later invocation refuses it; unrelated scratch is never removed.
        raise
    return manifest_path


def load_daily_context(
    project_root: Path | str,
    asset: str,
    *,
    version: str,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    columns: Iterable[str] | None = None,
) -> pa.Table:
    """Load completed daily rows; date bounds are trading-day inclusive/exclusive."""
    if version != VERSION:
        raise ValueError(f"unsupported daily context version: {version}")
    asset = asset.upper()
    if asset not in SOURCE_FILES:
        raise ValueError(f"unsupported asset: {asset}")
    path = Path(project_root) / f"data/features/bars/1d/feature_set={FEATURE_SET}/version={version}/asset={asset}/part-000.parquet"
    if not path.is_file():
        raise FileNotFoundError(path)
    selected = None if columns is None else list(columns)
    requested = None if selected is None else list(selected)
    if requested is not None and "trading_day" not in requested:
        requested.append("trading_day")
    table = pq.read_table(path, columns=requested)
    mask = None
    for boundary, operation in ((start_date, pc.greater_equal), (end_date, pc.less)):
        if boundary is None:
            continue
        value = date.fromisoformat(boundary) if isinstance(boundary, str) else boundary
        condition = operation(table["trading_day"], pa.scalar(value, type=pa.date32()))
        mask = condition if mask is None else pc.and_(mask, condition)
    if mask is not None:
        table = table.filter(mask)
    if selected is not None and "trading_day" not in selected:
        table = table.drop(["trading_day"])
    return table


def align_daily_context_asof(
    project_root: Path | str,
    asset: str,
    times: Iterable[datetime],
    *,
    version: str,
    max_age_days: int | None = 7,
    columns: Iterable[str] = ("trading_day", "available_at", "close", "atr14"),
) -> list[dict | None]:
    """Align many lower-timeframe timestamps to available completed daily bars.

    The default seven-calendar-day age limit prevents an old value from being
    silently carried across an extended data gap. Pass ``None`` to opt out.
    """
    if max_age_days is not None and max_age_days < 0:
        raise ValueError("max_age_days must be nonnegative or None")
    instants = list(times)
    for when in instants:
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError("all timestamps must be timezone aware")
    if not instants:
        return []
    selected = list(columns)
    requested = list(dict.fromkeys([*selected, "available_at"]))
    table = load_daily_context(project_root, asset, version=version, columns=requested)
    available = table["available_at"].to_pylist()
    rows = table.to_pylist()
    result = []
    for when in instants:
        utc_when = when.astimezone(timezone.utc)
        index = bisect.bisect_right(available, utc_when) - 1
        if index < 0 or (max_age_days is not None and (utc_when - available[index]).total_seconds() > max_age_days * DAY_SECONDS):
            result.append(None)
        else:
            result.append({name: rows[index][name] for name in selected})
    return result


def lookup_daily_context_asof(
    project_root: Path | str,
    asset: str,
    when: datetime,
    *,
    version: str,
    max_age_days: int | None = 7,
    columns: Iterable[str] = ("trading_day", "available_at", "close", "atr14"),
) -> dict | None:
    """Return one completed daily bar available at ``when`` or ``None``."""
    return align_daily_context_asof(
        project_root, asset, [when], version=version,
        max_age_days=max_age_days, columns=columns,
    )[0]


def verify_daily_context_release(
    project_root: Path | str, *, manifest_sha256: str | None = None
) -> dict:
    """Check the pinned raw and Parquet files without modifying the release."""
    root = Path(project_root)
    manifest_path = root / "catalog/datasets" / f"{DATASET_ID}.json"
    if manifest_sha256 is not None and _sha256(manifest_path) != manifest_sha256:
        raise ValueError("release manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("dataset_id") != DATASET_ID or manifest.get("version") != VERSION:
        raise ValueError("unexpected release identity")
    for path_key, hash_key in (("schema_path", "schema_sha256"), ("source_batch_manifest", "source_batch_manifest_sha256")):
        if _sha256(root / manifest[path_key]) != manifest[hash_key]:
            raise ValueError(f"{path_key} hash mismatch")
    if set(manifest["assets"]) != set(SOURCE_FILES):
        raise ValueError("asset set mismatch")
    total_rows = 0
    for asset, record in manifest["assets"].items():
        for kind in ("source", "output"):
            path = root / record[f"{kind}_path"]
            if path.stat().st_size != record[f"{kind}_bytes"] or _sha256(path) != record[f"{kind}_sha256"]:
                raise ValueError(f"{asset} {kind} checksum mismatch")
        table = pq.read_table(root / record["output_path"], columns=["available_at", "bar_confirmed"])
        if table.num_rows != record["published_rows"] or not all(table["bar_confirmed"].to_pylist()):
            raise ValueError(f"{asset} published row count or confirmation mismatch")
        available = table["available_at"].to_pylist()
        if any(left >= right for left, right in zip(available, available[1:])):
            raise ValueError(f"{asset} availability order mismatch")
        total_rows += table.num_rows
    return {"dataset_id": DATASET_ID, "assets": len(SOURCE_FILES), "confirmed_rows": total_rows, "status": "passed"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish or verify daily context exports")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    root = resolve_publication_root(args.root)
    if args.verify:
        if args.input_dir is not None:
            parser.error("--input-dir cannot be combined with --verify")
        print(json.dumps(verify_daily_context_release(root, manifest_sha256=args.manifest_sha256), indent=2))
    elif args.input_dir is not None:
        print(publish_daily_context(args.input_dir, root))
    else:
        parser.error("pass --input-dir to publish or --verify to check the release")


if __name__ == "__main__":
    main()
