"""Strict JSON and local paths shared by offline evidence/navigation checks."""
from __future__ import annotations

import json
import math
from pathlib import Path
import stat


class EvidenceError(ValueError):
    """Malformed metadata or an unsafe/missing declared local path."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("Duplicate JSON key: " + repr(key))
        result[key] = value
    return result


def _nonfinite(value):
    raise EvidenceError("Non-finite JSON number: " + value)


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        _nonfinite(value)
    return number


def load_json(path):
    """Decode an explicitly chosen file; callers enforce its local path boundary."""
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_nonfinite, parse_float=_finite_float)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError("Cannot read JSON {}: {}".format(path, error)) from error


def relative_path(value):
    """Validate a portable relative locator without accessing the filesystem."""
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
            or any(marker in value for marker in ("\\", ":", "?", "#", "%"))
            or value.startswith("/")):
        raise EvidenceError("Expected an unambiguous relative path: " + repr(value))
    if any(part in ("", ".", "..") or part != part.strip() for part in value.split("/")):
        raise EvidenceError("Unsafe relative path: " + repr(value))
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise EvidenceError("Relative path must be valid UTF-8 text: " + repr(value)) from error
    return value


def safe_path(root, relative, *, ordinary_file=False):
    """Resolve an existing local declaration, rejecting every symlink component.

    The caller explicitly chooses the root. Rejecting contained symlinks as well
    as escapes keeps the evidence boundary simple; no external storage is found.
    """
    relative = relative_path(relative)
    root = Path(root).resolve()
    path = root
    try:
        for component in relative.split("/"):
            path = path / component
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise EvidenceError("Symlink in declared local path: " + relative)
            if path != root / relative and not stat.S_ISDIR(mode):
                raise EvidenceError("Non-directory ancestor in declared local path: " + relative)
        if ordinary_file and not stat.S_ISREG(mode):
            raise EvidenceError("Expected an ordinary file: " + relative)
        if not ordinary_file and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise EvidenceError("Expected an ordinary file or directory: " + relative)
        if not path.resolve().is_relative_to(root):
            raise EvidenceError("Path escapes declared root: " + relative)
    except OSError as error:
        raise EvidenceError("Missing or inaccessible local path {}: {}".format(relative, error)) from error
    return path
