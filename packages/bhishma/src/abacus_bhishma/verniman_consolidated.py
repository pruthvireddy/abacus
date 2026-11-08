"""Consolidate explicitly pinned Verniman releases without changing their bytes.

This is an offline source-record union, not a new historical extraction. Identical
raw captures can have different legacy revision IDs; their latest extraction is
selected and every original ID remains in release_membership. Distinct revisions
and duplicate dates remain distinct. User recollections and supplied chart images
live in separate observation tables, without becoming captured blog plans.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import provenance
from .paths import resolve_publication_root
from .publication_safety import check_absent, check_path, write_new_bytes

VERSION = "13.0.0"
DATASET_ID = f"verniman_daily_levels__{VERSION}"
DATA_PATH = Path(f"data/curated/external_levels/source=verniman/version={VERSION}")
MANIFEST_PATH = Path(f"catalog/datasets/{DATASET_ID}.json")
SCHEMA_PATH = Path(f"catalog/schemas/{DATASET_ID}.json")
QUALITY_PATH = Path(f"reports/quality/{DATASET_ID}.md")
TIMING_STATUS = "historical_availability_unverified"
OBSERVATION_EVIDENCE = frozenset(("user_supplied_recollection", "user_supplied_image"))
COLOR_INTERPRETATION = "user_supplied_color_legend"
COLOR_ROLES = {"light_blue": {"side": "neutral", "role": "trigger"},
               "green": {"side": "bullish", "role": "target"},
               "red": {"side": "bearish", "role": "target"}}
TABLES = ("outlooks", "levels", "coverage", "issues", "release_membership",
          "source_coverage", "observations", "observation_levels")
PARTITIONED = frozenset(("outlooks", "levels", "coverage", "issues"))
TIME_FIELDS = frozenset(("captured_at", "raw_html_captured_at", "raw_atom_captured_at",
                        "available_at", "source_claimed_published_at", "source_claimed_updated_at",
                        "archive_observed_at", "recorded_at"))
INT_FIELDS = frozenset(("ordinal", "body_contract_year", "parsed_branch_count", "level_count",
                       "issue_count", "post_count", "complete_post_count", "partial_post_count",
                       "failed_post_count", "non_outlook_post_count", "source_level_count",
                       "observation_count", "source_coverage_count"))


@dataclass(frozen=True)
class _ReleaseIdentity:
    version: str
    dataset_id: str
    data_path: Path
    manifest_path: Path
    schema_path: Path
    quality_path: Path


def _release_identity(version: str) -> _ReleaseIdentity:
    if (not isinstance(version, str) or not re.fullmatch(r"[1-9][0-9]*\.0\.0", version)
            or int(version.split(".")[0]) < 13):
        raise ValueError("consolidated release version requires a major version of at least 13")
    dataset_id = f"verniman_daily_levels__{version}"
    return _ReleaseIdentity(version, dataset_id,
        Path(f"data/curated/external_levels/source=verniman/version={version}"),
        Path(f"catalog/datasets/{dataset_id}.json"),
        Path(f"catalog/schemas/{dataset_id}.json"),
        Path(f"reports/quality/{dataset_id}.md"))


def _json(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, default=_json_scalar) + "\n").encode()


def _json_scalar(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def _path(root: Path, value: str | Path) -> Path:
    selected = Path(value)
    selected = selected if selected.is_absolute() else root / selected
    # check_path checks all ancestors without accepting symlinked inputs.
    return check_path(selected, root, error=ValueError)


def _record(path: Path, root: Path) -> dict:
    path = _path(root, path)
    if not path.is_file():
        raise ValueError(f"missing input file: {path}")
    return {"path": path.relative_to(root).as_posix(), "sha256": provenance.sha256_file(path),
            "bytes": path.stat().st_size}


def _checked(root: Path, record: dict, *, verify_bytes: bool = True) -> Path:
    if not isinstance(record, dict) or not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", "")):
        raise ValueError("an explicit lowercase SHA256 pin is required")
    path = _path(root, record.get("path", ""))
    if not path.is_file():
        raise ValueError(f"missing pinned file: {path}")
    if record.get("bytes") is not None and path.stat().st_size != record["bytes"]:
        raise ValueError(f"pinned file size mismatch: {path}")
    if verify_bytes and provenance.sha256_file(path) != record["sha256"]:
        raise ValueError(f"pinned SHA256 mismatch: {path}")
    return path


def _date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        raise ValueError("session_date must be a calendar date, not a timestamp")
    return value if isinstance(value, date) else date.fromisoformat(value)


def _stamp(value) -> datetime | None:
    if value is None or value == "":
        return None
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamps must have an explicit timezone")
    return result.astimezone(timezone.utc)


def _normal_row(row: dict) -> dict:
    result = dict(row)
    for key, value in result.items():
        if key == "session_date":
            result[key] = _date(value)
        elif key in TIME_FIELDS:
            result[key] = _stamp(value)
        elif key in {"price_low", "price_high"} and value is not None:
            price = value if isinstance(value, Decimal) else Decimal(str(value))
            if not price.is_finite() or price.quantize(Decimal("0.01")) != price:
                raise ValueError("prices require finite exact hundredths")
            result[key] = price
        elif key in INT_FIELDS and value is not None:
            if isinstance(value, bool) or int(value) != Decimal(str(value)):
                raise ValueError(f"invalid integer {key}")
            result[key] = int(value)
        elif isinstance(value, (dict, list)):
            result[key] = json.dumps(value, sort_keys=True, default=_json_scalar)
    return result


def _base_schema(table: str) -> pa.Schema:
    bases = {
        "outlooks": {"outlook_id": pa.string(), "source_revision_id": pa.string(), "session_date": pa.date32(),
                     "source_post_id": pa.string(), "source_url": pa.string(), "title": pa.string(),
                     "content_sha256": pa.string(), "contract": pa.string(), "available_at": pa.timestamp("us", tz="UTC"),
                     "timing_status": pa.string(), "primary_source_dataset": pa.string(), "evidence_basis": pa.string()},
        "levels": {"outlook_id": pa.string(), "session_date": pa.date32(), "side": pa.string(),
                   "role": pa.string(), "ordinal": pa.int32(), "source_label": pa.string(),
                   "price_low": pa.decimal128(12, 2), "price_high": pa.decimal128(12, 2),
                   "available_at": pa.timestamp("us", tz="UTC"), "timing_status": pa.string(),
                   "primary_source_dataset": pa.string(), "evidence_basis": pa.string()},
        "issues": {"issue_id": pa.string(), "outlook_id": pa.string(), "session_date": pa.date32(),
                   "code": pa.string(), "description": pa.string(), "primary_source_dataset": pa.string()},
        "release_membership": {"source_dataset_id": pa.string(), "source_outlook_id": pa.string(),
                               "outlook_id": pa.string(), "session_date": pa.date32(),
                               "source_level_count": pa.int32(), "selected_primary": pa.bool_()},
        "coverage": {"session_date": pa.date32(), "status": pa.string(), "reason": pa.string(),
                     "post_count": pa.int32(), "level_count": pa.int32(), "issue_count": pa.int32(),
                     "observation_count": pa.int32(), "source_coverage_count": pa.int32(),
                     "complete_post_count": pa.int32(), "partial_post_count": pa.int32(),
                     "failed_post_count": pa.int32(), "non_outlook_post_count": pa.int32(),
                     "post_urls_json": pa.string(), "outlook_ids_json": pa.string()},
        "source_coverage": {"source_dataset_id": pa.string(), "session_date": pa.date32(),
                            "status": pa.string(), "reason": pa.string()},
        "observations": {"observation_id": pa.string(), "session_date": pa.date32(), "title": pa.string(),
                         "source_url": pa.string(), "contract": pa.string(), "evidence_basis": pa.string(),
                         "recorded_at": pa.timestamp("us", tz="UTC"), "claimed_read_time_text": pa.string(),
                         "claim_timing_class": pa.string(), "notes": pa.string(), "raw_evidence_path": pa.string(),
                         "available_at": pa.timestamp("us", tz="UTC")},
        "observation_levels": {"observation_id": pa.string(), "session_date": pa.date32(), "id": pa.string(),
                               "side": pa.string(), "role": pa.string(), "ordinal": pa.int32(),
                               "label": pa.string(), "price_low": pa.decimal128(12, 2),
                               "price_high": pa.decimal128(12, 2), "notes": pa.string(), "evidence_basis": pa.string()},
    }
    return pa.schema([pa.field(name, kind, nullable=True) for name, kind in bases[table].items()])


def _table(name: str, rows: list[dict], source_schemas: list[pa.Schema] = (),
           *, version: str = VERSION) -> pa.Table:
    # A union of stored fields preserves schema evolution. Missing fields remain
    # null; fields from a rejected old projection are retained in its pinned input.
    release = _release_identity(version)
    fields = {}
    for schema in [_base_schema(name), *source_schemas]:
        for field in schema:
            previous = fields.get(field.name)
            if previous is not None and previous != field.type:
                if pa.types.is_integer(previous) and pa.types.is_integer(field.type):
                    # Legacy count/year fields use different integer widths.
                    fields[field.name] = pa.int64()
                    continue
                raise ValueError(f"incompatible input types for {name}.{field.name}")
            fields[field.name] = field.type
    for key in sorted({key for row in rows for key in row} - fields.keys()):
        values = [row.get(key) for row in rows]
        if key == "session_date":
            kind = pa.date32()
        elif key in TIME_FIELDS:
            kind = pa.timestamp("us", tz="UTC")
        elif key in INT_FIELDS:
            kind = pa.int32()
        elif key in {"price_low", "price_high"}:
            kind = pa.decimal128(12, 2)
        else:
            kind = pa.array(values).type
            if pa.types.is_null(kind):
                kind = pa.string()
        fields[key] = kind
    schema = pa.schema([pa.field(key, kind, nullable=True) for key, kind in fields.items()],
                       metadata={b"dataset_id": release.dataset_id.encode(), b"table": name.encode()})
    return pa.Table.from_pylist(rows, schema=schema)


def _source_release(root: Path, pin: dict) -> tuple[dict, dict[str, pa.Table], list[dict]]:
    path = _checked(root, pin)
    manifest = json.loads(path.read_text())
    version = manifest.get("version", "")
    if (not re.fullmatch(r"(?:[1-9]|1[0-2])\.0\.0", version)
            or manifest.get("dataset_id") != f"verniman_daily_levels__{version}"):
        raise ValueError("historical inputs must explicitly identify Verniman releases 1 through 12")
    records = manifest.get("files", [])
    by_path = {}
    for record in records:
        if record.get("path") in by_path:
            raise ValueError("duplicate historical artifact path")
        _checked(root, record)
        by_path[record["path"]] = record
    tables = {}
    for name in ("outlooks", "levels", "issues", "coverage"):
        selected = manifest.get("tables", {}).get(name)
        if selected is None:
            if name in {"outlooks", "levels"}:
                raise ValueError(f"historical release lacks {name}")
            continue
        if selected.get("path") not in by_path:
            raise ValueError("historical table is absent from hashed artifact inventory")
        table = pq.ParquetFile(_path(root, selected["path"])).read()
        if table.num_rows != selected.get("rows"):
            raise ValueError("historical table count mismatch")
        tables[name] = table
    return manifest, tables, [_record(path, root), *records]


def _validate_image_pins(tables: dict[str, pa.Table], records: list[dict], *, version: str = VERSION) -> None:
    """Require each supplied image to be an explicitly pinned release input."""
    by_path = {record.get("path"): record for record in records}
    for row in tables["observations"].to_pylist():
        if row.get("evidence_basis") != "user_supplied_image":
            continue
        if int(_release_identity(version).version.split(".")[0]) < 16:
            raise ValueError("image observations require release version 16 or newer")
        pin = by_path.get(row.get("raw_evidence_path"), {})
        if pin.get("sha256") != row.get("raw_evidence_sha256"):
            raise ValueError("image observation must reference its exact pinned input bytes")
        if row.get("interpretation_basis") == COLOR_INTERPRETATION:
            if int(_release_identity(version).version.split(".")[0]) < 19:
                raise ValueError("image color interpretations require release version 19 or newer")
            legend = by_path.get(row.get("legend_path"), {})
            if legend.get("sha256") != row.get("legend_sha256"):
                raise ValueError("image interpretation must reference its exact pinned user legend")
            _validate_legend_document(row, by_path)


def _validate_legend_document(row: dict, pins: dict) -> None:
    document = row.get("legend_document_json")
    if not isinstance(document, str) or hashlib.sha256(document.encode()).hexdigest() != row.get("legend_sha256"):
        raise ValueError("image interpretation must retain its exact legend document")
    try:
        legend = json.loads(document)
    except ValueError as exc:
        raise ValueError("invalid user color legend document") from exc
    if (not isinstance(legend, dict) or legend.get("schema") != "abacus.verniman.image-color-legend/v1"
            or legend.get("interpretation_basis") != COLOR_INTERPRETATION):
        raise ValueError("unsupported user color legend document")
    mapping = legend.get("color_roles")
    if (not isinstance(mapping, dict) or set(mapping) != set(COLOR_ROLES)
            or any(not isinstance(mapping[color], dict)
                   or any(mapping[color].get(key) != value for key, value in roles.items())
                   for color, roles in COLOR_ROLES.items())):
        raise ValueError("user color legend must retain the declared pivot and target mapping")
    statement = legend.get("source_statement", {})
    if (not isinstance(statement, dict) or not isinstance(statement.get("path"), str)
            or not statement["path"].startswith("data/raw/user/verniman/")
            or ".." in Path(statement["path"]).parts
            or not re.fullmatch(r"[0-9a-f]{64}", statement.get("sha256") or "")
            or pins.get(statement["path"], {}).get("sha256") != statement.get("sha256")):
        raise ValueError("user color legend requires its exact pinned source statement")
    scope = legend.get("applies_to")
    if not isinstance(scope, list) or not any(isinstance(item, dict) and all(
            str(item.get(key)) == str(value) for key, value in {
                "observation_id": row.get("supersedes_observation_id") or row.get("observation_id"),
                "session_date": row.get("session_date"), "raw_evidence_path": row.get("raw_evidence_path"),
                "raw_evidence_sha256": row.get("raw_evidence_sha256")}.items()) for item in scope):
        raise ValueError("user color legend does not explicitly cover this exact image")


def _prepare_color_interpretations(root: Path, observations: list[dict], records: list[dict], *, version: str) -> None:
    pins = {pin.get("path"): pin for pin in records}
    for row in observations:
        if row.get("interpretation_basis") != COLOR_INTERPRETATION:
            continue
        if int(_release_identity(version).version.split(".")[0]) < 19:
            raise ValueError("image color interpretations require release version 19 or newer")
        path = row.get("legend_path")
        if (not isinstance(path, str) or not path.startswith("data/raw/user/verniman/")
                or ".." in Path(path).parts or not re.fullmatch(r"[0-9a-f]{64}", row.get("legend_sha256") or "")):
            raise ValueError("image interpretation requires an exact raw user legend pin")
        pin = pins.get(path, {})
        if pin.get("sha256") != row["legend_sha256"]:
            raise ValueError("image interpretation must reference its exact pinned user legend")
        if row.get("legend_document_json") is not None:
            raise ValueError("retained legend documents are generated from pinned inputs, not supplied")
        row["legend_document_json"] = _checked(root, pin).read_bytes().decode("utf-8")
        _validate_legend_document(row, pins)


def _annotation_rows(value, name: str) -> list[dict]:
    try:
        rows = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid {name}") from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{name} must contain annotation objects")
    return rows


def _annotation_identity(row: dict) -> tuple:
    # Interpretation changes side/role/order, never the transcribed annotation.
    return tuple(str(row.get(key)) for key in (
        "label", "source_label", "source_text", "annotation_text", "price_low", "price_high", "product", "contract"))


def _unpriced_identity(row: dict) -> tuple:
    return tuple(row.get(key) for key in ("source_label", "annotation_text", "price_low", "price_high"))


def _validate_same_image_revision(previous: dict, current: dict,
                                  previous_levels: list[dict], current_levels: list[dict]) -> None:
    if (previous.get("evidence_basis") != "user_supplied_image"
            or current.get("evidence_basis") != "user_supplied_image"
            or current.get("interpretation_basis") != COLOR_INTERPRETATION):
        raise ValueError("only an explicitly interpreted image can supersede a prior image observation")
    for key in ("session_date", "raw_evidence_path", "raw_evidence_sha256", "contract", "product",
                "date_source_text", "displayed_time_text", "image_timezone", "available_at"):
        if previous.get(key) != current.get(key):
            raise ValueError(f"superseded image {key} must remain unchanged")
    if Counter(map(_annotation_identity, previous_levels)) != Counter(map(_annotation_identity, current_levels)):
        raise ValueError("image interpretation must preserve every exact priced annotation")
    previous_unpriced = _annotation_rows(previous.get("unpriced_annotations_json", []), "prior unpriced annotations")
    current_unpriced = _annotation_rows(current.get("unpriced_annotations_json", []), "unpriced annotations")
    if Counter(map(_unpriced_identity, previous_unpriced)) != Counter(map(_unpriced_identity, current_unpriced)):
        raise ValueError("image interpretation must preserve every exact unpriced annotation")


def _select_observation_revisions(observations: list[dict], levels: list[dict], *, version: str
                                  ) -> tuple[list[dict], list[dict]]:
    by_id, active, level_groups = {}, {}, defaultdict(list)
    for row in levels:
        level_groups[row.get("observation_id")].append(row)
    for row in observations:
        oid = row.get("observation_id")
        if not oid or oid in by_id:
            raise ValueError("missing or duplicate observation identity")
        if row.get("superseded_observation_json") is not None or row.get("superseded_levels_json") is not None:
            raise ValueError("superseded observation snapshots are generated from pinned inputs, not supplied")
        previous_id = row.get("supersedes_observation_id")
        if previous_id:
            if int(_release_identity(version).version.split(".")[0]) < 19:
                raise ValueError("image supersession requires release version 19 or newer")
            previous = active.get(previous_id)
            if previous is None:
                raise ValueError("superseded observation must be an earlier active pinned input")
            _validate_same_image_revision(previous, row, level_groups[previous_id], level_groups[oid])
            row["superseded_observation_json"] = _json(previous).decode().strip()
            row["superseded_levels_json"] = _json(level_groups[previous_id]).decode().strip()
            del active[previous_id]
        by_id[oid] = row
        active[oid] = row
    if set(level_groups) - set(by_id):
        raise ValueError("orphan observation level")
    return list(active.values()), [row for row in levels if row.get("observation_id") in active]


def build_tables(root: Path | str, input_spec: dict, *, version: str = VERSION
                 ) -> tuple[dict[str, pa.Table], list[dict]]:
    """Verify explicit inputs and prepare the union without writing any files."""
    release = _release_identity(version)
    root = Path(root).resolve()
    start, end = _date(input_spec.get("start_date")), _date(input_spec.get("end_date"))
    if start is None or end is None or end < start:
        raise ValueError("explicit inclusive start_date/end_date are required")
    pins = input_spec.get("historical_releases")
    if not isinstance(pins, list) or not pins:
        raise ValueError("an explicit historical release list is required")
    inputs, datasets = [], []
    schema_inputs = defaultdict(list)
    all_coverage = []
    seen_datasets = set()
    for pin in pins:
        manifest, tables, records = _source_release(root, pin)
        identity = manifest["dataset_id"]
        if identity in seen_datasets:
            raise ValueError("duplicate historical dataset")
        seen_datasets.add(identity)
        inputs.extend(records)
        converted = {name: table.to_pylist() for name, table in tables.items()}
        datasets.append((tuple(map(int, manifest["version"].split("."))), identity, converted))
        for name, table in tables.items():
            if name != "coverage":
                schema_inputs[name].append(table.schema)
            else:
                schema_inputs["source_coverage"].append(table.schema)
        all_coverage.extend({**row, "source_dataset_id": identity} for row in converted.get("coverage", []))
    update_pin = input_spec.get("update")
    additional_updates = input_spec.get("additional_updates", [])
    if not isinstance(update_pin, dict):
        raise ValueError("an explicitly pinned update document is required")
    if (not isinstance(additional_updates, list)
            or any(not isinstance(pin, dict) for pin in additional_updates)):
        raise ValueError("additional_updates must be an explicit list of pinned documents")
    observations, observation_levels, coverage_overrides = [], [], {}
    for update_index, pin in enumerate([update_pin, *additional_updates]):
        update_path = _checked(root, pin)
        update = json.loads(update_path.read_text())
        update_id = update.get("dataset_id")
        if not isinstance(update_id, str) or not update_id or update_id in seen_datasets:
            raise ValueError("update needs a unique dataset_id")
        seen_datasets.add(update_id)
        update_tables = update.get("tables", {})
        if not isinstance(update_tables, dict) or set(update_tables) - set(TABLES):
            raise ValueError("unsupported update tables")
        if any(not isinstance(rows, list) for rows in update_tables.values()):
            raise ValueError("update table rows must be lists")
        if any(not isinstance(row, dict) for rows in update_tables.values() for row in rows):
            raise ValueError("update rows must be objects")
        converted = {name: [_normal_row(row) for row in rows] for name, rows in update_tables.items()}
        # Explicit list order gives later reviewed updates deterministic precedence;
        # each update keeps its original lineage identity and evidence document.
        datasets.append(((13, 0, update_index), update_id, converted))
        observations.extend(converted.get("observations", []))
        observation_levels.extend(converted.get("observation_levels", []))
        inputs.append(_record(update_path, root))
        for record in update.get("files", []):
            _checked(root, record)
            inputs.append(record)
        update_coverage = [_normal_row(row) for row in update.get("coverage", [])]
        if len({row.get("session_date") for row in update_coverage}) != len(update_coverage):
            raise ValueError("duplicate update coverage date within one document")
        all_coverage.extend({**row, "source_dataset_id": update_id} for row in update_coverage)
        for row in update_coverage:
            day = row.get("session_date")
            if day is None or not start <= day <= end:
                raise ValueError("invalid update coverage date")
            coverage_overrides[day] = row
    update_coverage = list(coverage_overrides.values())
    _prepare_color_interpretations(root, observations, inputs, version=release.version)
    observations, observation_levels = _select_observation_revisions(
        observations, observation_levels, version=release.version)

    # The old sample hashed raw Atom content; history releases hash its visible
    # text. Exact raw source hashes prove equivalence despite different IDs.
    groups, by_id, by_raw = [], {}, {}
    orphan_issues = []
    for version, identity, tables in sorted(datasets):
        source_rows = tables.get("outlooks", [])
        if len({row.get("outlook_id") for row in source_rows}) != len(source_rows):
            raise ValueError("duplicate outlook_id within an input release")
        level_groups, issue_groups = defaultdict(list), defaultdict(list)
        source_ids = {row.get("outlook_id") for row in source_rows}
        for level in tables.get("levels", []):
            if level.get("outlook_id") not in source_ids:
                raise ValueError("input level has no source parent")
            if level.get("evidence_basis") not in (None, "captured_source"):
                raise ValueError("image observations and recollections cannot become canonical levels")
            level_groups[level["outlook_id"]].append(level)
        for issue in tables.get("issues", []):
            oid = issue.get("outlook_id")
            if oid is not None and oid not in source_ids:
                raise ValueError("input issue has no source parent")
            if oid is None:
                orphan_issues.append({**issue, "primary_source_dataset": identity})
            else:
                issue_groups[oid].append(issue)
        for source in source_rows:
            oid = source.get("outlook_id")
            if not isinstance(oid, str) or not oid:
                raise ValueError("source outlook_id is required")
            raw = (source.get("source_post_id"), source.get("raw_html_sha256"), source.get("raw_atom_sha256"))
            raw_key = raw if raw[0] and any(raw[1:]) else None
            id_group, raw_group = by_id.get(oid), by_raw.get(raw_key) if raw_key else None
            if id_group is not None and raw_group is not None and id_group != raw_group:
                raise ValueError("inconsistent revision-equivalence graph")
            index = id_group if id_group is not None else raw_group
            if index is None:
                index = len(groups)
                groups.append([])
            for prior in groups[index]:
                for key in ("source_post_id",):
                    if prior["row"].get(key) != source.get(key):
                        raise ValueError(f"conflicting {key} for equivalent source revision")
                if prior["row"]["outlook_id"] == oid and prior["row"].get("content_sha256") != source.get("content_sha256"):
                    raise ValueError("conflicting content identity for identical outlook_id")
            groups[index].append({"row": source, "dataset": identity, "version": version,
                                  "levels": level_groups[oid], "issues": issue_groups[oid]})
            by_id[oid] = index
            if raw_key:
                by_raw[raw_key] = index

    qualified = input_spec.get("qualified_date_conflicts", [])
    if not isinstance(qualified, list) or any(not isinstance(row, dict) for row in qualified):
        raise ValueError("qualified_date_conflicts must be an explicit list")
    used_qualifications = set()
    selected_groups = []
    for group in groups:
        dates = {entry["row"].get("session_date") for entry in group}
        qualification = None
        if len(dates) > 1:
            assignments = {entry["dataset"]: str(entry["row"].get("session_date") or "") for entry in group}
            ids = {entry["row"]["outlook_id"] for entry in group}
            for index, candidate in enumerate(qualified):
                if (candidate.get("source_outlook_id") in ids
                        and candidate.get("assignments") == assignments
                        and isinstance(candidate.get("reason"), str) and candidate["reason"].strip()):
                    if qualification is not None:
                        raise ValueError("duplicate date-conflict qualification")
                    qualification = candidate
                    used_qualifications.add(index)
            if qualification is None:
                raise ValueError("conflicting session_date for equivalent source revision; explicit qualification required")
        for day in sorted(dates, key=lambda value: str(value or "")):
            selected_groups.append(([entry for entry in group if entry["row"].get("session_date") == day], qualification))
    if used_qualifications != set(range(len(qualified))):
        raise ValueError("unused or unmatched date-conflict qualification")

    rows = {name: [] for name in TABLES}
    rows["source_coverage"] = all_coverage
    rows["issues"] = orphan_issues
    rows["observations"] = observations
    rows["observation_levels"] = observation_levels
    for group, qualification in selected_groups:
        primary = max(group, key=lambda entry: (entry["version"], entry["dataset"]))
        source = primary["row"]
        revision_id, identity = source["outlook_id"], primary["dataset"]
        oid = (hashlib.sha256((revision_id + "\n" + str(source.get("session_date") or "")
                             + "\nqualified_date_conflict").encode()).hexdigest()
               if qualification else revision_id)
        evidence = source.get("evidence_basis", "captured_source")
        if evidence != "captured_source":
            raise ValueError("canonical outlooks require captured_source; recollections belong in observations")
        row = {**source, "outlook_id": oid, "source_revision_id": revision_id,
               "primary_source_dataset": identity, "evidence_basis": evidence}
        row.setdefault("level_count", len(primary["levels"]))
        row.setdefault("issue_count", len(primary["issues"]))
        row.setdefault("extraction_status", "complete" if primary["levels"] else "failed")
        rows["outlooks"].append(row)
        rows["levels"].extend({**level, "outlook_id": oid, "primary_source_dataset": identity,
                               "evidence_basis": evidence} for level in primary["levels"])
        rows["issues"].extend({**issue, "outlook_id": oid, "primary_source_dataset": identity}
                              for issue in primary["issues"])
        if qualification:
            rows["issues"].append({"issue_id": hashlib.sha256((oid + "\ndate_conflict").encode()).hexdigest(),
                "outlook_id": oid, "session_date": source.get("session_date"), "source_url": source.get("source_url"),
                "severity": "warning", "scope": "cross_release", "code": "cross_release_session_date_conflict",
                "description": "Conflicting historical date assignments preserved without adjudication. " + qualification["reason"],
                "source_text": json.dumps(qualification, sort_keys=True), "primary_source_dataset": identity})
            row["issue_count"] = len(primary["issues"]) + 1
        for member in group:
            rows["release_membership"].append({"source_dataset_id": member["dataset"],
                "source_outlook_id": member["row"]["outlook_id"], "outlook_id": oid,
                "session_date": member["row"].get("session_date"), "source_level_count": len(member["levels"]),
                "selected_primary": member is primary})
    rows["coverage"] = _coverage(rows, start, end, update_coverage)
    for name, values in rows.items():
        values.sort(key=lambda row: (str(row.get("session_date") or ""), str(row.get("outlook_id") or ""),
                                    str(row.get("observation_id") or ""), str(row.get("source_dataset_id") or ""),
                                    str(row.get("side") or ""), str(row.get("role") or ""),
                                    row.get("ordinal") or 0, str(row.get("issue_id") or "")))
    tables = {name: _table(name, values, schema_inputs[name], version=release.version)
              for name, values in rows.items()}
    validate_tables(tables, start, end)
    # One input file may be referenced by several releases, but its identity must
    # agree everywhere. This inventory is also rechecked before promotion.
    distinct = {}
    for record in inputs:
        current = {key: record[key] for key in ("path", "sha256", "bytes") if key in record}
        previous = distinct.get(current["path"])
        if previous and any(previous.get(key) != current.get(key) for key in ("sha256", "bytes")):
            raise ValueError("conflicting pinned input file identities")
        distinct[current["path"]] = current
    _validate_image_pins(tables, list(distinct.values()), version=release.version)
    return tables, [distinct[key] for key in sorted(distinct)]


def _coverage(rows: dict, start: date, end: date, updates: list[dict]) -> list[dict]:
    by_date = {name: defaultdict(list) for name in ("outlooks", "levels", "issues", "observations", "source_coverage")}
    for name, mapping in by_date.items():
        for row in rows[name]:
            if row.get("session_date"):
                mapping[row["session_date"]].append(row)
    update_by_date = {}
    for row in updates:
        day = row.get("session_date")
        if day is None or not start <= day <= end or day in update_by_date:
            raise ValueError("invalid or duplicate update coverage date")
        update_by_date[day] = row
    has_images = any(row.get("evidence_basis") == "user_supplied_image" for row in rows["observations"])
    image_levels = Counter(row.get("session_date") for row in rows["observation_levels"]
                           if row.get("evidence_basis") == "user_supplied_image")
    result, day = [], start
    while day <= end:
        posts = by_date["outlooks"][day]
        observations = by_date["observations"][day]
        images = [row for row in observations if row.get("evidence_basis") == "user_supplied_image"]
        override = update_by_date.get(day, {})
        if posts:
            status = "post_captured"
            reason = "One or more pinned captured revisions state this date; historical availability remains unverified."
        elif images:
            status = "image_observation_only"
            reason = "Supplied chart images are retained as observations, with any prior notes; no canonical captured daily blog plan is available."
        elif any(obs.get("observation_kind") != "no_plan_reported" for obs in observations):
            status = "user_observation_only"
            reason = "Only retrospective user-supplied observations are retained; no canonical captured plan is available."
        else:
            status = "no_post_observed"
            reason = "No dated captured outlook in selected inputs; observed absence does not prove no historical post existed."
        # Capture/exhaustion/pending qualifications can refine an absent date,
        # but cannot replace observed source records or recollections with absence.
        if not posts and not any(obs.get("observation_kind") != "no_plan_reported" for obs in observations) and override:
            status = override.get("status", status)
            reason = override.get("reason", reason)
        # Preserve fresh discovery timestamps, HTTP outcomes and other supplied
        # qualifications alongside reconstructed counts and primary status.
        row = {**override, "session_date": day, "status": status, "reason": reason,
               "post_count": len(posts), "level_count": len(by_date["levels"][day]),
               "issue_count": len(by_date["issues"][day]), "observation_count": len(observations),
               "source_coverage_count": len(by_date["source_coverage"][day]),
               "complete_post_count": sum(p.get("extraction_status") == "complete" for p in posts),
               "partial_post_count": sum(p.get("extraction_status") == "partial" for p in posts),
               "failed_post_count": sum(p.get("extraction_status") in {"failed", "failed_numeric_extraction"} for p in posts),
               "non_outlook_post_count": sum(p.get("content_kind") == "commentary_without_explicit_daily_plan" for p in posts),
               "post_urls_json": json.dumps(sorted({p["source_url"] for p in posts if p.get("source_url")})),
               "outlook_ids_json": json.dumps(sorted(p["outlook_id"] for p in posts))}
        if has_images:
            row.update(image_observation_count=len(images), image_level_count=image_levels[day])
        result.append(row)
        day += timedelta(days=1)
    return result


def validate_tables(tables: dict[str, pa.Table], start: date | str, end: date | str) -> None:
    """Validate relational integrity and missingness, never market accuracy."""
    start, end = _date(start), _date(end)
    if set(tables) != set(TABLES):
        raise ValueError("unsupported consolidated table inventory")
    rows = {name: table.to_pylist() for name, table in tables.items()}
    parents = {}
    for row in rows["outlooks"]:
        oid = row.get("outlook_id")
        if not oid or oid in parents:
            raise ValueError("missing or duplicate canonical outlook_id")
        parents[oid] = row
        if row.get("evidence_basis") != "captured_source" or row.get("available_at") is not None:
            raise ValueError("canonical capture evidence and null availability are required")
        if row.get("timing_status") != TIMING_STATUS:
            raise ValueError("historical timing status must remain unverified")
        if row.get("session_date") and not start <= row["session_date"] <= end:
            raise ValueError("outlook date outside declared calendar")
    seen, counts = set(), Counter()
    for row in rows["levels"]:
        parent = parents.get(row.get("outlook_id"))
        key = (row.get("outlook_id"), row.get("side"), row.get("role"), row.get("ordinal"))
        if parent is None or key in seen:
            raise ValueError("orphan or duplicate level key")
        seen.add(key)
        if row.get("side") not in {"bullish", "bearish"} or row.get("role") not in {"trigger", "target"}:
            raise ValueError("unsupported canonical side or level role")
        if not isinstance(row.get("ordinal"), int) or row["ordinal"] < 1:
            raise ValueError("level ordinal must be positive")
        if row.get("session_date") is None or row["session_date"] != parent.get("session_date"):
            raise ValueError("level date differs from its source parent")
        for name in ("contract", "product"):
            if name in row and name in parent and row[name] != parent[name]:
                raise ValueError(f"level {name} differs from source parent")
        if row.get("price_low") is None or row.get("price_high") is None or row["price_low"] > row["price_high"]:
            raise ValueError("missing or descending price bounds")
        if row.get("available_at") is not None or row.get("timing_status") != TIMING_STATUS:
            raise ValueError("level availability must remain null and unverified")
        if row.get("evidence_basis") != "captured_source":
            raise ValueError("canonical levels require captured_source evidence")
        counts[row["outlook_id"]] += 1
    for oid, parent in parents.items():
        if parent.get("level_count") != counts[oid]:
            raise ValueError("canonical source level count differs from selected projection")
    issue_keys = set()
    for row in rows["issues"]:
        key = (row.get("primary_source_dataset"), row.get("issue_id"))
        if not row.get("issue_id") or key in issue_keys:
            raise ValueError("missing or duplicate source issue identity")
        issue_keys.add(key)
        if row.get("outlook_id") is not None and row["outlook_id"] not in parents:
            raise ValueError("orphan issue")
    members, primary_counts = set(), Counter()
    for row in rows["release_membership"]:
        key = (row.get("source_dataset_id"), row.get("source_outlook_id"))
        if key in members or row.get("outlook_id") not in parents:
            raise ValueError("duplicate or orphan release membership")
        members.add(key)
        if row.get("selected_primary"):
            primary_counts[row["outlook_id"]] += 1
    if any(primary_counts[oid] != 1 for oid in parents):
        raise ValueError("every canonical revision requires one primary membership")
    obs = {}
    for row in rows["observations"]:
        identity = row.get("observation_id")
        if not identity or identity in obs or row.get("available_at") is not None:
            raise ValueError("invalid observation identity or availability")
        if row.get("evidence_basis") not in OBSERVATION_EVIDENCE:
            raise ValueError("unsupported observation evidence basis")
        if row.get("session_date") and not start <= row["session_date"] <= end:
            raise ValueError("observation date outside declared calendar")
        if row.get("evidence_basis") == "user_supplied_image":
            path = row.get("raw_evidence_path")
            if (row.get("observation_kind") != "chart_image" or row.get("session_date") is None
                    or not isinstance(path, str) or not path.startswith("data/raw/user/verniman/")
                    or ".." in Path(path).parts
                    or not re.fullmatch(r"[0-9a-f]{64}", row.get("raw_evidence_sha256") or "")
                    or not isinstance(row.get("date_source_text"), str) or not row["date_source_text"].strip()
                    or not isinstance(row.get("displayed_time_text"), str) or not row["displayed_time_text"].strip()
                    or row.get("timing_status") != TIMING_STATUS):
                raise ValueError("image observations require dated chart evidence, exact image provenance and unverified timing")
            if row.get("interpretation_basis") not in (None, COLOR_INTERPRETATION):
                raise ValueError("unsupported image interpretation basis")
            if row.get("interpretation_basis") == COLOR_INTERPRETATION:
                legend_path = row.get("legend_path")
                if (not isinstance(legend_path, str) or not legend_path.startswith("data/raw/user/verniman/")
                        or ".." in Path(legend_path).parts
                        or not re.fullmatch(r"[0-9a-f]{64}", row.get("legend_sha256") or "")):
                    raise ValueError("image interpretation requires exact raw user legend provenance")
                for annotation in _annotation_rows(row.get("unpriced_annotations_json", []), "unpriced annotations"):
                    expected = COLOR_ROLES.get(annotation.get("source_color"))
                    if (expected is None or any(annotation.get(key) != value for key, value in expected.items())
                            or annotation.get("price_low") is not None or annotation.get("price_high") is not None
                            or not isinstance(annotation.get("ordinal"), int)
                            or isinstance(annotation.get("ordinal"), bool) or annotation["ordinal"] < 1
                            or not annotation.get("annotation_text") or not annotation.get("source_label")):
                        raise ValueError("unpriced image annotations require declared color roles and null prices")
            elif row.get("supersedes_observation_id"):
                raise ValueError("image supersession requires an explicit user color interpretation")
        obs[identity] = row
    obs_keys = set()
    for row in rows["observation_levels"]:
        parent = obs.get(row.get("observation_id"))
        key = (row.get("observation_id"), row.get("side"), row.get("role"), row.get("ordinal"))
        if parent is None or key in obs_keys:
            raise ValueError("orphan or duplicate observation level")
        obs_keys.add(key)
        if row.get("session_date") != parent.get("session_date"):
            raise ValueError("observation level date differs from its parent")
        if row.get("price_low") is None or row.get("price_high") is None or row["price_low"] > row["price_high"]:
            raise ValueError("invalid observation level bounds")
        if row.get("evidence_basis") != parent.get("evidence_basis"):
            raise ValueError("observation levels must retain their parent evidence basis")
        if parent.get("evidence_basis") == "user_supplied_image":
            if (not isinstance(row.get("ordinal"), int) or isinstance(row.get("ordinal"), bool)
                    or row["ordinal"] < 1
                    or not isinstance(row.get("label"), str) or not row["label"].strip()
                    or not isinstance(row.get("source_text"), str) or not row["source_text"].strip()
                    or row.get("available_at") is not None or row.get("timing_status") != TIMING_STATUS):
                raise ValueError("image levels require labeled annotations, positive ordinals and null availability")
            if parent.get("interpretation_basis") == COLOR_INTERPRETATION:
                expected = COLOR_ROLES.get(row.get("source_color"))
                if (row.get("interpretation_basis") != COLOR_INTERPRETATION or expected is None
                        or any(row.get(key) != value for key, value in expected.items())):
                    raise ValueError("image pivot and target roles require the exact user color legend mapping")
            elif row.get("side") != "neutral" or row.get("role") != "reference" or row.get("interpretation_basis") is not None:
                raise ValueError("uninterpreted image levels require neutral references")
            for name in ("contract", "product"):
                if name in row and name in parent and row[name] != parent[name]:
                    raise ValueError(f"image level {name} differs from its source parent")
    for parent in obs.values():
        if parent.get("interpretation_basis") == COLOR_INTERPRETATION:
            for annotation in _annotation_rows(parent.get("unpriced_annotations_json", []), "unpriced annotations"):
                key = (parent["observation_id"], annotation["side"], annotation["role"], annotation["ordinal"])
                if key in obs_keys:
                    raise ValueError("duplicate priced or unpriced image role/order slot")
                obs_keys.add(key)
            slots = [key for key in obs_keys if key[0] == parent["observation_id"]]
            if sum(role == "trigger" for _, _, role, _ in slots) > 1:
                raise ValueError("a color-interpreted image can retain at most one labeled pivot")
            for side in ("bullish", "bearish"):
                orders = sorted(ordinal for _, actual_side, role, ordinal in slots if actual_side == side and role == "target")
                if orders != list(range(1, len(orders) + 1)):
                    raise ValueError("image target order must retain contiguous priced and unpriced annotation slots")
        if not parent.get("supersedes_observation_id"):
            continue
        try:
            previous = _normal_row(json.loads(parent["superseded_observation_json"]))
            previous_levels = [_normal_row(row) for row in _annotation_rows(parent["superseded_levels_json"], "superseded levels")]
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("image supersession requires its retained exact prior interpretation") from exc
        if previous.get("observation_id") != parent["supersedes_observation_id"] or any(
                row.get("observation_id") != previous["observation_id"] for row in previous_levels):
            raise ValueError("retained superseded image identity differs from its pointer")
        current_levels = [row for row in rows["observation_levels"] if row.get("observation_id") == parent["observation_id"]]
        _validate_same_image_revision(previous, parent, previous_levels, current_levels)
    expected = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    actual = [row.get("session_date") for row in rows["coverage"]]
    if actual != expected:
        raise ValueError("coverage must contain each declared calendar date exactly once in order")
    # Reconstruct counts independently from the canonical rows.
    expected_coverage = _coverage(rows, start, end, [])
    for row, rebuilt in zip(rows["coverage"], expected_coverage):
        count_keys = ["post_count", "level_count", "issue_count", "observation_count", "source_coverage_count"]
        count_keys.extend(key for key in ("image_observation_count", "image_level_count") if key in rebuilt)
        for key in count_keys:
            if row.get(key) != rebuilt[key]:
                raise ValueError(f"coverage count mismatch: {key}")


def _csv(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=table.column_names)
        writer.writeheader()
        for row in table.to_pylist():
            writer.writerow({key: "" if value is None else _json_scalar(value)
                             if isinstance(value, (date, datetime, Decimal)) else value for key, value in row.items()})


def _schema_document(tables: dict[str, pa.Table], *, version: str = VERSION) -> dict:
    release = _release_identity(version)
    document = {"dataset_id": release.dataset_id, "version": release.version,
            "tables": {name: [{"name": f.name, "arrow_type": str(f.type), "nullable": f.nullable}
                              for f in table.schema] for name, table in tables.items()},
            "identity_policy": "Same outlook_id or same source_post_id and exact retained HTML/Atom hashes; newest input version wins within a consistent date assignment; original IDs survive in release_membership.",
            "distinct_revisions": "Never deduplicate by session_date. Unknown date conflicts are refused; explicitly qualified historical conflicts retain both projections with contextual canonical IDs and original source_revision_id, without adjudication.",
            "timing": "All available_at null. Retrospective user read times are claims in observations, not verified historical availability.",
            "historical_semantics": "Selected saved extraction projections are copied without historical re-extraction or scientific reassessment.",
            "date_filter": "load_release start_date inclusive, end_date exclusive; undated records only returned without date bounds."}
    # Earlier pinned schemas remain exact saved contracts. The image observation
    # policy is additive for new releases, never a rewrite of versions 13–15.
    if int(release.version.split(".")[0]) >= 16:
        document["observation_evidence"] = "User recollections and supplied chart images retain distinct evidence_basis values. Image rows are exact printed labeled references only, never inferred blog pivots/targets; unpriced annotations stay in observation notes."
        document["timing"] += " Displayed image clocks retain their source text and do not establish timezone or historical availability."
    if int(release.version.split(".")[0]) >= 19:
        document["observation_evidence"] = "Supplied images remain distinct from captured blog plans. Explicitly pinned user color legends may classify light-blue labeled lines as pivots and green/red lines as bullish/bearish targets. Numeric annotations remain exact; unpriced annotations retain null prices. Explicit same-image interpretation supersession retains exact prior parent/child snapshots and all original input pins."
        document["image_color_roles"] = COLOR_ROLES
    return document


def _quality(tables: dict[str, pa.Table], start: date, end: date, *, version: str = VERSION) -> bytes:
    release = _release_identity(version)
    posts = tables["outlooks"].to_pylist()
    dated = sorted({p["session_date"] for p in posts if p.get("session_date")})
    revisions = {p["source_revision_id"] for p in posts}
    conflict_projections = sum(row.get("code") == "cross_release_session_date_conflict"
                               for row in tables["issues"].to_pylist())
    coverage = Counter(tables["coverage"]["status"].to_pylist())
    observation_counts = Counter(row.get("evidence_basis") for row in tables["observations"].to_pylist())
    image_count = observation_counts["user_supplied_image"]
    image_level_count = sum(row.get("evidence_basis") == "user_supplied_image"
                            for row in tables["observation_levels"].to_pylist())
    if image_count:
        observation_text = (f"User recollections: {observation_counts['user_supplied_recollection']}; supplied chart-image observations: {image_count}; "
                            f"image reference rows: {image_level_count}; total observation levels: {tables['observation_levels'].num_rows}. ")
        if int(release.version.split(".")[0]) >= 19:
            interpreted = sum(row.get("interpretation_basis") == COLOR_INTERPRETATION
                              for row in tables["observations"].to_pylist())
            observation_text = (f"User recollections: {observation_counts['user_supplied_recollection']}; supplied chart-image observations: {image_count}; "
                                f"image numeric annotation rows: {image_level_count}; user color interpretations: {interpreted}; "
                                f"total observation levels: {tables['observation_levels'].num_rows}. ")
    else:
        observation_text = f"Retrospective user observations: {tables['observations'].num_rows}; observation levels: {tables['observation_levels'].num_rows}. "
    text = (f"# Verniman consolidated daily levels {release.version}\n\n"
            f"Declared inclusive calendar: {start} through {end}. Canonical saved source projections: {len(posts)}; "
            f"distinct primary source revision IDs: {len(revisions)}; "
            f"distinct dated outlooks: {len(dated)}; numeric level rows: {tables['levels'].num_rows}. "
            f"Observed dated range: {dated[0] if dated else 'none'} through {dated[-1] if dated else 'none'}.\n\n"
            + observation_text
            + "These remain separate from captured-source plans and never supply missing canonical targets or labels.\n\n"
            "The original twelve releases remain unchanged. Canonical revisions use the latest saved extraction for equivalent exact source captures; "
            "release_membership maps every original revision ID to its selected canonical ID. Different revisions and duplicate dates remain. "
            "Pinned source releases retain discarded extraction projections and all prior qualifications. source_coverage preserves their original date ledgers.\n\n"
            f"Explicitly qualified conflicting-date projections: {conflict_projections}. These retain both historical date assignments "
            "with contextual canonical IDs, the original source_revision_id and cross_release_session_date_conflict issues; neither date is adjudicated.\n\n"
            "All available_at values remain null. Source timestamp claims, fresh capture times and user-reported read times do not establish historical pre-open availability. "
            "No source prices are adjusted, interpolated or silently corrected. Chart-only user references remain observations. "
            "The complete calendar is an observed retrieval ledger, not exchange eligibility or proof of original source completeness.\n\n"
            "## Coverage status\n\n| Status | Calendar dates |\n|---|---:|\n"
            + "\n".join(f"| {key} | {value} |" for key, value in sorted(coverage.items()))
            + "\n\nValidation checks pinned bytes, schema/relational consistency, duplicate-capture mapping and calendar accounting. "
              "It does not revalidate the historical extraction methods, underlying market prices or strategy performance.\n")
    return text.encode()


def publish_release(root: Path | str, input_spec_path: Path | str, request_path: Path | str,
                    *, version: str = VERSION) -> Path:
    """Publish a new immutable consolidated snapshot from explicit input pins."""
    release = _release_identity(version)
    root = Path(root).resolve()
    spec_path, request = _path(root, input_spec_path), _path(root, request_path)
    spec_record, request_record = _record(spec_path, root), _record(request, root)
    spec = json.loads(spec_path.read_text())
    finals = [root / release.data_path, root / release.manifest_path, root / release.schema_path, root / release.quality_path]
    inventory = finals + [path.with_name(path.name + ".part") for path in finals[1:]]
    stage = root / "data/staging/verniman" / f"consolidated-v{release.version}"
    for path in [*inventory, stage]:
        check_absent(path, root)
    tables, input_files = build_tables(root, spec, version=release.version)
    stage.mkdir(parents=True)
    prepared = stage / "curated"
    prepared.mkdir()
    (stage / "input-spec.json").write_bytes(spec_path.read_bytes())
    declared = provenance.publication_sources(Path(__file__), (
        "provenance.py", "publication_safety.py", "paths.py", "verniman_history.py",
        "verniman_levels.py", "verniman_backfill.py", "verniman_capture.py"))
    retained = provenance.retain_sources(prepared / "provenance", declared, artifact_id=release.dataset_id, root=root)
    table_records = {}
    for name, table in tables.items():
        _csv(prepared / f"{name}.csv", table)
        paths = []
        if name in PARTITIONED:
            grouped = defaultdict(list)
            for row in table.to_pylist():
                grouped[str(row["session_date"].year) if row.get("session_date") else "undated"].append(row)
            if not grouped:
                grouped["undated"] = []
            for year, rows in sorted(grouped.items()):
                relative = Path(name) / f"year={year}" / "part-000.parquet"
                destination = prepared / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), destination, compression="zstd")
                paths.append(str(release.data_path / relative))
        else:
            relative = Path(f"{name}.parquet")
            pq.write_table(table, prepared / relative, compression="zstd")
            paths.append(str(release.data_path / relative))
        table_records[name] = {"paths": paths, "rows": table.num_rows, "csv_path": str(release.data_path / f"{name}.csv"),
                               "partitioning": "year of stated session date; undated bucket" if name in PARTITIONED else None}
    # A human-readable daily view deliberately keeps revisions separate.
    summary_columns = [name for name in ("session_date", "contract", "title", "outlook_id", "source_url", "extraction_status",
        "level_count", "issue_count", "bullish_scenario_text", "bearish_scenario_text", "available_at", "timing_status", "primary_source_dataset")
        if name in tables["outlooks"].column_names]
    _csv(prepared / "daily_summary.csv", tables["outlooks"].select(summary_columns))
    evidence = prepared / "provenance" / "inputs"
    evidence.mkdir()
    (evidence / "input-spec.json").write_bytes(spec_path.read_bytes())
    update_pins = [spec["update"], *spec.get("additional_updates", [])]
    update_records = {}
    for index, pin in enumerate(update_pins):
        update_path = _checked(root, pin)
        name = "update.json" if index == 0 else f"additional-update-{index:03d}.json"
        (evidence / name).write_bytes(update_path.read_bytes())
        for record in json.loads(update_path.read_text()).get("files", []):
            update_records[record["path"]] = record
    (evidence / "request.yaml").write_bytes(request.read_bytes())
    # Preserve preparation scripts and review receipts from every explicitly
    # pinned update. Bulk captures remain in the raw layer with pinned hashes.
    update_evidence = []
    for path, record in sorted(update_records.items()):
        if not path.startswith(("data/staging/verniman/", "data/raw/user/verniman/")):
            continue
        incoming = _checked(root, record)
        relative = Path("provenance/update-evidence") / path
        destination = prepared / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(incoming.read_bytes())
        if provenance.sha256_file(destination) != record["sha256"]:
            raise ValueError("retained update evidence changed while copying")
        update_evidence.append({"original_path": path, "path": str(release.data_path / relative),
                                "sha256": record["sha256"], "bytes": destination.stat().st_size})
    schema_bytes = _json(_schema_document(tables, version=release.version))
    quality_bytes = _quality(tables, _date(spec["start_date"]), _date(spec["end_date"]), version=release.version)
    (stage / "schema.json").write_bytes(schema_bytes)
    (stage / "quality.md").write_bytes(quality_bytes)
    files = []
    for path in sorted(prepared.rglob("*")):
        if path.is_file():
            record = _record(path, prepared)
            record["path"] = str(release.data_path / record["path"])
            files.append(record)
    files.extend({"path": str(path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
                 for path, payload in ((release.schema_path, schema_bytes), (release.quality_path, quality_bytes)))
    manifest = {"dataset_id": release.dataset_id, "version": release.version, "source": "verniman",
        "created_at": datetime.now(timezone.utc).isoformat(), "start_date": spec["start_date"], "end_date": spec["end_date"],
        "available_at_policy": TIMING_STATUS, "input_spec": spec_record, "request": request_record,
        "input_files": input_files, "historical_releases": spec["historical_releases"], "update": spec["update"],
        "additional_updates": spec.get("additional_updates", []),
        "retained_update_evidence": update_evidence,
        "qualified_date_conflicts": spec.get("qualified_date_conflicts", []),
        "files": files, "tables": table_records, "schema_path": str(release.schema_path), "quality_report_path": str(release.quality_path),
        "provenance": {**provenance.git_version(root), "path": str(release.data_path / "provenance"), "retained": retained},
        "publication_invocation": {"entry_point": "abacus_bhishma.verniman_consolidated",
            "reconstruction_argv": ["./scripts/uv", "run", "--locked", "--no-sync", "python", "-m", "abacus_bhishma.verniman_consolidated",
                                    "--root", ".", "--version", release.version, "--input-spec", spec_record["path"], "--request", request_record["path"]]},
        "known_limitations": ["Historical availability unverified; every available_at remains null.",
            "Saved historical extraction projections are preserved, not independently re-extracted or scientifically revalidated.",
            "User recollections remain separate observations and do not repair canonical source records.",
            "Missing dates mean observed retrieval gaps, never proof no historical source post existed."]}
    if any(row.get("evidence_basis") == "user_supplied_image" for row in tables["observations"].to_pylist()):
        if any(row.get("interpretation_basis") == COLOR_INTERPRETATION for row in tables["observations"].to_pylist()):
            manifest["known_limitations"].append(
                "Image pivot/target roles follow the explicitly pinned user color legend. Saved target order includes unpriced annotations and is a display policy, not a verified execution sequence. Images do not recover complete blog plans, delivery contracts, timezone or historical availability.")
        else:
            manifest["known_limitations"].append(
                "Supplied chart images establish printed reference annotations only, not complete blog plans, directional target order, delivery contracts, timezone or historical availability.")
    (stage / "manifest.json").write_bytes(_json(manifest))
    provenance.verify_retained_sources(prepared / "provenance", declared, retained)
    for record in [spec_record, request_record, *input_files]:
        _checked(root, record)
    for path in inventory:
        check_absent(path, root)
    check_path(prepared, root)
    (root / release.data_path).parent.mkdir(parents=True, exist_ok=True)
    prepared.rename(root / release.data_path)
    write_new_bytes(root / release.schema_path, schema_bytes, root)
    write_new_bytes(root / release.quality_path, quality_bytes, root)
    write_new_bytes(root / release.manifest_path, _json(manifest), root)
    result = root / release.manifest_path
    verify_release(root, result, provenance.sha256_file(result), verify_inputs=True)
    return result


def _read_tables(root: Path, manifest: dict) -> dict[str, pa.Table]:
    release = _release_identity(manifest.get("version"))
    by_path = {record["path"]: record for record in manifest["files"]}
    tables = {}
    for name in TABLES:
        record = manifest["tables"][name]
        if record.get("csv_path") != str(release.data_path / f"{name}.csv"):
            raise ValueError("table CSV path is outside its release")
        paths = record.get("paths", [])
        if not paths or len(paths) != len(set(paths)):
            raise ValueError("missing or duplicate table partition inventory")
        parts = []
        for path in paths:
            valid_path = (path.startswith(str(release.data_path / name) + "/")
                          if name in PARTITIONED else path == str(release.data_path / f"{name}.parquet"))
            if path not in by_path or not valid_path:
                raise ValueError("table partition is absent from release inventory or outside its table")
            # ParquetFile avoids automatic Hive partition discovery/type inference.
            parts.append(pq.ParquetFile(_path(root, path)).read())
        table = pa.concat_tables(parts)
        if table.num_rows != record.get("rows"):
            raise ValueError("manifest table count differs from saved partitions")
        tables[name] = table
    # Partitions sort undated after years; restore the calendar's required order.
    tables["coverage"] = tables["coverage"].sort_by([("session_date", "ascending")])
    return tables


def verify_release(root: Path | str, manifest_path: Path | str, expected_manifest_sha256: str,
                   *, verify_bytes: bool = True, verify_inputs: bool = False) -> dict:
    """Verify saved release bytes; audit live original inputs only when requested.

    The release owns its retained source/evidence snapshots. Later edits to live
    package code or staging files cannot invalidate an immutable saved release.
    verify_inputs=True separately audits all original input pins with hashes.
    """
    root = Path(root).resolve()
    selected = _checked(root, {"path": str(manifest_path), "sha256": expected_manifest_sha256})
    manifest = json.loads(selected.read_text())
    release = _release_identity(manifest.get("version"))
    if (manifest.get("dataset_id") != release.dataset_id
            or manifest.get("schema_path") != str(release.schema_path)
            or manifest.get("quality_report_path") != str(release.quality_path)
            or manifest.get("available_at_policy") != TIMING_STATUS
            or set(manifest.get("tables", {})) != set(TABLES)):
        raise ValueError("unsupported consolidated release identity or table inventory")
    files = manifest.get("files", [])
    names = [record.get("path") for record in files]
    required = {str(release.schema_path), str(release.quality_path), str(release.data_path / "daily_summary.csv"),
                str(release.data_path / "provenance/sources.json"),
                *[str(release.data_path / f"{name}.csv") for name in TABLES]}
    if len(names) != len(set(names)) or not required.issubset(names):
        raise ValueError("incomplete or duplicated artifact inventory")
    if any(not isinstance(name, str) or not (
            name.startswith(str(release.data_path) + "/")
            or name in {str(release.schema_path), str(release.quality_path)}) for name in names):
        raise ValueError("artifact inventory crosses release boundaries")
    for record in files:
        _checked(root, record, verify_bytes=verify_bytes)
    if verify_inputs:
        for record in [manifest["input_spec"], manifest["request"], *manifest.get("input_files", [])]:
            _checked(root, record, verify_bytes=True)
    tables = _read_tables(root, manifest)
    _validate_image_pins(tables, manifest.get("input_files", []), version=release.version)
    schema = json.loads(_path(root, manifest["schema_path"]).read_text())
    if schema != _schema_document(tables, version=release.version):
        raise ValueError("schema document differs from saved table schemas")
    validate_tables(tables, manifest["start_date"], manifest["end_date"])
    return manifest


def load_release(root: Path | str, manifest_path: Path | str, expected_manifest_sha256: str,
                 *, table: str = "outlooks", start_date: date | str | None = None,
                 end_date: date | str | None = None, verify_bytes: bool = True) -> pa.Table:
    """Read an explicitly pinned table; start inclusive, end exclusive."""
    if table not in TABLES:
        raise ValueError(f"unsupported consolidated table: {table}")
    root = Path(root).resolve()
    manifest = verify_release(root, manifest_path, expected_manifest_sha256, verify_bytes=verify_bytes)
    result = _read_tables(root, manifest)[table]
    start, end = _date(start_date), _date(end_date)
    if start is not None and end is not None and end < start:
        raise ValueError("end_date precedes start_date")
    if start is not None:
        result = result.filter(pc.greater_equal(result["session_date"], pa.scalar(start, pa.date32())))
    if end is not None:
        result = result.filter(pc.less(result["session_date"], pa.scalar(end, pa.date32())))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--version", default=VERSION, help="New immutable major version; defaults to 13.0.0")
    parser.add_argument("--input-spec", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    result = publish_release(resolve_publication_root(args.root), args.input_spec, args.request, version=args.version)
    print(json.dumps({"manifest": str(result), "manifest_sha256": provenance.sha256_file(result)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
