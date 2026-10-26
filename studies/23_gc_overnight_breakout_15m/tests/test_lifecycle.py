"""Disposable preservation/receipt guards; never seal real study evidence."""
import importlib.util
import csv
import json
from pathlib import Path
import tempfile
import unittest


def module(name):
    spec=importlib.util.spec_from_file_location("study23_lifecycle_"+name,
        Path(__file__).resolve().parents[1]/(name+".py"))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


seal=module("seal")
report=module("save_report")


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value)if not isinstance(value,str)else value)


def synthetic(root):
    stage=root/"work"/seal.STUDY/"synthetic"
    retained=root/"data/research/sahadeva"/seal.STUDY/stage.name
    for name,text in {"config.json":"{}","inputs.lock.json":"{}","environment.lock":"locked",
        "source/engine.py":"# frozen execution bytes", "verification-source/checker.py":"# independent bytes",
        "proof.json":"{}","commands.json":"[]","exclusions.json":"[]","git-status.txt":"",
        "protocol.md":"frozen","tables/cohorts.csv":"year,count\nall,1\n","input-audit/minutes.parquet":"synthetic private bytes"}.items():put(stage/name,text)
    put(retained/"ledger.gz","synthetic ledger bytes")
    put(stage/"execution-completion.json",dict(phase2="uncomputed"))
    put(stage/"execution-freeze.json",dict(settings_sha256=seal.digest(stage/"config.json"),
        inputs_sha256=seal.digest(stage/"inputs.lock.json"),source_files=[dict(path="source/engine.py",sha256=seal.digest(stage/"source/engine.py"))]))
    put(stage/"scientific-verification.json",dict(status="passed",verification_environment=dict(environment_lock_sha256=seal.digest(stage/"environment.lock")),
        source_versions=[dict(path="verification-source/checker.py",sha256=seal.digest(stage/"verification-source/checker.py"),bytes=(stage/"verification-source/checker.py").stat().st_size)],
        records=[dict(path="proof.json",sha256=seal.digest(stage/"proof.json"),bytes=2)]))
    put(stage/"source-map.json",dict(run_id=stage.name,source_artifacts=[dict(path="tables/cohorts.csv",sha256=seal.digest(stage/"tables/cohorts.csv"))]))
    put(stage/"publication.json",dict(source=dict(runId=stage.name),sections=[],downloads=[]))
    put(stage/"publication-verification.json",dict(result="passed",artifact_hashes={path:seal.digest(stage/path)for path in ("publication.json","source-map.json","tables/cohorts.csv")}))
    put(stage/"checks.json",[dict(name=name,status="passed",record="proof.json")for name in
        ("study-numerical","independent-execution","publication-transfer","publication-contract")])
    put(stage/"events.manifest.json",[dict(id="ledger",locator=str((retained/"ledger.gz").relative_to(root)),bytes=(retained/"ledger.gz").stat().st_size,sha256=seal.digest(retained/"ledger.gz"))])
    put(stage/"input-audit/audit-artifacts.json",[dict(path="minutes.parquet",bytes=(stage/"input-audit/minutes.parquet").stat().st_size,sha256=seal.digest(stage/"input-audit/minutes.parquet"))])
    return stage,retained


class SealLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.stage,self.retained=synthetic(self.root)

    def tearDown(self):self.temp.cleanup()

    def rejected_read_only(self):
        before={str(p.relative_to(self.root)):seal.digest(p)for p in self.root.rglob("*")if p.is_file()and not p.is_symlink()}
        with self.assertRaises((ValueError,FileExistsError)):seal.preflight(self.stage,self.root)
        after={str(p.relative_to(self.root)):seal.digest(p)for p in self.root.rglob("*")if p.is_file()and not p.is_symlink()}
        self.assertEqual(before,after)
        self.assertFalse((self.stage/"sealed-bundle").exists())

    def test_passed_pins_preflight_is_read_only(self):
        target=seal.preflight(self.stage,self.root)
        self.assertEqual(target,self.root/"runs"/seal.STUDY/self.stage.name)
        self.assertFalse(target.exists())
        self.assertFalse((self.retained/"input-audit").exists())

    def test_existing_completed_run_never_overwritten(self):
        put(self.root/"runs"/seal.STUDY/self.stage.name/"kept.txt","old completed run")
        self.rejected_read_only()

    def test_failed_science_and_missing_required_check_refused(self):
        receipt=json.loads((self.stage/"scientific-verification.json").read_text());receipt["status"]="failed"
        put(self.stage/"scientific-verification.json",receipt);self.rejected_read_only()
        receipt["status"]="passed";put(self.stage/"scientific-verification.json",receipt)
        checks=json.loads((self.stage/"checks.json").read_text());put(self.stage/"checks.json",checks[:-1]);self.rejected_read_only()

    def test_frozen_code_settings_and_environment_drift_refused(self):
        for name in ("source/engine.py","config.json","inputs.lock.json","environment.lock"):
            old=(self.stage/name).read_bytes();(self.stage/name).write_bytes(old+b"changed")
            self.rejected_read_only();(self.stage/name).write_bytes(old)

    def test_retained_ledger_and_existing_audit_drift_refused(self):
        old=(self.retained/"ledger.gz").read_bytes();put(self.retained/"ledger.gz","changed")
        self.rejected_read_only();(self.retained/"ledger.gz").write_bytes(old)
        put(self.retained/"input-audit/minutes.parquet","wrong existing retained bytes")
        self.rejected_read_only()

    def test_nested_symlink_refused(self):
        file=self.stage/"source/hidden-link.py";file.symlink_to(self.stage/"source/engine.py")
        self.rejected_read_only()

    def test_duplicate_gate_json_and_phase2_execution_refused(self):
        put(self.stage/"scientific-verification.json",'{"status":"failed","status":"passed"}')
        self.rejected_read_only()
        self.stage,self.retained=synthetic(self.root)
        put(self.stage/"execution-completion.json",dict(phase2="computed"));self.rejected_read_only()

    def test_publication_artifact_and_verifier_source_drift_refused(self):
        for name in ("tables/cohorts.csv","verification-source/checker.py"):
            old=(self.stage/name).read_bytes();(self.stage/name).write_bytes(old+b"changed")
            self.rejected_read_only();(self.stage/name).write_bytes(old)


