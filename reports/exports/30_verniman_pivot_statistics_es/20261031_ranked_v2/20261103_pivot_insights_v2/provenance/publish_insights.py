"""Present pinned saved evidence as insight sections and a portable notebook.

No market data, research engines, aggregation, or bootstrap execution is used.
Each output is a fresh presentation revision of the selected completed run.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import string
import subprocess
import sys
from pathlib import Path

from src.insight_notebook import build_notebook, replay_notebook

STUDY = "30_verniman_pivot_statistics_es"
RUN = "20261031_ranked_v2"
ROOT = Path(__file__).resolve().parents[2]
OWNER = Path(__file__).resolve().parent
REPORT_IDS = {
    "pivot": "verniman-es-pivot-insights-20261103-v2",
    "vwap": "verniman-es-vwap-insights-20261103-v2",
}
REVISION_IDS = {
    "pivot": "20261103_pivot_insights_v2",
    "vwap": "20261103_vwap_insights_v2",
    "notebook": "20261103_insights_notebook_v2",
}
CREATED = "2026-11-03T06:00:10Z"
NOTEBOOK_NAME = "vern-pivot-cross-statistics.ipynb"


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_pinned(root, entry):
    locator = entry["path"]
    path = Path(locator)
    if path.is_absolute() or any(part in (".", "..") for part in locator.split("/")):
        raise ValueError(f"Invalid source locator: {locator}")
    target = root / path
    if not target.is_file() or target.is_symlink() or target.resolve() != target:
        raise ValueError(f"Expected contained regular source: {locator}")
    data = target.read_bytes()
    if sha(data) != entry["sha256"]:
        raise ValueError(f"Changed pinned source: {locator}")
    return data


def same_value(actual, expected):
    # Python equality alone conflates false, zero and null-adjacent selections.
    return type(actual) is type(expected) and actual == expected


def resolve_binding(section, binding):
    where = binding["where"]
    if not where or any(not isinstance(key, str) for key in where):
        raise ValueError("A binding needs explicit saved-row selectors")
    matches = [(i, row) for i, row in enumerate(section["rows"])
               if all(key in row and same_value(row[key], value) for key, value in where.items())]
    if len(matches) != 1:
        raise ValueError(f"Expected one saved row for {section['id']}: {where}; found {len(matches)}")
    index, row = matches[0]
    value = row[binding["column"]]
    fmt = binding["format"]
    precision = binding.get("precision", 0)
    if type(precision) is not int or not 0 <= precision <= 6:
        raise ValueError("Invalid precision")
    if value is None:
        rendered = "not available"
    elif isinstance(value, str) and fmt == "text":
        rendered = value
    elif type(value) in (int, float) and math.isfinite(value):
        if fmt == "percent":
            rendered = f"{value * 100:,.{precision}f}%"
        elif fmt in ("number", "integer"):
            if fmt == "integer" and value != int(value):
                raise ValueError("Integer formatting would discard a saved fraction")
            rendered = f"{value:,.{precision}f}"
        else:
            raise ValueError(f"Unsupported binding format: {fmt}")
    else:
        raise ValueError("Finding bindings must preserve text or finite saved numbers")
    return rendered, {"source_row": index, "where": where, "column": binding["column"],
                      "value": value, "rendered": rendered, "format": fmt, "precision": precision}


def compact_measure(row):
    """Shorten saved labels only; numerical cells are copied without arithmetic."""
    context = row["selection"]
    population = ""
    for prefix, label in (("Pivot-matched · RTH · ", "Pivot-matched RTH"),
                          ("VWAP-only RTH · RTH · ", "VWAP-only RTH"),
                          ("VWAP-only Globex · Globex · ", "Full Globex")):
        if context.startswith(prefix):
            context = context.removeprefix(prefix)
            population = label
            break
    parts = [part for part in context.split(" · ") if part not in ("All sections", "Both directions", "All crosses")]
    context = " · ".join(parts).replace("/pivot", "–pivot").replace("/vwap", "–VWAP").replace("_", " ")
    return " · ".join([part for part in (population, row["period"],
                         row["metric"].replace("_", " ").capitalize(), context) if part])


def compact_table(saved, evidence):
    indices = list(dict.fromkeys(binding["source_row"] for binding in evidence.values()))
    cited_optional = {binding["column"] for binding in evidence.values()} & {"median", "numerator"}
    rows = []
    for index in indices:
        row = saved["rows"][index]
        rows.append({"measure": compact_measure(row),
                     **{key: row[key] for key in ("value", "share", "denominator", "days", "unknown", "censored")},
                     **{key: row[key] for key in sorted(cited_optional)}})
    columns = [{"key": "measure", "label": "Saved measure and context"},
                        {"key": "value", "label": "Mean", "format": "number", "precision": 3},
                        {"key": "share", "label": "Share", "format": "percent", "precision": 1},
                        {"key": "denominator", "label": "Observations", "format": "number", "precision": 0},
                        {"key": "days", "label": "Days", "format": "number", "precision": 0},
                        {"key": "unknown", "label": "Unavailable", "format": "number", "precision": 0},
                        {"key": "censored", "label": "Censored", "format": "number", "precision": 0}]
    for key in sorted(cited_optional):
        columns.insert(3, {"key": key, "label": "Median" if key == "median" else "Count / sum",
                           "format": "number", "precision": 3})
    omitted = [key for key in ("value", "share") if all(row[key] is None for row in rows)]
    zero_support = [key for key in ("unknown", "censored") if all(row[key] == 0 for row in rows)]
    omitted.extend(zero_support)
    columns = [column for column in columns if column["key"] not in omitted]
    rows = [{key: value for key, value in row.items() if key not in omitted} for row in rows]
    return {"id": saved["id"], "kind": "table", "title": saved["title"], "columns": columns,
            "rows": rows,
            "notes": ["Observations and Days are the saved measure-specific support. Repeated events within a day are dependent; fewer than 30 days is sparse.",
                      "Not available differs from observed zero. Missing and censored counts can overlap. Units appear in the measure label.",
                      "Full comparisons and filters remain in Ranked statistics; the downloads below retain selected saved statistics and eligible period bounds."]
                     + (["All selected rows record zero for: " + ", ".join("unavailable observations" if key == "unknown" else "censored observations" for key in zero_support) + "."] if zero_support else [])}, indices


def prepare(root, spec, lock):
    if spec["source_run_id"] != RUN or lock["source_run_id"] != RUN:
        raise ValueError("Wrong selected saved run")
    pinned = {entry["path"]: read_pinned(root, entry) for entry in lock["artifacts"]}
    reports, maps, assets = {}, {}, {}
    for selection in spec["reports"]:
        key = selection["key"]
        if key in reports or key not in REPORT_IDS:
            raise ValueError("Duplicate or unsupported report key")
        source_id = selection["source_publication_id"]
        base = f"runs/{STUDY}/{RUN}/publications/{source_id}"
        source_path = f"{base}/publication.json"
        original = json.loads(pinned[source_path])
        if original["source"]["runId"] != RUN or original["id"] != source_id:
            raise ValueError("Source attribution mismatch")
        original_sections = {s["id"]: s for s in original["sections"]}
        expected_ids = [s["id"] for s in original["sections"] if s["kind"] == "table"]
        if [item["id"] for item in selection["insights"]] != expected_ids:
            raise ValueError("Insight inventory must preserve every saved question in order")
        report = copy.deepcopy(original)
        report.update(id=REPORT_IDS[key], publishedAt=CREATED,
                      title="Vern Pivot Cross Statistics — ES" if key == "pivot" else "Vern Pivot Cross Statistics — Globex VWAP",
                      summary=("Saved ES crossing results presented one question at a time, with a brief description, "
                               "findings summary and chart or table. Actual eligible dates are January 3, 2020–September 18, 2026. "
                               "Population, outcome horizon and missing support remain explicit. These descriptive observations "
                               "do not establish profitability."))
        scope = copy.deepcopy(original_sections["scope"])
        population = ("The pivot analysis uses 875 eligible RTH sessions matched to a single source pivot and its exact ES delivery contract. "
                      "Its VWAP comparisons use those same sessions." if key == "pivot" else
                      "The VWAP analysis keeps 1,308 eligible RTH sessions and 1,292 full-Globex sessions separate. "
                      "It does not require a matched daily pivot. Forward outcomes are RTH-only.")
        scope["body"] = (population + " Actual eligible dates span January 3, 2020–September 18, 2026; "
                         "requested coverage through October 30 extends beyond retained market data.\n\n"
                         "Crossings are actual strict-side transitions on completed three-minute closes. "
                         "EMA6 already on one side, a touch, or an equal value is a different state. "
                         "VWAP uses one-minute HLC3 and volume from 18:00 New York; the EMA20/50 cloud uses five-minute closes.\n\n"
                         "Each insight describes its named saved baseline, then shows a chart or compact supporting rows. "
                         "The companion notebook uses the same prose and evidence. Ranked statistics retains the fuller tables and filters. "
                         "Selected CSVs and eligible-period bounds are below. Historical pivot availability remains unverified; "
                         "eligibility is retrospective and conditional slices are exploratory. Fills, costs and profitability were not tested.")
        sections, bindings, transferred = [scope], [], []
        assets[key] = {}
        for item in selection["insights"]:
            saved = original_sections[item["id"]]
            substitutions, evidence = {}, {}
            for name, binding in item["bindings"].items():
                substitutions[name], evidence[name] = resolve_binding(saved, binding)
            fields = [field for _, field, _, _ in string.Formatter().parse(item["finding_template"]) if field]
            if set(fields) != set(substitutions):
                raise ValueError(f"Unbound or unused finding value in {key}/{item['id']}")
            finding = item["finding_template"].format(**substitutions)
            if not 0 < len(finding) <= 2000 or not 0 < len(item["description"]) <= 1000:
                raise ValueError("Insight prose exceeds the publication contract")
            if item.get("figure_section_id"):
                section = copy.deepcopy(original_sections[item["figure_section_id"]])
                section["id"] = item["id"]
                section["caption"] = section.get("caption", "") + (" Full supporting tables remain in the earlier Ranked statistics reports; the downloads below contain selected saved statistics and period bounds.")
                assets[key][section["path"]] = pinned[f"{base}/{section['path']}"]
                transferred.append({"section_id": item["id"], "source_section_id": item["figure_section_id"],
                                    "asset": section["path"], "sha256": sha(assets[key][section["path"]])})
            else:
                section, indices = compact_table(saved, evidence)
                transferred.append({"section_id": item["id"], "source_section_id": item["id"],
                                    "source_rows": indices, "output_rows": section["rows"],
                                    "operation": "Explicit saved-row/column selection, shortened text labels, unchanged numerical values",
                                    "saved_source_rows_sha256": sha(json_bytes([saved["rows"][i] for i in indices]))})
            section.update(title=item["title"], description=item["description"], finding=finding)
            sections.append(section)
            bindings.append({"section_id": item["id"], "source_section_id": item["id"], "bindings": evidence,
                             "finding": finding, "template": item["finding_template"]})
        sections.append(copy.deepcopy(original_sections["limits"]))
        report["sections"] = sections
        for download in report.get("downloads", []):
            assets[key][download["path"]] = pinned[f"{base}/{download['path']}"]
        reports[key] = report
        maps[key] = {"schema_version": "abacus.study30.insight-presentation/v1", "study_id": STUDY,
                     "source_run_id": RUN, "publication_id": report["id"],
                     "source_publication": {"path": source_path, "sha256": sha(pinned[source_path])},
                     "source_row_base": 0, "findings": bindings, "transfers": transferred,
                     "scope": "Formatting and exact saved-cell transfer only; no new research interpretation or calculations."}
    if set(reports) != {"pivot", "vwap"}:
        raise ValueError("Both populations must be presented separately")
    notebook = build_notebook(reports, assets, source_run_id=RUN)
    replayed = replay_notebook(notebook)
    return reports, maps, assets, notebook, replayed


def revision_root(root, key):
    return root / "reports" / "exports" / STUDY / RUN / REVISION_IDS[key]


def write_files(destination, files):
    destination.mkdir(parents=True, exist_ok=False)
    for relative, data in files.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def generate(root=ROOT, *, check=False):
    spec_path = OWNER / "insight-spec.json"
    lock_path = OWNER / "insight-inputs.lock.json"
    spec = json.loads(spec_path.read_bytes())
    lock = json.loads(lock_path.read_bytes())
    reports, maps, assets, notebook, replayed = prepare(root, spec, lock)
    producer_paths = [Path(__file__), OWNER / "src/insight_notebook.py", spec_path, lock_path,
                      root / "uv.lock", root / "apps/narada/contracts/report-1.1.schema.json",
                      root / "apps/narada/types/report.ts", root / "apps/narada/src/components/report-sections.tsx",
                      root / "apps/narada/src/components/report-table.tsx"]
    producer = {f"provenance/{path.name}": path.read_bytes() for path in producer_paths}
    all_files = {}
    for key, report in reports.items():
        files = {"publication.json": json_bytes(report), "source-map.json": json_bytes(maps[key]),
                 **assets[key], **producer}
        files["verification.json"] = json_bytes({
            "checks": [{"name": "Pinned saved source bytes", "passed": True},
                       {"name": "Unique exact typed saved-row bindings for every summary", "passed": True},
                       {"name": "Unchanged selected numerical cells and raster/CSV bytes", "passed": True},
                       {"name": "Portable notebook code and rich-output replay", "passed": True}],
            "notebook_code_cells_replayed": replayed,
            "limitations": "Presentation transfer checks only; no numerical research rerun, Jupyter kernel execution or hosted deployment."})
        all_files[key] = files
    all_files["notebook"] = {NOTEBOOK_NAME: json_bytes(notebook), **producer}
    if check:
        for key, files in all_files.items():
            destination = revision_root(root, key)
            for name, expected in files.items():
                if (destination / name).read_bytes() != expected:
                    raise ValueError(f"Changed presentation output: {destination / name}")
            manifest = json.loads((destination / "manifest.json").read_bytes())
            for output in manifest["outputs"]:
                read_pinned(root, output)
        return {"result": "passed", "insights": sum(len(m["findings"]) for m in maps.values()),
                "notebook_code_cells_replayed": replayed, "research_reexecuted": False}
    destinations = [revision_root(root, key) for key in all_files]
    if any(path.exists() for path in destinations):
        raise FileExistsError("Presentation revisions already exist; use --check or create new explicit revision IDs")
    git_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    for key, files in all_files.items():
        destination = revision_root(root, key)
        relative = destination.relative_to(root)
        manifest = {"study_id": STUDY, "source_run_id": RUN, "revision_id": REVISION_IDS[key],
                    "created_at_utc": CREATED, "change": "One question per insight using existing saved results; no research recalculation.",
                    "source_artifacts": lock["artifacts"],
                    "renderer": {"git_revision": git_revision, "dirty_source": "Exact producer bytes retained under provenance/",
                                 "python": sys.version, "platform": platform.platform(),
                                 "command": "python3 studies/30_verniman_pivot_statistics_es/publish_insights.py"},
                    "outputs": [{"path": (relative / name).as_posix(), "sha256": sha(data)} for name, data in files.items()]}
        if key in reports:
            manifest["publication_id"] = reports[key]["id"]
        files["manifest.json"] = json_bytes(manifest)
        write_files(destination, files)
    return {"result": "prepared", "insights": sum(len(m["findings"]) for m in maps.values()),
            "notebook_code_cells_replayed": replayed,
            "revisions": [str(path.relative_to(root)) for path in destinations]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only replay and byte comparison of prepared revisions")
    args = parser.parse_args()
    print(json.dumps(generate(check=args.check), indent=2))


if __name__ == "__main__":
    main()
