"""Small refusal mechanics for immutable publication destinations.

These checks do not lock directories or make multiple outputs transactional.
Publishers retain ownership of their inventories, stages and promotion order.
"""

from __future__ import annotations

import os
from pathlib import Path


def check_path(path: Path, root: Path, *, error=FileExistsError, directory: bool = False) -> Path:
    """Check lexical containment and every existing ancestor without following links."""
    root = Path(root).resolve()
    if root.exists() and not root.is_dir():
        raise error(f"publication root is not a directory: {root}")
    path = Path(path).absolute()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise error(f"publication path outside explicit root: {path}") from exc
    if not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise error(f"unsafe publication path: {path}")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise error(f"symlinked or non-directory publication ancestor: {current}")
    if path.is_symlink():
        raise error(f"symlinked publication path: {path}")
    if directory and path.exists() and not path.is_dir():
        raise error(f"publication parent is not a directory: {path}")
    return path


def check_absent(path: Path, root: Path, *, error=FileExistsError) -> None:
    path = check_path(path, root, error=error)
    if path.exists():
        raise error(f"refusing existing publication or recovery output: {path}; inspect it manually")


def write_new_bytes(path: Path, content: bytes, root: Path, *, error=FileExistsError,
                    recovery_path: Path | None = None) -> None:
    """Retain a new recovery file, then create the final leaf without replacement."""
    path = Path(path)
    temporary = recovery_path or path.with_name(path.name + ".part")
    check_absent(path, root, error=error)
    check_absent(temporary, root, error=error)
    path.parent.mkdir(parents=True, exist_ok=True)
    check_absent(temporary, root, error=error)
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise error(f"recovery output appeared during metadata creation: {temporary}") from exc
    identity = temporary.stat()
    check_absent(path, root, error=error)
    # A same-directory hard link creates the destination exclusively. A late
    # conflict cannot overwrite either final bytes or the recovery evidence.
    try:
        os.link(temporary, path)
    except FileExistsError as exc:
        raise error(f"publication output appeared during metadata creation: {path}; recovery retained") from exc
    actual = temporary.stat(follow_symlinks=False)
    if (actual.st_dev, actual.st_ino) == (identity.st_dev, identity.st_ino):
        temporary.unlink()
