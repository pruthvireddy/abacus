"""Causal one-minute reproduction of the supplied VP-HVN calculation.

Numerical profiles contain no study labels. The historical caller controls when
completed bars become available. Prices here are conventional contract points.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

_native = None


def enable_native(cache):
    """Build a source-hashed local accelerator in disposable workspace cache."""
    import ctypes
    import hashlib
    from pathlib import Path
    import subprocess
    source = Path(__file__).with_name("vp_hvn_native.cpp")
    target = Path(cache)/("vp_hvn_"+hashlib.sha256(source.read_bytes()).hexdigest()[:16]+".so")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = ["clang++", "-O2", "-std=c++17", "-shared", "-fPIC", "-ffp-contract=off", str(source), "-o", str(target)]
    if not target.exists():
        subprocess.run(command, check=True, capture_output=True)
    global _native
    _native = ctypes.CDLL(str(target))
    ptr = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    _native.vp_levels.argtypes = [ptr, ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_double, ptr]
    _native.hvn_build.argtypes = [ptr, ptr, ptr, ctypes.c_int, ctypes.c_double, ctypes.c_int,
                                  ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_double,
                                  ctypes.c_double, ptr, ptr]
    _native.hvn_build.restype = ctypes.c_int
    return {"command": command, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "compiler": subprocess.check_output(["clang++", "--version"], text=True).splitlines()[0]}


class Profile:
    """Absolute row grid; lower-coordinate POC and VA, exactly as in Pine."""
    def __init__(self, row: float = 4.0, va: float = .7):
        self.row, self.va = row, va
        self.levels = (math.nan, math.nan, math.nan)  # VAH, POC, VAL
        self.reset()

    def reset(self):
        # Pine init clears mass but deliberately retains reported levels.
        self.bins = np.empty(0, dtype=float)
        self.key = 0
        self.total = 0.0

    def add(self, high, low, volume):
        a, b = sorted((math.floor(low / self.row), math.floor(high / self.row)))
        volume = 0.0 if volume is None or not math.isfinite(volume) else float(volume)
        if not len(self.bins):
            self.key = a
            self.bins = np.zeros(b-a+1)
        else:
            left, right = max(0, self.key-a), max(0, b-(self.key+len(self.bins)-1))
            if left or right:
                self.bins = np.pad(self.bins, (left, right))
                self.key -= left
        self.bins[a-self.key:b-self.key+1] += volume / (b-a+1)
        self.total += volume

    def add_batch(self, high, low, volume):
        # Preserve sequential addition so true ties are not changed by a
        # difference-array reduction or floating-point reassociation.
        for h, l, v in zip(high, low, volume):
            self.add(h, l, v)

    def calculate(self):
        if self.total <= 0 or not len(self.bins):
            return self.levels
        if _native is not None:
            out = np.empty(3)
            _native.vp_levels(self.bins, len(self.bins), self.key, self.row, self.total*self.va, out)
            self.levels = tuple(out)
            return self.levels
        # Strict > in Pine: first maximum wins. Use no rounding/tolerance.
        p = int(np.argmax(self.bins))
        lo = hi = p
        cum, target = float(self.bins[p]), self.total*self.va
        while cum < target and (lo > 0 or hi < len(self.bins)-1):
            below = self.bins[lo-1] if lo else -1.0
            above = self.bins[hi+1] if hi < len(self.bins)-1 else -1.0
            if above >= below:
                hi += 1
                cum += self.bins[hi]
            else:
                lo -= 1
                cum += self.bins[lo]
        self.levels = ((self.key+hi)*self.row, (self.key+p)*self.row, (self.key+lo)*self.row)
        return self.levels


@dataclass
class Node:
    lo: float
    hi: float
    mid: float
    strength: float
    peak_row: int
    prominence: float
    node_id: str = ""
    candidate_id: str = ""
    match_ambiguous: bool = False


def composite(high, low, volume, row=1.0, smooth=3, peak_pct=.2,
              window=5, prominence_pct=.1, expansion=.6, width=2.0):
    """Pine low-anchored composite, adaptive 3000 row cap and capped bands."""
    high, low, volume = map(np.asarray, (high, low, volume))
    if not len(high):
        return [], {"rows": 0, "step": row, "mass": 0.0}
    if _native is not None:
        high, low, volume = [np.ascontiguousarray(x, dtype=float) for x in (high, low, volume)]
        out, meta = np.empty((3000, 6)), np.empty(5)
        count = _native.hvn_build(high, low, volume, len(high), row, smooth, peak_pct,
                                  window, prominence_pct, expansion, width, out, meta)
        nodes = [Node(float(x[0]), float(x[1]), float(x[2]), float(x[3]), int(x[4]), float(x[5])) for x in out[:count]]
        return nodes, {"rows": int(meta[0]), "step": meta[1], "mass": meta[2], "input_volume": meta[3], "base": meta[4]}
    base, top = float(low.min()), float(high.max())
    n = math.ceil((top-base)/row)+1
    if n > 3000:
        row = math.ceil(((top-base)/2999.0)/.25)*.25
        n = math.ceil((top-base)/row)+1
    a = np.floor((low-base)/row).astype(int)
    b = np.minimum(n-1, np.floor((high-base)/row).astype(int))
    mass = np.zeros(n)
    for aa, bb, vv in zip(a, b, volume):
        mass[aa:bb+1] += (0.0 if not math.isfinite(vv) else vv)/(bb-aa+1)
    half = smooth//2
    indices = np.arange(n)
    first, last = np.maximum(0, indices-half), np.minimum(n, indices+half+1)
    values = np.array([sum(mass[aa:bb])/(bb-aa) for aa, bb in zip(first, last)])
    vmax = values.max()
    nodes = []
    if vmax > 0:
        for r in np.flatnonzero(values >= vmax*(peak_pct*100.0)/100.0):
            v = values[r]
            neighbours = values[max(0, r-window):min(n, r+window+1)]
            if np.any(neighbours > v) or np.any(values[max(0, r-window):r] == v):
                continue
            lt = rt = float(v)
            q = r-1
            while q >= 0 and values[q] <= v:
                lt = min(lt, values[q]); q -= 1
            q = r+1
            while q < n and values[q] <= v:
                rt = min(rt, values[q]); q += 1
            prominence = v-max(lt, rt)
            if prominence < v*(prominence_pct*100.0)/100.0:
                continue
            floor = v-prominence*(expansion*100.0)/100.0
            left = right = int(r)
            while left > 0 and values[left-1] >= floor:
                left -= 1
            while right < n-1 and values[right+1] >= floor:
                right += 1
            mid = base+(r+.5)*row
            nodes.append(Node(max(base+left*row, mid-width/2),
                              min(base+(right+1)*row, mid+width/2),
                              mid, float(v), int(r), float(prominence)))
    return nodes, {"rows": n, "step": row, "mass": float(mass.sum()),
                   "input_volume": float(volume.sum()), "base": base}


def collides(a, b, gap):
    return a.lo <= b.hi+gap and a.hi >= b.lo-gap


def select(nodes, price, references, gap=2.0):
    """Filter BEFORE strength suppression, then distance/strength, side quotas."""
    reasons = {}
    eligible = []
    references = [x for x in references if x is not None and math.isfinite(x)]
    for i, n in enumerate(nodes):
        if n.lo <= price <= n.hi:
            reasons[i] = "contains_price"
        elif any(n.lo-gap <= x <= n.hi+gap for x in references):
            reasons[i] = "reference_collision"
        else:
            eligible.append(i)
    survivors = []
    # Equal strengths retain ascending candidate order (lower peak first).
    for i in sorted(eligible, key=lambda i: (-nodes[i].strength, i)):
        if any(collides(nodes[i], nodes[j], gap) for j in survivors):
            reasons[i] = "strength_suppressed"
        else:
            survivors.append(i)
    picked, counts, selected = [], {1: 0, -1: 0}, []
    for i in sorted(survivors, key=lambda i: (abs(nodes[i].mid-price), -nodes[i].strength, i)):
        side = 1 if nodes[i].lo > price else -1
        if counts[side] >= 2:
            reasons[i] = "side_quota"
        elif any(collides(nodes[i], nodes[j], gap) for j in picked):
            reasons[i] = "zone_clearance"
        else:
            counts[side] += 1
            picked.append(i)
            selected.append((i, side, counts[side]))
            reasons[i] = "selected"
    return selected, reasons


def match_nodes(nodes, previous, rebuild_id):
    """Conservative connected-component identities; preserve split/merge flags.

    Ambiguous connected matches share a lineage ID, preventing an ambiguous
    split from manufacturing a new first-touch opportunity.
    """
    links = {i: [j for j, p in enumerate(previous)
                 if n.lo <= p.hi and n.hi >= p.lo and abs(n.mid-p.mid) <= 2.0]
             for i, n in enumerate(nodes)}
    for i, n in enumerate(nodes):
        parents = links[i]
        shared = any(j in links[k] for j in parents for k in links if k != i)
        n.candidate_id = f"{rebuild_id}:{i}"
        n.match_ambiguous = len(parents) > 1 or shared or any(previous[j].match_ambiguous for j in parents)
        n.node_id = min((previous[j].node_id for j in parents), default=n.candidate_id)
    return nodes
