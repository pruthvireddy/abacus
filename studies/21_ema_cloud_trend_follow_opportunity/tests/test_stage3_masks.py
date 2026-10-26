import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage3_masks import ScoringPeriod, event_masks, calendar_weeks, scoring_periods


def roster(n=130):
    t = pd.date_range("2019-01-01 05:00", periods=n, freq="3min", tz="UTC")
    return pd.DataFrame(dict(product="ES", timestamp=t, available_at=t + pd.Timedelta(minutes=3),
        contract="ESH9", high=102., low=99., close=101., usable=True, quality_reason="complete",
        session="2019-01-01", known_closure_before=False))


def events(bars, indices):
    return pd.DataFrame([dict(event_id=f"e{i}", product="ES", timestamp=bars.timestamp.iloc[i],
        available_at=bars.available_at.iloc[i], entry_at=bars.available_at.iloc[i], contract="ESH9",
        signal_idx=i, reference_price=100., direction=1, side="Buy", entry_atr=2., session="2019-01-01",
        week="2018-12-31", month="2019-01", year=2019, time_stratum="Asia", hour=0,
        calendar_date="2019-01-01") for i in indices])


class MasksTest(unittest.TestCase):
    def test_invalid_slots_count_in_exact_hundred_slot_embargo(self):
        bars = roster()
        bars.loc[:98, "usable"] = False
        period = ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-02")
        out, audit = event_masks(bars, events(bars, [99, 100]), [1], period)
        self.assertEqual(out.start_embargo.tolist(), [True, False])
        self.assertEqual(audit["embargo_actual"], 100)
        self.assertEqual(audit["first_post_embargo_timestamp"], bars.timestamp.iloc[100])

    def test_known_closure_does_not_add_slots_or_make_clock_embargo(self):
        bars = roster()
        bars.loc[50:, "timestamp"] += pd.Timedelta(days=2)
        bars.loc[50:, "available_at"] += pd.Timedelta(days=2)
        bars.loc[50, "known_closure_before"] = True
        p = ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-05")
        out, _ = event_masks(bars, events(bars, [99, 100]), [1], p)
        self.assertEqual(out.start_embargo.tolist(), [True, False])

    def test_terminal_at_endpoint_allowed_beyond_endpoint_purged(self):
        bars = roster(5)
        end = bars.available_at.iloc[3]
        p = ScoringPeriod("development", "fixture", "2019-01-01", end, 0)
        out, _ = event_masks(bars, events(bars, [0]), [3, 4], p)
        self.assertEqual(out.endpoint_purge.tolist(), [False, True])

    def test_unusable_before_start_does_not_move_full_causal_ordinals(self):
        bars = roster()
        p = ScoringPeriod("development", "fixture", bars.timestamp.iloc[10], "2019-01-02", 2)
        out, audit = event_masks(bars, events(bars, [9, 10, 11, 12]), [1], p)
        self.assertEqual(out.signal_idx.tolist(), [10, 11, 12])
        self.assertEqual(out.start_embargo.tolist(), [True, True, False])
        self.assertEqual(audit["first_signal_idx"], 10)

    def test_missing_atr_changes_support_only(self):
        bars = roster()
        ev = events(bars, [101, 102])
        ev["entry_atr"] = [0., np.nan]
        out, _ = event_masks(bars, ev, [1], ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-02"))
        self.assertTrue(out.score_eligible.all())
        self.assertFalse(out.atr_support.any())

    def test_calendar_rosters_are_rebuilt_and_intersect_exact_period(self):
        old = calendar_weeks("2018-01-01", "2021-01-01")
        self.assertEqual((len(old), old[0], old[-1]), (157, "2018-01-01", "2020-12-28"))
        final = calendar_weeks("2024-01-01", "2026-01-01")
        self.assertEqual((len(final), final[0], final[-1]), (105, "2024-01-01", "2025-12-29"))
        recent = calendar_weeks("2026-01-01", "2026-09-18T21:00Z")
        self.assertEqual((recent[0], recent[-1]), ("2025-12-29", "2026-09-14"))
        self.assertNotIn("2025-12-22", recent)

    def test_all_six_development_halfyears_are_masked(self):
        cfg = dict(canonical_start_embargo_slots=100, development_folds=[dict(id=f"{y}H{h}", start=f"{y}-{'01' if h==1 else '07'}-01", end=f"{y}-07-01" if h==1 else f"{y+1}-01-01") for y in (2019, 2020) for h in (1, 2)])
        self.assertEqual([p.fold_id for p in scoring_periods(cfg, "development")], ["2018H1", "2018H2", "2019H1", "2019H2", "2020H1", "2020H2"])

    def test_reject_bad_ordinals_and_warmup_outcome_period(self):
        bars = roster()
        ev = events(bars, [101]); ev["signal_idx"] = 100
        with self.assertRaises(ValueError):
            event_masks(bars, ev, [1], ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-02"))
        with self.assertRaises(ValueError):
            ScoringPeriod("development", "warmup", "2017-01-01", "2018-01-01")


if __name__ == "__main__":
    unittest.main()
