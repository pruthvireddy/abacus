"""Check publication transfer and selected source hashes without recalculation."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
source_map = json.loads((HERE / "source-map.json").read_text())
report = json.loads((HERE / "publication.json").read_text())
sections = {s["id"]: s for s in report["sections"]}
assert report["source"]["runId"] == source_map["source_run_id"]
assert report["id"] == source_map["publication_id"]
for artifact in source_map["source_artifacts"]:
    assert hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"], artifact["path"]

run = ROOT / "runs" / source_map["study_id"] / source_map["source_run_id"]
manifest = json.loads((run / "manifest.json").read_text())
sealed = ({a["path"]: a["sha256"] for a in manifest["artifact_hashes"]} if "artifact_hashes" in manifest
          else {p: a["sha256"] for p, a in manifest["artifacts"].items()})
for artifact in source_map["source_artifacts"]:
    relative = str((ROOT / artifact["path"]).relative_to(run))
    if relative in sealed:
        assert artifact["sha256"] == sealed[relative], relative

checked = set()
for binding in source_map["numeric_bindings"]:
    source = ROOT / binding["source"]
    if "metric_id" in binding:
        values = json.loads(source.read_text())
        matches = [m for m in values if m["id"] == binding["metric_id"]]
        assert len(matches) == 1
        saved = matches[0][binding["field"]]
        displayed = sections[binding["section_id"]]["items"][binding["item"]]["value"]
        identity = (binding["section_id"], "item", binding["item"])
        item = sections[binding["section_id"]]["items"][binding["item"]]
        assert item["format"] == "percent" and item["precision"] == 1
        note = item["note"]
        m = matches[0]
        assert f"{m['numerator']:,} / {m['denominator']:,}" in note
        assert f"{m['ci_95'][0]:.1%}–{m['ci_95'][1]:.1%}" in note
    else:
        with source.open(newline="") as stream:
            matches = [r for r in csv.DictReader(stream) if all(r[k] == v for k, v in binding["selector"].items())]
        assert len(matches) == 1
        saved = None if matches[0][binding["field"]] == "" else float(matches[0][binding["field"]])
        displayed = sections[binding["section_id"]]["rows"][binding["row"]][binding["key"]]
        identity = (binding["section_id"], binding["row"], binding["key"])
    assert displayed == (None if saved is None else saved * binding["multiplier"]), binding
    checked.add(identity)

for section in report["sections"]:
    if section["kind"] == "table":
        for index, row in enumerate(section["rows"]):
            for key, value in row.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert (section["id"], index, key) in checked, (section["id"], index, key)
    if section["kind"] == "metrics":
        for index, item in enumerate(section["items"]):
            assert (section["id"], "item", index) in checked

if source_map.get("figures"):
    charts = {r["chart_id"]: r for r in csv.DictReader((run / "tables/charts.csv").open(newline=""))}
    captures = {r["file"]: r for r in json.loads((run / "capture-log.json").read_text())}
    for mapping in source_map["figures"]:
        chart = charts[mapping["chart_id"]]
        assert (HERE / mapping["output"]).read_bytes() == (ROOT / mapping["source"]).read_bytes()
        assert hashlib.sha256((HERE / mapping["output"]).read_bytes()).hexdigest() == chart["sha256"]
        assert captures[Path(mapping["source"]).name]["seconds"] == mapping["media_seconds"]
        caption = sections[mapping["section_id"]]["caption"]
        assert chart["timestamp"] in caption and chart["source_url"] in caption
        assert chart["visible_observation"] in caption and chart["interpretive_limit"] in caption
    claims = {r["claim_id"]: r for r in csv.DictReader((run / "tables/claims.csv").open(newline=""))}
    assert len(sections["claim-ledger"]["rows"]) == len(source_map["table"]["claim_ids"])
    for row, id_ in zip(sections["claim-ledger"]["rows"], source_map["table"]["claim_ids"]):
        assert row == {"claim": f"{id_} · {claims[id_]['claim_summary']}",
                       "attribution": claims[id_]["attribution"].replace("_", " "),
                       "status": claims[id_]["evidence_status"].replace("_", " "),
                       "qualification": claims[id_]["qualification"]}

if source_map.get("figure"):
    original = (ROOT / source_map["figure"]["source"]).read_text()
    expected = original.replace("width='900' height='250' viewBox='0 0 900 250'", "width='960' height='250' viewBox='0 0 960 250'")
    expected = expected.replace("<rect width='900' height='250'", "<rect width='960' height='250'")
    assert (HERE / "provenance/barrier-outcomes.svg").read_text() == expected
    png = (HERE / source_map["figure"]["output"]).read_bytes()
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    assert int.from_bytes(png[16:20], "big") == 1920 and int.from_bytes(png[20:24], "big") == 500

# Reject private paths and authoring placeholders in reader-facing content.
public_text = json.dumps(report, ensure_ascii=False)
for token in ["/Users/", "reports/exports/", "runs/", "work/", "data/research/", "<new-", "<study-", "TODO", "placeholder"]:
    assert token not in public_text, token
result = {"study_id": source_map["study_id"], "source_run_id": source_map["source_run_id"],
          "source_hashes": "passed", "sealed_manifest_identity": "passed for recorded consumed artifacts",
          "numeric_values_checked": len(checked), "selected_figures_checked": len(source_map.get("figures", [])) + int(bool(source_map.get("figure"))),
          "claim_rows_checked": len(source_map.get("table", {}).get("claim_ids", [])),
          "private_paths_and_placeholders": "absent", "research_recalculation": "not performed"}
(HERE / "content-verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
