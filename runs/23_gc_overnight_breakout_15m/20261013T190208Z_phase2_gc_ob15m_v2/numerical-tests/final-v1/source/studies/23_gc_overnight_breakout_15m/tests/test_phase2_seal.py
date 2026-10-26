"""Disposable Phase 2 lifecycle gates; never seal a retained research run."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

FILE=Path(__file__).resolve().parents[1]/"phase2_seal.py"
SPEC=importlib.util.spec_from_file_location("study23_phase2_sealer",FILE)
seal=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(seal)
RUN="20261013T190208Z_phase2_synthetic"


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(value if isinstance(value,str) else json.dumps(value,allow_nan=False))


def fixture(root):
    stage=root/"work"/seal.STUDY/RUN;stage.mkdir(parents=True)
    old=root/"runs"/seal.STUDY/"phase1-synthetic"
    for name in ("manifest.json","protocol.md","config.json","inputs.lock.json","coverage.csv","days.csv"):
        put(old/name,"synthetic pinned baseline "+name)
    old_pin={name:seal.identity(root,str((old/name).relative_to(root))) for name in ("manifest.json","protocol.md","config.json","inputs.lock.json","coverage.csv","days.csv")}
    baseline_external=root/"data/research/sahadeva"/seal.STUDY/"phase1-synthetic"/"original-ledger.gz"
    put(baseline_external,"retained baseline source")
    baseline_ext={"id":"baseline","locator":str(baseline_external.relative_to(root)),"bytes":baseline_external.stat().st_size,"sha256":seal.digest(baseline_external)}
    baseline={"status":"passed","study_id":seal.STUDY,"phase2_outcomes_calculated":False,
              "phase1_manifest":old_pin["manifest.json"],"baseline_protocol":old_pin["protocol.md"],"baseline_config":old_pin["config.json"],
              "original_market_lock":old_pin["inputs.lock.json"],"coverage_roster":old_pin["coverage.csv"],"complete_day_roster":old_pin["days.csv"],
              "local_artifacts":list(old_pin.values()),"selected_market_input_pins":[],"retained_source_pins":[],
              "retained_external_artifacts":[baseline_ext],"scenario_ledgers":[baseline_ext],"prepared_execution_inputs":{},
              "scenario_ledger_counts":{"primary-one-tick":{"trades":2}}}
    put(stage/"phase2-baseline-pin.json",baseline)
    put(stage/"config.json",{"run_id":RUN,"protocol_version":"2.0.0","phase3_state":"unimplemented_uncomputed","baseline_manifest_sha256":old_pin["manifest.json"]["sha256"]})
    put(stage/"protocol.md","frozen synthetic protocol")
    put(stage/"environment.lock","synthetic existing locked environment")
    put(stage/"inputs.lock.json",{"sha256":seal.digest(stage/"phase2-baseline-pin.json")})
    put(stage/"git-status.txt"," M synthetic producer")
    sources=[]
    for name in sorted(seal.RUNTIME):
        live=root/"studies"/seal.STUDY/name;put(live,"# synthetic frozen producer "+name)
        copied="source/studies/"+seal.STUDY+"/"+name;put(stage/copied,live.read_text())
        sources.append(seal.identity(stage,copied))
    freeze={"at":"2026-10-13T19:00:00Z","revision":"a"*40,"dirty":True,"source_files":sources}
    for name,key in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("phase2-baseline-pin.json","baseline_pin_sha256"),("environment.lock","environment_lock_sha256")):
        freeze[key]=seal.digest(stage/name)
    put(stage/"execution-freeze.json",freeze)
    put(stage/"selection.json",{"selected_policy":None,"frozen_at":"2026-10-13T19:01:00Z","later_alternative_outcomes_opened":False})
    selection_hash=seal.digest(stage/"selection.json")
    phases={};phase_artifacts=[]
    for name,years,end in (("dev-validation",[str(y) for y in range(2018,2024)],"19:01:02"),("later",["2024","2025","2026"],"19:03:00")):
        pins=[]
        for stem in ("policies","occurrence","recovery","boundary-events","level-opportunities"):
            path="phases/"+name+"/"+stem+".jsonl.gz";put(stage/path,"synthetic frozen "+name+" "+stem)
            pins.append(seal.identity(root,str((stage/path).relative_to(root))))
            phase_artifacts.append(path)
        completion={"finished_at":"2026-10-13T"+end+"Z","episodes":1,"original_years":years,"ledgers":pins,
                    "settings_sha256":freeze["settings_sha256"],"selection_sha256":selection_hash}
        path="phases/"+name+"/completion.json";put(stage/path,completion);phase_artifacts.append(path);phases[name]=completion
    put(stage/"selection-freeze.json",{"selection_sha256":selection_hash,"settings_sha256":freeze["settings_sha256"],
        "frozen_at":"2026-10-13T19:01:01Z","later_outcomes_opened":False,"development_validation_ledger":phases["dev-validation"]["ledgers"][0]})
    put(stage/"verification/dev-receipt.json",{"status":"passed","finished_at":"2026-10-13T19:01:30Z"})
    put(stage/"phase-starts.json",{"later":{"started_at":"2026-10-13T19:02:00Z","selection_sha256":selection_hash,
        "settings_sha256":freeze["settings_sha256"],"independent_dev_verification_path":"verification/dev-receipt.json",
        "independent_dev_verification_sha256":seal.digest(stage/"verification/dev-receipt.json")}})
    put(stage/"execution-completion.json",{"phase2":"computed","phase3":"uncomputed","episodes":2,
        "settings_sha256":freeze["settings_sha256"],"selection_sha256":selection_hash,"finished_at":"2026-10-13T19:04:00Z"})
    tables={}
    for name in ("paired","account","account-capacity"):
        path="tables/"+name+".csv";put(stage/path,"year,count\nall,2\n");tables[name]={"sha256":seal.digest(stage/path),"rows":1}
    put(stage/"metrics.json",{"run_id":RUN,"tables":tables})
    put(stage/"account-settings.json",{"initial_capital":10000})
    put(stage/"account-ledger.jsonl.gz","synthetic actual-account rows")
    for name in ("report.md","report.html","advice.md"):put(stage/name,"synthetic saved report")
    put(stage/"exclusions.json",{"known_exclusions":True})
    put(stage/"commands.json",[{"argv":["./scripts/uv","run","--locked","--no-sync","python","synthetic.py"],"cwd":str(root)}])
    source_snapshots=[]
    for role,name in (("verifier","checker.py"),("exporter","publisher.py"),("sealer","phase2_seal.py")):
        path="source-lifecycle/"+name
        put(stage/path,FILE.read_text() if role=="sealer" else "# synthetic "+role+" bytes")
        source_snapshots.append({**seal.identity(stage,path),"role":role})
    numerical_counts={"discovered":1,"tests_run":1,"failures":0,"errors":0,"skipped":0,"expected_failures":0,"unexpected_successes":0}
    put(stage/"numerical-result.json",{"outcome":"passed","counts":numerical_counts,"successful_callbacks":1,"skips":[]})
    publications=[];publication_receipts=[];report_paths=[]
    for n in range(23):
        pubid=f"gc-phase2-synthetic-{n:02d}";prefix="publications/"+pubid
        directory=stage/prefix
        put(directory/"references/config.json",(stage/"config.json").read_text())
        put(directory/"publication.json",{"id":pubid,"source":{"runId":RUN},"sections":[],"downloads":[]})
        put(directory/"source-map.json",{"run_id":RUN,"publication_id":pubid,"source_row_base":0,"source_artifacts":[{
            "path":"references/config.json","sha256":seal.digest(stage/"config.json"),"original_stage_source_path":"config.json","original_source_sha256":seal.digest(stage/"config.json")}],"figures":[]})
        put(directory/"publication-verification.json",{"status":"passed","publication_sha256":seal.digest(directory/"publication.json"),"source_map_sha256":seal.digest(directory/"source-map.json")})
        future=f"runs/{seal.STUDY}/{RUN}/publications/{pubid}/"
        put(directory/"publication-manifest.json",{"publication_id":pubid,"source_run_id":RUN,"study_id":seal.STUDY,
            "source_artifacts":[{"path":future+"references/config.json","sha256":seal.digest(directory/"references/config.json")}],
            "outputs":[{"path":future+name,"sha256":seal.digest(directory/name)} for name in ("publication.json","source-map.json","publication-verification.json")]})
        files=[seal.identity(directory,str(p.relative_to(directory))) for p in sorted(directory.rglob("*")) if p.is_file()]
        publications.append({"path":prefix,"files":files})
        report_paths.append(prefix+"/publication.json")
        publication_receipts.append({"publication_id":pubid,"status":"passed","publication_sha256":seal.digest(directory/"publication.json"),
            "source_map_sha256":seal.digest(directory/"source-map.json"),"publication_manifest_sha256":seal.digest(directory/"publication-manifest.json")})
    requirements={"science":["config.json","protocol.md","inputs.lock.json","phase2-baseline-pin.json","execution-freeze.json","selection.json","selection-freeze.json",*phase_artifacts],
        "metrics":["metrics.json",*("tables/"+name+".csv" for name in tables)],
        "account":["account-settings.json","account-ledger.jsonl.gz","tables/account.csv","tables/account-capacity.csv"],
        "publication_transfer":report_paths,"publication_contract":report_paths,"numerical":["numerical-result.json"]}
    receipt_pins={};checks=[]
    for gate,paths in requirements.items():
        receipt={"status":"passed","artifacts":[seal.identity(stage,path) for path in paths],"source_snapshots":[source_snapshots[0]]}
        if gate=="publication_transfer":receipt["publications"]=publication_receipts
        if gate=="numerical":
            live=root/"studies"/seal.STUDY/"tests/test_synthetic_numeric.py";put(live,"# synthetic numeric fixture")
            copy="numeric-source/test_synthetic_numeric.py";put(stage/copy,live.read_text())
            receipt["source_snapshots"]=[{**seal.identity(stage,copy),"original_workspace_path":str(live.relative_to(root))}]
            receipt.update(schema_version="study23.phase2-numerical-record/v1",counts=numerical_counts,skips=[],child_result=seal.identity(stage,"numerical-result.json"),
            successful_callbacks=1,environment_lock_sha256=freeze["environment_lock_sha256"],execution_freeze_sha256=seal.digest(stage/"execution-freeze.json"),
            command=["./scripts/uv","run","--locked","--no-sync","python","-m","unittest"])
        path="verification/"+gate+".json";put(stage/path,receipt);receipt_pins[gate]=seal.identity(stage,path)
        checks.append({"name":gate,"status":"passed","record":path})
    put(stage/"checks.json",checks)
    private="phases/dev-validation/policies.jsonl.gz"
    retained=root/"data/research/sahadeva"/seal.STUDY/RUN/private
    put(retained,(stage/private).read_text())
    external={"id":"phase2-private-ledger","locator":str(retained.relative_to(root)),"bytes":retained.stat().st_size,
              "sha256":seal.digest(retained),"source_stage_path":private}
    inputs={"schema_version":seal.SCHEMA,"run_id":RUN,"receipts":receipt_pins,"chronology":seal.identity(stage,"phase-starts.json"),
        "source_snapshots":source_snapshots,"publications":publications,"external_artifacts":[external],"private_staged_files":[private],
        "results_artifacts":["metrics.json","tables/paired.csv","tables/account.csv"]}
    put(stage/"sealing-inputs.json",inputs)
    return stage,retained,old


class Phase2SealTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir="/private/tmp")
        self.root=Path(self.temp.name)
        self.stage,self.retained,self.baseline=fixture(self.root)

    def tearDown(self):self.temp.cleanup()

    def inputs(self):return seal.read_json(self.stage/"sealing-inputs.json")

    def change_receipt(self,gate,mutate):
        inputs=self.inputs();path=inputs["receipts"][gate]["path"]
        record=seal.read_json(self.stage/path);mutate(record);put(self.stage/path,record)
        inputs["receipts"][gate]=seal.identity(self.stage,path);put(self.stage/"sealing-inputs.json",inputs)

    def change_publication_manifest(self,mutate):
        inputs=self.inputs();entry=inputs["publications"][0];directory=self.stage/entry["path"]
        manifest=seal.read_json(directory/"publication-manifest.json");mutate(manifest);put(directory/"publication-manifest.json",manifest)
        entry["files"]=[seal.identity(directory,item["path"]) if item["path"]=="publication-manifest.json" else item for item in entry["files"]]
        receipt_path=inputs["receipts"]["publication_transfer"]["path"];receipt=seal.read_json(self.stage/receipt_path)
        receipt["publications"][0]["publication_manifest_sha256"]=seal.digest(directory/"publication-manifest.json")
        put(self.stage/receipt_path,receipt);inputs["receipts"]["publication_transfer"]=seal.identity(self.stage,receipt_path)
        put(self.stage/"sealing-inputs.json",inputs)

    def rejected(self):
        before={str(p.relative_to(self.root)):seal.digest(p) for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}
        with self.assertRaises((ValueError,FileExistsError,KeyError)):seal.preflight(self.stage,self.root)
        after={str(p.relative_to(self.root)):seal.digest(p) for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}
        self.assertEqual(before,after)
        self.assertFalse((self.stage/"sealed-bundle").exists())

    def test_preflight_is_read_only_and_identity_derived(self):
        target=seal.preflight(self.stage,self.root)
        self.assertEqual(target,self.root/"runs"/seal.STUDY/RUN)
        self.assertFalse(target.exists())

    def test_actual_seal_contract_and_private_alias_preserve_baseline(self):
        before={p.name:seal.digest(p) for p in self.baseline.iterdir()}
        result=seal.seal(self.stage,self.root)
        target=Path(result["run"])
        manifest=seal.read_json(target/"manifest.json")
        self.assertEqual(manifest["contract"],"abacus.evidence/v1")
        self.assertEqual(result["selected_publications"],23)
        self.assertFalse((target/"phases/dev-validation/policies.jsonl.gz").exists())
        self.assertEqual(seal.digest(target/"events/phases/dev-validation/policies.jsonl.gz"),seal.digest(self.retained))
        self.assertEqual(seal.digest(target/"phases/dev-validation/completion.json"),seal.digest(self.stage/"phases/dev-validation/completion.json"))
        self.assertEqual(before,{p.name:seal.digest(p) for p in self.baseline.iterdir()})
        with self.assertRaises(FileExistsError):seal.preflight(self.stage,self.root)

    def test_existing_completed_run_never_overwritten(self):
        put(self.root/"runs"/seal.STUDY/RUN/"kept","old completed evidence")
        self.rejected()

    def test_nesting_run_stage_is_refused(self):
        nested=self.stage/"nested";nested.mkdir()
        with self.assertRaises(ValueError):seal.preflight(nested,self.root)

    def test_symlinked_ancestor_refused_before_resolution(self):
        link=self.root/"linked-work";link.symlink_to(self.root/"work",target_is_directory=True)
        with self.assertRaises(ValueError):seal.preflight(link/seal.STUDY/RUN,self.root)

    def test_nested_symlink_evidence_refused(self):
        (self.stage/"hidden-link").symlink_to(self.stage/"config.json")
        self.rejected()

    def test_duplicate_json_and_nonfinite_numeric_metadata_refused(self):
        for raw in ('{"run_id":"first","run_id":"second"}','{"value":NaN}','{"value":1e999}'):
            put(self.stage/"sealing-inputs.json",raw);self.rejected()

    def test_all_frozen_bytes_and_live_runtime_drift_refused(self):
        paths=[self.stage/name for name in ("config.json","protocol.md","inputs.lock.json","phase2-baseline-pin.json","environment.lock")]
        paths.append(self.root/"studies"/seal.STUDY/"phase2_accounts.py")
        paths.append(self.stage/"source/studies"/seal.STUDY/"phase2_run.py")
        for path in paths:
            before=path.read_bytes();path.write_bytes(before+b"changed");self.rejected();path.write_bytes(before)

    def test_reused_baseline_and_new_retained_private_drift_refused(self):
        for path in (self.retained,self.baseline/"manifest.json"):
            before=path.read_bytes();path.write_bytes(before+b"changed");self.rejected();path.write_bytes(before)

    def test_boolean_byte_count_refused(self):
        inputs=self.inputs();inputs["external_artifacts"][0]["bytes"]=True
        put(self.stage/"sealing-inputs.json",inputs);self.rejected()

    def test_failed_receipt_and_missing_scientific_artifact_binding_refused(self):
        self.change_receipt("science",lambda record:record.update(status="failed"));self.rejected()

    def test_science_requires_all_phase_and_frozen_artifacts(self):
        self.change_receipt("science",lambda record:record["artifacts"].pop());self.rejected()

    def test_metrics_and_accounts_require_exact_saved_output_pins(self):
        self.change_receipt("account",lambda record:record.update(artifacts=[]));self.rejected()

    def test_recorded_check_cannot_omit_required_passed_gate(self):
        checks=seal.read_json(self.stage/"checks.json");put(self.stage/"checks.json",checks[:-1]);self.rejected()

    def test_extra_requested_measurement_receipt_is_checked_not_ignored(self):
        inputs=self.inputs();receipt=seal.read_json(self.stage/inputs["receipts"]["metrics"]["path"])
        receipt["status"]="failed";path="verification/extra-measurement.json";put(self.stage/path,receipt)
        inputs["receipts"]["requested_measurement"]=seal.identity(self.stage,path)
        checks=seal.read_json(self.stage/"checks.json");checks.append({"name":"requested-measurement","status":"passed","record":path})
        put(self.stage/"checks.json",checks);put(self.stage/"sealing-inputs.json",inputs)
        self.rejected()

    def test_numeric_empty_failed_all_skipped_and_nonlocked_refused(self):
        self.change_receipt("numerical",lambda record:record["counts"].update(discovered=0,tests_run=0));self.rejected()

    def test_numeric_counts_are_actual_integers_and_not_booleans(self):
        self.change_receipt("numerical",lambda record:record["counts"].update(tests_run=True));self.rejected()

    def test_numeric_wrong_environment_or_freeze_refused(self):
        self.change_receipt("numerical",lambda record:record.update(environment_lock_sha256="a"*64));self.rejected()

    def test_numeric_command_requires_locked_no_sync(self):
        self.change_receipt("numerical",lambda record:record.update(command=["python","-m","unittest"]));self.rejected()

    def test_selection_byte_changes_refused(self):
        selection=seal.read_json(self.stage/"selection.json");selection["selected_policy"]="retuned"
        put(self.stage/"selection.json",selection);self.rejected()

    def test_later_start_must_follow_selection_and_independent_dev_pass(self):
        inputs=self.inputs();starts=seal.read_json(self.stage/"phase-starts.json")
        starts["later"]["started_at"]="2026-10-13T19:00:00Z";put(self.stage/"phase-starts.json",starts)
        inputs["chronology"]=seal.identity(self.stage,"phase-starts.json");put(self.stage/"sealing-inputs.json",inputs);self.rejected()

    def test_executed_ledger_byte_drift_and_partial_phase_set_refused(self):
        path=self.stage/"phases/later/occurrence.jsonl.gz";path.write_bytes(path.read_bytes()+b"changed");self.rejected()

    def test_exactly_23_report_bundles_required(self):
        inputs=self.inputs();inputs["publications"].pop();put(self.stage/"sealing-inputs.json",inputs);self.rejected()

    def test_independent_publication_receipt_must_cover_every_report(self):
        self.change_receipt("publication_transfer",lambda record:record["publications"].pop());self.rejected()

    def test_publication_contract_receipt_cannot_cover_only_one_report(self):
        self.change_receipt("publication_contract",lambda record:record.update(artifacts=record["artifacts"][:1]));self.rejected()

    def test_selected_publication_byte_drift_and_extra_bytes_refused(self):
        path=self.stage/"publications/gc-phase2-synthetic-00/references/config.json"
        path.write_bytes(path.read_bytes()+b"changed");self.rejected()

    def test_publication_manifest_future_run_and_publication_paths_required(self):
        self.change_publication_manifest(lambda m:m["source_artifacts"][0].update(path=f"runs/{seal.STUDY}/{RUN}/config.json"))
        self.rejected()

    def test_publication_manifest_identity_and_required_verification_pin(self):
        self.change_publication_manifest(lambda m:m.update(study_id="another-study"));self.rejected()

    def test_publication_manifest_cannot_omit_required_output(self):
        self.change_publication_manifest(lambda m:m["outputs"].pop());self.rejected()

    def test_publication_manifest_duplicate_source_pins_refused(self):
        self.change_publication_manifest(lambda m:m["source_artifacts"].append(dict(m["source_artifacts"][0])));self.rejected()

    def test_publication_manifest_copied_source_output_overlap_is_valid(self):
        self.change_publication_manifest(lambda m:m["outputs"].append(dict(m["source_artifacts"][0])))
        self.assertEqual(seal.preflight(self.stage,self.root).name,RUN)

    def test_actual_sealer_source_snapshot_required(self):
        inputs=self.inputs();sources=inputs["source_snapshots"]
        sources[-1]["role"]="exporter";put(self.stage/"sealing-inputs.json",inputs);self.rejected()

    def test_private_alias_requires_exact_external_pin(self):
        inputs=self.inputs();inputs["external_artifacts"][0].pop("source_stage_path")
        put(self.stage/"sealing-inputs.json",inputs);self.rejected()

    def test_other_run_external_namespace_refused(self):
        inputs=self.inputs();external=inputs["external_artifacts"][0]
        old=self.root/"data/research/sahadeva"/seal.STUDY/"another-run"/"private.gz"
        put(old,self.retained.read_text());external["locator"]=str(old.relative_to(self.root))
        put(self.stage/"sealing-inputs.json",inputs);self.rejected()


if __name__=="__main__":unittest.main()
