"""Validate and execute the study-authored V1 notebook in a fresh IPython kernel.

This file contains execution and provenance plumbing only. Study calculations
and plots belong in the notebook's visible cells.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
STUDY = "30_verniman_pivot_statistics_es"
MAX_SOURCE_CHARACTERS = 6000
_KINDS = {"table", "line", "bar"}
_ROLES = {"heading", "description", "analysis", "findings", "evidence"}
_PACKED_SOURCE = re.compile(r"(?:b64decode|b64encode|data:image/|zlib\.decompress|lzma\.decompress|pickle\.loads|[A-Za-z0-9+/]{200,}={0,2})")


def _source(cell: dict) -> str:
    value = cell.get("source", "")
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(line, str) for line in value):
        return "".join(value)
    raise ValueError("Notebook source must be text or lines of text.")


def validate_notebook(notebook: dict, *, require_outputs: bool = False) -> dict:
    """Check the three insight groups and ordinary visible notebook cell source."""
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise ValueError("Expected a version-4 Jupyter notebook.")
    groups: dict[str, dict] = {}
    seen_ids: set[str] = set()
    longest = 0
    code_count = 0
    for index, cell in enumerate(notebook["cells"]):
        identity = cell.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity) or identity in seen_ids:
            raise ValueError("Notebook cell identities must be valid and unique.")
        seen_ids.add(identity)
        text = _source(cell)
        longest = max(longest, len(text))
        if len(text) > MAX_SOURCE_CHARACTERS:
            raise ValueError(f"Cell {identity} exceeds {MAX_SOURCE_CHARACTERS} source characters.")
        if _PACKED_SOURCE.search(text):
            raise ValueError(f"Cell {identity} contains an encoded or compressed payload in source.")
        if cell.get("cell_type") not in {"markdown", "code"}:
            raise ValueError("Only Markdown and Python code cells are supported in V1.")
        metadata = cell.get("metadata", {})
        if cell["cell_type"] == "code":
            code_count += 1
            if (metadata.get("collapsed") or metadata.get("jupyter", {}).get("source_hidden")
                    or set(metadata.get("tags", [])).intersection({"hide-input", "remove-input", "hide-cell", "remove-cell"})):
                raise ValueError(f"Code source must stay visible: {identity}.")
            if any(output.get("output_type") == "error" for output in cell.get("outputs", [])):
                raise ValueError(f"Notebook contains an error output: {identity}.")
            if require_outputs and type(cell.get("execution_count")) is not int:
                raise ValueError(f"Code cell has not executed: {identity}.")
        abacus = metadata.get("abacus", {})
        insight_id = abacus.get("insight_id")
        if insight_id is None:
            continue
        if not isinstance(insight_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", insight_id):
            raise ValueError("Insight IDs must be stable lowercase hyphenated text.")
        kind, role = abacus.get("kind"), abacus.get("role")
        if kind not in _KINDS or role not in _ROLES:
            raise ValueError(f"Insight {insight_id} has an unsupported kind or role.")
        group = groups.setdefault(insight_id, {"kind": kind, "roles": {}, "first_cell": index, "last_cell": index})
        if group["kind"] != kind:
            raise ValueError(f"Insight {insight_id} changes its declared evidence kind.")
        group["last_cell"] = index
        group["roles"].setdefault(role, []).append(index)
        if role in {"heading", "description"} and cell["cell_type"] != "markdown":
            raise ValueError(f"Insight {insight_id} needs a Markdown {role} cell.")
        if role in {"analysis", "evidence"} and cell["cell_type"] != "code":
            raise ValueError(f"Insight {insight_id} needs a visible Python {role} cell.")
        if require_outputs and role in {"findings", "evidence"} and cell["cell_type"] == "code":
            bundles = [output.get("data", {}) for output in cell.get("outputs", [])
                       if output.get("output_type") in {"display_data", "execute_result"}]
            expected = {"text/markdown", "text/html"} if role == "findings" or kind == "table" else {"image/png", "image/svg+xml", "image/jpeg", "image/webp"}
            if not any(set(bundle).intersection(expected) for bundle in bundles):
                raise ValueError(f"Insight {insight_id} lacks its executed {role} display.")
    if len(groups) != 3 or {group["kind"] for group in groups.values()} != _KINDS:
        raise ValueError("V1 requires exactly three insight groups: one table, one line and one bar.")
    previous_end = -1
    for insight_id, group in groups.items():
        roles = group["roles"]
        if set(roles) != _ROLES or any(len(roles[role]) != 1 for role in _ROLES - {"analysis"}):
            raise ValueError(f"Insight {insight_id} needs distinct heading, description, findings and evidence cells, plus analysis.")
        if not (roles["heading"][0] < roles["description"][0] < min(roles["analysis"])
                <= max(roles["analysis"]) < roles["findings"][0] < roles["evidence"][0]):
            raise ValueError(f"Insight {insight_id} cells are outside the declared reading/execution order.")
        if group["first_cell"] <= previous_end:
            raise ValueError("Insight groups must form separate sequential notebook sections.")
        previous_end = group["last_cell"]
    return {"insights": [{"id": identity, "kind": group["kind"]} for identity, group in groups.items()],
            "cells": len(notebook["cells"]), "code_cells": code_count,
            "largest_source_cell_characters": longest, "executed_outputs_required": require_outputs}


def _load_execution_tools():
    try:
        import nbformat
        from nbclient import NotebookClient
        from jupyter_client import KernelManager
        from jupyter_client.kernelspec import KernelSpecManager
    except ImportError as error:
        raise RuntimeError("Fresh-kernel execution requires nbformat, nbclient, jupyter_client and ipykernel in the selected environment.") from error
    return nbformat, NotebookClient, KernelManager, KernelSpecManager


def _new_stage_file(path: str | Path) -> Path:
    target = Path(path).absolute()
    if target.resolve() != target:
        raise ValueError("Execution destinations must be regular workspace paths without symlinks.")
    try:
        relative = target.relative_to(ROOT / "work" / STUDY)
    except ValueError as error:
        raise ValueError(f"Execution output must be staged under work/{STUDY}/.") from error
    if len(relative.parts) < 2:
        raise ValueError("Use an explicit stage directory beneath the study's work folder.")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite an existing execution artifact: {target}")
    return target


def _hash_file(path: Path) -> dict:
    data = path.read_bytes()
    try:
        locator = path.relative_to(ROOT).as_posix()
    except ValueError:
        locator = str(path)
    return {"path": locator, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def execute_notebook(source_path: str | Path, *, output_path: str | Path,
                     python_executable: str | Path | None = None, timeout: int = 1200,
                     input_paths=(), receipt_path: str | Path | None = None,
                     working_directory: str | Path | None = None) -> dict:
    """Execute a trusted source notebook, writing only new staged artifacts.

    A fresh, temporary kernelspec launches the explicit interpreter. Cell
    failures retain an incomplete staged notebook and failed receipt, then raise.
    The source notebook and completed run directories are never written here.
    """
    source = Path(source_path).resolve(strict=True)
    output = _new_stage_file(output_path)
    receipt = _new_stage_file(receipt_path if receipt_path is not None else output.with_suffix(".execution.json"))
    if output == source or receipt in {source, output}:
        raise ValueError("Source, executed output and receipt must be distinct files.")
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("Execution timeout must be a positive number of seconds.")
    notebook_json = json.loads(source.read_text(encoding="utf-8"))
    before_validation = validate_notebook(notebook_json)
    # Preserve a virtual environment's interpreter symlink: resolving it would
    # launch the base Python and lose the explicitly selected environment.
    interpreter = Path(python_executable or sys.executable).absolute()
    if not interpreter.is_file():
        raise FileNotFoundError(f"Selected Python interpreter does not exist: {interpreter}")
    cwd = Path(working_directory).resolve(strict=True) if working_directory is not None else source.parent
    if not cwd.is_dir():
        raise ValueError("Kernel working directory must be a directory.")
    selected = [source, *(Path(path).resolve(strict=True) for path in input_paths)]
    before = [_hash_file(path) for path in selected]
    environment_command = [str(interpreter), "-c", "import json,platform,sys; print(json.dumps({'executable':sys.executable,'version':sys.version,'platform':platform.platform()}))"]
    environment = subprocess.run(environment_command, check=True, text=True, capture_output=True)
    environment_info = json.loads(environment.stdout)
    nbformat, NotebookClient, KernelManager, KernelSpecManager = _load_execution_tools()
    notebook = nbformat.reads(source.read_text(encoding="utf-8"), as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    kernel_argv = [str(interpreter), "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    started = _now()
    failure = None
    validation = None
    with tempfile.TemporaryDirectory(prefix="abacus-study30-notebook-kernel-") as directory:
        spec_root = Path(directory)
        kernel_name = "abacus-study30-v1"
        spec = spec_root / kernel_name
        spec.mkdir()
        (spec / "kernel.json").write_text(json.dumps({"argv": kernel_argv, "display_name": "Abacus study30 V1", "language": "python"}), encoding="utf-8")
        manager = KernelManager(kernel_name=kernel_name, kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(spec_root)]))
        client = NotebookClient(notebook, km=manager, timeout=timeout, allow_errors=False,
                                resources={"metadata": {"path": str(cwd)}})
        try:
            client.execute(cwd=str(cwd))
            after = [_hash_file(path) for path in selected]
            if after != before:
                raise ValueError("Notebook source or declared inputs changed during execution.")
            validation = validate_notebook(notebook, require_outputs=True)
        except Exception as error:
            failure = error
        finally:
            # Passing an explicit manager leaves kernel ownership with this caller.
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    output_bytes = nbformat.writes(notebook).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(output_bytes)
    record = {"schema_version": "abacus.study30.notebook-execution/v1", "result": "failed" if failure else "passed",
              "started_at_utc": started, "finished_at_utc": _now(), "source_and_inputs": before,
              "source_and_inputs_unchanged": all(_hash_file(path) == pin for path, pin in zip(selected, before)),
              "output": _hash_file(output), "kernel": {"argv": kernel_argv, "environment": environment_info},
              "working_directory": str(cwd), "timeout_seconds": timeout, "process_argv": sys.argv,
              "environment_probe_command": environment_command, "source_validation": before_validation,
              "executed_validation": validation,
              "limitation": "Fresh-kernel notebook execution and declared artifact checks; no website or independent scientific revalidation."}
    if failure is not None:
        record["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if failure is not None:
        raise RuntimeError(f"Notebook execution failed; retained diagnostic notebook and receipt at {output.parent}") from failure
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Validate notebook structure without executing cells")
    check.add_argument("notebook", type=Path)
    check.add_argument("--executed", action="store_true", help="Require successful executed findings/evidence displays")
    execute = subparsers.add_parser("execute", help="Execute in a fresh kernel into a new explicit work stage")
    execute.add_argument("notebook", type=Path)
    execute.add_argument("--output", required=True, type=Path)
    execute.add_argument("--receipt", type=Path)
    execute.add_argument("--python", type=Path)
    execute.add_argument("--cwd", type=Path)
    execute.add_argument("--input", action="append", default=[], type=Path)
    execute.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    if args.command == "check":
        result = validate_notebook(json.loads(args.notebook.read_text(encoding="utf-8")), require_outputs=args.executed)
    else:
        result = execute_notebook(args.notebook, output_path=args.output, receipt_path=args.receipt,
                                  python_executable=args.python, working_directory=args.cwd,
                                  input_paths=args.input, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
