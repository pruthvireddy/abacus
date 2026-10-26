"""Project explicitly selected saved CSV cells for presentation.

Study authors supply the columns, row predicates, section ID, and source path
used in bindings. This module does not discover evidence or calculate results.
"""

import csv
import math
from pathlib import Path


def _transfer(raw, column, scale, context):
    if raw == "":
        return None
    if column.get("format"):
        try:
            value = float(raw) * scale
        except ValueError as error:
            raise ValueError(f"{context}: invalid numeric value {raw!r}") from error
        if not math.isfinite(value):
            raise ValueError(f"{context}: numeric value must be finite ({raw!r}, scale={scale!r})")
        return value
    if raw in ["True", "False"]:
        return raw == "True"
    if column["key"] in ["metric_id", "metric_id_departure", "metric_id_touch"]:
        return raw
    return raw.replace("_", " ")


def project_table(path, *, columns, where, section, source):
    """Return projected rows and the existing per-cell source bindings.

    ``columns`` is an authored ordered list of ``column`` definitions and
    explicit ``scale`` values. ``where`` matches original CSV strings using
    AND; an empty mapping selects all rows. ``source`` is the caller's
    workspace-relative source path. Data row numbers are assigned before
    filtering, and output row numbers start at zero for this section.
    """
    path = Path(path)
    with path.open() as handle:
        saved_rows = list(csv.DictReader(handle))
    chosen = [
        (index, row)
        for index, row in enumerate(saved_rows, 1)
        if all(row[key] in values for key, values in where.items())
    ]
    if not chosen or len(chosen) > 100:
        raise ValueError(f"Section {section!r}, {source}: expected 1 to 100 selected rows; got {len(chosen)}")

    output = []
    bindings = []
    for source_row, row in chosen:
        target = {}
        for field in columns:
            column = field["column"]
            key = column["key"]
            context = f"Section {section!r}, {source}, data row {source_row}, column {key!r}"
            target[key] = _transfer(row[key], column, field["scale"], context)
            bindings.append({
                "section": section,
                "output_row": len(output),
                "column": key,
                "source": source,
                "data_row_1_based": source_row,
                "source_column": key,
                "source_raw": row[key],
                "scale": field["scale"],
                "value": target[key],
            })
        output.append(target)
    return output, bindings
