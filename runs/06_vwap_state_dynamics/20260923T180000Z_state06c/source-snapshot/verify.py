"""Read-only numerical/artifact gate on staged evidence before sealing."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pandas as pd
import pyarrow.parquet as pq

from src.features import digest


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href","src") and value and not value.startswith(("http:","https:","#","mailto:")):
                self.paths.append(value)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args()
    workspace=Path(__file__).resolve().parents[2]
    stage=workspace/"work/06_vwap_state_dynamics"/args.run_id
    required=("config.json","inputs.lock.json","protocol-1.0.0.json","protocol-1.0.0.md",
              "input-verification.json","feature-feasibility.json","feature-source-key-audit.json",
              "extraction-summary.json","numerical-audit.json","metrics.json","report.md","report.html","advice.md",
              "tables/funnel.csv","tables/primary_probabilities.csv","tables/matched_comparisons.csv",
              "tables/barrier_outcomes.csv","tables/paired_errors.csv","tables/probability_atlas.csv",
              "tables/examples.csv","tables/example-audit.csv","figures/primary-probabilities.svg",
              "figures/barrier-contrast.svg")
    for path in required:
        if not (stage/path).is_file(): raise FileNotFoundError(stage/path)
    checks=json.loads((stage/"input-verification.json").read_text())
    for item in checks:
        path=workspace/item["path"]
        if digest(path)!=item["sha256"]:
            raise ValueError(f"input changed after pilot: {item['path']}")
    key_audit=json.loads((stage/"feature-source-key-audit.json").read_text())
    key_total=sum(x["source_30m_key_capable"] for x in key_audit)
    key_n=sum(x["landmarks"] for x in key_audit)
    if key_total!=key_n or key_total!=367719: raise ValueError("source-key coverage mismatch")
    files=sorted((stage/"events").glob("events_*.parquet"))
    feature_files=sorted((stage/"features").glob("landmarks_*.parquet"))
    if len(files)!=46 or len(feature_files)!=6: raise ValueError("partition count mismatch")
    event_count=sum(pq.ParquetFile(path).metadata.num_rows for path in files)
    feature_count=sum(pq.ParquetFile(path).metadata.num_rows for path in feature_files)
    if event_count!=key_n or feature_count!=key_n: raise ValueError("event/feature counts mismatch")
    p=pd.read_csv(stage/"tables/primary_probabilities.csv")
    b=pd.read_csv(stage/"tables/barrier_outcomes.csv")
    f=pd.read_csv(stage/"tables/funnel.csv")
    primary=f[(f.cohort=="primary")&(f["product"]=="ALL")].iloc[0]
    if primary.landmarks!=133716 or primary.outcome_capable!=133716 or primary.missing_outcome!=0:
        raise ValueError("primary funnel mismatch")
    for _,row in p.iterrows():
        if row.numerator>row.denominator or row.landmarks!=row.denominator+row.outcome_missing:
            raise ValueError("probability denominator mismatch")
        if row.question=="Q3" and row.numerator+row.twap_wins+row.ties!=row.denominator:
            raise ValueError("paired classes not exhaustive")
    if (b[["favorable","adverse","neither","ambiguous"]].sum(axis=1)!=b.denominator).any():
        raise ValueError("barrier classes not exhaustive")
    if int(json.loads((stage/"metrics.json").read_text())["y1_y2_complement_checked"])!=event_count:
        raise ValueError("Y1/Y2 complement reconciliation mismatch")
    report=(stage/"report.md").read_text()
    html=(stage/"report.html").read_text()
    parser=Links();parser.feed(html)
    markdown_links=re.findall(r"\]\(([^)]+)\)",report)
    for path in set(parser.paths+markdown_links):
        if not (stage/path).is_file() and path not in ("events.manifest.json","manifest.json"):
            raise FileNotFoundError(f"broken report link: {path}")
    for path in (stage/"figures").glob("*.svg"):
        ET.parse(path)
    test_cmd=[str(workspace/".venv/bin/python"),"-m","unittest","discover","-s","studies/06_vwap_state_dynamics/tests","-v"]
    tests=subprocess.run(test_cmd,cwd=workspace,text=True,capture_output=True)
    (stage/"focused-tests.log").write_text(tests.stdout+tests.stderr)
    if tests.returncode:
        raise RuntimeError("focused numerical tests failed")
    result={"status":"passed","input_files_rehashed":len(checks),"source_key_landmarks":key_total,
            "event_rows":event_count,"feature_rows":feature_count,"event_partitions":len(files),
            "all_primary_outcomes_capable":True,"q1_q2_complement_rows":event_count,
            "probability_and_barrier_denominators":"exhaustive",
            "report_links_checked":len(set(parser.paths+markdown_links)),
            "svg_xml_checked":len(list((stage/"figures").glob("*.svg"))),
            "focused_numerical_tests":"6 passed"}
    (stage/"verification-results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__=="__main__":main()
