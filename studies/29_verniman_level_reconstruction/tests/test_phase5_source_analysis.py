"""Synthetic source-role and saved-only comparison checks; no answers read."""
from copy import deepcopy
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


B = module("study29_phase5_projection_tests", STUDY / "phase5/build_source_role_ledger.py")
A = module("study29_phase5_saved_comparison_tests", STUDY / "phase5/analyze_saved_development.py")
M = module("study29_phase5_analysis_synthetic_model", STUDY / "src/phase4_model.py")
H = module("study29_phase5_analysis_fixed_hydrator", STUDY / "phase4/analyze_saved_training.py")
U = module("study29_phase5_analysis_fixed_units", STUDY / "phase4/source_roles.py")
C = module("study29_phase5_analysis_fixed_comparison", STUDY / "phase4/run_training.py")
W = module("study29_phase5_analysis_window_adapter", STUDY / "phase5/window_identity.py")
DAY = "2026-10-15"


def plan(identifier="synthetic-a"):
    return {"session_date": DAY, "outlook_id": identifier, "source_revision_id": identifier, "product": "ES", "contract": "ESZ26", "available_at": None, "source_claimed_published_at": None, "body_text": "ESZ26: YVAH 120 YPOC 110 YVAL 100 GAP 110\nsynthetic plan", "bullish_conditions": "unmeasured synthetic condition", "bearish_conditions": "unmeasured synthetic condition"}


def level(identifier="synthetic-a", side="bullish", role="trigger", price="100", ordinal=1):
    return {"session_date": DAY, "outlook_id": identifier, "side": side, "role": role, "ordinal": ordinal, "price_low": price, "price_high": price, "source_text": "YVAL " + price, "available_at": None}


def saved(profile="synthetic-rth"):
    day = date.fromisoformat(DAY); cutoff = M.P3.BASE.local(day, 9, 25)
    refs = []
    for name, value, family, role in (("YVAL", 100, "VAL", "value_boundary"), ("YPOC", 110, "POC", "modal"), ("YVAH", 120, "VAH", "value_boundary"), ("ONPOC", 105, "POC", "modal"), ("ONH", 130, "ONH", "range_extreme"), ("ONL", 90, "ONL", "range_extreme")):
        refs.append(M.Candidate(name, value, (value, value), family, role, "completed_RTH", profile, cutoff - timedelta(days=1), True, auction_id=profile, origin_role=name, source_identity="synthetic-market-only"))
    inputs = M.SelectionInputs(day, cutoff, cutoff - timedelta(minutes=5), cutoff, 97, tuple(refs), (), True, True, input_identity="synthetic-market-only")
    return {"schema": "abacus.study29.phase5.local-development-map/v1", "session_date": DAY, "selector_inputs": M.record(inputs), "selections": {p + "-" + d: M.record(M.select_map(inputs, pivot_policy=p, target_policy=d)) for p in ("P0", "B0", "B1") for d in ("D0", "D1")}}


class SourceRoleProjectionTests(unittest.TestCase):
    def project(self, plans=None, levels=None, intakes=None):
        return B.project_day(DAY, plans or [], levels or [], [], [], intakes or [], [], [], U)

    def test_conflicting_plans_preserve_both_revisions_without_nearest_choice(self):
        levels = [level(identifier=revision, side=side, price=price) for revision, price in (("synthetic-a", "100"), ("synthetic-b", "105")) for side in ("bullish", "bearish")]
        rows, session = self.project([plan("synthetic-a"), plan("synthetic-b")], levels)
        units = session["functional_divider_interpretations"]
        self.assertEqual(len(units), 2)
        self.assertEqual([unit["primary_price_interval"] for unit in units], [["100", "100"], ["105", "105"]])
        self.assertEqual(len(session["canonical_source_revision_ids"]), 2)
        self.assertTrue(all(row["available_at"] is None for row in rows))

    def test_header_fields_are_structural_not_targets(self):
        rows, _ = self.project([plan()], [level(), level(side="bearish")])
        headers = [row for row in rows if "HEADER" in row["level_id"]]
        self.assertEqual(len(headers), 4)
        self.assertTrue(all(row["phase4_role"] == "structural_reference_without_selected_scenario_role" for row in headers))

    def test_all_targets_beyond_three_cap_preserved(self):
        rows, _ = self.project([plan()], [level(role="target", price=str(120 + rank), ordinal=rank) for rank in range(1, 6)])
        targets = [row for row in rows if row["phase4_role"] == "ordered_bullish_destination"]
        self.assertEqual([row["source_target_order"] for row in targets], [1, 2, 3, 4, 5])

    def test_closing_label_and_execution_do_not_supply_missing_plan(self):
        intake = {"session_date": DAY, "observation_id": "synthetic-observation", "sources": [{"source_id": "synthetic-post", "posted_at": None, "chart_session_date": DAY}], "closing_notes": [{"source_id": "synthetic-post", "category": "reference_level", "label_raw": "HVE 100", "numeric_value": "100", "note_id": "n1"}], "markers": [{"source_id": "synthetic-post", "annotation_raw": "Buy", "price": None}]}
        rows, session = self.project(intakes=[intake])
        self.assertEqual(session["source_review_status"], "source_suitability_failure")
        self.assertEqual(rows[0]["phase4_role"], "structural_reference_without_selected_scenario_role")
        self.assertEqual(len(session["execution_annotations"]["records"]), 1)
        self.assertEqual(session["selected_source_refs"], [])

    def test_missing_canonical_source_status_retained(self):
        rows, session = self.project()
        self.assertEqual(rows, [])
        self.assertTrue(session["failure_reasons"])

    def test_source_day_outside_allowlist_rejected(self):
        wrong = plan(); wrong["session_date"] = "2026-10-21"
        with self.assertRaisesRegex(ValueError, "outside exact"):
            self.project([wrong])

    def test_literal_compound_label_and_conditions_preserved(self):
        raw = level(); raw["source_text"] = "HVE-YVAL 100"
        rows, _ = self.project([plan()], [raw])
        self.assertEqual(rows[0]["original_label"], "HVE-YVAL 100")
        self.assertEqual(rows[0]["families"], ["HVE", "YVAL"])
        self.assertEqual(rows[0]["directional_conditions"], "unmeasured synthetic condition")


