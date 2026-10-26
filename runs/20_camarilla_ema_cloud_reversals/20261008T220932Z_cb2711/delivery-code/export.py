#!/usr/bin/env python3
"""Copy the sealed, already selected web source into a presentation locator.

Narada's release audit currently requires reports/exports locators. This is a
byte-identical portability copy, with no research recalculation or interpretation
change. It neither stages a website publication nor deploys one.
"""
import argparse
import json
from pathlib import Path
import shutil
from src.storage import sha, save_json, utc_now
from src.spec import STUDY


def export(run, revision):
    root = Path(__file__).resolve().parents[2]
    run = run.resolve()
    assert run.parent == root / "runs" / STUDY
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["study_id"] == STUDY and manifest["run_id"] == run.name
    for artifact in manifest["artifacts"]:
        assert sha(run / artifact["path"]) == artifact["sha256"], artifact["path"]
    assert json.loads((run / "verification.json").read_text())["passed"]
    assert json.loads((run / "website-verification.json").read_text())["passed"]
    assert revision and all(c.isalnum() or c in "_-" for c in revision)
    target = root / "reports" / "exports" / STUDY / run.name / revision
    if target.exists():
        raise RuntimeError("Presentation locator already exists; never overwrite")
    report = json.loads((run / "publication.json").read_text())
    selected = ["publication.json", "publication-source-map.json"]
    selected += [s["path"] for s in report["sections"] if s["kind"] == "figure"]
    selected += [d["path"] for d in report["downloads"]]
    target.mkdir(parents=True)
    for name in selected:
        dest = target / ("source-map.json" if name == "publication-source-map.json" else name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(run / name, dest)
        assert sha(dest) == sha(run / name)
    save_json(target / "verification.json", {
        "result": "passed", "verified_at": utc_now(),
        "checks": [{"name": "byte-identical selected source transfer", "passed": True},
                   {"name": "sealed numerical/source-cell reconciliation", "passed": True},
                   {"name": "sealed local Narada checks and browser preview", "passed": True}],
        "source_verification": str((run / "verification.json").relative_to(root)),
        "source_website_verification": str((run / "website-verification.json").relative_to(root)),
        "qualification": "Copies the source prepared before sealing; no changed numbers, methods or interpretation. No hosted deployment."
    })
    source_names = selected + ["manifest.json", "verification.json", "website-verification.json", "config.json"]
    source_map = json.loads((run / "publication-source-map.json").read_text())
    source_names += [m["source"] for m in source_map["tables"]]
    source_names += [m["source_artifact"] for m in source_map["downloads"]]
    def descriptor(path):
        return {"path": str(path.relative_to(root)), "sha256": sha(path), "bytes": path.stat().st_size}
    save_json(target / "manifest.json", {
        "study_id": STUDY, "source_run_id": run.name, "revision_id": revision,
        "publication_id": report["id"], "created_at_utc": utc_now(),
        "change": "Byte-identical portability copy of pre-seal selected source for Narada's explicit release-source locator.",
        "command": f".venv/bin/python studies/{STUDY}/export.py --run {run.relative_to(root)} --revision {revision}",
        "source_artifacts": [descriptor(run / n) for n in sorted(set(source_names))],
        "outputs": [descriptor(p) for p in sorted(target.rglob("*")) if p.is_file()]
    })
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    export(args.run, args.revision)
