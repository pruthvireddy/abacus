from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_config(path: str | Path) -> tuple[dict[str, Any], Path]:
    """Load the JSON-compatible YAML configuration and locate the project root."""
    config_path = Path(path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = config_path.parents[3]
    return config, project_root


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def config_hash(config: dict[str, Any]) -> str:
    return sha256_text(json.dumps(config, sort_keys=True, separators=(",", ":")))


def assign_split(dates: pd.Series, split_dates: dict[str, list[str]]) -> pd.Series:
    out = pd.Series("outside", index=dates.index, dtype="string")
    date_values = pd.to_datetime(dates).dt.date
    for label, (start, end) in split_dates.items():
        lo = pd.Timestamp(start).date()
        hi = pd.Timestamp(end).date()
        out.loc[(date_values >= lo) & (date_values <= hi)] = label
    return out


def read_dataset(
    dataset: dict[str, Any], config: dict[str, Any], project_root: Path
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = project_root / dataset["path"]
    names = config["schema"]
    raw = pd.read_csv(
        path,
        sep=config["delimiter"],
        header=None,
        names=names,
        dtype={"timestamp": "string"},
        keep_default_na=False,
    )
    source_hash = sha256_file(path)
    raw.insert(0, "source_row", np.arange(1, len(raw) + 1, dtype=np.int64))
    raw.insert(0, "source_file", path.name)
    raw.insert(0, "source_sha256", source_hash)

    numeric_ok = pd.Series(True, index=raw.index)
    for column in ("open", "high", "low", "close"):
        parsed = pd.to_numeric(raw[column], errors="coerce")
        numeric_ok &= parsed.notna() & np.isfinite(parsed)
        raw[column] = parsed

    parsed_time = pd.to_datetime(
        raw["timestamp"], format=config["timestamp_format"], errors="coerce"
    )
    alternate_time = pd.to_datetime(
        raw["timestamp"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
    )
    raw["parsed_timestamp"] = parsed_time
    raw["export_date"] = parsed_time.dt.strftime("%Y-%m-%d")

    ohlc_ok = (
        numeric_ok
        & (raw["high"] >= raw[["open", "close", "low"]].max(axis=1))
        & (raw["low"] <= raw[["open", "close", "high"]].min(axis=1))
    )
    tick_size = float(config["contracts"][dataset["asset"]]["tick_size"])
    tick_aligned = pd.Series(True, index=raw.index)
    for column in ("open", "high", "low", "close"):
        scaled = raw[column] / tick_size
        tick_aligned &= scaled.notna() & (np.abs(scaled - np.rint(scaled)) < 1e-7)
        raw[f"{column}_ticks"] = np.rint(scaled).astype("Int64")

    raw["parse_ok"] = parsed_time.notna()
    raw["numeric_ok"] = numeric_ok
    raw["ohlc_ok"] = ohlc_ok
    raw["tick_aligned"] = tick_aligned
    raw["valid_row"] = raw[["parse_ok", "numeric_ok", "ohlc_ok", "tick_aligned"]].all(axis=1)
    raw["bar_included"] = raw["valid_row"]
    if len(raw):
        raw.loc[raw.index[-1], "bar_included"] = False
    raw["exclusion_reason"] = ""
    raw.loc[~raw["valid_row"], "exclusion_reason"] = "invalid_row"
    if len(raw):
        raw.loc[raw.index[-1], "exclusion_reason"] = "final_bar_completion_unverified"

    close_ticks = raw["close_ticks"].astype("Float64")
    open_ticks = raw["open_ticks"].astype("Float64")
    raw["direction"] = np.sign(close_ticks - open_ticks).astype("Int8")
    raw["asset"] = dataset["asset"]
    raw["contract"] = dataset["contract"]
    raw["range_setting"] = int(dataset["range"])
    raw["chart_type"] = "Range XV (filename label)"
    raw["chart_identity_status"] = config["chart_identity_status"]
    raw["timing_status"] = config["timing_status"]
    raw["split"] = assign_split(raw["export_date"], config["split_dates"])

    # Invalid rows and date changes create hard sequence breaks. This prevents
    # neighbors of a removed row from becoming artificially adjacent.
    date_change = raw["export_date"].ne(raw["export_date"].shift())
    invalid_boundary = (~raw["valid_row"]) | (~raw["valid_row"].shift(fill_value=False))
    raw["sequence_id"] = (date_change | invalid_boundary).cumsum().astype(np.int64)

    timestamp_regressions = int((parsed_time.diff().dropna() < pd.Timedelta(0)).sum())
    repeated_timestamp_rows = int(parsed_time.duplicated(keep=False).sum())
    adjacent_zero_deltas = int((parsed_time.diff() == pd.Timedelta(0)).sum())
    inferred_headerless = len(raw) > 0 and bool(parsed_time.iloc[0] is not pd.NaT)
    audit = {
        "asset": dataset["asset"],
        "contract": dataset["contract"],
        "range_setting": int(dataset["range"]),
        "source_file": path.name,
        "source_path": dataset["path"],
        "source_sha256": source_hash,
        "size_bytes": path.stat().st_size,
        "rows": int(len(raw)),
        "columns": int(len(names)),
        "delimiter": config["delimiter"],
        "headerless_inference": inferred_headerless,
        "timestamp_format": config["timestamp_format"],
        "timestamp_parse_success": int(parsed_time.notna().sum()),
        "alternate_ymd_parse_success": int(alternate_time.notna().sum()),
        "numeric_failures": int((~numeric_ok).sum()),
        "ohlc_failures": int((~ohlc_ok).sum()),
        "off_tick_rows": int((~tick_aligned).sum()),
        "timestamp_regressions": timestamp_regressions,
        "repeated_timestamp_rows": repeated_timestamp_rows,
        "adjacent_zero_timestamp_deltas": adjacent_zero_deltas,
        "doji_rows": int((raw["direction"] == 0).sum()),
        "excluded_final_rows": 1 if len(raw) else 0,
        "first_timestamp": parsed_time.iloc[0].isoformat(sep=" ") if len(raw) else None,
        "last_timestamp": parsed_time.iloc[-1].isoformat(sep=" ") if len(raw) else None,
        "export_dates": int(raw["export_date"].nunique()),
        "tick_size": tick_size,
        "chart_identity_status": config["chart_identity_status"],
        "timing_status": config["timing_status"],
    }
    return raw, audit


def geometry_summary(bars: pd.DataFrame) -> pd.DataFrame:
    included = bars.loc[bars["bar_included"]].copy()
    included["high_low_ticks"] = included["high_ticks"] - included["low_ticks"]
    included["body_ticks"] = (included["close_ticks"] - included["open_ticks"]).abs()
    same_sequence = included["sequence_id"].eq(included["sequence_id"].shift())
    included["open_gap_ticks"] = (
        included["open_ticks"] - included["close_ticks"].shift()
    ).where(same_sequence)
    included["close_change_ticks"] = (
        included["close_ticks"] - included["close_ticks"].shift()
    ).where(same_sequence)

    rows: list[dict[str, Any]] = []
    identity = {
        "asset": str(included["asset"].iloc[0]),
        "contract": str(included["contract"].iloc[0]),
        "range_setting": int(included["range_setting"].iloc[0]),
        "chart_identity_status": str(included["chart_identity_status"].iloc[0]),
        "date_window": f"{included['export_date'].min()} to {included['export_date'].max()}",
        "split": "full",
        "direction": "all",
        "cohort": "included valid bars",
        "timing_status": str(included["timing_status"].iloc[0]),
    }
    for metric in ("high_low_ticks", "body_ticks", "open_gap_ticks", "close_change_ticks"):
        values = pd.to_numeric(included[metric], errors="coerce").dropna().astype(float)
        q = values.quantile([0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0])
        row = dict(identity)
        row.update(
            {
                "metric": metric,
                "denominator": int(len(values)),
                "horizon": "n/a",
                "units": "exchange ticks",
                "mean": float(values.mean()),
                "min": float(q.loc[0.0]),
                "p25": float(q.loc[0.25]),
                "median": float(q.loc[0.5]),
                "p75": float(q.loc[0.75]),
                "p90": float(q.loc[0.9]),
                "p95": float(q.loc[0.95]),
                "p99": float(q.loc[0.99]),
                "max": float(q.loc[1.0]),
                "zero_count": int((values == 0).sum()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def coverage_by_date(bars: pd.DataFrame) -> pd.DataFrame:
    included = bars.loc[bars["bar_included"]].copy()
    same_sequence = included["sequence_id"].eq(included["sequence_id"].shift())
    included["adjacent_timestamp_delta_seconds"] = (
        included["parsed_timestamp"].diff().dt.total_seconds().where(same_sequence)
    )
    grouped = included.groupby("export_date", sort=True, observed=True)
    result = grouped.agg(
        first_timestamp=("parsed_timestamp", "min"),
        last_timestamp=("parsed_timestamp", "max"),
        bar_count=("source_row", "size"),
        unique_timestamps=("parsed_timestamp", "nunique"),
        max_adjacent_timestamp_gap_seconds=("adjacent_timestamp_delta_seconds", "max"),
        median_adjacent_timestamp_delta_seconds=("adjacent_timestamp_delta_seconds", "median"),
    ).reset_index()
    result["max_adjacent_timestamp_gap_minutes"] = result["max_adjacent_timestamp_gap_seconds"] / 60.0
    result["raw_clock_span_hours"] = (
        (result["last_timestamp"] - result["first_timestamp"]).dt.total_seconds() / 3600.0
    )
    for column in ("asset", "contract", "range_setting", "chart_identity_status", "timing_status"):
        result[column] = included[column].iloc[0]
    result["date_window"] = result["export_date"]
    result["split"] = assign_split(result["export_date"], {
        name: [str(included.loc[included['split'].eq(name), 'export_date'].min()), str(included.loc[included['split'].eq(name), 'export_date'].max())]
        for name in included["split"].dropna().unique()
        if name != "outside" and not included.loc[included["split"].eq(name)].empty
    }) if not result.empty else ""
    result["direction"] = "all"
    result["cohort"] = "included valid bars"
    result["denominator"] = result["bar_count"]
    result["horizon"] = "one export date"
    result["units"] = "bars, raw timestamp hours, and observed timestamp-gap seconds"
    return result
