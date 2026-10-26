#!/usr/bin/env python3
"""Validate one explicit future Study 12/13 stage without running research."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from study_provenance import STUDIES, preflight, require_phase


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--study", choices=sorted(STUDIES), required=True)
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--phase", choices=("execution", "rendering", "verification", "seal"), default="seal")
    args = parser.parse_args(argv)
    try:
        root = args.workspace_root.absolute()
        if args.phase == "seal":
            preflight(root, args.stage, args.study)
        else:
            require_phase(root, args.stage, args.study, args.phase)
        print(json.dumps({"status": "verified_declared_provenance", "phase": args.phase,
                          "study_id": args.study, "stage": str(args.stage),
                          "limitations": "retained declared bytes and recorded outcomes; no scientific rerun, dependency or environment audit"}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "invalid", "reason": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
