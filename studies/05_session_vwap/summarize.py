"""Summarize saved evidence; never recompute market paths during report rendering."""

import argparse
from pathlib import Path
from src.reporting import write_all


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    write_all(args.workspace_root.resolve() / "work/05_session_vwap" / args.run_id)


if __name__ == "__main__":
    main()
