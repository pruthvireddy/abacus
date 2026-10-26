"""Presentation-only ReportLab chart renderer; consume saved numerical evidence."""
import argparse
import csv
import json
from pathlib import Path
import sys
import reportlab
from reportlab.graphics.shapes import Drawing,Rect,String,Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors


def render(stage):
    with (stage/'tables/rhythm_development.csv').open() as f:
        rows=list(csv.DictReader(f))
    drawing=Drawing(1020,650)
    drawing.add(Rect(0,0,1020,650,fillColor=colors.HexColor('#fafcfd'),strokeColor=None))
    drawing.add(String(75,623,'NQ evening pattern · 2020–2023 complete 15-minute bins',fontName='Helvetica',fontSize=18))
    series=[sorted((r for r in rows if r['season']==s),key=lambda r:int(r['bin_minute'])) for s in ('EST','EDT')]
    palette=[colors.HexColor('#174a73'),colors.HexColor('#d07a39')]
    for k,(season,color) in enumerate(zip(('EST','EDT'),palette)):
        drawing.add(Line(80+k*120,600,110+k*120,600,strokeColor=color,strokeWidth=2))
        drawing.add(String(117+k*120,596,season,fontName='Helvetica',fontSize=12,fillColor=color))
    for column,y,height,label in [('mean_volume',365,195,'Mean volume (contracts per 15 minutes)'),('mean_range_points',90,195,'Mean 15-minute range (NQ points)')]:
        drawing.add(Rect(85,y,860/3,height,fillColor=colors.HexColor('#eef2f5'),strokeColor=None))
        drawing.add(String(85,y+height+20,label,fontName='Helvetica',fontSize=12))
        plot=LinePlot();plot.x=85;plot.y=y;plot.width=860;plot.height=height
        plot.data=[[(int(r['bin_minute']),float(r[column])) for r in group] for group in series]
        for k,color in enumerate(palette):plot.lines[k].strokeColor=color;plot.lines[k].strokeWidth=2
        plot.xValueAxis.valueMin=0;plot.xValueAxis.valueMax=360;plot.xValueAxis.valueSteps=[0,60,120,180,240,300,360]
        plot.xValueAxis.labelTextFormat=lambda value:f'{(18+int(value)//60)%24:02d}:{int(value)%60:02d}'
        plot.yValueAxis.valueMin=0;plot.yValueAxis.visibleGrid=True;plot.yValueAxis.gridStrokeColor=colors.HexColor('#dce3e8')
        plot.xValueAxis.labels.fontName='Helvetica';plot.xValueAxis.labels.fontSize=10
        plot.yValueAxis.labels.fontName='Helvetica';plot.yValueAxis.labels.fontSize=10
        drawing.add(plot)
    drawing.add(String(85,42,'New York wall time · bin start · grey area is 18:00–20:00 context',fontName='Helvetica',fontSize=12))
    renderSVG.drawToFile(drawing,str(stage/'figures/volume_rhythm.svg'))
    (stage/'plot_environment.json').write_text(json.dumps({'purpose':'Presentation only; no study calculations','python':sys.version,'reportlab':reportlab.Version,'input':'tables/rhythm_development.csv'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=Path,required=True)
    a=parser.parse_args();render(a.stage.resolve())
