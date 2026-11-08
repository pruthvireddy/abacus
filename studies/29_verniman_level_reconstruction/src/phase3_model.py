"""Study 29 Phase 3 independent specification model, not a Pine interpreter.

N1/E1 is an experimental control. Nothing here identifies Verniman's algorithms,
selects a pivot/ordered targets, or certifies historical source availability.
Only explicitly supplied identified distributions/bars/anchors are consumed.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import hashlib
import importlib.util
import json
from math import ceil, floor, isclose, isfinite
from pathlib import Path
import sys
from typing import Iterable

_PATH = Path(__file__).with_name("reference_model.py")
_SPEC = importlib.util.spec_from_file_location("study29_phase3_phase1_oracle", _PATH)
BASE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = BASE
_SPEC.loader.exec_module(BASE)
POLICY = "N1-E1-P1-P2-v1"
MEASUREMENT = "uniform_chart_bar_volume_across_inclusive_touched_bins"


def _stamp(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _aware(value: datetime | None) -> bool:
    return value is not None and value.tzinfo is not None and value.utcoffset() is not None


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str,
                                     allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Distribution:
    """Ordered, contiguous grid rows and their declared provenance.

    Missing price-domain rows must not be silently filled here. A measured zero
    row may be supplied explicitly. ``coverage`` is an input assertion tied to
    the declared bar/window inventory, not a source-availability assertion.
    """
    profile_id: str
    window: str
    reference_start: datetime
    reference_end: datetime
    included_sessions: tuple[str, ...]
    masses: tuple[float | None, ...]
    min_key: int = 0
    row_size: float = 4.0
    grid_origin: float = 0.0
    contract: str = "ESZ2026"
    feed: str = "CME GLOBEX"
    adjustment: str = "individual_contract_unadjusted"
    tick_size: float = 0.25
    measurement: str = MEASUREMENT
    last_bar_open: datetime | None = None
    last_bar_close: datetime | None = None
    coverage: bool = True
    missing_volume: bool = False
    overflow: bool = False
    input_identity: str = ""
    code_identity: str = ""
    settings_identity: str = ""
    declared_total: float | None = None
    source_historical_available_at: datetime | None = None
    lineage: tuple[tuple[str, float], ...] = ()
    expected_sessions: tuple[str, ...] = ()

    def reasons(self, cutoff: datetime) -> list[str]:
        reasons = []
        if not self.profile_id or not self.window:
            reasons.append("missing_profile_or_window_identity")
        if not all((self.contract, self.feed, self.adjustment, self.measurement,
                    self.input_identity, self.code_identity, self.settings_identity)):
            reasons.append("missing_input_or_provenance_identity")
        if self.measurement != MEASUREMENT:
            reasons.append("incompatible_measurement")
        if (not isinstance(self.min_key, int) or not isfinite(self.grid_origin)
                or not isfinite(self.row_size) or self.row_size <= 0
                or not isfinite(self.tick_size) or self.tick_size <= 0
                or not isclose(self.row_size / self.tick_size,
                               round(self.row_size / self.tick_size), abs_tol=1e-10)):
            reasons.append("invalid_grid")
        if not self.coverage:
            reasons.append("incomplete_coverage")
        if self.missing_volume:
            reasons.append("missing_or_invalid_volume")
        if self.overflow or len(self.masses) > 6000:
            reasons.append("overflow")
        if not self.masses:
            reasons.append("empty_distribution")
        if any(x is None or not isfinite(x) or x < 0 for x in self.masses):
            reasons.append("invalid_row_mass")
        else:
            total = sum(self.masses)
            if not isfinite(total):
                reasons.append("nonfinite_total_mass")
            elif total <= 0:
                reasons.append("zero_total_mass")
            if (self.declared_total is not None and
                    (not isfinite(self.declared_total) or
                     not isclose(total, self.declared_total, rel_tol=1e-10, abs_tol=1e-8))):
                reasons.append("total_mass_mismatch")
        if not all(_aware(x) for x in (cutoff, self.reference_start,
                                      self.reference_end, self.last_bar_open,
                                      self.last_bar_close)):
            reasons.append("missing_or_naive_timing")
        elif not (self.reference_start <= self.last_bar_open < self.last_bar_close
                  == self.reference_end <= cutoff):
            reasons.append("incomplete_or_future_boundary")
        if not self.included_sessions or any(not x for x in self.included_sessions):
            reasons.append("missing_session_identity")
        if len(set(self.included_sessions)) != len(self.included_sessions):
            reasons.append("duplicate_session_identity")
        return reasons

    def record(self, cutoff: datetime) -> dict:
        reasons = self.reasons(cutoff)
        valid_mass = not any(x is None or not isfinite(x) or x < 0 for x in self.masses)
        total = sum(self.masses) if valid_mass else None
        if total is not None and not isfinite(total):
            total = None
        rows = [{"row_key": self.min_key + i,
                 "lower": self.grid_origin + (self.min_key + i) * self.row_size,
                 "upper": self.grid_origin + (self.min_key + i + 1) * self.row_size,
                 "raw_mass": mass,
                 "normalized_mass": mass / total if total and valid_mass else None}
                for i, mass in enumerate(self.masses)]
        metadata = asdict(self)
        metadata.pop("masses")
        metadata = {k: _stamp(v) if isinstance(v, datetime) else v
                    for k, v in metadata.items()}
        return {"metadata": metadata, "rows": rows, "total_mass": total,
                "readiness": "unavailable" if reasons else "ready",
                "reasons": reasons,
                "reconstruction_ready_at": _stamp(self.reference_end) if not reasons else None}

    def compatible_key(self) -> tuple:
        return (self.contract, self.feed, self.adjustment, self.tick_size,
                self.row_size, self.grid_origin, self.measurement,
                self.settings_identity)


def _price(d: Distribution, index: int) -> float:
    return d.grid_origin + (d.min_key + index) * d.row_size


def _base_candidate(d: Distribution, kind: str, identifier: str) -> dict:
    return {"candidate_id": f"{d.profile_id}:{kind}:{identifier}",
            "profile_id": d.profile_id, "window": d.window,
            "kind": f"candidate_{kind}", "policy": POLICY,
            "evidence_status": "experimental_engineering_control_unattributed",
            "parameters": {"smoothing_width": 1, "padding": "none",
                           "relative_height": .20, "relative_prominence": .10,
                           "region_fraction": .5, "minimum_separation_rows": 2,
                           "lvn_relative_height": .25, "edge_minimum_parent_rows": 2,
                           "edge_relative_contrast": .10},
            "reconstruction_ready_at": _stamp(d.reference_end),
            "source_historical_available_at": _stamp(d.source_historical_available_at),
            "provenance": {"input": d.input_identity, "code": d.code_identity,
                           "settings": d.settings_identity}}


def edge_candidates(d: Distribution, regions: list[dict]) -> list[dict]:
    """E1 for every qualified parent; rejected sides remain in the ledger."""
    edges = []
    for rank, parent in enumerate(regions):
        lo, hi, peak = parent["lower_index"], parent["upper_index"], parent["peak_mass"]
        for side, inside, outside in (("lower", lo, lo - 1), ("upper", hi, hi + 1)):
            boundary = _price(d, lo if side == "lower" else hi + 1)
            e = _base_candidate(d, "HVE", f"{parent['representative_key']}:{side}")
            reasons = []
            if hi - lo + 1 < 2:
                reasons.append("parent_narrower_than_two_rows")
            observed = 0 <= outside < len(d.masses)
            if not observed:
                reasons.append("domain_truncated_outside_neighbor")
            inside_mass = d.masses[inside]
            outside_mass = d.masses[outside] if observed else None
            contrast = (inside_mass - outside_mass) / peak if observed and peak > 0 else None
            if contrast is not None and contrast < 0.10:
                reasons.append("transition_below_0.10_peak")
            e.update(parent_id=parent["candidate_id"], side=side,
                     boundary=boundary, price_interval=[boundary - d.row_size / 2,
                                                       boundary + d.row_size / 2],
                     inside_key=d.min_key + inside, outside_key=d.min_key + outside,
                     inside_mass=inside_mass, outside_mass=outside_mass,
                     contrast=contrast, parent_rank=rank + 1,
                     qualified=not reasons, rejection_reasons=reasons,
                     readiness="qualified" if not reasons else "unavailable" if not observed else "rejected")
            edges.append(e)
    return edges


def detect_n1_e1(d: Distribution, cutoff: datetime) -> dict:
    """Literal frozen N1/E1; thresholds are controls, not fitted probabilities."""
    record = d.record(cutoff)
    result = {"policy": POLICY, "distribution": record, "peaks": [], "regions": [],
              "lvn_ledger": [], "edge_ledger": [], "presentation": {}, "counts": {}}
    if record["reasons"]:
        result["status"] = "unavailable"
        result["counts"] = {"regions": 0, "lvns": 0, "edges": 0}
        return result
    masses = d.masses
    maximum = max(masses)
    peaks = []
    i = 0
    while i < len(masses):
        j = i
        while j + 1 < len(masses) and masses[j + 1] == masses[i]:
            j += 1
        left_lower = i == 0 or masses[i - 1] < masses[i]
        right_lower = j == len(masses) - 1 or masses[j + 1] < masses[i]
        if left_lower and right_lower:
            peak = _base_candidate(d, "HVN", str(d.min_key + i))
            reasons = []
            if i == 0 or j == len(masses) - 1:
                reasons.append("endpoint_plateau_not_interior")
            left_min = right_min = masses[i]
            left_stop, right_stop = i, j
            k = i - 1
            while k >= 0:
                left_min = min(left_min, masses[k])
                left_stop = k
                if masses[k] > masses[i]:
                    break
                k -= 1
            k = j + 1
            while k < len(masses):
                right_min = min(right_min, masses[k])
                right_stop = k
                if masses[k] > masses[i]:
                    break
                k += 1
            saddle = max(left_min, right_min)
            prominence = masses[i] - saddle
            if masses[i] < 0.20 * maximum:
                reasons.append("height_below_0.20_global_maximum")
            if prominence < 0.10 * maximum:
                reasons.append("prominence_below_0.10_global_maximum")
            peak.update(plateau_keys=[d.min_key + i, d.min_key + j],
                        plateau_interval=[_price(d, i), _price(d, j + 1)],
                        representative_key=d.min_key + i,
                        representative_price=_price(d, i), peak_mass=masses[i],
                        normalized_peak_mass=masses[i] / record["total_mass"],
                        smoothed_peak_mass=masses[i],
                        prominence=prominence, saddle=saddle,
                        search_left_minimum=left_min, search_right_minimum=right_min,
                        search_left_stop_key=d.min_key + left_stop,
                        search_right_stop_key=d.min_key + right_stop,
                        rejection_reasons=reasons, qualified=not reasons,
                        plateau_indices=[i, j])
            peaks.append(peak)
        i = j + 1
    ranked = sorted((x for x in peaks if x["qualified"]),
                    key=lambda x: (-x["peak_mass"], -x["prominence"], x["representative_key"]))
    regions = []
    for peak in ranked:
        if any(abs(peak["representative_key"] - x["representative_key"]) < 2 for x in regions):
            peak["qualified"] = False
            peak["rejection_reasons"].append("representative_less_than_two_rows_from_prior_rank")
            continue
        lo, hi = peak["plateau_indices"]
        threshold = peak["saddle"] + 0.5 * peak["prominence"]
        while lo > 0 and masses[lo - 1] >= threshold:
            lo -= 1
        while hi < len(masses) - 1 and masses[hi + 1] >= threshold:
            hi += 1
        region = deepcopy(peak)
        region.update(lower_index=lo, upper_index=hi,
                      row_keys=[d.min_key + lo, d.min_key + hi],
                      price_interval=[_price(d, lo), _price(d, hi + 1)],
                      integrated_mass=sum(masses[lo:hi + 1]),
                      integrated_smoothed_mass=sum(masses[lo:hi + 1]),
                      integrated_normalized_mass=sum(masses[lo:hi + 1]) / record["total_mass"],
                      boundary_threshold=threshold, rank=len(regions) + 1,
                      endpoint_truncated=lo == 0 or hi == len(masses) - 1)
        regions.append(region)
    for region in regions:
        region["overlap_ids"] = [x["candidate_id"] for x in regions
                                 if x is not region and
                                 max(region["lower_index"], x["lower_index"]) <=
                                 min(region["upper_index"], x["upper_index"])]
        region["overlap"] = bool(region["overlap_ids"])
    ordered = sorted(regions, key=lambda x: x["representative_key"])
    lvns = []
    for a, b in zip(ordered, ordered[1:]):
        lvn = _base_candidate(d, "LVN", f"{a['representative_key']}:{b['representative_key']}")
        lvn.update(parent_ids=[a["candidate_id"], b["candidate_id"]])
        lo, hi = a["upper_index"] + 1, b["lower_index"] - 1
        reasons = []
        if lo > hi:
            reasons.append("overlapping_or_touching_parent_regions")
            lvn.update(qualified=False, rejection_reasons=reasons, price_interval=None,
                       trough_mass=None)
        else:
            trough_mass = min(masses[lo:hi + 1])
            index = next(k for k in range(lo, hi + 1) if masses[k] == trough_mass)
            end = index
            while end < hi and masses[end + 1] == trough_mass:
                end += 1
            parent_peak = min(a["peak_mass"], b["peak_mass"])
            if trough_mass > 0.25 * parent_peak:
                reasons.append("trough_above_0.25_smaller_parent_peak")
            lvn.update(qualified=not reasons, rejection_reasons=reasons,
                       representative_key=d.min_key + index,
                       row_keys=[d.min_key + index, d.min_key + end],
                       price_interval=[_price(d, index), _price(d, end + 1)],
                       trough_mass=trough_mass, relative_depth=trough_mass / parent_peak,
                       integrated_mass=sum(masses[index:end + 1]))
        lvns.append(lvn)
    edges = edge_candidates(d, regions)
    qualified_lvns = sorted((x for x in lvns if x["qualified"]),
                            key=lambda x: (x["trough_mass"], x["representative_key"]))
    qualified_edges = [x for x in edges if x["qualified"]]
    presentation = {}
    for kind, candidates, cap in (("HVN", regions, 8), ("LVN", qualified_lvns, 7),
                                  ("HVE", qualified_edges, 16)):
        presentation[kind] = {"display_ids": [x["candidate_id"] for x in candidates[:cap]],
                              "omitted_ids": [x["candidate_id"] for x in candidates[cap:]],
                              "cap": cap, "qualified_count": len(candidates),
                              "omitted_count": max(0, len(candidates) - cap)}
    result.update(status="ready", peaks=peaks, regions=regions, lvn_ledger=lvns,
                  edge_ledger=edges, presentation=presentation,
                  counts={"peak_plateaus": len(peaks), "rejected_peaks": sum(not p["qualified"] for p in peaks),
                          "regions": len(regions), "lvns": len(qualified_lvns),
                          "edges": len(qualified_edges), "rejected_edges": len(edges) - len(qualified_edges)})
    return result


def expected_rth_sessions(snapshot_date: date) -> tuple[date, ...]:
    """Three prior weekdays; no holiday substitution or inferred membership."""
    dates = []
    day = snapshot_date
    while len(dates) < 3:
        day -= timedelta(days=1)
        if day.weekday() < 5:
            dates.append(day)
    return tuple(sorted(dates))


def compose_rth(members: Iterable[Distribution], snapshot_date: date,
                cutoff: datetime) -> tuple[Distribution | None, dict]:
    """Fixed three-session RTH composite with explicit exclusions and lineage."""
    members = list(members)
    expected = expected_rth_sessions(snapshot_date)
    expected_ids = tuple(x.isoformat() for x in expected)
    exclusions = []
    if len({x.profile_id for x in members}) != len(members):
        exclusions.append("duplicate_profile_member")
    ids = [x.included_sessions[0] if len(x.included_sessions) == 1 else None for x in members]
    if len(set(ids)) != len(ids):
        exclusions.append("duplicate_session_member")
    if sorted(x for x in ids if x is not None) != list(expected_ids):
        exclusions.append("missing_or_unexpected_session_members")
    if len(members) != 3:
        exclusions.append("requires_exactly_three_members")
    for m, session_id in zip(members, ids):
        if m.window != "completed_RTH" or session_id is None:
            exclusions.append(f"{m.profile_id}:not_single_completed_RTH")
        elif session_id in expected_ids:
            session_date = date.fromisoformat(session_id)
            if m.reference_start != BASE.local(session_date, 9, 30) or m.reference_end != BASE.local(session_date, 16):
                exclusions.append(f"{m.profile_id}:partial_or_wrong_RTH_window")
        exclusions.extend(f"{m.profile_id}:{reason}" for reason in m.reasons(cutoff))
    if members and any(m.compatible_key() != members[0].compatible_key() for m in members[1:]):
        exclusions.append("incompatible_contract_feed_adjustment_grid_measurement_or_settings")
    ordered = sorted(members, key=lambda x: x.reference_start)
    ledger = {"policy": "last_3_expected_completed_RTH_sessions", "expected_sessions": expected_ids,
              "members": [{"profile_id": m.profile_id, "sessions": m.included_sessions,
                            "total_mass": sum(m.masses) if all(x is not None and isfinite(x) for x in m.masses) else None,
                            "inclusion_reason": "fixed_previous_three_expected_RTH_weekdays",
                            "reference_start": _stamp(m.reference_start),
                            "reference_end": _stamp(m.reference_end),
                            "last_bar_open": _stamp(m.last_bar_open),
                            "last_bar_close": _stamp(m.last_bar_close),
                            "coverage": m.coverage, "missing_volume": m.missing_volume,
                            "overflow": m.overflow, "input_identity": m.input_identity,
                            "code_identity": m.code_identity,
                            "settings_identity": m.settings_identity}
                           for m in ordered], "exclusions": exclusions,
              "status": "unavailable" if exclusions else "ready", "balance_established": False}
    if exclusions:
        return None, ledger
    lo = min(m.min_key for m in ordered)
    hi = max(m.min_key + len(m.masses) - 1 for m in ordered)
    if hi - lo + 1 > 6000:
        ledger.update(status="unavailable", exclusions=["composite_overflow"])
        return None, ledger
    masses = [0.0] * (hi - lo + 1)
    for m in ordered:
        for i, mass in enumerate(m.masses):
            masses[m.min_key + i - lo] += mass
    template = ordered[0]
    composite = Distribution(
        profile_id=f"composite_RTH3:{snapshot_date.isoformat()}", window="explicit_composite_RTH3",
        reference_start=template.reference_start, reference_end=ordered[-1].reference_end,
        included_sessions=expected_ids, masses=tuple(masses), min_key=lo,
        row_size=template.row_size, grid_origin=template.grid_origin,
        contract=template.contract, feed=template.feed, adjustment=template.adjustment,
        tick_size=template.tick_size, measurement=template.measurement,
        last_bar_open=ordered[-1].last_bar_open, last_bar_close=ordered[-1].last_bar_close,
        input_identity=_hash([(m.profile_id, m.input_identity) for m in ordered]),
        code_identity=template.code_identity, settings_identity=template.settings_identity,
        declared_total=sum(masses),
        lineage=tuple((m.profile_id, sum(m.masses)) for m in ordered))
    ledger["row_sum_lineage"] = composite.lineage
    ledger["composite_id"] = composite.profile_id
    return composite, ledger


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    lower: float
    upper: float
    reference_period: str
    contract: str
    measurement: str
    observed_at: datetime | None
    confirmed_at: datetime | None
    evidence: str
    selection_status: str
    reason: str
    reading_precision: str
    independently_supported: bool = False
    source_historical_available_at: datetime | None = None

    def reasons(self, cutoff: datetime) -> list[str]:
        reasons = []
        if not all((self.anchor_id, self.reference_period, self.contract, self.measurement,
                    self.evidence, self.reason, self.reading_precision)):
            reasons.append("missing_anchor_provenance")
        if self.selection_status not in ("explicit_source", "analyst_proposed"):
            reasons.append("invalid_selection_status")
        if not all(isfinite(x) for x in (self.lower, self.upper)) or self.lower > self.upper:
            reasons.append("invalid_anchor_interval")
        if not self.independently_supported:
            reasons.append("independent_causal_evidence_unsupported")
        if not all(_aware(x) for x in (self.observed_at, self.confirmed_at, cutoff)):
            reasons.append("missing_or_naive_anchor_timing")
        elif self.observed_at > self.confirmed_at:
            reasons.append("observation_after_confirmation")
        elif self.confirmed_at > cutoff:
            reasons.append("later_confirmed_anchor")
        return reasons


def _projection(hypothesis: str, anchors: tuple[Anchor | None, ...], cutoff: datetime,
                tick: float, settings_identity: str, expected_contract: str | None = None) -> dict:
    reasons = []
    for i, anchor in enumerate(anchors):
        if anchor is None:
            reasons.append(f"anchor_{i}:missing_anchor")
        else:
            reasons.extend(f"{anchor.anchor_id}:{r}" for r in anchor.reasons(cutoff))
    present = [x for x in anchors if x is not None]
    if len({x.contract for x in present}) > 1:
        reasons.append("mixed_contracts")
    if expected_contract is not None and any(x.contract != expected_contract for x in present):
        reasons.append("anchor_contract_differs_from_map_contract")
    if len({x.anchor_id for x in present}) != len(present):
        reasons.append("duplicate_anchor_identity")
    if not isfinite(tick) or tick <= 0:
        reasons.append("invalid_tick_size")
    if not settings_identity:
        reasons.append("missing_settings_identity")
    ready_times = [x.confirmed_at for x in present if _aware(x.confirmed_at)]
    return {"hypothesis": hypothesis, "policy": POLICY,
            "anchor_ids": [x.anchor_id if x else None for x in anchors],
            "contract": present[0].contract if present and len({x.contract for x in present}) == 1 else None,
            "anchors": [{k: _stamp(v) if isinstance(v, datetime) else v
                         for k, v in asdict(x).items()} if x else None for x in anchors],
            "status": "unavailable" if reasons else "ready",
            "reasons": reasons, "settings_identity": settings_identity,
            "recorded_confirmation_at": _stamp(max(ready_times)) if ready_times else None,
            "reconstruction_ready_at": _stamp(max(ready_times)) if ready_times and not reasons else None,
            "source_historical_available_at": None,
            "unrounded_intervals": None, "rounded_intervals": None,
            "evidence_status": "explicit_arithmetic_hypothesis_not_recovered_algorithm"}


def _round(interval: tuple[float, float], tick: float) -> list[float]:
    return [floor(interval[0] / tick) * tick, ceil(interval[1] / tick) * tick]


def project_p1(center: Anchor | None, edge: Anchor | None, cutoff: datetime, *,
               tick: float = .25, settings_identity: str = "phase3-3.0.0",
               complete_range: tuple[float, float] | None = None,
               expected_contract: str | None = None) -> dict:
    result = _projection("P1_center_reflection", (center, edge), cutoff, tick,
                         settings_identity, expected_contract)
    if result["reasons"]:
        return result
    interval = (2 * center.lower - edge.upper, 2 * center.upper - edge.lower)
    if not all(isfinite(x) for x in interval):
        result.update(status="unavailable", reasons=["nonfinite_projection_arithmetic"],
                      reconstruction_ready_at=None)
        return result
    identity = False
    if complete_range is not None:
        lo, hi = complete_range
        if not all(isfinite(x) for x in (lo, hi)) or lo >= hi:
            result.update(status="unavailable", reasons=["invalid_complete_range"],
                          reconstruction_ready_at=None)
            return result
        identity = (center.lower == center.upper == (lo + hi) / 2
                    and edge.lower == edge.upper and edge.lower in (lo, hi))
    result.update(unrounded_intervals={"reflection": list(interval)},
                  rounded_intervals={"reflection": _round(interval, tick)},
                  arithmetic="[2*C_low-E_high, 2*C_high-E_low]",
                  opposite_existing_bound_identity=identity,
                  interpretation="opposite_existing_boundary_not_new_external_target" if identity else "candidate_reflection")
    return result


def project_p2(lower: Anchor | None, upper: Anchor | None, cutoff: datetime, *,
               tick: float = .25, settings_identity: str = "phase3-3.0.0",
               expected_contract: str | None = None) -> dict:
    result = _projection("P2_balance_width_extension", (lower, upper), cutoff, tick,
                         settings_identity, expected_contract)
    if result["reasons"]:
        return result
    if lower.upper >= upper.lower:
        result.update(status="unavailable", reasons=["balance_bounds_not_strictly_ordered_for_all_inputs"],
                      reconstruction_ready_at=None)
        return result
    high = (2 * upper.lower - lower.upper, 2 * upper.upper - lower.lower)
    low = (2 * lower.lower - upper.upper, 2 * lower.upper - upper.lower)
    if not all(isfinite(x) for x in high + low):
        result.update(status="unavailable", reasons=["nonfinite_projection_arithmetic"],
                      reconstruction_ready_at=None)
        return result
    result.update(unrounded_intervals={"upper": list(high), "lower": list(low)},
                  rounded_intervals={"upper": _round(high, tick), "lower": _round(low, tick)},
                  width_interval=[upper.lower - lower.upper, upper.upper - lower.lower],
                  arithmetic="upper=[2*H_low-L_high,2*H_high-L_low]; lower=[2*L_low-H_high,2*L_high-H_low]")
    return result


@dataclass(frozen=True)
class ExpandedSnapshot:
    baseline: object
    distributions: tuple[Distribution, ...]
    candidate_ledgers: tuple[dict, ...]
    composite_ledger: dict
    projection_ledgers: tuple[dict, ...]


class TrackedProfile(BASE.Profile):
    """Keep Phase 1 arithmetic while retaining its invalidation cause separately."""
    def __post_init__(self):
        super().__post_init__()
        self.overflowed = False
        self.invalid_volume = False

    def reset(self):
        super().reset()
        self.overflowed = False
        self.invalid_volume = False

    def add(self, high, low, volume):
        if not self.bad:
            valid = (volume is not None and all(isfinite(x) for x in (high, low, volume))
                     and volume >= 0 and low <= high)
            self.invalid_volume = self.invalid_volume or not valid
            if valid:
                lo, hi = floor(low / self.row_size), floor(high / self.row_size)
                lo = min(lo, min(self.bins, default=lo))
                hi = max(hi, max(self.bins, default=hi))
                self.overflowed = hi - lo + 1 > self.max_bins
        super().add(high, low, volume)


class Phase3Engine(BASE.CandidateEngine):
    """Preserve the Phase 1 engine and freeze a separate expanded ledger.

    This is a synthetic specification oracle. Provider input identity must be
    supplied by a caller before any non-synthetic use; no data is fetched here.
    """
    def __init__(self, *, contract="ESZ2026", feed="CME GLOBEX",
                 adjustment="individual_contract_unadjusted", tick_size=.25,
                 input_identity="synthetic-fixture", code_identity="specification-model",
                 settings_identity="phase3-3.0.0", anchors=None, **kwargs):
        super().__init__(**kwargs)
        self.contract, self.feed_identity, self.adjustment = contract, feed, adjustment
        self.tick_size = tick_size
        self.input_identity, self.code_identity = input_identity, code_identity
        self.settings_identity = settings_identity
        self.anchors = deepcopy(anchors or {})
        self.rth_distributions = {}
        self.week_distributions = {}
        self.observed_week_sessions = {}
        self.expanded_snapshot = None

    def window(self, start, end, *, weekly=False):
        return BASE.Window(start, end, TrackedProfile(self.row_size, self.va_pct), weekly)

    def _distribution(self, window, name, included_sessions):
        profile = window.profile
        keys = sorted(profile.bins)
        return Distribution(
            profile_id=f"{name}:{window.start.isoformat()}:{window.end.isoformat()}",
            window=name, reference_start=window.start, reference_end=window.end,
            included_sessions=tuple(included_sessions),
            masses=tuple(profile.bins[k] for k in keys), min_key=min(keys, default=0),
            row_size=profile.row_size, contract=self.contract, feed=self.feed_identity,
            adjustment=self.adjustment, tick_size=self.tick_size,
            last_bar_open=window.last_close - timedelta(minutes=self.minutes) if window.last_close else None,
            last_bar_close=window.last_close, coverage=window.coverage,
            missing_volume=profile.invalid_volume, overflow=profile.overflowed,
            input_identity=self.input_identity, code_identity=self.code_identity,
            settings_identity=self.settings_identity, declared_total=profile.total)

    def accept(self, bar):
        identity = BASE.clock(bar.opened) if bar.confirmed else None
        if identity and self.trade_day != identity.trading_date:
            self.expanded_snapshot = None
        if identity:
            self.observed_week_sessions.setdefault(identity.week_start, set()).add(identity.trading_date.isoformat())
        super().accept(bar)
        if identity and bar.closed == identity.rth_end:
            self.rth_distributions[identity.trading_date] = self._distribution(
                self.rth, "completed_RTH", (identity.trading_date.isoformat(),))
        if identity and bar.closed == identity.week_end:
            self.week_distributions[identity.week_start] = self._distribution(
                self.week, "previous_completed_week",
                tuple(sorted(self.observed_week_sessions.get(identity.week_start, ()))))

    def _missing_distribution(self, name, start, end, sessions):
        return Distribution(
            profile_id=f"{name}:{start.isoformat()}:{end.isoformat()}",
            window=name, reference_start=start, reference_end=end,
            included_sessions=(), expected_sessions=tuple(sessions), masses=(), row_size=self.row_size,
            contract=self.contract, feed=self.feed_identity, adjustment=self.adjustment,
            tick_size=self.tick_size, coverage=False, input_identity=self.input_identity,
            code_identity=self.code_identity, settings_identity=self.settings_identity)

    def freeze(self, bar, cutoff):
        baseline = super().freeze(bar, cutoff)
        day = self.trade_day
        current_week = self._distribution(self.week, "current_week_prefix",
            tuple(sorted(self.observed_week_sessions.get(self.week.start, ()))))
        overnight = self._distribution(self.overnight, "overnight_prefix", (day.isoformat(),))
        # Prefixes end at the frozen cutoff, not the later declared full window end.
        from dataclasses import replace
        current_week = replace(current_week, reference_end=cutoff,
                               profile_id=f"current_week_prefix:{self.week.start.isoformat()}:{cutoff.isoformat()}")
        overnight = replace(overnight, reference_end=cutoff,
                            profile_id=f"overnight_prefix:{self.overnight.start.isoformat()}:{cutoff.isoformat()}")
        distributions = [current_week, overnight]
        previous_day = BASE.prior_trading_date(day)
        distributions.append(self.rth_distributions.get(previous_day) or
            self._missing_distribution("completed_RTH", BASE.local(previous_day, 9, 30),
                                       BASE.local(previous_day, 16), (previous_day.isoformat(),)))
        previous_week_start = BASE.local(self.week.start.date() - timedelta(days=7), 18)
        distributions.append(self.week_distributions.get(previous_week_start) or
            self._missing_distribution("previous_completed_week", previous_week_start,
                BASE.local(previous_week_start.date() + timedelta(days=5), 17),
                tuple((previous_week_start.date() + timedelta(days=x)).isoformat()
                      for x in range(1, 6))))
        members = [self.rth_distributions[d] for d in expected_rth_sessions(day)
                   if d in self.rth_distributions]
        composite, composite_ledger = compose_rth(members, day, cutoff)
        if composite:
            distributions.append(composite)
        else:
            expected = expected_rth_sessions(day)
            distributions.append(self._missing_distribution("explicit_composite_RTH3",
                BASE.local(expected[0], 9, 30), BASE.local(expected[-1], 16),
                tuple(x.isoformat() for x in expected)))
        p1 = project_p1(self.anchors.get("C"), self.anchors.get("E"), cutoff,
                        tick=self.tick_size, settings_identity=self.settings_identity,
                        expected_contract=self.contract)
        p2 = project_p2(self.anchors.get("L"), self.anchors.get("H"), cutoff,
                        tick=self.tick_size, settings_identity=self.settings_identity,
                        expected_contract=self.contract)
        self.expanded_snapshot = ExpandedSnapshot(
            baseline, tuple(distributions),
            tuple(deepcopy(detect_n1_e1(d, cutoff)) for d in distributions),
            deepcopy(composite_ledger), (deepcopy(p1), deepcopy(p2)))
        return baseline
