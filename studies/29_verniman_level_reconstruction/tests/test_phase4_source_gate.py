"""Synthetic reveal-gate checks. No actual market inputs or source targets read."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "studies/29_verniman_level_reconstruction/phase4/select_sources.py"
SPEC = importlib.util.spec_from_file_location("study29_phase4_source_gate", SOURCE)
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)


class RevealGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="study29-source-gate-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.stage = self.root / G.STAGE
        self.stage.mkdir(parents=True)
        paths = (G.PHASE + "/protocol.md", G.PHASE + "/settings.json", G.CANDIDATE_SETTINGS,
                 G.AUTOPIVOT_PINE, G.AUTOPIVOT_MODEL, G.LOADER)
        for relative in paths:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            source = REPOSITORY / relative
            if relative in (G.AUTOPIVOT_PINE, G.AUTOPIVOT_MODEL):
                source = REPOSITORY / G.STAGE / "local-producer-revision-5-files" / relative
            shutil.copyfile(source, target)
        producer = self.stage / "producer.json"
        records = []
        for original in (G.AUTOPIVOT_PINE, G.AUTOPIVOT_MODEL):
            snapshot = self.stage / "retained-source" / original
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / original, snapshot)
            records.append({"path": original, "sha256": G.digest(snapshot),
                            "snapshot_path": str(snapshot.relative_to(self.stage))})
        self.write(producer, {"schema": "abacus.study29.phase4.local-producer/v1", "id": "synthetic-producer",
            "retained_before_market_execution_at": "2026-10-31T01:40:00+00:00",
            "current_autopivot_pine_sha256": G.AUTOPIVOT_PINE_SHA256,
            "current_autopivot_model_sha256": G.AUTOPIVOT_MODEL_SHA256, "files": records})
        freeze = {"frozen_files": [self.pin(p) for p in paths[:2]]}
        self.write(self.stage / "protocol-freeze.json", freeze)
        exposure = self.stage / "exposure.json"
        self.write(exposure, {"already_exposed_training_dates": list(G.DATES[:3])})
        reconciliation = self.stage / "comparator-reconciliation.json"
        self.write(reconciliation, {"schema": "abacus.study29.phase4.comparator-reconciliation/v1",
            "old_source_sha256": G.PRIOR_AUTOPIVOT_PINE_SHA256, "old_model_sha256": G.PRIOR_AUTOPIVOT_MODEL_SHA256,
            "current_source_sha256": G.AUTOPIVOT_PINE_SHA256, "current_model_sha256": G.AUTOPIVOT_MODEL_SHA256,
            "checks": {name: True for name in ("primary_selector_block_equal", "alternate_function_equal", "profile_and_N1_E1_code_equal", "model_existing_functions_byte_prefix_unchanged")}})
        self.gate = {"schema": "abacus.study29.phase4.reveal-gate/v1",
                     "recorded_at": "2026-10-31T02:00:00+00:00",
                     "protocol": self.pin(paths[0]), "settings": self.pin(paths[1]),
                     "candidate_settings": self.pin(G.CANDIDATE_SETTINGS),
                     "autopivot_pine": self.pin((self.stage / records[0]["snapshot_path"]).relative_to(self.root)),
                     "autopivot_model": self.pin((self.stage / records[1]["snapshot_path"]).relative_to(self.root)),
                     "comparator_freeze": {"source_basis": "immutable_at_capture", "producer_manifest": self.pin(producer.relative_to(self.root)),
                        "retained_before_market_execution_at": "2026-10-31T01:40:00+00:00"},
                     "comparator_reconciliation": self.pin(reconciliation.relative_to(self.root)),
                     "loader_code": self.pin(G.LOADER),
                     "exposure_audit": self.pin(exposure.relative_to(self.root)), "captures": []}
        for day in G.ADDITIONAL:
            capture = self.make_map(day)
            path = self.stage / (day + ".json")
            self.write(path, capture)
            browser = self.stage / (day + ".png")
            browser.write_bytes(b"synthetic browser-evidence fixture only")
            self.gate["captures"].append({"session_date": day,
                 "model_pre_reveal_captured_at": "2026-10-31T01:50:00+00:00",
                 "candidate_map": {**self.pin(path.relative_to(self.root)), "semantic_selector": "expanded_snapshot"},
                 "autopivot_prediction": {**self.pin(path.relative_to(self.root)), "semantic_selector": "autopivot_comparator.frozen"},
                 "browser_evidence": [self.pin(browser.relative_to(self.root))]})
        self.gate_path = self.stage / "gate.json"

    def write(self, path, value):
        path.write_text(json.dumps(value, indent=2) + "\n")

    def pin(self, relative):
        return {"path": str(relative), "sha256": G.digest(self.root / relative)}

    def make_map(self, day):
        cutoff = day + "T09:25:00-04:00"
        opening = day + "T09:20:00-04:00"
        distributions = []
        ledgers = []
        for window in sorted(G.WINDOWS):
            ready = window in ("completed_RTH", "overnight_prefix")
            profile = window + ":" + day
            distributions.append({"window": window, "profile_id": profile,
                "input_identity": "synthetic-input", "code_identity": "synthetic-producer",
                "settings_identity": G.CANDIDATE_SETTINGS_SHA256})
            recorded = {"metadata": {"profile_id": profile}, "readiness": "ready" if ready else "unavailable",
                        "reasons": [] if ready else ["incomplete_coverage"],
                        "rows": [{"raw_mass": 10}] if ready else [], "total_mass": 10 if ready else 0}
            ledgers.append({"status": "ready" if ready else "unavailable", "distribution": recorded,
                            "peaks": [], "regions": [], "lvn_ledger": [], "edge_ledger": [],
                            "presentation": {}, "counts": {"regions": 0, "edges": 0}})
        return {"session_date": day, "producer_revision": "synthetic-producer",
            "expanded_snapshot": {"baseline": {"trading_date": day, "cutoff": cutoff, "last_open": opening,
                "last_close": cutoff, "values": [100] * 19}, "distributions": distributions,
                "candidate_ledgers": ledgers, "composite_ledger": {"status": "unavailable"},
                "projection_ledgers": [{"status": "unavailable", "reason": "missing_anchors"}]},
            "autopivot_comparator": {"frozen": {"trading_date": day, "cutoff": cutoff,
                "last_included_open": opening, "last_included_close": cutoff,
                "selection": {"price": 100, "inputs": [104, 100, 96, 100, 101]}}}}

    def validate(self):
        self.write(self.gate_path, self.gate)
        return G.validate_gate(self.root, self.stage, self.gate_path,
                               now=datetime(2026, 10, 31, 3, tzinfo=timezone.utc))

    def update_capture(self, edit):
        capture = self.gate["captures"][0]
        path = self.root / capture["candidate_map"]["path"]
        document = json.loads(path.read_text())
        edit(document)
        self.write(path, document)
        capture["candidate_map"]["sha256"] = G.digest(path)
        capture["autopivot_prediction"]["sha256"] = G.digest(path)

    def test_actual_structured_captures_pass_even_with_explicit_missing_optional_profiles(self):
        result = self.validate()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(len(result["captures"]), 7)
        self.assertEqual(set(result["captures"][0]["ready_windows"]), {"completed_RTH", "overnight_prefix"})
        self.assertEqual(len(result["captures"][0]["unavailable_windows"]), 3)

    def test_one_missing_date_cannot_be_replaced_by_operator_flag(self):
        self.gate["captures"].pop()
        self.gate["operator_says_complete"] = True
        with self.assertRaisesRegex(ValueError, "all seven"):
            self.validate()

    def test_protected_date_cannot_replace_an_allowed_date(self):
        self.gate["captures"][0]["session_date"] = "2026-10-15"
        with self.assertRaisesRegex(ValueError, "all seven"):
            self.validate()

    def test_failure_placeholder_is_not_an_expanded_map(self):
        self.update_capture(lambda d: d.update(expanded_snapshot={"status": "unavailable"}))
        with self.assertRaises((ValueError, KeyError)):
            self.validate()

    def test_hash_change_is_rejected(self):
        self.gate["captures"][0]["candidate_map"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "mismatched"):
            self.validate()

    def test_later_bar_cannot_be_terminal(self):
        self.update_capture(lambda d: d["expanded_snapshot"]["baseline"].update(last_open=G.ADDITIONAL[0] + "T09:25:00-04:00"))
        with self.assertRaisesRegex(ValueError, "exact09:20"):
            self.validate()

    def test_required_input_failure_rejected(self):
        def edit(document):
            for ledger, d in zip(document["expanded_snapshot"]["candidate_ledgers"], document["expanded_snapshot"]["distributions"]):
                if d["window"] == "overnight_prefix":
                    ledger["status"] = "unavailable"
                    ledger["distribution"].update(readiness="unavailable", reasons=["missing_terminal"])
        self.update_capture(edit)
        with self.assertRaisesRegex(ValueError, "RTH/ON"):
            self.validate()

    def test_changed_control_settings_rejected(self):
        self.update_capture(lambda d: d["expanded_snapshot"]["distributions"][0].update(settings_identity="different"))
        with self.assertRaisesRegex(ValueError, "candidate settings"):
            self.validate()

    def test_missing_comparator_prediction_rejected(self):
        self.update_capture(lambda d: d["autopivot_comparator"]["frozen"]["selection"].update(price=None))
        with self.assertRaisesRegex(ValueError, "actual current-comparator"):
            self.validate()

    def test_browser_hash_evidence_is_required(self):
        self.gate["captures"][0]["browser_evidence"] = []
        with self.assertRaisesRegex(ValueError, "browser capture"):
            self.validate()

    def test_capture_after_gate_rejected(self):
        self.gate["captures"][0]["model_pre_reveal_captured_at"] = "2026-10-31T02:01:00Z"
        with self.assertRaisesRegex(ValueError, "chronology"):
            self.validate()

    def test_explicit_semantic_selector_is_required(self):
        self.gate["captures"][0]["candidate_map"].pop("semantic_selector")
        with self.assertRaisesRegex(ValueError, "semantic selector"):
            self.validate()

    def test_invalid_gate_precedes_loader_import_or_answer_read(self):
        self.gate["recorded_at"] = datetime.now(timezone.utc).isoformat()
        self.gate["captures"] = []
        self.write(self.gate_path, self.gate)
        real_import = __import__
        def fail_on_loader(name, *args, **kwargs):
            if name.startswith("abacus_bhishma"):
                raise AssertionError("loader must never be imported before gate passes")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=fail_on_loader), self.assertRaisesRegex(ValueError, "all seven"):
            G.select(self.root, self.stage, self.gate_path)

    def test_narrow_source_postcondition_rejects_other_date(self):
        with self.assertRaisesRegex(ValueError, "exact authorized"):
            G.bounded_rows([{"session_date": "2026-10-15", "value": "synthetic"}], "2026-10-14")
        with self.assertRaises(ValueError):
            G.bounded_rows([], "2026-10-21")

    def test_other_chart_date_nested_source_is_metadata_only_projection(self):
        original = {"session_date": "2026-10-14", "sources": [
            {"source_id": "allowed", "chart_session_date": "2026-10-14", "source_text": "synthetic allowed"},
            {"source_id": "other", "chart_session_date": "2026-10-15", "source_text": "synthetic excluded answer", "post_id": "123"}],
            "markers": [{"source_id": "allowed", "annotation_raw": "synthetic"}, {"source_id": "other", "annotation_raw": "synthetic excluded"}],
            "closing_notes": [{"source_id": "other", "label_raw": "synthetic excluded"}],
            "issues": [{"source_id": None, "detail": "unscoped synthetic"}], "session_notes": "unscoped synthetic"}
        before = deepcopy(original)
        projected, excluded = G.bounded_observation(original, "2026-10-14")
        self.assertEqual(original, before)
        self.assertEqual([r["source_id"] for r in projected["sources"]], ["allowed"])
        self.assertEqual([r["source_id"] for r in projected["markers"]], ["allowed"])
        self.assertEqual(projected["closing_notes"], [])
        self.assertIsNone(projected["session_notes"])
        self.assertNotIn("source_text", excluded[0])
        self.assertEqual(excluded[0]["chart_session_date"], "2026-10-15")

    def test_unknown_nested_chart_date_retains_original_qualification(self):
        original = {"session_date": "2026-10-14", "sources": [{"source_id": "unknown", "chart_session_date": None, "notes": "unresolved"}]}
        projected, excluded = G.bounded_observation(original, "2026-10-14")
        self.assertEqual(projected, original)
        self.assertEqual(excluded, [])

    def test_current_comparator_requires_preserved_primary_policy_reconciliation(self):
        pin = self.gate["comparator_reconciliation"]
        path = self.root / pin["path"]
        record = json.loads(path.read_text())
        record["checks"]["primary_selector_block_equal"] = False
        self.write(path, record)
        pin["sha256"] = G.digest(path)
        with self.assertRaisesRegex(ValueError, "prior-policy reconciliation"):
            self.validate()

    def test_mutable_workspace_display_change_does_not_replace_captured_source(self):
        (self.root / G.AUTOPIVOT_PINE).write_text("later synthetic display revision")
        self.assertEqual(self.validate()["status"], "passed")

    def test_workspace_source_cannot_be_misattributed_to_retained_producer(self):
        self.gate["autopivot_pine"] = self.pin(G.AUTOPIVOT_PINE)
        with self.assertRaisesRegex(ValueError, "identity path"):
            self.validate()

    def test_different_map_producer_rejected(self):
        self.update_capture(lambda d: d.update(producer_revision="different"))
        with self.assertRaisesRegex(ValueError, "map producer"):
            self.validate()
