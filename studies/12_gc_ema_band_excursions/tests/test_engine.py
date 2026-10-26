import unittest
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import accepted_indices, analyze, classify_path


class CooldownAdapterTest(unittest.TestCase):
    def test_empty_and_all_false_masks_return_empty_int64(self):
        for candidates in (np.array([], dtype=bool), np.zeros(8, dtype=bool)):
            with self.subTest(length=len(candidates)):
                selected = accepted_indices(candidates, 3)
                self.assertEqual(selected.dtype, np.dtype(np.int64))
                self.assertEqual(selected.tolist(), [])

    def test_zero_cooldown_accepts_every_candidate_in_original_positions(self):
        candidates = np.array([False, True, True, False, True])
        selected = accepted_indices(candidates, 0)
        self.assertEqual(selected.tolist(), [1, 2, 4])
        self.assertEqual(selected.dtype, np.dtype(np.int64))

    def test_exact_cooldown_boundary_and_suppression_without_rearming(self):
        candidates = np.zeros(13, dtype=bool)
        candidates[[2, 3, 5, 6, 7, 9, 10]] = True
        # Bar 5 is i+C and suppressed; bar 6 is i+C+1 and eligible.
        # Suppressed bars 3/5 and 7/9 must not start a new timer.
        self.assertEqual(accepted_indices(candidates, 3).tolist(), [2, 6, 10])

    def test_sparse_candidates_use_chart_positions_not_candidate_ordinals(self):
        candidates = np.zeros(102, dtype=bool)
        candidates[[1, 50, 51, 100]] = True
        self.assertEqual(accepted_indices(candidates, 3).tolist(), [1, 50, 100])

    def test_calls_are_independent_and_candidate_mask_is_unchanged(self):
        candidates = np.array([True, True, False, True, True, False, True])
        before = candidates.copy()
        self.assertEqual(accepted_indices(candidates, 2).tolist(), [0, 3, 6])
        self.assertEqual(accepted_indices(candidates, 0).tolist(), [0, 1, 3, 4, 6])
        self.assertEqual(accepted_indices(candidates, 2).tolist(), [0, 3, 6])
        np.testing.assert_array_equal(candidates, before)

    def test_negative_cooldown_retains_existing_exception_message(self):
        with self.assertRaisesRegex(ValueError, "^cooldown must be nonnegative$"):
            accepted_indices(np.array([True, False]), -1)

    def test_bounded_masks_match_independent_slice_blocking_reference(self):
        for bits in range(1 << 8):
            candidates = np.array([bool(bits & (1 << index)) for index in range(8)])
            before = candidates.copy()
            for cooldown in range(5):
                available = candidates.copy()
                expected = []
                for index in range(len(available)):
                    if available[index]:
                        expected.append(index)
                        available[index + 1:index + cooldown + 1] = False
                with self.subTest(bits=bits, cooldown=cooldown):
                    selected = accepted_indices(candidates, cooldown)
                    self.assertEqual(selected.tolist(), expected)
                    self.assertEqual(selected.dtype, np.dtype(np.int64))
                    np.testing.assert_array_equal(candidates, before)


