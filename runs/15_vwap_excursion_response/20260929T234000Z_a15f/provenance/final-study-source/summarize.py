#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from src.statistics import summarize
from src.execution import check_freeze
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    check_freeze();summarize(a.out,json.loads((a.out/'tables/week-universe.json').read_text()))
