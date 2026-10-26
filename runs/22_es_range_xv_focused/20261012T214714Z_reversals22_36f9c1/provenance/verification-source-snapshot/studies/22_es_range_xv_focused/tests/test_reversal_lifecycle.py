"""Synthetic lifecycle gates; no retained market data or historical runs are read."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "src"))
spec = importlib.util.spec_from_file_location("study22_reversal_lifecycle", STUDY / "reversal_run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def child_result():
    return {"schema_version": 1, "outcome": "passed", "successful_callbacks": 2,
            "counts": {"discovered": 2, "tests_run": 2, "failures": 0, "errors": 0,
                       "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}, "skips": []}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.study = self.root / "studies" / runner.STUDY_ID
        self.study.mkdir(parents=True)
        for name in runner.SOURCE_FILES:
            destination = self.study / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((STUDY / name).read_bytes() if (STUDY / name).exists() else b"# Synthetic reporting source\n")
        for name in ("reversal.yaml", "reversal-plan.md", "notes.md"):
            (self.study / name).write_bytes((STUDY / name).read_bytes())
        (self.root / "uv.lock").write_text("synthetic environment lock\n")
        files = []
        columns = ["source_row", "source_timestamp", "bar_start_timestamp", "bar_completion_timestamp_proxy",
                   "bar_duration_seconds_proxy", "completion_proxy_status", "session_date_proxy", "open", "high", "low", "close"]
        for setting in runner.SETTINGS:
            for role in ("source", "enhanced"):
                path = self.root / "data" / f"{setting}_{role}.csv"
                path.parent.mkdir(parents=True, exist_ok=True)
                if role == "source":
                    path.write_text("Synthetic raw source\n")
                else:
                    with path.open("w", newline="") as stream:
                        writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
                        writer.writeheader()
                        for index, close in enumerate((100, 101, 101, 99, 101, 101, 100), 1):
                            stamp = f"2020-01-02 10:00:0{index}"
                            terminal = index == 7
                            writer.writerow({"source_row": index, "source_timestamp": stamp,
                                "bar_start_timestamp": stamp, "bar_completion_timestamp_proxy": "" if terminal else f"2020-01-02 10:00:0{index+1}",
                                "bar_duration_seconds_proxy": "" if terminal else "1", "completion_proxy_status": "unavailable_export_end" if terminal else "next_bar_start_proxy",
                                "session_date_proxy": "2020-01-02", "open": 100, "high": 101, "low": 99, "close": close})
                files.append({"role": role, "setting_ticks": setting, "root_alias": "publication_root",
                              **runner.record(path, self.root), "rows": 7})
        manifest = self.root / "data/manifest.json"
        manifest.write_text("{}\n")
        clock = self.root / "docs/clock.json"
        clock.parent.mkdir()
        clock.write_text("{}\n")
        lock = {"files": files, "manifests": [{"role": "range_xv_export_manifest", "root_alias": "publication_root", **runner.record(manifest, self.root)}],
                "clock_migration": {"root_alias": "workspace_root", **runner.record(clock, self.root)}}
        save(self.study / "inputs.lock.json", lock)
        self.stage = self.root / "work" / runner.STUDY_ID / "20261012T000000Z_synthetic"
        self.workspace_patch = patch.object(runner, "WORKSPACE", self.root)
        self.study_patch = patch.object(runner, "STUDY_DIRECTORY", self.study)
        self.git_patch = patch.object(runner, "git_identity", return_value={"revision": "synthetic", "dirty": True})
        for replacement in (self.workspace_patch, self.study_patch, self.git_patch):
            replacement.start()
            self.addCleanup(replacement.stop)

    def execute(self):
        return runner.execute(self.stage, self.root, ["synthetic", "execute"])

    def prepare_receipts(self):
        executed = self.execute()
        for setting in runner.SETTINGS:
            for analysis in ("continuation", "retracement"):
                save(self.stage / f"publications/{setting}t-{analysis}/publication.json", {"id": f"chart-{setting}", "source": {"runId": self.stage.name}})
        hashes = executed["artifact_hashes"]
        save(self.stage / "verification.json", {"result": "passed", "artifact_hashes": hashes})
        publication_hashes = {f"publications/{setting}t-{analysis}/publication.json": runner.digest(self.stage / f"publications/{setting}t-{analysis}/publication.json") for setting in runner.SETTINGS for analysis in ("continuation", "retracement")}
        publication_hashes.update({key: value for key, value in hashes.items() if key.startswith("tables/")})
        save(self.stage / "publication-verification.json", {"result": "passed", "artifact_hashes": publication_hashes})
        save(self.stage / "verification/numerical-test-result.json", child_result())
        preseal = {name: runner.digest(self.stage / name) for name in ("verification.json", "publication-verification.json", "verification/numerical-test-result.json")}
        save(self.stage / "preseal-checks.json", {"result": "passed", "artifact_hashes": preseal})

    def test_stage_containment_and_overwrite_refusal_before_input_reads(self):
        for candidate in (self.root / "runs" / runner.STUDY_ID / "bad", self.stage / "nested", self.stage.with_name("bad.name")):
            with self.assertRaisesRegex(ValueError, "direct unique child"):
                runner.stage_path(candidate, existing=False)
        self.stage.mkdir(parents=True)
        with patch.object(runner, "verify_inputs", side_effect=AssertionError("No input read allowed")):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                self.execute()

    def test_execute_freezes_sources_before_market_read_and_streams_complete_tables(self):
        original = runner.verify_inputs
        def inspect_before_input(stage, root):
            self.assertTrue((stage / "provenance/execution-start.json").is_file())
            self.assertFalse((stage / "evidence").exists())
            runner.assert_frozen(stage)
            return original(stage, root)
        with patch.object(runner, "verify_inputs", side_effect=inspect_before_input):
            result = self.execute()
        self.assertEqual(len(result["artifacts"]), 8)
        for name, count in runner.TABLE_ROWS.items():
            with (self.stage / "tables" / name).open(newline="") as stream:
                self.assertEqual(sum(1 for _ in csv.DictReader(stream)), count)
        with (self.stage / "evidence/reversals_4t.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["source_row"] for row in rows], ["4", "5"])
        self.assertEqual([row["prior_exact_length"] for row in rows], ["2", "1"])
        self.assertEqual([row["follow_count"] for row in rows], ["0", "1"])
        self.assertEqual([row["exact_follow_count"] for row in rows], ["0", ""])
        self.assertEqual(rows[-1]["right_censored"], "true")
        self.assertEqual(rows[0]["prior_start_known"], "true")
        self.assertEqual(rows[0]["start_timestamp"], "2020-01-02 10:00:04")

    def test_pinned_input_change_fails_without_statistics_or_completion_receipt(self):
        (self.root / "data/4_source.csv").write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "Pinned input bytes changed"):
            self.execute()
        self.assertTrue((self.stage / "provenance/execution-start.json").exists())
        self.assertFalse((self.stage / "provenance/execution-complete.json").exists())
        self.assertFalse((self.stage / "tables").exists())

    def test_changed_frozen_source_or_table_invalidates_execution(self):
        self.execute()
        runner.verify_artifacts(self.stage)
        (self.study / "src/trends.py").write_text("changed source\n")
        with self.assertRaisesRegex(ValueError, "Frozen execution"):
            runner.verify_artifacts(self.stage)
        (self.study / "src/trends.py").write_bytes((STUDY / "src/trends.py").read_bytes())
        (self.stage / "tables/reversal_summary.csv").write_text("changed table\n")
        with self.assertRaisesRegex(ValueError, "Executed artifact changed"):
            runner.verify_artifacts(self.stage)

    def test_settings_and_prior_cohort_protocol_are_frozen_and_hash_guarded(self):
        self.execute()
        settings = json.loads((self.study / "reversal.yaml").read_text())
        settings["reversal_definition"]["prior_leg_buckets"] = ["all", "3", "unknown_start"]
        save(self.study / "reversal.yaml", settings)
        with self.assertRaisesRegex(ValueError, "Frozen execution"):
            runner.verify_artifacts(self.stage)
        self.assertEqual(json.loads((self.stage / "study.yaml").read_text())["reversal_definition"]["prior_leg_buckets"],
                         ["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11-15", "16-20", "21+", "unknown_start"])

    def test_unsupported_prior_cohorts_and_event_conventions_refused_before_statistics(self):
        source = json.loads((self.study / "reversal.yaml").read_text())
        cases = (("reversal_definition", "prior_leg_buckets", ["all", "3", "unknown_start"]),
                 ("reversal_definition", "prior_leg_membership", "observed length even when start unknown"),
                 ("reversal_definition", "n_excludes_reversal", False),
                 ("reporting", "event_membership_timestamp", "F1.bar_completion_timestamp_proxy"))
        for index, (section, key, value) in enumerate(cases):
            settings = json.loads(json.dumps(source))
            settings[section][key] = value
            save(self.study / "reversal.yaml", settings)
            self.stage = self.stage.with_name(f"20261012T000000Z_unsupported_{index}")
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Unsupported reversal"):
                self.execute()
            self.assertFalse((self.stage / "evidence").exists())
            self.assertFalse((self.stage / "provenance/execution-complete.json").exists())

    def test_numerical_gate_rejects_empty_skipped_failed_and_expected_failure_results(self):
        for field, value in (("tests_run", 0), ("skipped", 1), ("errors", 1), ("failures", 1), ("expected_failures", 1), ("unexpected_successes", 1), ("discovered", 3)):
            result = child_result()
            result["counts"][field] = value
            save(self.stage / "verification/numerical-test-result.json", result)
            with self.subTest(field=field), self.assertRaises(ValueError):
                runner.require_numerical_result(self.stage)
        result = child_result()
        result["successful_callbacks"] = 0
        save(self.stage / "verification/numerical-test-result.json", result)
        with self.assertRaises(ValueError):
            runner.require_numerical_result(self.stage)
        save(self.stage / "verification/numerical-test-result.json", child_result())
        runner.require_numerical_result(self.stage)

    def test_success_flags_without_artifact_binding_are_refused(self):
        save(self.stage / "verification.json", {"result": "passed"})
        with self.assertRaisesRegex(ValueError, "artifact-bound"):
            runner.require_receipt(self.stage, "verification.json", {"tables/summary.csv"})
        (self.stage / "selected.txt").write_text("checked bytes\n")
        save(self.stage / "verification.json", {"result": "passed", "artifact_hashes": {"selected.txt": runner.digest(self.stage / "selected.txt")}})
        (self.stage / "selected.txt").write_text("changed bytes\n")
        with self.assertRaisesRegex(ValueError, "consumed bytes have changed"):
            runner.require_receipt(self.stage, "verification.json", {"selected.txt"})

    def test_seal_refuses_changed_checked_publication_before_relocation(self):
        self.prepare_receipts()
        save(self.stage / "publications/5t-retracement/publication.json", {"id": "changed", "source": {"runId": self.stage.name}})
        with self.assertRaisesRegex(ValueError, "consumed bytes have changed"):
            runner.seal(self.stage, self.root)
        self.assertTrue((self.stage / "evidence/reversals_4t.csv").exists())
        self.assertFalse((self.root / "runs").exists())
        self.assertFalse((self.root / "data/research").exists())

    def test_seal_retains_exact_ledger_bytes_and_immutable_unique_run(self):
        self.prepare_receipts()
        hashes = {setting: runner.digest(self.stage / f"evidence/reversals_{setting}t.csv") for setting in runner.SETTINGS}
        # The sealer's code locator is patched only for this synthetic workspace.
        with patch.object(runner, "__file__", str(self.study / "reversal_run.py")):
            destination = runner.seal(self.stage, self.root, ["synthetic", "seal"])
        self.assertFalse(self.stage.exists())
        events = json.loads((destination / "events.manifest.json").read_text())
        self.assertEqual(len(events["files"]), 3)
        for setting, item in zip(runner.SETTINGS, events["files"]):
            self.assertEqual(item["sha256"], hashes[setting])
            self.assertEqual(runner.digest(self.root / item["path"]), hashes[setting])
            self.assertEqual(item["rows"], 2)
        self.assertFalse((destination / "evidence/reversals_4t.csv").exists())
        self.assertTrue((destination / "manifest.json").exists())
        self.assertTrue((destination / "provenance/sealing.json").exists())
        self.assertTrue((destination / "provenance/source-snapshot/studies" / runner.STUDY_ID / "reversal_run.py").exists())


if __name__ == "__main__":
    unittest.main()
