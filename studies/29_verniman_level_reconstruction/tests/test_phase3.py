"""Hand-worked Phase 3 specification tests; no provider data or Pine execution."""
from dataclasses import replace
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "phase3_model.py"
SPEC = importlib.util.spec_from_file_location("study29_phase3_model", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
DAY = date(2026, 9, 30)
CUTOFF = M.BASE.local(DAY, 9, 25)


def dist(masses, **kwargs):
    values = dict(profile_id="synthetic-profile", window="overnight_prefix",
                  reference_start=M.BASE.local(DAY - timedelta(days=1), 18),
                  reference_end=CUTOFF, included_sessions=(DAY.isoformat(),),
                  masses=tuple(masses), row_size=1, last_bar_open=CUTOFF - timedelta(minutes=5),
                  last_bar_close=CUTOFF, input_identity="synthetic-input",
                  code_identity="specification-model", settings_identity="phase3-3.0.0")
    values.update(kwargs)
    return M.Distribution(**values)


def rth(day, masses=(0, 6, 10, 6, 0), **kwargs):
    end = M.BASE.local(day, 16)
    return dist(masses, profile_id=f"RTH:{day}", window="completed_RTH",
                reference_start=M.BASE.local(day, 9, 30), reference_end=end,
                included_sessions=(day.isoformat(),), last_bar_open=end - timedelta(minutes=5),
                last_bar_close=end, **kwargs)


def anchor(name, low, high=None, **kwargs):
    values = dict(anchor_id=name, lower=low, upper=low if high is None else high,
                  reference_period="synthetic_complete_prior_range", contract="ESZ2026",
                  measurement="explicit_price_interval", observed_at=CUTOFF - timedelta(hours=1),
                  confirmed_at=CUTOFF - timedelta(minutes=30), evidence="synthetic-independent-evidence",
                  selection_status="analyst_proposed", reason="declared synthetic anchor",
                  reading_precision="exact fixture values", independently_supported=True)
    values.update(kwargs)
    return M.Anchor(**values)


def bars(start, end, *, price=100, minutes=5):
    opened = start.astimezone(M.BASE.UTC)
    while opened < end.astimezone(M.BASE.UTC):
        closed = opened + timedelta(minutes=minutes)
        yield M.BASE.Bar(opened.astimezone(M.BASE.NY), closed.astimezone(M.BASE.NY),
                         price + 1, price - 1, price, 10)
        opened = closed


def full_day(day, price=100):
    return list(bars(M.BASE.local(day - timedelta(days=1), 18), M.BASE.local(day, 17), price=price))


class DistributionTests(unittest.TestCase):
    def test_rows_retain_raw_normalized_mass_and_grid_boundaries(self):
        d = dist([2, 6, 2], min_key=10, row_size=4, declared_total=10)
        record = d.record(CUTOFF)
        self.assertEqual(record["readiness"], "ready")
        self.assertEqual(record["rows"][1], {"row_key": 11, "lower": 44, "upper": 48,
                                            "raw_mass": 6, "normalized_mass": .6})
        self.assertEqual(sum(x["normalized_mass"] for x in record["rows"]), 1)
        self.assertIsNone(record["metadata"]["source_historical_available_at"])

    def test_empty_zero_missing_negative_nan_and_overflow_are_unavailable(self):
        for masses in ([], [0, 0], [1, None], [1, -1], [float("nan")], [1e308, 1e308], [1] * 6001):
            with self.subTest(masses=masses[:5]):
                result = M.detect_n1_e1(dist(masses), CUTOFF)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["regions"], [])
                self.assertEqual(result["edge_ledger"], [])

    def test_total_mismatch_coverage_and_terminal_bar_are_separate_failures(self):
        d = dist([1, 3, 1], declared_total=100, coverage=False,
                 last_bar_close=CUTOFF - timedelta(minutes=5))
        self.assertEqual(d.reasons(CUTOFF), ["incomplete_coverage", "total_mass_mismatch",
                                            "incomplete_or_future_boundary"])

    def test_unidentified_or_incompatible_measurement_rejects(self):
        self.assertIn("incompatible_measurement", dist([1], measurement="unknown").reasons(CUTOFF))
        self.assertIn("missing_input_or_provenance_identity", dist([1], input_identity="").reasons(CUTOFF))
        self.assertIn("missing_session_identity", dist([1], included_sessions=()).reasons(CUTOFF))

    def test_future_and_naive_boundary_rejects(self):
        self.assertIn("incomplete_or_future_boundary",
                      dist([1], reference_end=CUTOFF + timedelta(minutes=5),
                           last_bar_close=CUTOFF + timedelta(minutes=5)).reasons(CUTOFF))
        self.assertIn("missing_or_naive_timing", dist([1], reference_end=CUTOFF.replace(tzinfo=None)).reasons(CUTOFF))

    def test_immutable_rows_do_not_acquire_new_mass_after_capture(self):
        masses = [0, 6, 10, 6, 0]
        d = dist(masses)
        result = M.detect_n1_e1(d, CUTOFF)
        masses[2] = 1000
        self.assertEqual(result["regions"][0]["integrated_mass"], 22)
        self.assertEqual(d.masses[2], 10)


