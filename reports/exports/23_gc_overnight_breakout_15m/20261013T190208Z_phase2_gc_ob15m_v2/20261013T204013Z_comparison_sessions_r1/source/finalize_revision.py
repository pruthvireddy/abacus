"""Finalize only two verified saved-cell presentation exports, never a run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import session_revision as revision


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize(workspace, stage):
    records = []
    for spec in revision.SPECS:
        prepared = stage / "revisions" / spec.revision_id
        source_map = json.loads((prepared / "source-map.json").read_text())
        verification = json.loads((prepared / "verification.json").read_text())
        if verification.get("result") != "passed":
            raise ValueError("Independent presentation transfer must pass before finalization")
        if verification.get("publication_id") != spec.publication_id:
            raise ValueError("Independent publication identity mismatch")
        if verification.get("publication_sha256") != digest(prepared / "publication.json"):
            raise ValueError("Independent report hash mismatch")
        if verification.get("source_map_sha256") != digest(prepared / "source-map.json"):
            raise ValueError("Independent source-map hash mismatch")
        locator = f"reports/exports/{revision.STUDY}/{revision.RUN}/{spec.revision_id}"
        destination = workspace / locator
        if destination.exists() or (prepared / "manifest.json").exists():
            raise ValueError("A finalized presentation revision may not be overwritten")
        for path in sorted((stage / "source").glob("*.py")):
            target = prepared / "source" / path.name
            if target.exists() and target.read_bytes() != path.read_bytes():
                raise ValueError("Changed presentation source snapshot")
            if not target.exists():
                target.write_bytes(path.read_bytes())
        original = {revision.SOURCE_LOCATOR + "/manifest.json": revision.MANIFEST_SHA}
        for entry in source_map["source_artifacts"]:
            path = revision.SOURCE_LOCATOR + "/" + entry["original_stage_source_path"]
            pin = entry["original_source_sha256"]
            if path in original and original[path] != pin:
                raise ValueError("Conflicting original-source pins")
            original[path] = pin
        for path, pin in original.items():
            if digest(workspace / path) != pin:
                raise ValueError("Original immutable-source hash mismatch")
        outputs = [{"path": locator + "/" + path.relative_to(prepared).as_posix(),
                    "bytes": path.stat().st_size, "sha256": digest(path)}
                   for path in sorted(prepared.rglob("*")) if path.is_file()]
        manifest = {
            "schema_version": "study23.phase2-session-presentation-manifest/v1",
            "study_id": revision.STUDY, "source_run_id": revision.RUN,
            "source_run_manifest_sha256": revision.MANIFEST_SHA,
            "revision_id": spec.revision_id, "publication_id": spec.publication_id,
            "created_at_utc": revision.CREATED,
            "change": "Additive session-transition, actual-entry and all-level recovery timing saved-cell projections. Earlier reports and research values remain unchanged.",
            "renderer": "stdlib saved-cell JSON/CSV presentation; explicit short display keys bound to full saved column names",
            "renderer_version_record": locator + "/source/version-record.json",
            "generation_command": json.loads((prepared / "source/version-record.json").read_text())["generation_command"],
            "finalization_command": sys.argv,
            "source_artifacts": [{"path": path, "bytes": (workspace / path).stat().st_size, "sha256": pin} for path, pin in sorted(original.items())],
            "outputs": outputs,
            "qualification": "Independent saved-source transfer and byte integrity; no research rerun, statistical recomputation or inferred outcomes.",
        }
        (prepared / "manifest.json").write_bytes(revision.json_bytes(manifest))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(prepared, destination)
        for path in prepared.rglob("*"):
            if path.is_file() and digest(path) != digest(destination / path.relative_to(prepared)):
                raise ValueError("Final export portability copy changed bytes")
        records.append({"publication_id": spec.publication_id, "revision_id": spec.revision_id,
                        "locator": locator, "manifest_sha256": digest(destination / "manifest.json"),
                        "publication_sha256": digest(destination / "publication.json"),
                        "source_map_sha256": digest(destination / "source-map.json"),
                        "verification_sha256": digest(destination / "verification.json"),
                        "files": len(outputs) + 1})
    receipt = {"schema_version": "study23.phase2-session-presentation-finalization/v1", "result": "passed",
               "source_run_manifest_sha256": revision.MANIFEST_SHA, "publications": records,
               "qualification": "Exact verified byte portability and metadata inventory, distinct from scientific revalidation."}
    (stage / "finalization-receipt.json").write_bytes(revision.json_bytes(receipt))
    print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    finalize(args.workspace.resolve(), args.stage.resolve())
