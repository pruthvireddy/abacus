"""Write one explicitly selected, fresh presentation revision.

The caller owns publication content and supplies serialized payloads and producer
bytes. This writer does not discover research, create completion manifests, or
claim that the retained producer list covers every dependency. Failed writes keep
their partial revision for diagnosis; there is no multi-file transaction.
"""

import hashlib
import json
import os
from pathlib import Path
import re


def _ordinary_ancestors(path):
    for ancestor in reversed(path.parents):
        if ancestor.is_symlink():
            raise ValueError(f"Symlinked revision ancestor: {ancestor}")
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError(f"Non-directory revision ancestor: {ancestor}")


def _producer_path(name):
    if not isinstance(name, str) or "\\" in name or "\x00" in name:
        raise ValueError(f"Invalid producer path: {name!r}")
    parts = name.split("/")
    if len(parts) != 2 or parts[0] != "provenance" or parts[1] in {"", ".", "..", "source-inventory.json"}:
        raise ValueError(f"Invalid producer path: {name!r}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", parts[1]):
        raise ValueError(f"Invalid producer path: {name!r}")
    return name


def _write_new(path, content):
    _ordinary_ancestors(path)
    with path.open("xb") as handle:
        handle.write(content)


def write_revision(
    output,
    *,
    publication_bytes,
    source_map_bytes,
    readme_text,
    producer_sources,
):
    """Write prepared bytes without overwriting any revision or output file.

    All producer contents must already have been read by the caller. Serialization
    and explicit path/type validation finish before any destination is created.
    Existing revisions, broken links and redirected ancestors are refused.
    """
    output = Path(output)
    if not output.is_absolute() or ".." in output.parts:
        raise ValueError(f"Revision path must be absolute without traversal: {output}")
    if not isinstance(publication_bytes, bytes) or not isinstance(source_map_bytes, bytes):
        raise TypeError("Publication and source map must be prepared bytes")
    if not isinstance(readme_text, str):
        raise TypeError("Revision README must be text")

    readme_bytes = readme_text.encode("utf-8")
    sources = list(producer_sources)
    if not sources:
        raise ValueError("Explicit producer sources are required")
    inventory = []
    names = set()
    for name, content in sources:
        _producer_path(name)
        if name in names:
            raise ValueError(f"Duplicate producer path: {name}")
        if not isinstance(content, bytes):
            raise TypeError(f"Producer source must be bytes: {name}")
        names.add(name)
        inventory.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
    inventory_bytes = (
        json.dumps(inventory, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")

    _ordinary_ancestors(output)
    if os.path.lexists(output):
        raise FileExistsError(f"Revision already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    _ordinary_ancestors(output)
    output.mkdir(exist_ok=False)
    _write_new(output / "publication.json", publication_bytes)
    _write_new(output / "source-map.json", source_map_bytes)
    (output / "provenance").mkdir(exist_ok=False)
    for name, content in sources:
        _write_new(output / name, content)
    _write_new(output / "provenance/source-inventory.json", inventory_bytes)
    _write_new(output / "README.md", readme_bytes)
