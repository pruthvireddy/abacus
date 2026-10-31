"""Hand-worked ranked moving-reference/recross/sequence checks."""
from copy import deepcopy
from datetime import timedelta
import importlib.util
from pathlib import Path
import sys
import unittest

from test_engine import fixture, at, rth_row

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import ranked_engine as ranked
import engine as core
sys.path.pop(0)


def build(data=None, **kwargs):
    data = data or fixture()
    return ranked.build_ranked_day(data["session_date"], data["contract"],
                                   data["minutes"], data["bars3"], data["bars5"],
                                   pivot=data["pivot"], pivot_matched=True,
                                   vwap_rth=True, **kwargs)


def events(result, reference="vwap", series="ema6", mode="rth"):
    return [row for row in result["events"] if row["reference"] == reference and row["series"] == series and mode in row["scopes"]]


def set_vwap(data, changes):
    changes = sorted((at(key), value) for key, value in changes.items())
    for row in data["minutes"]:
        options = [value for timestamp, value in changes if timestamp <= row["close_time"]]
        if options:
            row["vwap"] = options[-1]


class RankedCrossingTests(unittest.TestCase):
    def test_moving_line_alone_can_cross_ema_without_price_side_requirement(self):
        data = fixture(ema_changes={"09:30": 98.})
        set_vwap(data, {"09:33": 97.})
        result = build(data)
        ema = events(result)
        self.assertEqual(len(ema), 1)
        self.assertEqual(ema[0]["direction"], 1)
        self.assertEqual(ema[0]["crossing_value"], 98.)
        self.assertEqual(ema[0]["reference_line_value"], 97.)
        self.assertEqual(ema[0]["difference"], 1.)

    def test_price_may_remain_opposite_side_of_moving_reference(self):
        data = fixture(ema_changes={"09:33": 101.})
        result = build(data)
        row = events(result)[0]
        self.assertEqual(row["direction"], 1)
        self.assertEqual(row["price_side_relative_vwap"], -1)

    def test_equality_carries_state_unknown_clears_it(self):
        data = fixture(ema_changes={"09:33": 99., "09:36": 101., "09:39": 99., "09:42": 98., "09:45": 101.})
        result = build(data)
        self.assertEqual([row["direction"] for row in events(result)], [1, -1, 1])
        rth_row(data["minutes"], "09:41")["vwap_valid"] = False
        repeated = build(data)
        self.assertEqual([row["direction"] for row in events(repeated)], [1])
        # At 09:42 unknown clears the remembered side; 09:45 initializes.

    def test_missing_three_minute_observation_reinitializes(self):
        data = fixture(ema_changes={"09:33": 101., "09:39": 98.})
        data["bars3"] = [r for r in data["bars3"] if r["open_time"] != at("09:33")]
        result = build(data)
        self.assertEqual(len(events(result)), 1)
        first = [r for r in result["recrosses"] if r["reference"] == "vwap" and r["horizon"] == "15m"][0]
        self.assertIsNone(first["no_recross"])
        self.assertEqual(first["unknown_reason"], "missing_reference_observation")

    def test_opening_seed_not_a_cross_and_section_state_does_not_reset(self):
        data = fixture(ema_changes={"09:30": 101., "10:30": 98., "10:33": 101., "12:30": 98., "12:33": 101.})
        result = build(data)
        ema = events(result)
        self.assertEqual([row["section"] for row in ema], ["opening_range", "new_york_am", "new_york_am", "new_york_pm"])
        self.assertEqual([row["ordinal"] for row in ema], [1, 2, 3, 4])
        self.assertEqual([row["ordinal_group"] for row in ema], ["1", "2", "3+", "3+"])
        self.assertEqual([row["first_per_section"] for row in ema], [True, True, False, True])

    def test_globex_anchor_never_uses_pre_anchor_reference(self):
        data = fixture(ema_changes={"09:30": 101.})
        # All EMA values are below 99 overnight until 09:30. First 18:03
        # observation is initialization, independent of yesterday's VWAP.
        result = build(data, vwap_globex=True)
        self.assertFalse(any(core._dt(row["observed_at"]) == data["bars3"][0]["close_time"] for row in events(result, mode="globex")))
        merged = [row for row in result["events"] if set(row["scopes"]) == {"rth", "globex"}]
        self.assertEqual(len({row["event_id"] for row in result["events"]}), len(result["events"]))
        for row in merged:
            self.assertIn(ranked.MATCHED, row["cohorts_by_mode"]["rth"])
            self.assertEqual(row["cohorts_by_mode"]["globex"], [ranked.VWAP_GLOBEX])

    def test_globex_crossing_state_carries_only_explicit_historical_pause(self):
        data = fixture(ema_changes={"16:33": 101.})
        data["bars3"] = [row for row in data["bars3"] if not at("16:15") <= row["open_time"] < at("16:30")]
        result = build(data, vwap_globex=True)
        self.assertEqual([r["observed_at"] for r in events(result, mode="globex")], [core._iso(core._dt(at("16:33")))])
        self.assertTrue(ranked._known_pause("2020-01-09", core._dt(at("16:15")), core._dt(at("16:30"))))
        self.assertFalse(ranked._known_pause("2022-01-09", core._dt(at("16:15")), core._dt(at("16:30"))))

    def test_full_globex_membership_can_exist_without_rth_membership(self):
        data = fixture(ema_changes={"09:33": 101.})
        result = ranked.build_ranked_day(data["session_date"], data["contract"], data["minutes"], data["bars3"], data["bars5"], vwap_globex=True)
        self.assertEqual({r["session_mode"] for r in result["daily"]}, {"globex"})
        self.assertEqual(result["sections"], [])
        self.assertEqual(result["outcomes"], [])
        self.assertEqual(result["transitions"], [])

    def test_pivot_crosses_match_original_engine(self):
        data = fixture(price_changes={"09:33": 102., "10:30": 98., "12:33": 103.},
                       ema_changes={"09:36": 101., "10:33": 99., "12:39": 102.})
        original = core.analyze_day(**data)
        result = build(data)
        for series, key in (("price", "price_events"), ("ema6", "ema_events")):
            self.assertEqual([(e["observed_at"], e["direction"]) for e in events(result, "pivot", series)],
                             [(e["observed_at"], e["direction"]) for e in original[key]])

    def test_zero_exposure_is_null_but_valid_zero_is_zero(self):
        data = fixture()
        result = build(data)
        row = next(r for r in result["daily"] if r["reference"] == "vwap" and r["series"] == "ema6")
        self.assertEqual((row["crosses"], row["observed_hours"], row["crosses_per_hour"]), (0, 6.5, 0.))
        self.assertEqual(row["count_bucket"], "0")
        for bar in data["bars3"]:
            bar["ema6_ready"] = False
        result = build(data)
        row = next(r for r in result["daily"] if r["reference"] == "vwap" and r["series"] == "ema6")
        self.assertEqual(row["observed_hours"], 0.)
        self.assertIsNone(row["crosses_per_hour"])

    def test_vwap_only_without_pivot_retains_unknown_configuration(self):
        data = fixture(ema_changes={"09:33": 101.})
        result = ranked.build_ranked_day(data["session_date"], data["contract"], data["minutes"], data["bars3"], data["bars5"], vwap_rth=True)
        self.assertEqual({r["reference"] for r in result["events"]}, {"vwap"})
        self.assertEqual(result["daily"][0]["opening_configuration"], "unknown")
        self.assertIsNone(result["snapshots"][0]["pivot"])