class N1Tests(unittest.TestCase):
    def test_single_peak_hand_worked_region_mass_and_edges(self):
        result = M.detect_n1_e1(dist([0, 6, 10, 6, 0]), CUTOFF)
        node = result["regions"][0]
        self.assertEqual(node["representative_key"], 2)
        self.assertEqual(node["saddle"], 0)
        self.assertEqual(node["prominence"], 10)
        self.assertEqual(node["boundary_threshold"], 5)
        self.assertEqual(node["row_keys"], [1, 3])
        self.assertEqual(node["price_interval"], [1, 4])
        self.assertEqual(node["integrated_mass"], 22)
        self.assertEqual([e["boundary"] for e in result["edge_ledger"]], [1, 4])
        self.assertTrue(all(e["qualified"] for e in result["edge_ledger"]))
        self.assertEqual(result["edge_ledger"][0]["contrast"], .6)
        self.assertEqual(result["edge_ledger"][0]["price_interval"], [.5, 1.5])

    def test_broad_shoulder_retains_full_connected_region_and_raw_mass(self):
        result = M.detect_n1_e1(dist([0, 5, 6, 7, 8, 10, 8, 7, 6, 5, 0]), CUTOFF)
        self.assertEqual(len(result["regions"]), 1)
        self.assertEqual(result["regions"][0]["price_interval"], [1, 10])
        self.assertEqual(result["regions"][0]["integrated_mass"], 62)
        self.assertEqual(result["regions"][0]["boundary_threshold"], 5)

    def test_flat_distribution_has_no_interior_peak_or_endpoint_lvn(self):
        result = M.detect_n1_e1(dist([5, 5, 5, 5]), CUTOFF)
        self.assertEqual(result["regions"], [])
        self.assertEqual(result["lvn_ledger"], [])
        self.assertIn("endpoint_plateau_not_interior", result["peaks"][0]["rejection_reasons"])

    def test_equal_maximum_plateau_uses_whole_plateau_lowest_representative(self):
        result = M.detect_n1_e1(dist([0, 10, 10, 0]), CUTOFF)
        node = result["regions"][0]
        self.assertEqual(node["plateau_keys"], [1, 2])
        self.assertEqual(node["representative_key"], 1)
        self.assertEqual(node["price_interval"], [1, 3])
        self.assertEqual(node["integrated_mass"], 20)

    def test_double_distribution_and_lowest_trough_tie(self):
        result = M.detect_n1_e1(dist([0, 6, 10, 6, 1, 1, 1.5, 1, 6, 10, 6, 0]), CUTOFF)
        self.assertEqual([x["representative_key"] for x in result["regions"]], [2, 9])
        lvn = result["lvn_ledger"][0]
        self.assertTrue(lvn["qualified"])
        self.assertEqual(lvn["row_keys"], [4, 5])
        self.assertEqual(lvn["relative_depth"], .1)
        self.assertEqual(lvn["parent_ids"], [x["candidate_id"] for x in result["regions"]])

    def test_shallow_trough_rejected_without_erasing_parent_regions(self):
        result = M.detect_n1_e1(dist([0, 6, 10, 6, 4, 6, 10, 6, 0]), CUTOFF)
        self.assertEqual(len(result["regions"]), 2)
        self.assertFalse(result["lvn_ledger"][0]["qualified"])
        self.assertEqual(result["lvn_ledger"][0]["rejection_reasons"], ["trough_above_0.25_smaller_parent_peak"])

    def test_unequal_adjacent_peak_search_stops_at_strictly_higher(self):
        result = M.detect_n1_e1(dist([0, 10, 8, 9, 0]), CUTOFF)
        smaller = next(x for x in result["peaks"] if x["representative_key"] == 3)
        self.assertEqual(smaller["search_left_stop_key"], 1)
        self.assertEqual(smaller["saddle"], 8)
        self.assertEqual(smaller["prominence"], 1)
        self.assertTrue(smaller["qualified"])  # Inclusive 0.10 threshold.

    def test_height_and_prominence_rejection_reasons_are_preserved(self):
        result = M.detect_n1_e1(dist([0, 10, 0, 1, 0, 8, 7.5, 8, 0]), CUTOFF)
        tiny = next(x for x in result["peaks"] if x["representative_key"] == 3)
        self.assertEqual(tiny["rejection_reasons"], ["height_below_0.20_global_maximum"])
        # Small shoulder prominence is 0.5, below 10% of global max 10.
        shoulder = next(x for x in result["peaks"] if x["representative_key"] == 7)
        self.assertEqual(shoulder["prominence"], 8)  # Equal peaks do not stop the search.
        unequal = M.detect_n1_e1(dist([0, 10, 8, 8.5, 0]), CUTOFF)
        self.assertIn("prominence_below_0.10_global_maximum", unequal["peaks"][1]["rejection_reasons"])

    def test_equal_peaks_can_overlap_and_are_never_merged(self):
        result = M.detect_n1_e1(dist([0, 10, 6, 10, 0]), CUTOFF)
        self.assertEqual(len(result["regions"]), 2)
        self.assertTrue(all(x["overlap"] for x in result["regions"]))
        self.assertEqual([x["price_interval"] for x in result["regions"]], [[1, 4], [1, 4]])
        self.assertFalse(result["lvn_ledger"][0]["qualified"])
        self.assertEqual(result["lvn_ledger"][0]["rejection_reasons"], ["overlapping_or_touching_parent_regions"])

    def test_endpoint_maximum_rejected_even_if_global_maximum(self):
        result = M.detect_n1_e1(dist([10, 4, 6, 0]), CUTOFF)
        self.assertIn("endpoint_plateau_not_interior", result["peaks"][0]["rejection_reasons"])
        self.assertTrue(all(x["representative_key"] != 0 for x in result["regions"]))

    def test_presentation_caps_preserve_uncapped_calculation_and_stable_ids(self):
        masses = [0]
        for _ in range(12):
            masses.extend([6, 10, 6, 0])
        result = M.detect_n1_e1(dist(masses), CUTOFF)
        self.assertEqual(result["counts"]["regions"], 12)
        self.assertEqual(result["counts"]["lvns"], 11)
        self.assertEqual(result["counts"]["edges"], 24)
        self.assertEqual(result["presentation"]["HVN"]["omitted_count"], 4)
        self.assertEqual(result["presentation"]["LVN"]["omitted_count"], 4)
        self.assertEqual(result["presentation"]["HVE"]["omitted_count"], 8)
        self.assertEqual(result, M.detect_n1_e1(dist(masses), CUTOFF))
        self.assertEqual(result["regions"][8]["candidate_id"], "synthetic-profile:HVN:34")
        self.assertTrue(any(x["parent_rank"] == 12 for x in result["edge_ledger"]))

    def test_raw_scaling_preserves_region_and_edge_geometry(self):
        first = M.detect_n1_e1(dist([0, 6, 10, 6, 0]), CUTOFF)
        scaled = M.detect_n1_e1(dist([0, 60, 100, 60, 0]), CUTOFF)
        self.assertEqual(first["regions"][0]["price_interval"], scaled["regions"][0]["price_interval"])
        self.assertEqual(first["edge_ledger"][0]["contrast"], scaled["edge_ledger"][0]["contrast"])


