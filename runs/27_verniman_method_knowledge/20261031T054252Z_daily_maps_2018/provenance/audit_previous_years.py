#!/usr/bin/env python3
"""Read-only preservation audit against the pre-2018-archive annual snapshot baseline."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


STAGE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check_record(root, record):
    path = (root / record["path"]).resolve()
    path.relative_to(root.resolve())
    raw = path.read_bytes()
    assert len(raw) == record["bytes"], f"changed length: {path}"
    assert digest(raw) == record["sha256"], f"changed bytes: {path}"


def main():
    baseline = json.loads((STAGE / "provenance/prior-annual-preservation.json").read_text())
    parser_path = ROOT / "studies/27_verniman_method_knowledge/build_daily_maps.py"
    spec = importlib.util.spec_from_file_location("read_only_prior_archive_check", parser_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = []
    for prior in baseline:
        manifest_path = ROOT / prior["manifest_path"]
        assert digest(manifest_path.read_bytes()) == prior["manifest_sha256"], f"changed run manifest: {manifest_path}"
        run = manifest_path.parent
        for record in prior["artifacts"]:
            check_record(run, record)
        stage = ROOT / "work/27_verniman_method_knowledge" / prior["run_id"]
        assert (stage / "capture-manifest.json").read_bytes() == (run / "capture-manifest.json").read_bytes(), f"changed capture inventory: {stage}"
        assert (stage / "archive/archive-manifest.json").read_bytes() == (run / "payload-inventory.json").read_bytes(), f"changed reader inventory: {stage}"
        reader = module.check(stage)
        captures = json.loads((stage / "capture-manifest.json").read_text())
        checked = set()
        for record in captures.get("attempts", []) + [image for post in captures["posts"] for image in post.get("images", [])]:
            if not record.get("path") or record["path"] in checked:
                continue
            check_record(stage, record)
            checked.add(record["path"])
        results.append({"run_id": prior["run_id"], "run_artifacts": len(prior["artifacts"]), "reader": reader,
                        "retained_capture_files_checked": len(checked), "status": "unchanged"})
    print(json.dumps({"status": "passed", "annual_snapshots": results, "scope": "Read-only byte and presentation preservation checks; no source or scientific revalidation."}, indent=2))


if __name__ == "__main__":
    main()
