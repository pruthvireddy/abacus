"""Validate and execute the six-theme study notebook; no analytical methods live here."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
STUDY = "30_verniman_pivot_statistics_es"
SCHEMA = "abacus.study30.authored-notebook/v2"
MIME = "application/vnd.abacus.insight+json"
THEMES = {
    "opening-context": {"S15", "S17"},
    "crossing-activity": {"S01", "S02", "S03", "S05"},
    "breaks-confirmation": {"S06", "S07", "S08"},
    "after-cross": {"S09", "S10", "S11", "S13", "S18"},
    "vwap-cloud": {"S14", "S16"},
    "timing-stability": {"S04", "S12", "S19", "S20"},
}
ROLES = ("heading", "description", "analysis", "findings", "evidence")
_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_PACKED = re.compile(r"(?:b64decode|b64encode|data:image/|zlib\.decompress|lzma\.decompress|pickle\.loads|[A-Za-z0-9+/]{200,}={0,2})")


def source_text(cell):
    source = cell.get("source", "")
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(line, str) for line in source):
        return "".join(source)
    raise ValueError("Cell source must be text.")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_pin(path, *, root=None):
    path = Path(path).absolute()
    data = path.read_bytes()
    try:
        locator = path.relative_to(root or ROOT).as_posix()
    except ValueError:
        locator = str(path)
    return {"path": locator, "sha256": digest(data), "bytes": len(data)}


def authoring_signature(book):
    """Outputs/kernel-generated metadata are excluded; authored cells/metadata are bound."""
    content = {"abacus": book.get("metadata", {}).get("abacus", {}),
               "cells": [{"id": c.get("id"), "cell_type": c.get("cell_type"),
                          "source": source_text(c), "metadata": {k: v for k, v in c.get("metadata", {}).items()
                                                                if k not in ("execution", "ExecuteTime")}}
                         for c in book.get("cells", [])]}
    return digest(json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())


def text_bound(value, maximum, label):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be nonblank text of at most {maximum} characters.")
    return value


def rich_values(cell, mime):
    return [out["data"][mime] for out in cell.get("outputs", [])
            if out.get("output_type") in ("display_data", "execute_result")
            and mime in out.get("data", {})]


def validate_evidence(cell, declared_kind):
    descriptors = rich_values(cell, MIME)
    if len(descriptors) != 1 or not isinstance(descriptors[0], dict):
        raise ValueError("Evidence needs exactly one structured insight MIME descriptor.")
    evidence = descriptors[0]
    if declared_kind == "table":
        if evidence.get("kind") != "table" or not rich_values(cell, "text/html"):
            raise ValueError("Table evidence needs its structured table and visible HTML output.")
        columns, rows = evidence.get("columns"), evidence.get("rows")
        if not isinstance(columns, list) or not 1 <= len(columns) <= 12:
            raise ValueError("Table evidence requires one to twelve columns.")
        keys = []
        for column in columns:
            if not isinstance(column, dict) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", column.get("key", "")):
                raise ValueError("Invalid table column key.")
            keys.append(column["key"])
            text_bound(column.get("label"), 160, "Column label")
            if column.get("format", "text") not in ("text", "number", "integer", "percent"):
                raise ValueError("Unsupported table format.")
            if "precision" in column and (type(column["precision"]) is not int or not 0 <= column["precision"] <= 6):
                raise ValueError("Unsupported table precision.")
            if "unit" in column:
                text_bound(column["unit"], 40, "Column unit")
        if len(set(keys)) != len(keys):
            raise ValueError("Table column keys must be unique.")
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("Notebook insight tables are bounded at 100 rows.")
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(keys):
                raise ValueError("Every table row must have exactly the declared columns.")
            for value in row.values():
                if not (value is None or type(value) is bool or
                        (isinstance(value, str) and len(value) <= 1000) or
                        (type(value) in (int, float) and math.isfinite(value))):
                    raise ValueError("Table cells must preserve finite JSON scalar values.")
            for column in columns:
                value = row[column["key"]]
                fmt = column.get("format", "text")
                if fmt != "text" and value is not None and type(value) not in (int, float):
                    raise ValueError("Numeric-formatted columns require numeric or null values.")
                if fmt == "integer" and value is not None and value != int(value):
                    raise ValueError("Integer formatting cannot discard a saved fraction.")
        notes = evidence.get("notes", [])
        if not isinstance(notes, list) or len(notes) > 6:
            raise ValueError("Table notes must be a bounded list.")
        for note in notes:
            text_bound(note, 1000, "Table note")
    else:
        if evidence.get("kind") != "figure":
            raise ValueError("Chart evidence requires a figure descriptor.")
        text_bound(evidence.get("alt"), 500, "Figure alternative text")
        text_bound(evidence.get("caption"), 1000, "Figure caption")
        pngs = rich_values(cell, "image/png")
        if len(pngs) != 1:
            raise ValueError("Figure evidence requires exactly one saved PNG.")
        try:
            png = base64.b64decode("".join(pngs[0]) if isinstance(pngs[0], list) else pngs[0], validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("Figure PNG is not valid base64.") from error
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Figure evidence is not a PNG.")
    return evidence


def insight_groups(book):
    groups = {}
    for index, cell in enumerate(book["cells"]):
        meta = cell.get("metadata", {}).get("abacus", {})
        insight = meta.get("insight_id")
        if insight is None:
            continue
        group = groups.setdefault(insight, {"id": insight, "theme_id": meta.get("theme_id"),
                                            "kind": meta.get("kind"), "roles": {}})
        if group["theme_id"] != meta.get("theme_id") or group["kind"] != meta.get("kind"):
            raise ValueError("An insight cannot change theme or evidence kind between cells.")
        group["roles"].setdefault(meta.get("role"), []).append((index, cell))
    return groups


def validate_notebook(book, *, require_outputs=False):
    if book.get("nbformat") != 4 or not isinstance(book.get("cells"), list):
        raise ValueError("Expected a version-4 notebook.")
    meta = book.get("metadata", {}).get("abacus", {})
    if meta.get("schema_version") != SCHEMA or meta.get("study_id") != STUDY:
        raise ValueError("Expected study30 authored notebook V2 metadata.")
    themes = meta.get("themes")
    if not isinstance(themes, list) or [t.get("id") for t in themes] != list(THEMES):
        raise ValueError("V2 requires the six approved themes in their declared reading order.")
    declared = []
    for theme in themes:
        text_bound(theme.get("title"), 160, "Theme title")
        text_bound(theme.get("question"), 800, "Theme question")
        ids = theme.get("insight_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or not _ID.fullmatch(i) for i in ids):
            raise ValueError("Every theme must declare its ordered insight IDs.")
        declared.extend(ids)
    if len(declared) != len(set(declared)) or meta.get("insight_order") != declared:
        raise ValueError("Theme membership and notebook insight order must be unique and identical.")
    notes = meta.get("publication_notes", [])
    if not isinstance(notes, list) or len(notes) > 20:
        raise ValueError("Publication notes must be a bounded list.")
    for note in notes:
        text_bound(note, 1000, "Publication note")
    seen, code_count, largest = set(), 0, 0
    for cell in book["cells"]:
        identity = cell.get("id", "")
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity) or identity in seen:
            raise ValueError("Cell IDs must be valid and unique.")
        seen.add(identity)
        text = source_text(cell)
        largest = max(largest, len(text))
        if len(text) > 6000 or _PACKED.search(text):
            raise ValueError("Keep notebook source ordinary visible code, without oversized or packed cells.")
        if cell.get("cell_type") not in ("markdown", "code"):
            raise ValueError("Only Markdown and Python code cells are supported.")
        if cell["cell_type"] == "code":
            code_count += 1
            cm = cell.get("metadata", {})
            if cm.get("collapsed") or cm.get("jupyter", {}).get("source_hidden") or set(cm.get("tags", [])).intersection({"hide-input", "remove-input", "hide-cell", "remove-cell"}):
                raise ValueError("Notebook code must remain visible to its author.")
            if any(o.get("output_type") == "error" for o in cell.get("outputs", [])):
                raise ValueError("Notebook contains an error output.")
            if require_outputs and type(cell.get("execution_count")) is not int:
                raise ValueError("Every code cell must have executed.")
    groups = insight_groups(book)
    if list(groups) != declared:
        raise ValueError("Notebook insight cells must match declared theme order exactly.")
    primary = []
    previous_end = -1
    for theme in themes:
        for identity in theme["insight_ids"]:
            group = groups[identity]
            if group["theme_id"] != theme["id"] or group["kind"] not in ("table", "line", "bar"):
                raise ValueError("Insight theme/kind does not match its declaration.")
            roles = group["roles"]
            if set(roles) != set(ROLES) or any(len(roles[r]) != 1 for r in ROLES if r != "analysis"):
                raise ValueError("Insights need heading, description, analysis, findings and evidence cells.")
            indices = [roles[r][0][0] for r in ROLES]
            if not (indices[0] < indices[1] < min(i for i, _ in roles["analysis"])
                    <= max(i for i, _ in roles["analysis"]) < indices[3] < indices[4]) or indices[0] <= previous_end:
                raise ValueError("Insight cells must remain separate and in reading/execution order.")
            previous_end = indices[4]
            for role, cells in roles.items():
                for _, cell in cells:
                    cm = cell["metadata"]["abacus"]
                    if cm.get("publish") is not (role != "analysis"):
                        raise ValueError("Insight publication selection must be explicit; analysis stays private.")
                    if (role in ("heading", "description")) != (cell["cell_type"] == "markdown"):
                        raise ValueError("Heading/description are Markdown; analysis/findings/evidence are Python.")
            heading_meta = roles["heading"][0][1]["metadata"]["abacus"]
            measure = heading_meta.get("primary_measure_id")
            if measure is not None:
                if measure not in THEMES[theme["id"]]:
                    raise ValueError("Primary measure is assigned to the wrong theme.")
                primary.append(measure)
            if require_outputs:
                findings = rich_values(roles["findings"][0][1], "text/markdown")
                if len(findings) != 1:
                    raise ValueError("Findings require exactly one executed Markdown output.")
                validate_evidence(roles["evidence"][0][1], group["kind"])
    if len(primary) != 20 or set(primary) != set().union(*THEMES.values()):
        raise ValueError("Every S01–S20 primary measure must appear exactly once.")
    return {"themes": [{"id": t["id"], "insights": len(t["insight_ids"])} for t in themes],
            "insights": len(groups), "primary_measures": len(primary), "cells": len(book["cells"]),
            "code_cells": code_count, "largest_source_cell_characters": largest,
            "executed_outputs_required": require_outputs}


def _new_stage_file(path):
    target = Path(path).absolute()
    if target.resolve() != target:
        raise ValueError("Execution destinations must be regular paths without symlinks.")
    try:
        relative = target.relative_to(ROOT / "work" / STUDY)
    except ValueError as error:
        raise ValueError("Execution artifacts must be staged under this study's work folder.") from error
    if len(relative.parts) < 2:
        raise ValueError("Use an explicit stage directory.")
    if target.exists():
        raise FileExistsError(f"Refusing existing execution artifact: {target}")
    return target


def _load_execution_tools():
    try:
        import nbformat
        from nbclient import NotebookClient
        from jupyter_client import KernelManager
        from jupyter_client.kernelspec import KernelSpecManager
    except ImportError as error:
        raise RuntimeError("Install the locked notebooks dependency group in the selected workspace environment.") from error
    return nbformat, NotebookClient, KernelManager, KernelSpecManager


def execute_notebook(source_path, *, output_path, python_executable=None, timeout=1200,
                     input_paths=(), receipt_path=None, working_directory=None):
    source = Path(source_path).resolve(strict=True)
    output = _new_stage_file(output_path)
    receipt = _new_stage_file(receipt_path or output.with_suffix(".execution.json"))
    if source == output or receipt in (source, output):
        raise ValueError("Source, output and receipt must be distinct files.")
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("Execution timeout must be a positive number of seconds.")
    book = json.loads(source.read_text())
    validation = validate_notebook(book)
    signature = authoring_signature(book)
    inputs = [source, *(Path(p).resolve(strict=True) for p in input_paths)]
    before = [file_pin(p) for p in inputs]
    interpreter = Path(python_executable or sys.executable).absolute()
    if not interpreter.is_file():
        raise FileNotFoundError(interpreter)
    cwd = Path(working_directory or ROOT).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("Kernel working directory must be a directory.")
    probe = [str(interpreter), "-c", "import json,platform,sys; print(json.dumps({'executable':sys.executable,'version':sys.version,'platform':platform.platform()}))"]
    environment = json.loads(subprocess.run(probe, check=True, text=True, capture_output=True).stdout)
    nbformat, NotebookClient, KernelManager, KernelSpecManager = _load_execution_tools()
    notebook = nbformat.from_dict(book)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs, cell.execution_count = [], None
    argv = [str(interpreter), "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    started = datetime.now(timezone.utc).isoformat()
    failure, completed_validation = None, None
    with tempfile.TemporaryDirectory(prefix="abacus-study30-v2-kernel-") as directory:
        spec = Path(directory) / "abacus-study30-v2"
        spec.mkdir()
        (spec / "kernel.json").write_bytes(json_bytes({"argv": argv, "display_name": "Abacus study30 V2", "language": "python"}))
        manager = KernelManager(kernel_name=spec.name, kernel_spec_manager=KernelSpecManager(kernel_dirs=[directory]))
        client = NotebookClient(notebook, km=manager, timeout=timeout, allow_errors=False,
                                resources={"metadata": {"path": str(cwd)}})
        try:
            client.execute(cwd=str(cwd))
            if before != [file_pin(p) for p in inputs]:
                raise ValueError("Source or declared inputs changed during execution.")
            if authoring_signature(notebook) != signature:
                raise ValueError("Execution changed authored notebook cells or metadata.")
            completed_validation = validate_notebook(notebook, require_outputs=True)
        except Exception as error:
            failure = error
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
            if client.kc is not None:
                client.kc.stop_channels()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(nbformat.writes(notebook).encode())
    record = {"schema_version": "abacus.study30.notebook-execution/v2", "result": "failed" if failure else "passed",
              "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_and_inputs": before, "source_and_inputs_unchanged": before == [file_pin(p) for p in inputs],
              "source_authoring_signature": signature, "executed_authoring_signature": authoring_signature(notebook),
              "output": file_pin(output), "kernel": {"argv": argv, "environment": environment},
              "working_directory": str(cwd), "process_argv": sys.argv, "source_validation": validation,
              "executed_validation": completed_validation,
              "limitation": "Fresh-kernel execution and pinned-byte checks; scientific numerical checks are separately recorded."}
    if failure:
        record["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("xb") as stream:
        stream.write(json_bytes(record))
    if failure:
        raise RuntimeError(f"Notebook execution failed; diagnostics retained in {output.parent}") from failure
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("notebook", type=Path)
    check.add_argument("--executed", action="store_true")
    execute = commands.add_parser("execute")
    execute.add_argument("notebook", type=Path)
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--receipt", type=Path)
    execute.add_argument("--python", type=Path)
    execute.add_argument("--cwd", type=Path)
    execute.add_argument("--input", action="append", type=Path, default=[])
    execute.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    if args.command == "check":
        result = validate_notebook(json.loads(args.notebook.read_text()), require_outputs=args.executed)
    else:
        result = execute_notebook(args.notebook, output_path=args.output, receipt_path=args.receipt,
                                  python_executable=args.python, working_directory=args.cwd,
                                  input_paths=args.input, timeout=args.timeout)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
