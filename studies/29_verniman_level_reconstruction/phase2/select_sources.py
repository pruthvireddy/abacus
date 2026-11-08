"""Read-only, allowlisted Phase 2 source selection; no level algorithms.

Run only after the neutral baseline walkthrough is complete. The public loader
internally validates/reads the release, then returns exact one-day selections.
Only those filtered rows are serialized into the private Phase 2 stage.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

DATES = ("2026-10-01", "2026-10-02", "2026-10-05")
MANIFEST = "catalog/datasets/verniman_daily_levels__13.0.0.json"
MANIFEST_SHA256 = "39a12cd01b131729908a6b7743a710eaefe73f86e7df9ecb66787787b88277bf"
PINE = "studies/29_verniman_level_reconstruction/indicator/verniman_levels.pine"
PINE_SHA256 = "5bbc40075cefb19feacb1a676c67ee5770cb5ef7023b9dd76781f2927a243f73"
TABLES = ("outlooks", "levels", "issues", "coverage", "source_coverage", "release_membership")
RECOLLECTION_TABLES = ("observations", "observation_levels")
INTAKE = "data/inbox/x/verniman_eod/20261028_backfill_2026"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, default=str)
        output.write("\n")


def bounded_rows(rows: list[dict], requested: str) -> list[dict]:
    if requested not in DATES:
        raise ValueError("session outside the Phase 2 target-access allowlist")
    # This check occurs before any selected rows can be written or printed.
    if any(str(row.get("session_date")) != requested for row in rows):
        raise ValueError("loader returned a row outside the exact requested session")
    return rows


def select(root: Path, stage: Path) -> dict:
    from abacus_bhishma.verniman_consolidated import load_release

    if digest(root / MANIFEST) != MANIFEST_SHA256:
        raise ValueError("consolidated release manifest identity differs")
    if digest(root / PINE) != PINE_SHA256:
        raise ValueError("verified Phase 1 Pine identity differs")
    freeze = json.loads((stage / "protocol-freeze.json").read_text())
    if not freeze.get("before_target_review"):
        raise ValueError("pre-target protocol freeze is absent")
    for relative, expected in freeze["sha256"].items():
        if digest(root / relative) != expected:
            raise ValueError("frozen protocol/input identity differs: " + relative)
    selected_dir = stage / "selected-sources"
    if selected_dir.exists():
        raise FileExistsError("selected-sources already exists; retain it and use a new stage")
    manifest = json.loads((root / MANIFEST).read_text())
    file_pins = {record["path"]: record for record in manifest["files"]}
    inventory: dict = {
        "selection_started_at": datetime.now(timezone.utc).isoformat(),
        "authorized_dates": list(DATES),
        "dataset_id": manifest["dataset_id"],
        "version": manifest["version"],
        "manifest": {"path": MANIFEST, "sha256": MANIFEST_SHA256},
        "baseline": {"path": PINE, "sha256": PINE_SHA256},
        "loader": "abacus_bhishma.verniman_consolidated.load_release",
        "loader_scope": "The public loader verifies/reads manifest-listed release tables internally before applying its date filter. Only exact authorized day rows are returned to this selector, checked and serialized. Unrestricted rows are never printed or passed into model context.",
        "timing_policy": "Preserve null available_at and original source/capture clocks. User recollections remain separate.",
        "release_table_inputs": {},
        "tables": {},
        "intake": [],
    }
    for table in (*TABLES, *RECOLLECTION_TABLES):
        inventory["tables"][table] = {}
        paths = manifest["tables"][table]["paths"]
        inventory["release_table_inputs"][table] = [file_pins[path] for path in paths]
        for requested in DATES:
            end = (date.fromisoformat(requested) + timedelta(days=1)).isoformat()
            filtered = load_release(
                root, MANIFEST, MANIFEST_SHA256,
                table=table, start_date=requested, end_date=end,
            )
            rows = bounded_rows(filtered.to_pylist(), requested)
            category = "user-recollections" if table in RECOLLECTION_TABLES else "release"
            target = selected_dir / category / requested / f"{table}.json"
            write_new(target, rows)
            inventory["tables"][table][requested] = {
                "rows": len(rows), "path": str(target.relative_to(stage)),
                "sha256": digest(target), "start_inclusive": requested,
                "end_exclusive": end,
            }
    for requested in DATES:
        relative = f"{INTAKE}/observations/{requested}__r001.json"
        original = root / relative
        if not original.is_file():
            inventory["intake"].append({"session_date": requested, "path": relative, "status": "missing"})
            continue
        observation = json.loads(original.read_text())
        bounded_rows([observation], requested)
        target = selected_dir / "intake" / f"{requested}__r001.json"
        write_new(target, observation)
        inventory["intake"].append({
            "session_date": requested, "path": relative, "sha256": digest(original),
            "selected_path": str(target.relative_to(stage)), "selected_sha256": digest(target),
            "observation_id": observation.get("observation_id"),
            "revision": observation.get("revision"),
            "status": observation.get("review_status"),
        })
    inventory["selection_completed_at"] = datetime.now(timezone.utc).isoformat()
    write_new(stage / "source-selection-manifest.json", inventory)
    return {
        "authorized_dates": list(DATES),
        "selected_table_counts": {
            table: {day: record["rows"] for day, record in values.items()}
            for table, values in inventory["tables"].items()
        },
        "intake_files": len(inventory["intake"]),
        "manifest": str(stage / "source-selection-manifest.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--neutral-baselines-complete", action="store_true",
                        help="Explicit operator gate after all three fresh neutral captures; do not set before completion")
    args = parser.parse_args()
    if not args.neutral_baselines_complete:
        parser.error("capture all three neutral baselines before selecting target sources")
    print(json.dumps(select(args.root.resolve(), args.stage.resolve()), indent=2))


if __name__ == "__main__":
    main()
