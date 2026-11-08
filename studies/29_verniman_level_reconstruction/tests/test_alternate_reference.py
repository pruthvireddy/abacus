"""Synthetic checks for a distinct, frozen prior-value alternate reference."""
from pathlib import Path
import sys
import unittest

# Root integrates the helper into the study model. The fallback lets this
# staged file run independently before it is copied into the study tests.
_study_src = Path(__file__).resolve().parents[1] / "src"
if _study_src.is_dir():
    sys.path.insert(0, str(_study_src))
    from pivot_model import alternate_reference
else:
    from alternate_model_addition import alternate_reference

HOLD = "Hold higher auction"
BALANCED = "Balanced fallback — no unique directional divider"


class AlternateReferenceTests(unittest.TestCase):
    def select(self, primary=96, reason="Prior-value reclaim boundary",
               yvah=104, ypoc=100, yval=96, price=94):
        return alternate_reference(primary, reason, yvah, ypoc, yval, price)

    def test_higher_auction_uses_prior_value_high(self):
        self.assertEqual(self.select(primary=112, reason=HOLD, price=114),
                         (104, "YVAH"))

    def test_higher_auction_skips_primary_equal_to_value_high(self):
        self.assertEqual(self.select(primary=104, reason=HOLD), (100, "YPOC"))

    def test_higher_auction_skips_duplicated_high_and_poc(self):
        self.assertEqual(self.select(primary=104, reason=HOLD, ypoc=104),
                         (96, "YVAL"))

    def test_reclaim_boundary_uses_value_center(self):
        self.assertEqual(self.select(), (100, "YPOC"))

    def test_overnight_shift_lower_uses_value_center(self):
        self.assertEqual(self.select(reason="Overnight value shifted lower"),
                         (100, "YPOC"))

    def test_lower_boundary_skips_duplicate_center(self):
        self.assertEqual(self.select(ypoc=96), (104, "YVAH"))

    def test_overnight_shift_higher_uses_value_center(self):
        self.assertEqual(self.select(primary=104, reason="Overnight value shifted higher"),
                         (100, "YPOC"))

    def test_prior_boundary_fallback_uses_value_center(self):
        self.assertEqual(self.select(primary=104, reason="Prior-value boundary fallback"),
                         (100, "YPOC"))

    def test_upper_boundary_skips_duplicate_center(self):
        self.assertEqual(self.select(primary=104, ypoc=104), (96, "YVAL"))

    def test_balanced_uses_closer_lower_boundary(self):
        self.assertEqual(self.select(primary=100, reason=BALANCED, price=98.5),
                         (96, "YVAL"))

    def test_balanced_uses_closer_upper_boundary(self):
        self.assertEqual(self.select(primary=100, reason=BALANCED, price=102),
                         (104, "YVAH"))

    def test_balanced_equal_distance_chooses_lower_price(self):
        self.assertEqual(self.select(primary=100, reason=BALANCED, price=100),
                         (96, "YVAL"))

    def test_balanced_skips_boundary_equal_to_primary(self):
        self.assertEqual(self.select(primary=100, reason=BALANCED, ypoc=100,
                                     yval=100, price=100), (104, "YVAH"))
        self.assertEqual(self.select(primary=100, reason=BALANCED, ypoc=100,
                                     yvah=100, price=100), (96, "YVAL"))

    def test_all_value_references_equal_primary_produce_no_alternate(self):
        for reason in (HOLD, BALANCED, "Prior-value reclaim boundary",
                       "Overnight value shifted higher"):
            with self.subTest(reason=reason):
                self.assertEqual(self.select(primary=100, yvah=100, ypoc=100,
                                             yval=100, reason=reason), (None, "na"))

    def test_missing_required_numeric_input_produces_no_alternate(self):
        valid = dict(primary=96, reason="Prior-value reclaim boundary",
                     yvah=104, ypoc=100, yval=96, price=94)
        for field in ("primary", "yvah", "ypoc", "yval", "price"):
            with self.subTest(field=field):
                self.assertEqual(alternate_reference(**(valid | {field: None})),
                                 (None, "na"))

    def test_nonfinite_required_input_produces_no_alternate(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for field in ("primary", "yvah", "ypoc", "yval", "price"):
                with self.subTest(value=value, field=field):
                    self.assertEqual(self.select(**{field: value}), (None, "na"))

    def test_missing_reason_produces_no_alternate(self):
        self.assertEqual(self.select(reason=None), (None, "na"))
        self.assertEqual(self.select(reason=""), (None, "na"))

    def test_unrecognized_primary_without_matching_reference_is_unavailable(self):
        self.assertEqual(self.select(primary=101, reason="unrecognized"),
                         (None, "na"))

    def test_no_price_snapping_or_averaging(self):
        self.assertEqual(self.select(primary=96.25, yval=96.25,
                                     ypoc=100.75, yvah=104.5), (100.75, "YPOC"))

    def test_primary_and_frozen_snapshot_are_not_modified(self):
        snapshot = dict(primary=100, reason=BALANCED, yvah=104,
                        ypoc=100, yval=96, price=100)
        original = snapshot.copy()
        self.assertEqual(alternate_reference(**snapshot), (96, "YVAL"))
        self.assertEqual(snapshot, original)

    def test_radically_different_later_paths_do_not_change_cutoff_alternate(self):
        frozen = dict(primary=100, reason=BALANCED, yvah=104,
                      ypoc=100, yval=96, price=100)
        paths = ((1, 20000, 0.25), (100, 100, 100), (10000, 2, 15000))
        selected = alternate_reference(**frozen)
        for later_path in paths:
            # The API takes the frozen terminal P, never the latest chart close.
            for later_close in later_path:
                self.assertEqual(alternate_reference(**frozen), selected)
            self.assertEqual(frozen["price"], 100)
        self.assertEqual(selected, (96, "YVAL"))


if __name__ == "__main__":
    unittest.main()
