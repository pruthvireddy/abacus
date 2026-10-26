"""Independent exact-cell and decision-prose check of saved Phase2 synthesis.

Only saved CSV, JSON and authored report bytes are consumed; no presentation
producer or numerical method is imported. This is distinct from research QA.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import sys


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ordinary(root, relative):
    root = Path(root).resolve()
    path = root / relative
    need(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
         "relative in-stage locator required")
    need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),
         "ordinary retained source required: " + relative)
    return path


def cells(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


class SavedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.links = []
        self.text = []
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.capture = True
            self.parts = []
        if tag == "a":
            self.links.append(dict(attrs).get("href"))

    def handle_data(self, data):
        self.text.append(data)
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "td":
            self.rows.append("".join(self.parts))
            self.capture = False


def markdown_cells(text):
    output = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        fields = re.split(r"(?<!\\)\|", line)[1:-1]
        values = [x.strip().replace(r"\|", "|") for x in fields]
        if values and all(x == "---" for x in values):
            continue
        # Source headers are the first pipe row after an empty line or h2.
        # They are recognized by the declared column vocabulary rather than
        # discarded by shape or numerical content.
        if values and values[0] in {"policy", "horizon"}:
            continue
        output.extend(values)
    return output


def expected_bindings(tables):
    specs = []
    combined = dict(year="all", session="all", side="combined")
    paired_cols = ["policy", "episodes", "complete_pairs", "missing_pairs", "fills", "completed", "mean_difference", "difference_low", "difference_high", "adjusted_low", "adjusted_high"]
    specs.append(("paired", dict(combined, family="primary"), paired_cols))
    specs.append(("trade-cohorts", combined, ["policy", "executable_fills", "completed", "censored", "wins", "losses", "breakevens", "net_dollars", "mean_net_dollars", "profit_factor", "max_drawdown_dollars"]))
    for side in ("upper-first", "lower-first"):
        specs.append(("occurrence", dict(year="all", session="all", side=side), ["horizon", "event", "episodes", "known_events", "known_denominator", "unknown", "rate", "lower_bound", "upper_bound", "mean_exposure_minutes", "mean_elapsed_minutes"]))
        specs.append(("paired", dict(year="all", session="all", side=side, family="protected"), paired_cols))
        if "time-recovery" in tables:
            specs.append(("time-recovery", dict(year="all", session="all", side=side), ["horizon", "level", "event", "known_breach_episodes", "known_recoveries", "unknown_recovery", "unknown_recovery_time", "mean_delay_minutes_source_estimate", "mean_delay_minutes_lower", "mean_delay_minutes_upper", "delay_minutes_source_estimate_denominator"]))
    specs.append(("account", combined, ["policy", "mode", "episodes", "signals", "eligible_loss", "original_fills", "second_fills", "quantity_skips", "completed_pairs", "full_recovery", "unknown", "net_dollars"]))
    expected = []
    for name, where, columns in specs:
        chosen = [(i, row) for i, row in enumerate(tables[name]) if all(row[k] == v for k, v in where.items())]
        need(bool(chosen), "required synthesis cohort missing")
        for index, row in chosen:
            for column in columns:
                value = row[column]
                expected.append(dict(table=name, source_row=index, source_column=column,
                                     value=value, rendered=value if value else "Unavailable"))
    return expected


def verify(stage):
    map_path = ordinary(stage, "report-source-map.json")
    mapping = json.loads(map_path.read_text())
    need(mapping["status"] == "prepared", "saved synthesis preparation status")
    tables = {}
    paths = ["report-source-map.json"]
    for name, pin in mapping["tables"].items():
        source = ordinary(stage, pin["path"])
        need(digest(source) == pin["sha256"], "synthesis source bytes drift")
        tables[name] = cells(source)
        paths.append(pin["path"])
    expected = expected_bindings(tables)
    need(mapping["bindings"] == expected, "synthesis exact source-cell roster/order/value")
    outputs = {}
    for name, hash_value in mapping["outputs"].items():
        source = ordinary(stage, name)
        need(digest(source) == hash_value, "synthesis output bytes drift")
        outputs[name] = source.read_text()
        paths.append(name)
    need(set(outputs) == {"report.md", "report.html", "advice.md"}, "exact synthesis outputs")
    rendered = [record["rendered"] for record in expected]
    need(markdown_cells(outputs["report.md"]) == rendered, "Markdown saved table cells")
    parser = SavedHTML()
    parser.feed(outputs["report.html"])
    need(parser.rows == rendered, "HTML saved table cells")
    decisions = {}
    for kind in ("selection", "assessment"):
        pin = mapping[kind]
        path = ordinary(stage, pin["path"])
        need(digest(path) == pin["sha256"], "synthesis decision source drift")
        decisions[kind] = json.loads(path.read_text())
        paths.append(pin["path"])
    chosen = decisions["selection"]["selected_policy"]
    shown = "Unavailable" if chosen is None else chosen
    validation = decisions["selection"]["decision"]
    later = decisions["assessment"]["decision"]
    for name in ("report.md", "advice.md"):
        text = outputs[name]
        need("Saved validation decision: `" + validation + "`" in text, "saved validation prose")
        need("selected " + ("policy" if name == "report.md" else "rule") + ": `" + shown + "`" in text,
             "saved chosen-policy prose")
        need(("Saved later assessment: `" if name == "report.md" else "Later assessment: `") + later + "`" in text,
             "saved later decision prose")
    html_text = "".join(parser.text)
    need("Validation: " + validation + ". Selected: " + shown + ". Later: " + later + "." in html_text,
         "HTML decision prose")
    need(len(mapping["publications"]) == 23 and len({p["id"] for p in mapping["publications"]}) == 23,
         "exact23 synthesis publication roster")
    for record in mapping["publications"]:
        path = ordinary(stage, record["source"])
        need(digest(path) == record["sha256"], "synthesis publication bytes drift")
        report = json.loads(path.read_text())
        need(report["id"] == record["id"] and report["title"] == record["title"]
             and report["source"]["runId"] == stage.name, "synthesis publication identity")
        need("- [" + record["title"] + "](" + record["source"] + ")" in outputs["report.md"],
             "Markdown publication locator")
        need(record["source"] in parser.links and record["title"] in html_text, "HTML publication locator/title")
        paths.append(record["source"])
    qualifications = ["not pristine holdouts", "Phase3", "remain uncomputed", "whole contracts", "Known no-fill is zero", "unknown execution remains unavailable", "Actual-entry trade performance has a different cohort anchor", "tick ordering and native TradingView replay remain unverified", "Assumed costs are not the user's broker charges"]
    if "time-recovery" in tables:
        qualifications.extend(["from the first known protected one-tick breach", "after policy execution", "It changes no order, P&L, comparison mask or selection", "not survival probabilities", "may reflect binary price noise", "Canonical ledgers retain censored-only observed holding time"])
    for phrase in qualifications:
        need(all(phrase in text for text in (outputs["report.md"], outputs["advice.md"], html_text)), "required synthesis qualification: " + phrase)
    return dict(status="passed", cells=len(expected), publications=23,
                validation_decision=validation, selected_policy=chosen, later_assessment=later,
                artifacts=[dict(path=path, bytes=ordinary(stage,path).stat().st_size, sha256=digest(ordinary(stage,path))) for path in sorted(set(paths))],
                limits=["This checks exact saved source transfer and disclosed decisions; statistical validity uses the independent scientific receipt."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    root = Path(__file__).resolve().parents[2]
    need(stage.is_relative_to(root / "work/23_gc_overnight_breakout_15m"), "owning work stage only")
    need(args.attempt.replace("-", "").isalnum(), "new plain attempt identity")
    folder = stage / "verification" / ("synthesis-independent-" + args.attempt)
    folder.mkdir(parents=True, exist_ok=False)
    snapshots = []
    for source in (Path(__file__), Path(__file__).parent / "tests/test_phase2_synthesis_verifier.py"):
        target = folder / source.name
        shutil.copyfile(source, target)
        snapshots.append(dict(path=str(target.relative_to(stage)), bytes=target.stat().st_size, sha256=digest(target)))
    receipt = dict(schema_version="study23.phase2-independent-synthesis/v1", attempt=args.attempt,
                   command=sys.argv, started_at=datetime.now(timezone.utc).isoformat(), source_snapshots=snapshots)
    try:
        receipt.update(verify(stage))
    except Exception as error:
        receipt.update(status="failed", error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        with (folder / "receipt.json").open("x") as handle:
            json.dump(receipt, handle, indent=2, allow_nan=False);handle.write("\n")
    print(json.dumps(receipt, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
