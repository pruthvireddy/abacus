"""Record the actual stage-bound Study23 numerical suite and success callbacks."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.callbacks=0
    def addSuccess(self,test):self.callbacks+=1;super().addSuccess(test)
    def addSubTest(self,test,subtest,err):
        if err is None:self.callbacks+=1
        super().addSubTest(test,subtest,err)


def record(stage):
    stage=Path(stage)
    freeze=stage/"execution-freeze.json"
    if not freeze.is_file():raise ValueError("frozen executed source required")
    target=stage/"verification"/"numerical-tests.json"
    if target.exists():raise FileExistsError("preserve recorded suite")
    stream=io.StringIO();loader=unittest.TestLoader()
    suite=loader.discover(str(HERE/"tests"),pattern="test_*.py")
    discovered=suite.countTestCases()
    started=datetime.now(timezone.utc).isoformat()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    target.parent.mkdir(parents=True,exist_ok=True)
    log=target.with_suffix(".log");log.write_text(stream.getvalue())
    snapshots=[]
    for path in [Path(__file__),*sorted((HERE/"tests").glob("test_*.py"))]:
        rel=path.relative_to(HERE);copy=stage/"source-numerical-tests"/rel;copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(path.read_bytes());snapshots.append({"path":str(copy.relative_to(stage)),"sha256":sha(copy),"bytes":copy.stat().st_size})
    record={"schema_version":"study23.phase3-numerical-record/v1","status":"passed" if result.wasSuccessful() and not result.skipped else "failed","run_id":stage.name,"started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"execution_freeze_sha256":sha(freeze),"environment_lock_sha256":sha(stage/"uv.lock"),"counts":{"discovered":discovered,"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},"successful_callbacks":result.callbacks,"source_snapshots":snapshots,"log":{"path":str(log.relative_to(stage)),"sha256":sha(log)},"argv":sys.argv,"cwd":str(Path.cwd()),"python":sys.version,"packages":{p:importlib.metadata.version(p) for p in ("numpy","pandas","pyarrow")},"scope":"Actual focused owning-study suite, independent of science reconciliation and artifact integrity."}
    target.write_text(json.dumps(record,indent=2)+"\n")
    return record


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--stage",type=Path,required=True);a=p.parse_args();r=record(a.stage);print(json.dumps(r,indent=2));sys.exit(0 if r["status"]=="passed" else 1)
