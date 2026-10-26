"""Synthetic full-grid serial/parallel equivalence and failure controls."""
from concurrent.futures import ProcessPoolExecutor
import copy
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from src import stage3_parallel_reconcile as parallel
from src import stage3_reconcile as independent
from src import stage3_reference as reference
from src import stage3_statistics as producer
from src.engine import map_features
from src.stage3_events import generate_gateway_stream
from src.stage3_selection import fold_records, assess_candidates, select_nominees
from tests.test_stage3_reference import config, roster


class SyntheticAuthorization:
    period = "development"
    start = "2018-01-01"
    end = "2021-01-01"
    def validate(self, *args):
        if args[0] != "development":
            raise ValueError("synthetic fixture authorizes development only")


def json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def ledger(stage, path, frame, role, product, interval, **metadata):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return independent.record(path) | dict(role=role, product=product, interval_minutes=interval,
        row_count=len(frame), schema={k: str(v) for k, v in frame.dtypes.items()}, **metadata)


def clone_gate(frame, base, gate):
    result = frame.copy()
    result["gate_id"], result["gate_family"], result["gate_threshold"] = gate["gate_id"], gate["family"], gate["threshold"]
    if "row_id" in result:
        result["row_id"] = result.row_id.str.replace("|" + base["gate_id"] + "|", "|" + gate["gate_id"] + "|", regex=False)
    return result


