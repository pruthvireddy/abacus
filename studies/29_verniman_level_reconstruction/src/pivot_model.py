"""Translated synthetic oracle for experimental Study 29 pivot rules.

This is not a Pine interpreter and performs no data loading. Unit tests use
synthetic bars; explicit verification can feed retained chart exports. Passing
checks prove model arithmetic only, not native TradingView acceptance or fidelity
to Verniman's proprietary method. Profile arithmetic imports the unchanged Phase 1
model to retain its exact inclusive-floor allocation and tie conventions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from math import isfinite
from typing import Iterable

from reference_model import Bar, NY, Profile, UTC, clock, local


@dataclass(frozen=True)
class Edge:
    region_id: str
    side: str
    coordinate: float | None
    uncertainty: tuple[float, float] | None
    contrast: float | None
    status: str
    profile_id: str


@dataclass
class Region:
    region_id: str
    profile_id: str
    plateau: tuple[int, int]
    representative: int
    lo: int
    hi: int
    height: float
    saddle: float
    prominence: float
    mass: float
    width: float
    overlap: bool = False
    lower: Edge | None = None
    upper: Edge | None = None
    normalized_height: float | None = None
    normalized_prominence: float | None = None
    normalized_mass: float | None = None

    @property
    def bounds(self) -> tuple[float, float]:
        return self.lo * self.width, (self.hi + 1) * self.width

    def contains(self, price: float) -> bool:
        lo, hi = self.bounds
        return lo <= price <= hi


@dataclass(frozen=True)
class NodeLedger:
    regions: tuple[Region, ...]
    qualified: tuple[Region, ...]
    rejected: tuple[tuple[int, str], ...]
    omitted: int
    lvns: tuple[tuple[int, int, int, float], ...]
    profile_id: str


def edge(region: Region, side: str, bins: dict[int, float]) -> Edge:
    """E1 exact shared bin boundary with half-row measurement uncertainty."""
    inside = region.lo if side == "lower" else region.hi
    outside = inside - 1 if side == "lower" else inside + 1
    status = "qualified"
    contrast = None
    coordinate = None
    uncertainty = None
    if region.hi - region.lo + 1 < 2:
        status = "parent narrower than two rows"
    elif outside not in bins:
        status = "domain truncated"
    else:
        contrast = (bins[inside] - bins[outside]) / region.height
        if contrast < .10:
            status = "insufficient border contrast"
        else:
            coordinate = (region.lo if side == "lower" else region.hi + 1) * region.width
            uncertainty = coordinate - region.width / 2, coordinate + region.width / 2
    return Edge(region.region_id, side, coordinate, uncertainty, contrast, status, region.profile_id)


def nodes(bins: dict[int, float], *, width: float = 4.0,
          profile_id: str = "ON", cap: int = 8) -> NodeLedger:
    """N1 control; full qualified ledger retained even when presentation is capped."""
    if not bins or width <= 0 or cap < 1 or len(bins) > 6000:
        raise ValueError("missing/invalid/overflow distribution")
    low, high = min(bins), max(bins)
    if set(bins) != set(range(low, high + 1)):
        raise ValueError("distribution must retain every domain row")
    if not all(isfinite(x) and x >= 0 for x in bins.values()) or sum(bins.values()) <= 0:
        raise ValueError("missing/negative/zero profile mass")
    maximum = max(bins.values())
    total = sum(bins.values())
    candidates: list[Region] = []
    rejected: list[tuple[int, str]] = []
    i = low
    while i <= high:
        j = i
        while j < high and bins[j + 1] == bins[i]:
            j += 1
        p = bins[i]
        if i == low or j == high:
            rejected.append((i, "domain endpoint plateau"))
        elif bins[i - 1] < p and bins[j + 1] < p:
            minima = []
            for start, step in ((i - 1, -1), (j + 1, 1)):
                minimum = p
                k = start
                while low <= k <= high:
                    minimum = min(minimum, bins[k])
                    if bins[k] > p:
                        break
                    k += step
                minima.append(minimum)
            s = max(minima)
            d = p - s
            if p < .20 * maximum:
                rejected.append((i, "height"))
            elif d < .10 * maximum:
                rejected.append((i, "prominence"))
            else:
                threshold = s + .5 * d
                lo, hi = i, j
                while lo > low and bins[lo - 1] >= threshold:
                    lo -= 1
                while hi < high and bins[hi + 1] >= threshold:
                    hi += 1
                candidates.append(Region(f"{profile_id}/N1/{i}", profile_id,
                    (i, j), i, lo, hi, p, s, d,
                    sum(bins[k] for k in range(lo, hi + 1)), width))
        else:
            rejected.append((i, "not interior maximum"))
        i = j + 1
    candidates.sort(key=lambda r: (-r.height, -r.prominence, r.representative))
    qualified: list[Region] = []
    for r in candidates:
        if any(abs(r.representative - previous.representative) < 2 for previous in qualified):
            rejected.append((r.representative, "minimum separation"))
        else:
            qualified.append(r)
    # Overlap flags refer to all qualified parents, including capped parents.
    for i, r in enumerate(qualified):
        # Keep normalized reporting; compare in the original scale to avoid
        # creating threshold error solely by dividing by profile total first.
        r.normalized_height = r.height / total
        r.normalized_prominence = r.prominence / total
        r.normalized_mass = r.mass / total
        r.overlap = any(i != j and max(r.lo, other.lo) <= min(r.hi, other.hi)
                        for j, other in enumerate(qualified))
        r.lower, r.upper = edge(r, "lower", bins), edge(r, "upper", bins)
    kept = qualified[:cap]
    lvns = []
    ordered = sorted(kept, key=lambda r: r.representative)
    for left, right in zip(ordered, ordered[1:]):
        if left.hi + 1 >= right.lo:
            continue
        start, end = left.hi + 1, right.lo - 1
        minimum = min(bins[k] for k in range(start, end + 1))
        trough = min(k for k in range(start, end + 1) if bins[k] == minimum)
        trough_end = trough
        while trough_end < end and bins[trough_end + 1] == minimum:
            trough_end += 1
        if minimum <= .25 * min(left.height, right.height):
            lvns.append((trough, trough_end, trough, minimum))
    return NodeLedger(tuple(kept), tuple(qualified), tuple(rejected),
                      max(0, len(qualified) - cap), tuple(lvns[:7]), profile_id)


@dataclass(frozen=True)
class Selection:
    price: float | None
    reason: str
    origin: str
    fallback: bool
    fallback_status: str
    inputs: tuple[float | None, ...]
    tolerance: float
    confluence: tuple[tuple[str, float, str, float], ...] = ()


def select(yvah: float | None, ypoc: float | None, yval: float | None,
           onpoc: float | None, price: float | None, ledger: NodeLedger | None,
           *, tick: float = .25, width: float = 4) -> Selection:
    b = max(2 * tick, width / 2)
    values = yvah, ypoc, yval, onpoc, price
    if (tick <= 0 or width <= 0 or any(x is None or not isfinite(x) for x in values)
            or not yval <= ypoc <= yvah or ledger is None):
        return Selection(None, "Unavailable required input", "na", False, "unavailable", values, b)
    fallback = False
    detail = "none"
    if price < yval - b:
        pivot, reason, origin = yval, "Prior-value reclaim boundary", "YVAL"
    elif price > yvah + b:
        containing = [r for r in ledger.regions if r.contains(price)]
        eligible = [r for r in containing if r.lower is not None
                    and r.lower.status == "qualified" and r.lower.coordinate > yvah + b]
        overlap = any(r.overlap for r in containing)
        missing_edge = any(r.lower is None or r.lower.status != "qualified" for r in containing)
        incomplete = ledger.omitted > 0 or missing_edge
        if len(eligible) == 1 and not overlap and not incomplete:
            pivot = eligible[0].lower.coordinate
            reason, origin = "Hold higher auction", eligible[0].region_id + "/lower E1"
        elif len(eligible) > 1 or overlap:
            detail = "ambiguous: competing/overlapping regions"
        elif ledger.omitted:
            detail = "incomplete: region cap"
        elif missing_edge:
            detail = "incomplete: missing lower E1 evidence"
        else:
            detail = "absent: no eligible lower E1 edge"
        if detail != "none":
            pivot, reason, origin = yvah, "Prior-value boundary fallback", "YVAH"
            fallback = True
    elif onpoc < ypoc - b:
        pivot, reason, origin = yval, "Overnight value shifted lower", "YVAL"
    elif onpoc > ypoc + b:
        pivot, reason, origin = yvah, "Overnight value shifted higher", "YVAH"
    else:
        pivot, reason, origin = ypoc, "Balanced fallback — no unique directional divider", "YPOC"
        fallback, detail = True, "balanced"
    confluence = ()
    if origin in ("YVAH", "YPOC", "YVAL"):
        confluence = tuple((origin, pivot, e.region_id + "/" + e.side + " E1", e.coordinate)
            for r in ledger.regions for e in (r.lower, r.upper)
            if e is not None and e.status == "qualified" and abs(e.coordinate - pivot) <= width)
    return Selection(pivot, reason, origin, fallback, detail, values, b, confluence)


@dataclass
class CoverageWindow:
    start: datetime
    end: datetime
    row_size: float
    profile: Profile = field(init=False)
    last_close: datetime | None = None
    bars: int = 0
    coverage: bool = True
    last_price: float | None = None

    def __post_init__(self):
        self.profile = Profile(self.row_size)

    def add(self, bar: Bar):
        if not bar.confirmed:
            return
        expected = self.start if self.last_close is None else self.last_close
        self.coverage &= (bar.opened == expected
                          and bar.closed.astimezone(UTC) - bar.opened.astimezone(UTC) == timedelta(minutes=5)
                          and self.start <= bar.opened < bar.closed <= self.end)
        self.last_close, self.last_price = bar.closed, bar.close
        self.bars += 1
        self.profile.add(bar.high, bar.low, bar.volume)
        if not isfinite(bar.close):
            self.coverage = False

    @property
    def ready(self):
        expected = int((self.end.astimezone(UTC) - self.start.astimezone(UTC)).total_seconds() / 300)
        return self.coverage and self.last_close == self.end and self.bars == expected and self.profile.levels()[0] is not None


@dataclass(frozen=True)
class Frozen:
    trading_date: date
    cutoff: datetime
    last_included_open: datetime | None
    last_included_close: datetime | None
    mode: str
    selection: Selection
    rth_date: date | None


class PivotEngine:
    """Confirmed 5m-only stream model. No later bar can revise a day's freeze."""
    def __init__(self, *, tick=.25, row_ticks=16, standard=True, minutes=5):
        if not standard or minutes != 5:
            raise ValueError("Unsupported chart: standard five-minute candles required")
        self.tick, self.width = tick, tick * row_ticks
        self.day = None
        self.overnight = None
        self.rth = None
        self.rth_date = None
        self.latest_rth = None
        self.latest_rth_date = None
        self.frozen = None
        self.status = "waiting"
        self.up = self.down = 0
        self.acceptance = "unresolved"

    def accept(self, bar: Bar, *, realtime=False):
        if not bar.confirmed:
            return
        identity = clock(bar.opened)
        if identity is None:
            return
        if self.day != identity.trading_date:
            # Preserve the latest actually observed RTH; a partial observed window
            # is retained as invalid, rather than skipped in favor of an older day.
            if self.rth is not None:
                self.latest_rth, self.latest_rth_date = self.rth, self.rth_date
            self.day = identity.trading_date
            self.overnight = CoverageWindow(identity.futures_start, local(self.day, 9, 25), self.width)
            self.rth = None
            self.rth_date = None
            self.frozen = None
            self.status = "waiting"
            self.up = self.down = 0
            self.acceptance = "unresolved"
        cutoff = local(self.day, 9, 25)
        if bar.closed <= cutoff:
            self.overnight.add(bar)
        if identity.rth_start <= bar.opened < identity.rth_end:
            if self.rth is None:
                self.rth, self.rth_date = CoverageWindow(identity.rth_start, identity.rth_end, self.width), self.day
            self.rth.add(bar)
        if self.frozen is None and bar.closed >= cutoff:
            rth_ready = self.latest_rth is not None and self.latest_rth.ready
            on_ready = self.overnight.ready and bar.closed == cutoff
            if rth_ready and on_ready:
                refs = self.latest_rth.profile.levels()
                onpoc = self.overnight.profile.levels()[1]
                ledger = nodes(self.overnight.profile.bins, width=self.width,
                    profile_id=f"ON/{self.day}")
                selected = select(*refs, onpoc, bar.close, ledger, tick=self.tick, width=self.width)
                self.status = "ready"
            else:
                selected = select(None, None, None, None, None, None, tick=self.tick, width=self.width)
                self.status = "unavailable: missing terminal bar" if bar.closed != cutoff else "unavailable: incomplete/invalid session or history"
            self.frozen = Frozen(self.day, cutoff, self.overnight.last_close - timedelta(minutes=5) if self.overnight.last_close else None,
                self.overnight.last_close, "observed realtime" if realtime else "historically reconstructed", selected, self.latest_rth_date)
        if self.frozen is not None and self.frozen.selection.price is not None and bar.opened >= cutoff:
            price, b = self.frozen.selection.price, self.frozen.selection.tolerance
            self.up = self.up + 1 if bar.close > price + b else 0
            self.down = self.down + 1 if bar.close < price - b else 0
            self.acceptance = "bullish acceptance" if self.up >= 2 else ("bearish acceptance" if self.down >= 2 else "unresolved")

    def feed(self, bars: Iterable[Bar]):
        for bar in bars:
            self.accept(bar)


