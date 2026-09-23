from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ingest import load_config
from .pipeline import audit_only, regenerate_html, run_study


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reversal-candle follow-through study")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "run"):
        command = subparsers.add_parser(name)
        command.add_argument("--config", required=True)
        command.add_argument("--run-id")
    report = subparsers.add_parser("report")
    report.add_argument("--run-id", required=True)
    report.add_argument(
        "--config",
        default="analysis/01_reversal_follow_through/configs/study.yaml",
        help="Used only to locate the project root",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        path = audit_only(args.config, args.run_id)
        print(json.dumps({"status": "audit complete", "work_dir": str(path)}, indent=2))
        return 0
    if args.command == "run":
        work_dir, report_dir = run_study(args.config, args.run_id)
        print(json.dumps({"status": "study complete", "work_dir": str(work_dir), "report_dir": str(report_dir)}, indent=2))
        return 0
    _, project_root = load_config(args.config)
    path = regenerate_html(project_root, args.run_id)
    print(json.dumps({"status": "report regenerated", "path": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

