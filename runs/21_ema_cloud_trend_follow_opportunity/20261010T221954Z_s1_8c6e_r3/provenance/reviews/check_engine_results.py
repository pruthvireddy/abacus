"""Independent saved-ledger scope/denominator and price-path review.

No producer engine, scorer, reference, or statistical routine is imported.
Only the saved authorized development outcomes are examined. The numerical
producer sources remain frozen; execution imports are byte guard helpers only.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

import pandas as pd

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[2]
sys.path.insert(0, str(ROOT / "studies/21_ema_cloud_trend_follow_opportunity"))
from src.execution import assert_frozen_sources


def record(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def require(condition, message):
    if not bool(condition):
        raise AssertionError(message)


def equal(actual, expected, message):
    if pd.isna(actual) or pd.isna(expected):
        require(pd.isna(actual) and pd.isna(expected), message + " null")
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        require(math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12), message)
    else:
        require(actual == expected, message)


def main():
    began = time.monotonic()
    before = json.loads((HERE / "engine-result-review-before.json").read_text())
    for item in before["sources_and_control_files"]:
        require(record(Path(item["path"])) == item, "checker/control identity changed")
    assert_frozen_sources(STAGE, ROOT)
    config = json.loads((STAGE / "config.json").read_text())
    manifest = json.loads((STAGE / "events.manifest.json").read_text())
    end = pd.Timestamp(config["development_endpoint_ny"]).tz_convert("UTC")
    cells, checked, input_identities = [], 0, []
    numeric = ("mfe", "mae", "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr")
    flags = ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie")
    for product in config["products"]:
        for interval in config["interval_minutes"]:
            selected = {r["role"]: r for r in manifest["records"] if r["product"] == product and r["interval_minutes"] == interval}
            frames = {}
            for role in ("technical", "events", "outcomes"):
                item = selected[role]
                path = Path(item["path"])
                actual = record(path)
                require(actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"], "saved ledger byte identity")
                frames[role] = pd.read_parquet(path)
                require(len(frames[role]) == item["row_count"], "saved row count")
                input_identities.append(actual)
            tech, events, outcomes = (frames[role] for role in ("technical", "events", "outcomes"))
            require(tech.timestamp.is_monotonic_increasing and not tech.timestamp.duplicated().any(), "full support chronology")
            require(tech.available_at.le(end).all(), "bar roster exceeds endpoint")
            tech_year = tech.timestamp.dt.tz_convert("America/New_York").dt.year
            require(tech_year.between(2017, 2020).all(), "bar roster beyond causal warmup/development")
            require(events.timestamp.dt.tz_convert("America/New_York").dt.year.between(2018, 2020).all(), "reserved signal event")
            require(events.accepted.all() and events.event_id.is_unique, "accepted event identity")
            accepted_technical = tech.loc[tech.accepted & tech_year.between(2018, 2020)]
            require(accepted_technical.event_id.tolist() == events.event_id.tolist(), "future-path exclusions changed accepted population")
            require((events.reference_price == events.close).all(), "reference is not confirmed signal close")
            require(events.usable.all() and events.feature_valid.all() and events.armed_before.all(), "acceptance gateway violated")
            threshold = config["minimum_width_points"][product]
            require((events.width + 1e-10 * max(1, abs(threshold)) >= threshold).all(), "width gateway violated")
            require(events.feature_contract.eq(events.contract).all(), "signal/source contract mismatch")
            reference_time = events.timestamp if interval == 3 else events.available_at
            require(events.feature_available_at.le(reference_time).all(), "mapped feature lookahead")
            if interval == 5:
                require(events.feature_source_timestamp.eq(events.timestamp).all(), "5m source is not current candle")
            hs = set(config[f"horizons_{interval}m"])
            require(not outcomes.duplicated(["event_id", "horizon"]).any(), "duplicate outcome identity")
            require(len(outcomes) == len(events) * len(hs), "missing outcome rows")
            require(set(outcomes.horizon) == hs and set(outcomes.event_id) == set(events.event_id), "outcome roster changed")
            require(outcomes.groupby("event_id").horizon.nunique().eq(len(hs)).all(), "an event lacks frozen horizons")
            roster = tech.to_dict("records")
            event_by_id = {event["event_id"]: event for event in events.to_dict("records")}
            for observed in outcomes.to_dict("records"):
                event = event_by_id[observed["event_id"]]
                i, h = int(event["signal_idx"]), int(observed["horizon"])
                require(roster[i]["timestamp"] == event["timestamp"], "absolute chart index mismatch")
                path = roster[i + 1:i + h + 1]
                reason = "development_endpoint" if len(path) < h else ""
                if not reason and any(row["available_at"] > end for row in path):
                    reason = "development_endpoint"
                if not reason:
                    for row in path:
                        if not row["usable"] or not all(pd.notna(row[key]) and math.isfinite(float(row[key])) for key in ("high", "low", "close")):
                            reason = "invalid_future_slot:" + str(row["quality_reason"])
                            break
                        if row["contract"] != event["contract"]:
                            reason = "contract_switch"
                            break
                if reason:
                    equal(observed["status"], "censored", "censored status")
                    equal(observed["censor_reason"], reason, "quality/roll/split censor reason")
                    for key in numeric + flags:
                        equal(observed[key], None, "censored outcome must be null")
                else:
                    require(all(pd.Timestamp(row["timestamp"]).tz_convert("America/New_York").year in (2018, 2019, 2020) for row in path), "reserved required outcome slot")
                    entry, direction = float(event["reference_price"]), int(event["direction"])
                    highest, lowest = max(float(row["high"]) for row in path), min(float(row["low"]) for row in path)
                    mfe = max(0., highest - entry) if direction == 1 else max(0., entry - lowest)
                    mae = max(0., entry - lowest) if direction == 1 else max(0., highest - entry)
                    delta = direction * (float(path[-1]["close"]) - entry)
                    eps = 1e-10 * max(1., mfe, mae)
                    expected = {"mfe": mfe, "mae": mae, "terminal_delta": delta,
                                "favorable": delta > 0, "neutral": delta == 0, "adverse": delta < 0,
                                "mfe_gt_mae": mfe - mae > eps, "mfe_mae_tie": abs(mfe - mae) <= eps}
                    equal(observed["status"], "completed", "completed status")
                    equal(observed["censor_reason"], "", "completed reason")
                    for key, value in expected.items():
                        equal(observed[key], value, "independent scalar " + key)
                    atr = event["entry_atr"]
                    for key in ("mfe", "mae", "terminal_delta"):
                        value = expected[key] / atr if pd.notna(atr) and atr > 0 else None
                        equal(observed[key + "_atr"], value, "ATR denominator")
                    equal(observed["terminal_at"], path[-1]["available_at"], "terminal time")
                    equal(observed["elapsed_minutes"], (path[-1]["available_at"] - event["entry_at"]).total_seconds() / 60, "elapsed time")
                checked += 1
            # Completion is a prefix property: later completed horizons may never
            # follow an earlier censored required path for the same event.
            for _, group in outcomes.groupby("event_id"):
                ordered = group.sort_values("horizon")
                censored_seen = False
                for status in ordered.status:
                    require(not (censored_seen and status == "completed"), "compressed missing timeline")
                    censored_seen |= status == "censored"
            primary = outcomes.loc[outcomes.horizon.eq(15)]
            good = primary.loc[primary.status.eq("completed")]
            dev = tech.loc[tech_year.between(2018, 2020)]
            eligible = dev.usable & dev.feature_valid
            annual = []
            for year in (2018, 2019, 2020):
                part = good.loc[good.year.eq(year)]
                annual.append({"year": year, "completed": len(part), "mean_terminal_delta": statistics.mean(part.terminal_delta) if len(part) else None})
            cells.append({"product": product, "interval_minutes": interval, "accepted": len(events),
                "scheduled_development_slots": len(dev), "eligible_slots": int(eligible.sum()),
                "events_per_1000_eligible_slots": len(events) / int(eligible.sum()) * 1000,
                "primary_completed": len(good), "primary_censored": len(primary) - len(good),
                "primary_completion_share": len(good) / len(events), "contributing_sessions": good.session.nunique(),
                "mean_mfe": statistics.mean(good.mfe), "mean_mae": statistics.mean(good.mae),
                "mean_terminal_delta": statistics.mean(good.terminal_delta), "median_terminal_delta": statistics.median(good.terminal_delta),
                "favorable_share": float(good.favorable.astype(float).mean()), "mfe_gt_mae_share": float(good.mfe_gt_mae.astype(float).mean()),
                "closure_crossing_primary": int(good.crosses_closure.eq(True).sum()),
                "same_session_primary": int(good.same_session.eq(True).sum()),
                "censor_reasons_all_horizons": {str(k): int(v) for k, v in outcomes.loc[outcomes.status.eq("censored"), "censor_reason"].value_counts().items()},
                "annual_primary": annual, "checked_outcome_rows": len(outcomes)})
            print(json.dumps(cells[-1]), flush=True)
    assert_frozen_sources(STAGE, ROOT)
    for item in before["sources_and_control_files"]:
        require(record(Path(item["path"])) == item, "checker/control identity changed after review")
    output = {"status": "passed", "reviewer": "study_engine_independent_saved_result_review",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic() - began,
        "command": {"argv": sys.argv, "cwd": str(Path.cwd()), "python": sys.executable, "version": sys.version},
        "before_execution": record(HERE / "engine-result-review-before.json"), "input_identities": input_identities,
        "core_guard_before": "passed", "core_guard_after": "passed", "scope": "Only saved 2018–2020 accepted events and already scored outcomes; 2017 bars serve causal state only.",
        "reserved_outcomes_examined": False, "independent_scalar_all_outcome_rows": checked,
        "scientific_findings": [], "cells": cells,
        "interpretation_limits": ["Development descriptive price paths; no profitability or executable stop/target interpretation.",
            "Four-week paired bootstrap intervals and one/eight-week sensitivities are reviewed separately when saved summary tables are available.",
            "Same-session/uninterrupted views select completed paths after observing support; their denominators are not the full accepted population.",
            "Session-balanced results condition on contributing sessions; eligible-bar opportunity rates do not assert zero events on unknown coverage.",
            "H15 spans45 active minutes on3m and75 on5m; compare60/150active-minute pairs separately.",
            "GC accepted support is materially smaller; unknown gaps and conservative holiday/warmup policy restrict observed populations."]}
    with (HERE / "engine-result-review.json").open("x") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
