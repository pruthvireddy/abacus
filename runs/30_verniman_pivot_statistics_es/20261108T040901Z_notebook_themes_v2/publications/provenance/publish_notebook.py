"""Export explicitly selected executed notebook insights as saved Narada reports.

The exporter performs no analysis and does not execute notebook HTML or Python.
Only narrative, structured scalar table cells and exact cached PNG bytes cross
the public publication boundary. Execution/provenance copies remain private.
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

_SPEC = importlib.util.spec_from_file_location("study30_notebook_v2", Path(__file__).with_name("notebook_v2.py"))
notebook = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(notebook)
ROOT = notebook.ROOT
STUDY = notebook.STUDY
MIME = notebook.MIME


def _regular(path):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_file():
        raise ValueError(f"Expected a regular non-symlink file: {path}")
    return path


def _locator(path):
    return Path(path).absolute().relative_to(ROOT).as_posix()


def _new_output(path):
    target = Path(path).absolute()
    if target.resolve() != target:
        raise ValueError("Export destination cannot traverse symlinks.")
    if not any(target.is_relative_to(base) and target != base for base in
               (ROOT / "work" / STUDY, ROOT / "reports" / "exports" / STUDY)):
        raise ValueError("Export into a new study work stage or presentation revision.")
    if target.exists():
        raise FileExistsError(f"Refusing existing notebook export: {target}")
    return target


def _relative(locator):
    if not isinstance(locator, str) or not locator or Path(locator).is_absolute() or any(p in ("", ".", "..") for p in locator.split("/")) or re.search(r"[\\:#?\x00-\x1f]", locator):
        raise ValueError("Retained locators must be bounded workspace-relative paths.")
    return locator


def plain_text(markdown, *, heading=False, finding=False):
    """Remove the notebook's presentation-only Markdown, retaining paragraphs."""
    value = "".join(markdown) if isinstance(markdown, list) else markdown
    if not isinstance(value, str):
        raise ValueError("Selected narrative must be text.")
    value = value.strip()
    if heading:
        value = re.sub(r"^#{1,6}\s+", "", value)
    if re.search(r"<[^>]*>|!\[|\]\(|```", value):
        raise ValueError("Selected narrative may not contain HTML, links, images or code blocks.")
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value, flags=re.S)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    if finding:
        value = re.sub(r"^Findings summary\.?\s*", "", value, flags=re.I)
    if re.search(r"/Users/|/private/|/home/|data/research/|work/30_verniman|\x1b", value):
        raise ValueError("Private paths or terminal output cannot enter public narrative.")
    return value.strip()


