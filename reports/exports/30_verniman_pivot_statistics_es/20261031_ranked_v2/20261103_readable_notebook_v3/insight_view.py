"""Display the sibling saved reports; no market-data calculations."""
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
