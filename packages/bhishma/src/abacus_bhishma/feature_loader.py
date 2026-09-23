"""Consumer loader for immutable Abacus Bhishma feature datasets."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

SUPPORTED_PRODUCTS = {"ES", "NQ", "GC"}
SUPPORTED_TIMEFRAMES = {"2m": 2, "5m": 5, 2: 2, 5: 5}
SUPPORTED_SESSION_ANCHORED_VWAP_VERSIONS = {"1.0.0"}


def session_anchored_vwap_path(
    project_root: Path | str,
    timeframe: str | int,
    *,
    version: str,
) -> Path:
    """Resolve a pinned session-anchored VWAP dataset version."""

    if version not in SUPPORTED_SESSION_ANCHORED_VWAP_VERSIONS:
        raise ValueError(f"unsupported session_anchored_vwap version: {version}")
    try:
        minutes = SUPPORTED_TIMEFRAMES[timeframe]
    except KeyError as exc:
        raise ValueError(f"unsupported timeframe: {timeframe}") from exc
    path = (
        Path(project_root)
        / f"data/features/bars/{minutes}m/feature_set=session_anchored_vwap/version={version}"
    )
    if not path.is_dir():
        raise FileNotFoundError(path)
    return path


def load_session_anchored_vwap(
    project_root: Path | str,
    product: str,
    timeframe: str | int,
    *,
    version: str,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    columns: Iterable[str] | None = None,
) -> pa.Table:
    """Load selected rows/columns from an explicitly pinned feature release.

    ``start_date`` is inclusive and ``end_date`` is exclusive, both interpreted
    as exchange ``session_date`` rather than UTC calendar dates.
    """

    product = product.upper()
    if product not in SUPPORTED_PRODUCTS:
        raise ValueError(f"unsupported product: {product}")
    root = session_anchored_vwap_path(project_root, timeframe, version=version)
    product_path = root / f"product={product}"
    if not product_path.is_dir():
        raise FileNotFoundError(product_path)
    dataset = ds.dataset(product_path, format="parquet", partitioning="hive")
    expression = None
    if start_date is not None:
        start = date.fromisoformat(start_date) if isinstance(start_date, str) else start_date
        expression = pc.field("session_date") >= pa.scalar(start, pa.date32())
    if end_date is not None:
        end = date.fromisoformat(end_date) if isinstance(end_date, str) else end_date
        condition = pc.field("session_date") < pa.scalar(end, pa.date32())
        expression = condition if expression is None else expression & condition
    requested = None if columns is None else list(columns)
    return dataset.to_table(columns=requested, filter=expression)
