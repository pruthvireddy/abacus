"""Read-only assessment of explicitly adopted future research evidence bundles."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from evidence_paths import EvidenceError, load_json, relative_path, safe_path

CONTRACT = "abacus.evidence/v1"
STUDY_ID = re.compile(r"[0-9]{2}_[a-z0-9_]+\Z")
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
LIMITS = [
    "Only declared local artifact bytes are verified; undeclared bundle contents are not assessed.",
    "External locators/checksums are declarations; external bytes and backup availability are unverified.",
    "Checks and commands are recorded evidence, never executed or independently reproduced.",
    "Retained source scope does not establish dependency completeness or which code executed historically.",
    "Integrity does not establish scientific validity, profitability or native TradingView compilation/runtime.",
]


def _object(value, required, optional, label):
    if not isinstance(value, dict):
        raise EvidenceError(f"{label}: expected an object")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise EvidenceError(f"{label}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise EvidenceError(f"{label}: expected a nonempty single-line string")
    return value


def _choice(value, choices, label):
    if not isinstance(value, str) or value not in choices:
        raise EvidenceError(f"{label}: expected one of {sorted(choices)}")
    return value


def _array(value, label, *, nonempty=False):
    if not isinstance(value, list) or nonempty and not value:
        raise EvidenceError(f"{label}: expected {'nonempty ' if nonempty else ''}array")
    return value


def _hash(value, label):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise EvidenceError(f"{label}: expected lowercase SHA-256 (64 hexadecimal characters)")


def _size(value, label):
    if type(value) is not int or value < 0:
        raise EvidenceError(f"{label}: expected a nonnegative integer byte size, not a boolean")


def _reference(value, inventory, label):
    try:
        path = relative_path(value)
    except EvidenceError as error:
        raise EvidenceError(f"{label}: {error}") from error
    if path not in inventory:
        raise EvidenceError(f"{label}: referenced file is not inventoried: {path}")
    return path


def _optional_reference(value, inventory, label):
    if isinstance(value, str):
        return _reference(value, inventory, label)
    _object(value, {"state", "reason"}, set(), label)
    _choice(value["state"], {"not_applicable"}, label + ".state")
    _text(value["reason"], label + ".reason")
    return None


def validate_manifest(manifest, *, manifest_name="manifest.json"):
    """Validate the adopted metadata only; raise EvidenceError, without opening files."""
    _object(manifest, {"contract", "bundle_kind", "study_id", "run_id", "inventory_scope",
                       "results", "provenance", "artifacts"}, {"external_artifacts"}, "manifest")
    _choice(manifest["contract"], {CONTRACT}, "manifest.contract")
    _choice(manifest["bundle_kind"], {"research"}, "manifest.bundle_kind")
    _choice(manifest["inventory_scope"], {"declared_artifacts"}, "manifest.inventory_scope")
    if not isinstance(manifest["study_id"], str) or not STUDY_ID.fullmatch(manifest["study_id"]):
        raise EvidenceError("manifest.study_id: expected an explicit study identity, such as 99_synthetic")
    if not isinstance(manifest["run_id"], str) or not IDENTITY.fullmatch(manifest["run_id"]):
        raise EvidenceError("manifest.run_id: expected an explicit single-segment run identity")

    inventory = {}
    for number, item in enumerate(_array(manifest["artifacts"], "manifest.artifacts", nonempty=True)):
        label = f"manifest.artifacts[{number}]"
        _object(item, {"path", "bytes", "sha256"}, set(), label)
        path = relative_path(item["path"])
        if path == manifest_name:
            raise EvidenceError(f"{label}: the manifest is excluded from its own artifact inventory")
        if path in inventory:
            raise EvidenceError(f"{label}: duplicate artifact inventory path: {path}")
        _size(item["bytes"], label + ".bytes")
        _hash(item["sha256"], label + ".sha256")
        inventory[path] = item

    results = manifest["results"]
    _object(results, {"kind", "state", "artifacts"}, {"reason"}, "manifest.results")
    _choice(results["kind"], {"quantitative", "qualitative"}, "manifest.results.kind")
    _choice(results["state"], {"computed", "not_computed"}, "manifest.results.state")
    selected = _array(results["artifacts"], "manifest.results.artifacts", nonempty=results["state"] == "computed")
    paths = [_reference(path, inventory, "manifest.results.artifacts") for path in selected]
    if len(paths) != len(set(paths)):
        raise EvidenceError("manifest.results.artifacts: duplicate references")
    if results["state"] == "not_computed" or "reason" in results:
        _text(results.get("reason"), "manifest.results.reason")

    provenance = manifest["provenance"]
    _object(provenance, {"settings", "input_lock", "exclusions", "commands", "checks", "environment_lock", "code"}, set(), "manifest.provenance")
    for key in ("settings", "commands", "checks", "environment_lock"):
        _reference(provenance[key], inventory, "manifest.provenance." + key)
    for key in ("input_lock", "exclusions"):
        _optional_reference(provenance[key], inventory, "manifest.provenance." + key)
    code = provenance["code"]
    _object(code, {"revision", "dirty", "status", "source_snapshot"}, set(), "manifest.provenance.code")
    if not isinstance(code["revision"], str) or not REVISION.fullmatch(code["revision"]):
        raise EvidenceError("manifest.provenance.code.revision: expected a pinned 40/64-character hexadecimal code revision")
    if type(code["dirty"]) is not bool:
        raise EvidenceError("manifest.provenance.code.dirty: expected boolean; null is not false")
    _reference(code["status"], inventory, "manifest.provenance.code.status")
    snapshot = code["source_snapshot"]
    _object(snapshot, {"paths", "scope"}, set(), "manifest.provenance.code.source_snapshot")
    _text(snapshot["scope"], "manifest.provenance.code.source_snapshot.scope")
    paths = [_reference(path, inventory, "manifest.provenance.code.source_snapshot.paths")
             for path in _array(snapshot["paths"], "manifest.provenance.code.source_snapshot.paths", nonempty=True)]
    if len(paths) != len(set(paths)):
        raise EvidenceError("manifest.provenance.code.source_snapshot.paths: duplicate retained source paths")

    external_ids = set()
    for number, item in enumerate(_array(manifest.get("external_artifacts", []), "manifest.external_artifacts")):
        label = f"manifest.external_artifacts[{number}]"
        _object(item, {"id", "locator", "bytes", "sha256"}, set(), label)
        identity = _text(item["id"], label + ".id")
        if identity in external_ids:
            raise EvidenceError(f"{label}: duplicate external artifact ID {identity}")
        external_ids.add(identity)
        _text(item["locator"], label + ".locator")
        _size(item["bytes"], label + ".bytes")
        _hash(item["sha256"], label + ".sha256")
    return inventory


def _recorded_commands(value):
    for number, command in enumerate(_array(value, "recorded commands", nonempty=True)):
        label = f"recorded commands[{number}]"
        _object(command, {"argv", "cwd"}, {"environment"}, label)
        arguments = _array(command["argv"], label + ".argv", nonempty=True)
        _text(arguments[0], label + ".argv executable")
        for argument in arguments:
            if not isinstance(argument, str) or "\0" in argument:
                raise EvidenceError(label + ".argv: expected exact string arguments without NUL")
        _text(command["cwd"], label + ".cwd")
        if "environment" in command:
            if not isinstance(command["environment"], dict):
                raise EvidenceError(label + ".environment: expected an object of recorded string values")
            for name, recorded in command["environment"].items():
                _text(name, label + ".environment name")
                if not isinstance(recorded, str):
                    raise EvidenceError(label + ".environment: values must be strings")


def _recorded_checks(value, inventory):
    names = set()
    for number, check in enumerate(_array(value, "recorded checks", nonempty=True)):
        label = f"recorded checks[{number}]"
        _object(check, {"name", "status"}, {"record", "reason"}, label)
        name = _text(check["name"], label + ".name")
        if name in names:
            raise EvidenceError(f"{label}: duplicate check name {name}")
        names.add(name)
        status = _choice(check["status"], {"passed", "failed", "not_run", "not_applicable"}, label + ".status")
        if status in {"passed", "failed"}:
            _reference(check.get("record"), inventory, label + ".record")
        elif "record" in check:
            _reference(check["record"], inventory, label + ".record")
        if status in {"not_run", "not_applicable"} or "reason" in check:
            _text(check.get("reason"), label + ".reason")
    return value


def _verify_artifact(root, item):
    path = safe_path(root, item["path"], ordinary_file=True)
    actual_size = path.stat().st_size
    if actual_size != item["bytes"]:
        raise EvidenceError(f"{item['path']}: byte-size mismatch (declared {item['bytes']}, actual {actual_size})")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != item["sha256"]:
        raise EvidenceError(f"{item['path']}: SHA-256 mismatch")


def assess_bundle(target):
    """Assess one selected bundle/manifest; never discover runs or resolve external locators."""
    result = {"assessment_version": 1, "status": "invalid", "contract": None,
              "metadata_valid": False, "local_artifacts_verified": 0,
              "external_artifacts": [], "recorded_checks": [], "errors": [],
              "inventory_scope": "declared_artifacts", "limits": list(LIMITS)}
    try:
        selected = Path(target)
        if selected.is_symlink():
            raise EvidenceError("Selected bundle/manifest must not be a symlink")
        manifest_path = selected / "manifest.json" if selected.is_dir() else selected
        root = manifest_path.parent.resolve(strict=True)
        manifest_path = safe_path(root, manifest_path.name, ordinary_file=True)
        result["manifest"] = str(manifest_path)
        manifest = load_json(manifest_path)
        if not isinstance(manifest, dict):
            raise EvidenceError("manifest: expected a JSON object")
        contract = manifest.get("contract")
        result["contract"] = contract
        if contract != CONTRACT:
            result["status"] = "unsupported"
            result["metadata_valid"] = None
            result["inventory_scope"] = None
            result["reason"] = ("Unsupported historical contract; not assessed under abacus.evidence/v1."
                                if "contract" not in manifest else "Unsupported contract/version; not assessed under abacus.evidence/v1.")
            return result
        inventory = validate_manifest(manifest, manifest_name=manifest_path.name)
        result["metadata_valid"] = True
        result["study_id"], result["run_id"] = manifest["study_id"], manifest["run_id"]
        result["results"] = manifest["results"]
        result["source_verification_scope"] = manifest["provenance"]["code"]["source_snapshot"]["scope"]
        result["external_artifacts"] = [dict(item, bytes_verified=False) for item in manifest.get("external_artifacts", [])]
        for item in inventory.values():
            try:
                _verify_artifact(root, item)
                result["local_artifacts_verified"] += 1
            except (EvidenceError, OSError, RuntimeError) as error:
                result["errors"].append(str(error))
        if result["errors"]:
            return result
        provenance = manifest["provenance"]
        _recorded_commands(load_json(safe_path(root, provenance["commands"], ordinary_file=True)))
        checks = _recorded_checks(load_json(safe_path(root, provenance["checks"], ordinary_file=True)), inventory)
        result["recorded_checks"] = [{"name": check["name"], "status": check["status"],
                                     **({"reason": check["reason"]} if "reason" in check else {})}
                                    for check in checks]
        result["status"] = "verified_declared_artifacts"
    except (EvidenceError, OSError, RuntimeError, UnicodeError, ValueError) as error:
        result["metadata_valid"] = False
        result["errors"].append(str(error))
    return result
