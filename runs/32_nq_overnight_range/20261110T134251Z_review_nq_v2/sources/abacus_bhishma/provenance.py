"""File hashing and Git provenance shared by publication builders."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .publication_safety import check_absent, check_path, write_new_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_version(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        return {"git_commit": commit, "git_worktree_dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"git_commit": None, "repository_state": "not_a_git_repository"}


def publication_sources(builder: Path, helpers: tuple[str, ...], *, workspace: Path | None = None
                        ) -> list[tuple[str, Path]]:
    """Resolve a publisher's explicit local source list and prepared environment lock."""
    from .paths import workspace_root

    workspace = workspace_root(workspace)
    package = Path(__file__).parent
    sources = [(f"abacus_bhishma/{builder.name}", builder)]
    sources.extend((f"abacus_bhishma/{name}", package / name) for name in helpers)
    sources.extend((name, workspace / name) for name in
                   ("pyproject.toml", "packages/bhishma/pyproject.toml", "uv.lock"))
    return sources


def retain_sources(destination: Path, sources: list[tuple[str, Path]], *, artifact_id: str,
                   root: Path, error=ValueError) -> dict[str, Any]:
    """Copy and verify only a declared source/lock scope; no dependency discovery."""
    check_absent(destination, root, error=error)
    labels = [label for label, _ in sources]
    if len(labels) != len(set(labels)):
        raise error("duplicate retained-source identity")
    prepared = []
    for label, source in sources:
        if (not isinstance(label, str) or not label or label != label.strip() or
                "\\" in label or ":" in label or Path(label).is_absolute() or
                any(part in {"", ".", ".."} for part in label.split("/"))):
            raise error(f"unsafe retained-source identity: {label}")
        if not source.is_file() or source.is_symlink() or source.resolve() != source.absolute():
            raise error(f"missing or symlinked declared source: {source}")
        prepared.append((label, source, sha256_file(source)))
    destination.mkdir(parents=True)
    records = []
    for label, source, expected in prepared:
        copy = destination / label
        check_absent(copy, root, error=error)
        copy.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as incoming, copy.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        actual = sha256_file(copy)
        if actual != expected or sha256_file(source) != expected:
            raise error(f"declared source changed during retention: {source}; copies retained for inspection")
        records.append({"source": label, "path": str(copy.relative_to(destination)),
                        "bytes": copy.stat().st_size, "sha256": actual})
    result = {"artifact_id": artifact_id,
              "scope": "declared local source and environment-lock bytes; not dependency discovery or execution proof",
              "files": records}
    write_new_bytes(destination / "sources.json", (json.dumps(result, indent=2) + "\n").encode(),
                    root, error=error)
    return result


def verify_retained_sources(destination: Path, sources: list[tuple[str, Path]],
                            retained: dict[str, Any], *, error=ValueError) -> None:
    """Recheck the declared snapshot and originals before a publisher's promotion."""
    records = retained["files"]
    if [r["source"] for r in records] != [label for label, _ in sources]:
        raise error("retained source inventory differs from declared scope")
    for record, (_, source) in zip(records, sources):
        copy = check_path(destination / record["path"], destination, error=error)
        if (source.is_symlink() or source.resolve() != source.absolute() or
                sha256_file(source) != record["sha256"] or
                copy.stat().st_size != record["bytes"] or sha256_file(copy) != record["sha256"]):
            raise error(f"declared source or retained copy changed: {source}; preserve staged evidence")
