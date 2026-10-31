"""Frozen, repository-only execution and immutable evidence lifecycle."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]
STUDY_ID = STUDY.name


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False, default=str)
        stream.write("\n")


def load(path):
    return json.loads(Path(path).read_text())


def _paths():
    owned = sorted(path for path in STUDY.rglob("*") if path.is_file() and path.suffix in (".py", ".mjs", ".yaml", ".json", ".md") and "__pycache__" not in path.parts)
    shared = [ROOT / "uv.lock", ROOT / "apps/narada/package-lock.json", ROOT / "requests/inbox/es_contract_session_indicators__1.0.0.yaml"]
    shared += [ROOT / "packages/bhishma/src/abacus_bhishma" / name for name in
               ("es_contract_session_indicators.py", "ema_cloud.py", "ema_cloud_loader_v2.py", "calendar.py",
                "paths.py", "manifest_selection.py", "provenance.py", "publication_safety.py", "verniman_consolidated.py")]
    return sorted(set(owned + shared))


def _state():
    return {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty": subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True)}


def assert_frozen(stage):
    stage = Path(stage)
    freeze = load(stage / "freeze.json")
    for record in freeze["sources"]:
        if digest(ROOT / record["path"]) != record["sha256"] or digest(stage / record["retained_path"]) != record["sha256"]:
            raise ValueError("frozen execution source/settings bytes changed")
    tests = load(stage / "numerical-tests.json")
    if tests["status"] != "passed" or tests["tests"] < 1 or digest(stage / "numerical-tests.log") != tests["log_sha256"]:
        raise ValueError("missing or invalid source-bound numerical tests")
    return freeze


def prepare_features(release_id):
    from abacus_bhishma.es_contract_session_indicators import build_release
    from abacus_bhishma.paths import resolve_publication_root
    lock = load(STUDY / "inputs.lock.json")
    cloud, minutes = (lock["inputs"][key] for key in ("retained_cloud_reference", "retained_continuous_minutes"))
    root = resolve_publication_root(workspace=ROOT)
    return build_release(root, release_id=release_id,
                         cloud_manifest_path=cloud["path"], cloud_manifest_sha256=cloud["sha256"],
                         minute_manifest_path=minutes["path"], minute_manifest_sha256=minutes["sha256"],
                         start_session="2020-01-01", end_session_exclusive="2026-10-31")


def freeze_run(run_id):
    from abacus_bhishma.paths import resolve_publication_root
    from abacus_bhishma.verniman_consolidated import load_release
    from source_selection import select_sources
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", run_id):
        raise ValueError("unsafe run ID")
    stage = ROOT / "work" / STUDY_ID / run_id
    if not stage.resolve().is_relative_to(ROOT / "work"):
        raise ValueError("run escapes workspace staging")
    stage.mkdir(parents=True, exist_ok=False)
    lock = load(STUDY / "inputs.lock.json")
    feature = lock["inputs"].get("session_indicators")
    if feature is None:
        raise ValueError("pin the new retained-data indicator release before freezing outcomes")
    root = resolve_publication_root(workspace=ROOT)
    for pin in lock["inputs"].values():
        if digest(root / pin["path"]) != pin["sha256"]:
            raise ValueError("pinned input manifest changed")
    input_check = lock.get("pre_execution_feature_audit")
    if input_check is None or digest(ROOT / input_check["path"]) != input_check["sha256"] or load(ROOT / input_check["path"]).get("status") != "passed":
        raise ValueError("independent pre-execution feature audit is required")
    retained_input_check = stage / "input-checks" / "feature-audit"
    retained_input_check.parent.mkdir()
    shutil.copytree((ROOT / input_check["path"]).parent, retained_input_check)
    records = []
    for path in _paths():
        relative = path.relative_to(ROOT)
        retained = stage / "provenance" / relative
        retained.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, retained)
        records.append({"path": str(relative), "retained_path": str(retained.relative_to(stage)), "sha256": digest(path)})
    pin = lock["inputs"]["verniman_daily_levels"]
    tables = {name: load_release(root, pin["path"], pin["sha256"], table=name).to_pylist()
              for name in ("outlooks", "levels", "issues", "coverage", "observations", "observation_levels")}
    selection = select_sources(tables)
    dump(stage / "source-selection.json", selection)
    command = [str(ROOT / "scripts/uv"), "run", "--locked", "--no-sync", "python", "-m", "unittest", "discover",
               "-s", str(STUDY / "tests"), "-v"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (stage / "numerical-tests.log").write_text(log)
    count = re.search(r"Ran (\d+) tests? in", log)
    passed = result.returncode == 0 and count is not None and int(count[1]) > 0 and "skipped=" not in log and "expected failures=" not in log
    dump(stage / "numerical-tests.json", {"status": "passed" if passed else "failed", "tests": int(count[1]) if count else 0,
                                         "argv": command, "cwd": str(ROOT), "exit_code": result.returncode,
                                         "log_sha256": digest(stage / "numerical-tests.log")})
    if not passed:
        raise ValueError("numerical tests failed; diagnostic stage retained")
    dump(stage / "freeze.json", {"schema_version": "abacus.study30.execution-freeze/v1", "study_id": STUDY_ID,
                                "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(),
                                "sources": records, "inputs": lock["inputs"], "publication_root": str(root),
                                "source_selection_sha256": digest(stage / "source-selection.json"),
                                "pre_execution_feature_audit": {**input_check, "retained_path": "input-checks/feature-audit/receipt.json"},
                                "command": sys.argv, "cwd": str(Path.cwd()),
                                "git": _state(), "python": sys.version, "environment_lock_sha256": digest(ROOT / "uv.lock"),
                                "qualification": "Declared executable/source scope retained; not complete transitive dependency discovery.",
                                "data_policy": "repository_only", "external_requests_submitted": False})
    assert_frozen(stage)
    return stage


def execute(stage):
    import pandas as pd
    from abacus_bhishma.es_contract_session_indicators import load_release
    from engine import analyze_day, IneligibleDay
    stage = Path(stage)
    freeze = assert_frozen(stage)
    if (stage / "execution.json").exists() or (stage / "ledgers.json.gz").exists():
        raise FileExistsError("execution evidence already exists")
    if digest(stage / "source-selection.json") != freeze["source_selection_sha256"]:
        raise ValueError("frozen source selection changed")
    pin, root = freeze["inputs"]["session_indicators"], Path(freeze["publication_root"])
    frames = {name: load_release(root, pin["path"], pin["sha256"], table=name) for name in ("bars1", "bars3", "bars5", "quality")}
    grouped = {name: {str(day): frame for day, frame in frames[name].groupby("session_date", sort=False)} for name in ("bars1", "bars3", "bars5")}
    quality = {str(row["session_date"]): row for row in frames["quality"].to_dict("records")}
    selection = load(stage / "source-selection.json")
    ledgers = {key: [] for key in ("daily", "sections", "snapshots", "price_events", "ema_events", "outcomes", "coverage")}
    decisions = {row["candidate_id"]: row for row in selection["decisions"]}
    candidates = {row["outlook_id"]: row for row in selection["candidates"]}
    # Last observed same-contract regular close; its exact source date is saved.
    prior_closes = {}
    for day, minutes in sorted(grouped["bars1"].items()):
        stamp = pd.Timestamp(day, tz="America/New_York") + pd.Timedelta(hours=15, minutes=59)
        row = minutes[minutes.open_time.eq(stamp.tz_convert("UTC"))]
        if len(row) == 1 and bool(row.iloc[0].usable):
            prior_closes[day] = (str(row.iloc[0].contract), float(row.iloc[0].close))
    for identity, decision in sorted(decisions.items(), key=lambda item: (item[1]["session_date"], item[0])):
        day = decision["session_date"]
        coverage = {"candidate_id": identity, "session_date": day, "contract": decision["contract"],
                    "source_eligible": decision["retrospective_source_eligible"], "data_eligible": False,
                    "reasons": list(decision["exclusion_reasons"]), "historical_availability": "unverified"}
        if identity not in candidates:
            ledgers["coverage"].append(coverage)
            continue
        candidate = candidates[identity]
        q = quality.get(day)
        if q is None:
            coverage["reasons"] = ["no_retained_market_session"]
        elif q["contract"] != candidate["contract"]:
            coverage["reasons"] = ["quoted_contract_differs_from_retained_delivery"]
        elif not (q["calendar_valid"] and q["rth_complete"] and q["anchor_to_rth_end_complete"]):
            coverage["reasons"] = ["incomplete_anchor_rth_or_uncertified_calendar"]
        else:
            # Select the expected previous supported session before checking
            # whether its close exists; never skip a missing close to use an
            # older apparently plausible value.
            prior = sorted(key for key, state in quality.items() if key < day and state.get("calendar_valid"))
            prior_day = prior[-1] if prior else None
            prior_close = None
            if prior_day in prior_closes and (date.fromisoformat(day) - date.fromisoformat(prior_day)).days <= 4 and prior_closes[prior_day][0] == candidate["contract"]:
                prior_close = prior_closes[prior_day][1]
            try:
                result = analyze_day(session_date=day, contract=candidate["contract"], pivot=candidate["pivot"],
                                     minutes=grouped["bars1"][day], bars3=grouped["bars3"][day], bars5=grouped["bars5"][day],
                                     source=candidate, prior_rth_close=prior_close)
            except IneligibleDay as exc:
                coverage["reasons"] = exc.codes
            else:
                for key, rows in result.items():
                    ledgers.setdefault(key, []).extend(rows)
                coverage["data_eligible"], coverage["reasons"] = True, []
                if result["daily"]:
                    result["daily"][0]["prior_rth_close_source_date"] = prior_day if prior_close is not None else None
        ledgers["coverage"].append(coverage)
    if not ledgers["daily"]:
        raise ValueError("no eligible sessions; keep coverage diagnostic and resolve inputs")
    with (stage / "ledgers.json.gz").open("xb") as target:
        with gzip.GzipFile(fileobj=target, mode="wb", mtime=0) as stream:
            stream.write(json.dumps(ledgers, sort_keys=True, allow_nan=False).encode())
    assert_frozen(stage)
    dump(stage / "execution.json", {"status": "completed", "run_id": freeze["run_id"], "created_at": datetime.now(timezone.utc).isoformat(),
                                   "command": sys.argv, "cwd": str(Path.cwd()),
                                   "ledger_sha256": digest(stage / "ledgers.json.gz"), "freeze_sha256": digest(stage / "freeze.json"),
                                   "rows": {key: len(rows) for key, rows in ledgers.items()},
                                   "eligible_start": min(row["session_date"] for row in ledgers["daily"]),
                                   "eligible_end": max(row["session_date"] for row in ledgers["daily"]),
                                   "coverage_reason_counts": dict(Counter(reason for row in ledgers["coverage"] for reason in row["reasons"]))})
    return load(stage / "execution.json")


def read_ledgers(stage):
    stage = Path(stage)
    record = load(stage / "execution.json")
    path = stage / "ledgers.json.gz"
    if not path.exists() and (stage / "events.manifest.json").exists():
        pin = load(stage / "events.manifest.json")["artifacts"][0]
        path = ROOT / pin["path"]
    if digest(path) != record["ledger_sha256"]:
        raise ValueError("saved ledger bytes changed")
    with gzip.open(path, "rt") as stream:
        return json.load(stream)


def render(stage):
    from reporting import write_statistics, render as figures
    stage = Path(stage)
    assert_frozen(stage)
    ledgers = read_ledgers(stage)
    result = write_statistics(stage, ledgers, bootstrap_replicates=2000)
    figures(stage)
    artifacts = [path for path in (stage / "tables").glob("*.csv")] + [stage / "metrics.json", stage / "report.md"]
    dump(stage / "rendering.json", {"status": "completed", "command": sys.argv, "cwd": str(Path.cwd()),
                                  "ledger_sha256": digest(stage / "ledgers.json.gz"),
                                  "artifacts": [{"path": str(path.relative_to(stage)), "sha256": digest(path)} for path in artifacts if path.exists()]})
    return {"stage": str(stage), "statistics": "saved", "tables": sorted(path.name for path in (stage / "tables").glob("*.csv"))}


def seal(stage):
    stage = Path(stage).resolve()
    freeze = assert_frozen(stage)
    receipt = load(stage / "scientific-verification.json")
    if receipt.get("status") != "passed":
        raise ValueError("scientific verification has not passed")
    if digest(stage / "ledgers.json.gz") != receipt["ledger_sha256"]:
        raise ValueError("scientifically verified ledger changed")
    if digest(stage / "freeze.json") != receipt["freeze_sha256"]:
        raise ValueError("scientifically verified freeze changed")
    for record in receipt["summary_tables"]:
        if digest(stage / record["path"]) != record["sha256"]:
            raise ValueError("scientifically verified summary table changed")
    sys.path.insert(0, str(STUDY))
    import publish_web
    publish_web.verify(stage, run_id=freeze["run_id"])
    publications = list((stage / "publications").glob("*/publication.json"))
    if len(publications) != 6:
        raise ValueError("six selected report sources must be prepared before sealing")
    for report in publications:
        receipt_path = report.parent / "publication-verification.json"
        if not receipt_path.exists():
            raise ValueError("publication source verification missing")
        check = load(receipt_path)
        if check.get("result") != "passed" or check.get("publication_sha256") != digest(report) or check.get("source_map_sha256") != digest(report.parent / "source-map.json"):
            raise ValueError("publication source verification invalid or stale")
    destination = ROOT / "runs" / STUDY_ID / freeze["run_id"]
    retained = ROOT / "data/research/sahadeva" / STUDY_ID / freeze["run_id"]
    if destination.exists() or retained.exists():
        raise FileExistsError("completed destination or retained evidence already exists")
    retained.mkdir(parents=True, exist_ok=False)
    ledger = stage / "ledgers.json.gz"
    bulk = retained / ledger.name
    shutil.move(str(ledger), bulk)
    dump(stage / "events.manifest.json", {"artifacts": [{"path": str(bulk.relative_to(ROOT)), "sha256": digest(bulk), "bytes": bulk.stat().st_size}],
                                          "qualification": "Retained local bulk evidence; no external backup is asserted."})
    artifacts = [{"path": str(path.relative_to(stage)), "sha256": digest(path), "bytes": path.stat().st_size}
                 for path in sorted(stage.rglob("*")) if path.is_file()]
    dump(stage / "manifest.json", {"study_id": STUDY_ID, "run_id": freeze["run_id"], "status": "completed",
                                   "protocol_version": "1.0.0", "artifacts": artifacts,
                                   "frozen_inputs": freeze["inputs"], "data_policy": "repository_only",
                                   "qualifications": ["Historical source availability unverified.", "Retrospective calendar/source/data eligibility.",
                                                      "Behavioral recurrence and excursions; no executable return or profitability claim."]})
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), destination)
    return destination