class SavedComparisonTests(unittest.TestCase):
    def test_hydration_never_reexecutes_selector_or_mutates_saved_schema(self):
        document = saved(); before = deepcopy(document)
        with patch.object(M, "select_map", side_effect=AssertionError("must not recompute")):
            inputs, selections = A.hydrate_saved(document, M, H)
        self.assertEqual(document, before)
        self.assertEqual(set(selections), A.POLICIES)
        self.assertEqual(inputs.trading_date.isoformat(), DAY)

    def test_selected_coordinate_must_remain_original(self):
        document = saved(); document["selections"]["P0-D1"]["pivot"]["candidate"]["price"] = 999
        with self.assertRaisesRegex(ValueError, "unchanged original"):
            A.hydrate_saved(document, M, H)

    def test_hidden_saved_map_schema_day_rejected(self):
        document = saved(); document["session_date"] = "2026-10-21"
        with self.assertRaisesRegex(ValueError, "authorized"):
            A.hydrate_saved(document, M, H)

    def test_six_saved_configurations_required(self):
        document = saved(); document["selections"].pop("B0-D0")
        with self.assertRaisesRegex(ValueError, "all six"):
            A.hydrate_saved(document, M, H)

    def test_unknown_windows_are_not_estimable_not_zero_coverage(self):
        rows, _ = B.project_day(DAY, [plan()], [level(), level(side="bearish"), level(role="target", price="120")], [], [], [], [], [], U)
        document = saved()
        with patch.object(M, "select_map", side_effect=AssertionError("must not recompute")):
            result = A.analyze_document(document, rows, M, H, C)
        self.assertEqual(result["P0-D1"]["pivot"]["strict_decomposition"]["status"], "not_estimable")
        self.assertIsNone(result["P0-D1"]["pivot"]["strict_decomposition"]["selected_matches_conditional_on_generated_candidate"])

    def test_revision_target_diagnostics_are_not_pooled(self):
        levels = [level(identifier=revision, role="target", price="120") for revision in ("synthetic-a", "synthetic-b")]
        rows, _ = B.project_day(DAY, [plan("synthetic-a"), plan("synthetic-b")], levels, [], [], [], [], [], U)
        result = A.analyze_document(saved(), rows, M, H, C)
        diagnostic = result["P0-D1"]["bullish"]["coordinate_only_diagnostic"]
        self.assertEqual(diagnostic["status"], "source_stratified_no_pooled_score")
        self.assertIsNone(diagnostic["matched_count"])
        self.assertEqual(len(diagnostic["per_source_stratum"]), 2)

    def test_supported_explicit_window_reaches_frozen_primary_matcher(self):
        profile = "completed_RTH:2026-10-14T09:30:00-04:00:2026-10-14T16:00:00-04:00"
        rows, _ = B.project_day(DAY, [plan()], [level(), level(side="bearish")], [], [], [], [], [], U)
        assessments = {row["level_id"]: {"status": "supported_explicit_metadata", "supported_window_id": profile, "normalized_contract": "ESZ2026", "adjustment": "individual_contract_unadjusted"} for row in rows}
        document = saved(profile)
        with patch.object(M, "select_map", side_effect=AssertionError("must not recompute")):
            result = A.analyze_document(document, rows, M, H, C, window_adapter=W, assessments=assessments)
        strict = result["P0-D1"]["pivot"]["strict_decomposition"]
        self.assertEqual(strict["status"], "compared")
        self.assertEqual(strict["source_occurrences_with_compatible_generated_candidate"], 1)
        self.assertEqual(strict["selected_matches_conditional_on_generated_candidate"], 1)

    def test_common_divider_does_not_pick_supported_window_from_one_branch(self):
        profile = "completed_RTH:2026-10-14T09:30:00-04:00:2026-10-14T16:00:00-04:00"
        rows, _ = B.project_day(DAY, [plan()], [level(), level(side="bearish")], [], [], [], [], [], U)
        assessments = {row["level_id"]: {"status": "supported_explicit_metadata", "supported_window_id": profile, "normalized_contract": "ESZ2026", "adjustment": "individual_contract_unadjusted"} for row in rows}
        assessments[rows[0]["level_id"]] = {"status": "unidentified_no_explicit_window_metadata"}
        result = A.analyze_document(saved(profile), rows, M, H, C, window_adapter=W, assessments=assessments)
        self.assertEqual(result["P0-D1"]["pivot"]["strict_decomposition"]["status"], "not_estimable")


if __name__ == "__main__":
    unittest.main()
