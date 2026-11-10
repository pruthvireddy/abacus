"""Execute the pinned Daily Facts notebook and seal verified local evidence."""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from fractions import Fraction
from html import escape
import json
import math
import os
from pathlib import Path
import re
import shutil
from statistics import mean, median
import subprocess
import sys
import tempfile

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

from abacus_bhishma.daily_facts_loader import load_daily_facts
from abacus_bhishma.paths import resolve_publication_root, workspace_root
from abacus_bhishma.provenance import (git_version, retain_sources, sha256_file,
                                      verify_retained_sources)
from abacus_bhishma.publication_safety import check_absent, check_path

STUDY = "31_daily_facts_volume_pilot"
NOTEBOOK = "daily-facts-volume-pilot.ipynb"
TABLES = ("coverage.csv", "paired_hours.csv", "rth_shares.csv")


def write_json(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def csv_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def compare_rows(path, expected):
    actual = csv_rows(path)
    if len(actual) != len(expected):
        raise ValueError(f"{path.name}: unexpected row count")
    for found, wanted in zip(actual, expected):
        if set(found) != set(wanted):
            raise ValueError(f"{path.name}: unexpected columns")
        for field, value in wanted.items():
            if isinstance(value, (float, Fraction)):
                ok = math.isclose(float(found[field]), float(value), rel_tol=1e-12, abs_tol=1e-9)
            else:
                ok = found[field] == str(value)
            if not ok:
                raise ValueError(f"{path.name}: {wanted.get('asset')} {field} differs")


def verify_saved_tables(stage, publication_root, pin):
    """Cross-check notebook outputs with stdlib arithmetic over pinned Arrow rows."""
    source = load_daily_facts(
        publication_root, manifest_path=pin["manifest_path"], manifest_sha256=pin["manifest_sha256"],
        assets=tuple(pin["assets"]), start=date.fromisoformat(pin["start"]),
        end_exclusive=date.fromisoformat(pin["end_exclusive"]),
        columns=["asset", "session_date", "calendar_status", "first60_volume", "last60_volume",
                 "rth_volume", "rth_aggregate_ready", "globex_aggregate_ready"],
    ).to_pylist()
    coverage, hours, shares, exclusions = [], [], [], []
    for asset in pin["assets"]:
        roster = [row for row in source if row["asset"] == asset]
        eligible = [row for row in roster if row["calendar_status"] == "eligible"]
        paired, share_pairs = [], []
        for row in roster:
            first, last, total = (row[name] for name in ("first60_volume", "last60_volume", "rth_volume"))
            calendar_ok = row["calendar_status"] == "eligible"
            pair = calendar_ok and first is not None and last is not None
            if pair:
                paired.append((first, last))
                if row["rth_aggregate_ready"] and total > 0:
                    share_pairs.append((Fraction(first, total), Fraction(last, total)))
                    continue
            reason = ("incomplete_or_zero_rth_volume" if pair else "incomplete_hour_pair"
                      if calendar_ok else row["calendar_status"])
            exclusions.append({"asset": asset, "session_date": row["session_date"],
                               "calendar_status": row["calendar_status"], "paired": pair, "reason": reason})
        coverage.append({
            "asset": asset, "weekday_roster": len(roster), "calendar_excluded": len(roster) - len(eligible),
            "eligible": len(eligible), "incomplete_hour_pair": len(eligible) - len(paired),
            "paired": len(paired), "share_excluded_after_pairing": len(paired) - len(share_pairs),
            "share_paired": len(share_pairs),
            "rth_complete_globex_incomplete": sum(row["rth_aggregate_ready"] and not row["globex_aggregate_ready"]
                                                  for row in eligible),
        })
        first, last = zip(*paired)
        higher = sum(a > b for a, b in paired)
        hours.append({
            "asset": asset, "paired_sessions": len(paired),
            "mean_first_contracts": mean(first), "mean_last_contracts": mean(last),
            "median_first_contracts": float(median(first)), "median_last_contracts": float(median(last)),
            "median_first_minus_last_contracts": float(median(a - b for a, b in paired)),
            "first_higher_sessions": higher, "equal_sessions": sum(a == b for a, b in paired),
            "first_higher_fraction": Fraction(higher, len(paired)),
        })
        first_share, last_share = zip(*share_pairs)
        shares.append({"asset": asset, "share_paired_sessions": len(share_pairs),
                       "mean_first_rth_share": mean(first_share), "mean_last_rth_share": mean(last_share)})
    exclusions.sort(key=lambda row: (row["asset"], row["session_date"]))
    for name, expected in zip((*TABLES, "exclusions.csv"), (coverage, hours, shares, exclusions)):
        compare_rows(stage / "tables" / name, expected)
    if coverage[-1]["asset"] != "GC" or coverage[-1]["rth_complete_globex_incomplete"] != 849:
        raise ValueError("GC independent-window handoff differs from the audited count")
    return {"status": "passed", "method": "Independent stdlib integer and rational arithmetic over pinned facts",
            "table_rows": {name: len(rows) for name, rows in
                           zip((*TABLES, "exclusions.csv"), (coverage, hours, shares, exclusions))},
            "gc_complete_rth_with_incomplete_globex": 849}


def report(stage):
    coverage, hours, shares = [csv_rows(stage / "tables" / name) for name in TABLES]
    entries = []
    for c, h, s in zip(coverage, hours, shares):
        entries.append([c["asset"], c["eligible"], c["paired"], c["incomplete_hour_pair"],
                        s["share_paired_sessions"], f"{float(h['first_higher_fraction']):.1%}",
                        f"{float(s['mean_first_rth_share']):.1%}", f"{float(s['mean_last_rth_share']):.1%}"])
    headers = ["Asset", "Eligible", "Hour pairs", "Incomplete pairs", "Share pairs",
               "First hour higher", "Mean first share", "Mean last share"]
    summary = (
        "The notebook pairs the first and last RTH hours within each asset and date. "
        "Mean shares use sessions with complete positive RTH volume and weight each session equally. "
        "The observation period is June 28, 2021 through September 18, 2026. "
        "Estimates describe the retained sample and use each asset's own RTH calendar."
    )
    table = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    table += ["| " + " | ".join(row) + " |" for row in entries]
    chart = "figures/rth_hour_shares.png"
    (stage / "report.md").write_text(
        "# Daily Facts volume pilot\n\n" + summary + "\n\n" + "\n".join(table)
        + f"\n\n![Mean first and last hour share by asset]({chart})\n\n"
        + f"[Executed notebook]({NOTEBOOK}) · [Coverage](tables/coverage.csv) · "
        "[Paired volumes](tables/paired_hours.csv) · [Shares](tables/rth_shares.csv)\n"
    )
    html_table = "<thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr></thead>"
    html_table += "<tbody>" + "".join(
        "<tr>" + "".join(f"<td>{escape(v)}</td>" for v in row) + "</tr>" for row in entries
    ) + "</tbody>"
    (stage / "report.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>Daily Facts volume pilot</title>'
        '<style>body{font:16px system-ui;max-width:66rem;margin:2rem auto;padding:0 1rem}'
        'table{border-collapse:collapse}th,td{padding:.55rem;text-align:right;border-bottom:1px solid #ccc}'
        'th:first-child,td:first-child{text-align:left}img{max-width:100%;height:auto}.table{overflow:auto}</style>'
        f'<main><h1>Daily Facts volume pilot</h1><p>{escape(summary)}</p>'
        f'<div class="table"><table>{html_table}</table></div>'
        f'<img src="{chart}" alt="Mean first and last hour share of RTH volume for ES, NQ and GC">'
        f'<p><a href="{NOTEBOOK}">Executed notebook</a> · '
        '<a href="tables/paired_hours.csv">Paired volume details</a></p></main></html>\n'
    )
    def numeric_rows(rows):
        return [{name: value if name == "asset" else int(value) if re.fullmatch(r"-?\d+", value)
                 else float(value) for name, value in row.items()} for row in rows]

    write_json(stage / "metrics.json", {
        "dataset_id": "daily_market_facts__1.0.0",
        "observation_unit": "one asset and session date",
        "volume_unit": "contracts", "share_unit": "fraction", "uncertainty": "descriptive point estimates",
        "coverage": numeric_rows(coverage), "paired_hours": numeric_rows(hours),
        "rth_shares": numeric_rows(shares),
    })


def execute_notebook(notebook, stage):
    with tempfile.TemporaryDirectory(prefix="abacus-df-") as directory:
        runtime = Path(directory)
        spec = runtime / "daily-facts"
        spec.mkdir()
        argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        write_json(spec / "kernel.json", {"argv": argv, "display_name": "Daily Facts pilot",
                                          "language": "python"})
        manager = KernelManager(kernel_name=spec.name, transport="ipc", ip=str(runtime / "kernel"),
                                connection_file=str(runtime / "connection.json"),
                                kernel_spec_manager=KernelSpecManager(kernel_dirs=[directory]))
        client = NotebookClient(notebook, km=manager, timeout=120,
                                resources={"metadata": {"path": str(stage)}})
        return client.execute(cleanup_kc=True), {"argv": argv, "transport": "ipc"}


def execute(root, run_id):
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[a-z0-9_]+", run_id):
        raise ValueError("use a sortable UTC run ID followed by a unique suffix")
    started = datetime.now(timezone.utc).isoformat()
    stage = root / "work" / STUDY / run_id
    final = root / "runs" / STUDY / run_id
    check_absent(stage, root)
    check_absent(final, root)
    stage.mkdir(parents=True, exist_ok=False)
    for directory in ("tables", "figures"):
        (stage / directory).mkdir()
    study = root / "studies" / STUDY
    sources = [(name, study / name) for name in
               ("run.py", NOTEBOOK, "plan.md", "study.yaml", "inputs.lock.json", "notes.md")]
    sources.append(("uv.lock", root / "uv.lock"))
    package = root / "packages/bhishma/src/abacus_bhishma"
    sources += [(f"abacus_bhishma/{name}", package / name) for name in
                ("__init__.py", "daily_facts_loader.py", "paths.py", "manifest_selection.py",
                 "provenance.py", "publication_safety.py")]
    retained = retain_sources(stage / "sources", sources, artifact_id=run_id, root=root)
    shutil.copyfile(stage / "sources/inputs.lock.json", stage / "inputs.lock.json")
    pin = json.loads((stage / "inputs.lock.json").read_text())
    write_json(stage / "config.json", {"study_id": STUDY, "protocol_version": "1.0.0",
                                      "template_version": 1, "run_id": run_id, "assets": pin["assets"],
                                      "start": pin["start"], "end_exclusive": pin["end_exclusive"],
                                      "pair": "eligible and both hour volumes defined",
                                      "share_subset": "paired and complete positive RTH volume"})
    code = git_version(root)
    (stage / "git-status.txt").write_text(subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True,
    ))
    original = nbformat.read(stage / "sources" / NOTEBOOK, as_version=4)
    notebook, kernel = execute_notebook(nbformat.read(stage / "sources" / NOTEBOOK, as_version=4), stage)
    nbformat.validate(notebook)
    if [(c.id, c.cell_type, c.source) for c in notebook.cells] != [
            (c.id, c.cell_type, c.source) for c in original.cells]:
        raise ValueError("executed notebook source differs from the retained authoring source")
    counts = [cell.execution_count for cell in notebook.cells if cell.cell_type == "code"]
    if counts != list(range(1, len(counts) + 1)):
        raise ValueError("notebook cells did not execute once in order")
    nbformat.write(notebook, stage / NOTEBOOK)
    comparison = verify_saved_tables(stage, resolve_publication_root(workspace=root), pin)
    plot = stage / "figures/rth_hour_shares.png"
    chart_cell = next(cell for cell in notebook.cells if cell.id == "share-evidence")
    if (plot.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n"
            or not any("image/png" in output.get("data", {}) for output in chart_cell.outputs)):
        raise ValueError("expected saved and inline notebook chart")
    verify_retained_sources(stage / "sources", sources, retained)
    report(stage)
    (stage / "advice.md").write_text(
        "# Pilot interpretation\n\nThe local facts handoff supports same-session descriptive "
        "volume comparisons with the recorded asset denominators. Retain window-level quality "
        "in later serving work. This pilot estimates descriptive volume only.\n"
    )
    write_json(stage / "verification.json", {**comparison, "executed_code_cells": len(counts),
                                             "started_at_utc": started,
                                             "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                                             "kernel": kernel,
                                             "authored_source_sha256": sha256_file(stage / "sources" / NOTEBOOK),
                                             "notebook_sha256": sha256_file(stage / NOTEBOOK),
                                             "release_manifest_sha256": pin["manifest_sha256"]})
    env = {key: os.environ[key] for key in ("MPLCONFIGDIR", "IPYTHONDIR", "JUPYTER_RUNTIME_DIR", "UV_CACHE_DIR")
           if key in os.environ}
    write_json(stage / "commands.json", [{"argv": [sys.executable, "-B", *sys.argv],
                                         "cwd": str(Path.cwd()), "environment": env}])
    write_json(stage / "checks.json", [{"name": "notebook_execution_and_independent_table_parity",
                                       "status": "passed", "record": "verification.json"}])
    records = [{"path": str(path.relative_to(stage)), "bytes": path.stat().st_size,
                "sha256": sha256_file(path)} for path in sorted(stage.rglob("*")) if path.is_file()]
    write_json(stage / "manifest.json", {
        "contract": "abacus.evidence/v1", "bundle_kind": "research",
        "study_id": STUDY, "run_id": run_id, "inventory_scope": "declared_artifacts",
        "results": {"kind": "quantitative", "state": "computed",
                    "artifacts": ["metrics.json", *[f"tables/{name}" for name in TABLES]]},
        "provenance": {"settings": "config.json", "input_lock": "inputs.lock.json",
                       "exclusions": "tables/exclusions.csv", "commands": "commands.json",
                       "checks": "checks.json", "environment_lock": "sources/uv.lock",
                       "code": {"revision": code["git_commit"], "dirty": code["git_worktree_dirty"],
                                "status": "git-status.txt",
                                "source_snapshot": {"paths": [f"sources/{name}" for name, _ in sources],
                                                    "scope": "Declared notebook, runner and Bhishma loader bytes"}}},
        "artifacts": records,
    })
    # Assess the staged evidence before reserving the immutable final directory.
    subprocess.run([sys.executable, "-B", str(root / "scripts/check-evidence-bundle.py"), str(stage)],
                   cwd=root, check=True)
    check_path(final, root)
    final.mkdir(parents=True, exist_ok=False)
    stage.rename(final)
    print(f"Sealed {final}. Started {started}. Executed {len(counts)} notebook cells.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    execute(workspace_root(), parser.parse_args().run_id)


if __name__ == "__main__":
    main()
