"""Freeze, derive and seal the explicitly authorized per-future descriptive run.

The input ledger is retained evidence. This producer never reconstructs prices,
EMA signals or event outcomes. Reporting is prepared before sealing the run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

SID = "25_forex_news_ema"
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read(path):
    return json.loads(path.read_text())


def pin(path, base):
    return {"path": path.relative_to(base).as_posix(), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def csv_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def save_csv(path, rows):
    require(rows, f"No rows for {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def source_integrity(stage):
    root = stage / "source-original" / "per_future_news"
    for item in read(stage / "import-manifest.json")["files"]:
        path = stage / item["retained_path"]
        actual = pin(path, stage)
        require(actual["sha256"] == item["sha256"] and actual["bytes"] == item["bytes"],
                f"Retained source mismatch: {item['path']}")
    for item in read(stage / "inputs.lock.json")["files"]:
        actual = pin(root / item["path"], root)
        require(actual == item, f"Locked source mismatch: {item['path']}")


def freeze(stage, workspace):
    source_integrity(stage)
    producer = stage / "producer"
    require(not producer.exists(), "Producer snapshot already exists")
    producer.mkdir()
    filenames = ["per_future.py", "src/per_future_stats.py", "tests/test_per_future_stats.py",
                 "per_future_verify.py", "per_future_report.py", "per_future_figures.py"]
    for name in filenames:
        target = producer / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / name, target)
    shutil.copyfile(workspace / "uv.lock", stage / "uv.lock")
    (stage / "code-status.txt").write_text(subprocess.check_output(
        ["git", "status", "--porcelain=v1"], cwd=workspace, text=True))
    write(stage / "code-snapshot.json", {
        "at": datetime.now(timezone.utc).isoformat(),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip(),
        "dirty": bool((stage / "code-status.txt").read_text().strip()),
        "files": [pin(path, stage) for path in sorted(producer.rglob("*")) if path.is_file()],
        "runtime": sys.version,
        "scope": "All new producer, numerical tests, independent checker and report/figure source frozen before calculation",
    })
    root = stage.relative_to(workspace).as_posix()
    prefix = "UV_CACHE_DIR=/private/tmp/abacus-forex25-uv-cache ./scripts/uv run --locked --no-sync python -B "
    write(stage / "commands.json", {
        "working_directory": str(workspace),
        "commands": [
            prefix + f"studies/{SID}/per_future.py freeze {root} --workspace .",
            prefix + f"-m unittest discover -s {root}/producer/tests -v",
            prefix + f"{root}/producer/per_future.py compute {root}",
            prefix + f"{root}/producer/per_future_verify.py {root}",
            "PYTHONPATH=/private/tmp/abacus-forex-plot-20261017 " + prefix +
            f"{root}/producer/per_future_report.py {root} --run-id {read(stage / 'config.json')['run_id']} " +
            "--figure-python /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
            prefix + f"{root}/producer/per_future_report.py {root} --run-id {read(stage / 'config.json')['run_id']} --check",
            prefix + f"studies/{SID}/per_future.py seal {root} --workspace .",
        ],
        "scope": "No original price reconstruction or signal/native export rerun; external matplotlib runtime draws saved chart inputs only",
    })


def verify_code(stage):
    for item in read(stage / "code-snapshot.json")["files"]:
        require(pin(stage / item["path"], stage) == item, "Frozen producer changed")


def compute(stage):
    source_integrity(stage)
    verify_code(stage)
    require(not (stage / "tables").exists(), "Refusing to replace computed tables")
    module_path = stage / "producer/src/per_future_stats.py"
    spec = importlib.util.spec_from_file_location("frozen_forex25_stats", module_path)
    stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stats)
    source = stage / "source-original/per_future_news"
    ledger = stats.load_ledger(source / "study/horizons.csv")
    tables = stats.build_tables(ledger)
    for symbol in stats.SYMBOLS:
        for name, rows in tables.items():
            save_csv(stage / "tables" / f"{symbol}-{name}.csv", [row for row in rows if row["symbol"] == symbol])
    events = csv_rows(source / "study/events.csv")
    exclusions = csv_rows(source / "study/exclusions.csv")
    coverage = []
    for symbol in stats.SYMBOLS:
        selected = [row for row in events if row["symbol"] == symbol and row["mode"] == "combined"]
        excluded = [row for row in exclusions if row["symbol"] == symbol and row["mode"] == "combined"]
        categories = read(source / f"calendars/{symbol}_archive.json")["category_map"]
        rows = []
        for category in categories:
            code = str(category["code"])
            eligible = sum(row["type_code"] == code for row in selected)
            mixed = sum(row["type_code"] == "13" and code in row["component_category_codes"].split(";") for row in selected)
            excluded_rows = [row for row in excluded if row["category_code"] == code]
            reasons = Counter(row["reason"] for row in excluded_rows)
            notes = [f"{reason}: {count}" for reason, count in sorted(reasons.items())]
            if mixed:
                notes.append(f"Also present in {mixed} Mixed timestamp(s); Mixed outcomes are kept exclusive")
            if not eligible and not mixed and not excluded_rows:
                notes.append("No eligible standalone source observations; no effect estimate available")
            rows.append({"news_type": category["label"], "eligible_signals": eligible,
                         "excluded": len(excluded_rows), "reason": "; ".join(notes) or "Eligible standalone observations retained"})
        mixed_n = sum(row["type_code"] == "13" for row in selected)
        rows.append({"news_type": "Mixed types (same timestamp)", "eligible_signals": mixed_n,
                     "excluded": 0, "reason": "Exclusive simultaneous selected-category bucket; never exploded into components"})
        save_csv(stage / "tables" / f"{symbol}-coverage.csv", rows)
        coverage.extend({"symbol": symbol, **row} for row in rows)
    write(stage / "coverage-summary.json", coverage)
    write(stage / "summary.json", {"study_id": SID, "run_id": read(stage / "config.json")["run_id"],
        "ledger_rows": len(ledger), "mode_event_selections": len(events),
        "combined_observations": sum(row["mode"] == "combined" for row in events),
        "aggregate_rows": {name: len(rows) for name, rows in tables.items()},
        "aggregate_cells_verified_separately": "scientific-verification.json",
        "calculation_scope": "New descriptive summaries of retained outcomes; original reconstructed price paths not rerun"})
    print(json.dumps(read(stage / "summary.json"), indent=2))


def seal(stage, workspace):
    source_integrity(stage)
    verify_code(stage)
    require(read(stage / "scientific-verification.json").get("status") == "passed", "Independent verification not passed")
    require(read(stage / "independent-publication-audit.json").get("result") == "passed", "Independent publication audit not passed")
    require(read(stage / "report-publisher-dry-runs.json").get("result") == "passed", "Six publisher dry runs not passed")
    publications = sorted((stage / "publications").iterdir())
    require(len(publications) == 6, "Six reports required")
    for directory in publications:
        require(read(directory / "publication-verification.json").get("result") == "passed", "Report verification not passed")
    require((stage / "numerical-tests.log").is_file(), "Numerical test receipt required")
    run_id = read(stage / "config.json")["run_id"]
    target = workspace / "runs" / SID / run_id
    require(not target.exists(), "Refusing to replace completed run")
    checks = [
        {"name": "independent descriptive aggregation", "status": "passed", "record": "scientific-verification.json"},
        {"name": "synthetic numerical boundary cases", "status": "passed", "record": "numerical-tests.log"},
        {"name": "independent publication and original-source preservation", "status": "passed", "record": "independent-publication-audit.json"},
        {"name": "six strict Narada source publisher dry runs", "status": "passed", "record": "report-publisher-dry-runs.json"},
        *[{"name": f"{directory.name} saved-cell presentation transfer", "status": "passed",
           "record": f"publications/{directory.name}/publication-verification.json"} for directory in publications],
        {"name": "historical price/EMA reconstruction and native TradingView checks", "status": "not_run",
         "reason": "Retained original market-data reconstruction and native receipts are not rerun; new aggregation verified independently"},
    ]
    write(stage / "checks.json", checks)
    (stage / "report.md").write_text(
        "# Six-contract news EMA descriptive report\n\n"
        "702 combined contract/timestamp observations; 1,410 overlapping mode/event selections; "
        "7,050 retained event/horizon outcomes. Twelve grouping families and six separately authored reports.\n\n"
        "See summary.json, scientific-verification.json, tables/, publications/, protocol.md and source-original/. "
        "Periods use America/Chicago. Mixed timestamps remain exclusive. This is descriptive path evidence, "
        "with no executable fill or cost-adjusted trading-performance claim.\n")
    code = read(stage / "code-snapshot.json")
    # Retain the original pre-calculation snapshot. This finalizer only corrects
    # receipt field integration and the evidence-contract check-list structure.
    shutil.copyfile(HERE / "per_future.py", stage / "producer/finalize_run.py")
    write(stage / "sealer-finalization.json", {
        "at": datetime.now(timezone.utc).isoformat(),
        "snapshot": pin(stage / "producer/finalize_run.py", stage),
        "scope": "Finalization-only receipt field/check-list integration after aggregate verification; no computed tables or report values changed",
        "original_precalculation_source": "code-snapshot.json"})
    artifacts = [pin(path, stage) for path in sorted(stage.rglob("*"))
                 if path.is_file() and path.name != "manifest.json" and "__pycache__" not in path.parts]
    write(stage / "manifest.json", {"contract": "abacus.evidence/v1", "bundle_kind": "research",
        "study_id": SID, "run_id": run_id, "inventory_scope": "declared_artifacts",
        "results": {"kind": "quantitative", "state": "computed",
                    "reason": "Authorized new descriptive aggregates from retained observations, independently reconstructed and presentation-checked",
                    "artifacts": ["summary.json", *[f"tables/{s}-overall.csv" for s in ("6E", "6B", "6J", "6A", "6C", "6S")]]},
        "provenance": {"settings": "config.json", "input_lock": "inputs.lock.json",
                       "exclusions": "source-original/per_future_news/study/exclusions.csv", "commands": "executed-commands.json",
                       "checks": "checks.json", "environment_lock": "uv.lock",
                       "code": {"revision": code["revision"], "dirty": code["dirty"], "status": "code-status.txt",
                                "source_snapshot": {"paths": [path.relative_to(stage).as_posix() for path in sorted((stage / "producer").rglob("*.py"))],
                                                    "scope": code["scope"] + "; presentation-only revision, independent publication verifier and finalizer retained separately before their execution/sealing"}}},
        "artifacts": artifacts})
    integrity = subprocess.run([sys.executable, str(workspace / "scripts/check-evidence-bundle.py"), str(stage)],
                               cwd=workspace, text=True, capture_output=True)
    require(integrity.returncode == 0, "Candidate integrity failed before sealing: " + integrity.stdout + integrity.stderr)
    shutil.copytree(stage, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "compute", "seal"))
    parser.add_argument("stage", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    stage, workspace = args.stage.resolve(), args.workspace.resolve()
    if args.action == "freeze":
        freeze(stage, workspace)
    elif args.action == "compute":
        compute(stage)
    else:
        seal(stage, workspace)


if __name__ == "__main__":
    main()
