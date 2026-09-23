from __future__ import annotations

import argparse
import json

from .pipeline import run_study


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze adverse movement of the same-direction second candle")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--run-id")
    args = parser.parse_args(argv)
    work_dir, report_dir = run_study(args.config, args.run_id)
    print(json.dumps({"status": "study complete", "work_dir": str(work_dir), "report_dir": str(report_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

