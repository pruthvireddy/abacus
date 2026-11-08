"""Synthetic prospective orchestration checks; never retained target sources."""
from copy import deepcopy
import csv
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location("study29_phase6_capture_tests", HERE.parents[1] / "phase6/capture.py")
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


class CaptureFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.stage = self.root / "work/29_verniman_level_reconstruction/phase6_synthetic"
        self.stage.mkdir(parents=True)
        self.day = "2026-11-02"
        self.started = C.at(self.day, "09:26").astimezone(timezone.utc)
        self.completed = self.started + timedelta(seconds=2)
        dates = []
        day = datetime.fromisoformat("2026-11-02")
        while day.date().isoformat() <= "2026-11-25":
            if day.weekday() < 5:
                dates.append(day.date().isoformat())
            day += timedelta(days=1)
        dates += ["2026-12-07", "2026-12-08"]
        self.freeze_path = self.stage / "freeze.json"
        old = json.loads((REPO / "work/29_verniman_level_reconstruction/phase5_20261031T023320Z/producer-1.json").read_text())
        originals = {r["role"]: r for r in old["files"]}
        rows = []
        for role in C.FIXED:
            old_role = "runner" if role == "phase5_runner" else role
            source = REPO / originals[old_role]["path"]
            if role in ("phase4_model", "phase3_model", "reference_model"):
                relative = "source/src/" + source.name
            elif role == "matcher":
                relative = "source/phase3/matching.py"
            else:
                relative = "source/" + role + "/" + source.name
            current, snapshot = self.stage / relative, self.stage / "snapshots" / relative
            for target in (current, snapshot):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            rows.append({"role": role, **C.pinned(self.root, current), "snapshot_path": str(snapshot.relative_to(self.root))})
        current, snapshot = self.stage / "source/capture.py", self.stage / "snapshots/capture.py"
        shutil.copyfile(C.__file__, current)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(C.__file__, snapshot)
        rows.append({"role": "capture_runner", **C.pinned(self.root, current), "snapshot_path": str(snapshot.relative_to(self.root))})
        calendar_source = REPO / "studies/29_verniman_level_reconstruction/phase6/calendar_control.py"
        current, snapshot = self.stage / "source/calendar_control.py", self.stage / "snapshots/calendar_control.py"
        shutil.copyfile(calendar_source, current)
        shutil.copyfile(calendar_source, snapshot)
        rows.append({"role": "calendar_control", **C.pinned(self.root, current), "snapshot_path": str(snapshot.relative_to(self.root))})
        self.calendar_path = self.stage / "calendar.json"
        shutil.copyfile(REPO / "studies/29_verniman_level_reconstruction/phase6/calendar.json", self.calendar_path)
        self.protocol_path = self.stage / "protocol.txt"
        self.protocol_path.write_text("Synthetic prospective protocol.\n")
        self.freeze = {"schema": "abacus.study29.phase6.freeze/v1", "frozen_at": "2026-10-31T12:00:00+00:00",
            "scheduled_dates": dates, "configurations": list(C.CONFIGURATIONS), "market_configuration": C.MARKET,
            "cutoff_local": "09:25", "capture_deadline_local": "09:30",
            "period_end_at": C.at(dates[-1], "16:00").isoformat(), "producer_files": rows,
            "files": [{"role": "calendar", **C.pinned(self.root, self.calendar_path)}, {"role": "protocol", **C.pinned(self.root, self.protocol_path)}]}
        dump(self.freeze_path, self.freeze)
        self.raw = self.stage / "raw.csv"
        self.write_csv([("2026-11-02T09:20:00-05:00", 100, 101, 99, 100, 5),
                        ("2026-11-02T09:25:00-05:00", "not-read", "future", "future", "future", "future")])
        self.input_dir = self.stage / "input"
        C.prepare_input(self.root, self.freeze_path, self.day, self.raw, self.input_dir, now=self.started - timedelta(seconds=20))
        self.access_path = self.stage / "access.json"
        self.access = {"schema": "abacus.study29.phase6.access-log/v1", "closed_through": (self.started - timedelta(seconds=1)).isoformat(),
            "complete_to_best_knowledge": True, "actors": [{"actor_id": "predictor-A", "role": "prediction"}, {"actor_id": "collector-B", "role": "collector"}],
            "events": [], "limitations": "Synthetic operator attestations, not access-control proof"}
        dump(self.access_path, self.access)
        self.native = self.stage / "synthetic-browser-evidence.txt"
        self.native.write_text("Synthetic evidence fixture; not an actual browser capture.\n")
        self.request_path = self.stage / "request.json"
        self.request = {"schema": "abacus.study29.phase6.capture-request/v1", "session_date": self.day,
            "operator_id": "predictor-A", "capture_mode": "prospective", "input_manifest": C.pinned(self.root, self.input_dir / "input-manifest.json"),
            "source_access_log": C.pinned(self.root, self.access_path), "native_evidence": [C.pinned(self.root, self.native)],
            "observed_terminal_bar": {"opened": C.at(self.day, "09:20").isoformat(), "closed": C.at(self.day, "09:25").isoformat(), "confirmed": True}}
        dump(self.request_path, self.request)
        self.output = self.stage / "capture"

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, rows):
        with self.raw.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("time", "open", "high", "low", "close", "Volume"))
            writer.writerows(rows)

    def clock(self):
        return iter((self.started, self.completed)).__next__

    def minimal_map(self, *args):
        return {"schema": "abacus.study29.phase6.local-map/v1", "session_date": self.day,
            "execution": {"started_at": self.started.isoformat(), "protocol_freeze": C.pinned(self.root, self.freeze_path)},
            "market_configuration": C.MARKET, "configurations": list(C.CONFIGURATIONS),
            "input": json.loads((self.input_dir / "input-manifest.json").read_text())["file"],
            "complete_expanded_map": False, "incomplete_reasons": ["synthetic_insufficient_history"],
            "bar_audit": {"last_included_open": C.at(self.day, "09:20").isoformat(), "last_included_close": C.at(self.day, "09:25").isoformat(), "excluded_after_cutoff_rows": 0},
            "selections": dict.fromkeys(C.CONFIGURATIONS, {})}

    def save_incomplete(self):
        with patch.object(C, "construct_map", side_effect=self.minimal_map):
            return C.capture(self.root, self.freeze_path, self.request_path, self.output, clock=self.clock())

    def synthetic_complete_history(self):
        current = C.at("2026-10-18", "18:00")
        end = C.at(self.day, "09:25")
        rows = []
        while current < end:
            weekday, hour = current.weekday(), current.hour
            valid = weekday < 5 and hour != 17 and not (weekday == 4 and hour >= 17)
            valid = valid or weekday == 6 and hour >= 18
            if valid:
                rows.append((current.isoformat(), 100, 101, 99, 100, 10))
            current += timedelta(minutes=5)
        self.write_csv(rows)
        shutil.rmtree(self.input_dir)
        C.prepare_input(self.root, self.freeze_path, self.day, self.raw, self.input_dir, now=self.started - timedelta(seconds=20))
        self.request["input_manifest"] = C.pinned(self.root, self.input_dir / "input-manifest.json")
        dump(self.request_path, self.request)


