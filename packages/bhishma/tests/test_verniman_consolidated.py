"""Synthetic checks for the additive Verniman consolidation and pinned reader."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from abacus_bhishma.provenance import sha256_file
from abacus_bhishma import verniman_consolidated as consolidated


def _json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _record(root: Path, path: Path) -> dict:
    return {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path),
            "bytes": path.stat().st_size}


def _post(identity: str = "shared", *, day: date | None = date(2026, 10, 20),
          label: str = "HVE", evidence_basis: str = "captured_source") -> tuple[dict, list[dict]]:
    content_hash = hashlib.sha256(identity.encode()).hexdigest()
    source_id = f"tag:blogger.com,1999:synthetic-{identity}"
    revision = hashlib.sha256((source_id + "\n" + content_hash).encode()).hexdigest()
    row = {
        "outlook_id": revision, "source_post_id": source_id,
        "content_sha256": content_hash,
        "source_url": f"https://verniman.blogspot.com/2009/10/{identity}.html",
        "title": identity, "session_date": day, "product": "ES", "contract": "ESZ26",
        "session_date_method": "explicit_reviewed_body_date", "body_contract_year": 2026,
        "session_date_source_text": "Outlook 10/20; ESZ26 (Dec2026)",
        "captured_at": datetime(2026, 10, 28, 20, tzinfo=timezone.utc),
        "available_at": None, "timing_status": "historical_availability_unverified",
        "body_text": "Synthetic retained source body.",
        "extraction_version": "synthetic", "extraction_status": "complete",
        "content_kind": "daily_outlook", "level_count": 2 if day else 0,
        "parsed_branch_count": 2 if day else 0, "issue_count": 0,
        "evidence_basis": evidence_basis,
    }
    levels = []
    if day:
        for side in ("bullish", "bearish"):
            levels.append({
                "outlook_id": revision, "session_date": day, "product": "ES", "contract": "ESZ26",
                "side": side, "role": "trigger", "ordinal": 1, "source_label": label,
                "source_text": f"{label} 7730", "scenario_text": f"Synthetic {side} source plan.",
                "conditions": f"{side} VIX/CVD", "notation": "point",
                "price_low": Decimal("7730.00"), "price_high": Decimal("7730.00"),
                "available_at": None, "timing_status": "historical_availability_unverified",
                "evidence_basis": evidence_basis,
            })
    return row, levels


_OUTLOOK_SCHEMA = pa.schema([
    pa.field(name, pa.string()) for name in (
        "outlook_id", "source_post_id", "content_sha256", "source_url", "title", "product", "contract",
        "session_date_method", "session_date_source_text", "timing_status", "body_text", "extraction_version",
        "extraction_status", "content_kind", "evidence_basis", "raw_html_sha256", "raw_atom_sha256")
] + [pa.field("session_date", pa.date32()), pa.field("body_contract_year", pa.int16()),
     pa.field("captured_at", pa.timestamp("us", tz="UTC")),
     pa.field("available_at", pa.timestamp("us", tz="UTC")),
     *[pa.field(name, pa.int32()) for name in ("level_count", "parsed_branch_count", "issue_count")]])
_LEVEL_SCHEMA = pa.schema([
    pa.field(name, pa.string()) for name in (
        "outlook_id", "product", "contract", "side", "role", "source_label", "source_text",
        "scenario_text", "conditions", "notation", "timing_status", "evidence_basis")
] + [pa.field("session_date", pa.date32()), pa.field("ordinal", pa.int32()),
     pa.field("price_low", pa.decimal128(12, 2)), pa.field("price_high", pa.decimal128(12, 2)),
     pa.field("available_at", pa.timestamp("us", tz="UTC"))])
_ISSUE_SCHEMA = pa.schema([pa.field(name, pa.string()) for name in (
    "issue_id", "outlook_id", "severity", "scope", "code", "description", "source_url", "side", "source_text")
] + [pa.field("session_date", pa.date32())])
_COVERAGE_SCHEMA = pa.schema([
    pa.field("session_date", pa.date32()), pa.field("status", pa.string()), pa.field("reason", pa.string()),
    pa.field("post_count", pa.int32()), pa.field("level_count", pa.int32())])


def _historical(root: Path, version: int, posts: list[tuple[dict, list[dict]]]) -> dict:
    """Write a small pinned old-style release, without invoking any old publisher."""
    dataset_id = f"verniman_daily_levels__{version}.0.0"
    destination = root / "data/curated/external_levels/source=verniman" / f"version={version}.0.0"
    destination.mkdir(parents=True)
    outlooks = [row for row, _ in posts]
    levels = [level for _, selected in posts for level in selected]
    coverage = [{"session_date": day, "status": "post_captured", "reason": "Synthetic source ledger.",
                 "post_count": sum(row["session_date"] == day for row in outlooks),
                 "level_count": sum(row["session_date"] == day for row in levels)}
                for day in sorted({row["session_date"] for row in outlooks if row["session_date"]})]
    tables = {"outlooks": pa.Table.from_pylist(outlooks, schema=_OUTLOOK_SCHEMA),
              "levels": pa.Table.from_pylist(levels, schema=_LEVEL_SCHEMA),
              "issues": pa.Table.from_pylist([], schema=_ISSUE_SCHEMA),
              "coverage": pa.Table.from_pylist(coverage, schema=_COVERAGE_SCHEMA)}
    inventory, locations = [], {}
    for name, table in tables.items():
        path = destination / f"{name}.parquet"
        pq.write_table(table, path)
        inventory.append(_record(root, path))
        locations[name] = {"path": path.relative_to(root).as_posix(), "rows": table.num_rows}
    path = root / f"catalog/datasets/{dataset_id}.json"
    _json(path, {"dataset_id": dataset_id, "version": f"{version}.0.0", "source": "verniman",
                 "files": inventory, "tables": locations,
                 "available_at_policy": "historical_availability_unverified"})
    return {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def fixture(root: Path, *, with_update: bool = True) -> tuple[Path, Path, dict, dict]:
    shared_old = _post(label="old-extraction")
    shared_new = _post(label="new-extraction")
    duplicate_date = _post("separate-revision")
    undated = _post("undated", day=None)
    old = _historical(root, 1, [shared_old])
    new = _historical(root, 2, [shared_new, duplicate_date, undated])
    update = {"dataset_id": "verniman_update_20261028", "files": [],
              "tables": {"outlooks": [], "levels": [], "issues": [],
                         "observations": [], "observation_levels": []},
              "coverage": [{"session_date": "2026-10-23", "status": "no_dated_plan_verified",
                            "reason": "Explicitly checked source; no dated daily plan verified."}]}
    if with_update:
        row, levels = _post("recent-source", day=date(2026, 10, 28))
        for item in [row, *levels]:
            item["session_date"] = item["session_date"].isoformat()
            for key, value in tuple(item.items()):
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    item[key] = str(value)
        update["tables"]["outlooks"].append(row)
        update["tables"]["levels"].extend(levels)
    update_path = root / "data/staging/verniman/synthetic-update/update.json"
    _json(update_path, update)
    spec = {"historical_releases": [old, new], "update": _record(root, update_path),
            "start_date": "2026-10-20", "end_date": "2026-10-28"}
    spec_path = root / "data/staging/verniman/synthetic-update/input_spec.json"
    _json(spec_path, spec)
    request = root / "requests/fulfilled/consolidated.yaml"
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text("request:\n  id: verniman_daily_levels__13.0.0\n")
    return spec_path, request, spec, update


def _shift_old_date(root: Path, spec: dict, day: date) -> str:
    """Model a saved historical date assignment that disagrees with a later release."""
    pin = spec["historical_releases"][0]
    manifest_path = root / pin["path"]
    manifest = json.loads(manifest_path.read_text())
    source_id = None
    for name in ("outlooks", "levels", "coverage"):
        path = root / manifest["tables"][name]["path"]
        table = pq.ParquetFile(path).read()
        rows = table.to_pylist()
        for row in rows:
            row["session_date"] = day
            source_id = source_id or row.get("outlook_id")
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    manifest["files"] = [_record(root, root / row["path"]) for row in manifest["files"]]
    _json(manifest_path, manifest)
    pin["sha256"] = sha256_file(manifest_path)
    return source_id


def _image_observation(root: Path, day: str = "2026-10-21") -> tuple[dict, dict, dict]:
    """A dated image annotation fixture, independent of any captured blog plan."""
    image = root / f"data/raw/user/verniman/synthetic-images/{day}.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic-chart-" + day.encode())
    pin = _record(root, image)
    identity = "image-" + day
    observation = {
        "observation_id": identity, "session_date": day, "title": "Supplied chart image",
        "source_url": None, "product": "ES", "contract": None,
        "evidence_basis": "user_supplied_image", "observation_kind": "chart_image",
        "raw_evidence_path": pin["path"], "raw_evidence_sha256": pin["sha256"],
        "date_source_text": day, "displayed_time_text": "9:33 AM", "image_timezone": None,
        "available_at": None, "timing_status": "historical_availability_unverified",
        "recorded_at": "2026-10-30T20:00:00-04:00",
        "notes": "Only the printed annotation is numeric. Unpriced labels stay in notes.",
        "unpriced_annotations_json": [{"label": "YVAL", "price": None}],
    }
    level = {
        "observation_id": identity, "session_date": day, "id": identity + "-1",
        "side": "neutral", "role": "reference", "ordinal": 1, "label": "HVE",
        "source_text": "HVE 7782", "price_low": "7782.00", "price_high": "7782.00",
        "product": "ES", "contract": None, "evidence_basis": "user_supplied_image",
        "available_at": None, "timing_status": "historical_availability_unverified",
        "notes": "A chart reference does not establish an A/B threshold or directional target.",
    }
    return observation, level, pin


def _color_image_fixture(root: Path) -> tuple[Path, Path, dict, dict, dict, dict]:
    """An old neutral image and an explicit, separately pinned user interpretation."""
    spec_path, request, spec, update = fixture(root)
    parent, pivot, image_pin = _image_observation(root)
    pivot.update(source_label="HVE", annotation_text="HVE 7782")
    target = {**copy.deepcopy(pivot), "id": "image-target", "ordinal": 2,
              "label": "HVE-PBT", "source_label": "HVE-PBT", "source_text": "HVE-PBT 7812 magnet",
              "annotation_text": "HVE-PBT 7812 magnet", "price_low": "7812.00", "price_high": "7812.00"}
    parent["unpriced_annotations_json"] = [
        {"source_label": "YHOD-ONH", "annotation_text": "YHOD-ONH", "price_low": None,
         "price_high": None, "side": "neutral", "role": "reference"},
        {"source_label": "YVAL", "annotation_text": "YVAL magnet", "price_low": None,
         "price_high": None, "side": "neutral", "role": "reference"},
    ]
    update["tables"]["observations"].append(parent)
    update["tables"]["observation_levels"].extend([pivot, target])
    update["files"].append(image_pin)
    update_path = root / spec["update"]["path"]
    _json(update_path, update)
    spec["update"] = _record(root, update_path)
    _json(spec_path, spec)
    statement = root / "data/raw/user/verniman/color-rule/user-message.txt"
    statement.parent.mkdir(parents=True)
    statement.write_text("Light blue is pivot, green is bullish target, red is bearish target.\n")
    legend_path = statement.with_name("legend.json")
    _json(legend_path, {
        "schema": "abacus.verniman.image-color-legend/v1",
        "interpretation_basis": "user_supplied_color_legend",
        "color_roles": {**consolidated.COLOR_ROLES,
                        "light_blue": {"side": "neutral", "role": "trigger", "display_role": "pivot"}},
        "source_statement": _record(root, statement),
        "applies_to": [{key: parent[key] for key in
                        ("observation_id", "session_date", "raw_evidence_path", "raw_evidence_sha256")}],
    })
    current = {**copy.deepcopy(parent), "observation_id": parent["observation_id"] + "-classified",
               "supersedes_observation_id": parent["observation_id"],
               "interpretation_basis": "user_supplied_color_legend",
               "legend_path": legend_path.relative_to(root).as_posix(), "legend_sha256": sha256_file(legend_path)}
    current["unpriced_annotations_json"][0].update(side="bullish", role="target", ordinal=1, source_color="green")
    current["unpriced_annotations_json"][1].update(side="bearish", role="target", ordinal=1, source_color="red")
    classified = []
    for previous, side, role, ordinal, color in ((pivot, "neutral", "trigger", 1, "light_blue"),
                                                (target, "bullish", "target", 2, "green")):
        row = {**copy.deepcopy(previous), "observation_id": current["observation_id"],
               "id": previous["id"] + "-classified", "side": side, "role": role,
               "ordinal": ordinal, "source_color": color,
               "interpretation_basis": "user_supplied_color_legend"}
        classified.append(row)
    interpretation = {"dataset_id": "explicit-user-color-interpretation",
        "files": [_record(root, legend_path), _record(root, statement)],
        "tables": {"observations": [current], "observation_levels": classified}}
    return spec_path, request, spec, update, interpretation, parent


class ConsolidatedPublicationTests(unittest.TestCase):
    def publish(self, root: Path, spec: Path, request: Path) -> tuple[Path, str]:
        manifest = consolidated.publish_release(root, spec, request)
        return manifest, sha256_file(manifest)

    def test_revision_dedup_keeps_membership_and_distinct_same_date_posts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec, request, _, _ = fixture(root)
            manifest, pin = self.publish(root, spec, request)
            rows = consolidated.load_release(root, manifest, pin).to_pylist()
            self.assertEqual(len(rows), 4)
            self.assertEqual(sum(row["session_date"] == date(2026, 10, 20) for row in rows), 2)
            shared = _post()[0]["outlook_id"]
            levels = consolidated.load_release(root, manifest, pin, table="levels").to_pylist()
            self.assertEqual({row["source_label"] for row in levels if row["outlook_id"] == shared},
                             {"new-extraction"})
            membership = consolidated.load_release(root, manifest, pin, table="release_membership").to_pylist()
            self.assertEqual(len([row for row in membership if row["outlook_id"] == shared]), 2)
            undated = [row for row in rows if row["session_date"] is None]
            self.assertEqual([row["title"] for row in undated], ["undated"])

    def test_same_raw_revision_with_legacy_hash_definition_is_deduplicated(self):
        """v1/v2 can hash the identical capture body differently; preserve both identities."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            source_ids = []
            for index, item in enumerate(spec["historical_releases"]):
                manifest_path = root / item["path"]
                manifest = json.loads(manifest_path.read_text())
                outlook_path = root / manifest["tables"]["outlooks"]["path"]
                rows = pq.ParquetFile(outlook_path).read().to_pylist()
                shared = next(row for row in rows if row["title"] == "shared")
                old_id = shared["outlook_id"]
                shared["outlook_id"] = str(index + 1) * 64
                shared["content_sha256"] = str(index + 3) * 64
                shared["raw_html_sha256"] = "a" * 64
                shared["raw_atom_sha256"] = "b" * 64
                source_ids.append(shared["outlook_id"])
                pq.write_table(pa.Table.from_pylist(rows, schema=_OUTLOOK_SCHEMA), outlook_path)
                level_path = root / manifest["tables"]["levels"]["path"]
                rows = pq.ParquetFile(level_path).read().to_pylist()
                for row in rows:
                    if row["outlook_id"] == old_id:
                        row["outlook_id"] = shared["outlook_id"]
                pq.write_table(pa.Table.from_pylist(rows, schema=_LEVEL_SCHEMA), level_path)
                manifest["files"] = [_record(root, root / entry["path"]) for entry in manifest["files"]]
                _json(manifest_path, manifest)
                item["sha256"] = sha256_file(manifest_path)
            _json(spec_path, spec)
            manifest, pin = self.publish(root, spec_path, request)
            rows = consolidated.load_release(root, manifest, pin).to_pylist()
            self.assertEqual(len(rows), 4)
            self.assertEqual([row["outlook_id"] for row in rows if row["title"] == "shared"], [source_ids[1]])
            memberships = consolidated.load_release(root, manifest, pin, table="release_membership").to_pylist()
            shared_memberships = [row for row in memberships if row["outlook_id"] == source_ids[1]]
            self.assertEqual({row["source_outlook_id"] for row in shared_memberships}, set(source_ids))
            self.assertEqual(sum(row["selected_primary"] for row in shared_memberships), 1)

    def test_distinct_captured_revisions_of_one_post_remain_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            item = spec["historical_releases"][1]
            manifest_path = root / item["path"]
            source_manifest = json.loads(manifest_path.read_text())
            path = root / source_manifest["tables"]["outlooks"]["path"]
            rows = pq.ParquetFile(path).read().to_pylist()
            shared = next(row for row in rows if row["title"] == "shared")
            revised = next(row for row in rows if row["title"] == "separate-revision")
            revised["source_post_id"] = shared["source_post_id"]
            revised["source_url"] = shared["source_url"]
            shared["raw_html_sha256"] = "a" * 64
            revised["raw_html_sha256"] = "b" * 64
            pq.write_table(pa.Table.from_pylist(rows, schema=_OUTLOOK_SCHEMA), path)
            source_manifest["files"] = [_record(root, root / value["path"]) for value in source_manifest["files"]]
            _json(manifest_path, source_manifest)
            item["sha256"] = sha256_file(manifest_path)
            _json(spec_path, spec)
            manifest, pin = self.publish(root, spec_path, request)
            selected = consolidated.load_release(root, manifest, pin).to_pylist()
            self.assertEqual(len(selected), 4)
            self.assertEqual(sum(row["source_post_id"] == shared["source_post_id"] for row in selected), 2)

    def test_calendar_preserves_checked_gap_and_weekend_and_old_source_ledgers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec, request, _, _ = fixture(root)
            manifest, pin = self.publish(root, spec, request)
            rows = consolidated.load_release(root, manifest, pin, table="coverage").to_pylist()
            expected = [date(2026, 10, 20) + timedelta(days=index) for index in range(9)]
            self.assertEqual([row["session_date"] for row in rows], expected)
            by_day = {row["session_date"]: row for row in rows}
            self.assertEqual(by_day[date(2026, 10, 23)]["status"], "no_dated_plan_verified")
            self.assertEqual(by_day[date(2026, 10, 24)]["post_count"], 0)
            self.assertEqual(by_day[date(2026, 10, 28)]["post_count"], 1)
            original = consolidated.load_release(root, manifest, pin, table="source_coverage").to_pylist()
            historical = [row for row in original if row["source_dataset_id"].startswith("verniman_daily_levels__")]
            self.assertEqual(len(historical), 2)
            self.assertTrue(all(row["reason"] == "Synthetic source ledger." for row in historical))
            self.assertEqual(len(original), 3)

    def test_recollection_and_chart_references_never_replace_captured_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, update = fixture(root)
            observation = {
                "observation_id": "remembered-1021", "session_date": "2026-10-21",
                "title": "Retrospective record", "contract": "ESZ26",
                "source_url": "https://verniman.blogspot.com/2009/10/missing.html",
                "evidence_basis": "user_supplied_recollection", "available_at": None,
                "recorded_at": "2026-10-28T16:00:00-04:00",
                "claimed_read_time_text": "verified 09:25:33 New York time",
                "claim_timing_class": "claimed_before_open", "notes": "Original acronym was not retained.",
            }
            observation_level = {
                "observation_id": "remembered-1021", "session_date": "2026-10-21", "id": "remembered-1021-pivot",
                "side": "neutral", "role": "pivot", "ordinal": 1, "label": None,
                "price_low": "7782.00", "price_high": "7782.00",
                "evidence_basis": "user_supplied_recollection", "notes": "No invented source label.",
            }
            update["tables"]["observations"].append(observation)
            update["tables"]["observation_levels"].append(observation_level)
            update_path = root / spec["update"]["path"]
            _json(update_path, update)
            spec["update"] = _record(root, update_path)
            _json(spec_path, spec)
            manifest, pin = self.publish(root, spec_path, request)
            canonical = consolidated.load_release(root, manifest, pin).to_pylist()
            self.assertFalse(any(row["session_date"] == date(2026, 10, 21) for row in canonical))
            self.assertTrue(all(row["available_at"] is None for row in canonical))
            retained = consolidated.load_release(root, manifest, pin, table="observations").to_pylist()
            self.assertEqual(retained[0]["claimed_read_time_text"], observation["claimed_read_time_text"])
            self.assertEqual(retained[0]["evidence_basis"], "user_supplied_recollection")
            self.assertIsNone(retained[0]["available_at"])
            level = consolidated.load_release(root, manifest, pin, table="observation_levels").to_pylist()[0]
            self.assertIsNone(level["label"])
            self.assertEqual(level["price_low"], Decimal("7782.00"))
            day = next(row for row in consolidated.load_release(root, manifest, pin, table="coverage").to_pylist()
                       if row["session_date"] == date(2026, 10, 21))
            self.assertEqual((day["status"], day["post_count"], day["observation_count"]),
                             ("user_observation_only", 0, 1))

    def test_report_of_no_verified_plan_does_not_become_positive_plan_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, update = fixture(root)
            update["tables"]["observations"].append({
                "observation_id": "remembered-no-plan-1023", "session_date": "2026-10-23",
                "evidence_basis": "user_supplied_recollection", "available_at": None,
                "observation_kind": "no_plan_reported", "notes": "No dated blog plan was verified in our checks.",
            })
            update["coverage"][0]["observed_as_of_utc"] = "2026-10-28T20:00:00+00:00"
            update_path = root / spec["update"]["path"]
            _json(update_path, update)
            spec["update"] = _record(root, update_path)
            _json(spec_path, spec)
            manifest, pin = self.publish(root, spec_path, request)
            day = next(row for row in consolidated.load_release(root, manifest, pin, table="coverage").to_pylist()
                       if row["session_date"] == date(2026, 10, 23))
            self.assertEqual((day["status"], day["post_count"], day["observation_count"]),
                             ("no_dated_plan_verified", 0, 1))
            self.assertEqual(day["observed_as_of_utc"], "2026-10-28T20:00:00+00:00")

    def test_image_observations_preserve_old_snapshots_notes_and_canonical_gaps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, update = fixture(root)
            update["tables"]["observations"].extend([
                {"observation_id": "prior-note-21", "session_date": "2026-10-21",
                 "evidence_basis": "user_supplied_recollection", "available_at": None,
                 "observation_kind": "daily_plan_recollection", "notes": "Retained earlier note."},
                {"observation_id": "prior-note-23", "session_date": "2026-10-23",
                 "evidence_basis": "user_supplied_recollection", "available_at": None,
                 "observation_kind": "no_plan_reported", "notes": "No captured daily plan."},
            ])
            update_path = root / spec["update"]["path"]
            _json(update_path, update)
            spec["update"] = _record(root, update_path)
            _json(spec_path, spec)
            old_manifest, old_pin = self.publish(root, spec_path, request)
            before = {path: sha256_file(path) for path in root.rglob("*") if path.is_file()}
            images = [_image_observation(root, day) for day in ("2026-10-21", "2026-10-23")]
            image_update = root / "data/staging/verniman/image-review/update.json"
            _json(image_update, {
                "dataset_id": "supplied-images", "files": [pin for _, _, pin in images],
                "tables": {"observations": [row for row, _, _ in images],
                           "observation_levels": [row for _, row, _ in images]},
            })
            image_spec = root / "data/staging/verniman/image-review/input-spec.json"
            _json(image_spec, {**spec, "additional_updates": [_record(root, image_update)]})
            manifest = consolidated.publish_release(root, image_spec, request, version="16.0.0")
            pin = sha256_file(manifest)
            self.assertTrue(all(sha256_file(path) == digest for path, digest in before.items()))
            self.assertEqual(consolidated.verify_release(root, old_manifest, old_pin)["version"], "13.0.0")
            for name in ("outlooks", "levels"):
                self.assertEqual(consolidated.load_release(root, old_manifest, old_pin, table=name).to_pylist(),
                                 consolidated.load_release(root, manifest, pin, table=name).to_pylist())
            observations = consolidated.load_release(root, manifest, pin, table="observations").to_pylist()
            self.assertEqual(len(observations), 4)
            self.assertEqual({row["evidence_basis"] for row in observations},
                             {"user_supplied_recollection", "user_supplied_image"})
            for row in observations:
                self.assertIsNone(row["available_at"])
            image_rows = [row for row in observations if row["evidence_basis"] == "user_supplied_image"]
            self.assertTrue(all(row["contract"] is None and row["image_timezone"] is None for row in image_rows))
            self.assertTrue(all(json.loads(row["unpriced_annotations_json"])[0]["price"] is None
                                for row in image_rows))
            days = consolidated.load_release(root, manifest, pin, table="coverage").to_pylist()
            for day in (date(2026, 10, 21), date(2026, 10, 23)):
                row = next(row for row in days if row["session_date"] == day)
                self.assertEqual((row["status"], row["post_count"], row["level_count"],
                                  row["observation_count"], row["image_observation_count"], row["image_level_count"]),
                                 ("image_observation_only", 0, 0, 2, 1, 1))
            for _, _, image_pin in images:
                retained = (root / "data/curated/external_levels/source=verniman/version=16.0.0"
                            / "provenance/update-evidence" / image_pin["path"])
                self.assertEqual(retained.read_bytes(), (root / image_pin["path"]).read_bytes())
            saved = json.loads(manifest.read_text())
            self.assertIn("supplied chart-image observations: 2", (root / saved["quality_report_path"]).read_text())
            self.assertIn("observation_evidence", json.loads((root / saved["schema_path"]).read_text()))
            self.assertNotIn("observation_evidence", json.loads((root / "catalog/schemas/verniman_daily_levels__13.0.0.json").read_text()))

    def test_image_observations_require_provenance_date_and_null_availability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, spec, update = fixture(root)
            observation, level, image_pin = _image_observation(root)
            update["files"] = [image_pin]
            update["tables"]["observation_levels"] = [level]
            path = root / spec["update"]["path"]
            cases = [
                {"raw_evidence_path": "data/raw/user/verniman/../other.png"},
                {"raw_evidence_path": None}, {"raw_evidence_sha256": None},
                {"raw_evidence_sha256": "a" * 64}, {"date_source_text": ""},
                {"displayed_time_text": ""}, {"session_date": None},
                {"observation_kind": "daily_plan_recollection"}, {"evidence_basis": "captured_source"},
                {"timing_status": "verified"}, {"available_at": "2026-10-21T09:33:00-04:00"},
            ]
            for changes in cases:
                with self.subTest(changes=changes):
                    update["tables"]["observations"] = [{**observation, **changes}]
                    _json(path, update)
                    spec["update"] = _record(root, path)
                    with self.assertRaises(ValueError):
                        consolidated.build_tables(root, spec, version="16.0.0")
            update["tables"]["observations"] = [observation]
            update["files"] = []
            _json(path, update)
            spec["update"] = _record(root, path)
            with self.assertRaisesRegex(ValueError, "exact pinned input bytes"):
                consolidated.build_tables(root, spec, version="16.0.0")

    def test_image_levels_require_neutral_references_and_matching_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, spec, update = fixture(root)
            observation, level, image_pin = _image_observation(root)
            update["files"] = [image_pin]
            update["tables"]["observations"] = [observation]
            path = root / spec["update"]["path"]
            for changes in [
                {"side": "bullish"}, {"side": "bearish"}, {"role": "trigger"}, {"role": "target"},
                {"evidence_basis": "user_supplied_recollection"}, {"ordinal": 0},
                {"label": None}, {"source_text": ""}, {"price_low": None},
                {"available_at": "2026-10-21T09:33:00-04:00"}, {"timing_status": "verified"},
                {"contract": "ESZ26"},
            ]:
                with self.subTest(changes=changes):
                    update["tables"]["observation_levels"] = [{**level, **changes}]
                    _json(path, update)
                    spec["update"] = _record(root, path)
                    with self.assertRaises(ValueError):
                        consolidated.build_tables(root, spec, version="16.0.0")

    def test_image_evidence_cannot_be_promoted_to_canonical_levels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, spec, update = fixture(root)
            update["tables"]["levels"][0]["evidence_basis"] = "user_supplied_image"
            path = root / spec["update"]["path"]
            _json(path, update)
            spec["update"] = _record(root, path)
            with self.assertRaisesRegex(ValueError, "cannot become canonical levels"):
                consolidated.build_tables(root, spec, version="16.0.0")

    def test_image_observations_require_a_new_schema_release_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, spec, update = fixture(root)
            observation, level, image_pin = _image_observation(root)
            update["files"] = [image_pin]
            update["tables"]["observations"] = [observation]
            update["tables"]["observation_levels"] = [level]
            path = root / spec["update"]["path"]
            _json(path, update)
            spec["update"] = _record(root, path)
            with self.assertRaisesRegex(ValueError, "version 16 or newer"):
                consolidated.build_tables(root, spec, version="15.0.0")

    def test_pinned_user_legend_revises_only_same_image_and_retains_previous_interpretation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _, interpretation, previous = _color_image_fixture(root)
            old_manifest = consolidated.publish_release(root, spec_path, request, version="16.0.0")
            old_pin = sha256_file(old_manifest)
            before = {p: sha256_file(p) for p in root.rglob("*") if p.is_file()}
            document = root / "data/staging/verniman/color-review/update.json"
            _json(document, interpretation)
            next_spec = root / "data/staging/verniman/color-review/input-spec.json"
            _json(next_spec, {**spec, "additional_updates": [_record(root, document)]})
            manifest = consolidated.publish_release(root, next_spec, request, version="19.0.0")
            pin = sha256_file(manifest)
            self.assertTrue(all(sha256_file(p) == digest for p, digest in before.items()))
            self.assertEqual(consolidated.verify_release(root, old_manifest, old_pin)["version"], "16.0.0")
            parents = consolidated.load_release(root, manifest, pin, table="observations").to_pylist()
            self.assertEqual(len(parents), 1)
            current = parents[0]
            self.assertEqual(current["supersedes_observation_id"], previous["observation_id"])
            self.assertEqual(json.loads(current["superseded_observation_json"])["observation_id"], previous["observation_id"])
            self.assertTrue(all(row["side"] == "neutral" and row["role"] == "reference"
                                for row in json.loads(current["superseded_levels_json"])))
            levels = consolidated.load_release(root, manifest, pin, table="observation_levels").to_pylist()
            self.assertEqual({(row["side"], row["role"], row["ordinal"]) for row in levels},
                             {("neutral", "trigger", 1), ("bullish", "target", 2)})
            unpriced = json.loads(current["unpriced_annotations_json"])
            self.assertEqual(unpriced[0]["ordinal"], 1)
            self.assertIsNone(unpriced[0]["price_low"])
            for table in ("outlooks", "levels", "issues", "source_coverage", "release_membership"):
                self.assertEqual(consolidated.load_release(root, old_manifest, old_pin, table=table).to_pylist(),
                                 consolidated.load_release(root, manifest, pin, table=table).to_pylist())
            day = next(row for row in consolidated.load_release(root, manifest, pin, table="coverage").to_pylist()
                       if row["session_date"] == date(2026, 10, 21))
            self.assertEqual((day["status"], day["image_observation_count"], day["image_level_count"]),
                             ("image_observation_only", 1, 2))
            source = root / current["legend_path"]
            self.assertEqual(hashlib.sha256(current["legend_document_json"].encode()).hexdigest(), sha256_file(source))
            source.unlink()
            for record in interpretation["files"]:
                (root / record["path"]).unlink(missing_ok=True)
            self.assertEqual(consolidated.load_release(root, manifest, pin, table="observations").num_rows, 1)
            with self.assertRaises(ValueError):
                consolidated.verify_release(root, manifest, pin, verify_inputs=True)

    def test_image_color_roles_require_exact_pinned_legend_scope_and_new_version(self):
        cases = ("missing_legend_pin", "wrong_legend_hash", "wrong_scope", "wrong_mapping", "wrong_statement_pin", "old_version")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                _, _, spec, _, interpretation, _ = _color_image_fixture(root)
                current = interpretation["tables"]["observations"][0]
                if case == "missing_legend_pin":
                    interpretation["files"] = interpretation["files"][1:]
                elif case == "wrong_legend_hash":
                    current["legend_sha256"] = "f" * 64
                elif case in {"wrong_scope", "wrong_mapping", "wrong_statement_pin"}:
                    path = root / current["legend_path"]
                    legend = json.loads(path.read_text())
                    if case == "wrong_scope":
                        legend["applies_to"][0]["raw_evidence_sha256"] = "f" * 64
                    elif case == "wrong_mapping":
                        legend["color_roles"]["green"]["side"] = "bearish"
                    else:
                        legend["source_statement"]["sha256"] = "f" * 64
                    _json(path, legend)
                    current["legend_sha256"] = sha256_file(path)
                    interpretation["files"][0] = _record(root, path)
                document = root / "data/staging/verniman/color-review/update.json"
                _json(document, interpretation)
                selected = {**spec, "additional_updates": [_record(root, document)]}
                with self.assertRaises(ValueError):
                    consolidated.build_tables(root, selected, version="18.0.0" if case == "old_version" else "19.0.0")

    def test_image_supersession_cannot_change_sources_prices_or_recollections(self):
        cases = ("different_image", "different_date", "different_price", "changed_unpriced_label", "recollection", "unknown_previous")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                _, _, spec, update, interpretation, previous = _color_image_fixture(root)
                current = interpretation["tables"]["observations"][0]
                if case == "different_image":
                    current["raw_evidence_path"] += ".other"
                elif case == "different_date":
                    current["session_date"] = "2026-10-22"
                elif case == "different_price":
                    interpretation["tables"]["observation_levels"][0]["price_low"] = "7783.00"
                    interpretation["tables"]["observation_levels"][0]["price_high"] = "7783.00"
                elif case == "changed_unpriced_label":
                    current["unpriced_annotations_json"][0]["source_label"] = "GAP"
                elif case == "recollection":
                    update["tables"]["observations"][0]["evidence_basis"] = "user_supplied_recollection"
                    path = root / spec["update"]["path"]
                    _json(path, update)
                    spec["update"] = _record(root, path)
                else:
                    current["supersedes_observation_id"] = "missing-parent"
                document = root / "data/staging/verniman/color-review/update.json"
                _json(document, interpretation)
                with self.assertRaises(ValueError):
                    consolidated.build_tables(root, {**spec, "additional_updates": [_record(root, document)]}, version="19.0.0")

    def test_color_annotations_require_correct_roles_and_complete_priced_unpriced_order(self):
        cases = ("wrong_side", "wrong_role", "missing_child_basis", "unknown_color", "unpriced_number", "duplicate_order", "missing_order")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                _, _, spec, _, interpretation, _ = _color_image_fixture(root)
                levels = interpretation["tables"]["observation_levels"]
                annotations = interpretation["tables"]["observations"][0]["unpriced_annotations_json"]
                if case == "wrong_side": levels[0]["side"] = "bullish"
                elif case == "wrong_role": levels[0]["role"] = "reference"
                elif case == "missing_child_basis": levels[0].pop("interpretation_basis")
                elif case == "unknown_color": levels[0]["source_color"] = "yellow"
                elif case == "unpriced_number": annotations[0]["price_low"] = "7793.00"
                elif case == "duplicate_order": levels[1]["ordinal"] = 1
                else: levels[1]["ordinal"] = 3
                document = root / "data/staging/verniman/color-review/update.json"
                _json(document, interpretation)
                with self.assertRaises(ValueError):
                    consolidated.build_tables(root, {**spec, "additional_updates": [_record(root, document)]}, version="19.0.0")

    def test_reader_filters_start_inclusive_end_exclusive_and_only_declared_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec, request, _, _ = fixture(root)
            manifest, pin = self.publish(root, spec, request)
            rows = consolidated.load_release(root, manifest, pin,
                start_date="2026-10-20", end_date="2026-10-28").to_pylist()
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["session_date"] == date(2026, 10, 20) for row in rows))
            # An unrelated Parquet file must never become an implicitly discovered input.
            extra = root / consolidated.DATA_PATH / "outlooks/year=2026/extra.parquet"
            pq.write_table(pa.table({"unrelated": [1]}), extra)
            self.assertEqual(consolidated.load_release(root, manifest, pin).num_rows, 4)
            with self.assertRaises(ValueError):
                consolidated.load_release(root, manifest, "0" * 64)
            with self.assertRaises(ValueError):
                consolidated.load_release(root, manifest, "0" * 64, verify_bytes=False)
            with self.assertRaises(ValueError):
                consolidated.load_release(root, manifest, pin, table="unlisted")

    def test_existing_final_is_refused_and_all_prior_inputs_remain_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec, request, _, _ = fixture(root)
            before = {path: sha256_file(path) for path in root.rglob("*") if path.is_file()}
            manifest, _ = self.publish(root, spec, request)
            self.assertTrue(all(sha256_file(path) == digest for path, digest in before.items()))
            with self.assertRaises((ValueError, FileExistsError)):
                consolidated.publish_release(root, spec, request)
            self.assertTrue(manifest.is_file())

    def test_new_version_preserves_old_snapshot_lineage_and_additional_update_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, update = fixture(root)
            update["tables"]["observations"].append({
                "observation_id": "retained-note", "session_date": "2026-10-21",
                "evidence_basis": "user_supplied_recollection", "available_at": None,
                "notes": "Original recollection remains separate from captured plans.",
            })
            update["tables"]["observation_levels"].append({
                "observation_id": "retained-note", "session_date": "2026-10-21",
                "side": "neutral", "role": "pivot", "ordinal": 1,
                "price_low": "7730.00", "price_high": "7730.00",
                "evidence_basis": "user_supplied_recollection",
            })
            update_path = root / spec["update"]["path"]
            _json(update_path, update)
            spec["update"] = _record(root, update_path)
            _json(spec_path, spec)
            old_manifest, old_pin = self.publish(root, spec_path, request)
            old_tables = {name: consolidated.load_release(root, old_manifest, old_pin, table=name)
                          for name in consolidated.TABLES}
            before = {path: sha256_file(path) for path in root.rglob("*") if path.is_file()}
            source, levels = _post("fresh-source", day=date(2026, 10, 29))
            for row in [source, *levels]:
                for key, value in tuple(row.items()):
                    if isinstance(value, (date, datetime)):
                        row[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        row[key] = str(value)
            receipt = root / "data/staging/verniman/new-review/receipt.json"
            _json(receipt, {"reviewed": True})
            additional = root / "data/staging/verniman/new-review/update.json"
            _json(additional, {
                "dataset_id": "fresh_reviewed_source", "files": [_record(root, receipt)],
                "tables": {"outlooks": [source], "levels": levels},
                "coverage": [
                    {"session_date": "2026-10-23", "status": "reviewed_source_gap",
                     "reason": "A later explicit review preserves the earlier coverage ledger."},
                    {"session_date": "2026-10-29", "status": "post_captured",
                     "reason": "New explicitly supplied source."}],
            })
            next_spec = {**spec, "end_date": "2026-10-29",
                         "additional_updates": [_record(root, additional)]}
            next_spec_path = root / "data/staging/verniman/new-review/input-spec.json"
            _json(next_spec_path, next_spec)
            new_manifest = consolidated.publish_release(root, next_spec_path, request, version="14.0.0")
            new_pin = sha256_file(new_manifest)
            self.assertTrue(all(sha256_file(path) == digest for path, digest in before.items()))
            self.assertEqual(consolidated.verify_release(root, old_manifest, old_pin)["version"], "13.0.0")
            metadata = consolidated.verify_release(root, new_manifest, new_pin, verify_inputs=True)
            self.assertEqual(metadata["version"], "14.0.0")
            self.assertIn("--version", metadata["publication_invocation"]["reconstruction_argv"])
            for name, old in old_tables.items():
                self.assertEqual(old.schema.metadata[b"dataset_id"], b"verniman_daily_levels__13.0.0")
                saved = consolidated.load_release(root, new_manifest, new_pin, table=name)
                self.assertEqual(saved.schema.metadata[b"dataset_id"], b"verniman_daily_levels__14.0.0")
                if name == "coverage":
                    continue
                new_rows = saved.to_pylist()
                for old_row in old.to_pylist():
                    self.assertIn(old_row, new_rows, name)
            new_sources = consolidated.load_release(root, new_manifest, new_pin).to_pylist()
            self.assertEqual(next(row for row in new_sources if row["title"] == "fresh-source")
                             ["primary_source_dataset"], "fresh_reviewed_source")
            days = consolidated.load_release(root, new_manifest, new_pin, table="coverage").to_pylist()
            self.assertEqual(next(row for row in days if row["session_date"] == date(2026, 10, 23))
                             ["status"], "reviewed_source_gap")
            retained = root / "data/curated/external_levels/source=verniman/version=14.0.0/provenance/inputs"
            self.assertEqual((retained / "update.json").read_bytes(), update_path.read_bytes())
            self.assertEqual((retained / "additional-update-001.json").read_bytes(), additional.read_bytes())
            copied_receipt = (root / "data/curated/external_levels/source=verniman/version=14.0.0"
                              / "provenance/update-evidence" / receipt.relative_to(root))
            self.assertEqual(copied_receipt.read_bytes(), receipt.read_bytes())
            with self.assertRaises((ValueError, FileExistsError)):
                consolidated.publish_release(root, next_spec_path, request, version="14.0.0")

    def test_reader_refuses_cross_release_partition_csv_metadata_and_inventory_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, _, _ = fixture(root)
            old_path, _ = self.publish(root, spec_path, request)
            new_path = consolidated.publish_release(root, spec_path, request, version="14.0.0")
            old = json.loads(old_path.read_text())
            new = json.loads(new_path.read_text())
            for mutation in ("partition", "csv", "schema", "quality", "inventory"):
                with self.subTest(mutation=mutation):
                    changed = copy.deepcopy(new)
                    if mutation == "partition":
                        changed["tables"]["levels"]["paths"] = old["tables"]["levels"]["paths"]
                        selected = set(old["tables"]["levels"]["paths"])
                        changed["files"].extend(row for row in old["files"] if row["path"] in selected)
                    elif mutation == "csv":
                        changed["tables"]["levels"]["csv_path"] = old["tables"]["levels"]["csv_path"]
                    elif mutation == "schema":
                        changed["schema_path"] = old["schema_path"]
                    elif mutation == "quality":
                        changed["quality_report_path"] = old["quality_report_path"]
                    else:
                        changed["files"].append(next(row for row in old["files"]
                                                     if row["path"].endswith("daily_summary.csv")))
                    _json(new_path, changed)
                    with self.assertRaises(ValueError):
                        consolidated.verify_release(root, new_path, sha256_file(new_path))

    def test_invalid_release_versions_and_additional_update_identities_are_refused(self):
        for version in ("12.0.0", "14.1.0", "014.0.0", "../14.0.0", None):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                spec_path, request, _, _ = fixture(root)
                with self.assertRaises(ValueError):
                    consolidated.publish_release(root, spec_path, request, version=version)
                self.assertFalse((root / consolidated.DATA_PATH).exists())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            spec["additional_updates"] = [spec["update"]]
            _json(spec_path, spec)
            with self.assertRaisesRegex(ValueError, "unique dataset_id"):
                consolidated.publish_release(root, spec_path, request, version="14.0.0")

    def test_metadata_recovery_or_staging_conflict_prevents_all_publication(self):
        for relative in (
            consolidated.MANIFEST_PATH.with_name(consolidated.MANIFEST_PATH.name + ".part"),
            consolidated.SCHEMA_PATH.with_name(consolidated.SCHEMA_PATH.name + ".part"),
            consolidated.QUALITY_PATH.with_name(consolidated.QUALITY_PATH.name + ".part"),
            Path("data/staging/verniman/consolidated-v13.0.0"),
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                spec, request, _, _ = fixture(root)
                occupied = root / relative
                occupied.parent.mkdir(parents=True, exist_ok=True)
                occupied.write_bytes(b"Retained recovery evidence.")
                with self.assertRaises((ValueError, FileExistsError)):
                    consolidated.publish_release(root, spec, request)
                self.assertEqual(occupied.read_bytes(), b"Retained recovery evidence.")
                self.assertFalse((root / consolidated.DATA_PATH).exists())
                self.assertFalse((root / consolidated.MANIFEST_PATH).exists())

    def test_bad_prior_manifest_pin_is_refused_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            spec["historical_releases"][0]["sha256"] = "0" * 64
            _json(spec_path, spec)
            with self.assertRaises(ValueError):
                consolidated.publish_release(root, spec_path, request)
            self.assertFalse((root / consolidated.MANIFEST_PATH).exists())

    def test_corrupted_prior_table_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            old = json.loads((root / spec["historical_releases"][0]["path"]).read_text())
            path = root / old["tables"]["levels"]["path"]
            path.write_bytes(path.read_bytes() + b"changed")
            with self.assertRaises(ValueError):
                consolidated.publish_release(root, spec_path, request)

    def test_saved_partition_corruption_is_detected_without_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, _, _ = fixture(root)
            manifest, pin = self.publish(root, spec_path, request)
            path = next((root / consolidated.DATA_PATH / "levels").rglob("*.parquet"))
            changed = path.read_bytes() + b"intentional corruption"
            path.write_bytes(changed)
            with self.assertRaises(ValueError):
                consolidated.verify_release(root, manifest, pin)
            self.assertEqual(path.read_bytes(), changed)

    def test_immutable_reader_does_not_depend_on_live_preparation_inputs(self):
        for original in ("update", "input_spec", "request", "old_manifest", "old_table"):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                spec_path, request, spec, _ = fixture(root)
                manifest, pin = self.publish(root, spec_path, request)
                expected = consolidated.load_release(root, manifest, pin)
                if original == "update":
                    source = root / spec["update"]["path"]
                elif original == "input_spec":
                    source = spec_path
                elif original == "request":
                    source = request
                elif original == "old_manifest":
                    source = root / spec["historical_releases"][0]["path"]
                else:
                    old = json.loads((root / spec["historical_releases"][0]["path"]).read_text())
                    source = root / old["tables"]["levels"]["path"]
                if original == "old_table":
                    source.write_bytes(b"Changed retained source table; published output must stand alone.")
                else:
                    source.unlink()
                actual = consolidated.load_release(root, manifest, pin)
                self.assertTrue(actual.equals(expected, check_metadata=True))
                self.assertEqual(consolidated.verify_release(root, manifest, pin)["version"], "13.0.0")
                with self.assertRaises(ValueError):
                    consolidated.verify_release(root, manifest, pin, verify_inputs=True)

    def test_path_escape_and_symlink_input_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            outside = root.parent / (root.name + "-external.json")
            try:
                outside.write_text("{}")
                spec["update"] = {"path": "../" + outside.name, "sha256": sha256_file(outside)}
                _json(spec_path, spec)
                with self.assertRaises((ValueError, FileExistsError)):
                    consolidated.publish_release(root, spec_path, request)
                link = root / "data/staging/verniman/linked.json"
                link.symlink_to(outside)
                spec["update"] = {"path": link.relative_to(root).as_posix(), "sha256": sha256_file(outside)}
                _json(spec_path, spec)
                with self.assertRaises((ValueError, FileExistsError)):
                    consolidated.publish_release(root, spec_path, request)
            finally:
                outside.unlink(missing_ok=True)

    def test_same_revision_with_conflicting_date_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            old_pin = spec["historical_releases"][0]
            old_path = root / old_pin["path"]
            old = json.loads(old_path.read_text())
            path = root / old["tables"]["outlooks"]["path"]
            rows = pq.ParquetFile(path).read().to_pylist()
            rows[0]["session_date"] = date(2026, 10, 19)
            pq.write_table(pa.Table.from_pylist(rows, schema=_OUTLOOK_SCHEMA), path)
            old["files"] = [_record(root, root / item["path"]) for item in old["files"]]
            _json(old_path, old)
            old_pin["sha256"] = sha256_file(old_path)
            _json(spec_path, spec)
            with self.assertRaises(ValueError):
                consolidated.publish_release(root, spec_path, request)

    def test_exact_qualified_historical_date_conflict_retains_both_assignments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            spec_path, request, spec, _ = fixture(root)
            original_id = _shift_old_date(root, spec, date(2026, 10, 21))
            spec["qualified_date_conflicts"] = [{
                "source_outlook_id": original_id,
                "assignments": {"verniman_daily_levels__1.0.0": "2026-10-21",
                                "verniman_daily_levels__2.0.0": "2026-10-20"},
                "reason": "Two frozen historical date assignments; retain both without choosing a date.",
            }]
            _json(spec_path, spec)
            manifest, pin = self.publish(root, spec_path, request)
            canonical = consolidated.load_release(root, manifest, pin).to_pylist()
            shared = [row for row in canonical if row["title"] == "shared"]
            self.assertEqual(len(canonical), 5)
            self.assertEqual({row["session_date"] for row in shared}, {date(2026, 10, 20), date(2026, 10, 21)})
            self.assertEqual({row["source_revision_id"] for row in shared}, {original_id})
            self.assertEqual(len({row["outlook_id"] for row in shared}), 2)
            self.assertTrue(all(row["outlook_id"] != original_id for row in shared))
            issues = consolidated.load_release(root, manifest, pin, table="issues").to_pylist()
            self.assertEqual([row["code"] for row in issues].count("cross_release_session_date_conflict"), 2)
            memberships = consolidated.load_release(root, manifest, pin, table="release_membership").to_pylist()
            mapped = [row for row in memberships if row["source_outlook_id"] == original_id]
            self.assertEqual({row["outlook_id"] for row in mapped}, {row["outlook_id"] for row in shared})

    def test_mismatched_or_unused_date_conflict_qualification_is_refused(self):
        for case in ("mismatched", "unused"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                spec_path, request, spec, _ = fixture(root)
                original_id = _shift_old_date(root, spec, date(2026, 10, 21)) if case == "mismatched" else _post()[0]["outlook_id"]
                spec["qualified_date_conflicts"] = [{
                    "source_outlook_id": original_id,
                    "assignments": {"verniman_daily_levels__1.0.0": "2026-10-22",
                                    "verniman_daily_levels__2.0.0": "2026-10-20"},
                    "reason": "This qualification must not act as a blanket date-conflict exception.",
                }]
                _json(spec_path, spec)
                with self.assertRaises(ValueError):
                    consolidated.publish_release(root, spec_path, request)

    def test_nonnull_historical_availability_and_descending_prices_are_refused(self):
        for mutation in ("available_at", "price_bounds", "observation_availability"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                spec_path, request, spec, update = fixture(root)
                if mutation == "available_at":
                    update["tables"]["outlooks"][0]["available_at"] = "2026-10-28T09:20:00-04:00"
                elif mutation == "observation_availability":
                    update["tables"]["observations"].append({
                        "observation_id": "bad-availability", "session_date": "2026-10-21",
                        "evidence_basis": "user_supplied_recollection",
                        "available_at": "2026-10-21T09:25:33-04:00",
                    })
                else:
                    update["tables"]["levels"][0]["price_high"] = "7720.00"
                update_path = root / spec["update"]["path"]
                _json(update_path, update)
                spec["update"] = _record(root, update_path)
                _json(spec_path, spec)
                with self.assertRaises(ValueError):
                    consolidated.publish_release(root, spec_path, request)

    def test_duplicate_level_slot_or_orphan_parent_is_refused(self):
        for mutation in ("duplicate_slot", "orphan"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                spec_path, request, spec, update = fixture(root)
                if mutation == "duplicate_slot":
                    update["tables"]["levels"].append(copy.deepcopy(update["tables"]["levels"][0]))
                else:
                    update["tables"]["levels"][0]["outlook_id"] = "f" * 64
                update_path = root / spec["update"]["path"]
                _json(update_path, update)
                spec["update"] = _record(root, update_path)
                _json(spec_path, spec)
                with self.assertRaises(ValueError):
                    consolidated.publish_release(root, spec_path, request)


if __name__ == "__main__":
    unittest.main()
