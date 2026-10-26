"""Check supplemental tables, parent retention, report links, and numerical tests."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pandas as pd

from src.features import digest


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ("href","src") and value and not value.startswith(("http:","https:","#","mailto:")):
                self.links.append(value)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--run-id",required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    stage=root/"work/06_vwap_state_dynamics"/args.run_id
    parent=root/"runs/06_vwap_state_dynamics/20260923T180000Z_state06c"
    verification=json.loads((stage/"parent-verification.json").read_text())
    if digest(parent/"manifest.json")!=verification["parent_manifest_sha256"]:
        raise ValueError("parent manifest changed")
    if digest(parent/"events.manifest.json")!=verification["parent_events_manifest_sha256"]:
        raise ValueError("parent event manifest changed")
    first=pd.read_csv(stage/"tables/first_cross_time.csv")
    clock=pd.read_csv(stage/"tables/explicit_clock_windows.csv")
    secondary=pd.read_csv(stage/"tables/secondary_paired_targets.csv")
    if len(first)!=12 or len(clock)!=120 or len(secondary)!=40:
        raise ValueError("supplemental table row counts changed")
    if (first.crossers+first.noncross_censored_at_30m!=first.landmarks).any():
        raise ValueError("first-cross denominators not exhaustive")
    q3=clock[(clock["product"]=="ALL")&(clock.question=="Q3")]
    if q3.denominator.sum()!=133716 or q3.clock_label.nunique()!=6:
        raise ValueError("clock gaps do not partition primary landmarks")
    if (secondary.numerator+secondary.twap_wins+secondary.ties!=secondary.denominator).any():
        raise ValueError("secondary paired outcomes not exhaustive")
    primary=secondary[(secondary.timeframe=="2m")&(secondary.anchor=="globex")&(secondary["product"]=="ALL")]
    if len(primary)!=2 or not (primary.denominator==133716).all():
        raise ValueError("secondary target primary cohort mismatch")
    page=Links();page.feed((stage/"report.html").read_text())
    for link in set(page.links):
        if link.startswith("../20260923T180000Z_state06c/"):
            target=parent/link.split("/",2)[-1]
        else:
            target=stage/link
        if not target.is_file() and link!="manifest.json":
            raise FileNotFoundError(target)
    for path in (stage/"figures").glob("*.svg"):
        ET.parse(path)
    cmd=[str(root/".venv/bin/python"),"-m","unittest","discover","-s","studies/06_vwap_state_dynamics/tests","-v"]
    tests=subprocess.run(cmd,cwd=root,capture_output=True,text=True)
    (stage/"focused-tests.log").write_text(tests.stdout+tests.stderr)
    if tests.returncode:raise RuntimeError("focused tests failed")
    result={"status":"passed","parent_manifest_sha256":verification["parent_manifest_sha256"],
            "parent_event_rows":367719,"primary_landmarks_clock_partitioned":133716,
            "first_cross_rows":len(first),"explicit_clock_rows":len(clock),
            "secondary_paired_rows":len(secondary),"report_links_checked":len(set(page.links)),
            "svg_xml_checked":len(list((stage/"figures").glob("*.svg"))),
            "focused_tests":"8 passed"}
    (stage/"verification-results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__=="__main__":main()
