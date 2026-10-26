"""Project immutable saved Phase 2 cells into additive presentation revisions.

No research producer is imported, executed, or modified. Short report keys are
presentation aliases; every cell binds to its exact full saved CSV column.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import sys

import saved_projection_helper as saved

STUDY = "23_gc_overnight_breakout_15m"
RUN = "20261013T190208Z_phase2_gc_ob15m_v2"
MANIFEST_SHA = "ffe43f2403520d9ba058720908ad711b88e665b0d8d3928bdaa5342ad7cb3c4a"
STAMP = "20261013T204013Z"
CREATED = "2026-10-13T20:40:13Z"
SOURCE_LOCATOR = f"runs/{STUDY}/{RUN}"
TRANSITIONS = "tables/transitions.csv"
TIMING = "additional/time-recovery/time-recovery.csv"
POLICIES = tuple(saved.POLICIES.values())
PROTECTED = POLICIES[-3:]


@dataclass(frozen=True)
class Spec:
    publication_id: str
    revision_id: str
    title: str


SPECS = (
    Spec("gc-overnight-breakout-15m-phase2-session-transitions-20261013-r1",
         STAMP + "_comparison_sessions_r1", "Phase 2 — Session transitions"),
    Spec("gc-overnight-breakout-15m-phase2-protected-entry-20261013-r1",
         STAMP + "_protected_entry_r1", "Protected boundary — Entry sessions & transitions"),
)


def json_bytes(value, compact=False):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":") if compact else None,
                       indent=None if compact else 2) + "\n").encode()


def table(draft, section, title, artifact, keys, filters, labels=None, description=""):
    """Bind exact saved cells; compact keys have no analytical meaning."""
    labels = labels or {}
    aliases = {key: "c" + str(index) for index, key in enumerate(keys)}
    if len(keys) > 12 or len(set(keys)) != len(keys):
        raise ValueError("At most twelve distinct displayed saved columns")
    raw = draft.copied_table(artifact)
    source = draft.sources[artifact]
    if not 1 <= len(raw) <= 1500 or any(key not in source["columns"] for key in keys):
        raise ValueError("Explicit saved table selection exceeds bounds")
    if len(filters) != 3 or any(key not in keys for key, _, _ in filters):
        raise ValueError("Exactly three displayed saved-row selectors required")
    columns = saved.columns(keys)
    for column in columns:
        original = column["key"]
        column["key"] = aliases[original]
        column["label"] = labels.get(original, column["label"])
    rows = []
    for row_index, row in enumerate(raw):
        displayed = {}
        for key in keys:
            value = saved.saved_cell(key, row[key])
            alias = aliases[key]
            displayed[alias] = value
            draft.bindings.append({
                "section": section, "row_index": row_index, "key": alias,
                "source_artifact": artifact, "source_row": row_index,
                "source_column": key, "value_type": saved.value_type(value),
                "original_stage_source_path": source["original_stage_source_path"],
                "original_source_row": source["selected_source_rows"][row_index],
                "original_source_column": key,
            })
        rows.append(displayed)
    row_filters = []
    for key, label, default in filters:
        selector = {"key": aliases[key], "label": label}
        if default is not None:
            if not any(row[aliases[key]] == default for row in rows):
                raise ValueError("Selector default must match a saved value")
            selector["defaultValue"] = default
        row_filters.append(selector)
    return {"id": section, "kind": "table", "title": title,
            "description": description, "columns": columns,
            "rows": rows, "rowFilters": row_filters}


def transition_table(draft, kind, section, title, origin):
    artifact = draft.copy_table(TRANSITIONS, "tables/" + section + ".csv", {"transition": kind})
    keys = ["year", "side", "from_session", "to_session", "count", "unknown"]
    filters = [("year", "Original breakout year", "all"),
               ("side", "Original first side", "combined"),
               ("from_session", origin + " session", "Asia")]
    destination = "Price-reclaim event session" if kind == "breach_to_price_reclaim" else "Actual candidate-fill session"
    return table(draft, section, title, artifact, keys, filters,
                 {"year": "Original breakout year", "side": "Original first side",
                  "from_session": origin + " session", "to_session": destination,
                  "count": "Saved confirmed pairs", "unknown": "Saved unknown count"},
                 "Saved transition: " + kind + ". Unknown is an explicit category; destination rows are not pooled or inferred. The saved unknown count accompanies the destination roster and must not be summed across destination rows.")


def original_transition_copy(draft):
    columns, rows = draft.inputs.table(TRANSITIONS)
    raw = draft.inputs.read(TRANSITIONS)
    target = "transitions-full.csv"
    draft.files[target] = raw
    draft.sources[target] = {
        "path": target, "kind": "csv", "sha256": saved.sha_bytes(raw),
        "original_stage_source_path": TRANSITIONS,
        "original_source_sha256": saved.sha_bytes(raw), "source_row_base": 0,
        "selected_source_rows": list(range(len(rows))), "columns": columns,
        "selectors": {}, "byte_identical_original": True,
    }


def assemble(inputs, spec):
    draft = saved.PublicationDraft(inputs, RUN, spec)
    draft.copy_json("config.json")
    draft.copy_json("selection.json")
    draft.copy_text("protocol.md")
    original_transition_copy(draft)
    sections = []
    def text(section, title, body, sources=None):
        sections.append(saved.text_section(draft, section, title, body, sources=sources))
    text("presentation-scope", "Saved evidence and cohort anchors",
         "This additive presentation revision exposes existing verified Phase 2 tables. It preserves the frozen policies, selection and research values. Original-breakout cohorts use the first breakout's New York year and original direction. Actual-entry performance uses each candidate fill's New York year, session and direction. A no-fill episode has no invented candidate-entry session. Unknown observations remain distinct from confirmed absence. The original Phase 1 baseline and the earlier Phase 2 report routes remain available.")
    text("transition-method", "Chronological transition pairs",
         "Breakout-to-candidate rows show original-breakout session to actual candidate-fill session. Breach-to-candidate pairs require a chronologically confirmed protected-boundary breach: its latest possible first-breach time is no later than the candidate entry. Breach-to-price-reclaim is a price event transition, distinct from an executed recovery or reversal trade. The saved count and unknown columns are reproduced directly. A zero count is not evidence of financial recovery; unknown is not zero.")
    if spec == SPECS[0]:
        for index, policy in enumerate(POLICIES):
            sections.append(transition_table(draft, "breakout_to_candidate_entry:" + policy,
                "breakout-fill-" + str(index), policy + " — Original breakout to actual candidate fill", "Original breakout"))
        original_kinds = tuple("breakout_to_candidate_entry:" + p for p in POLICIES)
        other_kinds = ("breakout_to_breach", "breach_to_price_reclaim") + tuple("breach_to_candidate_entry:" + p for p in POLICIES)
        for id, kinds, label in [("breakout-candidate-transitions", original_kinds, "Original breakout to candidate-fill transitions"),
                                 ("boundary-transitions", other_kinds, "Protected-breach and price-reclaim transitions")]:
            artifact = draft.copy_table(TRANSITIONS, "tables/" + id + ".csv", {"transition": kinds})
            draft.download(id, label, artifact, draft.sources[artifact]["columns"],
                population="Original-breakout cohorts with explicit original-side and source/destination session rosters.",
                units="Saved counts and New York session labels.",
                scope="Ordered disjoint saved-row projection. Together the selected transition CSVs cover the complete original table, with every original column and no recalculated cells.")
        text("complete-download-roster", "Complete transition download roster",
             "The two downloads partition the original transition table in original row order. They include every breakout-to-candidate policy, every breach-to-candidate policy, breakout-to-breach and breach-to-price-reclaim. All original columns are retained, including transition code and anchor. The private revision retains and pins a byte-identical copy of the full original CSV. Neither the downloads nor browser controls calculate combined statistics.")
    else:
        actual_filters = [("year", "Actual candidate-entry year", "all"),
                          ("session", "Actual candidate-entry session", "all"),
                          ("side", "Actual candidate-entry side", "combined")]
        candidate = draft.copy_table("tables/trade-cohorts.csv", "tables/protected-candidate-performance.csv", {"policy": PROTECTED})
        for index, policy in enumerate(PROTECTED):
            artifact = draft.copy_table("tables/trade-cohorts.csv", "tables/candidate-" + str(index) + ".csv", {"policy": policy})
            sections.append(table(draft, "candidate-performance-" + str(index), policy + " — Actual-entry performance", artifact,
                ["year", "session", "side", "executable_fills", "completed", "censored", "net_dollars", "mean_net_dollars", "mean_dollars_low", "mean_dollars_high", "win_rate", "profit_factor"],
                actual_filters, {"year": "Actual-entry year", "session": "Actual-entry session", "side": "Actual candidate side"},
                "Standardized assumed-cost one-contract completed P&L. Censored fills are explicit and excluded from completed return statistics; empty rates and undefined profit factors remain unavailable. Actual-entry performance is not source-account execution or a financial-recovery rate."))
        for index, policy in enumerate(PROTECTED):
            for prefix, origin in [("breakout", "Original breakout"), ("breach", "Actual protected breach")]:
                sections.append(transition_table(draft, prefix + "_to_candidate_entry:" + policy,
                    prefix + "-candidate-" + str(index), policy + " — " + origin + " to actual candidate fill", origin))
        sections.append(transition_table(draft, "breach_to_price_reclaim", "breach-price-reclaim",
                       "Protected breach to price-reclaim event", "Actual protected breach"))
        protected_kinds = ("breach_to_price_reclaim",) + tuple(prefix + "_to_candidate_entry:" + p for p in PROTECTED for prefix in ("breakout", "breach"))
        transitions = draft.copy_table(TRANSITIONS, "tables/protected-transitions.csv", {"transition": protected_kinds})
        draft.copy_json("additional/time-recovery/measurement-freeze.json", "time-measurement-freeze.json")
        text("time-recovery-anchor", "Conditional timing from the first known protected breach",
             "The timing origin is the first known protected-boundary one-tick breach, not the original fill. Delay means are conditional on known recovered-event timing under the declared observation horizon. They are source-OHLC minute estimates with lower and upper timing bounds and separate saved denominators, not survival probabilities or exact tick times. Post-breach exposure means also retain separate bound denominators. Original-boundary, midpoint and opposite-boundary are relative to the original first direction: original-boundary is H for upper-first and L for lower-first. Touch and close-reclaim are separate price events. These are price-path diagnostics, not executed targets or financial recovery.",
             sources=[{"source_artifact": "time-measurement-freeze.json"}, {"source_artifact": "protocol.md"}])
        timing_keys, _ = inputs.table(TIMING)
        timing = draft.copy_table(TIMING, "tables/all-level-time-recovery.csv")
        ids = ["year", "session", "side", "horizon", "level", "event"]
        groups = (
            ("support", "Known and unknown recovery support", ["original_episodes", "known_breach_episodes", "unknown_breach_episodes", "known_recoveries", "known_no_recovery", "unknown_recovery"]),
            ("delay", "Mean recovery delay and timing denominators", ["mean_delay_minutes_source_estimate", "delay_minutes_source_estimate_denominator", "mean_delay_minutes_lower", "delay_minutes_lower_denominator", "mean_delay_minutes_upper", "delay_minutes_upper_denominator"]),
            ("exposure", "Unknown timing and mean post-breach exposure", ["unknown_recovery_time", "mean_post_breach_exposure_minutes_lower", "post_breach_exposure_minutes_lower_denominator", "mean_post_breach_exposure_minutes_upper", "post_breach_exposure_minutes_upper_denominator", "not_executed_target_or_financial_recovery"]),
        )
        original_filters = [("year", "Original breakout year", "all"), ("session", "Original breakout session", "all"), ("side", "Original first side", "combined")]
        for horizon in ("original_session", "remaining_broker_window"):
            artifact = draft.copy_table(TIMING, "tables/time-" + horizon + ".csv", {"horizon": horizon})
            for suffix, title, values in groups:
                sections.append(table(draft, "time-" + horizon.replace("_", "-") + "-" + suffix,
                    horizon.replace("_", " ").capitalize() + " — " + title, artifact, ids + values, original_filters,
                    {"year": "Original breakout year", "session": "Original breakout session", "side": "Original first side"},
                    "Every saved level and event is shown under this explicit horizon. Means, unknown counts and their individual denominators are exact saved cells. Match year/session/side across the support, delay and exposure tables to inspect the same original cohort."))
        draft.download("protected-entry-performance", "Protected actual candidate-entry performance", candidate,
            ["policy", "year", "session", "side", "executable_fills", "completed", "censored", "wins", "losses", "breakevens", "win_rate", "net_dollars", "gross_dollars", "net_points", "gross_points", "cost_dollars", "mean_net_dollars", "mean_dollars_low", "mean_dollars_high", "net_r", "r_denominator", "expectancy_r", "profit_factor", "max_drawdown_dollars"],
            population="Actual protected-candidate-fill cohorts; actual entry year/session/side.", units="USD, counts, GC points, initial-risk R and ratio rates.", scope="Standardized one-contract completed returns; not source-account execution.")
        draft.download("protected-transitions", "Protected entry and price-event transitions", transitions, draft.sources[transitions]["columns"],
            population="Original-breakout cohorts and explicit source/destination event sessions.", units="Saved counts and New York sessions.", scope="Chronologically confirmed breach-to-entry pairs; price reclaim remains separate from actual entry.")
        draft.download("all-level-time-recovery", "All-level recovery timing, support and exposure", timing, [k for k in timing_keys if k != "anchor"],
            population="Original-breakout cohorts across every saved level, event and observation horizon.", units="Saved minute means/bounds, counts and explicit diagnostic flag.", scope="All timing means and individual denominators retained; first known protected-breach origin. The saved anchor is separately retained in the pinned private source and explained in this report.")
    references = [{"id": "source-" + str(i), "kind": "saved-artifact", "label": s["path"],
                   "title": "Verified saved-source presentation projection", "runId": RUN,
                   "artifact": s["path"], "sha256": s["sha256"]} for i, s in enumerate(draft.sources.values())]
    report = {"schemaVersion": "1.1", "id": spec.publication_id,
              "title": "GC- Overnight Breakout 15M — " + spec.title,
              "summary": "Saved Phase 2 session-transition and cohort evidence. This presentation-only supplement preserves research values, frozen selection, unknown outcomes and the earlier reports.",
              "publishedAt": CREATED, "source": {"producer": "sahadeva", "runId": RUN},
              "sections": sections, "references": references, "downloads": draft.download_entries,
              "notes": ["Saved-cell presentation revision of the immutable Phase 2 run; no statistics recomputed.",
                        "Short internal table keys are presentation aliases; labels, copied CSVs and source-cell bindings retain the full saved meanings.",
                        "New York session attribution differs by original breakout, actual breach, price event and actual candidate fill."]}
    if len(sections) > 30 or len(json_bytes(report, compact=True)) > 2 * 1024 * 1024:
        raise ValueError("Presentation report exceeds native filtered bounds")
    source_map = draft.source_map()
    source_map.update(source_run_manifest_sha256=MANIFEST_SHA, source_run_locator=SOURCE_LOCATOR,
                      presentation_revision_id=spec.revision_id,
                      report_key_qualification="Only display keys are aliased. Binding source_column and original_source_column remain exact saved column names.")
    return draft, report, source_map


def generate(workspace, stage):
    source = workspace / SOURCE_LOCATOR
    if hashlib.sha256((source / "manifest.json").read_bytes()).hexdigest() != MANIFEST_SHA:
        raise ValueError("Immutable source run manifest pin mismatch")
    inputs = saved.SavedInputs(source)
    records = []
    for spec in SPECS:
        draft, report, source_map = assemble(inputs, spec)
        target = stage / "revisions" / spec.revision_id
        target.mkdir(parents=True, exist_ok=False)
        for path, data in draft.files.items():
            saved.write_new(target, path, data)
        saved.write_new(target, "publication.json", json_bytes(report, compact=True))
        saved.write_new(target, "source-map.json", json_bytes(source_map))
        for path in sorted((stage / "source").glob("*.py")):
            saved.write_new(target, "source/" + path.name, path.read_bytes())
        record = {"publication_id": spec.publication_id, "revision_id": spec.revision_id,
                  "source_root": str(target.resolve()), "source_run_id": RUN,
                  "future_revision_locator": f"reports/exports/{STUDY}/{RUN}/{spec.revision_id}",
                  "sections": len(report["sections"]), "displayed_cells": len(draft.bindings),
                  "publication_bytes": len((target / "publication.json").read_bytes()),
                  "publication_sha256": saved.sha_bytes((target / "publication.json").read_bytes()),
                  "source_map_sha256": saved.sha_bytes((target / "source-map.json").read_bytes()),
                  "downloads": [{"id": d["id"], "rows": d["rowCount"], "sha256": d["sha256"]} for d in report["downloads"]]}
        records.append(record)
    receipt = {"schema_version": "study23.phase2-session-presentation/v1", "result": "generated-awaiting-independent-verification",
               "source_run_id": RUN, "source_run_manifest_sha256": MANIFEST_SHA,
               "command": sys.argv, "python": sys.version, "publications": records,
               "qualification": "Saved-cell projection only; no research execution or statistical recomputation."}
    saved.write_new(stage, "generation-receipt.json", json_bytes(receipt))
    print(json.dumps({"result": receipt["result"], "publications": [{k: r[k] for k in ("publication_id", "sections", "displayed_cells", "publication_bytes")} for r in records]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    generate(args.workspace.resolve(), args.stage.resolve())
