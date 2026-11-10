"""Execute the NQ overnight notebook and retain verified local review evidence."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import csv
from datetime import date, datetime, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

from abacus_bhishma.paths import workspace_root
from abacus_bhishma.provenance import git_version, retain_sources, sha256_file, verify_retained_sources
from abacus_bhishma.publication_safety import check_absent
from support import load_study

STUDY = "32_nq_overnight_range"
NOTEBOOK = "nq-overnight-range-cash-open.ipynb"


def write_json(path, value):
    with path.open("x") as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write("\n")


def read_csv(path):
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def verify_tables(root, pin, stage):
    """Reconcile all cohort records and primary rates independently of notebook code."""
    facts, paths, _ = load_study(root, pin)
    expected, levels = {}, {}
    for row in facts.itertuples():
        if row.overnight_status != "complete" or row.rth_status != "complete":
            continue
        if not row.overnight_low < row.rth_open < row.overnight_high:
            continue
        doubled = 2 * row.rth_open
        boundaries = row.overnight_high + row.overnight_low
        location = "upper half" if doubled > boundaries else "lower half" if doubled < boundaries else "midpoint"
        expected[row.session_date.isoformat()] = location
        levels[row.session_date] = float(row.overnight_high), float(row.overnight_low)
    results = read_csv(stage / "tables/session-outcomes.csv")
    if len(expected) != len(results) or {row["session_date"]: row["location"] for row in results} != expected:
        raise ValueError("saved outcome roster differs from independently selected sessions")

    counts, hits = Counter(), Counter()
    orders = Counter()
    for row in results:
        day = date.fromisoformat(row["session_date"])
        high, low = levels[day]
        prices = paths[day].tolist()
        from_prices = (next((minute for minute, (_, h, _) in enumerate(prices) if h >= high), 1000),
                       next((minute for minute, (_, _, l) in enumerate(prices) if l <= low), 1000))
        upper, lower = (int(float(row[key])) if row[key] else 1000 for key in ("high_minute", "low_minute"))
        order = ("high" if upper < lower else "low" if lower < upper
                 else "neither" if upper == 1000 else "same minute")
        if ((upper, lower) != from_prices or row["order"] != order or row["hit_high"] != str(upper < 390)
                or row["hit_low"] != str(lower < 390)
                or row["both"] != str(max(upper, lower) < 390)
                or row["neither"] != str(min(upper, lower) == 1000)):
            raise ValueError(f"saved first-touch labels differ for {row['session_date']}")
        counts[row["location"]] += 1
        hits[row["location"], "hit_high"] += upper < 390
        hits[row["location"], "hit_low"] += lower < 390
        near = row["near_side"]
        if near:
            orders["Unresolved" if order == "same minute" else "Neither" if order == "neither"
                   else "Near first" if order == near else "Far first"] += 1
    actual_orders = {row["outcome"]: int(row["n"]) for row in read_csv(stage / "tables/first-touch-order.csv")}
    if actual_orders != orders:
        raise ValueError("saved order summary differs from independently aggregated labels")
    rates = read_csv(stage / "tables/reel-touch-rates.csv")
    if {(row["group"], row["metric"]) for row in rates} != set(hits):
        raise ValueError("saved reel comparison is missing an opening cohort")
    for row in rates:
        group, metric = row["group"], row["metric"]
        numerator, denominator = hits[group, metric], counts[group]
        if ((int(row["hits"]), int(row["n"])) != (numerator, denominator)
                or not math.isclose(float(row["rate"]), numerator / denominator, rel_tol=1e-12)):
            raise ValueError("saved reel comparison differs from the independently aggregated ledger")

    prediction_rows = read_csv(stage / "tables/holdout-predictions.csv")
    models = read_csv(stage / "tables/holdout-model-scores.csv")
    model_keys = {}
    for row in models:
        pair = row["outcome"], row["model"]
        observations = {item["session_date"]: (float(item["prediction"]), float(item["observed"]))
                        for item in prediction_rows if (item["outcome"], item["model"]) == pair}
        if (len(observations) != int(row["holdout_n"])
                or any(date.fromisoformat(day).year < 2025 for day in observations)
                or not math.isclose(float(row["brier"]), sum((p - y) ** 2 for p, y in observations.values())
                                    / len(observations), rel_tol=1e-12)):
            raise ValueError("saved holdout score or dates disagree with the prediction table")
        model_keys[pair] = {day: y for day, (_, y) in observations.items()}
    for (outcome, _), observations in model_keys.items():
        if observations != model_keys[outcome, "Distances"]:
            raise ValueError("holdout outcomes differ across comparison models")
    return {"status": "passed", "outcome_rows": len(results), "reconciled_touch_estimates": len(rates),
            "independent_minute_boundary_checks": 2 * len(results),
            "holdout_model_scores": len(models), "holdout_prediction_rows": len(prediction_rows),
            "roster": len(facts)}


def render_report(notebook, stage):
    """Render the executed narrative and figures as a standalone local reading copy."""
    html = ["""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>NQ Overnight Range at the Cash Open</title>