def alternate_reference(primary, reason, yvah, ypoc, yval, price):
    """Choose one distinct prior-value alternate from a frozen cutoff snapshot.

    This engineering fallback does not change the primary selection or rank
    overnight nodes. Inputs and the returned reference must be frozen together.
    Equality and distance ties use original prices without snapping or rounding.
    """
    from math import isfinite

    values = (primary, yvah, ypoc, yval, price)
    if not reason or any(value is None or not isfinite(value) for value in values):
        return None, "na"

    if reason == "Hold higher auction":
        candidates = ((yvah, "YVAH"), (ypoc, "YPOC"), (yval, "YVAL"))
    elif reason == "Balanced fallback — no unique directional divider":
        candidates = sorted(
            ((yval, "YVAL"), (yvah, "YVAH")),
            key=lambda item: (abs(item[0] - price), item[0]),
        )
    elif primary == yval:
        candidates = ((ypoc, "YPOC"), (yvah, "YVAH"))
    elif primary == yvah:
        candidates = ((ypoc, "YPOC"), (yval, "YVAL"))
    else:
        return None, "na"

    return next((candidate for candidate in candidates if candidate[0] != primary),
                (None, "na"))


def rank_candidates(primary, alternate, yval, ypoc, yvah, onpoc, price,
                    edges=(), limit=5):
    """Rank distinct cutoff candidates without selecting or changing a pivot.

    Family codes: 1 YVAL, 2 YPOC, 3 YVAH, 4 ONPOC, 5 ON lower E1,
    6 ON upper E1. ``identity_mask`` ORs ``1 << (family - 1)`` for every
    source at the exact candidate price. E1 identities retain parent row keys.
    The caller separately reports omitted N1 regions; ``truncated`` means only
    that this display limit omitted known distinct prices.
    """
    from collections.abc import Mapping
    from math import isfinite

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 8:
        raise ValueError("candidate display limit must be an integer from 1 to 8")

    def finite(value):
        return (not isinstance(value, bool)
                and isinstance(value, (int, float)) and isfinite(value))

    empty = {"ready": False, "candidates": [], "all_candidates": [],
             "total_distinct": 0, "truncated": False, "limit": limit}
    if not all(finite(value) for value in (primary, yval, ypoc, yvah, onpoc, price)):
        return empty

    alternate = alternate if finite(alternate) else None
    family_names = {1: "YVAL", 2: "YPOC", 3: "YVAH", 4: "ONPOC",
                    5: "ON lower E1", 6: "ON upper E1"}
    pool = []

    def add(coordinate, family, parent_key=None, prominence=0.0):
        if coordinate == primary:
            return
        identity = family_names[family]
        if parent_key is not None:
            identity += f" N1@{parent_key}"
        pool.append({"price": coordinate, "family": family,
                     "parent_key": parent_key, "prominence": prominence,
                     "priority": 0 if alternate is not None and coordinate == alternate else 1,
                     "distance": abs(coordinate - price), "identity": identity})

    for family, coordinate in enumerate((yval, ypoc, yvah, onpoc), 1):
        add(coordinate, family)
    for edge in edges:
        if not isinstance(edge, Mapping):
            continue
        coordinate = edge.get("coordinate")
        family = edge.get("family")
        parent_key = edge.get("parent_key")
        prominence = edge.get("prominence", 0.0)
        if (edge.get("qualified") is not True or edge.get("overlap", False)
                or isinstance(family, bool) or not isinstance(family, int) or family not in (5, 6)
                or not finite(coordinate) or not finite(prominence) or prominence < 0
                or isinstance(parent_key, bool) or not isinstance(parent_key, int)):
            continue
        add(coordinate, family, parent_key, prominence)

    def key(candidate):
        return (candidate["priority"], candidate["distance"], candidate["family"],
                -candidate["prominence"], candidate["price"],
                candidate["parent_key"] if candidate["parent_key"] is not None else 0)

    # Sort the full source ledger first, so representative identity selection
    # obeys the same policy as price ranking and is independent of input order.
    pool.sort(key=key)
    unique = {}
    for candidate in pool:
        coordinate = candidate["price"]
        if coordinate not in unique:
            representative = candidate.copy()
            representative.pop("identity")
            representative["identity_mask"] = 0
            representative["source_identities"] = set()
            unique[coordinate] = representative
        merged = unique[coordinate]
        merged["identity_mask"] |= 1 << (candidate["family"] - 1)
        merged["source_identities"].add(candidate["identity"])
    ledger = sorted(unique.values(), key=key)
    for rank, candidate in enumerate(ledger, 1):
        candidate["rank"] = rank
        candidate["source_identities"] = tuple(sorted(candidate["source_identities"]))

    return {"ready": True, "candidates": ledger[:limit], "all_candidates": ledger,
            "total_distinct": len(ledger), "truncated": len(ledger) > limit,
            "limit": limit}
