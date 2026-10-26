"""Seal a future stage only after bound scientific and numerical gates pass."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import digest, seal_stage


def event_manifest(stage: Path) -> dict:
    retained = []
    for name in ("candidate_context.parquet", "candidate_outcomes.parquet"):
        path = stage / "tables" / name
        retained.append({"path": f"tables/{name}", "format": "parquet",
                         "rows": pq.read_metadata(path).num_rows, "sha256": digest(path),
                         "retention": "inside sealed run"})
    return {"files": retained}


def seal(stage: Path) -> Path:
    study = Path(__file__).resolve().parent
    return seal_stage(study.parents[1], study.name, stage, event_manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    print(seal(args.stage))


if __name__ == "__main__":
    main()
