"""Synthetic Phase 5 orchestration guards; no retained market or answer reads."""
from datetime import date, datetime, timedelta, timezone
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
SOURCE = STUDY / "phase5/run_development.py"
SPEC = importlib.util.spec_from_file_location("study29_phase5_runner_tests", SOURCE)
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)
MODEL = R.load_module("study29_phase5_synthetic_model", STUDY / "src/phase4_model.py")


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


class RetainedFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.stage = self.root / "work/29_verniman_level_reconstruction/phase5_synthetic"
        self.stage.mkdir(parents=True)
        self.input = self.stage / "market-inputs.json"
        self.freeze = self.stage / "protocol-freeze.json"
        self.producer = self.stage / "producer-1.json"
        self.output = self.stage / "attempt1"
        # Only source bytes and lock files are copied. No prior evidence, answer
        # file, source table, chart input or mutable comparator file is read.
        for role, relative in R.ROLE_PATHS.items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if role.startswith("phase5_"):
                if role == "phase5_settings":
                    dump(target, {"development_dates": list(R.DATES), "configurations": list(R.CONFIGURATIONS)})
                else:
                    target.write_text("Synthetic pre-answer protocol document.\n")
            else:
                shutil.copyfile(R.ROOT / relative, target)
        frozen = [{"path": R.ROLE_PATHS[role], "sha256": R.digest(self.root / R.ROLE_PATHS[role])}
                  for role in ("phase5_protocol", "phase5_settings", "phase5_inputs", "phase5_decision_rule")]
        dump(self.freeze, {"frozen_at": "2026-10-30T00:00:00+00:00", "frozen_files": frozen})
        records = []
        for day in R.DATES:
            target = self.stage / "inputs" / (day + ".csv")
            target.parent.mkdir(exist_ok=True)
            target.write_text("time,open,high,low,close,Volume,ignored_diagnostic\n" +
                              day + "T09:20:00-04:00,100,101,99,100,10,answer-like text ignored\n")
            records.append({"session_date": day, "path": str(target.relative_to(self.root)), "sha256": R.digest(target)})
        dump(self.input, {"schema": "abacus.study29.phase5.market-inputs/v1", "recorded_at": "2026-10-30T00:01:00+00:00",
                          "stage": str(self.stage.relative_to(self.root)), "market_configuration": R.MARKET, "files": records})

    def tearDown(self):
        self.tmp.cleanup()

    def freeze_producer(self):
        return R.freeze_producer(self.root, self.input, self.freeze, self.producer, "synthetic-producer-1")

    def validate(self):
        return R.validate_manifests(self.root, self.input, self.producer)

    def mutate_input(self, operation):
        document = json.loads(self.input.read_text())
        operation(document)
        dump(self.input, document)

    def test_freeze_retains_all_sources_without_parsing_market_rows(self):
        with patch.object(R, "read_bars", side_effect=AssertionError("market parsing prohibited during freeze")):
            result = self.freeze_producer()
        self.assertEqual(result["market_rows_parsed"], 0)
        _, _, _, snapshots, _ = self.validate()
        self.assertEqual(set(snapshots), set(R.ROLE_PATHS))
        self.assertTrue(all(p.is_relative_to(self.stage) for p in snapshots.values()))

    def test_original_and_snapshot_corruption_fail_before_import(self):
        self.freeze_producer()
        self.mutate_input(lambda x: x["files"][0].update(sha256="0" * 64))
        with patch.object(R, "load_module", side_effect=AssertionError("must validate before import")):
            with self.assertRaisesRegex(ValueError, "changed pinned bytes"):
                R.run(self.root, self.input, self.producer, self.output)
        self.assertFalse(self.output.exists())

    def test_protected_date_metadata_rejected_before_opening_paths(self):
        self.mutate_input(lambda x: x["files"][0].update(session_date="2026-10-21", path="do-not-read.csv"))
        with patch.object(R, "pin", side_effect=AssertionError("date allowlist must precede file reads")):
            with self.assertRaisesRegex(ValueError, "exact four"):
                R.validate_input_manifest(self.root, self.input)

    def test_missing_date_cannot_be_replaced_by_success_flag(self):
        self.mutate_input(lambda x: (x["files"].pop(), x.update(complete=True)))
        with self.assertRaisesRegex(ValueError, "exact four"):
            R.validate_input_manifest(self.root, self.input)

    def test_duplicate_dates_are_not_a_complete_batch(self):
        self.mutate_input(lambda x: x["files"][3].update(session_date=R.DATES[0]))
        with self.assertRaisesRegex(ValueError, "exact four"):
            R.validate_input_manifest(self.root, self.input)

    def test_shared_capture_cannot_stand_for_two_sessions(self):
        self.mutate_input(lambda x: x["files"][3].update(path=x["files"][0]["path"]))
        with self.assertRaisesRegex(ValueError, "own declared capture"):
            R.validate_input_manifest(self.root, self.input)

    def test_changed_market_policy_is_not_a_compatible_input(self):
        for key, value in (("row_ticks", 8), ("cutoff_minute", 30), ("manual_anchors", ["fabricated"]), ("adjustment", "continuous_adjusted")):
            with self.subTest(key=key):
                document = json.loads(self.input.read_text())
                document["market_configuration"] = dict(R.MARKET)
                document["market_configuration"][key] = value
                dump(self.input, document)
                with self.assertRaisesRegex(ValueError, "noncontrol market"):
                    R.validate_input_manifest(self.root, self.input)

    def test_immutable_comparator_is_required_instead_of_working_tree(self):
        self.freeze_producer()
        document = json.loads(self.producer.read_text())
        item = next(p for p in document["files"] if p["role"] == "autopivot_model")
        item["path"] = R.STUDY + "/src/pivot_model.py"
        mutable = self.root / item["path"]
        mutable.parent.mkdir(parents=True, exist_ok=True)
        mutable.write_text("mutable working tree substitute\n")
        item["sha256"] = R.digest(mutable)
        dump(self.producer, document)
        with self.assertRaisesRegex(ValueError, "unexpected source path"):
            self.validate()

    def test_changed_fixed_model_cannot_be_blessed_with_new_hash(self):
        target = self.root / R.ROLE_PATHS["phase4_model"]
        target.write_text(target.read_text() + "\n# changed\n")
        with self.assertRaisesRegex(ValueError, "fixed Phase4 identity"):
            self.freeze_producer()

    def test_corrupt_retained_copy_rejected(self):
        self.freeze_producer()
        document = json.loads(self.producer.read_text())
        item = next(p for p in document["files"] if p["role"] == "selector_pine")
        (self.stage / item["snapshot_path"]).write_text("changed retained bytes\n")
        with self.assertRaisesRegex(ValueError, "retained producer snapshot"):
            self.validate()

    def test_actual_relative_import_tree_is_verified(self):
        self.freeze_producer()
        document = json.loads(self.producer.read_text())
        item = next(p for p in document["files"] if p["role"] == "phase3_model")
        destination = self.stage / "unrelated/phase3_model.py"
        destination.parent.mkdir()
        shutil.copyfile(self.stage / item["snapshot_path"], destination)
        item["snapshot_path"] = str(destination.relative_to(self.stage))
        dump(self.producer, document)
        with self.assertRaisesRegex(ValueError, "dependency tree"):
            self.validate()

    def test_extra_configuration_rejected(self):
        settings = self.root / R.ROLE_PATHS["phase5_settings"]
        document = json.loads(settings.read_text())
        document["configurations"].append("P0-new-policy")
        dump(settings, document)
        frozen = json.loads(self.freeze.read_text())
        next(p for p in frozen["frozen_files"] if p["path"] == R.ROLE_PATHS["phase5_settings"])["sha256"] = R.digest(settings)
        dump(self.freeze, frozen)
        with self.assertRaisesRegex(ValueError, "six predeclared"):
            self.freeze_producer()

    def test_future_producer_time_rejected(self):
        self.freeze_producer()
        document = json.loads(self.producer.read_text())
        document["retained_at"] = "2099-01-01T00:00:00+00:00"
        dump(self.producer, document)
        with self.assertRaisesRegex(ValueError, "chronology"):
            self.validate()

    def test_insufficient_history_retained_as_failures_never_complete_maps(self):
        self.freeze_producer()
        result = R.run(self.root, self.input, self.producer, self.output)
        self.assertFalse(result["complete_four_session_batch"])
        batch = json.loads((self.output / "prediction-batch.json").read_text())
        self.assertEqual(len(batch["records"]), 4)
        self.assertFalse(batch["reveal_gate_passed"])
        self.assertTrue(all(not r["complete_expanded_map"] for r in batch["records"]))
        self.assertFalse(batch["development_answers_opened"])

    def test_refuses_overwriting_retained_attempt(self):
        self.freeze_producer()
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "fresh output"):
            R.run(self.root, self.input, self.producer, self.output)

    def test_complete_synthetic_history_retains_all_profiles_and_six_maps(self):
        day = R.DATES[0]
        document = json.loads(self.input.read_text())
        item = next(p for p in document["files"] if p["session_date"] == day)
        path = self.root / item["path"]
        start = MODEL.P3.BASE.local(date(2026, 10, 4), 18, 0)
        cutoff = MODEL.P3.BASE.local(date(2026, 10, 15), 9, 25)
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("time", "open", "high", "low", "close", "Volume"))
            current = start
            while current < cutoff:
                # Fixed futures-clock fixture, not real observed market data.
                weekday, hour = current.weekday(), current.hour
                valid = weekday < 5 and hour != 17 and not (weekday == 4 and hour >= 17)
                valid = valid or weekday == 6 and hour >= 18
                if valid:
                    writer.writerow((current.isoformat(),100,100,100,100,10))
                current += timedelta(minutes=5)
        item["sha256"] = R.digest(path)
        dump(self.input, document)
        self.freeze_producer()
        R.run(self.root, self.input, self.producer, self.output)
        saved = json.loads((self.output / (day + ".json")).read_text())
        self.assertTrue(saved["complete_expanded_map"], saved["incomplete_reasons"])
        self.assertEqual(set(saved["selections"]), set(R.CONFIGURATIONS))
        self.assertEqual(len(saved["expanded_snapshot"]["candidate_ledgers"]),5)
        self.assertTrue(all(p["status"] == "ready" for p in saved["profile_readiness"]))
        self.assertEqual(saved["selector_inputs"]["last_included_open"],day+"T09:20:00-04:00")
        self.assertEqual(saved["selector_inputs"]["last_included_close"],day+"T09:25:00-04:00")
        self.assertFalse(saved["development_answers_opened"])

    def test_imports_only_retained_model_snapshot_paths(self):
        self.freeze_producer()
        loaded = []
        original = R.load_module
        def tracking(name, path):
            loaded.append(path)
            return original(name, path)
        with patch.object(R, "load_module", side_effect=tracking):
            R.run(self.root, self.input, self.producer, self.output)
        self.assertEqual(len(loaded), 3)
        self.assertTrue(all(p.is_relative_to(self.stage) for p in loaded))
        self.assertTrue(any(p.name == "pivot_model.py" for p in loaded))


class BarAndCompletenessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "synthetic.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rows):
        with self.path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("time", "open", "high", "low", "close", "Volume", "ignored"))
            writer.writerows(rows)

    def test_only_completed_terminal_bar_enters_and_native_indicators_ignored(self):
        self.write([("2026-10-15T09:20:00-04:00",100,101,99,100,5,"not a number"),
                    ("2026-10-15T09:25:00-04:00","future-invalid","x","x","x","x","answer")])
        bars, audit = R.read_bars(self.path, R.DATES[0], MODEL)
        self.assertEqual(len(bars), 1)
        self.assertEqual((bars[-1].opened.hour,bars[-1].opened.minute,bars[-1].closed.minute),(9,20,25))
        self.assertEqual(audit["excluded_after_cutoff_rows"],1)
        self.assertEqual(audit["ignored_columns"],["ignored"])

    def test_duplicate_or_descending_included_timestamps_rejected(self):
        row=("2026-10-15T09:20:00-04:00",100,101,99,100,5,"")
        self.write([row,row])
        with self.assertRaisesRegex(ValueError,"strictly increasing"):
            R.read_bars(self.path,R.DATES[0],MODEL)

    def test_unknown_timezone_and_nonfive_minute_bars_rejected(self):
        for stamp in ("2026-10-15T09:20:00","2026-10-15T09:21:00-04:00"):
            with self.subTest(stamp=stamp):
                self.write([(stamp,100,101,99,100,5,"")])
                with self.assertRaises(ValueError):
                    R.read_bars(self.path,R.DATES[0],MODEL)

    def test_later_market_date_is_not_silently_consumed(self):
        self.write([("2026-10-16T09:20:00-04:00",100,101,99,100,5,"")])
        with self.assertRaisesRegex(ValueError,"after the authorized"):
            R.read_bars(self.path,R.DATES[0],MODEL)

    def test_invalid_ohlc_rejected(self):
        self.write([("2026-10-15T09:20:00-04:00",100,99,98,100,5,"")])
        with self.assertRaisesRegex(ValueError,"OHLC"):
            R.read_bars(self.path,R.DATES[0],MODEL)

    def test_missing_optional_family_is_not_complete_expanded_map(self):
        distributions=[SimpleNamespace(window=w) for w in R.WINDOWS]
        ledgers=[{"status":"ready"} for _ in distributions]
        expanded=SimpleNamespace(baseline=SimpleNamespace(values=[100]*19),distributions=distributions,candidate_ledgers=ledgers)
        inputs=SimpleNamespace(reasons=lambda:())
        selections=dict.fromkeys(R.CONFIGURATIONS)
        self.assertEqual(R.complete_map_reasons(expanded,inputs,selections),[])
        ledgers[-1]["status"]="unavailable"
        self.assertIn("required_profile_not_ready",R.complete_map_reasons(expanded,inputs,selections))

    def test_baseline_only_and_missing_boundary_do_not_complete_gate(self):
        expanded=SimpleNamespace(baseline=SimpleNamespace(values=[100]*19),distributions=[],candidate_ledgers=[])
        inputs=SimpleNamespace(reasons=lambda:("MISSING_EXACT_COMPLETED_CUTOFF",))
        reasons=R.complete_map_reasons(expanded,inputs,{"P0-D1":None})
        self.assertIn("five_profile_inventory_missing",reasons)
        self.assertIn("MISSING_EXACT_COMPLETED_CUTOFF",reasons)
        self.assertIn("six_configuration_batch_missing",reasons)


if __name__ == "__main__":
    unittest.main()
