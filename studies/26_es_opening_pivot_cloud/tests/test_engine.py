"""Synthetic scientific checks; none read strategy outcomes or market files."""
from __future__ import annotations

import copy
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import candidates, simulate  # noqa: E402

NY = ZoneInfo("America/New_York")


def fixture(direction="short", day="2025-06-02"):
    d = date.fromisoformat(day)
    start = datetime(d.year, d.month, d.day, 9, 25, tzinfo=NY)
    short = direction == "short"
    base = 98.5 if short else 101.5
    ema20, ema50 = (99.25, 99.75) if short else (100.75, 100.25)
    bars = []
    for i in range(7):
        bars.append({"time": start + timedelta(minutes=5 * i), "open": base,
                     "high": base + .25, "low": base - .25, "close": base,
                     "ema20": ema20, "ema50": ema50, "atr14": 5.0,
                     "ema20_lag3": ema20 + (.5 if short else -.5),
                     "ema50_lag3": ema50 + (.5 if short else -.5)})
    bars[0].update(open=97.5 if short else 102.5, high=97.75 if short else 102.75,
                   low=97.25 if short else 102.25, close=97.5 if short else 102.5)
    bars[1].update(open=100.0, high=100.5 if short else 102.0,
                   low=98.0 if short else 99.5, close=base)
    minutes = [{"time": start + timedelta(minutes=5 + i), "open": base,
                "high": base + .25, "low": base - .25, "close": base} for i in range(90)]
    return {"date": day, "eligible": True,
            "plan": {"pivot_lower": 100.0, "pivot_upper": 100.0, "description": "YVAL + YPOC",
                     "label_group": "YVAL+YPOC", "available_at": None,
                     "targets": {"long": [], "short": []}}, "bars5": bars, "minutes": minutes}


def candidate(session):
    found, _ = candidates(session)
    if not found:
        raise AssertionError("Synthetic fixture failed to form a candidate")
    return found[0]


def minute(session, hour, value):
    return next(b for b in session["minutes"] if b["time"].hour == hour and b["time"].minute == value)