class E1Tests(unittest.TestCase):
    def test_single_row_node_does_not_generate_edges(self):
        result = M.detect_n1_e1(dist([0, 10, 0]), CUTOFF)
        self.assertEqual(result["counts"]["edges"], 0)
        self.assertTrue(all("parent_narrower_than_two_rows" in e["rejection_reasons"] for e in result["edge_ledger"]))

    def test_domain_truncated_side_unavailable_and_other_side_inspected(self):
        d = dist([6, 10, 6, 0])
        parent = {"candidate_id": "manual-N1-parent", "representative_key": 1,
                  "lower_index": 0, "upper_index": 2, "peak_mass": 10}
        lower, upper = M.edge_candidates(d, [parent])
        self.assertEqual(lower["readiness"], "unavailable")
        self.assertIsNone(lower["outside_mass"])
        self.assertIn("domain_truncated_outside_neighbor", lower["rejection_reasons"])
        self.assertTrue(upper["qualified"])

    def test_broad_shallow_border_rejected_inclusive_contrast_threshold(self):
        d = dist([5.1, 6, 10, 6, 5])
        parent = {"candidate_id": "manual-N1-parent", "representative_key": 2,
                  "lower_index": 1, "upper_index": 3, "peak_mass": 10}
        lower, upper = M.edge_candidates(d, [parent])
        self.assertFalse(lower["qualified"])
        self.assertAlmostEqual(lower["contrast"], .09)
        self.assertTrue(upper["qualified"])
        self.assertEqual(upper["contrast"], .1)

    def test_edge_is_grid_boundary_not_poc_center_or_value_area_alias(self):
        result = M.detect_n1_e1(dist([0, 6, 10, 6, 0], min_key=100, row_size=4), CUTOFF)
        region = result["regions"][0]
        self.assertEqual(region["representative_price"], 408)
        self.assertEqual([x["boundary"] for x in result["edge_ledger"]], [404, 416])
        self.assertTrue(all(x["kind"] == "candidate_HVE" and x["parent_id"] == region["candidate_id"]
                            for x in result["edge_ledger"]))
        self.assertNotIn(408, [x["boundary"] for x in result["edge_ledger"]])


