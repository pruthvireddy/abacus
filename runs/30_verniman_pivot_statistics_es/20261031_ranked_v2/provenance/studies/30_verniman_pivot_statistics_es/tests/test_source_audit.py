"""Synthetic source-accounting checks; no retained dated answers are loaded."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import random
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "source_audit.py"
SPEC = importlib.util.spec_from_file_location("study30_source_audit", MODULE_PATH)
source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source)


def outlook(identity="a", day="2020-01-02", contract="ESH20", **changes):
    return {"outlook_id": identity, "session_date": day, "contract": contract,
            "source_revision_id": f"revision-{identity}", "product": "ES",
            "extraction_status": "complete", "evidence_basis": "captured_source",
            "content_kind": "daily_outlook", "available_at": None,
            "timing_status": "historical_availability_unverified",
            "session_date_method": "body_month_day_with_qualified_context",
            "source_year_status": "source_contract_year_matches_session", **changes}


def trigger(identity="a", day="2020-01-02", side="bullish", low="10.00",
            high="10.00", contract="ESH20", **changes):
    return {"outlook_id": identity, "session_date": day, "contract": contract,
            "role": "trigger", "side": side, "price_low": low,
            "price_high": high, "trigger_interpretation": "conditional_threshold",
            **changes}


def pair(identity="a", day="2020-01-02", contract="ESH20"):
    return [trigger(identity, day, contract=contract),
            trigger(identity, day, side="bearish", contract=contract)]


def audit(**changes):
    params = {"outlooks": [outlook()], "levels": pair(), "issues": [],
              "coverage": [{"session_date": "2020-01-02", "status": "post_captured"}],
              "start_date": "2020-01-01", "end_date": "2020-01-03"}
    params.update(changes)
    return source.audit_sources(**params)


class TriggerShapeTests(unittest.TestCase):
    def test_decimal_equality_is_numeric(self):
        rows = [trigger(low=Decimal("10.000"), high="10"),
                trigger(side="bearish", low="1E1", high="10.0")]
        result = source.classify_trigger_shape(rows)
        self.assertEqual(result["source_shape"], "single_shared_trigger")
        self.assertNotIn("price_low", json.dumps(result))

    def test_shared_zone_and_separate_thresholds(self):
        rows = [trigger(low="9", high="10"), trigger(side="bearish", low="9", high="10")]
        self.assertEqual(source.classify_trigger_shape(rows)["source_shape"], "shared_zone")
        rows[1]["price_low"] = "8"
        self.assertEqual(source.classify_trigger_shape(rows)["source_shape"], "separate_thresholds")

    def test_targets_cannot_become_pivots(self):
        rows = [trigger(role="target"), trigger(side="bearish", role="target")]
        self.assertEqual(source.classify_trigger_shape(rows)["source_shape"], "no_trigger")
        self.assertEqual(source.classify_trigger_shape(rows + [trigger()])["source_shape"], "one_sided")

    def test_invalid_and_multiple_rows_are_not_silently_repaired(self):
        for invalid in [None, "", "NaN", "Infinity", "bad"]:
            with self.subTest(invalid=invalid):
                rows = [trigger(low=invalid), trigger(side="bearish")]
                self.assertEqual(source.classify_trigger_shape(rows)["source_shape"], "invalid_trigger_data")
        self.assertEqual(source.classify_trigger_shape(pair() + [trigger()])["source_shape"], "multiple_triggers_per_side")
        self.assertEqual(source.classify_trigger_shape([trigger(side="neutral")])["source_shape"], "unsupported_trigger_side")


class ContractTests(unittest.TestCase):
    def test_context_expands_literal_year_and_retains_original(self):
        actual = source.normalize_es_contract("ESH0", "2020-01-02")
        self.assertEqual(actual["normalized_contract"], "ESH2020")
        self.assertEqual(actual["source_contract"], "ESH0")
        self.assertEqual(source.normalize_es_contract("ESH21", "2020-12-15")["normalized_contract"], "ESH2021")
        self.assertEqual(source.normalize_es_contract("ESZ2020", date(2020, 10, 1))["normalized_contract"], "ESZ2020")

    def test_missing_and_ambiguous_context_do_not_infer_front_month(self):
        for code, day in [(None, "2020-01-02"), ("ES", "2020-01-02"),
                          ("MESZ20", "2020-01-02"), ("ESZ26", "2020-01-02"),
                          ("ESH20", None), ("ESH2010", "2020-01-02"),
                          ("ESH20", "2020-12-15")]:
            with self.subTest(code=code, day=day):
                self.assertIsNone(source.normalize_es_contract(code, day)["normalized_contract"])


class SourceAuditTests(unittest.TestCase):
    def test_accounts_dates_sources_and_null_availability(self):
        result = audit()
        row = result["outlook_audit"][0]
        self.assertEqual(row["source_only_disposition"], "candidate_pending_data")
        self.assertIsNone(row["available_at"])
        self.assertFalse(row["point_in_time_eligible"])
        self.assertEqual(row["candidate_id"], "a")
        self.assertEqual(row["normalized_contract"], "ESH2020")
        self.assertEqual(result["summary"]["calendar_dates_accounted"], 3)
        self.assertEqual(result["summary"]["canonical_level_rows_accounted"], 2)
        self.assertEqual(result["calendar_audit"][0]["source_only_disposition"], "missing_coverage_record")

    def test_duplicate_date_keeps_all_revisions_and_never_selects_latest(self):
        result = audit(outlooks=[outlook("a"), outlook("b", source_claimed_updated="2099-01-01")],
                       levels=pair("a") + pair("b"))
        self.assertEqual(len(result["outlook_audit"]), 2)
        for row in result["outlook_audit"]:
            self.assertEqual(row["canonical_outlooks_on_date"], 2)
            self.assertIn("multiple_canonical_outlooks_on_date", row["review_reasons"])
            self.assertEqual(row["source_only_disposition"], "review_required")
        self.assertEqual(result["summary"]["duplicate_dates_in_range"], 1)

    def test_semantics_and_date_qualifications_require_review(self):
        levels = pair()
        levels[0]["trigger_interpretation"] = ""
        issues = [{"outlook_id": "a", "session_date": "2020-01-02",
                   "code": "source_weekday_differs", "severity": "warning"}]
        row = audit(levels=levels, issues=issues)["outlook_audit"][0]
        self.assertIn("pivot_semantics_unreviewed", row["review_reasons"])
        self.assertIn("source_issue:source_weekday_differs", row["review_reasons"])
        self.assertEqual(row["source_date_assignment_review_status"], "review_required")
        self.assertEqual(row["source_date_assignment_issue_codes"], ["source_weekday_differs"])

    def test_nonnull_timestamp_alone_does_not_establish_availability(self):
        row = audit(outlooks=[outlook(available_at="2020-01-02T14:25:00Z")])["outlook_audit"][0]
        self.assertFalse(row["null_available_at"])
        self.assertFalse(row["point_in_time_eligible"])
        self.assertEqual(row["availability_assessment"], "timestamp_present_not_independently_verified")

    def test_outside_and_undated_rows_are_accounted(self):
        rows = [outlook("old", "2019-12-31"), outlook("none", None), outlook()]
        result = audit(outlooks=rows, levels=pair())
        self.assertEqual(result["summary"]["canonical_outlook_rows_input"], 3)
        dispositions = {x["outlook_id"]: x["source_only_disposition"] for x in result["outlook_audit"]}
        self.assertEqual(dispositions["old"], "outside_requested_range")
        self.assertEqual(dispositions["none"], "undated")

    def test_leap_day_calendar_inclusive(self):
        result = audit(start_date="2020-02-28", end_date="2020-03-01")
        self.assertEqual([x["session_date"] for x in result["calendar_audit"]],
                         ["2020-02-28", "2020-02-29", "2020-03-01"])

    def test_level_parent_inconsistency_flagged(self):
        levels = pair()
        levels[0]["session_date"] = "2020-01-03"
        levels[1]["contract"] = "ESM20"
        row = audit(levels=levels)["outlook_audit"][0]
        self.assertIn("level_date_differs_from_parent", row["review_reasons"])
        self.assertIn("level_contract_differs_from_parent", row["review_reasons"])

    def test_error_and_partial_plan_never_eligible(self):
        row = audit(outlooks=[outlook(extraction_status="partial")],
                    issues=[{"outlook_id": "a", "code": "other_error", "severity": "error"}])["outlook_audit"][0]
        self.assertIn("source_error_issue_present", row["review_reasons"])
        self.assertIn("source_extraction_not_complete", row["review_reasons"])

    def test_observations_remain_separate_with_every_anonymous_level(self):
        parent = {"observation_id": "note", "session_date": "2020-01-02",
                  "evidence_basis": "user_supplied_recollection", "available_at": None}
        child = {"observation_id": "note", "session_date": "2020-01-02",
                 "role": "trigger", "side": "neutral", "price_low": "10", "price_high": "10"}
        result = audit(observations=[parent], observation_levels=[child, child])
        self.assertEqual(len(result["outlook_audit"]), 1)
        self.assertEqual(len(result["observation_level_audit"]), 2)
        identities = {row["record_id"] for row in result["observation_level_audit"]}
        self.assertEqual(len(identities), 2)
        self.assertEqual(result["observation_audit"][0]["source_only_disposition"], "separate_observation_not_canonical_plan")
        self.assertNotIn("price_low", json.dumps(result))

    def test_deterministic_for_input_order_and_does_not_mutate(self):
        params = {"outlooks": [outlook("b", "2020-01-03"), outlook()],
                  "levels": pair() + pair("b", "2020-01-03"),
                  "issues": [{"outlook_id": "a", "code": "z"}, {"outlook_id": "a", "code": "a"}],
                  "coverage": [{"session_date": "2020-01-02"}, {"session_date": "2020-01-03"}]}
        original = deepcopy(params)
        expected = audit(**params)
        self.assertEqual(params, original)
        rng = random.Random(30)
        for values in params.values():
            rng.shuffle(values)
        self.assertEqual(audit(**params), expected)
        self.assertEqual(original["outlooks"][0]["outlook_id"], "b")
        self.assertNotIn("normalized_contract", original["outlooks"][0])

    def test_date_scoped_issue_without_outlook_id_is_not_lost(self):
        row = audit(issues=[{"session_date": "2020-01-02",
                             "code": "ledger_body_date_mismatch"}])["outlook_audit"][0]
        self.assertIn("source_issue:ledger_body_date_mismatch", row["review_reasons"])
        self.assertEqual(row["source_date_assignment_review_status"], "review_required")

    def test_structural_corruption_refused(self):
        for changes in [{"outlooks": [outlook(), outlook()]},
                        {"outlooks": [{"session_date": "2020-01-02"}]},
                        {"levels": [trigger("unknown")]},
                        {"coverage": [{"session_date": "2020-01-02"}] * 2},
                        {"observation_levels": [{"observation_id": "unknown"}]},
                        {"start_date": "2020-02-01", "end_date": "2020-01-01"},
                        {"outlooks": [outlook(day="2020-1-2")]}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                audit(**changes)


if __name__ == "__main__":
    unittest.main()
