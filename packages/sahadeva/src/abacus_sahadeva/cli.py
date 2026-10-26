"""Read-only VWAP input-pin diagnostics; no study execution or feature reproduction."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from abacus_bhishma.paths import load_workspace_paths

from .inputs import read_samples, verify_inputs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser(
        "doctor",
        help="Check session_anchored_vwap input pins and configured storage",
        description=(
            "Diagnose session_anchored_vwap pins using the schema-version-1 VWAP lock "
            "contract and supported release versions. Check manifest/catalog identities "
            "and applicable audit/quality-report hashes. This bounded diagnostic does "
            "not verify every data partition, reproduce features, execute a study, "
            "or certify profitability."
        ),
    )
    doctor.add_argument("--workspace-root", type=Path, help="Workspace used to resolve storage and relative lock paths")
    doctor.add_argument(
        "--inputs-lock", type=Path, default=Path("studies/05_session_vwap/inputs.lock.json"),
        help=("A schema-version-1 VWAP lock with an explicitly supported release version "
              "(default: studies/05_session_vwap/inputs.lock.json)"),
    )
    doctor.add_argument(
        "--read-sample", action="store_true",
        help="Also hash one selected partition and load one session per product/timeframe; other partitions remain unverified",
    )
    args = parser.parse_args(argv)
    try:
        paths = load_workspace_paths(args.workspace_root)
        verified = verify_inputs(paths, args.inputs_lock)
        result = {
            "status": "passed",
            "workspace_root": str(paths.workspace_root),
            "publication_root": str(paths.publication_root),
            "legacy_research_root": str(paths.legacy_research_root) if paths.legacy_research_root else None,
            "inputs_lock": verified["inputs_lock"],
            "inputs_lock_sha256": verified["inputs_lock_sha256"],
            "feature_version": verified["version"],
            "verified_manifest_and_release_files": len(verified["checked_files"]),
            "all_data_partitions_verified": False,
            "samples": read_samples(paths, verified) if args.read_sample else [],
        }
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
