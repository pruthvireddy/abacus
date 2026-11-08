"""Synthetic four-session reveal controls; no actual market/answer inputs read."""
from copy import deepcopy
from datetime import datetime, date, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


G = module("study29_phase5_gate_tests", STUDY / "phase5/select_sources.py")
M = module("study29_phase5_gate_synthetic_model", STUDY / "src/phase4_model.py")


class DevelopmentGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="study29-phase5-gate-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stage = self.root / G.STAGE_PARENT / "phase5_20261031T030000Z"
        self.stage.mkdir(parents=True)
        self.created = "2026-10-31T04:00:00+00:00"
        self.producer = {"schema": "abacus.study29.phase5.producer/v1", "id": "synthetic-producer",
                         "retained_at": "2026-10-31T03:10:00+00:00", "stage": str(self.stage.relative_to(self.root)), "files": []}
        expected = {}
        for role in list(G.EXPECTED) + ["phase5_protocol", "phase5_settings", "phase5_inputs", "phase5_decision_rule", "runner", "environment_lock"]:
            original = self.root / "synthetic-originals" / role
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_text("synthetic producer bytes: " + role)
            dependency = {"phase4_model": "retained-study/src/phase4_model.py", "phase3_model": "retained-study/src/phase3_model.py", "reference_model": "retained-study/src/reference_model.py", "matcher": "retained-study/phase3/matching.py"}
            snapshot = self.stage / "producer-files" / dependency.get(role, role)
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, snapshot)
            self.producer["files"].append({"role": role, "path": str(original.relative_to(self.root)), "sha256": G.digest(snapshot), "snapshot_path": str(snapshot.relative_to(self.stage))})
            if role in G.EXPECTED:
                expected[role] = G.digest(snapshot)
        self.expected_patch = patch.object(G, "EXPECTED", expected)
        self.expected_patch.start(); self.addCleanup(self.expected_patch.stop)
        self.gate = {"schema": "abacus.study29.phase5.reveal-gate/v1", "recorded_at": self.created, "captures": []}
        frozen_files = []
        for key, filename in G.FROZEN_DOCUMENTS.items():
            target = self.root / G.PHASE / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if key == "settings":
                self.write(target, {"development_dates": list(G.DATES), "configurations": sorted(G.POLICIES)})
            else:
                target.write_text("synthetic frozen " + key)
            self.gate[key] = self.pin(target)
            frozen_files.append(self.pin(target))
            role = {"protocol": "phase5_protocol", "settings": "phase5_settings", "input_declaration": "phase5_inputs", "decision_rule": "phase5_decision_rule"}[key]
            item = next(r for r in self.producer["files"] if r["role"] == role)
            item.update(path=str(target.relative_to(self.root)), sha256=G.digest(target))
            shutil.copyfile(target, self.stage / item["snapshot_path"])
        freeze = self.stage / "protocol-freeze.json"
        self.write(freeze, {"frozen_at": "2026-10-31T03:00:00+00:00", "frozen_files": frozen_files})
        self.gate["protocol_freeze"] = self.pin(freeze)
        self.producer["protocol_freeze"] = self.pin(freeze)
        inputs = []
        for day in G.DATES:
            path = self.stage / (day + ".csv")
            path.write_text("synthetic chart CSV only\n")
            inputs.append({**self.pin(path), "session_date": day})
        input_manifest = self.stage / "input-manifest.json"
        self.write(input_manifest, {"schema": "abacus.study29.phase5.market-inputs/v1", "stage": str(self.stage.relative_to(self.root)), "market_configuration": G.MARKET, "recorded_at": "2026-10-31T03:05:00+00:00", "files": inputs})
        self.producer["input_manifest"] = self.pin(input_manifest)
        producer_path = self.stage / "producer.json"
        self.write(producer_path, self.producer)
        self.gate["producer_manifest"] = self.pin(producer_path)
        loader = self.root / G.LOADER
        loader.parent.mkdir(parents=True, exist_ok=True); loader.write_text("synthetic loader not imported")
        self.gate["loader_code"] = self.pin(loader)
        selector = self.root / G.PHASE / "select_sources.py"
        selector.write_text("synthetic selector identity")
        self.gate["source_selector"] = self.pin(selector)
        for key, filename in (("source_role_builder", "build_source_role_ledger.py"), ("scoring_orchestrator", "analyze_saved_development.py")):
            path = self.root / G.PHASE / filename; path.write_text("synthetic pre-answer orchestration")
            self.gate[key] = self.pin(path)
        adapter = self.root / G.PHASE / "window_identity.py"; adapter.write_text("synthetic metadata-only adapter")
        self.gate["window_adapter"] = self.pin(adapter)
        self.gate["window_adapter_policy"] = "phase5-explicit-window-metadata-v1"
        contracts = {}
        self.gate["comparison_files"] = []
        for path in G.COMPARISON_FILES:
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text("synthetic comparison: " + path)
            contracts[path] = G.digest(target); self.gate["comparison_files"].append(self.pin(target))
        comparison_patch = patch.object(G, "COMPARISON_FILES", contracts)
        comparison_patch.start(); self.addCleanup(comparison_patch.stop)
        exposure = self.stage / "exposure.json"
        self.write(exposure, {"development_answer_exposure_status": "none_known_before_capture"})
        self.gate["exposure_audit"] = self.pin(exposure)
        for item in inputs:
            day = item["session_date"]
            document = self.document(day, item)
            path = self.stage / (day + ".json"); self.write(path, document)
            native = self.native(day, document)
            native_path = self.stage / (day + "-native.json"); self.write(native_path, native)
            self.gate["captures"].append({"session_date": day, "input": self.pin(self.root / item["path"]), "prediction": self.pin(path), "native_verification": self.pin(native_path)})
        self.gate_path = self.stage / "reveal-gate.json"

    def write(self, path, value):
        path.write_text(json.dumps(value, indent=2) + "\n")

    def pin(self, path):
        return {"path": str(path.relative_to(self.root)), "sha256": G.digest(path)}

    def document(self, text, input_pin, *, balanced=False):
        day = date.fromisoformat(text); cutoff = M.P3.BASE.local(day, 9, 25)
        prices = (130, 70, 125, 110, 95, 135, 115, 85, 120, 110, 100, 115, 105, 101, 129, 90, 130, 95, 110)
        if balanced:
            prices = prices[:12] + (110,) + prices[13:]
        candidates = []
        for name, price in zip(G.BASELINE_NAMES, prices):
            family = "POC" if "POC" in name else "VAH" if "VAH" in name else "VAL" if "VAL" in name else name
            role = "modal" if family == "POC" else "value_boundary" if family in ("VAH", "VAL") else "range_extreme"
            candidates.append(M.Candidate("synthetic:" + name, price, (price, price), family, role, "completed_RTH", "synthetic-rth", cutoff - timedelta(days=1), True, auction_id="synthetic-rth", origin_role=name, source_identity=input_pin["sha256"]))
        close = 110 if balanced else 97
        inputs = M.SelectionInputs(day, cutoff, cutoff - timedelta(minutes=5), cutoff, close, tuple(candidates), (), True, True, input_identity=input_pin["sha256"])
        distributions, ledgers = [], []
        for window in sorted(G.WINDOWS):
            metadata = {"window": window, "profile_id": window + text, "input_identity": input_pin["sha256"], "code_identity": G.EXPECTED["phase3_model"], "settings_identity": G.EXPECTED["phase3_settings"], "contract": "ESZ2026", "feed": "CME GLOBEX", "adjustment": "individual_contract_unadjusted", "tick_size": .25, "row_size": 4, "grid_origin": 0, "measurement": "uniform_chart_bar_volume_across_inclusive_touched_bins"}
            distributions.append(metadata)
            ledgers.append({"distribution": {"metadata": metadata, "readiness": "ready", "reasons": [], "rows": [{"raw_mass": 10}], "total_mass": 10}, "status": "ready", "peaks": [], "regions": [], "lvn_ledger": [], "edge_ledger": [], "presentation": {}, "counts": {}})
        members = [{"profile_id": "synthetic-member-" + str(i), "input_identity": input_pin["sha256"]} for i in range(3)]
        derived = hashlib.sha256(json.dumps([(m["profile_id"], m["input_identity"]) for m in members], sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()
        for metadata in distributions:
            if metadata["window"] == "explicit_composite_RTH3":
                metadata["input_identity"] = derived
        return {"schema": "abacus.study29.phase5.local-development-map/v1", "session_date": text, "producer_revision": self.producer["id"], "input": input_pin, "complete_expanded_map": True, "incomplete_reasons": [],
                "model_pre_reveal_captured_at": "2026-10-31T03:20:00+00:00", "execution": {"started_at": "2026-10-31T03:15:00+00:00", "captured_at": "2026-10-31T03:20:00+00:00", "producer_manifest": self.gate["producer_manifest"]},
                "expanded_snapshot": {"baseline": {"trading_date": text, "cutoff": cutoff.isoformat(), "last_open": (cutoff - timedelta(minutes=5)).isoformat(), "last_close": cutoff.isoformat(), "values": list(prices)}, "distributions": distributions, "candidate_ledgers": ledgers, "composite_ledger": {"members": members, "status": "ready"}, "projection_ledgers": [{"status": "unavailable", "reason": "missing anchors"}]},
                "selector_inputs": M.record(inputs), "selections": {p + "-" + d: M.record(M.select_map(inputs, pivot_policy=p, target_policy=d)) for p in ("P0", "B0", "B1") for d in ("D0", "D1")},
                "autopivot_comparator": {"frozen": {"trading_date": text, "cutoff": cutoff.isoformat(), "last_included_open": (cutoff - timedelta(minutes=5)).isoformat(), "last_included_close": cutoff.isoformat(), "selection": {"price": 110 if balanced else 100, "inputs": [120, 110, 100, 110 if balanced else 105, close]}}}}

    def native(self, day, document):
        selection = document["selections"]["P0-D1"]
        semantic = {"pivot": {"candidate_id": "native:" + selection["pivot"]["candidate"]["candidate_id"], "price": selection["pivot"]["candidate"]["price"], "reason_code": selection["pivot"]["reason_code"], "fallback": selection["pivot"]["fallback"]}}
        for side in ("bullish", "bearish"):
            branch = selection[side]
            semantic[side] = {"status": branch["status"], "targets": [{"rank": t["rank"], "candidate_id": "native:" + t["candidate"]["candidate_id"], "price": t["candidate"]["price"], "reason_code": t["reason_code"]} for t in branch["targets"]]}
        states = {}
        for index, state in enumerate(("cutoff", "advanced", "restart")):
            image = self.stage / (day + "-" + state + ".png"); image.write_bytes(b"synthetic browser evidence only")
            states[state] = {"observed_at": f"2026-10-31T03:{25 + index:02d}:00+00:00", "last_included_open": day + "T09:20:00-04:00", "last_included_close": day + "T09:25:00-04:00", "selection": deepcopy(semantic), "evidence": [self.pin(image)]}
            if state == "advanced":
                states[state]["latest_observed_bar_close"] = day + "T10:00:00-04:00"
        source = next(r for r in self.producer["files"] if r["role"] == "selector_pine")
        return {"schema": "abacus.study29.phase5.native-date/v1", "session_date": day, "source": {"path": str((self.stage / source["snapshot_path"]).relative_to(self.root)), "sha256": source["sha256"]}, "implementation": "4.0.1", "control": "4.0.0",
                "settings": {"symbol": "CME_MINI:ESZ2026", "minutes": 5, "chart_type": "standard candles", "session": "ETH", "timezone": "America/New_York", "row_ticks": 16, "value_area_percent": 70, "cutoff": "09:25", "pivot_policy": "P0", "target_policy": "D1", "manual_anchors": []}, "states": states}

    def validate(self):
        self.write(self.gate_path, self.gate)
        return G.validate_gate(self.root, self.stage, self.gate_path, now=datetime(2026, 10, 31, 5, tzinfo=timezone.utc))

    def edit_prediction(self, edit):
        capture = self.gate["captures"][0]; path = self.root / capture["prediction"]["path"]
        document = json.loads(path.read_text()); edit(document); self.write(path, document); capture["prediction"] = self.pin(path)

    def edit_native(self, edit):
        capture = self.gate["captures"][0]; path = self.root / capture["native_verification"]["path"]
        document = json.loads(path.read_text()); edit(document); self.write(path, document); capture["native_verification"] = self.pin(path)

    def test_four_complete_maps_and_native_three_state_checks_pass(self):
        self.assertEqual(self.validate()["status"], "passed")

    def test_complete_profiles_with_honest_fallback_abstention_are_valid(self):
        capture = self.gate["captures"][0]
        document = self.document(capture["session_date"], capture["input"], balanced=True)
        self.assertTrue(document["selections"]["P0-D1"]["pivot"]["fallback"])
        self.assertEqual(document["selections"]["P0-D1"]["bullish"]["targets"], [])
        path = self.root / capture["prediction"]["path"]; self.write(path, document); capture["prediction"] = self.pin(path)
        path = self.root / capture["native_verification"]["path"]; self.write(path, self.native(capture["session_date"], document)); capture["native_verification"] = self.pin(path)
        self.assertEqual(self.validate()["status"], "passed")

    def test_one_missing_date_cannot_be_replaced_by_operator_boolean(self):
        self.gate["captures"].pop(); self.gate["operator_complete"] = True
        with self.assertRaisesRegex(ValueError, "all four"):
            self.validate()

    def test_hidden_date_rejected(self):
        self.gate["captures"][0]["session_date"] = "2026-10-21"
        with self.assertRaisesRegex(ValueError, "all four"):
            self.validate()

    def test_baseline_only_placeholder_rejected(self):
        self.edit_prediction(lambda d: d["expanded_snapshot"].pop("candidate_ledgers"))
        with self.assertRaisesRegex(ValueError, "all five"):
            self.validate()

    def test_optional_profile_unavailable_cannot_unlock_reveal(self):
        self.edit_prediction(lambda d: d["expanded_snapshot"]["candidate_ledgers"][0].update(status="unavailable"))
        with self.assertRaisesRegex(ValueError, "all five required profiles"):
            self.validate()

    def test_one_configuration_missing_rejected(self):
        self.edit_prediction(lambda d: d["selections"].pop("B1-D0"))
        with self.assertRaisesRegex(ValueError, "all six"):
            self.validate()

    def test_later_terminal_bar_rejected(self):
        self.edit_prediction(lambda d: d["selector_inputs"].update(last_included_open=G.DATES[0] + "T09:25:00-04:00"))
        with self.assertRaisesRegex(ValueError, "09:20-09:25"):
            self.validate()

    def test_source_price_inserted_into_selection_rejected(self):
        self.edit_prediction(lambda d: d["selections"]["P0-D1"]["bullish"]["targets"][0]["candidate"].update(price=999))
        with self.assertRaisesRegex(ValueError, "original candidate"):
            self.validate()

    def test_original19_and_selector_pool_must_agree(self):
        self.edit_prediction(lambda d: d["expanded_snapshot"]["baseline"]["values"].__setitem__(0, 999))
        with self.assertRaisesRegex(ValueError, "original-19"):
            self.validate()

    def test_frozen_native_identity_changes_rejected(self):
        self.edit_native(lambda n: n["states"]["restart"]["selection"]["pivot"].update(candidate_id="changed"))
        with self.assertRaisesRegex(ValueError, "changed after cutoff"):
            self.validate()

    def test_native_advance_must_reach_rth(self):
        self.edit_native(lambda n: n["states"]["advanced"].update(latest_observed_bar_close=G.DATES[0] + "T09:30:00-04:00"))
        with self.assertRaisesRegex(ValueError, "reach completed RTH"):
            self.validate()

    def test_missing_native_evidence_rejected(self):
        self.edit_native(lambda n: n["states"]["cutoff"].update(evidence=[]))
        with self.assertRaisesRegex(ValueError, "hashed actual browser"):
            self.validate()

    def test_missing_native_state_rejected(self):
        self.edit_native(lambda n: n["states"].pop("restart"))
        with self.assertRaisesRegex(ValueError, "cutoff/advance/restart"):
            self.validate()

    def test_after_gate_capture_rejected(self):
        self.edit_prediction(lambda d: d.update(model_pre_reveal_captured_at="2026-10-31T04:01:00Z"))
        with self.assertRaisesRegex(ValueError, "chronology"):
            self.validate()

    def test_changed_producer_snapshot_rejected(self):
        first = self.producer["files"][0]
        (self.stage / first["snapshot_path"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "mismatched"):
            self.validate()

    def test_execution_against_other_decision_rule_bytes_rejected(self):
        producer_path = self.root / self.gate["producer_manifest"]["path"]
        producer = json.loads(producer_path.read_text())
        item = next(r for r in producer["files"] if r["role"] == "phase5_decision_rule")
        path = self.stage / item["snapshot_path"]; path.write_text("synthetic other decision rule")
        item["sha256"] = G.digest(path)
        self.write(producer_path, producer); self.gate["producer_manifest"] = self.pin(producer_path)
        with self.assertRaisesRegex(ValueError, "producer protocol/decision bytes"):
            self.validate()

    def test_retained_model_dependency_path_must_identify_actual_import(self):
        producer_path = self.root / self.gate["producer_manifest"]["path"]
        producer = json.loads(producer_path.read_text())
        item = next(r for r in producer["files"] if r["role"] == "phase3_model")
        source = self.stage / item["snapshot_path"]; target = self.stage / "elsewhere.py"; shutil.copyfile(source, target)
        item["snapshot_path"] = "elsewhere.py"
        self.write(producer_path, producer); self.gate["producer_manifest"] = self.pin(producer_path)
        with self.assertRaisesRegex(ValueError, "actual sibling"):
            self.validate()

    def test_market_input_configuration_change_rejected(self):
        producer_path = self.root / self.gate["producer_manifest"]["path"]
        producer = json.loads(producer_path.read_text())
        input_path = self.root / producer["input_manifest"]["path"]
        declaration = json.loads(input_path.read_text()); declaration["market_configuration"]["row_ticks"] = 4
        self.write(input_path, declaration); producer["input_manifest"] = self.pin(input_path)
        self.write(producer_path, producer); self.gate["producer_manifest"] = self.pin(producer_path)
        with self.assertRaisesRegex(ValueError, "market input declaration"):
            self.validate()

    def test_guard_failure_precedes_answer_loader_import(self):
        self.gate["captures"] = []; self.write(self.gate_path, self.gate)
        original = __import__
        def guarded(name, *args, **kwargs):
            if name.startswith("abacus_bhishma"):
                raise AssertionError("must not import answer loader")
            return original(name, *args, **kwargs)
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 31, 5, tzinfo=timezone.utc)
        with patch("builtins.__import__", side_effect=guarded), patch.object(G, "datetime", FixedDateTime), self.assertRaisesRegex(ValueError, "all four"):
            G.select(self.root, self.stage, self.gate_path)

    def test_source_row_outside_allowlist_rejected(self):
        with self.assertRaises(ValueError):
            G.bounded_rows([{"session_date": "2026-10-21"}], G.DATES[0])
        with self.assertRaises(ValueError):
            G.bounded_rows([], "2026-10-21")

    def test_other_chart_date_nested_content_withheld(self):
        original = {"session_date": G.DATES[0], "sources": [{"source_id": "other", "chart_session_date": "2026-10-21", "source_text": "synthetic excluded"}], "markers": [{"source_id": "other", "annotation_raw": "synthetic excluded"}], "closing_notes": [{"source_id": "other", "label_raw": "synthetic excluded"}]}
        before = deepcopy(original)
        projected, excluded = G.bounded_observation(original, G.DATES[0])
        self.assertEqual(original, before)
        self.assertEqual(projected["sources"], [])
        self.assertEqual(projected["markers"], [])
        self.assertNotIn("source_text", excluded[0])

    def test_other_inferred_nested_date_cannot_leak_through_null_chart_date(self):
        original = {"session_date": G.DATES[0], "sources": [{"source_id": "other", "chart_session_date": None, "inferred_session_date": "2026-10-21", "source_text": "synthetic excluded"}], "markers": [], "closing_notes": []}
        projected, excluded = G.bounded_observation(original, G.DATES[0])
        self.assertEqual(projected["sources"], [])
        self.assertEqual(excluded[0]["inferred_session_date"], "2026-10-21")


if __name__ == "__main__":
    unittest.main()
