#!/usr/bin/env python3
"""Thin reproducible study stage command, using explicit staging paths."""
import argparse,sys
from pathlib import Path
from src.common import command,roots,STUDY,load,dump,sha,now
from src.execution import prepare,freeze,execute,seal
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','freeze','execute','summarize','verify','verify-report','seal','verify-sealed']);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    if a.stage=='verify-sealed':
        from src.verification import verify_sealed
        verify_sealed(out);sys.exit(0)
    if out.parent != roots().workspace_root/'work'/STUDY:
        p.error('Mutable stages require work/<study>/<unique-run>; completed runs are immutable. Use verify-sealed for read-only checks.')
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
        elif a.stage=='verify-report':
            from src.execution import check_freeze
            from src.verification import verify_report
            check_freeze(out);verify_report(out)
            verified=load(out/'verification.json');assert verified['status']=='pass'
            verified['report_refreshed_at_utc']=now();verified['report_verification_sha256']=sha(out/'report-verification.json');dump(out/'verification.json',verified)
            print('Refreshed offline report values/links/assets verified; frozen numerical sources unchanged.')
        else:seal(out)
    if a.stage=='prepare':command(out,a.stage,sys.argv)
