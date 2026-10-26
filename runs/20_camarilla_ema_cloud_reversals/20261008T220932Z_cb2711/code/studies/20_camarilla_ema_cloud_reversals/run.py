#!/usr/bin/env python3
"""Stage/freeze, audit, score, summarize, verify and seal Study 20."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.spec import STUDY, SETTINGS
from src.storage import sha, save_json, utc_now, guard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def freeze(work):
    if work.exists():
        raise RuntimeError("Freeze requires a new empty staging directory")
    work.mkdir(parents=True)
    for source, name in ((HERE / "plan.md", "protocol-draft.md"), (HERE / "study.yaml", "settings-draft.yaml"), (HERE / "report-proposal.md", "report-proposal.md"), (ROOT / "uv.lock", "uv.lock")):
        shutil.copy2(source, work / name)
    shutil.copy2(HERE / "executed-protocol.md", work / "protocol.md")
    save_json(work / "config.json", SETTINGS)
    save_json(work / "freeze.json", {"run_id": work.name, "study_id": STUDY, "frozen_at": utc_now(), "before_strategy_outcomes": True, "user_authorization": "2026-10-08 implementation, historical backtest, reports and local publication preview supersede planning-only scope; hosted deployment excluded", "settings_sha256": sha(work/"config.json"), "protocol_sha256": sha(work/"protocol.md"), "draft_sha256": sha(work/"protocol-draft.md")})
    print(work)

def audit(work, reuse=None):
    from src.inputs import verify_inputs, prepare_product
    root, manifest = verify_inputs(work, ROOT)
    if reuse:
        if not (reuse/"input-audit-complete.json").exists():raise RuntimeError("Reusable input audit is incomplete")
        old=json.loads((reuse/"inputs.lock.json").read_text())
        new=json.loads((work/"inputs.lock.json").read_text())
        if old["files"]!=new["files"]:raise RuntimeError("Reusable audit has different input identities")
        copies=[]
        for product in SETTINGS["products"]:
            for rel in (f"private/bars_{product}.parquet",f"private/minutes_{product}.parquet",f"tables/coverage_{product}.csv",f"audit_{product}.json"):
                target=work/rel;target.parent.mkdir(exist_ok=True)
                shutil.copy2(reuse/rel,target)
                assert sha(target)==sha(reuse/rel)
                copies.append({"path":rel,"sha256":sha(target)})
        save_json(work/"input-audit-complete.json",{"completed_at":utc_now(),"scoring_not_performed":True,"reused_input_audit":str(reuse),"reverified_market_hashes":True,"reused_outputs":copies,"qualification":"Reuses only unchanged input aggregation, features and coverage; never events/outcomes/trades"})
        print("Input hashes reverified; unchanged aggregation/features/coverage reused, no outcomes reused")
        return
    for product in SETTINGS["products"]:
        prepare_product(work, root, product, manifest)
    save_json(work / "input-audit-complete.json", {"completed_at": utc_now(), "scoring_not_performed": True})

def snapshot(work):
    destination = work / "code"
    if destination.exists():
        raise RuntimeError("Code already snapshotted; scoring may not overwrite")
    files = []
    for base in [HERE, ROOT/"packages/bhishma/src", ROOT/"packages/sahadeva/src"]:
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".md", ".json", ".yaml", ".toml", ".pine"):
                files.append(p)
    for p in [ROOT/"uv.lock", ROOT/"pyproject.toml", ROOT/"scripts/uv", ROOT/".python-version"]:
        files.append(p)
    descriptors = []
    for p in files:
        rel = p.relative_to(ROOT)
        d = destination/rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p,d)
        descriptors.append({"path": str(rel), "sha256": sha(d)})
    save_json(work / "code-identity.json", {"git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"],cwd=ROOT,text=True).strip(), "git_status": subprocess.check_output(["git", "status", "--porcelain"],cwd=ROOT,text=True), "snapshot_files": descriptors})
    save_json(work / "environment.json", {"python": sys.version, "executable": sys.executable, "packages": {p.metadata["Name"]:p.version for p in importlib.metadata.distributions()}, "uv_lock_sha256": sha(ROOT/"uv.lock")})

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("freeze", "audit", "score", "summarize", "report", "verify", "seal"))
    p.add_argument("--work", type=Path)
    p.add_argument("--reuse-audit", type=Path, help="Reuse only identical input-audited bars/features/coverage after rehashing inputs")
    args=p.parse_args()
    work = args.work or ROOT/"work"/STUDY/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:6])
    if args.action == "freeze":
        freeze(work)
        return
    guard(work)
    if sha(work/"config.json") != json.loads((work/"freeze.json").read_text())["settings_sha256"] or SETTINGS != json.loads((work/"config.json").read_text()):
        # JSON arrays turn tuple defaults into lists, so canonicalize both sides.
        from src.storage import clean
        if clean(SETTINGS) != json.loads((work/"config.json").read_text()):
            raise RuntimeError("Frozen settings differ from executable specification")
    if args.action == "audit":
        audit(work,args.reuse_audit)
    elif args.action == "score":
        if not (work/"input-audit-complete.json").exists():
            raise RuntimeError("Input audit prerequisite absent")
        log = subprocess.run([sys.executable,"-m","unittest","discover","-s",str(HERE/"tests"),"-v"],capture_output=True,text=True)
        (work/"numerical-tests-before-scoring.log").write_text(log.stdout+log.stderr)
        if log.returncode:
            raise RuntimeError("Pre-scoring tests failed")
        snapshot(work)
        from src.execution import execute
        execute(work)
    elif args.action == "summarize":
        from src.statistics import summarize
        summarize(work)
    elif args.action == "report":
        from src.reporting import render
        render(work)
    elif args.action == "verify":
        from src.delivery import verify
        verify(work)
    elif args.action == "seal":
        from src.delivery import seal
        seal(work, ROOT)

if __name__ == "__main__":
    main()
