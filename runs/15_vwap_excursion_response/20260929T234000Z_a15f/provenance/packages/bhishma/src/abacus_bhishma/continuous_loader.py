"""Consumer helpers for the versioned continuous-futures datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pyarrow.dataset as ds

PRICE_SCALE = 1e-9
METHODOLOGY = "volume_lead_v1"
ADJUSTMENT_METHODOLOGY = "prior_session_close_additive_v1"
SUPPORTED_VARIANTS = {"unadjusted", "back_adjusted"}


def price_to_float(values: np.ndarray | Iterable[int]) -> np.ndarray:
    """Convert Databento fixed-point price integers to conventional prices."""

    return np.asarray(values, dtype=np.float64) * PRICE_SCALE


def continuous_path(
    project_root: Path | str, product: str, variant: str = "unadjusted"
) -> Path:
    """Return the canonical continuous Parquet dataset path for ``product``."""

    product = product.upper()
    if product not in {"ES", "NQ", "GC"}:
        raise ValueError(f"unsupported product: {product}")
    if variant not in SUPPORTED_VARIANTS:
        raise ValueError(f"unsupported continuous variant: {variant}")
    path = (
        Path(project_root)
        / "data/curated/continuous/1m"
        / f"product={product}"
        / f"roll={METHODOLOGY}"
        / f"variant={variant}"
    )
    if variant == "back_adjusted":
        path /= f"adjustment={ADJUSTMENT_METHODOLOGY}"
    return path


def open_continuous_dataset(
    project_root: Path | str, product: str, variant: str = "unadjusted"
) -> ds.Dataset:
    """Open an unadjusted or back-adjusted product as an Arrow dataset.

    ``unadjusted`` contains real selected-contract prices for execution and P&L
    modeling. ``back_adjusted`` contains synthetic prices for indicators and signals.
    """

    return ds.dataset(
        continuous_path(project_root, product, variant), format="parquet", partitioning="hive"
    )
