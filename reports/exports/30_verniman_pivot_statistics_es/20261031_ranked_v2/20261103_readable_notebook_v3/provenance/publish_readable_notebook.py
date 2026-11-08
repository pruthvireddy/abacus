"""Prepare a notebook with short visible cells and adjacent saved evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from src.readable_insight_notebook import (
    build_readable_notebook, replay_readable_notebook, saved_payload, view_helper_source,
)

ROOT = Path(__file__).resolve().parents[2]
OWNER = Path(__file__).resolve().parent
STUDY = "30_verniman_pivot_statistics_es"
RUN = "20261031_ranked_v2"
REVISION = "20261103_readable_notebook_v3"
FROZEN = ROOT / "reports/exports" / STUDY / RUN / REVISION
WORKING = ROOT / "work" / STUDY / "notebook"
NOTEBOOK = "vern-pivot-cross-statistics.ipynb"


def encode(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()


def pin(path):
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest()}


def checked(entry):
    parts = entry["path"].split("/")
    if any(part in ("", ".", "..") for part in parts) or Path(entry["path"]).is_absolute():
        raise ValueError("Unsafe evidence locator")
    path = ROOT / entry["path"]
    if path.is_symlink() or path.resolve() != path or not path.is_file():
        raise ValueError("Expected contained regular saved evidence")
    if pin(path)["sha256"] != entry["sha256"]:
        raise ValueError("Changed saved evidence: " + entry["path"])
    return path.read_bytes()


def write(destination, files):
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def source_content():
    reports, assets, pins = {}, {}, {}
    for key in ("pivot", "vwap"):
        folder = ROOT / "reports/exports" / STUDY / RUN / f"20261103_{key}_insights_v2"
        manifest_path = folder / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        if manifest["study_id"] != STUDY or manifest["source_run_id"] != RUN:
            raise ValueError("Source presentation attribution mismatch")
        pins[manifest_path.relative_to(ROOT).as_posix()] = pin(manifest_path)
        for entry in manifest["source_artifacts"] + manifest["outputs"]:
            checked(entry)
            pins[entry["path"]] = entry
        report = json.loads((folder / "publication.json").read_bytes())
        if report["source"]["runId"] != RUN or report["id"] != manifest["publication_id"]:
            raise ValueError("Source report identity mismatch")
        reports[key] = report
        assets[key] = {section["path"]: (folder / section["path"]).read_bytes()
                       for section in report["sections"] if section["kind"] == "figure"}
    return reports, assets, list(pins.values())


def prepare():
    reports, assets, sources = source_content()
    notebook = build_readable_notebook(reports, assets, source_run_id=RUN)
    files = {NOTEBOOK: encode(notebook), "saved-reports.json": encode(saved_payload(reports, assets)),
             "insight_view.py": view_helper_source().encode()}
    for key, figures in assets.items():
        for name, data in figures.items():
            files[f"assets/{key}/{name}"] = data
    files["README.txt"] = (
        "Open vern-pivot-cross-statistics.ipynb in Cursor's Jupyter Notebook editor.\n"
        "Each insight has a normal Markdown cell and its own short evidence cell.\n"
        "Saved charts and tables are already included as notebook outputs.\n"
        "Keep insight_view.py, saved-reports.json and assets/ beside the notebook to rerun.\n"
        "The setup cell loads these saved presentation files; it does not calculate market statistics.\n"
        "This working folder can be edited; the completed copy is preserved separately.\n"
    ).encode()
    with tempfile.TemporaryDirectory(prefix="abacus-readable-notebook-") as directory:
        temporary = Path(directory) / "notebook"
        write(temporary, files)
        replayed = replay_readable_notebook(notebook, temporary)
    cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    source_lengths = [len("".join(cell["source"])) for cell in cells]
    if len(cells) != 33 or max(source_lengths) > 1500:
        raise ValueError("Expected one short setup and 32 short insight evidence cells")
    return files, sources, {"insights": 32, "code_cells_replayed": replayed,
                            "largest_code_cell_characters": max(source_lengths),
                            "notebook_source_contains_embedded_data": False}


def generate(*, check=False):
    if check:
        manifest = json.loads((FROZEN / "manifest.json").read_bytes())
        for entry in manifest["source_artifacts"] + manifest["outputs"]:
            checked(entry)
        notebook = json.loads((FROZEN / NOTEBOOK).read_bytes())
        replayed = replay_readable_notebook(notebook, FROZEN)
        return {"result": "passed", "code_cells_replayed": replayed,
                "largest_code_cell_characters": max(len("".join(cell["source"])) for cell in notebook["cells"] if cell["cell_type"] == "code"),
                "working_notebook_matches_completed_copy": (WORKING / NOTEBOOK).is_file() and (WORKING / NOTEBOOK).read_bytes() == (FROZEN / NOTEBOOK).read_bytes()}
    if FROZEN.exists() or WORKING.exists():
        raise FileExistsError("A completed revision or working notebook already exists; refusing to overwrite")
    files, sources, checks = prepare()
    files["verification.json"] = encode({"result": "passed", **checks,
        "execution_scope": "Python replay and exact cached rich-output parity; Jupyter frontend/kernel integration not tested.",
        "research_reexecuted": False})
    for path in (Path(__file__), OWNER / "src/readable_insight_notebook.py", ROOT / "uv.lock"):
        files[f"provenance/{path.name}"] = path.read_bytes()
    manifest = {"study_id": STUDY, "source_run_id": RUN, "revision_id": REVISION,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "change": "Remove oversized embedded-data setup cell; use short visible notebook cells and adjacent saved files.",
        "source_artifacts": sources,
        "renderer": {"git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                     "python": sys.version, "source_snapshots": "provenance/",
                     "command": "python3 studies/30_verniman_pivot_statistics_es/publish_readable_notebook.py"},
        "outputs": [{"path": (FROZEN.relative_to(ROOT) / name).as_posix(), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()]}
    write(FROZEN, {**files, "manifest.json": encode(manifest)})
    # A mutable authoring copy is separate from the completed presentation record.
    WORKING.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FROZEN, WORKING, ignore=shutil.ignore_patterns("manifest.json", "verification.json", "provenance"))
    return {"result": "prepared", **checks, "notebook": str(WORKING / NOTEBOOK), "completed_copy": str(FROZEN / NOTEBOOK)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only integrity and output replay of the completed copy")
    args = parser.parse_args()
    print(json.dumps(generate(check=args.check), indent=2))


if __name__ == "__main__":
    main()
