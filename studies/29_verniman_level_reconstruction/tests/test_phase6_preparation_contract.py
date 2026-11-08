"""Cross-file preparation contracts; never read markets or source answers."""
import json
from pathlib import Path
import unittest

PHASE = Path(__file__).resolve().parents[1] / "phase6"


def load(relative):
    return json.loads((PHASE / relative).read_text())


class PreparationContractTests(unittest.TestCase):
    def test_copyable_capture_request_has_real_cli_schema_and_required_fields(self):
        row = load("templates/capture-request.json")
        self.assertEqual(row["schema"], "abacus.study29.phase6.capture-request/v1")
        self.assertTrue({"session_date", "operator_id", "capture_mode", "input_manifest",
                         "source_access_log", "native_evidence", "observed_terminal_bar"} <= row.keys())
        self.assertTrue(row["template_only"])

    def test_pending_ledger_exactly_preserves_the_adopted_calendar(self):
        calendar, ledger = load("calendar.json"), load("scheduled-session-ledger.json")
        self.assertEqual([r["session_date"] for r in ledger["sessions"]], calendar["scheduled_dates"])
        self.assertEqual(len(ledger["sessions"]), 20)
        self.assertTrue(all(r["status"] == "pending" and r["receipt"] is None and
                            r["finalized_at"] is None for r in ledger["sessions"]))

    def test_settings_keep_estimation_minima_separate_from_acceptance(self):
        settings = load("settings.json")
        self.assertEqual(settings["scheduled_dates"], load("calendar.json")["scheduled_dates"])
        self.assertIsNone(settings["validated_configuration"])
        self.assertIsNone(settings["acceptance_threshold"])
        self.assertFalse(settings["configuration_switch_permitted"])
        self.assertEqual(settings["minimum_usable_distinct_dates"],
                         {"pivot": 15, "bullish": 15, "bearish": 15, "common_full_map": 15})

    def test_source_templates_cannot_masquerade_as_observed_collection(self):
        access, sources = load("templates/access-log.json"), load("templates/source-role-ledger.json")
        self.assertFalse(access["complete_to_best_knowledge"])
        self.assertIsNone(access["closed_through"])
        self.assertEqual(access["actors"], [])
        self.assertEqual(access["events"], [])
        self.assertEqual(sources["occurrences"], [])
        self.assertTrue(all(r["source_review_status"] == "pending" for r in sources["session_records"]))

    def test_preparation_declaration_is_not_a_daily_input_or_prediction(self):
        inputs = load("input-manifest.json")
        self.assertEqual(inputs["schema"], "abacus.study29.phase6.preparation-inputs/v1")
        self.assertEqual(inputs["actual_prospective_input_files"], [])
        self.assertEqual(inputs["actual_prospective_predictions"], [])
        self.assertFalse(inputs["source_answers_opened_in_phase6a"])


if __name__ == "__main__":
    unittest.main()
