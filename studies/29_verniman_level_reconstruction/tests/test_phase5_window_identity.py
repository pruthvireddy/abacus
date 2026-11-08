"""Synthetic metadata-only identity support; never reads answer prices."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("study29_phase5_window_tests", STUDY / "phase5/window_identity.py")
W = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(W)


class WindowIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="study29-window-metadata-")
        self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        self.evidence = self.root / "identity-evidence"; self.evidence.mkdir()
        start, end, cutoff = "2026-10-14T09:30:00-04:00", "2026-10-14T16:00:00-04:00", "2026-10-15T09:25:00-04:00"
        self.claim = {"schema": W.SCHEMA, "basis": "explicit_independent_source_metadata", "independent_of_candidate_prices": True,
                      "supported_window_id": "completed_RTH:" + start + ":" + end, "period_identity": "completed_RTH", "source_contract": "ESZ26",
                      "reference_start": start, "reference_end": end, "information_cutoff": cutoff, "measurement": W.PROFILE_MEASUREMENT, "adjustment": "individual_contract_unadjusted"}
        self.row = {"level_id": "synthetic-source-occurrence", "session_date": "2026-10-15", "source_class": "named_daily_plan", "actual_contract": "ESZ26", "families": ["YVAL"], "provenance": {"source_revision_id": "synthetic-revision"}, "source_window_identity_supplied": self.claim}
        self.write_evidence()

    def write_evidence(self):
        path = self.evidence / "explicit-window.json"
        identity = {key: self.claim[key] for key in W.FIELDS if key in self.claim}
        if "members" in self.claim:
            identity["members"] = self.claim["members"]
        record = {"schema": "abacus.study29.source-window-evidence/v1", "session_date": self.row["session_date"], "source_class": self.row["source_class"], "source_revision_id": self.row["provenance"]["source_revision_id"], "basis": "explicit_independent_source_metadata", "independent_of_candidate_prices": True, "identity": identity}
        path.write_text(json.dumps(record, indent=2))
        self.claim["identity_evidence"] = [{"path": str(path.relative_to(self.root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]

    def assess(self):
        return W.assess(self.row, self.root, allowed_evidence_roots=[self.evidence])

    def test_complete_explicit_same_revision_metadata_is_supported(self):
        result = self.assess()
        self.assertEqual(result["status"], "supported_explicit_metadata")
        self.assertEqual(result["supported_window_id"], self.claim["supported_window_id"])
        self.assertFalse(result["candidate_or_source_price_inspected"])

    def test_missing_metadata_defaults_none_without_evidence_reads(self):
        self.row["source_window_identity_supplied"] = None
        with patch.object(Path, "read_text", side_effect=AssertionError("no evidence read needed")):
            self.assertIsNone(self.assess()["supported_window_id"])

    def test_partial_metadata_is_retained_unassessed(self):
        self.claim.pop("information_cutoff")
        result = self.assess()
        self.assertEqual(result["status"], "provided_metadata_unassessed")
        self.assertIsNone(result["supported_window_id"])
        self.assertIsNotNone(result["supplied_metadata"])

    def test_unpinned_or_mismatched_identity_evidence_rejected(self):
        self.claim["identity_evidence"][0]["sha256"] = "0" * 64
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_no_evidence_boolean_alone_cannot_establish_window(self):
        self.claim["identity_evidence"] = []
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_price_or_label_inference_basis_rejected(self):
        self.claim["basis"] = "nearest_candidate_or_yesterday_label"
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_wrong_explicit_period_not_repaired_from_window_name(self):
        self.claim["reference_start"] = "2026-10-14T09:00:00-04:00"; self.write_evidence()
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_other_date_evidence_and_protected_row_rejected(self):
        self.row["session_date"] = "2026-10-21"
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_mismatched_source_revision_not_selected_by_proximity(self):
        self.row["provenance"]["source_revision_id"] = "another-revision"
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_unknown_measurement_remains_provided_but_unassessed(self):
        self.claim["measurement"] = "undisclosed_proprietary_profile"; self.write_evidence()
        self.assertIsNone(self.assess()["supported_window_id"])

    def test_target_price_changes_cannot_change_identity_assessment(self):
        first = self.assess()
        self.row.update(price_low="999", price_high="999", competing_nearest_candidate="different-price")
        self.assertEqual(self.assess(), first)

    def test_price_extreme_measurement_cannot_support_hve(self):
        self.claim["measurement"] = W.EXTREME_MEASUREMENT; self.row["families"] = ["HVE"]; self.write_evidence()
        self.assertIsNone(self.assess()["supported_window_id"])


if __name__ == "__main__":
    unittest.main()
