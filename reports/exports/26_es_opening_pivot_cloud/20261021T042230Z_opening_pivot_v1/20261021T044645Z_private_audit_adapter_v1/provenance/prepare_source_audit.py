#!/usr/bin/env python3
"""Add a private audit-receipt adapter; preserve sealed/public bytes exactly.

This standard-library presentation utility never imports scientific code. The
sealed producer records `status: passed`; Narada's generic private audit expects
`result: passed`. A fresh private revision records that compatibility receipt,
copies only selected publication assets verbatim, and pins the original evidence.
It does not create, modify, publish or deploy any research/public content.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

STUDY = "26_es_opening_pivot_cloud"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def local(root, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute(), "Expected relative file locator")
    require(all(part not in ("", ".", "..") for part in name.split("/")), "Unsafe file locator")
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()), "File escapes root")
    current = root
    require(not current.is_symlink(), "Root symlink is forbidden")
    for part in Path(name).parts:
        current = current / part
        require(not current.is_symlink(), "Source symlink is forbidden")
    require(path.is_file(), "Missing regular file: " + str(path))
    return path


def same_cell(public, raw):
    if public is None:
        return raw == ""
    if isinstance(public, bool):
        return raw.lower() == str(public).lower()
    if isinstance(public, (int, float)):
        try:
            return Decimal(str(public)) == Decimal(raw)
        except InvalidOperation:
            return False
    return str(public) == raw


def equivalent_csv_cell(left, right):
    if left == right:
        return True
    try:
        return Decimal(left) == Decimal(right)
    except InvalidOperation:
        return False


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def verify_cells(run, publication, mapping):
    """Re-read pinned original cells without trusting map.value or old receipt."""
    require(mapping["publication_id"] == publication["id"], "Map publication differs")
    require(mapping["source_run_id"] == publication["source"]["runId"], "Map source run differs")
    pins = {}
    for source in mapping["sources"]:
        name = source["artifact"]
        require(name not in pins, "Duplicate source pin")
        require(digest(local(run, name)) == source["sha256"], "Source pin differs: " + name)
        pins[name] = source["sha256"]
    sections = {section["id"]: section for section in publication["sections"]}
    require(len(sections) == len(publication["sections"]), "Duplicate section")
    tables, bound = {}, set()
    for binding in mapping["bindings"]:
        name = binding["source_artifact"]
        require(name in pins, "Unpinned binding")
        if name not in tables:
            tables[name] = rows(local(run, name))
        raw = tables[name][binding["source_row"]][binding["source_column"]]
        public = sections[binding["section"]]["rows"][binding["row"]][binding["column"]]
        require(same_cell(public, raw) and same_cell(binding["value"], raw), "Actual saved table cell differs")
        identity = (binding["section"], binding["row"], binding["column"])
        require(identity not in bound, "Duplicate binding")
        bound.add(identity)
    for section in sections.values():
        if section["kind"] == "table":
            for index, row in enumerate(section["rows"]):
                require(all((section["id"], index, key) in bound for key in row), "Unmapped public cell")
    downloads = {item["path"]: item for item in publication.get("downloads", [])}
    require(len(downloads) == len(publication.get("downloads", [])), "Duplicate download")
    projections = mapping.get("download_projections", [])
    require(set(downloads) == {item["path"] for item in projections}, "Projection inventory differs")
    count = 0
    for projection in projections:
        download = downloads[projection["path"]]
        source = projection["source"]
        require(source == download["source"], "Download source differs")
        require(source["runId"] == publication["source"]["runId"], "Download run differs")
        require(source["artifact"] in pins and source["sha256"] == pins[source["artifact"]], "Download source is unpinned")
        require(projection["columns"] == download["columns"], "Download columns differ")
        path = local(run, projection["path"])
        require(digest(path) == download["sha256"], "Download byte hash differs")
        with path.open(newline="") as stream:
            require(next(csv.reader(stream)) == download["columns"], "Download header differs")
        actual, original = rows(path), rows(local(run, source["artifact"]))
        require(len(actual) == len(original) == download["rowCount"], "Download row count differs")
        for output_row, source_row in zip(actual, original):
            for column in download["columns"]:
                require(equivalent_csv_cell(output_row[column], source_row[column]), "Actual download source cell differs")
                count += 1
    return {"actual_saved_table_cells": len(bound), "actual_saved_download_cells": count,
            "source_artifacts": len(pins), "downloads": len(downloads)}


def verify_original(run):
    manifest = read_json(local(run, "manifest.json"))
    publication = read_json(local(run, "publication.json"))
    mapping = read_json(local(run, "source-map.json"))
    producer = read_json(local(run, "publication-verification.json"))
    independent = read_json(local(run, "independent-publication-verification.json"))
    require(manifest["study_id"] == STUDY and manifest["run_id"] == run.name, "Run attribution differs")
    require(publication["source"]["runId"] == run.name, "Report source run differs")
    require(producer["status"] == independent["status"] == "passed", "Original receipts did not pass")
    for receipt in (producer, independent):
        require(receipt["publication_id"] == publication["id"] and receipt["source_run_id"] == run.name, "Receipt attribution differs")
    require(producer["checks"] and all(check.get("status") == "passed" for check in producer["checks"]), "Producer checks did not pass")
    for artifact in independent["artifacts"]:
        require(digest(local(run, artifact["path"])) == artifact["sha256"], "Independent retained pin differs")
    checks = verify_cells(run, publication, mapping)
    require(checks == independent["checks"], "Fresh cell audit differs from sealed independent receipt")
    return publication, mapping, manifest, checks


def verify_adapter(workspace, destination):
    manifest = read_json(local(destination, "manifest.json"))
    receipt = read_json(local(destination, "verification.json"))
    for entry in manifest["source_artifacts"] + manifest["outputs"]:
        require(digest(local(workspace, entry["path"])) == entry["sha256"], "Adapter/source pin differs")
    run = workspace / receipt["source_run"]
    publication, mapping, _, checks = verify_original(run)
    require(read_json(local(destination, "publication.json")) == publication, "Copied parsed publication differs")
    require(read_json(local(destination, "source-map.json")) == mapping, "Copied parsed source map differs")
    for copied in receipt["copied_files"]:
        original, output = local(workspace, copied["source"]), local(destination, copied["output"])
        require(original.read_bytes() == output.read_bytes(), "Copied bytes differ")
    require(receipt["result"] == "passed" and checks == receipt["source_cell_checks"], "Adapter verification differs")
    return {"result": "passed", "publication_id": publication["id"], **checks,
            "copied_files": len(receipt["copied_files"]), "revision": destination.relative_to(workspace).as_posix()}


def prepare(workspace, run_relative, revision_id, command):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", revision_id), "Unsafe revision ID")
    require(re.fullmatch(r"runs/" + STUDY + r"/[A-Za-z0-9][A-Za-z0-9_-]*", run_relative), "Expected this study's sealed run")
    run = workspace / run_relative
    publication, mapping, run_manifest, checks = verify_original(run)
    destination = workspace / "reports/exports" / STUDY / run.name / revision_id
    require(not destination.exists(), "Revision already exists; refusing overwrite")
    selected = {"publication.json", "source-map.json"}
    selected.update(section["path"] for section in publication["sections"] if section["kind"] == "figure")
    selected.update(download["path"] for download in publication.get("downloads", []))
    evidence = {"manifest.json", "publication-manifest.json", "publication-verification.json", "independent-publication-verification.json"}
    source_names = selected | evidence | {item["artifact"] for item in mapping["sources"]}
    source_names.update(item["path"] for item in read_json(local(run, "independent-publication-verification.json"))["artifacts"])
    run_pins = {entry["path"]: entry["sha256"] for entry in run_manifest["artifacts"]}
    # Source bytes are checked against the sealed inventory before any new write.
    for name in source_names - {"manifest.json"}:
        require(name in run_pins and digest(local(run, name)) == run_pins[name], "Sealed run pin differs: " + name)
    copy_plan = [(name, name) for name in sorted(selected)]
    copy_plan += [(name, "provenance/original-" + name) for name in sorted(evidence)]
    payloads = [(name, output, local(run, name).read_bytes()) for name, output in copy_plan]
    producer = Path(__file__).resolve()
    source_artifacts = [{"path": (run / name).relative_to(workspace).as_posix(), "sha256": digest(local(run, name))} for name in sorted(source_names)]
    destination.mkdir(parents=True)
    copied = []
    for name, output, content in payloads:
        target = destination / output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        require(target.read_bytes() == content, "Copied byte verification failed")
        copied.append({"source": (run / name).relative_to(workspace).as_posix(), "output": output, "sha256": digest(target)})
    snapshot = destination / "provenance/prepare_source_audit.py"
    shutil.copyfile(producer, snapshot)
    receipt = {"schema_version": "es-opening-pivot-cloud-private-source-audit/v1", "result": "passed",
               "publication_id": publication["id"], "source_run_id": run.name, "study_id": STUDY,
               "source_run": run_relative, "source_cell_checks": checks, "copied_files": copied,
               "publication_sha256": digest(destination / "publication.json"),
               "source_map_sha256": digest(destination / "source-map.json"),
               "checks": [{"name": "Original sealed source pins and receipts verified", "passed": True},
                          {"name": "Actual saved table/download cells freshly verified", "passed": True},
                          {"name": "Selected report/map/assets copied byte-identically", "passed": True}],
               "scope": "Private receipt vocabulary compatibility only. Public publication ID, parsed content and exact source/asset bytes are unchanged; no scientific calculation or public publishing occurs."}
    write_json(destination / "verification.json", receipt)
    write_json(destination / "provenance/preparation.json", {"created_at": datetime.now(timezone.utc).isoformat(),
               "command": command, "python": sys.version, "producer_sha256": digest(producer),
               "scope": receipt["scope"]})
    (destination / "README.md").write_text(
        "# Private source-audit compatibility adapter\n\n"
        "Narada's generic private audit accepts `result: passed`; the immutable sealed producer receipt uses `status: passed`. "
        "This additive private revision supplies that vocabulary adapter after freshly verifying actual saved source cells, original receipt pins, "
        "and exact copied publication/map/asset bytes. Original receipts and run manifest are retained under `provenance/`.\n\n"
        "The existing immutable publication ID and all public report/asset bytes remain unchanged. "
        "This is a private provenance mapping target, not a new publication or a scientific rerun. "
        "No sealed run, generated public bundle or hosted state was modified.\n")
    outputs = [{"path": path.relative_to(workspace).as_posix(), "sha256": digest(path)}
               for path in sorted(destination.rglob("*")) if path.is_file()]
    write_json(destination / "manifest.json", {"schema_version": "es-opening-pivot-cloud-private-source-adapter/v1",
               "publication_id": publication["id"], "source_run_id": run.name, "study_id": STUDY,
               "revision_id": revision_id, "presentation_changes": "Private audit receipt vocabulary only; exact public publication and selected asset bytes preserved.",
               "source_artifacts": source_artifacts, "outputs": outputs})
    return verify_adapter(workspace, destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run")
    parser.add_argument("--revision-id")
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    workspace = args.workspace.resolve()
    if args.check:
        require(not args.run and not args.revision_id, "Use --check alone")
        destination = args.check if args.check.is_absolute() else workspace / args.check
        result = verify_adapter(workspace, destination)
    else:
        require(args.run and args.revision_id, "Specify --run and --revision-id")
        command = [sys.executable, *sys.argv]
        result = prepare(workspace, args.run, args.revision_id, command)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
