#!/usr/bin/env python3
"""Read-only integrity audit for the explicitly declared incomplete Phase 3 stage.

Does not run detectors, access targets, discover source tables, compile Pine,
reveal answers, or establish numerical/scientific validity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
README = "studies/29_verniman_level_reconstruction/README.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(stage: Path) -> dict:
    stage = stage.resolve()
    declared = json.loads((PHASE / "input-declaration.json").read_text())
    if stage != (ROOT / declared["stage"]).resolve():
        raise ValueError("only the explicit declared Phase 3 stage is accepted")
    freeze = json.loads((stage / "protocol-freeze.json").read_text())
    exceptions = json.loads((stage / "navigation-exceptions.json").read_text())
    if {x["path"] for x in exceptions} != {README}:
        raise ValueError("only the additive study README navigation exception is allowed")
    exceptions = {x["path"]: x for x in exceptions}
    errors = []
    for pin in freeze["frozen_files"]:
        if digest(ROOT / pin["path"]) != pin["sha256"]:
            errors.append("frozen file changed: " + pin["path"])
    for pin in freeze["source_pins"]:
        actual = digest(ROOT / pin["path"])
        if pin["path"] in exceptions:
            exception = exceptions[pin["path"]]
            if pin["sha256"] != exception["before_sha256"] or actual != exception["after_sha256"]:
                errors.append("navigation exception hash mismatch: " + pin["path"])
        elif actual != pin["sha256"]:
            errors.append("preserved source changed: " + pin["path"])
    earlier = json.loads((stage / "preexisting-study-artifacts.json").read_text())
    for pin in earlier:
        expected = exceptions[pin["path"]]["after_sha256"] if pin["path"] in exceptions else pin["sha256"]
        if digest(ROOT / pin["path"]) != expected:
            errors.append("preexisting study file changed: " + pin["path"])
    manifest = json.loads((stage / "implementation-manifest.json").read_text())
    for pin in manifest["files"]:
        if digest(ROOT / pin["path"]) != pin["sha256"]:
            errors.append("implementation changed after retention: " + pin["path"])
        if digest(stage / pin["snapshot_path"]) != pin["sha256"]:
            errors.append("retained implementation differs: " + pin["path"])
    settings = json.loads((PHASE / "settings.json").read_text())
    training = json.loads((PHASE / "training-results.json").read_text())
    if [x["session_date"] for x in training["records"]] != settings["training_dates"]:
        errors.append("training dates differ from frozen control")
    if training["new_training_answers_opened"] or training["seven_map_reveal_gate_passed"]:
        errors.append("incomplete first pass must keep reveal gate closed")
    if training["native_phase3_compilation"] != "not_attempted_security_blocked":
        errors.append("native status does not reflect the access blocker")
    for record in training["records"]:
        if record["status"] != "unavailable" or not record["failure_reasons"]:
            errors.append("per-date failure record missing: " + record["session_date"])
        if record["phase3_candidate_counts"] is not None or record["phase3_cap_omissions"] is not None:
            errors.append("unknown candidate counts must remain null: " + record["session_date"])
        if record["comparison_status"] != "not_executed":
            errors.append("unavailable expanded map cannot have an executed comparison")
        if any(x["readiness"] != "unavailable" for x in record["profiles"]):
            errors.append("profile readiness fabricated in failure record")
    if digest(PHASE / "training-results.json") != digest(stage / "training-results.json"):
        errors.append("tracked and retained training status differ")
    return {"status": "fail" if errors else "pass", "errors": errors,
            "frozen_files": len(freeze["frozen_files"]), "preserved_source_pins": len(freeze["source_pins"]),
            "preexisting_study_files": len(earlier), "implementation_files": len(manifest["files"]),
            "training_failure_records": len(training["records"]),
            "native_verification": "unexecuted", "new_answer_access": False,
            "scope": "Integrity/status consistency only; not Pine execution or research revalidation."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path)
    args = parser.parse_args()
    declared = json.loads((PHASE / "input-declaration.json").read_text())
    result = audit(args.stage or ROOT / declared["stage"])
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