class CompositeTests(unittest.TestCase):
    def members(self):
        return [rth(day) for day in M.expected_rth_sessions(DAY)]

    def test_membership_order_does_not_change_histogram_or_identity(self):
        first, ledger = M.compose_rth(self.members(), DAY, CUTOFF)
        reversed_result, second = M.compose_rth(reversed(self.members()), DAY, CUTOFF)
        self.assertEqual(first, reversed_result)
        self.assertEqual(ledger, second)
        self.assertEqual(first.masses, (0, 18, 30, 18, 0))
        self.assertEqual(sum(first.masses), sum(x[1] for x in first.lineage))
        self.assertFalse(ledger["balance_established"])
        self.assertEqual(M.detect_n1_e1(first, CUTOFF)["status"], "ready")

    def test_monday_membership_is_previous_wednesday_thursday_friday(self):
        self.assertEqual(M.expected_rth_sessions(date(2026, 10, 5)),
                         (date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 2)))

    def test_duplicate_and_missing_members_fail_instead_of_double_counting(self):
        members = self.members()
        for rows in (members[:2], members + [members[0]], [members[0], members[0], members[2]]):
            with self.subTest(rows=len(rows)):
                result, ledger = M.compose_rth(rows, DAY, CUTOFF)
                self.assertIsNone(result)
                self.assertEqual(ledger["status"], "unavailable")

    def test_partial_member_and_gap_invalidate_whole_composite(self):
        for changed in (replace(self.members()[1], coverage=False),
                        replace(self.members()[1], reference_start=M.BASE.local(date(2026, 9, 28), 10)),
                        replace(self.members()[1], last_bar_close=M.BASE.local(date(2026, 9, 28), 15, 55))):
            members = self.members()
            members[1] = changed
            self.assertIsNone(M.compose_rth(members, DAY, CUTOFF)[0])

    def test_rollover_feed_adjustment_grid_and_measurement_are_incompatible(self):
        for field, value in (("contract", "ESH2027"), ("feed", "other-feed"),
                             ("adjustment", "back_adjusted"), ("row_size", 2),
                             ("measurement", "TPO")):
            with self.subTest(field=field):
                members = self.members()
                members[1] = replace(members[1], **{field: value})
                result, ledger = M.compose_rth(members, DAY, CUTOFF)
                self.assertIsNone(result)
                self.assertIn("incompatible_contract_feed_adjustment_grid_measurement_or_settings", ledger["exclusions"])

    def test_nonoverlapping_price_domains_are_zero_filled_only_after_member_validation(self):
        members = self.members()
        members[1] = replace(members[1], min_key=6)
        result, ledger = M.compose_rth(members, DAY, CUTOFF)
        self.assertEqual(result.masses[5], 0)
        self.assertEqual(result.masses[7], 6)
        self.assertEqual(sum(result.masses), 66)
        self.assertEqual(ledger["status"], "ready")