class SavedReportLifecycleTests(unittest.TestCase):
    def disposition_fixture(self,stage):
        path=stage/"tables";path.mkdir()
        columns=["broker_day","eligible","unknown_outcome","no_trade","completed_trades","censored_trades","accepted_breakouts","decision_available_at"]
        days=[dict(zip(columns,["2019-01-01","True","False","False",1,0,1,"2019-01-01T04:00:00+00:00"])),
            dict(zip(columns,["2018-01-01","False","False","False",0,0,0,"2018-01-01T04:00:00+00:00"]))]
        with (path/"days.csv").open("w",newline="")as f:
            writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(days)
        rows=[]
        for year in ["all",*(str(y)for y in range(2018,2027))]:
            n=int(year in ("all","2018"))
            rows.append(dict(year=year,eligible_days=n,completed_fill_days=n,censored_fill_days=0,
                known_no_trade_days=0,unobserved_first_fill_days=0,classification_total=n,excluded_calendar_days=int(year=="all")))
        with (path/"day-disposition.csv").open("w",newline="")as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        return columns,days,rows

    def test_completed_run_is_not_a_report_stage(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve()
            with self.assertRaises(ValueError):report.owned_stage(root/"runs"/seal.STUDY/"synthetic",root)
            self.assertEqual(report.owned_stage(root/"work"/seal.STUDY/"synthetic",root),root/"work"/seal.STUDY/"synthetic")

    def test_incomplete_or_duplicate_disposition_cohorts_refused(self):
        with tempfile.TemporaryDirectory()as temp:
            stage=Path(temp)
            put(stage/"tables/days.csv","broker_day,eligible,unknown_outcome,no_trade,completed_trades,censored_trades,accepted_breakouts,decision_available_at\n")
            put(stage/"tables/day-disposition.csv","year,eligible_days\n")
            with self.assertRaisesRegex(ValueError,"complete day-disposition"):report.verify_disposition(stage)
            put(stage/"tables/day-disposition.csv","year,eligible_days\nall,0\nall,0\n")
            with self.assertRaisesRegex(ValueError,"complete day-disposition"):report.verify_disposition(stage)

    def test_decision_new_york_year_and_supporting_excluded_edge(self):
        with tempfile.TemporaryDirectory()as temp:
            stage=Path(temp);_,_,rows=self.disposition_fixture(stage)
            receipt=report.verify_disposition(stage)
            self.assertEqual(receipt["rows"],10)
            self.assertEqual(receipt["supporting_edge_roster_days_outside_2018_2026"],1)
            rows[0]["excluded_calendar_days"]=2
            with (stage/"tables/day-disposition.csv").open("w",newline="")as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            with self.assertRaisesRegex(ValueError,"differs from saved day roster"):report.verify_disposition(stage)

    def test_completed_fill_and_no_trade_cannot_share_day(self):
        with tempfile.TemporaryDirectory()as temp:
            stage=Path(temp);columns,days,_=self.disposition_fixture(stage)
            days[0]["no_trade"]="True"
            with (stage/"tables/days.csv").open("w",newline="")as f:
                writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(days)
            with self.assertRaisesRegex(ValueError,"mutually exclusive"):report.verify_disposition(stage)


if __name__=="__main__":unittest.main()
