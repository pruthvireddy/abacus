from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from reversal_study.ingest import read_dataset
from reversal_study.statistics import holm_adjust, session_bootstrap_probability


class IngestAndStatisticsTests(unittest.TestCase):
    def test_ingest_parses_day_month_and_omits_only_final_bar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            path = root / "data" / "ES.csv"
            path.write_text(
                "2026-14-06 18:00:00;100.00;100.50;99.75;100.25\n"
                "2026-14-06 18:00:00;100.25;100.50;100.00;100.00\n",
                encoding="utf-8",
            )
            config = {
                "schema": ["timestamp", "open", "high", "low", "close"],
                "delimiter": ";",
                "timestamp_format": "%Y-%d-%m %H:%M:%S",
                "contracts": {"ES": {"tick_size": 0.25}},
                "chart_identity_status": "provisional",
                "timing_status": "unverified",
                "split_dates": {"development": ["2026-06-14", "2026-06-14"]},
            }
            dataset = {"asset": "ES", "contract": "ESU6", "range": 4, "path": "data/ES.csv"}
            bars, audit = read_dataset(dataset, config, root)
            self.assertEqual(str(bars.loc[0, "export_date"]), "2026-06-14")
            self.assertTrue(bars.loc[0, "bar_included"])
            self.assertFalse(bars.loc[1, "bar_included"])
            self.assertEqual(audit["timestamp_parse_success"], 2)
            self.assertEqual(audit["repeated_timestamp_rows"], 2)
            self.assertEqual(audit["off_tick_rows"], 0)

    def test_session_bootstrap_reconciles_counts(self):
        frame = pd.DataFrame(
            {
                "export_date": ["d1", "d1", "d2", "d2"],
                "eligible": [True, True, True, False],
                "success": [True, False, True, None],
            }
        )
        result = session_bootstrap_probability(frame, "eligible", "success", 2000, 7)
        self.assertEqual(result["eligible_n"], 3)
        self.assertEqual(result["successes"], 2)
        self.assertAlmostEqual(result["probability"], 2 / 3)
        self.assertLessEqual(result["ci_low"], result["probability"])
        self.assertGreaterEqual(result["ci_high"], result["probability"])

    def test_holm_adjustment_is_monotone_in_rank(self):
        adjusted = holm_adjust([0.01, 0.04, 0.03])
        self.assertEqual(adjusted, [0.03, 0.06, 0.06])


if __name__ == "__main__":
    unittest.main()

