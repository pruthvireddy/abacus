"""Numerical primitives with no input/output or research selection."""
import math
from fractions import Fraction
import numpy as np
import pandas as pd

MINUTE = 60_000_000_000
FIVE = 5 * MINUTE

def exact_price(value):
    """Recover the pinned 1e-9 fixed-point price; never a contact tolerance."""
    return Fraction(int(round(float(value)*1_000_000_000)),1_000_000_000)

def pivots(high, low, close, coefficient):
    if not all(np.isfinite([high, low, close])) or high < low:
        return (np.nan, np.nan)
    coefficient=Fraction(str(coefficient)).limit_denominator(1000000)
    h,l,c=map(exact_price,(high,low,close))
    return c - coefficient * (h-l), c + coefficient * (h-l)

def indicator_segment(high, low, close):
    n = len(close)
    fast, slow, atr = [np.full(n, np.nan) for _ in range(3)]
    tr_seed = []
    for i, c in enumerate(close):
        fast[i] = c if i == 0 else fast[i-1] + (2 / 21) * (c - fast[i-1])
        slow[i] = c if i == 0 else slow[i-1] + (2 / 51) * (c - slow[i-1])
        tr = high[i] - low[i] if i == 0 else max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
        if i < 14:
            tr_seed.append(tr)
            if i == 13:
                atr[i] = np.mean(tr_seed)
        else:
            atr[i] = atr[i-1] + (tr - atr[i-1]) / 14
    return fast, slow, atr

def rejection(previous, o, h, l, c, support, resistance, tolerance=0):
    if not np.isfinite(np.asarray([previous, o, h, l, c, support, resistance],dtype=float)).all():
        return None
    previous,o,h,l,c=map(exact_price,(previous,o,h,l,c))
    support=support if isinstance(support,Fraction) else exact_price(support)
    resistance=resistance if isinstance(resistance,Fraction) else exact_price(resistance)
    tolerance=exact_price(tolerance)
    if l <= support + tolerance and h >= resistance - tolerance:
        return 0
    if previous > support and o >= support and l <= support + tolerance and c > support and c > o:
        return 1
    if previous < resistance and o <= resistance and h >= resistance - tolerance and c < resistance and c < o:
        return -1
    return 0

def cloud(d, c, fast, slow):
    if not np.isfinite([c, fast, slow]).all():
        return {m: None for m in ("alignment", "outside", "alignment_outside")}
    alignment = d * (fast - slow) > 0
    outside = d * (c - fast) > 0 and d * (c - slow) > 0
    return {"alignment": bool(alignment), "outside": bool(outside), "alignment_outside": bool(alignment and outside)}

class Episodes:
    """The first technical event consumes the opportunity before any EMA test."""
    def __init__(self):
        self.consumed = {1: False, -1: False}

    def step(self, d, h, l, support, resistance, complete=True, tolerance=0):
        if not complete or not np.isfinite(np.asarray([h,l,support,resistance],dtype=float)).all():
            return False
        h,l=map(exact_price,(h,l))
        support=support if isinstance(support,Fraction) else exact_price(support)
        resistance=resistance if isinstance(resistance,Fraction) else exact_price(resistance)
        tolerance=exact_price(tolerance)
        if complete and l > support + tolerance:
            self.consumed[1] = False
        if complete and h < resistance - tolerance:
            self.consumed[-1] = False
        if d in (1, -1):
            accepted = not self.consumed[d]
            self.consumed[d] = True
            return accepted
        return False

def tick_round(value, tick, direction):
    scaled = value / tick
    return (math.ceil(scaled - 1e-9) if direction > 0 else math.floor(scaled + 1e-9)) * tick

def tick_valid(value, tick):
    return abs(value / tick - round(value / tick)) < 1e-6

def excursions(d, entry, high, low, close, atr):
    if not len(high) or atr <= 0:
        return None
    favorable = high - entry if d > 0 else entry - low
    adverse = entry - low if d > 0 else high - entry
    return {"mfe": max(0., float(max(favorable))) / atr,
            "mae": max(0., float(max(adverse))) / atr,
            "delta": d * (float(close[-1]) - entry) / atr,
            "delta_points": d * (float(close[-1]) - entry),
            "literal_above": bool(close[-1] > entry)}

def threshold_order(favorable, adverse, threshold, complete=True):
    f = np.flatnonzero(favorable >= threshold)
    a = np.flatnonzero(adverse >= 1)
    if len(f) and (not len(a) or f[0] < a[0]):
        return "favorable_first"
    if len(a) and (not len(f) or a[0] < f[0]):
        return "adverse_first"
    if len(f) and len(a):
        return "same_minute_ambiguous"
    return "neither" if complete else "censored"

def forward_outcome(bars, index, horizon, entry, direction, atr, pivot, deadline):
    """Strict uninterrupted path; entry bar is one, signal bar is excluded."""
    path = bars.iloc[index:index + horizon]
    start = int(bars.iloc[index].ts)
    expected = start + np.arange(horizon, dtype=np.int64) * FIVE
    valid = (len(path) == horizon and np.array_equal(path.ts.to_numpy(), expected)
             and bool(path.complete.all()) and int(path.iloc[-1].ts) + FIVE <= deadline
             and path.contract.nunique() == 1 and path.day.nunique() == 1)
    if not valid:
        return {"completed": False, "censor": "missing_partial_roll_or_deadline"}
    out = excursions(direction, entry, path.high.to_numpy(), path.low.to_numpy(), path.close.to_numpy(), atr)
    exact_pivot=pivot if isinstance(pivot,Fraction) else exact_price(pivot)
    out.update(completed=True, censor="", defended=bool(direction * (exact_price(path.iloc[-1].close) - exact_pivot) > 0), favorable=out["delta"] > 0, mfe_gt_mae=out["mfe"] > out["mae"])
    return out
