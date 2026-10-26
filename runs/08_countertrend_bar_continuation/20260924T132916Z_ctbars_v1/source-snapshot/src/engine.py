"""Study 08 extraction. All clock values in enhanced files are NY wall time."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


TICKS = {"ES": .25, "GC": .1, "NQ": .25}
READ_COLS = ["source_row", "source_timestamp", "bar_start_timestamp",
             "bar_completion_timestamp_proxy", "bar_duration_seconds_proxy",
             "completion_proxy_status", "session_date_proxy", "open", "high", "low", "close"]
STATUS_STRICT = "next_bar_start_proxy"
STATUS_SAME = "next_bar_start_same_second"


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
        checked.append({"path": record["path"], "sha256": actual, "bytes": path.stat().st_size})
    return checked


def session_window(clock: str) -> str:
    t = clock[-8:]
    if t >= "18:00:00" or t < "03:00:00": return "asia"
    if t < "09:30:00": return "london_pre_ny"
    if t < "12:00:00": return "ny_morning"
    if t < "16:00:00": return "ny_afternoon"
    return "transition"


def run_lengths(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dojis have length zero and terminate both neighboring directional runs."""
    n = len(direction)
    lengths = np.zeros(n, dtype=np.int32)
    starts = np.arange(n, dtype=np.int32)
    ends = np.arange(n, dtype=np.int32)
    for i in range(n):
        if direction[i] and i and direction[i] == direction[i-1]:
            lengths[i] = lengths[i-1] + 1
            starts[i] = starts[i-1]
        elif direction[i]:
            lengths[i] = 1
    for i in range(n-2, -1, -1):
        if direction[i] and direction[i] == direction[i+1]:
            ends[i] = ends[i+1]
    return lengths, starts, ends


def iter_sessions(path: Path):
    """Read one complete inferred session at a time, including chunk boundaries."""
    carry = None
    for chunk in pd.read_csv(path, sep=";", usecols=READ_COLS, chunksize=200_000):
        if carry is not None:
            chunk = pd.concat([carry, chunk], ignore_index=True)
        dates = chunk["session_date_proxy"].to_numpy()
        cuts = np.flatnonzero(dates[1:] != dates[:-1]) + 1
        start = 0
        for stop in cuts:
            yield chunk.iloc[start:stop].copy().reset_index(drop=True)
            start = int(stop)
        carry = chunk.iloc[start:].copy()
    if carry is not None and len(carry):
        yield carry.reset_index(drop=True)


def larger_states(path: Path, tick: float) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    states = {}
    for df in iter_sessions(path):
        ok = df["completion_proxy_status"].eq(STATUS_STRICT).to_numpy()
        t = pd.to_datetime(df.loc[ok, "bar_completion_timestamp_proxy"],
                           format="%Y-%m-%d %H:%M:%S").to_numpy(dtype="datetime64[s]")
        d = np.sign(np.rint(df.loc[ok, "close"].to_numpy()/tick)-
                    np.rint(df.loc[ok, "open"].to_numpy()/tick)).astype(np.int8)
        states[str(df["session_date_proxy"].iloc[0])] = (t, d)
    return states


