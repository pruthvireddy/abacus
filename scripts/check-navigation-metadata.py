#!/usr/bin/env python3
"""Check navigation metadata and local targets; do not verify artifact bytes."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from navigation_metadata import NavigationMetadataError, load_navigation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root (independent of caller cwd)")
    args = parser.parse_args(argv)
    try:
        studies, strategies = load_navigation(args.root)
    except (NavigationMetadataError, OSError, UnicodeError) as error:
        print(f"Navigation metadata invalid: {error}", file=sys.stderr)
        return 1
    reference_count = sum(len(card.get("evidence_refs", [])) for card in strategies)
    print(f"Navigation metadata valid: {len(studies)} studies, {len(strategies)} strategy cards, {reference_count} structured references.")
    print("Local paths and declarations checked; hashes, CSV rows, research validity and index freshness are not assessed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