def synthetic_bundle(stage):
    """Actual schemas, all six cells/192 gateways/14 horizons, no historical data.

    A large constant cloud makes every fixture gate pass. All gateway scientific
    populations are therefore identical within a branch; cloning metadata from
    the real producer's base table is exact and avoids 192 producer reruns.
    """
    cfg = config()
    cfg["periods"]["development"] = dict(start="2019-01-02", end="2019-01-03")
    json_write(stage / "config.json", cfg)
    (stage / "protocol.md").write_text("Synthetic parallel-verification fixture; development only.\n")
    json_write(stage / "baseline.lock.json", {})
    acceptance, paths, native_records = [], [], []
    scorecards, quantiles, stabilities, folds, audits, flows, coverages = [], [], [], [], [], [], []
    for product in cfg["products"]:
        native = roster(160, start="2019-01-02T14:00Z", interval=5)
        native["product"], native["contract"] = product, product + "H9"
        native["ema20"], native["ema50"], native["atr14"] = 1102., 100., 100.
        native["consecutive_count"] = np.arange(len(native)) + 50
        native["calendar_valid"] = True
        native.loc[:, "low"] = np.resize([1103., 100., 1103., 1101.], len(native))
        native["high"] = np.where(native.low.eq(100.), 1104., native.low + 2.)
        native["open"], native["close"] = native.low + 1., native.low + 1.
        nrec = ledger(stage, stage / "synthetic-inputs" / f"{product}_native5.parquet", native, "native", product, 5)
        native_records.append(nrec)
        for interval in cfg["interval_minutes"]:
            if interval == 5:
                raw = native.copy()
            else:
                raw = roster(240, start="2019-01-02T14:00Z", interval=3)
                raw["product"], raw["contract"] = product, product + "H9"
                raw["low"] = np.resize([1103., 100., 1103., 1101.], len(raw))
                raw["high"] = np.where(raw.low.eq(100.), 1104., raw.low + 2.)
                raw["open"], raw["close"] = raw.low + 1., raw.low + 1.
                raw["calendar_valid"] = True
            bars = map_features(raw, native, interval)
            acceptance.append(ledger(stage, stage / "synthetic-inputs" / f"{product}_{interval}_bars.parquet", bars, "bars", product, interval))
            ready = bars.usable & bars.feature_valid
            coverages.append(dict(row_id=f"{product}|{interval}|2019", product=product, interval_minutes=interval, year=2019,
                scope="input_only", scheduled_slots=len(bars), usable_slots=int(bars.usable.sum()), feature_ready_slots=int(ready.sum()), mapped_ready_slots=int(ready.sum()),
                atr_valid_slots=int((ready & bars.atr14.gt(0)).sum()), ready_share=float(ready.mean()), usable_share=float(bars.usable.mean()), unknown_signal_slots=int((~ready).sum()),
                contributing_sessions=bars.session.nunique(), ready_sessions=bars.loc[ready, "session"].nunique(), first_timestamp=bars.timestamp.min().isoformat(),
                last_available_at=bars.available_at.max().isoformat(), coverage_complete=bool(ready.all()), calendar_uncertified_slots=0,
                quality_counts=json.dumps({"complete":len(bars)})))
            fixed = dict(gate_id=reference.gate_id("absolute", cfg["minimum_width_points"][product]), family="absolute", threshold=cfg["minimum_width_points"][product])
            for branch in cfg["touch_modes"]:
                payload = generate_gateway_stream(bars, interval, branch, fixed)
                base_out, base_audit, base_record = producer._phase_stream(stage, cfg, payload, "development", SyntheticAuthorization())
                base_score = producer.summaries(base_out, payload, "development", cfg["horizons"])
                base_q = producer.quantiles(base_out, payload, "development", cfg["horizons"])
                base_stability = producer.stability(base_out, payload, "development", cfg)
                base_fold = fold_records(base_out, fixed, product, interval, branch, [f["id"] for f in cfg["development_folds"]])
                base_flow = producer._flow(payload, "development", cfg)
                for gate in reference.gate_grid(cfg, product):
                    actual = generate_gateway_stream(bars, interval, branch, gate)
                    if set(actual["events"].event_id) != set(payload["events"].event_id):
                        raise ValueError("fixture cloud must pass every gateway without changing acceptance")
                    metadata = dict(touch_mode=branch, gate_id=gate["gate_id"], period="development")
                    prefix = f"{product}_{interval}_{branch}_{gate['gate_id']}"
                    acceptance.append(ledger(stage, stage / "synthetic-acceptance" / (prefix + "_technical.parquet"), actual["technical"], "technical", product, interval, **metadata))
                    acceptance.append(ledger(stage, stage / "synthetic-acceptance" / (prefix + "_events.parquet"), actual["events"], "events", product, interval, **metadata))
                    if gate["gate_id"] == fixed["gate_id"]:
                        paths.append(base_record)
                    else:
                        paths.append(ledger(stage, stage / "ledgers/stage3/development" / (prefix + "_outcomes.parquet"), clone_gate(base_out, fixed, gate), "outcomes", product, interval, **metadata))
                    score = clone_gate(base_score, fixed, gate)
                    if gate["family"] == "atr":
                        score = score.loc[score.support.eq("common_atr_valid")].copy()
                    scorecards.append(score)
                    quantiles.append(clone_gate(base_q, fixed, gate))
                    stabilities.append(clone_gate(base_stability, fixed, gate))
                    folds.append(clone_gate(base_fold, fixed, gate))
                    audits.append(clone_gate(base_audit, fixed, gate))
                    flows.append(clone_gate(base_flow, fixed, gate))
    json_write(stage / "delivery.json", dict(output_files=native_records))
    json_write(stage / "inputs.lock.json", dict(delivery=independent.record(stage / "delivery.json")))
    json_write(stage / "mapped.manifest.json", dict(records=[r for r in acceptance if r["role"] == "bars"]))
    json_write(stage / "acceptance-development.manifest.json", dict(records=acceptance))
    grid = producer.grid_comparisons(pd.concat(scorecards, ignore_index=True), cfg)
    fold_table = pd.concat(folds, ignore_index=True)
    assessments = assess_candidates(fold_table, cfg, phase="development")
    nominees = select_nominees(assessments, cfg)
    fold_table["record_kind"], assessments["record_kind"] = "fold_support", "candidate_assessment"
    fold_table["phase"], fold_table["period_id"] = "development", "development"
    assessments["period_id"], assessments["fold_id"] = "development", "assessment"
    t12 = pd.concat([fold_table, assessments], ignore_index=True)
    t12["row_id"] = [producer._id(r, ("fold_id", "record_kind")) for r in t12.to_dict("records")]
    nominees["period_id"] = "development"
    nominees["row_id"] = [producer._id(r, ("phase",)) for r in nominees.to_dict("records")]
    tables = [producer._write_csv(stage, name, frame) for name, frame in (
        ("S3-T01_development_flow.csv", pd.concat(flows, ignore_index=True)),
        ("S3-T02_development_horizon_scorecard.csv", pd.concat(scorecards, ignore_index=True)),
        ("S3-T03_development_quantiles.csv", pd.concat(quantiles, ignore_index=True)),
        ("S3-T04_development_stability.csv", pd.concat(stabilities, ignore_index=True)),
        ("S3-T11_development_grid.csv", grid), ("S3-T12_development_fold_eligibility.csv", t12),
        ("S3-T13_development_nominees.csv", nominees), ("S3-T15_neighborhood_frontiers.csv", producer.neighborhoods(grid)),
        ("S3-T16_development_masks.csv", pd.concat(audits, ignore_index=True)))]
    producer._write_csv(stage, "S3-T00_coverage.csv", pd.DataFrame(coverages))
    producer._manifest(stage, "development", paths, tables, nominees)
    if cfg.get("development_recovery"):
        # This all-gateway fixture models receipt dependencies only. Its saved
        # scientific populations remain the exact existing synthetic grid.
        marker = stage / "provenance/synthetic-recovery-driver.txt"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("Synthetic recovery provenance; no historical recovery.\n")
        recovery = cfg["development_recovery"]
        for name in ("adopted-recovery-packets.json", "development-recovery-freeze.json",
                     "development-recovery-completion.json"):
            json_write(stage / "provenance" / name, dict(status="passed", phase="development",
                gateway_count=recovery["expected_adopted_gateways"] + len(recovery["expected_missing_gateways"]),
                adopted_count=recovery["expected_adopted_gateways"], missing_count=len(recovery["expected_missing_gateways"]),
                records=[independent.record(marker) | dict(path=marker.relative_to(stage).as_posix())],
                external_records=[]))


