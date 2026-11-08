"""Render manually read, authorized case evidence; no level detector/selector.

Reads only the three already-filtered private source extracts and neutral maps.
Original captures are never copied into the tracked figures directory.
"""
from __future__ import annotations

import csv
from decimal import Decimal
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE = ROOT / 'work/29_verniman_level_reconstruction/phase2_20261030T222323Z'
DATES = ('2026-10-01', '2026-10-02', '2026-10-05')

# Each tuple is a manual image reading: exact short label, price/interval, basis.
# Intervals are deliberately coarse axis estimates, not inferred tick prices.
MAPS = {
 'B-20261001-I01': [
  ('GAP 7803 magnet',7803,'printed'),('HVE-YVAH magnet',(7778,7781),'axis_estimate'),
  ('YPOC-ONH magnet',7767.75,'aligned_axis_badge'),('YVAL',(7746,7748),'axis_estimate'),
  ('GAP 7722 magnet',7722,'printed'),('YLOD-ONL',7705,'aligned_axis_badge'),('VPOC 7691 magnet',7691,'printed')],
 'B-20261001-I02': [
  ('PBT 7856 magnet',7856,'printed'),('ATH-RTH',(7847,7851),'axis_estimate'),('HVE 7842',7842,'printed'),
  ('GAP-PBT 7830 magnet',7830,'printed'),('GAP 7803 magnet',7803,'printed'),
  ('HVE-YVAH magnet',(7778,7781),'axis_estimate'),('YPOC-ONH magnet',(7766,7769),'axis_estimate'),
  ('YVAL',(7746,7748),'axis_estimate'),('GAP 7722 magnet',7722,'printed'),
  ('YLOD-ONL',(7704,7707),'axis_estimate'),('VPOC 7691 magnet',7691,'printed'),
  ('HVE 7656',7656,'printed'),('HVE 7634',7634,'printed'),('GAP 7621 magnet',7621,'printed')],
 'B-20261002-I01': [
  ('PBT 7856 magnet',7856,'printed'),('ATH-RTH',(7847,7851),'axis_estimate'),('HVE 7842',7842,'printed'),
  ('GAP-PBT 7830 magnet',7830,'printed'),('GAP 7803 magnet',7803,'printed'),('HVE 7785',7785,'printed'),
  ('HVE-YHOD',(7766,7769),'axis_estimate'),('HVE-YVAH',(7743,7745),'axis_estimate'),
  ('YPOC-GAP magnet',(7731,7733),'axis_estimate'),('HVE-YVAL magnet',(7694,7699),'axis_estimate'),
  ('HVE-YLOD',(7671,7675),'axis_estimate')],
 'B-20261002-I02': [
  ('PBT 7856 magnet',7856,'printed'),('ATH-RTH',(7847,7851),'axis_estimate'),('HVE 7842',7842,'printed'),
  ('GAP-PBT 7830 magnet',7830,'printed'),('HVE 7804',7804,'printed'),('HVE 7785',7785,'printed'),
  ('HVE-YHOD',(7766,7769),'axis_estimate'),('HVE-YVAH',(7743,7745),'axis_estimate'),
  ('YPOC-GAP magnet',(7731,7733),'axis_estimate'),('HVE-YVAL magnet',(7694,7699),'axis_estimate'),
  ('HVE-YLOD',(7671,7675),'axis_estimate'),('HVE 7656 (LOD exp)',7656,'printed'),
  ('HVE 7634',7634,'printed'),('GAP 7621 magnet',7621,'printed')],
 'B-20261005-I01': [
  ('GAP-PBT 7830 magnet',7830,'printed'),('HVE 7812',7812,'printed'),
  ('YVAH magnet',(7797,7800),'axis_estimate'),('HVE-GAP magnet',(7784,7787),'axis_estimate'),
  ('HVE-YVAL',(7766,7769),'axis_estimate'),('PBT-ETH magnet',7746.75,'aligned_axis_badge'),
  ('GAP 7732 magnet',7732,'printed'),('HVE 7704',7704,'printed')],
 'B-20261005-I02': [
  ('PBT 7856 magnet',7856,'printed'),('ATH-RTH',(7847,7851),'axis_estimate'),('HVE 7842',7842,'printed'),
  ('GAP-PBT 7830 magnet',7830,'printed'),('HVE 7812',7812,'printed'),
  ('YVAH magnet',(7797,7800),'axis_estimate'),('HVE-GAP magnet',(7784,7787),'axis_estimate'),
  ('HVE-YVAL',(7766,7769),'axis_estimate'),('PBT-ETH magnet',(7745,7748),'axis_estimate'),
  ('GAP 7732 magnet',7732,'printed'),('HVE 7704',7704,'printed'),
  ('HVE-YLOD',(7671,7675),'axis_estimate'),('HVE 7656',7656,'printed'),
  ('HVE 7634',7634,'printed'),('GAP 7621 magnet',7621,'printed')],
 'X-2105752800323924362': [
  ('GAP 7803 magnet',7803,'printed'),('HVE 7786',7786,'printed'),('HVE 7767',7767,'printed'),
  ('HVE 7742',7742,'printed'),('HVE 7704',7704,'printed'),('HVE 7670',7670,'printed')],
 'X-2106113331052585421': [
  ('GAP-PBT 7830 magnet',7830,'printed'),('HVE 7812',7812,'printed'),('HVE 7785',7785,'printed'),
  ('HVE 7767',7767,'printed'),('GAP 7732 magnet',7732,'printed'),
  ('HVE-YVAL magnet',(7694,7699),'axis_estimate'),('HVE-YLOD',(7671,7675),'axis_estimate'),('HVE 7656',7656,'printed')],
 'X-2107206362547839375': [
  ('PBT 7917 magnet',7917,'printed'),('PBT 7890 magnet',7890,'printed'),('PBT 7878 magnet',7878,'printed'),
  ('PBT 7856 magnet',7856,'printed'),('ATH-RTH',(7847,7851),'axis_estimate'),('HVE 7842',7842,'printed'),
  ('HVE 7812',7812,'printed'),('HVE 7785',7785,'printed'),('HVE 7767',7767,'printed'),('GAP 7732 magnet',7732,'printed')],
 # Named structural references only; execution arrows/P&L/readouts are excluded.
 'X-2105752127028990422': [
  ('YPOC-ONH',(7766,7769),'axis_estimate'),('YVAL',(7746,7748),'axis_estimate'),
  ('YLOD-ONL',(7704,7707),'axis_estimate'),('LOD expected fulfilled.',(7673,7676),'axis_estimate')],
 'X-2106113108016021595': [
  ('HVE 7812',7812,'printed'),('HVE 7785',7785,'printed'),('HVE 7767',7767,'printed')],
 'X-2107205857691971880': [
  ('PBT 7856 magnet',7856,'printed'),('ATH-RTH (HOD expected)',(7848,7852),'axis_estimate'),
  ('HVE 7842',7842,'printed'),('HVE-YHOD',(7809,7813),'axis_estimate'),
  ('YVAH',(7797,7800),'axis_estimate'),('ONH',(7792,7794),'axis_estimate'),('HVE 7785',7785,'printed'),
  ('YPOC',(7774,7777),'axis_estimate'),('HVE-YVAL',(7766,7769),'axis_estimate'),('ONL',(7759,7762),'axis_estimate')],
}

