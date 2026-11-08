"""Synthetic strict-score distillation; no real plans, market data or files."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / "phase5"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


D = load("study29_phase5_distillation_decision", BASE / "assess_decision.py")
X = load("study29_phase5_pure_distillation", BASE / "distill_decision.py")


def occurrence(name, family="YVAL", matched=True):
    return {"source_id": name, "families": [family], "eligible_roles": [family],
            "matched_roles": [family] if matched else [], "coverage": "full_roles" if matched else "unmatched"}


def fixture():
    summary = {"schema": "abacus.study29.phase5.saved-comparisons/v1", "configurations": list(D.CONFIGURATIONS),
               "reveal_gate": {"status": "passed", "gate": {"path": "synthetic/gate.json", "sha256": "a" * 64}},
               "source_ledger": {"path": "synthetic/ledger.json", "sha256": "b" * 64},
               "selection_recomputed": False, "candidate_inputs_modified": False,
               "records": [{"session_date": day, "path": "synthetic/" + day + ".json", "sha256": "c" * 64} for day in D.DATES]}
    ledger = {"schema": "abacus.study29.phase5.source-role-ledger/v1", "occurrences": []}
    records = []
    for day in D.DATES:
        revision = "synthetic-revision:" + day
        rows = []
        for side in ("bullish", "bearish"):
            rows.append({"level_id": day + ":trigger:" + side, "session_date": day, "source_class": "named_daily_plan",
                         "provenance": {"source_revision_id": revision}, "families": ["YVAL"],
                         "phase4_role": "conditional_scenario_divider", "scenario_side": side,
                         "directional_conditions": "", "source_target_order": None})
            for rank in (1, 2):
                rows.append({"level_id": day + ":" + side + ":" + str(rank), "session_date": day,
                             "source_class": "named_daily_plan", "provenance": {"source_revision_id": revision},
                             "families": ["YVAH"], "phase4_role": "ordered_" + side + "_destination",
                             "directional_conditions": "", "source_target_order": rank})
        ledger["occurrences"].extend(rows)
        pivot_id = "interpreted-functional-divider:" + day
        unit = {"unit_id": pivot_id, "source_stratum": {"session_date": day, "source_class": "named_daily_plan", "source_revision_id": revision},
                "status": "unique_common_functional_divider", "primary_family_identity_consistent": True,
                "primary_price_interval": ["100", "100"]}
        analysis = {}
        for config in D.CONFIGURATIONS:
            role_results = {}
            for role in D.ROLES:
                ids = [pivot_id] if role == "pivot" else [r["level_id"] for r in rows if r["phase4_role"] == "ordered_" + role + "_destination"]
                occs = [occurrence(name, "YVAL" if role == "pivot" else "YVAH") for name in ids]
                assignments = [{"source_id": name, "candidate_id": "candidate:" + name, "boundary": None,
                                "candidate_interval_width": "0", "interval_gap_points": "0"} for name in ids]
                strict = {"status": "compared", "generation": {"occurrences": deepcopy(occs)},
                          "selection": {"occurrences": deepcopy(occs), "strata": [{"assignments": assignments}]},
                          "physical_selected_count": len(ids), "selector_abstained": False, "ordering": []}
                if role != "pivot":
                    strict["ordering"] = [{"session_date": day, "source_class": "named_daily_plan", "revision_id": revision,
                        "observed_target_count": 2, "complete_ladder_agreement": True, "source_order_ambiguous": False,
                        "source_targets_not_truncated": True, "matched_order_pairs": [[1, 1], [2, 2]]}]
                role_results[role] = {"strict_decomposition": strict,
                    "primary_pivot_interpretation": {"status": "unique_common_functional_divider", "source_strata": [deepcopy(unit)]} if role == "pivot" else None,
                    "coordinate_only_diagnostic": {"must_not_be_read": True}}
            analysis[config] = role_results
        records.append({"schema": "abacus.study29.phase5.saved-comparison/v1", "session_date": day,
                        "source_ledger": deepcopy(summary["source_ledger"]), "selection_recomputed": False,
                        "candidate_inputs_modified": False, "analysis": analysis,
                        "source_window_identity_assessments": [{"source_occurrence_id": r["level_id"],
                            "status": "supported_explicit_metadata", "supported_window_id": "synthetic-window:" + day,
                            "normalized_contract": "ESZ2026", "adjustment": "individual_contract_unadjusted"} for r in rows]})
    return summary, records, ledger


def distill(values):
    return X.distill(*values, decision_spec=D)


class DistillationTests(unittest.TestCase):
    def test_full_supported_units_are_common_and_trigger_occurrences_count_once(self):
        result = distill(fixture())
        self.assertEqual({r: len(result["common_primary_units"][r]) for r in D.ROLES}, {r: 4 for r in D.ROLES})
        self.assertEqual(result["configuration_results"][D.PRIMARY]["metrics"]["end_to_end_eligible_source_recall"],
                         {"status": "estimable", "numerator": 20, "denominator": 20})
        self.assertTrue(D.assess(result)["identifiability_passed"])
        self.assertIsNone(D.assess(result)["selected_configuration"])

    def test_unknown_metadata_gives_empty_units_and_not_estimable_vectors(self):
        values = fixture()
        for record in values[1]:
            for claim in record["source_window_identity_assessments"]:
                claim.update(status="unidentified_no_explicit_window_metadata", supported_window_id=None)
        result = distill(values)
        self.assertTrue(all(not result["common_primary_units"][r] for r in D.ROLES))
        self.assertTrue(all(m["status"] == "not_estimable" and m["numerator"] is None
                            for row in result["configuration_results"].values() for m in row["metrics"].values()))
        self.assertTrue(D.assess(result)["no_validated_configuration_selected"])

    def test_provided_but_unassessed_identity_is_not_supported(self):
        values = fixture()
        values[1][0]["source_window_identity_assessments"][0]["status"] = "provided_metadata_unassessed"
        result = distill(values)
        self.assertEqual(len(result["common_primary_units"]["pivot"]), 3)

    def test_common_unit_intersection_excludes_unit_ineligible_for_one_configuration(self):
        values = fixture()
        row = values[1][0]["analysis"]["B0-D0"]["bullish"]["strict_decomposition"]["generation"]["occurrences"][0]
        row["eligible_roles"] = []
        result = distill(values)
        self.assertEqual(len(result["common_primary_units"]["bullish"]), 3)
        ids = [v["common_primary_unit_ids"]["bullish"] for v in result["configuration_results"].values()]
        self.assertTrue(all(x == ids[0] for x in ids))

    def test_generation_failure_stays_in_end_to_end_denominator(self):
        values = fixture()
        for config in D.CONFIGURATIONS:
            strict = values[1][0]["analysis"][config]["bullish"]["strict_decomposition"]
            for section in ("generation", "selection"):
                strict[section]["occurrences"][1].update(matched_roles=[], coverage="unmatched")
            strict["ordering"][0].update(complete_ladder_agreement=False, matched_order_pairs=[[1, 1]])
        result = distill(values)["configuration_results"][D.PRIMARY]
        self.assertEqual(result["metrics"]["end_to_end_eligible_source_recall"], {"status": "estimable", "numerator": 19, "denominator": 20})
        self.assertEqual(result["metrics"]["bullish_extras_per_branch"]["numerator"], 1)

    def test_source_destinations_beyond_cap_are_not_truncated(self):
        summary, records, ledger = fixture(); day = D.DATES[0]
        template = next(r for r in ledger["occurrences"] if r["level_id"] == day + ":bullish:2")
        for rank in (3, 4, 5):
            row = {**template, "level_id": day + ":bullish:" + str(rank), "source_target_order": rank}
            ledger["occurrences"].append(row)
            records[0]["source_window_identity_assessments"].append({**records[0]["source_window_identity_assessments"][0], "source_occurrence_id": row["level_id"]})
        for config in D.CONFIGURATIONS:
            strict = records[0]["analysis"][config]["bullish"]["strict_decomposition"]
            ids = [day + ":bullish:" + str(rank) for rank in range(1, 6)]
            strict["generation"]["occurrences"] = [occurrence(name, "YVAH") for name in ids]
            strict["selection"]["occurrences"] = [occurrence(name, "YVAH", i < 3) for i, name in enumerate(ids)]
            strict["physical_selected_count"] = 3
            strict["ordering"][0].update(observed_target_count=5, complete_ladder_agreement=False,
                                           matched_order_pairs=[[1, 1], [2, 2], [3, 3]])
        result = distill((summary, records, ledger))
        self.assertEqual(result["common_primary_units"]["bullish"][0]["eligible_source_occurrence_count"], 5)
        self.assertEqual(result["configuration_results"][D.PRIMARY]["metrics"]["end_to_end_eligible_source_recall"],
                         {"status": "estimable", "numerator": 21, "denominator": 23})

    def test_e1_overlap_does_not_pass_actual_pivot_boundary_agreement(self):
        values = fixture()
        for record in values[1]:
            for config in D.CONFIGURATIONS:
                strict = record["analysis"][config]["pivot"]["strict_decomposition"]
                strict["selection"]["strata"][0]["assignments"][0].update(boundary="100" if config == "B1-D1" else "103",
                    candidate_interval_width="4", interval_gap_points="0" if config == "B1-D1" else "1")
        result = distill(values)
        self.assertEqual(result["configuration_results"][D.PRIMARY]["metrics"]["pivot_identity_role_price_agreement"]["numerator"], 0)
        self.assertEqual(result["configuration_results"][D.PRIMARY]["metrics"]["end_to_end_eligible_source_recall"]["numerator"], 20)
        self.assertEqual(D.assess(result)["selected_configuration"], "B1-D1")

    def test_vix_cvd_conditions_remain_essential_and_unmeasured(self):
        values = fixture()
        for row in values[2]["occurrences"]:
            row["directional_conditions"] = "bullish VIX/CVD"
        result = distill(values)
        self.assertEqual(result["essential_unmeasured_conditions"], ["CVD", "VIX"])
        self.assertFalse(D.assess(result)["identifiability_passed"])

    def test_missing_condition_reading_is_not_silently_measured(self):
        values = fixture(); values[2]["occurrences"][0]["directional_conditions"] = None
        self.assertIn("UNRESOLVED_DIRECTIONAL_CONDITION_STATUS", distill(values)["essential_unmeasured_conditions"])

    def test_conflicting_pivot_or_missing_order_does_not_pick_a_nearer_answer(self):
        values = fixture()
        for config in D.CONFIGURATIONS:
            values[1][0]["analysis"][config]["pivot"]["primary_pivot_interpretation"]["status"] = "unresolved_single_pivot_ground_truth"
            values[1][0]["analysis"][config]["bearish"]["strict_decomposition"]["ordering"][0]["complete_ladder_agreement"] = None
        result = distill(values)
        self.assertEqual(len(result["common_primary_units"]["pivot"]), 3)
        self.assertEqual(len(result["common_primary_units"]["bearish"]), 3)

    def test_duplicate_compound_role_assignments_do_not_double_matched_physical_targets(self):
        values = fixture()
        for config in D.CONFIGURATIONS:
            values[1][0]["analysis"][config]["bullish"]["strict_decomposition"]["ordering"][0]["matched_order_pairs"].append([1, 1])
        result = distill(values)["configuration_results"][D.PRIMARY]
        self.assertEqual(result["metrics"]["bullish_extras_per_branch"]["numerator"], 0)
        self.assertEqual(result["metrics"]["end_to_end_eligible_source_recall"]["numerator"], 20)

    def test_abstention_is_not_a_missing_source_or_a_negative_extra_count(self):
        values = fixture()
        for config in D.CONFIGURATIONS:
            strict = values[1][0]["analysis"][config]["bearish"]["strict_decomposition"]
            strict.update(selector_abstained=True, physical_selected_count=0)
            for row in strict["selection"]["occurrences"]: row.update(matched_roles=[], coverage="unmatched")
            strict["ordering"][0].update(complete_ladder_agreement=False, matched_order_pairs=[])
        result = distill(values)["configuration_results"][D.PRIMARY]
        self.assertEqual(result["abstentions"]["bearish"], 1)
        self.assertEqual(result["metrics"]["bearish_extras_per_branch"]["numerator"], 0)
        self.assertEqual(result["metrics"]["end_to_end_eligible_source_recall"]["denominator"], 20)

    def test_all_scheduled_dates_and_unchanged_saved_predictions_are_required(self):
        values = fixture(); values[1].pop()
        with self.assertRaisesRegex(ValueError, "four unique"): distill(values)
        values = fixture(); values[1][0]["selection_recomputed"] = True
        with self.assertRaises(ValueError): distill(values)

    def test_changed_target_denominator_or_impossible_rank_is_rejected(self):
        values = fixture(); values[1][0]["analysis"][D.PRIMARY]["bullish"]["strict_decomposition"]["ordering"][0]["observed_target_count"] = 1
        with self.assertRaisesRegex(ValueError, "denominator"): distill(values)
        values = fixture(); values[1][0]["analysis"][D.PRIMARY]["bullish"]["strict_decomposition"]["ordering"][0]["matched_order_pairs"] = [[1, 3]]
        with self.assertRaisesRegex(ValueError, "rank"): distill(values)

    def test_coordinates_and_failed_gate_source_payload_are_never_read(self):
        class Poison(dict):
            def get(self, *args, **kwargs): raise AssertionError("unpermitted source/coordinate read")
        values = fixture()
        for record in values[1]:
            for row in record["analysis"].values():
                for role in D.ROLES: row[role]["coordinate_only_diagnostic"] = Poison()
        self.assertFalse(distill(values)["coordinate_diagnostics_read"])
        summary = fixture()[0]; summary["reveal_gate"] = {"status": "failed"}
        result = X.distill(summary, Poison(), Poison(), decision_spec=D)
        self.assertFalse(result["source_data_examined_by_distiller"])
        self.assertEqual(D.assess(result)["status"], "engineering_incomplete")

    def test_inputs_are_not_mutated(self):
        values = fixture(); before = deepcopy(values)
        self.assertEqual(distill(values), distill(values))
        self.assertEqual(values, before)


if __name__ == "__main__":
    unittest.main()
