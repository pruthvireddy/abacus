"""Project the sealed Study 32 notebook into six Narada presentation revisions."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

STUDY = "32_nq_overnight_range"
RUN = "20261110T134251Z_review_nq_v2"
NOTEBOOK = "nq-overnight-range-cash-open.ipynb"
REVISION = "narada-v1"
TABLES = {
    "coverage": "coverage", "fresh-touches": "fresh-touches",
    "placebo": "placebo-comparison", "distance-matched": "distance-matched-vxn",
    "holdout-models": "holdout-model-scores", "annual-width": "annual-width-and-volatility",
}
FIGURES = {
    "opening-geometry": "Distribution of overnight width by era and distribution of normalized cash-open location.",
    "regime-width": "Overnight width in NQ points across pre-open VXN and VIX regimes on matched dates.",
    "daytime-range": "Median regular-session movement by width and VXN, plus annual raw and relative overnight width.",
    "reel-comparison": "Overnight boundary reach rates by opening half, with Wilson intervals and reel benchmarks.",
    "width-outcomes": "Near-only, far-only, both and neither outcomes across overnight width bands.",
    "width-vxn": "Near-first and both-side reach rates by overnight width and VXN, with session counts.",
    "first-timing": "First-boundary ordering and cumulative probability of reaching the near and far boundary.",
    "excursion": "Adverse movement bounds before a near-side hit and full-session adverse movement on misses.",
    "annual-stability": "Boundary reach and first-touch rates by era and recent year, with Wilson intervals.",
    "era-regimes": "Range-width and VXN matrices split by era, with small cells shown as counts only.",
}
PERCENT = {"fresh_rate", "actual_near", "placebo_near", "actual_first", "placebo_first",
           "low_vxn", "high_vxn", "mean_predicted", "observed_rate"}
POINTS = {"median_points", "p25_points", "p75_points", "cutoff_median_points"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return "".join(value)


def plain(value):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", value).strip()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def metadata(cell):
    return cell["metadata"]["abacus"]


def rich(cell):
    outputs = cell["outputs"]
    if len(outputs) != 1 or outputs[0]["output_type"] != "display_data":
        raise ValueError(f"unexpected rich output in {cell['id']}")
    return outputs[0]["data"]


def table_evidence(data, path):
    frame = pd.read_csv(path, float_precision="round_trip")
    expected = text(data["text/html"])
    if frame.round(4)._repr_html_() != expected:
        raise ValueError(f"typed saved table differs from executed display: {path.name}")
    columns = []
    for key, dtype in frame.dtypes.items():
        kind = dtype.kind
        column = {"key": key, "label": key.replace("_", " ").title()}
        if kind in "fi":
            column.update(format="number", precision=0 if kind == "i" else 4)
        if key in PERCENT:
            column.update(format="percent", precision=1)
        if key in POINTS:
            column.update(unit="points", precision=2)
        columns.append(column)
    rows = json.loads(frame.to_json(orient="records", double_precision=15))
    for row, original in zip(rows, frame.itertuples(index=False, name=None), strict=True):
        for key, value in zip(frame.columns, original, strict=True):
            if not pd.isna(value):
                row[key] = value
    return {"kind": "table", "columns": columns, "rows": rows}


def project(root, published_at, *, check=False):
    run = root / "runs" / STUDY / RUN
    locator = Path("reports/exports") / STUDY / RUN
    executable = root / "studies" / STUDY / "publish_notebook.py"
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if manifest["run_id"] != RUN or manifest["study_id"] != STUDY:
        raise ValueError("sealed run identity differs")
    inventory = {row["path"]: row for row in manifest["artifacts"]}

    def pinned(relative):
        data = (run / relative).read_bytes()
        row = inventory[relative]
        if len(data) != row["bytes"] or digest(data) != row["sha256"]:
            raise ValueError(f"changed sealed artifact: {relative}")
        return data

    execution = json.loads(pinned("verification.json"))
    book = json.loads(pinned(NOTEBOOK))
    authored = json.loads(pinned("sources/" + NOTEBOOK))
    if (execution["status"] != "passed" or execution["notebook_sha256"] != digest(pinned(NOTEBOOK))
            or execution["authored_source_sha256"] != digest(pinned("sources/" + NOTEBOOK))
            or (root / "studies" / STUDY / NOTEBOOK).read_bytes() != pinned("sources/" + NOTEBOOK)):
        raise ValueError("verified execution or current notebook source differs")
    cells = book["cells"]
    authored_cells = authored["cells"]
    signature = lambda entries: [(cell["id"], cell["source"], metadata(cell)) for cell in entries]
    if signature(cells) != signature(authored_cells) or book["metadata"]["abacus"] != authored["metadata"]["abacus"]:
        raise ValueError("executed notebook theme and cell identity differs")
    counts = [cell["execution_count"] for cell in cells if cell["cell_type"] == "code"]
    if counts != list(range(1, execution["executed_code_cells"] + 1)):
        raise ValueError("executed notebook cells are incomplete or out of order")

    def pin(path, data):
        return {"path": path.relative_to(root).as_posix(), "bytes": len(data), "sha256": digest(data)}

    sources = [pin(manifest_path, manifest_path.read_bytes()), pin(executable, executable.read_bytes())]
    for relative in (NOTEBOOK, "verification.json", "sources/" + NOTEBOOK,
                     "sources/inputs.lock.json", "sources/uv.lock"):
        sources.append(pin(run / relative, pinned(relative)))
    public = []
    seen = set()
    themes = book["metadata"]["abacus"]["themes"]
    if len(themes) != execution["notebook_checks"]["themes"]:
        raise ValueError("theme count differs from verified execution")
    for theme in themes:
        theme_id = theme["id"]
        publication = f"nq-overnight-{theme_id}-v1"
        revision = root / locator / f"{REVISION}-{theme_id.replace('-', '_')}"
        theme_cells = [cell for cell in cells if metadata(cell).get("theme") == theme_id]
        header, *insight_cells = theme_cells
        expected_heading, summary = text(header["source"]).split("\n\n", 1)
        if expected_heading != "## " + theme["label"]:
            raise ValueError(f"theme header differs: {theme_id}")
        report = {"schemaVersion": "1.1", "presentation": "research-paper", "id": publication,
                  "title": theme["label"], "summary": summary, "publishedAt": published_at,
                  "source": {"producer": "sahadeva", "runId": RUN}, "sections": [],
                  "notes": ["One unadjusted NQ contract per session. New York overnight hours are 18:00–09:30 and regular hours are 09:30–16:00.",
                            "The study covers January 2015 through September 18, 2026. 2018–2019 supply 295 of 307 earlier-era sessions.",
                            "Reel benchmark: Instagram reel Dfai3hHvMDn by @rithvikrishna64. Its exact sample and event definitions are unavailable.",
                            "Reaches use one-minute OHLC. The study describes price behavior and does not estimate trade execution or returns."]}
        assets, transfers, theme_sources = {}, [], []
        for index in range(0, len(insight_cells), 5):
            group = insight_cells[index:index + 5]
            roles = [metadata(cell)["role"] for cell in group]
            key = metadata(group[0])["insight"]
            if (roles != ["heading", "description", "analysis", "finding", "evidence"]
                    or {metadata(cell)["insight"] for cell in group} != {key} or key in seen):
                raise ValueError(f"unexpected or duplicate insight: {key}")
            seen.add(key)
            heading, description, _, finding, evidence = group
            title = text(heading["source"]).removeprefix("### ")
            original = text(rich(finding)["text/markdown"])
            section = {"id": key, "title": title, "description": text(description["source"]),
                       "finding": plain(original)}
            selected = rich(evidence)
            if key in TABLES:
                source = f"tables/{TABLES[key]}.csv"
                theme_sources.append(pin(run / source, pinned(source)))
                section.update(table_evidence(selected, run / source))
            elif key in FIGURES:
                source = f"figures/{key}.png"
                png = base64.b64decode(text(selected["image/png"]), validate=True)
                if png != pinned(source):
                    raise ValueError(f"figure bytes differ from sealed notebook: {key}")
                theme_sources.append(pin(run / source, png))
                assets[source] = png
                section.update(kind="figure", path=source, caption=FIGURES[key], alt=FIGURES[key])
            else:
                raise ValueError(f"missing explicit evidence selection: {key}")
            report["sections"].append(section)
            transfers.append({"insight_id": key, "cells": [cell["id"] for cell in group],
                              "evidence": source, "evidence_sha256": inventory[source]["sha256"],
                              "original_finding_sha256": digest(original.encode()),
                              "public_section_sha256": digest(json_bytes(section))})
        assets["publication.json"] = json_bytes(report)
        assets["source-map.json"] = json_bytes({"study_id": STUDY, "source_run_id": RUN,
                                                "publication_id": publication, "insights": transfers})
        assets["verification.json"] = json_bytes({"result": "passed", "publication_id": publication,
                                                   "source_run_id": RUN, "selected_insights": len(transfers),
                                                   "checks": ["Run receipt and locked artifact hashes",
                                                              "Authoring and executed cell identity",
                                                              "Exact selected wording, typed table display and PNG bytes"]})
        assets["manifest.json"] = json_bytes({
            "study_id": STUDY, "source_run_id": RUN, "publication_id": publication,
            "created_at_utc": published_at, "source_artifacts": [*sources, *theme_sources],
            "outputs": [pin(revision / path, data) for path, data in assets.items()],
            "change": "Render selected executed notebook output. Presentation-only.",
        })
        public.append((theme, publication, revision, assets))
    if seen != set(TABLES) | set(FIGURES):
        raise ValueError("explicit evidence selection does not cover every insight")
    for _, _, revision, assets in public:
        if check:
            if {str(file.relative_to(revision)) for file in revision.rglob("*") if file.is_file()} != set(assets):
                raise ValueError(f"revision inventory differs: {revision}")
            for path, data in assets.items():
                if (revision / path).read_bytes() != data:
                    raise ValueError(f"revision bytes differ: {revision / path}")
        elif revision.exists():
            raise FileExistsError(revision)
    if not check:
        for _, _, revision, assets in public:
            revision.mkdir(parents=True, exist_ok=False)
            for path, data in assets.items():
                destination = revision / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as output:
                    output.write(data)
    return [(theme, publication, revision.relative_to(root)) for theme, publication, revision, _ in public]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-at", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for _, _, revision in project(root, args.published_at, check=args.check):
        print(revision)


if __name__ == "__main__":
    main()