class EventTests(unittest.TestCase):
    def test_short_and_long_mirror_and_primary_id(self):
        for direction in ("short", "long"):
            s = fixture(direction)
            found, events = candidates(s)
            self.assertEqual(len(found), 1)
            c = found[0]
            self.assertEqual(c["direction"], direction)
            self.assertTrue(c["is_primary"])
            self.assertEqual(c["reaction_time"].strftime("%H:%M"), "09:35")
            self.assertEqual(c["formation_bars"], 1)
            self.assertTrue(c["ordering_pass"] and c["slope_pass"])
            self.assertEqual(c["pivot_kind"], "single")
            self.assertIsNone(c["available_at"])
            self.assertEqual(events[0]["event"], "episode_started")
            self.assertEqual(events[1]["candidate_id"], c["candidate_id"])

    def test_09_30_reset_ignores_older_approach(self):
        s = fixture()
        s["bars5"][0].update(open=100, close=100, low=99.75, high=100.25)
        older = copy.deepcopy(s["bars5"][0])
        older.update(time=older["time"] - timedelta(minutes=5), open=95, close=95, high=95.25, low=94.75)
        s["bars5"].insert(0, older)
        self.assertEqual(candidates(s)[0], [])

    def test_approach_must_precede_return(self):
        s = fixture()
        s["bars5"][0].update(open=100, close=100, low=99.75, high=100.25)
        # Reaction close below the pivot cannot establish its own approach.
        found, events = candidates(s)
        self.assertEqual(found, [])
        self.assertIn("no_prior_approach", [e["reason"] for e in events])

    def test_delta_rounds_up_from_prior_atr_and_freezes(self):
        s = fixture()
        s["bars5"][0]["atr14"] = 12.6
        s["bars5"][1]["atr14"] = 50
        self.assertEqual(candidate(s)["delta"], 1.5)
        self.assertEqual(candidate(s)["atr14"], 50)
        self.assertEqual(candidate(s)["first_touch_prior_atr14"], 12.6)
        self.assertEqual(candidate(s)["preopen_atr14"], 12.6)

    def test_pivot_zone_outer_bounds_and_stop(self):
        s = fixture()
        s["plan"]["pivot_lower"], s["plan"]["pivot_upper"] = 99.5, 100.75
        c = candidate(s)
        self.assertEqual(c["pivot_kind"], "zone")
        self.assertEqual(c["pivot_width"], 1.25)
        self.assertEqual(c["stop_price"], 101.75)

    def test_inclusive_approach_and_tolerance_touch_boundaries(self):
        s = fixture()
        s["bars5"][0].update(open=99, close=99, low=98.75, high=99.25)
        s["bars5"][1].update(open=99, high=99, low=97.5, close=98)
        self.assertEqual(candidate(s)["approach_close"], 99)

    def test_reaction_close_must_be_strictly_beyond_cloud(self):
        s = fixture()
        s["bars5"][1]["close"] = 99.25
        self.assertEqual(candidates(s)[0], [])

    def test_neutral_bar_not_directional_reaction(self):
        s = fixture()
        s["bars5"][1]["open"] = s["bars5"][1]["close"]
        found, events = candidates(s)
        self.assertEqual(found, [])
        self.assertIn("formation_window_expired", [e["reason"] for e in events])

    def test_pivot_and_cloud_can_touch_on_separate_bars(self):
        s = fixture()
        # First bar reaches pivot but is at least one tick short of cloud tolerance.
        s["bars5"][1].update(open=99, close=99.5, low=99, high=100, ema20=102, ema50=103)
        # Next bar touches only cloud, whose separation is now exactly delta.
        s["bars5"][2].update(open=102.5, close=101.5, low=101.25, high=102.75, ema20=101, ema50=102)
        # Short reaction comes on third episode bar, remaining below cloud.
        s["bars5"][3].update(open=101, close=99.5, low=99.25, high=101.25, ema20=100, ema50=101)
        c = candidate(s)
        self.assertEqual(c["formation_bars"], 3)
        self.assertEqual(c["reaction_time"].strftime("%H:%M"), "09:45")
        self.assertEqual(c["pivot_cloud_separation"], 0)

    def test_cloud_interaction_remains_required_filter_off(self):
        s = fixture()
        for b in s["bars5"][1:]:
            b.update(ema20=110, ema50=111)
        found, events = candidates(s)
        self.assertEqual(found, [])
        expired = next(e for e in events if e["event"] == "episode_expired")
        self.assertIn("cloud_touch", expired["missing_ingredients"])

    def test_cloud_separation_required_even_with_both_touched(self):
        s = fixture()
        s["bars5"][1].update(high=106, ema20=104, ema50=105)
        for b in s["bars5"][2:]:
            b.update(ema20=104, ema50=105)
        self.assertEqual(candidates(s)[0], [])

    def test_expiration_has_three_bars_no_late_reaction(self):
        s = fixture()
        for b in s["bars5"][1:4]:
            b["open"] = b["close"]
        s["bars5"][4].update(open=100, high=100.5, low=98, close=98.5)
        found, events = candidates(s)
        self.assertEqual(found, [])
        expiry = next(e for e in events if e["event"] == "episode_expired")
        self.assertEqual(expiry["time"].strftime("%H:%M"), "09:45")

    def test_candidate_suppression_requires_later_approach(self):
        s = fixture()
        # 09:35 can only establish the next approach; 09:40 reacts.
        s["bars5"][2].update(open=98.5, close=98.5, low=98, high=100.5)
        s["bars5"][3].update(open=100, close=98.5, low=98, high=100.5)
        found, _ = candidates(s)
        self.assertEqual(len(found), 2)
        self.assertEqual([c["is_primary"] for c in found], [True, False])
        self.assertEqual(found[1]["reaction_time"].strftime("%H:%M"), "09:45")
        self.assertEqual(simulate(s, found[1])["reason"], "later_candidate_suppressed")

    def test_opposite_approach_overlap_is_rejected(self):
        s = fixture()
        # Prior short approach, then far-above close without pivot touch.
        s["bars5"][1].update(open=103, close=103, low=102.75, high=103.25)
        s["bars5"][2].update(open=100, close=98.5, low=98, high=100.5)
        found, events = candidates(s)
        self.assertEqual(found, [])
        self.assertIn("opposite_approach_overlap", [e["reason"] for e in events])

    def test_10_oclock_reaction_not_candidate(self):
        s = fixture()
        for b in s["bars5"][1:6]:
            b.update(open=97.5, high=98, low=97, close=97.5)
        s["bars5"][6].update(open=100, close=98.5, low=98, high=100.5)
        self.assertEqual(candidates(s)[0], [])

    def test_09_50_reaction_generates_09_55_fill(self):
        s = fixture()
        for b in s["bars5"][1:5]:
            b.update(open=97.5, high=98, low=97, close=97.5)
        s["bars5"][5].update(open=100, close=98.5, low=98, high=100.5)
        c = candidate(s)
        self.assertEqual(c["reaction_time"].strftime("%H:%M"), "09:55")
        self.assertEqual(simulate(s, c)["entry_time"].strftime("%H:%M"), "09:55")

    def test_later_completed_features_do_not_change_existing_candidate(self):
        s = fixture()
        c = candidate(s)
        for b in s["bars5"][2:]:
            b.update(ema20=1, ema50=2, atr14=100, ema20_lag3=10, ema50_lag3=20)
        self.assertEqual(candidate(s), c)

    def test_feature_readiness_not_weakened(self):
        s = fixture()
        s["bars5"][0]["atr14"] = None
        found, events = candidates(s)
        self.assertEqual(found, [])
        self.assertEqual(events[0]["reason"], "feature_not_ready")
        self.assertIsNone(simulate(s, None)["net_dollars"])

    def test_ineligible_contract_not_converted_to_no_trade(self):
        s = fixture()
        s.update(eligible=False, reason="contract_mismatch")
        self.assertEqual(candidates(s)[1][0]["reason"], "contract_mismatch")
        r = simulate(s, None)
        self.assertIsNone(r["net_dollars"])
        self.assertFalse(r["trade"])

    def test_aware_timestamp_required(self):
        s = fixture()
        s["bars5"][0]["time"] = s["bars5"][0]["time"].replace(tzinfo=None)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            candidates(s)

    def test_dst_and_utc_bar_open_conversion(self):
        for d, utc_hour in (("2025-03-07", 14), ("2025-03-10", 13), ("2025-11-03", 14)):
            s = fixture(day=d)
            for b in s["bars5"] + s["minutes"]:
                b["time"] = b["time"].astimezone(timezone.utc)
            c = candidate(s)
            self.assertEqual(c["reaction_time"].astimezone(timezone.utc).hour, utc_hour)
            self.assertEqual(simulate(s, c)["entry_time"].strftime("%H:%M"), "09:35")


