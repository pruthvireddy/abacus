"""Parallel phase orchestration over unchanged scientific helpers.

Only product/interval cells execute independently. Original per-gate frames
are collected in configured order before one parent closes the full evidence.
No numerical algorithm, scoring mask, population or selection rule lives here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time
import traceback

import pandas as pd

from .execution import file_record, verify_record
from .stage3_execution import assert_frozen, assert_input_bytes, write_once
from .stage3_events import gate_spec
from .stage3_selection import (CELL, fixed_gate_id, fold_records, assess_candidates,
    select_nominees, validation_decisions)
from .stage3_statistics import (_phase_stream, summaries, quantiles, stability,
    _flow, grid_comparisons, neighborhoods, period_effects, _id, _write_csv, _manifest, TABLE_FILES)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configured_gates(cfg):
    result = []
    for product in cfg["products"]:
        gates = ([gate_spec("absolute", value) for value in cfg["absolute_gates"][product]]
                 + [gate_spec("atr", value) for value in cfg["atr_gates"]])
        for interval in cfg["interval_minutes"]:
            for touch in cfg["touch_modes"]:
                result.extend((product, int(interval), touch, gate["gate_id"]) for gate in gates)
    require(len(result) == len(set(result)), "duplicate configured development gateway")
    return tuple(result)


def cell_plan(cfg, authorized_gates):
    """Exact complete whitelist, partitioned without reordering or regrouping."""
    expected = configured_gates(cfg)
    actual = tuple(tuple(gate) for gate in authorized_gates)
    require(len(actual) == len(set(actual)) and set(actual) == set(expected),
            "complete authorized development gateway inventory required")
    return tuple(dict(cell=(product, int(interval)),
                      gates=tuple(g for g in expected if g[:2] == (product, int(interval))))
                 for product in cfg["products"] for interval in cfg["interval_minutes"])


def evaluation_plan(cfg, choices, period, authorized_gates):
    """Only frozen nominee/final choice plus its fixed baseline, never a grid."""
    require(period in ("validation", "final", "recent"), "explicit reserved evaluation period")
    require(not choices.duplicated(list(CELL)).any(), "duplicate frozen choice cell")
    expected_cells = {(p, int(i), t) for p in cfg["products"] for i in cfg["interval_minutes"] for t in cfg["touch_modes"]}
    actual_cells = {(r["product"], int(r["interval_minutes"]), r["touch_mode"]) for r in choices.to_dict("records")}
    require(len(choices) == len(expected_cells) and actual_cells == expected_cells, "complete frozen choice cell inventory")
    expected, known = set(), set(configured_gates(cfg))
    for row in choices.to_dict("records"):
        cell = row["product"], int(row["interval_minutes"]), row["touch_mode"]
        selected = row["nominee_gate_id"] if period == "validation" else row["selected_gate_id"]
        if period != "validation":
            require(row.get("final_gate_id", selected) == selected, "final frozen choice columns disagree")
        require(row["fixed_gate_id"] == fixed_gate_id(cell[0], cfg), "original own-cell fixed baseline required")
        pair = {(*cell, selected), (*cell, row["fixed_gate_id"])}
        require(pair <= known, "unknown frozen reserved gateway")
        expected.update(pair)
    actual = tuple(tuple(g) for g in authorized_gates)
    require(len(actual) == len(set(actual)) and set(actual) == expected, "reserved gateway roster differs from frozen choices")
    return tuple(dict(cell=(p, int(i)), gates=tuple(sorted(g for g in expected if g[:2] == (p, int(i)))))
                 for p in cfg["products"] for i in cfg["interval_minutes"])


@dataclass(frozen=True)
class CellJob:
    ordinal: int
    cell: tuple[str, int]
    gates: tuple[tuple[str, int, str, str], ...]
    stage: Path
    cfg: dict
    authorization: object
    acceptance_manifest: Path
    period: str = "development"


def stream_chunk(stage, cfg, payload, authorization, *, period="development"):
    """Call only the original scorers/statistical producers for one gateway."""
    require(period in ("development", "validation", "final", "recent") and authorization.period == period,
            "explicit matching scientific phase authorization")
    out, audit, record = _phase_stream(stage, cfg, payload, period, authorization)
    chunk = dict(key=(payload["product"], int(payload["interval_minutes"]), payload["touch_mode"], payload["gate"]["gate_id"]),
        record=record, scorecard=summaries(out, payload, period, cfg["horizons"]),
        quantiles=quantiles(out, payload, period, cfg["horizons"]),
        stability=stability(out, payload, period, cfg), audit=audit, flow=_flow(payload, period, cfg))
    if period in ("development", "validation"):
        chunk["folds"] = fold_records(out, payload["gate"], payload["product"], payload["interval_minutes"], payload["touch_mode"],
                                      [fold["id"] for fold in cfg["development_folds" if period == "development" else "validation_folds"]])
    if period != "development":
        chunk["outcomes"] = out
    return chunk


def run_cell(job):
    """One original causal iterator, one cell, unique existing output namespaces."""
    from run_stage3 import gateway_iterator
    assert_frozen(job.stage, job.authorization.workspace)
    require(job.period in ("development", "validation", "final", "recent") and job.authorization.period == job.period,
            "matching explicit worker phase authorization")
    require(all(g[:2] == job.cell and g in job.authorization.gates for g in job.gates), "worker cell whitelist")
    if job.period == "development":
        expected = next(item["gates"] for item in cell_plan(job.cfg, job.authorization.gates) if item["cell"] == job.cell)
    else:
        expected = tuple(sorted(g for g in job.authorization.gates if g[:2] == job.cell))
    require(job.gates == expected, "complete original ordered cell gateway inventory")
    chunks, observed = [], []
    for payload in gateway_iterator(job.stage, job.period, list(job.gates),
                                    cell=job.cell, manifest_path=job.acceptance_manifest):
        key = payload["product"], int(payload["interval_minutes"]), payload["touch_mode"], payload["gate"]["gate_id"]
        require(key in job.gates and key not in observed, "unexpected or duplicate worker gateway")
        observed.append(key)
        if job.period == "development":
            chunks.append(stream_chunk(job.stage, job.cfg, payload, job.authorization))
        else:
            chunks.append(stream_chunk(job.stage, job.cfg, payload, job.authorization, period=job.period))
    require(tuple(observed) == job.gates, "worker yielded incomplete or reordered cell")
    require(job.acceptance_manifest.is_file(), "complete retained cell acceptance manifest required")
    assert_frozen(job.stage, job.authorization.workspace)
    return dict(ordinal=job.ordinal, cell=job.cell, chunks=chunks, acceptance_manifest=file_record(job.acceptance_manifest, job.stage))


def ordered_chunks(plan, results):
    """Reject failures/duplicates/missing work before any global publication."""
    found = {}
    for result in results:
        ordinal = result["ordinal"]
        require(type(ordinal) is int and 0 <= ordinal < len(plan) and ordinal not in found,
                "duplicate or unknown completed cell ordinal")
        expected = plan[ordinal]
        require(tuple(result["cell"]) == expected["cell"], "completed cell identity differs")
        keys = tuple(tuple(chunk["key"]) for chunk in result["chunks"])
        require(keys == expected["gates"], "completed cell has missing/duplicate/reordered gateway chunks")
        found[ordinal] = result
    require(set(found) == set(range(len(plan))), "incomplete parallel cell results; global close refused")
    chunks = [chunk for ordinal in range(len(plan)) for chunk in found[ordinal]["chunks"]]
    keys = [tuple(chunk["key"]) for chunk in chunks]
    require(len(keys) == len(set(keys)), "duplicate global gateway chunks")
    return chunks, [found[ordinal] for ordinal in range(len(plan))]


def close_development(stage, cfg, chunks, expected_gates):
    """Original single-parent concatenation/schema/write sequence, unmodified estimators."""
    require(tuple(tuple(chunk["key"]) for chunk in chunks) == tuple(expected_gates),
            "original complete development chunk order required")
    scorecard = pd.concat([c["scorecard"] for c in chunks], ignore_index=True)
    fold_table = pd.concat([c["folds"] for c in chunks], ignore_index=True)
    grid = grid_comparisons(scorecard, cfg)
    assessments = assess_candidates(fold_table, cfg, phase="development")
    nominees = select_nominees(assessments, cfg)
    fold_table["record_kind"], assessments["record_kind"] = "fold_support", "candidate_assessment"
    fold_table["phase"], fold_table["period_id"] = "development", "development"
    assessments["period_id"], assessments["fold_id"] = "development", "assessment"
    t12 = pd.concat([fold_table, assessments], ignore_index=True)
    t12["row_id"] = [_id(row, ("fold_id", "record_kind")) for row in t12.to_dict("records")]
    nominees["period_id"] = "development"
    nominees["row_id"] = [_id(row, ("phase",)) for row in nominees.to_dict("records")]
    tables = [
        _write_csv(stage, "S3-T01_development_flow.csv", pd.concat([c["flow"] for c in chunks], ignore_index=True)),
        _write_csv(stage, "S3-T02_development_horizon_scorecard.csv", scorecard),
        _write_csv(stage, "S3-T03_development_quantiles.csv", pd.concat([c["quantiles"] for c in chunks], ignore_index=True)),
        _write_csv(stage, "S3-T04_development_stability.csv", pd.concat([c["stability"] for c in chunks], ignore_index=True)),
        _write_csv(stage, TABLE_FILES["grid"], grid), _write_csv(stage, TABLE_FILES["folds"], t12),
        _write_csv(stage, TABLE_FILES["nominees"], nominees),
        _write_csv(stage, TABLE_FILES["neighbors"], neighborhoods(grid)),
        _write_csv(stage, "S3-T16_development_masks.csv", pd.concat([c["audit"] for c in chunks], ignore_index=True)),
    ]
    return _manifest(stage, "development", [chunk["record"] for chunk in chunks], tables, nominees)


def close_evaluation(stage, cfg, choices, period, chunks, expected_gates):
    """Original reserved parent close, including shared-period paired uncertainty."""
    require(period in ("validation", "final", "recent"), "explicit reserved evaluation close")
    require(tuple(tuple(chunk["key"]) for chunk in chunks) == tuple(expected_gates),
            "original complete reserved chunk order required")
    outcomes = pd.concat([chunk["outcomes"] for chunk in chunks], ignore_index=True)
    tables, evaluation_choices = [], choices.copy()
    if period == "validation":
        fold_table = pd.concat([chunk["folds"] for chunk in chunks], ignore_index=True)
        assessments = assess_candidates(fold_table, cfg, phase="validation")
        decisions = validation_decisions(assessments, choices, cfg)
        evaluation_choices["selected_gate_id"] = evaluation_choices.nominee_gate_id
        decisions["period_id"] = "validation"
        decisions["row_id"] = [_id(row, ("phase",)) for row in decisions.to_dict("records")]
        fold_table["record_kind"], assessments["record_kind"] = "fold_support", "candidate_assessment"
        fold_table["period_id"], assessments["period_id"] = period, period
        assessments["fold_id"] = "assessment"
        t12 = pd.concat([fold_table, assessments], ignore_index=True)
        t12["row_id"] = [_id(row, ("fold_id", "record_kind")) for row in t12.to_dict("records")]
        tables.extend([_write_csv(stage, "S3-T12_validation_fold_eligibility.csv", t12),
                       _write_csv(stage, "S3-T13_validation_decisions.csv", decisions)])
    else:
        decisions = choices.copy()
    effects, sufficient = period_effects(outcomes, evaluation_choices, cfg, period)
    tables.extend([
        _write_csv(stage, f"S3-T01_{period}_flow.csv", pd.concat([chunk["flow"] for chunk in chunks], ignore_index=True)),
        _write_csv(stage, f"S3-T02_{period}_horizon_scorecard.csv", pd.concat([chunk["scorecard"] for chunk in chunks], ignore_index=True)),
        _write_csv(stage, f"S3-T03_{period}_quantiles.csv", pd.concat([chunk["quantiles"] for chunk in chunks], ignore_index=True)),
        _write_csv(stage, f"S3-T04_{period}_stability.csv", pd.concat([chunk["stability"] for chunk in chunks], ignore_index=True)),
        _write_csv(stage, f"S3-T14_{period}_effects.csv", effects),
        _write_csv(stage, f"S3-weekly-{period}.csv", sufficient),
        _write_csv(stage, f"S3-T16_{period}_masks.csv", pd.concat([chunk["audit"] for chunk in chunks], ignore_index=True)),
    ])
    return _manifest(stage, period, [chunk["record"] for chunk in chunks], tables, decisions)


def acceptance_records(stage, mapped, ordered_results, expected_gates, *, period="development"):
    """Original common bars then per-gate technical/events record ordering."""
    require(len(mapped) == len({(r["product"], int(r["interval_minutes"])) for r in mapped}), "duplicate common mapped cell")
    by_gate, declared_bars = {}, {}
    for result in ordered_results:
        manifest_path = verify_record(result["acceptance_manifest"], stage)
        value = json.loads(Path(manifest_path).read_text())
        require(value["period"] == period and value["schema_version"] == "study21.stage3-acceptance/v1", "cell acceptance manifest scope")
        for record in value["records"]:
            if record["role"] == "bars":
                key = record["product"], int(record["interval_minutes"])
                require(key not in declared_bars or declared_bars[key] == record, "conflicting common mapped bar pins")
                declared_bars[key] = record
                continue
            require(record["role"] in ("technical", "events"), "unexpected cell acceptance role")
            key = record["product"], int(record["interval_minutes"]), record.get("touch_mode", record.get("branch")), record["gate_id"]
            require(key[:2] == tuple(result["cell"]) and key in expected_gates, "cell acceptance artifact outside whitelist")
            role_key = key, record["role"]
            require(role_key not in by_gate, "duplicate acceptance artifact role")
            by_gate[role_key] = record
    expected_bars = {(r["product"], int(r["interval_minutes"])): r for r in mapped}
    require(declared_bars == expected_bars, "complete identical common mapped input pins required")
    require(set(by_gate) == {(key, role) for key in expected_gates for role in ("technical", "events")},
            "complete technical/event acceptance inventory required")
    records = list(mapped) + [by_gate[(key, role)] for key in expected_gates for role in ("technical", "events")]
    require(len({r["path"] for r in records}) == len(records), "unique acceptance artifact locations required")
    for record in records:
        verify_record(record, None if Path(record["path"]).is_absolute() else stage)
    return records


def validate_outcome_records(stage, chunks, *, period="development"):
    """Reject cross-cell/phase record identities before global publication."""
    paths = set()
    for chunk in chunks:
        record = chunk["record"]
        key = (record["product"], int(record["interval_minutes"]), record["touch_mode"], record["gate_id"])
        require(key == tuple(chunk["key"]) and record["role"] == "outcomes" and record["period_id"] == period,
                "outcome identity differs from completed authorized gateway")
        require(record["path"] not in paths, "duplicate phase outcome artifact location")
        paths.add(record["path"])
        verify_record(record, stage)


def collect_cells(jobs, workers, worker=run_cell):
    """Abort the pool on a cell failure; no global scientific artifacts close."""
    require(type(workers) is int and workers > 0, "positive explicit process count")
    pool = multiprocessing.get_context("spawn").Pool(processes=workers)
    try:
        results = list(pool.imap_unordered(worker, jobs, chunksize=1))
        pool.close()
        pool.join()
        return results
    except BaseException:
        pool.terminate()
        pool.join()
        raise


def evaluate_period_parallel(stage, cfg, choices, period, authorization, *, workers=3):
    """Whitelisted reserved streams only, six cells, original shared-week close."""
    stage = Path(stage).resolve()
    require(period in ("validation", "final", "recent") and authorization is not None and authorization.period == period,
            "explicit reserved-period authorization required")
    require(Path(authorization.stage).resolve() == stage, "authorization stage must identify output stage")
    require(type(workers) is int and workers == cfg["evaluation_workers"] == 3, "three workers must match frozen evaluation configuration")
    require(json.loads((stage / "config.json").read_text()) == cfg, "execution configuration differs from frozen saved config")
    choice_source = file_record(Path(choices)) if isinstance(choices, (str, Path)) else None
    choices = pd.read_csv(choices) if choice_source is not None else choices.copy()
    plan = evaluation_plan(cfg, choices, period, authorization.gates)
    expected = tuple(g for item in plan for g in item["gates"])
    require(len(plan) == 6 and len(choices) == 12 and 12 <= len(expected) <= 24 and all(2 <= len(item["gates"]) <= 4 for item in plan),
            "complete six-cell twelve-choice reserved execution required")
    require(not (stage / f"acceptance-{period}.manifest.json").exists() and not (stage / f"stage3-{period}.manifest.json").exists(), "parallel phase overwrite refused")
    require(not list((stage / f"ledgers/stage3/{period}").glob("*.parquet")), "fresh reserved outcome namespace required")
    assert_frozen(stage, authorization.workspace)
    assert_input_bytes(stage)
    if authorization.predecessor is not None:
        verify_record(authorization.predecessor, stage)
    mapped_manifest = stage / "mapped.manifest.json"
    mapped = json.loads(mapped_manifest.read_text())["records"]
    require({(r["product"], int(r["interval_minutes"])) for r in mapped} == {item["cell"] for item in plan}, "full common mapped cell inventory")
    for record in mapped:
        verify_record(record)
    directory = stage / f"provenance/cell-acceptance/{period}"
    directory.mkdir(parents=True, exist_ok=False)
    jobs = [CellJob(i, item["cell"], item["gates"], stage, cfg, authorization,
                    directory / f'{item["cell"][0]}_{item["cell"][1]}.manifest.json', period) for i, item in enumerate(plan)]
    started = time.perf_counter()
    write_once(stage / f"provenance/parallel-{period}-before.json", dict(status="frozen_before_parallel_evaluation",
        period=period, created_at_utc=datetime.now(timezone.utc).isoformat(), checker=file_record(Path(__file__)), workers=workers,
        source_inventory=file_record(stage / "provenance/source-inventory.json", stage), config=file_record(stage / "config.json", stage),
        input_lock=file_record(stage / "inputs.lock.json", stage), mapped_manifest=file_record(mapped_manifest, stage),
        predecessor=authorization.predecessor, choice_source=choice_source,
        cells=[dict(ordinal=job.ordinal, cell=list(job.cell), gates=[list(g) for g in job.gates], manifest=job.acceptance_manifest.relative_to(stage).as_posix()) for job in jobs],
        execution=dict(argv=[sys.executable, *sys.argv], cwd=os.getcwd(), environment={k: os.environ[k] for k in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "UV_CACHE_DIR", "PYTHONPATH") if k in os.environ}),
        numerical_disposition="Only explicitly frozen selected/nominee and fixed streams; original numerical helpers and single global shared-week uncertainty close; no replacement or grid."))
    try:
        results = collect_cells(jobs, workers)
        chunks, ordered = ordered_chunks(plan, results)
        require(tuple(tuple(chunk["key"]) for chunk in chunks) == expected, "complete original reserved gateway order")
        acceptance = acceptance_records(stage, mapped, ordered, expected, period=period)
        validate_outcome_records(stage, chunks, period=period)
        assert_frozen(stage, authorization.workspace)
        assert_input_bytes(stage)
        if authorization.predecessor is not None:
            verify_record(authorization.predecessor, stage)
        if choice_source is not None:
            verify_record(choice_source)
        write_once(stage / f"acceptance-{period}.manifest.json", dict(schema_version="study21.stage3-acceptance/v1",
            period=period, records=acceptance,
            technical_scope="Causal 2017-to-phase-end prefix; state fields joined to full input-only bars by timestamp; no outcome eligibility changes acceptance."))
        receipt = close_evaluation(stage, cfg, choices, period, chunks, expected)
        assert_frozen(stage, authorization.workspace)
        write_once(stage / f"provenance/parallel-{period}-completion.json", dict(status="passed", period=period, workers=workers,
            runtime_seconds=time.perf_counter()-started, gateway_count=len(chunks), cell_count=len(ordered),
            acceptance_manifest=file_record(stage / f"acceptance-{period}.manifest.json", stage),
            outcome_manifest=receipt["manifest"], cell_manifests=[result["acceptance_manifest"] for result in ordered],
            scientific_order="Original configured cell/authorized per-gate frame order; original validation decisions and shared-period paired-week uncertainty in one parent."))
        return receipt
    except BaseException as error:
        write_once(stage / f"provenance/parallel-{period}-failure.json", dict(status="failed_partial_artifacts_preserved", period=period,
            error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(), runtime_seconds=time.perf_counter()-started,
            qualification="Partial cell evidence cannot close a reserved phase, rescue a failed nominee, or authorize any following period."))
        raise


def produce_development_parallel(stage, cfg, authorization, *, workers=3):
    """Production development only; all192 gates, six cells, one global close."""
    stage = Path(stage).resolve()
    require(authorization is not None and authorization.period == "development", "explicit development phase authorization required")
    require(Path(authorization.stage).resolve() == stage, "authorization stage must identify output stage")
    require(type(workers) is int and workers == cfg["development_workers"] == 3, "three workers must match frozen execution configuration")
    require(json.loads((stage / "config.json").read_text()) == cfg, "execution configuration differs from frozen saved config")
    plan = cell_plan(cfg, authorization.gates)
    expected = configured_gates(cfg)
    require(len(plan) == 6 and len(expected) == 192 and all(len(item["gates"]) == 32 for item in plan), "complete six-cell192-stream development execution required")
    require(not (stage / "acceptance-development.manifest.json").exists() and not (stage / "stage3-development.manifest.json").exists(), "parallel phase overwrite refused")
    require(not list((stage / "ledgers/stage3/development").glob("*.parquet")), "fresh development outcome namespace required")
    assert_frozen(stage, authorization.workspace)
    assert_input_bytes(stage)
    mapped_manifest = stage / "mapped.manifest.json"
    mapped = json.loads(mapped_manifest.read_text())["records"]
    require({(r["product"], int(r["interval_minutes"])) for r in mapped} == {item["cell"] for item in plan}, "full common mapped cell inventory")
    for record in mapped:
        verify_record(record)
    directory = stage / "provenance/cell-acceptance/development"
    directory.mkdir(parents=True, exist_ok=False)
    jobs = [CellJob(i, item["cell"], item["gates"], stage, cfg, authorization,
                    directory / f'{item["cell"][0]}_{item["cell"][1]}.manifest.json') for i, item in enumerate(plan)]
    started = time.perf_counter()
    write_once(stage / "provenance/parallel-development-before.json", dict(status="frozen_before_parallel_development",
        created_at_utc=datetime.now(timezone.utc).isoformat(), checker=file_record(Path(__file__)), workers=workers,
        source_inventory=file_record(stage / "provenance/source-inventory.json", stage), config=file_record(stage / "config.json", stage),
        input_lock=file_record(stage / "inputs.lock.json", stage), mapped_manifest=file_record(mapped_manifest, stage),
        fixed_baseline=file_record(stage / "provenance/fixed-baseline-parity.json", stage),
        cells=[dict(ordinal=job.ordinal, cell=list(job.cell), gates=[list(g) for g in job.gates], manifest=job.acceptance_manifest.relative_to(stage).as_posix()) for job in jobs],
        execution=dict(argv=[sys.executable, *sys.argv], cwd=os.getcwd(), environment={k: os.environ[k] for k in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "UV_CACHE_DIR", "PYTHONPATH") if k in os.environ}),
        numerical_disposition="Only existing frozen numerical helpers; independent cell scheduling and deterministic single-parent scientific close."))
    try:
        results = collect_cells(jobs, workers)
        chunks, ordered = ordered_chunks(plan, results)
        require(tuple(tuple(c["key"]) for c in chunks) == expected, "complete original192 gateway order")
        acceptance = acceptance_records(stage, mapped, ordered, expected)
        # Validate all results and current immutable inputs before global close.
        validate_outcome_records(stage, chunks)
        assert_frozen(stage, authorization.workspace)
        assert_input_bytes(stage)
        write_once(stage / "acceptance-development.manifest.json", dict(schema_version="study21.stage3-acceptance/v1",
            period="development", records=acceptance,
            technical_scope="Causal 2017-to-phase-end prefix; state fields joined to full input-only bars by timestamp; no outcome eligibility changes acceptance."))
        receipt = close_development(stage, cfg, chunks, expected)
        assert_frozen(stage, authorization.workspace)
        write_once(stage / "provenance/parallel-development-completion.json", dict(status="passed", workers=workers,
            runtime_seconds=time.perf_counter()-started, gateway_count=len(chunks), cell_count=len(ordered),
            acceptance_manifest=file_record(stage / "acceptance-development.manifest.json", stage),
            outcome_manifest=receipt["manifest"], cell_manifests=[result["acceptance_manifest"] for result in ordered],
            scientific_order="Original configured product/interval/touch/gate frame order; no per-cell concatenation before global inference."))
        return receipt
    except BaseException as error:
        write_once(stage / "provenance/parallel-development-failure.json", dict(status="failed_partial_artifacts_preserved",
            error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(),
            runtime_seconds=time.perf_counter()-started,
            qualification="Failed work never qualifies a complete scientific phase; retained partial artifacts must not be overwritten or used to select a replacement."))
        raise
