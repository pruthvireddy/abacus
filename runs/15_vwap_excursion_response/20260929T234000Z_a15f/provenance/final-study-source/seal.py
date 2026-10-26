#!/usr/bin/env python3
import argparse
from pathlib import Path
from src.sealing import seal
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();seal(a.out)
