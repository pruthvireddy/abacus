"""Offline 2016 leap calendar using retained archive sources and honest coverage gaps."""
import csv,gzip,hashlib,importlib.util,json,tempfile,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
spec=importlib.util.spec_from_file_location('fixture_builder2016',ROOT/'studies/27_verniman_method_knowledge/build_daily_maps.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory(prefix='daily-map-2016-leap-') as tmp:
 s=Path(tmp);(s/'captures').mkdir();posts=[]
 for i,stamp in enumerate(['2016-12-01','2016-02-29','2016-01-05'],1):
  title='Outlook '+stamp[5:].replace('-','/')
  raw=('<h3 class="post-title">'+title+'</h3><div class="post-body entry-content"><p>Complete archived plan text.</p></div>').encode();gz=gzip.compress(raw,mtime=0);relative=f'captures/p{i}.html.gz';(s/relative).write_bytes(gz)
  posts.append({'url':f'https://verniman.blogspot.com/2016/fixture-{i}.html','session_date':stamp,'title':title,'html':{'path':relative,'bytes':len(gz),'sha256':hashlib.sha256(gz).hexdigest(),'uncompressed_sha256':hashlib.sha256(raw).hexdigest()},'images':[],'date_warnings':['Historical coverage is not complete.'],'capture_kind':'retained','date_method':'explicit_fixture_reviewed_title_date','captured_at':'2026-10-21T00:00:00Z','archive_observed_at':stamp+'T20:00:00Z','source_format':'archived_html'})
 (s/'capture-manifest.json').write_text(json.dumps({'run_id':'fixture2016','seed_url':posts[0]['url'],'start_date':'2016-01-01','end_date':'2016-12-31','lower_boundary_reached':False,'stop_reason':'retained_archive_collection','posts':posts}))
 result=builder.build(s);assert result['status']=='passed' and result['calendar_days']==366
 a=s/'archive';rows=list(csv.DictReader((a/'coverage.csv').open()));by={r['date']:r for r in rows}
 assert len(rows)==366 and rows[0]['date']=='2016-12-31' and rows[-1]['date']=='2016-01-01'
 assert [r['date'] for r in rows]==sorted(by,reverse=True)
 assert by['2016-02-29']['post_count']=='1' and by['2016-12-01']['post_count']=='1' and by['2016-01-05']['post_count']=='1'
 assert by['2016-12-31']['post_count']=='0' and by['2016-12-31']['status']=='no_dated_post_observed_weekend'
 assert by['2016-01-01']['post_count']=='0' and by['2016-01-01']['status']=='no_dated_post_observed_weekday'
 inv=json.loads((a/'archive-manifest.json').read_text());indexes={x['path']:x['dates'] for x in inv['indexes']};assert len(indexes['2016/02/index.html'])==29 and len(indexes['2016/12/index.html'])==31
 assert (a/'2016/02/29/index.html').is_file() and not(a/'2015').exists() and not(a/'2017').exists()
 metrics=json.loads((a/'metrics.json').read_text());assert metrics['map_records']==3 and metrics['retained_map_records']==3 and metrics['unassigned_or_boundary_records']==0
print(json.dumps({'status':'passed','calendar_days':366,'first_calendar_date':'2016-01-01','last_calendar_date':'2016-12-31','latest_fixture_map':'2016-12-01','earliest_fixture_map':'2016-01-05','leap_day_map':'2016-02-29','february_days':29,'lower_boundary_observed':False,'source_kind':'retained archive fixture'}))