class RankedPathTests(unittest.TestCase):
    def test_ema_recross_differs_from_price_reversal(self):
        data = fixture(price_changes={"09:33": 102., "09:36": 98.}, ema_changes={"09:33": 101., "10:06": 98.})
        result = build(data)
        rows = [r for r in result["recrosses"] if r["reference"] == "pivot" and r["event_id"] == events(result, "pivot")[0]["event_id"]]
        self.assertEqual({r["horizon"]: r["no_recross"] for r in rows}, {"15m": True, "30m": True, "60m": False})
        self.assertEqual(rows[0]["next_recross_minutes"], 33.)

    def test_late_recross_horizon_is_censored_even_with_early_reverse(self):
        data = fixture(ema_changes={"15:45": 101., "15:48": 98.})
        result = build(data)
        first = events(result)[0]
        rows = [r for r in result["recrosses"] if r["event_id"] == first["event_id"]]
        self.assertEqual({r["horizon"]: r["no_recross"] for r in rows}, {"15m": False, "30m": None, "60m": None})
        last = events(result)[1]
        rows = [r for r in result["recrosses"] if r["event_id"] == last["event_id"]]
        self.assertTrue(all(r["no_recross"] is None for r in rows))

    def test_horizon_path_excludes_signal_extremes_and_stays_in_rth(self):
        data = fixture(ema_changes={"09:33": 101., "15:48": 98.})
        rth_row(data["minutes"], "09:30")["high"] = 1000.
        result = build(data)
        row = next(r for r in result["outcomes"] if r["event_id"] == events(result)[0]["event_id"] and r["horizon"] == "30m")
        self.assertEqual(row["favorable_excursion_points"], .25)
        late = next(r for r in result["outcomes"] if r["event_id"] == events(result)[1]["event_id"] and r["horizon"] == "30m")
        self.assertIsNone(late["displacement_points"])
        self.assertEqual(late["unknown_reason"], "outside_rth")

    def test_crossing_snapshots_are_native_completed_and_stably_linked(self):
        data = fixture(ema_changes={"09:33": 101.})
        rth_row(data["bars5"], "09:30").update(ema20=900., ema50=800.)
        result = build(data)
        index = {s["snapshot_id"]: s for s in result["snapshots"]}
        event = events(result)[0]
        snapshot = index[event["feature_snapshot_id"]]
        self.assertEqual(snapshot["ema20"], 102.)
        self.assertEqual(snapshot["cloud_source_at"], core._iso(core._dt(at("09:30"))))
        self.assertEqual(snapshot["snapshot_at"], event["observed_at"])
        for row in result["outcomes"]:
            self.assertEqual(index[row["feature_snapshot_id"]]["snapshot_at"], row["reference_at"])

    def test_sequence_distinguishes_second_before_recross(self):
        data = fixture(ema_changes={"09:33": 99.5, "09:39": 101., "09:42": 99.5, "09:45": 98.})
        result = build(data)
        sequence = result["sequences"][0]
        self.assertEqual(sequence["first_reference"], "vwap")
        self.assertEqual(sequence["result"], "second_before_recross")
        pivot = next(r for r in result["sequences"] if r["first_reference"] == "pivot")
        self.assertEqual(pivot["result"], "already_beyond_other")

    def test_sequence_simultaneous_is_not_ordered(self):
        result = build(fixture(ema_changes={"09:33": 101.}))
        self.assertEqual({r["result"] for r in result["sequences"]}, {"simultaneous"})
        self.assertTrue(all(r["second_before_recross"] is None for r in result["sequences"]))

    def test_sequence_equal_other_line_is_separate_from_at_risk(self):
        result = build(fixture(ema_changes={"09:33": 100., "09:39": 101.}))
        first = next(r for r in result["sequences"] if r["event_id"] == events(result)[0]["event_id"])
        self.assertEqual(first["result"], "other_equal_at_start")
        self.assertIsNone(first["second_before_recross"])

    def test_sequence_endpoint_tie_does_not_infer_order(self):
        data = fixture(ema_changes={"09:33": 99.5, "09:39": 101.})
        set_vwap(data, {"09:39": 102.})
        result = build(data)
        # At 09:39 EMA crosses fixed pivot up while VWAP moves above EMA:
        # the first-reference reverse and second-reference cross are tied.
        first = next(r for r in result["sequences"] if r["event_id"] == events(result)[0]["event_id"])
        self.assertEqual(first["result"], "simultaneous_endpoint")
        self.assertIsNone(first["second_before_recross"])

    def test_sequence_recross_first_and_late_censoring(self):
        result = build(fixture(ema_changes={"09:33": 99.5, "09:36": 98., "15:48": 99.5}))
        self.assertEqual(result["sequences"][0]["result"], "recross_first")
        last = result["sequences"][-1]
        self.assertEqual(last["result"], "censored_no_endpoint")

    def test_fixed_bands_and_opening_ordering(self):
        self.assertEqual([ranked.distance_band(x) for x in (None, 0, 4.999, 5, 14.999, 15, 29.999, 30)],
                         ["unknown", "<5", "<5", "5–<15", "5–<15", "15–<30", "15–<30", "≥30"])
        self.assertEqual(ranked.configuration(101., 100., 99.), "above_both")
        self.assertEqual(ranked.configuration(98., 100., 99.), "below_both")
        self.assertEqual(ranked.configuration(99.5, 100., 99.), "between")
        self.assertEqual(ranked.configuration(100., 100., 99.), "equal")

    def test_section_persistence_includes_opening_through_pm(self):
        result = build(fixture(ema_changes={"10:30": 101., "12:30": 98., "16:00": 101.}))
        rows = [r for r in result["transitions"] if r["reference"] == "pivot" and r["metric"] == "ema6_side"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["persistent"] for r in rows], [False, False, True])

    def test_cloud_transition_records_true_bullish_bearish_reversal(self):
        data = fixture()
        for row in data["bars5"]:
            if row["close_time"] > at("10:30"):
                row.update(ema20=99., ema50=101.)
        result = build(data)
        rows = [r for r in result["transitions"] if r["reference"] == "pivot" and r["metric"] == "cloud_order"]
        self.assertEqual([r["reversed"] for r in rows], [True, False, True])

    def test_cloud_support_requires_order_and_both_native_slopes(self):
        snapshot = {"cloud_order": "bullish", "ema20_slope_15m": 1., "ema50_slope_15m": 2.}
        self.assertEqual(ranked.cloud_support(snapshot, 1), "support")
        self.assertEqual(ranked.cloud_support(snapshot, -1), "opposition")
        self.assertEqual(ranked.cloud_support({**snapshot, "ema50_slope_15m": -1.}, 1), "mixed")
        self.assertEqual(ranked.cloud_support({**snapshot, "ema50_slope_15m": None}, 1), "unknown")


if __name__ == "__main__":
    unittest.main()
