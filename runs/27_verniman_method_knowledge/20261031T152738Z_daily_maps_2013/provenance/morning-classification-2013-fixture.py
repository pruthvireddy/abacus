"""Synthetic exact-source classification scope guards; no historical membership inference."""
import copy, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
root = Path('/Users/pruthvi/Documents/projects/abacus')
spec = importlib.util.spec_from_file_location('classification2013', root/'studies/27_verniman_method_knowledge/recover_archived_daily_maps.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
checks = {}
with tempfile.TemporaryDirectory(prefix='verniman-2013-classification-', dir=root/'work') as temp:
    base=Path(temp)
    def record(path):
        raw=path.read_bytes(); return {'path':path.relative_to(root).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    review_file=base/'review.json';review_file.write_text('{"synthetic":true}')
    review_record=record(review_file)
    def source(title):
        body='Overnight inventory and a prospective opening auction. Synthetic fixture only.'
        path=base/'source.html';path.write_text('<a name="12345"></a><h3 class="post-title">'+title+'</h3><div class="post-body">'+body+'</div>')
        post={'source_post_id':'12345','title':title,'url':'https://verniman.blogspot.com/2013/01/fixture.html','body_text':body,'source_format':'archived_html','html':record(path),'role':'excluded_context_candidate'}
        post_file=base/'post.json';post_file.write_text(json.dumps(post));post['post_record']=record(post_file)
        decision={'status':'reviewed_morning_plan','source_post_id':'12345','source_title':title,'source_post_record':post['post_record'],'normalized_body_sha256':module.sha(module.PARSER.text_identity(body).encode()),'session_date':'2013-01-02','reason':'Synthetic exact classification fixture only.','year_context_reason':'Synthetic2013 scope fixture, not historical source evidence.'}
        return post,decision
    def classify(post,decision,year=2013):
        return module.reviewed_morning_classification(copy.deepcopy(post),copy.deepcopy(decision),review_record,module.PARSER.Adapter(root),year)
    for title in ['Market Update 0102','Update 01/02']:
        p,d=source(title);r=classify(p,d);assert r['session_date']=='2013-01-02' and r['year_evidence']['year']==2013
        assert p['role']=='excluded_context_candidate'
    checks['2013_exact_existing_title_families_accepted_without_raw_change']=True
    for year in [2012,2015]:
        p,d=source('Market Update 0102')
        try: classify(p,d,year)
        except ValueError: checks[f'classification_scope_{year}_rejected']=True
        else:raise AssertionError(year)
    p,d=source('Market Update 0102');d['session_date']='2014-01-02'
    try:classify(p,d)
    except ValueError:checks['classification_assigned_year_drift_rejected']=True
    else:raise AssertionError('assigned year')
    p,d=source('Market Update 0102');d['normalized_body_sha256']='0'*64
    try:classify(p,d)
    except ValueError:checks['classification_actual_body_drift_rejected']=True
    else:raise AssertionError('body drift')
assert len(checks)==5 and all(checks.values())
print(json.dumps({'status':'passed','checks':checks,'check_count':len(checks),'network_requests':0,'temporary_fixture_only':True},indent=2))
