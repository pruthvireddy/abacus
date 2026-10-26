import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from abacus_bhishma.gc_ema_bands import band_values
from abacus_bhishma.feature_loader import load_gc_5m_release


class BandValuesTest(unittest.TestCase):
    def test_seed_and_population_dispersion(self):
        ema, sigma, lower = band_values(np.array([10., 11., 9., 12.]), 3, 3)
        self.assertAlmostEqual(ema[0], 10.)
        self.assertAlmostEqual(ema[1], 10.5)
        self.assertTrue(np.isnan(sigma[1]))
        expected_residuals = np.array([0., .5, -.75])
        self.assertAlmostEqual(sigma[2], expected_residuals.std(ddof=0))
        self.assertAlmostEqual(lower[2], ema[2] - 3 * sigma[2])

    def test_no_future_close_in_previous_band(self):
        a = band_values(np.arange(300, dtype=float))
        b = band_values(np.r_[np.arange(299, dtype=float), 10000.])
        for x, y in zip(a, b):
            np.testing.assert_allclose(x[:299], y[:299], equal_nan=True)

    def test_gc_loader_orders_partitions_and_pins_version(self):
        with TemporaryDirectory() as temp:
            base = (Path(temp) / "data/features/bars/5m"
                    / "feature_set=gc_ema_deviation_bands/version=1.0.0/product=GC")
            for year in (2026, 2025):
                path = base / f"year={year}" / "part-000.parquet"
                path.parent.mkdir(parents=True)
                pq.write_table(pa.table({"value": [year]}), path)
            values = load_gc_5m_release(temp, "gc_ema_deviation_bands", version="1.0.0", columns=["value"])
            self.assertEqual(values.column("value").to_pylist(), [2025, 2026])
            with self.assertRaises(ValueError):
                load_gc_5m_release(temp, "gc_ema_deviation_bands", version="latest")


if __name__ == "__main__":
    unittest.main()
