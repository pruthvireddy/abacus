"""Synthetic execution/ordering/failure fixtures; no historical inputs read."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from src.execution import file_record, write_json
from src.stage3_events import gate_spec, generate_gateway_stream
from src.stage3_parallel_execution import (CellJob, acceptance_records, cell_plan, close_development,
    close_evaluation, collect_cells, configured_gates, evaluate_period_parallel, evaluation_plan,
    ordered_chunks, produce_development_parallel, run_cell, stream_chunk, validate_outcome_records)
from src.stage3_statistics import evaluate_period, produce_development
from src.stage3_selection import fixed_gate_id
from test_stage3_events import bars


def config():
    return json.loads((STUDY / "config-stage3.json").read_text())


class SyntheticAuthorization:
    def __init__(self, gates, stage=None, workspace=None, *, period="development", start="2018-01-01", end="2021-01-01"):
        self.period, self.start, self.end = period, start, end
        self.gates = tuple(gates)
        self.stage, self.workspace = stage, workspace
        self.calls, self.predecessor = 0, None

    def validate(self, period, product, interval, touch, gate):
        self.calls += 1
        if period != self.period or (product, interval, touch, gate) not in self.gates:
            raise ValueError("outside synthetic authorization")


def synthetic_worker(job):
    """Picklable spawned test worker; never calls research producers."""
    if job["fail"]:
        raise RuntimeError("intentional cell failure")
    time.sleep(job["delay"])
    return dict(ordinal=job["ordinal"], pid=os.getpid(), value=job["value"])


def chunk_results(plan):
    return [dict(ordinal=i, cell=item["cell"], chunks=[dict(key=g) for g in item["gates"]])
            for i, item in enumerate(plan)]


def frozen_choices(cfg):
    rows = []
    for product in cfg["products"]:
        fixed = fixed_gate_id(product, cfg)
        candidate = gate_spec("absolute", cfg["absolute_gates"][product][4])["gate_id"]
        for interval in cfg["interval_minutes"]:
            for touch in cfg["touch_modes"]:
                selected = candidate if touch == "fast" else fixed
                rows.append(dict(product=product, interval_minutes=interval, touch_mode=touch,
                    nominee_gate_id=selected, selected_gate_id=selected, final_gate_id=selected, fixed_gate_id=fixed,
                    nomination_status="eligible_improvement" if touch == "fast" else "no_eligible_improvement",
                    selection_score=1. if touch == "fast" else np.nan, selection_improvement=.1 if touch == "fast" else np.nan,
                    selected_gate_family="absolute", selected_gate_threshold=cfg["absolute_gates"][product][4] if touch == "fast" else cfg["minimum_width_points"][product]))
    return pd.DataFrame(rows)


class ParallelExecutionTest(unittest.TestCase):
    def test_complete192_shards_are_disjoint32_streams_and_original_order(self):
        cfg = config()
        gates = configured_gates(cfg)
        plan = cell_plan(cfg, reversed(gates))
        self.assertEqual(len(gates), 192)
        self.assertEqual([p["cell"] for p in plan], [(p, i) for p in ("ES", "GC", "NQ") for i in (3, 5)])
        self.assertEqual([len(p["gates"]) for p in plan], [32] * 6)
        self.assertEqual(tuple(g for p in plan for g in p["gates"]), gates)
        self.assertEqual(gates[:9], tuple(("ES", 3, "fast", g) for g in
            ("abs_0", "abs_1p2", "abs_1p8", "abs_2p4", "abs_3", "abs_3p6", "abs_4p8", "abs_7p2", "atr_0p1")))
        for bad in (gates[:-1], gates + (gates[0],), gates[:-1] + (("ES", 3, "fast", "abs_99"),)):
            with self.assertRaisesRegex(ValueError, "inventory"):
                cell_plan(cfg, bad)

    def test_unordered_cell_completion_restores_original_per_gate_frame_order(self):
        cfg = config(); plan = cell_plan(cfg, configured_gates(cfg))
        results = chunk_results(plan)
        chunks, ordered = ordered_chunks(plan, list(reversed(results)))
        self.assertEqual(tuple(c["key"] for c in chunks), configured_gates(cfg))
        self.assertEqual([r["ordinal"] for r in ordered], list(range(6)))
        for bad in (results[:-1], results + [results[0]]):
            with self.assertRaises(ValueError): ordered_chunks(plan, bad)
        bad = copy.deepcopy(results); bad[0]["cell"] = ("ES", 5)
        with self.assertRaisesRegex(ValueError, "identity"):
            ordered_chunks(plan, bad)
        for mutation in ("missing", "duplicate", "reordered"):
            bad = copy.deepcopy(results)
            if mutation == "missing": bad[0]["chunks"].pop()
            elif mutation == "duplicate": bad[0]["chunks"][-1] = bad[0]["chunks"][0]
            else: bad[0]["chunks"].reverse()
            with self.assertRaisesRegex(ValueError, "gateway chunks"):
                ordered_chunks(plan, bad)

    def test_spawned_pool_uses_three_workers_and_aborts_on_failure(self):
        parent = os.getpid()
        jobs = [dict(ordinal=i, fail=False, delay=.1, value=str(i)) for i in range(6)]
        actual = collect_cells(jobs, 3, synthetic_worker)
        self.assertEqual({r["ordinal"] for r in actual}, set(range(6)))
        self.assertTrue(all(r["pid"] != parent for r in actual))
        self.assertEqual(len({r["pid"] for r in actual}), 3)
        jobs[0]["fail"] = True
        with self.assertRaisesRegex(RuntimeError, "intentional cell failure"):
            collect_cells(jobs, 3, synthetic_worker)
        with self.assertRaises(ValueError): collect_cells([], 0, synthetic_worker)

    def test_serial_and_sharded_scientific_outputs_are_exact_for_all_nine_tables(self):
        cfg = config()
        cfg["products"], cfg["interval_minutes"] = ["ES"], [3, 5]
        cfg["absolute_gates"]["ES"], cfg["atr_gates"], cfg["horizons"] = [0., 2.4], [.5], [1, 15]
        cfg["development_surface_folds"] = [cfg["development_surface_folds"][2]]
        payloads = []
        for interval in cfg["interval_minutes"]:
            source = bars(160, interval)
            source["low"] = np.resize([104., 102., 104., 99.], 160)
            source["high"] = source.low + 5.
            source["open"], source["close"] = source.low + 2., source.low + 3.
            # A real cross-cell undefined/populated dtype boundary at global concatenation.
            if interval == 5: source["atr14"] = np.nan
            for touch in cfg["touch_modes"]:
                specs = [gate_spec("absolute", value) for value in cfg["absolute_gates"]["ES"]] + [gate_spec("atr", .5)]
                for spec in specs:
                    payloads.append(generate_gateway_stream(source, interval, touch, spec))
        self.assertTrue(all(p["events"].empty for p in payloads if p["interval_minutes"] == 5 and p["gate"]["family"] == "atr"))
        gates = configured_gates(cfg)
        auth = SyntheticAuthorization(gates)
        with tempfile.TemporaryDirectory() as tmp:
            serial, sharded = Path(tmp) / "serial", Path(tmp) / "sharded"
            serial_receipt = produce_development(serial, cfg, iter(payloads), auth)
            plan = cell_plan(cfg, gates)
            results = []
            # Deliberately finish the later cell first; retain original per-gate frames.
            for ordinal in reversed(range(len(plan))):
                item = plan[ordinal]
                work = [p for p in payloads if (p["product"], p["interval_minutes"]) == item["cell"]]
                results.append(dict(ordinal=ordinal, cell=item["cell"],
                    chunks=[stream_chunk(sharded, cfg, p, auth) for p in work]))
            chunks, _ = ordered_chunks(plan, results)
            validate_outcome_records(sharded, chunks)
            parallel_receipt = close_development(sharded, cfg, chunks, gates)
            self.assertEqual(len(serial_receipt["tables"]), 9)
            for a, b in zip(serial_receipt["tables"], parallel_receipt["tables"]):
                self.assertEqual(a["path"], b["path"])
                self.assertEqual((serial / a["path"]).read_bytes(), (sharded / b["path"]).read_bytes(), a["path"])
            for a, b in zip(serial_receipt["records"], parallel_receipt["records"]):
                self.assertEqual(a, b)
                pd.testing.assert_frame_equal(pd.read_parquet(serial / a["path"]), pd.read_parquet(sharded / b["path"]), check_exact=True)
            self.assertEqual(json.loads((serial / "stage3-development.manifest.json").read_text()),
                             json.loads((sharded / "stage3-development.manifest.json").read_text()))
            self.assertTrue(parallel_receipt["choices"].fallback.all())
            self.assertTrue(parallel_receipt["choices"].selected_gate_id.eq("abs_2p4").all())
            masked = pd.read_csv(sharded / "tables/S3-T16_development_masks.csv")
            self.assertGreater(masked.excluded_start_embargo.sum(), 0)
            self.assertGreater(masked.completed.sum(), 0)

    def test_acceptance_merge_requires_complete_exact_scientific_roles_and_bytes(self):
        cfg = config(); cfg["products"], cfg["interval_minutes"] = ["ES"], [3, 5]
        cfg["touch_modes"], cfg["absolute_gates"]["ES"], cfg["atr_gates"] = ["fast"], [2.4], []
        gates = configured_gates(cfg); plan = cell_plan(cfg, gates)
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp); mapped, results = [], []
            for ordinal, item in enumerate(plan):
                product, interval = item["cell"]
                bar = stage / f"bars_{interval}.txt"; bar.write_text("synthetic bar identity")
                mapped.append(file_record(bar) | dict(role="bars", product=product, interval_minutes=interval))
                records = [mapped[-1]]
                for role in ("technical", "events"):
                    path = stage / f"{interval}_{role}.txt"; path.write_text(role)
                    records.append(file_record(path) | dict(role=role, product=product, interval_minutes=interval,
                        touch_mode="fast", gate_id="abs_2p4"))
                manifest = stage / f"{interval}.manifest.json"
                write_json(manifest, dict(schema_version="study21.stage3-acceptance/v1", period="development", records=records))
                results.append(dict(cell=item["cell"], acceptance_manifest=file_record(manifest, stage)))
            actual = acceptance_records(stage, mapped, results, gates)
            self.assertEqual([r["role"] for r in actual], ["bars", "bars", "technical", "events", "technical", "events"])
            original = json.loads((stage / "3.manifest.json").read_text())
            for mutation in ("missing", "duplicate", "outside", "phase"):
                bad = copy.deepcopy(original)
                if mutation == "missing": bad["records"].pop()
                elif mutation == "duplicate": bad["records"].append(bad["records"][-1])
                elif mutation == "outside": bad["records"][-1]["gate_id"] = "abs_99"
                else: bad["period"] = "validation"
                write_json(stage / "3.manifest.json", bad)
                results[0]["acceptance_manifest"] = file_record(stage / "3.manifest.json", stage)
                with self.assertRaises(ValueError): acceptance_records(stage, mapped, results, gates)
            write_json(stage / "3.manifest.json", original)
            results[0]["acceptance_manifest"] = file_record(stage / "3.manifest.json", stage)
            (stage / "3_events.txt").write_text("mutated retained source bytes")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                acceptance_records(stage, mapped, results, gates)

    def test_outcome_identity_rejects_wrong_gate_phase_and_duplicate_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp); path = stage / "out.txt"; path.write_text("saved synthetic outcome")
            chunk = dict(key=("ES", 3, "fast", "abs_2p4"), record=file_record(path, stage) |
                dict(role="outcomes", period_id="development", product="ES", interval_minutes=3,
                     touch_mode="fast", gate_id="abs_2p4"))
            validate_outcome_records(stage, [chunk])
            for column, value in (("gate_id", "abs_0"), ("period_id", "validation"), ("role", "events")):
                bad = copy.deepcopy(chunk); bad["record"][column] = value
                with self.assertRaisesRegex(ValueError, "identity differs"):
                    validate_outcome_records(stage, [bad])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                validate_outcome_records(stage, [chunk, chunk])

    def test_production_guards_refuse_reserved_or_partial_or_existing_before_scoring(self):
        cfg = config()
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            write_json(stage / "config.json", cfg)
            auth = SyntheticAuthorization(configured_gates(cfg), stage, stage)
            with patch("src.stage3_parallel_execution.collect_cells") as scoring:
                auth.period = "validation"
                with self.assertRaisesRegex(ValueError, "development phase"):
                    produce_development_parallel(stage, cfg, auth)
                auth.period = "development"; auth.gates = auth.gates[:-1]
                with self.assertRaisesRegex(ValueError, "inventory"):
                    produce_development_parallel(stage, cfg, auth)
                auth.gates = configured_gates(cfg)
                (stage / "acceptance-development.manifest.json").write_text("retained partial disposition")
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    produce_development_parallel(stage, cfg, auth)
                self.assertEqual((stage / "acceptance-development.manifest.json").read_text(), "retained partial disposition")
                scoring.assert_not_called()

    def test_cell_worker_requires_complete_original_whitelist_and_retained_manifest(self):
        cfg = config(); cfg["products"], cfg["interval_minutes"] = ["ES"], [3]
        cfg["touch_modes"], cfg["absolute_gates"]["ES"], cfg["atr_gates"] = ["fast"], [2.4, 3.], []
        gates = configured_gates(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp); auth = SyntheticAuthorization(gates, stage, stage)
            manifest = stage / "partial.json"
            job = CellJob(0, ("ES", 3), gates, stage, cfg, auth, manifest)
            calls = []
            def iterator(output, period, allowed, **kwargs):
                calls.append((output, period, allowed, kwargs))
                for key in gates:
                    yield dict(product=key[0], interval_minutes=key[1], touch_mode=key[2],
                        gate=dict(gate_id=key[3]))
                manifest.write_text("synthetic completed manifest")
            def chunk(output, settings, payload, authorization):
                return dict(key=(payload["product"], payload["interval_minutes"], payload["touch_mode"], payload["gate"]["gate_id"]))
            with patch("src.stage3_parallel_execution.assert_frozen"), patch("run_stage3.gateway_iterator", iterator), \
                 patch("src.stage3_parallel_execution.stream_chunk", chunk):
                result = run_cell(job)
                self.assertEqual(tuple(c["key"] for c in result["chunks"]), gates)
                self.assertEqual(calls[0][3], dict(cell=("ES", 3), manifest_path=manifest))
                with self.assertRaisesRegex(ValueError, "complete original"):
                    run_cell(CellJob(0, ("ES", 3), gates[:-1], stage, cfg, auth, manifest))
                with patch("run_stage3.gateway_iterator", return_value=iter(())):
                    with self.assertRaisesRegex(ValueError, "incomplete"):
                        run_cell(job)

    def test_parent_failure_retains_partial_bytes_and_refuses_all_global_close(self):
        cfg = config()
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            write_json(stage / "config.json", cfg)
            for relative in ("provenance/source-inventory.json", "inputs.lock.json", "provenance/fixed-baseline-parity.json"):
                write_json(stage / relative, dict(synthetic_fixture=True))
            mapped = []
            for product in cfg["products"]:
                for interval in cfg["interval_minutes"]:
                    path = stage / f"{product}_{interval}_bars.txt"; path.write_text("synthetic pinned input")
                    mapped.append(file_record(path) | dict(role="bars", product=product, interval_minutes=interval))
            write_json(stage / "mapped.manifest.json", dict(records=mapped))
            auth = SyntheticAuthorization(configured_gates(cfg), stage, stage)
            partial = stage / "ledgers/stage3/development/retained_partial.parquet"
            def fail(jobs, workers):
                self.assertEqual(len(jobs), 6)
                self.assertEqual(workers, 3)
                self.assertEqual(len({j.acceptance_manifest for j in jobs}), 6)
                before = json.loads((stage / "provenance/parallel-development-before.json").read_text())
                self.assertEqual(sum(len(c["gates"]) for c in before["cells"]), 192)
                partial.parent.mkdir(parents=True); partial.write_text("retained synthetic partial bytes")
                raise RuntimeError("intentional parent incomplete cell failure")
            with patch("src.stage3_parallel_execution.assert_frozen") as guard, \
                 patch("src.stage3_parallel_execution.assert_input_bytes") as input_guard, \
                 patch("src.stage3_parallel_execution.collect_cells", side_effect=fail), \
                 patch("src.stage3_parallel_execution.close_development") as close:
                with self.assertRaisesRegex(RuntimeError, "incomplete cell failure"):
                    produce_development_parallel(stage, cfg, auth)
                guard.assert_called_once_with(stage.resolve(), stage)
                input_guard.assert_called_once_with(stage.resolve())
                close.assert_not_called()
            self.assertEqual(partial.read_text(), "retained synthetic partial bytes")
            self.assertFalse((stage / "acceptance-development.manifest.json").exists())
            self.assertFalse((stage / "stage3-development.manifest.json").exists())
            self.assertFalse((stage / "tables").exists())
            self.assertEqual(json.loads((stage / "provenance/parallel-development-failure.json").read_text())["status"],
                "failed_partial_artifacts_preserved")
            with self.assertRaisesRegex(ValueError, "fresh development outcome"):
                produce_development_parallel(stage, cfg, auth)

    def test_reserved_plan_is_only_frozen_choice_plus_own_fixed_without_rescue(self):
        cfg = config(); choices = frozen_choices(cfg)
        allowed = sorted({(r.product, r.interval_minutes, r.touch_mode, g) for r in choices.itertuples()
                          for g in (r.selected_gate_id, r.fixed_gate_id)})
        for period in ("validation", "final", "recent"):
            plan = evaluation_plan(cfg, choices, period, reversed(allowed))
            self.assertEqual(len(plan), 6)
            self.assertEqual(sum(len(p["gates"]) for p in plan), 18)
            self.assertTrue(all(len(p["gates"]) == 3 for p in plan))
            self.assertEqual(tuple(g for p in plan for g in p["gates"]), tuple(allowed))
            for bad in (allowed[:-1], allowed + [allowed[0]], configured_gates(cfg)):
                with self.assertRaisesRegex(ValueError, "roster"):
                    evaluation_plan(cfg, choices, period, bad)
        with self.assertRaisesRegex(ValueError, "cell inventory"):
            evaluation_plan(cfg, choices.iloc[:-1], "final", allowed)
        bad = choices.copy(); bad.loc[0, "fixed_gate_id"] = "abs_0"
        with self.assertRaisesRegex(ValueError, "own-cell"):
            evaluation_plan(cfg, bad, "final", allowed)
        bad = choices.copy(); bad.loc[0, "final_gate_id"] = "abs_0"
        with self.assertRaisesRegex(ValueError, "columns disagree"):
            evaluation_plan(cfg, bad, "final", allowed)
        # Failed validation retains the nominee descriptively; final authorization
        # may include only selected fixed identity, without the failed nominee.
        fallback = choices.copy()
        fallback["selected_gate_id"], fallback["final_gate_id"] = fallback.fixed_gate_id, fallback.fixed_gate_id
        fixed_only = sorted({(r.product, r.interval_minutes, r.touch_mode, r.fixed_gate_id) for r in fallback.itertuples()})
        self.assertEqual(sum(len(p["gates"]) for p in evaluation_plan(cfg, fallback, "final", fixed_only)), 12)
        with self.assertRaisesRegex(ValueError, "roster"):
            evaluation_plan(cfg, fallback, "final", allowed)

    def test_serial_reserved_tables_effects_decisions_and_identity_nulls_match_exactly(self):
        cfg = config(); cfg["products"] = ["ES"]; cfg["horizons"] = [1, 15]
        cfg["bootstrap"]["resamples"] = 37
        choices = frozen_choices(cfg)
        allowed = sorted({(r.product, r.interval_minutes, r.touch_mode, g) for r in choices.itertuples()
                          for g in (r.selected_gate_id, r.fixed_gate_id)})
        with tempfile.TemporaryDirectory() as tmp:
            for period in ("validation", "final", "recent"):
                with self.subTest(period=period):
                    limits = cfg["periods"][period]
                    auth = SyntheticAuthorization(allowed, period=period, start=limits["start"], end=limits["end"])
                    plan = evaluation_plan(cfg, choices, period, allowed)
                    payloads = []
                    for interval in cfg["interval_minutes"]:
                        source = bars(160, interval)
                        shift = pd.Timestamp(limits["start"][:10] + "T14:00Z") + pd.Timedelta(days=1) - source.timestamp.iloc[0]
                        for col in ("timestamp", "available_at", "feature_source_timestamp", "feature_available_at"):
                            source[col] = source[col] + shift
                        source["session"] = source.timestamp.iloc[0].strftime("%Y-%m-%d")
                        source["low"] = np.resize([104., 102., 104., 99.], 160)
                        source["high"], source["close"], source["open"] = source.low + 5., source.low + 3., source.low + 2.
                        source.loc[np.arange(1, 160, 4), "ema20"] = 102.8
                        if interval == 5: source["atr14"] = np.nan
                        specs = {gate_spec("absolute", v)["gate_id"]: gate_spec("absolute", v) for v in cfg["absolute_gates"]["ES"]}
                        for p, i, touch, gate in allowed:
                            if i == interval:
                                payloads.append(generate_gateway_stream(source, interval, touch, specs[gate]))
                    serial, sharded = Path(tmp) / period / "serial", Path(tmp) / period / "sharded"
                    original = evaluate_period(serial, cfg, choices, period, auth, iter(payloads))
                    results = []
                    for ordinal in reversed(range(len(plan))):
                        item = plan[ordinal]
                        work = [p for p in payloads if (p["product"], p["interval_minutes"]) == item["cell"]]
                        results.append(dict(ordinal=ordinal, cell=item["cell"],
                            chunks=[stream_chunk(sharded, cfg, p, auth, period=period) for p in work]))
                    chunks, _ = ordered_chunks(plan, results)
                    validate_outcome_records(sharded, chunks, period=period)
                    actual = close_evaluation(sharded, cfg, choices, period, chunks, allowed)
                    self.assertEqual(len(actual["tables"]), 9 if period == "validation" else 7)
                    for a, b in zip(original["tables"], actual["tables"]):
                        self.assertEqual(a, b)
                        self.assertEqual((serial / a["path"]).read_bytes(), (sharded / b["path"]).read_bytes(), a["path"])
                    for a, b in zip(original["records"], actual["records"]):
                        self.assertEqual(a, b)
                        pd.testing.assert_frame_equal(pd.read_parquet(serial / a["path"]), pd.read_parquet(sharded / b["path"]), check_exact=True)
                    self.assertEqual(json.loads((serial / f"stage3-{period}.manifest.json").read_text()),
                                     json.loads((sharded / f"stage3-{period}.manifest.json").read_text()))
                    effects = pd.read_csv(sharded / f"tables/S3-T14_{period}_effects.csv", float_precision="round_trip")
                    primary = effects.loc[effects.horizon.eq(15) & effects.direction.eq("All") & effects.unit.eq("atr") &
                        effects.metric.eq("terminal_delta") & effects.weighting.eq("event") & effects.block_weeks.eq(4)]
                    identity = primary.loc[primary.touch_mode.eq("slow") & primary.interval_minutes.eq(3)]
                    self.assertTrue(identity.estimate.eq(0).all() and identity.ci_low.eq(0).all() and identity.ci_high.eq(0).all())
                    undefined = primary.loc[primary.interval_minutes.eq(5)]
                    self.assertTrue(undefined.estimate.isna().all() and undefined.ci_low.isna().all() and undefined.ci_high.isna().all())
                    self.assertTrue(undefined.undefined_draws.eq(37).all())
                    if period == "validation":
                        self.assertTrue(actual["choices"].selected_gate_id.eq("abs_2p4").all())
                        self.assertIn("fixed_fallback_validation_failed", set(actual["choices"].validation_status))
                        # Nominee effects survive failed selection; final identity
                        # has not replaced them in the validation evidence.
                        self.assertTrue(primary.loc[primary.touch_mode.eq("fast"), "selected_gate_id"].eq("abs_3").all())
                    if period == "final":
                        family = primary.loc[primary.interval_kind.eq("bonferroni12")]
                        self.assertTrue(family.quantile_low.eq(.05 / 24).all())
                        self.assertTrue(family.quantile_high.eq(1 - .05 / 24).all())

    def test_reserved_parent_failure_preserves_partial_without_effects_or_decisions(self):
        cfg = config(); choices = frozen_choices(cfg)
        allowed = sorted({(r.product, r.interval_minutes, r.touch_mode, g) for r in choices.itertuples()
                          for g in (r.selected_gate_id, r.fixed_gate_id)})
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp); write_json(stage / "config.json", cfg)
            for relative in ("provenance/source-inventory.json", "inputs.lock.json"):
                write_json(stage / relative, dict(synthetic_fixture=True))
            mapped = []
            for product in cfg["products"]:
                for interval in cfg["interval_minutes"]:
                    path = stage / f"{product}_{interval}_bars.txt"; path.write_text("synthetic pinned input")
                    mapped.append(file_record(path) | dict(role="bars", product=product, interval_minutes=interval))
            write_json(stage / "mapped.manifest.json", dict(records=mapped))
            limits = cfg["periods"]["validation"]
            auth = SyntheticAuthorization(allowed, stage, stage, period="validation", start=limits["start"], end=limits["end"])
            partial = stage / "ledgers/stage3/validation/retained_partial.parquet"
            def fail(jobs, workers):
                self.assertTrue(all(j.period == "validation" for j in jobs))
                self.assertEqual(sum(len(j.gates) for j in jobs), 18)
                partial.parent.mkdir(parents=True); partial.write_text("reserved synthetic partial bytes")
                raise RuntimeError("intentional reserved failure")
            with patch("src.stage3_parallel_execution.assert_frozen"), patch("src.stage3_parallel_execution.assert_input_bytes"), \
                 patch("src.stage3_parallel_execution.collect_cells", side_effect=fail), patch("src.stage3_parallel_execution.close_evaluation") as close:
                with self.assertRaisesRegex(RuntimeError, "reserved failure"):
                    evaluate_period_parallel(stage, cfg, choices, "validation", auth)
                close.assert_not_called()
            self.assertEqual(partial.read_text(), "reserved synthetic partial bytes")
            self.assertFalse((stage / "tables").exists())
            self.assertFalse((stage / "acceptance-validation.manifest.json").exists())
            self.assertFalse((stage / "stage3-validation.manifest.json").exists())
            self.assertEqual(json.loads((stage / "provenance/parallel-validation-failure.json").read_text())["status"], "failed_partial_artifacts_preserved")
            with self.assertRaisesRegex(ValueError, "fresh reserved"):
                evaluate_period_parallel(stage, cfg, choices, "validation", auth)


if __name__ == "__main__":
    unittest.main()
