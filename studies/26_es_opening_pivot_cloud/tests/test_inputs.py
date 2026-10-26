"""Synthetic input-contract tests; no historical strategy outcomes."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.inputs import (NY, audit_session, build_plan, canonical_feature_contract,
                        canonical_quoted_contract, independent_feature_audit)


def plan_rows(day=date(2024, 3, 11)):
    outlook = dict(outlook_id="one", content_kind="daily_outlook", extraction_status="complete",
                   parsed_branch_count=2, contract="ESH24", available_at=None, source_url="retained",
                   source_post_id="post", timing_status="historical_availability_unverified", session_date=day)
    levels = []
    for side in ("bullish", "bearish"):
        levels.append(dict(outlook_id="one", role="trigger", side=side, contract="ESH24", available_at=None,
                           price_low=Decimal("5000"), price_high=Decimal("5000"), source_label="YVAL-HVE",
                           source_text="YVAL-HVE 5000", ordinal=1, source_row_id="one:" + side, session_date=day))
        for ordinal, price in ((1, 5010 if side == "bullish" else 4990), (2, 5020 if side == "bullish" else 4980)):
            levels.append(dict(outlook_id="one", role="target", side=side, contract="ESH24", available_at=None,
                               price_low=Decimal(price), price_high=Decimal(price + 2), source_label="YPOC",
                               source_text=f"YPOC {price}-{price + 2}", ordinal=ordinal,
                               source_row_id=f"one:{side}:{ordinal}", session_date=day))
    return [outlook], levels


def session_frames(day="2024-03-11"):
    stamps = pd.date_range(f"{day} 09:10", periods=12, freq="5min", tz=NY).tz_convert("UTC")
    feature = pd.DataFrame(dict(timestamp=stamps, open=5000., high=5001., low=4999., close=5000.,
                                ema20=5000., ema50=5000., atr14=2., ema20_lag3=5000., ema50_lag3=5000.,
                                available_at=stamps + pd.Timedelta(minutes=5), contract="ES:12:2024:3:ESH4",
                                raw_symbol="ESH4", lineage="frozen", feature_valid=True,
                                consecutive_count=300, usable=True, calendar_valid=True))
    minute = pd.date_range(f"{day} 09:30", periods=90, freq="min", tz=NY).tz_convert("UTC")
    minutes = pd.DataFrame(dict(timestamp=minute, open=5000., high=5001., low=4999., close=5000.,
                               instrument_id=12, raw_symbol="ESH4"))
    return feature, minutes


class InputContractTests(unittest.TestCase):
    def test_full_delivery_year_matches_instead_of_single_digit_suffix(self):
        self.assertEqual(canonical_quoted_contract("/ESH24"), "ESH2024")
        self.assertEqual(canonical_feature_contract("ES:12:2024:3:ESH4"), "ESH2024")
        self.assertNotEqual(canonical_feature_contract("ES:12:2014:3:ESH4"), "ESH2024")
        self.assertIsNone(canonical_quoted_contract("ESH4"))

    def test_coincident_pivots_are_one_price_and_target_zones_stay_targets(self):
        outlooks, levels = plan_rows()
        plan, reason = build_plan(outlooks, levels)
        self.assertEqual(reason, "")
        self.assertEqual((plan["pivot_lower"], plan["pivot_upper"]), (5000, 5000))
        self.assertFalse(plan["pivot_is_zone"])
        self.assertEqual(plan["label_group"], "HVE+YVAL")
        self.assertEqual(plan["targets"]["long"][0]["upper"], 5012)
        self.assertIsNone(plan["available_at"])

    def test_distinct_trigger_bounds_form_outer_zone(self):
        outlooks, levels = plan_rows()
        levels[3]["price_low"], levels[3]["price_high"] = Decimal("4995"), Decimal("5003")
        plan, _ = build_plan(outlooks, levels)
        self.assertEqual((plan["pivot_lower"], plan["pivot_upper"]), (4995, 5003))
        self.assertTrue(plan["pivot_is_zone"])

    def test_duplicate_date_skips_even_with_only_one_complete_plan(self):
        outlooks, levels = plan_rows()
        outlooks.append({**outlooks[0], "extraction_status": "failed"})
        self.assertEqual(build_plan(outlooks, levels), (None, "ambiguous_duplicate_source_date"))

    def test_verified_availability_cannot_silently_enter_conditional_cohort(self):
        outlooks, levels = plan_rows()
        outlooks[0]["available_at"] = "2024-03-11T08:00:00-04:00"
        with self.assertRaisesRegex(ValueError, "separately frozen cohort"):
            build_plan(outlooks, levels)

    def test_dst_timing_and_completeness_use_bar_open_clock(self):
        outlooks, levels = plan_rows()
        features, minutes = session_frames()
        session, audit = audit_session(date(2024, 3, 11), outlooks, levels, features, minutes)
        self.assertTrue(session["eligible"])
        self.assertEqual(session["bars5"][0]["time"].isoformat(), "2024-03-11T09:25:00-04:00")
        self.assertEqual(session["bars5"][0]["available_at"].isoformat(), "2024-03-11T09:30:00-04:00")
        self.assertEqual(session["minutes"][-1]["time"].isoformat(), "2024-03-11T10:59:00-04:00")
        self.assertEqual(len(session["minutes"]), 90)
        self.assertTrue(audit["input_eligible"])

    def test_readiness_must_hold_for_entire_frozen_window(self):
        outlooks, levels = plan_rows()
        features, minutes = session_frames()
        features.loc[0, "feature_valid"] = False
        _, audit = audit_session(date(2024, 3, 11), outlooks, levels, features, minutes)
        self.assertEqual(audit["exclusion_reason"], "feature_not_ready")

    def test_missing_or_duplicate_minutes_are_missing_outcomes_not_no_trade(self):
        outlooks, levels = plan_rows()
        features, minutes = session_frames()
        for bad in (minutes.iloc[:-1], pd.concat([minutes, minutes.iloc[:1]], ignore_index=True)):
            session, audit = audit_session(date(2024, 3, 11), outlooks, levels, features, bad)
            self.assertFalse(session["eligible"])
            self.assertEqual(audit["exclusion_reason"], "incomplete_execution_window")

    def test_wrong_contract_is_excluded_without_adjusting_levels(self):
        outlooks, levels = plan_rows()
        features, minutes = session_frames()
        features["contract"] = "ES:13:2024:6:ESM4"
        session, audit = audit_session(date(2024, 3, 11), outlooks, levels, features, minutes)
        self.assertFalse(session["eligible"])
        self.assertEqual(audit["exclusion_reason"], "contract_mismatch")
        self.assertEqual(session["plan"]["pivot_lower"], 5000)

    def test_uncertified_early_close_is_explicit_exclusion(self):
        outlooks, levels = plan_rows()
        features, minutes = session_frames()
        _, audit = audit_session(date(2024, 3, 11), outlooks, levels, features, minutes,
                                 calendar_event="Christmas Eve early close", cash_session=True)
        self.assertTrue(audit["exchange_session"])
        self.assertEqual(audit["exclusion_reason"], "published_calendar_uncertified")


if __name__ == "__main__":
    unittest.main()
