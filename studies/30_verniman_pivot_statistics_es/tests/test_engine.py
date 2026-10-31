"""Hand-worked synthetic event/path checks; no retained market inputs."""

from copy import deepcopy
from datetime import datetime, timedelta
import importlib.util
import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo


SPEC = importlib.util.spec_from_file_location("study30_engine", Path(__file__).resolve().parents[1] / "src" / "engine.py")
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)
NY = ZoneInfo("America/New_York")
DAY = "2020-01-09"


def at(clock, day=DAY):
    return datetime.fromisoformat(f"{day}T{clock}:00").replace(tzinfo=NY)


def fixture(*, price_changes=None, ema_changes=None, opening=98., cloud=(102., 101.)):
    """Observed features are supplied explicitly; recurrence belongs to features."""
    prices = sorted((at(key), value) for key, value in (price_changes or {}).items())
    emas = sorted((at(key), value) for key, value in (ema_changes or {}).items())
    anchor, close = at("18:00", "2020-01-08"), at("17:00")

    def state(changes, timestamp, initial=98.):
        values = [value for key, value in changes if key <= timestamp]
        return values[-1] if values else initial

    minutes = []
    current = anchor
    while current < close:
        # A native three-minute close is assigned to every minute in its block.
        local_minutes = current.hour * 60 + current.minute
        block_close = current + timedelta(minutes=3 - local_minutes % 3)
        value = state(prices, block_close)
        bar_open = opening if current == at("09:30") else value
        minutes.append({"open_time": current, "close_time": current + timedelta(minutes=1),
                        "contract": "ESH2020", "open": bar_open, "high": max(bar_open, value) + .25,
                        "low": min(bar_open, value) - .25, "close": value, "volume": 1.,
                        "usable": True, "vwap": 99., "vwap_valid": True})
        current += timedelta(minutes=1)
    frames = {}
    for interval in (3, 5):
        rows = []
        current = anchor
        while current < close:
            observed = current + timedelta(minutes=interval)
            selected = [row for row in minutes if current <= row["open_time"] < observed]
            row = {"open_time": current, "close_time": observed, "contract": "ESH2020",
                   "open": selected[0]["open"], "high": max(value["high"] for value in selected),
                   "low": min(value["low"] for value in selected), "close": selected[-1]["close"],
                   "volume": interval, "usable": True}
            if interval == 3:
                row.update(ema6=state(emas, observed), ema6_ready=True)
            else:
                row.update(ema20=cloud[0], ema50=cloud[1], cloud_ready=True)
            rows.append(row)
            current = observed
        frames[interval] = rows
    return {"session_date": DAY, "contract": "ESH2020", "pivot": 100.,
            "minutes": minutes, "bars3": frames[3], "bars5": frames[5],
            "source": {"outlook_id": "synthetic-source"}}


def rth_row(rows, opening):
    return next(row for row in rows if row["open_time"] == at(opening))


def outcome(result, *, event_type="price_cross", horizon="30m", index=0):
    return [row for row in result["outcomes"] if row["event_type"] == event_type and row["horizon"] == horizon][index]


class StateTests(unittest.TestCase):
    def test_equality_remembers_but_unknown_clears(self):
        state, crossing = engine.transition(-1, 0)
        self.assertEqual((state, crossing), (-1, None))
        self.assertEqual(engine.transition(state, 1), (1, 1))
        self.assertEqual(engine.transition(1, None), (None, None))
        self.assertEqual(engine.transition(None, -1), (-1, None))
        self.assertIsNone(engine.strict_side(float("nan"), 100))


