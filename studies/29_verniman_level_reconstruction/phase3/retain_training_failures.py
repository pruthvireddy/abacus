#!/usr/bin/env python3
"""Retain explicit current-stage failures without opening any new answer source.

This does not generate candidate maps. It attributes already retained Phase 1
baselines and declares unavailable Phase 3 fields. Existing stage outputs are
never overwritten. Run only after final implementation-byte retention.
"""
from datetime import date, datetime, time, timedelta
import csv
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior(day):
    return day - timedelta(days=3 if day.weekday() == 0 else 1)


def at(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), NY).isoformat()


def profile(name, start, end, sessions, **extra):
    return dict(window=name, expected_start=start, expected_end=end,
                expected_sessions=sessions, included_sessions=[],
                readiness="unavailable", rows=None, raw_total_mass=None,
                last_included_completed_bar=None, code_settings_input_identity="see record identities",
                reason="No accepted identified Phase 3 distribution/capture; no detector executed.", **extra)


def main():
    settings = json.loads((PHASE / "settings.json").read_text())
    declared = json.loads((PHASE / "input-declaration.json").read_text())
    stage = ROOT / declared["stage"]
    if (stage / "training-results.json").exists():
        raise SystemExit("Refusing to overwrite retained failure records")
    implementation = stage / "implementation-manifest.json"
    if not implementation.exists():
        raise SystemExit("Retain implementation bytes before recording failures")
    baseline = ROOT / "work/29_verniman_level_reconstruction/phase1_20261030/frozen-candidates.csv"
    neutral = ROOT / "work/29_verniman_level_reconstruction/phase2_20261030T222323Z/neutral-baselines.json"
    with baseline.open(newline="") as handle:
        originals = {row["date"]: row for row in csv.DictReader(handle)}
    observed = {row["date"]: row for row in json.loads(neutral.read_text())["observations"]}
    old_inventory = json.loads((PHASE.parent / "phase2/level-inventory.json").read_text())
    source_counts = {day: sum(row["session_date"] == day for row in old_inventory["levels"])
                     for day in originals}
    records = []
    for day_text in settings["training_dates"]:
        day = date.fromisoformat(day_text)
        previous = prior(day)
        members = []
        cursor = day
        for _ in range(3):
            cursor = prior(cursor)
            members.insert(0, cursor)
        monday = day - timedelta(days=day.weekday())
        week_start = monday - timedelta(days=1)
        previous_week = week_start - timedelta(days=7)
        profiles = [
            profile("completed_RTH", at(previous, 9, 30), at(previous, 16), [previous.isoformat()]),
            profile("overnight_prefix", at(day - timedelta(days=1), 18), at(day, 9, 25), [day_text]),
            profile("current_week_prefix", at(week_start, 18), at(day, 9, 25),
                    [(monday + timedelta(days=i)).isoformat() for i in range(day.weekday() + 1)]),
            profile("previous_completed_week", at(previous_week, 18), at(previous_week + timedelta(days=5), 17),
                    [(previous_week + timedelta(days=i)).isoformat() for i in range(1, 6)]),
            profile("explicit_composite_RTH3", at(members[0], 9, 30), at(members[-1], 16),
                    [x.isoformat() for x in members], balance_established=False,
                    member_lineage=None, exclusions=["no accepted compatible member distributions"]),
        ]
        reasons = ["TradingView separate-layout Make-copy submission security-blocked; Phase 3 compile/Replay not attempted.",
                   "Alternate connector input lacks established required ETH/feed/adjustment identity and was not accepted."]
        if day <= date(2026, 10, 6):
            reasons.append("Latest5000-bar connector response starts October6 14:20 New York, after this cutoff.")
        else:
            reasons.append("Some later neutral bars exist, but no compatible identified expanded map was computed or captured.")
        fields = {key: value for key, value in originals[day_text].items()
                  if key not in ("date", "cutoff_new_york")} if day_text in originals else None
        record = {
            "session_date": day_text, "status": "unavailable", "failure_reasons": reasons,
            "frozen_settings_identity": sha(PHASE / "settings.json"),
            "implementation_manifest_sha256": sha(implementation),
            "input_assessment_sha256": sha(stage / "market-input-assessment.json"),
            "symbol": settings["symbol"], "cutoff": at(day, 9, 25),
            "expected_last_included_bar": [at(day, 9, 20), at(day, 9, 25)],
            "actual_phase3_last_included_bar": None,
            "phase1_baseline_fields": fields,
            "baseline_attribution": {"status": "reused_Phase1_and_Phase2_observation_not_Phase3_capture",
                "csv_path": str(baseline.relative_to(ROOT)), "csv_sha256": sha(baseline),
                "neutral_record_path": str(neutral.relative_to(ROOT)), "neutral_record_sha256": sha(neutral),
                "source_periods": {key: observed[day_text][key] for key in
                     ("full_and_rth_source_trading_date", "previous_week_start", "last_included_open", "last_included_close")}}
                if fields else {"status": "no_accepted_cutoff_baseline", "fields": None},
            "profiles": profiles, "phase3_regions": None, "phase3_edges": None,
            "phase3_candidate_counts": None, "phase3_cap_omissions": None,
            "pbt": {"P1": "unavailable_missing_supported_anchors", "P2": "unavailable_missing_supported_anchors",
                    "anchor_ids": [], "reconstruction_ready_at": None, "source_historical_available_at": None},
            "comparison_status": "not_executed", "matched_pairs": None, "unmatched_generated_candidates": None,
            "source_access": "retained_Phase2_inventory_only_previously_exposed" if fields else "new_target_sources_closed",
            "retained_phase2_source_occurrences": source_counts.get(day_text),
            "native_browser_evidence": "none_for_Phase3; see browser-access.json",
            "out_of_sample": False,
        }
        records.append(record)
    result = {"schema": "abacus.study29.phase3.training-status/v1", "protocol_version": "3.0.0",
              "phase3_id": stage.name, "kind": "explicit_unavailable_cases_not_candidate_maps",
              "native_phase3_compilation": "not_attempted_security_blocked",
              "new_training_answers_opened": False, "seven_map_reveal_gate_passed": False,
              "comparison_status": "not_executed", "records": records}
    encoded = json.dumps(result, indent=2) + "\n"
    (stage / "training-results.json").write_text(encoded)
    (PHASE / "training-results.json").write_text(encoded)
    (stage / "training-record-hashes.json").write_text(json.dumps({
        row["session_date"]: hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        for row in records}, indent=2) + "\n")
    print(json.dumps({"records": len(records), "retained_sha256": sha(stage / "training-results.json"),
                      "actual_expanded_maps": 0, "new_answers_opened": False}, indent=2))


if __name__ == "__main__":
    main()
