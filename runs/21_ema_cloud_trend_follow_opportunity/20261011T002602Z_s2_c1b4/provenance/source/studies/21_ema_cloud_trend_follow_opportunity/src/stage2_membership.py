"""Candle geometry, accepted membership and retrospective shared episodes.

Nothing in this module is read by either branch's signal state machine.
Warmup first counterparts remain first; outcomes are not calculated here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .outcomes import _boundary

KEY = ["product", "interval_minutes", "timestamp"]
START = _boundary("2018-01-01")
END = _boundary("2021-01-01")
EPISODE_COLUMNS = ["shared_episode_id", "product", "interval_minutes", "contract", "direction", "side",
    "start_timestamp", "start_available_at", "last_timestamp", "last_available_at", "termination_timestamp",
    "end_reason", "status", "start_in_development", "contains_development", "first_fast_event_id",
    "first_fast_timestamp", "first_fast_in_development", "first_slow_event_id", "first_slow_timestamp",
    "first_slow_in_development", "same_bar_slow_contact", "strictly_later_slow_contact", "strictly_later_slow_signal",
    "first_later_slow_contact_timestamp", "first_later_slow_signal_timestamp", "retrospective_scope_reason"]
PAIR_EXTRA_COLUMNS = ["pair_id", "pair_relation", "pair_in_development", "pair_scope", "fast_reference_price",
    "slow_reference_price", "slow_minus_fast_signal_minutes", "slow_minus_fast_reference_points"]


def _in_development(value) -> bool:
    return pd.notna(value) and START <= pd.Timestamp(value) < END


def _timestamps(frame: pd.DataFrame) -> pd.DataFrame:
    for column in frame.columns:
        if column.endswith("timestamp") or column in ("start_available_at", "last_available_at"):
            frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def attach_episode_metadata(events: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    """Attach signal-time episode identity without replacing branch arm IDs."""
    out = events.drop(columns=["shared_episode_id"], errors="ignore").merge(
        membership[KEY + ["shared_episode_id"]], on=KEY, how="left", validate="many_to_one", sort=False)
    if out.shared_episode_id.isna().any():
        raise ValueError("an accepted event has no active geometric episode")
    return out


def _union(events: pd.DataFrame) -> pd.DataFrame:
    development = events.loc[events.timestamp.ge(START) & events.timestamp.lt(END)].copy()
    rows = []
    union_keys = ["product", "interval_minutes", "direction", "timestamp"]
    identity_fields = ["contract", "side", "reference_price", "entry_atr", "entry_at", "available_at", "signal_idx",
                       "ema20", "ema50", "feature_source_timestamp", "feature_available_at", "feature_contract"]
    for _, group in development.groupby(union_keys, sort=False, dropna=False):
        if group.touch_mode.duplicated().any() or len(group) > 2:
            raise ValueError("union contains duplicate accepted branch/bar identity")
        if len(group) == 2:
            for column in identity_fields:
                if column in group and not group[column].iloc[0:1].reset_index(drop=True).equals(group[column].iloc[1:2].reset_index(drop=True)):
                    raise ValueError("same-bar dual reference/feature identity mismatch: " + column)
        selected = group.loc[group.touch_mode.eq("slow")].iloc[0] if group.touch_mode.eq("slow").any() else group.iloc[0]
        row = selected.to_dict()
        row["representative_event_id"] = row["event_id"]
        row["fast_event_id"] = group.loc[group.touch_mode.eq("fast"), "event_id"].iloc[0] if group.touch_mode.eq("fast").any() else None
        row["slow_event_id"] = group.loc[group.touch_mode.eq("slow"), "event_id"].iloc[0] if group.touch_mode.eq("slow").any() else None
        row["accepted_membership"] = "both" if len(group) == 2 else str(selected.touch_mode) + "_only"
        row["union_id"] = f'{selected["product"]}|{int(selected.interval_minutes)}m|{selected.timestamp.isoformat()}|{selected.side}|union'
        row["event_id"], row["touch_mode"] = row["union_id"], "union"
        rows.append(row)
    columns = list(events.columns) + ["representative_event_id", "fast_event_id", "slow_event_id", "accepted_membership", "union_id"]
    result = pd.DataFrame(rows, columns=list(dict.fromkeys(columns)))
    if not result.empty:
        result = result.sort_values(KEY, kind="stable").reset_index(drop=True)
    return result


def build_membership(mapped_bars: pd.DataFrame, technical_long: pd.DataFrame,
                     events_long: pd.DataFrame, endpoint="2021-01-01") -> dict[str, pd.DataFrame]:
    """Build a full causal membership roster and separate shared episodes.

    Reset terminates an episode before its bar. A valid departure on that bar
    can start a new one. Known scheduled closures do not end an episode.
    ``termination_timestamp`` is excluded; ``last_timestamp`` is included.
    """
    end = _boundary(endpoint)
    if end > END:
        raise ValueError("Stage 2 endpoint cannot extend into reserved outcomes")
    membership = mapped_bars.copy().reset_index(drop=True)
    membership["timestamp"] = pd.to_datetime(membership.timestamp, utc=True)
    membership["available_at"] = pd.to_datetime(membership.available_at, utc=True)
    if "interval_minutes" not in membership:
        intervals = technical_long.interval_minutes.unique()
        if len(intervals) != 1:
            raise ValueError("mapped roster requires interval identity")
        membership["interval_minutes"] = int(intervals[0])
    if membership.duplicated(KEY).any():
        raise ValueError("duplicate membership roster identity")
    if membership.timestamp.ge(end).any() or membership.available_at.gt(end).any():
        raise ValueError("membership input extends beyond development endpoint")
    membership = membership.sort_values(KEY, kind="stable").reset_index(drop=True)
    branch_fields = ["accepted", "event_id", "suppression_reason", "armed_before", "armed_after", "penetration"]
    if set(technical_long.touch_mode.unique()) != {"fast", "slow"}:
        raise ValueError("both independent technical streams are required")
    for branch in ("fast", "slow"):
        technical = technical_long.loc[technical_long.touch_mode.eq(branch)]
        if len(technical) != len(membership) or technical.duplicated(KEY).any():
            raise ValueError("technical branch must preserve every scheduled slot")
        columns = KEY + branch_fields + (["direction", "side", "reset_reason"] if branch == "slow" else [])
        renamed = {field: branch + "_" + ("reason" if field == "suppression_reason" else field) for field in branch_fields}
        membership = membership.merge(technical[columns].rename(columns=renamed), on=KEY, how="left", validate="one_to_one", sort=False)
        if membership[branch + "_accepted"].isna().any():
            raise ValueError("technical and mapped roster keys differ")
        accepted_ids = set(technical.loc[technical.accepted, "event_id"])
        event_ids = set(events_long.loc[events_long.touch_mode.eq(branch), "event_id"])
        if accepted_ids != event_ids:
            raise ValueError("accepted technical IDs and full causal events differ")
    membership["eligible"] = membership.usable.fillna(False).astype(bool) & membership.feature_valid.fillna(False).astype(bool)
    finite = np.isfinite(membership[["low", "high", "ema20", "ema50"]].to_numpy(float)).all(axis=1)
    defined = membership.eligible.to_numpy() & finite & membership.low.le(membership.high).to_numpy()
    fast_touch = defined & membership.low.le(membership.ema20).to_numpy() & membership.high.ge(membership.ema20).to_numpy()
    slow_touch = defined & membership.low.le(membership.ema50).to_numpy() & membership.high.ge(membership.ema50).to_numpy()
    membership["fast_touch"], membership["slow_touch"] = fast_touch, slow_touch
    membership["geometry"] = np.select([~defined, fast_touch & slow_touch, fast_touch, slow_touch],
                                          ["undefined", "both", "fast_only", "slow_only"], default="neither")
    membership["accepted_membership"] = np.select(
        [membership.fast_accepted & membership.slow_accepted, membership.fast_accepted, membership.slow_accepted],
        ["both", "fast_only", "slow_only"], default="neither")
    membership["full_departure"] = defined & np.where(membership.direction.eq(1),
        membership.low.gt(membership[["ema20", "ema50"]].max(axis=1)),
        np.where(membership.direction.eq(-1), membership.high.lt(membership[["ema20", "ema50"]].min(axis=1)), False))
    membership["shared_episode_id"] = None
    shared_ids = np.full(len(membership), None, dtype=object)
    episodes, pairs = [], []
    lookup = events_long.set_index("event_id", verify_integrity=True)
    for (product, interval), group in membership.groupby(["product", "interval_minutes"], sort=False):
        active = None
        previous_departure = False
        rows = group[["timestamp", "available_at", "contract", "direction", "side", "reset_reason", "full_departure",
            "fast_accepted", "slow_accepted", "fast_event_id", "slow_event_id", "slow_touch"]].itertuples()

        def finish(reason, termination):
            nonlocal active
            if active is None:
                return
            active.update(termination_timestamp=termination, end_reason=reason,
                status="resolved" if reason == "new_departure" else "endpoint" if reason == "development_endpoint" else "interrupted")
            first_fast = active["first_fast_timestamp"]
            if pd.isna(first_fast):
                active["retrospective_scope_reason"] = "no_fast_event"
            elif not active["first_fast_in_development"]:
                active["retrospective_scope_reason"] = "outside_scope_warmup_first_fast"
            else:
                for field in ("strictly_later_slow_contact", "strictly_later_slow_signal"):
                    if active[field] is not True:
                        active[field] = False if reason == "new_departure" else None
                active["retrospective_scope_reason"] = "resolved_new_departure" if reason == "new_departure" else "interrupted:" + reason
            pair = active.copy()
            f, s = active["first_fast_event_id"], active["first_slow_event_id"]
            ft, st = active["first_fast_timestamp"], active["first_slow_timestamp"]
            pair["pair_id"] = active["shared_episode_id"] + "|first_pair"
            pair["pair_relation"] = ("same_bar" if ft == st else "fast_before_slow" if ft < st else "slow_before_fast") if f and s else "fast_only" if f else "slow_only" if s else "neither"
            fd, sd = active["first_fast_in_development"], active["first_slow_in_development"]
            pair["pair_in_development"] = bool(f and s and fd and sd)
            pair["pair_scope"] = "both_development" if pair["pair_in_development"] else "warmup_counterpart" if f and s and (fd or sd) else "outside_scope" if f and s else "unpaired_development" if fd or sd else "unpaired_warmup" if f or s else "no_accepted"
            pair["fast_reference_price"] = float(lookup.loc[f, "reference_price"]) if f else np.nan
            pair["slow_reference_price"] = float(lookup.loc[s, "reference_price"]) if s else np.nan
            pair["slow_minus_fast_signal_minutes"] = (st - ft).total_seconds() / 60 if pair["pair_in_development"] else np.nan
            pair["slow_minus_fast_reference_points"] = pair["slow_reference_price"] - pair["fast_reference_price"] if pair["pair_in_development"] else np.nan
            episodes.append(active.copy())
            pairs.append(pair)
            active = None

        for row in rows:
            reset = str(row.reset_reason)
            if reset:
                finish(reset, row.timestamp)
                previous_departure = False
            departure = bool(row.full_departure)
            if departure and (active is None or not previous_departure):
                finish("new_departure", row.timestamp)
                episode_id = f'{product}|{int(interval)}m|{row.contract}|{row.timestamp.isoformat()}|{row.side}|shared_episode'
                active = dict(shared_episode_id=episode_id, product=product, interval_minutes=int(interval), contract=row.contract,
                    direction=int(row.direction), side=row.side, start_timestamp=row.timestamp, start_available_at=row.available_at,
                    start_in_development=_in_development(row.timestamp), contains_development=False,
                    first_fast_event_id=None, first_fast_timestamp=pd.NaT, first_fast_in_development=False,
                    first_slow_event_id=None, first_slow_timestamp=pd.NaT, first_slow_in_development=False,
                    same_bar_slow_contact=None, strictly_later_slow_contact=None, strictly_later_slow_signal=None,
                    first_later_slow_contact_timestamp=pd.NaT, first_later_slow_signal_timestamp=pd.NaT)
            if active is not None:
                shared_ids[row.Index] = active["shared_episode_id"]
                active["last_timestamp"], active["last_available_at"] = row.timestamp, row.available_at
                active["contains_development"] |= _in_development(row.timestamp)
                for branch in ("fast", "slow"):
                    if getattr(row, branch + "_accepted") and active["first_" + branch + "_event_id"] is None:
                        active["first_" + branch + "_event_id"] = getattr(row, branch + "_event_id")
                        active["first_" + branch + "_timestamp"] = row.timestamp
                        active["first_" + branch + "_in_development"] = _in_development(row.timestamp)
                        if branch == "fast" and active["first_fast_in_development"]:
                            active["same_bar_slow_contact"] = bool(row.slow_touch)
                if active["first_fast_in_development"] and row.timestamp > active["first_fast_timestamp"]:
                    for field, timefield, observed in (("strictly_later_slow_contact", "first_later_slow_contact_timestamp", row.slow_touch),
                                                      ("strictly_later_slow_signal", "first_later_slow_signal_timestamp", row.slow_accepted)):
                        if observed and active[field] is not True:
                            active[field], active[timefield] = True, row.timestamp
            previous_departure = departure
        finish("development_endpoint", end)
    membership["shared_episode_id"] = shared_ids
    episode_frame = _timestamps(pd.DataFrame(episodes, columns=EPISODE_COLUMNS))
    pair_frame = _timestamps(pd.DataFrame(pairs, columns=EPISODE_COLUMNS + PAIR_EXTRA_COLUMNS))
    attached = attach_episode_metadata(events_long, membership)
    return {"membership": membership, "episodes": episode_frame, "pairs": pair_frame, "union": _union(attached)}
