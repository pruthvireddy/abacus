"""Independent reconstruction detects mutated synthetic ledgers."""
import csv
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine import fixture
from src.engine import candidates, simulate
from src.reporting import summarize
from src.verification import reference_candidates, reference_outcome, verify_publication, verify_stage


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["date"]
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()})


def make_stage(path):
    session = fixture()
    no_signal = fixture(day="2025-06-03")
    for bar in no_signal["bars5"]:
        bar.update(open=98., close=98., low=97.75, high=98.25)
    sessions = [session, no_signal]
    with gzip.open(path / "sessions.json.gz", "wt") as stream:
        json.dump(sessions, stream, default=lambda value: value.isoformat())
    daily, candidate_rows = [], []
    for s in sessions:
        formed, _ = candidates(s)
        candidate_rows.extend(formed)
        for entry in ("early", "confirmed"):
            for mask in "ABCD":
                for exit_policy in ("fixed_2r", "verne"):
                    row = simulate(s, formed[0] if formed else None, entry, mask, exit_policy)
                    row["split"] = "validation"
                    daily.append(row)
    write_csv(path / "trades.csv", [row for row in daily if row["trade"]])
    # Daily can acquire columns present only on cancelled/unfilled rows. The
    # trade-only CSV omits those columns; an absent field equals a blank null.
    daily[-1]["invalidation_time"] = None
    write_csv(path / "daily.csv", daily)
    write_csv(path / "candidates.csv", candidate_rows)
    write_csv(path / "coverage.csv", [])
    write_csv(path / "waterfall.csv", [])
    summarize(path)


def mutate_csv(path, column, value, row_number=0):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[row_number][column] = value
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def publication_fixture(path):
    (path / "tables").mkdir()
    (path / "downloads").mkdir()
    source = "tables/summary.csv"
    download = "downloads/summary.csv"
    write_csv(path / source, [{"label": "all", "net": 12.5}])
    write_csv(path / download, [{"net": 12.5}])
    pin = lambda name: hashlib.sha256((path / name).read_bytes()).hexdigest()
    provenance = dict(runId="fixture", artifact=source, sha256=pin(source))
    publication = dict(id="fixture-report", source=dict(runId="fixture"),
                       sections=[dict(id="summary", kind="table", rows=[dict(label="all", net=12.5)])],
                       downloads=[dict(path=download, sha256=pin(download), source=provenance,
                                       columns=["net"], rowCount=1)], references=[])
    source_map = dict(publication_id="fixture-report", source_run_id="fixture",
                      sources=[dict(artifact=source, sha256=pin(source))],
                      bindings=[dict(section="summary", row=0, column=key, source_artifact=source,
                                     source_row=0, source_column=key, value=value)
                                for key, value in (("label", "all"), ("net", 12.5))],
                      download_projections=[dict(path=download, source=provenance, columns=["net"])])
    (path / "publication.json").write_text(json.dumps(publication))
    (path / "source-map.json").write_text(json.dumps(source_map))


class VerificationTests(unittest.TestCase):
    def test_scalar_reconstruction_mirrors_long_and_short(self):
        for direction in ("long", "short"):
            session = fixture(direction)
            expected = reference_candidates(session)
            actual, _ = candidates(session)
            self.assertEqual(expected[0]["candidate_id"], actual[0]["candidate_id"])
            self.assertEqual(expected[0]["stop_price"], actual[0]["stop_price"])
            for entry in ("early", "confirmed"):
                outcome = reference_outcome(session, expected[0], entry, "A", "fixed_2r")
                actual_outcome = simulate(session, actual[0], entry)
                for key in outcome:
                    self.assertEqual(outcome[key], actual_outcome[key], key)

    def test_complete_synthetic_stage_reconciles(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            receipt = verify_stage(path)
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["checks"]["independently_reconstructed_daily_outcomes"], 32)
            self.assertTrue((path / "scientific-verification.json").exists())

    def test_changed_fill_or_cost_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            mutate_csv(path / "daily.csv", "net_dollars", "42")
            with self.assertRaisesRegex(ValueError, "net_dollars"):
                verify_stage(path)

    def test_changed_candidate_stop_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            mutate_csv(path / "candidates.csv", "stop_price", "999")
            with self.assertRaisesRegex(ValueError, "candidate stop_price"):
                verify_stage(path)

    def test_missing_data_cannot_be_relabelled_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            # First variant is fixed2R; second is unavailable Verne target.
            mutate_csv(path / "daily.csv", "net_dollars", "0", row_number=1)
            with self.assertRaisesRegex(ValueError, "expected undefined"):
                verify_stage(path)

    def test_changed_summary_point_estimate_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            mutate_csv(path / "tables/variant_summary.csv", "expectancy_r", "99")
            with self.assertRaisesRegex(ValueError, "expectancy_r"):
                verify_stage(path)

    def test_secondary_holm_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            mutate_csv(path / "tables/secondary_comparisons.csv", "holm_tail_probability", ".123")
            with self.assertRaisesRegex(ValueError, "Holm"):
                verify_stage(path)

    def test_cut_population_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            make_stage(path)
            mutate_csv(path / "tables/prespecified_cuts.csv", "trades", "999")
            with self.assertRaisesRegex(ValueError, "Cut"):
                verify_stage(path)

    def test_publication_uses_actual_source_cells(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            publication_fixture(path)
            receipt = verify_publication(path)
            self.assertEqual(receipt["checks"]["actual_saved_table_cells"], 2)
            self.assertEqual(receipt["checks"]["actual_saved_download_cells"], 1)
            publication = json.loads((path / "publication.json").read_text())
            source_map = json.loads((path / "source-map.json").read_text())
            publication["sections"][0]["rows"][0]["net"] = 999
            source_map["bindings"][1]["value"] = 999
            (path / "publication.json").write_text(json.dumps(publication))
            (path / "source-map.json").write_text(json.dumps(source_map))
            with self.assertRaisesRegex(ValueError, "actual saved cell"):
                verify_publication(path)

    def test_download_mutation_cannot_be_hidden_by_updating_its_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            publication_fixture(path)
            mutate_csv(path / "downloads/summary.csv", "net", "999")
            publication = json.loads((path / "publication.json").read_text())
            publication["downloads"][0]["sha256"] = hashlib.sha256((path / "downloads/summary.csv").read_bytes()).hexdigest()
            (path / "publication.json").write_text(json.dumps(publication))
            with self.assertRaisesRegex(ValueError, "actual source-cell projection"):
                verify_publication(path)

    def test_changed_saved_source_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            publication_fixture(path)
            mutate_csv(path / "tables/summary.csv", "net", "999")
            with self.assertRaisesRegex(ValueError, "source hash differs"):
                verify_publication(path)


if __name__ == "__main__":
    unittest.main()
