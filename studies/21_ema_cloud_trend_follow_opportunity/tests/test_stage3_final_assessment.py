"""The final interpretation is fixed before recent outcomes are authorized."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_stage3 import freeze_final_assessment
from src.execution import file_record


class FinalAssessmentTests(unittest.TestCase):
    def fixture(self, root):
        stage = Path(root)
        (stage / "tables").mkdir()
        (stage / "provenance").mkdir()
        (stage / "config.json").write_text(json.dumps({"primary_comparison_family": {"size": 12}}))
        rows = []
        for n, cell in enumerate((p, i, b) for p in ("ES", "GC", "NQ") for i in (3, 5) for b in ("fast", "slow")):
            low, high = ("", "") if n == 0 else (".1", ".2") if n < 4 else ("-.2", "-.1") if n < 6 else ("0", "0")
            rows.append(dict(product=cell[0], interval_minutes=cell[1], touch_mode=cell[2],
                horizon=15, direction="All", unit="atr", metric="terminal_delta", weighting="event",
                block_weeks=4, interval_kind="bonferroni12", ci_low=low, ci_high=high, row_id=str(n)))
        path = stage / "tables/S3-T14_final_effects.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        receipt = stage / "provenance/independent-final.json"
        receipt.write_text(json.dumps({"status": "passed", "phase": "final", "records": [file_record(path, stage)]}))
        return stage, path, receipt

    def test_full_family_null_identity_and_direction_are_frozen(self):
        with tempfile.TemporaryDirectory() as root:
            stage, _, _ = self.fixture(root)
            assessment = json.loads(freeze_final_assessment(stage).read_text())
            self.assertEqual(assessment["classification"], {"includes_zero": 6, "above_zero": 3, "below_zero": 2, "undefined": 1})
            self.assertEqual(len(assessment["primary_rows"]), 12)
            self.assertIn("do not establish executable profitability", assessment["conclusion"])
            with self.assertRaisesRegex(ValueError, "overwrite refused"):
                freeze_final_assessment(stage)

    def test_postverification_mutation_and_incomplete_family_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            stage, path, receipt = self.fixture(root)
            frame = pd.read_csv(path).iloc[:-1]
            frame.to_csv(path, index=False)
            with self.assertRaises(ValueError):
                freeze_final_assessment(stage)
            receipt.write_text(json.dumps({"status": "passed", "phase": "final", "records": [file_record(path, stage)]}))
            with self.assertRaisesRegex(ValueError, "twelve-cell"):
                freeze_final_assessment(stage)


if __name__ == "__main__":
    unittest.main()
