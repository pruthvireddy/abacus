"""Synthetic mutation fixtures for the independent scientific checker."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import generate_events
from src.outcomes import score_outcomes
from src.statistics import quantiles, signal_flow, stability, summarize
from src.reconcile import (linear_quantile, reconcile_mapping, reconcile_outcomes,
                           reconcile_signals, reconcile_tables, reconcile_examples,
                           reconcile_primary_bootstrap, reconcile_coverage)
from src.reporting import select_examples


def fixture(direction=1):
    timestamps = pd.date_range("2018-01-02T14:00Z", periods=120, freq="3min")
    bars = pd.DataFrame({"product": "ES", "interval_minutes": 3, "timestamp": timestamps,
                         "available_at": timestamps + pd.Timedelta(minutes=3), "contract": "ES-A",
                         "session": "2018-01-02", "usable": True, "feature_valid": True,
                         "feature_reset": False, "feature_source_timestamp": timestamps,
                         "open": 104., "high": 105., "low": 104., "close": 104.5,
                         "ema20": 103. if direction == 1 else 100., "ema50": 100. if direction == 1 else 103.,
                         "atr14": 2., "quality_reason": "complete", "known_closure_before": False})
    if direction == -1:
        bars.loc[:, ["open", "high", "low", "close"]] = [98., 99., 97., 98.]
    bars.loc[1, ["open", "high", "low", "close"]] = [102., 110., 90., 101.]
    technical, events = generate_events(bars, 3)
    outcomes = score_outcomes(bars, events, interval_minutes=3, roster_end_is_endpoint=True)
    return bars, technical, events, outcomes


def coverage_fixture(interval):
    """Manually enumerated coverage, independent of the research producers."""
    timestamps = pd.to_datetime(["2017-01-03T15:00Z", "2018-01-02T15:00Z", "2018-01-02T15:05Z",
                                 "2018-01-03T15:00Z", "2018-01-04T15:00Z", "2019-01-02T15:00Z", "2019-01-03T15:00Z"])
    technical = pd.DataFrame({"product": "ES", "interval_minutes": interval, "timestamp": timestamps,
                              "usable": [True, True, False, True, True, True, True],
                              "feature_valid": [True, True, True, False, True, True, False],
                              "session": ["w", "a", "b", "c", "d", "e", "f"],
                              "quality_reason": ["", "", "missing_source_minutes", "", "", "", ""],
                              "source_count": [interval, interval, 0, interval, interval, interval, interval],
                              "contract_count": [1, 1, 2, 1, 1, 1, 1],
                              "calendar_valid": [True, True, False, True, True, True, True],
                              "expected_count": interval,
                              "known_closure_before": [True, True, False, False, False, True, False]})
    native = pd.DataFrame({"timestamp": pd.to_datetime(["2017-01-03T15:00Z"]), "feature_valid": [True]})
    rows = []
    for year, count, usable, missing, sessions, ready in ((2017, 1, 1, 0, None, None),
                                                       (2018, 4, 3, 1, 2, 2), (2019, 2, 2, 0, 1, 1)):
        rows.append({"product": "ES", "interval_minutes": interval, "year": year,
                     "split": "warmup_only" if year == 2017 else "development", "scheduled_slots": count,
                     "usable_slots": usable, "missing_slots": missing, "empty_slots": missing,
                     "mixed_slots": missing, "calendar_invalid_slots": missing,
                     "expected_source_minutes": count * interval, "observed_source_minutes": usable * interval,
                     "known_closures_before": 1,
                     "feature_ready_slots": (1 if interval == 5 else None) if year == 2017 else ready,
                     "mapped_ready_slots": ready, "ready_share": ready / count if ready is not None else None,
                     "ready_sessions": sessions})
    return technical, native, rows


def write_coverage(path, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class CoverageChecks(unittest.TestCase):
    def test_ready_requires_usable_and_valid_mapped_cloud_both_intervals(self):
        for interval in (3, 5):
            with self.subTest(interval=interval), tempfile.TemporaryDirectory() as tmp:
                technical, native, rows = coverage_fixture(interval)
                path = Path(tmp) / "coverage.csv"
                write_coverage(path, rows)
                result = reconcile_coverage(technical, native, path)
                self.assertEqual(result["status"], "passed")
                self.assertEqual(result["annual_support"][1]["eligible_slots"], 2)
                self.assertEqual(result["annual_support"][1]["ready_sessions"], 2)
                # Counting feature validity alone would incorrectly include row 2.
                self.assertEqual(int(technical.iloc[1:5].feature_valid.sum()), 3)

    def test_warmup_native_five_readiness_preserved(self):
        technical, native, rows = coverage_fixture(5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coverage.csv"
            write_coverage(path, rows)
            self.assertEqual(reconcile_coverage(technical, native, path)["status"], "passed")
            native.loc[0, "feature_valid"] = False
            with self.assertRaisesRegex(ValueError, "feature_ready_slots"):
                reconcile_coverage(technical, native, path)

    def test_warmup_three_readiness_is_undefined(self):
        technical, native, rows = coverage_fixture(3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coverage.csv"
            write_coverage(path, rows)
            self.assertEqual(reconcile_coverage(technical, native, path)["status"], "passed")
            rows[0]["feature_ready_slots"] = 0
            write_coverage(path, rows)
            with self.assertRaisesRegex(ValueError, "null mismatch"):
                reconcile_coverage(technical, native, path)

    def test_complete_unique_annual_support_required(self):
        technical, native, rows = coverage_fixture(3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coverage.csv"
            for broken in (rows[:-1], rows + [rows[-1]]):
                write_coverage(path, broken)
                with self.assertRaisesRegex(ValueError, "annual support"):
                    reconcile_coverage(technical, native, path)

    def test_corrupted_readiness_count_share_sessions_and_missing_field_rejected(self):
        for column, value in (("feature_ready_slots", 3), ("mapped_ready_slots", 3),
                              ("ready_share", .75), ("ready_sessions", 3)):
            with self.subTest(column=column), tempfile.TemporaryDirectory() as tmp:
                technical, native, rows = coverage_fixture(3)
                rows[1][column] = value
                path = Path(tmp) / "coverage.csv"
                write_coverage(path, rows)
                with self.assertRaisesRegex(ValueError, column):
                    reconcile_coverage(technical, native, path)
        with tempfile.TemporaryDirectory() as tmp:
            technical, native, rows = coverage_fixture(3)
            for row in rows:
                del row["ready_sessions"]
            path = Path(tmp) / "coverage.csv"
            write_coverage(path, rows)
            with self.assertRaisesRegex(ValueError, "missing coverage field: ready_sessions"):
                reconcile_coverage(technical, native, path)


class IndependentChecks(unittest.TestCase):
    def test_linear_quantile_unequal_spacing_and_null(self):
        self.assertEqual(linear_quantile([0., 2., 100.], .25), 1.)
        self.assertEqual(linear_quantile([0., 2., 100.], .75), 51.)
        self.assertIsNone(linear_quantile([], .5))

    def test_long_short_entry_exclusion_all_horizons(self):
        for direction in (1, -1):
            bars, technical, events, outcomes = fixture(direction)
            self.assertEqual(reconcile_signals(technical, events)["status"], "passed")
            self.assertEqual(reconcile_outcomes(bars, events, outcomes)["status"], "passed")
            self.assertTrue(outcomes.mfe.lt(10).all())
            broken = outcomes.copy()
            broken.loc[0, "mfe"] += .25
            with self.assertRaisesRegex(ValueError, "outcome"):
                reconcile_outcomes(bars, events, broken)

    def test_censored_is_null_not_zero_and_shorter_complete(self):
        bars, technical, events, _ = fixture()
        bars.loc[20, "usable"] = False
        bars.loc[20, "quality_reason"] = "partial"
        outcomes = score_outcomes(bars, events, interval_minutes=3, roster_end_is_endpoint=True)
        self.assertEqual(reconcile_outcomes(bars, events, outcomes)["status"], "passed")
        self.assertEqual(outcomes.loc[outcomes.horizon == 15, "status"].iloc[0], "completed")
        self.assertEqual(outcomes.loc[outcomes.horizon == 20, "status"].iloc[0], "censored")
        outcomes.loc[outcomes.horizon == 20, "mfe"] = 0.
        with self.assertRaisesRegex(ValueError, "null mismatch"):
            reconcile_outcomes(bars, events, outcomes)

    def test_signal_state_mutation_and_event_drop_rejected(self):
        bars, technical, events, outcomes = fixture()
        technical.loc[1, "armed_after"] = True
        with self.assertRaisesRegex(ValueError, "armed_after"):
            reconcile_signals(technical, events)
        _, technical, events, _ = fixture()
        with self.assertRaisesRegex(ValueError, "identity/order"):
            reconcile_signals(technical, events.iloc[:0])

    def test_latest_partial_cloud_not_carried(self):
        times = pd.date_range("2018-01-02T14:00Z", periods=3, freq="5min")
        source = pd.DataFrame({"product": "ES", "timestamp": times, "available_at": times + pd.Timedelta(minutes=5),
                               "contract": "ES-A", "usable": [True, False, True], "feature_valid": [True, False, True],
                               "ema20": [103., 103., 103.], "ema50": [100., 100., 100.], "atr14": [2., 2., 2.]})
        technical = pd.DataFrame({"product": "ES", "interval_minutes": 3,
                                  "timestamp": [pd.Timestamp("2018-01-02T14:12Z")],
                                  "available_at": [pd.Timestamp("2018-01-02T14:15Z")], "contract": "ES-A",
                                  "feature_source_timestamp": [times[1]], "feature_available_at": [times[1] + pd.Timedelta(minutes=5)],
                                  "feature_valid": False, "ema20": np.nan, "ema50": np.nan, "atr14": np.nan})
        self.assertEqual(reconcile_mapping(technical, source)["status"], "passed")
        technical.loc[0, "feature_source_timestamp"] = times[0]
        with self.assertRaisesRegex(ValueError, "latest scheduled"):
            reconcile_mapping(technical, source)

    def test_every_summary_quantile_flow_and_calendar_value(self):
        bars, technical, events, outcomes = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            tables = {}
            frames = {"S1-T00": pd.DataFrame({"row_id": ["coverage"]}), "S1-T01": signal_flow(technical, events, outcomes),
                      "S1-T02": summarize(outcomes), "S1-T03": quantiles(outcomes),
                      "S1-T04": stability(outcomes).query("period_kind == 'year'"),
                      "S1-T05": stability(outcomes).query("period_kind == 'month'"),
                      "S1-T06": pd.DataFrame({"row_id": ["example"]})}
            for name, frame in frames.items():
                tables[name] = stage / (name + ".csv")
                frame.to_csv(tables[name], index=False, float_format="%.17g")
            receipt = reconcile_tables(outcomes, tables, technical)
            self.assertEqual(receipt["status"], "passed")
            self.assertGreater(receipt["checked_numeric_cells"], 500)
            frame = frames["S1-T02"].copy()
            frame.loc[0, "mean_terminal_delta"] = 999
            frame.to_csv(tables["S1-T02"], index=False)
            with self.assertRaisesRegex(ValueError, "mean_terminal_delta"):
                reconcile_tables(outcomes, tables, technical)

    def test_deterministic_example_selection_independent_and_mutation(self):
        bars, technical, events, outcomes = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "examples.csv"
            examples = select_examples(technical, events, outcomes)
            examples.to_csv(path, index=False)
            self.assertEqual(reconcile_examples(outcomes, technical, path)["status"], "passed")
            row = examples.index[examples.selection_status == "selected"][0]
            examples.loc[row, "signal_idx"] += 1
            examples.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "example ordinal"):
                reconcile_examples(outcomes, technical, path)

    def test_first_development_week_bootstrap_support_excludes_preceding_week(self):
        """The empty December 25 week changes seeded undefined draws despite constant prices."""
        rows, summaries, bootstrap_rows = [], [], []
        # Deterministic counts for 157 intersecting weeks, seed 20261010 and
        # 10,000 circular samples with events solely in the January 1 week.
        undefined = {4: 3643, 1: 3596, 8: 3640}
        for product in ("ES", "GC", "NQ"):
            for interval in (3, 5):
                rows.append(dict(product=product, interval_minutes=interval, horizon=15,
                                 status="completed", week="2018-01-01", terminal_delta=2.))
                summaries.append(dict(product=product, interval_minutes=interval, horizon=15,
                                      direction="All", unit="points", support="all", ci95_low=2., ci95_high=2.))
                for block in (4, 1, 8):
                    bootstrap_rows.append(dict(kind="cohort", product=product, interval_minutes=interval,
                                               horizon=15, direction="All", unit="points", metric="terminal_delta",
                                               weighting="event", block_weeks=block, ci_low=2., ci_high=2.,
                                               undefined_draws=undefined[block]))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score_path, bootstrap_path = root / "score.csv", root / "bootstrap.csv"
            pd.DataFrame(summaries).to_csv(score_path, index=False)
            bootstrap = pd.DataFrame(bootstrap_rows)
            bootstrap.to_csv(bootstrap_path, index=False)
            result = reconcile_primary_bootstrap(pd.DataFrame(rows), score_path, bootstrap_path)
            self.assertEqual(len(result["cells"]), 18)
            # The former 158-week roster's four-week undefined count was 3625.
            bootstrap.loc[0, "undefined_draws"] = 3625
            bootstrap.to_csv(bootstrap_path, index=False)
            with self.assertRaisesRegex(ValueError, "undefined bootstrap draws"):
                reconcile_primary_bootstrap(pd.DataFrame(rows), score_path, bootstrap_path)

    def test_calendar_summary_preceding_empty_week_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tables = {}
            for name in ("S1-T00", "S1-T01", "S1-T02", "S1-T03", "S1-T04", "S1-T05", "S1-T06"):
                tables[name] = Path(tmp) / (name + ".csv")
                tables[name].write_text("row_id\n")
            tables["S1-T05"].write_text("row_id,period_kind,period\npreceding,week,2017-12-25\n")
            with self.assertRaisesRegex(ValueError, "does not intersect development"):
                reconcile_tables(pd.DataFrame(), tables)


if __name__ == "__main__":
    unittest.main()
