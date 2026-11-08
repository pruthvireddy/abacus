"""Strict, saved-reference comparison for Study 29 Phase 3.

No source discovery, data loading, detector, target selector or source-window
inference occurs here. The caller supplies explicitly normalized identities.
All feasible pairs are retained; matching is descriptive construction coverage,
not evidence of recovered algorithms or historical source availability.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

SUPPORTED_FAMILIES = frozenset({
    "HVN", "LVN", "HVE", "PBT", "YVAH", "YPOC", "YVAL", "ONH", "ONL",
    "YHOD", "YLOD", "PRIOR_CLOSE",
})


@dataclass(frozen=True)
class SourceReference:
    # This is a level-occurrence ID (for example inventory level_id), not the
    # shared source-document ID attached to several level occurrences.
    source_id: str
    session_date: str
    source_class: str
    revision_id: str
    families: tuple[str, ...]
    interval: tuple[object, object] | None
    # None means unidentified. Do not pass a prose uncertainty string as if it
    # were an exact session/member/cutoff identity.
    window_id: str | None
    contract: str | None
    adjustment: str | None
    timing_class: str = "unresolved"
    source_historical_available_at: str | None = None


@dataclass(frozen=True)
class CandidateReference:
    candidate_id: str
    session_date: str
    family: str
    interval: tuple[object, object] | None
    window_id: str
    contract: str
    adjustment: str
    ready: bool = True
    displayed: bool = True
    boundary: object | None = None


def _interval(value: tuple[object, object] | None) -> tuple[Decimal, Decimal] | None:
    if value is None or len(value) != 2:
        return None
    try:
        low, high = (Decimal(str(item)) for item in value)
    except (InvalidOperation, ValueError):
        return None
    return (low, high) if low.is_finite() and high.is_finite() and low <= high else None


def interval_gap(source: tuple[object, object], candidate: tuple[object, object]) -> Decimal:
    """Nonnegative distance between closed intervals; touching is zero."""
    first, second = _interval(source), _interval(candidate)
    if first is None or second is None:
        raise ValueError("finite, ordered interval bounds required")
    return max(Decimal(0), first[0] - second[1], second[0] - first[1])


@dataclass
class _Arc:
    target: int
    reverse: int
    capacity: int
    cost: tuple[Decimal, int]


def _sum_cost(first: tuple[Decimal, int], second: tuple[Decimal, int]) -> tuple[Decimal, int]:
    return first[0] + second[0], first[1] + second[1]


def _optimal_pairs(
    source_ids: Iterable[str], candidate_ids: Iterable[str],
    edges: dict[tuple[str, str], Decimal],
) -> tuple[list[tuple[str, str]], Decimal]:
    """Unit-capacity min-cost maximum flow with exact lexicographic tie-break.

    The second cost component is a bit vector favoring the earliest sorted
    (source ID, candidate ID) pair. For fixed cardinality and total gap this
    chooses the lexicographically smallest sorted pair list, without perturbing
    the primary error objective. Reverse arcs allow prior assignments to move.
    """
    sources, candidates = sorted(source_ids), sorted(candidate_ids)
    source_nodes = {key: i + 1 for i, key in enumerate(sources)}
    candidate_nodes = {key: i + 1 + len(sources) for i, key in enumerate(candidates)}
    sink = len(sources) + len(candidates) + 1
    graph: list[list[_Arc]] = [[] for _ in range(sink + 1)]

    def add(start: int, end: int, cost: tuple[Decimal, int]) -> _Arc:
        forward = _Arc(end, len(graph[end]), 1, cost)
        backward = _Arc(start, len(graph[start]), 0, (-cost[0], -cost[1]))
        graph[start].append(forward)
        graph[end].append(backward)
        return forward

    zero = (Decimal(0), 0)
    for source in sources:
        add(0, source_nodes[source], zero)
    for candidate in candidates:
        add(candidate_nodes[candidate], sink, zero)
    pair_arcs = {}
    ordered = sorted(edges)
    for index, pair in enumerate(ordered):
        # Integer arithmetic keeps tie-breaking exact, even for equal gaps.
        pair_arcs[pair] = add(source_nodes[pair[0]], candidate_nodes[pair[1]],
                             (edges[pair], -(1 << (len(ordered) - index - 1))))

    while True:
        distances: list[tuple[Decimal, int] | None] = [None] * len(graph)
        previous: list[tuple[int, int] | None] = [None] * len(graph)
        distances[0] = zero
        # Bellman-Ford permits negative residual arcs. Every augmentation
        # preserves minimum cost at its cardinality; no negative cycle remains.
        for _ in range(len(graph) - 1):
            changed = False
            for start, arcs in enumerate(graph):
                if distances[start] is None:
                    continue
                for index, arc in enumerate(arcs):
                    if not arc.capacity:
                        continue
                    proposal = _sum_cost(distances[start], arc.cost)
                    if distances[arc.target] is None or proposal < distances[arc.target]:
                        distances[arc.target] = proposal
                        previous[arc.target] = (start, index)
                        changed = True
            if not changed:
                break
        if distances[sink] is None:
            break
        node = sink
        while node:
            assert previous[node] is not None
            start, index = previous[node]
            arc = graph[start][index]
            arc.capacity = 0
            graph[node][arc.reverse].capacity = 1
            node = start

    chosen = sorted(pair for pair, arc in pair_arcs.items() if arc.capacity == 0)
    return chosen, sum((edges[pair] for pair in chosen), Decimal(0))


def _stratum(source: SourceReference, family: str) -> tuple[str, ...]:
    return (source.session_date, source.source_class, source.revision_id, family,
            source.window_id or "", source.contract or "", source.adjustment or "")


def compare_references(
    sources: Iterable[SourceReference], candidates: Iterable[CandidateReference], *,
    candidate_map_ready: bool, tolerance: object = "1.0",
) -> dict:
    """Compare supplied saved inputs under the frozen Phase 3 eligibility rule.

    `candidate_map_ready=False` returns not-executed status. Failure records or
    baseline-only maps must use that state. Candidate caps affect display counts,
    not the complete qualified-ledger comparison. No inferred alias is applied.
    The caller supplies qualified family candidates only: a P1 known-opposite-
    boundary identity is not an external PBT candidate and must not be supplied
    as a ready PBT reference. Anchor qualification belongs to the detector ledger.
    """
    sources, candidates = list(sources), list(candidates)
    if len({source.source_id for source in sources}) != len(sources):
        raise ValueError("source occurrence IDs must be unique")
    if len({candidate.candidate_id for candidate in candidates}) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    limit = Decimal(str(tolerance))
    if not limit.is_finite() or limit < 0:
        raise ValueError("finite nonnegative tolerance required")
    source_intervals = {source.source_id: _interval(source.interval) for source in sources}
    candidate_intervals = {candidate.candidate_id: _interval(candidate.interval) for candidate in candidates}
    candidate_exclusions = []
    valid_candidates = []
    for candidate in candidates:
        reasons = []
        if not candidate.ready:
            reasons.append("not_ready")
        if candidate_intervals[candidate.candidate_id] is None:
            reasons.append("invalid_interval")
        if not all((candidate.session_date, candidate.family, candidate.window_id,
                    candidate.contract, candidate.adjustment)):
            reasons.append("missing_candidate_identity")
        if candidate.boundary is not None:
            try:
                if not Decimal(str(candidate.boundary)).is_finite():
                    reasons.append("invalid_boundary")
            except InvalidOperation:
                reasons.append("invalid_boundary")
        if reasons:
            candidate_exclusions.append({"candidate_id": candidate.candidate_id, "reasons": reasons})
        else:
            valid_candidates.append(candidate)
    result = {
        "status": "not_executed" if not candidate_map_ready else "not_estimable",
        "tolerance_points": str(limit),
        "readable_source_occurrences": sum(value is not None for value in source_intervals.values()),
        "source_occurrences": len(sources),
        "qualified_generated_count": len(valid_candidates),
        "displayed_generated_count": sum(candidate.displayed for candidate in valid_candidates),
        "presentation_omitted_ids": sorted(candidate.candidate_id for candidate in valid_candidates if not candidate.displayed),
        "candidate_exclusions": candidate_exclusions,
        "source_role_exclusions": [], "unresolved_alternatives": [],
        "strata": [], "occurrences": [],
        "eligible_role_count": 0, "matched_role_count": 0,
        "eligible_occurrence_count": 0, "matched_occurrence_count": 0,
        "fully_covered_occurrence_count": 0, "primary_role_coverage": None,
        "primary_occurrence_coverage": None,
        "unmatched_generated_candidate_ids": [],
    }
    if not candidate_map_ready:
        result["reason"] = "actual_expanded_candidate_map_unavailable"
        result["qualified_generated_count"] = None
        result["displayed_generated_count"] = None
        result["presentation_omitted_ids"] = None
        return result

    grouped: dict[tuple[str, ...], list[SourceReference]] = {}
    eligible: dict[str, list[str]] = {source.source_id: [] for source in sources}
    matched: dict[str, list[str]] = {source.source_id: [] for source in sources}
    for source in sources:
        if not source.families or len(set(source.families)) != len(source.families):
            raise ValueError("source families must be nonempty and unique")
        for family in source.families:
            reasons = []
            if source_intervals[source.source_id] is None:
                reasons.append("unreadable_or_invalid_interval")
            if family not in SUPPORTED_FAMILIES:
                reasons.append("unsupported_family")
            if not source.window_id:
                reasons.append("unknown_reference_window")
            if not source.contract or not source.adjustment:
                reasons.append("unknown_contract_or_price_coordinates")
            if reasons:
                result["source_role_exclusions"].append({
                    "source_id": source.source_id, "family": family, "reasons": reasons,
                    "source_timing_class": source.timing_class,
                    "source_historical_available_at": source.source_historical_available_at,
                })
                if (not source.window_id and source_intervals[source.source_id] is not None
                        and family in SUPPORTED_FAMILIES):
                    for candidate in sorted(valid_candidates, key=lambda item: item.candidate_id):
                        if candidate.family != family or candidate.session_date != source.session_date:
                            continue
                        if source.contract and source.contract != candidate.contract:
                            continue
                        if source.adjustment and source.adjustment != candidate.adjustment:
                            continue
                        gap = interval_gap(source.interval, candidate.interval)
                        result["unresolved_alternatives"].append({
                            "source_id": source.source_id, "family": family,
                            "candidate_id": candidate.candidate_id,
                            "candidate_window_id": candidate.window_id,
                            "interval_gap_points": str(gap), "within_tolerance": gap <= limit,
                            "status": "descriptive_only_unidentified_source_window",
                            "primary_match": False,
                        })
            else:
                eligible[source.source_id].append(family)
                grouped.setdefault(_stratum(source, family), []).append(source)

    all_matched_candidates = set()
    for key, rows in sorted(grouped.items()):
        date, source_class, revision, family, window, contract, adjustment = key
        available = [candidate for candidate in valid_candidates
                     if (candidate.session_date, candidate.family, candidate.window_id,
                         candidate.contract, candidate.adjustment)
                     == (date, family, window, contract, adjustment)]
        edges = {}
        for source in rows:
            for candidate in available:
                gap = interval_gap(source.interval, candidate.interval)
                if gap <= limit:
                    edges[source.source_id, candidate.candidate_id] = gap
        chosen, error = _optimal_pairs((source.source_id for source in rows),
                                       (candidate.candidate_id for candidate in available), edges)
        chosen_set = set(chosen)
        alternatives = []
        # Retain feasibility separately from whether a pair participates in any
        # maximum-cardinality/minimum-gap optimum (before deterministic tie-break).
        for pair, gap in sorted(edges.items()):
            residual_edges = {edge: distance for edge, distance in edges.items()
                              if edge[0] != pair[0] and edge[1] != pair[1]}
            remainder, residual_error = _optimal_pairs(
                (source.source_id for source in rows if source.source_id != pair[0]),
                (candidate.candidate_id for candidate in available if candidate.candidate_id != pair[1]),
                residual_edges,
            )
            alternatives.append({"source_id": pair[0], "candidate_id": pair[1],
                                 "interval_gap_points": str(gap), "selected": pair in chosen_set,
                                 "in_equal_optimum": len(remainder) + 1 == len(chosen)
                                 and residual_error + gap == error})
        candidate_by_id = {candidate.candidate_id: candidate for candidate in available}
        source_by_id = {source.source_id: source for source in rows}
        assignments = []
        for source_id, candidate_id in chosen:
            matched[source_id].append(family)
            all_matched_candidates.add(candidate_id)
            source_interval, candidate_interval = source_intervals[source_id], candidate_intervals[candidate_id]
            candidate = candidate_by_id[candidate_id]
            assignments.append({
                "source_id": source_id, "candidate_id": candidate_id,
                "interval_gap_points": str(edges[source_id, candidate_id]),
                "source_interval_width": str(source_interval[1] - source_interval[0]),
                "candidate_interval_width": str(candidate_interval[1] - candidate_interval[0]),
                "boundary": None if candidate.boundary is None else str(candidate.boundary),
                "source_midpoint_minus_boundary": None if candidate.boundary is None else
                str((source_interval[0] + source_interval[1]) / 2 - Decimal(str(candidate.boundary))),
                "source_timing_class": source_by_id[source_id].timing_class,
                "source_historical_available_at": source_by_id[source_id].source_historical_available_at,
            })
        used_sources = {pair[0] for pair in chosen}
        used_candidates = {pair[1] for pair in chosen}
        result["strata"].append({
            "session_date": date, "source_class": source_class, "revision_id": revision,
            "family": family, "window_id": window, "contract": contract, "adjustment": adjustment,
            "eligible_source_roles": len(rows), "qualified_candidates": len(available),
            "assignments": assignments, "total_interval_gap_points": str(error),
            "feasible_alternatives": alternatives,
            "unmatched_source_ids": sorted(source.source_id for source in rows if source.source_id not in used_sources),
            "unmatched_candidate_ids": sorted(candidate.candidate_id for candidate in available if candidate.candidate_id not in used_candidates),
        })

    for source in sorted(sources, key=lambda value: value.source_id):
        source_eligible, source_matched = sorted(eligible[source.source_id]), sorted(matched[source.source_id])
        full = len(source_matched) == len(source.families)
        result["occurrences"].append({
            "source_id": source.source_id, "families": list(source.families),
            "eligible_roles": source_eligible, "matched_roles": source_matched,
            "coverage": "full_roles" if full else "partial_roles" if source_matched else
                        "unmatched" if source_eligible else "not_eligible",
        })
        result["eligible_role_count"] += len(source_eligible)
        result["matched_role_count"] += len(source_matched)
        result["eligible_occurrence_count"] += bool(source_eligible)
        result["matched_occurrence_count"] += bool(source_matched)
        result["fully_covered_occurrence_count"] += full
    if result["eligible_role_count"]:
        result["status"] = "compared"
        result["primary_role_coverage"] = result["matched_role_count"] / result["eligible_role_count"]
        result["primary_occurrence_coverage"] = result["matched_occurrence_count"] / result["eligible_occurrence_count"]
    result["unmatched_generated_candidate_ids"] = sorted(
        candidate.candidate_id for candidate in valid_candidates if candidate.candidate_id not in all_matched_candidates)
    return result