class EventTests(unittest.TestCase):
    def test_no_cross_day_retains_zero_counts_and_valid_occupancy(self):
        result = engine.analyze_day(**fixture())
        day = result["daily"][0]
        self.assertEqual(day["price_crosses"], 0)
        self.assertEqual(day["ema_crosses"], 0)
        self.assertEqual(day["sampled_close_below"], 130)
        self.assertEqual(day["occupancy_below_share"], 1.)
        self.assertTrue(day["quality_eligible"])
        self.assertEqual(len(result["sections"]), 3)
        self.assertEqual(result["outcomes"], [])

    def test_crossing_rates_distinguish_observed_zero_from_zero_exposure(self):
        data = fixture()
        observed = engine.analyze_day(**data)
        self.assertEqual(observed["daily"][0]["price_observed_hours"], 6.5)
        self.assertEqual(observed["daily"][0]["ema_observed_hours"], 6.5)
        self.assertEqual([row["price_observed_hours"] for row in observed["sections"]], [1., 2., 3.5])
        self.assertEqual(observed["daily"][0]["price_crosses_per_hour"], 0.)
        self.assertEqual(observed["daily"][0]["ema_crosses_per_hour"], 0.)
        for row in data["bars3"]:
            row["usable"] = False
        unknown = engine.analyze_day(**data, require_quality=False)
        for row in [*unknown["daily"], *unknown["sections"]]:
            self.assertEqual(row["price_observed_hours"], 0.)
            self.assertEqual(row["ema_observed_hours"], 0.)
            self.assertIsNone(row["price_crosses_per_hour"])
            self.assertIsNone(row["ema_crosses_per_hour"])

    def test_opening_seed_is_not_cross_and_first_strict_after_equal_initializes(self):
        data = fixture(opening=102., price_changes={"09:33": 102.}, ema_changes={"09:30": 102.})
        result = engine.analyze_day(**data)
        self.assertEqual(result["price_events"], [])
        self.assertEqual(result["ema_events"], [])
        data = fixture(opening=100., price_changes={"09:33": 100., "09:36": 102.}, ema_changes={"09:30": 100., "09:36": 102.})
        result = engine.analyze_day(**data)
        self.assertEqual(result["price_events"], [])
        self.assertEqual(result["ema_events"], [])

    def test_same_close_confirmation_and_reverse_endpoint_ordering(self):
        data = fixture(price_changes={"09:33": 102., "09:36": 98.},
                       ema_changes={"09:33": 101., "09:36": 99.})
        result = engine.analyze_day(**data)
        first, second = result["price_events"]
        self.assertEqual(first["confirmation_kind"], "same_close")
        self.assertEqual(first["confirmation_lag_minutes"], 0.)
        self.assertEqual(first["returned_at"], at("09:36").astimezone(engine.UTC).isoformat())
        self.assertEqual(first["episode_label"], "confirmed_then_returned")
        self.assertEqual(second["confirmation_kind"], "same_close")
        self.assertTrue(second["return_censored"])
        self.assertEqual(result["daily"][0]["price_recrosses"], 1)

    def test_already_aligned_is_not_actual_confirmation(self):
        result = engine.analyze_day(**fixture(price_changes={"09:33": 102., "09:39": 98.},
                                              ema_changes={"09:30": 101.}))
        event = result["price_events"][0]
        self.assertEqual(event["ema_state_at_cross"], "already_aligned")
        self.assertIsNone(event["confirmation_at"])
        self.assertEqual(event["episode_label"], "returned_without_new_ema_cross")
        self.assertTrue(event["ema_already_aligned_at_start"])

    def test_delayed_confirmation_has_new_reference_time_and_price(self):
        result = engine.analyze_day(**fixture(price_changes={"09:33": 102., "09:39": 104.},
                                              ema_changes={"09:39": 101.}))
        event = result["price_events"][0]
        self.assertEqual(event["confirmation_kind"], "delayed")
        self.assertEqual(event["confirmation_lag_minutes"], 6.)
        confirmed = outcome(result, event_type="ema_confirmation")
        self.assertEqual(confirmed["reference_price"], 104.)
        self.assertEqual(confirmed["reference_at"], at("09:39").astimezone(engine.UTC).isoformat())

    def test_confirmation_uses_own_section_endpoint_and_retains_origin(self):
        result = engine.analyze_day(**fixture(price_changes={"10:30": 102.},
                                              ema_changes={"10:33": 101.}))
        row = outcome(result, event_type="ema_confirmation", horizon="section_end")
        self.assertTrue(row["valid"])
        self.assertEqual(row["section"], "new_york_am")
        self.assertEqual(row["origin_section"], "opening_range")
        self.assertEqual(row["endpoint_at"], at("12:30").astimezone(engine.UTC).isoformat())

    def test_opposite_ema_at_reverse_does_not_confirm_old_episode(self):
        result = engine.analyze_day(**fixture(price_changes={"09:33": 102., "09:36": 98.},
                                              ema_changes={"09:36": 101.}))
        first, second = result["price_events"]
        self.assertIsNone(first["confirmation_at"])
        self.assertIsNone(second["confirmation_at"])
        self.assertEqual(first["episode_label"], "returned_without_new_ema_cross")

    def test_count_matches_independent_hand_state_machine(self):
        data = fixture(price_changes={"09:33": 100., "09:36": 98., "09:39": 102.,
                                      "09:42": 100., "09:45": 102., "09:48": 98.})
        remembered, expected = -1, []
        for row in data["bars3"]:
            if not at("09:30") <= row["open_time"] < at("16:00"):
                continue
            side = 1 if row["close"] > 100 else -1 if row["close"] < 100 else 0
            if side:
                if side != remembered:
                    expected.append((row["close_time"].astimezone(engine.UTC).isoformat(), side))
                remembered = side
        actual = engine.analyze_day(**data)["price_events"]
        self.assertEqual([(row["observed_at"], row["direction"]) for row in actual], expected)

    def test_missing_bar_resets_state_and_censors_episode(self):
        data = fixture(price_changes={"09:33": 102., "09:39": 98.})
        data["bars3"] = [row for row in data["bars3"] if row["open_time"] != at("09:33")]
        with self.assertRaises(engine.IneligibleDay):
            engine.analyze_day(**data)
        result = engine.analyze_day(**data, require_quality=False)
        self.assertEqual(len(result["price_events"]), 1)
        self.assertEqual(result["price_events"][0]["episode_label"], "unknown_after_data_gap")
        self.assertEqual(result["price_events"][0]["episode_end_at"], at("09:33").astimezone(engine.UTC).isoformat())
        self.assertFalse(result["daily"][0]["quality_eligible"])

    def test_section_membership_follows_bar_open_and_first_panels(self):
        result = engine.analyze_day(**fixture(price_changes={"10:30": 102., "10:33": 98., "12:30": 102., "12:33": 98.}))
        events = result["price_events"]
        self.assertEqual([row["section"] for row in events], ["opening_range", "new_york_am", "new_york_am", "new_york_pm"])
        self.assertEqual([row["first_per_day"] for row in events], [True, False, False, False])
        self.assertEqual([row["first_per_section"] for row in events], [True, True, False, True])

    def test_day_end_event_is_censored_and_has_no_followthrough(self):
        result = engine.analyze_day(**fixture(price_changes={"16:00": 102.}, ema_changes={"16:00": 101.}))
        event = result["price_events"][0]
        self.assertTrue(event["return_censored"])
        self.assertEqual(event["episode_duration_minutes"], 0.)
        self.assertEqual(event["episode_penetration_points"], 2.)
        row = outcome(result, horizon="day_end")
        self.assertFalse(row["valid"])
        self.assertEqual(row["unknown_reason"], "no_followthrough_interval")
        self.assertIsNone(result["ema_events"][0]["retest_found"])

    def test_missing_tail_censors_episode_before_unobserved_close(self):
        data = fixture(price_changes={"09:33": 102.})
        data["bars3"] = [row for row in data["bars3"] if row["open_time"] != at("15:57")]
        result = engine.analyze_day(**data, require_quality=False)
        self.assertEqual(result["price_events"][0]["episode_end_reason"], "data_gap")
        self.assertEqual(result["price_events"][0]["episode_end_at"], at("15:57").astimezone(engine.UTC).isoformat())

    def test_initial_ema_state_unknown_does_not_become_already_aligned(self):
        data = fixture(price_changes={"09:33": 102.}, ema_changes={"09:33": 101.})
        rth_row(data["bars3"], "09:27")["ema6_ready"] = False
        result = engine.analyze_day(**data, require_quality=False)
        self.assertEqual(result["price_events"][0]["ema_state_at_cross"], "unavailable_uninitialized")
        self.assertIsNone(result["price_events"][0]["confirmation_at"])


