"""Read the explicitly pinned Daily Facts release."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow.dataset as ds

from .manifest_selection import read_pinned_manifest, require_identity, selected_files

DATASET_ID = "daily_market_facts__1.0.0"
VERSION = "1.0.0"
ASSETS = ("ES", "NQ", "GC")
WINDOWS = ("globex", "overnight", "rth", "or15", "first60", "last60")
DATA_PATH = Path("data/features/daily/feature_set=daily_market_facts/version=1.0.0")


def load_daily_facts(
    root: Path | str, *, manifest_path: Path | str, manifest_sha256: str,
    assets: tuple[str, ...] = ASSETS, start: date | None = None,
    end_exclusive: date | None = None, columns: list[str] | None = None,
    verify_selected_files: bool = True,
):
    """Return a projected Arrow table with half-open session-date bounds.

    Window availability and retrospective coverage columns are kept separately.
    Callers using facts at a decision time must apply the relevant availability.
    """
    if (not assets or len(assets) != len(set(assets))
            or any(asset not in ASSETS for asset in assets)):
        raise ValueError("select unique assets from ES, NQ and GC")
    if start is not None and end_exclusive is not None and start >= end_exclusive:
        raise ValueError("session-date bounds must be increasing")
    manifest = read_pinned_manifest(root, manifest_path, manifest_sha256, verify_selected_files)
    if manifest is None:
        raise ValueError("Daily Facts requires a manifest and SHA-256 pin")
    require_identity(manifest, {"dataset_id": DATASET_ID, "version": VERSION})
    expected = {str(DATA_PATH / f"product={asset}/part-000.parquet") for asset in assets}
    paths = selected_files(root, manifest, expected.__contains__, verify=verify_selected_files)
    if len(paths) != len(expected):
        raise ValueError("Daily Facts manifest does not declare all selected assets")
    predicate = None
    if start is not None:
        predicate = ds.field("session_date") >= start
    if end_exclusive is not None:
        upper = ds.field("session_date") < end_exclusive
        predicate = upper if predicate is None else predicate & upper
    return ds.dataset(paths, format="parquet").to_table(columns=columns, filter=predicate)
