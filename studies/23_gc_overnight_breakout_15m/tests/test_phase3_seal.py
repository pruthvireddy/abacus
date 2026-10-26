"""Synthetic lifecycle failures cannot masquerade as sealed research evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from phase3_seal import preflight,GATES,identity,digest


class Phase3SealTests(unittest.TestCase):
    def prepare(self,root):
        stage=root/"synthetic-phase3";stage.mkdir()
        def put(path,value):
            p=stage/path;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value) if not isinstance(value,str) else value)
            return identity(stage,path)
        settings=put("config.json",{"run_id":stage.name})
        protocol=put("protocol.md","Synthetic protocol")
        lock=put("uv.lock","synthetic-lock")
        source=put("source/checker.py","# synthetic reviewer source\n")
        freeze=put("execution-freeze.json",{"settings_sha256":settings["sha256"],"source_files":[source]})
        complete=put("execution-completion.json",{"phase3":"computed"})
        selection=put("selection.json",{"later_outcomes_opened":False})
        selectionfreeze=put("selection-freeze.json",{"selection_sha256":selection["sha256"],"later_outcomes_opened":False,"frozen_at":"2026-10-13T02:00:00Z"})
        put("phases/dev-validation/completion.json",{"finished_at":"2026-10-13T01:00:00Z"})
        put("phases/later/completion.json",{"started_at":"2026-10-13T03:00:00Z"})
        gates={}
        for name in GATES:
            receipt={"status":"passed","run_id":stage.name}
            if name=="numerical":receipt.update(counts={"discovered":1,"tests_run":1,"failures":0,"errors":0,"skipped":0,"unexpected_successes":0},execution_freeze_sha256=freeze["sha256"],successful_callbacks=1)
            gates[name]={**put(f"checks/{name}.json",receipt),"checker_sources":[source]}
        publications=[]
        for i in range(19):
            pub=f"synthetic-{i}";folder=f"publications/{pub}"
            report=put(folder+"/publication.json",{"id":pub})
            mapping=put(folder+"/source-map.json",{})
            put(folder+"/publication-verification.json",{"status":"passed","publication_sha256":report["sha256"],"source_map_sha256":mapping["sha256"]})
            manifest=put(folder+"/publication-manifest.json",{"source_run_id":stage.name,"outputs":[{"path":f"runs/23_gc_overnight_breakout_15m/{stage.name}/"+report["path"],"sha256":report["sha256"]}]})
            publications.append({"publication_id":pub,"manifest":manifest})
        spec={"schema_version":"study23.phase3-sealing-inputs/v1","run_id":stage.name,"publication_sources_prepared_before_seal":True,"execution_freeze":freeze,"settings":settings,"protocol":protocol,"environment_lock":lock,"completion":complete,"gates":gates,"selection":selection,"selection_freeze":selectionfreeze,"publications":publications}
        put("sealing-inputs.json",spec)
        return stage,spec,put

    def test_complete_synthetic_metadata_gate_and_changed_settings_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();stage,spec,put=self.prepare(root)
            self.assertEqual(preflight(stage,root)["status"],"passed")
            put("config.json",{"retuned":True})
            with self.assertRaisesRegex(ValueError,"bytes changed"):preflight(stage,root)

    def test_failed_science_receipt_and_missing_required_gate_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();stage,spec,put=self.prepare(root)
            spec["gates"]["science"]={**put("checks/science.json",{"status":"failed"}),"checker_sources":[identity(stage,"source/checker.py")]}
            put("sealing-inputs.json",spec)
            with self.assertRaisesRegex(ValueError,"did not pass"):preflight(stage,root)
            del spec["gates"]["science"];put("sealing-inputs.json",spec)
            with self.assertRaisesRegex(ValueError,"gate roster"):preflight(stage,root)

    def test_later_opened_before_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();stage,spec,put=self.prepare(root)
            put("phases/later/completion.json",{"started_at":"2026-10-13T00:00:00Z"})
            with self.assertRaisesRegex(ValueError,"chronological"):preflight(stage,root)

    def test_numeric_skips_and_changed_report_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();stage,spec,put=self.prepare(root)
            receipt=json.loads((stage/"checks/numerical.json").read_text());receipt["counts"]["skipped"]=1
            spec["gates"]["numerical"]={**put("checks/numerical.json",receipt),"checker_sources":[identity(stage,"source/checker.py")]};put("sealing-inputs.json",spec)
            with self.assertRaisesRegex(ValueError,"meaningful suite"):preflight(stage,root)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();stage,spec,put=self.prepare(root)
            put("publications/synthetic-0/publication.json",{"altered":True})
            with self.assertRaisesRegex(ValueError,"report bytes"):preflight(stage,root)


if __name__=="__main__":unittest.main()
