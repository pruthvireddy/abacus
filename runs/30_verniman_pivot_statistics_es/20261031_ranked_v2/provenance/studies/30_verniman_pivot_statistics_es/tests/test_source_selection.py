import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from source_selection import review_threshold


class ThresholdReviewTests(unittest.TestCase):
    def row(self, text, **extra):
        return {"side": "bullish", "scenario_text": text, "source_text": "HVE100",
                "price_low": "100", "price_high": "100", "trigger_interpretation": None, **extra}

    def test_explicit_legacy_threshold_is_supported_from_source_not_blank_enum(self):
        row = self.row("If market moves above HVE100 with bullish internals, buy towards110.")
        row["scenario_text"] = "If market moves above HVE 100 with bullish internals, buy towards 110."
        result = review_threshold(row)
        self.assertEqual(result["decision"], "conditional_threshold_supported")
        self.assertNotIn("scenario_text", result)
        self.assertEqual(len(result["scenario_sha256"]), 64)

    def test_mirrored_bearish_condition_and_comma_decimal_price(self):
        result = review_threshold(self.row("If market remains below YVAH 1,000.25 with bearish internals, sell.",
                                           side="bearish", price_low="1000.25", price_high="1000.25"))
        self.assertEqual(result["decision"], "conditional_threshold_supported")

    def test_missing_wrong_side_wrong_first_price_and_range_remain_unresolved(self):
        for text in ["", "Pivot 100", "If market moves below HVE 100, buy.",
                     "If market moves above HVE 110 towards100.", "If market moves above HVE 100-110, buy.",
                     "If market moves above not HVE100, buy."]:
            with self.subTest(text=text):
                self.assertEqual(review_threshold(self.row(text))["decision"], "unresolved")

    def test_explicit_execution_interpretation_is_never_overridden(self):
        result = review_threshold(self.row("If market moves above HVE 100, buy.", trigger_interpretation="execution_reference"))
        self.assertEqual(result["reason"], "explicit_incompatible_source_interpretation")


if __name__ == "__main__":
    unittest.main()
