"""Mutation checks for the independent Stage 2 scientific checker.

Only small synthetic populations are used. Producer tables below are adversarial
inputs to the checker; the independent reference modules import no producers.
"""
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.stage2_comparisons import branch_contrasts, paired_uncertainty
from src.stage2_reconcile import cell, compare_frames, reconcile_contrasts, reconcile_paths
from src.stage2_reference import reference_outcomes, reference_stream
from test_stage2_comparisons import streams
from test_stage2_reference import bars


class Stage2ReconcileReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.population = streams()
        # Two draws keep this inventory fixture fast. Its valid inventory must
        # pass the complete-grid guard and then fail the frozen 10,000-draw guard.
        cls.contrasts = pd.concat([
            branch_contrasts(cls.population),
            paired_uncertainty(cls.population, resamples=2, block_lengths=(1, 4, 8)),
        ], ignore_index=True)
        cls.primary = (cls.contrasts.interval_type.eq("bonferroni") &
                       cls.contrasts.block_weeks.eq(4))
        cls.synthetic_bars = bars([(106, 108), (104, 106)] + [(106, 110)] * 14)
        _, events = reference_stream(cls.synthetic_bars)
        cls.synthetic_events = events.loc[events.touch_mode.eq("fast")].iloc[:1].copy()
        cls.synthetic_paths = reference_outcomes(cls.synthetic_bars, cls.synthetic_events)

    def write_and_check(self, frame):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contrasts.csv"
            frame.to_csv(path, index=False, float_format="%.17g")
            return reconcile_contrasts(self.population, path)

    def test_csv_false_null_and_numeric_zero_have_distinct_contracts(self):
        for token in ("False", "false"):
            cell(token, False, "observed false")
        cell("", None, "undefined")
        cell("0", 0, "actual numeric zero")
        for token in ("0", "0.0", "no", "nan", "", " True "):
            with self.subTest(token=token), self.assertRaises(ValueError):
                cell(token, False, "flag mutation")
        for token in ("False", "false", "0", "NaN"):
            with self.subTest(null_token=token), self.assertRaisesRegex(ValueError, "undefined cell"):
                cell(token, None, "null mutation")
        with self.assertRaises(ValueError):
            cell("False", 0, "numeric mutation")

    def test_ledger_boolean_zero_and_null_mutations_are_rejected(self):
        expected = pd.DataFrame(dict(event_id=["a", "b"], favorable=pd.Series([False, None], dtype=object)))
        compare_frames(expected.copy(), expected, ["event_id"], fields=["favorable"])
        for value in (0, 0.0, None):
            changed = expected.copy()
            changed.loc[0, "favorable"] = value
            with self.subTest(false_mutation=value), self.assertRaises(ValueError):
                compare_frames(changed, expected, ["event_id"], fields=["favorable"])
        changed = expected.copy()
        changed.loc[1, "favorable"] = False
        with self.assertRaisesRegex(ValueError, "null mismatch"):
            compare_frames(changed, expected, ["event_id"], fields=["favorable"])

    def test_dropped_primary_cell_is_rejected_before_numerical_check(self):
        selected = self.contrasts.loc[self.primary]
        self.assertEqual(set(zip(selected["product"], selected.interval_minutes)),
                         {(product, interval) for product in ("ES", "GC", "NQ") for interval in (3, 5)})
        self.assertEqual(len(selected), 6)
        with self.assertRaisesRegex(ValueError, "frozen bootstrap settings"):
            self.write_and_check(self.contrasts)
        changed = self.contrasts.drop(index=selected.index[0])
        with self.assertRaisesRegex(ValueError, "complete unique frozen contrast/uncertainty key inventory"):
            self.write_and_check(changed)

    def test_duplicate_primary_cell_with_fresh_row_id_is_rejected(self):
        duplicate = self.contrasts.loc[self.primary].iloc[[0]].copy()
        duplicate["row_id"] += "|duplicate-scientific-cell"
        changed = pd.concat([self.contrasts, duplicate], ignore_index=True)
        self.assertTrue(changed.row_id.is_unique)
        with self.assertRaisesRegex(ValueError, "complete unique frozen contrast/uncertainty key inventory"):
            self.write_and_check(changed)

    def test_carried_forward_contract_and_feature_identity_corruption_is_rejected(self):
        receipt = reconcile_paths(self.synthetic_bars, self.synthetic_events, self.synthetic_paths)
        self.assertEqual(receipt["status"], "passed")
        self.assertTrue(self.synthetic_paths.status.eq("censored").any())
        self.assertTrue(self.synthetic_paths.status.eq("completed").any())
        for field, value in (("contract", "ESM8"), ("signal_idx", 0),
                             ("ema20", 105.25), ("available_at", self.synthetic_paths.available_at.iloc[0] + pd.Timedelta(minutes=1))):
            changed = self.synthetic_paths.copy()
            changed.loc[changed.index[0], field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                reconcile_paths(self.synthetic_bars, self.synthetic_events, changed)


if __name__ == "__main__":
    unittest.main()
