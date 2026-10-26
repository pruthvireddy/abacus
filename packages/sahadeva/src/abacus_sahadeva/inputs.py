"""Read-only VWAP schema-version-1 input-pin and bounded sample checks."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from abacus_bhishma.feature_loader import (
    SUPPORTED_SESSION_ANCHORED_VWAP_VERSIONS,
    load_session_anchored_vwap,
)
from abacus_bhishma.paths import WorkspacePaths


class InputPinError(ValueError):
    """A publication no longer matches the study's saved input identities."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise InputPinError(f"Input pin must use a relative path: {relative!r}")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise InputPinError(f"Input pin escapes its root: {relative}")
    return result


def _check(root: Path, record: dict[str, Any]) -> Path:
    path = _contained(root, record["path"])
    if not path.is_file():
        raise InputPinError(f"Missing pinned file: {path}")
    if sha256(path) != record["sha256"]:
        raise InputPinError(f"SHA-256 mismatch: {path}")
    return path


def _json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise InputPinError(f"Expected a JSON object: {path}")
    return value


def verify_inputs(paths: WorkspacePaths, inputs_lock: Path | str) -> dict[str, Any]:
    """Verify supported session_anchored_vwap lock and release identities.

    The VWAP lock must use schema version 1 and an explicitly supported release
    version. Check release, dataset, and related manifest/catalog hashes, plus
    applicable audit and quality-report hashes. Arbitrary study locks are not
    supported. This does not re-hash every data partition, reproduce features,
    execute a study, or certify profitability.
    """
    lock_path = Path(inputs_lock)
    if not lock_path.is_absolute():
        lock_path = paths.workspace_root / lock_path
    lock = _json(lock_path)
    if lock.get("schema_version") != 1:
        raise InputPinError("Unsupported inputs.lock schema_version")
    version = lock.get("version")
    if (
        lock.get("feature_set") != "session_anchored_vwap"
        or version not in SUPPORTED_SESSION_ANCHORED_VWAP_VERSIONS
    ):
        raise InputPinError("An explicitly supported session_anchored_vwap version is required")
    checks: dict[str, str] = {}

    def check(record: dict[str, Any], *, catalog_copy: bool = False) -> Path:
        path = _check(paths.publication_root, record)
        checks[str(path)] = record["sha256"]
        if catalog_copy:
            copied = _check(paths.workspace_root, record)
            checks[str(copied)] = record["sha256"]
        return path

    release = _json(check(lock["release_manifest"], catalog_copy=True))
    if (
        release.get("version") != version
        or release.get("feature_set") != lock["feature_set"]
        or release.get("release_id") != f"session_anchored_vwap__{version}"
    ):
        raise InputPinError("Release identity differs from the study pin")
    datasets = lock.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise InputPinError("At least one pinned dataset is required")
    verified = []
    seen: set[str] = set()
    for pin in datasets:
        timeframe = pin["timeframe"]
        if timeframe not in ("2m", "5m") or timeframe in seen:
            raise InputPinError(f"Unsupported or duplicate timeframe: {timeframe}")
        seen.add(timeframe)
        record = {"path": pin["manifest_path"], "sha256": pin["manifest_sha256"]}
        release_record = release.get("datasets", {}).get(timeframe, {})
        if any(record[key] != release_record.get(key) for key in ("path", "sha256")):
            raise InputPinError(f"Dataset {timeframe} differs from its release manifest")
        manifest = _json(check(record, catalog_copy=True))
        if (
            manifest.get("dataset_id") != pin["dataset_id"]
            or manifest.get("dataset_version") != version
            or manifest.get("timeframe") != timeframe
        ):
            raise InputPinError(f"Dataset identity differs from its pin: {timeframe}")
        verified.append({"pin": pin, "manifest": manifest})
    for record in lock.get("related_manifests", []):
        check(record, catalog_copy=True)
    for key in ("audit", "quality_report"):
        if key in release:
            check(release[key])
    if "audit" in lock:
        if any(lock["audit"][key] != release.get("audit", {}).get(key) for key in ("path", "sha256")):
            raise InputPinError("Audit differs from the pinned release")
        check(lock["audit"])
    return {
        "inputs_lock": str(lock_path.resolve()),
        "inputs_lock_sha256": sha256(lock_path),
        "version": version,
        "checked_files": checks,
        "datasets": verified,
    }


def read_samples(paths: WorkspacePaths, verified: dict[str, Any]) -> list[dict[str, Any]]:
    """Hash one selected VWAP partition and read one session per product/timeframe.

    Read through Bhishma's public loader after checking the selected partition's
    hash. Other partitions remain unverified by this bounded integration check;
    it does not reproduce features or execute a study.
    """
    import pyarrow.parquet as pq

    samples = []
    for dataset in verified["datasets"]:
        pin, manifest = dataset["pin"], dataset["manifest"]
        for product in sorted(manifest["products"]):
            selected = next(
                (record for record in manifest["output_files"]
                 if f"/product={product}/" in record["path"]),
                None,
            )
            if selected is None:
                raise InputPinError(f"No partition listed for {product}/{pin['timeframe']}")
            partition = _check(paths.publication_root, selected)
            parquet = pq.ParquetFile(partition)
            if parquet.metadata.num_rows == 0:
                raise InputPinError(f"Empty sample partition: {partition}")
            first_date = parquet.read_row_group(0, columns=["session_date"])["session_date"][0].as_py()
            table = load_session_anchored_vwap(
                paths.publication_root,
                product,
                pin["timeframe"],
                version=verified["version"],
                start_date=first_date,
                end_date=first_date + timedelta(days=1),
                columns=["session_date", "ts_event", "available_at", "close"],
            )
            if table.num_rows == 0:
                raise InputPinError(f"Loader returned no rows for {product}/{pin['timeframe']}")
            samples.append({
                "product": product,
                "timeframe": pin["timeframe"],
                "session_date": first_date.isoformat(),
                "rows": table.num_rows,
                "partition_sha256": selected["sha256"],
                "columns": table.column_names,
            })
    return samples
