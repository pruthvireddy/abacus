"""Recovery fixtures use synthetic bars only; adopted scorers must never run."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve()
WORKSPACE = next(p for p in ROOT.parents if (p / "studies/21_ema_cloud_trend_follow_opportunity").is_dir())
STUDY = WORKSPACE / "studies/21_ema_cloud_trend_follow_opportunity"
sys.path.insert(0, str(STUDY)); sys.path.insert(0, str(STUDY / "tests"))
draft = ROOT.with_name("stage3_recovery.py")
if draft.is_file() and ROOT.parent.name == "B-recovery":
    spec = importlib.util.spec_from_file_location("src.stage3_recovery", draft)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
from src import stage3_recovery as recovery
from src.execution import file_record, write_json
from src.stage3_events import generate_gateway_stream, gate_spec
from src.stage3_parallel_execution import configured_gates, stream_chunk, close_development
from test_stage3_events import bars
from test_stage3_parallel_execution import SyntheticAuthorization


def frame_record(frame, path, role, key=None, gate=None, stage=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression="zstd")
    record = file_record(path, stage) | dict(role=role, schema={c: str(t) for c, t in frame.dtypes.items()})
    if role == "outcomes":
        record.update(rows=len(frame), columns=list(frame), period_id="development")
    else:
        record.update(row_count=len(frame))
    if key:
        record.update(product=key[0], interval_minutes=key[1], touch_mode=key[2], gate_id=key[3])
    if gate:
        record.update(period="development", gate=gate)
    return record


def compact(payload):
    full, tech = payload["bars"], payload["technical"]
    keep = [c for c in tech if c not in full or c in ("product", "timestamp", "interval_minutes")]
    return tech[keep].copy()


def orchestration_fixture(base):
    """A complete192 identity fixture; numerical kernels are separately tested."""
    cfg = json.loads((STUDY / "config-stage3.json").read_text())
    cfg["development_recovery"] = dict(adopted_attempt_id="old", expected_adopted_gateways=187,
        expected_missing_gateways=[["NQ", 3, "slow", g] for g in ("atr_0p4", "atr_0p5", "atr_0p75", "atr_1", "atr_1p5")])
    expected = configured_gates(cfg); missing = tuple(tuple(k) for k in cfg["development_recovery"]["expected_missing_gateways"])
    stage, old = base / "new", base / "old"
    stage.mkdir(parents=True); old.mkdir()
    write_json(stage / "config.json", cfg)
    original_cfg = {k: v for k, v in cfg.items() if k != "development_recovery"}
    original_cfg["protocol_version"] = "0.1.0-stage3.1"
    write_json(old / "config.json", original_cfg)
    sources = []
    for name in recovery.KERNELS:
        target = old / "snapshots" / name
        target.parent.mkdir(exist_ok=True); target.write_text("unchanged synthetic kernel identity: " + name)
        sources.append(dict(workspace_path="studies/21_ema_cloud_trend_follow_opportunity/src/" + name,
                            snapshot_path="snapshots/" + name, **{k: v for k, v in file_record(target).items() if k != "path"}))
    for root in (stage, old): write_json(root / "provenance/source-inventory.json", dict(sources=sources))
    write_json(old / "provenance/parallel-development-before.json", dict(status="original_attempt"))
    for name in ("execution-freeze.json", "stage3-numerical.json"):
        write_json(stage / "provenance" / name, dict(status="passed"))
    mapped, packets, manifest_records = [], [], {}
    tiny = pd.DataFrame(dict(value=pd.Series([True], dtype=object)))
    for p in cfg["products"]:
        for i in cfg["interval_minutes"]:
            source = bars(4, i); source["product"] = p
            record = frame_record(source, old / "mapped" / f"{p}_{i}.parquet", "bars")
            record.update(product=p, interval_minutes=i)
            mapped.append(record); manifest_records[(p, i)] = [record]
    write_json(stage / "mapped.manifest.json", dict(records=mapped))
    for key in expected:
        if key in missing: continue
        p, i, t, g = key; gate = recovery.gate_specs(cfg, p)[g]
        technical = frame_record(tiny, old / "retained" / f"{p}_{i}m_{t}_{g}_technical.parquet", "technical", key, gate)
        events = frame_record(tiny, old / "retained" / f"{p}_{i}m_{t}_{g}_events.parquet", "events", key, gate)
        original_path = old / "ledgers/stage3/development" / f"{p}_{i}_{t}_{g}_outcomes.parquet"
        original_record = frame_record(tiny, original_path, "outcomes", key)
        target = stage / original_path.relative_to(old)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(original_path, target)
        packet = dict(key=list(key), gate=gate, technical=technical, events=events,
                      outcomes=original_record | dict(path=target.relative_to(stage).as_posix()), original_outcomes=file_record(original_path))
        packets.append(packet); manifest_records[(p, i)].extend([technical, events])
    cell_manifests = []
    for cell, records in manifest_records.items():
        if cell == ("NQ", 3): continue
        target = old / "provenance/cell-acceptance/development" / f"{cell[0]}_{cell[1]}.manifest.json"
        write_json(target, dict(schema_version="study21.stage3-acceptance/v1", period="development", records=records))
        cell_manifests.append(file_record(target))
    adoption = stage / "provenance/adopted-recovery-packets.json"
    write_json(adoption, dict(status="passed", records=[], external_records=[]))
    paths = [old / "config.json", old / "provenance/source-inventory.json", old / "provenance/parallel-development-before.json",
             Path(recovery.__file__), adoption]
    paths.extend(old / r["snapshot_path"] for r in sources)
    paths.extend(Path(r["path"]) for r in mapped + cell_manifests)
    for packet in packets:
        paths.extend(Path(packet[r]["path"]) for r in ("technical", "events", "original_outcomes"))
        paths.append(stage / packet["outcomes"]["path"])
    local, external = recovery.deduplicated_pins(stage, paths)
    freeze_path = stage / "provenance/development-recovery-freeze.json"
    write_json(freeze_path, dict(status="passed", schema_version=recovery.SCHEMA, source_stage=str(old), output_stage=str(stage),
        workspace=str(WORKSPACE), records=local, external_records=external, mapped=mapped, packets=packets,
        missing_gates=[list(k) for k in missing], cell_manifests=cell_manifests))
    auth = SyntheticAuthorization(expected, stage, WORKSPACE)
    def fake_chunk(key, record):
        return dict(key=key, record=record, **{field: pd.DataFrame(dict(gateway=["|".join(map(str, key))], value=pd.Series([None], dtype=object))) for field in recovery.FRAME_KEYS})
    def adopted(stage_, cfg_, packet, full):
        return fake_chunk(tuple(packet["key"]), packet["outcomes"])
    def score(stage_, cfg_, payload, auth_):
        key = payload["product"], payload["interval_minutes"], payload["touch_mode"], payload["gate"]["gate_id"]
        path = stage_ / "ledgers/stage3/development" / ("_".join(map(str, key)) + "_outcomes.parquet")
        require_absent = not path.exists()
        if not require_absent: raise AssertionError("missing scorer attempted to overwrite")
        record = frame_record(tiny, path, "outcomes", key, stage=stage_)
        return fake_chunk(key, record)
    def iterator(stage_, period, allowed, *, cell, manifest_path):
        records = [r for r in mapped if (r["product"], r["interval_minutes"]) == tuple(cell)]
        for key in allowed:
            p, i, t, g = key; gate = recovery.gate_specs(cfg, p)[g]
            for role in ("technical", "events"):
                records.append(frame_record(tiny, stage_ / "retained" / f"{p}_{i}m_{t}_{g}_{role}.parquet", role, key, gate))
            yield dict(product=p, interval_minutes=i, touch_mode=t, gate=gate)
        write_json(manifest_path, dict(schema_version="study21.stage3-acceptance/v1", period=period, records=records))
    def close(stage_, cfg_, chunks, expected_):
        if tuple(c["key"] for c in chunks) != expected_: raise AssertionError("global recovery reordered")
        path = stage_ / "stage3-development.manifest.json"
        if path.exists(): raise AssertionError("global close overwritten")
        write_json(path, dict(status="produced", records=[c["record"] for c in chunks]))
        return dict(manifest=file_record(path, stage_), records=[c["record"] for c in chunks], tables=[])
    return dict(stage=stage, cfg=cfg, auth=auth, freeze=freeze_path, expected=expected, missing=missing,
                adopted=adopted, score=score, iterator=iterator, close=close)


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.cfg = json.loads((STUDY / "config-stage3.json").read_text())
        cls.cfg["products"], cls.cfg["interval_minutes"] = ["ES"], [3, 5]
        cls.cfg["absolute_gates"]["ES"], cls.cfg["atr_gates"], cls.cfg["horizons"] = [0., 2.4], [.5], [1, 15]
        cls.cfg["development_surface_folds"] = [cls.cfg["development_surface_folds"][2]]
        cls.expected = configured_gates(cls.cfg)
        cls.cfg["development_recovery"] = dict(adopted_attempt_id="original", expected_adopted_gateways=10,
                                               expected_missing_gateways=[list(k) for k in cls.expected[-2:]])
        cls.original, cls.output = cls.base / "original", cls.base / "output"
        cls.auth = SyntheticAuthorization(cls.expected)
        cls.payloads, cls.original_chunks, cls.packets, cls.mapped = {}, {}, [], {}
        for interval in (3, 5):
            source = bars(160, interval)
            source["low"] = np.resize([104., 102., 104., 99.], 160)
            source["high"] = source.low + 5.
            source["open"], source["close"] = source.low + 2., source.low + 3.
            if interval == 5: source["atr14"] = np.nan
            cls.mapped[("ES", interval)] = source
            for key in (k for k in cls.expected if k[1] == interval):
                gate = recovery.gate_specs(cls.cfg, "ES")[key[3]]
                payload = generate_gateway_stream(source, interval, key[2], gate)
                cls.payloads[key] = payload
                chunk = stream_chunk(cls.original, cls.cfg, payload, cls.auth)
                cls.original_chunks[key] = chunk
                technical = frame_record(compact(payload), cls.base / "retained" / f"ES_{interval}m_{key[2]}_{key[3]}_technical.parquet", "technical", key, gate)
                events = frame_record(payload["events"], cls.base / "retained" / f"ES_{interval}m_{key[2]}_{key[3]}_events.parquet", "events", key, gate)
                if key in cls.expected[:-2]:
                    relative = chunk["record"]["path"]
                    target = cls.output / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(cls.original / relative, target)
                    cls.packets.append(dict(key=list(key), gate=gate, technical=technical, events=events,
                        outcomes=copy.deepcopy(chunk["record"]), original_outcomes=file_record(cls.original / relative)))
        cls.serial_receipt = close_development(cls.original, cls.cfg, [cls.original_chunks[k] for k in cls.expected], cls.expected)
        cls.freeze = dict(packets=cls.packets, missing_gates=[list(k) for k in cls.expected[-2:]])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_adopted_mask_and_scientific_frames_exact_without_scorer(self):
        # Both imports are blocked: no adopted future-path computation can hide
        # behind an imported function reference in the statistics producer.
        with patch("src.stage3_statistics.score_period", side_effect=AssertionError("adopted rescoring forbidden")), \
             patch("src.stage3_outcomes.score_period", side_effect=AssertionError("adopted rescoring forbidden")):
            for packet in self.packets:
                key = tuple(packet["key"])
                actual = recovery.adopted_chunk(self.output, self.cfg, packet, self.mapped[key[:2]])
                self.assertEqual(actual["key"], key)
                self.assertEqual(actual["record"], self.original_chunks[key]["record"])
                for field in recovery.FRAME_KEYS:
                    pd.testing.assert_frame_equal(actual[field], self.original_chunks[key][field], check_exact=True)

    def test_recovered_global_close_matches_original_all_nine_csv_bytes_and_fallback(self):
        output = self.base / "close-equality"
        chunks = []
        for key in self.expected:
            if key in self.expected[:-2]:
                packet = next(p for p in self.packets if tuple(p["key"]) == key)
                target = output / packet["outcomes"]["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.output / packet["outcomes"]["path"], target)
                chunk = recovery.adopted_chunk(output, self.cfg, packet, self.mapped[key[:2]])
            else:
                chunk = stream_chunk(output, self.cfg, self.payloads[key], self.auth)
            chunks.append(chunk)
        result = close_development(output, self.cfg, chunks, self.expected)
        for a, b in zip(self.serial_receipt["tables"], result["tables"]):
            self.assertEqual(a, b)
            self.assertEqual((self.original / a["path"]).read_bytes(), (output / b["path"]).read_bytes(), a["path"])
        self.assertEqual((self.original / "stage3-development.manifest.json").read_bytes(),
                         (output / "stage3-development.manifest.json").read_bytes())
        self.assertTrue(result["choices"].fallback.all())
        self.assertTrue(result["choices"].selection_score.isna().all())

    def test_packet_partition_requires_complete_unique_exact_original_gates(self):
        expected, packets, missing = recovery.packet_plan(self.cfg, self.freeze, tuple(reversed(self.expected)))
        self.assertEqual(expected, self.expected)
        self.assertEqual(set(packets), set(self.expected[:-2]))
        self.assertEqual(missing, self.expected[-2:])
        for mutation in ("missing", "duplicate", "outside", "spec", "missing_order"):
            bad = copy.deepcopy(self.freeze)
            if mutation == "missing": bad["packets"].pop()
            elif mutation == "duplicate": bad["packets"].append(bad["packets"][0])
            elif mutation == "outside": bad["packets"][0]["key"][3] = "abs_99"
            elif mutation == "spec": bad["packets"][0]["gate"]["threshold"] = 99.
            else: bad["missing_gates"].reverse()
            with self.assertRaises(ValueError): recovery.packet_plan(self.cfg, bad, self.expected)
        with self.assertRaises(ValueError): recovery.packet_plan(self.cfg, self.freeze, self.expected[:-1])

    def test_strict_metadata_filename_original_copy_schema_and_byte_pins(self):
        packet = copy.deepcopy(self.packets[0])
        recovery.check_packet_records(packet, self.output)
        for mutation in ("role", "gate", "phase", "original", "filename"):
            bad = copy.deepcopy(packet)
            if mutation == "role": bad["events"]["role"] = "technical"
            elif mutation == "gate": bad["technical"]["gate_id"] = "abs_99"
            elif mutation == "phase": bad["outcomes"]["period_id"] = "final"
            elif mutation == "original": bad["original_outcomes"]["sha256"] = "0" * 64
            else: bad["technical"]["path"] = str(Path(bad["technical"]["path"]).with_name("wrong.parquet"))
            with self.assertRaises(ValueError): recovery.check_packet_records(bad, self.output)
        for mutation in ("rows", "schema", "order", "columns", "bytes"):
            bad = copy.deepcopy(packet["outcomes"])
            if mutation == "rows": bad["rows"] += 1
            elif mutation == "schema": bad["schema"]["direction"] = "int64"
            elif mutation == "order": bad["schema"] = dict(reversed(list(bad["schema"].items())))
            elif mutation == "columns": bad["columns"].reverse()
            else: bad["sha256"] = "0" * 64
            with self.assertRaises(ValueError): recovery.read_frame(bad, self.output)

    def test_linked_technical_requires_all_ordinals_nulls_dtypes_and_order(self):
        key = self.expected[0]; payload = self.payloads[key]
        native = compact(payload)
        restored = recovery.reconstruct_payload(payload["bars"], native, payload["events"], key, payload["gate"], self.cfg)
        pd.testing.assert_frame_equal(restored["technical"], payload["technical"], check_exact=True)
        for mutation in ("missing", "reordered", "timestamp", "ordinal", "dtype", "null", "event_copy"):
            tech, events = native.copy(), payload["events"].copy()
            if mutation == "missing": tech = tech.iloc[:-1].copy()
            elif mutation == "reordered": tech = tech.iloc[::-1].reset_index(drop=True)
            elif mutation == "timestamp": tech.loc[1, "timestamp"] = tech.timestamp.iloc[0]
            elif mutation == "ordinal": tech.loc[2, "signal_idx"] += 1
            elif mutation == "dtype": tech["direction"] = tech.direction.astype("int64")
            elif mutation == "null": tech.loc[events.signal_idx.iloc[0], "width"] = np.nan
            else: events.loc[0, "ema20"] += 1.
            with self.assertRaises((ValueError, AssertionError)):
                recovery.reconstruct_payload(payload["bars"], tech, events, key, payload["gate"], self.cfg)

    def test_mask_reconstruction_rejects_wrong_null_boolean_row_order_and_ordinal(self):
        key = self.expected[0]; out = pd.read_parquet(self.original / self.original_chunks[key]["record"]["path"])
        for mutation in ("order", "ordinal", "embargo", "fold", "null", "outside"):
            bad = out.copy()
            if mutation == "order": bad = bad.iloc[::-1].reset_index(drop=True)
            elif mutation == "ordinal": bad.loc[0, "terminal_signal_idx"] += 1
            elif mutation == "embargo": bad.loc[0, "start_embargo"] = not bad.start_embargo.iloc[0]
            elif mutation == "fold": bad.loc[0, "fold_id"] = "wrong"
            elif mutation == "null": bad.loc[0, "entry_atr"] = np.nan
            else: bad.loc[0, "status"] = "outside"
            with self.assertRaises((ValueError, AssertionError)):
                recovery.rebuild_audit(bad, self.payloads[key], self.cfg)

    def test_checkpoint_preserves_all_exact_typed_frames_and_refuses_overwrite_drift(self):
        stage = self.base / "checkpoint"
        dependency = dict(path="frozen-before.json", bytes=5, sha256="a" * 64)
        chunk = self.original_chunks[self.expected[0]]
        record = recovery.checkpoint(stage, chunk, dependency)
        loaded = recovery.load_checkpoint(stage, record, dependency)
        for field in recovery.FRAME_KEYS:
            pd.testing.assert_frame_equal(loaded[field], chunk[field], check_exact=True)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            recovery.checkpoint(stage, chunk, dependency)
        with self.assertRaisesRegex(ValueError, "dependency"):
            recovery.load_checkpoint(stage, record, dependency | dict(bytes=6))
        receipt = json.loads((stage / record["path"]).read_text())
        binary = stage / receipt["records"][0]["path"]
        before = binary.read_bytes()
        binary.write_bytes(before + b"drift")
        with self.assertRaisesRegex(ValueError, "identity"):
            recovery.load_checkpoint(stage, record, dependency)
        binary.write_bytes(before)

    def test_null_free_object_boolean_parquet_seam_preserves_nine_original_tables(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["interval_minutes"] = [3]
        cfg["canonical_start_embargo_slots"] = 0
        gates = configured_gates(cfg)
        auth = SyntheticAuthorization(gates)
        original, output = self.base / "bool-original", self.base / "bool-recovered"
        source = self.mapped[("ES", 3)].copy()
        source.loc[140:, "low"] = 104.
        source["high"], source["open"], source["close"] = source.low + 5., source.low + 2., source.low + 3.
        original_chunks, recovered_chunks = [], []
        for key in gates:
            gate = recovery.gate_specs(cfg, "ES")[key[3]]
            payload = generate_gateway_stream(source, 3, key[2], gate)
            chunk = stream_chunk(original, cfg, payload, auth)
            original_chunks.append(chunk)
            decoded = pd.read_parquet(original / chunk["record"]["path"])
            self.assertTrue(decoded.status.eq("completed").all())
            self.assertTrue(all(str(decoded[c].dtype) == "bool" and chunk["record"]["schema"][c] == "object" for c in recovery.ROUNDTRIP_FLAGS))
            technical = frame_record(compact(payload), self.base / "bool-retained" / f"ES_3m_{key[2]}_{key[3]}_technical.parquet", "technical", key, gate)
            events = frame_record(payload["events"], self.base / "bool-retained" / f"ES_3m_{key[2]}_{key[3]}_events.parquet", "events", key, gate)
            target = output / chunk["record"]["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / chunk["record"]["path"], target)
            packet = dict(key=list(key), gate=gate, technical=technical, events=events,
                          outcomes=chunk["record"], original_outcomes=file_record(original / chunk["record"]["path"]))
            with patch("src.stage3_statistics.score_period", side_effect=AssertionError("adopted rescoring forbidden")):
                recovered = recovery.adopted_chunk(output, cfg, packet, source)
            recovered_chunks.append(recovered)
            for field in recovery.FRAME_KEYS:
                pd.testing.assert_frame_equal(chunk[field], recovered[field], check_exact=True)
        a = close_development(original, cfg, original_chunks, gates)
        b = close_development(output, cfg, recovered_chunks, gates)
        for x, y in zip(a["tables"], b["tables"]):
            self.assertEqual(x, y)
            self.assertEqual((original / x["path"]).read_bytes(), (output / y["path"]).read_bytes())

    def test_failure_incomplete_order_cannot_close_and_existing_packets_survive(self):
        hashes = [(p["outcomes"]["path"], file_record(self.output / p["outcomes"]["path"])["sha256"]) for p in self.packets]
        stage = self.base / "refused-close"
        for chunks in ([self.original_chunks[k] for k in self.expected[:-1]],
                       [self.original_chunks[k] for k in reversed(self.expected)]):
            with self.assertRaisesRegex(ValueError, "complete development chunk order"):
                close_development(stage, self.cfg, chunks, self.expected)
        self.assertFalse(stage.exists())
        self.assertEqual(hashes, [(p["outcomes"]["path"], file_record(self.output / p["outcomes"]["path"])["sha256"]) for p in self.packets])

    def test_generic_receipts_reject_relative_externals_traversal_duplicate_and_drift(self):
        stage = self.base / "pins"; stage.mkdir()
        source = stage / "source.txt"; source.write_text("synthetic")
        value = dict(status="passed", records=[file_record(source, stage)], external_records=[])
        recovery.generic_pins(value, stage)
        for bad in (dict(records=[], external_records=[value["records"][0]]),
                    dict(records=[dict(path="../outside", bytes=0, sha256="0" * 64)], external_records=[]),
                    dict(records=value["records"] * 2, external_records=[]),
                    dict(records=[value["records"][0] | dict(bytes=0)], external_records=[])):
            with self.assertRaises(ValueError): recovery.generic_pins(bad, stage)

    def test_public_recovery_rejects_reserved_and_foreign_stage_before_any_helper(self):
        for auth in (None, SyntheticAuthorization(self.expected, self.output, WORKSPACE, period="final"),
                     SyntheticAuthorization(self.expected, self.original, WORKSPACE)):
            with patch.object(recovery, "assert_frozen", side_effect=AssertionError("guard reached")):
                with self.assertRaisesRegex(ValueError, "matching development"):
                    recovery.recover_development(self.output, self.cfg, auth, self.output / "provenance/development-recovery-freeze.json")

    def test_complete192_orchestration_only_scores_five_then_one_ordered_global_close(self):
        f = orchestration_fixture(self.base / "public-complete")
        with patch.object(recovery, "assert_frozen") as source_guard, patch.object(recovery, "assert_input_bytes") as input_guard, \
             patch.object(recovery, "assert_numerical_gate"), patch.object(recovery, "adopted_chunk", side_effect=f["adopted"]) as adopted, \
             patch.object(recovery, "stream_chunk", side_effect=f["score"]) as score, \
             patch.object(recovery, "close_development", side_effect=f["close"]) as close, \
             patch("run_stage3.gateway_iterator", side_effect=f["iterator"]), patch("builtins.print"):
            result = recovery.recover_development(f["stage"], f["cfg"], f["auth"], f["freeze"])
        self.assertEqual(adopted.call_count, 187); self.assertEqual(score.call_count, 5); self.assertEqual(close.call_count, 1)
        self.assertGreaterEqual(source_guard.call_count, 3); self.assertGreaterEqual(input_guard.call_count, 3)
        self.assertEqual(len(result["records"]), 192)
        receipt = json.loads((f["stage"] / "provenance/development-recovery-completion.json").read_text())
        self.assertEqual((receipt["status"], receipt["phase"], receipt["gateway_count"], receipt["adopted_count"], receipt["missing_count"], receipt["checkpoint_count"], receipt["global_close_count"]),
                         ("passed", "development", 192, 187, 5, 192, 1))
        recovery.generic_pins(receipt, f["stage"])
        self.assertFalse(receipt["adopted_outcomes_scored"])
        self.assertEqual(tuple(tuple(k) for k in receipt["missing_gateways_scored"]), f["missing"])
        acceptance = json.loads((f["stage"] / "acceptance-development.manifest.json").read_text())["records"]
        self.assertEqual(len(acceptance), 390)
        self.assertEqual(tuple(recovery.key_of(r) for r in acceptance[6::2]), f["expected"])

    def test_missing_worker_failure_preserves187_and_partial_checkpoint_without_close(self):
        f = orchestration_fixture(self.base / "public-failure")
        before = {p.name: file_record(p)["sha256"] for p in (f["stage"] / "ledgers/stage3/development").glob("*.parquet")}
        def interrupted(*args, **kwargs):
            for payload in f["iterator"](*args, **kwargs):
                yield payload
                raise RuntimeError("synthetic missing-gateway failure")
        with patch.object(recovery, "assert_frozen"), patch.object(recovery, "assert_input_bytes"), \
             patch.object(recovery, "assert_numerical_gate"), patch.object(recovery, "stream_chunk", side_effect=f["score"]), \
             patch.object(recovery, "adopted_chunk") as adopted, patch.object(recovery, "close_development") as close, \
             patch("run_stage3.gateway_iterator", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "missing-gateway failure"):
                recovery.recover_development(f["stage"], f["cfg"], f["auth"], f["freeze"])
        self.assertFalse(close.called); self.assertFalse(adopted.called)
        self.assertTrue(all(file_record(f["stage"] / "ledgers/stage3/development" / name)["sha256"] == digest for name, digest in before.items()))
        self.assertEqual(len(list((f["stage"] / "provenance/recovery-checkpoints").glob("*.pickle"))), 1)
        self.assertFalse((f["stage"] / "stage3-development.manifest.json").exists())
        self.assertFalse((f["stage"] / "provenance/development-recovery-completion.json").exists())
        failure = json.loads((f["stage"] / "provenance/development-recovery-failure.json").read_text())
        self.assertEqual(failure["status"], "failed_partial_artifacts_preserved")


if __name__ == "__main__":
    unittest.main()
