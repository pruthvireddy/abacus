"""Read-only workspace diagnostics; no study execution is implemented here."""

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
    doctor = commands.add_parser("doctor", help="Check configured storage and pinned input identities")
    doctor.add_argument("--workspace-root", type=Path)
    doctor.add_argument("--inputs-lock", type=Path, default=Path("studies/05_session_vwap/inputs.lock.json"))
    doctor.add_argument("--read-sample", action="store_true", help="Also hash and read one source partition/session per product and timeframe")
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