def extract_session(df: pd.DataFrame, product: str, setting: int,
                    larger: tuple[np.ndarray, np.ndarray] | None = None) -> tuple[pd.DataFrame, dict]:
    n = len(df)
    date = str(df["session_date_proxy"].iloc[0])
    tick = TICKS[product]
    o, h, l, c = [np.rint(df[k].to_numpy(dtype=np.float64)/tick).astype(np.int64)
                  for k in ("open", "high", "low", "close")]
    if np.any(h < np.maximum.reduce([o,l,c])) or np.any(l > np.minimum.reduce([o,h,c])):
        raise ValueError(f"invalid OHLC {product} {setting} {date}")
    d = np.sign(c-o).astype(np.int8)
    lengths, starts, ends = run_lengths(d)
    strict = df["completion_proxy_status"].eq(STATUS_STRICT).to_numpy()
    same = df["completion_proxy_status"].eq(STATUS_SAME).to_numpy()
    i = np.flatnonzero((d[1:] != 0) & (d[1:] == -d[:-1]) & (lengths[:-1] > 0)) + 1
    if not len(i): return pd.DataFrame(), {"date":date,"bars":n,"signals":0}
    p = i-1
    prior_len = lengths[p]
    prior_start = starts[p]
    binname = np.select([prior_len <= 2, prior_len <= 4, prior_len <= 7],
                        ["1-2", "3-4", "5-7"], default="8+")
    start_t = pd.to_datetime(df["bar_start_timestamp"]).to_numpy(dtype="datetime64[s]")
    complete_t = pd.to_datetime(df["bar_completion_timestamp_proxy"],
                                format="%Y-%m-%d %H:%M:%S", errors="coerce").to_numpy(dtype="datetime64[s]")
    # Strictly completed prior bars have a nonnegative next-bar-start duration.
    durations = df["bar_duration_seconds_proxy"].to_numpy(dtype=np.float64)
    rng = np.maximum(h-l, 1)
    adverse = np.where(d > 0, o-l, h-o)/rng
    opposing = np.where(d > 0, h-c, c-l)/rng
    prior_opp = np.empty(len(i), dtype=np.float64)
    pace = np.empty(len(i), dtype=np.float64)
    for k,(lo,hi) in enumerate(zip(prior_start,p)):
        prior_opp[k] = np.mean(opposing[lo:hi+1])
        pace[k] = np.nanmedian(durations[lo:hi+1])
    body = np.abs(c[i]-o[i])/rng[i]
    close_loc = np.where(d[i] > 0, (c[i]-l[i])/rng[i], (h[i]-c[i])/rng[i])
    break_prev = np.where(d[i] > 0, c[i] > h[p], c[i] < l[p])
    net_units_per_bar = d[p]*(c[p]-o[prior_start])/setting/prior_len
    horizon_complete = i+2 < n
    valid = i+2 < n
    horizon_complete[valid] &= strict[i[valid]+1] & strict[i[valid]+2]
    primary = horizon_complete & strict[i]
    three = primary & (i+3 < n)
    valid3 = i+3 < n
    three[valid3] &= strict[i[valid3]+3]
    c2 = np.zeros(len(i), dtype=bool)
    c3 = np.zeros(len(i), dtype=bool)
    c4 = np.zeros(len(i), dtype=bool)
    c2[i+1<n] = d[i[i+1<n]+1] == d[i[i+1<n]]
    c3[i+2<n] = d[i[i+2<n]+2] == d[i[i+2<n]]
    c4[i+3<n] = d[i[i+3<n]+3] == d[i[i+3<n]]
    subsequent = ends[i]-i
    censored = ends[i] == n-1
    clock = df["bar_completion_timestamp_proxy"].fillna("").astype(str).to_numpy()
    windows = np.array([session_window(x) if x else "unavailable" for x in clock[i]])
    block = "early" if date <= "2021-12-31" else ("middle" if date <= "2023-12-31" else "recent")
    # Search side='left' guarantees a larger completion strictly before signal.
    larger_dir = np.zeros(len(i), dtype=np.int8)
    larger_time = np.full(len(i), "", dtype="U19")
    equal_tie = np.zeros(len(i), dtype=bool)
    if larger is not None and len(larger[0]):
        times, directions = larger
        loc = np.searchsorted(times, complete_t[i], side="left")-1
        has = (loc >= 0) & ~np.isnat(complete_t[i])
        larger_dir[has] = directions[loc[has]]
        larger_time[has] = np.datetime_as_string(times[loc[has]], unit="s")
        equal_tie = (~np.isnat(complete_t[i]) &
                     (np.searchsorted(times, complete_t[i], side="right") >
                      np.searchsorted(times, complete_t[i], side="left")))
        if np.any(times[loc[has]] >= complete_t[i[has]]):
            raise AssertionError("larger look-ahead")
    context = np.where(larger_dir == 0, "unavailable", np.where(larger_dir == d[i], "aligned", "against"))
    out = pd.DataFrame({
        "product":product,"setting":setting,"session_date":date,"block":block,
        "source_row":df["source_row"].to_numpy()[i],
        "source_timestamp":df["source_timestamp"].to_numpy()[i],
        "c1_start":df["bar_start_timestamp"].to_numpy()[i],
        "c1_completion":clock[i],"direction":d[i],"prior_run":prior_len,"prior_bin":binname,
        "session_window":windows,"primary_eligible":primary,"horizon_complete":horizon_complete,
        "three_eligible":three,
        "c1_same_second":same[i],"c2_follows":c2,"c3_follows":c3,"c4_follows":c4,
        "c2_doji":np.where(i+1<n,d[np.minimum(i+1,n-1)]==0,False),
        "c3_doji":np.where(i+2<n,d[np.minimum(i+2,n-1)]==0,False),
        "subsequent_run_length":subsequent,"run_censored":censored,
        "body_ge_70":body>=.70,"close_loc_ge_80":close_loc>=.80,
        "adverse_wick_lt_20":adverse[i]<.20,"break_prev_extreme":break_prev,
        "prior_opposing_wick_lt_20":prior_opp<.20,
        "prior_net_units_per_bar_ge_075":net_units_per_bar>=.75,
        "prior_pace_lt_60s":pace<60,
        "larger_direction":larger_dir,"larger_completion":larger_time,
        "larger_context":context,"larger_equal_second_tie":equal_tie,
        "gc_gap_excluded": product == "GC" and date in {"2026-01-28","2026-02-04","2026-02-20","2026-03-19","2026-04-02"},
    })
    out["c2_c3_follow"] = out["c2_follows"] & out["c3_follows"]
    out["c2_c3_c4_follow"] = out["c2_c3_follow"] & out["c4_follows"]
    out["immediate_resumption"] = ~out["c2_follows"] & ~out["c2_doji"]
    return out, {"date":date,"bars":n,"signals":len(i),
                 "primary_eligible":int(primary.sum()),"same_second_signals":int(same[i].sum()),
                 "horizon_or_completion_excluded":int((~primary & strict[i]).sum()),
                 "signal_completion_excluded":int((~strict[i]).sum()),
                 "larger_equal_second_ties":int(equal_tie.sum())}
