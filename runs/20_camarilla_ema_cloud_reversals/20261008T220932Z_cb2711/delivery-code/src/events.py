"""Shared technical opportunities and independent future labels."""
import numpy as np
from fractions import Fraction
import pandas as pd
from .spec import COEFFICIENTS, HORIZONS, PRODUCTS, split_for
from .calendar import stamp, week, previous_weekday
from .core import FIVE, MINUTE, Episodes, cloud, pivots, rejection, forward_outcome, threshold_order, exact_price

def build_events(product, bars, coverage):
    rows = []
    lookup = coverage.set_index("day")
    day_groups = bars.groupby("day", sort=False)
    tick = PRODUCTS[product][0]
    for day, g in day_groups:
        r = lookup.loc[day]
        if not r.eligible and not r.session_eligible:
            continue
        split = split_for(day)
        if split is None:
            continue
        # Episodes process the entire current electronic session, not just the entry window.
        for pair, coefficient in COEFFICIENTS.items():
            support, resistance = pivots(r.prior_high, r.prior_low, r.prior_close, coefficient)
            states = {"core": Episodes(), "tolerance": Episodes()}
            last_cooldown = -100000
            previous = None
            for b in g.itertuples():
                approaches = previous is not None and previous.contract == b.contract and previous.ts + FIVE == b.ts
                for variant, tolerance in (("core", 0), ("tolerance", tick)):
                    d = rejection(previous.close, b.open, b.high, b.low, b.close, support, resistance, tolerance) if approaches and b.complete else 0
                    first = states[variant].step(d, b.high, b.low, support, resistance, b.complete, tolerance)
                    if d not in (-1, 1):
                        continue
                    entry_ts = b.ts + FIVE
                    entry_minute = b.minute_NY + 5
                    if not 500 <= entry_minute < 960:
                        continue
                    filters = cloud(d, b.close, b.fast, b.slow)
                    cooldown = 570 <= entry_minute < 690 and b.Index > last_cooldown + 10 if variant == "core" else False
                    if variant == "core" and cooldown:
                        last_cooldown = b.Index
                    pivot = support if d > 0 else resistance
                    body = abs(b.close - b.open)
                    wick = min(b.open, b.close) - b.low if d > 0 else b.high - max(b.open, b.close)
                    rows.append({"event_id": f"{product}-{pair}-{variant}-{b.ts}-{d}", "product": product, "pair": pair, "variant": variant, "day": day, "week": week(day), "year": int(day[:4]), "split": split, "direction": d, "side": "long" if d > 0 else "short", "confirmation_index": b.Index, "confirmation_ts": b.ts, "available_at": entry_ts, "entry_ts": entry_ts, "entry_minute_NY": entry_minute, "contract": b.contract, "pivot": float(pivot), "pivot_numerator": pivot.numerator, "pivot_denominator": pivot.denominator, "opposite_pivot": float(resistance if d > 0 else support), "opposite_numerator": (resistance if d > 0 else support).numerator, "opposite_denominator": (resistance if d > 0 else support).denominator, "prior_close": r.prior_close, "prior_range": r.prior_high-r.prior_low, "confirmation_high": b.high, "confirmation_low": b.low, "confirmation_close": b.close, "atr": b.atr, "fast": b.fast, "slow": b.slow, "first_episode": first, "cooldown": cooldown, "seed_valid": b.seed_valid, "strict_seed": b.seed_coverage == 1, "seed500_valid": b.seed500_valid, "strict_prior": r.strict_prior, "main_eligible": r.eligible, "session_eligible": r.session_eligible, "slope": bool(d*b.fast_slope > 0 and d*b.slow_slope > 0), "wick": bool(body > 0 and wick >= body), "relative_volume": b.relative_volume, "rvol": bool(b.relative_volume >= 1), "approach_distance": d*(previous.close-pivot)/b.atr, "approach_half_atr": bool(d*(previous.close-pivot) >= .5*b.atr), "penetration_atr": (pivot-b.low if d > 0 else b.high-pivot)/b.atr, "wick_body": wick/body if body else np.nan, "cloud_separation_atr": d*(b.fast-b.slow)/b.atr, "distance_cloud_atr": d*(b.close-b.slow)/b.atr, "prior_coverage": r.prior_coverage, **filters})
                # Continuation is a separate family at the outer pair, not a fade.
                if pair == "4" and approaches and b.complete:
                    d = 1 if exact_price(previous.close) < resistance and exact_price(b.close) > resistance and b.close > b.open else (-1 if exact_price(previous.close) > support and exact_price(b.close) < support and b.close < b.open else 0)
                    if d and 500 <= b.minute_NY + 5 < 960:
                        filters = cloud(d, b.close, b.fast, b.slow)
                        rows.append({"event_id": f"{product}-continuation-{b.ts}-{d}", "product": product, "pair": "4", "variant": "continuation", "day": day, "week": week(day), "year": int(day[:4]), "split": split, "direction": d, "side": "long" if d>0 else "short", "confirmation_index": b.Index, "confirmation_ts": b.ts, "available_at": b.ts+FIVE, "entry_ts": b.ts+FIVE, "entry_minute_NY": b.minute_NY+5, "contract": b.contract, "pivot": float(resistance if d>0 else support), "pivot_numerator": (resistance if d>0 else support).numerator, "pivot_denominator": (resistance if d>0 else support).denominator, "opposite_pivot": np.nan, "prior_close": r.prior_close, "prior_range": r.prior_high-r.prior_low, "confirmation_high": b.high, "confirmation_low": b.low, "confirmation_close": b.close, "atr": b.atr, "first_episode": True, "cooldown": True, "seed_valid": b.seed_valid, "main_eligible": r.eligible, "session_eligible": r.session_eligible, **filters})
                previous = b
    return pd.DataFrame(rows)

