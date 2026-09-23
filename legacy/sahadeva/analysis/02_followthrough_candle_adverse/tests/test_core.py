from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from followthrough_adverse.core import detect_reversals, read_chart


CONFIG = {
    "primary_reference": "follow-through candle open",
    "timing_status": "unresolved",
}


def make_bars(rows, sequences=None):
    frame = pd.DataFrame(rows, columns=["open_ticks", "high_ticks", "low_ticks", "close_ticks"])
    n = len(frame)
    frame["direction"] = np.sign(frame["close_ticks"] - frame["open_ticks"]).astype(int)
    if sequences is None:
        sequences = [1] * n
    for column in ("open", "high", "low", "close"):
        frame[column] = frame[f"{column}_ticks"]
    return frame.assign(
        source_row=np.arange(1, n + 1),
        timestamp=[f"2026-01-01 00:00:{i:02d}" for i in range(n)],
        parsed_timestamp=pd.date_range("2026-01-01", periods=n, freq="s"),
        export_date="2026-01-01",
        valid_row=True,
        bar_included=True,
        split="development",
        sequence_id=sequences,
        source_file="synthetic.csv",
        source_sha256="abc",
        asset="ES",
        contract="ESU6",
        range_setting=4,
        chart_identity_status="provisional",
    )


class CoreTests(unittest.TestCase):
    def test_long_second_candle_adverse_from_own_open(self):
        bars = make_bars(
            [
                (103, 103, 101, 102),
                (102, 102, 100, 101),
                (101, 101, 99, 100),
                (99, 101, 98, 100),
                (101, 105, 99, 104),
                (104, 104, 102, 103),
            ]
        )
        events = detect_reversals(bars, CONFIG)
        event = events.loc[events["bar_index"].eq(3)].iloc[0]
        self.assertEqual(event["prior_opposite_run"], 3)
        self.assertTrue(event["next_bar_same_direction"])
        self.assertEqual(event["adverse_from_follow_open_ticks"], 2)
        self.assertEqual(event["favorable_from_follow_open_ticks"], 4)
        self.assertEqual(event["close_progress_from_follow_open_ticks"], 3)
        self.assertEqual(event["adverse_from_signal_close_ticks"], 1)
        self.assertEqual(event["directional_open_gap_ticks"], 1)

    def test_short_is_symmetric(self):
        bars = make_bars(
            [
                (97, 99, 97, 98),
                (98, 100, 98, 99),
                (99, 101, 99, 100),
                (101, 102, 99, 100),
                (99, 101, 95, 96),
                (96, 98, 96, 97),
            ]
        )
        event = detect_reversals(bars, CONFIG).loc[lambda x: x["bar_index"].eq(3)].iloc[0]
        self.assertEqual(event["signal_side"], "short")
        self.assertEqual(event["adverse_from_follow_open_ticks"], 2)
        self.assertEqual(event["favorable_from_follow_open_ticks"], 4)
        self.assertEqual(event["close_progress_from_follow_open_ticks"], 3)
        self.assertEqual(event["adverse_from_signal_close_ticks"], 1)
        self.assertEqual(event["directional_open_gap_ticks"], 1)

    def test_wrong_color_next_bar_is_not_in_conditional_cohort(self):
        bars = make_bars([(101, 101, 99, 100), (99, 101, 99, 100), (101, 101, 99, 100)])
        event = detect_reversals(bars, CONFIG).iloc[0]
        self.assertTrue(event["eligible_next_bar"])
        self.assertFalse(event["next_bar_same_direction"])
        self.assertTrue(pd.isna(event["adverse_from_follow_open_ticks"]))

    def test_doji_breaks_reversal_adjacency(self):
        bars = make_bars([(101, 101, 99, 100), (100, 101, 99, 100), (99, 101, 99, 100)])
        self.assertTrue(detect_reversals(bars, CONFIG).empty)

    def test_boundary_next_bar_is_excluded(self):
        bars = make_bars(
            [(101, 101, 99, 100), (99, 101, 99, 100), (100, 102, 100, 101)],
            sequences=[1, 1, 2],
        )
        event = detect_reversals(bars, CONFIG).iloc[0]
        self.assertFalse(event["eligible_next_bar"])
        self.assertFalse(event["next_bar_same_direction"])

    def test_ingest_omits_final_row_and_validates_ticks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data" / "ES.csv").write_text(
                "2026-14-06 18:00:00;100.00;100.50;99.75;100.25\n"
                "2026-14-06 18:00:01;100.25;100.50;100.00;100.00\n",
                encoding="utf-8",
            )
            config = {
                "delimiter": ";",
                "timestamp_format": "%Y-%d-%m %H:%M:%S",
                "contracts": {"ES": {"tick_size": 0.25}},
                "split_dates": {"development": ["2026-06-14", "2026-06-14"]},
                "chart_identity_status": "provisional",
            }
            dataset = {"asset": "ES", "contract": "ESU6", "range": 4, "path": "data/ES.csv"}
            bars, audit = read_chart(dataset, config, root)
            self.assertTrue(bars.loc[0, "bar_included"])
            self.assertFalse(bars.loc[1, "bar_included"])
            self.assertEqual(audit["off_tick_rows"], 0)
            self.assertEqual(audit["timestamp_parse_failures"], 0)


if __name__ == "__main__":
    unittest.main()

