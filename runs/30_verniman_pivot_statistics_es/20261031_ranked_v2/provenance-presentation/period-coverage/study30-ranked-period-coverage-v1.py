"""Add exact eligible-window metadata downloads before sealing Study 30.

This supplementary presentation operation selects dates and counts eligible
sessions. It calculates no crossing, outcome, estimate or uncertainty interval.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys


COHORTS = ("pivot_matched_rth", "vwap_only_rth", "vwap_only_full_globex")
COLUMNS = ("cohort", "period_kind", "period", "eligible_sessions", "window_start", "window_end", "requested_cutoff")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    stage = args.stage.resolve()
    study = root / "studies/30_verniman_pivot_statistics_es"
    sys.path[:0] = [str(study), str(study / "src")]
    import lifecycle
    import ranked_lifecycle
    import ranked_statistics
    import publish_ranked as publisher
    from reporting import read_csv, require, sha, write_csv, write_json
    require(stage.is_relative_to(root / "work/30_verniman_pivot_statistics_es"), "Only a staged Study 30 run is allowed")
    require(not (stage / "manifest.json").exists(), "Refusing completed evidence")
    freeze = lifecycle.assert_frozen(stage)
    run_id = freeze["run_id"]
    scientific = json.loads((stage / "ranked-verification.json").read_text())
    require(scientific.get("status") == "passed", "Ranked scientific verification must pass first")
    provenance = stage / "provenance-presentation/period-coverage"
    require(not provenance.exists(), "Refusing to replace an existing metadata operation")
    provenance.mkdir(parents=True)
    script = Path(__file__).resolve()
    snapshot = provenance / script.name
    shutil.copyfile(script, snapshot)
    before = {str(path.relative_to(stage)): sha(path) for path in sorted((stage / "tables").glob("*.csv"))}
    evidence = ranked_lifecycle.read_ranked(stage)
    dates = {cohort: sorted(row["session_date"] for row in evidence["coverage"] if row.get(cohort) is True) for cohort in COHORTS}
    require(all(len(days) == len(set(days)) for days in dates.values()), "Duplicate eligible session dates")
    write_json(provenance / "eligible-session-rosters.json", dates)
    roster = []
    for cohort, days in dates.items():
        for kind, period, members in ranked_statistics.windows(days):
            selected = sorted(members)
            roster.append(dict(zip(COLUMNS, (cohort, kind, period, len(selected), selected[0] if selected else None,
                                            selected[-1] if selected else None, "2026-10-30"))))
    source = "tables/ranked_period_coverage.csv"
    require(not (stage / source).exists(), "Refusing to overwrite saved period metadata")
    write_csv(stage / source, roster)
    require(read_csv(stage / source) == roster, "Period metadata CSV round trip changed values")
    # Independently select each date window without using the frozen windows
    # helper, retaining empty periods and observed zero-event days explicitly.
    for row in roster:
        days, kind, period = dates[row["cohort"]], row["period_kind"], row["period"]
        if kind == "overall":
            selected = days
        elif kind == "year":
            selected = [day for day in days if day[:4] == period]
        elif kind == "calendar_month":
            selected = [day for day in days if day[:7] == period]
        elif kind == "recent":
            selected = days[-int(period.removeprefix("last_")):]
        elif kind == "preceding":
            size = int(period.removeprefix("before_last_"))
            selected = days[:-size] if len(days) > size else []
        else:
            raise ValueError(f"Unknown period kind: {kind}")
        require((row["eligible_sessions"], row["window_start"], row["window_end"]) ==
                (len(selected), selected[0] if selected else None, selected[-1] if selected else None), "Independent eligible window reconstruction differs")
    maps, added = [], [source]
    checked_cells = 0
    paragraph = ("The Actual valid date coverage column describes observations contributing to each measure. The Eligible cohort period coverage download separately records the eligible session count and actual window bounds, including sessions with zero crossings. Those cohort windows can extend beyond the valid-event coverage of a measure; empty periods have zero sessions and blank bounds.")
    for slug in publisher.SLUGS:
        directory = stage / "publications" / publisher.identity(run_id, slug)
        for name in ("publication.json", "source-map.json", "publication-verification.json", "publication-manifest.json"):
            destination = provenance / "before" / directory.relative_to(stage) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(directory / name, destination)
        cohorts = ("pivot_matched_rth",) if slug == "pivot-statistics" else ("vwap_only_rth", "vwap_only_full_globex")
        selected = [(index, row) for index, row in enumerate(roster) if row["cohort"] in cohorts]
        artifact = f"tables/publication-{slug}-period-coverage.csv"
        require(not (stage / artifact).exists(), "Refusing to overwrite selected period metadata")
        write_csv(stage / artifact, [row for _, row in selected])
        added.append(artifact)
        target = "downloads/period-coverage.csv"
        require(not (directory / target).exists(), "Period coverage download already exists")
        shutil.copyfile(stage / artifact, directory / target)
        report = json.loads((directory / "publication.json").read_text())
        require(not any(item["id"] == "period-coverage" for item in report.get("downloads", [])), "Duplicate period download")
        report["sections"][0]["body"] += "\n\n" + paragraph
        report["downloads"].append({"id": "period-coverage", "path": target, "label": "Eligible cohort period coverage",
                   "description": "Exact saved eligible-session counts and actual date bounds for every overall, annual, calendar-month and recent/preceding window. Includes zero-event days and empty periods. This differs from each metric's valid-contributing-date coverage.",
                   "population": ", ".join(cohorts) + "; separately retained eligible-date rosters, with no event-based selection.",
                   "units": "eligible_sessions is a count of observed eligible sessions. Bounds are ISO New York session dates. Empty periods have zero sessions and blank bounds; requested_cutoff is the requested calendar end.",
                   "scope": "Coverage metadata only. Recent 20/60/120 windows use eligible observed sessions and their preceding comparisons exclude the corresponding recent window. Cohorts are never pooled.",
                   "mediaType": "text/csv", "sha256": sha(directory / target), "rowCount": len(selected), "columns": list(COLUMNS),
                   "source": {"runId": run_id, "artifact": artifact, "sha256": sha(stage / artifact)}})
        write_json(directory / "publication.json", report)
        mapping = json.loads((directory / "source-map.json").read_text())
        item = {"artifact": source, "sha256": sha(stage / source), "source_rows": [i for i, _ in selected], "columns": list(COLUMNS),
                "saved_artifact": artifact, "saved_sha256": sha(stage / artifact), "target": target}
        mapping["period_coverage_download"] = item
        write_json(directory / "source-map.json", mapping)
        # Exact saved-row and byte verification is supplementary to the frozen
        # exporter's original summary-download check.
        expected = [{key: roster[index][key] for key in COLUMNS} for index in item["source_rows"]]
        require(expected == read_csv(stage / artifact) == read_csv(directory / target), "Period coverage source-cell transfer mismatch")
        require(sha(stage / artifact) == sha(directory / target) == report["downloads"][-1]["sha256"], "Period coverage byte pin mismatch")
        require(report["downloads"][-1]["rowCount"] == len(expected) and report["downloads"][-1]["columns"] == list(COLUMNS), "Period coverage declaration mismatch")
        maps.append({"publication_id": report["id"], **item, "row_count": len(expected)})
        checked_cells += len(expected) * len(COLUMNS)
    after = {str(path.relative_to(stage)): sha(path) for path in sorted((stage / "tables").glob("*.csv"))}
    require(all(after.get(path) == digest for path, digest in before.items()), "An existing saved numerical/public table changed")
    require(set(after) - set(before) == set(added), "Unexpected new table artifacts")
    lifecycle.assert_frozen(stage)
    transfer = publisher.verify(stage, run_id=run_id)
    counts = {**transfer, "checked_cells": transfer["checked_cells"] + checked_cells, "checked_period_coverage_cells": checked_cells}
    publisher.finalize(stage, run_id, counts)
    receipt_path = provenance / "period-coverage-verification.json"
    write_json(receipt_path, {"schema_version": "abacus.study30.period-coverage-transfer/v1", "status": "passed",
               "created_at": datetime.now(timezone.utc).isoformat(), "source_run_id": run_id, "command": sys.argv, "cwd": str(Path.cwd()),
               "source_code": {"path": str(script.relative_to(root)), "sha256": sha(script)},
               "source_snapshot": {"path": str(snapshot.relative_to(stage)), "sha256": sha(snapshot)},
               "freeze_sha256": sha(stage / "freeze.json"), "ranked_execution_sha256": sha(stage / "ranked-execution.json"),
               "ranked_verification_sha256": sha(stage / "ranked-verification.json"), "eligible_rosters_sha256": sha(provenance / "eligible-session-rosters.json"),
               "source_artifact": {"path": source, "sha256": sha(stage / source), "rows": len(roster)},
               "cohort_session_counts": {cohort: len(days) for cohort, days in dates.items()},
               "projections": maps, "checked_period_coverage_cells": checked_cells, "original_exporter_transfer": transfer,
               "unchanged_table_hashes": before,
               "checks": ["Frozen windows metadata matches independent date selection", "Each saved/downloaded period cell and byte matches its declaration", "All prior tables unchanged; frozen source assertion passed"],
               "scope": "Eligible date population metadata only. No numerical estimates, events, outcomes, uncertainty intervals or cohort decisions changed."})
    for directory in (stage / "publications").iterdir():
        manifest = json.loads((directory / "publication-manifest.json").read_text())
        extra = [stage / source, snapshot, receipt_path, provenance / "eligible-session-rosters.json"]
        extra += [stage / item["saved_artifact"] for item in maps if item["publication_id"] == directory.name]
        for path in extra:
            manifest["source_artifacts"].append({"path": f"runs/{publisher.SID}/{run_id}/{path.relative_to(stage)}", "sha256": sha(path)})
        write_json(directory / "publication-manifest.json", manifest)
    print(json.dumps({"status": "passed", "source_sha256": sha(script), "period_rows": len(roster),
                      "cohort_sessions": {cohort: len(days) for cohort, days in dates.items()},
                      "checked_period_coverage_cells": checked_cells, "counts": counts,
                      "receipt": str(receipt_path.relative_to(root))}, sort_keys=True))


if __name__ == "__main__":
    main()
