"""Independent read-only explanatory-pattern and exact-transfer review.

Reads saved report JSON and CSV bytes only. It neither imports the exporter nor
loads market data, and does not establish research validity or execution fills.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha(path)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stripped(report):
    result = deepcopy(report)
    for key in ("id", "publishedAt", "patterns", "patternOverviewId"):
        result.pop(key, None)
    for section in result["sections"]:
        section.pop("patternId", None)
        section.pop("patternFocus", None)
    return result


def sign(candle):
    return (candle["close"] > candle["open"]) - (candle["close"] < candle["open"])


def close(a, b):
    return abs(a - b) < 1e-9


def review_geometry(pattern, analysis):
    checked = Counter()
    for variant in pattern["variants"]:
        candles = variant["candles"]
        by_id = {c["id"]: c for c in candles}
        ids = [c["id"] for c in candles]
        require(len(by_id) == len(candles), "Duplicate schematic candle IDs")
        for c in candles:
            require(0 <= c["low"] <= min(c["open"], c["close"]) <=
                    max(c["open"], c["close"]) <= c["high"] <= 100,
                    "Invalid illustrative OHLC geometry")
        marks = variant.get("marks", [])
        for mark in marks:
            require(mark["startCandle"] in by_id and mark["endCandle"] in by_id,
                    "Missing mark candle")
            require(ids.index(mark["startCandle"]) <= ids.index(mark["endCandle"]),
                    "Mark reverses source order")
        checked["variants"] += 1
        checked["candles"] += len(candles)
        checked["marks"] += len(marks)
        require("schematic" in pattern["description"].lower() and
                "not actual" in pattern["description"].lower(),
                "Illustration must distinguish synthetic from market geometry")
        if analysis == "trend-length":
            direction = sign(by_id["t1"])
            require(direction != 0 and all(sign(by_id[x]) == direction for x in ("t1", "t2", "t3")),
                    "Exact trend candles differ in direction")
            require(sign(by_id["x"]) == 0 and sign(by_id["breaker"]) == -direction,
                    "Exact trend lacks observed start/end breaker")
            require(all(sign(by_id[x]) == direction for x in ("u1", "u2")),
                    "Censored trend direction mismatch")
            require("unknown" in variant["description"] and "excluded" in variant["description"],
                    "Trend caption must identify excluded breaker and unknown exact length")
            checked["exact_and_censored_trend_variants"] += 1
            continue
        direction = sign(by_id["r"])
        require(direction in (-1, 1) and by_id["r"]["role"] == "signal", "R must be directional signal")
        if analysis.startswith("pullback-"):
            require(all(sign(by_id[x]) == direction for x in ("a1", "a2", "a3")),
                    "Earlier A differs from R direction")
            require(sign(by_id["b"]) == -direction, "B must be one opposite candle")
            require(ids.index("b") + 1 == ids.index("r") and ids.index("a3") + 1 == ids.index("b"),
                    "A/B/R must be adjacent")
            require("x" in by_id and sign(by_id["x"]) != direction,
                    "Exact illustrated A length requires observed prior breaker")
        else:
            require(all(sign(by_id[x]) == -direction for x in ("p1", "p2", "p3")),
                    "Preceding reversal leg must oppose R")
            require(sign(by_id["x"]) == direction, "Known preceding leg start not demonstrated")
        if analysis.endswith("continuation"):
            require(all(sign(by_id[x]) == direction and by_id[x]["role"] == "measured"
                        for x in ("f1", "f2")), "F1/F2 continuation geometry mismatch")
            require(sign(by_id["breaker"]) == -direction, "Continuation failure breaker mismatch")
            require("n=2" in variant["description"] and "n=3" in variant["description"] and
                    "unknown" in variant["description"], "Continuation needs success/failure/unknown explanation")
            checked["continuation_success_failure_variants"] += 1
        elif analysis.endswith("retracement"):
            r, f1 = by_id["r"], by_id["f1"]
            require(direction * (f1["close"] - r["close"]) > 0, "Drawn favorable close is not strict beyond R.close")
            body = [m for m in marks if m["kind"] == "band" and m["label"].startswith("R body")]
            require(len(body) == 1 and close(body[0]["low"], min(r["open"], r["close"])) and
                    close(body[0]["high"], max(r["open"], r["close"])), "R body band includes wicks")
            for mark in marks:
                match = re.match(r"(25|50|75|100)%", mark["label"])
                if not match:
                    continue
                depth = int(match[1])
                expected = r["close"] + (r["open"] - r["close"]) * depth / 100
                require(mark["kind"] == "level" and close(mark["price"], expected), "Incorrect body retracement level")
                require(f1["low"] <= expected if direction == 1 else f1["high"] >= expected,
                        "F1 does not touch drawn body level")
                if depth == 100:
                    require(close(mark["price"], r["open"]) and r["low"] != r["open"] and r["high"] != r["open"],
                            "100% level must reach R.open, not outer wick")
                checked["body_level_formula_checks"] += 1
            require("strictly" in variant["description"] and "order" in variant["description"],
                    "Retracement caption must distinguish strict close and unresolved path")
            checked["retracement_variants"] += 1
        else:
            b, r, f1 = by_id["b"], by_id["r"], by_id["f1"]
            entry = next(m for m in marks if m["kind"] == "level" and m["label"].startswith("Entry reference"))
            stop = next(m for m in marks if m["kind"] == "level" and m["label"].startswith("Stop"))
            expected_stop = min(b["low"], r["low"]) - .25 if direction == 1 else max(b["high"], r["high"]) + .25
            require(close(entry["price"], f1["open"]) and close(stop["price"], expected_stop),
                    "Payoff reference entry or structural stop differs from frozen rule")
            risk = direction * (entry["price"] - stop["price"])
            require(risk > 0, "Invalid schematic risk")
            targets = []
            for mark in marks:
                target = re.match(r"([12])R target", mark["label"])
                if target:
                    expected = entry["price"] + direction * risk * int(target[1])
                    require(close(mark["price"], expected), "Payoff target is not the labelled R multiple")
                    targets.append(mark["price"])
                    checked["target_r_formula_checks"] += 1
            require(targets, "Payoff diagram lacks target")
            if pattern["id"] == "ambiguity":
                for target in targets:
                    require(f1["low"] <= min(stop["price"], target) and
                            f1["high"] >= max(stop["price"], target), "Dual-touch illustration does not touch both levels")
                    require(min(stop["price"], target) < f1["open"] < max(stop["price"], target),
                            "Open must be inside dual-touch bracket")
                require("order is unknown" in variant["description"] and "No intrabar path" in variant["description"],
                        "Dual touch must not infer sequence")
                checked["dual_touch_variants"] += 1
            else:
                require(sign(by_id["c2"]) == -direction and sign(by_id["c3"]) == 0,
                        "Physical payoff horizon must illustrate opposite/doji inclusion")
                for cid in ("f1", "c2", "c3", "c10"):
                    for target in targets:
                        c = by_id[cid]
                        require(c["low"] > min(stop["price"], target) and c["high"] < max(stop["price"], target),
                                "Timeout diagram already crosses a bracket")
                require("omitted" in variant["description"] and "unknown" in variant["description"],
                        "Timeout caption must identify omitted physical candles and barriers")
                checked["physical_timeout_variants"] += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    require(stage.parent == ROOT / "work/22_es_range_xv_focused", "Unexpected stage ownership")
    settings = json.loads((stage / "settings.json").read_text())
    transfer_path = stage / "transfer-verification.json"
    transfer = json.loads(transfer_path.read_text())
    require(len(settings["selected"]) == 18, "Expected all 18 selected ES chart reports")
    require(transfer["result"] == "passed", "Producer transfer is not passing")
    verified_pins = {}
    for item in (*transfer["source_artifacts"], *transfer["outputs"]):
        path = ROOT / item["path"]
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size == item["bytes"] and sha(path) == item["sha256"],
                f"Retained source or frozen draft pin changed: {item['path']}")
        verified_pins[item["path"]] = item["sha256"]
    baseline_path = ROOT / "work/22_es_range_xv_focused/pattern-prior-publication-hashes.json"
    baseline = json.loads(baseline_path.read_text())
    for item in baseline:
        path = ROOT / item["path"]
        require(path.is_file() and path.stat().st_size == item["bytes"] and sha(path) == item["sha256"],
                f"Prior public artifact changed: {item['path']}")
    totals = Counter()
    reports = []
    for selection in settings["selected"]:
        old_id = selection["publicationId"]
        old_path = ROOT / selection["revision"] / "publication.json"
        new_path = stage / (old_id + "-patterns-r1") / "publication.json"
        old, new = json.loads(old_path.read_text()), json.loads(new_path.read_text())
        require(stripped(old) == stripped(new), f"Previous content changed: {old_id}")
        public = json.loads((ROOT / f"apps/narada/public/publications/{old_id}/report.json").read_text())["report"]
        require(old == public, f"Saved original differs from old published selection: {old_id}")
        ids = {p["id"]: p for p in new["patterns"]}
        require(len(ids) == len(new["patterns"]) and new["patternOverviewId"] in ids, "Invalid pattern identity")
        references = {new["patternOverviewId"]}
        numeric_sections = 0
        for section in new["sections"]:
            if section["kind"] not in ("table", "metrics"):
                continue
            numeric_sections += 1
            require(section.get("patternId") in ids and 0 < len(section.get("patternFocus", "")) <= 500,
                    f"Missing quantitative-section explanation: {old_id}/{section['id']}")
            references.add(section["patternId"])
            direction = "bullish" if section["id"].endswith("bullish") else "bearish" if section["id"].endswith("bearish") else None
            if direction and selection["analysis"] != "trend-length":
                require([v["id"] for v in ids[section["patternId"]]["variants"]] == [direction],
                        "Directional section uses mismatched diagram")
        require(references == set(ids), f"An authored explanatory diagram is invisible: {old_id}")
        counts = Counter()
        for pattern in new["patterns"]:
            counts.update(review_geometry(pattern, selection["analysis"]))
        for name in ("source-map.json",):
            require((new_path.parent / name).read_bytes() == (old_path.parent / name).read_bytes(), "Source bindings changed")
        assets = []
        for download in old.get("downloads", []):
            before, after = old_path.parent / download["path"], new_path.parent / download["path"]
            require(before.read_bytes() == after.read_bytes() and sha(after) == download["sha256"], "Selected CSV changed")
            assets.append(pin(after))
        totals.update(counts)
        totals["reports"] += 1
        totals["quantitative_sections"] += numeric_sections
        totals["patterns"] += len(ids)
        totals["table_rows"] += sum(len(s["rows"]) for s in old["sections"] if s["kind"] == "table")
        totals["csv_assets"] += len(assets)
        reports.append({"publication_id": new["id"], "analysis": selection["analysis"],
                        "setting": selection["setting"], "quantitative_sections": numeric_sections,
                        "geometry_checks": dict(counts), "original": pin(old_path), "draft": pin(new_path),
                        "csv_assets": assets, "result": "passed"})
    require(totals["quantitative_sections"] == 216, "Expected all 216 numerical sections")
    result = {"result": "passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Independent illustrative OHLC geometry, frozen pattern-rule semantics, all numerical-section references and exact prior report/source-map/CSV transfer. Reads saved reports only; no market calculations or research revalidation.",
              "transfer_verification_sha256": sha(transfer_path), "reviewer_source": pin(Path(__file__).resolve()),
              "settings": pin(stage / "settings.json"), "totals": dict(totals), "reports": reports,
              "retained_source_and_draft_pins_verified": len(verified_pins),
              "prior_public_artifacts_verified": len(baseline), "prior_public_baseline": pin(baseline_path),
              "manual_semantic_review": [
                  "Continuation counts additional F1... candles and excludes R; an observed opposite/doji fails longer horizons while unresolved boundaries remain unknown.",
                  "General reversal preceding opposite leg is distinct from pullback earlier A followed by exactly one B and returning R.",
                  "Immediate F1 retracement measures R body levels, inclusive touches and strict beyond-R.close favorability, without inferring intrabar sequencing or fills.",
                  "Trend summaries require known starts and ends; the breaker is excluded and boundary-limited observed lengths remain censored.",
                  "Gross OHLC payoff follows ten physical completed candles including opposite/doji; nominal0.25 structural stop, separate1R/2R scenarios, opening precedence and same-bar ambiguity are explained.",
                  "All diagrams are normalized illustrative schematics, independent of observed market bars; diagram success is an example rather than a guaranteed outcome."
              ]}
    out = stage / "pattern-semantics-verification.json"
    require(not out.exists(), "Independent receipt overwrite refused")
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "totals": result["totals"], "receipt": str(out.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
