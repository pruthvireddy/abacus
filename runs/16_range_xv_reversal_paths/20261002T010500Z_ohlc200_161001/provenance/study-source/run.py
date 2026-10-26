#!/usr/bin/env python3
"""Thin reproducible study stage command, using explicit staging paths."""
import argparse,sys
from pathlib import Path
from src.common import command
from src.execution import prepare,freeze,execute,seal
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','freeze','execute','summarize','verify','seal']);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    if a.stage=='prepare':prepare(out)
    else:
        command(out,a.stage,sys.argv)
        if a.stage=='freeze':freeze(out)
        elif a.stage=='execute':execute(out)
        elif a.stage=='summarize':
            from src.report import render
            render(out)
        elif a.stage=='verify':
            from src.verification import verify
            verify(out)
        else:seal(out)
    if a.stage=='prepare':command(out,a.stage,sys.argv)
