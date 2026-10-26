#!/usr/bin/env python3
"""Thin study entry point. Each stage requires explicit local output paths."""
import argparse
from pathlib import Path
from src.execution import execute
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--pilot',type=Path,required=True)
    a=p.parse_args();execute(a.out,a.pilot)
