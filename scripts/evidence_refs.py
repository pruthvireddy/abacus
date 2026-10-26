"""Verify explicitly authored strategy references against saved CSV bytes.

The navigation validator owns the reference shape. This module verifies only
declared local artifacts and their exact string-valued row selection; it does
not infer a run, interpret statistics, or alter a strategy's evidence status.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

from evidence_paths import EvidenceError, load_json, safe_path
from navigation_metadata import NavigationMetadataError, validate_reference_shape


class EvidenceReferenceError(ValueError):
    """An invalid strategy index or reference selection."""


LIMITS = [
    "Only explicitly declared references are checked; other card claims are not covered.",
    "Saved CSV values remain strings; no statistics or outcomes are recalculated.",
    "Matching local bytes and one row does not establish scientific validity or profitability.",
    "This check does not assess evidence-bundle contracts or generated-index freshness.",
]


def _report(errors, verified, cards_checked):
    return {
        "schema_version": 1,
        "validation_kind": "strategy_evidence_references",
        "status": "invalid" if errors else "valid",
        "cards_checked": cards_checked,
        "references_verified": len(verified),
        "errors": errors,
        "verified_refs": verified,
        "limits": list(LIMITS),
    }


def _cards(value):
    if not isinstance(value, list):
        raise EvidenceReferenceError("strategies must be an array")
    identifiers = set()
    for index, card in enumerate(value):
        label = "strategies[{}]".format(index)
        if not isinstance(card, dict):
            raise EvidenceReferenceError(label + " must be an object")
        identifier = card.get("strategy_id")
        if (not isinstance(identifier, str) or not identifier.strip()
                or any(ord(character) < 32 or ord(character) == 127 for character in identifier)):
            raise EvidenceReferenceError(label + ".strategy_id must be a nonempty string")
        if identifier in identifiers:
            raise EvidenceReferenceError("Duplicate strategy ID: " + identifier)
        identifiers.add(identifier)
        associations = card.get("study_ids")
        if (not isinstance(associations, list)
                or any(not isinstance(study, str) or not study for study in associations)
                or len(associations) != len(set(associations))):
            raise EvidenceReferenceError(label + ".study_ids must be an array of unique study IDs")
        references = card.get("evidence_refs", [])
        if not isinstance(references, list):
            raise EvidenceReferenceError(label + ".evidence_refs must be an array")
    return value


def _selected_row(data, reference, label):
    try:
        text = data.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        headers = next(reader, None)
        if (not headers or any(not column for column in headers)
                or len(headers) != len(set(headers))):
            raise EvidenceReferenceError(label + ": CSV headers must be nonempty and unique")
        required = set(reference["where"]) | set(reference["columns"])
        missing = sorted(required - set(headers))
        if missing:
            raise EvidenceReferenceError(label + ": unknown CSV selectors or columns: " + ", ".join(missing))
        matches, selected = 0, None
        for row_number, cells in enumerate(reader, 2):
            if not cells:
                continue
            if len(cells) != len(headers):
                raise EvidenceReferenceError(
                    "{}: CSV record {} has {} fields; expected {}".format(label, row_number, len(cells), len(headers)))
            row = dict(zip(headers, cells))
            if all(row[column] == value for column, value in reference["where"].items()):
                matches += 1
                selected = {column: row[column] for column in reference["columns"]}
        if matches != 1:
            raise EvidenceReferenceError("{}: expected exactly one matching row; found {}".format(label, matches))
        return selected
    except (UnicodeError, csv.Error) as error:
        raise EvidenceReferenceError(label + ": cannot read saved CSV: " + str(error)) from error


def validate_references(root, cards):
    """Return a versioned assessment; validate all selected metadata before bytes.

    Cards without references are valid and contribute no certified claims.
    Only reference-specific card shape is assessed here; global navigation
    metadata is a separate check.
    """
    root = Path(root).resolve()
    errors, prepared, verified = [], [], []
    try:
        cards = _cards(cards)
    except EvidenceReferenceError as error:
        return _report([str(error)], [], 0)
    for card in cards:
        identifiers = set()
        for index, reference in enumerate(card.get("evidence_refs", [])):
            label = "{}.evidence_refs[{}]".format(card["strategy_id"], index)
            try:
                validate_reference_shape(reference, card["study_ids"], label)
                if reference["id"] in identifiers:
                    raise EvidenceReferenceError(label + ": duplicate reference ID " + reference["id"])
                identifiers.add(reference["id"])
                study = safe_path(root, "studies/" + reference["study_id"])
                if not study.is_dir():
                    raise EvidenceReferenceError(label + ": referenced study is not a directory")
                run_relative = "runs/{}/{}".format(reference["study_id"], reference["run_id"])
                run = safe_path(root, run_relative)
                if not run.is_dir():
                    raise EvidenceReferenceError(label + ": referenced run is not a directory")
                artifact_relative = run_relative + "/" + reference["artifact"]
                safe_path(root, artifact_relative, ordinary_file=True)
                prepared.append((card["strategy_id"], reference, label, artifact_relative))
            except (NavigationMetadataError, EvidenceError, EvidenceReferenceError) as error:
                errors.append(str(error))
    if errors:
        return _report(errors, [], len(cards))
    for strategy_id, reference, label, artifact_relative in prepared:
        try:
            artifact = safe_path(root, artifact_relative, ordinary_file=True)
            data = artifact.read_bytes()
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != reference["sha256"]:
                raise EvidenceReferenceError(label + ": saved artifact SHA-256 mismatch")
            values = _selected_row(data, reference, label)
            verified.append({
                "strategy_id": strategy_id,
                "reference_id": reference["id"],
                "label": reference["label"],
                "study_id": reference["study_id"],
                "run_id": reference["run_id"],
                "artifact": reference["artifact"],
                "path": artifact_relative,
                "sha256": actual_hash,
                "where": dict(reference["where"]),
                "columns": list(reference["columns"]),
                "values": values,
            })
        except (EvidenceError, EvidenceReferenceError, OSError) as error:
            errors.append(str(error))
    return _report(errors, verified, len(cards))


def select_cards(index, strategy_ids=()):
    """Check the minimum index/card shape and resolve explicit strategy IDs."""
    if not isinstance(index, dict):
        raise EvidenceReferenceError("Strategy index must be an object")
    if type(index.get("schema_version")) is not int or index["schema_version"] != 1:
        raise EvidenceReferenceError("Unsupported strategy index schema_version (expected 1)")
    cards = _cards(index.get("strategies"))
    requested = set(strategy_ids)
    unknown = requested - {card["strategy_id"] for card in cards}
    if unknown:
        raise EvidenceReferenceError("Unknown strategy IDs: " + ", ".join(sorted(unknown)))
    return [card for card in cards if not requested or card["strategy_id"] in requested]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    parser.add_argument("--strategy", action="append", default=[], metavar="ID", help="Check only this strategy (repeatable)")
    parser.add_argument("--json", action="store_true", help="Print the versioned assessment as JSON")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        index = load_json(safe_path(root, "strategies/index.json", ordinary_file=True))
        report = validate_references(root, select_cards(index, args.strategy))
    except (EvidenceError, EvidenceReferenceError) as error:
        report = _report([str(error)], [], 0)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Strategy reference integrity: {} ({} references across {} cards).".format(
            report["status"], report["references_verified"], report["cards_checked"]))
        for reference in report["verified_refs"]:
            selectors = ", ".join("{}={}".format(key, repr(value)) for key, value in reference["where"].items())
            print("  {} / {}: {} [{}]".format(reference["strategy_id"], reference["reference_id"], reference["path"], selectors))
        for error in report["errors"]:
            print("  " + error, file=sys.stderr)
        print("Only declared rows and local artifact bytes are verified; other claims and research validity are not assessed.")
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
