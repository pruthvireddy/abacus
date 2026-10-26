"""Tests execute the scalar bodies from the delivered Pine source.
This small translator is not a Pine compiler or series-runtime emulator.
"""
from pathlib import Path
import re
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PINE_PATH = Path(__file__).resolve().parents[1] / "pine/camarilla_pivot_levels.pine"
SOURCE = PINE_PATH.read_text()

def scalar_helper(name, extra=None):
    lines = SOURCE.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(name + "("))
    signature = lines[start].split("(", 1)[1].rsplit(")", 1)[0]
    arguments = [parameter.strip().split()[-1] for parameter in signature.split(",")]
    body = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        statement = line.split("//", 1)[0].rstrip()
        if not statement.strip():
            continue
        statement = re.sub(r"^(\s*)(?:bool|int|float) ", r"\1", statement)
        statement = statement.replace(":=", "=").replace("else if ", "elif ")
        statement = re.sub(r"\bpass\b", "passed", statement)
        statement = re.sub(r"\btrue\b", "True", statement)
        statement = re.sub(r"\bfalse\b", "False", statement)
        statement = re.sub(r"\bna\(", "_missing(", statement)
        statement = re.sub(r"\bna\b", "None", statement)
        if statement.lstrip().startswith(("if ", "elif ")) or statement.strip() == "else":
            statement += ":"
        body.append(statement)
    # Pine returns its last expression, which these helpers leave at base indent.
    if not body[-1].startswith("    ") or body[-1].startswith("        "):
        raise ValueError("Expected a final base-indented scalar return")
    body[-1] = "    return " + body[-1].strip()
    namespace = {"_missing": lambda value: value is None, "math": type("Math", (), {"max": max, "min": min, "abs": abs})}
    namespace.update(extra or {})
    exec("def " + name + "(" + ", ".join(arguments) + "):\n" + "\n".join(body), namespace)
    return namespace[name]


REJECT = scalar_helper("csReject")
CLOUD = scalar_helper("csCloudPass")
SIZE = scalar_helper("csSizePass")
ACCEPT = scalar_helper("csAccept")
EXCURSIONS = scalar_helper("csExcursions")
ENTRY = scalar_helper("csEntryAllowed")

CLOCK = scalar_helper("csClockPass")
def ny_part(part):
    return lambda at, tz: getattr(datetime.fromtimestamp(at / 1000, ZoneInfo(tz)), part)
def pine_timestamp(tz, year, month, day, hour, minute):
    return int(datetime(year,month,day,hour,minute,tzinfo=ZoneInfo(tz)).timestamp()*1000)
def pine_dayofweek(at, tz):
    return (datetime.fromtimestamp(at/1000,ZoneInfo(tz)).weekday()+1)%7+1
pine_dayofweek.monday = 2
TIME_ENV = dict(CS_TZ="America/New_York",year=ny_part("year"),month=ny_part("month"),
                dayofmonth=ny_part("day"),timestamp=pine_timestamp,dayofweek=pine_dayofweek)
DATE_KEY = scalar_helper("csDateKey",TIME_ENV)
WEEK_KEY = scalar_helper("csWeekKey",dict(TIME_ENV,csDateKey=DATE_KEY))


