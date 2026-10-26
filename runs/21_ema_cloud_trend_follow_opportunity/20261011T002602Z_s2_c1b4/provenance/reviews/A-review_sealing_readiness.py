"""Read-only metadata readiness review, outside the staged research bundle."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(8 << 20), b""):
            h.update(data)
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=h.hexdigest())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    workspace = stage.parents[2]
    sys.path.insert(0, str(workspace / "scripts"))
    from evidence_contract import _recorded_checks, _recorded_commands

    checks_path = stage / "provenance/checks.json"
    checks_before = pin(checks_path)
    checks = json.loads(checks_path.read_text())
    inventory = {p.relative_to(stage).as_posix(): pin(p) for p in stage.rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts}
    require(all(set(r) <= {"name", "status", "record", "reason"} for r in checks), "strict check field contract")
    _recorded_checks(checks, inventory)
    _recorded_commands(json.loads((stage / "provenance/commands.json").read_text()))

    cli = workspace / "studies/21_ema_cloud_trend_follow_opportunity/run_stage2.py"
    tree = ast.parse(cli.read_text())
    seal = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "seal")
    required = next(ast.literal_eval(n.value) for n in ast.walk(seal)
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "required" for t in n.targets))
    passed = {r["name"] for r in checks if r["status"] == "passed"}
    pending = required - passed
    expected_pending = {"scientific-reconciliation", "external-ledger-bytes", "independent-uncertainty", "report-transfer"}
    require(pending <= expected_pending, "unexpected outstanding mandatory check")
    require("handoff" in cli.read_text() and "'stage3-handoff.json'" in ast.get_source_segment(cli.read_text(), seal),
            "handoff/seal contract")

    required_paths = ["config.json", "protocol.md", "inputs.lock.json", "baseline.lock.json",
        "metrics.json", "exclusions.json", "execution.json", "report.md", "report.html",
        "advice.md", "publication.json", "source-bindings.json", "events.manifest.json",
        "evidence.manifest.json", "acceptance.manifest.json", "slow-evidence.manifest.json",
        "data-preparation/coverage.csv", "data-preparation/calendar-exclusions.csv",
        "figure-environment.json", "tables/selected-example-paths.parquet",
        "provenance/source-inventory.json", "provenance/environment.json", "provenance/uv.lock",
        "provenance/git-status.txt", "provenance/commands.json", "provenance/checks.json",
        "provenance/stage2-numerical.json", "provenance/study21-numerical.json",
        "provenance/bhishma-ema-numerical.json", "provenance/input-coverage-identity.json",
        "provenance/slow-baseline-parity.json", "provenance/user-request.txt",
        "provenance/lifecycle.json", "provenance/publication-dry-run.json"]
    names = ["coverage", "signal_flow", "horizon_scorecard", "quantiles", "stability",
             "calendar", "examples", "geometry_membership", "branch_contrasts",
             "episode_pairing", "union_overlap"]
    required_paths += [f"tables/S2-T{i:02d}_{name}.csv" for i, name in enumerate(names)]
    required_paths += ["tables/S2-bootstrap.csv", "tables/S2-duration-comparisons.csv",
        "tables/S2-calendar-sufficient-statistics.csv", "tables/S2-episode-pair-metrics.csv"]
    required_paths += ["downloads/" + x for x in
        ("annual-side-session.csv", "episode-diagnostics.csv", "primary-branches.csv", "primary-effects.csv")]
    required_paths += ["figures/" + x + ".png" for x in
        ("calendar_coverage", "distributions", "episodes", "frequency_quality", "horizons", "qualifying_examples")]
    require(all(name in inventory for name in required_paths), "required retained artifact presence")

    source = json.loads((stage / "provenance/source-inventory.json").read_text())
    for r in source["sources"]:
        for p in (workspace / r["workspace_path"], stage / r["snapshot_path"]):
            observed = pin(p)
            require(observed["bytes"] == r["bytes"] and observed["sha256"] == r["sha256"], "frozen source identity")
    manifest_path = stage / "events.manifest.json"
    manifest_before = pin(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    records = manifest["records"]
    require(len(records) == 72 and manifest["reserved_outcomes_computed"] is False, "actual final72 declaration scope")
    expected = {(p, i, role, branch) for p in ("ES", "GC", "NQ") for i in (3, 5)
                for role, branch in ([("bars", "common"), ("membership", "common"), ("episodes", "common"),
                    ("pairs", "common"), ("union", "common"), ("union_outcomes", "common")]
                    + [(role, branch) for role in ("technical", "events", "outcomes") for branch in ("fast", "slow")])}
    actual = {(r["product"], int(r["interval_minutes"]), r["role"], r.get("branch", "common")) for r in records}
    require(actual == expected, "complete unique external role/branch/cell inventory")
    externals = []
    for r in records:
        p = Path(r["path"])
        observed = pin(p)
        require(p.is_file() and not p.is_symlink() and observed["bytes"] == r["bytes"]
                and observed["sha256"] == r["sha256"], "explicit external ledger bytes")
        externals.append(dict(id=f'{r["product"]}-{r["interval_minutes"]}m-{r.get("branch","common")}-{r["role"]}',
                              locator=r["path"], bytes=r["bytes"], sha256=r["sha256"]))
    require(len({r["id"] for r in externals}) == 72, "unique evidence manifest external IDs")
    require(pin(stage / "evidence.manifest.json")["sha256"] == manifest_before["sha256"], "final/evidence declaration consistency")
    lifecycle = json.loads((stage / "provenance/lifecycle.json").read_text())
    require(lifecycle["staged_root"] == str(stage) and lifecycle["sealed_root"] ==
            str(workspace / "runs/21_ema_cloud_trend_follow_opportunity" / stage.name), "locator lifecycle record")
    require(checks_before == pin(checks_path) and manifest_before == pin(manifest_path), "reviewed metadata stable")
    print(json.dumps(dict(status="passed_with_pending_sealing_gates", created_at=datetime.now(timezone.utc).isoformat(),
        checker=pin(__file__), stage=str(stage), checks=checks_before, strict_checks_count=len(checks),
        status_counts=dict(Counter(r["status"] for r in checks)),
        required_present_artifact_count=len(required_paths), source_inventory=pin(stage / "provenance/source-inventory.json"),
        frozen_source_records=len(source["sources"]), final_manifest=manifest_before,
        final_external_declarations=len(externals), final_external_ids=[r["id"] for r in externals],
        external_byte_verification=True, mandatory_pending=sorted(pending),
        pending_finalization=["Stage 3 handoff after passed reconciliation", "Complete mandatory gate records",
                              "Final manifest creation and declared-local integrity assessment", "Unique-run immutable move"],
        material_metadata_defects=[], source_edits=False, scientific_replay=False, market_scoring=False,
        qualification="This reviews present metadata/artifact bytes and the CLI contract. Active scientific/uncertainty/report-transfer/external-byte gates are intentionally pending; this receipt does not authorize sealing or replace those checks. Failed historical reconstruction prerequisites remain honestly recorded, and absolute execution locators are covered by lifecycle.json."),
        indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
