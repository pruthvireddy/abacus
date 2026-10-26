#!/usr/bin/env python3
"""Validate offline report structure, local links and source-derived cell text."""
import argparse,json,re
from pathlib import Path
from html.parser import HTMLParser
from xml.etree import ElementTree
import pandas as pd
from src.common import dump,sha,utcnow
from src.reporting import headline_rows
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
class Report(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.images=[];self.cells=[];self.incell=False;self.current='';self.tables=0
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=='a':self.links.append(attrs.get('href',''))
  if tag=='img':self.images.append(attrs.get('src',''));assert attrs.get('alt')
  if tag=='td':self.incell=True;self.current=''
  if tag=='table':self.tables+=1
  assert tag not in ['script','iframe']
 def handle_data(self,data):
  if self.incell:self.current+=data
 def handle_endtag(self,tag):
  if tag=='td':self.cells.append(self.current);self.incell=False
s=pd.read_parquet(out/'tables/summary.parquet');records=[]
for name in ['report','asia','london','ny','globex']:
 text=(out/(name+'.html')).read_text();parser=Report();parser.feed(text)
 assert 'NaN' not in text and '>nan<' not in text and 'undefined' not in text
 for link in parser.links+parser.images:
  assert not link.startswith(('http:','https:','data:'))
  assert (out/link).is_file() or link=='events.manifest.json',link
 expected=headline_rows(s,None if name=='report' else name)
 for row in expected:
  for value in row:assert str(value) in parser.cells,(name,value)
 assert (out/(name+'.md')).is_file()
 records.append({'report':name,'tables':parser.tables,'images':len(parser.images),'links':len(parser.links),'headline_cells_checked':sum(map(len,expected)),'pass':True,'sha256':sha(out/(name+'.html'))})
for svg in (out/'figures').glob('*.svg'):
 root=ElementTree.parse(svg).getroot();assert root.attrib['viewBox']=='0 0 920 480';assert root.find('{http://www.w3.org/2000/svg}title') is not None
 assert 'nan' not in svg.read_text().lower()
dump(out/'report-verification.json',{'status':'pass','verified_at':utcnow(),'reports':records,'svg_count':len(list((out/'figures').glob('*.svg'))),
 'external_resources':False,'browser_layout_verified':False,'browser_limitation':'Browser security policy blocks file://; no alternate browser or serving workaround attempted.',
 'structural_checks':['all table headlines equal saved numerical evidence','no missing linked assets except retention manifest prepared at seal','no scripts or remote resources','valid standalone SVG XML','all report pairs present'],
 'visual_method':'Local SVG rasterization with bundled sharp; PNG contact sheets and detailed plots inspected separately.'})
print('Report structure and source-value checks passed for five HTML/Markdown pairs')