class StatisticsTest(unittest.TestCase):
    def reject(self, direction=1, **overrides):
        values = dict(candleOpen=101., candleHigh=103., candleLow=99.,
                      candleClose=102., previousClose=102., level=100.,
                      atrValue=2., tick=.25, tolerance=0., approachRequired=True,
                      bodyRequired=True, wickRatio=0., approachAtr=0.,
                      maxPenetration=0.)
        values.update(overrides)
        return REJECT(direction, **values)

    def test_rejection_requires_touch_reclaim_and_body(self):
        self.assertTrue(self.reject())
        self.assertFalse(self.reject(candleLow=100.25))
        self.assertFalse(self.reject(candleClose=100.))
        self.assertFalse(self.reject(candleClose=100.5))
        self.assertTrue(self.reject(candleClose=100.5, bodyRequired=False))
        self.assertFalse(self.reject(previousClose=100.))
        self.assertFalse(self.reject(candleOpen=99.))
        self.assertTrue(self.reject(candleOpen=99., approachRequired=False))

    def test_tolerance_changes_contact_not_required_close(self):
        self.assertTrue(self.reject(candleLow=100.25, tolerance=1))
        self.assertFalse(self.reject(candleLow=100.26, tolerance=1))
        self.assertFalse(self.reject(candleClose=100., bodyRequired=False, tolerance=10))

    def test_wick_distance_penetration_thresholds(self):
        self.assertTrue(self.reject(wickRatio=2, approachAtr=1, maxPenetration=.5))
        self.assertFalse(self.reject(wickRatio=2.01))
        self.assertFalse(self.reject(approachAtr=1.01))
        self.assertFalse(self.reject(maxPenetration=.49))
        self.assertFalse(self.reject(candleClose=101., wickRatio=9, bodyRequired=False))

    def test_short_is_symmetric(self):
        self.assertTrue(self.reject(-1, candleOpen=99., candleHigh=101.,
                                    candleLow=97., candleClose=98., previousClose=98.))
        self.assertFalse(self.reject(-1, candleOpen=99., candleHigh=101.,
                                     candleLow=97., candleClose=100., previousClose=98.))

    def test_cloud_filter_variants_and_equality(self):
        self.assertTrue(CLOUD(1, 105, 102, 100, "Cloud alignment"))
        self.assertTrue(CLOUD(-1, 95, 98, 100, "Alignment + price outside"))
        self.assertFalse(CLOUD(1, 101, 102, 100, "Alignment + price outside"))
        self.assertTrue(CLOUD(1, 105, 100, 102, "Price outside both EMAs"))
        self.assertFalse(CLOUD(1, 105, 100, 100, "Cloud alignment"))
        self.assertFalse(CLOUD(-1, 100, 98, 100, "Price outside both EMAs"))
        self.assertTrue(CLOUD(1, 1, 2, 3, "None"))

    def test_oversized_candle_uses_prior_atr(self):
        self.assertTrue(SIZE(2, 20, 10))
        self.assertFalse(SIZE(2, 20.01, 10))
        self.assertFalse(SIZE(2, 20, None))
        self.assertFalse(SIZE(2, 20, 0))
        self.assertTrue(SIZE(0, 20, None))

    def test_cooldown_suppresses_exactly_n_candles(self):
        self.assertTrue(ACCEPT(True, 100, None, 10))
        for i in range(101, 111):
            self.assertFalse(ACCEPT(True, i, 100, 10))
        self.assertTrue(ACCEPT(True, 111, 100, 10))
        self.assertTrue(ACCEPT(True, 101, 100, 0))
        self.assertFalse(ACCEPT(False, 111, 100, 10))

    def test_entry_requires_following_contiguous_full_candle(self):
        self.assertTrue(ENTRY(1, 1000, 1000, True, True, True))
        for arguments in [(0,1000,1000,True,True,True),
                          (1,1000,1001,True,True,True),
                          (1,1000,1000,False,True,True),
                          (1,1000,1000,True,False,True),
                          (1,1000,1000,True,True,False)]:
            self.assertFalse(ENTRY(*arguments))

    def test_excursions_direction_and_frozen_normalization(self):
        self.assertEqual(EXCURSIONS(1, 100, 98, 106, 102, 2), [3,1,1])
        self.assertEqual(EXCURSIONS(-1, 100, 98, 106, 102, 2), [1,3,-1])
        self.assertEqual(EXCURSIONS(1, 100, 101, 102, 101, 2), [1,0,.5])
        self.assertEqual(EXCURSIONS(-1, 100, 98, 99, 99, 2), [1,0,.5])
        self.assertEqual(EXCURSIONS(1, 100, 98, 102, 100, 2), [1,1,0])

    def test_signal_bar_extremes_do_not_enter_path(self):
        # Next open can gap in price while timestamps remain contiguous.
        signal_extremes = (50, 200)
        entry, lows, highs = 105, [104,103,102], [107,108,110]
        self.assertEqual(EXCURSIONS(1, entry, min(lows), max(highs), 109, 2),
                         [2.5,1.5,2])
        self.assertNotEqual(EXCURSIONS(1, entry, *signal_extremes, 109, 2),
                            [2.5,1.5,2])
        self.assertIn("CsPath.new(cs_pending_direction, open, cs_pending_atr, open, open, 0", SOURCE)
        self.assertIn("cs_pending_atr := cs_atr", SOURCE)

    def test_horizon_denominators_and_ties(self):
        # Oracle: two normalized outcomes, equal excursions and flat close remain in N.
        events = [EXCURSIONS(1,100,98,106,102,2), EXCURSIONS(-1,100,98,102,100,2)]
        self.assertEqual(sum(x[0] for x in events)/2, 2)
        self.assertEqual(sum(x[1] for x in events)/2, 1)
        self.assertEqual(sum(x[2] for x in events)/2, .5)
        self.assertEqual(sum(x[2]>0 for x in events)/2, .5)
        self.assertEqual(sum(x[0]>x[1] for x in events)/2, .5)
        self.assertIn("if path.age == array.get(cs_horizons, h)", SOURCE)
        self.assertIn("eventDelta > 0 ? 1 : 0", SOURCE)
        self.assertIn("eventMfe > eventMae ? 1 : 0", SOURCE)
        self.assertIn("cs_interrupted_paths += 1", SOURCE)
        self.assertNotIn("cs_samples, h, array.get(cs_samples, h) -", SOURCE)

    def test_entry_window_boundaries_and_overnight(self):
        self.assertFalse(CLOCK(569,570,690,True,True,True))
        self.assertTrue(CLOCK(570,570,690,True,True,True))
        self.assertTrue(CLOCK(689,570,690,True,True,True))
        self.assertFalse(CLOCK(690,570,690,True,True,True))
        self.assertFalse(CLOCK(600,570,690,True,True,False))
        self.assertTrue(CLOCK(600,570,690,False,False,False))
        self.assertTrue(CLOCK(23*60,18*60,6*60,True,False,True))
        self.assertTrue(CLOCK(5*60,18*60,6*60,True,False,True))
        self.assertFalse(CLOCK(6*60,18*60,6*60,True,False,True))
        self.assertTrue(CLOCK(1,570,570,True,False,True))

    def test_actual_pine_week_key_across_dst_year_and_utc_boundary(self):
        fixtures = [("2026-03-09T03:30:00+00:00","2026-03-02"),
                    ("2026-03-09T04:00:00+00:00","2026-03-09"),
                    ("2026-11-02T04:30:00+00:00","2026-10-26"),
                    ("2026-11-02T05:00:00+00:00","2026-11-02"),
                    ("2027-01-01T15:00:00+00:00","2026-12-28")]
        for at, monday in fixtures:
            ms=int(datetime.fromisoformat(at).timestamp()*1000)
            self.assertEqual(datetime.fromtimestamp(WEEK_KEY(ms)/1000,timezone.utc).strftime("%Y-%m-%d"),monday)

    def test_causal_series_and_week_integration(self):
        self.assertIn('[high[1], low[1], close[1]]', SOURCE)
        self.assertIn("cs_stats_fast = ema_cloud_is_htf ? ema_cloud_confirmed_fast", SOURCE)
        self.assertIn("csSizePass(cs_max_range, ta.tr(true), cs_atr[1])", SOURCE)
        self.assertIn("csWindowPass(time_close, cs_session, cs_use_session, cs_weekdays)", SOURCE)
        self.assertIn("int w = path.weekIndex", SOURCE)
        self.assertIn("cs_pending_week := array.size(cs_weeks) - 1", SOURCE)
        self.assertIn("csDateKey(at) - daysSinceMonday * 86400000", SOURCE)


if __name__ == "__main__":
    unittest.main()
