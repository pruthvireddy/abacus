#!/usr/bin/env python3
"""Import, verify, or finish moving the eight October 1 ATAS FX downloads.

This batch orchestrator never writes into an existing snapshot. Conversion
and validation belong to Bhishma; the retained inputs belong to Sahadeva.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from zoneinfo import TZPATH

from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.range_xv import HEADER, digest, enhance_range_xv, verify_enhanced


SNAPSHOT = Path("data/range_xv/fx_20170721_20261001")
TRACKED_MANIFEST = Path("docs/data/range_xv_fx_20170721_20261001.json")
DOCUMENTATION = Path("docs/range-xv-fx-20261001.md")
MANIFEST_NAME = "range_xv_exports_manifest.json"
EXPORTS = (
    ("6E", "Euro", 4, "6E-4RXV.csv", 435603, "64a1a96e72aadf281bcdb7386253697728f9f7a04707704db748b9f7ebdc1a61"),
    ("6E", "Euro", 5, "6E-5rxv.csv", 303314, "ea426d72c685a2d8c8b2f4058bf4e592f599dca8cc63c41d69d78f6287169699"),
    ("6B", "British pound", 4, "6b-4rxv.csv", 202295, "c02fdefb34eae689fc250e2d69d200b6be7f5be7321a26307b4233c1a66d5acd"),
    ("6B", "British pound", 5, "6b-5rxv.csv", 142007, "c4b1b554824fb68c12fc788b72296d051e42e402c8d1bf5fb8eba5aa1a7343d9"),
    ("6J", "Japanese yen", 4, "6J-4rxv.csv", 253253, "4181ab73f3af2e91c71d968158794fccd3adae72054467bdcbf29484aebb1ed9"),
    ("6J", "Japanese yen", 5, "6j-5rxv.csv", 178148, "2b839ee2cc458b0c9df117e5672b3b1fd9235b030df9a16d32d11634795c8e76"),
    ("6S", "Swiss franc", 4, "6s-4rxv.csv", 283389, "69526e770322d98a4d6aa96f5adf5347ce1615a4107888ecb6f9ff320a598e07"),
    ("6S", "Swiss franc", 5, "6s-5rxv.csv", 204269, "aed7ff8a559dda7a682a6d0f1d6553aed597c6502887766277f9f0c68ed78063"),
)
PROTECTED = (
    "data/range_xv/README.md",
    "data/range_xv/range_xv_exports_manifest.json",
    "data/range_xv/20191101_20260924/range_xv_exports_manifest.json",
    "docs/data/range_xv_long_history_20191101_20260924.json",
    "docs/migration/range-xv-clock-normalization-20260924.json",
)
CODE = (
    "packages/bhishma/src/abacus_bhishma/range_xv.py",
    "packages/bhishma/src/abacus_bhishma/paths.py",
    "scripts/import-range-xv-20261001.py",
    "uv.lock",
)


def identity(path: Path, locator: Path) -> dict:
    return {"path": locator.as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}


def contained(root: Path, locator: str) -> Path:
    path = (root / locator).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"artifact escapes workspace: {locator}")
    return path


def verify_snapshot(root: Path, *, full: bool = True) -> dict:
    manifest_path = root / SNAPSHOT / MANIFEST_NAME
    if manifest_path.read_bytes() != (root / TRACKED_MANIFEST).read_bytes():
        raise ValueError("physical and tracked FX manifests differ")
    manifest = json.loads(manifest_path.read_text())
    if manifest["dataset_id"] != "atas_range_xv_fx_20170721_20261001" or len(manifest["files"]) != 8:
        raise ValueError("unexpected FX batch identity")
    for item in manifest["artifacts"] + manifest["protected_historical_inputs"]:
        path = contained(root, item["path"])
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"artifact identity changed: {item['path']}")
    if full:
        for record in manifest["files"]:
            rows = verify_enhanced(contained(root, record["source_path"]), contained(root, record["enhanced_path"]))
            if rows != record["rows"]:
                raise ValueError(f"row count changed: {record['enhanced_path']}")
            print(f"verified {record['product']} {record['setting_ticks']}: {rows:,} rows", flush=True)
    return {"status": "pass", "files": 8, "rows": sum(item["rows"] for item in manifest["files"]),
            "artifacts_checked": len(manifest["artifacts"]), "manifest_sha256": digest(manifest_path),
            "full_source_and_derived_label_check": full}


def import_snapshot(root: Path, downloads: Path, command: list[str]) -> None:
    destination = root / SNAPSHOT
    mirror = root / TRACKED_MANIFEST
    if destination.exists() or mirror.exists():
        raise FileExistsError("FX snapshot already exists; use verify, never re-import in place")
    protected = [identity(root / name, Path(name)) for name in PROTECTED]
    for _, _, _, name, _, expected_hash in EXPORTS:
        if digest(downloads / name) != expected_hash:
            raise ValueError(f"download differs from inspected bytes: {name}")
    (root / "work").mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="import-range-xv-fx-20261001-", dir=root / "work"))
    records, artifacts, coverage = [], [], {}
    flag_totals: Counter[str] = Counter()
    for product, instrument, setting, name, expected_rows, expected_hash in EXPORTS:
        canonical = f"{product}_rangexv_{setting}t_20170721_20261001.csv"
        relative_source = Path("source") / canonical
        relative_enhanced = Path("enhanced") / canonical
        relative_flags = Path("quality") / f"{Path(canonical).stem}_flags.csv"
        relative_sessions = Path("quality") / f"{Path(canonical).stem}_sessions.csv"
        source = stage / relative_source
        source.parent.mkdir(parents=True, exist_ok=True)
        with (downloads / name).open("rb") as reader, source.open("xb") as writer:
            shutil.copyfileobj(reader, writer, 4 * 1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        if digest(source) != expected_hash:
            raise ValueError(f"source-copy mismatch: {name}")
        result = enhance_range_xv(source, stage / relative_enhanced, stage / relative_flags, stage / relative_sessions)
        coverage[canonical] = set(result.pop("session_dates"))
        if (result["rows"] != expected_rows or result["first_session_date_proxy"] != "2017-07-21"
                or result["last_session_date_proxy"] != "2026-10-01" or result["session_dates_with_data"] != 2377):
            raise ValueError(f"unexpected coverage: {name}")
        verified_rows = verify_enhanced(source, stage / relative_enhanced)
        if verified_rows != expected_rows:
            raise ValueError(f"enhanced verification row mismatch: {name}")
        record = {"product": product, "instrument_label": instrument, "setting_ticks": setting,
                  "label_basis": "download_filename_not_ATAS_chart_configuration_verified",
                  "original_download_name": name, "original_download_path": str(downloads / name),
                  "source_path": (SNAPSHOT / relative_source).as_posix(),
                  "enhanced_path": (SNAPSHOT / relative_enhanced).as_posix(),
                  "quality_flags_path": (SNAPSHOT / relative_flags).as_posix(),
                  "session_profile_path": (SNAPSHOT / relative_sessions).as_posix(),
                  "source_sha256": expected_hash, "enhanced_sha256": digest(stage / relative_enhanced),
                  "source_bytes": source.stat().st_size, "enhanced_bytes": (stage / relative_enhanced).stat().st_size,
                  "source_row_order_and_ohlc_verification": "pass_all_rows", **result}
        records.append(record)
        flag_totals.update(result["quality_flag_counts"])
        for relative in (relative_source, relative_enhanced, relative_flags, relative_sessions):
            artifacts.append(identity(stage / relative, SNAPSHOT / relative))
        print(f"imported and verified {product} {setting}: {expected_rows:,} rows", flush=True)
    for name in CODE:
        original = root / name
        relative = Path("provenance") / name
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with original.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
        artifacts.append(identity(target, SNAPSHOT / relative))
    readme = stage / "README.md"
    readme.write_text(
        "# ATAS Range XV FX snapshot — October 1, 2026\n\n"
        "Eight exports: 6E, 6B, 6J, and 6S at filename-labelled 4- and 5-tick settings.\n"
        "2,002,278 rows; inferred session dates 2017-07-21 through 2026-10-01.\n\n"
        "- `source/`: byte-identical five-column exports, renamed consistently.\n"
        "- `enhanced/`: the established eleven-column Range XV schema.\n"
        "- `quality/`: per-row flags and per-session row/edge profiles.\n"
        "- `provenance/`: the converter, batch script, path resolver, lock, and clock data.\n"
        "- [Manifest](range_xv_exports_manifest.json): labels, input/output hashes, timing assumptions, and checks.\n\n"
        "Source timestamps and OHLC strings and all original row positions are preserved.\n"
        "Derived times use the inferred fixed UTC-04:00 to New York conversion.\n"
        "No volume, contract-roll metadata, or exact completion time was exported.\n"
        "Repeated/zero-range records remain flagged; the final session is partial.\n"
        "Snapshot files must not be overwritten.\n\n"
        "See the [import and quality guide](../../../docs/range-xv-fx-20261001.md)\n"
        "and [column definitions](../README.md). From the workspace root, verify with:\n\n"
        "```sh\n./scripts/uv run --locked python scripts/import-range-xv-20261001.py verify\n```\n"
    )
    artifacts.append(identity(readme, SNAPSHOT / "README.md"))
    union = set().union(*coverage.values())
    git_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    zonefile = next((Path(location) / "America/New_York" for location in TZPATH
                     if (Path(location) / "America/New_York").is_file()), None)
    if zonefile is not None:
        target = stage / "provenance/America_New_York.tzif"
        target.write_bytes(zonefile.read_bytes())
        artifacts.append(identity(target, SNAPSHOT / "provenance/America_New_York.tzif"))
    manifest = {
        "schema_version": 2, "dataset_id": "atas_range_xv_fx_20170721_20261001",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "storage_root": "configured_publication_root_equal_to_workspace",
        "source_timestamp_format": "%Y-%d-%m %H:%M:%S",
        "source_columns": ["timestamp", "open", "high", "low", "close"],
        "enhanced_columns": HEADER.decode("ascii").strip().split(";"),
        "source_header": False, "delimiter": ";", "volume_available": False,
        "enhanced_timestamp_format": "%Y-%m-%d %H:%M:%S America/New_York wall time",
        "timestamp_normalization": {"source_export_clock_assumption": "fixed_UTC_minus_04:00",
            "canonical_timestamp_zone": "America/New_York",
            "timezone_status": "inferred_from_seasonal_session_open_pattern_not_ATAS_configuration_verified",
            "source_timestamp_column": "verbatim_ATAS_export_clock",
            "historical_method_reference": "docs/migration/range-xv-clock-normalization-20260924.json"},
        "session_date_proxy_basis": "18:00 America/New_York boundary; session calendar unverified",
        "bar_start_timestamp_basis": "ATAS opening-time interpretation with inferred clock conversion",
        "bar_completion_timestamp_proxy_basis": "next bar's normalized start in same inferred session; not exact completion",
        "source_price_adjustment_status": "unknown; source OHLC strings preserved without adjustment",
        "contract_and_roll_metadata": "not_exported; product labels only",
        "exclusions": {"rows_removed": 0, "deduplicated": False, "zero_range_bars_removed": False},
        "export_end_policy": "retain final row, mark completion unavailable; final session partial",
        "coverage": {"session_union_count": len(union), "all_files_have_same_observed_sessions":
            all(dates == union for dates in coverage.values()),
            "missing_sessions_relative_to_batch_union": {name: sorted(union - dates) for name, dates in coverage.items()},
            "intraday_completeness": "not_certified; gaps between event-driven bars do not prove missing data"},
        "total_rows": sum(item["rows"] for item in records), "quality_flag_totals": dict(sorted(flag_totals.items())),
        "import_script": "scripts/import-range-xv-20261001.py", "documentation": DOCUMENTATION.as_posix(),
        "execution": {"argv": command, "working_directory": str(root), "python": sys.version,
            "platform": platform.platform(), "git_revision": git_revision, "git_dirty": dirty,
            "reproducibility": "exact converter, orchestrator, path resolver, uv.lock and system zonefile retained in provenance/"},
        "files": records, "artifacts": artifacts, "protected_historical_inputs": protected,
    }
    body = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    with (stage / MANIFEST_NAME).open("xb") as writer:
        writer.write(body)
    for item in artifacts:
        relative = Path(item["path"]).relative_to(SNAPSHOT)
        if digest(stage / relative) != item["sha256"]:
            raise ValueError(f"staged artifact changed: {relative}")
    for item in protected:
        if digest(root / item["path"]) != item["sha256"]:
            raise ValueError("historical snapshot changed during import")
    if destination.exists() or mirror.exists():
        raise FileExistsError("snapshot appeared during staging")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.rename(stage, destination)
    mirror.parent.mkdir(parents=True, exist_ok=True)
    with mirror.open("xb") as writer:
        writer.write(body)
    print(json.dumps(verify_snapshot(root, full=False)), flush=True)


def remove_downloads(root: Path, downloads: Path) -> None:
    """Finish an explicitly requested move only after stored artifacts verify."""
    verify_snapshot(root, full=False)
    manifest = json.loads((root / TRACKED_MANIFEST).read_text())
    originals = []
    for record in manifest["files"]:
        original = downloads / record["original_download_name"]
        if not original.exists():
            continue
        if original.resolve() == contained(root, record["source_path"]):
            raise ValueError("refusing to remove retained source")
        if str(original.resolve()) != str(Path(record["original_download_path"]).resolve()):
            raise ValueError("download location differs from import provenance")
        if digest(original) != record["source_sha256"]:
            raise ValueError(f"download changed after import: {original}")
        originals.append(original)
    for original in originals:
        original.unlink()
        print(f"moved into retained Abacus source: {original.name}", flush=True)
    print(json.dumps({"status": "pass", "downloads_removed_after_verified_storage": len(originals)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("import", "verify", "remove-downloads"))
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--workspace-root", type=Path)
    args = parser.parse_args()
    paths = load_workspace_paths(args.workspace_root)
    if paths.publication_root != paths.workspace_root:
        raise ValueError("this in-Abacus snapshot requires publication_root to equal workspace_root")
    if args.mode == "verify":
        print(json.dumps(verify_snapshot(paths.workspace_root)))
        return
    if args.source_dir is None:
        parser.error("--source-dir is required for import/remove-downloads")
    downloads = args.source_dir.expanduser().resolve()
    if args.mode == "import":
        import_snapshot(paths.workspace_root, downloads, [sys.executable, *sys.argv])
    else:
        remove_downloads(paths.workspace_root, downloads)


if __name__ == "__main__":
    main()
