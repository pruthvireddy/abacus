"""Development-only parallel orchestration of the unchanged independent checker.

The per-cell body and its byte-checking read closure are extracted from the
maintained serial verifier's AST without changing any scientific expression.
The parent retains the global family, neighborhood and byte close. Reserved
phase verification continues through the original serial verifier.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ProcessPoolExecutor
import copy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import inspect
import itertools
import json
import multiprocessing
from pathlib import Path
from time import perf_counter

from . import stage3_reconcile as scientific


def executable_sources():
    src = Path(__file__).resolve().parent
    return [src / name for name in ("stage3_reference.py", "stage3_reconcile.py", "stage3_parallel_reconcile.py")] + [src.parent / "tests/test_stage3_parallel_reconcile.py"]


def assert_pins(pins, label="parallel verifier source/input drift"):
    for pin in pins:
        path = Path(pin["path"])
        scientific.require(path.stat().st_size == pin["bytes"] and scientific.sha256(path) == pin["sha256"], label)


def extraction_identity():
    tree = ast.parse(inspect.getsource(scientific.verify_bundle))
    function = tree.body[0]
    loops = [node for node in ast.walk(function) if isinstance(node, ast.For)
        and ast.unparse(node.target) == "(product, interval)"
        and ast.unparse(node.iter) == "itertools.product(config['products'], config['interval_minutes'])"]
    reads = [node for node in function.body if isinstance(node, ast.FunctionDef) and node.name == "read"]
    scientific.require(len(loops) == len(reads) == 1, "exact serial cell/read extraction inventory")
    cell, read = loops[0], reads[0]
    digest = lambda node: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    return cell, read, dict(method="unchanged AST extraction; only cell scheduling and global close are separated",
        serial_source=scientific.record(Path(scientific.__file__)),
        cell_body_ast_sha256=digest(ast.Module(body=cell.body, type_ignores=[])),
        read_closure_ast_sha256=digest(read), cell_body_lines=[cell.lineno + 1, cell.end_lineno],
        read_closure_lines=[read.lineno, read.end_lineno], scientific_expressions_modified=0)


@lru_cache(maxsize=1)
def _cell_checker():
    cell, read, _ = extraction_identity()
    # Initialization/return are orchestration only. The read closure and entire
    # scientific cell body, including all inventories, are copied verbatim AST.
    wrapper = ast.parse("""def verify_development_cell(stage, config, records, phase_manifest, current, bychoice, product, interval):
    checks=[]
    consumed=[]
    populations={}
    grid_rows=[]
    neighbor_rows=[]