class ProjectionTests(unittest.TestCase):
    def test_reflection_and_width_extension_are_distinct_hand_worked_formulas(self):
        p1 = M.project_p1(anchor("C", 100), anchor("E", 90), CUTOFF)
        p2 = M.project_p2(anchor("L", 90), anchor("H", 110), CUTOFF)
        self.assertEqual(p1["unrounded_intervals"], {"reflection": [110, 110]})
        self.assertEqual(p2["unrounded_intervals"], {"upper": [130, 130], "lower": [70, 70]})
        self.assertNotEqual(p1["hypothesis"], p2["hypothesis"])
        self.assertIsNone(p1["source_historical_available_at"])

    def test_interval_uncertainty_and_outward_tick_rounding_preserve_unrounded_values(self):
        p1 = M.project_p1(anchor("C", 100.1, 100.2), anchor("E", 90.1, 90.3), CUTOFF)
        self.assertAlmostEqual(p1["unrounded_intervals"]["reflection"][0], 109.9)
        self.assertAlmostEqual(p1["unrounded_intervals"]["reflection"][1], 110.3)
        self.assertEqual(p1["rounded_intervals"], {"reflection": [109.75, 110.5]})
        p2 = M.project_p2(anchor("L", 90, 91), anchor("H", 109, 110), CUTOFF)
        self.assertEqual(p2["unrounded_intervals"], {"upper": [127, 130], "lower": [70, 73]})
        self.assertEqual(p2["width_interval"], [18, 20])

    def test_midpoint_reflection_is_existing_opposite_bound_identity(self):
        p1 = M.project_p1(anchor("C", 100), anchor("E", 90), CUTOFF, complete_range=(90, 110))
        self.assertTrue(p1["opposite_existing_bound_identity"])
        self.assertEqual(p1["interpretation"], "opposite_existing_boundary_not_new_external_target")
        self.assertEqual(p1["unrounded_intervals"]["reflection"], [110, 110])

    def test_missing_invalid_reversed_and_overlapping_bounds_unavailable(self):
        for center, edge in ((None, anchor("E", 90)), (anchor("C", float("nan")), anchor("E", 90)),
                             (anchor("C", 101, 100), anchor("E", 90))):
            self.assertEqual(M.project_p1(center, edge, CUTOFF)["status"], "unavailable")
        p2 = M.project_p2(anchor("L", 100, 110), anchor("H", 105, 115), CUTOFF)
        self.assertEqual(p2["status"], "unavailable")
        self.assertIsNone(p2["unrounded_intervals"])
        self.assertIsNone(p2["reconstruction_ready_at"])
        p1 = M.project_p1(anchor("C", 100), anchor("E", 90), CUTOFF, complete_range=(110, 90))
        self.assertEqual(p1["status"], "unavailable")
        self.assertIsNone(p1["reconstruction_ready_at"])

    def test_nonfinite_arithmetic_is_unavailable_even_with_finite_anchors(self):
        p1 = M.project_p1(anchor("C", 1e308), anchor("E", -1e308), CUTOFF)
        p2 = M.project_p2(anchor("L", -1e308), anchor("H", 1e308), CUTOFF)
        self.assertEqual(p1["reasons"], ["nonfinite_projection_arithmetic"])
        self.assertEqual(p2["reasons"], ["nonfinite_projection_arithmetic"])
        self.assertIsNone(p1["unrounded_intervals"])
        self.assertIsNone(p2["reconstruction_ready_at"])

    def test_entered_timestamp_does_not_prove_causal_evidence(self):
        p1 = M.project_p1(anchor("C", 100, independently_supported=False), anchor("E", 90), CUTOFF)
        self.assertEqual(p1["status"], "unavailable")
        self.assertIn("C:independent_causal_evidence_unsupported", p1["reasons"])
        self.assertIsNone(p1["reconstruction_ready_at"])
        self.assertIsNotNone(p1["recorded_confirmation_at"])
        self.assertIsNone(p1["source_historical_available_at"])

    def test_later_confirmed_anchor_excluded_even_with_early_observation(self):
        late = anchor("C", 100, confirmed_at=CUTOFF + timedelta(minutes=5))
        p1 = M.project_p1(late, anchor("E", 90), CUTOFF)
        self.assertEqual(p1["status"], "unavailable")
        self.assertIn("C:later_confirmed_anchor", p1["reasons"])
        self.assertIsNone(p1["rounded_intervals"])
        # A later calculation can become ready; that never rewrites the earlier one.
        self.assertEqual(M.project_p1(late, anchor("E", 90), CUTOFF + timedelta(minutes=5))["status"], "ready")
        self.assertEqual(p1["status"], "unavailable")

    def test_different_declared_measurements_do_not_erase_supported_price_anchors(self):
        p1 = M.project_p1(anchor("C", 100, measurement="declared_profile_POC"),
                          anchor("E", 90, measurement="observed_range_low"), CUTOFF)
        self.assertEqual(p1["status"], "ready")
        self.assertEqual(p1["unrounded_intervals"], {"reflection": [110, 110]})

    def test_anchor_contract_must_match_map_even_when_anchors_match_each_other(self):
        p1 = M.project_p1(anchor("C", 100, contract="ESH2027"),
                          anchor("E", 90, contract="ESH2027"), CUTOFF,
                          expected_contract="ESZ2026")
        p2 = M.project_p2(anchor("L", 90, contract="ESH2027"),
                          anchor("H", 110, contract="ESH2027"), CUTOFF,
                          expected_contract="ESZ2026")
        self.assertEqual(p1["reasons"], ["anchor_contract_differs_from_map_contract"])
        self.assertEqual(p2["reasons"], ["anchor_contract_differs_from_map_contract"])
        self.assertIsNone(p1["reconstruction_ready_at"])

    def test_mixed_contracts_duplicate_ids_and_inconsistent_times_reject(self):
        pairs = ((anchor("C", 100, contract="ESH2027"), anchor("E", 90)),
                 (anchor("same", 100), anchor("same", 90)),
                 (anchor("C", 100, observed_at=CUTOFF, confirmed_at=CUTOFF - timedelta(minutes=1)), anchor("E", 90)))
        for center, edge in pairs:
            self.assertEqual(M.project_p1(center, edge, CUTOFF)["status"], "unavailable")


