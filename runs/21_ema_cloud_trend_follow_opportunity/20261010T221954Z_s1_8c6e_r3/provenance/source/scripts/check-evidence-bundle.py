#!/usr/bin/env python3
"""Read-only integrity assessment of one explicitly selected future evidence bundle."""
import argparse
import json
from pathlib import Path
import sys

# Suppress sibling import caches: checking a bundle must not write into the workspace.
sys.dont_write_bytecode = True
from evidence_contract import assess_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Explicit bundle directory (manifest.json) or manifest file")
    parser.add_argument("--json", action="store_true", help="Print the versioned structured assessment")
    args = parser.parse_args(argv)
    result = assess_bundle(args.target)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(result["status"] + ": " + result.get("manifest", str(args.target)))
        if "reason" in result:
            print(result["reason"])
        if result["status"] == "verified_declared_artifacts":
            print(f"Verified {result['local_artifacts_verified']} declared local artifacts; "
                  f"{len(result['external_artifacts'])} external declarations remain unverified.")
        for error in result["errors"]:
            print("Error: " + error)
        for limitation in result["limits"]:
            print("Scope: " + limitation)
    return {"verified_declared_artifacts": 0, "invalid": 1, "unsupported": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
