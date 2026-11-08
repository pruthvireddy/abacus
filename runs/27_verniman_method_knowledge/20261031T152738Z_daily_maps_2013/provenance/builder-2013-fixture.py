#!/usr/bin/env python3
"""Synthetic 2013 calendar fixture; dates here make no historical source claim."""
import csv
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
spec=importlib.util.spec_from_file_location('calendar_fixture_2013',ROOT/'studies/27_verniman_method_knowledge/build_daily_maps.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory(prefix='daily-map-2013-calendar-') as temp:
    stage=Path(temp);(stage/'captures').mkdir();posts=[]
    for i,(stamp,title) in enumerate([('2013-07-15','Synthetic dated source A'),('2013-07-15','Synthetic dated source B'),(None,'Synthetic unresolved source')],1):
        raw=('<h3 class="post-title">'+title+'</h3><div class="post-body entry-content"><p>Complete synthetic retained source text.</p></div>').encode()
        packed=gzip.compress(raw,mtime=0);relative=f'captures/source-{i}.html.gz';(stage/relative).write_bytes(packed)
        posts.append({'url':f'https://verniman.blogspot.com/2013/fixture-{i}.html','title':title,'session_date':stamp,'html':{'path':relative,'bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),'uncompressed_bytes':len(raw),'uncompressed_sha256':hashlib.sha256(raw).hexdigest()},'images':[],'capture_kind':'retained','captured_at':'2026-10-31T00:00:00Z','source_capture_at':'2026-10-31T00:00:00Z','date_method':'synthetic_explicit_date' if stamp else 'synthetic_unresolved_date','date_warnings':[]})
    (stage/'capture-manifest.json').write_text(json.dumps({'run_id':'synthetic-calendar-2013','start_date':'2013-01-01','end_date':'2013-12-31','posts':posts,'attempts':[],'lower_boundary_reached':False,'historical_full_year_completeness_claimed':False}))
    result=builder.build(stage);assert result['status']=='passed'
    archive=stage/'archive';rows=list(csv.DictReader((archive/'coverage.csv').open()));dates=[r['date'] for r in rows];by={r['date']:r for r in rows}
    assert len(rows)==365 and dates==sorted(dates,reverse=True)
    assert dates[0]=='2013-12-31' and dates[-1]=='2013-01-01'
    assert not any(d.endswith('-02-29') for d in dates)
    assert by['2013-07-15']['post_count']=='2'
    assert by['2013-01-01']['post_count']=='0' and by['2013-12-31']['post_count']=='0'
    inventory=json.loads((archive/'archive-manifest.json').read_text());index={r['path']:r['dates'] for r in inventory['indexes']}
    assert len(index['2013/02/index.html'])==28
    assert len(index['index.html'])==365 and len(index['2013/index.html'])==365
    assert (archive/'undated/index.html').is_file()
    assert not (archive/'2012').exists() and not (archive/'2014').exists()
    metrics=json.loads((archive/'metrics.json').read_text())
    assert metrics['calendar_days']==365 and metrics['days_with_maps']==1 and metrics['map_records']==2
    assert metrics['duplicate_date_count']==1 and metrics['unassigned_or_boundary_records']==1
print(json.dumps({'status':'passed','fixture_scope':'Synthetic calendar/rendering only; no historical dates or boundary inferred.','calendar_days':365,'date_order':'descending','first_date':'2013-12-31','last_date':'2013-01-01','february_days':28,'leap_day_present':False,'duplicate_source_records_preserved':True,'unresolved_record_kept_undated':True,'adjacent_year_folders_absent':True}))
