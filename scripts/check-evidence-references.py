#!/usr/bin/env python3
"""Read-only verification of explicitly authored strategy CSV-row references."""
import sys

sys.dont_write_bytecode = True

from evidence_refs import main


if __name__ == "__main__":
    raise SystemExit(main())
