"""Synthetic numerical evidence checks; no market inputs or historical runs."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "src" / "reporting.py"
spec = importlib.util.spec_from_file_location("opening_pivot_reporting", MODULE)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def daily(day, *, policy="early", mask="A", exit_policy="fixed_2r", amount=0, trade=False, **extra):
    return {"date": day, "entry_policy": policy, "mask": mask, "exit_policy": exit_policy,
            "net_dollars": amount, "net_r": amount / 100 if trade else None,
            "optimistic_net_dollars": amount, "trade": trade, "candidate": trade,
            "entry_time": day + "T09:35:00-04:00" if trade else None,
            "direction": "long" if trade else None, "confirmation_delay": 0 if trade else None,
            "reason": "filled" if trade else "no_candidate", "initial_risk_points": 2 if trade else None,
            "exit_reason": "target" if amount is not None and amount > 0 else "stop" if trade else None,
            **extra}


class NumericalTests(unittest.TestCase):
    def test_real_zero_and_unavailable_have_different_denominators(self):
        result = r.summarize_group([daily("2026-01-05", amount=100, trade=True), daily("2026-01-06")])
        self.assertEqual(result["net_per_session"], 50)
        self.assertEqual(result["expectancy_dollars"], 100)
        self.assertEqual(result["participation"], .5)
        unavailable = r.summarize_group([daily("2026-01-05", amount=100, trade=True), daily("2026-01-06", amount=None)])
        self.assertIsNone(unavailable["net_per_session"])
        self.assertEqual(unavailable["net_per_available_session"], 100)
        self.assertEqual(unavailable["unavailable_sessions"], 1)

    def test_paired_difference_preserves_missed_opportunity(self):
        a = [daily("2026-01-05", amount=100, trade=True), daily("2026-01-06", amount=-50, trade=True)]
        b = [daily("2026-01-05", policy="confirmed"), daily("2026-01-06", policy="confirmed", amount=-25, trade=True)]
        result = r.paired(a, b)
        self.assertEqual(result["difference_dollars"], 37.5)
        self.assertEqual(result["left_only"], 1)
        self.assertEqual(result["both_filled"], 1)
        self.assertEqual(result["coincident_rate"], 1)
        subset = r.paired(a, b, both_filled=True)
        self.assertEqual(subset["difference_dollars"], -25)
        self.assertEqual(subset["paired_sessions"], 1)
        self.assertIsNone(subset["ci_low"])
        b[1]["net_dollars"] = None
        self.assertIsNone(r.paired(a, b, require_complete=True)["difference_dollars"])
        self.assertIsNotNone(r.paired(a, b)["difference_dollars"])

    def test_bootstrap_is_deterministic_and_week_clusters_are_weighted(self):
        values, days = [10, 10, -10], ["2026-01-05", "2026-01-06", "2026-01-12"]
        first = r.bootstrap(values, days, week=True)
        self.assertEqual(first, r.bootstrap(values, days, week=True))
        self.assertEqual(first["clusters"], 2)
        self.assertAlmostEqual(first["estimate"], 10 / 3)
        self.assertEqual(first["ci_low"], -10)
        self.assertEqual(first["ci_high"], 10)
        self.assertIsNone(r.bootstrap([1, 2], ["2026-01-05", "2026-01-06"], week=True)["ci_low"])

    def test_undefined_ratios_and_initial_equity_peak(self):
        result = r.summarize_group([daily("2026-01-05", amount=-50, trade=True), daily("2026-01-06", amount=25, trade=True)])
        self.assertEqual(result["max_drawdown_dollars"], 50)
        self.assertEqual(result["profit_factor"], .5)
        self.assertEqual(result["payoff_ratio"], .5)
        self.assertIsNone(r.summarize_group([daily("2026-01-05", amount=100, trade=True)])["profit_factor"])

    def test_holm_family_and_fixed_bin_boundaries(self):
        self.assertEqual(r.holm([.03, .01, .5, None]), [.09, .04, 1., None])
        self.assertEqual(r._bin(1, (0, 1, 2)), "[1, 2)")
        self.assertEqual(r._bin(0, (0, 1, 2), zero=True), "single_price")
        self.assertEqual(r._bin(None, (0, 1)), "unknown")
        self.assertEqual(r._pivot_type("YVAL + hve"), "HVE+YVAL")
        self.assertEqual(r.tags(daily("2026-01-05"))["split"], "temporal_test")


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.stage = Path(self.temporary.name)
        rows = []
        for day, dollars in (("2024-02-05", 100), ("2025-02-05", -50), ("2026-02-05", 75)):
            for policy, mask, exit_policy in r.VARIANTS:
                rows.append(daily(day, policy=policy, mask=mask, exit_policy=exit_policy,
                                  amount=dollars if policy == "early" else dollars - 10, trade=True,
                                  pivot_description="YVAL + HVE", pivot_kind="single", pivot_width=0,
                                  atr14=4, target_ordinal=None, target_description=None,
                                  pivot_lower=5000, pivot_upper=5000, stop_price=4998, entry_price=5000,
                                  target_price=5004, candidate_id=day + ":1"))
        r.write_rows(self.stage / "daily.csv", rows)

    def tearDown(self):
        self.temporary.cleanup()

    def test_summarize_sixteen_variants_and_saved_render(self):
        metrics = r.summarize(self.stage)
        self.assertEqual(len(metrics["variants"]), 16)
        primary = r._saved_table(self.stage, "primary_comparison.csv")
        self.assertEqual([row["cohort"] for row in primary], ["pooled_exploratory", "development", "validation", "temporal_test"])
        self.assertEqual(primary[0]["difference_dollars"], 10)
        self.assertEqual(len(r._saved_table(self.stage, "secondary_comparisons.csv")), 15)
        # Report must render the saved tables even when original outcomes disappear.
        (self.stage / "daily.csv").unlink()
        publication = r.report(self.stage, "26_es_opening_pivot_cloud", "synthetic", published_at="2026-10-21T12:00:00Z")
        self.assertEqual(publication["schemaVersion"], "1.1")
        self.assertEqual(len(publication["downloads"]), 4)
        self.assertLessEqual(len(publication["sections"]), 30)
        self.assertEqual(json.loads((self.stage / "publication-verification.json").read_text())["status"], "passed")
        self.assertTrue((self.stage / "report.html").exists())
        for download in publication["downloads"]:
            self.assertEqual(r._hash(self.stage / download["path"]), download["sha256"])
            self.assertLessEqual((self.stage / download["path"]).stat().st_size, 256 * 1024)
        source_map = json.loads((self.stage / "source-map.json").read_text())
        self.assertTrue(source_map["bindings"])
        self.assertEqual(r.verify_saved_projection(self.stage)["status"], "passed")
        publication["sections"][2]["body"] = "Text is outside cell verification."
        target = next(section for section in publication["sections"] if section["kind"] == "table")
        first_column = target["columns"][0]["key"]
        target["rows"][0][first_column] = "tampered"
        r._write_json(self.stage / "publication.json", publication)
        with self.assertRaisesRegex(ValueError, "source-cell"):
            r.verify_saved_projection(self.stage)

    def test_refuse_duplicate_or_incomplete_daily_panel(self):
        rows = r.read_rows(self.stage / "daily.csv")
        r.write_rows(self.stage / "daily.csv", rows + rows[:1])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            r.summarize(self.stage)
        r.write_rows(self.stage / "daily.csv", rows[1:])
        with self.assertRaisesRegex(ValueError, "sixteen"):
            r.summarize(self.stage)


if __name__ == "__main__":
    unittest.main()
