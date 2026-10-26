"""Validate navigation inputs without reading saved artifact bytes.

Study content kinds describe navigation, independently of harness ownership.
Exact reference hashes and CSV rows belong to the separate reference validator.
"""
from __future__ import annotations

from pathlib import Path
import re

from evidence_paths import EvidenceError, load_json, relative_path, safe_path

STUDY_ID = re.compile(r"[0-9]{2}_[a-z0-9_]+\Z")
STRATEGY_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
REFERENCE_ID = re.compile(r"[a-z][a-z0-9_-]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
CONTENT_KINDS = {"research", "indicator_implementation"}


class NavigationMetadataError(ValueError):
    """A declared navigation input is malformed or has a missing local target."""


def _utf8(value, label):
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise NavigationMetadataError(f"{label}: expected UTF-8-encodable text") from error


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise NavigationMetadataError(f"{label}: expected a nonempty single-line string")
    _utf8(value, label)
    return value


def _object(value, label):
    if not isinstance(value, dict):
        raise NavigationMetadataError(f"{label}: expected an object")
    return value


def _array(value, label, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise NavigationMetadataError(f"{label}: expected {'nonempty ' if nonempty else ''}array")
    for item in value:
        _text(item, label)
    if len(value) != len(set(value)):
        raise NavigationMetadataError(f"{label}: duplicate values")
    return value


def _identifier(value, expression, label):
    if not isinstance(value, str) or not expression.fullmatch(value):
        raise NavigationMetadataError(f"{label}: invalid identifier {value!r}")
    return value


def _relative(value, label):
    if isinstance(value, str):
        _utf8(value, label)
    try:
        return relative_path(value)
    except EvidenceError as error:
        raise NavigationMetadataError(f"{label}: {error}") from error


def _component(value, label):
    _text(value, label)
    _relative(value, label)
    if "/" in value:
        raise NavigationMetadataError(f"{label}: expected one path component")
    return value


def _target(root, value, label, *, directory=False):
    try:
        path = safe_path(root, _relative(value, label), ordinary_file=not directory)
        if directory and not path.is_dir():
            raise NavigationMetadataError(f"{label}: missing directory {value}")
        return path
    except EvidenceError as error:
        raise NavigationMetadataError(f"{label}: {error}") from error


def _schema(record, label):
    if "schema_version" in record and (type(record["schema_version"]) is not int or record["schema_version"] != 1):
        raise NavigationMetadataError(f"{label}: unsupported schema_version; expected integer 1 when supplied")


def _load_metadata(source, locator):
    try:
        return load_json(source)
    except EvidenceError as error:
        raise NavigationMetadataError(f"{locator}: {error}") from error


def validate_reference_shape(reference, study_ids, label="evidence reference"):
    """Validate one csv_row declaration, without stat, reads, or coercion.

    Raises NavigationMetadataError. Selector values are exact saved strings,
    including blank strings. Reference IDs are unique within a card, not globally.
    """
    record = _object(reference, label)
    fields = {"id", "label", "kind", "study_id", "run_id", "artifact", "sha256", "where", "columns"}
    missing, unknown = fields - record.keys(), record.keys() - fields
    if missing or unknown:
        raise NavigationMetadataError(f"{label}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")
    _identifier(record["id"], REFERENCE_ID, label + ".id")
    _text(record["label"], label + ".label")
    if record["kind"] != "csv_row":
        raise NavigationMetadataError(f"{label}: unsupported reference kind {record['kind']!r}")
    _identifier(record["study_id"], STUDY_ID, label + ".study_id")
    if record["study_id"] not in study_ids:
        raise NavigationMetadataError(f"{label}: referenced study is outside the card's declared study_ids")
    _component(record["run_id"], label + ".run_id")
    _relative(record["artifact"], label + ".artifact")
    if not isinstance(record["sha256"], str) or not SHA256.fullmatch(record["sha256"]):
        raise NavigationMetadataError(f"{label}: sha256 must be 64 lowercase hexadecimal characters")
    where = _object(record["where"], label + ".where")
    if not where:
        raise NavigationMetadataError(f"{label}.where: expected at least one exact selector")
    for column, value in where.items():
        _text(column, label + ".where column")
        if not isinstance(value, str):
            raise NavigationMetadataError(f"{label}.where[{column!r}]: selector value must be a string")
        _utf8(value, f"{label}.where[{column!r}]")
    _array(record["columns"], label + ".columns", nonempty=True)


def _study(root, record, owner):
    label = f"study {owner}"
    _object(record, label)
    required = {"study_id", "title", "summary", "status", "topic", "products", "data_summary", "evidence_status", "strategy_ids"}
    missing = required - record.keys()
    if missing:
        raise NavigationMetadataError(f"{label}: missing fields {sorted(missing)}")
    _schema(record, label)
    sid = _identifier(record["study_id"], STUDY_ID, label + ".study_id")
    if sid != owner:
        raise NavigationMetadataError(f"{label}: study_id differs from owning directory ({sid})")
    for field in ("title", "summary", "status", "topic", "data_summary", "evidence_status"):
        _text(record[field], label + "." + field)
    _array(record["products"], label + ".products")
    for strategy_id in _array(record["strategy_ids"], label + ".strategy_ids"):
        _identifier(strategy_id, STRATEGY_ID, label + ".strategy_ids")
    _target(root, f"studies/{sid}/README.md", label + " overview")
    kind = record.get("content_kind", "research")
    if not isinstance(kind, str) or kind not in CONTENT_KINDS:
        raise NavigationMetadataError(f"{label}: unsupported content_kind {kind!r}")
    for field in ("reference_run", "run_id", "latest_exploratory_run"):
        if field in record and record[field] is not None:
            _component(record[field], label + "." + field)
    if record.get("reference_run") is not None:
        _target(root, f"runs/{sid}/{record['reference_run']}", label + " reference_run", directory=True)
    if "archived_code_path" in record:
        _target(root, record["archived_code_path"], label + ".archived_code_path", directory=True)
        _target(root, record["archived_code_path"] + "/README.md", label + " archived overview")
    if kind == "indicator_implementation":
        implementation = _object(record.get("implementation"), label + ".implementation")
        fields = {"plan", "settings", "inputs_lock", "source"}
        if set(implementation) != fields:
            raise NavigationMetadataError(f"{label}.implementation: expected fields {sorted(fields)}")
        for field, locator in implementation.items():
            _target(root, f"studies/{sid}/{_relative(locator, label + '.implementation.' + field)}", label + ".implementation." + field)
        if record.get("reference_run") is not None:
            raise NavigationMetadataError(f"{label}: indicator implementation must not select a research reference_run")
    elif record["status"] == "planned":
        for locator in ("plan.md", "study.yaml", "inputs.lock.json", "notes.md"):
            _target(root, f"studies/{sid}/{locator}", label + " planned input")


def validate_navigation(root, studies, strategies):
    """Check already loaded study/card records; inspect paths, never artifact bytes.

    Associations must name registered identities. They need not be symmetric:
    contextual associations and exact supporting evidence have different roles.
    """
    root = Path(root).resolve()
    if not isinstance(studies, list) or not isinstance(strategies, list):
        raise NavigationMetadataError("navigation: studies and strategies must be arrays")
    study_ids = set()
    for record in studies:
        _object(record, "study")
        sid = record.get("study_id")
        _identifier(sid, STUDY_ID, "study.study_id")
        if sid in study_ids:
            raise NavigationMetadataError(f"navigation: duplicate study_id {sid}")
        study_ids.add(sid)
        _study(root, record, sid)
    strategy_ids = set()
    for record in strategies:
        _object(record, "strategy")
        required = {"strategy_id", "title", "path", "status", "study_ids", "summary"}
        missing = required - record.keys()
        if missing:
            raise NavigationMetadataError(f"strategy: missing fields {sorted(missing)}")
        sid = _identifier(record["strategy_id"], STRATEGY_ID, "strategy.strategy_id")
        label = f"strategy {sid}"
        if sid in strategy_ids:
            raise NavigationMetadataError(f"navigation: duplicate strategy_id {sid}")
        strategy_ids.add(sid)
        for field in ("title", "status", "summary"):
            _text(record[field], label + "." + field)
        _target(root, record["path"], label + ".path")
        declared = _array(record["study_ids"], label + ".study_ids")
        if set(declared) - study_ids:
            raise NavigationMetadataError(f"{label}: unknown study_ids {sorted(set(declared) - study_ids)}")
        references = record.get("evidence_refs", [])
        if not isinstance(references, list):
            raise NavigationMetadataError(f"{label}.evidence_refs: expected array")
        reference_ids = set()
        for index, reference in enumerate(references):
            ref_label = f"{label}.evidence_refs[{index}]"
            validate_reference_shape(reference, declared, ref_label)
            if reference["id"] in reference_ids:
                raise NavigationMetadataError(f"{label}: duplicate evidence reference ID {reference['id']}")
            reference_ids.add(reference["id"])
            run = f"runs/{reference['study_id']}/{reference['run_id']}"
            _target(root, run, ref_label + " run", directory=True)
            _target(root, run + "/" + reference["artifact"], ref_label + " artifact")
    for record in studies:
        unknown = set(record["strategy_ids"]) - strategy_ids
        if unknown:
            raise NavigationMetadataError(f"study {record['study_id']}: unknown strategy_ids {sorted(unknown)}")
    return studies, strategies


def load_navigation(root):
    """Load only explicit study JSON inputs and the mutable strategy index."""
    root = Path(root).resolve()
    studies = []
    try:
        study_root = _target(root, "studies", "study metadata root", directory=True)
        for directory in sorted(study_root.iterdir()):
            if directory.is_symlink():
                _target(root, directory.relative_to(root).as_posix(), "study metadata directory", directory=True)
            if not directory.is_dir():
                continue
            directory = _target(root, directory.relative_to(root).as_posix(), "study metadata directory", directory=True)
            source = directory / "study.json"
            if source.is_symlink():
                _target(root, source.relative_to(root).as_posix(), "study metadata")
            if not source.exists():
                continue
            locator = source.relative_to(root).as_posix()
            source = _target(root, locator, "study metadata")
            study = _load_metadata(source, locator)
            _study(root, study, source.parent.name)
            studies.append(study)
        source = _target(root, "strategies/index.json", "strategy metadata")
        index = _object(_load_metadata(source, "strategies/index.json"), "strategy index")
        _schema(index, "strategy index")
        if "strategies" not in index:
            raise NavigationMetadataError("strategy index: missing strategies array")
        return validate_navigation(root, studies, index["strategies"])
    except EvidenceError as error:
        raise NavigationMetadataError(str(error)) from error
