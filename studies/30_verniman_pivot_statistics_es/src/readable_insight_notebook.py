"""Readable notebook cells backed by explicit sibling presentation artifacts.

Saved report JSON, view-helper code and raster files stay beside the notebook.
Cell source contains ordinary display calls, without embedded data or images.
"""

from __future__ import annotations

import ast
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re


_HELPER_SOURCE = r'''"""Display the sibling saved reports; no market-data calculations."""
import base64
from decimal import Decimal, ROUND_HALF_UP, localcontext
from html import escape
import json
import math
from pathlib import Path

_FOLDER = Path(__file__).resolve().parent


def _saved_scalar(value, column):
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return "true" if value else "false"
    if not isinstance(value, (int, float)):
        return str(value)
    if not math.isfinite(value):
        return "Not available"
    precision = column.get("precision", 2)
    with localcontext() as context:
        context.prec = 400
        decimal = Decimal(str(value))
        if column.get("format") == "percent":
            decimal *= 100
        rounded = decimal.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
    return format(rounded, f",.{precision}f") + ("%" if column.get("format") == "percent" else "")


def _saved_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


class SavedInsightView:
    def __init__(self, data):
        self.data = data

    def _repr_mimebundle_(self, include=None, exclude=None):
        return {key: value for key, value in self.data.items()
                if (include is None or key in include) and (exclude is None or key not in exclude)}


def render_insight(payload, report_key, insight_id, read_asset, selections=None):
    """Render exact saved cells or image bytes; no aggregation or estimation."""
    report = payload["reports"][report_key]
    matches = [section for section in report["sections"] if section["id"] == insight_id]
    if len(matches) != 1:
        raise ValueError("Expected one saved insight: " + insight_id)
    section = matches[0]
    if section["kind"] == "figure":
        if selections is not None:
            raise ValueError("A saved figure has no table selections.")
        relative = payload["assets"][report_key][section["path"]]
        encoded = base64.b64encode(read_asset(relative)).decode("ascii")
        mime = "image/" + ("jpeg" if section["path"].lower().endswith((".jpg", ".jpeg"))
                            else section["path"].rsplit(".", 1)[1].lower())
        caption = section.get("caption", "")
        markup = ('<figure><img style="display:block;max-width:100%;height:auto" src="data:'
                  + mime + ';base64,' + encoded + '" alt="' + escape(section["alt"], quote=True)
                  + '"><figcaption>' + escape(caption) + '</figcaption></figure>')
        return SavedInsightView({"text/html": markup, mime: encoded,
                                 "text/plain": section["title"] + ("\n" + caption if caption else "")})
    if section["kind"] != "table":
        raise ValueError("Expected a saved chart or table.")
    filters = section.get("rowFilters", [])
    if selections is None:
        selections = {item["key"]: item["defaultValue"] for item in filters if "defaultValue" in item}
    allowed = {item["key"] for item in filters}
    if set(selections) - allowed:
        raise ValueError("Unknown saved row filter.")
    for key, value in selections.items():
        if not any(_saved_equal(row.get(key), value) for row in section["rows"]):
            raise ValueError("Unavailable saved row-filter value.")
    matching = [row for row in section["rows"]
                if all(_saved_equal(row.get(key), value) for key, value in selections.items())]
    rows = matching[:100]
    labels = {item["key"]: item["label"] for item in filters}
    active = "; ".join(labels[key] + ": " + _saved_scalar(value, {}) for key, value in selections.items())
    context = ("Showing " + str(len(rows)) + " of " + str(len(matching))
               + " matching saved rows; " + str(len(section["rows"])) + " saved rows in this table.")
    if active:
        context += " Selections: " + active + "."
    context += " This is a saved evidence selection, not the complete research dataset."
    header = "".join('<th scope="col">' + escape(column["label"])
                     + ("<br>" + escape(column["unit"]) if column.get("unit") else "") + "</th>"
                     for column in section["columns"])
    body = "".join("<tr>" + "".join("<td>" + escape(_saved_scalar(row.get(column["key"]), column))
                                     + "</td>" for column in section["columns"]) + "</tr>" for row in rows)
    if not rows:
        body = '<tr><td colspan="' + str(len(section["columns"])) + '">No saved rows match these selections.</td></tr>'
    notes = "".join("<li>" + escape(note) + "</li>" for note in section.get("notes", []))
    markup = ('<div class="saved-insight-evidence"><p>' + escape(context)
              + '</p><div role="region" tabindex="0" aria-label="' + escape(section["title"], quote=True)
              + '" style="overflow-x:auto"><table style="border-collapse:collapse">'
              + '<caption style="text-align:left">' + escape(section["title"])
              + '</caption><thead><tr>' + header + '</tr></thead><tbody>' + body
              + '</tbody></table></div>' + ('<ul>' + notes + '</ul>' if notes else '') + '</div>')
    plain = context + "\n" + " | ".join(column["label"] for column in section["columns"])
    for row in rows:
        plain += "\n" + " | ".join(_saved_scalar(row.get(column["key"]), column) for column in section["columns"])
    return SavedInsightView({"text/html": markup, "text/plain": plain})


def _read_asset(relative):
    path = (_FOLDER / relative).resolve()
    if not path.is_relative_to(_FOLDER / "assets"):
        raise ValueError("Saved figure must stay inside the sibling assets directory.")
    return path.read_bytes()


def show_insight(report_key, insight_id, selections=None):
    """Select saved evidence from this folder and return its rich display."""
    payload = json.loads((_FOLDER / "saved-reports.json").read_text(encoding="utf-8"))
    return render_insight(payload, report_key, insight_id, _read_asset, selections)
'''


