"""Synthetic manual-ledger serialization checks; no real anchors or browser calls."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "phase3" / "anchor_inputs.py"
SPEC = importlib.util.spec_from_file_location("study29_anchor_inputs", SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class AnchorInputTests(unittest.TestCase):
    def record(self):
        return dict(role="C", anchor_id="synthetic-center", lower="10.125", upper="10.25",
                    contract="CME_MINI:ESZ2026", reference_period="synthetic-prior-window",
                    measurement="synthetic-declared-center", observed_at="2026-10-01T09:00:00-04:00",
                    confirmed_at="2026-10-01T09:05:00-04:00", evidence="synthetic-fixture-only",
                    reason="hand-worked encoder check", selection_status="analyst_proposed",
                    independently_supported=True, reading_precision="0.125",
                    source_historical_available_at=None)

    def test_empty_ledger_has_no_default_price_or_string(self):
        result = M.encode_ledger({"schema": "abacus.study29.phase3.anchors/v1", "anchors": []},
                                 contract="CME_MINI:ESZ2026", cutoff=M.timestamp("2026-10-01T09:25:00-04:00"))
        self.assertEqual(result["anchors"], {})
        self.assertEqual(result["missing_roles"], ["C", "E", "H", "L"])

    def test_exact_string_and_millisecond_times(self):
        encoded, reasons = M.encode_record(self.record(), contract="CME_MINI:ESZ2026",
                                           cutoff=M.timestamp("2026-10-01T09:25:00-04:00"))
        self.assertEqual(encoded, "synthetic-center|10.125|10.25|CME_MINI:ESZ2026|synthetic-prior-window|synthetic-declared-center|1790859600000|1790859900000|synthetic-fixture-only|hand-worked encoder check|analyst-proposed|true|0.125")
        self.assertEqual(reasons, [])

    def test_late_and_unsupported_record_remains_auditable_and_ineligible(self):
        record = self.record()
        record.update(confirmed_at="2026-10-01T10:00:00-04:00", independently_supported=False)
        _, reasons = M.encode_record(record, contract="CME_MINI:ESZ2026",
                                     cutoff=M.timestamp("2026-10-01T09:25:00-04:00"))
        self.assertEqual(reasons, ["later_confirmed_anchor", "independent_causal_evidence_unsupported"])

    def test_delimiter_and_nonfinite_price_rejected(self):
        for update in ({"evidence": "misleading|extra-field"}, {"lower": "NaN"},
                       {"observed_at": "2026-10-01T09:00:00"}, {"reading_precision": ""},
                       {"independently_supported": "true"}):
            record = self.record()
            record.update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                M.encode_record(record, contract="CME_MINI:ESZ2026",
                                cutoff=M.timestamp("2026-10-01T09:25:00-04:00"))

    def test_duplicate_roles_rejected(self):
        with self.assertRaises(ValueError):
            M.encode_ledger({"schema": "abacus.study29.phase3.anchors/v1", "anchors": [self.record(), self.record()]},
                            contract="CME_MINI:ESZ2026", cutoff=M.timestamp("2026-10-01T09:25:00-04:00"))
