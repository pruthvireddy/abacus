"""Portable notebook presentation of explicitly supplied, already saved evidence.

This module does not load market data, calculate statistics, or write artifacts.
The notebook embeds its selected report content and exact raster bytes, so a
fresh Python kernel can redisplay it using only the standard library.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import html
import json
import re
import zlib


_RUNTIME = r'''
from decimal import Decimal, ROUND_HALF_UP, localcontext
from html import escape
import math

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

def show_insight(report_key, insight_id, selections=None):
    """Select and display saved evidence; selections never calculate a statistic."""
    report = _saved_payload["reports"][report_key]
    matches = [section for section in report["sections"] if section["id"] == insight_id]
    if len(matches) != 1:
        raise ValueError("Expected one saved insight: " + insight_id)
    section = matches[0]
    if section["kind"] == "figure":
        if selections is not None:
            raise ValueError("A saved figure has no table selections.")
        encoded = _saved_payload["assets"][report_key][section["path"]]
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
'''


def _markdown(cell_id: str, source: str, metadata: dict | None = None) -> dict:
    return {"cell_type": "markdown", "id": cell_id, "metadata": metadata or {}, "source": source.splitlines(keepends=True)}


def _code(cell_id: str, source: str, count: int, outputs: list, metadata: dict | None = None) -> dict:
    return {"cell_type": "code", "id": cell_id,
            "metadata": {"jupyter": {"source_hidden": True}, "collapsed": True,
                         "tags": ["hide-input"], **(metadata or {})},
            "source": source.splitlines(keepends=True), "execution_count": count, "outputs": outputs}


def _run_cell(cell: dict, namespace: dict):
    """Replay only trusted notebook cells produced by this module."""
    tree = ast.parse("".join(cell["source"]))
    final = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    exec(compile(tree, "<saved-insight-notebook>", "exec"), namespace)
    return eval(compile(ast.Expression(final.value), "<saved-insight-notebook>", "eval"), namespace) if final else None


def replay_notebook(notebook: dict) -> int:
    """Replay a trusted generated notebook and require exact cached MIME parity.

    This is standard-library Python execution and output comparison, not a
    Jupyter-kernel or notebook-frontend integration check.
    """
    if notebook.get("nbformat") != 4 or notebook.get("nbformat_minor") != 5:
        raise ValueError("Expected notebook format 4.5.")
    namespace: dict = {"__name__": "__main__"}
    seen: set[str] = set()
    count = 0
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
    return count


def build_notebook(reports: dict[str, dict], assets: dict[str, dict[str, bytes]], *, source_run_id: str) -> dict:
    """Build one portable notebook using the exact supplied Narada presentations."""
    if not reports:
        raise ValueError("At least one explicitly selected report is required.")
    selected_assets: dict[str, dict[str, str]] = {}
    for key, report in reports.items():
        if not re.fullmatch(r"[a-z0-9-]{1,20}", key) or report.get("source", {}).get("runId") != source_run_id:
            raise ValueError("Report key/source-run identity mismatch.")
        seen: set[str] = set()
        selected_assets[key] = {}
        for section in report["sections"]:
            if section["id"] in seen:
                raise ValueError("Duplicate section identity.")
            seen.add(section["id"])
            if section["kind"] not in {"table", "figure"}:
                continue
            if not section.get("description", "").strip() or not section.get("finding", "").strip():
                raise ValueError("Every insight needs description and findings summary.")
            if section["kind"] == "figure":
                image = assets.get(key, {}).get(section["path"])
                if not isinstance(image, bytes) or not image:
                    raise ValueError("Missing exact saved figure bytes: " + section["path"])
                selected_assets[key][section["path"]] = base64.b64encode(image).decode("ascii")
    payload = json.dumps({"reports": reports, "assets": selected_assets}, ensure_ascii=False,
                         allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    compressed = base64.b64encode(zlib.compress(payload, level=9)).decode("ascii")
    setup = ('# Embedded saved presentation only: no market-data reads or statistical calculations.\n'
             'import base64 as _base64, hashlib as _hashlib, json as _json, zlib as _zlib\n'
             f'_saved_bytes = _zlib.decompress(_base64.b64decode({compressed!r}))\n'
             f'if _hashlib.sha256(_saved_bytes).hexdigest() != {digest!r}:\n'
             '    raise ValueError("Embedded saved presentation hash mismatch.")\n'
             '_saved_payload = _json.loads(_saved_bytes)\n' + _RUNTIME)
    cells = [_markdown("notebook-introduction", "# Vern Pivot Cross Statistics — ES\n\n"
                       "Each insight presents its question, a brief description and findings summary, then a saved chart or table. "
                       "The notebook and Narada page use the same selected results.\n\n"
                       "**How to use:** open this file in Jupyter with a Python 3 kernel. All outputs are already included. "
                       "Run all cells from a fresh kernel to redisplay the embedded evidence; no Abacus checkout, market data, "
                       "network access or extra Python packages are required. Code is collapsed to keep the reading order clear. "
                       "Compact tables contain the selected saved rows cited in each summary. "
                       "The earlier Ranked statistics reports retain the fuller saved comparisons and filters. "
                       "Redisplaying this notebook never recalculates a statistic.\n\n"
                       "**Evidence context:** the selected eligible samples span January 3, 2020–September 18, 2026: "
                       "875 pivot-matched RTH, 1,308 VWAP-only RTH and 1,292 full-Globex sessions. "
                       "Requested coverage extends through October 30, 2026; later requested dates are uncovered. "
                       "Historical pivot availability remains unverified, eligibility is retrospective, and conditional views are exploratory. "
                       "Forward outcomes are RTH-only; fills, costs and profitability were not tested.\n\n"
                       f"**Saved source run:** `{html.escape(source_run_id)}`. The summaries describe their stated saved baselines "
                       "and do not change when a different table selection is displayed."),
             _code("saved-presentation-setup", setup, 1, [])]
    namespace: dict = {"__name__": "__main__"}
    _run_cell(cells[1], namespace)
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
                                   "## " + html.escape(section["title"]) + "\n\n"
                                   + html.escape(section["description"]) + "\n\n**Findings summary.** "
                                   + html.escape(section["finding"]), {"abacus": {**identity, "role": "narrative"}}))
            count += 1
            source = f"show_insight({key!r}, {section['id']!r})\n"
            view = namespace["show_insight"](key, section["id"])
            outputs = [{"output_type": "execute_result", "execution_count": count,
                        "data": view._repr_mimebundle_(), "metadata": {}}]
            cells.append(_code(key + "-" + section["id"] + "-evidence", source, count, outputs,
                               {"abacus": {**identity, "role": "evidence"}}))
        limits = next((s["body"] for s in report["sections"] if s.get("id") == "limits"), "")
        if limits:
            cells.append(_markdown(key + "-evidence-limits", "## Evidence qualifications\n\n" + html.escape(limits)))
    notebook = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
                "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                             "language_info": {"name": "python", "file_extension": ".py", "mimetype": "text/x-python"},
                             "abacus": {"format_version": "abacus.study30.insight-notebook/v1", "presentation_only": True,
                                        "source_run_id": source_run_id, "embedded_payload_sha256": digest,
                                        "publication_ids": {key: report["id"] for key, report in reports.items()}}}}
    replay_notebook(notebook)
    return notebook