class SnapshotAndBaselineTests(unittest.TestCase):
    def history(self):
        result = []
        for offset in range(16):
            day = date(2026, 9, 14) + timedelta(days=offset)
            if day.weekday() < 5:
                result += full_day(day, 100 + offset)
        result += list(bars(M.BASE.local(DAY - timedelta(days=1), 18), CUTOFF, price=120))
        return result

    def test_expansion_preserves_all_19_original_baseline_fields(self):
        original, expanded = M.BASE.CandidateEngine(), M.Phase3Engine()
        history = self.history()
        original.feed(history)
        expanded.feed(history)
        self.assertEqual(expanded.snapshot, original.snapshot)
        self.assertEqual(expanded.expanded_snapshot.baseline, original.snapshot)
        self.assertEqual(len(original.snapshot.values), 19)
        self.assertTrue(all(x is not None for x in original.snapshot.values))
        self.assertEqual(len(expanded.expanded_snapshot.distributions), 5)
        self.assertEqual(expanded.expanded_snapshot.composite_ledger["status"], "ready")
        self.assertTrue(all(x["status"] == "ready" for x in expanded.expanded_snapshot.candidate_ledgers))

    def test_advance_restart_anchor_change_and_profile_mutation_cannot_rewrite_snapshot(self):
        engine = M.Phase3Engine(anchors={"C": anchor("C", 100), "E": anchor("E", 90)})
        history = self.history()
        engine.feed(history)
        saved = engine.expanded_snapshot
        engine.anchors["C"] = anchor("C", 1000)
        engine.feed(bars(CUTOFF, M.BASE.local(DAY, 16), price=900))
        self.assertIs(engine.expanded_snapshot, saved)
        self.assertEqual(saved.projection_ledgers[0]["unrounded_intervals"], {"reflection": [110, 110]})
        restarted = M.Phase3Engine(anchors={"C": anchor("C", 100), "E": anchor("E", 90)})
        restarted.feed(history)
        self.assertEqual(saved, restarted.expanded_snapshot)

    def test_new_day_clears_expansion_and_missing_terminal_cannot_invent_it(self):
        engine = M.Phase3Engine()
        engine.feed(self.history())
        engine.feed(bars(CUTOFF, M.BASE.local(DAY, 17)))
        engine.accept(next(bars(M.BASE.local(DAY, 18), M.BASE.local(DAY, 18, 5))))
        self.assertIsNone(engine.expanded_snapshot)
        engine.feed(bars(M.BASE.local(DAY, 18, 5), M.BASE.local(DAY + timedelta(days=1), 9, 20)))
        engine.accept(next(bars(M.BASE.local(DAY + timedelta(days=1), 9, 25), M.BASE.local(DAY + timedelta(days=1), 9, 30))))
        self.assertIsNone(engine.expanded_snapshot)
        self.assertEqual(engine.snapshot_status, "missing exact cutoff bar")

    def test_unconfirmed_and_truncated_history_are_unavailable_not_false_detection(self):
        engine = M.Phase3Engine()
        engine.feed(bars(M.BASE.local(DAY, 9), M.BASE.local(DAY, 9, 20)))
        bar = next(bars(M.BASE.local(DAY, 9, 20), CUTOFF))
        engine.accept(replace(bar, confirmed=False))
        self.assertIsNone(engine.expanded_snapshot)
        engine.accept(bar)
        self.assertTrue(all(x["status"] == "unavailable" for x in engine.expanded_snapshot.candidate_ledgers))
        self.assertEqual(engine.expanded_snapshot.composite_ledger["status"], "unavailable")
        self.assertEqual(len(engine.expanded_snapshot.distributions), 5)
        week = next(x for x in engine.expanded_snapshot.distributions if x.window == "current_week_prefix")
        self.assertEqual(week.included_sessions, (DAY.isoformat(),))
        missing = next(x for x in engine.expanded_snapshot.distributions if x.window == "completed_RTH")
        self.assertEqual(missing.included_sessions, ())
        self.assertEqual(missing.expected_sessions, ((DAY - timedelta(days=1)).isoformat(),))
        self.assertTrue(all(x["status"] == "unavailable" for x in engine.expanded_snapshot.projection_ledgers))

    def test_reset_drops_invalid_profile_state_and_retains_overflow_reason(self):
        p = M.TrackedProfile(row_size=1, max_bins=3)
        p.add(4, 0, 100)
        self.assertTrue(p.overflowed)
        self.assertEqual(p.levels(), (None, None, None))
        p.reset()
        p.add(1, 1, 10)
        self.assertFalse(p.overflowed)
        self.assertFalse(p.invalid_volume)
        p.add(1, 1, None)
        self.assertTrue(p.invalid_volume)
        self.assertEqual(p.levels(), (None, None, None))


if __name__ == "__main__":
    unittest.main()
