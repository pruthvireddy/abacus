"""Independent small-number aggregation and saved-publication checks."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
spec = importlib.util.spec_from_file_location("pivot30_reporting", STUDY / "src/reporting.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
webspec = importlib.util.spec_from_file_location("pivot30_web", STUDY / "publish_web.py")
w = importlib.util.module_from_spec(webspec)
webspec.loader.exec_module(w)


def fixture():
    days = ["2026-09-17", "2026-09-18"]
    result = {key: [] for key in ("daily", "sections", "snapshots", "price_events", "ema_events", "outcomes")}
    for i, day in enumerate(days):
        result["daily"].append({"session_date": day, "price_crosses": 2 if i == 0 else 0,
                                "ema_crosses": 1 if i == 0 else 0, "touch_bars": 3 if i == 0 else 0,
                                "opening_gap_points": None if i == 0 else 0})
        for section in r.SECTIONS:
            result["sections"].append({"session_date": day, "section": section,
                                       "price_crosses": 2 if i == 0 and section == "opening_range" else 0,
                                       "ema_crosses": 1 if i == 0 and section == "opening_range" else 0,
                                       "touch_bars": 3 if i == 0 and section == "opening_range" else 0,
                                       "end_price_side_relative_pivot": 1, "end_cloud_order": "bullish"})
        for snapshot in ("0925", "0930"):
            result["snapshots"].append({"session_date": day, "snapshot_label": snapshot,
                                        "cloud_order": "bullish", "price_cloud_location": "above",
                                        "pivot_cloud_location": "inside", "price_side_relative_pivot": 1,
                                        "ema6_side_relative_pivot": 1, "vwap_side_relative_pivot": 0})
    for i, value in enumerate((10., -4.)):
        event = {"event_id": f"event-{i}", "session_date": days[0], "direction": 1 if i == 0 else -1,
                 "section": "opening_range", "first_per_day": i == 0, "first_per_section": i == 0,
                 "reference_price": 5000., "ema_state_at_cross": "already_aligned" if i == 0 else "opposite",
                 "confirmation_kind": None if i == 0 else "delayed", "confirmation_at": None if i == 0 else "2026-09-17T10:00:00-04:00",
                 "confirmation_lag_minutes": None if i == 0 else 6., "returned_at": "2026-09-17T10:03:00-04:00" if i == 0 else None,
                 "return_censored": i == 1, "episode_penetration_points": 12. if i == 0 else 7.,
                 "episode_duration_minutes": 12. if i == 0 else 300., "cloud_order": "bullish",
                 "price_cloud_location": "above", "pivot_cloud_location": "inside",
                 "vwap_side_relative_pivot": 1, "price_side_relative_vwap": 1, "ema6_slope_15m": 2.,
                 "ema_raw_side": 1, "ema20_slope_15m": 2., "ema50_slope_15m": 1.}
        result["price_events"].append(event)
        for horizon in r.HORIZONS:
            outcome = {**event, "event_type": "price_cross", "horizon": horizon,
                       "valid": True, "unknown_reason": None, "displacement_points": value,
                       "favorable_excursion_points": max(value, 0) + 2,
                       "adverse_excursion_points": max(-value, 0) + 1, "elapsed_minutes": 30.}
            for side in ("favorable", "adverse"):
                for threshold in (5, 10, 20):
                    outcome[f"{side}_reach_{threshold}"] = outcome[f"{side}_excursion_points"] >= threshold
            result["outcomes"].append(outcome)
    result["ema_events"] = [{"event_id": "ema-1", "session_date": days[0], "direction": 1,
                              "section": "opening_range", "first_per_day": True, "first_per_section": True,
                              "retest_found": True, "retest_window_complete": True,
                              "time_to_retest_minutes": 6., "retest_close_classification": "hold"},
                             {"event_id": "ema-2", "session_date": days[0], "direction": -1,
                              "section": "new_york_pm", "first_per_day": False, "first_per_section": True,
                              "retest_found": None, "retest_window_complete": False,
                              "time_to_retest_minutes": None, "retest_close_classification": None}]
    return result


def selected(rows, **wanted):
    return [row for row in rows if all(row.get(key) == value for key, value in wanted.items())]


class NumericalTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.tables = r.summarize(self.data, bootstrap_replicates=20)

    def test_zero_day_and_empty_month_have_different_meanings(self):
        overall = selected(self.tables["daily_summary"], period_kind="overall", section="all", metric="price_crosses")[0]
        self.assertEqual((overall["denominator"], overall["estimate"], overall["zero_share"]), (2, 1, .5))
        absent = selected(self.tables["daily_summary"], period_kind="calendar_month", period="2026-10", section="all", metric="price_crosses")[0]
        self.assertEqual(absent["denominator"], 0)
        self.assertIsNone(absent["estimate"])
        self.assertIsNone(absent["zero_share"])

    def test_unknown_metric_is_not_observed_zero(self):
        gap = selected(self.tables["daily_summary"], period_kind="overall", section="all", metric="opening_gap_points")[0]
        self.assertEqual((gap["denominator"], gap["unknown"], gap["estimate"]), (1, 1, 0))

    def test_observed_hour_rate_retains_zero_and_missing_exposure(self):
        data = deepcopy(self.data)
        data["daily"][0].update(price_crosses_per_hour=2 / 6.5, ema_crosses_per_hour=None)
        data["daily"][1].update(price_crosses_per_hour=0., ema_crosses_per_hour=0.)
        rows = r.summarize(data, bootstrap_replicates=0)["daily_summary"]
        price = selected(rows, period_kind="overall", section="all", metric="price_crosses_per_hour")[0]
        self.assertAlmostEqual(price["estimate"], 1 / 6.5)
        self.assertEqual((price["denominator"], price["zero_count"]), (2, 1))
        ema = selected(rows, period_kind="overall", section="all", metric="ema_crosses_per_hour")[0]
        self.assertEqual((ema["denominator"], ema["unknown"], ema["estimate"]), (1, 1, 0))

    def test_event_mean_and_distinct_days_are_not_day_mean(self):
        row = selected(self.tables["outcome_summary"], period_kind="overall", event_type="price_cross", panel="all_crosses", section="all", direction="all", condition="all", horizon="30m")[0]
        self.assertEqual((row["events"], row["denominator"], row["valid_days"]), (2, 2, 1))
        self.assertEqual(row["mean_points"], 3)
        self.assertEqual(row["positive_rate"], .5)
        self.assertEqual(row["mean_bps"], 6)
        first = selected(self.tables["outcome_summary"], period_kind="overall", event_type="price_cross", panel="first_per_day", section="all", direction="all", condition="all", horizon="30m")[0]
        self.assertEqual((first["denominator"], first["mean_points"]), (1, 10))

    def test_invalid_horizon_retains_unknown_and_has_no_return(self):
        data = deepcopy(self.data)
        for row in data["outcomes"]:
            if row["event_id"] == "event-1" and row["horizon"] == "30m":
                row.update(valid=False, displacement_points=None)
        rows = r.summarize(data, bootstrap_replicates=0)["outcome_summary"]
        row = selected(rows, period_kind="overall", event_type="price_cross", panel="all_crosses", section="all", direction="all", condition="all", horizon="30m")[0]
        self.assertEqual((row["denominator"], row["unknown"], row["mean_points"]), (1, 1, 10))

    def test_returned_without_new_cross_and_censored_are_not_merged(self):
        row = selected(self.tables["episode_summary"], period_kind="overall", panel="all_crosses", section="all", direction="all", condition="all")[0]
        self.assertEqual((row["returned_without_new_cross"], row["actual_confirmed"], row["return_censored"]), (1, 1, 1))
        states = selected(self.tables["episode_summary"], period_kind="overall", panel="all_crosses", condition="ema_state_at_cross")
        self.assertEqual({r["condition_value"] for r in states}, {"already_aligned", "opposite"})
        primary = selected(self.tables["episode_summary"], period_kind="overall", panel="all_crosses", condition="initial_confirmation_state", condition_value="initially_unconfirmed")[0]
        self.assertEqual((primary["events"], primary["returned_without_new_cross"], primary["actual_confirmed"]), (1, 0, 1))

    def test_alignment_combinations_do_not_rename_alignment_as_crossing(self):
        row = r.attach_context(self.data)[0]
        self.assertTrue(row["ema_cloud_aligned"])
        self.assertTrue(row["ema_vwap_aligned"])
        self.assertTrue(row["ema_cloud_vwap_aligned"])
        self.assertFalse(row["actual_ema_cross_at_reference"])
        data = deepcopy(self.data)
        data["outcomes"][0]["ema20_slope_15m"] = None
        unknown = r.attach_context(data)[0]
        self.assertIsNone(unknown["ema_cloud_aligned"])
        self.assertIsNone(unknown["ema_cloud_vwap_aligned"])
        self.assertTrue(unknown["ema_vwap_aligned"])

    def test_retest_incidence_excludes_short_window_but_keeps_censor_count(self):
        row = selected(self.tables["retest_summary"], period_kind="overall", section="all", direction="all")[0]
        self.assertEqual((row["events"], row["complete_windows"], row["censored"], row["touch_rate"]), (2, 1, 1, 1))
        self.assertEqual(row["hold_rate"], 1)

    def test_recent_windows_anchor_requested_cutoff_but_reveal_older_data(self):
        row = selected(self.tables["daily_summary"], period_kind="recent", period="last_20", section="all", metric="price_crosses")[0]
        self.assertEqual(row["requested_cutoff"], "2026-10-30")
        self.assertEqual(row["latest_session"], "2026-09-18")
        self.assertEqual(row["days"], 2)

    def test_moving_block_weights_preserve_whole_days_and_seed(self):
        days = [f"2026-01-{n:02d}" for n in range(1, 12)]
        a = r.block_weights(days, 50)
        np.testing.assert_array_equal(a.sum(axis=1), np.full(50, 11))
        np.testing.assert_array_equal(a, r.block_weights(days, 50))
        self.assertTrue(np.all(a >= 0))
        self.assertTrue(np.all(a == np.floor(a)))

    def test_duplicate_daily_rows_fail(self):
        self.data["daily"].append(dict(self.data["daily"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            r.summarize(self.data, bootstrap_replicates=0)

    def test_crossing_snapshots_do_not_change_scheduled_statistics(self):
        changed = deepcopy(self.data)
        changed["snapshots"].append({**changed["snapshots"][0], "snapshot_label": "crossing",
                                      "cloud_order": "bearish", "cloud_width": 999,
                                      "price_minus_pivot": -999, "pivot": 5000})
        self.assertEqual(self.tables, r.summarize(changed, bootstrap_replicates=20))


class ArtifactTests(unittest.TestCase):
    def test_saved_chart_preserves_negative_values_and_source_asset_transfer(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            r.write_statistics(stage, fixture(), bootstrap_replicates=10)
            before = {p.name: r.sha(p) for p in (stage / "tables").glob("*.csv")}
            rendered = r.render(stage)
            self.assertEqual(rendered["figures"], ["figures/price-ema-30m.png"])
            figure = stage / "figures/price-ema-30m.png"
            self.assertEqual(figure.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            inputs = json.loads((stage / "figures/price-ema-30m-inputs.json").read_text())
            saved = r.read_csv(stage / inputs["artifact"])
            self.assertEqual(inputs["rows"], [saved[i] for i in inputs["source_rows"]])
            self.assertIn(-4., [row["mean_points"] for row in inputs["rows"]])
            receipt = json.loads((stage / "figures/price-ema-30m-render.json").read_text())
            self.assertEqual(receipt["png_sha256"], r.sha(figure))
            if receipt["renderer"] == "sharp-svg":
                svg = (stage / "figures/price-ema-30m.svg").read_text()
                self.assertIn('data-mean="-4"', svg)
                self.assertIn('-4.00 points', svg)
                self.assertIn('2026-09-18', svg)
                self.assertIn('2026-10-30', svg)
                self.assertIn("sharp", receipt["versions"])
                self.assertIn("rsvg", receipt["versions"])
            self.assertEqual(before, {p.name: r.sha(p) for p in (stage / "tables").glob("*.csv")})
            counts = w.prepare(stage, "synthetic", "2026-10-31T12:00:00Z")
            self.assertEqual(counts["checked_assets"], 1)
            figure.write_bytes(figure.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "asset mismatch"):
                w.verify(stage, run_id="synthetic")

    def test_saved_publications_need_no_original_ledgers_and_detect_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            r.write_statistics(stage, fixture(), bootstrap_replicates=10)
            # Deliberately provide no original source/event CSVs in this stage.
            counts = w.prepare(stage, "synthetic", "2026-10-31T12:00:00Z")
            self.assertEqual(counts["publications"], 6)
            self.assertGreater(counts["checked_cells"], 0)
            for directory in (stage / "publications").iterdir():
                report = json.loads((directory / "publication.json").read_text())
                self.assertEqual(report["schemaVersion"], "1.1")
                self.assertEqual(report["source"]["producer"], "sahadeva")
                for section in report["sections"]:
                    if section["kind"] == "table":
                        self.assertLessEqual(len(section["rows"]), 1500)
                        self.assertLessEqual(len(section["columns"]), 12)
                receipt = json.loads((directory / "publication-verification.json").read_text())
                self.assertEqual(receipt["result"], "passed")
            chosen = next((stage / "publications").iterdir())
            report = json.loads((chosen / "publication.json").read_text())
            table = next(s for s in report["sections"] if s["kind"] == "table" and s["rows"])
            table["rows"][0][next(iter(table["rows"][0]))] = "tampered"
            r.write_json(chosen / "publication.json", report)
            with self.assertRaisesRegex(ValueError, "source-cell"):
                w.verify(stage, run_id="synthetic")

    def test_csv_roundtrip_preserves_boolean_zero_null_and_period_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "values.csv"
            source = [{"period": "2026", "sparse": False, "estimate": 0, "unknown": None}]
            r.write_csv(target, source)
            self.assertEqual(r.read_csv(target), source)

    def test_refuses_replacing_existing_statistics_and_publications(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            r.write_statistics(stage, fixture(), bootstrap_replicates=0)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                r.write_statistics(stage, fixture(), bootstrap_replicates=0)
            w.prepare(stage, "synthetic", "2026-10-31T12:00:00Z")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                w.prepare(stage, "synthetic", "2026-10-31T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
