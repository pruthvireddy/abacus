"""Original comparison figures, presentation only; no detector or selector.

Uses bundled ReportLab and Sharp; matplotlib is absent from the locked environment.
Third-party chart bytes are not copied into the authored figures.
"""
from pathlib import Path
import json
import math
import subprocess
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STAGE=ROOT/'work/29_verniman_level_reconstruction/phase2_20261030T222323Z'
RUNTIME=Path('/Users/pruthvi/.cache/codex-runtimes/codex-primary-runtime/dependencies')
BLUE='#1d4ed8';ORANGE='#b45309';INK='#172033';GRAY='#526177'

def text(d,x,y,value,size=12,color=INK,anchor='start',bold=False):
    d.add(String(x,y,value,fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,fillColor=HexColor(color),textAnchor=anchor))

def main():
    levels=json.loads((HERE/'level-inventory.json').read_text())['levels']
    baselines={r['date']:r['frozen_values'] for r in json.loads((STAGE/'neutral-baselines.json').read_text())['observations']}
    out=HERE/'figures';out.mkdir(exist_ok=True)
    for day,baseline in baselines.items():
        sid='B-'+day.replace('-','');rows=[r for r in levels if r['source_id']==sid]
        refs=[next(r for r in rows if r['level_id'].endswith('HEADER-'+label)) for label in ['YVAH','YPOC','YVAL']]
        values=[float(r['price_low']) for r in refs]+[baseline[k] for k in ['completed_rth_vah','completed_rth_poc','completed_rth_val']]
        low=math.floor((min(values)-4)/10)*10;high=math.ceil((max(values)+4)/10)*10
        def px(price):return 100+(price-low)/(high-low)*440
        d=Drawing(1120,620);d.add(Rect(0,0,1120,620,fillColor=HexColor('#f5f7fb'),strokeColor=None))
        text(d,45,575,day+' | Verniman source and neutral references',22,bold=True)
        text(d,45,545,'Source timing unresolved. Baseline: ESZ2026, 5m ETH, 16 ticks / 70%, 09:25 New York.',13,GRAY)
        text(d,45,495,'Named profile references',16,bold=True)
        for tick in range(low,high+1,10):
            d.add(Line(px(tick),150,px(tick),465,strokeColor=HexColor('#d9e0ea'),strokeWidth=.7))
            text(d,px(tick),128,str(tick),11,GRAY,'middle')
        for idx,(r,key) in enumerate(zip(refs,['completed_rth_vah','completed_rth_poc','completed_rth_val'])):
            y=435-115*idx;source=float(r['price_low']);ours=baseline[key]
            text(d,45,y-4,['YVAH','YPOC','YVAL'][idx],13,bold=True)
            d.add(Line(px(source),y,px(ours),y,strokeColor=HexColor('#9ca9ba'),strokeWidth=2))
            d.add(Circle(px(source),y,6,fillColor=HexColor(BLUE),strokeColor=None))
            d.add(Rect(px(ours)-5,y-5,10,10,fillColor=HexColor(ORANGE),strokeColor=None))
            text(d,px(source),y+19,f'{source:g}',13,BLUE,'middle')
            text(d,px(ours),y-27,f'{ours:g}',13,ORANGE,'middle')
        text(d,100,98,'Blue: source printed reference',12,BLUE)
        text(d,100,78,'Orange: our completed-RTH approximation',12,ORANGE)
        text(d,640,495,'Printed conditional scenarios',16,bold=True)
        plans=[r for r in rows if isinstance(r['origin'],dict)]
        trigger=next(r for r in plans if r['scenario_side']=='bullish' and r['origin']['original_role']=='trigger')
        text(d,640,453,'Divider: '+trigger['original_label'],15,bold=True)
        y=411
        for side,color in [('bullish','#166534'),('bearish','#b91c1c')]:
            text(d,640,y,side.title()+' branch (VIX/CVD condition)',13,color,bold=True);y-=30
            for r in sorted([r for r in plans if r['scenario_side']==side and r['origin']['original_role']=='target'],key=lambda r:r['source_target_order']):
                price=f"{float(r['price_low']):g}"
                text(d,655,y,f"{r['source_target_order']}. {r['origin']['original_label']} {price}",13,color);y-=24
            y-=25
        note=['Numbers describe source claims, not a target selector.']
        if day=='2026-10-01':note=['Conflict retained: plan VPOC6691; chart VPOC7691.','YVALH versus YVAL wording also differs.']
        if day=='2026-10-05':note=['Plan PBT7746 versus chart axis7746.75.','No causal projection anchors identified.']
        for i,line in enumerate(note):text(d,640,83-17*i,line,11,GRAY)
        text(d,45,28,'Authored illustration. No source chart/full post reproduced. Proximity does not identify construction or historical availability.',11,GRAY)
        svg=out/f'{day}-comparison.svg';png=out/f'{day}-comparison.png'
        renderSVG.drawToFile(d,str(svg))
        code="const sharp=require(process.argv[1]);sharp(process.argv[2],{density:144}).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exit(1)})"
        subprocess.run([str(RUNTIME/'node/bin/node'),'-e',code,str(RUNTIME/'node/node_modules/sharp'),str(svg),str(png)],check=True)
    print('Rendered three original comparison figures (ReportLab SVG + Sharp PNG).')

if __name__=='__main__':main()
