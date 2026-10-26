"""Extract C1 opportunities and ordinary two-bar states from pinned RXV bars."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


TICKS = {"ES": .25, "GC": .1, "NQ": .25}
READ_COLS = ["source_row", "source_timestamp", "bar_start_timestamp",
             "bar_completion_timestamp_proxy", "completion_proxy_status",
             "session_date_proxy", "open", "high", "low", "close"]
STRICT = "next_bar_start_proxy"
SAME = "next_bar_start_same_second"
GC_EXCLUDED = {"2026-01-28", "2026-02-04", "2026-02-20", "2026-03-19", "2026-04-02"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs(root: Path, lock: dict) -> list[dict]:
    checked = []
    for record in [lock["manifest"], *lock["files"]]:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise FileNotFoundError(record["path"])
        actual = digest(path)
        if actual != record["sha256"]:
            raise ValueError(f"hash mismatch: {record['path']}")
        checked.append({"path": record["path"], "sha256": actual,
                        "bytes": path.stat().st_size})
    return checked


def iter_sessions(path: Path):
    carry = None
    for chunk in pd.read_csv(path, sep=";", usecols=READ_COLS, chunksize=200_000):
        if carry is not None:
            chunk = pd.concat([carry, chunk], ignore_index=True)
        dates = chunk.session_date_proxy.to_numpy()
        cuts = np.flatnonzero(dates[1:] != dates[:-1]) + 1
        start = 0
        for stop in cuts:
            yield chunk.iloc[start:stop].copy().reset_index(drop=True)
            start = int(stop)
        carry = chunk.iloc[start:].copy()
    if carry is not None and len(carry):
        yield carry.reset_index(drop=True)


def session_window(clock: str) -> str:
    if not clock:
        return "unavailable"
    t = clock[-8:]
    if t >= "18:00:00" or t < "03:00:00": return "asia"
    if t < "09:30:00": return "london_pre_ny"
    if t < "12:00:00": return "ny_morning"
    if t < "16:00:00": return "ny_afternoon"
    return "transition"


def run_lengths(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(direction)
    lengths = np.zeros(n, dtype=np.int32)
    starts = np.arange(n, dtype=np.int32)
    for index in range(n):
        if direction[index] and index and direction[index] == direction[index-1]:
            lengths[index] = lengths[index-1]+1
            starts[index] = starts[index-1]
        elif direction[index]:
            lengths[index] = 1
    return lengths, starts


def larger_states(path: Path, tick: float) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    states = {}
    for df in iter_sessions(path):
        ok = df.completion_proxy_status.eq(STRICT).to_numpy()
        times = pd.to_datetime(df.loc[ok, "bar_completion_timestamp_proxy"],
                               format="%Y-%m-%d %H:%M:%S").to_numpy(dtype="datetime64[s]")
        directions = np.sign(np.rint(df.loc[ok, "close"].to_numpy()/tick)-
                             np.rint(df.loc[ok, "open"].to_numpy()/tick)).astype(np.int8)
        states[str(df.session_date_proxy.iloc[0])] = (times, directions)
    return states


def attach_larger(c1_completion: np.ndarray,
                  larger: tuple[np.ndarray, np.ndarray] | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    count = len(c1_completion)
    state = np.zeros(count, dtype=np.int8)
    state_time = np.full(count, "", dtype="U19")
    tie = np.zeros(count, dtype=bool)
    if larger is None or not len(larger[0]):
        return state, state_time, tie
    times, directions = larger
    left = np.searchsorted(times, c1_completion, side="left")
    right = np.searchsorted(times, c1_completion, side="right")
    positions = left-1
    good = (positions >= 0) & ~np.isnat(c1_completion)
    state[good] = directions[positions[good]]
    state_time[good] = np.datetime_as_string(times[positions[good]], unit="s")
    tie = (right > left) & ~np.isnat(c1_completion)
    if np.any(times[positions[good]] >= c1_completion[good]):
        raise AssertionError("larger state look-ahead")
    return state, state_time, tie


def price_path(direction: np.ndarray, entry: np.ndarray, exit_price: np.ndarray,
               lows_1: np.ndarray, lows_2: np.ndarray,
               highs_1: np.ndarray, highs_2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    movement = direction * (exit_price-entry)
    adverse = np.where(direction > 0, entry-np.minimum(lows_1, lows_2),
                       np.maximum(highs_1, highs_2)-entry)
    return movement, np.maximum(adverse, 0)


def extract_session(df: pd.DataFrame, product: str, setting: int,
                    larger: tuple[np.ndarray, np.ndarray] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    n = len(df)
    date = str(df.session_date_proxy.iloc[0])
    tick = TICKS[product]
    o,h,l,c = [np.rint(df[name].to_numpy(dtype=np.float64)/tick).astype(np.int64)
               for name in ("open","high","low","close")]
    if np.any(h < np.maximum.reduce([o,l,c])) or np.any(l > np.minimum.reduce([o,h,c])):
        raise ValueError(f"invalid OHLC {product} {setting} {date}")
    direction = np.sign(c-o).astype(np.int8)
    length, start = run_lengths(direction)
    strict = df.completion_proxy_status.eq(STRICT).to_numpy()
    same = df.completion_proxy_status.eq(SAME).to_numpy()
    source = df.source_row.to_numpy()
    clock = df.bar_completion_timestamp_proxy.fillna("").astype(str).to_numpy()
    complete_t = pd.to_datetime(df.bar_completion_timestamp_proxy,
                                format="%Y-%m-%d %H:%M:%S", errors="coerce").to_numpy(dtype="datetime64[s]")
    block = "early" if date <= "2021-12-31" else ("middle" if date <= "2023-12-31" else "recent")
    excluded = product == "GC" and date in GC_EXCLUDED

    c1 = np.flatnonzero((direction[1:] != 0) & (direction[1:] == -direction[:-1]) &
                        (length[:-1] > 0))+1
    prior = length[c1-1]
    main = prior >= 3
    bins = np.select([prior <= 2, prior <= 4, prior <= 7],
                     ["1-2","3-4","5-7"], default="8+")
    eligible = c1+4 < n
    valid = np.flatnonzero(eligible)
    for offset in range(4):
        eligible[valid] &= strict[c1[valid]+offset]
    has_c2 = c1+1 < n
    has_c3 = c1+2 < n
    has_c4 = c1+3 < n
    c2_follow = np.zeros(len(c1), dtype=bool)
    c2_old = np.zeros(len(c1), dtype=bool)
    c2_doji = np.zeros(len(c1), dtype=bool)
    c3_follow = np.zeros(len(c1), dtype=bool)
    c4_follow = np.zeros(len(c1), dtype=bool)
    c3_old = np.zeros(len(c1), dtype=bool)
    c2_follow[has_c2] = direction[c1[has_c2]+1] == direction[c1[has_c2]]
    c2_old[has_c2] = direction[c1[has_c2]+1] == -direction[c1[has_c2]]
    c2_doji[has_c2] = direction[c1[has_c2]+1] == 0
    c3_follow[has_c3] = direction[c1[has_c3]+2] == direction[c1[has_c3]]
    c4_follow[has_c4] = direction[c1[has_c4]+3] == direction[c1[has_c4]]
    c3_old[has_c3] = direction[c1[has_c3]+2] == -direction[c1[has_c3]]
    # Padding is used only for ineligible boundary rows; their price outputs are null.
    safe_o = np.pad(o, (0, 5), mode="edge")
    safe_h = np.pad(h, (0, 5), mode="edge")
    safe_l = np.pad(l, (0, 5), mode="edge")
    immediate_ticks, immediate_mae = price_path(direction[c1], safe_o[c1+1], safe_o[c1+3],
        safe_l[c1+1], safe_l[c1+2], safe_h[c1+1], safe_h[c1+2])
    wait_ticks, wait_mae = price_path(direction[c1], safe_o[c1+2], safe_o[c1+4],
        safe_l[c1+2], safe_l[c1+3], safe_h[c1+2], safe_h[c1+3])
    larger_dir, larger_time, larger_tie = attach_larger(complete_t[c1], larger)
    context = np.where(larger_dir == 0, "unavailable",
                       np.where(larger_dir == direction[c1], "aligned", "against"))
    opportunities = pd.DataFrame({
        "product":product,"setting":setting,"session_date":date,"block":block,
        "c1_source_row":source[c1],
        "c2_source_row":np.where(c1+1<n,source[np.minimum(c1+1,n-1)],-1),
        "c1_start":df.bar_start_timestamp.to_numpy()[c1],
        "c1_completion":clock[c1],"c2_completion":clock[np.minimum(c1+1,n-1)],
        "direction":direction[c1],"prior_run":prior,"prior_bin":bins,
        "c1_window":[session_window(x) for x in clock[c1]],
        "decision_window":[session_window(x) for x in clock[np.minimum(c1+1,n-1)]],
        "main_prior":main,"common_eligible":eligible,"c1_same_second":same[c1],
        "c2_same_second":same[np.minimum(c1+1,n-1)],
        "c2_follows":c2_follow,"c2_old_trend":c2_old,"c2_doji":c2_doji,
        "c3_follows":c3_follow,"c4_follows":c4_follow,"c3_old_trend":c3_old,
        "immediate_two_success":c2_follow & c3_follow,
        "wait_two_success":c2_follow & c3_follow & c4_follow,
        "immediate_signed_ticks":np.where(eligible,immediate_ticks,np.nan),
        "immediate_mae_ticks":np.where(eligible,immediate_mae,np.nan),
        "wait_signed_ticks":np.where(eligible & c2_follow,wait_ticks,np.nan),
        "wait_mae_ticks":np.where(eligible & c2_follow,wait_mae,np.nan),
        "larger_direction":larger_dir,"larger_completion":larger_time,
        "larger_context":context,"larger_equal_second_tie":larger_tie,
        "gc_gap_excluded":excluded,
    })

    # B2 is the decision bar for ordinary adjacent same-direction pairs.
    b2 = np.arange(1,max(n-3,1))
    if len(b2):
        candidate_b2 = np.zeros(n, dtype=bool)
        candidate_b2[c1[main & c2_follow & (c1+1<n)]+1] = True
        pair = (direction[b2] != 0) & (direction[b2] == direction[b2-1])
        complete_pair = strict[b2-1] & strict[b2] & strict[b2+1] & strict[b2+2]
        excluded_candidate = pair & complete_pair & candidate_b2[b2]
        j = b2[pair & complete_pair & ~candidate_b2[b2]]
        baseline_ticks, baseline_mae = price_path(direction[j], o[j+1],o[j+3],
            l[j+1],l[j+2],h[j+1],h[j+2])
        baseline = pd.DataFrame({
            "product":product,"setting":setting,"session_date":date,"block":block,
            "b2_source_row":source[j],"b2_completion":clock[j],
            "direction":direction[j],"pair_run_age":length[j],
            "decision_window":[session_window(x) for x in clock[j]],
            "b3_follows":direction[j+1] == direction[j],
            "b4_follows":direction[j+2] == direction[j],
            "two_success":(direction[j+1] == direction[j]) & (direction[j+2] == direction[j]),
            "signed_ticks":baseline_ticks,"mae_ticks":baseline_mae,"gc_gap_excluded":excluded,
        })
        excluded_count = int(excluded_candidate.sum())
    else:
        baseline = pd.DataFrame()
        excluded_count = 0
    audit = {"date":date,"bars":n,"c1_signals":len(c1),
             "main_c1_signals":int(main.sum()),"main_common_eligible":int((main & eligible).sum()),
             "main_c2_confirmed":int((main & eligible & c2_follow).sum()),
             "main_excluded_completion_or_boundary":int((main & ~eligible).sum()),
             "main_c1_same_second":int((main & same[c1]).sum()),
             "ordinary_pairs":len(baseline),"candidate_pairs_removed_from_ordinary":excluded_count,
             "larger_equal_second_ties":int(larger_tie.sum())}
    return opportunities, baseline, audit
