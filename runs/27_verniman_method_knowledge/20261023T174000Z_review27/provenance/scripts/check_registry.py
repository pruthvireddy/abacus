"""Load the explicit workspace check allowlist; do not execute or import its checks."""
from __future__ import annotations

import json
import re
from pathlib import Path
from string import Formatter

REGISTRY_PATH = "config/workspace-checks.json"
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
STUDY = re.compile(r"[0-9]{2}_[a-z0-9_]+\Z")


class RegistryError(ValueError):
    """The maintained allowlist is malformed or a selection is unknown."""


def _fields(record, required, optional, label):
    if not isinstance(record, dict):
        raise RegistryError(f"{label}: expected an object")
    missing = required - record.keys()
    unknown = record.keys() - required - optional
    if missing or unknown:
        raise RegistryError(f"{label}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise RegistryError(f"{label}: expected a nonempty single-line string")
    return value


def _strings(values, label, *, nonempty=True):
    if not isinstance(values, list) or (nonempty and not values):
        raise RegistryError(f"{label}: expected {'nonempty ' if nonempty else ''}array")
    for value in values:
        _text(value, label)
    if len(values) != len(set(values)):
        raise RegistryError(f"{label}: duplicate records")
    return values


def _identifier(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise RegistryError(f"{label}: invalid ID {value!r}")


def repository_path(root, value, label, *, kind=None, allow_root=False):
    """Validate an explicit relative locator without opening its contents."""
    _text(value, label)
    if value == "." and allow_root:
        path = root
    else:
        if "\\" in value or ":" in value or value.startswith("/") or any(p in {"", ".", ".."} for p in value.split("/")):
            raise RegistryError(f"{label}: expected a bounded repository-relative path")
        path = root / value
    try:
        if not path.resolve().is_relative_to(root):
            raise RegistryError(f"{label}: path escapes repository")
        if kind == "file" and not path.is_file():
            raise RegistryError(f"{label}: missing file {value}")
        if kind == "directory" and not path.is_dir():
            raise RegistryError(f"{label}: missing directory {value}")
        if kind == "entry" and not path.exists():
            raise RegistryError(f"{label}: missing context path {value}")
    except (OSError, RuntimeError) as error:
        raise RegistryError(f"{label}: cannot resolve path: {error}") from error
    return path


def _guide(root, value, label):
    repository_path(root, value, label, kind="file")
    if not value.endswith(".md"):
        raise RegistryError(f"{label}: expected a Markdown guide")
    parts = value.split("/")
    if (parts[0] == "legacy" or parts[0] == "runs" and value != "runs/README.md"
            or value.startswith("reports/exports/")
            or value.startswith("apps/narada/releases/") and value != "apps/narada/releases/README.md"
            or any(part in {"node_modules", ".next", "out", ".release-artifacts", "provenance", "reference"} for part in parts)):
        raise RegistryError(f"{label}: historical/generated files are outside maintained guide coverage")


def _substitutions(value, allowed, label):
    try:
        for _, field, format_spec, conversion in Formatter().parse(value):
            if field is not None and (field not in allowed or format_spec or conversion):
                raise RegistryError(f"{label}: unsupported placeholder {{{field}}}")
    except ValueError as error:
        raise RegistryError(f"{label}: malformed placeholder: {error}") from error


def _prerequisite(root, record, label):
    if not isinstance(record, dict) or "kind" not in record:
        raise RegistryError(f"{label}: expected prerequisite object with kind")
    fields = {"file": {"path"}, "directory": {"path"}, "executable": {"name"},
              "node-major": {"major"}, "argument": {"name"}, "note": set()}
    kind = record["kind"]
    if not isinstance(kind, str) or kind not in fields:
        raise RegistryError(f"{label}: unsupported prerequisite kind {kind!r}")
    _fields(record, {"kind", "description"} | fields[kind], set(), label)
    _text(record["description"], label + ".description")
    if kind in {"file", "directory"}:
        repository_path(root, record["path"], label + ".path")
    elif kind == "executable":
        _text(record["name"], label + ".name")
        if "/" in record["name"] or "\\" in record["name"]:
            raise RegistryError(f"{label}: executable must be a PATH name")
    elif kind == "node-major":
        if type(record["major"]) is not int or record["major"] < 1:
            raise RegistryError(f"{label}: major must be a positive integer")
    elif kind == "argument" and record["name"] != "preview_origin":
        raise RegistryError(f"{label}: unsupported required argument")


def validate_registry(root, registry):
    """Validate a JSON-shaped registry, keeping its declared ordering intact."""
    root = Path(root).resolve()
    _fields(registry, {"schema_version", "default_profile", "profiles", "owners", "checks"}, set(), "registry")
    if type(registry["schema_version"]) is not int or registry["schema_version"] != 1:
        raise RegistryError("registry: unsupported schema_version (expected 1)")
    owners, profiles, checks = registry["owners"], registry["profiles"], registry["checks"]
    if not isinstance(owners, dict) or not owners or not isinstance(profiles, dict) or not profiles:
        raise RegistryError("registry: owners and profiles must be nonempty objects")
    if not isinstance(checks, list) or not checks:
        raise RegistryError("registry: checks must be a nonempty array")
    declared_guides = set()
    study_paths = set()
    for owner_id, owner in owners.items():
        label = f"owner {owner_id}"
        _identifier(owner_id, label)
        _fields(owner, {"kind", "path", "description", "guides", "read_first", "entry_points", "preservation"},
                {"study_id", "no_suite_reason", "plan_absence_reason", "related_checks"}, label)
        if not isinstance(owner["kind"], str) or owner["kind"] not in {"workspace", "package", "app", "study"}:
            raise RegistryError(f"{label}: unsupported owner kind")
        _text(owner["description"], label + ".description")
        repository_path(root, owner["path"], label + ".path", kind="directory", allow_root=True)
        for field in ("guides", "read_first", "entry_points", "preservation"):
            _strings(owner[field], label + "." + field)
        for guide in owner["guides"]:
            _guide(root, guide, label + ".guides")
            if guide in declared_guides:
                raise RegistryError(f"{label}: duplicate guide declaration {guide}")
            declared_guides.add(guide)
        for guide in owner["read_first"]:
            repository_path(root, guide, label + ".read_first", kind="file")
        for path in owner["entry_points"]:
            repository_path(root, path, label + ".entry_points", kind="entry")
        for field in ("no_suite_reason", "plan_absence_reason"):
            if field in owner:
                _text(owner[field], label + "." + field)
        if "related_checks" in owner:
            _strings(owner["related_checks"], label + ".related_checks", nonempty=False)
        if owner["kind"] == "study":
            study_id = owner.get("study_id")
            if not isinstance(study_id, str) or not STUDY.fullmatch(study_id) or owner["path"] != "studies/" + study_id:
                raise RegistryError(f"{label}: study_id must match its study directory")
            if owner["path"] in study_paths:
                raise RegistryError(f"{label}: duplicate study owner")
            study_paths.add(owner["path"])
        elif "study_id" in owner or "plan_absence_reason" in owner:
            raise RegistryError(f"{label}: study-only fields on another owner")
    check_ids = set()
    for record in checks:
        if not isinstance(record, dict):
            raise RegistryError("check: expected object")
        check_id = record.get("id")
        label = f"check {check_id}"
        _identifier(check_id, label)
        if check_id in check_ids:
            raise RegistryError(f"{label}: duplicate check ID")
        check_ids.add(check_id)
        base = {"id", "owner", "kind", "description", "cwd", "env", "prerequisites", "scope"}
        kind = record.get("kind")
        if kind == "command":
            _fields(record, base | {"argv"}, set(), label)
            if not isinstance(record["argv"], list) or not record["argv"]:
                raise RegistryError(f"{label}: argv must be a nonempty array")
            for value in record["argv"]:
                _text(value, label + ".argv")
                _substitutions(value, {"root", "python", "preview_origin"}, label + ".argv")
        elif kind == "unittest":
            _fields(record, base | {"runtime", "unittest"}, set(), label)
            if not isinstance(record["runtime"], str) or record["runtime"] not in {"standard-library", "locked-python"}:
                raise RegistryError(f"{label}: unsupported unittest runtime")
            selection = record["unittest"]
            _fields(selection, {"start_dir", "pattern", "optimize"}, {"names"}, label + ".unittest")
            repository_path(root, selection["start_dir"], label + ".start_dir", kind="directory")
            _text(selection["pattern"], label + ".pattern")
            if "/" in selection["pattern"] or "\\" in selection["pattern"]:
                raise RegistryError(f"{label}: pattern must be a filename pattern")
            if type(selection["optimize"]) is not bool:
                raise RegistryError(f"{label}: optimize must be boolean")
            if "names" in selection:
                _strings(selection["names"], label + ".names")
                if any(not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*", n) for n in selection["names"]):
                    raise RegistryError(f"{label}: test names must be dotted identifiers")
        else:
            raise RegistryError(f"{label}: unsupported check kind {kind!r}")
        if not isinstance(record["owner"], str) or record["owner"] not in owners:
            raise RegistryError(f"{label}: unknown owner {record['owner']!r}")
        _text(record["description"], label + ".description")
        repository_path(root, record["cwd"], label + ".cwd", kind="directory", allow_root=True)
        _strings(record["scope"], label + ".scope")
        if not isinstance(record["env"], dict):
            raise RegistryError(f"{label}: env must be an object")
        for name, value in record["env"].items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name) or name in {"HOME", "CODEX_HOME"}:
                raise RegistryError(f"{label}: invalid child environment name")
            if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise RegistryError(f"{label}: environment values must be strings without controls")
            _substitutions(value, {"root"}, label + ".env")
        if not isinstance(record["prerequisites"], list):
            raise RegistryError(f"{label}: prerequisites must be an array")
        for prerequisite in record["prerequisites"]:
            _prerequisite(root, prerequisite, label + ".prerequisites")
    for profile_id, profile in profiles.items():
        label = f"profile {profile_id}"
        _identifier(profile_id, label)
        _fields(profile, {"description", "checks"}, set(), label)
        _text(profile["description"], label + ".description")
        _strings(profile["checks"], label + ".checks")
        unknown = set(profile["checks"]) - check_ids
        if unknown:
            raise RegistryError(f"{label}: unknown check IDs {sorted(unknown)}")
    if not isinstance(registry["default_profile"], str) or registry["default_profile"] not in profiles:
        raise RegistryError("registry: unknown default_profile")
    for owner_id, owner in owners.items():
        unknown = set(owner.get("related_checks", ())) - check_ids
        if unknown:
            raise RegistryError(f"owner {owner_id}: unknown related checks {sorted(unknown)}")
    return registry


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError(f"registry: duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_registry(root, path=None):
    root = Path(root).resolve()
    locator = REGISTRY_PATH if path is None else path
    source = repository_path(root, locator, "registry path", kind="file")
    try:
        registry = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RegistryError(f"cannot load registry: {error}") from error
    return validate_registry(root, registry)


def maintained_guides(registry):
    return tuple(guide for owner in registry["owners"].values() for guide in owner["guides"])


def select_checks(registry, profiles=(), checks=(), use_default=True):
    """Select the union in registry order; repeated requests execute once."""
    profiles, checks = tuple(profiles), tuple(checks)
    if not profiles and not checks and use_default:
        profiles = (registry["default_profile"],)
    known = {record["id"] for record in registry["checks"]}
    selected = set()
    for profile_id in profiles:
        if profile_id not in registry["profiles"]:
            raise RegistryError(f"unknown profile {profile_id!r}")
        selected.update(registry["profiles"][profile_id]["checks"])
    for check_id in checks:
        if check_id not in known:
            raise RegistryError(f"unknown check ID {check_id!r}")
        selected.add(check_id)
    if not selected:
        raise RegistryError("selection is empty")
    return tuple(record for record in registry["checks"] if record["id"] in selected)


def owner_for_context(registry, selector):
    for owner_id, owner in registry["owners"].items():
        if selector == owner_id or selector == owner.get("study_id"):
            return dict(owner, id=owner_id)
    raise RegistryError(f"unknown context owner or study {selector!r}")


def coverage_errors(root, registry):
    """Compare only current study directories and three current guide locations."""
    root = Path(root).resolve()
    declared = {owner["path"]: (owner_id, owner) for owner_id, owner in registry["owners"].items() if owner["kind"] == "study"}
    suites = {}
    for record in registry["checks"]:
        if record["kind"] == "unittest":
            suites.setdefault(record["unittest"]["start_dir"], set()).add(record["owner"])
    errors = []
    study_root = root / "studies"
    if not study_root.is_dir():
        return []
    for directory in sorted(study_root.iterdir()):
        if not directory.is_dir() or not STUDY.fullmatch(directory.name):
            continue
        relative = "studies/" + directory.name
        declaration = declared.get(relative)
        if declaration is None:
            errors.append(f"unregistered current study owner: {relative}")
            continue
        owner_id, owner = declaration
        guides = set(owner["guides"])
        for suffix in ("README.md", "plan.md", "pine/README.md"):
            path = relative + "/" + suffix
            if (root / path).is_file() and path not in guides:
                errors.append(f"unregistered maintained study guide: {path}")
        plan_exists = (directory / "plan.md").is_file()
        if not plan_exists and not owner.get("plan_absence_reason"):
            errors.append(f"missing explicit absent-plan reason: {relative}")
        if plan_exists and owner.get("plan_absence_reason"):
            errors.append(f"obsolete absent-plan reason: {relative}")
        local_suite = relative + "/tests"
        if (directory / "tests").is_dir():
            if owner_id not in suites.get(local_suite, ()):
                errors.append(f"unregistered active study test directory: {local_suite}")
            if owner.get("no_suite_reason"):
                errors.append(f"obsolete no-suite reason: {relative}")
        elif not owner.get("no_suite_reason"):
            errors.append(f"missing explicit no-suite reason: {relative}")
    for relative in sorted(set(declared) - {"studies/" + p.name for p in study_root.iterdir() if p.is_dir() and STUDY.fullmatch(p.name)}):
        errors.append(f"registered current study directory is missing: {relative}")
    return errors
