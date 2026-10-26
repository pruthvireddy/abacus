"""Build saved representative profile paths and an offline SVG from fixed-rule examples."""
from __future__ import annotations

import argparse
import gzip
import html
import json
import math
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent))
from src.study_run import read_snapshots

M=60_000_000_000


def render(stage,root):
    manifest=json.loads((root/'catalog/datasets/nq_causal_vp_hvn__1.0.0.json').read_text())
    examples=[json.loads(s) for s in gzip.open(stage/'tables/representative_paths.jsonl.gz','rt')]
    with gzip.open(stage/'events/ledger_2010.jsonl.gz','rt') as stream:
        exclusion=next(json.loads(s) for s in stream
                       if '"input_unavailable"' in s and '"setup":"A"' in s)
    (stage/'tables/representative_exclusion.json').write_text(json.dumps(exclusion,indent=2,sort_keys=True)+'\n')
    examples.append({'setup':'A','class':'excluded','direction':exclusion['direction'],
                     'session_date':exclusion['session_date'],'signal_ts':exclusion['ts_event']})
    by_year={}
    rows=[]
    for example in examples:
        year=int(example['session_date'][:4])
        if year not in by_year:
            by_year[year]=read_snapshots(root,manifest,year)
        records=[x for x in by_year[year] if x['session_date']==example['session_date']]
        lookup={x['ts_event']:x for x in records}
        entry=lookup.get(example['signal_ts']+M)
        if entry is None and example['class']!='excluded': raise ValueError('representative entry missing')
        entry_price=entry['open'] if example['class']!='excluded' else lookup[example['signal_ts']]['close']
        direction=example['direction']
        for offset in range(-10,31):
            r=lookup.get(example['signal_ts']+offset*M)
            if r is None: continue
            row={'setup':example['setup'],'class':example['class'],'direction':direction,
                 'session_date':example['session_date'],'signal_ts':example['signal_ts'],
                 'offset_from_signal':offset,'anchor_price':entry_price,
                 'anchor_type':'signal_close_no_trade' if example['class']=='excluded' else 'actual_next_open',
                 'signed_close':direction*(r['close']-entry_price),
                 'signed_poc':direction*(r['on_poc']-entry_price),
                 'signed_vah':direction*(r['on_vah']-entry_price),
                 'signed_val':direction*(r['on_val']-entry_price)}
            rows.append(row)
    frame=pd.DataFrame(rows)
    frame.to_csv(stage/'tables/representative_profiles.csv',index=False)
    # SVG consumes only the saved table, so its plotted numbers can be audited.
    colors={'signed_close':'#136f63','signed_poc':'#9c4e97','signed_vah':'#d28528','signed_val':'#4777bc'}
    W,H=1440,1430
    fragments=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
               '<rect width="100%" height="100%" fill="#f6f8fa"/>',
               '<text x="30" y="42" font-family="system-ui" font-size="27" fill="#173144">Fixed-rule representative paths and developing profile</text>',
               '<text x="30" y="70" font-family="system-ui" font-size="16" fill="#46606f">Signed NQ points relative to next open; excluded example uses signal close and has no trade</text>']
    for index,example in enumerate(examples):
        panel=frame[(frame.setup==example['setup'])&(frame['class']==example['class'])]
        if panel.empty: continue
        col=index%3; row=index//3
        x0=30+col*470; y0=100+row*330; width=440;height=305
        px=x0+45;py=y0+52;pw=370;ph=225
        values=panel[['signed_close','signed_poc','signed_vah','signed_val']].to_numpy().ravel()
        finite=[float(v) for v in values if math.isfinite(float(v))]
        ymin=min(finite+[0]);ymax=max(finite+[0]);padding=max(2.,(ymax-ymin)*.09)
        ymin-=padding;ymax+=padding
        def xy(offset,value):
            return (px+(offset+10)/40*pw,py+ph-(value-ymin)/(ymax-ymin)*ph)
        fragments.append(f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" rx="12" fill="white" stroke="#d6e1e8"/>')
        label=f"Setup {example['setup']} · {example['class']} · {example['session_date']}"
        fragments.append(f'<text x="{x0+18}" y="{y0+28}" font-family="system-ui" font-size="17" fill="#173144">{html.escape(label)}</text>')
        zero=xy(0,0)[1]
        fragments.append(f'<line x1="{px}" y1="{zero:.1f}" x2="{px+pw}" y2="{zero:.1f}" stroke="#9eacb5" stroke-dasharray="4 4"/>')
        signal_x=xy(0,0)[0]
        fragments.append(f'<line x1="{signal_x:.1f}" y1="{py}" x2="{signal_x:.1f}" y2="{py+ph}" stroke="#b8c7d1" stroke-dasharray="3 4"/>')
        for name,color in colors.items():
            points=[]
            for r in panel.itertuples(index=False):
                value=getattr(r,name)
                if not math.isfinite(value):continue
                x,y=xy(r.offset_from_signal,value)
                points.append(f'{x:.1f},{y:.1f}')
            if points:
                fragments.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="{3 if name=="signed_close" else 1.6}" opacity="{1 if name=="signed_close" else .77}"/>')
        fragments.append(f'<text x="{px}" y="{y0+293}" font-family="system-ui" font-size="12" fill="#536b78">−10m</text>')
        fragments.append(f'<text x="{px+pw-30}" y="{y0+293}" font-family="system-ui" font-size="12" fill="#536b78">+30m</text>')
    legend_x=30;legend_y=1415
    for name,color in colors.items():
        fragments.append(f'<line x1="{legend_x}" y1="{legend_y-5}" x2="{legend_x+23}" y2="{legend_y-5}" stroke="{color}" stroke-width="3"/>')
        fragments.append(f'<text x="{legend_x+30}" y="{legend_y}" font-family="system-ui" font-size="15" fill="#173144">{name.replace("signed_", "").upper()}</text>')
        legend_x+=150
    fragments.append('</svg>')
    (stage/'figures/representative_profiles.svg').write_text(''.join(fragments))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    render(args.stage.resolve(),args.root.resolve())
