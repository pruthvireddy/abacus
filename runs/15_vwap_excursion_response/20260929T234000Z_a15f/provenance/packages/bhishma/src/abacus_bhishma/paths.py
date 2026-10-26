"""Resolve storage locations independently of the installed package location."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


class PathConfigurationError(ValueError):
    """A required storage root was not explicitly configured."""


@dataclass(frozen=True)
class WorkspacePaths:
    workspace_root: Path
    publication_root: Path
    legacy_research_root: Path | None = None


def workspace_root(explicit: Path | str | None = None) -> Path:
    """Use an explicit root, an environment override, or a parent workspace."""
    selected = explicit if explicit is not None else os.environ.get("ABACUS_WORKSPACE_ROOT")
    if selected is not None:
        root = Path(selected).expanduser().resolve()
        if not (root / "pyproject.toml").is_file():
            raise PathConfigurationError(f"No workspace pyproject.toml at {root}")
        return root
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        definition = candidate / "pyproject.toml"
        if definition.is_file():
            with definition.open("rb") as stream:
                project = tomllib.load(stream)
            if "workspace" in project.get("tool", {}).get("uv", {}):
                return candidate
    raise PathConfigurationError(
        "Run inside the Abacus workspace or set ABACUS_WORKSPACE_ROOT."
    )


def _configured_paths(root: Path) -> dict[str, object]:
    config = root / "config/paths.local.toml"
    if not config.is_file():
        return {}
    with config.open("rb") as stream:
        values = tomllib.load(stream).get("paths", {})
    if not isinstance(values, dict):
        raise PathConfigurationError(f"Expected a [paths] table in {config}")
    return values


def _storage_path(value: object, root: Path, key: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PathConfigurationError(f"{key} must be a nonempty path string")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def resolve_publication_root(
    explicit: Path | str | None = None,
    *,
    workspace: Path | str | None = None,
) -> Path:
    """Explicit CLI roots win; never derive a data root from __file__."""
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    override = os.environ.get("ABACUS_PUBLICATION_ROOT")
    # An absolute publication override also works from outside the workspace.
    if override and Path(override).expanduser().is_absolute():
        return Path(override).expanduser().resolve()
    root = workspace_root(workspace)
    value = override if override is not None else _configured_paths(root).get("publication_root")
    if value is None:
        raise PathConfigurationError(
            "Set paths.publication_root in config/paths.local.toml or "
            "ABACUS_PUBLICATION_ROOT, or pass an explicit publication root."
        )
    return _storage_path(value, root, "publication_root")


def load_workspace_paths(explicit: Path | str | None = None) -> WorkspacePaths:
    root = workspace_root(explicit)
    values = _configured_paths(root)
    legacy = os.environ.get("ABACUS_LEGACY_RESEARCH_ROOT", values.get("legacy_research_root"))
    return WorkspacePaths(
        workspace_root=root,
        publication_root=resolve_publication_root(workspace=root),
        legacy_research_root=(
            None if legacy is None else _storage_path(legacy, root, "legacy_research_root")
        ),
    )