def _public_guard(value):
    """All selected public strings, including typed evidence cells, must be clean."""
    if isinstance(value, str):
        if re.search(r"/Users/|/private/|/home/|data/research/|work/30_verniman|\x1b", value.replace("\\", "/")):
            raise ValueError("Private paths or terminal output cannot enter public evidence.")
    elif isinstance(value, list):
        for item in value:
            _public_guard(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _public_guard(key)
            _public_guard(item)


def _record_pin(data, locator):
    return {"path": locator, "sha256": notebook.digest(data), "bytes": len(data)}


def _resolved_pin(pin):
    path = Path(pin["path"])
    path = path if path.is_absolute() else ROOT / path
    path = _regular(path)
    actual = notebook.file_pin(path, root=ROOT)
    if actual["sha256"] != pin.get("sha256") or actual["bytes"] != pin.get("bytes"):
        raise ValueError(f"Execution source/input no longer matches its receipt: {pin['path']}")
    return path


def _validated_execution(source_path, executed_path, receipt_path):
    source, executed, receipt = map(_regular, (source_path, executed_path, receipt_path))
    source_book = json.loads(source.read_bytes())
    executed_book = json.loads(executed.read_bytes())
    record = json.loads(receipt.read_bytes())
    notebook.validate_notebook(source_book)
    notebook.validate_notebook(executed_book, require_outputs=True)
    if record.get("schema_version") != "abacus.study30.notebook-execution/v2" or record.get("result") != "passed" or record.get("source_and_inputs_unchanged") is not True:
        raise ValueError("A passing fresh-kernel V2 execution receipt is required.")
    signature = notebook.authoring_signature(source_book)
    if not (signature == notebook.authoring_signature(executed_book) == record.get("source_authoring_signature") == record.get("executed_authoring_signature")):
        raise ValueError("Source has changed since this execution; rerun the notebook before export.")
    pin = notebook.file_pin(executed, root=ROOT)
    if any(pin[key] != record.get("output", {}).get(key) for key in ("sha256", "bytes")):
        raise ValueError("Executed notebook bytes differ from the execution receipt.")
    entries = record.get("source_and_inputs")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Execution receipt is missing source/input pins.")
    input_files = [_resolved_pin(pin) for pin in entries]
    lock_name = source_book["metadata"]["abacus"].get("input_lock")
    if not isinstance(lock_name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", lock_name):
        raise ValueError("Notebook metadata must name its active study input lock.")
    active_lock = _regular(ROOT / "studies" / STUDY / lock_name)
    environment = _regular(ROOT / "uv.lock")
    if active_lock not in input_files or environment not in input_files:
        raise ValueError("Execution must pin the exact active study input lock and workspace uv.lock.")
    lock = json.loads(active_lock.read_bytes())
    if lock.get("environment_lock_sha256") != notebook.digest(environment.read_bytes()):
        raise ValueError("The active notebook lock does not match the pinned Python environment.")
    artifacts = lock.get("artifacts")
    if isinstance(artifacts, dict):
        artifacts = list(artifacts.values())
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("The active notebook input lock must declare its source artifacts.")
    publication_root = None
    for artifact in artifacts:
        root_kind = artifact.get("root", "workspace")
        if root_kind == "workspace":
            storage = ROOT
        elif root_kind == "publication":
            if publication_root is None:
                from abacus_bhishma.paths import load_workspace_paths
                publication_root = load_workspace_paths(ROOT).publication_root
            storage = publication_root
        else:
            raise ValueError("Unsupported locked artifact storage root.")
        locator = _relative(artifact.get("path"))
        path = (storage / locator).resolve(strict=True)
        if not path.is_relative_to(storage.resolve()) or path not in input_files:
            raise ValueError(f"Execution receipt is missing locked artifact: {locator}")
        if notebook.digest(path.read_bytes()) != artifact.get("sha256"):
            raise ValueError(f"Locked artifact does not match the notebook input declaration: {locator}")
    return source_book, executed_book, record, input_files


def prepare_export(source_path, *, executed_path, receipt_path, output_path, run_id,
                   publication_suffix="20261108-notebook-v2", published_at=None,
                   retained_root=None, retained_stage=None, analysis_verification_path=None):
    destination = _new_output(output_path)
    source, executed, receipt = map(_regular, (source_path, executed_path, receipt_path))
    source_book, book, execution, inputs = _validated_execution(source, executed, receipt)
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", run_id):
        raise ValueError("An explicit safe source run ID is required.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", publication_suffix):
        raise ValueError("Publication suffix must be lowercase hyphenated text.")
    retained = _relative(retained_root or _locator(destination))
    if retained_root is not None and not (retained.startswith(f"runs/{STUDY}/{run_id}/") or retained.startswith(f"reports/exports/{STUDY}/{run_id}/")):
        raise ValueError("Retained export attribution must match this study and run.")
    created = published_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created):
        raise ValueError("Use a UTC publication timestamp without fractional seconds.")
    stage_projection = None
    if retained_stage is not None:
        stage_projection = _relative(retained_stage)
        if stage_projection != f"runs/{STUDY}/{run_id}":
            raise ValueError("Retained stage must be the exact selected study/run locator.")
    meta = book["metadata"]["abacus"]
    groups = notebook.insight_groups(book)
    if analysis_verification_path is None:
        raise ValueError("Export requires the executed notebook's numerical reconciliation receipt.")
    numerical_path = _regular(analysis_verification_path)
    numerical = json.loads(numerical_path.read_bytes())
    checks = numerical.get("checks")
    if (numerical.get("result") != "passed" or numerical.get("publication_run_id") != run_id
            or numerical.get("source_run_id") != meta.get("source_run_id")
            or not isinstance(checks, list) or not checks
            or any(c.get("passed") is not True or c.get("insight_id") not in groups for c in checks)
            or {c["insight_id"] for c in checks} != set(groups)
            or numerical.get("insight_coverage") != meta["insight_order"]):
        raise ValueError("Numerical reconciliation must pass and cover every selected insight for this run.")
    files = {}
    # One private source copy per export, shared by six publication manifests.
    snapshots = {"executed.ipynb": executed.read_bytes(), "execution.json": receipt.read_bytes(),
                 "authoring.ipynb": inputs[0].read_bytes(),
                 "analysis-verification.json": numerical_path.read_bytes(),
                 "notebook_v2.py": Path(notebook.__file__).read_bytes(),
                 "publish_notebook.py": Path(__file__).read_bytes()}
    for pin_path in inputs:
        if pin_path.name in (meta["input_lock"], "uv.lock"):
            if pin_path.name in snapshots and snapshots[pin_path.name] != pin_path.read_bytes():
                raise ValueError("Conflicting frozen provenance snapshots.")
            snapshots[pin_path.name] = pin_path.read_bytes()
    for name, data in snapshots.items():
        files[f"provenance/{name}"] = data
    source_artifacts = [_record_pin(data, f"{retained}/provenance/{name}") for name, data in snapshots.items()]
    publications = []
    for theme in meta["themes"]:
        publication_id = f"verniman-es-{theme['id']}-{publication_suffix}"
        notebook.text_bound(publication_id, 80, "Publication ID")
        report = {"schemaVersion": "1.1", "presentation": "research-paper", "id": publication_id,
                  "title": plain_text(theme["title"]), "summary": plain_text(theme["question"]),
                  "publishedAt": created, "source": {"producer": "sahadeva", "runId": run_id},
                  "sections": [], "notes": copy.deepcopy(meta.get("publication_notes", []))}
        for note in report["notes"]:
            if plain_text(note) != note:
                raise ValueError("Publication notes must already be bounded plain text.")
        transfers = []
        for identity in theme["insight_ids"]:
            group = groups[identity]
            cells = {role: entries[0][1] for role, entries in group["roles"].items()}
            heading = plain_text(notebook.source_text(cells["heading"]), heading=True)
            description = plain_text(notebook.source_text(cells["description"]))
            original_finding = notebook.rich_values(cells["findings"], "text/markdown")[0]
            finding = plain_text(original_finding, finding=True)
            notebook.text_bound(heading, 160, "Insight heading")
            notebook.text_bound(description, 1000, "Insight description")
            notebook.text_bound(finding, 2000, "Insight findings")
            evidence = notebook.validate_evidence(cells["evidence"], group["kind"])
            section = {"id": identity, "title": heading, "description": description, "finding": finding}
            transfer = {"insight_id": identity, "theme_id": theme["id"],
                        "cells": {role: [c["id"] for _, c in entries] for role, entries in group["roles"].items()},
                        "source": evidence.get("source", {}),
                        "text": {"title": heading, "description": description, "finding": finding},
                        "text_operation": "Remove heading/strong/code Markdown delimiters and the renderer-owned Findings summary label; preserve wording and paragraphs.",
                        "source_findings_sha256": notebook.digest(notebook.json_bytes(original_finding))}
            if evidence["kind"] == "table":
                columns = []
                for column in evidence["columns"]:
                    selected = {key: column[key] for key in ("key", "label", "unit", "precision") if key in column}
                    fmt = column.get("format", "text")
                    if fmt != "text":
                        selected["format"] = "number" if fmt == "integer" else fmt
                    if fmt == "integer":
                        selected["precision"] = 0
                    columns.append(selected)
                section.update(kind="table", columns=columns, rows=copy.deepcopy(evidence["rows"]))
                if evidence.get("notes"):
                    section["notes"] = copy.deepcopy(evidence["notes"])
                transfer["structured_table_sha256"] = notebook.digest(notebook.json_bytes({"columns": section["columns"], "rows": section["rows"], "notes": section.get("notes", [])}))
            else:
                encoded = notebook.rich_values(cells["evidence"], "image/png")[0]
                data = base64.b64decode("".join(encoded) if isinstance(encoded, list) else encoded, validate=True)
                path = f"figures/{identity}.png"
                files[f"{publication_id}/{path}"] = data
                section.update(kind="figure", path=path, alt=evidence["alt"], caption=evidence["caption"])
                transfer["figure"] = {"path": path, "sha256": notebook.digest(data), "operation": "Exact executed PNG bytes; no redraw or image modification."}
            report["sections"].append(section)
            transfers.append(transfer)
        _public_guard(report)
        report_path = f"{publication_id}/publication.json"
        source_map = {"schema_version": "abacus.study30.notebook-web-transfer/v2", "study_id": STUDY,
                      "source_run_id": run_id, "upstream_source_run_id": meta.get("source_run_id"),
                      "publication_id": publication_id, "theme_id": theme["id"],
                      "authoring_signature": notebook.authoring_signature(source_book),
                      "executed_notebook_sha256": notebook.digest(executed.read_bytes()),
                      "execution_receipt_sha256": notebook.digest(receipt.read_bytes()),
                      "analysis_verification_sha256": notebook.digest(numerical_path.read_bytes()),
                      "retained_stage": stage_projection, "insights": transfers,
                      "public_selection": "Only selected narrative, structured scalar tables and exact PNG outputs. Code and private cell output are omitted."}
        files[report_path] = notebook.json_bytes(report)
        files[f"{publication_id}/source-map.json"] = notebook.json_bytes(source_map)
        verification = {"schema_version": "abacus.study30.notebook-publication-transfer/v2", "result": "passed",
                        "study_id": STUDY, "source_run_id": run_id, "publication_id": publication_id,
                        "checks": [{"name": "Passing fresh-kernel execution and unchanged pinned inputs", "passed": True},
                                   {"name": "Passing numerical reconciliation covers every selected insight", "passed": True},
                                   {"name": "Current authoring signature equals verified executed notebook", "passed": True},
                                   {"name": "Explicit theme/cell selection and bounded scalar table transfer", "passed": True},
                                   {"name": "Exact saved PNG byte transfer", "passed": True}],
                        "limitation": "Notebook-to-publication transfer verification; numerical research checks and hosted/browser checks are separate."}
        files[f"{publication_id}/publication-verification.json"] = notebook.json_bytes(verification)
        outputs = [_record_pin(data, f"{retained}/{name}") for name, data in files.items() if name.startswith(publication_id + "/")]
        manifest = {"study_id": STUDY, "source_run_id": run_id, "publication_id": publication_id,
                    "created_at_utc": created, "source_artifacts": source_artifacts, "outputs": outputs,
                    "change": "Render the selected executed notebook theme in the Research paper design; export performs no analysis.",
                    "renderer": {"producer": "publish_notebook.py", "version": "2", "command": "Explicit recorded exporter arguments are retained in notebook-export.json."}}
        files[f"{publication_id}/publication-manifest.json"] = notebook.json_bytes(manifest)
        publications.append({"theme_id": theme["id"], "title": theme["title"], "publication_id": publication_id,
                             "source_run_id": run_id, "insights": len(theme["insight_ids"]),
                             "path": f"{publication_id}/publication.json"})
    index = {"schema_version": "abacus.study30.notebook-export/v2", "result": "prepared", "study_id": STUDY,
             "source_run_id": run_id, "upstream_source_run_id": meta.get("source_run_id"), "created_at_utc": created,
             "source_authoring_signature": notebook.authoring_signature(source_book),
             "executed_notebook_sha256": notebook.digest(executed.read_bytes()),
             "retained_root": retained, "retained_stage": stage_projection, "publications": publications,
             "files": [_record_pin(data, name) for name, data in files.items()]}
    files["notebook-export.json"] = notebook.json_bytes(index)
    return destination, files, index


def export_notebook(source_path, **kwargs):
    destination, files, index = prepare_export(source_path, **kwargs)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    return index


def check_export(directory):
    root = Path(directory).absolute()
    if root.resolve() != root:
        raise ValueError("Export checks require regular paths without symlinks.")
    index = json.loads((root / "notebook-export.json").read_bytes())
    if index.get("schema_version") != "abacus.study30.notebook-export/v2":
        raise ValueError("Expected a notebook V2 export inventory.")
    for pin in index["files"]:
        relative = _relative(pin["path"])
        data = _regular(root / relative).read_bytes()
        if notebook.digest(data) != pin["sha256"] or len(data) != pin["bytes"]:
            raise ValueError(f"Export bytes changed: {relative}")
    expected = {pin["path"] for pin in index["files"]} | {"notebook-export.json"}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != expected:
        raise ValueError("Export directory contains unlisted or missing artifacts.")
    return {"result": "passed", "publications": len(index["publications"]), "files": len(index["files"]),
            "limitation": "Retained export integrity; no research execution or hosted verification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", nargs="?", type=Path)
    parser.add_argument("--executed", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--publication-suffix", default="20261108-notebook-v2")
    parser.add_argument("--published-at")
    parser.add_argument("--retained-root")
    parser.add_argument("--retained-stage")
    parser.add_argument("--analysis-verification", type=Path)
    parser.add_argument("--check", type=Path, metavar="EXPORT_DIRECTORY")
    args = parser.parse_args()
    if args.check:
        result = check_export(args.check)
    else:
        if not all((args.notebook, args.executed, args.receipt, args.output, args.run_id)):
            parser.error("Export requires notebook, --executed, --receipt, --output and --run-id")
        result = export_notebook(args.notebook, executed_path=args.executed, receipt_path=args.receipt,
                                 output_path=args.output, run_id=args.run_id, publication_suffix=args.publication_suffix,
                                 published_at=args.published_at, retained_root=args.retained_root, retained_stage=args.retained_stage,
                                 analysis_verification_path=args.analysis_verification)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
