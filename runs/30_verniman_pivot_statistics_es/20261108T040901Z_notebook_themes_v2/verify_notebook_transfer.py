"""Independent saved-notebook/public-bundle transfer check; no research rerun."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re


def read(path):
    return json.loads(Path(path).read_text())


def text(value):
    return value if isinstance(value, str) else "".join(value)


def prose(value):
    value = text(value).strip()
    value = re.sub(r"^#{1,6}\s+", "", value)
    value = value.replace("**", "").replace("`", "")
    return re.sub(r"^Findings summary\.?\s*", "", value).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("publications", type=Path)
    parser.add_argument("--suffix", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    book = read(args.notebook)
    metadata = book["metadata"]["abacus"]
    cells = {}
    for cell in book["cells"]:
        meta = cell.get("metadata", {}).get("abacus", {})
        if "insight_id" in meta:
            cells.setdefault(meta["insight_id"], {})[meta["role"]] = cell
    def output(cell, mime):
        found = [out["data"][mime] for out in cell.get("outputs", []) if mime in out.get("data", {})]
        if len(found) != 1:
            raise ValueError(f"Expected one saved {mime} in {cell['id']}")
        return found[0]
    checks = []
    for theme in metadata["themes"]:
        identity = f"verniman-es-{theme['id']}-{args.suffix}"
        bundle = read(args.publications / identity / "report.json")
        report = bundle["report"]
        assert report["source"]["runId"] == args.run_id
        assert report["presentation"] == "research-paper"
        assert report["title"] == theme["title"] and report["summary"] == theme["question"]
        sections = report["sections"]
        assert [section["id"] for section in sections] == theme["insight_ids"]
        for section in sections:
            group = cells[section["id"]]
            assert section["title"] == prose(group["heading"]["source"])
            assert section["description"] == prose(group["description"]["source"])
            assert section["finding"] == prose(output(group["findings"], "text/markdown"))
            evidence = output(group["evidence"], "application/vnd.abacus.insight+json")
            if section["kind"] == "table":
                assert section["rows"] == evidence["rows"]
                assert len(section["columns"]) == len(evidence["columns"])
                for actual, expected in zip(section["columns"], evidence["columns"]):
                    assert actual["key"] == expected["key"] and actual["label"] == expected["label"]
                    fmt = expected.get("format", "text")
                    if fmt == "text":
                        assert "format" not in actual
                    else:
                        assert actual["format"] == ("number" if fmt == "integer" else fmt)
                        assert actual.get("precision", 0) == expected.get("precision", 0)
                    assert actual.get("unit") == expected.get("unit")
                assert section.get("notes", []) == evidence.get("notes", [])
                checked_values = sum(len(row) for row in section["rows"])
                visual = {"kind": "table", "cells": checked_values}
            else:
                png = base64.b64decode(text(output(group["evidence"], "image/png")))
                saved = (args.publications / identity / section["path"]).read_bytes()
                assert saved == png
                assert section["alt"] == evidence["alt"]
                assert section["caption"] == evidence["caption"]
                visual = {"kind": "figure", "bytes": len(saved), "sha256": hashlib.sha256(saved).hexdigest()}
            checks.append({"publication_id": identity, "insight_id": section["id"],
                           "narrative": "exact selected heading/description/executed findings", "evidence": visual,
                           "passed": True})
        public_text = json.dumps(bundle, ensure_ascii=False)
        for private in ("import pandas", "display(Markdown", "ABACUS_NOTEBOOK", "/Users/", "ipykernel", ".venv", "execution_count", "cell_type"):
            assert private not in public_text, (identity, private)
    assert len(checks) == len(metadata["insight_order"])
    record = {"result": "passed", "scope": "Independent selected narrative, typed table cells and exact saved PNG transfer; not scientific revalidation.",
              "notebook_sha256": hashlib.sha256(args.notebook.read_bytes()).hexdigest(),
              "themes": len(metadata["themes"]), "insights": len(checks), "checks": checks}
    with args.receipt.open("x") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"result": "passed", "themes": record["themes"], "insights": len(checks),
                      "table_cells": sum(c["evidence"].get("cells", 0) for c in checks),
                      "figures": sum(c["evidence"]["kind"] == "figure" for c in checks)}))


if __name__ == "__main__":
    main()
