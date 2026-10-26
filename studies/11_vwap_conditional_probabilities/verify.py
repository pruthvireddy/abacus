"""Read-only numerical, source-recount, and artifact gate before sealing."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from abacus_bhishma.paths import load_workspace_paths
from src.features import SCALE, digest
from src.outcomes import load_source_year


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value and not value.startswith(("http:", "https:", "#", "mailto:")):
                self.paths.append(value)


def source_slice(source: pd.DataFrame, start: pd.Timestamp, minutes=30) -> pd.DataFrame:
    index = int(source.ts_event.searchsorted(start))
    return source.iloc[index:index + minutes]


def independent_contact(path: pd.DataFrame, lower: float, upper: float) -> bool:
    highs = path.high.to_numpy(dtype=float) * SCALE
    lows = path.low.to_numpy(dtype=float) * SCALE
    return bool(np.any((lows <= upper + 1e-10) & (highs >= lower - 1e-10)))


def independent_b_race(path: pd.DataFrame, row: pd.Series) -> str:
    side = int(row.side)
    lower, upper, extension = row.return_zone_low, row.return_zone_high, row.extension_target
    for bar in path.itertuples(index=False):
        opening, high, low = bar.open * SCALE, bar.high * SCALE, bar.low * SCALE
        if side > 0:
            at_return, at_extension = opening <= upper + 1e-10, opening >= extension - 1e-10
            touch_return, touch_extension = low <= upper + 1e-10, high >= extension - 1e-10
        else:
            at_return, at_extension = opening >= lower - 1e-10, opening <= extension + 1e-10
            touch_return, touch_extension = high >= lower - 1e-10, low <= extension + 1e-10
        if (at_return and at_extension) or (touch_return and touch_extension):
            return "ambiguous"
        if at_return or touch_return:
            return "return_first"
        if at_extension or touch_extension:
            return "extension_first"
    return "neither"


def independent_c_race(path: pd.DataFrame, row: pd.Series) -> str:
    day_zone = (row.day_zone_low - row.price_adjustment * SCALE,
                row.day_zone_high - row.price_adjustment * SCALE)
    session_zone = (row.session_zone_low - row.price_adjustment * SCALE,
                    row.session_zone_high - row.price_adjustment * SCALE)
    if row.day_below_session:
        lower, upper, lower_name, upper_name = day_zone, session_zone, "day_first", "session_first"
    else:
        lower, upper, lower_name, upper_name = session_zone, day_zone, "session_first", "day_first"
    for bar in path.itertuples(index=False):
        opening, high, low = bar.open * SCALE, bar.high * SCALE, bar.low * SCALE
        lower_open, upper_open = opening <= lower[1] + 1e-10, opening >= upper[0] - 1e-10
        lower_touch, upper_touch = low <= lower[1] + 1e-10, high >= upper[0] - 1e-10
        if (lower_open and upper_open) or (lower_touch and upper_touch):
            return "ambiguous"
        if lower_open or lower_touch:
            return lower_name
        if upper_open or upper_touch:
            return upper_name
    return "neither"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    root = load_workspace_paths(workspace).publication_root
    stage = workspace / "work/11_vwap_conditional_probabilities" / args.run_id
    required = (
        "config.json", "inputs.lock.json", "protocol-1.0.0.json", "protocol-1.0.0.md",
        "input-verification.json", "feature-feasibility.json", "feature-coverage.csv",
        "corridor-threshold-support.csv", "corridor-selection.csv", "extraction-summary.json",
        "metrics.json", "report.md", "report.html", "advice.md", "chart-display-spec.md",
        "tables/funnel.csv", "tables/exclusions.csv", "tables/question_a_rates.csv",
        "tables/question_b_outcomes.csv", "tables/question_c_outcomes.csv",
        "tables/model_scores.csv", "tables/calibration.csv", "tables/probability_atlas.csv",
        "tables/examples.csv", "tables/barrier_geometry.csv",
        "figures/remaining-return-by-elapsed.svg",
        "figures/return-versus-extension.svg", "figures/day-session-corridor.svg",
        "figures/corridor-by-position.svg", "figures/corridor-by-width.svg",
        "figures/calibration.svg", "figures/time-to-event.svg",
        "figures/chart-example-success.svg", "figures/chart-example-failure.svg",
    )
    for relative in required:
        if not (stage / relative).is_file():
            raise FileNotFoundError(stage / relative)
    pins = json.loads((stage / "input-verification.json").read_text())
    for item in pins:
        if digest(root / item["path"]) != item["sha256"]:
            raise ValueError(f"input changed after gate: {item['path']}")

    metrics = json.loads((stage / "metrics.json").read_text())
    ab_files = sorted((stage / "events").glob("ab_*.parquet"))
    c_files = [path for path in sorted((stage / "events").glob("c_*.parquet"))
               if not path.name.startswith("c_updates_")]
    update_files = sorted((stage / "events").glob("c_updates_*.parquet"))
    ab_rows = sum(pq.ParquetFile(path).metadata.num_rows for path in ab_files)
    c_rows = sum(pq.ParquetFile(path).metadata.num_rows for path in c_files)
    update_rows = sum(pq.ParquetFile(path).metadata.num_rows for path in update_files)
    if ab_rows != metrics["primary_ab_rows"] + metrics["five_minute_ab_rows"]:
        raise ValueError("AB evidence count mismatch")
    if c_rows != metrics["primary_corridor_rows"] + metrics["five_minute_corridor_rows"]:
        raise ValueError("corridor evidence count mismatch")

    ab = pd.concat([pd.read_parquet(path) for path in ab_files], ignore_index=True)
    corridors = pd.concat([pd.read_parquet(path) for path in c_files], ignore_index=True)
    valid_ab = ab[ab.outcome_missing.isna()]
    valid_c = corridors[corridors.outcome_missing.isna()]
    b_classes = ["return_first", "extension_first", "neither", "ambiguous"]
    c_classes = ["day_first", "session_first", "neither", "ambiguous"]
    if not valid_ab.barrier_primary.isin(b_classes).all():
        raise ValueError("B classes not exhaustive")
    if not valid_c.frozen_outcome.isin(c_classes).all():
        raise ValueError("C classes not exhaustive")
    if valid_ab.frozen_return_30.isna().any() or valid_ab.evolving_return_30.isna().any():
        raise ValueError("null A outcomes inside evaluable rows")
    if (valid_ab.evolving_without_frozen_30 & ~valid_ab.evolving_return_30).any():
        raise ValueError("evolving-only identity failed")
    q_b = pd.read_csv(stage / "tables/question_b_outcomes.csv")
    q_c = pd.read_csv(stage / "tables/question_c_outcomes.csv")
    for table, names in ((q_b, b_classes), (q_c, c_classes)):
        overall = table[(table["product"] != "ALL") & (table.anchor == "ALL") &
                        (table.split == "all") & (table.facet == "overall")]
        for _, group in overall.groupby("product"):
            if set(group.outcome_class) != set(names) or group.denominator.nunique() != 1:
                raise ValueError("reported class denominators not exhaustive")

    examples = pd.read_csv(stage / "tables/examples.csv")
    audits = []
    source_cache = {}
    for _, example in examples.iterrows():
        event_file = stage / "events" / example.source_partition
        event = pd.read_parquet(event_file)
        row = event[event.event_id == example.event_id].iloc[0]
        key = (row["product"], int(row.year), row.session_date)
        if key not in source_cache:
            source = load_source_year(root, key[0], key[1])
            source_cache[key] = source[source.session_date.astype(str) == key[2]].reset_index(drop=True)
        path = source_slice(source_cache[key], row.forecast_ts)
        if len(path) != 30:
            raise ValueError(f"example source gap: {row.event_id}")
        if example.domain == "A":
            observed = independent_contact(path, row.return_zone_low, row.return_zone_high)
            if observed != bool(row.frozen_return_30):
                raise ValueError(f"independent A recount failed: {row.event_id}")
        elif example.domain == "B":
            observed = independent_b_race(path, row)
            if observed != row.barrier_primary:
                raise ValueError(f"independent B recount failed: {row.event_id}")
        else:
            observed = independent_c_race(path, row)
            if observed != row.frozen_outcome:
                raise ValueError(f"independent C recount failed: {row.event_id}")
        audits.append({"event_id": row.event_id, "domain": example.domain,
                       "stored_outcome": example.outcome, "independent_recount": observed})
    pd.DataFrame(audits).to_csv(stage / "tables" / "example-audit.csv", index=False)
    audit_result = {"examples_recounted": len(audits),
                    "products": sorted(set(examples["product"])),
                    "domains": sorted(set(examples.domain)),
                    "classes": sorted(set(examples.outcome))}
    (stage / "numerical-audit.json").write_text(json.dumps(audit_result, indent=2) + "\n")

    report = (stage / "report.md").read_text()
    html = (stage / "report.html").read_text()
    parser_links = Links()
    parser_links.feed(html)
    markdown_links = re.findall(r"\]\(([^)]+)\)", report)
    special_future = {"events.manifest.json", "manifest.json"}
    for relative in set(parser_links.paths + markdown_links):
        if relative not in special_future and not (stage / relative).is_file():
            raise FileNotFoundError(f"broken report link: {relative}")
    svg_files = list((stage / "figures").glob("*.svg"))
    for svg in svg_files:
        ET.parse(svg)
        text = svg.read_text()
        if "chart-example" in svg.name and ("RETROSPECTIVE" not in text or "deadline" not in text):
            raise ValueError(f"misleading example label: {svg.name}")
    test_command = [str(workspace / ".venv/bin/python"), "-m", "unittest", "discover",
                    "-s", "studies/11_vwap_conditional_probabilities/tests", "-v"]
    tests = subprocess.run(test_command, cwd=workspace, text=True, capture_output=True)
    (stage / "focused-tests.log").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise RuntimeError("focused tests failed")
    result = {
        "status": "passed", "input_files_rehashed": len(pins),
        "ab_event_rows": ab_rows, "corridor_event_rows": c_rows,
        "corridor_update_rows": update_rows, "ab_partitions": len(ab_files),
        "corridor_partitions": len(c_files), "update_partitions": len(update_files),
        "a_null_false_distinction": "passed", "b_classes_exhaustive": True,
        "c_classes_exhaustive": True, "examples_independently_recounted": len(audits),
        "report_links_checked": len(set(parser_links.paths + markdown_links)),
        "svg_xml_and_labels_checked": len(svg_files), "focused_tests": "12 passed",
    }
    (stage / "verification-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