def select_events(events, pair="3", mode="alignment", extension="core", window_name="main", product=None):
    variant = "tolerance" if extension == "tolerance" else ("continuation" if extension == "continuation" else "core")
    sel = (events.pair == str(pair)) & (events.variant == variant) & events.seed_valid.fillna(False)
    sel &= events.cooldown.fillna(False) if extension == "cooldown" else events.first_episode.fillna(False)
    if window_name == "main":
        sel &= events.main_eligible & (events.entry_minute_NY >= 570) & (events.entry_minute_NY < 690)
    else:
        p = product or events["product"].iloc[0]
        a,b = (500, 620) if p == "GC" else (570, 960)
        sel &= events.session_eligible & (events.entry_minute_NY >= a) & (events.entry_minute_NY < b)
    if mode != "none":
        sel &= events[mode].fillna(False)
    if extension in ("slope", "wick", "rvol", "approach_half_atr"):
        sel &= events[extension].fillna(False)
    if extension == "strict":
        sel &= events.strict_prior.fillna(False) & events.strict_seed.fillna(False)
    if extension == "warm500":
        sel &= events.seed500_valid.fillna(False)
    if extension == "rollbuffer":
        # Two additional calendar weekdays after the incoming mapping starts.
        sel &= events.rollbuffer_ok
    return events.loc[sel].copy()

def exact_range_hit(low, high, event):
    if not len(low) or not np.isfinite(event.opposite_pivot):
        return False
    p = Fraction(int(event.opposite_numerator),int(event.opposite_denominator))*1_000_000_000
    lo=np.rint(low*1_000_000_000).astype(np.int64)
    hi=np.rint(high*1_000_000_000).astype(np.int64)
    return bool(((lo*p.denominator<=p.numerator)&(hi*p.denominator>=p.numerator)).any())


def label_paths(events, bars, minutes):
    ts_to_bar = {int(t): i for i,t in enumerate(bars.ts)}
    minute_ts = minutes.ts.to_numpy()
    mhigh, mlow, mclose = (minutes[c].to_numpy() for c in ("high", "low", "close"))
    rows, orders = [], []
    for e in events.itertuples():
        i = ts_to_bar.get(e.entry_ts)
        entered = i is not None and int(bars.iloc[i]["first"]) == e.entry_ts and np.isfinite(bars.iloc[i].open) and bars.iloc[i].contract == e.contract
        entry = float(bars.iloc[i].open) if entered else np.nan
        deadline = stamp(e.day, 960)
        for h in (*HORIZONS, 0):
            bars_needed = h if h else int((deadline-e.entry_ts)//FIVE)
            out = forward_outcome(bars, i, bars_needed, entry, e.direction, e.atr, Fraction(int(e.pivot_numerator),int(e.pivot_denominator)), deadline) if entered else {"completed": False, "censor": "entry_open_absent"}
            row = {"event_id": e.event_id, "horizon": h, "entered": entered, "entry_reference": entry, **out}
            rows.append(row)
            start = np.searchsorted(minute_ts, e.entry_ts)
            end = np.searchsorted(minute_ts, min(deadline, e.entry_ts + bars_needed*FIVE))
            mt = minute_ts[start:end]
            expected_m = e.entry_ts + np.arange(bars_needed*5)*MINUTE
            valid = len(mt) == bars_needed*5 and np.array_equal(mt, expected_m)
            if len(mt):
                # End any measurable partial path at its FIRST missing interval.
                miss = np.flatnonzero(mt != expected_m[:len(mt)])
                bad = np.flatnonzero(~minutes.valid.iloc[start:end].to_numpy())
                usable = min([len(mt), *([int(miss[0])] if len(miss) else []), *([int(bad[0])] if len(bad) else [])])
                valid = valid and not len(bad)
                f = (mhigh[start:start+usable]-entry if e.direction>0 else entry-mlow[start:start+usable])/e.atr
                a = (entry-mlow[start:start+usable] if e.direction>0 else mhigh[start:start+usable]-entry)/e.atr
            else:
                usable, f, a = 0, np.array([]), np.array([])
            for threshold in (.5, 1, 2):
                orders.append({"event_id": e.event_id, "horizon": h, "threshold_ATR": threshold, "order": threshold_order(f, a, threshold, valid) if entered else "entry_cancelled", "observed_minutes": usable, "complete_minute_path": valid, "MFE_first_interval_minute": int(np.argmax(f))+1 if len(f) and max(f)>0 else np.nan, "MAE_first_interval_minute": int(np.argmax(a))+1 if len(a) and max(a)>0 else np.nan, "recovery_interval_minute": int(np.flatnonzero((np.cumsum(a>0)>0)&(f>=0))[0])+1 if len(f) and ((np.cumsum(a>0)>0)&(f>=0)).any() else np.nan, "prior_close_hit": bool(len(f) and ((mlow[start:start+usable] <= e.prior_close)&(mhigh[start:start+usable] >= e.prior_close)).any()), "opposite_pivot_hit": exact_range_hit(mlow[start:start+usable],mhigh[start:start+usable],e)})
    return pd.DataFrame(rows), pd.DataFrame(orders)
