#!/usr/bin/env python3
"""Read-only independent check of attribution-only presentation revisions.

Only the requested work receipt is written. Sealed runs and completed exports
are read, hashed and compared; no numerical or publication producer is called.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

RUN = "20261017T193830Z_perfuture25_d2c74b"
STUDY = "25_forex_news_ema"
SYMBOLS = ("6e", "6b", "6j", "6a", "6c", "6s")


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def differences(left, right, prefix=""):
    if type(left) is not type(right):
        return {prefix}
    if isinstance(left, dict):
        changed = {prefix + "/" + key for key in left.keys() ^ right.keys()}
        for key in left.keys() & right.keys():
            changed |= differences(left[key], right[key], prefix + "/" + key)
        return changed
    if isinstance(left, list):
        if len(left) != len(right):
            return {prefix}
        return {path for index, (old, new) in enumerate(zip(left, right))
                for path in differences(old, new, prefix + "/" + str(index))}
    return set() if left == right else {prefix}


def leaves(document):
    if isinstance(document, dict):
        return sum(leaves(item) for item in document.values())
    if isinstance(document, list):
        return sum(leaves(item) for item in document)
    return 1


def workspace_path(workspace, relative):
    path = workspace / relative
    require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
            f"invalid workspace artifact path: {relative}")
    return path


def verify(workspace):
    run_root = workspace / "runs" / STUDY / RUN
    run_manifest = read(run_root / "manifest.json")
    declared = run_manifest["artifacts"]
    require(run_manifest["run_id"] == RUN and run_manifest["study_id"] == STUDY and len(declared) == 943,
            "unexpected sealed-run identity/artifact count")
    counts, pins = Counter(), {}
    declared_paths = set()
    for item in declared:
        relative = item["path"]
        require(relative not in declared_paths and not Path(relative).is_absolute() and ".." not in Path(relative).parts,
                "duplicate/invalid sealed-run artifact path")
        declared_paths.add(relative)
        path = run_root / relative
        require(path.is_file() and path.stat().st_size == item["bytes"] and digest(path) == item["sha256"],
                f"sealed-run artifact changed: {relative}")
        counts["sealed_run_artifact_pins"] += 1
    run_manifest_sha256 = digest(run_root / "manifest.json")
    pins[(run_root / "manifest.json").relative_to(workspace).as_posix()] = run_manifest_sha256
    revisions = {}
    export_root = workspace / "reports/exports" / STUDY / RUN
    for symbol in SYMBOLS:
        old_id = f"forex-news-{symbol}-20261017-v2"
        new_id = old_id + "-r1"
        revision_id = f"20261017T205500Z_attribution_{symbol}_r1"
        original = run_root / "publications" / old_id
        revision = export_root / revision_id
        report = read(revision / "publication.json")
        old_report = read(original / "publication.json")
        require(report["id"] == new_id and report["source"]["producer"] == "sahadeva", "incorrect canonical revision identity/producer")
        require(differences(old_report, report) == {"/id", "/source/producer"},
                f"{symbol}: report changed beyond the two attribution fields")
        require(report["source"]["runId"] == RUN, "revision source run changed")
        old_map, new_map = read(original / "source-map.json"), read(revision / "source-map.json")
        require(new_map["publication_id"] == new_id and differences(old_map, new_map) == {"/publication_id"},
                f"{symbol}: source map changed beyond publication identity")
        counts["report_metadata_changes"] += 2
        counts["source_map_metadata_changes"] += 1
        counts["unchanged_report_json_leaves"] += leaves(old_report) - 2
        counts["unchanged_source_map_json_leaves"] += leaves(old_map) - 1
        assets = {item["path"] for item in old_report["downloads"]}
        figures = {section["path"] for section in old_report["sections"] if section["kind"] == "figure"}
        require(len(assets) == 4 and len(figures) == 3, "unexpected original asset selection")
        assets |= figures | {"chart-spec.json", "figure-environment.json"}
        for relative in assets:
            require((revision / relative).read_bytes() == (original / relative).read_bytes(),
                    f"{symbol}: selected asset bytes changed: {relative}")
            counts["byte_identical_assets"] += 1
            if relative.endswith(".csv"):
                counts["byte_identical_csvs"] += 1
            if relative.endswith(".png"):
                counts["byte_identical_pngs"] += 1
        manifest = read(revision / "manifest.json")
        require(manifest["publication_id"] == new_id and manifest["source_run_id"] == RUN and
                manifest["study_id"] == STUDY and manifest["revision_id"] == revision_id,
                "presentation manifest identity differs")
        require(len({item["path"] for item in manifest["source_artifacts"]}) == len(manifest["source_artifacts"]),
                "duplicate presentation source pins")
        source_paths = {item["path"] for item in manifest["source_artifacts"]}
        required_sources = {(run_root / "manifest.json").relative_to(workspace).as_posix(),
                            *{(original / relative).relative_to(workspace).as_posix() for relative in
                              (*assets, "publication.json", "source-map.json", "publication-manifest.json")}}
        require(required_sources <= source_paths, "presentation manifest lacks an original publication source pin")
        for item in manifest["source_artifacts"]:
            path = workspace_path(workspace, item["path"])
            require(path.is_relative_to(run_root) and digest(path) == item["sha256"], "presentation original source pin differs")
            counts["revision_source_pins"] += 1
        outputs = manifest["outputs"]
        require(len({item["path"] for item in outputs}) == len(outputs), "duplicate revision output pins")
        expected_outputs = {path.relative_to(workspace).as_posix() for path in revision.rglob("*") if path.is_file() and path.name != "manifest.json"}
        require({item["path"] for item in outputs} == expected_outputs, "presentation output inventory coverage differs")
        for item in outputs:
            path = workspace_path(workspace, item["path"])
            require(path.is_relative_to(revision) and digest(path) == item["sha256"], "presentation output pin differs")
            pins[item["path"]] = item["sha256"]
            counts["revision_output_pins"] += 1
        for name in ("verification.json", "publisher-verification.json", "catalog-verification.json"):
            receipt = read(revision / name)
            require(receipt["status"] == receipt["result"] == "passed", "authored revision verification did not pass")
            if name != "verification.json":
                require(receipt["exit_code"] == 0, "authored revision validation returned a failure")
            if "publication_sha256" in receipt:
                require(receipt["publication_sha256"] == digest(revision / "publication.json"), "authored receipt publication pin differs")
        check = read(revision / "verification.json")
        require(check["source_map_sha256"] == digest(revision / "source-map.json"), "authored receipt source map pin differs")
        catalog = read(revision / "catalog-verification.json")
        require(catalog["candidate_sha256"] == digest(revision / "catalog-candidate.json"), "catalog candidate pin differs")
        for item in catalog["reports"]:
            require(digest(workspace_path(workspace, item["path"])) == item["sha256"], "catalog report pin differs")
        revision_manifest_relative = (revision / "manifest.json").relative_to(workspace).as_posix()
        pins[revision_manifest_relative] = digest(revision / "manifest.json")
        revisions[new_id] = {"revision_id": revision_id, "publication_sha256": digest(revision / "publication.json"),
                             "source_map_sha256": digest(revision / "source-map.json"),
                             "manifest_sha256": digest(revision / "manifest.json"), "byte_identical_assets": len(assets)}
        counts["revisions"] += 1
    return {"status": "passed", "result": "passed", "source_run_id": RUN,
            "scope": "Independent read-only comparison of completed metadata-only presentation revisions and all sealed-run declared bytes. No statistics, price paths, figures or original outputs recalculated.",
            "counts": dict(counts), "sealed_run_manifest_sha256": run_manifest_sha256,
            "revisions": revisions, "source_and_revision_hashes": pins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    workspace, receipt = args.workspace.resolve(), args.receipt.resolve()
    require(receipt.parent == workspace / "work" / STUDY / RUN and receipt.name == "revision-independent-audit.json",
            "receipt must be the explicit study-25 work audit path")
    try:
        result = verify(workspace)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result = {"status": "failed", "result": "failed", "error": str(exc)}
    result.update(checker_path=str(Path(__file__).resolve()), checker_sha256=digest(__file__),
                  executed_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "counts", "error") if key in result}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
