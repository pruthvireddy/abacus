"""Synthetic saved-summary transfer checks; no market input or research rerun."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
import publish_ranked as p
from src.reporting import read_csv, write_csv, write_json


def fixture():
    rows = []
    for rank in range(1, 21):
        for cohort in ("pivot_matched_rth", "vwap_only_rth", "vwap_only_full_globex"):
            rows.append({"statistic_id": f"S{rank:02d}", "cohort": cohort, "reference": "vwap" if rank == 1 or cohort != "pivot_matched_rth" else "pivot",
                         "series": "ema6", "session_mode": "globex" if cohort.endswith("globex") else "rth",
                         "period_kind": "overall", "period": "all", "section": "all", "direction": "all", "panel": "all_crosses",
                         "horizon": "30m", "condition": "all", "condition_value": "all", "metric": "crosses" if rank == 1 else "movement",
                         "unit": "fraction" if rank in (3, 6, 11, 19) else "points", "estimate": 0.0 if rank == 1 else -.25 if rank == 9 else .5,
                         "median": 0, "numerator": 1, "denominator": 2, "days": 2, "unknown": 0, "censored": 1,
                         "earliest": "2026-09-17", "latest": "2026-09-18", "ci95_low": None, "ci95_high": None})
    expanded = []
    for row in rows:
        if row["statistic_id"] == "S12":
            expanded.extend({**row, "metric": "first_cross_timing", "unit": "fraction", "condition": "minutes_from_session_start",
                             "condition_value": f"{left}–<{left+30}"} for left in range(0, 360, 30))
        else:
            expanded.append(row)
    rows = expanded
    for row in deepcopy(rows):
        if row["statistic_id"] == "S20":
            for kind in ("recent", "earlier"):
                rows.append({**row, "period_kind": kind, "period": "last_20" if kind == "recent" else "before_last_20"})
    return rows


class ProjectionTests(unittest.TestCase):
    def test_fraction_null_zero_and_negative_points_keep_types(self):
        row = fixture()[0]
        zero = p.projected(row)
        self.assertEqual(zero["value"], 0)
        self.assertIsNone(zero["share"])
        fraction = p.projected({**row, "unit": "fraction", "estimate": .42})
        self.assertEqual(fraction["share"], .42)
        self.assertIsNone(fraction["value"])
        missing = p.projected({**row, "estimate": None, "earliest": None, "latest": None})
        self.assertIsNone(missing["value"])
        self.assertEqual(missing["coverage"], "No valid observations")
        self.assertEqual(p.projected({**row, "estimate": -4})["value"], -4)
        self.assertEqual(len(p.PUBLIC_KEYS), 12)

    def test_cohorts_and_inapplicable_questions_stay_separate(self):
        pivot = p.selected_rows(fixture(), "pivot-statistics")
        vwap = p.selected_rows(fixture(), "globex-vwap-statistics")
        self.assertEqual({r["cohort"] for _, r in pivot}, {"pivot_matched_rth"})
        self.assertEqual({r["cohort"] for _, r in vwap}, {"vwap_only_rth", "vwap_only_full_globex"})
        self.assertNotIn("S18", {r["statistic_id"] for _, r in vwap})
        self.assertNotIn("S14", {r["statistic_id"] for _, r in vwap})

    def test_public_calendar_scope_is_authored_without_selecting_estimates(self):
        row = fixture()[0]
        source = [{**row, "period_kind": "calendar_month", "period": f"2025-{month:02d}", "estimate": month} for month in range(1, 13)]
        source.append({**row, "period_kind": "calendar_month", "period": "2026-01", "estimate": -999})
        chosen = p.selected_rows(source, "pivot-statistics")
        self.assertEqual(len(chosen), 12)
        self.assertNotIn("2025-01", {r["period"] for _, r in chosen})
        self.assertIn(-999, {r["estimate"] for _, r in chosen})

    def test_forward_detail_varies_one_axis_only_and_uses_primary_horizon(self):
        row = fixture()[0]
        source = [row, {**row, "direction": 1, "section": "opening_range"},
                  {**row, "direction": 1, "horizon": "15m"}, {**row, "direction": -1},
                  {**row, "period_kind": "year", "period": "2026", "horizon": "60m"}]
        self.assertEqual([i for i, _ in p.selected_rows(source, "pivot-statistics")], [0, 3])

    def test_first_timing_chart_uses_numeric_bins_and_one_primary_population(self):
        rows = fixture()
        template = next(row for row in rows if row["statistic_id"] == "S12" and row["cohort"] == "vwap_only_full_globex")
        source = [{**template, "condition_value": f"{left}–<{left+30}"} for left in range(0, 1380, 30)]
        source += [{**template, "condition_value": "no_cross"},
                   {**template, "cohort": "vwap_only_rth", "session_mode": "rth", "condition_value": "0–<30"}]
        source.sort(key=lambda row: row["condition_value"])
        selected = p._chart_candidates(list(enumerate(source)), "S12")
        self.assertEqual([row["condition_value"] for _, row in selected], [f"{left}–<{left+30}" for left in range(0, 360, 30)])
        self.assertEqual({row["cohort"] for _, row in selected}, {"vwap_only_full_globex"})
        self.assertTrue(all(row["denominator"] == 2 for _, row in selected))
        matched = [(i, {**row, "cohort": "pivot_matched_rth", "session_mode": "rth", "reference": ref}) for i, row in enumerate(source) if row["cohort"] == "vwap_only_full_globex" for ref in ("vwap", "pivot")]
        selected = p._chart_candidates(matched, "S12")
        self.assertEqual({row["reference"] for _, row in selected}, {"pivot"})
        self.assertEqual([row["condition_value"] for _, row in selected], [f"{left}–<{left+30}" for left in range(0, 360, 30)])


class ArtifactTests(unittest.TestCase):
    def build(self, stage):
        write_csv(stage / p.SUMMARY, fixture())
        return p.build(stage, run_id="synthetic_ranked", published_at="2026-10-31T12:00:00Z")

    def test_two_reports_ranked_tables_bounded_filters_and_exact_transfers(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            counts = self.build(stage)
            self.assertEqual(counts["publications"], 2)
            self.assertEqual(counts["checked_assets"], 8)
            self.assertGreater(counts["checked_cells"], 0)
            for directory in (stage / "publications").iterdir():
                report = json.loads((directory / "publication.json").read_text())
                tables = [section for section in report["sections"] if section["kind"] == "table"]
                ids = [section["id"] for section in tables]
                self.assertEqual(ids, sorted(ids))
                self.assertLessEqual(len(report["sections"]), 30)
                for section in tables:
                    self.assertLessEqual(len(section["columns"]), 12)
                    self.assertLessEqual(len(section["rows"]), 1500)
                    self.assertLessEqual(len(section["rowFilters"]), 3)
                    self.assertEqual(next(c for c in section["columns"] if c["key"] == "share")["format"], "percent")
                receipt = json.loads((directory / "publication-verification.json").read_text())
                self.assertEqual(receipt["result"], "passed")
                manifest = json.loads((directory / "publication-manifest.json").read_text())
                self.assertTrue(all(item["path"].startswith("runs/30_verniman_pivot_statistics_es/synthetic_ranked/") for item in manifest["outputs"]))
            with self.assertRaisesRegex(ValueError, "overwrite"):
                p.build(stage, run_id="synthetic_ranked")

    def test_tampered_display_download_and_chart_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            self.build(stage)
            directory = next((stage / "publications").iterdir())
            target = directory / "publication.json"
            report = json.loads(target.read_text())
            table = next(s for s in report["sections"] if s["kind"] == "table")
            table["rows"][0]["denominator"] = 999
            write_json(target, report)
            with self.assertRaisesRegex(ValueError, "source-cell"):
                p.verify(stage, run_id="synthetic_ranked")
            table["rows"][0]["denominator"] = 2
            write_json(target, report)
            p.verify(stage, run_id="synthetic_ranked")
            download = directory / report["downloads"][0]["path"]
            original = download.read_bytes()
            download.write_bytes(original + b"tamper")
            with self.assertRaisesRegex(ValueError, "byte mismatch"):
                p.verify(stage, run_id="synthetic_ranked")
            download.write_bytes(original)
            figure = directory / next(s["path"] for s in report["sections"] if s["kind"] == "figure")
            figure.write_bytes(figure.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "asset mismatch"):
                p.verify(stage, run_id="synthetic_ranked")

    def test_negative_saved_chart_value_is_not_clipped(self):
        svg = p._chart_svg("Signed test", [{"label": "negative", "value": -4, "unit": "points", "denominator": 10, "days": 3, "coverage": "2026-09-17–2026-09-18"}])
        self.assertIn('data-value="-4"', svg)
        self.assertIn("-4.000 points", svg)


if __name__ == "__main__":
    unittest.main()
