"""Read saved research tables only; no numerical producer or estimator imports."""
from datetime import datetime,timezone
from pathlib import Path
import csv,hashlib,json,platform,sys
HERE=Path(__file__).resolve().parent
STAGE=HERE.parents[1]
def record(path):
    return {"path":str(path),"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
def read(name, predicate):
    path=STAGE/"tables"/name
    with path.open(newline="") as f:
        return [dict(row,source_artifact="tables/"+name,data_row=i,csv_line=i+1) for i,row in enumerate(csv.DictReader(f),1) if predicate(row)]
def main():
    receipt=json.loads((HERE/"interpretation-review-before-v2.json").read_text())
    for item in receipt["pinned_sources_and_tables"]:
        assert record(Path(item["path"]))==item,item["path"]
    inventory=json.loads((STAGE/"provenance/source-inventory.json").read_text())
    for item in inventory["sources"]:
        for path in (STAGE/item["snapshot_path"],STAGE.parents[2]/item["workspace_path"]):
            assert record(path)["sha256"]==item["sha256"],str(path)
    h15=lambda r:r["horizon"]=="15" and r["support"]=="all"
    fields={
      "primary_and_side_h15":read("S1-T02_horizon_scorecard.csv",h15),
      "equal_active_scorecards":read("S1-T02_horizon_scorecard.csv",lambda r:r["direction"]=="All" and r["support"]=="all" and (r["interval_minutes"],r["horizon"]) in (("3","20"),("3","50"),("5","12"),("5","30"))),
      "annual_h15":read("S1-T04_stability.csv",lambda r:h15(r) and r["direction"]=="All" and r["unit"]=="points" and r["period_kind"]=="year"),
      "annual_coverage":read("S1-T00_coverage.csv",lambda r:r["split"]=="development"),
      "cohort_uncertainty_h15":read("S1-bootstrap.csv",lambda r:r["kind"]=="cohort" and h15(r) and r["unit"]=="points" and r["metric"] in ("terminal_delta","favorable","mfe_gt_mae")),
      "equal_active_contrasts":read("S1-comparisons.csv",lambda r:r["direction"]=="All" and r["support"]=="all" and r["comparison"].startswith("equal_active")),
      "paired_uncertainty":read("S1-bootstrap.csv",lambda r:r["kind"]=="contrast" and r["direction"]=="All" and r["support"]=="all" and r["unit"]=="points" and r["metric"]=="terminal_delta"),
    }
    output={"scope":"Saved table rows copied verbatim; no additional estimator/scoring runs.","generated_at_utc":datetime.now(timezone.utc).isoformat(),"command":{"argv":sys.argv,"cwd":str(Path.cwd()),"python":sys.executable,"version":sys.version,"platform":platform.platform()},"before_execution":record(HERE/"interpretation-review-before-v2.json"),"rows":fields}
    for item in receipt["pinned_sources_and_tables"]:
        assert record(Path(item["path"]))==item,item["path"]
    with (HERE/"interpretation-table-extract-v2.json").open("x") as f:json.dump(output,f,indent=2);f.write("\n")
    print(json.dumps({"counts":{name:len(rows) for name,rows in fields.items()},"output":record(HERE/"interpretation-table-extract-v2.json")}))
if __name__=="__main__":main()
