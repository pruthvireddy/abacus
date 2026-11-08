"""Synthetic translated-model checks, not Pine compilation or replay tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
import sys
import unittest
import random

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reference_model import Bar, NY, Profile, UTC, local
from pivot_model import (
    CoverageWindow, Edge, NodeLedger, PivotEngine, Region, edge, nodes, select,
)


def histogram(values, start=0):
    return {start + i: float(value) for i, value in enumerate(values)}


def ledger(*regions, omitted=0):
    return NodeLedger(tuple(regions), tuple(regions), (), omitted, (), "ON/test")


def region(name="r1", lo=27, hi=30, *, lower=True, overlap=False, width=4):
    r = Region(name, "ON/test", (lo + 1, lo + 1), lo + 1,
               lo, hi, 10, 0, 10, 30, width, overlap)
    r.lower = Edge(name, "lower", lo * width if lower else None,
                   ((lo * width - width / 2), (lo * width + width / 2)) if lower else None,
                   .5 if lower else None, "qualified" if lower else "domain truncated", "ON/test")
    r.upper = Edge(name, "upper", (hi + 1) * width,
                   ((hi + 1) * width - width / 2, (hi + 1) * width + width / 2),
                   .5, "qualified", "ON/test")
    return r


def bars(start, end, *, high=100, low=100, close=100, volume=100):
    # Step in actual elapsed time, preserving aware New York boundary identities.
    now = start.astimezone(UTC)
    stop = end.astimezone(UTC)
    while now < stop:
        following = now + timedelta(minutes=5)
        yield Bar(now.astimezone(NY), following.astimezone(NY), high, low, close, volume)
        now = following


def warmup(engine, previous=date(2026, 9, 30)):
    engine.feed(bars(local(previous, 9, 30), local(previous, 16)))


def overnight(day=date(2026, 10, 1), **kwargs):
    return list(bars(local(day - timedelta(days=1), 18), local(day, 9, 25), **kwargs))


class SelectionTests(unittest.TestCase):
    def pick(self, price=100, onpoc=100, parents=None, **kwargs):
        return select(104, 100, 96, onpoc, price,
                      ledger() if parents is None else parents, **kwargs)

    def test_below_value_selects_reclaim_boundary(self):
        s = self.pick(price=93.75)
        self.assertEqual((s.price, s.reason, s.origin, s.fallback),
                         (96, "Prior-value reclaim boundary", "YVAL", False))

    def test_above_value_qualified_lower_edge(self):
        r = region()
        s = self.pick(price=112, parents=ledger(r))
        self.assertEqual((s.price, s.reason, s.origin, s.fallback),
                         (108, "Hold higher auction", "r1/lower E1", False))
        self.assertNotEqual(s.price, r.representative * r.width)

    def test_above_value_absent_parent_fallback(self):
        s = self.pick(price=112)
        self.assertEqual((s.price, s.reason, s.fallback),
                         (104, "Prior-value boundary fallback", True))
        self.assertTrue(s.fallback_status.startswith("absent:"))

    def test_above_value_absent_eligible_edge_even_with_valid_parent(self):
        s = self.pick(price=112, parents=ledger(region(lo=25, hi=30)))
        self.assertEqual(s.price, 104)
        self.assertTrue(s.fallback_status.startswith("absent:"))

    def test_competing_regions_fallback(self):
        s = self.pick(price=112, parents=ledger(region(), region("r2", lo=28, hi=32)))
        self.assertEqual(s.price, 104)
        self.assertTrue(s.fallback_status.startswith("ambiguous:"))

    def test_overlapped_parent_blocks_otherwise_unique_edge(self):
        s = self.pick(price=112, parents=ledger(region(overlap=True)))
        self.assertEqual(s.price, 104)
        self.assertIn("overlapping", s.fallback_status)

    def test_cap_omission_blocks_uniqueness(self):
        s = self.pick(price=112, parents=ledger(region(), omitted=1))
        self.assertEqual(s.price, 104)
        self.assertEqual(s.fallback_status, "incomplete: region cap")

    def test_missing_edge_fallback(self):
        s = self.pick(price=112, parents=ledger(region(lower=False)))
        self.assertEqual(s.price, 104)
        self.assertEqual(s.fallback_status, "incomplete: missing lower E1 evidence")

    def test_incomplete_other_containing_parent_blocks_unique_qualified_edge(self):
        # Inclusive physical boundaries can touch even when row parents disjoint.
        s = self.pick(price=112, parents=ledger(region(lo=27, hi=27),
            region("unknown", lo=28, hi=30, lower=False)))
        self.assertEqual(s.price, 104)
        self.assertTrue(s.fallback_status.startswith("incomplete:"))

    def test_within_value_shifted_lower(self):
        s = self.pick(onpoc=97.75)
        self.assertEqual((s.price, s.reason, s.fallback),
                         (96, "Overnight value shifted lower", False))

    def test_within_value_shifted_higher(self):
        s = self.pick(onpoc=102.25)
        self.assertEqual((s.price, s.reason, s.fallback),
                         (104, "Overnight value shifted higher", False))

    def test_balanced_fallback(self):
        s = self.pick()
        self.assertEqual((s.price, s.origin, s.fallback, s.fallback_status),
                         (100, "YPOC", True, "balanced"))
        self.assertEqual(s.reason, "Balanced fallback — no unique directional divider")

    def test_exact_price_tolerance_boundaries_are_inside(self):
        for price in (94, 106):
            with self.subTest(price=price):
                s = self.pick(price=price, onpoc=100)
                self.assertEqual((s.price, s.fallback_status), (100, "balanced"))

    def test_exact_onpoc_tolerance_boundaries_are_balanced(self):
        for onpoc in (98, 102):
            with self.subTest(onpoc=onpoc):
                self.assertEqual(self.pick(onpoc=onpoc).fallback_status, "balanced")

    def test_edge_exactly_at_value_plus_buffer_is_ineligible(self):
        r = region(width=2, lo=53, hi=60)
        s = select(104, 100, 96, 100, 112, ledger(r), tick=.25, width=4)
        self.assertEqual((s.price, s.fallback), (104, True))

    def test_region_containment_includes_physical_boundaries(self):
        r = region()
        self.assertTrue(r.contains(108))
        self.assertTrue(r.contains(124))
        self.assertFalse(r.contains(124.25))

    def test_tolerance_uses_two_ticks_for_small_row(self):
        s = self.pick(tick=1, width=1)
        self.assertEqual(s.tolerance, 2)

    def test_missing_required_inputs_unavailable(self):
        inputs = [104, 100, 96, 100, 100]
        for i in range(5):
            bad = inputs.copy()
            bad[i] = None
            with self.subTest(input=i):
                s = select(*bad, ledger())
                self.assertIsNone(s.price)
                self.assertEqual(s.fallback_status, "unavailable")
        self.assertIsNone(select(*inputs, None).price)
        self.assertIsNone(select(104, 100, 96, float("nan"), 100, ledger()).price)

    def test_confluence_preserves_both_original_prices_and_identities(self):
        r = region(lo=25, hi=30)
        s = self.pick(onpoc=100, parents=ledger(r))
        self.assertEqual(s.price, 100)
        self.assertIn(("YPOC", 100, "r1/lower E1", 100), s.confluence)
        r = region(lo=26, hi=30)
        s = self.pick(onpoc=100, parents=ledger(r))
        self.assertEqual(s.price, 100)
        self.assertIn(("YPOC", 100, "r1/lower E1", 104), s.confluence)
        self.assertEqual(r.lower.coordinate, 104)

    def test_confluence_does_not_count_unqualified_or_distant_edges(self):
        self.assertEqual(self.pick(parents=ledger(region())).confluence, ())
        r = region(lo=25, hi=30, lower=False)
        self.assertEqual(self.pick(parents=ledger(r)).confluence, ())


class ProfileTests(unittest.TestCase):
    def test_inclusive_floor_allocation_and_boundary_high(self):
        p = Profile(4)
        p.add(high=8, low=4, volume=100)
        self.assertEqual(p.bins, {1: 50, 2: 50})
        self.assertEqual(p.total, 100)

    def test_lowest_price_poc_tie_and_upward_value_area_tie(self):
        p = Profile(1)
        for price, volume in ((0, 10), (1, 20), (2, 10)):
            p.add(price, price, volume)
        self.assertEqual(p.levels(), (2, 1, 1))
        p = Profile(1)
        p.add(1, 0, 100)
        self.assertEqual(p.levels(), (1, 0, 0))

    def test_zero_missing_negative_volume_and_overflow(self):
        p = Profile(1)
        p.add(1, 0, 0)
        self.assertEqual(p.levels(), (None, None, None))
        for volume in (None, -1, float("nan")):
            p = Profile(1)
            p.add(1, 0, volume)
            self.assertTrue(p.bad)
            self.assertEqual(p.levels(), (None, None, None))
        p = Profile(1)
        p.add(6000, 0, 10)
        self.assertTrue(p.bad)
        self.assertEqual(p.bins, {})

    def test_zero_individual_bar_is_allowed_when_total_positive(self):
        p = Profile(1)
        p.add(1, 0, 0)
        p.add(1, 0, 20)
        self.assertEqual(p.total, 20)
        self.assertFalse(p.bad)
        self.assertIsNotNone(p.levels()[0])


class N1E1Tests(unittest.TestCase):
    def test_plateau_rep_and_region_bounds(self):
        result = nodes(histogram([0, 4, 10, 10, 4, 0]))
        self.assertEqual(len(result.regions), 1)
        r = result.regions[0]
        self.assertEqual((r.plateau, r.representative, r.lo, r.hi), ((2, 3), 2, 2, 3))
        self.assertEqual((r.height, r.saddle, r.prominence, r.mass), (10, 0, 10, 20))
        self.assertEqual(r.bounds, (8, 16))

    def test_e1_coordinates_uncertainty_and_parent_ids(self):
        r = nodes(histogram([0, 4, 10, 10, 4, 0]), profile_id="ON/date").regions[0]
        self.assertEqual((r.lower.coordinate, r.upper.coordinate), (8, 16))
        self.assertEqual((r.lower.uncertainty, r.upper.uncertainty), ((6, 10), (14, 18)))
        self.assertAlmostEqual(r.lower.contrast, .6)
        self.assertEqual((r.lower.region_id, r.lower.profile_id), (r.region_id, "ON/date"))

    def test_one_row_parent_has_no_qualified_edges(self):
        r = nodes(histogram([0, 10, 0])).regions[0]
        self.assertEqual((r.lower.coordinate, r.upper.coordinate), (None, None))
        self.assertEqual(r.lower.status, "parent narrower than two rows")

    def test_prominence_search_stops_at_strictly_higher_peak(self):
        result = nodes(histogram([0, 10, 9.5, 10.5, 0]))
        self.assertIn((1, "prominence"), result.rejected)
        self.assertEqual([r.representative for r in result.regions], [3])

    def test_height_threshold(self):
        result = nodes(histogram([0, 1, 0, 10, 10, 0]))
        self.assertIn((1, "height"), result.rejected)

    def test_exact_height_and_prominence_thresholds(self):
        result = nodes(histogram([0, 2, 0, 10, 10, 0]))
        self.assertIn(1, [r.representative for r in result.regions])
        result = nodes(histogram([0, 9, 8, 10, 0]))
        r = next(r for r in result.regions if r.representative == 1)
        self.assertEqual((r.saddle, r.prominence), (8, 1))

    def test_exact_prominence_survives_normalized_reporting(self):
        # p=6, saddle=5, d=1, global maximum=10 qualifies at the exact
        # ten-percent boundary. Normalize-first subtraction loses it to IEEE
        # rounding on this fixture; raw-scale arithmetic avoids that extra error.
        values = [1, 5, 9, 9, 4, 1, 8, 5, 6, 6, 0, 0, 1, 7, 10, 3, 5, 1, 7, 5]
        result = nodes(histogram(values))
        r = next(r for r in result.regions if r.representative == 8)
        self.assertEqual((r.height, r.saddle, r.prominence), (6, 5, 1))
        self.assertAlmostEqual(r.normalized_height, 6 / sum(values))
        self.assertAlmostEqual(r.normalized_prominence, 1 / sum(values))
        self.assertAlmostEqual(r.normalized_mass, r.mass / sum(values))

    def test_rank_height_prominence_then_price(self):
        result = nodes(histogram([0, 10, 10, 0, 10, 10, 0]))
        self.assertEqual([r.representative for r in result.regions], [1, 4])
        result = nodes(histogram([0, 10, 9, 11, 0, 10, 0]))
        self.assertEqual([r.representative for r in result.regions], [3, 5])

    def test_overlapping_equal_peaks_flagged_never_merged(self):
        result = nodes(histogram([0, 6, 10, 6, 10, 6, 0]))
        self.assertEqual(len(result.regions), 2)
        self.assertTrue(all(r.overlap for r in result.regions))
        self.assertEqual([(r.lo, r.hi) for r in result.regions], [(1, 5), (1, 5)])

    def test_domain_endpoint_is_not_interior_peak(self):
        for values in ([10, 6, 0], [0, 6, 10], [10, 10, 10]):
            self.assertEqual(nodes(histogram(values)).regions, ())

    def test_domain_truncated_edges_are_unavailable(self):
        r = region(lo=0, hi=1, width=4)
        e = edge(r, "lower", histogram([10, 10, 0]))
        self.assertEqual((e.status, e.coordinate, e.uncertainty), ("domain truncated", None, None))
        r = region(lo=1, hi=2, width=4)
        self.assertEqual(edge(r, "upper", histogram([0, 10, 10])).status, "domain truncated")

    def test_border_contrast_threshold(self):
        r = nodes(histogram([0, 4.1, 5, 10, 10, 5, 4.1, 0])).regions[0]
        self.assertEqual(r.lower.status, "insufficient border contrast")
        r = nodes(histogram([0, 4, 5, 10, 10, 5, 4, 0])).regions[0]
        self.assertEqual(r.lower.status, "qualified")
        self.assertAlmostEqual(r.lower.contrast, .1)

    def test_caps_preserve_full_ledger_and_omitted_count(self):
        values = [0]
        for _ in range(10):
            values.extend([10, 10, 0])
        result = nodes(histogram(values))
        self.assertEqual((len(result.regions), len(result.qualified), result.omitted), (8, 10, 2))
        self.assertEqual([r.representative for r in result.regions], list(range(1, 23, 3)))
        self.assertLessEqual(sum(e.status == "qualified" for r in result.regions for e in (r.lower, r.upper)), 16)

    def test_lvn_lowest_price_plateau_and_cap(self):
        result = nodes(histogram([0, 10, 10, 0, 0, 10, 10, 0]))
        self.assertEqual(result.lvns, ((3, 4, 3, 0),))

    def test_scale_invariance_of_normalized_thresholds(self):
        original = nodes(histogram([0, 4, 10, 10, 4, 0]))
        scaled = nodes(histogram([0, 400, 1000, 1000, 400, 0]))
        self.assertEqual([(r.lo, r.hi, r.representative) for r in original.regions],
                         [(r.lo, r.hi, r.representative) for r in scaled.regions])
        self.assertEqual(original.regions[0].lower.coordinate, scaled.regions[0].lower.coordinate)

    def test_invalid_distributions_are_not_false_negative_detections(self):
        for bins_ in ({}, {0: 0}, {0: None}, {0: -1}, {0: float("nan")}, {0: 1, 2: 1}):
            with self.subTest(bins=bins_):
                with self.assertRaises((ValueError, TypeError)):
                    nodes(bins_)


class PineOptimizationTranslationTests(unittest.TestCase):
    """Optimized-path translations compared with simple independent arithmetic.

    These checks do not execute, import, or compile the Pine source.
    """
    @staticmethod
    def side_min(values, reverse=False):
        result = [0] * len(values)
        heights, block_mins = [], []
        for idx in (range(len(values) - 1, -1, -1) if reverse else range(len(values))):
            height = values[idx]
            bottom = height
            while heights and heights[-1] <= height:
                bottom = min(bottom, block_mins.pop())
                heights.pop()
            result[idx] = bottom
            heights.append(height)
            block_mins.append(bottom)
        return result

    def test_monotonic_stack_minima_match_brute_strictly_higher_search(self):
        rng = random.Random(20261030)
        for trial in range(500):
            values = [rng.randrange(11) for _ in range(rng.randrange(1, 100))]
            for reverse, step in ((False, -1), (True, 1)):
                expected = []
                for idx, height in enumerate(values):
                    minimum = height
                    k = idx + step
                    while 0 <= k < len(values):
                        minimum = min(minimum, values[k])
                        if values[k] > height:
                            break
                        k += step
                    expected.append(minimum)
                self.assertEqual(self.side_min(values, reverse), expected, (trial, reverse, values))

    def test_range_tree_binary_growth_matches_contiguous_expansion(self):
        rng = random.Random(925)
        for _ in range(300):
            values = [rng.randrange(11) for _ in range(rng.randrange(1, 100))]
            base = 1
            while base < len(values):
                base *= 2
            tree = [float("inf")] * (base * 2)
            tree[base:base + len(values)] = values
            for idx in range(base - 1, 0, -1):
                tree[idx] = min(tree[idx * 2], tree[idx * 2 + 1])

            def minimum(first, last):
                lo, hi, answer = base + first, base + last, float("inf")
                while lo <= hi:
                    if lo % 2:
                        answer = min(answer, tree[lo])
                        lo += 1
                    if not hi % 2:
                        answer = min(answer, tree[hi])
                        hi -= 1
                    lo //= 2
                    hi //= 2
                return answer

            for index in range(len(values)):
                boundary = rng.uniform(0, values[index])
                expected_lo = expected_hi = index
                while expected_lo and values[expected_lo - 1] >= boundary:
                    expected_lo -= 1
                while expected_hi + 1 < len(values) and values[expected_hi + 1] >= boundary:
                    expected_hi += 1
                lo, hi = 0, index
                while lo < hi:
                    middle = (lo + hi) // 2
                    if minimum(middle, index) >= boundary:
                        hi = middle
                    else:
                        lo = middle + 1
                actual_lo = lo
                lo, hi = index, len(values) - 1
                while lo < hi:
                    middle = (lo + hi + 1) // 2
                    if minimum(index, middle) >= boundary:
                        lo = middle
                    else:
                        hi = middle - 1
                self.assertEqual((actual_lo, lo), (expected_lo, expected_hi))

    def test_overlap_difference_coverage_matches_pairwise_intervals(self):
        # Includes a broad later parent engulfing earlier disjoint parents.
        rng = random.Random(16)
        examples = [[(1, 2), (5, 6), (1, 9)]]
        for _ in range(200):
            intervals = []
            for representative in sorted(rng.sample(range(50), rng.randrange(1, 15))):
                intervals.append((rng.randrange(representative + 1), rng.randrange(representative, 50)))
            examples.append(intervals)
        for intervals in examples:
            difference = [0] * 51
            for lo, hi in intervals:
                difference[lo] += 1
                difference[hi + 1] -= 1
            active, overlap_prefix = 0, [0]
            for idx in range(50):
                active += difference[idx]
                overlap_prefix.append(overlap_prefix[-1] + (active > 1))
            actual = [overlap_prefix[hi + 1] > overlap_prefix[lo] for lo, hi in intervals]
            expected = [any(i != j and max(lo, other_lo) <= min(hi, other_hi)
                            for j, (other_lo, other_hi) in enumerate(intervals))
                        for i, (lo, hi) in enumerate(intervals)]
            self.assertEqual(actual, expected)


class TimingAndCoverageTests(unittest.TestCase):
    def test_supported_chart_gate(self):
        for settings in ({"minutes": 1}, {"minutes": 15}, {"standard": False}):
            with self.assertRaisesRegex(ValueError, "Unsupported chart"):
                PivotEngine(**settings)

    def test_regular_counts_terminal_included_and_next_bar_excluded(self):
        e = PivotEngine()
        warmup(e)
        prefix = overnight()
        self.assertEqual((e.rth.bars, len(prefix)), (78, 185))
        e.feed(prefix[:-1])
        self.assertIsNone(e.frozen)
        self.assertEqual(e.status, "waiting")
        e.accept(prefix[-1])
        frozen = e.frozen
        self.assertEqual(e.status, "ready")
        self.assertEqual((frozen.last_included_open, frozen.last_included_close),
                         (local(date(2026, 10, 1), 9, 20), local(date(2026, 10, 1), 9, 25)))
        e.feed(bars(local(date(2026, 10, 1), 9, 25), local(date(2026, 10, 1), 9, 30), high=2000, low=0, close=1900))
        self.assertIs(e.frozen, frozen)
        self.assertEqual(e.overnight.profile.total, 18500)

    def test_missing_terminal_bar_withholds_pivot(self):
        e = PivotEngine()
        warmup(e)
        e.feed(overnight()[:-1])
        e.feed(bars(local(date(2026, 10, 1), 9, 25), local(date(2026, 10, 1), 9, 30)))
        self.assertIsNone(e.frozen.selection.price)
        self.assertEqual(e.status, "unavailable: missing terminal bar")

    def test_interior_gap_and_partial_overnight_unavailable(self):
        for mutate in (lambda p: p[1:], lambda p: p[:30] + p[31:]):
            e = PivotEngine()
            warmup(e)
            e.feed(mutate(overnight()))
            self.assertIsNone(e.frozen.selection.price)
            self.assertIn("unavailable", e.status)

    def test_missing_zero_and_negative_volume(self):
        for bad in (None, 0, -1):
            e = PivotEngine()
            warmup(e)
            prefix = overnight(volume=bad)
            e.feed(prefix)
            self.assertIsNone(e.frozen.selection.price)
        e = PivotEngine()
        warmup(e)
        prefix = overnight()
        prefix[50] = replace(prefix[50], volume=0)
        e.feed(prefix)
        self.assertEqual(e.status, "ready")

    def test_partial_initial_rth_shortened_session_and_missing_rth_terminal(self):
        d = date(2026, 9, 30)
        variations = (list(bars(local(d, 10), local(d, 16))),
                      list(bars(local(d, 9, 30), local(d, 13))),
                      list(bars(local(d, 9, 30), local(d, 15, 55))))
        for rth in variations:
            e = PivotEngine()
            e.feed(rth)
            e.feed(overnight())
            self.assertIsNone(e.frozen.selection.price)

    def test_missing_rth_bar_does_not_substitute_older_complete_session(self):
        e = PivotEngine()
        warmup(e, date(2026, 9, 29))
        partial = list(bars(local(date(2026, 9, 30), 9, 30), local(date(2026, 9, 30), 16)))
        e.feed(partial[:20] + partial[21:])
        e.feed(overnight())
        self.assertEqual(e.frozen.rth_date, date(2026, 9, 30))
        self.assertIsNone(e.frozen.selection.price)

    def test_no_prior_history_unavailable(self):
        e = PivotEngine()
        e.feed(overnight())
        self.assertIsNone(e.frozen.selection.price)
        self.assertIn("history", e.status)

    def test_monday_uses_friday_actual_rth(self):
        e = PivotEngine()
        warmup(e, date(2026, 10, 2))
        e.feed(overnight(date(2026, 10, 5)))
        self.assertEqual(e.status, "ready")
        self.assertEqual(e.frozen.rth_date, date(2026, 10, 2))

    def test_new_futures_day_resets_pivot_and_acceptance(self):
        e = PivotEngine()
        warmup(e)
        e.feed(overnight())
        e.feed(bars(local(date(2026, 10, 1), 9, 25), local(date(2026, 10, 1), 9, 35), high=120, low=120, close=120))
        self.assertEqual(e.acceptance, "bullish acceptance")
        e.feed(bars(local(date(2026, 10, 1), 18), local(date(2026, 10, 1), 18, 5)))
        self.assertEqual(e.day, date(2026, 10, 2))
        self.assertIsNone(e.frozen)
        self.assertEqual((e.status, e.up, e.down, e.acceptance), ("waiting", 0, 0, "unresolved"))

    def test_unconfirmed_terminal_is_not_used(self):
        e = PivotEngine()
        warmup(e)
        prefix = overnight()
        e.feed(prefix[:-1])
        e.accept(replace(prefix[-1], confirmed=False))
        self.assertIsNone(e.frozen)
        e.accept(prefix[-1], realtime=True)
        self.assertEqual(e.frozen.mode, "observed realtime")

    def test_historical_reconstruction_and_replay_restart_reproduce(self):
        a, b = PivotEngine(), PivotEngine()
        for e in (a, b):
            warmup(e)
            e.feed(overnight())
        self.assertEqual(a.frozen, b.frozen)
        self.assertEqual(a.frozen.mode, "historically reconstructed")

    def test_identical_prefix_radically_different_post_cutoff_invariant(self):
        a, b = PivotEngine(), PivotEngine()
        for e in (a, b):
            warmup(e)
            e.feed(overnight())
        frozen = a.frozen
        a.feed(bars(local(date(2026, 10, 1), 9, 25), local(date(2026, 10, 1), 16),
                    high=100000, low=99000, close=99999, volume=10**9))
        b.feed(bars(local(date(2026, 10, 1), 9, 25), local(date(2026, 10, 1), 16),
                    high=2, low=1, close=1, volume=1))
        self.assertEqual(a.frozen, frozen)
        self.assertEqual(b.frozen, frozen)
        self.assertEqual((a.acceptance, b.acceptance), ("bullish acceptance", "bearish acceptance"))

    def test_acceptance_counts_post_cutoff_only_and_requires_consecutive_closes(self):
        e = PivotEngine()
        warmup(e)
        e.feed(overnight())
        self.assertEqual((e.up, e.down), (0, 0))
        d = date(2026, 10, 1)
        e.feed(bars(local(d, 9, 25), local(d, 9, 30), high=120, low=120, close=120))
        self.assertEqual(e.acceptance, "unresolved")
        e.feed(bars(local(d, 9, 30), local(d, 9, 35), high=120, low=120, close=120))
        self.assertEqual(e.acceptance, "bullish acceptance")
        e.feed(bars(local(d, 9, 35), local(d, 9, 40), high=100, low=100, close=100))
        self.assertEqual((e.acceptance, e.up), ("unresolved", 0))

    def test_new_york_dst_uses_civil_cutoff(self):
        expectations = ((date(2026, 3, 6), 14), (date(2026, 3, 9), 13),
                        (date(2026, 10, 30), 13), (date(2026, 11, 2), 14))
        for day, hour in expectations:
            with self.subTest(day=day):
                cutoff = local(day, 9, 25)
                self.assertEqual((cutoff.astimezone(UTC).hour, cutoff.astimezone(UTC).minute), (hour, 25))
                self.assertEqual(len(overnight(day)), 185)

    def test_bad_duration_and_overflow_window_unavailable(self):
        d = date(2026, 10, 1)
        w = CoverageWindow(local(d, 9), local(d, 9, 5), 1)
        w.add(Bar(local(d, 9), local(d, 9, 5), 6000, 0, 100, 100))
        self.assertFalse(w.ready)
        w = CoverageWindow(local(d, 9), local(d, 9, 5), 1)
        w.add(Bar(local(d, 9), local(d, 9, 4), 100, 100, 100, 100))
        self.assertFalse(w.ready)


if __name__ == "__main__":
    unittest.main()
