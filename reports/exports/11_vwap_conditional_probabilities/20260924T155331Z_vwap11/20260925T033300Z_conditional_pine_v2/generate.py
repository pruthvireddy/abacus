"""Presentation-only Pine export from the immutable study-11 tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
RUN = ROOT / "runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11"
TABLES = RUN / "tables"
SOURCE_NAME = "source-indicator.pine"
OUTPUT_NAME = "session_vwap_conditional_stats.pine"
EXPECTED_SOURCE_SHA256 = "5f42139c73c5084ceb951bab3b11f236a52921bef7be3bf5448863b083a0166e"
CLASS_ORDER = {
    "B": ["return_first", "extension_first", "neither", "ambiguous"],
    "C": ["day_first", "session_first", "neither", "ambiguous"],
}
DISTANCE = ["<0.75σ", "0.75–1.25σ", "1.25–2σ", "2σ+"]
ELAPSED = ["<20m", "20–39m", "40–59m", "60–119m", "120–239m", "240m+"]
GEOMETRY = ["<0.25", "0.25–0.4", "0.4–0.6", "0.6–0.75", "0.75+"]
POSITION = ["day quarter", "day middle", "session middle", "session quarter"]
GEOMETRY_SOURCE = ["<0.25", "0.25-0.4", "0.4-0.6", "0.6-0.75", "0.75+"]
POSITION_SOURCE = ["day_quarter", "day_middle", "session_middle", "session_quarter"]
PRODUCTS = ["ES", "NQ", "GC"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def pct(value: str | float) -> str:
    return f"{100 * float(value):.1f}%"


def ci(row: dict[str, str]) -> str:
    return f"{pct(row['ci_low'])}–{pct(row['ci_high'])}"


def support(row: dict[str, str]) -> str:
    return f"n={int(row['denominator']):,}"


def provenance(row: dict[str, str]) -> str:
    return (
        f"{int(row['denominator']):,} rows; {int(row['episodes']):,} episodes/events; "
        f"{int(row['product_sessions']):,} product-days; {int(row['shared_weeks']):,} shared weeks. "
        "Complete-day eligibility was retrospective."
    )


def payload(display: str, row: dict[str, str], tooltip: str) -> str:
    if int(row["denominator"]) < 100:
        display = "SPARSE"
        tooltip = (
            "Suppressed: fewer than 100 historical observations in this product-specific "
            "conditional cell. No rate is displayed. " + provenance(row)
        )
    return "¦".join((display, support(row), tooltip))


def a_lookup() -> dict[str, str]:
    all_rows = rows("question_a_rates.csv")
    overall = {
        (row["product"], row["metric"]): row
        for row in all_rows
        if row["product"] in PRODUCTS and row["anchor"] == "ALL"
        and row["split"] == "all" and row["facet"] == "overall"
    }
    selected = [
        row for row in all_rows
        if row["product"] in PRODUCTS
        and row["anchor"] == "ALL"
        and row["split"] == "all"
        and row["facet"] == "distance_x_elapsed"
        and row["metric"] == "frozen_return_30"
    ]
    result = {}
    for row in selected:
        distance, elapsed = row["facet_value"].split("|")
        d = ["<0.75", "0.75-1.25", "1.25-2", "2+"].index(distance)
        e = ["<20", "20-39", "40-59", "60-119", "120-239", "240+"].index(elapsed)
        key = f"A|{row['product']}|{d}|{e}"
        tip = (
            f"A · {row['product']} 2m; Globex/Asia/London/NY anchors pooled. "
            f"At-risk fresh departure checkpoints: current distance {DISTANCE[d]}, "
            f"elapsed without causal evolving-VWAP return {ELAPSED[e]}. "
            f"Future event: frozen checkpoint VWAP ±1 tick contacted within 30 elapsed minutes. "
            f"{int(row['numerator']):,}/{int(row['denominator']):,} = {pct(row['probability'])}; "
            f"95% shared-week interval {ci(row)}. {provenance(row)} "
            f"Product-wide secondary references (not this cell): evolving-only 30m "
            f"{pct(overall[(row['product'], 'evolving_without_frozen_30')]['probability'])}; "
            f"frozen contact by variable window end "
            f"{pct(overall[(row['product'], 'frozen_return_window')]['probability'])}. "
            "Clock, anchor, and prior volatility are not jointly conditioned in this displayed raw cell. "
            "New path context improved evaluation Brier by only 0.5%; no pristine holdout. "
            "Chart feed/eligibility can differ from the pinned Databento release. Not a trade win rate."
        )
        result[key] = payload(pct(row["probability"]), row, tip)
    assert len(result) == 72, len(result)
    return result


def race_lookup(name: str, kind: str, facet: str) -> dict[str, str]:
    groups: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    values = GEOMETRY_SOURCE if kind == "B" else POSITION_SOURCE
    for row in rows(name):
        if (row["product"] in PRODUCTS and row["anchor"] == "ALL" and row["split"] == "all"
                and row["facet"] == facet and row["facet_value"] in values):
            groups[(row["product"], row["facet_value"])][row["outcome_class"]] = row
    result = {}
    for (product, value), outcomes in groups.items():
        classes = CLASS_ORDER[kind]
        assert set(outcomes) == set(classes), (product, value, outcomes)
        index = values.index(value)
        key = f"{kind}|{product}|{index}"
        first = outcomes[classes[0]]
        denominator = int(first["denominator"])
        assert sum(int(outcomes[c]["numerator"]) for c in classes) == denominator
        lead = "R" if kind == "B" else "D"
        second = "X" if kind == "B" else "S"
        display = (
            f"{lead} {pct(outcomes[classes[0]]['probability'])} · {second} {pct(outcomes[classes[1]]['probability'])}\\n"
            f"N {pct(outcomes['neither']['probability'])} · ? {pct(outcomes['ambiguous']['probability'])}"
        )
        if kind == "B":
            condition = (
                f"Geometry share {GEOMETRY[index]} = distance to return-zone edge / "
                "(return-zone distance + extension distance). Anchors pooled. "
                "Return target is frozen checkpoint VWAP ±1 tick; extension is 0.5σ "
                "outward from checkpoint close, rounded to whole ticks. Unequal distances: 50% is not neutral."
            )
        else:
            condition = (
                f"Starting position: {POSITION[index]}, measured from frozen day VWAP across "
                "the frozen day/session corridor. Asia/London/NY sessions pooled. "
                "Cross must be completed, both anchors mature, corridor ≥8 ticks and ≥0.25 day σ. "
                "Nearer-boundary frequency is geometry, not evidence of VWAP attraction."
            )
        class_detail = " ".join(
            f"{label} {int(outcomes[cls]['numerator']):,}/{denominator:,} "
            f"({pct(outcomes[cls]['probability'])}, CI {ci(outcomes[cls])});"
            for label, cls in zip((lead, second, "N", "?"), classes)
        )
        tip = (
            f"{kind} · {product} 2m. {condition} 30-minute frozen-target race, "
            f"including neither and same-minute ambiguity. {class_detail} "
            f"{provenance(first)} Raw cohort; clock/volatility are not jointly conditioned in the displayed cell. "
            f"{'Added path context improved evaluation Brier by only 1.0%.' if kind == 'B' else 'No added C path-context cell reached the 100-row development floor.'} "
            "All periods exploratory; chart feed may differ. Not a trade win rate."
        )
        result[key] = payload(display, first, tip)
    expected = 15 if kind == "B" else 12
    assert len(result) == expected, len(result)
    return result


def update_lookup() -> dict[str, str]:
    groups: dict[tuple[str, int, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows("updated_corridor.csv"):
        if row["product"] in PRODUCTS and row["anchor"] == "ALL" and row["facet"] == "position_bin":
            groups[(row["product"], int(row["elapsed_minutes"]), row["facet_value"])][row["outcome_class"]] = row
    result = {}
    for (product, age, value), outcomes in groups.items():
        assert age in (10, 20)
        classes = CLASS_ORDER["C"]
        assert set(outcomes) == set(classes)
        index = POSITION_SOURCE.index(value)
        first = outcomes["day_first"]
        den = int(first["denominator"])
        assert sum(int(outcomes[c]["numerator"]) for c in classes) == den
        display = (
            f"D {pct(outcomes['day_first']['probability'])} · S {pct(outcomes['session_first']['probability'])}\\n"
            f"N {pct(outcomes['neither']['probability'])} · ? {pct(outcomes['ambiguous']['probability'])}"
        )
        detail = " ".join(
            f"{label} {int(outcomes[cls]['numerator']):,}/{den:,} "
            f"({pct(outcomes[cls]['probability'])}, CI {ci(outcomes[cls])});"
            for label, cls in zip(("D", "S", "N", "?"), classes)
        )
        tip = (
            f"C updated conditional · {product} 2m, {age}m after event, only original frozen races "
            f"still unresolved. Current position {POSITION[index]} relative to original frozen targets; "
            f"deadline remains the original event time +30m. Sessions pooled. {detail} "
            f"{provenance(first)} Raw cohort, not a new event and not a trading win rate. "
            "All periods exploratory; chart feed may differ."
        )
        result[f"U{age}|{product}|{index}"] = payload(display, first, tip)
    assert len(result) == 24, len(result)
    return result


def pine_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, help="Original pasted Pine source; omit after source snapshot is saved")
    args = parser.parse_args()
    source = args.source if args.source else HERE / SOURCE_NAME
    if sha256(source) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("Original indicator source hash does not match the user attachment")
    original = source.read_text()
    if not original.startswith("// This Pine Script® code") or original.count("indicator(") != 1:
        raise SystemExit("Unexpected source-indicator structure")
    if args.source:
        (HERE / SOURCE_NAME).write_bytes(source.read_bytes())
    data = {}
    data.update(a_lookup())
    data.update(race_lookup("question_b_outcomes.csv", "B", "geometry_bin"))
    data.update(race_lookup("question_c_outcomes.csv", "C", "position_bin"))
    data.update(update_lookup())
    # Pine rejects a single very large switch (CE10205). Each function below
    # has at most six cases, and the dispatcher uses separate one-line ifs.
    cases = sorted(data.items())
    chunks = [cases[index:index + 6] for index in range(0, len(cases), 6)]
    lookup = ""
    for number, chunk in enumerate(chunks):
        lookup += f"f_study_lookup_{number:02d}(string key) =>\n    switch key\n"
        lookup += "".join(
            f"        {pine_quote(key)} => {pine_quote(value)}\n"
            for key, value in chunk
        )
        lookup += '        => ""\n\n'
    lookup += 'f_study_lookup(string key) =>\n    string result = f_study_lookup_00(key)\n'
    for number in range(1, len(chunks)):
        lookup += f'    if result == ""\n        result := f_study_lookup_{number:02d}(key)\n'
    lookup += '    result\n'
    module = (HERE / "conditional_stats.pinepart").read_text().replace("// @STUDY_LOOKUP@", lookup)
    if "@STUDY_LOOKUP@" in module:
        raise SystemExit("Lookup marker was not replaced")
    updated = original.replace(
        'indicator("Session VWAP OE Scalp - Delta + TICK Bubbles", shorttitle="OE Scalp - Delta + TICK", overlay=true, max_labels_count=500)',
        'indicator("Session VWAP OE + VWAP Conditional Map", shorttitle="OE + VWAP Map", overlay=true, max_labels_count=500)',
    )
    if updated == original:
        raise SystemExit("Indicator header did not match expected input")
    output = HERE / OUTPUT_NAME
    output.write_text(updated.rstrip() + "\n" + module)
    artifacts = [SOURCE_NAME, "conditional_stats.pinepart", "generate.py", OUTPUT_NAME, "README.md", "verification.md"]
    sources = [
        "runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/question_a_rates.csv",
        "runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/question_b_outcomes.csv",
        "runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/question_c_outcomes.csv",
        "runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/tables/updated_corridor.csv",
        "runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/chart-display-spec.md",
        "studies/11_vwap_conditional_probabilities/protocol-1.0.0.json",
    ]
    manifest = {
        "schema_version": 1,
        "study_id": "11_vwap_conditional_probabilities",
        "source_run_id": "20260924T155331Z_vwap11",
        "presentation_revision_id": HERE.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "format_version": "pine-v6-v1",
        "renderer": "generate.py",
        "render_command": f"python3 {HERE.relative_to(ROOT)}/generate.py",
        "original_source_sha256": EXPECTED_SOURCE_SHA256,
        "lookup_cells": len(data),
        "changes": "Compiler-size revision of v1: 123 saved-evidence lookup cells split into six-case switches; all probabilities and indicator behavior unchanged.",
        "limitations": "Presentation-only export. Chart feed, session eligibility, and intrabar history are not independently audited against the research inputs; Pine compilation awaits a private TradingView editor check.",
        "checks": ["focused study/export tests", "agent documentation check", "research index check", "Pine CE10205 addressed by bounded switch chunks; compile pending"],
        "source_artifacts": {path: sha256(ROOT / path) for path in sources},
        "output_artifacts": {name: sha256(HERE / name) for name in artifacts},
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Rendered {output} with {len(data)} saved-evidence lookup cells")


if __name__ == "__main__":
    main()
