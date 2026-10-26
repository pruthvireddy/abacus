"""Copy verified pre-seal chart reports into unique presentation revisions."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "22_es_range_xv_focused"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}


def export(run_id: str, revision_prefix: str) -> list[dict]:
    if any(not value or '/' in value or '\\' in value or value in ('.', '..') for value in (run_id, revision_prefix)):
        raise ValueError("Run/revision IDs must be single safe path components")
    run = ROOT / "runs" / STUDY_ID / run_id
    manifest = json.loads((run / "manifest.json").read_text())
    if manifest["study_id"] != STUDY_ID or manifest["run_id"] != run_id:
        raise ValueError("Completed run identity mismatch")
    pins = {entry["path"]: entry for entry in manifest["artifacts"]}
    for relative in ("verification.json", "publication-verification.json", "preseal-checks.json"):
        if json.loads((run / relative).read_text())["result"] != "passed":
            raise ValueError("Completed evidence lacks passing gates")
    revisions = []
    for setting in (4, 5, 6):
        source = run / "publications" / f"{setting}t"
        revision = ROOT / "reports" / "exports" / STUDY_ID / run_id / f"{revision_prefix}_{setting}t"
        if revision.exists():
            raise FileExistsError("Presentation revision overwrite refused")
        paths = sorted(path for path in source.rglob("*") if path.is_file())
        for path in paths:
            relative = path.relative_to(run).as_posix()
            if path.is_symlink() or digest(path) != pins[relative]["sha256"]:
                raise ValueError("Pre-seal presentation bytes changed")
        revision.mkdir(parents=True, exist_ok=False)
        outputs = []
        for path in paths:
            target = revision / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            if digest(path) != digest(target):
                raise ValueError("Portability copy differs from source")
            outputs.append(record(target))
        report = json.loads((revision / "publication.json").read_text())
        source_artifacts = [record(run / relative) for relative in (
            "manifest.json", "config.json", "inputs.lock.json", "verification.json",
            "publication-verification.json", "preseal-checks.json", "input-audit.json",
            "tables/trend_summary.csv", "tables/trend_histogram.csv", "tables/trend_survival.csv", "tables/coverage.csv",
        )] + [record(path) for path in paths] + [record(Path(__file__).resolve())]
        data = {"study_id": STUDY_ID, "source_run_id": run_id,
                "revision_id": revision.name, "publication_id": report["id"],
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "change": "Byte-identical portability copy of the verified pre-seal report and selected CSVs; no analysis or numerical transformation.",
                "command": ["python", "studies/22_es_range_xv_focused/export.py", "--run", run_id, "--revision-prefix", revision_prefix],
                "source_artifacts": source_artifacts, "outputs": outputs}
        with (revision / "manifest.json").open("x") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        revisions.append({"publicationId": report["id"], "revision": revision.relative_to(ROOT).as_posix()})
    return revisions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--revision-prefix", required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.run, args.revision_prefix), indent=2))
