import copy, hashlib, importlib.util, json, sys, tempfile
from datetime import date
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'studies/27_verniman_method_knowledge' / file)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
adapter = module('empty_adapter', 'capture_retained_daily_maps.py')
builder = module('empty_builder', 'build_daily_maps.py')
checks = {}
with tempfile.TemporaryDirectory(prefix='daily-map-2013-empty-') as temporary:
    root = Path(temporary)
    def write(name, raw):
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    def document():
        precheck = write('input/precheck.json', json.dumps({'status': 'passed', **{k: 0 for k in ['selected_records','dated','undated','image_references','unique_image_hashes']}}).encode())
        review = {'status': 'reviewed_no_in_scope_daily_plans', 'requested_start_date': '2013-01-01', 'anchor_session_date': '2013-12-31', 'reason': 'Synthetic retained body is educational context; no in-scope morning source established.', 'independent_selection_precheck': precheck}
        original = write('input/review.json', json.dumps({'empty_daily_selection_review': review}).encode())
        raw = write('input/source.html', b'<h3 class="post-title">Synthetic method</h3><div class="post-body">Educational context.</div>')
        result = {'source':'verniman','requested_start_date':'2013-01-01','anchor_session_date':'2013-12-31','posts': [], 'files': [raw], 'chronology_review':original,'collection_completion_review':original,'archive_capture_manifest':original,'collection_review':original,'selection_review':precheck,'empty_daily_selection_review':{**review,'review_record':original}}
        return result
    def prepare(doc):
        record = write('input/collection.json', json.dumps(doc).encode())
        return adapter.Adapter(root).prepare(root / record['path'], date(2013,1,1), date(2013,12,31), record['sha256'])
    def reject(name, edit):
        doc = document(); edit(doc)
        try: prepare(doc)
        except (ValueError, KeyError, TypeError): checks[name] = True
        else: raise AssertionError(name)
    def alter_precheck(doc, count):
        values = {'status':'passed', **{k:0 for k in ['selected_records','dated','undated','image_references','unique_image_hashes']}}
        values['selected_records'] = count
        precheck = write('input/precheck.json', json.dumps(values).encode())
        doc['selection_review'] = precheck
        doc['empty_daily_selection_review']['independent_selection_precheck'] = precheck
        authored = {k:v for k,v in doc['empty_daily_selection_review'].items() if k != 'review_record'}
        review = write('input/review.json', json.dumps({'empty_daily_selection_review':authored}).encode())
        for key in ['chronology_review','collection_completion_review','archive_capture_manifest','collection_review']:
            doc[key] = review
        doc['empty_daily_selection_review']['review_record'] = review
    reject('unreviewed_empty_collection_rejected', lambda d: d.pop('empty_daily_selection_review'))
    reject('empty_review_wrong_scope_rejected', lambda d: d['empty_daily_selection_review'].update(anchor_session_date='2014-12-31'))
    reject('empty_reason_rejected', lambda d: d['empty_daily_selection_review'].update(reason=''))
    reject('changed_review_pin_rejected', lambda d: d['empty_daily_selection_review']['review_record'].update(sha256='0'*64))
    reject('changed_precheck_pin_rejected', lambda d: d['empty_daily_selection_review']['independent_selection_precheck'].update(sha256='0'*64))
    reject('authored_decision_drift_rejected', lambda d: d['empty_daily_selection_review'].update(reason='Changed decision without new review.'))
    reject('positive_precheck_count_rejected', lambda d: alter_precheck(d, 1))
    reject('boolean_zero_precheck_rejected', lambda d: alter_precheck(d, False))
    reject('selected_posts_conflict_with_empty_review', lambda d: d.update(posts=[{'synthetic':True}]))
    doc = document(); collection = write('input/collection.json', json.dumps(doc).encode()); stage = root / 'stage'
    result = adapter.adapt(root, stage, root / collection['path'], date(2013,1,1), date(2013,12,31), collection['sha256'])
    assert result['posts'] == 0 and result['image_references'] == 0 and result['network_requests'] == 0
    captured = json.loads((stage/'capture-manifest.json').read_text()); assert captured['seed_url'] is None and captured['posts'] == []
    checks['reviewed_empty_adaptation_has_no_invented_seed_posts_or_images'] = True
    built = builder.build(stage); audited = builder.check(stage); assert built['calendar_days'] == 365 and audited['map_records'] == 0
    metrics = json.loads((stage/'archive/metrics.json').read_text()); assert metrics['weekday_gaps'] == 261 and metrics['weekend_gaps'] == 104
    assert not (stage/'archive/assets').exists() and not (stage/'archive/undated').exists()
    index = (stage/'archive/index.html').read_text(); assert 'No in-scope daily plans could be established' in index and 'source-review.json' in index
    assert (stage/'archive/2013/02/index.html').read_text().count('<tr data-date=') == 28
    assert index.count('<tr data-date=') == 365
    checks['empty_reader_roundtrip_preserves_all_365_gaps_and_review'] = True
    bad = copy.deepcopy(captured); bad.pop('empty_daily_selection_review'); (stage/'capture-manifest.json').write_text(json.dumps(bad))
    try: builder.reviewed_empty_selection(stage, bad)
    except ValueError: checks['builder_rejects_unreviewed_empty_capture'] = True
    else: raise AssertionError('builder accepted missing review')
    changed = copy.deepcopy(captured); changed['empty_daily_selection_review']['reason'] = 'Altered without retained copy.'
    try: builder.reviewed_empty_selection(stage, changed)
    except ValueError: checks['builder_rejects_empty_review_drift'] = True
    else: raise AssertionError('builder accepted drift')
    assert adapter.canonical('http://verniman.blogspot.com.ar:80/2013/06/example.html?m=1') == 'https://verniman.blogspot.com/2013/06/example.html'
    checks['observed_country_alias_canonicalizes_without_changing_permalink_path'] = True
    try: adapter.canonical('https://verniman.blogspot.com.example.org/2013/example.html')
    except ValueError: checks['unrecognized_alias_rejected'] = True
    else: raise AssertionError('unknown host accepted')
print(json.dumps({'status':'passed','scope':'Synthetic reviewed empty-year retention/rendering and alias guards; no historical absence inferred.','check_count':len(checks),'checks':checks},indent=2))