class EngineTest(unittest.TestCase):
    def test_cooldown_skips_exact_following_bars(self):
        raw = np.array([True] * 8)
        np.testing.assert_array_equal(accepted_indices(raw, 0), np.arange(8))
        np.testing.assert_array_equal(accepted_indices(raw, 2), [0, 3, 6])

    def test_path_reasons(self):
        ts = np.arange(5, dtype=np.int64) * 300_000_000_000
        complete = np.ones(5, dtype=bool)
        symbol = np.array(["A"] * 5)
        adj = np.zeros(5)
        self.assertEqual(classify_path(0, 3, ts, complete, symbol, adj), "valid")
        self.assertEqual(classify_path(2, 3, ts, complete, symbol, adj), "insufficient_future_bars")
        ts[2] += 60_000_000_000
        self.assertEqual(classify_path(0, 3, ts, complete, symbol, adj), "time_gap")
        ts = np.arange(5, dtype=np.int64) * 300_000_000_000
        complete[2] = False
        self.assertEqual(classify_path(0, 3, ts, complete, symbol, adj), "partial_or_mixed_bar")
        complete[2] = True
        symbol[2] = "B"
        self.assertEqual(classify_path(0, 3, ts, complete, symbol, adj), "contract_change")
        symbol[2] = "A"
        adj[2] = 1
        self.assertEqual(classify_path(0, 3, ts, complete, symbol, adj), "adjustment_change")

    def test_entry_bar_counts_in_both_excursions(self):
        ts = pd.date_range("2025-01-01", periods=6, freq="5min", tz="UTC")
        bars = pd.DataFrame({"ts_event": ts, "session_date": [pd.Timestamp("2025-01-01").date()] * 6,
                             "open": [100, 100, 101, 101, 101, 101],
                             "high": [101, 103, 102, 102, 102, 102],
                             "low": [99, 98, 100, 100, 100, 100],
                             "close": [100, 101, 101, 101, 101, 101],
                             "price_adjustment": [0] * 6, "raw_symbol": ["GCZ5"] * 6,
                             "source_bar_count": [5] * 6, "is_partial_bar": [False] * 6,
                             "is_mixed_contract_bar": [False] * 6, "is_mixed_adjustment_bar": [False] * 6,
                             "contains_roll": [False] * 6})
        for col in ["open", "high", "low", "close"]:
            bars[col] *= 1_000_000_000
        bands = pd.DataFrame({"ts_event": ts, "available_at": ts + pd.Timedelta(minutes=5),
                              "lower_outer_3sigma": [100] + [0] * 5})
        ledger, cohort = analyze(bars, bands, [0], [2])
        self.assertEqual(len(ledger), 1)
        self.assertEqual(cohort.accepted_signals.iloc[0], 1)
        self.assertEqual(ledger.mae_points.iloc[0], 2)
        self.assertEqual(ledger.mfe_points.iloc[0], 3)

    def test_future_path_exclusion_does_not_change_signal_acceptance(self):
        ts = pd.date_range("2025-01-02 13:00", periods=6, freq="5min", tz="UTC")
        # The accepted signal at bar 0 has a gap before entry. Bar 1 remains a
        # candidate, but its valid future path must not undo bar 0's cooldown.
        ts = pd.DatetimeIndex([ts[0], *(ts[1:] + pd.Timedelta(minutes=5))])
        bars = pd.DataFrame({
            "ts_event": ts, "session_date": [pd.Timestamp("2025-01-02").date()] * 6,
            "open": [110_000_000_000] * 6, "high": [111_000_000_000] * 6,
            "low": [109_000_000_000] * 6, "close": [110_000_000_000] * 6,
            "price_adjustment": [10_000_000_000] * 6, "raw_symbol": ["GCG5"] * 6,
            "source_bar_count": [5] * 6, "is_partial_bar": [False] * 6,
            "is_mixed_contract_bar": [False] * 6, "is_mixed_adjustment_bar": [False] * 6,
            "contains_roll": [False] * 6,
        })
        bands = pd.DataFrame({
            "ts_event": ts, "available_at": ts + pd.Timedelta(minutes=5),
            "lower_outer_3sigma": [110, 110, 0, 110, 0, 0],
        })
        original_bars, original_bands = bars.copy(deep=True), bands.copy(deep=True)
        ledger, cohort = analyze(bars, bands, [2], [1])
        self.assertEqual(ledger.signal_ts_utc.tolist(), [ts[0].isoformat(), ts[3].isoformat()])
        self.assertEqual(ledger.status.tolist(), ["time_gap", "valid"])
        self.assertEqual(cohort.raw_candidates.tolist(), [3])
        self.assertEqual(cohort.accepted_signals.tolist(), [2])
        self.assertTrue(pd.isna(ledger.entry_unadjusted.iloc[0]))
        self.assertEqual(ledger.entry_unadjusted.iloc[1], 100)
        self.assertEqual(ledger.mae_points.iloc[1], 1)
        self.assertEqual(ledger.mfe_points.iloc[1], 1)
        self.assertEqual(ledger.terminal_points.iloc[1], 0)
        pd.testing.assert_frame_equal(bars, original_bars)
        pd.testing.assert_frame_equal(bands, original_bands)


if __name__ == "__main__":
    unittest.main()
