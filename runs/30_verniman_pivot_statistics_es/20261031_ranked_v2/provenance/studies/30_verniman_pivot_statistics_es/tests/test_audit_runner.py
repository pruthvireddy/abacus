"""Phase 1 retained-stage guards using tiny synthetic source records only."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


STUDY = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_module("study30_audit_runner", STUDY / "run.py")
sources = load_module("study30_runner_source_fixture", STUDY / "src" / "source_audit.py")
requirements = load_module("study30_runner_requirements_fixture", STUDY / "src" / "data_requirements.py")


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fixture(stage):
    """Build exactly the same artifact projections from synthetic metadata."""
    stage.mkdir()
    parent = {"outlook_id": "synthetic-a", "source_revision_id": "synthetic-r1",
              "session_date": "2020-01-09", "contract": "ESH20", "product": "ES",
              "extraction_status": "complete", "content_kind": "daily_outlook",
              "evidence_basis": "captured_source", "available_at": None,
              "timing_status": "historical_availability_unverified",
              "session_date_method": "body_month_day_with_qualified_context"}
    levels = [{"outlook_id": "synthetic-a", "session_date": "2020-01-09",
               "contract": "ESH20", "role": "trigger", "side": side,
               "price_low": "10", "price_high": "10",
               "trigger_interpretation": "conditional_threshold"}
              for side in ("bullish", "bearish")]
    source = sources.audit_sources(outlooks=[parent], levels=levels, issues=[],
                                   coverage=[{"session_date": "2020-01-09", "status": "post_captured"}],
                                   start_date="2020-01-08", end_date="2020-01-10")
    retained = {"sessions": []}
    needed = requirements.build_contract_windows(
        [{"candidate_id": "synthetic-a", "session_date": "2020-01-09", "full_contract": "ESH2020"}],
        retained)
    payloads = {"source-audit.json": source, "retained-coverage.json": retained,
                "data-requirements.json": needed,
                "costing.json": {"status": "not_quoted", "estimated_cost_usd": None,
                                 "paid_order_authorized": False, "approved_max_cost_usd": None}}
    for name, payload in payloads.items():
        write_json(stage / name, payload)
    csvs = {"source-audit.csv": source["outlook_audit"],
            "calendar-audit.csv": source["calendar_audit"],
            "observation-audit.csv": source["observation_audit"],
            "observation-level-audit.csv": source["observation_level_audit"],
            "candidate-requirements.csv": needed["candidate_requirements"]}
    for name, rows in csvs.items():
        (stage / name).write_bytes(runner.csv_bytes(rows))
    retained_source = stage / "provenance" / "synthetic-source.py"
    retained_source.parent.mkdir()
    retained_source.write_text("# Synthetic retained source; no market data.\n")
    manifest = {
        "schema_version": "abacus.study30.phase1-inventory/v1", "study_id": runner.STUDY_ID,
        "run_id": "synthetic", "phase": "source_and_input_identity_inventory",
        "requested_interval": {"start_date": "2020-01-08", "end_date": "2020-01-10",
                               "end_inclusive": True, "end_exclusive": "2020-01-11"},
        "artifacts": [{"path": path.relative_to(stage).as_posix(), "sha256": runner.sha256(path),
                       "bytes": path.stat().st_size} for path in sorted(stage.rglob("*")) if path.is_file()],
        "sources": [{"path": "synthetic-source.py", "retained_path": "provenance/synthetic-source.py",
                     "sha256": runner.sha256(retained_source), "bytes": retained_source.stat().st_size}],
        "market_outcomes_computed": False, "features_published": False,
        "paid_requests_submitted": False, "sealed_research_run": False,
    }
    write_json(stage / "audit-manifest.json", manifest)
    return source, needed


def refresh(stage, *names):
    """Rehash modified test artifacts to exercise semantic reconciliation."""
    manifest = read_json(stage / "audit-manifest.json")
    for record in manifest["artifacts"]:
        if record["path"] in names:
            path = stage / record["path"]
            record.update(sha256=runner.sha256(path), bytes=path.stat().st_size)
    write_json(stage / "audit-manifest.json", manifest)


def save_source(stage, source):
    write_json(stage / "source-audit.json", source)
    (stage / "source-audit.csv").write_bytes(runner.csv_bytes(source["outlook_audit"]))
    (stage / "calendar-audit.csv").write_bytes(runner.csv_bytes(source["calendar_audit"]))
    refresh(stage, "source-audit.json", "source-audit.csv", "calendar-audit.csv")


def save_requirements(stage, needed):
    write_json(stage / "data-requirements.json", needed)
    (stage / "candidate-requirements.csv").write_bytes(runner.csv_bytes(needed["candidate_requirements"]))
    refresh(stage, "data-requirements.json", "candidate-requirements.csv")


class StagePathTests(unittest.TestCase):
    def test_safe_fresh_run_id_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            stage = runner.stage_for_run("20261031T000000Z_phase1", workspace)
            self.assertEqual(stage, workspace.resolve() / "work" / runner.STUDY_ID / "20261031T000000Z_phase1")
            self.assertFalse((workspace / "work").exists())

    def test_unsafe_ids_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            for value in ["", "../other", "/tmp/other", "a/b", "a b", ".", "a" * 102]:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    runner.stage_for_run(value, Path(temporary))

    def test_existing_stage_and_escaping_parent_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            workspace.mkdir()
            stage = workspace / "work" / runner.STUDY_ID / "existing"
            stage.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                runner.stage_for_run("existing", workspace)
            outside = Path(temporary) / "outside"
            outside.mkdir()
            stage.parent.rename(stage.parent.with_name("saved"))
            stage.parent.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                runner.stage_for_run("fresh", workspace)

    def test_work_root_symlink_cannot_redirect_stage_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            outside = Path(temporary) / "outside"
            workspace.mkdir()
            outside.mkdir()
            (workspace / "work").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                runner.stage_for_run("fresh", workspace)
            self.assertEqual(list(outside.iterdir()), [])


class AuditVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.stage = Path(self.temporary.name) / "synthetic"
        self.source, self.needed = fixture(self.stage)

    def test_synthetic_inventory_passes_without_any_market_reads(self):
        result = runner.verify_audit(self.stage)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["data_candidates_accounted"], 1)
        self.assertEqual(result["calendar_dates_accounted"], 3)

    def test_changed_artifact_bytes_refused(self):
        with (self.stage / "source-audit.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ValueError, "artifact mismatch"):
            runner.verify_audit(self.stage)

    def test_unsafe_or_duplicate_artifact_names_refused(self):
        path = self.stage / "audit-manifest.json"
        original = read_json(path)
        for record in [{"path": "../outside", "bytes": 0, "sha256": "0" * 64},
                       {"path": "/tmp/outside", "bytes": 0, "sha256": "0" * 64},
                       original["artifacts"][0]]:
            with self.subTest(record=record):
                manifest = {**original, "artifacts": [*original["artifacts"], record]}
                write_json(path, manifest)
                with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                    runner.verify_audit(self.stage)

    def test_required_artifact_omission_refused(self):
        path = self.stage / "audit-manifest.json"
        manifest = read_json(path)
        manifest["artifacts"] = [record for record in manifest["artifacts"] if record["path"] != "costing.json"]
        write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "incomplete audit artifact"):
            runner.verify_audit(self.stage)

    def test_retained_source_digest_mismatch_refused(self):
        path = self.stage / "audit-manifest.json"
        manifest = read_json(path)
        manifest["sources"][0]["sha256"] = "0" * 64
        write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "retained audit source mismatch"):
            runner.verify_audit(self.stage)

    def test_csv_projection_mismatch_refused_even_with_updated_checksum(self):
        (self.stage / "calendar-audit.csv").write_text("wrong,projection\n")
        refresh(self.stage, "calendar-audit.csv")
        with self.assertRaisesRegex(ValueError, "projection mismatch"):
            runner.verify_audit(self.stage)

    def test_canonical_source_count_mismatch_refused(self):
        self.source["summary"]["canonical_outlook_rows_input"] += 1
        save_source(self.stage, self.source)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_same_length_shifted_calendar_cannot_pass(self):
        self.source["calendar_audit"][0]["session_date"] = "2020-01-07"
        save_source(self.stage, self.source)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_manifest_and_source_requested_intervals_must_agree(self):
        path = self.stage / "audit-manifest.json"
        manifest = read_json(path)
        manifest["requested_interval"]["start_date"] = "2019-01-01"
        write_json(path, manifest)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_reported_accounted_summary_cannot_disagree_with_rows(self):
        self.source["summary"]["canonical_outlook_rows_accounted"] += 1
        save_source(self.stage, self.source)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_calendar_records_reconcile_source_ids_counts_and_observations(self):
        original = deepcopy(self.source)
        changes = [("canonical_outlook_ids", ["unknown-source"]),
                   ("canonical_outlook_count", 2),
                   ("duplicate_date", True), ("user_observation_count", 1)]
        for key, value in changes:
            with self.subTest(key=key):
                modified = deepcopy(original)
                modified["calendar_audit"][1][key] = value
                save_source(self.stage, modified)
                with self.assertRaises(ValueError):
                    runner.verify_audit(self.stage)

    def test_phase1_cannot_promote_source_timing_even_with_matching_summary(self):
        self.source["outlook_audit"][0]["point_in_time_eligible"] = True
        self.source["summary"]["point_in_time_eligible_outlooks"] = 1
        save_source(self.stage, self.source)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_requirements_summary_cannot_disagree_with_candidates(self):
        self.needed["summary"]["candidates"] += 1
        save_requirements(self.stage, self.needed)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_request_identity_must_match_source_candidate(self):
        self.needed["candidate_requirements"][0]["full_contract"] = "ESM2020"
        save_requirements(self.stage, self.needed)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_candidate_omission_refused(self):
        self.needed["candidate_requirements"] = []
        save_requirements(self.stage, self.needed)
        with self.assertRaises(ValueError):
            runner.verify_audit(self.stage)

    def test_phase1_outcome_acquisition_feature_and_sealing_flags_refused(self):
        path = self.stage / "audit-manifest.json"
        original = read_json(path)
        for flag in ["market_outcomes_computed", "paid_requests_submitted", "features_published", "sealed_research_run"]:
            with self.subTest(flag=flag):
                manifest = {**original, flag: True}
                write_json(path, manifest)
                with self.assertRaises(ValueError):
                    runner.verify_audit(self.stage)


if __name__ == "__main__":
    unittest.main()
