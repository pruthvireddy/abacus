"""Retained coverage-only correction to frozen r3 verification, never scoring."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

STAGE = Path(__file__).resolve().parents[2]
WORKSPACE = STAGE.parents[2]
REVIEW = STAGE / "provenance/reviews"
sys.path.insert(0, str(WORKSPACE / "studies"))
FROZEN = importlib.import_module("21_ema_cloud_trend_follow_opportunity.src.reconcile")
NY = "America/New_York"


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(path):
    path = Path(path).resolve()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def cell(raw, expected, label):
    if expected is None:
        require(raw == "", label + ": expected undefined readiness")
    else:
        require(raw != "" and math.isfinite(float(raw)) and
                math.isclose(float(raw), float(expected), rel_tol=2e-10, abs_tol=2e-10),
                label + f": mismatch {raw!r} versus {expected!r}")


def independent_coverage(technical, native_five, table_path):
    """Check all saved annual coverage fields; development readiness is eligibility."""
    require(len(technical) > 0, "empty technical coverage roster")
    products = technical["product"].unique().tolist()
    intervals = technical["interval_minutes"].unique().tolist()
    require(len(products) == len(intervals) == 1, "coverage checker requires one cell")
    product, interval = str(products[0]), int(intervals[0])
    local_year = pd.to_datetime(technical["timestamp"], utc=True).dt.tz_convert(NY).dt.year
    native_year = pd.to_datetime(native_five["timestamp"], utc=True).dt.tz_convert(NY).dt.year
    with Path(table_path).open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["product"] == product and int(r["interval_minutes"]) == interval]
    years = sorted(set(int(y) for y in local_year if 2017 <= int(y) <= 2020))
    require(sorted(int(r["year"]) for r in rows) == years, "coverage annual support is incomplete or duplicated")
    checked = 0
    annual = []
    for row in rows:
        year = int(row["year"])
        group = technical.loc[local_year.eq(year)]
        eligible = group["usable"].astype(bool) & group["feature_valid"].astype(bool)
        ready = int(eligible.sum())
        values = {
            "scheduled_slots": len(group), "usable_slots": int(group["usable"].astype(bool).sum()),
            "missing_slots": int(group["quality_reason"].fillna("").str.contains("missing_source_minutes", regex=False).sum()),
            "empty_slots": int(group["source_count"].eq(0).sum()),
            "mixed_slots": int(group["contract_count"].gt(1).sum()),
            "calendar_invalid_slots": int((~group["calendar_valid"].astype(bool)).sum()),
            "expected_source_minutes": int(group["expected_count"].sum()),
            "observed_source_minutes": int(group["source_count"].sum()),
            "known_closures_before": int(group["known_closure_before"].astype(bool).sum()),
        }
        if 2018 <= year <= 2020:
            values.update(feature_ready_slots=ready, mapped_ready_slots=ready,
                          ready_share=ready / len(group) if len(group) else None,
                          ready_sessions=int(group.loc[eligible, "session"].nunique()))
            require(row.get("split") == "development", "development coverage split differs")
        else:
            native = native_five.loc[native_year.eq(year)]
            values.update(feature_ready_slots=int(native["feature_valid"].astype(bool).sum()) if interval == 5 else None,
                          mapped_ready_slots=None, ready_share=None, ready_sessions=None)
            require(row.get("split") == "warmup_only", "warmup coverage split differs")
        for key, expected in values.items():
            require(key in row, "missing coverage field: " + key)
            cell(row[key], expected, f"independent corrected coverage {product}/{interval}/{year}/{key}")
            checked += 1
        annual.append({"year": year, "scheduled_slots": len(group), "eligible_slots": ready,
                       "ready_sessions": values["ready_sessions"], "warmup_readiness_undefined": year == 2017 and interval == 3})
    return {"check": "independent_saved_roster_coverage_quality_with_mapped_readiness", "status": "passed",
            "product": product, "interval_minutes": interval, "numeric_cells": checked, "annual_support": annual,
            "correction": "2018–2020 feature_ready_slots and mapped_ready_slots count usable AND feature_valid; 2017 native5m/undefined3m convention retained."}


def fixture(interval):
    stamps = pd.to_datetime(["2017-01-03T15:00Z", "2018-01-02T15:00Z", "2018-01-02T15:05Z",
                             "2018-01-03T15:00Z", "2018-01-04T15:00Z", "2019-01-02T15:00Z", "2019-01-03T15:00Z"])
    technical = pd.DataFrame({"product": "ES", "interval_minutes": interval, "timestamp": stamps,
                              "usable": [True, True, False, True, True, True, True],
                              "feature_valid": [True, True, True, False, True, True, False],
                              "session": ["w", "a", "b", "c", "d", "e", "f"],
                              "quality_reason": ["", "", "missing_source_minutes", "", "", "", ""],
                              "source_count": [interval, interval, 0, interval, interval, interval, interval],
                              "contract_count": [1, 1, 2, 1, 1, 1, 1],
                              "calendar_valid": [True, True, False, True, True, True, True],
                              "expected_count": interval, "known_closure_before": [True, True, False, False, False, True, False]})
    native = pd.DataFrame({"timestamp": pd.to_datetime(["2017-01-03T15:00Z"]), "feature_valid": [True]})
    rows = []
    for year, count, usable, missing, sessions, ready in ((2017, 1, 1, 0, None, None), (2018, 4, 3, 1, 2, 2), (2019, 2, 2, 0, 1, 1)):
        rows.append({"product": "ES", "interval_minutes": interval, "year": year,
                     "split": "warmup_only" if year == 2017 else "development", "scheduled_slots": count,
                     "usable_slots": usable, "missing_slots": missing, "empty_slots": missing,
                     "mixed_slots": missing, "calendar_invalid_slots": missing,
                     "expected_source_minutes": count * interval, "observed_source_minutes": usable * interval,
                     "known_closures_before": 1, "feature_ready_slots": (1 if interval == 5 else None) if year == 2017 else ready,
                     "mapped_ready_slots": ready, "ready_share": ready / count if ready is not None else None,
                     "ready_sessions": sessions})
    return technical, native, rows


def save_fixture(path, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class CoverageFixtures(unittest.TestCase):
    def test_mapped_three_and_unusable_feature_valid(self):
        technical, native, rows = fixture(3)
        with tempfile.TemporaryDirectory(prefix="study21-coverage-") as directory:
            path = Path(directory) / "coverage.csv"
            save_fixture(path, rows)
            result = independent_coverage(technical, native, path)
        self.assertEqual(result["annual_support"][1]["eligible_slots"], 2)
        self.assertEqual(result["annual_support"][1]["ready_sessions"], 2)

    def test_native_five_warmup_preserved(self):
        technical, native, rows = fixture(5)
        with tempfile.TemporaryDirectory(prefix="study21-coverage-") as directory:
            path = Path(directory) / "coverage.csv"
            save_fixture(path, rows)
            self.assertEqual(independent_coverage(technical, native, path)["numeric_cells"], 39)

    def test_warmup_three_must_remain_null(self):
        technical, native, rows = fixture(3)
        rows[0]["feature_ready_slots"] = 0
        with tempfile.TemporaryDirectory(prefix="study21-coverage-") as directory:
            path = Path(directory) / "coverage.csv"
            save_fixture(path, rows)
            with self.assertRaisesRegex(ValueError, "undefined readiness"):
                independent_coverage(technical, native, path)

    def test_missing_annual_support_rejected(self):
        technical, native, rows = fixture(3)
        with tempfile.TemporaryDirectory(prefix="study21-coverage-") as directory:
            path = Path(directory) / "coverage.csv"
            save_fixture(path, rows[:-1])
            with self.assertRaisesRegex(ValueError, "annual support"):
                independent_coverage(technical, native, path)

    def test_corrupt_readiness_share_and_session_rejected(self):
        for column, value in (("feature_ready_slots", 3), ("mapped_ready_slots", 3), ("ready_share", .75), ("ready_sessions", 3)):
            with self.subTest(column=column), tempfile.TemporaryDirectory(prefix="study21-coverage-") as directory:
                technical, native, rows = fixture(3)
                rows[1][column] = value
                path = Path(directory) / "coverage.csv"
                save_fixture(path, rows)
                with self.assertRaisesRegex(ValueError, column):
                    independent_coverage(technical, native, path)


def source_guard():
    inventory = json.loads((STAGE / "provenance/source-inventory.json").read_text())
    for row in inventory["sources"]:
        require(sha256(WORKSPACE / row["workspace_path"]) == row["sha256"] == sha256(STAGE / row["snapshot_path"]), "frozen source identity changed: " + row["workspace_path"])
    return len(inventory["sources"])


def capture():
    source_count = source_guard()
    failed_log = STAGE / "provenance/scientific-verify.log"
    require("feature_ready_slots: null mismatch 45541.0/None" in failed_log.read_text(), "original scientific failure is missing")
    files = [Path(__file__), STAGE / "config.json", STAGE / "protocol.md", STAGE / "inputs.lock.json",
             STAGE / "events.manifest.json", STAGE / "evidence.manifest.json", STAGE / "provenance/source-inventory.json",
             STAGE / "provenance/reviews/coverage-fixtures.json", failed_log,
             STAGE / "report.md", STAGE / "report.html", STAGE / "advice.md", STAGE / "publication.json", STAGE / "source-bindings.json"]
    files.extend((STAGE / "tables").glob("*"))
    files.extend((STAGE / "figures").glob("*.png"))
    lock = json.loads((STAGE / "inputs.lock.json").read_text())
    delivery_path = Path(lock["delivery"]["path"])
    if not delivery_path.is_absolute():
        delivery_path = WORKSPACE / delivery_path
    files.append(delivery_path)
    require(sha256(delivery_path) == lock["delivery"]["sha256"], "native delivery manifest changed")
    records = json.loads((STAGE / "events.manifest.json").read_text())["records"]
    native = json.loads(delivery_path.read_text())["output_files"]
    external = records + [r for r in native if int(r["interval_minutes"]) == 5]
    for record in external:
        path = Path(record["path"])
        if not path.is_absolute():
            path = WORKSPACE / path
        require(path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"], "external input differs before execution")
    before = {"schema_version": 1, "run_id": STAGE.name, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "prepared", "source_count": source_count, "files": [identity(p) for p in sorted(set(files)) if p.is_file()],
              "external_manifest_records": external,
              "method": "Import byte-identical frozen canonical src.reconcile; replace only reconcile_coverage with this independent annual checker; call entire unchanged verify_bundle. No producer, estimator, outcome, bootstrap, selector, source inventory or protocol mutation.",
              "correction": "T00 development readiness is usable AND feature_valid for both chart intervals, with annual share/session support. Warmup native5m/undefined3m convention retained.",
              "original_failure_retained": identity(failed_log), "source_mutations": False}
    write(REVIEW / "coverage-adapter-before-execution.json", before)
    return before


def execute():
    before_path = REVIEW / "coverage-adapter-before-execution.json"
    before = json.loads(before_path.read_text())
    for pin in before["files"]:
        require(identity(pin["path"]) == pin, "prepared review input/source changed: " + pin["path"])
    source_guard()
    functions_before = {name: value for name, value in vars(FROZEN).items() if callable(value)}
    original = FROZEN.reconcile_coverage
    FROZEN.reconcile_coverage = independent_coverage
    try:
        receipt = FROZEN.verify_bundle(STAGE)
    finally:
        FROZEN.reconcile_coverage = original
    require(all(vars(FROZEN)[name] is value for name, value in functions_before.items()), "unexpected verifier mutation")
    require(receipt["status"] == "passed", "full frozen verification did not pass")
    source_guard()
    receipt["verification_correction"] = {"adapter": identity(__file__), "before_execution": identity(before_path),
                                          "synthetic_fixtures": identity(REVIEW / "coverage-fixtures.json"),
                                          "original_failure_retained": before["original_failure_retained"],
                                          "only_replaced_function": "reconcile_coverage", "canonical_sources_unchanged": True,
                                          "all_other_verify_bundle_checks_unchanged": True}
    write(STAGE / "provenance/scientific-reconciliation.json", receipt)
    records = json.loads((STAGE / "events.manifest.json").read_text())["records"]
    for record in records:
        path = Path(record["path"])
        require(path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"], "external ledger bytes changed after verification")
    write(STAGE / "provenance/external-bytes.json", {"status": "passed", "verified": len(records),
          "events_manifest": identity(STAGE / "events.manifest.json"),
          "records": [{key: r[key] for key in ("path", "sha256", "bytes", "row_count", "role", "product", "interval_minutes")} for r in records],
          "scope": "Explicit retained external ledger bytes; no backup certification.", "verification_adapter": identity(__file__)})
    completion = {"status": "passed", "run_id": STAGE.name, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                  "before_execution": identity(before_path), "adapter": identity(__file__), "checks": len(receipt["checks"]),
                  "scientific_reconciliation": identity(STAGE / "provenance/scientific-reconciliation.json"),
                  "external_bytes": identity(STAGE / "provenance/external-bytes.json"), "source_mutations": False,
                  "qualification": "Narrow verification-only readiness correction disclosed; numerical artifacts and all scientific estimators unchanged."}
    write(REVIEW / "coverage-adapter-completion.json", completion)
    return completion


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("fixtures", "prepare", "run"))
    args = parser.parse_args()
    if args.mode == "fixtures":
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CoverageFixtures))
        write(REVIEW / "coverage-fixtures.json", {"status": "passed" if result.wasSuccessful() else "failed", "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "checker": identity(__file__), "historical_outcomes_used": False})
        sys.exit(0 if result.wasSuccessful() else 1)
    elif args.mode == "prepare":
        print(json.dumps(capture(), indent=2))
    else:
        print(json.dumps(execute(), indent=2))
