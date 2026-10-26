"""Consumer loader for immutable Abacus Bhishma feature datasets."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Iterable

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .manifest_selection import read_pinned_manifest, require_identity, selected_files

SUPPORTED_PRODUCTS = {"ES", "NQ", "GC"}
SUPPORTED_TIMEFRAMES = {"2m": 2, "5m": 5, 2: 2, 5: 5}
SUPPORTED_SESSION_ANCHORED_VWAP_VERSIONS = {"1.0.0"}


def load_gc_5m_release(
    project_root: Path | str,
    release: str,
    *,
    version: str,
    columns: Iterable[str] | None = None,
    manifest_path: Path | str | None = None,
    expected_manifest_sha256: str | None = None,
    verify_selected_files: bool = False,
) -> pa.Table:
    """Load a pinned GC five-minute bar or EMA-band release in year order.

    Legacy mode discovers the existing year partitions. Supplying a manifest
    path and its SHA-256 together selects only its declared GC bar files.
    Selected file checksums are optional; unlisted files are ignored, not audited.
    """
    choices = {
        "dridr_ohlcv_5m": "dridr_ohlcv_5m",
        "gc_ema_deviation_bands": "gc_ema_deviation_bands",
    }
    if release not in choices or version != "1.0.0":
        raise ValueError(f"unsupported five-minute release/version: {release}/{version}")
    path = (Path(project_root) / "data/features/bars/5m"
            / f"feature_set={choices[release]}" / f"version={version}" / "product=GC")
    manifest = read_pinned_manifest(project_root, manifest_path,
                                    expected_manifest_sha256, verify_selected_files)
    if manifest is None:
        files = sorted(path.glob("year=*/part-000.parquet"))
    else:
        if release == "dridr_ohlcv_5m":
            identity = {"dataset_id": "tv_indicators__dridr_ohlcv_5m__v1",
                        "feature_set": release, "feature_set_version": version}
        else:
            identity = {"dataset_id": f"{release}__{version}",
                        "feature_set": release, "version": version}
        require_identity(manifest, identity)
        scope = path.relative_to(Path(project_root)).as_posix()
        pattern = re.compile(re.escape(scope) + r"/year=[0-9]{4}/part-[^/]+\.parquet")
        files = sorted(selected_files(project_root, manifest,
                                      lambda name: pattern.fullmatch(name) is not None,
                                      verify=verify_selected_files))
    if not files:
        raise FileNotFoundError(path)
    requested = None if columns is None else list(columns)
    tables = [pq.read_table(file, columns=requested) for file in files]
    return pa.concat_tables(tables, promote_options="default")


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
    manifest_path: Path | str | None = None,
    expected_manifest_sha256: str | None = None,
    verify_selected_files: bool = False,
) -> pa.Table:
    """Load selected rows/columns from an explicitly pinned feature release.

    ``start_date`` is inclusive and ``end_date`` is exclusive, both interpreted
    as exchange ``session_date`` rather than UTC calendar dates. Paired manifest
    pin arguments opt into interval identity and declared-file selection;
    optional byte verification covers only selected product files.
    """

    product = product.upper()
    if product not in SUPPORTED_PRODUCTS:
        raise ValueError(f"unsupported product: {product}")
    root = session_anchored_vwap_path(project_root, timeframe, version=version)
    product_path = root / f"product={product}"
    if not product_path.is_dir():
        raise FileNotFoundError(product_path)
    manifest = read_pinned_manifest(project_root, manifest_path,
                                    expected_manifest_sha256, verify_selected_files)
    if manifest is None:
        dataset = ds.dataset(product_path, format="parquet", partitioning="hive")
    else:
        minutes = SUPPORTED_TIMEFRAMES[timeframe]
        require_identity(manifest, {"dataset_id": f"session_anchored_vwap_{minutes}m_v1",
                                    "dataset_version": version,
                                    "feature_set": "session_anchored_vwap",
                                    "release_id": f"session_anchored_vwap__{version}",
                                    "timeframe": f"{minutes}m"})
        scope = product_path.relative_to(Path(project_root)).as_posix()
        pattern = re.compile(re.escape(scope) + r"/year=[0-9]{4}/part-[^/]+\.parquet")
        files = selected_files(project_root, manifest,
                               lambda name: pattern.fullmatch(name) is not None,
                               verify=verify_selected_files)
        dataset = ds.dataset([str(file) for file in files], format="parquet",
                             partitioning="hive", partition_base_dir=str(product_path.resolve()))
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
