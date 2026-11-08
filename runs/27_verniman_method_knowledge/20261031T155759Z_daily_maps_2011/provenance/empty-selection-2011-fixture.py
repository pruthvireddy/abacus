"""No-network explicit reviewed zero-source guards; no historical absence inference."""
import contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True
root=Path('/Users/pruthvi/Documents/projects/abacus')
spec=importlib.util.spec_from_file_location('empty_selection2011',root/'studies/27_verniman_method_knowledge/recover_archived_daily_maps.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks={}
with tempfile.TemporaryDirectory(prefix='verniman-2011-empty-selection-',dir=root/'work') as temp:
    base=Path(temp)
    def desc(path):
        raw=path.read_bytes();return {'path':path.relative_to(root).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    def write(path,value):path.write_text(json.dumps(value));return desc(path)
    scope={'requested_start_date':'2011-01-01','anchor_session_date':'2011-12-31'}
    raw={'source':'verniman',**scope,'image_capture_status':'completed','posts':[],'files':[]}
    pre={'status':'passed','selected_source_ids':[],'selected_records':0,'dated':0,'undated':0,'image_references':0,'unique_image_hashes':0,'overlaps':[]}
    pre_path=base/'precheck.json';pre_rec=write(pre_path,pre)
    empty={'status':'reviewed_no_in_scope_daily_plans',**scope,'reason':'Synthetic zero-source fixture only, not proof of historical absence.','independent_selection_precheck':pre_rec}
    limits={**scope,'lower_boundary_observed':False,'historical_full_year_completeness_claimed':False}
    review={'schema_version':'daily-map-archive-source-review-1','review_status':'reviewed',**scope,'historical_full_year_completeness_claimed':False,
            'source_recovery_manifest':write(base/'raw.json',raw),'selection_precheck':pre_rec,
            'chronology_review':write(base/'chronology.json',limits),'collection_completion_review':write(base/'completion.json',limits),
            'empty_daily_selection_review':empty,'supporting_files':[]}
    review_path=base/'review.json';write(review_path,review)
    def project(name='selected.json',document=None,year=2011):
        write(review_path,review if document is None else document)
        with contextlib.redirect_stdout(io.StringIO()):m.reviewed_collection(SimpleNamespace(root=root,year=year,review_selection=review_path,reviewed_output=base/name))
        return json.loads((base/name).read_text())
    result=project();assert result['posts']==[] and len(result['coverage'])==365
    assert result['empty_daily_selection_review']['review_record']==result['collection_review']
    assert result['empty_daily_selection_review']['independent_selection_precheck']==result['selection_review']
    checks['reviewed_2011_empty_selection_preserves365_dates_and_exact_review_pins']=True
    assert sum(r['session_date']=='2011-02-29' for r in result['coverage'])==0
    assert sum(r['session_date'].startswith('2011-02-') for r in result['coverage'])==28
    checks['reviewed_empty_selection_preserves28February_without_leap_day']=True
    def reject(name,mutate,year=2011):
        changed=copy.deepcopy(review);mutate(changed)
        try:project(name+'.json',changed,year)
        except ValueError:checks[name]=True
        else:raise AssertionError(name)
    reject('unreviewed_empty_selection_rejected',lambda d:d.pop('empty_daily_selection_review'))
    reject('wrong_empty_status_rejected',lambda d:d['empty_daily_selection_review'].update(status='assumed_empty'))
    reject('wrong_empty_scope_rejected',lambda d:d['empty_daily_selection_review'].update(anchor_session_date='2014-12-31'))
    reject('empty_reason_rejected',lambda d:d['empty_daily_selection_review'].update(reason=' '))
    reject('empty_precheck_identity_drift_rejected',lambda d:d['empty_daily_selection_review']['independent_selection_precheck'].update(sha256='0'*64))
    changed_pre={**pre,'selected_records':1};bad_rec=write(base/'bad-precheck.json',changed_pre)
    reject('nonzero_precheck_rejected',lambda d:(d.update(selection_precheck=bad_rec),d['empty_daily_selection_review'].update(independent_selection_precheck=bad_rec)))
    changed_pre={**pre,'image_references':False};bad_bool_rec=write(base/'bool-precheck.json',changed_pre)
    reject('boolean_is_not_integer_zero_precheck_rejected',lambda d:(d.update(selection_precheck=bad_bool_rec),d['empty_daily_selection_review'].update(independent_selection_precheck=bad_bool_rec)))
    reject('cross_requested_year_rejected',lambda d:None,2014)
assert len(checks)==10 and all(checks.values())
print(json.dumps({'status':'passed','checks':checks,'check_count':len(checks),'network_requests':0,'temporary_fixture_only':True},indent=2))
