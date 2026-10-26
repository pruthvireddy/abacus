"""Consumer helpers for the versioned continuous-futures datasets."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

import numpy as np
import pyarrow.dataset as ds

from .manifest_selection import read_pinned_manifest, require_identity, selected_files

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
    project_root: Path | str, product: str, variant: str = "unadjusted", *,
    manifest_path: Path | str | None = None,
    expected_manifest_sha256: str | None = None,
    verify_selected_files: bool = False,
) -> ds.Dataset:
    """Open an unadjusted or back-adjusted product as an Arrow dataset.

    ``unadjusted`` contains real selected-contract prices for execution and P&L
    modeling. ``back_adjusted`` contains synthetic prices for indicators and signals.
    Paired manifest pin arguments select only declared product/variant bars.
    Optional checksums cover those selected files; auxiliary and unlisted files
    are not loaded or audited. Scanning/filtering remains caller-controlled.
    """

    path = continuous_path(project_root, product, variant)
    manifest = read_pinned_manifest(project_root, manifest_path,
                                    expected_manifest_sha256, verify_selected_files)
    if manifest is None:
        return ds.dataset(path, format="parquet", partitioning="hive")
    identity = {"algorithm_version": "1.0.0", "adjusted": variant == "back_adjusted"}
    if variant == "unadjusted":
        identity.update(dataset="volume_lead_unadjusted_v1", methodology=METHODOLOGY)
    else:
        identity.update(dataset="volume_lead_back_adjusted_v1", roll_methodology=METHODOLOGY,
                        adjustment_methodology=ADJUSTMENT_METHODOLOGY)
    require_identity(manifest, identity)
    scope = path.relative_to(Path(project_root)).as_posix()
    pattern = re.compile(re.escape(scope) + r"/year=[0-9]{4}/part-[^/]+\.parquet")
    files = selected_files(project_root, manifest,
                           lambda name: pattern.fullmatch(name) is not None,
                           verify=verify_selected_files)
    return ds.dataset([str(file) for file in files], format="parquet", partitioning="hive",
                      partition_base_dir=str(path.resolve()))
