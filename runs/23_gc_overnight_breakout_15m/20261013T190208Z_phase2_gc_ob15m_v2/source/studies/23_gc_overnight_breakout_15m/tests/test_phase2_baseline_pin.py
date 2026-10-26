"""Synthetic byte/authority guards; do not calculate alternative outcomes."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("study23_phase2_baseline_pin",HERE/"phase2_baseline_pin.py")
p=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(p)


class BaselinePinTests(unittest.TestCase):
    def test_selected_bytes_and_hash_drift(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory).resolve();file=root/"fixture";file.write_bytes(b"pinned original")
            record=dict(path="fixture",bytes=file.stat().st_size,sha256=p.digest(file))
            self.assertEqual(p.verify_records(root,[record])[0]["sha256"],record["sha256"])
            file.write_bytes(b"changed bytes")
            with self.assertRaises(ValueError):p.verify_records(root,[record])

    def test_unsafe_symlink_and_duplicate_selections_refused(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory).resolve();file=root/"fixture";file.write_text("original")
            record=dict(path="fixture",bytes=file.stat().st_size,sha256=p.digest(file))
            with self.assertRaisesRegex(ValueError,"duplicate"):p.verify_records(root,[record,record])
            for name in ("../fixture","/fixture","./fixture","a//fixture"):
                with self.assertRaises(ValueError):p.ordinary_file(root,name)
            (root/"linked").symlink_to(file)
            with self.assertRaisesRegex(ValueError,"symlink"):p.ordinary_file(root,"linked")

    def test_duplicate_json_and_nonfinite_pins_refused(self):
        with tempfile.TemporaryDirectory()as directory:
            file=Path(directory)/"json"
            for value in ('{"sha":"old","sha":"new"}','{"price":NaN}'):
                file.write_text(value)
                with self.assertRaises(ValueError):p.read_json(file)

    def test_real_frozen_baseline_conventions_and_scenario_count(self):
        config=json.loads((HERE/"config-phase1.json").read_text())
        scenarios={name:dict(signal_minutes=15,stop_percent=1,tick_size=.1,point_value=100,
            model="validated_native",execution_minutes=1)for name in p.SCENARIOS}
        p.verify_protocol(config,scenarios)
        changed=copy.deepcopy(config);changed["stop_percent"]=.5
        with self.assertRaisesRegex(ValueError,"convention changed"):p.verify_protocol(changed,scenarios)
        with self.assertRaisesRegex(ValueError,"nine"):p.verify_protocol(config,{k:v for k,v in scenarios.items()if k!="source-account"})

    def test_cost_or_contract_economics_cannot_be_silently_replaced(self):
        config=json.loads((HERE/"config-phase1.json").read_text())
        scenarios={name:dict(signal_minutes=15,stop_percent=1,tick_size=.1,point_value=100,
            model="validated_native",execution_minutes=1)for name in p.SCENARIOS}
        for path,value in (("costs",3),("instrument",10)):
            changed=copy.deepcopy(config)
            changed[path]["commission_fees_dollars_per_contract_per_side"if path=="costs"else "dollars_per_point"]=value
            with self.assertRaises(ValueError):p.verify_protocol(changed,scenarios)

    def test_live_check_requires_actual_status_and_exact_bytes(self):
        row=dict(url="https://example.invalid/original",bytes=3,sha256="a"*64)
        okay=lambda url:dict(status=200,bytes=3,sha256="a"*64)
        self.assertEqual(len(p.verify_live([row],okay)),1)
        for response in [dict(status=403,bytes=3,sha256="a"*64),dict(status=200,bytes=4,sha256="a"*64),dict(status=200,bytes=3,sha256="b"*64)]:
            with self.assertRaisesRegex(ValueError,"live Phase1"):p.verify_live([row],lambda url:response)

    def test_new_phase2_audit_never_overwrites_or_targets_completed_run(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory).resolve();stage=root/"work"/p.STUDY/"new-phase2"
            value=dict(status="passed",checked_at="synthetic",counts={},phase1_manifest={},publication=dict(live_checked=True),limits=[])
            p.write_new_audit(root,stage,value)
            original=(stage/"baseline-pin/phase1-baseline.pin.json").read_bytes()
            with self.assertRaises(FileExistsError):p.write_new_audit(root,stage,value)
            self.assertEqual((stage/"baseline-pin/phase1-baseline.pin.json").read_bytes(),original)
            for blocked in (root/"runs"/p.STUDY/"new-phase2",root/"work"/p.STUDY/p.RUN_ID):
                with self.assertRaises(ValueError):p.write_new_audit(root,blocked,value)


if __name__=="__main__":unittest.main()
