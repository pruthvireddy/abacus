"""Boundary checks for the explicitly exploratory local-clock labels."""

from pathlib import Path
import sys
import unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from supplement import clock_label


class SupplementClockTest(unittest.TestCase):
    def test_every_boundary_and_gap(self):
        expected={0:"asia",5:"asia",6:"london",17:"london",
                  18:"pre_ny_gap",19:"ny",31:"ny",32:"post_ny_gap",
                  33:"post_ny_gap",36:"pre_asia_gap",39:"pre_asia_gap",
                  40:"asia",47:"asia"}
        for halfhour,label in expected.items():
            self.assertEqual(clock_label(halfhour),label)

    def test_dst_local_clock_label_stability(self):
        for timestamp in ("2024-01-10T00:00:00Z","2024-07-10T23:00:00Z"):
            local=pd.Timestamp(timestamp).tz_convert("America/New_York")
            self.assertEqual(clock_label(local.hour*2+local.minute//30),"pre_asia_gap")


if __name__=="__main__":unittest.main()
