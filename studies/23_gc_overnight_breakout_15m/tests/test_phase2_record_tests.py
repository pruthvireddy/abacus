"""Synthetic actual unittest-child results and numerical receipt drift guards."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase2_record_tests as recorder
from test_phase2_seal import fixture,put

REAL_RUN=subprocess.run
TINY="import unittest\nclass Tiny(unittest.TestCase):\n    def test_truth(self): self.assertEqual(2+2,4)\n"


class NumericalReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir="/private/tmp")
        self.root=Path(self.temp.name)
        self.stage,_,_=fixture(self.root)
        put(self.root/"uv.lock",(self.stage/"environment.lock").read_text())
        self.tiny=self.root/"studies"/recorder.STUDY/"tests/test_tiny.py"
        put(self.tiny,TINY)
        put(self.root/"studies"/recorder.STUDY/"phase2_record_tests.py",Path(recorder.__file__).read_text())
        for name in ("unittest_child.py","uv"):
            path=self.root/"scripts"/name;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(recorder.ROOT/"scripts"/name,path)
        self.record=self.stage/"numerical-tests/final/receipt.json"

    def tearDown(self):self.temp.cleanup()

    def execute_fixture_child(self,command,**kwargs):
        # Execute the real retained child against disposable tiny unittest
        # fixtures. The production helper's uv invocation is asserted below;
        # these fixtures intentionally do not install/sync another environment.
        self.assertEqual(command[1:5],["run","--locked","--no-sync","python"])
        self.assertEqual(Path(command[5]),self.root/"scripts/unittest_child.py")
        return REAL_RUN([sys.executable,*command[5:]],**kwargs)

    def run_fixture(self,executor=None):
        with patch.object(recorder.subprocess,"run",side_effect=executor or self.execute_fixture_child):
            return recorder.record_tests(self.stage,root=self.root)

    def test_actual_child_result_is_retained_and_stage_bound(self):
        result=self.run_fixture()
        self.assertEqual(result["tests_run"],1)
        record=recorder.validate_record(self.stage,self.record,self.root)
        self.assertEqual(record["successful_callbacks"],1)
        self.assertEqual(record["counts"]["tests_run"],1)
        self.assertEqual(record["skips"],[])
        self.assertEqual(record["environment"]["PYTHONDONTWRITEBYTECODE"],"1")
        self.assertTrue(any(p["original_workspace_path"].endswith("unittest_child.py") for p in record["source_snapshots"]))
        self.assertTrue(any(p["original_workspace_path"].endswith("test_tiny.py") for p in record["source_snapshots"]))
        self.assertTrue(all((self.stage/p["path"]).is_file() for p in record["source_snapshots"]))

    def test_fresh_attempt_never_overwrites_existing_record(self):
        self.run_fixture();before=self.record.read_bytes()
        with self.assertRaises(FileExistsError):self.run_fixture()
        self.assertEqual(self.record.read_bytes(),before)

    def test_completed_run_cannot_receive_new_numerical_evidence(self):
        put(self.root/"runs"/recorder.STUDY/self.stage.name/"kept","completed")
        with self.assertRaises(FileExistsError):self.run_fixture()
        self.assertFalse((self.stage/"numerical-tests").exists())

    def test_stage_and_workspace_lock_must_match(self):
        put(self.root/"uv.lock","different locked environment")
        with self.assertRaises(ValueError):self.run_fixture()
        self.assertFalse((self.stage/"numerical-tests").exists())

    def test_frozen_producer_drift_refused_before_execution(self):
        file=self.root/"studies"/recorder.STUDY/"phase2_accounts.py";put(file,file.read_text()+"\n# drift")
        with self.assertRaises(ValueError):self.run_fixture()
        self.assertFalse((self.stage/"numerical-tests").exists())

    def test_actual_failure_and_log_are_retained_but_gate_refuses(self):
        put(self.tiny,TINY.replace("2+2,4","2+2,5"))
        with self.assertRaises(ValueError):self.run_fixture()
        record=recorder.read_json(self.record)
        self.assertEqual(record["status"],"failed")
        self.assertEqual(record["counts"]["failures"],1)
        self.assertIn("FAILED",(self.record.parent/"tests.log").read_text())
        with self.assertRaises(ValueError):recorder.validate_record(self.stage,self.record,self.root)

    def test_all_skipped_actual_child_is_not_a_passing_gate(self):
        put(self.tiny,TINY.replace("class Tiny","@unittest.skip('fixture skip')\nclass Tiny"))
        with self.assertRaises(ValueError):self.run_fixture()
        record=recorder.read_json(self.record)
        self.assertEqual(record["child_outcome"],"all_skipped")
        self.assertEqual(record["counts"]["skipped"],1)
        self.assertEqual(record["successful_callbacks"],0)

    def test_source_change_during_child_retains_failed_drift_record(self):
        def executor(command,**kwargs):
            result=self.execute_fixture_child(command,**kwargs)
            put(self.tiny,TINY+"\n# source changed after test")
            return result
        with self.assertRaises(ValueError):self.run_fixture(executor)
        record=recorder.read_json(self.record)
        self.assertEqual(record["child_outcome"],"passed")
        self.assertEqual(record["status"],"failed")
        self.assertIn("bytes changed",record["error"])

    def test_source_and_wrapper_drift_after_pass_refused(self):
        self.run_fixture()
        for file in (self.tiny,self.root/"scripts/unittest_child.py"):
            old=file.read_bytes();file.write_bytes(old+b"\n# changed")
            with self.assertRaises(ValueError):recorder.validate_record(self.stage,self.record,self.root)
            file.write_bytes(old)

    def test_receipt_cannot_replace_actual_child_counts(self):
        self.run_fixture();record=recorder.read_json(self.record)
        record["counts"]["tests_run"]=99;put(self.record,record)
        with self.assertRaises(ValueError):recorder.validate_record(self.stage,self.record,self.root)

    def test_child_result_bytes_and_duplicate_json_refused(self):
        self.run_fixture();record=recorder.read_json(self.record)
        child=self.stage/record["child_result"]["path"];put(child,'{"outcome":"failed","outcome":"passed"}')
        with self.assertRaises(ValueError):recorder.validate_record(self.stage,self.record,self.root)

    def test_symlink_source_selection_refused_before_execution(self):
        (self.tiny.parent/"linked.py").symlink_to(self.tiny)
        with self.assertRaises(ValueError):self.run_fixture()
        self.assertFalse((self.stage/"numerical-tests").exists())


if __name__=="__main__":unittest.main()
