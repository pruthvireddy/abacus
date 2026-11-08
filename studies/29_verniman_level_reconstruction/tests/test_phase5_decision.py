"""Synthetic frozen development decision rule; no market or answer reads."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "phase5/assess_decision.py"
SPEC = importlib.util.spec_from_file_location("study29_phase5_pure_decision", PATH)
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


def fixture():
    units = {role: [{"unit_id": role + ":" + day, "session_date": day,
                     "source_class": "synthetic_plan", "source_revision_id": "synthetic_revision",
                     "family_supported": True, "contract_supported": True, "exact_window_supported": True,
                     "eligible_source_occurrence_count": 1,
                     "eligible_source_occurrence_ids": ["source:" + role + ":" + day]}
                    for day in D.DATES[:3]] for role in D.ROLES}
    denominators = dict(zip(D.METRICS, (3, 3, 3, 9, 3, 3)))
    metrics = {name: {"status": "estimable", "numerator": 1 if direction == 1 else 2,
                      "denominator": denominators[name]} for name, direction in D.METRICS.items()}
    rows = {config: {"metric_basis": "strict_common_primary_units",
                     "common_primary_unit_ids": {role: [u["unit_id"] for u in units[role]] for role in D.ROLES},
                     "metrics": deepcopy(metrics), "abstentions": {role: 1 for role in D.ROLES}}
            for config in D.CONFIGURATIONS}
    return {"schema": D.SCHEMA, "decision_rule_sha256": D.RULE_SHA256,
            "scheduled_dates": list(D.DATES), "configurations": list(D.CONFIGURATIONS),
            "engineering_gate": {"status": "passed", "receipt": {"path": "synthetic/gate-check.json", "sha256": "a" * 64}},
            "common_primary_units": units, "essential_unmeasured_conditions": [], "configuration_results": rows}


def improve(payload, config="B1-D1", metric="pivot_identity_role_price_agreement"):
    row = payload["configuration_results"][config]["metrics"][metric]
    row["numerator"] += D.METRICS[metric]


class DecisionRuleTests(unittest.TestCase):
    def test_rule_identity_matches_unchanged_frozen_document(self):
        self.assertEqual(sha256((PATH.parent / "decision-rule.md").read_bytes()).hexdigest(), D.RULE_SHA256)

    def test_one_strict_dominator_is_selected_only_as_bounded_development_result(self):
        payload = fixture(); improve(payload)
        result = D.assess(payload)
        self.assertEqual(result["selected_configuration"], "B1-D1")
        self.assertEqual(result["dominating_alternatives"], ["B1-D1"])
        self.assertTrue(result["identifiability_passed"])
        self.assertFalse(result["source_method_final_evaluation_ready"])
        self.assertFalse(result["phase6_execution_authorized"])

    def test_failed_engineering_keeps_answers_out_of_this_assessment(self):
        payload = fixture(); payload["engineering_gate"] = {"status": "failed"}
        payload.pop("configuration_results"); payload.pop("common_primary_units")
        result = D.assess(payload)
        self.assertEqual(result["status"], "engineering_incomplete")
        self.assertIsNone(result["retained_engineering_default"])
        self.assertIsNone(result["selected_configuration"])

    def test_passed_engineering_requires_a_pinned_receipt(self):
        payload = fixture(); payload["engineering_gate"].pop("receipt")
        with self.assertRaisesRegex(ValueError, "receipt"):
            D.assess(payload)

    def test_no_supported_units_is_not_estimable_not_zero_accuracy(self):
        payload = fixture(); payload["common_primary_units"] = {r: [] for r in D.ROLES}
        for row in payload["configuration_results"].values():
            row["metrics"] = {k: {"status": "not_estimable", "numerator": None, "denominator": 0} for k in D.METRICS}
        result = D.assess(payload)
        self.assertIn("INSUFFICIENT_COMMON_ELIGIBLE_DATES", result["reasons"])
        self.assertTrue(result["no_validated_configuration_selected"])
        self.assertEqual(result["retained_engineering_default"], D.PRIMARY)

    def test_three_distinct_dates_are_required_for_each_branch(self):
        payload = fixture(); payload["common_primary_units"]["bearish"] = payload["common_primary_units"]["bearish"][:2]
        self.assertIn("INSUFFICIENT_COMMON_ELIGIBLE_DATES", D.assess(payload)["reasons"])

    def test_many_revisions_on_one_date_do_not_make_three_dates(self):
        payload = fixture()
        for row in payload["common_primary_units"]["pivot"]:
            row["session_date"] = D.DATES[0]
        self.assertEqual(D.assess(payload)["common_eligible_dates"]["pivot"], [D.DATES[0]])
        self.assertFalse(D.assess(payload)["identifiability_passed"])

    def test_unknown_window_does_not_enter_eligible_date_denominator(self):
        payload = fixture(); payload["common_primary_units"]["pivot"][0]["exact_window_supported"] = None
        result = D.assess(payload)
        self.assertIn("UNKNOWN_OR_UNSUPPORTED_PRIMARY_IDENTITY", result["reasons"])
        self.assertEqual(result["common_eligible_unit_counts"]["pivot"], 2)

    def test_unmeasured_essential_conditions_prevent_validated_selection(self):
        payload = fixture(); improve(payload); payload["essential_unmeasured_conditions"] = ["VIX", "CVD"]
        result = D.assess(payload)
        self.assertIn("ESSENTIAL_SOURCE_CONDITIONS_UNMEASURED", result["reasons"])
        self.assertIsNone(result["selected_configuration"])

    def test_coordinate_advantage_never_selects_a_configuration(self):
        payload = fixture(); improve(payload)
        for row in payload["configuration_results"].values():
            row["metric_basis"] = "coordinate_only"
            row["coordinate_MAE"] = 0
        result = D.assess(payload)
        self.assertIn("NONSTRICT_METRIC_BASIS", result["reasons"])
        self.assertFalse(result["coordinate_metrics_used_for_selection"])
        self.assertIsNone(result["selected_configuration"])

    def test_unestimable_strict_metric_is_inconclusive(self):
        payload = fixture(); improve(payload)
        payload["configuration_results"]["B0-D0"]["metrics"]["complete_bearish_ladder_agreement"] = {"status": "not_estimable", "numerator": None, "denominator": 0}
        self.assertIn("STRICT_METRICS_NOT_ESTIMABLE", D.assess(payload)["reasons"])

    def test_tied_vectors_do_not_force_a_winner(self):
        result = D.assess(fixture())
        self.assertTrue(result["identifiability_passed"])
        self.assertEqual(result["reasons"], ["NO_STRICT_DOMINATING_ALTERNATIVE"])
        self.assertIsNone(result["selected_configuration"])

    def test_improvement_with_a_worse_other_metric_is_not_dominance(self):
        payload = fixture(); improve(payload)
        payload["configuration_results"]["B1-D1"]["metrics"]["bearish_extras_per_branch"]["numerator"] += 1
        self.assertIsNone(D.assess(payload)["selected_configuration"])

    def test_more_abstention_in_any_common_role_blocks_replacement(self):
        payload = fixture(); improve(payload)
        payload["configuration_results"]["B1-D1"]["abstentions"]["bullish"] = 2
        self.assertIsNone(D.assess(payload)["selected_configuration"])

    def test_less_abstention_alone_is_not_a_strict_core_metric_improvement(self):
        payload = fixture()
        payload["configuration_results"]["B1-D1"]["abstentions"] = {r: 0 for r in D.ROLES}
        self.assertIsNone(D.assess(payload)["selected_configuration"])

    def test_lower_extra_count_can_be_the_strict_improvement(self):
        payload = fixture(); improve(payload, metric="bullish_extras_per_branch")
        self.assertEqual(D.assess(payload)["selected_configuration"], "B1-D1")

    def test_multiple_dominators_are_not_ranked_by_geometry_or_magnitude(self):
        payload = fixture(); improve(payload, "B1-D1"); improve(payload, "B0-D1")
        payload["configuration_results"]["B1-D1"]["metrics"]["pivot_identity_role_price_agreement"]["numerator"] = 3
        result = D.assess(payload)
        self.assertEqual(set(result["dominating_alternatives"]), {"B0-D1", "B1-D1"})
        self.assertEqual(result["reasons"], ["MULTIPLE_DOMINATING_ALTERNATIVES"])
        self.assertIsNone(result["selected_configuration"])

    def test_metric_denominator_cannot_drop_first_pass_misses(self):
        payload = fixture(); improve(payload)
        payload["configuration_results"]["B1-D1"]["metrics"]["end_to_end_eligible_source_recall"]["denominator"] = 8
        with self.assertRaisesRegex(ValueError, "denominator"):
            D.assess(payload)

    def test_different_comparable_units_cannot_be_hidden_by_equal_counts(self):
        payload = fixture()
        payload["configuration_results"]["B1-D1"]["common_primary_unit_ids"]["pivot"][0] = "different-unit"
        with self.assertRaisesRegex(ValueError, "common unit IDs"):
            D.assess(payload)

    def test_two_raw_triggers_cannot_double_one_functional_divider(self):
        payload = fixture(); row = payload["common_primary_units"]["pivot"][0]
        row["eligible_source_occurrence_count"] = 2
        row["eligible_source_occurrence_ids"].append("second-raw-trigger")
        with self.assertRaisesRegex(ValueError, "functional divider counts once"):
            D.assess(payload)

    def test_one_occurrence_cannot_be_counted_in_two_compound_role_units(self):
        payload = fixture()
        payload["common_primary_units"]["bullish"][0]["eligible_source_occurrence_ids"] = payload["common_primary_units"]["pivot"][0]["eligible_source_occurrence_ids"]
        with self.assertRaisesRegex(ValueError, "unique eligible source occurrence IDs"):
            D.assess(payload)

    def test_unknown_configuration_or_protected_date_is_rejected(self):
        payload = fixture(); payload["configurations"][0] = "new-date-specific-rule"
        with self.assertRaises(ValueError): D.assess(payload)
        payload = fixture(); payload["scheduled_dates"][0] = "2026-10-21"
        with self.assertRaises(ValueError): D.assess(payload)

    def test_invalid_count_or_nonfinite_metric_is_rejected(self):
        for value in (True, float("nan"), -1):
            payload = fixture()
            payload["configuration_results"]["B1-D1"]["metrics"]["pivot_identity_role_price_agreement"]["numerator"] = value
            with self.assertRaises(ValueError): D.assess(payload)

    def test_count_ratios_do_not_use_float_rounding_or_mutate_inputs(self):
        payload = fixture(); improve(payload)
        payload["unused_coordinate_diagnostic"] = {"B0-D0": -1000000}
        before = deepcopy(payload); first = D.assess(payload); second = D.assess(payload)
        self.assertEqual(first, second)
        self.assertEqual(payload, before)
        self.assertEqual(first["selected_configuration"], "B1-D1")


if __name__ == "__main__":
    unittest.main()
