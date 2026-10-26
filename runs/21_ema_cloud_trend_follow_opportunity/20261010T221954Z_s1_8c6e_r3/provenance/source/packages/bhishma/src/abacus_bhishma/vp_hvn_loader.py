"""Read manifest-selected VP/HVN tables through Arrow's lazy dataset interface."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.dataset as ds

SUPPORTED_VERSION = "1.0.0"
SUPPORTED_TABLES = ("snapshots", "candidates", "decisions", "sessions", "rhythm")


def load_release(root, version, table="snapshots"):
    """Open an explicitly pinned VP/HVN table without materializing its rows.

    The caller verifies manifest identities and checksums. Only manifest-listed
    files are selected; partition columns are not inferred from their paths.
    """
    if version != SUPPORTED_VERSION:
        raise ValueError(f"unsupported VP/HVN version: {version!r}; supported version: {SUPPORTED_VERSION}")
    if table not in SUPPORTED_TABLES:
        raise ValueError(f"unsupported VP/HVN table: {table!r}; supported tables: {', '.join(SUPPORTED_TABLES)}")
    manifest = json.loads(
        (Path(root) / f"catalog/datasets/nq_causal_vp_hvn__{version}.json").read_text()
    )
    files = [str(Path(root) / item["path"]) for item in manifest["output_files"] if item["table"] == table]
    if not files:
        raise ValueError(f"no manifest-listed files for VP/HVN table: {table!r}")
    return ds.dataset(files, format="parquet")