_SETUP_SOURCE = '''# Load the saved evidence viewer beside this notebook.
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

_relative_folders = (
    "work/30_verniman_pivot_statistics_es/notebook",
    "reports/exports/30_verniman_pivot_statistics_es/20261031_ranked_v2/20261103_readable_notebook_v3",
)
_start = Path.cwd().resolve()
_candidates = []
for _ancestor in (_start, *_start.parents):
    _candidates.extend([_ancestor, *(_ancestor / name for name in _relative_folders)])
_folder = next((folder for folder in _candidates
                if (folder / "insight_view.py").is_file()
                and (folder / "saved-reports.json").is_file()), None)
if _folder is None:
    raise FileNotFoundError("Keep insight_view.py, saved-reports.json and assets beside the notebook; start the kernel in that folder.")
_spec = spec_from_file_location("vern_pivot_insight_view", _folder / "insight_view.py")
_view = module_from_spec(_spec)
_spec.loader.exec_module(_view)
show_insight = _view.show_insight
'''


def view_helper_source() -> str:
    """Return the standalone sibling helper; it needs only standard Python."""
    return _HELPER_SOURCE


def saved_payload(reports: dict[str, dict], assets: dict[str, dict[str, bytes]]) -> dict:
    """Return saved JSON content and explicit relative asset locators only."""
    if not reports:
        raise ValueError("At least one explicitly selected report is required.")
    selected_assets: dict[str, dict[str, str]] = {}
    for key, report in reports.items():
        if not re.fullmatch(r"[a-z0-9-]{1,20}", key):
            raise ValueError("Invalid report key.")
        selected_assets[key] = {}
        seen: set[str] = set()
        for section in report["sections"]:
            identity = section["id"]
            if not re.fullmatch(r"[a-z0-9-]{1,32}", identity) or identity in seen:
                raise ValueError("Section identities must be valid and unique.")
            seen.add(identity)
            if section["kind"] not in {"table", "figure"}:
                continue
            if not section.get("description", "").strip() or not section.get("finding", "").strip():
                raise ValueError("Every insight needs description and findings summary.")
            if section["kind"] == "figure":
                path = section["path"]
                parts = PurePosixPath(path).parts
                if (not path.startswith("figures/") or "\\" in path or PurePosixPath(path).is_absolute()
                        or any(part in {".", ".."} for part in parts) or str(PurePosixPath(path)) != path):
                    raise ValueError("Saved figure paths must stay inside figures/.")
                image = assets.get(key, {}).get(path)
                if not isinstance(image, bytes) or not image:
                    raise ValueError("Missing exact saved figure bytes: " + path)
                selected_assets[key][path] = "assets/" + key + "/" + path
    # Round-trip retains scalar types and rejects nonfinite numbers before output.
    return json.loads(json.dumps({"reports": reports, "assets": selected_assets}, ensure_ascii=False, allow_nan=False))


def _markdown(cell_id: str, source: str, metadata: dict | None = None) -> dict:
    return {"cell_type": "markdown", "id": cell_id, "metadata": metadata or {}, "source": source.splitlines(keepends=True)}


def _code(cell_id: str, source: str, count: int, outputs: list, metadata: dict | None = None) -> dict:
    return {"cell_type": "code", "id": cell_id, "metadata": metadata or {},
            "source": source.splitlines(keepends=True), "execution_count": count, "outputs": outputs}


def _run_cell(cell: dict, namespace: dict):
    """Execute only trusted generated display cells."""
    tree = ast.parse("".join(cell["source"]))
    final = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    exec(compile(tree, "<readable-insight-notebook>", "exec"), namespace)
    return eval(compile(ast.Expression(final.value), "<readable-insight-notebook>", "eval"), namespace) if final else None