def features(label):
    return [x for x in ('HVE','HVN','LVN','PBT','GAP','YVAH','YPOC','YVAL','YVALH','VPOC','YHOD','YLOD','ONH','ONL','ATH-RTH','LOD')
            if re.search(r'(?<![A-Z])'+re.escape(x)+r'(?![A-Z])',label)]

def explanation(tokens):
    proposals=[]
    if 'HVE' in tokens: proposals.append('Boundary of an unspecified fuller-volume region; exact segmentation/edge rule not recovered.')
    if 'PBT' in tokens: proposals.append('Projected balance completion; anchor identities, center and projection rule remain unidentified.')
    if any(x in tokens for x in ('YVAH','YPOC','YVAL','VPOC')): proposals.append('Prior/named profile reference; period, data and profile method must be specified before equivalence to baseline.')
    if 'GAP' in tokens: proposals.append('Persisting gap/reference boundary; origin is not established and it is not inferred from today actual RTH open.')
    if any(x in tokens for x in ('YHOD','YLOD','ONH','ONL')): proposals.append('Named prior/overnight extreme; compound labels can express confluence.')
    if 'ATH-RTH' in tokens: proposals.append('Claimed regular-session all-time extreme; requires long contract-consistent history absent from this comparison.')
    return proposals or ['Unresolved structural reference.']