""").body[0]
    wrapper.body.append(copy.deepcopy(read))
    wrapper.body.extend(copy.deepcopy(cell.body))
    wrapper.body.extend(ast.parse("return dict(product=product, interval_minutes=interval, checks=checks, consumed=consumed, grid_rows=grid_rows, neighbor_rows=neighbor_rows)").body)
    tree = ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[]))
    namespace = scientific.__dict__.copy()
    exec(compile(tree, str(Path(scientific.__file__)), "exec"), namespace)
    return namespace["verify_development_cell"]


def _worker(payload):
    assert_pins(payload["source_pins"])
    started = perf_counter()
    result = _cell_checker()(Path(payload["stage"]), payload["config"], payload["records"], payload["phase_manifest"],
        "development", payload["bychoice"], payload["product"], payload["interval_minutes"])
    assert_pins(payload["source_pins"])
    result["seconds"] = perf_counter() - started
    return result


def collect_cells(results, expected):
    actual = [(r["product"], int(r["interval_minutes"])) for r in results]
    scientific.require(len(actual) == len(set(actual)), "duplicate independent product/interval result")
    scientific.require(set(actual) == set(expected) and len(actual) == len(expected), "complete independent product/interval inventory")
    bycell = dict(zip(actual, results))
    return [bycell[key] for key in expected]


def verify_bundle(stage, phase="development", workers=3):
    """Verify all six development cells with three spawn workers, then close once.

    The same entry point permits workers=1 for serial-equivalence fixtures.
    Historical callers must freeze these executable sources before invocation.
    This function reads saved authorized evidence; it never calls a producer.
    """
    scientific.require(phase == "development", "parallel companion is development only")
    scientific.require(type(workers) is int and workers in (1, 3), "frozen development worker count is three; one is serial comparison")
    stage = Path(stage).resolve()
    started = perf_counter()
    sources = [scientific.record(path) for path in executable_sources()]
    cell, read, extraction = extraction_identity()
    config = json.loads((stage / "config.json").read_text())
    recovery_pins = scientific.recovery_dependency_pins(stage, config)
    consumed = [scientific.record(stage / name) for name in ("config.json", "protocol.md", "inputs.lock.json", "baseline.lock.json", "mapped.manifest.json")] + recovery_pins
    acceptance_path = stage / "acceptance-development.manifest.json"
    phase_path = stage / "stage3-development.manifest.json"
    acceptance = json.loads(acceptance_path.read_text())
    phase_manifest = json.loads(phase_path.read_text())
    records = acceptance["records"] + phase_manifest["records"]
    scientific.require(records, "requested phase retained ledger inventory absent")
    consumed.extend([scientific.record(acceptance_path), scientific.record(phase_path)])
    for table in phase_manifest["tables"]:
        path = stage / table["path"]
        scientific.require(path.stat().st_size == table["bytes"] and scientific.sha256(path) == table["sha256"], "saved numerical table bytes")
        consumed.append(scientific.record(path))
    choice_path = stage / "tables/S3-T13_development_nominees.csv"
    consumed.append(scientific.record(choice_path))
    _, choices = scientific.read_csv(choice_path)
    scientific.inventory(choices, list(scientific.CELL), itertools.product(config["products"], map(str, config["interval_minutes"]), config["touch_modes"]), "complete twelve-cell frozen choices")
    bychoice = {scientific._identity_tuple(row): row for row in choices}
    expected = list(itertools.product(config["products"], config["interval_minutes"]))
    scientific.require(len(expected) == len(set(expected)) == 6, "exact six development product/interval cells")
    payloads = [dict(stage=str(stage), config=config, records=records, phase_manifest=phase_manifest, bychoice=bychoice,
        product=product, interval_minutes=interval, source_pins=sources) for product, interval in expected]
    # All parent metadata/whole table pins are established before workers begin.
    assert_pins(consumed, "parallel verification input bytes changed before execution")
    if workers == 1:
        results = [_worker(payload) for payload in payloads]
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(_worker, payloads))
    results = collect_cells(results, expected)
    checks, grids, neighbors = [], [], []
    for result in results:
        checks.extend(result["checks"])
        consumed.extend(result["consumed"])
        grids.extend(result["grid_rows"])
        neighbors.extend(result["neighbor_rows"])
    # This is the original serial development global close, run exactly once.
    checks.append(scientific.reconcile_neighborhoods(grids, neighbors))
    scientific.require(len(grids) == 2688, "exact2688 scientific development grid cells")
    assert_pins(consumed, "input bytes changed during independent verification")
    assert_pins(sources, "independent checker source changed during execution")
    return dict(schema_version="study21.stage3-independent/v1", status="passed", phase="development", checks=checks,
        **scientific.portable_pins(stage, consumed), pins=sources,
        scope="Unchanged independent development full causal states, carried identities, all authorized scalar paths/masks, complete table inventories, selection, neighborhoods/frontiers and exact byte checks; six cells scheduled in parallel.",
        parallel_orchestration=dict(workers=workers, cells=[dict(product=r["product"], interval_minutes=r["interval_minutes"], seconds=r["seconds"]) for r in results],
            seconds=perf_counter()-started, extraction=extraction, scientific_expressions_modified=0, checks_skipped=0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute-reviewed", action="store_true")
    args = parser.parse_args()
    if not args.execute_reviewed:
        parser.error("Historical verification requires the explicit reviewed execution flag")
    if args.output.exists():
        raise ValueError("independent parallel receipt overwrite refused")
    from .stage3_execution import assert_frozen
    workspace = Path(__file__).resolve().parents[3]
    assert_frozen(args.stage, workspace)
    before = args.output.with_name(args.output.stem + "-before.json")
    with before.open("x") as stream:
        json.dump(dict(captured_at_utc=datetime.now(timezone.utc).isoformat(), source_identities=[scientific.record(p) for p in executable_sources()],
            stage=str(args.stage.resolve()), phase="development", workers=3), stream, indent=2)
    result = verify_bundle(args.stage)
    assert_frozen(args.stage, workspace)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
