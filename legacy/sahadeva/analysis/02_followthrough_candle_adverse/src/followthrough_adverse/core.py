from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_config(path: str | Path) -> tuple[dict[str, Any], Path]:
    config_path = Path(path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return config, config_path.parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def assign_split(export_date: pd.Series, split_dates: dict[str, list[str]]) -> pd.Series:
    result = pd.Series("outside", index=export_date.index, dtype="string")
    dates = pd.to_datetime(export_date).dt.date
    for label, (start, end) in split_dates.items():
        result.loc[
            (dates >= pd.Timestamp(start).date()) & (dates <= pd.Timestamp(end).date())
        ] = label
    return result


def read_chart(
    dataset: dict[str, Any], config: dict[str, Any], project_root: Path
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = project_root / dataset["path"]
    columns = ["timestamp", "open", "high", "low", "close"]
    frame = pd.read_csv(
        path,
        sep=config["delimiter"],
        header=None,
        names=columns,
        dtype={"timestamp": "string"},
    )
    frame.insert(0, "source_row", np.arange(1, len(frame) + 1, dtype=np.int64))
    parsed = pd.to_datetime(
        frame["timestamp"], format=config["timestamp_format"], errors="coerce"
    )
    numeric_ok = pd.Series(True, index=frame.index)
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        numeric_ok &= frame[column].notna() & np.isfinite(frame[column])
    ohlc_ok = (
        numeric_ok
        & frame["high"].ge(frame[["open", "close", "low"]].max(axis=1))
        & frame["low"].le(frame[["open", "close", "high"]].min(axis=1))
    )
    tick_size = float(config["contracts"][dataset["asset"]]["tick_size"])
    tick_ok = pd.Series(True, index=frame.index)
    for column in ("open", "high", "low", "close"):
        scaled = frame[column] / tick_size
        tick_ok &= np.abs(scaled - np.rint(scaled)) < 1e-7
        frame[f"{column}_ticks"] = np.rint(scaled).astype("Int64")
    frame["parsed_timestamp"] = parsed
    frame["export_date"] = parsed.dt.strftime("%Y-%m-%d")
    frame["valid_row"] = parsed.notna() & numeric_ok & ohlc_ok & tick_ok
    frame["bar_included"] = frame["valid_row"]
    if len(frame):
        frame.loc[frame.index[-1], "bar_included"] = False
    frame["direction"] = np.sign(
        frame["close_ticks"].astype("Float64") - frame["open_ticks"].astype("Float64")
    ).astype("Int8")
    frame["split"] = assign_split(frame["export_date"], config["split_dates"])
    date_change = frame["export_date"].ne(frame["export_date"].shift())
    invalid_boundary = (~frame["valid_row"]) | (~frame["valid_row"].shift(fill_value=False))
    frame["sequence_id"] = (date_change | invalid_boundary).cumsum().astype(np.int64)
    source_hash = sha256_file(path)
    frame["source_file"] = path.name
    frame["source_sha256"] = source_hash
    frame["asset"] = dataset["asset"]
    frame["contract"] = dataset["contract"]
    frame["range_setting"] = int(dataset["range"])
    frame["chart_identity_status"] = config["chart_identity_status"]
    audit = {
        "asset": dataset["asset"],
        "contract": dataset["contract"],
        "range_setting": int(dataset["range"]),
        "source_path": dataset["path"],
        "source_file": path.name,
        "source_sha256": source_hash,
        "size_bytes": path.stat().st_size,
        "rows": int(len(frame)),
        "included_rows": int(frame["bar_included"].sum()),
        "timestamp_parse_failures": int(parsed.isna().sum()),
        "ohlc_failures": int((~ohlc_ok).sum()),
        "off_tick_rows": int((~tick_ok).sum()),
        "timestamp_regressions": int((parsed.diff().dropna() < pd.Timedelta(0)).sum()),
        "repeated_timestamp_rows": int(parsed.duplicated(keep=False).sum()),
        "doji_rows": int(frame["direction"].eq(0).sum()),
        "export_dates": int(frame["export_date"].nunique()),
        "first_timestamp": str(parsed.iloc[0]),
        "last_timestamp": str(parsed.iloc[-1]),
        "status": "analyzed",
    }
    return frame, audit


def _prior_run_lengths(direction: np.ndarray, sequence: np.ndarray) -> np.ndarray:
    prior = np.zeros(len(direction), dtype=np.int32)
    current_run = 0
    for i in range(len(direction)):
        if i == 0 or sequence[i] != sequence[i - 1] or direction[i - 1] == 0:
            prior[i] = 0
        else:
            prior[i] = current_run
        if direction[i] == 0:
            current_run = 0
        elif i > 0 and sequence[i] == sequence[i - 1] and direction[i] == direction[i - 1]:
            current_run += 1
        else:
            current_run = 1
    return prior


def detect_reversals(bars: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    direction = usable["direction"].to_numpy(dtype=np.int8)
    sequence = usable["sequence_id"].to_numpy(dtype=np.int64)
    prior = _prior_run_lengths(direction, sequence)
    reversal = np.zeros(len(usable), dtype=bool)
    if len(usable) > 1:
        reversal[1:] = (
            (sequence[1:] == sequence[:-1])
            & (direction[1:] != 0)
            & (direction[:-1] != 0)
            & (direction[1:] == -direction[:-1])
        )
    positions = np.flatnonzero(reversal)
    events = usable.iloc[positions].copy()
    events.insert(0, "bar_index", positions)
    events.insert(
        0,
        "event_id",
        [f"{row.asset}{int(row.range_setting)}-r{int(row.source_row)}" for row in events.itertuples(index=False)],
    )
    events["signal_side"] = np.where(events["direction"].eq(1), "long", "short")
    events["prior_opposite_run"] = prior[positions]
    events["followthrough_position"] = 1
    events["sequence_position_including_reversal"] = 2
    events["eligible_next_bar"] = False
    events["next_bar_same_direction"] = False

    output_columns = (
        "follow_open_ticks",
        "follow_high_ticks",
        "follow_low_ticks",
        "follow_close_ticks",
        "adverse_from_follow_open_ticks",
        "favorable_from_follow_open_ticks",
        "close_progress_from_follow_open_ticks",
        "adverse_from_signal_close_ticks",
        "favorable_from_signal_close_ticks",
        "directional_open_gap_ticks",
    )
    for column in output_columns:
        events[column] = pd.NA
    events["follow_source_row"] = pd.NA
    events["follow_timestamp"] = pd.NA

    for event_idx, position in zip(events.index, positions):
        next_position = position + 1
        if next_position >= len(usable) or sequence[next_position] != sequence[position]:
            continue
        events.at[event_idx, "eligible_next_bar"] = True
        if direction[next_position] != direction[position]:
            continue
        events.at[event_idx, "next_bar_same_direction"] = True
        follow = usable.iloc[next_position]
        side = int(direction[position])
        open_tick = int(follow["open_ticks"])
        high_tick = int(follow["high_ticks"])
        low_tick = int(follow["low_ticks"])
        close_tick = int(follow["close_ticks"])
        signal_close = int(usable.iloc[position]["close_ticks"])
        if side == 1:
            adverse_open = open_tick - low_tick
            favorable_open = high_tick - open_tick
            close_progress = close_tick - open_tick
            adverse_signal = max(0, signal_close - low_tick)
            favorable_signal = max(0, high_tick - signal_close)
            open_gap = open_tick - signal_close
        else:
            adverse_open = high_tick - open_tick
            favorable_open = open_tick - low_tick
            close_progress = open_tick - close_tick
            adverse_signal = max(0, high_tick - signal_close)
            favorable_signal = max(0, signal_close - low_tick)
            open_gap = signal_close - open_tick
        values = {
            "follow_open_ticks": open_tick,
            "follow_high_ticks": high_tick,
            "follow_low_ticks": low_tick,
            "follow_close_ticks": close_tick,
            "adverse_from_follow_open_ticks": adverse_open,
            "favorable_from_follow_open_ticks": favorable_open,
            "close_progress_from_follow_open_ticks": close_progress,
            "adverse_from_signal_close_ticks": adverse_signal,
            "favorable_from_signal_close_ticks": favorable_signal,
            "directional_open_gap_ticks": open_gap,
            "follow_source_row": int(follow["source_row"]),
            "follow_timestamp": follow["timestamp"],
        }
        for column, value in values.items():
            events.at[event_idx, column] = value

    for column in output_columns + ("follow_source_row",):
        events[column] = pd.to_numeric(events[column], errors="coerce").astype("Float64")
    events["eligible_next_bar"] = events["eligible_next_bar"].astype(bool)
    events["next_bar_same_direction"] = events["next_bar_same_direction"].astype(bool)
    events["primary_condition"] = "next bar exists in segment and closes in reversal direction"
    events["primary_reference"] = config["primary_reference"]
    events["timing_status"] = config["timing_status"]
    return events.reset_index(drop=True)


def reconcile_sample(
    bars: pd.DataFrame, events: pd.DataFrame, seed: int, sample_size: int = 12
) -> tuple[pd.DataFrame, dict[str, Any]]:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    conditioned = events.loc[events["next_bar_same_direction"]]
    take = min(sample_size, len(conditioned))
    rng = np.random.default_rng(seed)
    selected = conditioned.iloc[rng.choice(len(conditioned), size=take, replace=False)] if take else conditioned
    rows = []
    matches = 0
    for event in selected.itertuples(index=False):
        follow = usable.iloc[int(event.bar_index) + 1]
        if event.signal_side == "long":
            independent = int(follow.open_ticks - follow.low_ticks)
        else:
            independent = int(follow.high_ticks - follow.open_ticks)
        match = independent == int(event.adverse_from_follow_open_ticks)
        matches += int(match)
        rows.append(
            {
                "event_id": event.event_id,
                "asset": event.asset,
                "contract": event.contract,
                "range_setting": int(event.range_setting),
                "source_file": event.source_file,
                "source_row": int(event.source_row),
                "follow_source_row": int(event.follow_source_row),
                "direction": event.signal_side,
                "prior_opposite_run": int(event.prior_opposite_run),
                "calculated_adverse_ticks": int(event.adverse_from_follow_open_ticks),
                "independent_adverse_ticks": independent,
                "match": match,
            }
        )
    return pd.DataFrame(rows), {"sampled": take, "matches": matches, "all_match": matches == take}

