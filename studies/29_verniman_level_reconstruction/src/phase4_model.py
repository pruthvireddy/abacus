"""Independent Phase 4 selection control; no Pine interpreter or source learning.

Consumes supplied frozen Phase 3 candidates only. No market data or source-answer
loading occurs. P0 adapts an existing hypothesis to strict Phase 3 windows; D1
is an unfitted structural itinerary. All values retain their original coordinates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import importlib.util
from math import isfinite
from pathlib import Path
import sys
from typing import Iterable

_PATH = Path(__file__).with_name("phase3_model.py")
_SPEC = importlib.util.spec_from_file_location("study29_phase4_phase3_oracle", _PATH)
P3 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = P3
_SPEC.loader.exec_module(P3)
POLICY = "phase4-4.0.0"
DESTINATION_ROLES = frozenset({"value_boundary", "range_extreme", "edge", "projection"})


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    price: float | None
    interval: tuple[float, float] | None
    family: str
    role: str
    window: str
    profile_id: str
    ready_at: datetime | None
    ready: bool = True
    auction_id: str = ""
    parent_id: str = ""
    side: str = ""
    origin_role: str = ""
    contract: str = "ESZ2026"
    source_identity: str = ""
    identity_projection: bool = False
    unavailable_reasons: tuple[str, ...] = ()

    def reasons(self, cutoff: datetime) -> tuple[str, ...]:
        reasons = list(self.unavailable_reasons)
        if not self.ready:
            reasons.append("NOT_READY")
        if not self.candidate_id or not self.window or not self.profile_id or not self.contract or not self.source_identity:
            reasons.append("MISSING_IDENTITY")
        if self.price is None or not isfinite(self.price):
            reasons.append("NO_FINITE_ORIGINAL_PRICE")
        if (self.interval is None or len(self.interval) != 2 or
                not all(isfinite(x) for x in self.interval) or self.interval[0] > self.interval[1]):
            reasons.append("INVALID_INTERVAL")
        elif self.price is not None and isfinite(self.price) and not self.interval[0] <= self.price <= self.interval[1]:
            reasons.append("PRICE_OUTSIDE_DECLARED_INTERVAL")
        if self.ready_at is None or self.ready_at.tzinfo is None or cutoff.tzinfo is None:
            reasons.append("MISSING_AWARE_READINESS")
        elif self.ready_at > cutoff:
            reasons.append("LATER_THAN_CUTOFF")
        return tuple(dict.fromkeys(reasons))


@dataclass(frozen=True)
class Region:
    region_id: str
    lower: float
    upper: float
    lower_edge_id: str | None
    upper_edge_id: str | None = None
    overlap: bool = False
    rank: int = 1

    def contains(self, price: float) -> bool:
        return self.lower <= price <= self.upper


@dataclass(frozen=True)
class SelectionInputs:
    trading_date: date
    cutoff: datetime
    last_included_open: datetime | None
    last_included_close: datetime | None
    cutoff_close: float | None
    candidates: tuple[Candidate, ...]
    overnight_regions: tuple[Region, ...]
    rth_ready: bool
    overnight_ready: bool
    tick_size: float = .25
    row_size: float = 4.0
    input_identity: str = ""
    generator_identity: str = "phase3-3.0.0"
    contract: str = "ESZ2026"
    adjustment: str = "individual_contract_unadjusted"

    @property
    def buffer(self) -> float:
        return max(2 * self.tick_size, self.row_size / 2)

    def reasons(self) -> tuple[str, ...]:
        reasons = []
        if not all(isfinite(x) and x > 0 for x in (self.tick_size, self.row_size)):
            reasons.append("INVALID_TICK_OR_ROW")
        if (self.cutoff.tzinfo is None or self.last_included_open is None or
                self.last_included_close is None or self.last_included_open.tzinfo is None or
                self.last_included_close.tzinfo is None or
                self.last_included_close != self.cutoff or
                self.last_included_open + timedelta(minutes=5) != self.cutoff):
            reasons.append("MISSING_EXACT_COMPLETED_CUTOFF")
        if self.cutoff.tzinfo is not None and (self.cutoff.astimezone(P3.BASE.NY).hour, self.cutoff.astimezone(P3.BASE.NY).minute) != (9, 25):
            reasons.append("NONCONTROL_CUTOFF")
        if self.cutoff_close is None or not isfinite(self.cutoff_close):
            reasons.append("MISSING_CUTOFF_CLOSE")
        if not self.rth_ready:
            reasons.append("PRIOR_EXPECTED_RTH_UNAVAILABLE")
        if not self.overnight_ready:
            reasons.append("OVERNIGHT_UNAVAILABLE")
        if self.adjustment != "individual_contract_unadjusted":
            reasons.append("UNSUPPORTED_ADJUSTMENT_CONVENTION")
        if not self.input_identity or not self.generator_identity or not self.contract:
            reasons.append("MISSING_MAP_PROVENANCE")
        if len({x.candidate_id for x in self.candidates}) != len(self.candidates):
            reasons.append("DUPLICATE_CANDIDATE_ID")
        return tuple(reasons)


@dataclass(frozen=True)
class Alternative:
    candidate_id: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class PivotChoice:
    policy: str
    candidate: Candidate | None
    reason_code: str
    status: str
    fallback: bool
    fallback_status: str
    cutoff: datetime
    explanatory_inputs: tuple[tuple[str, float | str | None], ...]
    alternatives: tuple[Alternative, ...] = ()
    confluence_ids: tuple[str, ...] = ()

    @property
    def price(self) -> float | None:
        return None if self.candidate is None else self.candidate.price


@dataclass(frozen=True)
class Target:
    rank: int
    candidate: Candidate
    group: tuple[Candidate, ...]
    reason_code: str
    originating_candidate_id: str


@dataclass(frozen=True)
class Branch:
    side: str
    policy: str
    targets: tuple[Target, ...]
    status: str
    reasons: tuple[str, ...]
    alternatives: tuple[Alternative, ...]


@dataclass(frozen=True)
class SelectionMap:
    policy: str
    cutoff: datetime
    cutoff_close: float | None
    pivot: PivotChoice
    bullish: Branch
    bearish: Branch
    candidate_ids: tuple[str, ...]
    input_identity: str
    generator_identity: str


def _named(inputs: SelectionInputs, name: str) -> Candidate | None:
    matches = [c for c in inputs.candidates if c.origin_role == name]
    return matches[0] if len(matches) == 1 and not matches[0].reasons(inputs.cutoff) and matches[0].contract == inputs.contract else None


def select_pivot(inputs: SelectionInputs, policy: str = "P0") -> PivotChoice:
    if policy not in ("P0", "B0", "B1"):
        raise ValueError("frozen pivot policy must be P0, B0 or B1")
    refs = {name: _named(inputs, name) for name in ("YVAH", "YPOC", "YVAL", "ONPOC")}
    values = {name: c.price if c else None for name, c in refs.items()}
    values.update(P=inputs.cutoff_close, b=inputs.buffer, adjustment=inputs.adjustment)
    explanation = tuple(values.items())
    reasons = list(inputs.reasons())
    if any(c is None for c in refs.values()):
        reasons.append("MISSING_REQUIRED_VALUE_REFERENCE")
    elif not values["YVAL"] <= values["YPOC"] <= values["YVAH"]:
        reasons.append("INCONSISTENT_PRIOR_VALUE")
    alternatives = [Alternative(c.candidate_id, reason) for c in inputs.candidates
                    for reason in c.reasons(inputs.cutoff)]
    if reasons:
        return PivotChoice(policy, None, "ABSTAIN_REQUIRED_INPUT", "unavailable", False,
                           ";".join(reasons), inputs.cutoff, explanation, tuple(alternatives))
    vah, poc, val, onpoc, price, b = (values[k] for k in ("YVAH", "YPOC", "YVAL", "ONPOC", "P", "b"))
    chosen, code, fallback, detail = None, "", False, "none"
    if policy == "B0":
        chosen, code = refs["YPOC"], "B0_FIXED_YPOC"
    elif policy == "B1":
        chosen = min((refs[k] for k in ("YVAL", "YPOC", "YVAH")),
                     key=lambda c: (abs(c.price - price), c.price, c.candidate_id))
        code = "B1_NEAREST_VALUE"
    elif price < val - b:
        chosen, code = refs["YVAL"], "P0_BELOW_VALUE_RECLAIM"
    elif price > vah + b:
        retained = sorted(inputs.overnight_regions, key=lambda r: r.rank)[:8]
        containing = [r for r in retained if r.contains(price)]
        candidates = {c.candidate_id: c for c in inputs.candidates}
        lower = [candidates.get(r.lower_edge_id) for r in containing]
        edge_ready = lambda c: c is not None and not c.reasons(inputs.cutoff) and c.family == "HVE" and c.contract == inputs.contract
        eligible = [c for c in lower if edge_ready(c) and c.price > vah + b]
        overlap = any(r.overlap for r in containing)
        missing = any(not edge_ready(c) for c in lower)
        if len(eligible) == 1 and not overlap and len(inputs.overnight_regions) <= 8 and not missing:
            chosen, code = eligible[0], "P0_HIGHER_AUCTION_LOWER_E1"
        else:
            chosen, code, fallback = refs["YVAH"], "P0_PRIOR_VAH_FALLBACK", True
            detail = ("OVERLAP_OR_AMBIGUITY" if overlap or len(eligible) > 1 else
                      "CAP" if len(inputs.overnight_regions) > 8 else
                      "MISSING_EDGE" if missing else "ABSENT")
    elif onpoc < poc - b:
        chosen, code = refs["YVAL"], "P0_ON_VALUE_SHIFT_LOWER"
    elif onpoc > poc + b:
        chosen, code = refs["YVAH"], "P0_ON_VALUE_SHIFT_HIGHER"
    else:
        chosen, code, fallback, detail = refs["YPOC"], "P0_BALANCED_FALLBACK", True, "balanced"
    confluence = tuple(c.candidate_id for c in inputs.candidates
                      if c.family == "HVE" and c.contract == inputs.contract and not c.reasons(inputs.cutoff) and
                      chosen.family != "HVE" and abs(c.price - chosen.price) <= inputs.row_size)
    alternatives.extend(Alternative(c.candidate_id, "NOT_PRIMARY_PIVOT", "Candidate construction retained; not selected by frozen pivot rule")
                        for c in inputs.candidates if c.candidate_id != chosen.candidate_id)
    return PivotChoice(policy, chosen, code, "ready", fallback, detail, inputs.cutoff,
                       explanation, tuple(alternatives), confluence)


def _destination_reasons(c: Candidate, inputs: SelectionInputs) -> tuple[str, ...]:
    reasons = list(c.reasons(inputs.cutoff))
    if c.contract != inputs.contract:
        reasons.append("INCOMPATIBLE_CONTRACT")
    if c.role not in DESTINATION_ROLES:
        reasons.append("MODAL_NOT_DESTINATION" if c.role == "modal" else "UNSUPPORTED_FAMILY")
    if c.family not in {"VAH", "VAL", "FULL_HIGH", "FULL_LOW", "ONH", "ONL", "RTH_HIGH", "RTH_LOW", "HVE", "PBT"}:
        reasons.append("UNSUPPORTED_FAMILY")
    if c.family == "PBT":
        if c.identity_projection:
            reasons.append("IDENTITY_NOT_EXTERNAL")
        if c.interval is None or len(c.interval) != 2 or c.interval[0] != c.interval[1] or c.price != c.interval[0]:
            reasons.append("NONEXACT_PBT")
    return tuple(dict.fromkeys(reasons))


def select_targets(inputs: SelectionInputs, pivot: PivotChoice, policy: str = "D1") -> tuple[Branch, Branch]:
    if policy not in ("D0", "D1"):
        raise ValueError("frozen target policy must be D0 or D1")
    branches = []
    for side, sign in (("bullish", 1), ("bearish", -1)):
        alternatives = []
        if pivot.candidate is None or pivot.status != "ready" or pivot.fallback:
            reason = "PIVOT_FALLBACK_TARGET_ABSTENTION" if pivot.fallback else "PIVOT_UNAVAILABLE"
            branches.append(Branch(side, policy, (), "unavailable", (reason,), ()))
            continue
        valid = []
        for c in inputs.candidates:
            reasons = _destination_reasons(c, inputs)
            if not reasons and sign * (c.price - pivot.price) <= inputs.buffer:
                reasons = ("WRONG_DIRECTION_OR_WITHIN_BUFFER",)
            alternatives.extend(Alternative(c.candidate_id, r) for r in reasons)
            if not reasons:
                valid.append(c)
        # Exact coordinate groups retain all eligible roles; no interval averaging.
        groups = {}
        for c in valid:
            groups.setdefault(c.price, []).append(c)
        grouped = [tuple(sorted(group, key=lambda c: c.candidate_id)) for group in groups.values()]
        grouped.sort(key=lambda group: (sign * (group[0].price - pivot.price), group[0].candidate_id))
        for group in grouped:
            alternatives.extend(Alternative(c.candidate_id, "DUPLICATE_PRICE_GROUPED", group[0].candidate_id) for c in group[1:])
        selected = []
        selected_ids = set()
        last = pivot.price

        def take(group, reason, origin):
            nonlocal last
            if len(selected) >= 3 or group[0].price in selected_ids:
                return False
            if sign * (group[0].price - last) <= inputs.buffer:
                return False
            selected.append(Target(len(selected) + 1, group[0], group, reason, origin.candidate_id))
            selected_ids.add(group[0].price)
            last = group[0].price
            return True

        if policy == "D1":
            own = []
            pc = pivot.candidate
            for group in grouped:
                for c in group:
                    same_value_auction = (c.auction_id == pc.auction_id and c.auction_id and
                                         ((pc.origin_role == "YVAL" and side == "bullish" and c.origin_role == "YVAH") or
                                          (pc.origin_role == "YVAH" and side == "bearish" and c.origin_role == "YVAL")))
                    same_node_auction = (pc.family == "HVE" and pc.side == "lower" and side == "bullish" and
                                         c.family == "HVE" and c.side == "upper" and
                                         pc.parent_id and c.parent_id == pc.parent_id)
                    if same_value_auction or same_node_auction:
                        own.append((group, c))
            for group, c in own:
                if take(group, "OWN_AUCTION_EXIT", c):
                    break
            for role, reason in (("range_extreme", "RANGE_EXTREME"), (None, "EXTERNAL_BOUNDARY_OR_PROJECTION")):
                for group in grouped:
                    origins = [c for c in group if c.role == role] if role else [c for c in group if c.role in ("edge", "value_boundary", "projection")]
                    if origins:
                        take(group, reason, origins[0])
        else:
            for group in grouped:
                take(group, "DISTANCE_BASELINE", group[0])
        for group in grouped:
            if group[0].price not in selected_ids:
                if len(selected) == 3 and sign * (group[0].price - last) > inputs.buffer:
                    reason = "TARGET_CAP"
                elif policy == "D1" and selected and sign * (group[0].price - pivot.price) < sign * (selected[0].candidate.price - pivot.price):
                    reason = "INTERVENING_REFERENCE_SKIPPED_BY_STRUCTURAL_PRIORITY"
                else:
                    reason = "SPACING"
                alternatives.extend(Alternative(c.candidate_id, reason) for c in group)
        status = "ready" if len(selected) == 3 else "partial"
        reasons = () if len(selected) == 3 else ("FEWER_THAN_THREE_ELIGIBLE_DESTINATIONS",)
        if not any(c.family == "PBT" and not _destination_reasons(c, inputs) for c in inputs.candidates):
            reasons += ("NO_ELIGIBLE_EXACT_CAUSAL_PBT",)
        branches.append(Branch(side, policy, tuple(selected), status, reasons, tuple(alternatives)))
    return tuple(branches)


def select_map(inputs: SelectionInputs, *, pivot_policy: str = "P0", target_policy: str = "D1") -> SelectionMap:
    pivot = select_pivot(inputs, pivot_policy)
    bullish, bearish = select_targets(inputs, pivot, target_policy)
    return SelectionMap(POLICY, inputs.cutoff, inputs.cutoff_close, pivot, bullish, bearish,
                        tuple(c.candidate_id for c in inputs.candidates), inputs.input_identity, inputs.generator_identity)


def inputs_from_phase3(expanded, cutoff_close: float | None) -> SelectionInputs:
    """Adapt the original19 baseline fields, E1 sides and causal PBT ledger.

    Composite E1 candidates remain eligible. Internal composite VA values are
    not added as new saved fields. Full HVN/LVN evidence stays in the supplied
    Phase3 ledger and is not a modal/trough destination in this adapter.
    No source-answer price is inserted into the pool.
    """
    baseline = expanded.baseline
    distributions = {d.window: d for d in expanded.distributions}
    ledgers = {d.window: ledger for d, ledger in zip(expanded.distributions, expanded.candidate_ledgers)}
    cutoff = baseline.cutoff
    rth, on = distributions.get("completed_RTH"), distributions.get("overnight_prefix")
    refs = {name: (start, end) for name, start, end in baseline.references}
    candidates = []
    names = ["FULL_HIGH", "FULL_LOW", "WEEK_VAH", "WEEK_POC", "WEEK_VAL", "PREVWEEK_VAH", "PREVWEEK_POC", "PREVWEEK_VAL",
             "YVAH", "YPOC", "YVAL", "ONVAH", "ONPOC", "ONVAL", "ONH", "ONL", "RTH_HIGH", "RTH_LOW", "RTH_CLOSE"]
    windows = ["full", "full", "current_week_prefix", "current_week_prefix", "current_week_prefix",
               "previous_completed_week", "previous_completed_week", "previous_completed_week", "completed_RTH", "completed_RTH", "completed_RTH",
               "overnight_prefix", "overnight_prefix", "overnight_prefix", "overnight_prefix", "overnight_prefix", "completed_RTH", "completed_RTH", "completed_RTH"]
    for i, (name, window, price) in enumerate(zip(names, windows, baseline.values)):
        d = distributions.get(window)
        if window == "full":
            start, end = refs.get("full", (None, None))
            profile_id = f"full:{start}:{end}"
            ready_at, ready = end, price is not None and end is not None and end <= cutoff
        else:
            profile_id = d.profile_id if d else f"missing:{window}"
            ready_at, ready = (d.reference_end, not d.reasons(cutoff)) if d else (None, False)
        if "POC" in name or name == "RTH_CLOSE":
            family, role = ("POC" if name != "RTH_CLOSE" else "PRIOR_CLOSE"), "modal" if name != "RTH_CLOSE" else "unsupported"
        elif name.endswith("HIGH") or name.endswith("LOW") or name in ("ONH", "ONL"):
            family, role = name, "range_extreme"
        else:
            family, role = ("VAH" if name.endswith("VAH") else "VAL"), "value_boundary"
        candidates.append(Candidate(f"{profile_id}:baseline:{name}", price, (price, price) if price is not None else None,
                                    family, role, window, profile_id, ready_at, ready,
                                    auction_id=profile_id, origin_role=name,
                                    contract=d.contract if d else (rth.contract if rth else "ESZ2026"),
                                    source_identity=d.input_identity if d else (rth.input_identity if rth else "")))
    regions = []
    for window, ledger in ledgers.items():
        d = distributions[window]
        for edge in ledger.get("edge_ledger", ()):
            candidates.append(Candidate(edge["candidate_id"], edge["boundary"], tuple(edge["price_interval"]), "HVE", "edge",
                                        window, d.profile_id, d.reference_end, ledger.get("status") == "ready" and edge["qualified"],
                                        auction_id=edge["parent_id"], parent_id=edge["parent_id"], side=edge["side"], contract=d.contract,
                                        source_identity=d.input_identity, unavailable_reasons=tuple(edge.get("rejection_reasons", ()))))
        if window == "overnight_prefix":
            edges = ledger.get("edge_ledger", ())
            for region in ledger.get("regions", ()):
                side = {e["side"]: e["candidate_id"] for e in edges if e["parent_id"] == region["candidate_id"] and e["qualified"]}
                regions.append(Region(region["candidate_id"], *region["price_interval"], side.get("lower"), side.get("upper"), region["overlap"], region["rank"]))
    for projection in expanded.projection_ledgers:
        raw = projection.get("unrounded_intervals") or {}
        for branch, interval in raw.items():
            point = interval[0] if interval[0] == interval[1] else None
            ready_text = projection.get("reconstruction_ready_at")
            ready_at = datetime.fromisoformat(ready_text) if ready_text else None
            anchors = projection.get("anchor_ids", ())
            identity = bool(projection.get("opposite_existing_bound_identity"))
            candidates.append(Candidate(f"{projection['hypothesis']}:{':'.join(str(x) for x in anchors)}:{branch}", point, tuple(interval),
                                        "PBT", "projection", "manual_anchor_projection", projection["hypothesis"], ready_at,
                                        projection.get("status") == "ready", source_identity=projection.get("settings_identity", ""),
                                        contract=rth.contract if rth else "ESZ2026", identity_projection=identity,
                                        unavailable_reasons=tuple(projection.get("reasons", ()))))
    return SelectionInputs(baseline.trading_date, cutoff, baseline.last_open, baseline.last_close, cutoff_close,
                           tuple(candidates), tuple(regions), bool(rth and not rth.reasons(cutoff)), bool(on and not on.reasons(cutoff) and rth and on.compatible_key() == rth.compatible_key()),
                           rth.tick_size if rth else .25, rth.row_size if rth else 4,
                           rth.input_identity if rth else "", "phase3-3.0.0", rth.contract if rth else "ESZ2026",
                           rth.adjustment if rth else "unknown")


def record(value):
    """JSON-ready immutable result projection; preserves timestamps as ISO strings."""
    def convert(item):
        if isinstance(item, (datetime, date)):
            return item.isoformat()
        if isinstance(item, dict):
            return {k: convert(v) for k, v in item.items()}
        if isinstance(item, (tuple, list)):
            return [convert(x) for x in item]
        return item
    return convert(asdict(value))


class Phase4Engine(P3.Phase3Engine):
    """Freeze selection at the same exact completed boundary as Phase3."""
    def __init__(self, *, pivot_policy="P0", target_policy="D1", **kwargs):
        super().__init__(**kwargs)
        self.pivot_policy, self.target_policy = pivot_policy, target_policy
        self.selection_snapshot = None

    def accept(self, bar):
        identity = P3.BASE.clock(bar.opened) if bar.confirmed else None
        if identity and self.trade_day != identity.trading_date:
            self.selection_snapshot = None
        super().accept(bar)

    def freeze(self, bar, cutoff):
        baseline = super().freeze(bar, cutoff)
        inputs = inputs_from_phase3(self.expanded_snapshot, bar.close)
        self.selection_snapshot = select_map(inputs, pivot_policy=self.pivot_policy, target_policy=self.target_policy)
        return baseline


def _matching_module():
    name = "study29_phase4_saved_reference_matcher"
    if name not in sys.modules:
        path = Path(__file__).parents[1] / "phase3/matching.py"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def evaluate_role(inputs: SelectionInputs | None, selection: SelectionMap | None,
                  sources: Iterable, *, role: str,
                  source_order: dict[str, int] | None = None) -> dict:
    """Compare explicit saved SourceReference objects for one semantic role.

    ``sources`` must use the Phase3 matcher's SourceReference schema and explicit
    normalized identities. No source reading, aliases inferred from prose, price
    insertion or source-assisted selector call occurs here. Unknown windows stay
    descriptive. Call separately per pivot/bullish/bearish role; source class and
    revision remain separate strata inside each call. Source order is retained in
    full, including lists longer than the executable three-target cap.
    """
    if role not in ("pivot", "bullish", "bearish"):
        raise ValueError("role must be pivot, bullish or bearish")
    matching = _matching_module()
    sources = list(sources)
    source_order = source_order or {}
    if any(isinstance(rank, bool) or not isinstance(rank, int) or rank < 1 for rank in source_order.values()):
        raise ValueError("source orders must be positive integers")
    day = inputs.trading_date.isoformat() if inputs else ""
    unsupported_reasons = tuple(reason for reason in inputs.reasons() if reason in {
        "UNSUPPORTED_ADJUSTMENT_CONVENTION", "INVALID_TICK_OR_ROW", "NONCONTROL_CUTOFF",
        "MISSING_MAP_PROVENANCE", "DUPLICATE_CANDIDATE_ID", "MISSING_EXACT_COMPLETED_CUTOFF"}) if inputs else ("NO_EXPANDED_MAP",)
    map_available = inputs is not None and not unsupported_reasons

    def family(c):
        # These roles are already explicit original baseline fields. There is no
        # nearest-price/source-text inference and no full/RTH alias collapsing.
        explicit_roles = {"YVAH": "YVAH", "YPOC": "YPOC", "YVAL": "YVAL",
                          "ONH": "ONH", "ONL": "ONL", "FULL_HIGH": "YHOD",
                          "RTH_HIGH": "YHOD", "FULL_LOW": "YLOD",
                          "RTH_LOW": "YLOD", "RTH_CLOSE": "PRIOR_CLOSE"}
        return explicit_roles.get(c.origin_role, c.family)

    def reference(c):
        return matching.CandidateReference(c.candidate_id, day, family(c), c.interval,
                c.profile_id, c.contract, inputs.adjustment,
                not c.reasons(inputs.cutoff), True,
                c.price if c.family == "HVE" else None)

    pool = []
    if inputs:
        pool = [c for c in inputs.candidates if not c.reasons(inputs.cutoff) and c.contract == inputs.contract
                and (role == "pivot" or not _destination_reasons(c, inputs))]
    generation = matching.compare_references(sources, [reference(c) for c in pool],
                                             candidate_map_ready=map_available)
    chosen = []
    target_rank = {}
    physical_count = None
    abstention = None
    selection_executed = map_available and selection is not None
    if selection_executed:
        if role == "pivot":
            chosen = [selection.pivot.candidate] if selection.pivot.candidate else []
            physical_count = len(chosen)
            abstention = selection.pivot.candidate is None
        else:
            branch = selection.bullish if role == "bullish" else selection.bearish
            physical_count = len(branch.targets)
            abstention = branch.status == "unavailable"
            for target in branch.targets:
                # One physical exact-price group may have several original roles
                # or windows, but is one candidate per family/window stratum.
                by_role_window = {}
                for c in target.group:
                    key = family(c), c.profile_id, c.contract
                    if key not in by_role_window or c.candidate_id < by_role_window[key].candidate_id:
                        by_role_window[key] = c
                for c in by_role_window.values():
                    chosen.append(c)
                    target_rank[c.candidate_id] = target.rank
    selected = matching.compare_references(sources, [reference(c) for c in chosen],
                                           candidate_map_ready=selection_executed)
    source_by_id = {source.source_id: source for source in sources}
    gen_occurrences = {x["source_id"]: x for x in generation["occurrences"]}
    chosen_occurrences = {x["source_id"]: x for x in selected["occurrences"]}
    feasible = {x["source_id"] for group in generation["strata"] for x in group["feasible_alternatives"]}
    selected_pairs = [x for group in selected["strata"] for x in group["assignments"]]
    selected_ids = {x["source_id"] for x in selected_pairs}
    available_count = 0
    matched_available = 0
    outcomes = []
    for source in sorted(sources, key=lambda x: x.source_id):
        sid = source.source_id
        gen = gen_occurrences.get(sid)
        picked = chosen_occurrences.get(sid)
        if not map_available:
            status = "GENERATOR_UNAVAILABLE"
        elif not gen or not gen["eligible_roles"]:
            status = "UNRESOLVED_IDENTITY_OR_UNSUPPORTED_FAMILY"
        elif sid not in feasible:
            status = "CANDIDATE_GENERATION_FAILURE"
        else:
            available_count += 1
            if not selection_executed:
                status = "SELECTION_NOT_EXECUTED"
            elif abstention:
                status = "SELECTOR_ABSTENTION"
            elif sid in selected_ids:
                status = "END_TO_END_SUPPORTED_ROLE_MATCH"
                matched_available += 1
            else:
                possible_selected = any(x["source_id"] == sid for group in selected["strata"] for x in group["feasible_alternatives"])
                status = "AMBIGUOUS_ONE_TO_ONE_COMPETITION" if possible_selected else "SELECTION_FAILURE"
        outcomes.append({"source_id": sid, "status": status,
                         "source_order": source_order.get(sid),
                         "eligible_roles": gen["eligible_roles"] if gen else None,
                         "generated_matched_roles": gen["matched_roles"] if gen else None,
                         "selected_matched_roles": picked["matched_roles"] if picked else None,
                         "source_timing_class": source.timing_class,
                         "source_historical_available_at": source.source_historical_available_at})
    order_results = []
    if role != "pivot" and selection_executed:
        groups = {}
        for source in sources:
            groups.setdefault((source.session_date, source.source_class, source.revision_id), []).append(source)
        for key, observations in sorted(groups.items()):
            observed_ids = {source.source_id for source in observations}
            pairs = [pair for pair in selected_pairs if pair["source_id"] in observed_ids]
            ranked = sorted({(source_order[pair["source_id"]], target_rank[pair["candidate_id"]])
                             for pair in pairs if pair["source_id"] in source_order})
            has_order = all(source.source_id in source_order for source in observations)
            unique_order = has_order and len({source_order[source.source_id] for source in observations}) == len(observations)
            eligible = all(gen_occurrences.get(source.source_id, {}).get("eligible_roles") for source in observations)
            full_roles = all(chosen_occurrences.get(source.source_id, {}).get("coverage") == "full_roles" for source in observations)
            relative_order = (all(ranked[i][1] < ranked[i + 1][1] for i in range(len(ranked) - 1))
                              if len(ranked) > 1 else None)
            complete = (has_order and unique_order and eligible and full_roles and len(observations) == physical_count
                        and len(ranked) == len(observations) and (len(ranked) < 2 or relative_order))
            order_results.append({"session_date": key[0], "source_class": key[1], "revision_id": key[2],
                                  "observed_target_count": len(observations), "executable_target_cap": 3,
                                  "matched_order_pairs": [list(pair) for pair in ranked],
                                  "relative_order_agreement_on_matched_subset": relative_order,
                                  "source_order_ambiguous": has_order and not unique_order,
                                  "complete_ladder_agreement": bool(complete) if has_order and unique_order and eligible else None,
                                  "source_targets_not_truncated": True})
    return {"role": role, "status": "not_executed" if not map_available else
                         "generation_only" if not selection_executed else
                         "not_estimable" if not generation["eligible_role_count"] else "compared",
            "generation": generation, "selection": selected, "source_outcomes": outcomes,
            "map_unavailable_reasons": list(unsupported_reasons),
            "source_occurrences_with_compatible_generated_candidate": available_count if map_available else None,
            "selected_matches_conditional_on_generated_candidate": matched_available / available_count
                         if available_count and selection_executed else None,
            "physical_selected_count": physical_count, "selector_abstained": abstention,
            "ordering": order_results,
            "limits": "Identity support uses declared exact windows; unknown windows are descriptive only. Matched role strata are not independent confirmations; source historical availability is unchanged."}
