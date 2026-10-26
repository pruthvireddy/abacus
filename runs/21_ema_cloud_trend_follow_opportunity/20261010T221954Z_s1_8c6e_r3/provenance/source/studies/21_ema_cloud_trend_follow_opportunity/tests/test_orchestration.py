"""Guard fixtures enforce frozen identities and fresh-stage preservation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.execution import assert_stage, file_record, verify_record
from src.pipeline import _selected_paths


class ExecutionGuardTests(unittest.TestCase):
    def test_changed_source_bytes_fail_even_when_size_is_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.py"
            source.write_text("price=100\n")
            pin = file_record(source, root)
            self.assertEqual(verify_record(pin, root), source)
            source.write_text("price=999\n")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                verify_record(pin, root)

    def test_completed_identity_and_outside_stage_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "work/21_ema_cloud_trend_follow_opportunity/fresh"
            stage.mkdir(parents=True)
            assert_stage(stage, root)
            completed = root / "runs/21_ema_cloud_trend_follow_opportunity/fresh"
            completed.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "completed"):
                assert_stage(stage, root)
            with self.assertRaisesRegex(ValueError, "direct study work"):
                assert_stage(root / "runs/other", root)

    def test_relative_lock_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "unsafe"):
                verify_record({"path": "../source", "bytes": 0, "sha256": "0" * 64}, Path(temp))

    def test_example_paths_keep_signal_identity_and_exclude_reserved_prices(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / "tables").mkdir()
            times = pd.date_range("2021-01-01T04:54Z", periods=4, freq="3min")
            records = []
            for product in ("ES", "GC", "NQ"):
                for interval in (3, 5):
                    bars = pd.DataFrame({"timestamp": times, "available_at": times + pd.Timedelta(minutes=interval),
                        "signal_idx": range(4), "open": [100, 100, 999, 999], "high": [102, 102, 999, 999],
                        "low": [99, 99, 999, 999], "close": [101, 101, 999, 999], "ema20": 102., "ema50": 100.,
                        "usable": True, "quality_reason": "complete", "contract": "same"})
                    path = stage / f"{product}-{interval}.parquet"
                    bars.to_parquet(path, index=False)
                    records.append({**file_record(path), "product": product, "interval_minutes": interval, "role": "technical"})
            (stage / "events.manifest.json").write_text(json.dumps({"records": records}))
            selections = pd.DataFrame([{"product": "ES", "interval_minutes": 3, "selection_status": "selected",
                "signal_idx": 1, "selection_id": "fixed", "event_id": "event", "reference_price": 101., "example_class": "typical"}])
            selected = pd.read_parquet(_selected_paths(stage, selections))
            self.assertEqual(selected.relative_slot.tolist(), [-1, 0])
            self.assertEqual(selected.close.tolist(), [101, 101])
            self.assertEqual(selected.row_id.tolist(), ["fixed|slot=-1", "fixed|slot=0"])


if __name__ == "__main__":
    unittest.main()
