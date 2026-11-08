#!/usr/bin/env python3
"""Read-only nominal-calendar checks for the fixed prospective Study 29 sample.

This module does not fetch market data, inspect sources or relax the existing
eight fixed-clock history windows around holidays. Calendar support is a
pre-prediction eligibility condition, not evidence that future bars exist.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SCHEMA = "abacus.study29.phase6.calendar/v1"
FIXED_CONTRACT = "ESZ2026"


def aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("calendar/freeze timestamp needs an explicit timezone")
    return parsed


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), NY)


def prior_weekday(day: date) -> date:
    return day - timedelta(days=3 if day.weekday() == 0 else 1)


def required_windows(day_text: str):
    """Same eight fixed-clock windows as the unchanged Phase 5 coverage gate."""
    day = date.fromisoformat(day_text)
    if day.weekday() > 4:
        raise ValueError("RTH observation date must be a weekday")
    prior = prior_weekday(day)
    current_sunday = day - timedelta(days=day.weekday() + 1)
    previous_sunday = current_sunday - timedelta(days=7)
    windows = [("prior_full", at(prior - timedelta(days=1), 18), at(prior, 17), False),
               ("completed_RTH", at(prior, 9, 30), at(prior, 16), False),
               ("overnight_prefix", at(day - timedelta(days=1), 18), at(day, 9, 25), False),
               ("current_week_prefix", at(current_sunday, 18), at(day, 9, 25), True),
               ("previous_completed_week", at(previous_sunday, 18), at(previous_sunday + timedelta(days=5), 17), True)]
    cursor, members = day, []
    for _ in range(3):
        cursor = prior_weekday(cursor)
        members.insert(0, cursor)
    windows.extend(("composite_member_" + member.isoformat(), at(member, 9, 30), at(member, 16), False) for member in members)
    return windows


def support_exclusions(day_text: str, events: list[dict]) -> list[dict]:
    """Identify nominal closed/shortened history without holiday substitution."""
    day = date.fromisoformat(day_text)
    if day.weekday() > 4:
        return [{"window": "current_RTH", "affected_dates": [day_text], "reason": "weekend"}]
    bad = {}
    for event in events:
        event_day = date.fromisoformat(event["session_date"])
        if event["kind"] not in {"closed", "shortened"}:
            raise ValueError("known calendar event must be closed or shortened")
        if event_day in bad:
            raise ValueError("duplicate known calendar event")
        bad[event_day] = event["kind"]
    checks = []
    if day in bad:
        checks.append({"window": "current_RTH", "affected_dates": [day_text], "reason": bad[day]})
    for window, start, end, _ in required_windows(day_text):
        if window in {"prior_full", "completed_RTH"}:
            days = [prior_weekday(day)]
        elif window.startswith("composite_member_"):
            days = [start.date()]
        elif window == "current_week_prefix":
            monday = day - timedelta(days=day.weekday())
            days = [monday + timedelta(days=n) for n in range(day.weekday())]
        elif window == "previous_completed_week":
            monday = start.date() + timedelta(days=1)
            days = [monday + timedelta(days=n) for n in range(5)]
        else:
            # No holiday substitution is inferred for an overnight input.
            # Current closed/shortened dates are already ineligible above.
            days = []
        affected = sorted(d.isoformat() for d in days if d in bad)
        if affected:
            checks.append({"window": window, "affected_dates": affected,
                           "reason": "known_nonfull_required_history"})
    return checks


def expected_dates(frozen_at: str, events: list[dict], count: int = 20) -> list[str]:
    frozen = aware(frozen_at).astimezone(NY)
    if type(count) is not int or not 1 <= count <= 60:
        raise ValueError("bounded positive calendar sample size required")
    cursor = frozen.date()
    selected = []
    for _ in range(200):
        day = cursor.isoformat()
        if cursor.weekday() < 5 and at(cursor, 9, 25) > frozen and not support_exclusions(day, events):
            selected.append(day)
            if len(selected) == count:
                return selected
        cursor += timedelta(days=1)
    raise ValueError("no supported bounded calendar block")


def validate_calendar(calendar: dict, frozen_at: str) -> dict:
    if calendar.get("schema") != SCHEMA or calendar.get("timezone") != "America/New_York":
        raise ValueError("explicit Phase 6 calendar schema and New York timezone required")
    if calendar.get("sample_size") != 20 or calendar.get("no_replacement_of_scheduled_failures") is not True:
        raise ValueError("fixed twenty-session nonreplacement rule required")
    freeze = aware(frozen_at)
    anchor = calendar.get("freeze_anchor") or {}
    if not aware(anchor["earliest_allowed_freeze"]) <= freeze < aware(anchor["latest_allowed_freeze_exclusive"]):
        raise ValueError("freeze lies outside the adopted calendar-anchor interval; do not silently shift dates")
    events = calendar.get("known_events") or []
    dates = calendar.get("scheduled_dates") or []
    if len(dates) != 20 or len(set(dates)) != 20 or dates != sorted(dates):
        raise ValueError("twenty unique ordered scheduled dates required")
    if dates != expected_dates(frozen_at, events):
        raise ValueError("dates are not the first twenty full supported sessions after freeze")
    contract = calendar.get("contract") or {}
    if (contract.get("contract"), contract.get("symbol"), contract.get("adjustment")) != (
            FIXED_CONTRACT, "CME_MINI:ESZ2026", "individual_contract_unadjusted"):
        raise ValueError("unsupported contract transition, continuous series or adjustment")
    expiry, roll = aware(contract["last_trade_at"]), aware(contract["customary_roll_at"])
    final_close = at(date.fromisoformat(dates[-1]), 16)
    if final_close >= expiry or final_close >= roll:
        raise ValueError("calendar exceeds declared pre-roll contract-suitability interval")
    sessions = calendar.get("sessions") or []
    if len(sessions) != 20 or [r.get("session_date") for r in sessions] != dates:
        raise ValueError("all twenty explicit session records required")
    for row in sessions:
        day = date.fromisoformat(row["session_date"])
        cutoff = at(day, 9, 25)
        if row.get("cutoff_ny") != cutoff.isoformat() or row.get("cutoff_utc") != cutoff.astimezone(timezone.utc).isoformat():
            raise ValueError("cutoff violates New York DST-aware conversion")
        if row.get("rth_open_ny") != at(day, 9, 30).isoformat() or row.get("rth_close_ny") != at(day, 16).isoformat():
            raise ValueError("full RTH boundaries differ")
    actual_exclusions = []
    cursor = freeze.astimezone(NY).date()
    while cursor <= date.fromisoformat(dates[-1]):
        if cursor.weekday() < 5 and at(cursor, 9, 25) > freeze:
            excluded = support_exclusions(cursor.isoformat(), events)
            if excluded:
                actual_exclusions.append({"session_date": cursor.isoformat(), "affected_windows": excluded})
        cursor += timedelta(days=1)
    recorded_exclusions = calendar.get("calendar_exclusions") or []
    if recorded_exclusions != actual_exclusions:
        raise ValueError("predeclared calendar/support exclusions differ from unchanged required windows")
    return {"status": "passed", "scheduled_sessions": 20, "first": dates[0], "last": dates[-1],
            "known_weekday_exclusions": len(recorded_exclusions), "timezone": "America/New_York",
            "required_windows_per_session": 8, "future_market_observations_verified": False,
            "scope": "Nominal calendar and fixed-contract support only; actual daily input coverage is still required."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--frozen-at", required=True, help="Actual protocol-freeze timestamp, with timezone")
    args = parser.parse_args()
    print(json.dumps(validate_calendar(json.loads(args.calendar.read_text()), args.frozen_at), indent=2))


if __name__ == "__main__":
    main()
