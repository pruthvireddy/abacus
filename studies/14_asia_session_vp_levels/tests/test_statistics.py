import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.statistics import development_quintiles,volatility_bin,moving_week_mean_interval,support


class StatisticsTests(unittest.TestCase):
    def test_only_development_defines_quintiles(self):
        cutoff=development_quintiles([1,2,3,4,1000],[2020,2021,2022,2023,2024])
        np.testing.assert_allclose(cutoff,[1.6,2.2,2.8,3.4])
        self.assertEqual(volatility_bin([1,3,np.nan],cutoff).tolist(),[0,3,-1])

    def test_week_blocks_pairing_empty_weeks_and_reproducibility(self):
        weeks=['2024-01-01','2024-01-01','2024-01-15','2024-01-22']
        effect=np.array([2.,2.,2.,2.])
        result=moving_week_mean_interval(weeks,effect)
        self.assertEqual(result['calendar_weeks'],4)
        self.assertEqual(result['weeks'],3)
        self.assertEqual((result['estimate'],result['lower'],result['upper']),(2,2,2))
        self.assertEqual(result,moving_week_mean_interval(weeks,effect))

    def test_sparse_and_null_intervals_retained(self):
        self.assertIsNone(moving_week_mean_interval(['2024-01-01'],[3])['lower'])
        self.assertIsNone(moving_week_mean_interval(['2024-01-01'],[np.nan])['estimate'])
        self.assertEqual(support(50,30,12),'adequate')
        self.assertEqual(support(1000,29,20),'low_support')


if __name__=='__main__':unittest.main()
