"""Saved-input, acceptance, parity and dual-path review; no producer imports."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

STUDY = "21_ema_cloud_trend_follow_opportunity"
BASELINE_ID = "20261010T221954Z_s1_8c6e_r3"
DELIVERY_SHA = "59010a558b4e727dbfaa37a64b4a209590288f23744127ab98747cd27ff56d44"
START = pd.Timestamp("2018-01-01", tz="America/New_York").tz_convert("UTC")
END = pd.Timestamp("2021-01-01", tz="America/New_York").tz_convert("UTC")
KEY = ["product", "interval_minutes", "timestamp"]
TABLES = ("S1-T00_coverage.csv", "S1-T01_signal_flow.csv", "S1-T02_horizon_scorecard.csv",
          "S1-T03_quantiles.csv", "S1-T04_stability.csv", "S1-T05_calendar.csv",
          "S1-T06_examples.csv", "S1-bootstrap.csv", "S1-comparisons.csv")


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def pin(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def verify(record, base=None):
    path = Path(record["path"])
    if not path.is_absolute():
        require(base is not None and ".." not in path.parts, "unsafe relative locator")
        path = base / path
    require(path.is_file() and not path.is_symlink(), "ordinary retained file required")
    observed = pin(path)
    require(observed["bytes"] == record["bytes"] and observed["sha256"] == record["sha256"],
            "byte identity: " + str(path))
    return path


def read(record, base=None):
    path = verify(record, base)
    result = pd.read_parquet(path)
    verify(record, base)
    return result


def compare(actual, expected, keys, fields=None, label="frame"):
    require(not actual.duplicated(keys).any() and not expected.duplicated(keys).any(),
            label + ": duplicate keys")
    fields = list(expected.columns) if fields is None else list(fields)
    require(set(fields) <= set(actual.columns), label + ": missing inherited fields")
    actual, expected = actual.set_index(keys).sort_index(), expected.set_index(keys).sort_index()
    require(actual.index.equals(expected.index), label + ": scientific key set")
    for field in fields:
        if field in keys:
            continue
        a, e = actual[field], expected[field]
        same = a.eq(e).fillna(False) | (a.isna() & e.isna())
        if pd.api.types.is_bool_dtype(e.dtype):
            require(pd.api.types.is_bool_dtype(a.dtype), label + "/" + field + ": boolean dtype")
        elif e.dtype == object and any(isinstance(v, (bool, np.bool_)) for v in e.dropna().unique()):
            at = a.map(lambda v: isinstance(v, (bool, np.bool_)) if pd.notna(v) else None)
            et = e.map(lambda v: isinstance(v, (bool, np.bool_)) if pd.notna(v) else None)
            same &= at.eq(et) | (a.isna() & e.isna())
        require(same.all(), label + "/" + field + ": exact/null-aware value")
    return len(expected) * len(fields)


def source_and_inputs(stage, workspace):
    inventory = json.loads((stage / "provenance/source-inventory.json").read_text())
    covered = set()
    for r in inventory["sources"]:
        covered.add(r["workspace_path"])
        for path, base in ((r["workspace_path"], workspace), (r["snapshot_path"], stage)):
            verify(dict(path=path, bytes=r["bytes"], sha256=r["sha256"]), base)
    required = {p.relative_to(workspace).as_posix()
                for p in (workspace / "studies" / STUDY).rglob("*.py")}
    require(required <= covered, "every study Python source/test retained")
    baseline = workspace / "runs" / STUDY / BASELINE_ID
    require(pin(stage / "inputs.lock.json")["sha256"] == pin(baseline / "inputs.lock.json")["sha256"],
            "unchanged inherited input lock")
    lock = json.loads((stage / "inputs.lock.json").read_text())
    delivery_path = verify(lock["delivery"], workspace)
    require(lock["delivery"]["sha256"] == DELIVERY_SHA, "explicit reusable release pin")
    delivery = json.loads(delivery_path.read_text())
    consumed, producer_records = [], []
    for r in delivery["output_files"] + delivery["auxiliary_files"] + delivery["source_manifest_pins"]:
        consumed.append(pin(verify(r, workspace)))
    producer = workspace / "data/features/ema_cloud/version=1.0.0/provenance"
    for r in delivery["source_files"]:
        historical = r.get("role") == "executed_data_source"
        path = producer / Path(r["path"]).name if historical else workspace / r["path"]
        observed = pin(verify(dict(r, path=str(path))))
        consumed.append(observed)
        if historical:
            producer_records.append(dict(declared_historical_locator=r["path"],
                                         retained_producer=observed,
                                         current_canonical=pin(workspace / r["path"])))
    require(lock["feature_warmup"] == 250 and lock["endpoint"] == END.isoformat(),
            "warmup/endpoint unchanged")
    require(pin(stage / "provenance/uv.lock")["sha256"] == pin(workspace / "uv.lock")["sha256"],
            "environment lock identity")
    for name, canonical in (("config.json", "config-stage2.json"), ("protocol.md", "protocol-stage2.md")):
        require(pin(stage / name)["sha256"] == pin(workspace / "studies" / STUDY / canonical)["sha256"],
                "frozen settings/protocol")
    return dict(frozen_sources=len(inventory["sources"]),
        source_inventory=pin(stage / "provenance/source-inventory.json"),
        input_lock=pin(stage / "inputs.lock.json"), delivery=pin(delivery_path),
        consumed_input_records=consumed, historical_producer_resolutions=producer_records,
        qualification="Published partitions/support bytes and immutable original producer snapshots verify. Corrected canonical source is separately frozen. Missing raw mappings/condition JSON/ES roll1 definitions, vendor arrival, native TradingView equivalence, annual holiday certification and off-device backup remain unverified. 2017 causal warmup, 250-observation resets, conservative unusable holiday/early-close sessions and retained unknown slots are unchanged.")


def acceptance(stage, manifest):
    cells = []
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            selected = [r for r in manifest["records"]
                        if r["product"] == product and r["interval_minutes"] == interval]
            def role(name, branch=None):
                matches = [r for r in selected if r["role"] == name
                           and (branch is None or r.get("branch") == branch)]
                require(len(matches) == 1, "unique saved role/branch")
                return read(matches[0], stage)
            bars, member, episodes, pairs, union = (
                role(name) for name in ("bars", "membership", "episodes", "pairs", "union"))
            require((bars.timestamp < END).all() and (bars.available_at <= END).all(),
                    "retained roster endpoint")
            n = compare(member, bars, KEY, label="membership complete mapped roster")
            require(member.eligible.eq(bars.usable & bars.feature_valid).all(), "common eligibility")
            streams, dev_events = {}, []
            for branch in ("fast", "slow"):
                tech, event = role("technical", branch), role("events", branch)
                streams[branch] = tech
                n += compare(tech, bars, KEY, label=branch + " complete mapped roster")
                require(tech.touch_mode.eq(branch).all() and event.touch_mode.eq(branch).all(),
                        "explicit branch metadata")
                scoped = tech.loc[tech.accepted & tech.timestamp.ge(START) & tech.timestamp.lt(END)]
                n += compare(event, scoped, ["event_id"], label=branch + " accepted development identities")
                require(event.reference_price.eq(event.close).all()
                        and event.entry_at.eq(event.available_at).all(), "confirmed close/modelled arrival")
                require((event.timestamp >= START).all() and (event.timestamp < END).all(),
                        "development event scope")
                fields = ("accepted", "event_id", "suppression_reason", "armed_before",
                          "armed_after", "penetration")
                expected = tech[KEY + list(fields)].rename(columns={
                    f: branch + "_" + ("reason" if f == "suppression_reason" else f) for f in fields})
                n += compare(member, expected, KEY, label=branch + " independent membership decisions")
                dev_events.append(event)
            n += compare(streams["fast"], streams["slow"], KEY,
                         fields=KEY + ["direction", "side", "reset_reason", "full_departure"],
                         label="common reset/departure")
            require(not episodes.shared_episode_id.duplicated().any()
                    and not pairs.pair_id.duplicated().any(), "unique shared episode/pair IDs")
            n += compare(pairs, episodes, ["shared_episode_id"], label="pair preserves causal episode")
            for branch in ("fast", "slow"):
                accepted = member.loc[member[branch + "_accepted"]]
                require(accepted.shared_episode_id.notna().all(), "accepted geometric episode")
                first = accepted.groupby("shared_episode_id", sort=False).first()
                declared = pairs.set_index("shared_episode_id")
                expected_ids = first[branch + "_event_id"].reindex(declared.index)
                ids = declared["first_" + branch + "_event_id"]
                require((ids.eq(expected_ids) | (ids.isna() & expected_ids.isna())).all(),
                        "full causal first " + branch + " retained")
                scope = first.timestamp.ge(START) & first.timestamp.lt(END)
                require(declared["first_" + branch + "_in_development"].eq(
                    scope.reindex(declared.index, fill_value=False)).all(), "first-event scope flags")
            require(pairs.pair_in_development.eq(
                pairs.first_fast_in_development & pairs.first_slow_in_development).all(),
                "paired development scope")
            outside = pairs.loc[~pairs.pair_in_development]
            require(outside[["slow_minus_fast_signal_minutes", "slow_minus_fast_reference_points"]]
                    .isna().all().all(), "outside-scope pair differences null")
            warm = pairs.loc[pairs.first_fast_event_id.notna() & ~pairs.first_fast_in_development]
            require(warm[["same_bar_slow_contact", "strictly_later_slow_contact",
                          "strictly_later_slow_signal"]].isna().all().all(),
                    "warmup-first descriptors remain undefined")
            accepted_dev = member.loc[member.timestamp.ge(START) & member.timestamp.lt(END)
                                     & (member.fast_accepted | member.slow_accepted)]
            n += compare(union, accepted_dev, KEY,
                fields=KEY + ["fast_event_id", "slow_event_id", "accepted_membership", "shared_episode_id"],
                label="deduplicated accepted union")
            require(union.representative_event_id.eq(
                union.slow_event_id.combine_first(union.fast_event_id)).all(),
                "slow-preferred union representative")
            event_lookup = pd.concat(dev_events, ignore_index=True).set_index("event_id", verify_integrity=True)
            representative = event_lookup.loc[union.representative_event_id].reset_index(drop=True)
            representative["event_id"], representative["touch_mode"] = union.event_id.to_numpy(), "union"
            n += compare(union, representative, ["event_id"], label="union selected saved event transfer")
            cells.append(dict(product=product, interval_minutes=interval, scheduled_slots=len(bars),
                fast_development_events=len(dev_events[0]), slow_development_events=len(dev_events[1]),
                episodes=len(episodes), union_events=len(union), compared_cells=n))
    return dict(status="passed", cells=cells, compared_cells=sum(c["compared_cells"] for c in cells))


def slow_parity(stage, workspace, manifest):
    baseline = workspace / "runs" / STUDY / BASELINE_ID
    old_manifest = json.loads((baseline / "events.manifest.json").read_text())
    receipt = json.loads((stage / "provenance/slow-baseline-parity.json").read_text())
    require(receipt["status"] == "passed" and receipt["mismatch_count"] == 0
            and receipt["tolerance"] == 0, "actual exact slow parity receipt")
    require(receipt["ledger_artifacts_compared"] == 24 and receipt["table_artifacts_compared"] == 9,
            "complete slow parity scope")
    require(receipt["manifests"] == [pin(baseline / "events.manifest.json"),
            pin(stage / "slow-evidence.manifest.json")], "immutable parity phase manifest pins")
    for r in receipt["consumed_artifacts"]:
        verify(r)
    n = 0
    for r in old_manifest["records"]:
        matches = [x for x in manifest["records"] if x["role"] == r["role"]
                   and x["product"] == r["product"] and x["interval_minutes"] == r["interval_minutes"]
                   and x.get("branch", "slow") == "slow"]
        require(len(matches) == 1, "one inherited slow ledger")
        old, current = read(r, baseline), read(matches[0], stage)
        keys = KEY if r["role"] in ("bars", "technical") else (
            ["event_id", "horizon"] if r["role"] == "outcomes" else ["event_id"])
        n += compare(current, old, keys, fields=[c for c in old if c != "stage"],
                     label="independent inherited " + r["role"])
    table_cells = 0
    for name in TABLES:
        old = pd.read_csv(baseline / "tables" / name, dtype=str, keep_default_na=False)
        current = pd.read_csv(stage / "parity/slow" / name, dtype=str, keep_default_na=False)
        keys = ["row_id"] if "row_id" in old else ["product", "interval_minutes", "year", "split"]
        table_cells += compare(current, old, keys, label="exact original-string " + name)
    return dict(status="passed", receipt=pin(stage / "provenance/slow-baseline-parity.json"),
                ledgers=24, tables=9, ledger_cells=n, table_cells=table_cells, tolerance=0)


def final_dual(stage, manifest):
    cells = []
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            records = [r for r in manifest["records"]
                       if r["product"] == product and r["interval_minutes"] == interval]
            union = read(next(r for r in records if r["role"] == "union"), stage)
            outcome = pd.concat([read(r, stage) for r in records if r["role"] == "outcomes"],
                                ignore_index=True)
            require(outcome.timestamp.ge(START).all() and outcome.timestamp.lt(END).all(),
                    "outcome development scope")
            require(outcome.terminal_at.dropna().le(END).all(), "outcome completion boundary")
            lookup, dual = outcome.set_index("event_id"), union.loc[union.accepted_membership.eq("both")]
            n = 0
            fields = [c for c in outcome if c not in
                      {"event_id", "touch_mode", "selected_ema", "episode_id"}]
            for row in dual.itertuples(index=False):
                fast = lookup.loc[[row.fast_event_id]].reset_index()
                slow = lookup.loc[[row.slow_event_id]].reset_index()
                n += compare(fast, slow, ["horizon"], fields=fields,
                             label="direct all-field dual path equality")
            saved = read(next(r for r in records if r["role"] == "union_outcomes"), stage)
            projected = outcome.merge(union[["union_id", "representative_event_id",
                    "fast_event_id", "slow_event_id"]], left_on="event_id",
                    right_on="representative_event_id", how="inner", validate="many_to_one")
            projected["source_event_id"] = projected.event_id
            projected["event_id"], projected["touch_mode"] = projected.union_id, "union"
            n += compare(saved, projected, ["event_id", "horizon"],
                         label="saved slow-preferred union paths")
            cells.append(dict(product=product, interval_minutes=interval, dual_bars=len(dual),
                              horizon_rows=len(saved), compared_cells=n))
    return dict(status="passed", cells=cells, compared_cells=sum(c["compared_cells"] for c in cells))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--phase", choices=("acceptance", "slow", "final"), required=True)
    args = parser.parse_args()
    stage, workspace = args.stage.resolve(), args.stage.resolve().parents[2]
    name = {"acceptance": "acceptance.manifest.json", "slow": "slow-evidence.manifest.json",
            "final": "events.manifest.json"}[args.phase]
    before = pin(stage / name)
    manifest = json.loads((stage / name).read_text())
    require(not manifest["reserved_outcomes_computed"] and manifest["run_id"] == stage.name,
            "phase identity/scope")
    for r in manifest["records"]:
        verify(r, stage)
    result = dict(schema_version="study21.stage2-independent-input-acceptance-review/v1",
        status="passed", phase=args.phase, run_id=stage.name, checker=pin(__file__),
        created_at=datetime.now(timezone.utc).isoformat(), phase_manifest=before,
        input_review=source_and_inputs(stage, workspace), acceptance_review=acceptance(stage, manifest),
        outcomes_computed=False, features_rebuilt=False, source_edits=False,
        numerical_producer_imports=False)
    if args.phase in ("slow", "final"):
        result["slow_parity_review"] = slow_parity(stage, workspace, manifest)
    if args.phase == "final":
        result["direct_dual_union_review"] = final_dual(stage, manifest)
    require(before == pin(stage / name), "phase manifest changed during review")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
