#!/usr/bin/env python3
"""Assemble actual native receipts from retained UI text and visual reviews.

This file never imports a candidate/selection model or loads predicted values.
Prices/IDs/reasons come from captured tooltip text. Branch/pivot display states
and cutoff boundaries come from separately hashed screenshot reviews. The
parser refuses to fill absent native observations from local predictions.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
STUDY = "studies/29_verniman_level_reconstruction"
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
SOURCE_SHA = "1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924"
NY = ZoneInfo("America/New_York")
SETTINGS = {"symbol": "CME_MINI:ESZ2026", "minutes": 5, "chart_type": "standard candles", "session": "ETH",
            "timezone": "America/New_York", "row_ticks": 16, "value_area_percent": 70, "cutoff": "09:25",
            "pivot_policy": "P0", "target_policy": "D1", "manual_anchors": []}
KEYS = ("pivot", "bullish1", "bullish2", "bullish3", "bearish1", "bearish2", "bearish3",
        "pivot_status", "bullish_status", "bearish_status")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def within(root, relative):
    if Path(relative).is_absolute():
        raise ValueError("relative retained-artifact path required")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("artifact path escapes its declared root")
    return path


def pin(root, path):
    return {"path": str(path.relative_to(root)), "sha256": digest(path)}


def pinned(root, record):
    path = within(root, record["path"])
    if not path.is_file() or digest(path) != record["sha256"]:
        raise ValueError("missing or changed observed artifact: " + record["path"])
    return path


def stamp(text):
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware observation required")
    return value


def tooltip_lines(text):
    if "container common-tooltip-wrapper" not in text:
        raise ValueError("actual captured tooltip wrapper required")
    cropped = text[text.index("container common-tooltip-wrapper"):]
    lines = re.findall(r"^\s*\d+ text (.*)$", cropped, flags=re.M)
    if not lines:
        raise ValueError("tooltip has no captured text observations")
    return lines


def parse_candidate(text, *, target=False):
    lines = tooltip_lines(text)
    originals = [i for i, line in enumerate(lines) if line.startswith("Original price=")]
    if not originals:
        # Missing-target cells display a retained branch reason, never a price.
        known = ("FEWER_THAN_THREE_ELIGIBLE_DESTINATIONS", "PIVOT_FALLBACK_TARGET_ABSTENTION", "PIVOT_UNAVAILABLE")
        if target and any(any(reason in line for reason in known) for line in lines):
            return None
        raise ValueError("no original native candidate price/identity; unavailable cannot be filled")
    if len(originals) != 1 or originals[0] == 0:
        raise ValueError("one unambiguous original native candidate required")
    index = originals[0]
    identifier = lines[index - 1]
    if not (identifier.startswith("CME_MINI:ESZ2026:") or identifier.startswith("full:")):
        raise ValueError("unexpected native candidate identity")
    price = re.fullmatch(r"Original price=([-+\d.]+); interval=\[([-+\d.]+), ([-+\d.]+)\]", lines[index])
    family = re.fullmatch(r"Family=(.*?); role=(.*?); window=(.*)", lines[index + 1]) if index + 1 < len(lines) else None
    auction = re.fullmatch(r"Auction=(.*?); parent=(.*?); side=(.*?); readyAt=(.*)", lines[index + 2]) if index + 2 < len(lines) else None
    if not price or not family or not auction:
        raise ValueError("native price/interval/family/window/auction provenance missing")
    value, low, high = map(float, price.groups())
    if not all(isfinite(x) for x in (value, low, high)) or not low <= value <= high:
        raise ValueError("invalid observed native interval")
    result = {"candidate_id": identifier, "price": value, "interval": [low, high],
              "family": family[1], "role": family[2], "window": family[3],
              "auction_id": auction[1], "parent_id": auction[2], "side": auction[3],
              "native_ready_at": auction[4]}
    if target:
        reason_lines = [line for line in lines if line.startswith("Reason=")]
        if len(reason_lines) != 1:
            raise ValueError("actual native target reason/origin required")
        reason = re.fullmatch(r"Reason=(.*?); originating=(.*)", reason_lines[0])
        group_indices = [i for i, line in enumerate(lines) if line.startswith("Exact-price group has ")]
        if not reason or len(group_indices) != 1:
            raise ValueError("actual native confluence group required")
        group_index = group_indices[0]
        count = re.fullmatch(r"Exact-price group has (\d+) original IDs\. No averaging\.", lines[group_index])
        members = lines[group_index + 1:]
        if (not count or int(count[1]) > 16 or len(members) != int(count[1]) or
                len(set(members)) != len(members) or identifier not in members or reason[2] not in members):
            raise ValueError("full observed native group IDs missing or conflicting")
        result.update({"reason_code": reason[1], "originating_candidate_id": reason[2],
                       "group_candidate_ids": members, "group_count": len(members)})
    return result


def conservative_advanced_close(path, day):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 2:
        raise ValueError("advanced export needs at least two observed bars")
    fields = {key.lower(): key for key in rows[0]}
    if "time" not in fields:
        raise ValueError("advanced export requires explicit bar timestamps")
    opens = []
    for row in rows:
        text = row[fields["time"]]
        opened = datetime.fromtimestamp(int(text), timezone.utc) if text.lstrip("-").isdigit() else stamp(text)
        opens.append(opened.astimezone(NY))
    if any(a >= b for a, b in zip(opens, opens[1:])) or opens[-1].date().isoformat() != day:
        raise ValueError("advanced export has conflicting date/order")
    # The final exported bar may still be forming. The preceding observed bar
    # is conservatively completed when a later bar is present.
    latest = opens[-2] + timedelta(minutes=5)
    if latest < stamp(day + "T09:35:00-04:00"):
        raise ValueError("advanced export does not prove completed RTH bars")
    return {"latest_observed_bar_close": latest.isoformat(), "penultimate_open": opens[-2].isoformat(),
            "last_exported_open": opens[-1].isoformat(), "method": "penultimate exported open + five minutes; final possibly forming bar withheld"}


def assemble(root, stage, review_path, output):
    review = json.loads(review_path.read_text())
    day = review.get("session_date")
    if review.get("schema") != "abacus.study29.phase5.native-visual-review/v1" or day not in DATES:
        raise ValueError("explicit authorized-date screenshot review required")
    if output.exists() or not output.is_relative_to(stage) or not review_path.is_relative_to(stage):
        raise ValueError("fresh native receipt and retained visual review inside declared stage required")
    if review.get("settings") != SETTINGS or set(review.get("states", {})) != {"cutoff", "advanced", "restart"}:
        raise ValueError("actual settings and all three screenshot states required")
    settings_path = pinned(root, review["settings_evidence"])
    readback = pinned(root, review["source_readback"])
    if sha256(readback.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != SOURCE_SHA:
        raise ValueError("actual source readback differs from frozen4.0.1")
    source_path = root / STUDY / "indicator/verniman_levels_phase4.pine"
    if digest(source_path) != SOURCE_SHA:
        raise ValueError("retained selector source changed")
    result = {"schema": "abacus.study29.phase5.native-date/v1", "session_date": day,
              "source": pin(root, source_path), "implementation": "4.0.1", "control": "4.0.0",
              "settings": SETTINGS, "states": {}, "visual_review": pin(root, review_path),
              "source_readback": pin(root, readback), "settings_evidence": pin(root, settings_path),
              "assembly_code": pin(root, Path(__file__).resolve()),
              "native_model_values_mixed": False, "local_prediction_fields_read": False,
              "scope": "Captured native text plus separately hashed screenshot observations; no model values substituted."}
    selections = []
    for state_name in ("cutoff", "advanced", "restart"):
        visual = review["states"][state_name]
        raw_path = stage / "native-evidence" / f"{day}-{state_name}-raw.json"
        raw = json.loads(raw_path.read_text())
        if raw.get("session_date") != day or raw.get("state") != state_name:
            raise ValueError("raw native observation date/state differs")
        screenshot = pinned(root, visual["screenshot"])
        if screenshot != within(stage, raw["screenshot"]):
            raise ValueError("visual review screenshot differs from raw observation")
        entries = raw.get("tooltips", [])
        tips = {r.get("key"): r for r in entries}
        if len(entries) != 10 or set(tips) != set(KEYS):
            raise ValueError("all ten actual native tooltip captures required")
        evidence = [pin(root, raw_path), pin(root, screenshot)]
        for key, item in tips.items():
            path = within(stage, item["path"])
            if path.name != f"{day}-{state_name}-{key}.txt" or not path.is_relative_to(stage / "native-evidence"):
                raise ValueError("tooltip capture identity differs")
            if item["tooltip"] not in path.read_text():
                raise ValueError("embedded native tooltip differs from retained actual AX capture")
            evidence.append(pin(root, path))
        pivot_capture = {"method": "direct selection-price tooltip", "original_raw_capture_retained": True}
        observed_at = stamp(raw["observed_at"])
        override = visual.get("pivot_capture_override")
        if override is not None:
            if override.get("format") != "selected_pivot_ledger":
                raise ValueError("only an explicit selected-pivot native ledger supplement is supported")
            supplement = pinned(root, override["capture"])
            supplement_image = pinned(root, override["screenshot"])
            if not supplement.is_relative_to(stage / "native-evidence") or not supplement_image.is_relative_to(stage / "native-evidence"):
                raise ValueError("native pivot supplement must remain in retained evidence directory")
            text = supplement.read_text()
            lines = tooltip_lines(text)
            if not lines[0].startswith("P0_") or lines[0] != visual["pivot"]["reason_code"]:
                raise ValueError("supplement must identify the actual selected P0 reason, not an alternative")
            pivot = parse_candidate(text)
            captured_at = stamp(override["captured_at"])
            observed_at = max(observed_at, captured_at)
            pivot_capture.update({"method": "selected-pivot alternative-ledger tooltip supplement",
                "capture": override["capture"], "screenshot": override["screenshot"],
                "captured_at": override["captured_at"], "captured_at_basis": override["captured_at_basis"],
                "selected_reason_observed_in_supplement": lines[0]})
            evidence.extend([override["capture"], override["screenshot"]])
        else:
            pivot = parse_candidate(tips["pivot"]["tooltip"])
        if pivot["price"] != visual["pivot"]["price"]:
            raise ValueError("screenshot pivot price differs from actual tooltip")
        if not visual["pivot"].get("reason_code") or not isinstance(visual["pivot"].get("fallback"), bool):
            raise ValueError("screenshot-observed pivot reason/fallback required")
        pivot.update({k: visual["pivot"][k] for k in ("reason_code", "fallback", "status", "native_display_status")})
        status_lines = tooltip_lines(tips["pivot_status"]["tooltip"])
        if status_lines[0] == "none" and pivot["fallback"]:
            raise ValueError("native fallback-none tooltip conflicts with screenshot status")
        pivot["fallback_detail"] = status_lines[0]
        pivot["native_confluence_text"] = status_lines[1:]
        selection = {"pivot": pivot}
        for side in ("bullish", "bearish"):
            targets, missing_seen = [], False
            for rank in range(1, 4):
                parsed = parse_candidate(tips[side + str(rank)]["tooltip"], target=True)
                if parsed is None:
                    missing_seen = True
                elif missing_seen:
                    raise ValueError("native ordered ladder has a missing middle rank")
                else:
                    parsed["rank"] = rank
                    targets.append(parsed)
            if [t["price"] for t in targets] != visual[side]["prices"]:
                raise ValueError("screenshot target prices differ from actual tooltips")
            if visual[side]["status"] not in ("ready", "partial", "unavailable"):
                raise ValueError("actual native branch display status required")
            selection[side] = {"status": visual[side]["status"], "targets": targets,
                               "native_reason_text": tooltip_lines(tips[side + "_status"]["tooltip"])}
        cutoff = stamp(day + "T09:25:00-04:00")
        if stamp(visual["last_included_open"]) != cutoff - timedelta(minutes=5) or stamp(visual["last_included_close"]) != cutoff or stamp(visual["cutoff"]) != cutoff:
            raise ValueError("actual screenshot included-bar boundary differs")
        state = {"observed_at": observed_at.isoformat(), "raw_capture_completed_at": raw["observed_at"],
                 "pivot_capture_provenance": pivot_capture, "cutoff": visual["cutoff"],
                 "last_included_open": visual["last_included_open"], "last_included_close": visual["last_included_close"],
                 "selection": selection, "evidence": evidence,
                 "screenshot_table_observations": {k: visual[k] for k in ("cutoff_close", "buffer", "reference_count", "destination_group_count", "other_pivots")}}
        if state_name == "advanced":
            csv_path = stage / "native-evidence" / (day + "-advanced.csv")
            proven = conservative_advanced_close(csv_path, day)
            state["latest_observed_bar_close"] = proven["latest_observed_bar_close"]
            state["advance_evidence_method"] = proven
            evidence.append(pin(root, csv_path))
        result["states"][state_name] = state
        selections.append(selection)
    if selections[0] != selections[1] or selections[0] != selections[2]:
        raise ValueError("actual native selection identity/price/reason/group/state changed across cutoff/advance/restart")
    if [stamp(result["states"][s]["observed_at"]) for s in ("cutoff", "advanced", "restart")] != sorted(stamp(result["states"][s]["observed_at"]) for s in ("cutoff", "advanced", "restart")):
        raise ValueError("native observations do not retain chronological order")
    result["three_state_selection_semantics_equal"] = True
    result["assembled_at"] = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return {"session_date": day, "receipt": pin(root, output), "native_state_invariance": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--visual-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    def path(value):
        return value.resolve() if value.is_absolute() else (root / value).resolve()
    stage = path(args.stage)
    if stage.parent != root / "work/29_verniman_level_reconstruction" or not stage.name.startswith("phase5_"):
        raise ValueError("explicit Phase5 work stage required")
    print(json.dumps(assemble(root, stage, path(args.visual_review), path(args.output)), indent=2))


if __name__ == "__main__":
    main()