def first_payload(stage):
    cfg = json.loads((stage / "config.json").read_text())
    phase = json.loads((stage / "stage3-development.manifest.json").read_text())
    acceptance = json.loads((stage / "acceptance-development.manifest.json").read_text())
    _, choices = independent.read_csv(stage / "tables/S3-T13_development_nominees.csv")
    return dict(stage=str(stage), config=cfg, records=acceptance["records"] + phase["records"], phase_manifest=phase,
        bychoice={independent._identity_tuple(r):r for r in choices}, product="ES", interval_minutes=3,
        source_pins=[independent.record(p) for p in parallel.executable_sources()])


class ParallelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.stage = Path(cls.temporary.name)
        synthetic_bundle(cls.stage)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_full_six_cell_serial_parallel_scientific_equivalence(self):
        serial = independent.verify_bundle(self.stage, "development")
        scheduled_serial = parallel.verify_bundle(self.stage, workers=1)
        concurrent = parallel.verify_bundle(self.stage, workers=3)
        self.assertEqual(serial["checks"], scheduled_serial["checks"])
        self.assertEqual(serial["checks"], concurrent["checks"])
        for key in ("consumed", "records", "external_records"):
            normalize = lambda receipt: sorted(receipt[key], key=lambda r:r["path"])
            self.assertEqual(normalize(serial), normalize(concurrent))
        self.assertEqual(concurrent["parallel_orchestration"]["checks_skipped"], 0)
        self.assertEqual(len(concurrent["parallel_orchestration"]["cells"]), 6)
        self.assertEqual(len([r for r in concurrent["checks"] if r["check"] == "independent_full_gateway_state"]), 192)

    def test_failure_preserves_original_message_in_spawn_worker(self):
        path = self.stage / "acceptance-development.manifest.json"
        original_manifest = path.read_bytes()
        manifest = json.loads(original_manifest)
        record = next(r for r in manifest["records"] if r["role"] == "technical" and r["product"] == "ES" and r["interval_minutes"] == 3 and r["touch_mode"] == "fast")
        target = Path(record["path"])
        original_ledger = target.read_bytes()
        try:
            frame = pd.read_parquet(target)
            frame.loc[frame.index[0], "signal_idx"] = 1000000
            frame.to_parquet(target, index=False)
            record.update(independent.record(target))
            json_write(path, manifest)
            with self.assertRaises(ValueError) as serial:
                independent.verify_bundle(self.stage, "development")
            payload = first_payload(self.stage)
            with ProcessPoolExecutor(max_workers=3, mp_context=multiprocessing.get_context("spawn")) as pool:
                with self.assertRaises(ValueError) as concurrent:
                    pool.submit(parallel._worker, payload).result()
            self.assertEqual(str(serial.exception), str(concurrent.exception))
        finally:
            target.write_bytes(original_ledger)
            path.write_bytes(original_manifest)

    def test_duplicate_missing_and_ordered_cell_inventory(self):
        expected = [("ES",3),("ES",5)]
        results = [dict(product="ES",interval_minutes=5),dict(product="ES",interval_minutes=3)]
        self.assertEqual([r["interval_minutes"] for r in parallel.collect_cells(results, expected)], [3,5])
        for changed in ([results[0],results[0]],results[:1]):
            with self.assertRaises(ValueError):
                parallel.collect_cells(changed, expected)

    def test_source_drift_rejected_before_worker_science(self):
        payload = first_payload(self.stage)
        payload["source_pins"][0]["sha256"] = "0" * 64
        with ProcessPoolExecutor(max_workers=3, mp_context=multiprocessing.get_context("spawn")) as pool:
            with self.assertRaisesRegex(ValueError, "source/input drift"):
                pool.submit(parallel._worker, payload).result()

    def test_input_drift_and_conflicting_portable_pins_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "pin"
            target.write_text("before")
            before = independent.record(target)
            target.write_text("after")
            with self.assertRaises(ValueError):
                parallel.assert_pins([before])
            with self.assertRaises(ValueError):
                independent.portable_pins(Path(d), [before, independent.record(target)])

    def test_explicit_development_only_and_unchanged_ast(self):
        cell, read, identity = parallel.extraction_identity()
        self.assertEqual(identity["scientific_expressions_modified"], 0)
        self.assertEqual(identity["cell_body_ast_sha256"], parallel.extraction_identity()[2]["cell_body_ast_sha256"])
        self.assertTrue(cell.body)
        self.assertEqual(read.name, "read")
        for phase, workers in (("validation",3),("final",3),("recent",3),("complete",3),("development",2),("development",True)):
            with self.assertRaises(ValueError):
                parallel.verify_bundle(self.stage, phase, workers)


if __name__ == "__main__":
    unittest.main()
