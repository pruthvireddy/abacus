"""Summarize the saved A/C context evidence without reopening source data."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.conditional_reporting import write_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    stage = args.workspace_root.resolve() / "work/05_session_vwap" / args.run_id
    if not stage.is_dir():
        raise FileNotFoundError(stage)
    write_all(stage)


if __name__ == "__main__":
    main()
