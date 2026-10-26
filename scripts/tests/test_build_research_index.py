"""Disposable offline library fixtures; generation never touches real outputs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_navigation_metadata import SCRIPTS, reference_record, strategy_record, study_record, write_file, write_navigation

SPEC = importlib.util.spec_from_file_location("research_index_fixture_builder", SCRIPTS / "build-research-index.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def complete_fixture(root, studies=None, strategies=None):
    studies = [study_record()] if studies is None else studies
    strategies = [strategy_record()] if strategies is None else strategies
    write_navigation(root, studies, strategies)
    write_file(root, "reports/quality/synthetic_quality.md")
    write_file(root, "catalog/datasets/session_anchored_vwap__1.0.0.release.json", "{}")
    write_file(root, "studies/05_session_vwap/inputs.lock.json", "{}")
    write_file(root, "legacy/sahadeva/presentation-exports/RangeXV_All_7_Posters.pdf", "synthetic PDF placeholder")
    write_file(root, "legacy/sahadeva/presentation-exports/RangeXV_Stats_First_Draft.xlsx", "synthetic workbook placeholder")
    for locator in ("templates/README.md", "studies/README.md", "strategies/README.md"):
        write_file(root, locator)
    write_file(root, "templates/library.css", "body { color: black; }\n")
    for run_id in ("run2", "run10"):
        write_file(root, "runs/01_synthetic/" + run_id + "/report.html", "<html>saved fixture</html>")


def snapshot(root):
    return {path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob("*") if path.is_file()}


class ResearchIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        complete_fixture(self.root)

    def command(self, *arguments, optimize=False):
        return subprocess.run([sys.executable] + (["-O"] if optimize else []) + [str(SCRIPTS / "build-research-index.py"), "--root", str(self.root)] + list(arguments), cwd=self.root.parent, text=True, capture_output=True)

    def test_deterministic_markdown_and_html_without_generation_timestamp(self):
        first = BUILDER.build(self.root)
        self.assertEqual(first, BUILDER.build(self.root))
        self.assertEqual(set(first), {"reports/index.md", "reports/index.html"})
        self.assertIn("1 studies · 2 saved runs · 1 strategy cards", first["reports/index.md"])
        self.assertNotIn("Generated at", first["reports/index.html"])

    def test_natural_run_order_and_explicit_reference_are_distinct(self):
        record = study_record(reference_run="run2", latest_exploratory_run="run10")
        write_file(self.root, "studies/01_synthetic/study.json", json.dumps(record))
        outputs = BUILDER.build(self.root)
        markdown = outputs["reports/index.md"]
        self.assertLess(markdown.index("run10 · latest by ID"), markdown.index("run2 · selected reference"))
        self.assertNotIn("run10 · latest by ID · selected reference", markdown)
        self.assertIn("Selected reference", outputs["reports/index.html"])

    def test_run_id_does_not_select_reference(self):
        record = study_record(run_id="run10")
        write_file(self.root, "studies/01_synthetic/study.json", json.dumps(record))
        markdown = BUILDER.build(self.root)["reports/index.md"]
        self.assertIn("run10 · latest by ID", markdown)
        self.assertNotIn("selected reference", markdown)

    def test_indicator_branch_does_not_advertise_completed_research_or_assume_notes(self):
        record = study_record("18_indicator_fixture", content_kind="indicator_implementation", products=[], status="indicator_implementation", summary="An indicator prototype; synthetic adapter/kernel checks only.", evidence_status="No market-data outcomes, TradingView compilation/runtime or profitability established.", implementation={"plan": "plan.md", "settings": "study.yaml", "inputs_lock": "inputs.lock.json", "source": "pine/prototype.pine"})
        write_navigation(self.root, [record], [])
        (self.root / "studies/01_synthetic/study.json").unlink()
        for locator in record["implementation"].values():
            write_file(self.root, "studies/18_indicator_fixture/" + locator)
        outputs = BUILDER.build(self.root)
        for name, content in outputs.items():
            self.assertIn("prototype", content)
            self.assertIn("TradingView", content)
            self.assertIn("pine/prototype.pine", content)
            self.assertNotIn("Candidate strategies", content)
            self.assertNotIn("Browse saved runs and evidence", content)
            self.assertNotIn("notes.md", content)
        self.assertIn(r"indicator\_implementation", outputs["reports/index.md"])

    def test_existing_planned_branch_remains_available(self):
        record = study_record(status="planned")
        write_file(self.root, "studies/01_synthetic/study.json", json.dumps(record))
        for locator in ("plan.md", "study.yaml", "inputs.lock.json", "notes.md"):
            write_file(self.root, "studies/01_synthetic/" + locator)
        outputs = BUILDER.build(self.root)
        self.assertIn("No computed strategy outcomes", outputs["reports/index.md"])
        self.assertIn("Candidate strategies", outputs["reports/index.html"])

    def test_html_markdown_and_url_escaping(self):
        title = '<script>"[bad](*text*) & `tick`'
        record = study_record(title=title)
        card = strategy_record(title=title, path="strategies/card [space].md")
        write_navigation(self.root, [record], [card])
        outputs = BUILDER.build(self.root)
        self.assertIn("&lt;script&gt;", outputs["reports/index.html"])
        self.assertNotIn("<script>", outputs["reports/index.html"])
        self.assertIn(r"\<script\>", outputs["reports/index.md"])
        self.assertIn(r"\[bad\]\(\*text\*\)", outputs["reports/index.md"])
        self.assertIn("card%20%5Bspace%5D.md", outputs["reports/index.html"])
        self.assertIn("card%20%5Bspace%5D.md", outputs["reports/index.md"])

    def test_reference_links_display_authored_selectors_and_columns_without_values(self):
        reference = reference_record(label='Selected [row] <safe>', where={"metric_id": "primary", "blank": ""})
        card = strategy_record(evidence_refs=[reference])
        write_navigation(self.root, [study_record()], [card])
        write_file(self.root, "runs/01_synthetic/run2/tables/scores.csv", "artifact bytes are not CSV and the hash is deliberately wrong")
        with patch.object(Path, "read_bytes", side_effect=AssertionError("builder must not verify saved artifact bytes")):
            outputs = BUILDER.build(self.root)
        self.assertIn("tables/scores.csv", outputs["reports/index.html"])
        self.assertIn(r"metric\_id='primary'", outputs["reports/index.md"])
        self.assertIn("blank=''", outputs["reports/index.md"])
        self.assertIn("columns: events, value", outputs["reports/index.md"])
        self.assertNotIn("artifact bytes are not CSV", outputs["reports/index.html"])

    def test_historical_links_remain_and_exports_are_not_recursively_discovered(self):
        write_file(self.root, "reports/exports/01_synthetic/run2/revision/private.html", "not automatically indexed")
        outputs = BUILDER.build(self.root)
        self.assertIn("RangeXV_All_7_Posters.pdf", outputs["reports/index.html"])
        self.assertIn("Exact source-run attribution remains unresolved", outputs["reports/index.md"])
        self.assertNotIn("private.html", outputs["reports/index.html"])

    def test_cli_root_independent_of_cwd_and_check_makes_no_writes(self):
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr)
        before = snapshot(self.root)
        result = self.command("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(self.root), before)
        write_file(self.root, "reports/index.md", "stale output")
        before = snapshot(self.root)
        result = self.command("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Out of date", result.stdout)
        self.assertEqual(snapshot(self.root), before)

    def test_invalid_metadata_never_overwrites_existing_outputs(self):
        for name in ("reports/index.md", "reports/index.html"):
            write_file(self.root, name, "preserve generated baseline\n")
        write_file(self.root, "strategies/index.json", '{"strategies": [], "strategies": []}')
        before = snapshot(self.root)
        for optimize in (False, True):
            result = self.command(optimize=optimize)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("duplicate", result.stderr.lower())
            self.assertEqual(snapshot(self.root), before)

    def test_non_utf8_metadata_never_truncates_either_output_ordinary_or_optimized(self):
        for name in ("reports/index.md", "reports/index.html"):
            write_file(self.root, name, "preserve generated baseline\n")
        record = study_record(title="bad " + chr(0xd800))
        write_file(self.root, "studies/01_synthetic/study.json", json.dumps(record))
        before = snapshot(self.root)
        for optimize in (False, True):
            result = self.command(optimize=optimize)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("title: expected UTF-8", result.stderr)
            self.assertEqual(snapshot(self.root), before)

    def test_output_encoding_is_preflighted_before_either_file_is_opened(self):
        for name in ("reports/index.md", "reports/index.html"):
            write_file(self.root, name, "preserve generated baseline\n")
        before = snapshot(self.root)
        # This also protects output assembled from future fields or templates.
        with patch.object(BUILDER, "build", return_value={"reports/index.html": "valid output", "reports/index.md": "bad " + chr(0xd800)}), patch.object(sys, "argv", ["build-research-index.py", "--root", str(self.root)]), patch.object(sys, "stderr"):
            self.assertEqual(BUILDER.main(), 1)
        self.assertEqual(snapshot(self.root), before)

    def test_missing_target_gives_useful_error_without_output_writes(self):
        (self.root / "strategies/synthetic_card.md").unlink()
        before = snapshot(self.root)
        result = self.command()
        self.assertEqual(result.returncode, 1)
        self.assertIn("strategy synthetic_card.path", result.stderr)
        self.assertEqual(snapshot(self.root), before)

    def test_symlinked_artifact_and_output_are_rejected(self):
        artifact = self.root / "runs/01_synthetic/run2/report.html"
        source = write_file(self.root, "other.html", "saved fixture")
        artifact.unlink()
        artifact.symlink_to(source)
        result = self.command()
        self.assertEqual(result.returncode, 1)
        self.assertIn("symlink", result.stderr.lower())
        artifact.unlink()
        artifact.write_text("saved fixture", encoding="utf-8")
        (self.root / "reports/index.html").symlink_to(source)
        before = snapshot(self.root)
        result = self.command()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(snapshot(self.root), before)


if __name__ == "__main__":
    unittest.main()
