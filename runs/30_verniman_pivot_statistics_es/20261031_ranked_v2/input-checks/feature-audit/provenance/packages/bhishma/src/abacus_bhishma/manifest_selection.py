"""Bounded mechanics for explicitly hash-pinned consumer manifests.

Family identity and canonical data scope belong to each public loader. This
module validates declarations without discovering files or auditing a release.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import stat
from typing import Any, Callable

from .provenance import sha256_file


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate manifest JSON key: {key!r}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"nonfinite manifest JSON number: {value}")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"nonfinite manifest JSON number: {value}")
    return result


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def relative_file(value: Any) -> str:
    """Validate a manifest's root-relative, unambiguous POSIX file locator."""
    if (not isinstance(value, str) or not value or value != value.strip()
            or value.startswith("/") or any(c in value for c in "\\:\x00?#%")
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f"unsafe manifest file path: {value!r}")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"unsafe manifest file path: {value!r}") from exc
    if any(part in ("", ".", "..") or part != part.strip() for part in value.split("/")):
        raise ValueError(f"unsafe manifest file path: {value!r}")
    return value


def _ordinary_file(root: Path, relative: str) -> Path:
    path = root
    parts = relative.split("/")
    for index, part in enumerate(parts):
        path /= part
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f"symlink in selected manifest path: {path}")
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise ValueError(f"non-directory selected manifest ancestor: {path}")
        if index == len(parts) - 1 and not stat.S_ISREG(mode):
            raise ValueError(f"selected manifest path is not an ordinary file: {path}")
    return path


def read_pinned_manifest(
    project_root: Path | str,
    manifest_path: Path | str | None,
    expected_manifest_sha256: str | None,
    verify_selected_files: bool,
) -> dict[str, Any] | None:
    """Read the selected bytes; absence of both pin arguments retains legacy mode.

Relative manifest locators resolve from the explicit publication root. An
absolute caller-selected manifest may be outside it; listed data locators
always resolve inside the publication root and never follow symlinks.
    """
    if type(verify_selected_files) is not bool:
        raise ValueError("verify_selected_files must be a boolean")
    if manifest_path is None and expected_manifest_sha256 is None:
        if verify_selected_files:
            raise ValueError("selected-file verification requires a pinned manifest")
        return None
    if manifest_path is None or expected_manifest_sha256 is None:
        raise ValueError("manifest_path and expected_manifest_sha256 are required together")
    expected = _digest(expected_manifest_sha256, "expected_manifest_sha256")
    explicit_root = Path(project_root).absolute()
    root = explicit_root.resolve()
    selected = Path(manifest_path)
    if not selected.is_absolute():
        selected = _ordinary_file(root, relative_file(str(selected)))
    else:
        # The caller's explicit root may use a system alias; do not erase links
        # below that root or below an independently selected manifest's anchor.
        try:
            relative = selected.relative_to(explicit_root)
        except ValueError:
            selected = _ordinary_file(Path(selected.anchor), relative_file(selected.relative_to(selected.anchor).as_posix()))
        else:
            selected = _ordinary_file(root, relative_file(relative.as_posix()))
    encoded = selected.read_bytes()
    if hashlib.sha256(encoded).hexdigest() != expected:
        raise ValueError(f"selected manifest SHA-256 mismatch: {selected}")
    manifest = json.loads(encoded, object_pairs_hook=_pairs, parse_constant=_constant,
                          parse_float=_float)
    if not isinstance(manifest, dict):
        raise ValueError("selected manifest must be a JSON object")
    records = manifest.get("output_files")
    if not isinstance(records, list) or not records:
        raise ValueError("selected manifest output_files must be a nonempty list")
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("selected manifest file records must be objects")
        relative = relative_file(record.get("path"))
        if relative in seen:
            raise ValueError(f"duplicate manifest file record: {relative}")
        seen.add(relative)
        if type(record.get("bytes")) is not int or record["bytes"] < 0:
            raise ValueError(f"invalid manifest file size: {relative}")
        _digest(record.get("sha256"), f"manifest file SHA-256 for {relative}")
    return manifest


def require_identity(manifest: dict[str, Any], expected: dict[str, Any]) -> None:
    for key, value in expected.items():
        actual = manifest.get(key)
        if type(actual) is not type(value) or actual != value:
            raise ValueError(f"selected manifest identity mismatch for {key}: {actual!r}")


def selected_files(
    project_root: Path | str,
    manifest: dict[str, Any],
    belongs: Callable[[str], bool],
    *,
    verify: bool,
) -> list[Path]:
    """Select existing declared files only; optionally verify those bytes only."""
    root = Path(project_root).resolve()
    files = []
    for record in manifest["output_files"]:
        if not belongs(record["path"]):
            continue
        path = _ordinary_file(root, record["path"])
        if verify and (path.stat().st_size != record["bytes"]
                       or sha256_file(path) != record["sha256"]):
            raise ValueError(f"selected file size/SHA-256 mismatch: {path}")
        files.append(path)
    if not files:
        raise ValueError("no manifest-listed files in the requested dataset scope")
    return files
