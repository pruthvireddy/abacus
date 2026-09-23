from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _run_metadata(direction: np.ndarray, sequence: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return prior-run length, future same-direction length, and censor flags."""
    n = len(direction)
    prior = np.zeros(n, dtype=np.int32)
    current_run = 0
    for i in range(n):
        if i == 0 or sequence[i] != sequence[i - 1] or direction[i - 1] == 0:
            previous_run = 0
        else:
            previous_run = current_run
        prior[i] = previous_run
        if direction[i] == 0:
            current_run = 0
        elif i > 0 and sequence[i] == sequence[i - 1] and direction[i] == direction[i - 1]:
            current_run += 1
        else:
            current_run = 1

    future = np.zeros(n, dtype=np.int32)
    censored = np.zeros(n, dtype=bool)
    for i in range(n - 1, -1, -1):
        if direction[i] == 0:
            continue
        if i + 1 >= n or sequence[i + 1] != sequence[i]:
            future[i] = 0
            censored[i] = True
        elif direction[i + 1] == direction[i]:
            future[i] = 1 + future[i + 1]
            censored[i] = censored[i + 1]
        else:
            future[i] = 0
            censored[i] = False
    return prior, future, censored


def detect_events(bars: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    direction = usable["direction"].to_numpy(dtype=np.int8)
    sequence = usable["sequence_id"].to_numpy(dtype=np.int64)
    prior, future, censored = _run_metadata(direction, sequence)
    usable["prior_same_direction_run"] = prior
    usable["future_same_direction_run"] = future
    usable["future_run_censored"] = censored

    previous_opposite = np.zeros(len(usable), dtype=bool)
    if len(usable) > 1:
        previous_opposite[1:] = (
            (sequence[1:] == sequence[:-1])
            & (direction[1:] != 0)
            & (direction[:-1] != 0)
            & (direction[1:] == -direction[:-1])
        )
    signal_positions = np.flatnonzero(previous_opposite)
    events = usable.iloc[signal_positions].copy()
    events.insert(0, "bar_index", signal_positions)
    events.insert(
        0,
        "event_id",
        [
            f"{row.asset}{int(row.range_setting)}-r{int(row.source_row)}"
            for row in events.itertuples(index=False)
        ],
    )
    events["signal_side"] = np.where(events["direction"].eq(1), "long", "short")
    events["prior_opposite_run"] = events["prior_same_direction_run"]
    events["prior_run_bucket"] = pd.cut(
        events["prior_opposite_run"], bins=[0, 1, 2, np.inf], labels=["1", "2", "3+"]
    ).astype("string")
    events["observed_L"] = events["future_same_direction_run"].astype(int)
    events["run_censored"] = events["future_run_censored"].astype(bool)
    events["censor_reason"] = np.where(events["run_censored"], "export_date_boundary", "")
    events["completed_L"] = events["observed_L"].where(~events["run_censored"])
    events["T_including_reversal"] = (1 + events["observed_L"]).where(~events["run_censored"])
    events["signal_reference_ticks"] = events["close_ticks"].astype("Int64")
    events["signal_raw_timestamp"] = events["timestamp"]
    events["signal_confirmation_status"] = "unverified timestamp semantics"

    seq_end = np.empty(len(usable), dtype=np.int64)
    start = 0
    while start < len(usable):
        end = start + 1
        while end < len(usable) and sequence[end] == sequence[start]:
            end += 1
        seq_end[start:end] = end
        start = end

    for threshold in config["thresholds"]:
        eligible = signal_positions + threshold < seq_end[signal_positions]
        events[f"eligible_L_ge_{threshold}"] = eligible
        success = np.zeros(len(events), dtype=bool)
        for offset in range(1, threshold + 1):
            valid_idx = np.flatnonzero(eligible)
            success[valid_idx] |= False
            success[valid_idx] = success[valid_idx] & True if offset > 1 else True
            success[valid_idx] &= direction[signal_positions[valid_idx] + offset] == direction[signal_positions[valid_idx]]
        events[f"success_L_ge_{threshold}"] = pd.array(
            np.where(eligible, success.astype(object), None), dtype="boolean"
        )

    events["shared_eligible_10"] = events["eligible_L_ge_10"]
    events["restricted_L_10"] = np.minimum(events["observed_L"], 10).where(
        events["shared_eligible_10"]
    )

    baseline = usable.loc[usable["direction"].ne(0)].copy()
    baseline_positions = baseline.index.to_numpy(dtype=np.int64)
    baseline["bar_index"] = baseline_positions
    for threshold in config["thresholds"]:
        eligible = baseline_positions + threshold < seq_end[baseline_positions]
        success = np.ones(len(baseline), dtype=bool)
        for offset in range(1, threshold + 1):
            good = np.flatnonzero(eligible)
            success[~eligible] = False
            success[good] &= direction[baseline_positions[good] + offset] == direction[baseline_positions[good]]
        baseline[f"eligible_L_ge_{threshold}"] = eligible
        baseline[f"success_L_ge_{threshold}"] = pd.array(
            np.where(eligible, success.astype(object), None), dtype="boolean"
        )
    baseline["signal_side"] = np.where(baseline["direction"].eq(1), "long", "short")
    return events.reset_index(drop=True), baseline.reset_index(drop=True)


def detect_events_bruteforce(bars: pd.DataFrame, positions: list[int]) -> list[dict[str, Any]]:
    """Independent, deliberately simple event scanner used for reconciliation."""
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    out: list[dict[str, Any]] = []
    for pos in positions:
        direction = int(usable.loc[pos, "direction"])
        sequence = int(usable.loc[pos, "sequence_id"])
        prior = 0
        cursor = pos - 1
        while cursor >= 0 and int(usable.loc[cursor, "sequence_id"]) == sequence:
            if int(usable.loc[cursor, "direction"]) != -direction:
                break
            prior += 1
            cursor -= 1
        run = 0
        cursor = pos + 1
        while cursor < len(usable) and int(usable.loc[cursor, "sequence_id"]) == sequence:
            if int(usable.loc[cursor, "direction"]) != direction:
                break
            run += 1
            cursor += 1
        censored = cursor >= len(usable) or int(usable.loc[cursor, "sequence_id"]) != sequence
        out.append({"bar_index": pos, "prior_opposite_run": prior, "observed_L": run, "run_censored": censored})
    return out

