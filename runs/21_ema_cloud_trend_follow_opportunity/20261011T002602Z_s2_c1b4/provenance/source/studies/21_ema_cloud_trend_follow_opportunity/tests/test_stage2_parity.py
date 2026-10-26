import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage2_parity import DUAL_FIELDS, TABLE_NAMES, compare_baseline, compare_frames, verify_dual_outcomes


class ExactParityTest(unittest.TestCase):
    def test_null_false_zero_and_arm_state_differences_are_detected(self):
        baseline = pd.DataFrame(dict(event_id=["A", "B", "C"], favorable=[None, False, True], armed_before=[True, False, True], mfe=[np.nan, 0., 2.]))
        same = baseline.copy()
        same["stage"] = 2
        same["shared_episode_id"] = "new metadata"
        self.assertEqual(compare_frames(baseline, same, keys=["event_id"])["mismatch_count"], 0)
        same.loc[0, "favorable"] = False
        same.loc[1, "favorable"] = 0
        same.loc[2, "armed_before"] = False
        self.assertEqual(compare_frames(baseline, same, keys=["event_id"])["mismatch_count"], 3)
        same = baseline.copy()
        same.loc[2, "mfe"] += 1e-12
        self.assertEqual(compare_frames(baseline, same, keys=["event_id"])["mismatch_count"], 1)

    def test_equal_headline_counts_do_not_hide_changed_ids_or_missing_fields(self):
        old = pd.DataFrame(dict(event_id=["A", "B"], accepted=[True, True], suppression_reason=["accepted"] * 2))
        changed = old.copy()
        changed.loc[1, "event_id"] = "C"
        self.assertGreater(compare_frames(old, changed, keys=["event_id"])["mismatch_count"], 0)
        self.assertGreater(compare_frames(old, old.drop(columns="suppression_reason"), keys=["event_id"])["mismatch_count"], 0)

    def test_manifest_bytes_and_every_saved_table_value_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root / "old", root / "new"
            old.mkdir(); new.mkdir()
            baseline = pd.DataFrame(dict(product=["ES"] * 2, interval_minutes=[5] * 2,
                timestamp=pd.date_range("2019-01-01", periods=2, freq="5min", tz="UTC"), armed_before=[False, True],
                accepted=[False, True], episode_id=[1, 1]))
            long = pd.concat([baseline.assign(touch_mode="fast"), baseline.assign(touch_mode="slow")], ignore_index=True)
            for folder, frame in ((old, baseline), (new, long)):
                path = folder / "technical.parquet"
                frame.to_parquet(path, index=False)
                record = dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              role="technical", product="ES", interval_minutes=5)
                (folder / "events.manifest.json").write_text(json.dumps(dict(records=[record])))
                for name in TABLE_NAMES:
                    pd.DataFrame(dict(row_id=["same scientific key"], mean_terminal_delta=[.12345678901234567],
                        completed=[2], ci_low=[-.1], ci_high=[.4])).to_csv(folder / name, index=False, float_format="%.17g")
            receipt = compare_baseline(old / "events.manifest.json", new / "events.manifest.json", old, new)
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["table_artifacts_compared"], 9)
            table = new / TABLE_NAMES[2]
            table.write_text(table.read_text().replace("0.12345678901234566", "0.12345678901234567"))
            if compare_baseline(old / "events.manifest.json", new / "events.manifest.json", old, new)["status"] == "passed":
                table.write_text(table.read_text().replace(".123456", ".123457"))
            self.assertEqual(compare_baseline(old / "events.manifest.json", new / "events.manifest.json", old, new)["status"], "failed")
            (new / "technical.parquet").write_bytes(b"drift")
            with self.assertRaisesRegex(ValueError, "byte identity"):
                compare_baseline(old / "events.manifest.json", new / "events.manifest.json", old, new)

    def test_all_same_bar_outcome_fields_and_censored_nulls_must_agree(self):
        records = []
        for event_id in ("F", "S"):
            for horizon in (5, 15):
                row = {field: None for field in DUAL_FIELDS}
                row.update(event_id=event_id, horizon=horizon, status="completed" if horizon == 5 else "censored",
                    censor_reason="" if horizon == 5 else "development_endpoint", mfe=4. if horizon == 5 else np.nan,
                    mae=2. if horizon == 5 else np.nan, terminal_delta=1. if horizon == 5 else np.nan,
                    favorable=True if horizon == 5 else None)
                records.append(row)
        outcomes = pd.DataFrame(records)
        union = pd.DataFrame(dict(accepted_membership=["both"], union_id=["U"], fast_event_id=["F"], slow_event_id=["S"]))
        result = verify_dual_outcomes(outcomes, union)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["compared_horizon_rows"], 2)
        outcomes.loc[outcomes.event_id.eq("F") & outcomes.horizon.eq(15), "favorable"] = False
        self.assertEqual(verify_dual_outcomes(outcomes, union)["mismatch_count"], 1)
        outcomes = outcomes.loc[~(outcomes.event_id.eq("F") & outcomes.horizon.eq(15))]
        self.assertEqual(verify_dual_outcomes(outcomes, union)["status"], "failed")
        self.assertEqual(verify_dual_outcomes(outcomes.iloc[:0], union)["status"], "failed")


if __name__ == "__main__": unittest.main()