<style>body{font:17px/1.55 system-ui;color:#20262c;margin:2rem auto;padding:0 1rem;max-width:62rem}
h1,h2,h3{line-height:1.15}h2{margin-top:3rem;border-bottom:1px solid #ddd;padding-bottom:.4rem}
h3{margin-top:2rem}img{max-width:100%;height:auto}.table{overflow:auto}td,th{padding:.25rem .6rem}
.finding{border-left:3px solid #36668f;padding:.15rem .8rem}a{color:#285d83}</style>
<main>"""]
    markdown = []
    figures = 0
    for cell in notebook.cells:
        role = cell.metadata.abacus.role
        if role in {"intro", "theme", "heading", "description"}:
            markdown.append(cell.source)
            for paragraph in cell.source.split("\n\n"):
                level = len(paragraph) - len(paragraph.lstrip("#"))
                if level:
                    html.append(f"<h{level}>{escape(paragraph[level:].strip())}</h{level}>")
                else:
                    prose = escape(paragraph)
                    if role == "intro":
                        prose = prose.replace("[reel’s two headline rates](https://www.instagram.com/reel/Dfai3hHvMDn/)",
                                              '<a href="https://www.instagram.com/reel/Dfai3hHvMDn/">reel’s two headline rates</a>')
                    html.append(f"<p>{prose}</p>")
        elif role in {"finding", "evidence"}:
            outputs = [output.data for output in cell.outputs if "data" in output]
            if len(outputs) != 1:
                raise ValueError(f"expected one display output for {cell.id}")
            data = outputs[0]
            key = cell.metadata.abacus.insight
            if role == "finding":
                text = data["text/markdown"]
                markdown.append(text)
                formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escape(text))
                html.append(f'<p class="finding">{formatted}</p>')
            elif "image/png" in data:
                path = f"figures/{key}.png"
                if base64.b64decode(data["image/png"]) != (stage / path).read_bytes():
                    raise ValueError(f"notebook image disagrees with saved figure {key}")
                alt = key.replace("-", " ").capitalize()
                html.append(f'<img src="{path}" alt="{alt}">')
                markdown.append(f"![{alt}]({path})")
                figures += 1
            else:
                html.append(f'<div class="table">{data["text/html"]}</div>')
    html.append(f'<p><a href="{NOTEBOOK}">Executed notebook</a> · '
                '<a href="tables/coverage.csv">Coverage table</a> · <a href="tables/era-year-rates.csv">Era and yearly rates</a></p></main>')
    (stage / "report.html").write_text("\n".join(html) + "\n")
    (stage / "report.md").write_text("\n\n".join(markdown) + "\n")
    return figures


def execute_notebook(source, stage):
    notebook = nbformat.read(source, as_version=4)
    originals = [(cell.id, cell.source) for cell in notebook.cells]
    with TemporaryDirectory(prefix="abacus-nq-") as directory:
        runtime = Path(directory)
        spec = runtime / "nq-overnight"
        spec.mkdir()
        argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        write_json(spec / "kernel.json", {"argv": argv, "display_name": "NQ overnight", "language": "python"})
        manager = KernelManager(kernel_name=spec.name, transport="ipc", ip=str(runtime / "kernel"),
                                connection_file=str(runtime / "connection.json"),
                                kernel_spec_manager=KernelSpecManager(kernel_dirs=[directory]))
        env = {**os.environ, "ABACUS_NQ_STAGE": str(stage), "ABACUS_NQ_SOURCE": str(source.parent),
               "MPLCONFIGDIR": str(runtime / "matplotlib"), "PYTHONDONTWRITEBYTECODE": "1"}
        NotebookClient(notebook, km=manager, timeout=180,
                       resources={"metadata": {"path": str(stage)}}).execute(cleanup_kc=True, env=env)
    nbformat.validate(notebook)
    counts = [cell.execution_count for cell in notebook.cells if cell.cell_type == "code"]
    if [(cell.id, cell.source) for cell in notebook.cells] != originals or counts != list(range(1, len(counts) + 1)):
        raise ValueError("executed notebook source or cell order changed")
    nbformat.write(notebook, stage / NOTEBOOK)
    return notebook, argv, len(counts)


def execute(root, run_id):
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[a-z0-9_]+", run_id):
        raise ValueError("use a sortable UTC run ID with a unique suffix")
    stage, final = root / "work" / STUDY / run_id, root / "runs" / STUDY / run_id
    check_absent(stage, root)
    check_absent(final, root)
    stage.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    study = root / "studies" / STUDY
    source_files = [(name, study / name) for name in
                    (NOTEBOOK, "run.py", "support.py", "plan.md", "study.yaml", "inputs.lock.json", "notes.md")]
    source_files.append(("uv.lock", root / "uv.lock"))
    source_files.extend((path.name, path) for path in sorted((study / "tests").glob("test*.py")))
    package = root / "packages/bhishma/src/abacus_bhishma"
    source_files.extend((f"abacus_bhishma/{name}.py", package / f"{name}.py") for name in (
        "__init__", "calendar", "continuous_loader", "daily_context", "daily_facts", "daily_facts_loader",
        "manifest_selection", "nq_opening_range", "paths", "provenance", "publication_safety"))
    source_pin = retain_sources(stage / "sources", source_files, artifact_id=run_id, root=root)
    settings = json.loads((stage / "sources/study.yaml").read_text())
    pin = json.loads((stage / "sources/inputs.lock.json").read_text())
    write_json(stage / "config.json", {"run_id": run_id, **settings})
    code = git_version(root)
    (stage / "git-status.txt").write_text(subprocess.check_output(["git", "status", "--porcelain"],
                                                                  cwd=root, text=True))
    notebook, kernel, executed_cells = execute_notebook(stage / "sources" / NOTEBOOK, stage)
    verification = verify_tables(root, pin, stage)
    verification["verified_inline_figures"] = render_report(notebook, stage)
    verify_retained_sources(stage / "sources", source_files, source_pin)
    write_json(stage / "verification.json", {
        **verification, "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "executed_code_cells": executed_cells, "kernel": {"argv": kernel, "transport": "ipc"},
        "notebook_sha256": sha256_file(stage / NOTEBOOK),
        "authored_source_sha256": sha256_file(stage / "sources" / NOTEBOOK),
        "notebook_checks": json.loads((stage / "notebook-checks.json").read_text()),
    })
    write_json(stage / "commands.json", [{"argv": [sys.executable, "-B", *sys.argv],
                                         "cwd": str(root), "environment": {}}])
    write_json(stage / "checks.json", [{"name": "notebook_and_independent_reconciliation", "status": "passed",
                                         "record": "verification.json"}])
    tables = ["reel-touch-rates", "first-touch-order", "era-year-rates", "annual-common-cutoff",
              "holdout-model-scores", "distance-matched-vxn"]
    records = [{"path": str(path.relative_to(stage)), "bytes": path.stat().st_size,
                "sha256": sha256_file(path)} for path in sorted(stage.rglob("*")) if path.is_file()]
    write_json(stage / "manifest.json", {
        "contract": "abacus.evidence/v1", "bundle_kind": "research", "study_id": STUDY,
        "run_id": run_id, "inventory_scope": "declared_artifacts",
        "results": {"kind": "quantitative", "state": "computed", "artifacts": [
            *[f"tables/{name}.csv" for name in tables]]},
        "provenance": {
            "settings": "config.json", "input_lock": "sources/inputs.lock.json",
            "exclusions": "tables/exclusions.csv", "commands": "commands.json", "checks": "checks.json",
            "environment_lock": "sources/uv.lock",
            "code": {"revision": code["git_commit"], "dirty": code["git_worktree_dirty"],
                     "status": "git-status.txt", "source_snapshot": {
                         "paths": [f"sources/{name}" for name, _ in source_files],
                         "scope": "Declared study notebook, execution and Bhishma sources"}},
        },
        "artifacts": records,
    })
    subprocess.run([sys.executable, "-B", str(root / "scripts/check-evidence-bundle.py"), str(stage)],
                   cwd=root, check=True)
    final.parent.mkdir(parents=True, exist_ok=True)
    final.mkdir(exist_ok=False)
    stage.rename(final)
    print(f"Sealed {final} with {executed_cells} executed cells.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    execute(workspace_root(), parser.parse_args().run_id)


if __name__ == "__main__":
    main()