class ExecutionTests(unittest.TestCase):
    def test_earliest_fill_and_coincident_confirmation(self):
        s = fixture()
        c = candidate(s)
        a, b = simulate(s, c), simulate(s, c, "confirmed")
        self.assertEqual(a["entry_time"].strftime("%H:%M"), "09:35")
        self.assertEqual(a["entry_time"], b["entry_time"])
        self.assertEqual(a["entry_price"], b["entry_price"])
        self.assertEqual(a["net_dollars"], b["net_dollars"])
        self.assertTrue(b["coincident_entry"])
        self.assertEqual(b["confirmation_delay"], 0)

    def waiting(self):
        s = fixture()
        # Cloud is above pivot; close is below cloud but NOT below pivot.
        s["bars5"][0].update(open=97.5, high=97.75, low=97.25, close=97.5)
        s["bars5"][1].update(open=101, high=101.5, low=99.5, close=100.25, ema20=100.5, ema50=101,
                               ema20_lag3=101, ema50_lag3=101.5)
        # First subsequent close confirms. Entry at 09:40.
        s["bars5"][2].update(open=100.25, high=100.5, low=99, close=99.5, ema20=100.5, ema50=101)
        return s, candidate(s)

    def test_confirmed_waits_completed_bar_and_same_frozen_stop(self):
        s, c = self.waiting()
        early, confirmed = simulate(s, c), simulate(s, c, "confirmed")
        self.assertEqual(confirmed["entry_time"].strftime("%H:%M"), "09:40")
        self.assertEqual(confirmed["confirmation_delay"], 1)
        self.assertFalse(confirmed["coincident_entry"])
        self.assertEqual(early["stop_price"], confirmed["stop_price"])

    def test_waiting_stop_breach_cancels_even_if_confirmation_closes(self):
        s, c = self.waiting()
        minute(s, 9, 37).update(open=100, high=c["stop_price"], low=99, close=100)
        r = simulate(s, c, "confirmed")
        self.assertFalse(r["trade"])
        self.assertEqual(r["reason"], "structural_invalidation")
        self.assertEqual(r["net_dollars"], 0)

    def test_stop_touch_before_entry_same_open_rejects(self):
        s = fixture()
        c = candidate(s)
        minute(s, 9, 35).update(open=c["stop_price"], high=c["stop_price"]+.5,
                               low=c["stop_price"]-.5, close=c["stop_price"])
        r = simulate(s, c)
        self.assertEqual(r["reason"], "entry_open_beyond_stop")
        self.assertFalse(r["trade"])

    def test_confirmation_expires_after_three_subsequent_bars(self):
        s, c = self.waiting()
        for b in s["bars5"][2:5]:
            b.update(open=100.25, close=100.25, high=100.5, low=100)
        # Fourth bar would confirm; excluded by the three-bar deadline.
        s["bars5"][5].update(open=100, close=99, high=100, low=98.75)
        self.assertEqual(simulate(s, c, "confirmed")["reason"], "confirmation_expired")

    def test_confirmation_on_third_subsequent_bar_allowed(self):
        s, c = self.waiting()
        for b in s["bars5"][2:4]:
            b.update(open=100.25, close=100.25, high=100.5, low=100)
        s["bars5"][4].update(open=100, close=99, high=100, low=98.75)
        r = simulate(s, c, "confirmed")
        self.assertTrue(r["trade"])
        self.assertEqual(r["confirmation_delay"], 3)
        self.assertEqual(r["entry_time"].strftime("%H:%M"), "09:50")

    def test_10_oclock_confirmation_fill_ineligible(self):
        s, c = self.waiting()
        # Candidate moved to 09:45 reaction close, fourth/fifth bars no confirm.
        c["reaction_time"] = s["bars5"][3]["time"] + timedelta(minutes=5)
        for b in s["bars5"][3:6]:
            b.update(open=100.25, close=100.25, high=100.5, low=100)
        s["bars5"][6].update(open=100, close=99, high=100, low=98.75)
        r = simulate(s, c, "confirmed")
        self.assertFalse(r["trade"])
        self.assertEqual(r["reason"], "confirmation_expired")

    def test_filters_frozen_at_reaction_and_no_replacement(self):
        s = fixture()
        c = candidate(s)
        c.update(ordering_pass=False, slope_pass=False)
        self.assertTrue(simulate(s, c, mask="A")["trade"])
        for mask in "BCD":
            r = simulate(s, c, mask=mask)
            self.assertFalse(r["trade"])
            self.assertEqual(r["reason"], "ema_filter_rejected")
        c.update(ordering_pass=True)
        self.assertTrue(simulate(s, c, mask="B")["trade"])
        self.assertFalse(simulate(s, c, mask="C")["trade"])
        self.assertFalse(simulate(s, c, mask="D")["trade"])

    def test_later_features_do_not_recheck_reaction_filter(self):
        s, c = self.waiting()
        for b in s["bars5"][2:]:
            b.update(ema20=101, ema50=100.5, ema20_lag3=99, ema50_lag3=99)
        self.assertTrue(c["ordering_pass"])
        self.assertTrue(simulate(s, c, "confirmed", "D")["trade"])

    def test_time_exit_costs_and_r_units_once(self):
        for direction in ("short", "long"):
            s = fixture(direction)
            c = candidate(s)
            r = simulate(s, c)
            self.assertEqual(r["exit_reason"], "time")
            self.assertEqual(r["exit_time"].strftime("%H:%M"), "11:00")
            self.assertEqual(r["gross_dollars"], -25)
            self.assertEqual(r["fees_dollars"], 5)
            self.assertEqual(r["net_dollars"], -30)
            self.assertAlmostEqual(r["net_r"], -30 / (r["initial_risk_points"] * 50))
            self.assertEqual(r["holding_minutes"], 85)

    def test_time_exit_uses_10_59_close_no_11_oclock_lookahead(self):
        s = fixture()
        minute(s, 10, 59).update(open=98.5, high=99.5, low=98, close=99)
        s["minutes"].append({"time": datetime(2025, 6, 2, 11, tzinfo=NY),
                              "open": 10000, "high": 10001, "low": 9999, "close": 10000})
        r = simulate(s, candidate(s))
        self.assertEqual(r["exit_price"], 99.25)
        self.assertEqual(r["exit_time_precision"], "11:00_flatten")

    def test_gap_through_stop_uses_worse_open_and_slippage(self):
        for direction in ("short", "long"):
            s = fixture(direction)
            c = candidate(s)
            gap = c["stop_price"] + (2 if direction == "short" else -2)
            minute(s, 9, 36).update(open=gap, high=gap+.25, low=gap-.25, close=gap)
            r = simulate(s, c)
            self.assertEqual(r["exit_reason"], "stop_gap")
            self.assertEqual(r["exit_price"], gap + (.25 if direction == "short" else -.25))
            self.assertFalse(r["ambiguity"])
            self.assertEqual(r["exit_time_precision"], "bar_open")

    def test_unresolved_same_minute_ambiguity_adverse_first_and_bound(self):
        for direction in ("short", "long"):
            s = fixture(direction)
            c = candidate(s)
            preliminary = simulate(s, c)
            target = preliminary["target_price"]
            minute(s, 9, 36).update(high=max(c["stop_price"], target)+.25,
                                   low=min(c["stop_price"], target)-.25)
            r = simulate(s, c)
            self.assertEqual(r["exit_reason"], "stop")
            self.assertTrue(r["ambiguity"])
            self.assertEqual(r["ambiguity_count"], 1)
            self.assertLess(r["net_dollars"], 0)
            self.assertGreater(r["optimistic_net_dollars"], 0)
            self.assertAlmostEqual(r["optimistic_net_r"], 2 - 5/(r["initial_risk_points"]*50))

    def test_target_requires_full_tick_trade_through(self):
        s = fixture()
        c = candidate(s)
        target = simulate(s, c)["target_price"]
        minute(s, 9, 36)["low"] = target
        self.assertEqual(simulate(s, c)["exit_reason"], "time")
        minute(s, 9, 36)["low"] = target-.25
        r = simulate(s, c)
        self.assertEqual(r["exit_reason"], "target")
        self.assertEqual(r["exit_price"], target)

    def test_opening_target_gap_precedes_later_minute_stop(self):
        s = fixture()
        c = candidate(s)
        target = simulate(s, c)["target_price"]
        minute(s, 9, 36).update(open=target-.5, low=target-.75, close=target,
                               high=c["stop_price"]+.25)
        r = simulate(s, c)
        self.assertEqual(r["exit_reason"], "target")
        self.assertFalse(r["ambiguity"])

    def test_no_target_touch_before_entry_counted(self):
        s = fixture()
        c = candidate(s)
        minute(s, 9, 34)["low"] = 1
        self.assertEqual(simulate(s, c)["exit_reason"], "time")

    def test_target_zones_near_edge_nearest_first_two_only(self):
        s = fixture()
        s["plan"]["targets"]["short"] = [
            {"lower": 89, "upper": 90, "description": "YVAL target", "ordinal": 1},
            {"lower": 94, "upper": 95, "description": "HVE target", "ordinal": 2},
            {"lower": 96, "upper": 97, "description": "must not use third", "ordinal": 3}]
        r = simulate(s, candidate(s), exit_policy="verne")
        self.assertEqual(r["target_price"], 95)
        self.assertEqual(r["target_ordinal"], 2)
        self.assertEqual(r["target_description"], "HVE target")
        s = fixture("long")
        s["plan"]["targets"]["long"] = [{"lower": 104, "upper": 105, "ordinal": 1}]
        self.assertEqual(simulate(s, candidate(s), exit_policy="verne")["target_price"], 104)

    def test_target_strictly_beyond_actual_slipped_fill(self):
        s = fixture()
        c = candidate(s)
        fill = simulate(s, c)["entry_price"]
        s["plan"]["targets"]["short"] = [{"lower": fill-.25, "upper": fill, "ordinal": 1}]
        r = simulate(s, c, exit_policy="verne")
        self.assertEqual(r["reason"], "target_unavailable")
        self.assertIsNone(r["net_dollars"])
        self.assertFalse(r["trade"])

    def test_missing_targets_no_fixed_2r_fallback(self):
        s = fixture()
        c = candidate(s)
        r = simulate(s, c, exit_policy="verne")
        self.assertIsNone(r["net_dollars"])
        self.assertEqual(r["reason"], "target_unavailable")
        self.assertTrue(simulate(s, c, exit_policy="fixed_2r")["trade"])

    def test_cost_stress_and_no_double_counting(self):
        s = fixture()
        c = candidate(s)
        self.assertEqual([simulate(s, c, slippage=n)["net_dollars"] for n in (0, 1, 2, 4)],
                         [-5, -30, -55, -105])

    def test_fixed_target_uses_actual_fill_risk(self):
        s = fixture("long")
        c = candidate(s)
        r = simulate(s, c, slippage=4)
        self.assertEqual(r["target_price"], r["entry_price"] + 2*(r["entry_price"]-r["stop_price"]))
        self.assertEqual(r["target_distance_r"], 2)

    def test_stop_buffer_changes_structural_stop_only(self):
        s = fixture()
        for buffer in (.5, 1, 1.5):
            c = candidates(s, stop_buffer=buffer)[0][0]
            self.assertEqual(c["stop_price"], 100.5+buffer)
            self.assertEqual(c["reaction_time"].strftime("%H:%M"), "09:35")

    def test_missing_minute_is_undefined_even_if_no_candidate(self):
        s = fixture()
        c = candidate(s)
        s["minutes"].pop()
        for cand in (None, c):
            r = simulate(s, cand)
            self.assertEqual(r["reason"], "incomplete_execution_data")
            self.assertIsNone(r["net_dollars"])

    def test_duplicate_minute_not_silently_resolved(self):
        s = fixture()
        s["minutes"].append(copy.deepcopy(s["minutes"][0]))
        self.assertIsNone(simulate(s, None)["net_dollars"])

    def test_complete_no_candidate_is_genuine_zero(self):
        s = fixture()
        r = simulate(s, None)
        self.assertEqual(r["reason"], "no_candidate")
        self.assertEqual(r["net_dollars"], 0)
        self.assertIsNone(r["net_r"])

    def test_invalid_ohlc_is_undefined(self):
        s = fixture()
        minute(s, 10, 0)["high"] = 1
        self.assertEqual(simulate(s, None)["reason"], "invalid_execution_ohlc")

    def test_deterministic_no_mutation(self):
        s = fixture()
        before = copy.deepcopy(s)
        c = candidate(s)
        self.assertEqual(simulate(s, c), simulate(s, c))
        self.assertEqual(s, before)

    def test_post_exit_minutes_cannot_change_outcome(self):
        s = fixture()
        c = candidate(s)
        minute(s, 9, 36).update(high=c["stop_price"]+.25)
        before = simulate(s, c)
        for b in s["minutes"]:
            if b["time"] > minute(s, 9, 36)["time"]:
                b.update(open=1000, high=1001, low=999, close=1000)
        self.assertEqual(simulate(s, c), before)

    def test_stop_entry_minute_is_sequenced_after_open_fill(self):
        s = fixture()
        c = candidate(s)
        minute(s, 9, 35)["high"] = c["stop_price"]
        r = simulate(s, c)
        self.assertTrue(r["trade"])
        self.assertEqual(r["exit_reason"], "stop")
        self.assertEqual(r["exit_bar_open_time"].strftime("%H:%M"), "09:35")
        self.assertEqual(r["exit_time_precision"], "bar_completion")


if __name__ == "__main__":
    unittest.main()