def run():
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    sources={s['source_id']:s for s in manifest['sources']}
    neutral=json.loads((STAGE/'neutral-baselines.json').read_text())
    baselines={o['date']:o['frozen_values'] for o in neutral['observations']}
    inventory=[]

    def add(source_id, suffix, label, value, basis, role='unresolved', side=None, order=None, origin=None):
        source=sources[source_id]; day=source['session_date']; assert day in DATES
        lo,hi=value if isinstance(value,tuple) else (value,value)
        tokens=features(label)
        period='weekly_or_composite_unspecified' if source_id.endswith('I02') else 'unknown'
        if any(t in tokens for t in ('YVAH','YPOC','YVAL','YHOD','YLOD')):
            period='previous_session_unspecified' if period=='unknown' else period+'; prior-session confluence'
        if any(t in tokens for t in ('ONH','ONL')): period+='; overnight unspecified clock'
        exact=basis!='axis_estimate'
        inventory.append({
          'level_id':source_id+'-'+suffix,'session_date':day,'source_id':source_id,
          'original_label':label,'exact_readable_source_text':label,
          'price_low':str(lo),'price_high':str(hi),'price_basis':basis,
          'reading_uncertainty':'Literal printed number; rounding convention unknown.' if basis=='printed' else 'Number is readable in an aligned axis badge; association with the named line is qualified.' if exact else 'Coarse bracket from visible price axis; no tick precision inferred.',
          'instrument':'ES from parent-plan context' if source_id.startswith('B-') else '/ES context; technical-map header may be absent',
          'actual_contract':'ESZ26' if source_id.startswith('B-') and '-I' not in source_id else None,
          'parent_plan_contract':'ESZ26' if source_id.startswith('B-') else None,
          'contract_identity_basis':'Printed in daily-plan text.' if source_id.startswith('B-') and '-I' not in source_id else 'Chart delivery contract not printed; parent plan provides context, not direct chart-contract proof.' if source_id.startswith('B-') else 'X chart delivery contract unknown; no automatic equivalence to ESZ2026.',
          'reference_period':period,'developing_or_completed':'completed prior profile / developing overnight confluence' if any(t in tokens for t in ('ONH','ONL')) else 'prior completed reference; exact period unknown' if any(t in tokens for t in ('YVAH','YPOC','YVAL','YHOD','YLOD')) else 'unresolved',
          'source_timing_class':'supported later/intraday' if source_id.startswith('X-') else 'unresolved',
          'available_at':None,'preopen_status':'unresolved; filename/update clock claims do not certify publication availability',
          'provenance':{'source_revision_id':source.get('source_revision_id',source.get('observation_id',source.get('parent_source_id'))),'source_posted_at':source.get('source_posted_at',source.get('source_claimed_published_at')),'source_claimed_updated_at':source.get('source_claimed_updated_at'),'capture_timestamp':source.get('captured_at'),'claimed_chart_clock':source.get('claimed_chart_clock'),'claimed_chart_timezone':source.get('claimed_chart_timezone'),'source_url':source['source_url'],'image_path':source.get('path') or (source.get('bytes',{}).get('path') if isinstance(source.get('bytes'),dict) else None)},
          'apparent_role':role,'scenario_side':side,'source_target_order':order,'families':tokens,
          'candidate_explanations':explanation(tokens),
          'supporting_evidence':[source_id,'neutral-'+day],
          'competing_explanations':['Different reference profile/session, feed, row size, value-area arithmetic or chart timeframe.','Compound confluence and nearby prices do not identify one cause.'],
          'confidence':{'label_reading':'high','price_reading':'high' if basis=='printed' else 'medium','construction':'low'},
          'unresolved_questions':['Historical pre-open availability?','Exact profile/anchor identity and rule?'],
          'origin':origin or 'manual retained-image reading; not fresh browser image inspection',
        })

    for day in DATES:
        tag=day.replace('-',''); sid='B-'+tag
        plans=json.loads((STAGE/'selected-sources/release'/day/'levels.json').read_text())
        for row in plans:
            assert row['session_date']==day and row['available_at'] is None
            suffix='PLAN-'+row['side']+'-'+row['role']+'-'+str(row['ordinal'])
            role='scenario divider' if row['role']=='trigger' else 'destination'
            add(sid,suffix,row['source_text'],(Decimal(row['price_low']),Decimal(row['price_high'])),'printed',role,row['side'],row['ordinal'],
                {'kind':'canonical release row','outlook_id':row['outlook_id'],'original_role':row['role'],'original_label':row['source_label'],'conditions':row['conditions']})
        outlook=json.loads((STAGE/'selected-sources/release'/day/'outlooks.json').read_text())[0]
        header=outlook['body_text'].split('ESZ26 (Dec2026): ',1)[1].splitlines()[0]
        for label,price in re.findall(r'(YVAH|YPOC|YVAL|GAP) (\d+(?:\.\d+)?)',header):
            add(sid,'HEADER-'+label,label+' '+price,Decimal(price),'printed','location / reference',origin='Exact reference block in allowed retained plan; not necessarily included in canonical target rows.')
    for sid,readings in MAPS.items():
        for index,(label,value,basis) in enumerate(readings,1):
            add(sid,'MAP-'+str(index).zfill(2),label,value,basis,'destination candidate' if 'magnet' in label else 'location / unresolved')

    conflicts=[
     {'id':'Q1','session_date':'2026-10-01','sources':['B-20261001','B-20261001-I01'],'detail':'Plan VPOC6691 versus image VPOC7691; preserve both, no canonical correction.'},
     {'id':'Q2','session_date':'2026-10-01','sources':['B-20261001'],'detail':'Bullish YVALH versus bearish YVAL at7747; source wording retained.'},
     {'id':'Q3','session_date':'2026-10-01','sources':['B-20261001','B-20261001-I01'],'detail':'Plan HVE7786 versus earlier claimed HVE-YVAH near7779; later map has HVE7786.'},
     {'id':'Q4','session_date':'2026-10-02','sources':['B-20261002-I01','B-20261002-I02'],'detail':'Daily GAP7803 versus nearby weekly HVE7804; no merging.'},
     {'id':'Q5','session_date':'2026-10-05','sources':['B-20261005','B-20261005-I01'],'detail':'Plan GAP7783 versus image HVE-GAP axis bracket7784–7787; PBT7746 versus aligned7746.75. The nearby grey7768badge does not conclusively price the unnumbered HVE-YVAL line.'},
    ]
    result={'schema':'abacus.study29.phase2.levels/v1','authorized_dates':DATES,
      'scope':'Every named structural horizontal reference read in six blog maps, three closing technical maps, three dated trade recaps, and allowed plan/header text. Execution markers, P&L, unnamed histogram modal lines and floating indicator/current-bar readouts are excluded from candidate levels.',
      'timing_policy':'No historically certified pre-open level; all original available_at null. Supported later/intraday refers to retained after-cutoff post context, not verified original publication bytes.',
      'levels':inventory,'source_conflicts':conflicts}
    result['axis_context_notes']=[{'source_id':'B-20261005-I01','readable_badges':['7793','7760.25','7768'],'association':'7793/7760.25 axis extrema align with the depicted overnight segment, also consistent with named ONH/ONL in the later recap; neither is explicitly priced as ONH/ONL in I01. Grey7768 is near the unnumbered HVE-YVAL line but may be a different chart readout; do not assign its tick precision to that line.','use':'Qualified context only, not proof of chart contract or profile methodology.'}]
    (HERE/'level-inventory.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    # Compare every occurrence to every frozen family. Nearest is descriptive,
    # never a selector, construction identity or target-match score.
    csv_rows=[]
    for level in inventory:
        lo,hi=Decimal(level['price_low']),Decimal(level['price_high'])
        candidates=[]
        for family,price in baselines[level['session_date']].items():
            p=Decimal(str(price));distance=max(lo-p,p-hi,Decimal(0))
            candidates.append({'family':family,'price':str(p),'distance_points':str(distance)})
            csv_rows.append([level['level_id'],level['session_date'],level['source_id'],level['original_label'],str(lo),str(hi),level['price_basis'],family,str(p),str(distance)])
        level['nearest_baseline_candidates']=sorted(candidates,key=lambda x:(Decimal(x['distance_points']),x['family']))[:3]
    (HERE/'level-inventory.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    with (HERE/'baseline-comparison.csv').open('w',newline='') as out:
        writer=csv.writer(out);writer.writerow(['level_id','session_date','source_id','source_label','source_price_low','source_price_high','price_basis','baseline_family','baseline_price','distance_to_source_interval_points']);writer.writerows(csv_rows)
    print(f'{len(inventory)} level occurrences; {len(csv_rows)} all-family comparison rows; no detector or selector implemented.')

if __name__=='__main__':
    run()