def replay_readable_notebook(notebook: dict, folder: str | Path) -> int:
    """Replay trusted display cells and require exact cached MIME parity.

    The target is an explicit folder holding the helper, JSON and selected
    assets. This is Python replay, not a notebook frontend/kernel check.
    """
    if notebook.get("nbformat") != 4 or notebook.get("nbformat_minor") != 5:
        raise ValueError("Expected notebook format 4.5.")
    previous = Path.cwd()
    namespace: dict = {"__name__": "__main__"}
    seen: set[str] = set()
    count = 0
    try:
        os.chdir(Path(folder).resolve())
        for cell in notebook["cells"]:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cell.get("id", "")) or cell["id"] in seen:
                raise ValueError("Notebook cell IDs must be valid and unique.")
            seen.add(cell["id"])
            if cell["cell_type"] == "markdown":
                continue
            if cell["cell_type"] != "code":
                raise ValueError("Unexpected notebook cell type.")
            count += 1
            value = _run_cell(cell, namespace)
            expected = [] if value is None else [{"output_type": "execute_result", "execution_count": count,
                                                  "data": value._repr_mimebundle_(), "metadata": {}}]
            if cell.get("execution_count") != count or cell.get("outputs") != expected:
                raise ValueError("Cached notebook output differs from replay: " + cell["id"])
    finally:
        os.chdir(previous)
    return count


def build_readable_notebook(reports: dict[str, dict], assets: dict[str, dict[str, bytes]], *, source_run_id: str) -> dict:
    """Build readable cells; the caller writes JSON, helper and images beside it."""
    payload = saved_payload(reports, assets)
    if any(report.get("source", {}).get("runId") != source_run_id for report in reports.values()):
        raise ValueError("Report source-run identity mismatch.")
    namespace = {"__file__": "insight_view.py"}
    exec(compile(_HELPER_SOURCE, "insight_view.py", "exec"), namespace)
    asset_bytes = {relative: assets[key][path]
                   for key, paths in payload["assets"].items() for path, relative in paths.items()}
    cells = [_markdown("notebook-introduction", "# Vern Pivot Cross Statistics — ES\n\n"
                       "Each insight has a heading, brief description and findings summary, followed by its saved chart or table. "
                       "The same selected results appear on Narada.\n\n"
                       "Open this file in a notebook editor with a Python 3 kernel. Each question has its own Markdown cell "
                       "and a short, visible Python display cell. Outputs are already included. Run the setup cell, then any insight, "
                       "or run all cells to redisplay the saved evidence. Keep `insight_view.py`, `saved-reports.json` and `assets/` "
                       "in this folder. Redisplaying uses standard Python and does not execute the research calculations.\n\n"
                       "Eligible samples span January 3, 2020–September 18, 2026: 875 pivot-matched RTH, 1,308 VWAP-only RTH "
                       "and 1,292 full-Globex sessions. Requested coverage extends through October 30, 2026. "
                       "Historical pivot availability is unverified, eligibility is retrospective and conditional views are exploratory. "
                       "Forward outcomes are RTH-only; fills, costs and profitability were not tested.\n\n"
                       f"Saved source run: `{html.escape(source_run_id)}`. Each summary describes its stated saved baseline."),
             _code("saved-presentation-setup", _SETUP_SOURCE, 1, [], {"abacus": {"role": "setup"}})]
    count = 1
    for key, report in reports.items():
        scope = next((s["body"] for s in report["sections"] if s.get("id") == "scope"), report.get("summary", ""))
        cells.append(_markdown(key + "-introduction", "# " + html.escape(report["title"]) + "\n\n" + html.escape(scope),
                               {"abacus": {"report_key": key, "publication_id": report["id"], "source_run_id": source_run_id}}))
        for section in report["sections"]:
            if section["kind"] not in {"table", "figure"}:
                continue
            identity = {"report_key": key, "publication_id": report["id"], "source_run_id": source_run_id,
                        "insight_id": section["id"], "evidence_kind": section["kind"]}
            cells.append(_markdown(key + "-" + section["id"] + "-heading",
                                   "## " + html.escape(section["title"]) + "\n\n" + html.escape(section["description"])
                                   + "\n\n**Findings summary.** " + html.escape(section["finding"]),
                                   {"abacus": {**identity, "role": "narrative"}}))
            count += 1
            view = namespace["render_insight"](payload, key, section["id"], asset_bytes.__getitem__)
            outputs = [{"output_type": "execute_result", "execution_count": count,
                        "data": view._repr_mimebundle_(), "metadata": {}}]
            cells.append(_code(key + "-" + section["id"] + "-evidence",
                               f"show_insight({key!r}, {section['id']!r})\n", count, outputs,
                               {"abacus": {**identity, "role": "evidence"}}))
        limits = next((s["body"] for s in report["sections"] if s.get("id") == "limits"), "")
        if limits:
            cells.append(_markdown(key + "-evidence-limits", "## Evidence qualifications\n\n" + html.escape(limits)))
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python", "file_extension": ".py", "mimetype": "text/x-python"},
                         "abacus": {"format_version": "abacus.study30.readable-insight-notebook/v1",
                                    "presentation_only": True, "source_run_id": source_run_id,
                                    "saved_payload_sha256": digest, "companion_files": ["insight_view.py", "saved-reports.json", "assets/"],
                                    "publication_ids": {key: report["id"] for key, report in reports.items()}}}}