class PathAndSnapshotTests(unittest.TestCase):
    def test_outcomes_exclude_signal_bar_extremes_and_preserve_zero(self):
        data = fixture(price_changes={"09:33": 102.})
        rth_row(data["minutes"], "09:30")["high"] = 1000.
        result = engine.analyze_day(**data)
        row = outcome(result)
        self.assertEqual(row["displacement_points"], 0.)
        self.assertEqual(row["favorable_excursion_points"], .25)
        self.assertEqual(row["adverse_excursion_points"], .25)
        self.assertIs(row["favorable_reach_5"], False)

    def test_both_reaches_are_retained_without_intraminute_ordering(self):
        data = fixture(price_changes={"09:33": 102.})
        rth_row(data["minutes"], "09:33").update(high=125., low=75.)
        row = outcome(engine.analyze_day(**data))
        self.assertIs(row["favorable_reach_20"], True)
        self.assertIs(row["adverse_reach_20"], True)
        self.assertEqual(row["favorable_excursion_points"], 23.)
        self.assertEqual(row["adverse_excursion_points"], 27.)

    def test_late_and_missing_horizons_are_null_not_truncated(self):
        data = fixture(price_changes={"15:45": 102.})
        result = engine.analyze_day(**data)
        self.assertTrue(outcome(result, horizon="15m")["valid"])
        self.assertEqual(outcome(result, horizon="30m")["unknown_reason"], "outside_rth")
        self.assertIsNone(outcome(result, horizon="30m")["favorable_reach_5"])
        data = fixture(price_changes={"09:33": 102.})
        data["minutes"] = [row for row in data["minutes"] if row["open_time"] != at("09:40")]
        result = engine.analyze_day(**data, require_quality=False)
        self.assertEqual(outcome(result)["unknown_reason"], "missing_or_unusable_forward_minute")

    def test_retest_is_subsequent_first_touch_and_classifies_close(self):
        data = fixture(price_changes={"09:33": 102.}, ema_changes={"09:33": 101.})
        # The signal bar touches the pivot; it must not be its own retest.
        row = rth_row(data["bars3"], "09:33")
        row.update(low=100., high=103., close=102.)
        result = engine.analyze_day(**data)
        event = result["ema_events"][0]
        self.assertTrue(event["retest_found"])
        self.assertEqual(event["retest_minutes"], 3.)
        self.assertEqual(event["retest_close_classification"], "hold")
        self.assertTrue(event["retest_window_complete"])

    def test_retest_equal_and_failed_closes_remain_distinct(self):
        for value, expected in [(100., "equal"), (98., "failed")]:
            with self.subTest(value=value):
                data = fixture(price_changes={"09:33": 102.}, ema_changes={"09:33": 101.})
                rth_row(data["bars3"], "09:33").update(low=98., high=103., close=value)
                row = engine.analyze_day(**data)["ema_events"][0]
                self.assertEqual(row["retest_close_classification"], expected)

    def test_no_retest_false_requires_full_window_and_missing_is_unknown(self):
        data = fixture(price_changes={"09:33": 102.}, ema_changes={"09:33": 101.})
        result = engine.analyze_day(**data)
        self.assertIs(result["ema_events"][0]["retest_found"], False)
        data["bars3"] = [row for row in data["bars3"] if row["open_time"] != at("09:36")]
        result = engine.analyze_day(**data, require_quality=False)
        self.assertIsNone(result["ema_events"][0]["retest_found"])
        self.assertTrue(result["ema_events"][0]["retest_censored"])

    def test_asof_snapshot_uses_native_completed_values_without_future(self):
        data = fixture(ema_changes={"09:24": 99., "09:27": 777., "09:30": 101.})
        rth_row(data["bars5"], "09:25").update(ema20=103., ema50=102.)
        result = engine.analyze_day(**data)
        before, opening = result["snapshots"][:2]
        self.assertEqual(before["ema6"], 99.)
        self.assertEqual(before["ema6_source_at"], at("09:24").astimezone(engine.UTC).isoformat())
        self.assertEqual(before["ema20"], 102.)
        self.assertEqual(opening["ema20"], 103.)
        self.assertEqual(opening["price"], 98.)

    def test_later_feature_changes_cannot_change_opening_snapshot(self):
        data = fixture(price_changes={"09:33": 102.})
        original = engine.analyze_day(**data)
        changed = deepcopy(data)
        for row in changed["bars5"]:
            if row["open_time"] >= at("12:00"):
                row.update(ema20=9999., ema50=-9999.)
        repeated = engine.analyze_day(**changed)
        self.assertEqual(original["snapshots"][:2], repeated["snapshots"][:2])
        for key in engine.CONTEXT_FIELDS:
            self.assertEqual(original["price_events"][0][key], repeated["price_events"][0][key])

    def test_crossing_snapshots_deduplicate_and_link_full_asof_values(self):
        data = fixture(price_changes={"09:33": 102., "09:39": 98.},
                       ema_changes={"09:33": 101., "09:42": 99.})
        rth_row(data["bars5"], "09:30").update(ema20=999., ema50=998.)
        result = engine.analyze_day(**data)
        snapshots = {row["snapshot_id"]: row for row in result["snapshots"]}
        crossings = [row for row in result["snapshots"] if row["snapshot_label"] == "crossing"]
        events = result["price_events"] + result["ema_events"]
        self.assertEqual(len(snapshots), len(result["snapshots"]))
        self.assertEqual({row["snapshot_at"] for row in crossings}, {row["observed_at"] for row in events})
        self.assertEqual(len(crossings), 3)
        self.assertEqual(result["price_events"][0]["feature_snapshot_id"], result["ema_events"][0]["feature_snapshot_id"])
        for event in events:
            row = snapshots[event["feature_snapshot_id"]]
            self.assertEqual(row["snapshot_at"], event["observed_at"])
            for key in ("ema6", "ema20", "ema50", "vwap", "ema6_source_at", "cloud_source_at", "vwap_source_at"):
                self.assertIsNotNone(row[key])
            for key in ("ema6_source_at", "cloud_source_at", "vwap_source_at"):
                self.assertLessEqual(engine._dt(row[key]), engine._dt(event["observed_at"]))
        first = snapshots[result["price_events"][0]["feature_snapshot_id"]]
        self.assertEqual(first["ema6"], 101.)
        self.assertEqual(first["ema20"], 102.)
        self.assertEqual(first["cloud_source_at"], at("09:30").astimezone(engine.UTC).isoformat())
        for event in result["price_events"]:
            confirmation = snapshots[event["confirmation_feature_snapshot_id"]]
            self.assertEqual(confirmation["snapshot_at"], event["confirmation_at"])
        for row in result["outcomes"]:
            self.assertEqual(snapshots[row["feature_snapshot_id"]]["snapshot_at"], row["reference_at"])
        delayed = result["price_events"][1]
        self.assertNotEqual(delayed["feature_snapshot_id"], delayed["confirmation_feature_snapshot_id"])
        delayed_outcomes = [row for row in result["outcomes"] if row["event_id"] == delayed["event_id"] and row["event_type"] == "ema_confirmation"]
        self.assertTrue(delayed_outcomes)
        self.assertTrue(all(row["feature_snapshot_id"] == delayed["confirmation_feature_snapshot_id"] for row in delayed_outcomes))
        scheduled = [row["snapshot_label"] for row in result["snapshots"][:5]]
        self.assertEqual(scheduled, ["0925", "0930", "opening_range_end", "new_york_am_end", "new_york_pm_end"])

    def test_quality_gate_requires_overnight_and_preopen_readiness(self):
        data = fixture()
        data["minutes"] = [row for row in data["minutes"] if row["open_time"] >= at("09:00")]
        rth_row(data["bars3"], "09:21")["ema6_ready"] = False
        with self.assertRaises(engine.IneligibleDay) as raised:
            engine.analyze_day(**data)
        self.assertIn("incomplete_or_unusable_anchor_to_rth_end_minutes", raised.exception.codes)
        self.assertIn("unavailable_0925_ema6", raised.exception.codes)

    def test_cloud_width_gap_and_strict_run_definitions(self):
        data = fixture(price_changes={"09:33": 102., "09:36": 100., "09:39": 102., "09:42": 98.}, cloud=(101., 101.))
        result = engine.analyze_day(**data, prior_rth_close=97.)
        day = result["daily"][0]
        self.assertEqual(day["opening_gap_points"], 1.)
        self.assertEqual(day["opening_cloud_order"], "flat")
        self.assertEqual(day["opening_cloud_width"], 0.)
        self.assertEqual(day["longest_above_run_3m"], 1)
        self.assertEqual(result["snapshots"][1]["cloud_width_change_15m"], 0.)

    def test_outputs_json_finite_and_cross_contract_rejected(self):
        data = fixture(price_changes={"09:33": 102.})
        result = engine.analyze_day(**data)
        json.dumps(result, allow_nan=False)
        data["minutes"][0]["contract"] = "ESM2020"
        with self.assertRaisesRegex(ValueError, "mix delivery"):
            engine.analyze_day(**data)
        data["minutes"][0]["contract"] = None
        with self.assertRaisesRegex(engine.IneligibleDay, "native_contract_missing"):
            engine.analyze_day(**data)


if __name__ == "__main__":
    unittest.main()