class IdentityAndInputTests(CaptureFixtures):
    def test_exact_thirteen_required_producer_roles_validate(self):
        _, snapshots = C.validate_freeze(self.root, self.freeze_path, now=self.started)
        self.assertEqual(len(snapshots), 13)

    def test_calendar_anchor_allows_same_day_freeze_before_first_cutoff(self):
        self.freeze["frozen_at"] = "2026-11-02T08:00:00-05:00"
        dump(self.freeze_path, self.freeze)
        actual, _ = C.validate_freeze(self.root, self.freeze_path, now=self.started)
        self.assertEqual(actual["scheduled_dates"][0], "2026-11-02")

    def test_changed_frozen_protocol_bytes_rejected(self):
        self.protocol_path.write_text("Changed protocol.")
        with self.assertRaisesRegex(ValueError, "changed pinned"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_changed_calendar_bytes_rejected(self):
        self.calendar_path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "changed pinned"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_arbitrary_twenty_weekdays_rejected_against_frozen_calendar(self):
        self.freeze["scheduled_dates"][-2:] = ["2026-12-09", "2026-12-10"]
        self.freeze["period_end_at"] = C.at("2026-12-10", "16:00").isoformat()
        dump(self.freeze_path, self.freeze)
        with self.assertRaisesRegex(ValueError, "fixed calendar"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_unsupported_holiday_calendar_cannot_be_re_pinned_into_valid_freeze(self):
        calendar = json.loads(self.calendar_path.read_text())
        calendar["scheduled_dates"][-1] = "2026-12-09"
        dump(self.calendar_path, calendar)
        self.freeze["files"][0] = {"role": "calendar", **C.pinned(self.root, self.calendar_path)}
        dump(self.freeze_path, self.freeze)
        with self.assertRaisesRegex(ValueError, "first twenty"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_wrong_session_rejected_without_prediction_generation(self):
        self.request["session_date"] = "2026-10-26"
        dump(self.request_path, self.request)
        with self.assertRaisesRegex(ValueError, "calendar"):
            C.capture(self.root, self.freeze_path, self.request_path, self.output, clock=self.clock())
        self.assertFalse(self.output.exists())

    def test_wrong_artifact_hash_rejected_before_import(self):
        self.freeze["producer_files"][0]["sha256"] = "0" * 64
        dump(self.freeze_path, self.freeze)
        with self.assertRaisesRegex(ValueError, "fixed Phase5"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_changed_snapshot_rejected(self):
        snapshot = self.root / self.freeze["producer_files"][0]["snapshot_path"]
        snapshot.write_text("changed")
        with self.assertRaisesRegex(ValueError, "snapshot differs"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_silent_contract_or_adjusted_series_substitution_rejected(self):
        self.freeze["market_configuration"] = {**C.MARKET, "contract": "ESH2027"}
        dump(self.freeze_path, self.freeze)
        with self.assertRaisesRegex(ValueError, "market configuration"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_new_configuration_not_permitted(self):
        self.freeze["configurations"].append("P0-D2")
        dump(self.freeze_path, self.freeze)
        with self.assertRaisesRegex(ValueError, "six unchanged"):
            C.validate_freeze(self.root, self.freeze_path, now=self.started)

    def test_prefix_excludes_raw_open0925_without_reading_future_values(self):
        source = json.loads((self.input_dir / "input-manifest.json").read_text())
        self.assertEqual(source["included_rows"], 1)
        self.assertEqual(source["excluded_raw_after_cutoff_rows"], 1)
        self.assertEqual(C._csv_rows(self.root / source["file"]["path"], self.day, trim=False)[0][-1][0], C.at(self.day, "09:20"))

    def test_execution_input_postcutoff_contamination_rejected(self):
        with self.assertRaisesRegex(ValueError, "post-cutoff"):
            C._csv_rows(self.raw, self.day, trim=False)

    def test_missing_exact_terminal_is_rejected(self):
        self.write_csv([("2026-11-02T09:15:00-05:00", 100, 101, 99, 100, 5)])
        with self.assertRaisesRegex(ValueError, "terminal bar missing"):
            C._csv_rows(self.raw, self.day, trim=True)

    def test_duplicate_timestamps_rejected(self):
        row = ("2026-11-02T09:20:00-05:00", 100, 101, 99, 100, 5)
        self.write_csv([row, row])
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            C._csv_rows(self.raw, self.day, trim=True)

    def test_later_market_date_rejected(self):
        self.write_csv([("2026-11-03T09:20:00-05:00", 100, 101, 99, 100, 5)])
        with self.assertRaisesRegex(ValueError, "later market date"):
            C._csv_rows(self.raw, self.day, trim=True)

    def test_input_prefix_must_reproduce_declared_raw_transformation(self):
        source_path = self.input_dir / "input-manifest.json"
        source = json.loads(source_path.read_text())
        prefix = self.root / source["file"]["path"]
        prefix.write_text(prefix.read_text().replace("100.0", "102.0"))
        source["file"] = C.pinned(self.root, prefix)
        dump(source_path, source)
        with self.assertRaises(ValueError):
            C.validate_input(self.root, self.freeze_path, self.day, C.pinned(self.root, source_path))

    def test_cannot_prepare_future_observation(self):
        with self.assertRaisesRegex(ValueError, "future completed"):
            C.prepare_input(self.root, self.freeze_path, self.day, self.raw, self.stage / "new", now=C.at(self.day, "09:24"))


class TimingAndReceiptTests(CaptureFixtures):
    def test_dst_cutoff_uses_newyork_not_fixed_utc_offset(self):
        self.assertEqual(C.at("2026-10-30", "09:25").astimezone(timezone.utc).hour, 13)
        self.assertEqual(C.at("2026-11-02", "09:25").astimezone(timezone.utc).hour, 14)
        self.assertEqual(C.at("2026-11-02", "09:25").utcoffset(), timedelta(hours=-5))

    def test_classification_timely_boundary_and_late(self):
        for completed, status in ((C.at(self.day, "09:30"), "timely"), (C.at(self.day, "09:30") + timedelta(microseconds=1), "late")):
            self.assertEqual(C.classify(self.freeze, self.day, "prospective", self.started, completed, self.access, "predictor-A", True), status)

    def test_historical_replay_cannot_be_relabelled_timely(self):
        self.assertEqual(C.classify(self.freeze, self.day, "historical_replay", self.started, self.completed, self.access, "predictor-A", True), "reconstructed")

    def test_later_day_capture_is_late(self):
        self.assertEqual(C.classify(self.freeze, self.day, "prospective", self.started + timedelta(days=1), self.completed + timedelta(days=1), self.access, "predictor-A", True), "late")

    def test_answer_access_or_disclosure_classifies_exposed(self):
        for event in ({"actor_id": "predictor-A", "kind": "answer_access"}, {"actor_id": "collector-B", "recipient_actor_id": "predictor-A", "kind": "answer_disclosure"}):
            access = deepcopy(self.access)
            access["events"] = [{**event, "session_date": self.day, "occurred_at": (self.started - timedelta(seconds=30)).isoformat()}]
            self.assertEqual(C.classify(self.freeze, self.day, "prospective", self.started, self.completed, access, "predictor-A", True), "exposed")

    def test_forged_replay_or_unsupported_future_cutoff_rejected(self):
        early = C.at(self.day, "09:24")
        for mode, complete in (("historical_replay", True), ("prospective", False)):
            with self.assertRaisesRegex(ValueError, "before confirmed cutoff"):
                C.classify(self.freeze, self.day, mode, early, early, self.access, "predictor-A", complete)

    def test_placeholder_prediction_actor_is_not_an_actual_identity(self):
        self.access["actors"][0]["actor_id"] = "prediction-operator-pending"
        dump(self.access_path, self.access)
        with self.assertRaisesRegex(ValueError, "nonplaceholder"):
            C.validate_access_log(self.root, C.pinned(self.root, self.access_path), "prediction-operator-pending", self.started)

    def test_fresh_log_cannot_claim_future_closure(self):
        for closed in (self.started + timedelta(seconds=1), self.started - timedelta(minutes=6)):
            self.access["closed_through"] = closed.isoformat()
            dump(self.access_path, self.access)
            with self.assertRaisesRegex(ValueError, "five minutes"):
                C.validate_access_log(self.root, C.pinned(self.root, self.access_path), "predictor-A", self.started)

    def test_incomplete_synthetic_map_is_unsupported_not_complete_prediction(self):
        receipt = self.save_incomplete()
        self.assertEqual(receipt["status"], "unsupported")
        self.assertFalse(receipt["complete_expanded_map"])
        self.assertFalse(receipt["timestamp_evidence"]["independent_certification"])

    def test_saved_prediction_modification_detected_without_selection_rerun(self):
        self.save_incomplete()
        (self.output / "prediction.json").write_text("{}")
        with patch.object(C, "construct_map", side_effect=AssertionError("must not rerun")):
            with self.assertRaisesRegex(ValueError, "changed pinned"):
                C.verify_capture(self.root, self.freeze_path, self.output / "capture-receipt.json", now=self.completed)

    def test_receipt_timing_status_modification_rejected(self):
        self.save_incomplete()
        path = self.output / "capture-receipt.json"
        receipt = json.loads(path.read_text())
        receipt["status"] = "timely"
        dump(path, receipt)
        with self.assertRaisesRegex(ValueError, "incorrectly classifies"):
            C.verify_capture(self.root, self.freeze_path, path, now=self.completed)

    def test_refuses_overwrite(self):
        self.save_incomplete()
        with self.assertRaisesRegex(ValueError, "fresh immutable"):
            self.save_incomplete()

    def test_missing_status_after_deadline_never_has_prediction(self):
        request = {"schema": "abacus.study29.phase6.status-request/v1", "session_date": self.day, "status": "missing", "incomplete_reasons": ["operator unavailable"],
            "operator_id": "predictor-A", "source_access_log": C.pinned(self.root, self.access_path)}
        dump(self.request_path, request)
        current = C.at(self.day, "09:30")
        receipt = C.finalize_status(self.root, self.freeze_path, self.request_path, self.output, now=current)
        self.assertIsNone(receipt["prediction"])
        self.assertEqual(receipt["status"], "missing")
        self.assertFalse((self.output / "prediction.json").exists())

    def test_missing_status_before_deadline_rejected(self):
        request = {"schema": "abacus.study29.phase6.status-request/v1", "session_date": self.day, "status": "input_unavailable", "incomplete_reasons": ["no feed"],
            "operator_id": "predictor-A", "source_access_log": C.pinned(self.root, self.access_path)}
        dump(self.request_path, request)
        with self.assertRaisesRegex(ValueError, "before its deadline"):
            C.finalize_status(self.root, self.freeze_path, self.request_path, self.output, now=self.started)

    def test_failure_placeholder_cannot_claim_complete_map(self):
        request = {"schema": "abacus.study29.phase6.status-request/v1", "session_date": self.day, "status": "missing", "incomplete_reasons": ["no capture"],
            "operator_id": "predictor-A", "source_access_log": C.pinned(self.root, self.access_path)}
        dump(self.request_path, request)
        C.finalize_status(self.root, self.freeze_path, self.request_path, self.output, now=C.at(self.day, "09:30"))
        path = self.output / "capture-receipt.json"
        receipt = json.loads(path.read_text()); receipt["complete_expanded_map"] = True; dump(path, receipt)
        with self.assertRaisesRegex(ValueError, "placeholder"):
            C.verify_capture(self.root, self.freeze_path, path, now=C.at(self.day, "09:30"))

    def test_status_creation_rejects_unidentified_request_schema(self):
        request = {"schema": "generic-json", "session_date": self.day, "status": "missing", "incomplete_reasons": ["no capture"],
            "operator_id": "predictor-A", "source_access_log": C.pinned(self.root, self.access_path)}
        dump(self.request_path, request)
        with self.assertRaisesRegex(ValueError, "status request required"):
            C.finalize_status(self.root, self.freeze_path, self.request_path, self.output, now=C.at(self.day, "09:30"))
        self.assertFalse(self.output.exists())

    def test_failure_readback_binds_original_status_and_reasons(self):
        request = {"schema": "abacus.study29.phase6.status-request/v1", "session_date": self.day, "status": "missing", "incomplete_reasons": ["no capture"],
            "operator_id": "predictor-A", "source_access_log": C.pinned(self.root, self.access_path)}
        dump(self.request_path, request)
        C.finalize_status(self.root, self.freeze_path, self.request_path, self.output, now=C.at(self.day, "09:30"))
        path = self.output / "capture-receipt.json"
        original = json.loads(path.read_text())
        for key, value in (("status", "input_unavailable"), ("incomplete_reasons", ["different reason"])):
            with self.subTest(field=key):
                receipt = deepcopy(original)
                receipt[key] = value
                dump(path, receipt)
                with self.assertRaisesRegex(ValueError, "schema/status/reasons differ"):
                    C.verify_capture(self.root, self.freeze_path, path, now=C.at(self.day, "09:30"))

    def test_map_readback_rejects_unidentified_capture_request(self):
        self.save_incomplete()
        self.request["schema"] = "generic-json"
        dump(self.request_path, self.request)
        path = self.output / "capture-receipt.json"
        receipt = json.loads(path.read_text()); receipt["request"] = C.pinned(self.root, self.request_path); dump(path, receipt)
        with self.assertRaisesRegex(ValueError, "capture request required"):
            C.verify_capture(self.root, self.freeze_path, path, now=self.completed)

    def test_map_readback_rechecks_terminal_confirmation_attestation(self):
        self.save_incomplete()
        self.request["observed_terminal_bar"]["confirmed"] = False
        dump(self.request_path, self.request)
        path = self.output / "capture-receipt.json"
        receipt = json.loads(path.read_text()); receipt["request"] = C.pinned(self.root, self.request_path); dump(path, receipt)
        with self.assertRaisesRegex(ValueError, "confirmed terminal-bar"):
            C.verify_capture(self.root, self.freeze_path, path, now=self.completed)

    def test_map_readback_rejects_re_pinned_empty_native_evidence(self):
        self.save_incomplete()
        self.native.write_text("")
        evidence = [C.pinned(self.root, self.native)]
        self.request["native_evidence"] = evidence
        dump(self.request_path, self.request)
        path = self.output / "capture-receipt.json"
        receipt = json.loads(path.read_text()); receipt["request"] = C.pinned(self.root, self.request_path)
        receipt["timestamp_evidence"]["operator_evidence"] = evidence
        dump(path, receipt)
        with self.assertRaisesRegex(ValueError, "native evidence is empty"):
            C.verify_capture(self.root, self.freeze_path, path, now=self.completed)

    def test_baseline_only_placeholder_cannot_claim_complete_expanded_map(self):
        candidate = self.minimal_map()
        candidate["complete_expanded_map"] = True
        candidate["incomplete_reasons"] = []
        candidate["original_baseline_fields"] = {name: 100 for name in C.BASELINE_FIELDS}
        candidate["input_coverage"] = {"status": "complete", "required_windows": [{"ready": True, "missing_bars": 0} for _ in range(8)]}
        with self.assertRaisesRegex(ValueError, "five actual distributions"):
            C.validate_saved_map(candidate, self.day)

    def test_full_synthetic_snapshot_uses_exact_frozen_models_and_saves_all_six(self):
        self.synthetic_complete_history()
        receipt = C.capture(self.root, self.freeze_path, self.request_path, self.output, clock=self.clock())
        self.assertEqual(receipt["status"], "timely")
        prediction = json.loads((self.output / "prediction.json").read_text())
        self.assertTrue(prediction["complete_expanded_map"], prediction["incomplete_reasons"])
        self.assertEqual(len(prediction["expanded_snapshot"]["candidate_ledgers"]), 5)
        self.assertEqual(set(prediction["selections"]), set(C.CONFIGURATIONS))
        self.assertEqual(prediction["bar_audit"]["last_included_close"], self.day + "T09:25:00-05:00")
        self.assertFalse(receipt["native_execution_established_by_capture_tool"])
        self.assertEqual(len(prediction["input_coverage"]["required_windows"]), 8)
        self.assertEqual(prediction["input_coverage"]["status"], "complete")
        with patch.object(C, "construct_map", side_effect=AssertionError("must not rerun")):
            self.assertEqual(C.verify_capture(self.root, self.freeze_path, self.output / "capture-receipt.json", now=self.completed)["status"], "timely")

    def test_missing_preceding_history_bar_is_explicit_unsupported_map(self):
        self.synthetic_complete_history()
        with self.raw.open() as handle:
            rows = list(csv.reader(handle))
        rows = [row for row in rows if not row[0].startswith("2026-10-27T10:00")]
        with self.raw.open("w", newline="") as handle:
            csv.writer(handle).writerows(rows)
        shutil.rmtree(self.input_dir)
        C.prepare_input(self.root, self.freeze_path, self.day, self.raw, self.input_dir, now=self.started - timedelta(seconds=20))
        self.request["input_manifest"] = C.pinned(self.root, self.input_dir / "input-manifest.json")
        dump(self.request_path, self.request)
        receipt = C.capture(self.root, self.freeze_path, self.request_path, self.output, clock=self.clock())
        self.assertEqual(receipt["status"], "unsupported")
        prediction = json.loads((self.output / "prediction.json").read_text())
        self.assertEqual(prediction["input_coverage"]["status"], "incomplete")
        self.assertIn("required_eight_fixed_clock_windows_incomplete", prediction["incomplete_reasons"])

    def test_saved_complete_map_rejects_arbitrary_nineteen_baseline_names(self):
        self.synthetic_complete_history()
        C.capture(self.root, self.freeze_path, self.request_path, self.output, clock=self.clock())
        path = self.output / "prediction.json"
        prediction = json.loads(path.read_text())
        baseline = prediction["original_baseline_fields"]
        baseline["arbitrary_replacement"] = baseline.pop("previous_full_high")
        self.assertEqual(len(baseline), 19)
        dump(path, prediction)
        receipt_path = self.output / "capture-receipt.json"
        receipt = json.loads(receipt_path.read_text()); receipt["prediction"] = C.pinned(self.root, path); dump(receipt_path, receipt)
        with patch.object(C, "construct_map", side_effect=AssertionError("must not rerun selection")):
            with self.assertRaisesRegex(ValueError, "exact19.*field names"):
                C.verify_capture(self.root, self.freeze_path, receipt_path, now=self.completed)

    def test_saved_ready_coverage_flags_must_match_actual_csv_timestamps(self):
        self.synthetic_complete_history()
        C.capture(self.root, self.freeze_path, self.request_path, self.output, clock=self.clock())
        path = self.output / "prediction.json"
        prediction = json.loads(path.read_text())
        window = prediction["input_coverage"]["required_windows"][0]
        window["expected_bars"] -= 1
        window["observed_bars"] -= 1
        self.assertTrue(window["ready"])
        self.assertEqual(window["missing_bars"], 0)
        dump(path, prediction)
        receipt_path = self.output / "capture-receipt.json"
        receipt = json.loads(receipt_path.read_text()); receipt["prediction"] = C.pinned(self.root, path); dump(receipt_path, receipt)
        with patch.object(C, "construct_map", side_effect=AssertionError("must not rerun selection")):
            with self.assertRaisesRegex(ValueError, "coverage differs from actual input timestamps"):
                C.verify_capture(self.root, self.freeze_path, receipt_path, now=self.completed)


if __name__ == "__main__":
    unittest.main()
